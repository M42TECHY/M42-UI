"""The widgets from the user's references (2026-11-03): landing sections of the full-page shots (team, logos, blog
cards, video band, newsletter, portfolio) and app cards (funnel, gantt, comments, integrations); and the bundled design
data (uiux.py) for a page with no reference picture. Pages render with no class / id / JS problem and a clean
phone-width check; screenshots in tests/uikit/pb_new_*.png."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import pagebuild  # noqa: E402
import uiux  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402
import widgets  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


NEW = ("team", "logos", "blog_cards", "video_band", "newsletter", "portfolio", "funnel", "gantt", "comments", "integrations")
for w in NEW:
    check(f"{w}: in the library with its notes, look and width", w in widgets.WIDGETS and w in widgets.NOTES and w in widgets.LOOKS
          and w in widgets.WIDTH and w in pagebuild.PARTS and w in webkit.PARTS)

LANDING = {"brand": {"name": "Buildora", "icon": "bi-buildings"},
           "hero": {"eyebrow": "Since 1998", "title": "Easy industry solutions", "accent": "for any business",
                    "lead": "Construction, manufacturing and maintenance by one trusted team.", "actions": ["Our services", "Get a quote"],
                    "stats": [{"value": 5000, "suffix": "+", "label": "projects done"}, {"value": 3300, "suffix": "+", "label": "happy clients"}]},
           "sections": [
               {"part": "logos", "eyebrow": "", "title": "", "lead": "",
                "items": [{"title": "Bayern"}, {"title": "Smatrico"}, {"title": "Burflex"}, {"title": "Acrevis"}, {"title": "Sauter"}]},
               {"part": "portfolio", "eyebrow": "Case study", "title": "Our recent projects", "lead": "",
                "items": [{"title": "Mixico Solid Steel", "group": "Industry", "icon": "bi-gear-wide-connected"},
                          {"title": "Avilox Luxury House", "group": "Building", "icon": "bi-house"},
                          {"title": "Oil Refinery Upgrade", "group": "Energy", "icon": "bi-fuel-pump"},
                          {"title": "City Bridge", "group": "Building", "icon": "bi-signpost-split"}]},
               {"part": "video_band", "eyebrow": "Watch", "title": "World's leading contract industrial services", "lead": "Two minutes inside our plants.",
                "button": "Our services", "items": []},
               {"part": "team", "eyebrow": "Team", "title": "Our experts team", "lead": "",
                "items": [{"title": "Amonodo Dimolat", "text": "Founder"}, {"title": "Alonso Blowson", "text": "CEO"},
                          {"title": "Miranda Halim", "text": "Designer"}, {"title": "Iqbal Hossain", "text": "Engineer"}]},
               {"part": "blog_cards", "eyebrow": "News", "title": "Company blog & insights", "lead": "",
                "items": [{"title": "Transform your community", "text": "Create a lasting impact.", "meta": ["29 Feb"], "badge": "Industry"},
                          {"title": "Don't underestimate the software", "text": "Admin UX that works.", "meta": ["28 Feb"], "badge": "Industry"},
                          {"title": "Mega dropdown patterns", "text": "Navigation done well.", "meta": ["24 Feb"], "badge": "Design"}]},
               {"part": "newsletter", "eyebrow": "", "title": "Get industry news", "lead": "One email a month.", "button": "Subscribe", "items": []}],
           "footer": "Buildora Industry"}
APP = {"brand": {"name": "Pulse CRM", "icon": "bi-activity"},
       "hero": {"eyebrow": "", "title": "Sales overview", "accent": "", "lead": "", "actions": []},
       "sections": [
           {"part": "funnel", "eyebrow": "This month", "title": "Sales funnel", "lead": "",
            "items": [{"title": "Visitors", "value": 12400}, {"title": "Leads", "value": 3100}, {"title": "Demos", "value": 860}, {"title": "Won", "value": 214}]},
           {"part": "comments", "eyebrow": "", "title": "Team comments", "lead": "",
            "items": [{"title": "Priya", "text": "Client approved the quote.", "meta": ["2h ago"]}, {"title": "Arun", "text": "Demo moved to Friday.", "meta": ["5h ago"]}]},
           {"part": "gantt", "eyebrow": "Q3", "title": "Project timeline", "lead": "", "labels": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "items": [{"title": "Research", "meta": [0, 2], "value": 100, "text": "Priya"}, {"title": "Design", "meta": [1, 2], "value": 70, "text": "Arun"},
                      {"title": "Build", "meta": [2, 3], "value": 35, "text": "Team"}, {"title": "Launch", "meta": [5, 1], "value": 0, "text": "All"}]},
           {"part": "integrations", "eyebrow": "", "title": "Integrations", "lead": "",
            "items": [{"title": "Slack", "text": "Deal alerts", "icon": "bi-slack", "badge": "on"}, {"title": "Gmail", "text": "Email sync", "icon": "bi-envelope", "badge": "off"},
                      {"title": "Stripe", "text": "Payments", "icon": "bi-credit-card", "badge": "on"}]}],
       "footer": "Pulse CRM"}

out = Path(__file__).parent / "uikit"
out.mkdir(exist_ok=True)
tmp = Path(tempfile.mkdtemp())
webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
for name, plan, spec, req, look in (
        ("landing", LANDING, {"hero": "split"}, "construction company landing page", {"theme": "light", "style": "minimal", "font": "modern",
                                                                                     "colors": ["#dc2626", "#334155", "#f59e0b"]}),
        ("app", APP, {"hero": "compact"}, "crm admin dashboard", {"theme": "light", "style": "minimal", "font": "modern",
                                                                 "colors": ["#4f46e5", "#06b6d4", "#f59e0b"]})):
    theme = webkit.make_theme(req, look=look)
    theme["look"]["hero"] = spec["hero"]
    page = pagebuild.render(plan, spec, theme, req)
    local, _ = webkit.localize(page, tmp)
    (tmp / f"{name}.html").write_text(local, encoding="utf-8")
    (tmp / f"{name}_still.html").write_text(local.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
    probs = webkit.kit_problems({"index.html": page}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
    probs = [p for ps in probs.values() for p in ps] + webkit.duplicate_ids(page) + webkit.ui_problems(req, page)
    check(f"{name}: no class / id / UI problems", not probs, probs)
    for sec in plan["sections"]:
        cls = {"team": "m42-w-team", "logos": "m42-w-logos", "blog_cards": "m42-w-posts", "video_band": "m42-w-video", "newsletter": "m42-w-news",
               "portfolio": "m42-w-works", "funnel": "m42-w-funnel", "gantt": "m42-w-gantt", "comments": "m42-w-comments", "integrations": "m42-w-integs"}[sec["part"]]
        check(f"{name}: {sec['part']} is on the page", cls in page)
    if browser.find_browser():
        r = browser.check(tmp / f"{name}.html", clicks=True)
        check(f"{name}: runs without errors", not r["errors"], r["errors"])
        ux = webkit.ux_problems(browser.check(tmp / f"{name}.html", ux=True).get("ux"), {"index.html": page})
        check(f"{name}: phone-width UX clean", not ux, ux)
        webclone.snapshot(tmp / f"{name}_still.html", out / f"pb_new_{name}.png", 1280, 4200 if name == "landing" else 1400)

# the design data with no reference picture (the chooser is the 4B in M42: faked here)
names = [r["Product Type"] for r in uiux.rows("products.csv")]
check("the bundled design data is there (192 product types)", len(names) >= 150, len(names))
cafe = names.index("Bakery/Cafe")
spec, a = uiux.apply({"look": {"colors": ["#123456"]}}, "coffee shop landing page", choose=lambda m: cafe)
check("coffee shop: the chooser's Bakery/Cafe, its palette in the look", a and a["product"] == "Bakery/Cafe" and spec["look"]["colors"][0] == a["colors"][0], spec.get("look"))
check("its section order for the page plan", spec.get("reference"), spec.get("reference"))
spec, a = uiux.apply({"look": {"colors": ["#123456"]}}, "coffee shop landing page in green colour", choose=lambda m: cafe)
check("a colour the user named wins", spec["look"]["colors"] == ["#123456"])
spec, a = uiux.apply({"look": {}}, "construction company website", choose=lambda m: 1 / 0)
check("a chooser that fails: the words (construction)", a and a["product"].startswith("Construction"), a and a["product"])
spec, a = uiux.apply({"look": {}}, "zzqx", choose=lambda m: -1)
check("none fits: the spec as it was", a is None and spec == {"look": {}})
check("the chooser's list is the same each time (llama-server caches it)", uiux.choose_messages("a")[0] == uiux.choose_messages("b")[0])
print("FAILS:", fails)
