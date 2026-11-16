"""Long landing-page screenshots in the library (2026-11-03: the user's full-page shots, 1,595 x 18,000-52,000 px)
and the folder chosen by the chat model. A temporary library; the choosers (the 4B in M42) are faked."""
import json
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llamacpp  # noqa: E402,F401
import designref  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


lib = Path(tempfile.mkdtemp())
for d in ("landing-page", "restaurant", "school"):
    (lib / d).mkdir()
# a long page: 12 coloured sections of 800 px, then 9,000 px of blank and a floating "to top" button at the end
im = Image.new("RGB", (800, 9600 + 9000), "white")
dr = ImageDraw.Draw(im)
for i in range(12):
    dr.rectangle((40, i * 800 + 60, 760, i * 800 + 700), fill=(30 + i * 15, 80, 200 - i * 10))
dr.ellipse((740, 18500, 780, 18540), outline="black", width=3)
im.save(lib / "landing-page" / "Long Agency Template.png")
Image.new("RGB", (60, 40), "orange").save(lib / "restaurant" / "cafe.webp")
Image.new("RGB", (60, 40), "blue").save(lib / "school" / "a.webp")
(lib / "catalog.json").write_text(json.dumps({
    "landing-page/Long Agency Template.png": {"kind": "landing-page", "notes": "agency landing; purple", "long": True,
                                              "sections": ["hero", "services", "pricing", "footer"]},
    "restaurant/cafe.webp": {"kind": "restaurant", "notes": "cafe menu page"}}), encoding="utf-8")
designref.LIBRARY = lib

trimmed = designref.trim_blank(im)
check("the blank end is cut (the footer stays)", 9500 <= trimmed.height <= 9700, trimmed.size)
short = Image.new("RGB", (800, 3000), "white")
ImageDraw.Draw(short).rectangle((0, 0, 800, 2900), fill="navy")
check("a page that ends with a short margin is kept whole", designref.trim_blank(short).height == 3000)
check("a long picture is a whole page", designref.is_long(lib / "landing-page" / "Long Agency Template.png"))
check("a dashboard shot is not", not designref.is_long(lib / "school" / "a.webp"))
out = Path(designref.as_png(lib / "landing-page" / "Long Agency Template.png", tempfile.mkdtemp()))
sheet = Image.open(out)
check("the long page goes to the vision model in columns (wider than tall, readable)", sheet.width > sheet.height and sheet.width <= 1800,
      sheet.size)
check("no blank columns from the cut end: the last column has content", sheet.crop((sheet.width * 4 // 5, 0, sheet.width, sheet.height)).convert("L").getextrema()[0] < 200)
check("the brief prompt tells it how to read the columns",
      "columns" in str(designref.brief_messages("data:x", "agency site", "", designref.SHEET_NOTE)[1]["content"][0]["text"]))
e = designref.catalog_entry(lib / "landing-page" / "Long Agency Template.png")
check("the catalog entry with the page's sections", e.get("sections") == ["hero", "services", "pricing", "footer"], e)

folders = list(designref.page_folders().items())
check("the folders with pictures, each with its notes", [f for f, _ in folders] == ["landing-page", "restaurant", "school"]
      and "cafe menu page" in dict(folders)["restaurant"], folders)
msgs = designref.folder_messages("cafe website", folders)
check("the folder prompt: the request and the folder names", "cafe website" in msgs[1]["content"] and "1. restaurant" in msgs[1]["content"])
p = designref.library_pick("cafe website", "cafe website", False,
                           choose_folder=lambda f: [[n for n, _ in f].index("restaurant")])
check("'cafe website' (no folder word): the chooser's folder", p and p[1] == "restaurant", p)
check("no chooser: the word match as before (nothing for 'coffee house')", designref.library_pick("coffee house", "coffee house site", False) is None)
p = designref.library_pick("school admin", "school admin panel", True, choose_folder=lambda f: 1 / 0)
check("a chooser that fails: the word match", p and p[1] == "school", p)
p = designref.library_pick("school admin", "school admin panel", True, choose_folder=lambda f: [99])
check("a number out of range: the word match", p and p[1] == "school", p)
print("FAILS:", fails)
