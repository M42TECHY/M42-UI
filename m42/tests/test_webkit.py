"""The default web kit (the user's idea, 2026-10-25): websites get Bootstrap 5.3 + Icons, jQuery, SweetAlert2,
Toastr and anime.js from M42's bundled/ folder, a computed theme, only the files the code uses, and checks from the
libraries' own files (classes, APIs) plus a phone-width render (overflow, contrast, alt, labels, h1)."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import browser  # noqa: E402
import llm  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


# which requests get the kit
for req, want in [("restaurant website pannu", True), ("portfolio site with contact form", True), ("todo app", True),
                  ("snake game pannu", False), ("portfolio using tailwind", False), ("react dashboard", False),
                  ("website without bootstrap", False), ("bootstrap venam simple page", False),
                  ("three.js solar system", False)]:
    check(f"kit for '{req}': {want}", webkit.wants_kit(req) == want)
check("planner's own bootstrap/jquery entries dropped, a user library kept",
      webkit.drop_kit_libraries(["bootstrap.min.css", "jquery-3.7.1.min.js", "sweetalert2.all.min.js", "chart.umd.js"])
      == ["chart.umd.js"])

# theme: computed contrast for every hue
worst = min(webkit.palette(h)["contrast"] for h in range(0, 360, 5))
check("theme: text on the primary colour >= 4.5:1 for every hue", worst >= 4.5, worst)
t = webkit.make_theme("biryani restaurant website")
check("restaurant -> warm colour, reason given", 10 <= t["hue"] <= 30 and ("restaurant" in t["why"] or "biryani" in t["why"]), t)
check("a colour the user names wins", webkit.make_theme("green colour la portfolio")["hue"] == 150)
check("theme overrides Bootstrap's compiled button colours", "--bs-btn-bg" in t["css"] and t["primary"] in t["css"])

# checks from the libraries' own files
html = ('<nav class="navbar navbar-expand-lg"><a class="navbar-brand ml-3">X</a></nav><i class="bi bi-facebok"></i>'
        '<div class="hero-section card-glow reveal"></div><button data-toggle="collapse">x</button>')
js = "document.querySelectorAll('.reveal'); Swal.fire({type: 'success'}); toastr.show('x'); swal('a'); anime({targets: '.x'});"
probs = webkit.kit_problems({"index.html": html, "js/main.js": js}, ["bootstrap.min.css", "bootstrap-icons.min.css"])
flat = " ".join(p for ps in probs.values() for p in ps)
check("Bootstrap 4 class -> its Bootstrap 5 name", "ml-3 (Bootstrap 5: ms-3)" in flat)
check("a misspelt icon -> the real one", "bi-facebook" in flat)
check("an invented framework-style class is found; a plain custom name and a JS hook are not",
      "card-glow" in flat and "hero-section" not in flat and "reveal" not in flat)
check("data-toggle, swal(), type:, toastr.show found", all(w in flat for w in ("data-bs-toggle", "swal(...)", "icon:",
                                                                           "toastr.show")))
check("real API names pass (Swal.fire, anime(), toastr.success, bootstrap.Modal)",
      not webkit.api_problems({"a.js": "Swal.fire({icon:'info'}); toastr.success('x'); new bootstrap.Modal(m); "
                                       "anime.stagger(50); anime.timeline();"}))
check("only the files the code uses; Toastr brings jQuery", webkit.used_files({"a.js": "toastr.success('x')"}) ==
      ["bootstrap.min.css", "toastr.min.css", "jquery.min.js", "toastr.min.js"])

# phone-width render
if browser.find_browser():
    d = Path(tempfile.mkdtemp())
    (d / "lib").mkdir()
    (d / "lib" / "bootstrap.min.css").write_bytes((webkit.BUNDLED / "bootstrap.min.css").read_bytes())
    (d / "index.html").write_text('<!DOCTYPE html><html><head><link rel="stylesheet" href="lib/bootstrap.min.css">'
                                  '</head><body><h1>A</h1><h1>B</h1><p style="color:#ccc">faint</p>'
                                  '<div id="wide" style="width:800px">w</div><img src="a.png"><input id="q"></body></html>')
    ux = browser.check(d / "index.html", ux=True).get("ux") or {}
    check("390 px render: overflow, contrast, alt, label, h1 measured",
          ux.get("scroll", 0) >= 300 and ux.get("contrast") and ux.get("noalt") and ux.get("nolabel") and ux.get("h1") == 2,
          ux)
    ok_page = ('<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">'
               '<link rel="stylesheet" href="lib/bootstrap.min.css"></head><body><div class="container"><h1>Hi</h1>'
               '<label for="e">Email</label><input id="e" class="form-control"><img src="a.png" alt="x" class="img-fluid">'
               '<button class="btn btn-primary">Go</button></div></body></html>')
    (d / "index.html").write_text(ok_page)
    left = webkit.ux_problems(browser.check(d / "index.html", ux=True).get("ux"), {"index.html": ok_page})
    check("a clean Bootstrap page: no UX problems", not left, left)

# (M42 UI has no step-by-step Build mode: its build test is left out)
print("FAILS:", fails)
