"""The Jiron time-tracker reference (2026-10-30, the user's real run in a project folder): the site's pages are the
reference's menu (not the site-map prompt's example), the week calendar is one card, week planner + project cards
widgets, dark text on pale colours."""
import sys, warnings, re
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llamacpp  # noqa: F401
import designref, pagebuild, webkit, widgets

HERE = Path(__file__).resolve().parent
fails = 0
def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300]); fails += not ok

g = designref.cards(HERE / "refs" / "jiron.webp")
check("jiron: 3 cards (team tiles, the board, the week calendar whole)", len(g["boxes"]) == 3 and g["boxes"][2][3] - g["boxes"][2][1] > .35,
      [[round(v, 2) for v in b] for b in g["boxes"]])
spec = {"side_menu": [{"label": x, "group": "", "active": x == "Time Tracker"} for x in ("Time Tracker", "Projects", "Reports", "Tags", "Team", "Clients", "Log out")],
        "title": "Time Tracker", "items": [], "sections": []}
check("the pages are the reference's menu (5, no Log out)", pagebuild.menu_pages(spec) == ["Time Tracker", "Projects", "Reports", "Tags", "Team"])
msg = pagebuild.sitemap_messages("time tracker", spec)[1]["content"]
check("the site map is told those pages", "EXACTLY these" in msg and "Time Tracker, Projects" in msg)
check("no page names in the site-map prompt to copy", "Products, Orders, Customers" not in pagebuild.SITEMAP_PROMPT)
pages = [("Time Tracker", "index.html"), ("Projects", "projects.html")]
nav = pagebuild.side_menu_html(spec["side_menu"], [], pages, "projects.html")
check("site menu: pages link to their files, this page active, the rest open-here",
      'href="index.html"' in nav and 'active" href="projects.html"' in nav and 'data-m42-toast="Clients opens here"' in nav and nav.count(" active") == 1, nav[:300])
ws = widgets.w_week_schedule({"title": "T", "labels": ["Monday 09.08", "Tuesday 10.08", "Wednesday 11.08"],
                              "items": [{"title": "A", "text": "08:30 - 09:30", "group": "Monday"}, {"title": "B", "text": "09:30 - 11:00", "group": "Wednesday"}]},
                             {"ids": set()})
check("week planner: each event on its day, at its time, for its length", "grid-column:2;grid-row:2 / span 2" in ws and "grid-column:4;grid-row:4 / span 3" in ws, ws[-600:])
check("week planner: Month / Day / Week tabs, Week on", ws.count("m42-ws-tab ") + ws.count('m42-ws-tab"') == 3 and 'is-on"' in ws)
pc = widgets.w_project_cards({"items": [{"title": "UI Designers", "text": "x", "meta": ["Asha Rao"], "badge": "2", "value": 70}]}, {"ids": set()})
check("project cards: faces, count, title, progress bar", "m42-pc-av" in pc and "<em>2</em>" in pc and 'aria-valuenow="70"' in pc)
check("dark text on a pale colour, white on a strong one", webkit.on_colour("#afccfc") != "#ffffff" and webkit.on_colour("#5b21b6") == "#ffffff")
check("the 4B can name both new widgets", "week_schedule" in widgets.LOOKS and "project_cards" in widgets.LOOKS)
print("FAILS:", fails)
