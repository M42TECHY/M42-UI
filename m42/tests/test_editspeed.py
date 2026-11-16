"""Follow-ups on a built site stay fast (the user, 2026-11-11: an edit took minutes: the whole chat with the build in
it went to the model, 16k tokens and a 141 s fold, and a failing download was tried again and again):
- in a folder with a built site the model sees the last two turns, not the whole chat;
- the same error twice (even from other arguments) stops the request."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import sitedit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


d = Path(tempfile.mkdtemp())
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], {"id": "e", "name": "e", "folders": [str(d)]})
sitedit.save(d, sitedit.new_site("a bakery page", {}, None, [({"sections": []}, {}, "index.html")], single=True))
page = "<html>" + "x" * 20000 + "</html>"
for k in range(6):  # a long chat: the build and earlier edits, each with a whole page in it
    a.messages += [{"role": "user", "content": f"request {k}"}, {"role": "assistant", "content": "```html\n" + page + "\n```"}]

seen = {}


def fake_ask(emit):
    hist = a._trimmed_history()
    seen.setdefault("sizes", []).append(sum(len(m.get("content") or "") for m in hist))
    seen["first"] = hist[0]["content"]
    n = len(seen["sizes"])
    # a download that fails the same way with other URLs each time
    return "", [{"id": f"c{n}", "name": "run_command", "arguments": '{"command": "curl https://cdn.example.com/anime@4.%d.js"}' % n}]


a._ask_model = fake_ask
a._execute = lambda c, emit: ("Error: download blocked for https://cdn.example.com/anime@4.%s.js (exit 7)" % c["id"], False)
ev = []
a.run("intha page la enna library use pannirukku", ev.append)
check("a follow-up on a built site: the model gets a short history, not the whole chat",
      seen["sizes"] and seen["sizes"][0] < 12000 and "built the site in this folder" in seen["first"], seen.get("sizes"))
errs = [e["message"] for e in ev if e.get("type") == "error"]
check("the same error twice stops the request (other URLs, same error)", len(seen["sizes"]) == 2 and errs
      and "twice" in errs[0], (len(seen["sizes"]), errs))

# without a site the chat's own history is used as before
d2 = Path(tempfile.mkdtemp())
b = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
b.load([], {"id": "f", "name": "f", "folders": [str(d2)]})
b.messages += [{"role": "user", "content": "first"}, {"role": "assistant", "content": "one"},
               {"role": "user", "content": "second"}, {"role": "assistant", "content": "two"}]
b._history_from = 0
check("no site in the folder: the whole (short) chat as before", [m["content"] for m in b._trimmed_history()][:2] == ["first", "one"])
print("FAILS:", fails)
