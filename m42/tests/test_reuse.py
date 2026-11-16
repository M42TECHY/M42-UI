"""A page asked for in a folder that already has one is not built again from nothing (the user, 2026-11-12: "a file
already made, made again and again, only costs time: use what is there, smartly"):
- the same request (and picture) again: drawn anew from the saved plan, no model call, the file's own changes kept;
- a change with the same picture: an edit; a new picture for the same site: restyle (its content kept);
  another page or "from scratch": a new build, the old one backed up whole;
- a picture's readings are kept by its fingerprint and reused."""
import base64
import io
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402
import designref  # noqa: E402
designref.READS = Path(tempfile.mkdtemp())  # (not the app's own saved readings)
import llm  # noqa: E402
import sitedit  # noqa: E402
import test_site as ts  # noqa: E402
from PIL import Image  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


def picture(colour):
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), colour).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


red, blue = picture("red"), picture("blue")
llm.complete_json = ts.fake_json
d = Path(tempfile.mkdtemp())
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], {"id": "r", "name": "r", "folders": [str(d)]})
check("an empty folder: nothing to reuse", a.existing_build("oru admin page vennum for retail shop management")[0] == "")
a._raw_message, a._ref_hash = "oru admin page vennum for retail shop management", designref.fingerprint(red)
a.page_from_plan("oru admin page vennum for retail shop management", dict(ts.SPEC), [].append)
site = sitedit.load(d)
check("the site keeps the words and the picture it was built from", site.get("message", "").startswith("oru admin page")
      and site.get("ref_hash") == designref.fingerprint(red), (site.get("message"), site.get("ref_hash")))

msg = "oru admin page vennum for retail shop management"
check("the same request and picture: redraw", a.existing_build(msg, [red])[0] == "redraw", a.existing_build(msg, [red]))
check("the same picture with a change: edit", a.existing_build("sidebar colour blue ah maathu", [red])[0] == "edit")
check("a new picture for the same site: restyle (its content kept)", a.existing_build(msg, [blue])[0] == "restyle")
check("another page: new", a.existing_build("hospital appointment booking website", [])[0] == "new")
check("from scratch: new", a.existing_build(msg + " puthusa from scratch", [red])[0] == "new")

# a redraw: no model call, the file's own change kept, the page drawn again
page = (d / "index.html").read_text(encoding="utf-8")
(d / "index.html").write_text(page.replace("</body>", "<script>function keepMe(){}</script>\n</body>", 1), encoding="utf-8")


def no_model(*a_, **k):
    raise AssertionError("the model was called in a redraw")


llm.complete_json = no_model
ev = []
a.edit_site(msg, ev.append, redraw="drawn again")
after = (d / "index.html").read_text(encoding="utf-8")
check("redraw: no model call, the page there with its own change kept", "keepMe" in after and "m42-" in after,
      [e.get("text") or e.get("message") for e in ev if e.get("type") in ("assistant_text", "error")])
check("... and its preview shown", any(e.get("type") == "page_preview" for e in ev))

# the whole site backed up before a new build
saved = a.backup_site(d)
check("a backup: pages, plan and pictures", saved and (d / saved / "index.html").exists() and (d / saved / ".m42" / "site.json").exists(), saved)
check("the old content for a new design", "brand" in sitedit.content_text(sitedit.load(d)))

# a picture's readings, by its fingerprint
designref.save_read(red, "grid", {"sections": [{"name": "x"}]})
check("a reading kept by the picture's fingerprint", designref.saved_read(red, "grid") == {"sections": [{"name": "x"}]}
      and designref.saved_read(blue, "grid") is None)
calls = []
a.stop_event.clear()
out = a.read_ref_grid(red, lambda e: calls.append(e), "m")
check("the same picture's cards are not read again", out == {"sections": [{"name": "x"}]}
      and any("read before" in str(e.get("message")) for e in calls))
(designref.READS / f"{designref.fingerprint(red)}-grid.json").unlink()
print("FAILS:", fails)
