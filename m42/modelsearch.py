"""🧊 3D models for a page's 3D scene: M42's own kit first (bundled/m42-3d.js: its catalog of objects, stories, extras
read here from the file itself, so a new object there is known at once), then the user's own model files in the
project folder, then free models online (Poly Haven: every model CC0, no key): searched by the words of the thing,
its size checked (a web page needs a small one), saved in the project's models/ with a credit line.
(The user, 2026-11-13: "objects and stories cover most; when none fits, take one from online".)"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent / "bundled" / "m42-3d.js"
API = "https://api.polyhaven.com"
UA = {"User-Agent": "M42-UI/1.0 (local web page builder)"}
MAX_BYTES = 15 * 1024 * 1024  # a model with its textures: more is too heavy for a page
USER_EXT = (".glb", ".gltf", ".stl")

_catalog = None
LIB = Path(__file__).resolve().parent / "bundled" / "models3d"  # 📦 free CC0 model packs bundled with M42 (Kenney, 2026-11-14)
_library = None
# a pack's file name -> the thing's name in the catalog (people and animals by what they are; the rest by their own name)
_PREFIX = {"character-": "", "animal-": "", "aid-": "", "item-": ""}
_PEOPLE = {"female-a": "woman", "female-b": "woman_2", "female-c": "woman_3", "female-d": "woman_4", "female-e": "woman_5",
           "female-f": "woman_6", "male-a": "man", "male-b": "man_2", "male-c": "man_3", "male-d": "man_4", "male-e": "man_5",
           "male-f": "man_6", "male-g": "man_7", "worker": "worker", "soldier": "soldier", "knight": "knight", "robot": "robot_person",
           "alien": "alien", "raider": "raider", "zombie": "zombie"}


def _snake(stem):
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"([a-z])([A-Z])", r"\1_\2", stem).lower()).strip("_")


def library():
    """{name: "pack/file.glb"} of the bundled model packs (people, pets, food, furniture): things the kit's own
    makers lack (the user, 2026-11-14: "people and such are not in the kit: download the free ones and add them")."""
    global _library
    if _library is not None:
        return _library
    out = {}
    for f in sorted(LIB.glob("*/*.glb")) if LIB.is_dir() else []:
        stem = f.stem
        if f.parent.name == "mini-characters" and stem.startswith("character-"):
            name = _PEOPLE.get(stem[len("character-"):], "")
        else:
            for pre in _PREFIX:
                if stem.startswith(pre):
                    stem = stem[len(pre):]
            name = _snake(stem)
        if re.match(r"(floor|wall|stairs|doorway|paneling|ceiling)(_|$)", name):
            continue  # (a room's building pieces: no thing a story shows)
        if name and name not in out:
            out[name] = f"{f.parent.name}/{f.name}"
    if "woman" in out:
        out.setdefault("person", out["woman"])
        out.setdefault("people", out["man"]) if "man" in out else None
    _library = out
    return out


def catalog():
    """{"objects": [...], "stories": [...], "extras": [...], "liquids": [...]} from bundled/m42-3d.js."""
    global _catalog
    if _catalog is not None:
        return _catalog
    try:
        js = KIT.read_text(encoding="utf-8")
    except OSError:
        _catalog = {"objects": [], "stories": [], "extras": [], "cameras": [], "liquids": []}
        return _catalog
    names = set()
    for arr in re.findall(r"family\(\[([^\]]*)\]", js):
        names.update(re.findall(r'"([a-z0-9_]+)"', arr))
    vessels = re.search(r"const VESSELS = \{(.*?)\n  \};", js, re.S)
    if vessels:
        names.update(re.findall(r"^\s{4}([a-z0-9_]+):", vessels.group(1), re.M))
    def const(name):
        m = re.search(name + r" = \[([^\]]*)\]", js)
        return re.findall(r'"([a-z0-9_]+)"', m.group(1)) if m else []
    liquids = re.search(r"const LIQUIDS = \{(.*?)\};", js, re.S)
    names |= {n for n in library() if n not in names}  # (the kit's own maker wins a shared name)
    _catalog = {"objects": sorted(names), "stories": const("const STORIES"), "extras": const("const EXTRAS"), "cameras": const("const CAMERAS"),
                "liquids": sorted(re.findall(r"([a-z]+):", liquids.group(1))) if liquids else []}
    return _catalog


def library_files(names, root):
    """The bundled models a scene uses, copied into the page's folder (models/lib/...): {name: relative path}."""
    import shutil
    lib, out = library(), {}
    for n in names:
        rel = lib.get(n)
        if not rel or not root:
            continue
        src = LIB / rel
        dst = Path(root) / "models" / "lib" / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
            tex = src.parent / "Textures"
            if tex.is_dir() and not (dst.parent / "Textures").exists():
                shutil.copytree(tex, dst.parent / "Textures")
            lic = src.parent / "License.txt"
            if lic.is_file() and not (dst.parent / "License.txt").exists():
                shutil.copy2(lic, dst.parent / "License.txt")
        except OSError:
            continue
        out[n] = f"models/lib/{rel}"
    return out


