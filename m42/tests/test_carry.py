"""A correction draws a page anew from its plan; what was changed in the file after the build stays (2026-11-11: an
attendance page's line fixes and rules, 63 lines, were lost when "the student table's CSS" re-drew it, and the page
fell apart): the page as drawn is kept in site.json, the file's changes since are made again on the new drawing."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402
import llm  # noqa: E402
import sitedit  # noqa: E402
import test_site as ts  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


llm.complete_json = ts.fake_json
d = Path(tempfile.mkdtemp())
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], {"id": "c", "name": "c", "folders": [str(d)]})
a.page_from_plan("oru admin page vennum for retail shop management", dict(ts.SPEC), [].append)
site = sitedit.load(d)
check("the page as drawn is kept with the site", site and site["pages"][0].get("rendered")
      == (d / "index.html").read_text(encoding="utf-8"))

# after the build: a fix in the file (as the line fixer makes) and a script for a rule
page = (d / "index.html").read_text(encoding="utf-8")
fixed = page.replace("</body>", "<script>function markAttendance(){ return 42; }</script>\n</body>", 1)
fixed = fixed.replace('<main', '<main data-fixed="yes"', 1) if "<main" in fixed else fixed.replace("<body", '<body data-fixed="yes"', 1)
(d / "index.html").write_text(fixed, encoding="utf-8")

# a correction to one section draws the page anew
secs = site["pages"][0]["plan"]["sections"]
k = next(i for i, s in enumerate(secs) if s["part"] in ("table", "data_table"))
LOC = {"changes": [{"page": "index.html", "action": "edit_section", "section": k, "part": "", "position": -1, "colors": [],
                    "theme": "", "name": "", "what": "rename"}]}


def fake(base, model, messages, schema, **kw):
    if "changes" in schema.get("properties", {}):
        return LOC, {}
    return dict(secs[k], title="Student Register"), {}


llm.complete_json = fake
ev = []
a.edit_site("student table title maathu", ev.append)
after = (d / "index.html").read_text(encoding="utf-8")
check("the section changed", "Student Register" in after)
check("the fix and the rule's script made after the build are still there", "markAttendance" in after and 'data-fixed="yes"' in after,
      [e.get("text") for e in ev if e.get("type") == "assistant_text"])
check("site.json keeps the new drawing for the next correction", sitedit.load(d)["pages"][0].get("rendered") not in (None, page))
print("FAILS:", fails)
