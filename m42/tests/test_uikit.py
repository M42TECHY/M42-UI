"""M42 UI on every page (the user, 2026-10-25: "any web page or site: premium components, experience and look, never
plain; and the CSS / JS I ask to add goes in too"). The kit is wired like Bootstrap, the coder is told its parts,
a plain page or an unfed stat is sent back, the user's own code is added by M42, named libraries are checked."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


HERE = Path(__file__).parent / "uikit"
site, dash = (HERE / "site.html").read_text(encoding="utf-8"), (HERE / "dash.html").read_text(encoding="utf-8")
check("the kit has M42 UI last (it styles over Bootstrap)", webkit.KIT_FILES[-2:] == ["m42-ui.css", "m42-ui.js"])
check("a page using m42- classes loads M42 UI", {"m42-ui.css", "m42-ui.js"} <= set(webkit.used_files({"index.html": site})))
check("the coder's notes: site parts for every page, live parts only for a dashboard",
      "m42-hero" in webkit.chat_note("restaurant website", webkit.make_theme("x")) and "M42UI.set" not in
      webkit.chat_note("restaurant website", webkit.make_theme("x")) and "M42UI.set" in webkit.file_note("weather dashboard"))
check("the sample site and dashboard pass the UI check", not webkit.ui_problems("restaurant site", site)
      and not webkit.ui_problems("iot weather dashboard", dash), webkit.ui_problems("iot weather dashboard", dash))
plain = "<html><body><div class='container'><h1>Hi</h1><div class='card'>x</div></div></body></html>"
check("a plain Bootstrap page is sent back", webkit.ui_problems("portfolio website", plain))
check("a stat nobody feeds is found", any("#wind" in p for p in webkit.ui_problems(
    "dashboard", dash.replace("M42UI.set('wind', w);", ""))))
# the user's own CSS / JS
req = "portfolio website pannu, intha css add pannu:\n```css\n.hero h1 { letter-spacing: 2px; }\n```\nand <script>console.log('hi')</script>"
css, js = webkit.user_code(req)
check("the user's CSS and JS are read from the request", "letter-spacing: 2px" in css and "console.log('hi')" in js, (css, js))
out = webkit.inject_user_code(plain.replace("<body>", "<head></head><body>"), css, js)
check("M42 adds them itself, after the kit", "<style data-m42-user>" in out and "<script data-m42-user>" in out)
check("not twice", webkit.inject_user_code(out, css, js) == out)
ans = "Here:\n```html\n" + plain + "\n```\nDone"
check("in a chat answer's html block", "data-m42-user" in webkit.inject_in_answer(ans, css, js))
check("a library the user named but the page doesn't load", webkit.lib_problems("AOS animation use pannu site", plain)
      and not webkit.lib_problems("AOS use pannu", plain.replace("<body>", '<body><script src="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.js"></script>')))
# kit updates reach a folder that has an older copy M42 put there, never a file the user changed
d = Path(tempfile.mkdtemp())
webkit.sync_files(d, {"m42-ui.css"}, "")
(d / "lib" / "m42-ui.css").write_text("/* old kit */", encoding="utf-8")
import json  # noqa: E402
man = json.loads((d / webkit.MANIFEST).read_text())
man["m42-ui.css"] = webkit._sha(d / "lib" / "m42-ui.css")  # as if M42 had written that old version
(d / webkit.MANIFEST).write_text(json.dumps(man))
webkit.sync_files(d, {"m42-ui.css"}, "")
check("an older kit file M42 wrote is updated", (d / "lib" / "m42-ui.css").read_bytes() == (webkit.BUNDLED / "m42-ui.css").read_bytes())
(d / "lib" / "m42-ui.css").write_text("/* the user's own edit */", encoding="utf-8")
webkit.sync_files(d, {"m42-ui.css"}, "")
check("a kit file the user changed is left alone", "user's own edit" in (d / "lib" / "m42-ui.css").read_text())
if browser.find_browser():
    tmp = Path(tempfile.mkdtemp())
    for n in ("site.html", "dash.html"):
        shutil.copy(HERE / n, tmp / n)
    webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
    for n in ("site.html", "dash.html"):
        r = browser.check(tmp / n, clicks=True)
        check(f"{n}: no JS errors, buttons and forms fine", not r["errors"], r["errors"])
        ux = browser.check(tmp / n, ux=True).get("ux") or {}
        left = webkit.ux_problems(ux, {"index.html": (tmp / n).read_text(encoding="utf-8")})
        check(f"{n}: phone-width UX clean (contrast, overflow, labels) with M42 UI", not left, left)
print("FAILS:", fails)
