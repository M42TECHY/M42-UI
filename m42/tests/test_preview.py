"""▶ Run / ⬇ Download (the user, 2026-10-25): a chat page runs in a popup and downloads as a zip with its CSS / JS.
The page is served from its own random folder (never with the M42 token), only its own files; the zip has
index.html + only the kit files it uses (with the icon fonts) and works offline."""
import io
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


PORT = 8799
app.PREVIEWS = Path(tempfile.mkdtemp())
app.State.port, app.State.token = PORT, "test-token-123"
srv = ThreadingHTTPServer(("127.0.0.1", PORT), app.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{PORT}"


def req(path, data=None, token=True):
    r = urllib.request.Request(B + path, data=json.dumps(data).encode() if data is not None else None,
                               headers={"Content-Type": "application/json", **({"X-M42-Token": "test-token-123"} if token else {})},
                               method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {}


C = webkit.CDN
page = (f'<!DOCTYPE html><html><head><link rel="stylesheet" href="{C["bootstrap.min.css"]}">'
        f'<link rel="stylesheet" href="{C["bootstrap-icons.min.css"]}"><link rel="stylesheet" href="m42-ui.css"></head>'
        f'<body class="m42-ui"><header class="m42-hero"><h1>Hi <i class="bi bi-star"></i></h1></header>'
        f'<script src="{C["bootstrap.bundle.min.js"]}"></script><script src="m42-ui.js"></script></body></html>')
code, body, _ = req("/api/page/preview", {"html": page})
d = json.loads(body)
check("a page is saved for the popup", code == 200 and d["url"].startswith("/preview/") and "test-token" not in d["url"], d)
code, html, _ = req(d["url"], token=False)
check("the popup's page is served without the M42 token, its kit tags pointing at local files",
      code == 200 and b"lib/bootstrap.min.css" in html and b"cdn.jsdelivr" not in html and b'href="lib/m42-ui.css"' in html)
code, css, h = req(d["url"].replace("index.html", "lib/m42-ui.css"), token=False)
check("its lib files load (relative URLs work in the iframe)", code == 200 and b".m42-hero" in css and "text/css" in h.get("Content-Type", ""))
check("only its own folder: ../ is refused", req(d["url"].replace("index.html", "../../app.py"), token=False)[0] == 404
      and req("/preview/" + "0" * 16 + "/index.html", token=False)[0] == 404)
check("M42's own API still needs the token", req("/api/session", token=False)[0] == 403)
code, data, h = req(d["download"])
z = zipfile.ZipFile(io.BytesIO(data)) if code == 200 else None
names = sorted(z.namelist()) if z else []
check("⬇ a zip: index.html + only the kit files it uses + icon fonts", code == 200 and "attachment" in h.get("Content-Disposition", "")
      and "m42-page/index.html" in names and "m42-page/lib/m42-ui.js" in names and "m42-page/lib/fonts/bootstrap-icons.woff2" in names
      and "m42-page/lib/jquery.min.js" not in names and "m42-page/lib/sweetalert2.all.min.js" not in names
      and not any(n.endswith(".m42-kit.json") for n in names), names)
check("the download needs the token", req(d["download"], token=False)[0] == 403)
ui = open(str(Path(__file__).resolve().parent.parent / r"ui\app.js"), encoding="utf-8").read()
ui += open(str(Path(__file__).resolve().parent.parent / "ui" / "index.html"), encoding="utf-8").read()
check("the UI: ▶ Run on whole pages, the preview panel's frame sandboxed without same-origin, auto-open only for new pages",
      "code-run" in ui and 'sandbox="allow-scripts allow-forms allow-modals allow-popups' in ui and "allow-same-origin" not in ui
      and "previewNewPage()" in ui and "!replaying" in ui and 'id="previewPane"' in ui)
srv.shutdown()
print("FAILS:", fails)
