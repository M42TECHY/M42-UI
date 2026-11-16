"""The top bar only where the page needs it (the user, 2026-10-27: "m42-topbar comes on every page, static; only on
the pages that need it"): the reference's own top strip decides, else what the page holds."""
from pathlib import Path
import os, re, sys, tempfile
os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import designref, pagebuild, webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


def page(secs, spec, request, pages=None, current="index.html"):
    plan = {"brand": {"name": "StayPulse", "icon": "bi-building"}, "hero": {"title": "Dashboard", "lead": "", "actions": [], "stats": []},
            "sections": secs, "footer": ""}
    theme = webkit.make_theme("dashboard", look={"theme": "light", "colors": ["#7b4fa0"]})
    return pagebuild.render(plan, dict({"hero": "compact", "ref_layout": "sidebar"}, **spec), theme, request, pages, current)


def bar(html):
    m = re.search(r'<header class="m42-topbar[^"]*">.*?</header>', html, re.S)
    return m.group(0) if m else ""


table = {"part": "data_table", "title": "Bookings", "eyebrow": "", "lead": "", "items": [{"title": "A", "text": "x", "badge": "Paid", "value": 5}]}
form = {"part": "form", "title": "Write to us", "eyebrow": "", "lead": "", "fields": [{"label": "Name", "type": "text"}], "button": "Send", "items": []}
pages = [("Home", "index.html"), ("Contact", "contact.html")]

home = bar(page([table], {}, "hotel admin dashboard", pages, "index.html"))
check("a dashboard's home: search, bell, the person", "m42-topsearch" in home and "bi-bell" in home and "m42-topuser" in home, home[:200])
contact = page([form], {}, "hotel admin dashboard", pages, "contact.html")
check("a contact page: no top bar on a big screen (only the phone's menu button)",
      'class="m42-topbar d-lg-none"' in contact and "m42-topsearch" not in contact and "bi-bell" not in contact)
ref = bar(page([table], {"top_bar": ["search", "messages", "notifications", "user", "language"]}, "hotel dashboard", pages, "index.html"))
check("the reference's strip: its search, messages, bell and person; no theme switch it doesn't have",
      "m42-topsearch" in ref and "bi-chat-dots" in ref and "bi-bell" in ref and "m42-topuser" in ref and "m42-theme-toggle" not in ref)
none = page([table], {"top_bar": []}, "hotel dashboard", pages, "index.html")
check("a reference with no top strip: no search, bell or person (a live page keeps its feed status)",
      "m42-topsearch" not in bar(none) and "bi-bell" not in bar(none) and "m42-topuser" not in bar(none))
check("the brief keeps the strip's things, drops unknown ones",
      designref.clean_brief({"header": ["search", "user", "rocket", "user"]})["header"] == ["search", "user"]
      and designref.clean_brief({})["header"] is None)
