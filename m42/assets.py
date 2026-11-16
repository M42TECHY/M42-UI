"""Front-end libraries (anime.js, three.js, Chart.js ...) downloaded from cdnjs into the project folder.

The model often writes `<script src="anime.min.js">` and then tells the user to "download it from animejs.com
and save it in the same folder". M42 does that itself: cdnjs has a free JSON API (no key), and picking the
newest version that still contains the exact file name the HTML asks for keeps the API the model wrote for
(anime.min.js only exists in anime.js 3.x; 4.x renamed it and changed the API).
"""
import json
import re
import urllib.parse

from tools import ToolError
from web import _cache_get, _cache_put, _http

API = "https://api.cdnjs.com/libraries"
ALLOWED_HOSTS = {"cdnjs.cloudflare.com", "cdn.jsdelivr.net", "unpkg.com"}
ASSET_EXT = (".js", ".mjs", ".css", ".map", ".woff", ".woff2", ".ttf", ".otf")
MAX_BYTES = 8 * 1024 * 1024
MAX_VERSIONS_CHECKED = 12
# <script src="x.js"> and <link href="x.css">: local files the page needs
LOCAL_REF_RX = re.compile(r"""<(?:script[^>]*\ssrc|link[^>]*\shref)\s*=\s*["']([^"'?#]+)["']""", re.I)

SPECS = [{"type": "function", "function": {
    "name": "download_library",
    "description": "Download a front-end library file (JS/CSS, e.g. anime.min.js, three.min.js, chart.umd.js, "
                   "bootstrap.min.css) from cdnjs into the project folder. Use this instead of telling the user "
                   "to download it.",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string", "description": "Library or file name, e.g. 'anime.min.js' or 'animejs'"},
        "save_as": {"type": "string", "description": "Path in the project, default: the file name"},
    }, "required": ["name"]},
}}]
NAMES = {"download_library"}


def _get_json(url):
    key = "cdnjs|" + url
    cached = _cache_get(key)
    if cached is not None:
        return cached
    _, _, body = _http(url, timeout=20)
    try:
        data = json.loads(body)
    except ValueError:
        raise ToolError("cdnjs returned an unreadable response")
    _cache_put(key, data)
    return data


def _version_key(v):
    return [int(n) for n in re.findall(r"\d+", v)[:4]]


def _stable(v):
    return not re.search(r"[a-z]", v.split("+")[0], re.I)  # 1.2.3 yes, 4.0.0-beta.1 / 2.0rc no


def _candidates(name):
    """cdnjs libraries for a file or library name: 'anime.min.js' -> animejs, 'three.module.js' -> three.js."""
    base = re.sub(r"(\.(umd|esm|module|min|bundle|prod|production|global))*\.(m?js|css)$", "", name.lower())
    base = re.sub(r"[-_.]v?\d+(\.\d+)*$", "", base) or name.lower()  # jquery-3.7.1 -> jquery, p5 stays
    q = urllib.parse.urlencode({"search": base, "fields": "filename,version", "limit": 5})
    results = _get_json(f"{API}?{q}").get("results", [])
    # exact-ish names first: "anime" -> animejs before animo.js
    results.sort(key=lambda r: _simple(r["name"]) != _simple(base))
    # only libraries whose name matches: "game.js" must never pull some random cdnjs package
    return [r for r in results if _simple(r["name"]).startswith(_simple(base))
            or _simple(base).startswith(_simple(r["name"]))][:3]


def _simple(s):
    return re.sub(r"[^a-z0-9]", "", s.lower()).removesuffix("js")


def looks_like_library(ref):
    """anime.min.js, chart.umd.js, three.module.js, jquery-3.7.1.min.js: a vendored library, not the
    project's own game.js / styles.css."""
    name = ref.rsplit("/", 1)[-1].lower()
    return bool(re.search(r"\.(min|umd|esm|module|bundle|prod|production)\.(m?js|css)$", name)
                or re.search(r"[-.]v?\d+(\.\d+)+(\.min)?\.(m?js|css)$", name))


