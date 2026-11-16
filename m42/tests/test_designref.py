"""Design from references (the user, 2026-10-27: "look at how real designs of that kind are made, then build:
dynamic, not static"): real sites found (no design galleries), their pixels and their design (vision brief) go
into the spec; the layout, hero and look come from the reference; the built page is checked against it."""
import base64
import io
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

import agent  # noqa: E402
import designref  # noqa: E402
import llm  # noqa: E402
import pagebuild  # noqa: E402
import web  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402
import importlib.util  # noqa: E402
import ast  # noqa: E402
# the sample plans FOOD and ADMIN from test_pagebuild.py, without running that test
_tree = ast.parse(Path(__file__).with_name("test_pagebuild.py").read_text(encoding="utf-8"))
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("FOOD", "ADMIN") for t in _node.targets):
        exec(compile(ast.Module([_node], []), "test_pagebuild.py", "exec"))

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


# ---- real sites only ----
res = [{"url": "https://dribbble.com/shots/123-restaurant"}, {"url": "https://en.wikipedia.org/wiki/Restaurant"},
       {"url": "https://www.zomato-blog.com/blog/top-10-restaurant-websites"}, {"url": "https://www.saravanabhavan.com/menu"},
       {"url": "https://www.saravanabhavan.com/about"}, {"url": "https://adminlte.io/themes/v3/index.html"},
       {"url": "https://demo.themesberg.com/volt/pages/dashboard.html"}, {"url": "https://www.behance.net/gallery/1"},
       {"url": "https://www.pinterest.com/pin/1"}, {"url": "https://colorlib.com/wp/free-dashboard-templates/"},
       {"url": "https://www.anjappar.com/"}]
c = designref.candidates(res, limit=4)
check("design galleries, wikis, articles and deep pages (a template list) are skipped; one home page per site; a live demo keeps its path",
      c == ["https://www.saravanabhavan.com/", "https://demo.themesberg.com/volt/pages/dashboard.html",
            "https://www.anjappar.com/"], c)


# ---- pixels ----
def shot(bg, blocks, size=(1280, 800)):
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    for box, col in blocks:
        d.rectangle(box, fill=col)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


dark = shot((14, 16, 28), [((0, 0, 260, 800), (24, 28, 48)), ((300, 40, 1240, 200), (124, 58, 237)),
                           ((300, 240, 760, 700), (34, 38, 60)), ((800, 240, 1240, 700), (34, 38, 60)),
                           ((320, 260, 700, 300), (16, 185, 129))])
_im = Image.open(io.BytesIO(base64.b64decode(dark.split(",", 1)[1])))
_d = ImageDraw.Draw(_im)
for y in range(320, 690, 14):  # rows of table text: a crowded app screen
    for x in range(310, 1230, 46):
        _d.line((x, y, x + 30, y), fill=(200, 205, 220), width=2)
_buf = io.BytesIO()
_im.save(_buf, "PNG")
dark = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode()
light = shot((250, 250, 248), [((80, 120, 600, 180), (30, 30, 30)), ((80, 220, 300, 270), (234, 88, 12))])
pd, pl = designref.profile(dark), designref.profile(light)
check("a dark app shot: dark, violet first, then green; dense", pd["theme"] == "dark" and pd["colors"][:1]
      and designref.hue_gap(pd["colors"][0], "#7c3aed") < 15 and any(designref.hue_gap(x, "#10b981") < 15 for x in pd["colors"])
      and pd["density"] == "dense", pd)
check("a white landing shot: light, orange, airy", pl["theme"] == "light" and pl["colors"]
      and designref.hue_gap(pl["colors"][0], "#ea580c") < 15 and pl["density"] == "airy", pl)
# a Dribbble-style shot: the UI card on a purple board (a real run took the board's dull purple as the brand)
board = shot((98, 73, 147), [((60, 80, 1220, 740), (255, 255, 255)), ((1100, 0, 1280, 60), (140, 118, 190)),
                             ((900, 120, 1060, 160), (89, 29, 223)), ((120, 200, 1160, 204), (220, 220, 230))])