probs = webkit.kit_problems({"a.html": home + contact + ref}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes", not [p for ps in probs.values() for p in ps], probs)
TRAVELGO = ["title", "search", "messages", "notifications", "favorites", "user", "language"]  # its strip, left to right
full = page([table], {"top_bar": TRAVELGO}, "hotel admin dashboard", pages, "index.html")
b = bar(full)
check("the reference's strip: its title, search, chat, bell, heart, person, EN; no title row under it",
      'class="m42-toptitle"' in b and "m42-topsearch" in b and "bi-chat-dots" in b and "bi-bell" in b and "bi-heart" in b
      and "m42-topuser" in b and "m42-topchip" in b and "m42-pagehead" not in full, b[:300])
order = [b.find(x) for x in ("m42-toptitle", "m42-topsearch", "bi-chat-dots", "bi-bell", "bi-heart", "m42-topuser", "m42-topchip")]
check("... in the reference's order, left to right", order == sorted(order), order)
check("... no theme switch the reference doesn't have", "m42-theme-toggle" not in b)
sub = bar(page([table], {"top_bar": TRAVELGO}, "hotel admin dashboard", pages, "contact.html"))
check("another page: the icons and the person, not the title", "bi-heart" in sub and "m42-toptitle" not in sub)
check("no 'Connecting…' on a page with demo numbers (no device / API is fetched)", 'id="conn"' not in full)
dev = page([table], {}, "esp32 sensor dashboard live readings", pages, "index.html")
check("a device page keeps its feed status", 'id="conn"' in dev)
probs = webkit.kit_problems({"b.html": full}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes (title, chip)", not [p for ps in probs.values() for p in ps], probs)
TRAVELGO = ["title", "search", "messages", "notifications", "favorites", "user", "language"]  # its strip, left to right
full = page([table], {"top_bar": TRAVELGO}, "hotel admin dashboard", pages, "index.html")
b = bar(full)
check("the reference's strip: its title, search, chat, bell, heart, person, EN; no title row under it",
      'class="m42-toptitle"' in b and "m42-topsearch" in b and "bi-chat-dots" in b and "bi-bell" in b and "bi-heart" in b
      and "m42-topuser" in b and "m42-topchip" in b and "m42-pagehead" not in full, b[:300])
order = [b.find(x) for x in ("m42-toptitle", "m42-topsearch", "bi-chat-dots", "bi-bell", "bi-heart", "m42-topuser", "m42-topchip")]
check("... in the reference's order, left to right", order == sorted(order), order)
check("... no theme switch the reference doesn't have", "m42-theme-toggle" not in b)
sub = bar(page([table], {"top_bar": TRAVELGO}, "hotel admin dashboard", pages, "contact.html"))
check("another page: the icons and the person, not the title", "bi-heart" in sub and "m42-toptitle" not in sub)
check("no 'Connecting…' on a page with demo numbers (no device / API is fetched)", 'id="conn"' not in full)
dev = page([table], {}, "esp32 sensor dashboard live readings", pages, "index.html")
check("a device page keeps its feed status", 'id="conn"' in dev)
probs = webkit.kit_problems({"b.html": full}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("no unknown classes (title, chip)", not [p for ps in probs.values() for p in ps], probs)
Y = lambda **k: dict({x: "no" for x in designref.TOP_ICONS}, heading="", greeting="no", chips=0, **{a: "yes" for a, v in k.items() if v == 1})
bits, hd = designref.clean_top(dict(Y(search=1, notifications=1, messages=1, favorites=1, user=1, language=1), heading="Dashboard"))
check("the top strip read alone (Travelgo): its title, search, chat, bell, heart, person, EN", bits == ["title", "search", "notifications", "messages", "favorites", "user", "language"], bits)
bits, hd = designref.clean_top(dict(Y(language=1), heading="What dish do you want to learn to cook today?", greeting="yes", chips=4))
check("the cooking top: a big heading with a greeting and 4 chips; its flags are chips, not a language picker",
      hd == {"big": True, "greeting": True, "chips": 4} and "language" not in bits and "title" not in bits, (bits, hd))
bits, hd = designref.clean_top({x: "yes" for x in designref.TOP_ICONS} | {"heading": "Dashboard", "greeting": "no", "chips": 0})
check("everything 'seen' is a copied list: no icons trusted", bits == ["title"], bits)
check("a whole-page header list naming nearly everything is not trusted", designref.clean_brief({"header": list(designref.HEADER_BITS)[:9]})["header"] is None)
bplan = {"brand": {"name": "CookFine", "icon": "bi-egg-fried"}, "footer": "", "sections": [table],
         "hero": {"title": "What dish do you want to cook today?", "eyebrow": "Hello, Priya", "actions": ["Italian", "French", "Greek"], "stats": []}}
big = pagebuild.render(bplan, {"hero": "compact", "ref_layout": "sidebar", "top_bar": [], "ref_head": {"big": True, "greeting": True, "chips": 3}},
                       webkit.make_theme("dashboard", look={"theme": "light", "colors": ["#658230"]}), "cooking school dashboard", pages, "index.html")
check("the reference's big head on the page: greeting, big heading, 3 chips", 'm42-pagehead is-big' in big and "Hello, Priya" in big
      and big.count("m42-chip-btn") == 3 and "Greek" in big)
check("the plan is told to write it", "category words shown as chips" in pagebuild.plan_messages("x", {"sections": [], "ref_head": {"big": True, "chips": 4}})[1]["content"])
print("FAILS:", fails)
