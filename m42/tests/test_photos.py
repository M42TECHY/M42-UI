"""Real photos in the pages (photos.py, 2026-11-05): the hero and the cards get images/*.jpg, a section's cards all
with photos or none, no stock faces for a team, credits written, the hero photo inline (a url() in a CSS variable was
read from lib/). The photo libraries are faked here (no network)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pagebuild  # noqa: E402
import photos  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


def plan():
    return {"brand": {"name": "Crumb", "icon": "bi-shop"}, "hero": {"title": "Warm crusts", "accent": "baked fresh", "lead": "x",
                                                                "actions": ["Order"]},
            "sections": [{"part": "image_cards", "title": "Breads", "items": [{"title": "Sourdough", "value": 120}, {"title": "Baguette", "value": 90}]},
                         {"part": "image_cards", "title": "Cakes", "items": [{"title": "Cheesecake", "value": 200}, {"title": "Mystery cake", "value": 150}]},
                         {"part": "team", "title": "Our bakers", "items": [{"title": "Asha", "text": "Head baker"}]}],
            "footer": "Crumb"}


photos.search = lambda q, keys, wide=True: [] if "Mystery" in q else [{"url": "x-" + q, "by": "Ann", "page": "p", "source": "Pexels",
                                                                     "licence": "Pexels licence", "alt": q}]
photos.save = lambda cand, folder, name, width: f"{name}.jpg"
root = Path(tempfile.mkdtemp())
p = plan()
credits = photos.add_to_plan(p, "bakery landing page pannu", root, {"pexels_key": "k"})
check("the hero gets a photo of the subject", p["hero"].get("photo") == "images/bakery.jpg", p["hero"])
check("a section whose cards all have one: photos", all(i.get("photo") for i in p["sections"][0]["items"]), p["sections"][0])
check("a section with one card missing: that card gets another photo of the subject (not every card's dropped)",
      all(i.get("photo") for i in p["sections"][1]["items"]), p["sections"][1])
check("no stock faces for the team", not any(i.get("photo") for i in p["sections"][2]["items"]))
photos.write_credits(root, credits)
check("credits written", "Pexels licence" in (root / "images" / "CREDITS.txt").read_text(encoding="utf-8"))
check("the footer note names the source", photos.footer_note(credits).startswith("Photos: Pexels"))
check("the search words: the item and the subject", ("Sourdough bakery" in [q for _, q, _, _ in photos.wanted(plan(), "bakery landing page")]))
theme = webkit.make_theme("bakery landing page", look={"theme": "light", "colors": ["#9f4d1b", "#c69039", "#d88d79"]})
for kind in ("split", "centered"):
    theme["look"]["hero"] = kind
    html = pagebuild.render(p, {"hero": kind}, theme, "bakery landing page")
    check(f"{kind} hero: the photo is on the page", "images/bakery.jpg" in html)
    check(f"{kind} hero: cards show their photos", 'src="images/sourdough-bakery.jpg"' in html)
check("a centered hero's photo is inline (not a CSS variable read from lib/)", "url(images/bakery.jpg)" in html
      and "--m42-hero-image:url(" not in html)
check("an item photo path that is not images/*.jpg is ignored", "evil" not in pagebuild.widgets.photo({"photo": "../evil.jpg"}))
print("FAILS:", fails)