fb = designref.profile(board)
check("a shot on a coloured board: the board is cut away, the UI's own violet is the brand, it is light",
      fb["theme"] == "light" and fb["colors"] and designref.hue_gap(fb["colors"][0], "#591ddf") < 15, fb)
check("a page with its own coloured menu bar is not cut", designref._image(light).size == designref._image(light).size)
check("a blank capture is not a reference", designref.blank(designref.profile(shot((255, 255, 255), []))))

# ---- the brief and the merge ----
brief = designref.clean_brief({"layout": "sidebar", "hero": "compact", "cards": "outlined", "corners": "pill",
                               "style": "minimal", "font": "tech", "mood": "calm data", "sections": [
                                   "4 number cards with sparklines", "orders table", ""], "match": "yes"})
check("a brief keeps known values and real blocks only", brief["sections"] == ["4 number cards with sparklines", "orders table"]
      and brief["corners"] == "pill" and brief["match"], brief)
spec = {"title": "Restaurant", "items": [], "rules": [], "hero": "split", "sections": [{"name": "Menu", "what": "", "part": "tabs"}],
        "look": {"theme": "light", "style": "elegant", "colors": ["#b45309"]}}
m = designref.merge(spec, [brief], [pd], "oru restaurant admin panel venum")
lk = m["look"]
check("the reference decides: layout, hero, theme, colours, style, font, corners, cards, density, its blocks",
      m["ref_layout"] == "sidebar" and m["hero"] == "compact" and lk["theme"] == "dark" and lk["colors"][0] == pd["colors"][0]
      and lk["style"] == "minimal" and lk["font"] == "tech" and lk["corners"] == "pill" and lk["cards"] == "outlined"
      and lk["density"] == "dense" and "orders table" in m["reference"] and m["ref_done"], m)
m2 = designref.merge(spec, [brief], [pd], "light theme la restaurant admin panel")
check("a light / dark the user named stays", m2["look"]["theme"] == "light", m2["look"])
check("the plan reads the reference's blocks", "Reference design, its blocks" in webkit.spec_text(m))

# ---- the layout comes from the reference, not from words ----
theme = webkit.make_theme("restaurant", look=lk)
page = pagebuild.render(FOOD, dict(m, hero="compact"), theme, "biryani restaurant website")
check("a restaurant with a sidebar reference becomes an app shell", "m42-app" in page and "m42-side " in page, "")
check("its look attributes are on <html>", 'data-m42-corners="pill"' in page and 'data-m42-density="dense"' in page
      and 'data-m42-cards="outlined"' in page)
page = pagebuild.render(ADMIN, {"hero": "compact", "ref_layout": "top-nav"}, webkit.make_theme("admin dashboard"), "admin dashboard")
check("an admin panel with a top-nav reference stays a top-nav page", "m42-app" not in page and "m42-nav" in page)
page = pagebuild.render(ADMIN, {"hero": "compact"}, webkit.make_theme("admin dashboard"), "admin dashboard")
check("no reference: an admin panel is an app (the words)", "m42-app" in page)

# ---- the check after the build ----
diffs = designref.check(pl, pd)
check("the check finds light vs dark, a far colour, airy vs dense", {k for k, _, _ in diffs} == {"theme", "colors", "density"}, diffs)
check("nothing to correct when they match", designref.check(pd, pd) == [])
fixed = designref.apply(m, diffs, "admin")
check("apply: the look gets the reference's values", fixed["look"]["theme"] == "dark" and fixed["look"]["density"] == "dense")

# ---- the agent: find real sites (search + capture), read them, merge ----
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": True})
a._web_enabled = lambda: True
tmp = Path(tempfile.mkdtemp())
(tmp / "a.png").write_bytes(base64.b64decode(dark.split(",", 1)[1]))
(tmp / "w.png").write_bytes(base64.b64decode(shot((255, 255, 255), []).split(",", 1)[1]))
web.web_search = lambda q, *x, **k: {"results": res}
opened = []


