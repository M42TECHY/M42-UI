"""The design-reference flow inside M42's request handling: a page asked in the chat goes spec -> references
(found, or the user's attached shot) -> page plan; the data-source question does not look for references twice;
a page request with a screenshot uses it as the design reference (not a copy)."""
from pathlib import Path
import base64
import io
import os
import sys
import tempfile

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image  # noqa: E402

import agent as agent_mod  # noqa: E402
import app  # noqa: E402
import llamacpp  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


buf = io.BytesIO()
Image.new("RGB", (64, 40), (200, 30, 30)).save(buf, "PNG")
SHOT = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
app.State.config = {"base_url": "x", "model": "llama.cpp/auto", "web_enabled": True}
app.State.agent = a = agent_mod.Agent(app.State.config)
calls = []
llamacpp.vision_model = lambda prefer=None: "llama.cpp/q35-4b"
app.switch_model = lambda target, kind, emit, vision=False, warm=True: calls.append(("switch", kind, vision)) or True
a.find_design_refs = lambda asked, spec, emit, model=None: calls.append(("find", asked)) or [("x.png", "https://r.example/")]
app.webclone.to_data_url = lambda p: SHOT
a.read_design_refs = lambda asked, spec, refs, emit, model: calls.append(("read", len(refs), model)) or dict(spec, ref_done=True, ref_layout="top-nav")

spec = {"title": "Restaurant", "sections": [{"name": "Menu", "what": "", "part": "tabs"}]}
out = app.design_refs("oru restaurant site", dict(spec), [].append, model="llama.cpp/q35-4b")
check("no shot attached: no GitHub lookup, M42 designs the page itself",
      calls == [] and out.get("ref_done") and "ref_layout" not in out, calls)
calls.clear()
out2 = app.design_refs("oru restaurant site", out, [].append)
check("after the data-source answer: not looked up again", calls == [], calls)
calls.clear()
out3 = app.design_refs("intha mathiri design la restaurant site", dict(spec), [].append, images=[SHOT])
check("the user's shot is the reference: no search", [c[0] for c in calls] == ["switch", "read"] and calls[1][1] == 1
      and a._ref_kind is None, calls)
calls.clear()
a.find_design_refs = lambda asked, spec, emit, model=None: calls.append(("find", asked)) or []
out4 = app.design_refs("oru restaurant site", dict(spec), [].append)
check("nothing found: the spec as it was, marked so the answer path doesn't search again",
      out4.get("ref_done") and "ref_layout" not in out4 and calls == [], calls)

# a page request with a screenshot goes to the reference flow (not the clone / the bug-report reader)
ran = []
app.page_with_reference = lambda message, images, emit, vision: ran.append((message, len(images)))
import webkit  # noqa: E402
msg = "intha design mathiri oru biryani restaurant website pannu"
check("the words: a site, not a clone", webkit.site_request(msg) and not app.webclone.wants_clone(msg),
      (webkit.site_request(msg), app.webclone.wants_clone(msg)))
# the user's shot + no topic of their own: the page is about what the picture shows (a real run: a smart home
# dashboard shot + "admin dashboard" became a "Tamil Nadu Bus Admin")
import importlib  # noqa: E402
importlib.reload(app)
app.State.config, app.State.agent = {"base_url": "x", "model": "llama.cpp/auto", "web_enabled": True}, a
app.switch_model = lambda *x, **k: True
llamacpp.vision_model = lambda prefer=None: "llama.cpp/q35-4b"
brief = {"match": True, "layout": "sidebar", "hero": "compact", "sections": ["device cards"], "cards": "shadow",
         "corners": "rounded", "style": "minimal", "font": "modern", "mood": "calm", "topic": "smart home device control"}


def fake_read(asked, spec, refs, emit, model):
    a._ref_read = ([brief], [None])
    return dict(spec, ref_done=True)


a.read_design_refs = fake_read
asked_for = []
PICTURES = []
a._page_spec = lambda asked, emit, model=None, picture="": PICTURES.append(picture) or asked_for.append(asked) or {"title": "x", "sections": [{"name": "a", "what": "", "part": "stats"}]}
a.ask_page_question = lambda *x: False
READING = {}  # what the model reads in the request + picture (agent.understand): set per case below


def fake_understand(asked, emit, image=None, model=None):
    a.use_intent(READING)
    a._understood = True
    return {}


a.understand = fake_understand
built_with = []
a.page_from_plan = lambda asked, spec, emit, model=None: built_with.append((asked, spec)) or True
ev = []
READING.update(layout="app screen", names_subject=False, subject="smart home device control")
app.page_with_reference("intha mathiri oru site pannu admin dashboard", [SHOT], ev.append, "llama.cpp/q35-4b")
check("no topic in the words: the spec and the page are about the picture's topic",
      "smart home device control" in asked_for[0] and "smart home" in built_with[0][0]
      and built_with[0][1].get("ref_layout") == "sidebar", (asked_for, built_with[0][1].get("ref_layout")))
check("the user is told where the topic came from", any("name no subject" in str(e.get("message")) for e in ev))
asked_for.clear()
READING.update(names_subject=True, subject="bus ticket admin")
app.page_with_reference("intha mathiri bus ticket admin pannu", [SHOT], [].append, "llama.cpp/q35-4b")
check("a topic the user named stays first; the picture's is only a hint the model can drop",
      asked_for and asked_for[0].startswith("intha mathiri bus ticket admin pannu") and "unless the request names another" in asked_for[0], asked_for)
asked_for.clear()
READING.update(names_subject=False, subject="smart home device control")
app.page_with_reference("ithe matheri web page ready panni kutu", [SHOT], [].append, "llama.cpp/q35-4b")
check("a misspelt 'mathiri' (matheri) the model reads as no subject: the picture's topic is the subject",
      "about: smart home device control" in asked_for[0], asked_for)
check("a reference picture: the spec is made from its cards / blocks, not from web ideas", PICTURES and all(x.strip() for x in PICTURES), PICTURES[:2])
import webkit as _wk  # noqa: E402
m = _wk.spec_messages("pos page", "web text about POS", "- Cart (list thumbs): rows")[1]["content"]
check("... and the spec prompt has the picture's cards and no web text", "Cart (list thumbs)" in m and "web text" not in m and "add no other features" in m)
print("FAILS:", fails)
