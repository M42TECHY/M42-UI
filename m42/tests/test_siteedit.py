"""A correction after a site is built goes to the right page and section (the user, 2026-10-27: "after a web design,
any correction I say: go to that file and edit it correctly"): the site's plans kept in .m42/site.json; the chat
model places the change; the plan changes; only that page is made again; a change no plan can say is a line edit
on that one file, kept through later re-renders."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402
import browser  # noqa: E402
import llm  # noqa: E402
import sitedit  # noqa: E402
import test_site as ts  # noqa: E402  (builds its own sites first, with its fakes)

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


llm.complete_json = ts.fake_json
d = Path(tempfile.mkdtemp())
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], {"id": "e", "name": "e", "folders": [str(d)]})
a.page_from_plan("oru admin site vennum for retail shop management, 3 pages", dict(ts.SPEC), [].append)
site = sitedit.load(d)
check("the build keeps the site's plans in .m42/site.json", site and [p["file"] for p in site["pages"]] == ["index.html", "products.html", "login.html"]
      and site["pages"][0]["plan"]["sections"], site and [p["file"] for p in site["pages"]])
check("a correction in this folder goes to the site edit; a new site does not",
      a.wants_site_edit("orders table la status column colour maathu") and not a.wants_site_edit("oru puthu website create pannu"))
print(sitedit.outline(site))

LOC, SEC, CALLS = {}, {}, []


def fake(base, model, messages, schema, **k):
    CALLS.append(schema)
    if "changes" in schema.get("properties", {}):
        return LOC, {}
    return SEC, {}


llm.complete_json = fake


def run(msg):
    files = {f: (d / f).read_text(encoding="utf-8") for f in ("index.html", "products.html", "login.html")}
    ev = []
    a.edit_site(msg, ev.append)
    after = {f: (d / f).read_text(encoding="utf-8") for f in files}
    return files, after, ev


# 1. a section's content: only that page changes
home_secs = sitedit.load(d)["pages"][0]["plan"]["sections"]
k = next(i for i, s in enumerate(home_secs) if s["part"] in ("table", "data_table"))
LOC = {"changes": [{"page": "index.html", "action": "edit_section", "section": k, "part": "", "position": -1, "colors": [], "theme": "",
                    "name": "", "what": "rename the orders"}]}
SEC = dict(home_secs[k], title="Today's Orders", part=home_secs[k]["part"])
before, after, ev = run("orders table title ah Today's Orders nu maathu")
check("edit a section: the home page has the new title", "Today&#x27;s Orders" in after["index.html"] or "Today's Orders" in after["index.html"],
      after["index.html"][:200])
check("... and the other pages are untouched", before["products.html"] == after["products.html"] and before["login.html"] == after["login.html"])
check("... the diff is shown for that file", any(e.get("type") == "tool_result" and e.get("path") == "index.html" and e.get("diff") for e in ev))
check("... the plan in site.json has it (a later change starts from it)", sitedit.load(d)["pages"][0]["plan"]["sections"][k]["title"] == "Today's Orders")

# 2. remove a section
n = len(sitedit.load(d)["pages"][0]["plan"]["sections"])
LOC = {"changes": [{"page": "index.html", "action": "remove_section", "section": k, "part": "", "position": -1, "colors": [], "theme": "",
                    "name": "", "what": "remove orders"}]}
before, after, ev = run("orders table remove pannu")
check("remove a section: gone from the page and the plan", "Today's Orders" not in after["index.html"]
      and len(sitedit.load(d)["pages"][0]["plan"]["sections"]) == n - 1)

# 3. the colours: every page, the theme file
old_css = (d / "css/theme.css").read_text(encoding="utf-8")
LOC = {"changes": [{"page": "index.html", "action": "look", "section": -1, "part": "", "position": -1, "colors": ["#7c3aed"], "theme": "",
                    "name": "", "what": "purple"}]}
before, after, ev = run("colour purple ah maathu")
check("the look: css/theme.css has the new colour", "#7c3aed" in (d / "css/theme.css").read_text(encoding="utf-8").lower()
      and (d / "css/theme.css").read_text(encoding="utf-8") != old_css)
check("... and site.json keeps it", sitedit.load(d)["look"]["colors"][0] == "#7c3aed")

# 4. a widget changed on the products page
psecs = sitedit.load(d)["pages"][1]["plan"]["sections"]
LOC = {"changes": [{"page": "products.html", "action": "change_widget", "section": 0, "part": "image_cards", "position": -1, "colors": [],
                    "theme": "", "name": "", "what": "as picture cards"}]}
SEC = dict(psecs[0], part="image_cards")
before, after, ev = run("products ah picture cards ah kaatu")
check("change a widget: the products page shows it, the home page untouched", "m42-w-" in after["products.html"]
      and before["index.html"] == after["index.html"] and sitedit.load(d)["pages"][1]["plan"]["sections"][0]["part"] == "image_cards")
check("... the page spec follows (render() keeps the new widget)", sitedit.load(d)["pages"][1]["spec"]["sections"][0]["part"] == "image_cards")

# 5. a change no plan says: a line edit on that file, kept when the page is made again
a.load_model = lambda kind, em: "coder"
home = (d / "index.html").read_text(encoding="utf-8")
line = next(l for l in home.splitlines() if "m42-app-foot" in l)


def fake_stream(base, model, msgs, **k):
    yield "text", "x"
    yield "done", {"content": f"<<<<<<< SEARCH\n{line}\n=======\n{line.replace('m42-app-foot', 'm42-app-foot fw-bold')}\n>>>>>>> REPLACE\n"}


llm.stream_chat = fake_stream
LOC = {"changes": [{"page": "index.html", "action": "other", "section": -1, "part": "", "position": -1, "colors": [], "theme": "",
                    "name": "", "what": "bold footer"}]}
before, after, ev = run("footer bold ah podu")
check("other: a line edit on that one file", "m42-app-foot fw-bold" in after["index.html"] and before["products.html"] == after["products.html"],
      [e for e in ev if e.get("type") in ("check", "assistant_text")])
check("... kept with the page in site.json", sitedit.load(d)["pages"][0]["hand_edits"])
LOC = {"changes": [{"page": "index.html", "action": "brand", "section": -1, "part": "", "position": -1, "colors": [], "theme": "",
                    "name": "ShopPulse", "what": "rename"}]}
before, after, ev = run("site name ShopPulse nu maathu")
check("the brand on every page, and the earlier line edit is still on the home page", all("ShopPulse" in after[f] for f in after)
      and "m42-app-foot fw-bold" in after["index.html"])
if browser.find_browser():
    r = browser.check(d / "index.html", clicks=True)
    check("the edited home page runs without errors", not r["errors"], r["errors"])

# 6. a reference grid page: a removed card leaves the grid in step
t = {"dir": "cols", "children": [{"leaf": 0, "box": [0, 0, .5, 1]}, {"dir": "rows", "children": [{"leaf": 1, "box": [.5, 0, 1, .5]},
                                                                                                    {"leaf": 2, "box": [.5, .5, 1, 1]}], "box": [.5, 0, 1, 1]}], "box": [0, 0, 1, 1]}
check("a grid without card 1: card 2 moves up, a column of one is that card",
      sitedit.drop_leaf(t, 1) == {"dir": "cols", "children": [{"leaf": 0, "box": [0, 0, .5, 1]}, {"leaf": 1, "box": [.5, .5, 1, 1]}], "box": [0, 0, 1, 1]})
# 6. an animation for one section (2026-11-11: "intha section ku anime.js animation kondu va" went to the general agent,
# which linked anime.js 4 from a CDN): the motion edit, no coder, the kit's anime.js from lib/, and "intha section" next time
llm.complete_json = fake
secs6 = sitedit.load(d)["pages"][0]["plan"]["sections"]
# (the model's own answer: "motion" for an animation ask; no word rule turns its answer into another, 2026-11-12)
LOC = {"changes": [{"page": "index.html", "action": "motion", "section": 0, "part": "", "position": -1, "colors": [], "theme": "",
                    "name": "", "what": "animation"}]}
SEC = {"level": "subtle", "hero": "none", "reveal": "stagger", "hover": "lift", "counters": True, "notify": "toast",
       "confirm": True, "progress": False, "to_top": False, "doodle": "none"}
a.load_model = lambda kind, em: (_ for _ in ()).throw(AssertionError("the coder was loaded"))
before, after, ev = run("intha section ku anime.js use panni animation kondu va")
check("an animation ask is a motion edit: the section has its own reveal", 'data-m42-sec-reveal="stagger"' in after["index.html"],
      [e.get("text") or e.get("message") for e in ev if e.get("type") in ("assistant_text", "check")])
check("... anime.js from lib/, no CDN link added", "anime.min.js" in after["index.html"] and "animejs@" not in after["index.html"])
check("... and site.json remembers that section for 'intha section'", sitedit.load(d).get("last") == {"page": "index.html", "section": 0}
      and "section 0" in sitedit.last_note(sitedit.load(d)))
print("FAILS:", fails)
