"""📦 The optional 3D pack (the user, 2026-11-17: "not in the git repo, 200 MB makes it heavy: an optional 3D pack in the
installer; whoever needs it downloads it"): about 850 free low-poly models from Polyfork (polyfork.dev, CC BY 4.0) in
the kits a website shows (restaurant, hospital, office, lab, university, hotel, city, airport, cars, UI, building
site, nature, farm, stage), one GLB each, in m42/packs/models3d/<kit>/. modelsearch.library() reads it beside the
bundled packs, so a 3D scene can use them; each model a page uses gets its credit line (models/CREDITS.txt and the
page's footer), as CC BY asks.

    python m42/pack3d.py status             is the pack here, how many models
    python m42/pack3d.py install [--yes]    download it from M42 UI's GitHub release (SHA-256 checked) and unpack
    python m42/pack3d.py remove [--yes]     delete it (the app works without it)
  for the maker of a release:
    python m42/pack3d.py build              fetch the models from Polyfork, one by one (resumes; skips the ones here)
    python m42/pack3d.py zip                dist/M42-3D-pack-<v>.zip and its .sha256, for the release "3d-pack"
Only the standard library is used (the installer runs it)."""
import hashlib
import json
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PACK = HERE / "packs" / "models3d"
VERSION = "1"
REPO = "M42TECHY/M42-UI"
TAG = "3d-pack"  # (its own release, apart from the app's: an app update never downloads it again)
ZIP_NAME = "M42-3D-pack.zip"
URL = f"https://github.com/{REPO}/releases/download/{TAG}/{ZIP_NAME}"
CATALOG = "https://raw.githubusercontent.com/lucas-martinic/polyfork-catalog/main/catalog.json"
try:
    from version import VERSION as _APP
except ImportError:
    _APP = "1"
UA = {"User-Agent": f"M42-UI/{_APP} (local website builder; 3D pack)"}
KITS = ["Modern Restaurant Cafe kit", "Hospital kit", "Office", "Research Lab", "University", "Hotel Casino kit",
        "New York City Kit", "Airport", "Retro Cars Kit", "3D UI kit", "Construction Site", "Nature & Forest Kit",
        "Cozy Farm", "Symphony Stagecraft kit"]
MAX_TRIANGLES = 15000  # (a web page's scene: the few heavier ones stay out)
SIZE_MB = 120  # about, for the installer's question


