"""What the model actually receives for a project chat vs a general chat."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import llm  # noqa: E402

seen = []


def fake_stream(base_url, model, messages, **k):
    seen.append(messages)
    name = "list_dir" if len(seen) == 1 else None
    calls = [{"id": None, "name": name, "arguments": "{}"}] if name else []
    if not name:
        yield ("text", "ok")
    yield ("done", {"content": "" if name else "ok", "tool_calls": calls, "usage": None, "stopped": False})


llm.stream_chat = fake_stream
base = Path(tempfile.mkdtemp())
for d in ("web", "api"):
    (base / d).mkdir()
    (base / d / f"{d}.txt").write_text(d)

a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
project = {"name": "Shop App", "folders": [str(base / "web"), str(base / "api")],
           "instructions": "Use Python 3.12. Reply in Tanglish."}
a.load([], project)
events = []
a.run("list the files", events.append)
print("--- context message sent to the model:")
print(seen[0][1]["content"])
print("--- list_dir result the model got:")
print([m["content"] for m in a.messages if m["role"] == "tool"][0])
project_system = seen[0][0]["content"]

a.load([], None)
seen.clear()
a.run("hello", lambda e: None)
print("--- general chat context:")
print(seen[0][1]["content"])
print("system prompt identical for both (cache shared):", seen[0][0]["content"] == project_system)
