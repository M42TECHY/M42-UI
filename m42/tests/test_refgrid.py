"""Steps 1, 2 and 4 of building from a reference (the user, 2026-10-27: "every widget the reference has must come"):
the reference's cards and grid from its pixels, each card's widget from the vision model, the grid rendered as the
page's layout, and a card the library lacks written by the coder, cleaned, and kept as an example."""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import designref  # noqa: E402
import tempfile as _tf  # noqa: E402
designref.READS = Path(_tf.mkdtemp())  # (the readings this test makes are not kept for the app)
import learn  # noqa: E402
import llm  # noqa: E402
import pagebuild  # noqa: E402
import webkit  # noqa: E402

HERE = Path(__file__).resolve().parent
fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:400])
    fails += not ok


def leaves(n):
    return [n["leaf"]] if "leaf" in n else [x for c in n["children"] for x in leaves(c)]


# ---- Step 1: cards and grid from the user's references ----
want = {"63": (7, True), "64": (8, True), "66": (7, True), "62": (7, True)}  # (66 SchoolHub: 7 since its banner is one card, 2026-10-30) smart home (security photo, white-on-white door / theatre cards, a text menu), ClothIQ, SchoolHub, Travelgo (shadow-only cards)
for f, (n_min, side) in want.items():
    g = designref.cards(HERE / "refs" / f"{f}.webp")
    check(f"ref {f}: at least {n_min} cards, sidebar {side}", g and len(g["boxes"]) >= n_min and g["sidebar"] == side,
          g and (len(g["boxes"]), g["sidebar"]))
    if g:
        check(f"ref {f}: the grid's leaves are the cards in reading order", leaves(g["tree"]) == list(range(len(g["boxes"]))))
g64 = designref.cards(HERE / "refs" / "64.webp")
check("ClothIQ: a right column of task cards beside the main area", g64["tree"]["dir"] == "cols" and len(g64["tree"]["children"]) == 2
      and g64["tree"]["children"][1]["dir"] == "rows", json.dumps(g64["tree"])[:300])
_blank = HERE / "_work" / "blank.png"  # (it read test_pagebuild's screenshot, which may not be there)
__import__("PIL.Image").Image.new("RGB", (1200, 800), "white").save(_blank)
check("a blank picture has no grid", designref.cards(_blank) is None)

g62 = designref.cards(HERE / "refs" / "62.webp")
check("Travelgo: no card from the pink arc above the board; the 4 number tiles are one card (a row)",
      g62 and all(b[1] > .15 for b in g62["boxes"]) and any(b[2] - b[0] > .5 and b[3] - b[1] < .15 for b in g62["boxes"]), g62 and g62["boxes"])
check("Travelgo: the review card cut by the picture's bottom edge is a card (the 70% / 30% card and it stack on the right)",
      g62 and any(b[1] > .8 and b[0] > .5 for b in g62["boxes"]), g62 and g62["boxes"])
# (2026-11-12: no word rules on the model's description: what it answers stands; a card it lists as two rings in its
# blocks is drawn from them)
check("the model's own widget stands (no word rule rewrites its answer)",
      designref.clean_card({"widget": "donut", "what": "Two donut charts side by side, each with a percentage", "count": 2})["widget"] == "donut")
check("... and a card whose blocks mix kinds is drawn from its blocks",
      designref.clean_card({"widget": "donut", "what": "x", "count": 2, "blocks": ["heading", "date range", "donut", "legend"]})["widget"] == "composed")
p62 = designref.profile(HERE / "refs" / "62.webp")
check("the colour the vision model names, in the picture's shade (Travelgo: purple, not the pink room)",
      designref.merge({}, [designref.clean_brief({"accent": "purple", "layout": "sidebar"})], [p62], "x")["look"]["colors"][0] == p62["shades"]["purple"])
g79 = designref.cards(HERE / "refs" / "79.webp")
check("D.CC: its grid, not one column of cards (Stores ran 1.7% into the next row: the cut found no gutter)",
      g79 and g79["tree"]["dir"] == "rows" and len(g79["tree"]["children"]) == 2 and g79["tree"]["children"][1]["dir"] == "cols",
      g79 and g79["tree"])
# how each card is drawn inside (the D.CC shot: striped bars, an arrow / "This Month" on each card, pills)
lk = designref.clean_card({"widget": "bar_chart", "what": "bars by month", "count": 9, "header": "dropdown and arrow", "bars": "one highlighted",
                           "progress_bar": "no", "boxes": "no", "status_pills": "no", "photos": "no"})["look"]