def _snake(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def _get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def status():
    """{"installed": bool, "models": n, "version": v}"""
    meta = PACK / "pack.json"
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    n = sum(1 for _ in PACK.glob("*/*.glb")) if PACK.is_dir() else 0
    return {"installed": bool(n and info), "models": n, "version": info.get("version")}


def credits():
    """{"kit/file.glb": {"name", "url"}} of the pack's models (empty without the pack)."""
    try:
        return json.loads((PACK / "credits.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def credit_line(c):
    return f"{c['name']} by Polyfork ({c['url']}), CC BY 4.0"


# ---------------------------------------------------------------- build (the release maker's PC)
def build(pause=0.6):
    """The pack's models from Polyfork's CDN, one at a time with a pause (their terms: no bulk pulls, a User-Agent
    that names the product, back off on 429). Resumes: a model already here is skipped."""
    cat = json.loads(_get(CATALOG))
    kits = {k["id"]: k["title"] for k in cat["kits"] if k["title"] in KITS}
    missing = set(KITS) - set(kits.values())
    if missing:
        print("Not in Polyfork's catalog any more:", ", ".join(sorted(missing)))
    PACK.mkdir(parents=True, exist_ok=True)
    old = credits()
    out, names = {}, set()
    todo = [a for a in cat["assets"] if a.get("kit") in kits and a.get("type") != "ultra"
            and (a.get("triangles") or 0) <= MAX_TRIANGLES and a.get("glb")]
    print(f"{len(todo)} models in {len(kits)} kits")
    for i, a in enumerate(todo, 1):
        folder = _snake(kits[a["kit"]]).replace("_kit", "") or "kit"
        base = _snake(a["title"]) or a["id"]
        name, n = base, 2
        while f"{folder}/{name}" in names:
            name, n = f"{base}_{n}", n + 1
        names.add(f"{folder}/{name}")
        rel = f"{folder}/{name}.glb"
        dst = PACK / rel
        out[rel] = {"name": a["title"], "url": a["page"], "id": a["id"], "type": a["type"], "triangles": a.get("triangles")}
        if dst.is_file() and dst.stat().st_size and rel in old:
            continue
        for wait in (0, 30, 120, 300):
            if wait:
                print(f"  busy (429): waiting {wait} s")
                time.sleep(wait)
            try:
                data = _get(a["glb"])
                break
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    print(f"  {a['title']}: HTTP {e.code}, skipped")
                    data = None
                    break
            except OSError as e:
                print(f"  {a['title']}: {e}, skipped")
                data = None
                break
        else:
            data = None
        if not data or data[:4] != b"glTF":
            out.pop(rel, None)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        if i % 25 == 0:
            print(f"  {i}/{len(todo)}")
            _write_meta(out)
        time.sleep(pause)
    _write_meta(out)
    st = status()
    print(f"Done: {st['models']} models in {PACK}")
    return st


def _write_meta(out):
    (PACK / "credits.json").write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    (PACK / "pack.json").write_text(json.dumps({"version": VERSION, "models": len(out), "source": "https://polyfork.dev",
                                                "kits": KITS}, indent=1), encoding="utf-8")
    lines = "\n".join(credit_line(c) for c in out.values())
    (PACK / "LICENSE.txt").write_text(
        "M42 UI 3D pack: free low-poly models by Polyfork (https://polyfork.dev), under CC BY 4.0\n"
        "(https://creativecommons.org/licenses/by/4.0/). The models are unchanged. Polyfork's name and logo are not\n"
        "licensed; Polyfork does not endorse M42 UI. Each model, with its credit line:\n\n" + lines + "\n", encoding="utf-8")


def make_zip():
    st = status()
    if not st["installed"]:
        raise SystemExit("No pack here: run build first.")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    z = dist / ZIP_NAME
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in sorted(PACK.rglob("*")):
            if p.is_file():
                f.write(p, p.relative_to(PACK).as_posix())
    digest = hashlib.sha256(z.read_bytes()).hexdigest()
    (dist / (ZIP_NAME + ".sha256")).write_text(f"{digest}  {ZIP_NAME}\n", encoding="utf-8")
    print(f"{z} ({z.stat().st_size / 2 ** 20:.0f} MB), sha256 {digest}\n"
          f"GitHub: Releases > Draft a new release > tag '{TAG}' > attach {ZIP_NAME} and {ZIP_NAME}.sha256 > Publish.")
    return z


# ---------------------------------------------------------------- install (the user's PC)
def install(progress=None, url=URL):
    """Download the pack's zip, check its SHA-256, unpack into m42/packs/models3d (the old one replaced only when the
    new one is good)."""
    work = Path(tempfile.mkdtemp(prefix="m42-3d-"))
    try:
        expect = _get(url + ".sha256", 30).decode("utf-8", "replace").split()[0].lower()
        zpath = work / ZIP_NAME
        req = urllib.request.Request(url, headers=UA)
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
            total, done = int(r.headers.get("Content-Length") or 0), 0
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        if h.hexdigest() != expect:
            raise RuntimeError("The 3D pack's SHA-256 does not match: nothing was changed.")
        new = work / "pack"
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():
                if n.startswith(("/", "\\")) or ".." in Path(n).parts:
                    raise RuntimeError("The 3D pack's zip has an unsafe path: nothing was changed.")
            z.extractall(new)
        if not (new / "pack.json").is_file() or not (new / "credits.json").is_file():
            raise RuntimeError("This is not M42 UI's 3D pack: nothing was changed.")
        if PACK.exists():
            shutil.rmtree(PACK)
        PACK.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(new), str(PACK))
        return status()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def remove():
    if PACK.exists():
        shutil.rmtree(PACK)
    return status()


def _bar(done, total):
    pct = int(done * 100 / total) if total else 0
    sys.stdout.write(f"\r  [{'#' * (pct // 4)}{'-' * (25 - pct // 4)}] {pct:3d}%  {done / 2 ** 20:.0f} of {total / 2 ** 20:.0f} MB")
    sys.stdout.flush()


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    cmd = argv[0] if argv else "status"
    yes = "--yes" in argv
    if cmd == "status":
        st = status()
        print(f"3D pack: {st['models']} models (version {st['version']})" if st["installed"] else "3D pack: not installed")
    elif cmd == "build":
        build()
    elif cmd == "zip":
        make_zip()
    elif cmd == "install":
        if not yes and input(f"Download the 3D pack (about {SIZE_MB} MB, ~850 free models, CC BY 4.0)? [Y/n] ").strip().lower() in ("n", "no"):
            return 0
        try:
            st = install(_bar)
        except (OSError, RuntimeError) as e:
            print(f"\nThe 3D pack did not install: {e}")
            return 1
        print(f"\n3D pack ready: {st['models']} models.")
    elif cmd == "remove":
        if yes or input("Delete the 3D pack? [y/N] ").strip().lower() in ("y", "yes"):
            remove()
            print("3D pack deleted.")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
