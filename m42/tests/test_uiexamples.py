"""The UIGEN-T2 examples (uiexamples.py, 2026-11-03) and the web flow on the 4B only: a card's example cut from a
similar page, none for a card the data has no page of; a page's section outline where there is no reference picture;
every web page / card / clone / site edit goes to the chat model (switch_web), never the 7B coder."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uiexamples  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


if not uiexamples.ready():
    print("SKIPPED: knowledge/uigen-t2/index.sqlite is not built (uiexamples.build())")
    sys.exit(0)
r = uiexamples.example("Seat map: pick your seats in the cinema hall, booked seats grey")
check("a seat map card: a seat booking page's part", r and "seat" in (r[0] + r[1]).lower() and len(r[1]) <= 2200, r and r[0])
check("no example for a card the data has no page of (sankey: not an onboarding 'flow')",
      uiexamples.example("Sankey flow: energy sources to uses") is None)
check("the snippet has no scripts", r and "<script" not in r[1])
o = uiexamples.outline("coffee shop landing page")
check("a coffee shop: a coffee shop page's sections", o and "coffee" in o[0].lower() and len(o[1]) >= 3, o)
check("'construction company': not a no-code builder's 'logic construction'", uiexamples.outline("construction company website") is None
      or "company" in uiexamples.outline("construction company website")[0].lower())
check("Tanglish words are no search words", "pannu" not in uiexamples._terms("bakery website pannu"))

app = Path(str(Path(__file__).resolve().parent.parent / r"app.py")).read_text(encoding="utf-8")
check("the web flow loads the chat model (switch_web), the coder only for firmware / games",
      "def switch_web" in app and app.count("switch_web(") >= 6)
for name in ("def page_with_reference", "def build_clone"):
    body = app.split(name, 1)[1].split("\ndef ", 1)[0]
    check(f"{name[4:]}: no 7B coder", 'auto_target("code")' not in body)
check("custom cards / site edits: the loader gives the chat model", 'agent.load_model = lambda kind, em: ((auto_target("chat") if switch_web(em)' in app)
agent = Path(str(Path(__file__).resolve().parent.parent / r"agent.py")).read_text(encoding="utf-8")
check("custom cards get a UIGEN example when none is learned", "uiexamples.example(what)" in agent)
check("no picture: the dataset's page outline goes to the plan", "uiexamples.outline(asked)" in agent)
print("FAILS:", fails)
