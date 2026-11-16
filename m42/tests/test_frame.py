"""Shots on a backdrop / in a browser window (2026-10-30, the user's design-refs/admin-dashboard): the page is found,
its top bar is read from the page's own top, a page-wide background is no card, open sections are cut apart."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llamacpp  # noqa: F401
import designref
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
fails = 0
def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300]); fails += not ok

def frame(f):
    im = Image.open(HERE / "refs" / f).convert("RGB")
    im = im.resize((1000, round(im.height * 1000 / im.width)))
    return designref._page_frame(np.asarray(im))

fr = frame("fitshop.webp")
check("fitshop: the window on its backdrop, below its browser bar", fr and abs(fr[0] - .062) < .01 and abs(fr[1] - .128) < .01
      and abs(fr[2] - .938) < .01, fr)
fr = frame("mycogen.webp")  # a soft gradient backdrop, no browser bar
check("mycogen: a window on a gradient backdrop", fr and abs(fr[0] - .111) < .01 and abs(fr[1] - .039) < .01, fr)
check("cooking: a browser bar is cut off the page", (frame("82.webp") or [0, 0])[1] > .14, frame("82.webp"))
g = designref.cards(HERE / "refs" / "fitshop.webp")
boxes = sorted(g["boxes"], key=lambda b: (round(b[1], 1), b[0]))
check("fitshop: 7 cards (4 on top, 3 open sections below)", len(boxes) == 7 and sum(b[1] < .3 for b in boxes) == 4, [[round(v, 2) for v in b] for b in boxes])
check("... the menu + heading is no card", all(b[1] > .25 for b in boxes))
check("... its round flags in a list are no icon rail / sidebar", g["sidebar"] is False)
check("... the top bar is read from the page's top", abs(g["page_top"] - .128) < .01, g["page_top"])
check("... 'Product sales' keeps its number columns", any(b[0] > .69 and b[2] > .9 and b[1] > .5 for b in boxes))
# the top row on a strip of its own is the top bar, not a card (and the heading's controls under it go with it)
for name, first in (("ethan.webp", .25), ("boltz.webp", .26)):
    g = designref.cards(HERE / "refs" / name)
    top = min(b[1] for b in g["boxes"])
    check(f"{name}: the top bar / heading row is no card (first card at {first})", top >= first - .01, round(top, 3))
# the school shot: the banner whole (its 3D picture joined), the tiles not grown into it, the top bar kept for reading
g = designref.cards(HERE / "refs" / "school.webp")
bs = sorted(g["boxes"], key=lambda b: (b[1], b[0]))
check("school: 7 cards, the first the whole banner", len(bs) == 7 and bs[0][2] > .65 and bs[0][3] < .26, [[round(v, 2) for v in b] for b in bs])
check("... the KPI tiles below the banner, not into it", any(b[1] > .25 and b[3] < .36 for b in bs))
check("... the top strip (search, icons, profile) above the cards", g["page_top"] < .08 and min(b[1] for b in bs) > .12)
print("FAILS:", fails)