def user_models(root):
    """The user's own 3D model files in the project folder (models/, or the folder itself): relative paths."""
    root = Path(root)
    out = []
    for p in list(root.glob("*")) + list((root / "models").glob("**/*")):
        if p.is_file() and p.suffix.lower() in USER_EXT and "lib" not in p.parts:
            out.append(p.relative_to(root).as_posix())
    return sorted(set(out))[:12]


def _get(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def search_online(words, limit=6):
    """Poly Haven models whose name / tags / categories have the words: [(id, name, score)], best first."""
    try:
        assets = json.loads(_get(f"{API}/assets?t=models"))
    except (OSError, ValueError):
        return []
    want = [w for w in re.findall(r"[a-z]+", (words or "").lower()) if len(w) > 2]
    if not want:
        return []
    found = []
    for aid, a in assets.items():
        hay = " ".join([aid.replace("_", " "), str(a.get("name") or "")] + list(a.get("tags") or []) + list(a.get("categories") or [])).lower()
        score = sum(2 if re.search(rf"\b{re.escape(w)}", str(a.get("name") or "").lower()) else 1 for w in want if w in hay)
        if score:
            found.append((aid, str(a.get("name") or aid), score))
    found.sort(key=lambda x: -x[2])
    return found[:limit]


def thumb(aid):
    return f"https://cdn.polyhaven.com/asset_img/thumbs/{urllib.parse.quote(aid)}.png?width=256&height=256"


def fetch(aid, root, name=""):
    """The model's glTF (1k textures) and its files into <root>/models/<id>/, when it is small enough; a credit
    line in models/CREDITS.txt. Its path (relative to root), or None."""
    try:
        files = json.loads(_get(f"{API}/files/{urllib.parse.quote(aid)}"))
        g = (files.get("gltf") or {})
        res = g.get("1k") or g.get("2k") or next(iter(g.values()), None)
        main = (res or {}).get("gltf")
    except (OSError, ValueError, StopIteration, AttributeError):
        return None
    if not main or not main.get("url"):
        return None
    inc = main.get("include") or {}
    total = int(main.get("size") or 0) + sum(int(v.get("size") or 0) for v in inc.values())
    if total > MAX_BYTES:
        return None
    dest = Path(root) / "models" / aid
    try:
        dest.mkdir(parents=True, exist_ok=True)
        gl = dest / Path(urllib.parse.urlparse(main["url"]).path).name
        gl.write_bytes(_get(main["url"], 60))
        for rel, v in inc.items():
            if ".." in rel or rel.startswith(("/", "\\")):
                continue
            f = dest / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(_get(v["url"], 60))
        credits = Path(root) / "models" / "CREDITS.txt"
        line = f"{name or aid}: Poly Haven, https://polyhaven.com/a/{aid} (CC0)\n"
        old = credits.read_text(encoding="utf-8") if credits.exists() else ""
        if line not in old:
            credits.write_text(old + line, encoding="utf-8")
    except (OSError, KeyError, ValueError):
        return None
    return gl.relative_to(Path(root)).as_posix()
