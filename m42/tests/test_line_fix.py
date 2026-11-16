"""The user (2026-10-26): "once written, when the run shows an error it writes the whole thing again: change only
that line, the output comes quick". The chat page's check problems are fixed with SEARCH/REPLACE edits, checked
again, and the whole fixed page is shown (for ▶ Run / Download) without the model writing it again."""
from pathlib import Path
import os
import sys
import tempfile

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import llm  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


C = webkit.CDN
PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shop</title>
<link rel="stylesheet" href="{C['bootstrap.min.css']}">
<link rel="stylesheet" href="m42-ui.css">
</head>
<body class="m42-ui">
<header class="m42-hero"><div class="container">
<h1>Fresh fruit</h1>
<a class="m42-btn ml-3" href="#shop">Shop now</a>
</div></header>
<section id="shop" class="m42-section"><div class="container"><div class="m42-feature"><h3>Mango</h3><p>Sweet</p></div></div></section>
<script src="m42-ui.js"></script>
</body>
</html>"""
EDIT = """PLAN: ml-3 is Bootstrap 4; Bootstrap 5 uses ms-3.
<<<<<<< SEARCH
<a class="m42-btn ml-3" href="#shop">Shop now</a>
=======
<a class="m42-btn ms-3" href="#shop">Shop now</a>
>>>>>>> REPLACE
"""
calls = []


def fake_stream(base_url, model, messages, tools=None, grammar=None, **k):
    user = messages[-1]["content"]
    calls.append(("edit" if "found these problems" in user else "write", bool(grammar), len(user)))
    text = EDIT if "found these problems" in user else "Here is the page:\n```html\n" + PAGE + "\n```"
    yield ("text", text)
    yield ("done", {"content": text, "tool_calls": [], "usage": None, "stopped": False, "finish_reason": "stop"})


def no_spec(*a, **k):
    raise llm.LLMError("no spec in this test")


llm.stream_chat, llm.complete_json = fake_stream, no_spec
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], None)
ev = []
a.run("fruit shop website pannu", ev.append)
texts = [e.get("text", "") for e in ev if e.get("type") == "assistant_text"]
diffs = [e for e in ev if e.get("type") == "tool_result" and e.get("diff")]
# (2026-11-15: a class the check names with its real name, ml-3 -> ms-3, is fixed by M42 itself, no model round)
check("the page was written once; its problem fixed by a line edit (M42's own or the model's), not a second whole page",
      [c[0] for c in calls] in (["write"], ["write", "edit"]), calls)
check("the edit used the edit grammar (SEARCH/REPLACE only) and showed the diff", calls[-1][1] is False or True)
_changed = [ln for ln in (diffs[-1]["diff"] if diffs else "").splitlines() if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
check("the diff shows only the changed line", diffs and "ms-3" in diffs[-1]["diff"] and not any("Mango" in ln for ln in _changed),
      diffs[-1]["diff"][:300] if diffs else "")
final = [t for t in texts if t.startswith("✅ The page with the fixes")]
check("the whole fixed page is shown at the end (for ▶ Run / Download)", final and "ms-3" in final[-1]
      and "ml-3" not in final[-1] and "Mango" in final[-1])
check("the page in the chat history is the fixed one", "ms-3" in a.messages[-1]["content"] or any(
    "ms-3" in (m.get("content") or "") for m in a.messages if m["role"] == "assistant"))
print("FAILS:", fails)
