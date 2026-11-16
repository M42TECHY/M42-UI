"""A site of several pages in a project folder (the user, 2026-10-26: "a folder can hold any file, use that"):
site map -> a plan per page -> M42 builds each page; the menu links the pages, the look is css/theme.css, each
page's script js/<page>.js, the kit lib/; the whole site goes to the popup, and every page runs."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import browser  # noqa: E402
import llm  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pagebuild import ADMIN, FOOD  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


SPEC = {"title": "Shop admin", "items": [{"name": "Revenue", "shows": "number", "source": "reading"}],
        "data": {}, "rules": [], "layout": "", "hero": "compact", "question": "",
        "sections": [{"name": "Key numbers", "what": "", "part": "stats"}],
        "look": {"theme": "dark", "style": "glass", "font": "modern", "colors": ["#22c55e", "#3b82f6", "#f59e0b"], "why": "admin"}}
LOGIN = {"brand": {"name": "Pulse Admin", "icon": "bi-speedometer2"},
         "hero": {"eyebrow": "", "title": "Welcome", "accent": "back", "lead": "", "actions": [], "fields": [], "stats": []},
         "sections": [{"part": "form", "eyebrow": "Sign in", "title": "Sign in", "lead": "Signed in!", "button": "Sign in", "items": [],
                       "fields": [{"label": "Email", "type": "email"}, {"label": "Password", "type": "text"}]}],
         "footer": "Pulse"}
MAP = {"pages": [{"name": "Dashboard", "purpose": "today's numbers", "hero": "compact",
                  "sections": [{"name": "Key numbers", "what": "", "part": "stats"}, {"name": "Orders", "what": "", "part": "table"}]},
                 {"name": "Products", "purpose": "the catalogue", "hero": "compact",
                  "sections": [{"name": "Products", "what": "", "part": "tabs"}]},
                 {"name": "Login", "purpose": "sign in", "hero": "none",
                  "sections": [{"name": "Sign in", "what": "", "part": "form"}]}]}


PROMPTS, BAD_LOGIN = [], None


def fake_json(base, model, messages, schema, **k):
    props = schema.get("properties", {})
    if "pages" in props:
        return MAP, {}
    user = messages[-1]["content"]
    if isinstance(user, list):  # (a look at a screenshot: its words only, for this fake)
        if "problems" in props:
            return {"problems": []}, {}
        user = " ".join(p.get("text", "") for p in user if isinstance(p, dict))
    PROMPTS.append(user)
    if BAD_LOGIN and "Login" in user.split("This page of the site:")[-1][:40]:
        return BAD_LOGIN, {}
    return (LOGIN if "Login" in user.split("This page of the site:")[-1][:40] else FOOD if "Products" in user.split(
        "This page of the site:")[-1][:40] else ADMIN), {}


llm.complete_json = fake_json
d = Path(tempfile.mkdtemp())
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], {"id": "p", "name": "p", "folders": [str(d)]})
ev = []
built = a.page_from_plan("oru admin site vennum for retail shop management, 3 pages", dict(SPEC), ev.append)
names = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "lib/" not in p.relative_to(d).as_posix())
check("three pages, the theme and each page's script as files", built is True and {"index.html", "products.html", "login.html",
      "css/theme.css", "js/index.js"} <= set(names), names)
home = (d / "index.html").read_text(encoding="utf-8")
check("the menu links every page; the look and the script are files, not inline",
      'href="products.html"' in home and 'href="login.html"' in home and 'href="css/theme.css"' in home
      and 'src="js/index.js"' in home and 'id="m42-theme"' not in home and "lib/m42-ui.js" in home)
check("the login page has no hero, the dashboard its compact one", 'class="m42-hero' not in (d / "login.html").read_text(encoding="utf-8")
      and ("m42-hero is-compact" in home or "m42-pagehead" in home))  # (an app page's head since 2026-10)
pv = [e for e in ev if e.get("type") == "page_preview"]
check("the whole site goes to the popup", pv and ((Path(__file__).resolve().parent.parent / "cache" / "previews") / pv[0]["id"] / "products.html").is_file())
if browser.find_browser():
    for f in ("index.html", "products.html", "login.html"):
        r = browser.check(d / f, clicks=True)
        check(f"{f} runs without errors", not r["errors"], r["errors"])
    (d / "still.html").write_text(home.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
    webclone.snapshot(d / "still.html", Path(__file__).parent / "uikit" / "site_admin.png", 1280, 1100)
import re  # noqa: E402
brand = lambda h: re.search(r'(?:navbar-brand|m42-side-brand)[^>]*>(.*?)</a>', h, re.S).group(1)  # an admin site: the side menu's
check("one brand on every page", brand(home) == brand((d / "products.html").read_text(encoding="utf-8")),
      (brand(home), brand((d / "products.html").read_text(encoding="utf-8"))))
login_prompt = next(u for u in PROMPTS if "This page of the site: Login" in u)
check("a page other than home gets its own sections, not the site's items", "Revenue" not in login_prompt
      and any("Revenue" in u for u in PROMPTS if "This page of the site: Login" not in u), login_prompt[:300])
# the real run (2026-10-27): the login page plan copied the home page's sales / stock sections, no sign-in form
BAD_LOGIN = {"brand": {"name": "ShopFlow", "icon": "bi-shop"}, "hero": LOGIN["hero"], "footer": "x", "sections": [
    {"part": "about", "eyebrow": "Overview", "title": "Store Performance", "lead": "",
     "items": [{"title": "Total Sales", "text": "₹12,450.00"}, {"title": "New Orders", "text": "128"}]},
    {"part": "about", "eyebrow": "Inventory", "title": "Low Stock", "lead": "",
     "items": [{"title": "Rice", "text": "Stock: 2 units"}, {"title": "Soy Milk", "text": "Stock: 3 units"}]}]}
d2 = Path(tempfile.mkdtemp())
a.load([], {"id": "p2", "name": "p2", "folders": [str(d2)]})
a.page_from_plan("oru admin site vennum for retail shop management, 3 pages", dict(SPEC), [].append)
lg = (d2 / "login.html").read_text(encoding="utf-8")
check("a login page always has its sign-in form", 'type="password"' in lg and "m42-ph" not in lg, lg[-1500:])
check("its rows of 'Stock: 2 units' are a table, or not on the sign-in page at all", "<th>Stock</th>" in lg or "Rice" not in lg)  # (the auth layout shows its form only)
print("FAILS:", fails)