check("the card's look is read: a dropdown and an arrow, one highlighted bar", lk == {"header": "both", "bars": "one highlighted"}, lk)
th = webkit.make_theme("dashboard", look={"theme": "light", "colors": ["#f76f42"]})
vsecs = [{"part": "kpi_tiles", "title": "Orders", "items": [{"title": "Pending", "value": 25, "badge": "75%", "text": "Total 57"}]},
         {"part": "bar_chart", "title": "Revenue", "labels": ["Jan", "Feb", "Mar"], "items": [{"title": "R", "values": [3, 9, 5]}]},
         {"part": "list_thumbs", "title": "Stores", "items": [{"title": "Anna Nagar", "text": "Chennai", "badge": "Closed"}]}]
vg = {"sidebar": True, "tree": {"dir": "rows", "children": [{"leaf": k, "box": [0, k / 3, 1, (k + 1) / 3]} for k in range(3)], "box": [0, 0, 1, 1]}}
vp = pagebuild.render({"brand": {"name": "D", "icon": "bi-shop"}, "hero": {"title": "Dashboard"}, "sections": vsecs, "footer": ""},
                      {"hero": "compact", "ref_layout": "sidebar", "ref_grid": vg, "sections": [
                          {"part": "kpi_tiles", "look": {"progress": True}}, {"part": "bar_chart", "look": {"header": "both", "bars": "one highlighted"}},
                          {"part": "list_thumbs", "look": {"photos": True, "pills": True}}]}, th, "restaurant dashboard")
check("the looks drawn: a striped progress bar, a highlighted bar with its tip, This Month and an arrow, a photo tile and a red 'Closed' pill",
      "m42-w-track is-striped" in vp and "m42-w-bartip" in vp and "is-pale" in vp and "This Month" in vp and "bi-arrow-up-right" in vp
      and "m42-w-thumb is-photo" in vp and 'm42-badge is-bad">Closed' in vp)
check("a page with no looks keeps the plain widgets", "is-striped" not in pagebuild.render(
    {"brand": {"name": "D", "icon": "bi-shop"}, "hero": {}, "sections": vsecs, "footer": ""}, {"hero": "compact", "ref_layout": "sidebar"}, th, "x"))
