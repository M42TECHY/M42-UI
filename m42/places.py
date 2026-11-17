"""📦 Where M42 UI keeps its models (the user, 2026-11-17: "a ZIP from GitHub sits in Downloads on C:; its models must
not fill C: — say first how much space they need, ask where to put them, and never start when that drive is short").

The folder is chosen once on a PC and kept in two places: the app's own config.json (it moves with the app folder) and
the user's own settings (%APPDATA%\\M42\\settings.json, ~/.m42/settings.json: a second copy of the app, unzipped
elsewhere, finds the models already there and asks nothing). With none chosen, the app folder's models/ is used, so a
PC that already has its models there is never asked. M42_MODELS_DIR (the environment) wins over both (tests)."""
import json
import os
import platform
import shutil
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.json"
DEFAULT = ROOT / "models"
GB = 2 ** 30
MARGIN = 1.5 * GB  # room beyond the files themselves (a download's .part, unpacking a runner, the OS's own needs)


def user_settings():
    base = os.environ.get("APPDATA") if os.name == "nt" else None
    return Path(base) / "M42" / "settings.json" if base else Path.home() / ".m42" / "settings.json"


def _read(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(p, key, value):
    p = Path(p)
    d = _read(p)
    d[key] = value
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
        return True
    except OSError:
        return False


def saved():
    """The models folder chosen on this PC ("" when none): the app's config first, then the user's settings."""
    env = os.environ.get("M42_MODELS_DIR")
    if env:
        return env
    for src in (CONFIG, user_settings()):
        v = str(_read(src).get("models_dir") or "").strip()
        if v:
            return v
    return ""


def models_dir():
    p = saved()
    return Path(p) if p else DEFAULT


def has_models(folder):
    """A folder that already holds a chat model of M42's (any .gguf of its tiers)."""
    f = Path(folder)
    return f.is_dir() and any(f.glob("Qwen3.5-*-Q4_K_M.gguf"))


def chosen():
    """True when a folder was chosen on this PC, or the app folder's models/ already has a model (an old install:
    never asked)."""
    return bool(saved()) or has_models(DEFAULT)


def save(folder):
    """The folder kept in the app's config and in the user's settings; every module told (no restart)."""
    folder = str(Path(folder).expanduser().resolve())
    _write(CONFIG, "models_dir", folder)
    _write(user_settings(), "models_dir", folder)
    apply()
    return folder


def apply():
    """Every module that keeps the models folder points at the chosen one."""
    import sys
    d = models_dir()
    for name, attr in (("firstrun", "MODELS"), ("llamacpp", "MODELS_DIR"), ("speech", "MODELS")):
        mod = sys.modules.get(name)
        if mod is not None:
            setattr(mod, attr, d)
    mod = sys.modules.get("speech")
    if mod is not None and hasattr(mod, "use_models"):
        mod.use_models(d)
    mod = sys.modules.get("llamacpp")
    if mod is not None and not os.environ.get("M42_MODELS_FILE"):
        mod.CUSTOM_FILE = d / "m42-models.json"


def free_bytes(folder):
    """Free space where `folder` is (its nearest existing parent), or 0."""
    p = Path(folder)
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return 0


def drives():
    """[{"path", "label", "free_gb", "total_gb", "app"}]: the PC's disks with their free space (the app's own first)."""
    roots = []
    if os.name == "nt":
        roots = [f"{L}:\\" for L in string.ascii_uppercase if os.path.exists(f"{L}:\\")]
    else:
        roots = ["/", str(Path.home())]
        for base in (["/Volumes"] if platform.system() == "Darwin" else ["/media", "/mnt", f"/media/{os.environ.get('USER', '')}"]):
            try:
                roots += [str(p) for p in Path(base).iterdir() if p.is_dir()]
            except OSError:
                pass
    app_anchor = Path(ROOT.anchor or "/")
    out, seen = [], set()
    for r in roots:
        try:
            u = shutil.disk_usage(r)
        except OSError:
            continue
        key = (u.total, u.free) if os.name != "nt" else r
        if key in seen or u.total < GB:
            continue
        seen.add(key)
        out.append({"path": r, "folder": folder_on(r), "label": r.rstrip("\\") if os.name == "nt" else r, "free_gb": round(u.free / GB, 1),
                    "total_gb": round(u.total / GB, 1), "app": Path(r).anchor == app_anchor.anchor if os.name == "nt"
                    else str(ROOT).startswith(r.rstrip("/") + "/") and r != "/"})
    out.sort(key=lambda d: (not d["app"], -d["free_gb"]))
    return out


def folder_on(drive_path):
    """The models folder M42 suggests on a drive: the app folder's own models/ on its drive, else <drive>/M42-models."""
    if os.name == "nt" and Path(drive_path).anchor.lower() == ROOT.anchor.lower():
        return str(DEFAULT)
    if os.name != "nt" and str(ROOT).startswith(str(drive_path).rstrip("/") + "/") and drive_path not in ("/",):
        return str(DEFAULT)
    return str(Path(drive_path) / "M42-models")


def suggest(need):
    """The folder M42 suggests for `need` bytes: the app folder's models/ when its drive has the room (with the margin),
    else the drive with the most room. (folder, enough)"""
    if free_bytes(DEFAULT) >= need + MARGIN:
        return str(DEFAULT), True
    best = max(drives(), key=lambda d: d["free_gb"], default=None)
    if best and best["free_gb"] * GB >= need + MARGIN:
        return folder_on(best["path"]), True
    return str(DEFAULT), False


def check(folder, need):
    """"" when `folder` can take `need` bytes (made, writable, room with the margin), else why not, in words."""
    p = Path(str(folder or "")).expanduser()
    if not str(folder or "").strip() or not p.is_absolute():
        return "Choose a full folder path (for example D:\\M42-models)."
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".m42-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return f"M42 cannot write in {p} ({e.strerror or e})."
    have = free_bytes(p)
    if have < need + MARGIN:
        return (f"Not enough space on {p.anchor or p}: {have / GB:.1f} GB free, {(need + MARGIN) / GB:.1f} GB needed "
                f"({need / GB:.1f} GB of files + {MARGIN / GB:.1f} GB room). Choose another drive.")
    return ""
