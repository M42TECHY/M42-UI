"""🎨 Themes (themes.py): whole designs the 4B picks; each draws a page differently, a site's theme can be changed
later ("vera theme") with its content kept. (No model needed.)"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pagebuild  # noqa: E402
import sitedit  # noqa: E402
import themes  # noqa: E402
import webkit  # noqa: E402

FAILS = 0


def check(name, ok, info=""):
    global FAILS
    print(("ok   " if ok else "FAIL ") + name, info if not ok else "")
    FAILS += 0 if ok else 1


check("30 themes", len(themes.THEMES) == 30, len(themes.THEMES))
check("... each a whole design (base, look, hero, head, rhythm, pic, divider)", all(
    t["base"] in webkit.ARCHETYPES and set(t["look"]) >= {"theme", "style", "font", "corners", "density", "cards"}
    and all(k in t for k in ("hero", "head", "rhythm", "pic", "divider", "desc", "fits")) for t in themes.THEMES.values()))
sigs = {(t["base"], t["head"], t["rhythm"], t["pic"], t["divider"], t["look"]["theme"]) for t in themes.THEMES.values()}
check("... no two alike", len(sigs) == len(themes.THEMES))

look = {"colors": ["#2c3e50", "#d4af37", "#49df94"], "style": "glass", "theme": "light", "archetype": "warm"}
noir = webkit.make_theme("a school landing page", look=dict(look, design="noir"))["look"]
check("a theme sets the look (noir: dark, elegant, editorial)", (noir["theme"], noir["style"], noir["archetype"]) == ("dark", "elegant", "editorial"), noir)
check("... the 4B's colours stay", noir["primary"].lower() != "" and "design" in noir and noir["head"] == "center")
plain = webkit.make_theme("a school landing page", look=look)["look"]
check("no theme: the look as before", "design" not in plain and plain["style"] == "glass")

plan = {"brand": {"name": "Green Valley School"}, "hero": {"title": "Learn", "accent": "and grow", "lead": "A school", "actions": ["Apply"]},
        "sections": [{"part": "cards", "title": "Programs", "eyebrow": "What we teach", "lead": "Every age",
                      "items": [{"title": f"Item {i}", "text": "words", "photo": f"images/item-{i}.jpg"} for i in range(6)]},
                     {"part": "steps", "title": "Admission", "items": [{"title": "Visit"}, {"title": "Apply"}, {"title": "Join"}]},
                     {"part": "faq", "title": "Questions", "items": [{"title": "Fees?", "text": "Low"}]}]}
spec = {"hero": "split", "sections": [{"name": "Programs", "what": "", "part": "cards"}], "look": look}
pages = {}
for n in themes.NAMES:
    th = webkit.make_theme("a school landing page", look=dict(look, design=n))
    th["look"]["hero"] = "split"
    pages[n] = pagebuild.render(copy.deepcopy(plan), spec, th, "a school landing page")
check("every theme renders, its name and axes on <html>", all(f'data-m42-design="{n}"' in h and f'data-m42-head="{themes.THEMES[n]["head"]}"' in h
                                                           for n, h in pages.items()))
check("... the section head follows the theme (pill / split / sticky / numbered)",
      "is-pill" in pages["campus"] and "is-split" in pages["bento"] and "is-sticky" in pages["split"] and "m42-ed-num" in pages["atelier"])
check("... noir is not numbered (its own head over its editorial base)", "m42-ed-num" not in pages["noir"].split("<section", 1)[1])
check("... the hero follows the theme (campus: bleed, magazine: giant, corporate: block, showcase: product, signature ones)",
      "is-bleed" in pages["campus"] and "is-giant" in pages["magazine"] and "is-block" in pages["corporate"] and "is-product" in pages["showcase"]
      and "is-poster" in pages["playground"] and "is-duo" in pages["sport"] and "is-showroom" in pages["organic"] and "is-diagonal" in pages["retro"])
check("... sections take the theme's layouts in turn (campus: zigzag, swiss: watermark, heritage: stage)",
      "m42-lx-zigzag" in pages["campus"] and "m42-lx-wm" in pages["swiss"] and "m42-lx-stage" in pages["heritage"])
check("... no new hero gets the spec's own is-image on top", not any("is-giant is-image" in h or "is-block is-image" in h or "is-bleed is-image" in h
                                                                     for h in pages.values()))
bodies = {n: h.split("<body", 1)[1] for n, h in pages.items()}
check("... all different pages", len(set(pages.values())) == len(themes.THEMES))
probs = {n: webkit.class_problems({"index.html": h}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"]) for n, h in pages.items()}
check("... every class they use is in M42's CSS", not any(probs.values()), {n: p for n, p in probs.items() if p})

site = sitedit.new_site("a school", dict(look, design="campus", design_options=["corporate", "atelier"]), None,
                        [(plan, spec, "index.html")], single=True)
done, note = sitedit.apply(site, {"page": "index.html", "action": "design", "design": "", "section": -1})
check("'another theme': the next one the 4B said fits", site["look"]["design"] == "corporate" and done == ["index.html"], (site["look"], note))
sitedit.apply(site, {"page": "index.html", "action": "design", "design": "noir", "section": -1})
check("... a named theme", site["look"]["design"] == "noir" and site["pages"][0]["spec"]["look"]["design"] == "noir")
check("... the old ones kept to go back to", "corporate" in site["look"]["design_options"] and "campus" in site["look"]["design_options"])
check("the locate step knows the design action", "design" in sitedit.ACTIONS and "design" in sitedit.locate_schema(site, pagebuild.PARTS)["properties"]["changes"]["items"]["properties"])
check("... and the theme names", "THEMES_LIST" not in sitedit.locate_messages(site, "vera theme")[0]["content"] and "magazine" in sitedit.locate_messages(site, "vera theme")[0]["content"])
same = pagebuild.clean({"hero": {"title": "Forge your strength", "accent": "FORGE YOUR  strength"}, "sections": []}, {})
check("a heading's accent that repeats its title is dropped", same["hero"]["accent"] == "")

# ---- app themes (admin / POS / CRM / dashboard / management)
check("20 app themes, none named like a landing theme", len(themes.APP_THEMES) == 20 and not set(themes.APP_THEMES) & set(themes.THEMES))
check("... each with its own palettes and all its axes", all(t.get("palettes") and all(k in t for k in themes.APP_AXES) for t in themes.APP_THEMES.values()))
asigs = {tuple(t[k] for k in themes.APP_AXES) + (t["look"]["theme"],) for t in themes.APP_THEMES.values()}
check("... no two alike", len(asigs) == 20, len(asigs))
aplan = {"brand": {"name": "ShopFlow"}, "hero": {"title": "Good morning", "lead": "Your store today", "actions": ["New sale"]},
         "sections": [{"part": "kpi_tiles", "title": "Today", "items": [{"title": "Sales", "value": 12450, "unit": "₹"}, {"title": "Orders", "value": 42}]},
                      {"part": "data_table", "title": "Orders", "labels": ["Order", "Amount"], "items": [{"title": "#1", "meta": ["₹200"]}]},
                      {"part": "line_chart", "title": "Sales", "items": [{"title": d, "value": v} for d, v in (("Mon", 3), ("Tue", 5), ("Wed", 4), ("Thu", 7))]}]}
aspec = {"hero": "compact", "sections": [], "look": look}
apages = {}
for n in themes.APP_NAMES:
    th = webkit.make_theme("pos billing admin panel for a supermarket", look=dict(look, design=n))
    th["look"]["hero"] = "compact"
    apages[n] = pagebuild.render(copy.deepcopy(aplan), aspec, th, "pos billing admin panel for a supermarket")
check("every app theme renders as an app screen, its axes on <html>", all("m42-app" in h and f'data-m42-design="{n}"' in h and
      f'data-m42-side="{themes.APP_THEMES[n]["side"]}"' in h for n, h in apages.items()))
check("... a greeting band where the theme has one, tabs on a phone where it has them",
      "m42-hello-band" in apages["citrus"] and "m42-hello-band" not in apages["slate"] and "m42-tabbar" in apages["register"] and "m42-tabbar" not in apages["ledger"])
check("... the top-menu themes put the menu in the top bar", "m42-topnav" in apages["ledger"] and "m42-topnav" not in apages["midnight"])
check("... its own colours (two shops can differ), the landing look untouched",
      webkit.make_theme("x", look=dict(look, design="citrus"))["primary"].lower() != webkit.make_theme("x", look=dict(look, design="nova"))["primary"].lower())
aprobs = {n: webkit.class_problems({"index.html": h}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"]) for n, h in apages.items()}
check("... every class they use is in M42's CSS", not any(aprobs.values()), {n: p for n, p in aprobs.items() if p})
asite = sitedit.new_site("pos", dict(look, design="register", design_options=["citrus", "slate"]), None, [(aplan, aspec, "index.html")], single=True)
sitedit.apply(asite, {"page": "index.html", "action": "design", "design": "", "section": -1})
check("'another theme' on an app keeps an app theme", asite["look"]["design"] == "citrus", asite["look"])
dup = pagebuild.clean({"hero": {"title": "POS"}, "sections": [
    {"part": "image_cards", "title": "Products", "items": [{"title": "Fresh Milk", "text": "1L"}, {"title": "Fresh Milk", "text": "1L"}, {"title": "Rice"}, {"title": "Eggs"}]},
    {"part": "image_cards", "title": "Best sellers", "items": [{"title": "Fresh Milk", "text": "1L"}, {"title": "Rice"}, {"title": "Eggs"}]},
    {"part": "data_table", "title": "Orders", "items": [{"title": "#1"}, {"title": "#2"}, {"title": "#3"}]}]}, {})
check("the same item never twice in a section, the same list never twice on a page",
      [len(x["items"]) for x in dup["sections"]] == [3, 3] and [x["title"] for x in dup["sections"]] == ["Products", "Orders"], [(x["title"], len(x["items"])) for x in dup["sections"]])
nophoto = dict(plan, sections=[dict(plan["sections"][0], items=[{"title": f"Item {i}", "text": "words"} for i in range(6)])])
th = webkit.make_theme("a school landing page", look=dict(look, design="aurora"))
th["look"]["hero"] = "split"
check("a layout made of photos is not used for a section without them (no orbit round an empty circle)",
      "m42-lx-orbit" not in pagebuild.render(copy.deepcopy(nophoto), spec, th, "a school landing page"))
figs = dict(plan, sections=[{"part": "cards", "title": "Why us", "items": [
    {"title": "15+ Years", "text": "Of weddings", "value": 15, "unit": "Years", "photo": "images/a.jpg"},
    {"title": "500+", "text": "Weddings planned", "value": 500, "unit": "Weddings", "photo": "images/b.jpg"},
    {"title": "₹25L+", "text": "Decor managed", "value": 2500000, "unit": "INR"}]}])
th = webkit.make_theme("a school landing page", look=dict(look, design="heritage"))
th["look"]["hero"] = "split"
fh = pagebuild.render(copy.deepcopy(figs), spec, th, "a school landing page")
check("things that are figures are drawn as numbers, not on a stage", "m42-lx-nums" in fh and "m42-lx-stage" not in fh)
print("FAILS:", FAILS)