probs = webkit.kit_problems({"v.html": vp}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes in the looks", not [p for ps in probs.values() for p in ps], probs)
# one item's parts (row template): read by the 4B, drawn row by row
check("row template: '#4587 · Wait 9 min' read as numbers and an icon is meta",
      designref.clean_item(["photo", "title", "number", "number", "icon", "pill"]) == ["photo", "title", "meta", "pill"])
ra = {"part": "notifications", "title": "Recent Activity", "items": [{"title": "Order ready", "meta": ["₹109.00", "#4587", "Wait 9 min"], "badge": "Completed"}]}
rp = pagebuild.render({"brand": {"name": "D", "icon": "bi-shop"}, "hero": {"title": "Dashboard"}, "sections": [ra], "footer": ""},
                      {"hero": "compact", "ref_layout": "sidebar", "ref_grid": {"sidebar": True, "tree": {"leaf": 0, "box": [0, 0, 1, 1]}},
                       "sections": [{"part": "notifications", "look": {"row": ["photo", "title", "meta", "pill"]}}]}, th, "restaurant dashboard")
check("the row drawn from it: a picture, the title, its facts with icons, the pill",
      "m42-w-trow" in rp and "m42-w-facts" in rp and "#4587" in rp and "bi-clock" in rp and 'is-good">Completed' in rp)
check("the plan is told each item's fields", "meta = 2-3 short facts" in designref.grid_sections(None, [designref.clean_card(
      {"widget": "notifications", "what": "rows", "count": 4, "item": ["photo", "title", "meta", "pill"]})])[0]["what"])
# one item's parts (row template): read by the 4B, drawn row by row
check("row template: '#4587 · Wait 9 min' read as numbers and an icon is meta",
      designref.clean_item(["photo", "title", "number", "number", "icon", "pill"]) == ["photo", "title", "meta", "pill"])
ra = {"part": "notifications", "title": "Recent Activity", "items": [{"title": "Order ready", "meta": ["₹109.00", "#4587", "Wait 9 min"], "badge": "Completed"}]}
rp = pagebuild.render({"brand": {"name": "D", "icon": "bi-shop"}, "hero": {"title": "Dashboard"}, "sections": [ra], "footer": ""},
                      {"hero": "compact", "ref_layout": "sidebar", "ref_grid": {"sidebar": True, "tree": {"leaf": 0, "box": [0, 0, 1, 1]}},
                       "sections": [{"part": "notifications", "look": {"row": ["photo", "title", "meta", "pill"]}}]}, th, "restaurant dashboard")
check("the row drawn from it: a picture, the title, its facts with icons, the pill",
      "m42-w-trow" in rp and "m42-w-facts" in rp and "#4587" in rp and "bi-clock" in rp and 'is-good">Completed' in rp)
check("the plan is told each item's fields", "meta = 2-3 short facts" in designref.grid_sections(None, [designref.clean_card(
      {"widget": "notifications", "what": "rows", "count": 4, "item": ["photo", "title", "meta", "pill"]})])[0]["what"])
# the UI element model (uidetect) with the pixel finder: the soft cooking JPG's cards with no surface of their own
import uidetect  # noqa: E402
if uidetect.available():
    g82 = designref.cards(HERE / "refs" / "82.webp")
    check("cooking JPG: 8+ cards in three columns (4 before: the chart, the icon grid, the photo card, the date picker were missed)",
          g82 and len(g82["boxes"]) >= 8 and g82["tree"]["dir"] == "cols" and len(g82["tree"]["children"]) == 3, g82 and len(g82["boxes"]))
    check("... its big heading is not a card", all(b[1] > .28 for b in g82["boxes"]), g82 and [b for b in g82["boxes"] if b[1] <= .28])
# the POS shot: a grid of 8 products is one card; its tabs strip is chips; its dark menu stays dark; a cart row's - 1 +
if uidetect.available():
    g85 = designref.cards(HERE / "refs" / "85.webp")
    check("POS: the 8 products are one grid card, the dark menu's colour is kept", g85 and 8 in g85["grid_cells"].values() and g85["side_color"], g85 and (g85["grid_cells"], g85["side_color"]))
    gi = next(iter(g85["grid_cells"]))
    c = designref.clean_card({"widget": "list_thumbs", "what": "products", "count": 4, "photos": "yes", "item": ["photo", "title", "price", "text"]})
    check("... read as a photo grid of 8 (the 4B said a list of rows)", designref.shape_card(c, g85["boxes"][gi], (1536, 1024), 8)["widget"] == "image_cards")
    flat = designref.shape_card(designref.clean_card({"widget": "list_thumbs", "what": "tabs", "count": 7, "item": ["icon", "title", "arrow"]}), (0.24, 0.22, 0.65, 0.28), (1536, 1024))
    check("... its tabs strip is chips", flat["widget"] == "category_chips" and "row" not in flat["look"])
cart = {"part": "list_thumbs", "title": "Current Sale", "items": [{"title": "Cotton T-Shirt", "text": "White / M", "value": 19.99, "unit": "$", "meta": ["1"]}]}
cp = pagebuild.render({"brand": {"name": "D", "icon": "bi-shop"}, "hero": {"title": "Sales"}, "sections": [cart], "footer": ""},
                      {"hero": "compact", "ref_layout": "sidebar", "ref_grid": {"sidebar": True, "side_color": "#1b2537", "tree": {"leaf": 0, "box": [0, 0, 1, 1]}},
                       "sections": [{"part": "list_thumbs", "look": {"row": ["photo", "title", "text", "price", "stepper", "delete"]}}]}, th, "pos")
check("a cart row: - 1 + and a bin; the menu dark", "m42-w-qty" in cp and 'data-q="1"' in cp and "m42-w-del" in cp and "m42-side-dark" in cp and "#1b2537" in cp)
probs = webkit.kit_problems({"c.html": cp}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes (cart, dark menu)", not [p for ps in probs.values() for p in ps], probs)
# the POS shot: a grid of 8 products is one card; its tabs strip is chips; its dark menu stays dark; a cart row's - 1 +
if uidetect.available():
    g85 = designref.cards(HERE / "refs" / "85.webp")
    check("POS: the 8 products are one grid card, the dark menu's colour is kept", g85 and 8 in g85["grid_cells"].values() and g85["side_color"], g85 and (g85["grid_cells"], g85["side_color"]))
    gi = next(iter(g85["grid_cells"]))
    c = designref.clean_card({"widget": "list_thumbs", "what": "products", "count": 4, "photos": "yes", "item": ["photo", "title", "price", "text"]})
    check("... read as a photo grid of 8 (the 4B said a list of rows)", designref.shape_card(c, g85["boxes"][gi], (1536, 1024), 8)["widget"] == "image_cards")
    flat = designref.shape_card(designref.clean_card({"widget": "list_thumbs", "what": "tabs", "count": 7, "item": ["icon", "title", "arrow"]}), (0.24, 0.22, 0.65, 0.28), (1536, 1024))
    check("... its tabs strip is chips", flat["widget"] == "category_chips" and "row" not in flat["look"])
cart = {"part": "list_thumbs", "title": "Current Sale", "items": [{"title": "Cotton T-Shirt", "text": "White / M", "value": 19.99, "unit": "$", "meta": ["1"]}]}
cp = pagebuild.render({"brand": {"name": "D", "icon": "bi-shop"}, "hero": {"title": "Sales"}, "sections": [cart], "footer": ""},
                      {"hero": "compact", "ref_layout": "sidebar", "ref_grid": {"sidebar": True, "side_color": "#1b2537", "tree": {"leaf": 0, "box": [0, 0, 1, 1]}},
                       "sections": [{"part": "list_thumbs", "look": {"row": ["photo", "title", "text", "price", "stepper", "delete"]}}]}, th, "pos")
check("a cart row: - 1 + and a bin; the menu dark", "m42-w-qty" in cp and 'data-q="1"' in cp and "m42-w-del" in cp and "m42-side-dark" in cp and "#1b2537" in cp)
probs = webkit.kit_problems({"c.html": cp}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes (cart, dark menu)", not [p for ps in probs.values() for p in ps], probs)
# ---- prune ----
t = {"dir": "rows", "children": [{"leaf": 0, "box": (0, 0, 1, .2)}, {"dir": "cols", "children": [
    {"leaf": 1, "box": (0, .3, .5, .6)}, {"leaf": 2, "box": (.5, .3, 1, .6)}], "box": (0, .3, 1, .6)}], "box": (0, 0, 1, .6)}
check("prune: past the cards read, and a node with one child is that child", designref.prune(t, 2) == {"dir": "rows", "children": [
    {"leaf": 0, "box": (0, 0, 1, .2)}, {"leaf": 1, "box": (0, .3, .5, .6)}], "box": (0, 0, 1, .6)})

# ---- Step 2: each card's widget (fake vision), the spec's sections in grid order ----
calls = []


def fake_json(base, model, msgs, schema, **k):
    props = schema.get("properties", {})
    if "widget" in props:
        calls.append(msgs[-1]["content"][1]["image_url"]["url"][:30])
        kinds = ["kpi_tiles", "kpi_tiles", "line_chart", "agenda", "badges", "task_cards", "task_cards", "task_cards", "task_cards", "custom"]
        k = kinds[(len(calls) - 1) % len(kinds)]
        return {"widget": k, "title": f"Card {len(calls)}", "what": "a thing", "count": 3, "icons": ["calendar"]}, {}
    if "html" in props:
        return {"html": '<div class="d-flex gap-2"><script>x()</script><span style="color:var(--m42-accent)">Shift A</span>'
                        '<img src="https://x/y.png"><b onclick="z()">06:00</b></div>'}, {}
    return {}, {}


llm.complete_json = fake_json
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
ev = []
out = a.read_ref_grid(str(HERE / "refs" / "64.webp"), ev.append, "m")
check("each card read on its own (a crop, at most 10, and a card under the sidebar menu when there is one)",
      out and 3 <= len(calls) <= 11 and all(c.startswith("data:image/png") for c in calls), len(calls))
check("the spec gets one section per card, the grid, the sidebar layout",
      out and len(out["sections"]) == len(calls) and out["ref_grid"]["tree"] and out["ref_layout"] == "sidebar"
      and out["sections"][0]["part"] == "kpi_tiles" and "icons: calendar" in out["sections"][0]["what"], out and out["sections"][:2])
check("the user sees which cards were found", any("cards in the reference" in str(e.get("text")) for e in ev))

# ---- the grid as the page's layout ----
secs = [{"part": s["part"], "title": s["name"], "eyebrow": "", "lead": "", "items": [
    {"title": "Efficiency", "value": 82, "unit": "%", "icon": "bi-bullseye", "badge": "+3%"}] if s["part"] == "kpi_tiles" else
    [{"title": "Quality check", "badge": "High", "meta": ["Zone A", "Due 2 PM"], "value": 60}] if s["part"] == "task_cards" else
    [{"title": "Badge", "value": 75, "badge": "Active"}] if s["part"] == "badges" else
    [{"title": "Shift", "text": "06:00 - 14:00", "group": "Thu"}] if s["part"] == "agenda" else
    [{"title": "Trend", "values": [60, 70, 85, 80, 90]}]} for s in out["sections"]]
plan = {"brand": {"name": "ClothIQ", "icon": "bi-scissors"}, "hero": {"title": "My Performance Analytics", "accent": "", "lead": "",
        "eyebrow": "", "actions": [], "fields": [], "stats": []}, "sections": secs, "footer": "Zone A"}
spec = dict(out, hero="compact")
theme = webkit.make_theme("workforce dashboard", look={"theme": "light", "style": "minimal", "colors": ["#5b4bdb", "#10b981", "#f59e0b"]})
page = pagebuild.render(plan, spec, theme, "workforce dashboard")
check("the page has the reference's columns: main area and a right column of stacked cards",
      'class="col-12 col-lg-' in page and "m42-stack" in page and "m42-app" in page)
check("every card of the grid is on the page once", all(page.count(f'id="{pagebuild.slug(s["title"], set())}"') == 1 for s in secs[:3]))
probs = webkit.kit_problems({"index.html": page}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes in the grid page", not [p for ps in probs.values() for p in ps], probs)

# ---- Step 4: a card the library lacks, by the coder, cleaned, kept ----
plan2 = pagebuild.clean({"sections": [{"part": "custom", "title": "Shift board", "lead": "who works when", "items": [{"title": "A", "text": "x"}]}]},
                        {"hero": "compact", "sections": [{"part": "custom"}]})
loaded = []
a.load_model = lambda kind, em: loaded.append(kind) or "coder"
n = a.custom_cards(plan2["sections"], "workforce dashboard", [].append)
html = plan2["sections"][0].get("html", "")
check("the coder is loaded once and writes the card", n == 1 and loaded == ["code"], (n, loaded))
check("its HTML is cleaned: no script, image, handler", html and "<script" not in html and "<img" not in html and "onclick" not in html
      and "Shift A" in html, html)
store = learn.DIR / "widgets-learned.json"
check("the card is kept in M42's widget library (memory/widgets-learned.json)", store.exists() and "Shift board" in store.read_text(encoding="utf-8"))
page2 = pagebuild.render(dict(plan2, brand={"name": "X", "icon": "bi-x"}, hero={}, footer=""), {"hero": "compact", "ref_layout": "sidebar"}, theme, "dashboard")
check("the coder's card is on the page as written", "Shift A" in page2 and "m42-custom" in page2)
prompts = []
llm.complete_json = lambda base, model, msgs, schema, **k: (prompts.append(msgs[-1]["content"]), ({"html": "<b>ok</b>"}, {}))[1]
plan3 = pagebuild.clean({"sections": [{"part": "custom", "title": "Shift board", "lead": "who works when today", "items": []}]}, {"hero": "compact", "sections": []})
a.custom_cards(plan3["sections"], "workforce dashboard", [].append)
check("next time a card like it comes, the kept one is the coder's example", prompts and "worked before" in prompts[0], prompts[:1])
# the cooking reference: an icon rail and rows of small things (chips, step pills, an icon grid) as cards
g61 = designref.cards(HERE / "refs" / "61.webp")
check("cooking reference: an icon rail, at least 6 cards (3 before)", g61 and g61["rail"] and g61["sidebar"] and len(g61["boxes"]) >= 6,
      g61 and (g61["rail"], len(g61["boxes"])))
page_r = pagebuild.render(plan, dict(spec, ref_grid=dict(spec["ref_grid"], rail=True)), theme, "cooking app")
check("a rail reference: the menu is a rail of round icons", 'class="m42-ui m42-app is-rail"' in page_r and 'title="' in page_r)
# the calendar's highlighted days show their events' icons
cal = {"part": "calendar", "title": "Plan", "eyebrow": "", "lead": "", "labels": ["August 2026"], "taken": ["5", "9", "20"],
       "items": [{"title": "Grill", "icon": "bi-fire"}, {"title": "Bake", "icon": "bi-cake"}]}
page_c = pagebuild.render({"brand": {"name": "C", "icon": "bi-egg"}, "hero": {}, "sections": [cal], "footer": ""}, {"hero": "compact", "ref_layout": "sidebar"}, theme, "cooking")
check("calendar days with icons: 5 fire, 9 cake, 20 fire again", page_c.count('mark has-icon') == 3 and 'title="5" aria-label="5"><i class="bi bi-fire"' in page_c
      and 'aria-label="9"><i class="bi bi-cake"' in page_c, re.findall(r'mark has-icon[^>]*><i class="bi [^"]+', page_c))
probs = webkit.kit_problems({"index.html": page_r + page_c}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes (rail, calendar icons)", not [p for ps in probs.values() for p in ps], probs)
print("FAILS:", fails)
