"""Every page its own look (the user, 2026-10-26): "same design for everything; pick the palette from the prompt's
content and the web; icons sometimes don't show; don't ask every page for an ESP IP; 'admin dashboard' in a new chat
came out with temperature and humidity". The spec's look -> colours / theme / style / fonts M42 puts in itself;
examples from the page's own items; the kit tags the page forgot are added; no data-source question without a device."""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


ADMIN = "glass ui la oru admin panel design ready pannu, Dashboard design matum iruntha pothum. ana ui advance level ah irukamum"
raw = {"title": "Admin", "items": [{"name": "Total users", "shows": "number", "source": "reading"},
                                   {"name": "Revenue this month", "shows": "₹ number", "source": "reading"},
                                   {"name": "Server load", "shows": "%", "source": "reading"}],
       "data": {"where": "", "fields": []}, "rules": [], "layout": "", "question": "Where does the data come from?",
       "look": {"theme": "dark", "style": "glass", "font": "tech", "colors": ["#6366f1", "#22d3ee", "#f472b6"], "why": "SaaS admin"}}
spec = webkit.clean_spec(raw, ADMIN)
check("an admin panel (no device): no data-source question", not spec["question"] and not spec["data"], spec["question"])
check("an IoT page: no question, demo readings (2026-11-11)", not webkit.clean_spec(raw, "iot weather dashboard")["question"]
      and webkit.clean_spec(raw, "iot weather dashboard")["data"].get("where", "").startswith("demo"))
note = webkit.chat_note(ADMIN, webkit.make_theme(ADMIN, look=spec["look"]), spec)
check("the admin note: its own items as examples, no weather words, no fetch",
      "Total users" in note and not re.search(r"humid|temperat|rain", note, re.I) and "API_URL" not in note, note[-600:])
check("a device page is told to fetch with demo readings", "API_URL" in webkit.chat_note("esp32 iot dashboard", webkit.make_theme("x")))

spa = webkit.make_look("spa and wellness website", look={"theme": "light", "style": "elegant", "font": "elegant",
                                                         "colors": ["#7c9a82", "#c8a97e", "#c47a5a"], "why": "calm, natural"})
check("the spec's colours become the page's, made readable", spa["accent2"] == "#c8a97e" and spa["contrast"] >= 4.5
      and spa["style"] == "elegant" and spa["theme"] == "light", spa)
check("a colour the user names wins over the model's", webkit.make_look("green colour spa site", look={"colors": ["#ff0000", "#00ff00", "#0000ff"]})["hue"] == 150)
check("the user's own style word wins", webkit.make_look("minimal portfolio", look={"style": "bold"})["style"] == "minimal")
looks = {webkit.make_look(r)["primary"] + webkit.make_look(r)["theme"] for r in
         ["restaurant website", "cyber security dashboard", "kids school site", "spa salon", "bank portal"]}
check("different requests, different looks even without a spec", len(looks) >= 4, looks)

# the page the model forgot things in: M42 makes it whole
bare = ('<!DOCTYPE html><html lang="en"><head><link rel="stylesheet" href="' + webkit.CDN["bootstrap.min.css"] +
        '"><style>:root{--bs-primary:#2775ce}</style></head><body><header class="m42-hero"><h1>Hi <i class="bi bi-star"></i></h1>'
        '</header><div class="m42-stat" id="users" data-label="Users" data-icon="bi-people"></div>'
        '<script>Swal.fire({title:"x"}); M42UI.set("users", 5);</script></body></html>')
theme = webkit.make_theme(ADMIN, look=spec["look"])
fixed = webkit.wire_chat_page(bare, theme)
check("forgotten kit tags added: icons CSS, M42 UI CSS + JS, SweetAlert2 before the page's script",
      "bootstrap-icons.min.css" in fixed and 'href="m42-ui.css"' in fixed and 'src="m42-ui.js"' in fixed
      and fixed.index("sweetalert2") < fixed.index("Swal.fire"), fixed[:400])
check("the look is put in: theme style last in <head>, html data attributes, body class",
      fixed.index('id="m42-theme"') > fixed.index("--bs-primary:#2775ce") and 'data-m42-theme="dark"' in fixed
      and 'data-m42-style="glass"' in fixed and '<body class="m42-ui">' in fixed)
check("idempotent", webkit.wire_chat_page(fixed, theme) == fixed)
bad_icon = bare.replace("bi-people", "bi-peoplez")
probs = webkit.class_problems({"index.html": bad_icon}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
check("a misspelt data-icon is found", any("bi-peoplez" in p for ps in probs.values() for p in ps), probs)
check("m42-updated is a real M42 UI class now", ".m42-updated" in (webkit.BUNDLED / "m42-ui.css").read_text(encoding="utf-8"))

if browser.find_browser():
    here = Path(__file__).parent / "uikit"
    site = (here / "site.html").read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp())
    webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
    for name, req, look in [("look_elegant", "spa wellness website", spa),
                            ("look_bold", "cyber security startup website", {"theme": "dark", "style": "bold", "font": "tech",
                                                                         "colors": ["#22d3ee", "#6366f1", "#a3e635"]}),
                            ("look_playful", "kids school website", {"theme": "light", "style": "playful", "font": "friendly",
                                                                     "colors": ["#f97316", "#facc15", "#14b8a6"]})]:
        th = webkit.make_theme(req, look=look)
        page = webkit.wire_chat_page(site.replace('<style>:root { --bs-primary: #c15425; --bs-primary-rgb: 193, 84, 37; }</style>', ''), th)
        (tmp / f"{name}.html").write_text(page.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
        r = browser.check(tmp / f"{name}.html", clicks=True)
        check(f"{name}: no JS errors, no 'button did nothing' for the theme toggle / menu", not r["errors"]
              and not r.get("dead"), (r["errors"], r.get("dead")))
        webclone.snapshot(tmp / f"{name}.html", here / f"{name}.png", 1280, 1100)
print("FAILS:", fails)