def fake_snap(url, out_png, **k):
    opened.append(url)
    return str(tmp / ("w.png" if "saravana" in url else "a.png"))


webclone.live_snapshot = fake_snap
llm.complete_json = lambda base, model, msgs, schema, **k: (
    ({"kind": "south indian restaurant", "app": False}, {}) if "kind" in schema["properties"] else
    ({"match": "yes", "layout": "sidebar", "hero": "compact", "cards": "glass", "corners": "rounded", "style": "glass",
      "font": "modern", "mood": "dark data", "sections": ["stat cards"]}, {}))
searched = []
web.web_search = lambda q, *x, **k: (searched.append(q), {"results": res})[1]
# the order since 2026-11-05 (the user: the library's shots are other people's designs): GitHub, else M42's own design;
# no library picture and no web search
designref.LIBRARY, designref.REF_SITES = tmp / "lib", []
from PIL import Image
(designref.LIBRARY / "restaurant").mkdir(parents=True)
Image.open(tmp / "a.png").convert("RGB").save(designref.LIBRARY / "restaurant" / "r1.jpg")
real_github = designref.github_demos
designref.github_demos = lambda *x, **k: []
ev = []
none = a.find_design_refs("oru restaurant site", {"title": "Restaurant"}, ev.append)
check("no GitHub template: no reference (M42 designs it), no web search, the library's picture not used",
      none == [] and not searched and not opened, (none, searched, opened))
check("the user is told M42 designs it itself", any("designs this page itself" in str(e.get("text")) for e in ev))
designref.github_demos = lambda kind, app, get, **k: [("https://x.github.io/resto/", "x/resto", "MIT")]
ev = []
shots = a.find_design_refs("oru restaurant site", {"title": "Restaurant"}, ev.append)
check("a GitHub template demo, captured and shown with its licence (not the library's picture)",
      [u for _, u in shots] == ["https://x.github.io/resto/"] and not searched and any("x/resto (MIT)" in str(e.get("caption")) for e in ev), shots)
a._web_enabled = lambda: False
check("the web off: nothing looked for", a.find_design_refs("oru restaurant site", {"title": "Restaurant"}, [].append) == [])
a._web_enabled = lambda: True
designref.github_demos = real_github
out = a.read_design_refs("oru restaurant site", dict(spec), [webclone.to_data_url(p) for p, _ in shots], ev.append, "m")
check("read: the spec has the reference's design, the profile is kept for the check",
      out["ref_layout"] == "sidebar" and out["look"]["theme"] == "dark" and a._design_ref and a._design_ref["theme"] == "dark")
check("the user sees what was taken", any("Design taken from the reference" in str(e.get("message")) for e in ev))
# a site M42 found that is not of this kind is not used; the user's own shot always is
import tempfile as _tf  # noqa: E402
designref.READS = Path(_tf.mkdtemp())  # (the same picture read again with another answer: not its saved reading)
llm.complete_json = lambda base, model, msgs, schema, **k: ({"match": "no", "layout": "top-nav", "hero": "centered", "cards": "flat",
                                                             "corners": "sharp", "style": "bold", "font": "tech", "mood": "x",
                                                             "sections": ["template thumbnails"]}, {})
a._ref_kind = "south indian restaurant"
ev = []
out = a.read_design_refs("oru restaurant site", dict(spec), [dark], ev.append, "m")
check("a found page that is not of this kind (a template shop) is skipped", out.get("ref_layout") is None
      and any("skipped" in str(e.get("text")) for e in ev), [e.get("text") for e in ev])
a._ref_kind = None
out = a.read_design_refs("oru restaurant site", dict(spec), [dark], [].append, "m")
check("the user's own reference shot is always used", out.get("ref_layout") == "top-nav" and out["look"]["corners"] == "sharp")
print("FAILS:", fails)
