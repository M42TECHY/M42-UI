"""🧩 The user's idea (2026-11-17): a page as numbered blocks (a short map for the 4B, no code), the 4B picks the
block by its number (or the user clicks it on the preview), writes that block alone, and M42 puts it in the file's
own text: every other byte stays. Checked here without a model: the index, the map, the splice, the preview's
marks (never in the file or the download), the clicked block found again, and the block edit's guards."""
from pathlib import Path
import io
import json
import os
import sys
import tempfile
import zipfile

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import domnode  # noqa: E402
import llm  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Plans</title>
<style>.card{border:1px solid #ddd}</style>
</head>
<body class="m42-ui">
  <nav class="top-bar"><a href="#">Home</a> <a href="#plans">Plans</a></nav>
  <section id="plans" class="m42-section">
    <h2>Pricing</h2>
    <div class="grid-layout">
      <div class="card"><h3>Basic</h3><p class="price">&#8377;299</p><button class="buy" data-plan="basic">Buy</button></div>
      <div class="card"><h3>Pro</h3><p class="price">&#8377;999</p><button class="buy" data-plan="pro">Buy</button></div>
      <div class="card"><h3>Enterprise</h3><p class="price">&#8377;1999</p><button class="buy">Buy</button></div>
    </div>
    <img src="images/team.jpg" alt="Team">
    <p>Unclosed paragraph
  </section>
  <footer><p>(c) Shop</p></footer>
  <script>document.querySelectorAll('.buy').forEach(function(b){b.onclick=function(){alert(b.dataset.plan)}});</script>
</body>
</html>
"""

nodes = domnode.index(PAGE)
check("every node starts at its own tag", all(PAGE[n["start"]:].lower().startswith("<" + n["tag"]) for n in nodes.values()))
cards = [i for i, n in nodes.items() if n["attrs"].get("class") == "card"]
check("three cards found", len(cards) == 3, cards)
pro = nodes[cards[1]]
check("a card's text is the whole card", domnode.source(PAGE, pro).startswith('<div class="card"><h3>Pro') and
      domnode.source(PAGE, pro).endswith("</button></div>"), domnode.source(PAGE, pro))
check("a void <img> ends at its tag", domnode.source(PAGE, next(n for n in nodes.values() if n["tag"] == "img")) ==
      '<img src="images/team.jpg" alt="Team">')
sec = next(i for i, n in nodes.items() if n["attrs"].get("id") == "plans")
check("an unclosed <p> ends where its section closes", nodes[sec]["end"] > next(
    n for n in nodes.values() if n["tag"] == "p" and "Unclosed" in " ".join(n["words"]))["end"])

mp = domnode.skeleton(nodes, domnode.body_nodes(nodes))
check("the map: blocks with their words, no code", f'[{cards[1]}] <div.card> "Pro | ₹999 | Buy"' in mp and "<style" not in mp
      and "querySelectorAll" not in mp, mp)
check("the map: the section's id and the img's file", "section#plans.m42-section" in mp and 'src="team.jpg"' in mp, mp)

# the splice: only the block's own bytes change
new = domnode.splice(PAGE, pro, '<div class="card gold"><h3>Pro</h3><p class="price">&#8377;499</p><button class="buy" data-plan="pro">Buy</button></div>')
a, b = PAGE[:pro["start"]], PAGE[pro["end"]:]
check("splice: every other byte as it was", new.startswith(a) and new.endswith(b) and "&#8377;499" in new)
check("splice of the same text: the same file", domnode.splice(PAGE, pro, domnode.source(PAGE, pro)) == PAGE)

# the preview's marks: on the copy only, and gone from the download
marked = webkit.pickable(PAGE)
check("preview: blocks marked with their numbers", f'data-m42-n="{cards[1]}"' in marked and 'id="m42-pick"' in marked)
check("preview: no mark in <head>", 'data-m42-n' not in marked[:marked.find("<body")])
check("preview: the marks taken off give the page back", webkit.unpickable(marked) == PAGE)
tmp = Path(tempfile.mkdtemp())
(tmp / "src").mkdir()
(tmp / "src" / "index.html").write_text(PAGE, encoding="utf-8")
pid = webkit.make_preview_folder(tmp / "src", tmp / "prev", ["index.html"])
shown = (tmp / "prev" / pid / "index.html").read_text(encoding="utf-8")
check("preview folder: its page has the marks", "data-m42-n" in shown)
z = zipfile.ZipFile(io.BytesIO(webkit.preview_zip(tmp / "prev", pid)))
check("download: the page without the marks", z.read("m42-page/index.html").decode("utf-8") == PAGE)
check("project file untouched", (tmp / "src" / "index.html").read_text(encoding="utf-8") == PAGE)

# hooks: what the page's script reads, kept
check("hooks: the class the script reads", ".buy" in domnode.hooks(PAGE, domnode.source(PAGE, pro)))
check("hooks lost: a rename of .buy", domnode.lost_hooks(PAGE, domnode.source(PAGE, pro),
                                                         '<div class="card"><button class="btn">Buy</button></div>') == [".buy"])

# the agent: the clicked block found again; the block edit with a fake 4B
calls = []


def fake(base, model, msgs, schema, **k):
    calls.append((msgs, schema))
    if "target" in schema["properties"]:
        return {"target": str(cards[1]), "why": "the Pro card"}, {}
    if len([c for c in calls if "code" in c[1]["properties"]]) == 1 and "lost" not in msgs[-1]["content"]:
        return {"code": '<div class="card"><h3>Pro</h3><p class="price">&#8377;499</p><button class="btn">Buy</button></div>',
                "add": "", "where": "", "why": "price"}, {}
    return {"code": '<div class="card" style="border:2px solid gold"><h3>Pro</h3><p class="price">&#8377;499</p>'
                    '<button class="buy" data-plan="pro">Buy</button></div>', "add": "", "where": "", "why": "price 499, gold border"}, {}


llm.complete_json = fake
ag = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
ag.load([], {"id": "t", "name": "t", "folders": [str(tmp / "src")]})
notes = []
emit = lambda ev: notes.append(ev.get("message") or ev.get("text") or "")  # noqa: E731
edits, out = ag._node_edit(PAGE, "index.html", "Pro plan price 499 and a golden border", emit)
check("the 4B picked the block from the map (its number only)", any("target" in c[1]["properties"] for c in calls))
check("a block edit that lost .buy: asked again", any("lost .buy" in n for n in notes), notes)
check("the block put in place, the rest as it was", out and out.startswith(PAGE[:pro["start"]]) and out.endswith(PAGE[pro["end"]:])
      and "gold" in out, out and out[pro["start"] - 20:pro["start"] + 200])
check("kept as one edit (the old block -> the new one)", edits and edits[0][0] == domnode.source(PAGE, pro))
pick = ag.pick_node({"page": "index.html", "n": cards[2], "tag": "div", "words": "Enterprise", "sig": domnode.signature(PAGE)})
check("a click on the preview: its block in the file", pick and pick["node"] == cards[2] and pick["words"].startswith("Enterprise"), pick)
pick = ag.pick_node({"page": "index.html", "n": 999, "tag": "div", "words": "Enterprise ₹1999 Buy", "sig": "old"})
check("a preview older than the file: the block found by its words", pick and pick["node"] == cards[2], pick)
check("a click outside the folder: nothing", ag.pick_node({"page": "../x.html", "n": 1, "tag": "div"}) is None)
calls.clear()
edits, out = ag._node_edit(PAGE, "index.html", "make it gold", emit, node=cards[1])
check("a clicked block: no map read, the block edited", out and not any("target" in c[1]["properties"] for c in calls))

# 🧩 a page drawn again from its plan: only the parts the change made go into the page as it is
OLD = PAGE
NEW = PAGE.replace("<h2>Pricing</h2>", "<h2>Our prices</h2>").replace("(c) Shop", "(c) Shop 2026")
NOW = PAGE.replace("&#8377;999", "&#8377;499").replace("</head>", "<style>.mine{}</style>\n</head>")
m = domnode.merge_render(OLD, NEW, NOW)
check("merge: the changed parts in", m and "Our prices" in m and "(c) Shop 2026" in m, m)
check("merge: the user's own edits kept", m and "&#8377;499" in m and ".mine{}" in m)
check("merge: nothing else changed", m and m == NOW.replace("<h2>Pricing</h2>", "<h2>Our prices</h2>").replace("(c) Shop", "(c) Shop 2026"))
check("merge: the same drawing: the file as it is", domnode.merge_render(OLD, OLD, NOW) == NOW)
RENAMED = PAGE.replace('id="plans"', 'id="prices"').replace('href="#plans"', 'href="#prices"')
m = domnode.merge_render(OLD, RENAMED, NOW)
check("merge: a renamed section's link outside it follows", m and 'href="#prices"' in m and 'id="prices"' in m and "&#8377;499" in m)
ADDED = PAGE.replace("<footer>", "<section><h2>FAQ</h2></section>\n  <footer>")
check("merge: a section added: None (the whole page drawn, edits carried)", domnode.merge_render(OLD, ADDED, NOW) is None)

# 🎨 the user's asked looks and their CSS's classes on the built page (fake 4B)
check("a name with the listing echoed back: cleaned", agent.Agent._plain_name("menu [cards] Glassmorphism cards") == "menu")
check("a plain name kept", agent.Agent._plain_name("Signature Drinks") == "Signature Drinks")
n2 = domnode.index(PAGE)
prices = [i for i, n in n2.items() if n["attrs"].get("class") == "price"]
withcls = domnode.add_class(PAGE, n2, prices, "menu-price")
check("add_class: the class on each block, the rest as it was", withcls.count('class="price menu-price"') == 3
      and withcls.replace(" menu-price", "") == PAGE)
ASKED = 'Pricing page, glassmorphism cards, add this CSS: ```css\n.menu-price{color:#b45309}\n```'


def fake2(base, model, msgs, schema, **k):
    if "ids" in schema["properties"]:
        return {"ids": [str(i) for i in prices]}, {}
    return {"css": ".card{background:rgba(255,255,255,.18);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.3)}",
            "why": "glass cards"}, {}


llm.complete_json = fake2
page2 = webkit.inject_user_code(PAGE, *webkit.user_code(ASKED))
out = ag._asked_looks(page2, {"styles": ["glassmorphism cards"]}, ASKED, emit)
check("looks: the pasted CSS's class on the prices", out.count("menu-price") >= 4, out[:200])
check("looks: the glass CSS after the page's CSS", 'data-m42-asked="looks"' in out and "backdrop-filter" in out)


def fake3(base, model, msgs, schema, **k):
    if "ids" in schema["properties"]:
        return {"ids": []}, {}
    return {"css": ".nothere{color:red}", "why": "x"}, {}


llm.complete_json = fake3
out = ag._asked_looks(PAGE, {"styles": ["neon"]}, "neon page", emit)
check("looks: CSS for classes the page lacks is left out", "nothere" not in out)

# 🧩 the plan bound to the spec's sections by name: order, a duplicate dropped, a missing one written alone
import pagebuild  # noqa: E402
SPEC = {"frame_items": ["Footer"], "items": [{"name": "Sales Chart", "shows": "a chart"}, {"name": "Footer", "shows": "links"}], "sections": [{"name": "menu", "part": "image_cards", "role": "offer"}, {"name": "sales", "part": "bar_chart", "asks": ["Sales Chart"]},
                     {"name": "location", "part": "table"}]}
names = pagebuild.bound_names(SPEC)
RAW = {"brand": {"name": "Bean Story"}, "sections": [
    {"for": "sales", "part": "stats", "title": "Our sales", "items": [{"title": "Jan", "value": 120}]},
    {"for": "menu", "part": "cards", "title": "Menu", "items": [{"title": "Espresso", "value": 120}]},
    {"for": "menu", "part": "cards", "title": "Menu again", "items": [{"title": "Latte"}]}]}


def fake4(base, model, msgs, schema, **k):
    return {"section": {"part": "cards", "title": "Visit Us", "items": [{"title": "Anna Nagar, Chennai"}]}}, {}


llm.complete_json = fake4
bound, spec_b = ag._bind_plan(RAW, SPEC, names, "coffee", emit, None)
check("bound: the spec's order, one each", [s.get("title") for s in bound["sections"]] == ["Menu", "Our sales", "Visit Us"],
      [s.get("title") for s in bound["sections"]])
check("bound: the missing one written alone, with its own part", bound["sections"][2]["part"] == "table")
check("bound: no 'for' left in the plan", not any("for" in s for s in bound["sections"]))
plan_b = pagebuild.clean(bound, spec_b)
check("bound: each section drawn as its spec row's part", [s["part"] for s in plan_b["sections"]][:2] == ["image_cards", "bar_chart"]
      or [s["part"] for s in plan_b["sections"]][1] == "bar_chart", [s["part"] for s in plan_b["sections"]])
check("bound: the asks of the sections written count as on the page", set(spec_b.get("placed") or []) == {"Footer", "Sales Chart"})
import webkit as wk  # noqa: E402
check("bound: no word check says a placed ask is missing", not wk.spec_problems(spec_b, "<html><body>nothing</body></html>"),
      wk.spec_problems(spec_b, "<html><body>nothing</body></html>"))

# 🧩 the asks read with every one "inside" its section (a real build): taken as the section itself, each ask once
def fake5(base, model, msgs, schema, **k):
    props = schema["properties"]
    if "asks" in props:
        return {"asks": [{"item": "Sales Chart", "place": "inside sales", "part": "stats", "role": "", "name": "", "what": ""},
                         {"item": "Gallery", "place": "inside gallery", "part": "gallery", "role": "", "name": "", "what": ""},
                         {"item": "Menu", "place": "inside menu", "part": "cards", "role": "", "name": "", "what": ""},
                         {"item": "Menu", "place": "inside menu", "part": "cards", "role": "", "name": "", "what": ""}],
                "libraries": []}, {}
    if "part" in props:
        said = msgs[-1]["content"]
        return {"part": "bar_chart" if "Sales" in said else "keep"}, {}
    if "styles" in props:
        return {"styles": []}, {}
    return {}, {}


llm.complete_json = fake5
rows5 = [{"name": "menu", "part": "cards"}, {"name": "sales", "part": "stats"}, {"name": "gallery", "part": "gallery"}]
spec5 = {"items": [{"name": "Sales Chart", "shows": "bar chart of sales"}, {"name": "Gallery", "shows": "photos"},
                   {"name": "Menu", "shows": "drinks"}]}
out5 = ag._landing_asks("coffee page with a sales chart, a gallery and the menu", spec5, rows5, emit, None)
check("all-inside: the sales section drawn as the chart asked", next(r for r in out5 if "Sales Chart" in (r.get("asks") or []))["part"] == "bar_chart",
      [(r["name"], r["part"]) for r in out5])
check("all-inside: each ask once in its section", [r.get("asks") for r in out5] == [["Menu"], ["Sales Chart"], ["Gallery"]], [r.get("asks") for r in out5])

# 🩹 links to files the folder does not have: taken out, for any page
root_ = Path(tempfile.mkdtemp())
(root_ / "js").mkdir()
(root_ / "js" / "app.js").write_text("x")
PAGE_L = ('<html><head><link rel="stylesheet" href="lib/m42-ui.css"><link rel="stylesheet" href="css/nope.css"></head><body>'
          '<script src="m42-cart.js"></script>\n<script src="js/app.js"></script>\n<script src="js/app.js"></script>\n'
          '<script src="https://cdn.example/x.js"></script>\n</body>\n</html>\n<script src="m42-cart.js"></script>')
mended, gone_ = webkit.mend_refs(PAGE_L, root_)
check("refs: a missing file's script and stylesheet taken out", "m42-cart.js" not in mended and "nope.css" not in mended, gone_)
check("refs: the kit, a real file and the web kept", all(x in mended for x in ("lib/m42-ui.css", "js/app.js", "https://cdn.example/x.js")))
check("refs: a script linked twice, once", mended.count("js/app.js") == 1)
check("refs: nothing after </html>", mended.rstrip().endswith("</html>"))

# ★ in an app's column: the main tool, then the work, then what helps it (any kind)
import appflows  # noqa: E402


def fake6(base, model, msgs, schema, **k):
    if "asks" in schema["properties"]:
        return {"asks": [{"item": "Cart", "place": "Current bill", "part": "", "name": "", "what": ""},
                         {"item": "Footer", "place": "FRAME", "part": "", "name": "", "what": ""}], "main": "", "libraries": []}, {}
    return {}, {}


llm.complete_json = fake6
pos_ = ag._skeleton_spec("a POS", {"items": [{"name": "Cart", "shows": "bill"}, {"name": "Footer", "shows": "links"}]},
                         appflows.skeleton("pos"), emit, None, "r")
left = [s["part"] for s in pos_["sections"] if s["slot"] == [0, 0]]
check("column: the products first, filters and the day's numbers under them", left == ["image_cards", "category_chips", "kpi_tiles"], left)
check("column: the layout says the same order", pos_["app_layout"][0][0]["parts"] == left)
check("app asks: each ask kept with its section, the frame's too",
      next(s for s in pos_["sections"] if s["part"] == "invoice").get("asks") == ["Cart"] and pos_.get("frame_items") == ["Footer"])

# 🩹 a CDN link to a library the folder has: its own copy; a cut name made whole
(root_ / "lib").mkdir(exist_ok=True)
(root_ / "lib" / "chart.js-4.6.1-chart.umd.min.js").write_text("x")
cdn, gone2 = webkit.mend_refs('<html><body><script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>'
                              '<script src="lib/m42-ui.js"></script><script src="m42-ui.js"></script></body></html>', root_)
check("refs: the web's Chart.js -> the folder's own copy", 'src="lib/chart.js-4.6.1-chart.umd.min.js"' in cdn and "jsdelivr" not in cdn, cdn)
check("refs: the kit by its own name is never taken for missing", "m42-ui.js (no such file)" not in " ".join(gone2), gone2)
check("name: a cut brand made whole", pagebuild.whole_name("NexusHome IoT Hub Pro v2.4.1 (") == "NexusHome IoT Hub Pro v2.4.1")
check("one reading: all asks in the frame", agent.Agent._one_reading([{"place": "FRAME"}] * 4)
      and not agent.Agent._one_reading([{"place": "FRAME"}, {"place": "Devices"}, {"place": "NEW section"}]))

print("FAILS:", fails)
sys.exit(1 if fails else 0)
