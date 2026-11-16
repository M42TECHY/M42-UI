"""Widget polish against the school reference (2026-10-30): plain white tiles in one row with arrowed trend pills,
$ before the number, a marked day keeps its number, the card picker says the plan's word, tasks with checkboxes."""
from pathlib import Path
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llamacpp  # noqa: F401
import designref, pagebuild, widgets

fails = 0
def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300]); fails += not ok

ctx = {"ids": set(), "ref_grid": {"sidebar": True}}
tiles = {"items": [{"title": "Total Classes", "value": 147, "badge": "+15%"}, {"title": "Total Students", "value": 3250, "badge": "-5%"},
                   {"title": "Total Hours", "value": 104687, "badge": "-10%"}, {"title": "Total Income", "value": 1682500, "unit": "$", "badge": "+23%"}],
         "_look": {"plain": True}}
h = widgets.w_kpi_tiles(tiles, ctx)
check("plain tiles from the reference, in one row of 4", 'is-plain' in h and 'is-row" style="--n:4' in h, h[:200])
check("trend pills with their arrows", "bi-arrow-up" in h and "bi-arrow-down" in h)
check("$ before the number", "$1,682,500" in h and "1,682,500 $" not in h)
check("₹ as before", pagebuild.amount(1200, "₹") == "₹1,200" and pagebuild.amount(12, "kg") == "12 kg")
check("tinted tiles stay when the reference's are not plain", "is-plain" not in widgets.w_kpi_tiles(dict(tiles, _look={}), ctx))
cal = widgets.w_calendar({"labels": ["March 2030"], "taken": [15], "items": [{"title": "A", "icon": "bi-book"}, {"title": "B", "icon": "bi-mic"},
                                                                              {"title": "C", "icon": "bi-journal"}]}, {"ids": set()})
check("one marked day and an agenda of 3: the day keeps its number", 'class="mark">15<' in cal and "has-icon" not in cal)
rows = widgets.w_template_rows({"items": [{"title": "Grade essays", "text": "April 24"}, {"title": "Update plans", "text": "April 25", "badge": "done"}],
                                "_look": {"row": ["checkbox", "title", "meta", "edit", "delete"]}}, {"ids": set()})
check("tasks: a checkbox each, ticked when done, edit + delete", rows.count('type="checkbox"') == 2 and rows.count(" checked") == 1
      and "bi-pencil-square" in rows and "bi-trash3" in rows)
src = Path(str(Path(__file__).resolve().parent.parent / r"pagebuild.py")).read_text(encoding="utf-8")
check("the card picker says the plan's word (Weekly), else This Month", 'e(sec.get("eyebrow") or "This Month")' in src)
check("the 4B can name a checkbox / edit in a row", "checkbox" in designref.ROW_KINDS and "edit" in designref.ROW_KINDS)
# the reference's own colours, kept as they are (the school shot: sky blue, its pastel yellow and lavender)
import webkit
prof = designref.profile(Path(__file__).resolve().parent / "refs" / "school.webp")
check("colours: the sky blue, a yellow and the lavender (each its own hue)", len(prof["colors"]) == 3
      and any(designref.hue_gap(c, "#cfcefe") < 20 for c in prof["colors"]), prof["colors"])
lk = webkit.make_look("school admin", look={"colors": ["#44bddd", "#f6f2cf", "#cfcefe"], "exact": True})
check("an exact reference colour is not darkened; dark text on it", lk["primary"] == "#44bddd" and lk["on"] != "#ffffff", lk)
check("its pastel 2nd / 3rd colours kept (not invented ones)", lk["accent2"] == "#f6f2cf" and lk["accent3"] == "#cfcefe", lk)
lk2 = webkit.make_look("school admin", look={"colors": ["#44bddd"]})
check("a model's colour (not a picture's) still made readable as before", lk2["primary"] != "#44bddd", lk2["primary"])
print("FAILS:", fails)
