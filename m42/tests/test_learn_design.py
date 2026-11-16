"""🧠 Design lessons (learn.add_design_lesson / recall_design): rules M42 learns from looking at its own pages, kept per
kind of page, the same rule counted not doubled, read back for the next builds. (No model needed; its own memory folder.)"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp(prefix="m42-learn-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import learn  # noqa: E402

FAILS = 0


def check(name, ok, info=""):
    global FAILS
    print(("ok   " if ok else "FAIL ") + name, info if not ok else "")
    FAILS += 0 if ok else 1


check("no rules yet: nothing to read", learn.recall_design("landing", "a bakery page") == "")
a = learn.add_design_lesson("landing", "hero: text covered by the photo",
                            "Keep a long hero headline clear of the photo: give the words their own column", True)
b = learn.add_design_lesson("landing", "packages: squeezed column",
                            "Never make a section of cards narrow to fill an empty area; give it more items or a wider layout", False)
c = learn.add_design_lesson("app", "pos: cart drawn as a form", "A point of sale's bill is drawn as an invoice beside the products, never as a form", True)
check("rules are kept", all((a, b, c)), (a, b, c))
check("... a rule too short to mean anything is not", learn.add_design_lesson("landing", "x", "be nice", True) is None)
land = learn.recall_design("landing", "a wedding planner landing page")
check("a landing page reads the landing rules", "headline" in land and "narrow" in land, land)
check("... not the app's", "invoice" not in land)
check("an app screen reads its own", "invoice" in learn.recall_design("app", "a supermarket POS"))
learn.add_design_lesson("landing", "hero again", "Keep a long hero headline clear of the photo: give the words their own column always", True)
rows = learn.design_listing()
check("the same rule again is counted, not doubled", sum("headline" in r[1] for r in rows) == 1 and any(r[3] == 2 for r in rows), rows)
check("... a fix that made it worse is kept as what not to do", any(not r[2] and "narrow" in r[1] for r in rows))
print("FAILS:", FAILS)
