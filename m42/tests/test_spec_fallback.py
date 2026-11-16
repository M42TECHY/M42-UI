"""The school reference run (2026-10-30): the picture's 9 cards were read, then the spec JSON came back broken and M42
let the coder write the page from the words (a random dark look). Now the spec comes from the picture's cards."""
from pathlib import Path
import os, sys, tempfile
os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import llamacpp, agent, llm

fails = 0
def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300]); fails += not ok

a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a._web_enabled = lambda: False
budgets = []
def broken(base, model, msgs, schema, max_tokens=0, **k):
    budgets.append(max_tokens)
    raise llm.LLMError('Model did not return valid JSON: { "title": "School Management Dashboard", "items": [')
llm.complete_json = broken
SECS = [{"name": "Banner", "part": "banner", "what": "classes up 30%"},
        {"name": "Totals", "part": "kpi_tiles", "what": "classes, students, hours, income"},
        {"name": "Student Attendance", "part": "donut", "what": "present vs absent"}]
a._ref_grid = {"sections": SECS, "ref_grid": {"sidebar": True}}
ev = []
picture = "\n".join(f"- {s['name']} ({s['part']}): {s['what']}" for s in SECS)
spec = a._page_spec("enakku ithe mathiri web page vennum (about: school management dashboard, as in the reference picture)",
                    ev.append, model="m", picture=picture)
check("a picture: the spec gets more room (1600 tokens)", 1600 in budgets, budgets)
check("broken JSON + a picture: the spec from its cards", spec and [i["name"] for i in spec["items"]] == ["Banner", "Totals", "Student Attendance"]
      and spec["title"] == "School Management Dashboard", spec)
check("the user is told", any("Spec from your picture's 3 cards" in str(e.get("text")) for e in ev))
# no picture: as before (None: the coder writes the page)
a._ref_grid = None
budgets.clear()
check("no picture: no spec as before, 900 tokens", a._page_spec("restaurant site vennum", [].append, model="m") is None and budgets[-1:] == [900], budgets)  # (the request in full first: 380)
print("FAILS:", fails)