def find(name):
    """Return {"library", "version", "file", "url"} for a library/file name, or raise ToolError."""
    name = name.strip().rsplit("/", 1)[-1]
    wanted = name.lower() if name.lower().endswith(ASSET_EXT) else None
    libs = _candidates(name)
    if not libs:
        raise ToolError(f"No library named '{name}' on cdnjs")
    if not wanted:  # just a library name: its default file in the latest version
        lib = libs[0]
        return {"library": lib["name"], "version": lib["version"], "file": lib["filename"], "url": lib["latest"]}
    # jquery-3.7.1.min.js: version 3.7.1, file jquery.min.js
    pinned = re.search(r"[-.@]v?(\d+(?:\.\d+)+)(?=\.(?:min\.)?(?:m?js|css)$)", wanted)
    plain = wanted.replace(pinned.group(0), "") if pinned else wanted
    for lib in libs:
        versions = _get_json(f"{API}/{urllib.parse.quote(lib['name'])}?fields=versions").get("versions", [])
        versions = sorted((v for v in versions if _stable(v)), key=_version_key, reverse=True)
        if pinned:
            versions = [v for v in versions if v == pinned.group(1)] or versions
            wanted = plain
        # newest release first, then the newest of each older major (4.5.0, 4.4.1, 3.2.2, 2.2.0 ...): a file
        # renamed in a new major (anime.min.js -> anime.umd.min.js) is found in a few requests
        order, majors = versions[:2], set()
        for v in versions:
            major = (_version_key(v) or [0])[0]
            if major not in majors:
                majors.add(major)
                order.append(v)
        for v in list(dict.fromkeys(order))[:MAX_VERSIONS_CHECKED]:
            files = _get_json(f"{API}/{urllib.parse.quote(lib['name'])}/{urllib.parse.quote(v)}?fields=files")
            match = next((f for f in files.get("files", []) if f.rsplit("/", 1)[-1].lower() == wanted), None)
            if match:
                return {"library": lib["name"], "version": v, "file": match,
                        "url": f"https://cdnjs.cloudflare.com/ajax/libs/{lib['name']}/{v}/{match}"}
    raise ToolError(f"cdnjs has no file named '{name}'. Try the library name (e.g. 'animejs').")


def download(workspace, name, save_as=None):
    info = find(name)
    url = info["url"]
    host = urllib.parse.urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS or not url.lower().endswith(ASSET_EXT):
        raise ToolError(f"Refusing to download {url}: only JS/CSS/font files from {', '.join(sorted(ALLOWED_HOSTS))}")
    _, _, raw = _http(url, timeout=60, as_bytes=True, limit=MAX_BYTES)
    if len(raw) > MAX_BYTES:
        raise ToolError(f"{info['file']} is larger than {MAX_BYTES // 1024 // 1024} MB")
    target = save_as or info["file"].rsplit("/", 1)[-1]
    p = workspace.resolve(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.write_bytes(raw)
    summary = (f"Downloaded {info['library']} {info['version']} ({info['file']}, {len(raw) // 1024} KB) "
               f"from cdnjs → {workspace.rel(p)}")
    return {"summary": summary, "content": summary + f"\nSource: {url}", "output": f"Source: {url}",
            "path": workspace.rel(p), "changed": True, "created": not existed, "url": url}


def missing_refs(workspace, html_paths):
    """Local <script src>/<link href> files that the given HTML files need but that don't exist."""
    missing = {}
    for hp in html_paths:
        try:
            text = hp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ref in LOCAL_REF_RX.findall(text):
            if re.match(r"^(https?:)?//|^data:", ref, re.I) or not ref.lower().endswith(ASSET_EXT):
                continue
            target = (hp.parent / ref).resolve()
            if not target.exists():
                try:
                    missing[workspace.rel(workspace.resolve(str(target)))] = ref
                except ToolError:
                    continue  # points outside the project
    return missing


def call(name, args, workspace):
    if name != "download_library":
        raise ToolError(f"Unknown tool {name}")
    try:
        return download(workspace, **args)
    except TypeError as e:
        raise ToolError(f"Bad arguments for {name}: {e}")
