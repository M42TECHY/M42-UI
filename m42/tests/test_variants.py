"""Layout variants of site sections (pagebuild.variant, 2026-11-06): every layout of features, testimonials, pricing,
steps and the closing band renders, is on the page, runs without errors and passes the phone-width / contrast check;
a site keeps its layouts when built again, and app pages keep the first one. Screenshots: tests/uikit/variant_*.png."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import pagebuild  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402
from PIL import Image  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


def plan():
    return {"brand": {"name": "Brew & Bean", "icon": "bi-cup-hot"},
            "hero": {"eyebrow": "Since 2012", "title": "Coffee roasted", "accent": "this morning", "lead": "Small batches in Chennai.",
                     "actions": ["See the menu", "Visit us"], "photo": "images/hero.jpg"},
            "sections": [
                {"part": "cards", "eyebrow": "Why us", "title": "What makes us different", "lead": "",
                 "items": [{"title": "Single origin", "text": "Beans from three estates in Coorg.", "icon": "bi-geo-alt"},
                           {"title": "Roasted daily", "text": "Every bag is roasted the day it ships.", "icon": "bi-fire"},
                           {"title": "Free delivery", "text": "Across Chennai on orders over ₹499.", "icon": "bi-truck"}]},
                {"part": "steps", "eyebrow": "How it works", "title": "Three steps", "lead": "",
                 "items": [{"title": "Pick", "text": "Choose your roast."}, {"title": "Grind", "text": "Whole or ground."},
                           {"title": "Brew", "text": "At home in minutes."}]},
                {"part": "prices", "eyebrow": "Plans", "title": "Subscriptions", "lead": "",
                 "items": [{"title": "Taster", "text": "One bag", "value": 399, "unit": "/month", "meta": ["250 g", "Free shipping"]},
                           {"title": "Regular", "text": "Two bags", "value": 699, "unit": "/month", "meta": ["500 g", "Free shipping"]},
                           {"title": "Office", "text": "Five bags", "value": 1499, "unit": "/month", "meta": ["1.25 kg", "Priority"]}]},
                {"part": "reviews", "eyebrow": "Reviews", "title": "What people say", "lead": "",
                 "items": [{"title": "Anita R", "text": "The best filter coffee I have had outside my grandmother's kitchen.", "value": 5, "meta": ["Chennai"]},
                           {"title": "Karthik S", "text": "Delivered fresh every week.", "value": 5, "meta": ["Adyar"]},
                           {"title": "Meera V", "text": "Lovely roast, lovely people.", "value": 4, "meta": ["Velachery"]}]},
                {"part": "cta", "eyebrow": "", "title": "Your first bag is on us", "lead": "Try any roast free this week.", "button": "Claim it",
                 "items": []}],
            "footer": "Brew & Bean, Chennai"}


tmp = Path(tempfile.mkdtemp())
webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
(tmp / "images").mkdir()
Image.new("RGB", (1200, 800), (90, 60, 40)).save(tmp / "images" / "hero.jpg")
theme = webkit.make_theme("coffee shop website", look={"theme": "light", "style": "minimal", "font": "elegant",
                                                       "colors": ["#6f4e37", "#c69039", "#2f6f4e"]})
theme["look"]["hero"] = "split"
real = pagebuild.variant
MARK = {"cards": ["m42-feature", "m42-tile", "m42-splitfeat", "m42-numfeat"], "reviews": ["m42-quote", "m42-spot", "is-tint"],
        "prices": ["m42-price", "m42-prices-deep"], "steps": ["m42-steps", "m42-steprow"], "cta": ["m42-cta", "is-split"]}
out = Path(__file__).resolve().parent / "uikit"
for v in range(4):
    pagebuild.variant = lambda ctx, part, n, v=v: min(v, n - 1) if ctx.get("layout") == "site" else 0
    html = pagebuild.render(plan(), {"hero": "split"}, theme, "coffee shop website")
    for part, marks in MARK.items():
        mark = marks[min(v, len(marks) - 1)]
        check(f"layout {v}: {part} drawn as {mark}", mark in html)
    local, _ = webkit.localize(html, tmp)
    f = tmp / f"v{v}.html"
    f.write_text(local, encoding="utf-8")
    probs = webkit.kit_problems({"index.html": html}, ["bootstrap.min.css", "bootstrap-icons.min.css", "lucide.css", "m42-ui.css"])
    probs = [p for ps in probs.values() for p in ps] + webkit.duplicate_ids(html)
    check(f"layout {v}: no unknown class / duplicate id", not probs, probs)
    if browser.find_browser():
        r = browser.check(f, clicks=True)
        check(f"layout {v}: runs without errors", not r["errors"], r["errors"])
        ux = webkit.ux_problems(browser.check(f, ux=True).get("ux"), {"index.html": html})
        check(f"layout {v}: phone-width / contrast clean", not ux, ux)
        still = tmp / f"v{v}_still.html"
        still.write_text(local.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
        webclone.snapshot(still, out / f"variant_{v}.png", 1280, 3600)
pagebuild.variant = real
a = pagebuild.render(plan(), {"hero": "split"}, theme, "coffee shop website")
b = pagebuild.render(plan(), {"hero": "split"}, theme, "coffee shop website")
check("the same site keeps its layouts when built again", a == b)
other = plan()
other["brand"]["name"] = "Filter House"
kinds = {pagebuild.variant({"layout": "site", "site_key": name, "sec_n": 0}, "cards", 4) for name in
         ("Brew & Bean", "Filter House", "Bean There", "Roast Room", "Kaapi Co", "Daily Grind", "Mocha Hub", "Cup Story")}
check("different sites get different layouts", len(kinds) >= 3, kinds)
check("app pages keep the first layout", pagebuild.variant({"layout": "app", "site_key": "x"}, "cards", 4) == 0)
print("FAILS:", fails)
