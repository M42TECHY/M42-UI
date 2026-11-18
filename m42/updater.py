"""Updates for M42 UI from its GitHub Releases, the same on Windows, macOS and Linux (plain Python, no git needed).

    check()     the latest release on GitHub (read at most every 6 hours; only its public version info is fetched,
                nothing about this PC is sent)
    apply()     download it, check its SHA-256, back up the files it replaces, put the new app files in place and
                keep everything that is the user's (models, chats, projects, settings, .venv, the launchers the
                installer made); new Python packages when requirements.txt changed
    rollback()  put the last backup back (the version before the update)

The app shows "Update available" when a newer release is there (app.py: /api/update), and update.bat / update.sh /
update.command run the same from a terminal (for when the app itself will not open):

    python m42/updater.py check | apply [--yes] | rollback [--yes]

A release on GitHub: the tag is the version with a "v" (v1.2.0, the same number as version.py), and its assets are
M42-UI-1.2.0.zip and M42-UI-1.2.0.zip.sha256, made by release.py. Without those assets the tag's source zip from
GitHub is used (checked to be M42 UI of that version, but with no SHA-256 to compare)."""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the M42-UI folder
APP = ROOT / "m42"
sys.path.insert(0, str(APP))
from version import VERSION  # noqa: E402

REPO = "M42TECHY/M42-UI"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
HEADERS = {"User-Agent": "M42-UI-updater", "Accept": "application/vnd.github+json"}
CHECK_EVERY = 6 * 3600
KEEP_BACKUPS = 2

# never replaced or removed by an update: what the user, the installer and the first run made on this PC
KEEP_DIRS = ("models", "llama.cpp", "whisper.cpp", "knowledge", "workspace", "projects", ".venv", ".git", ".claude",
             "benchmark", "m42/cache", "m42/sessions", "m42/memory", "m42/logs", "m42/projects", "m42/plugins",
             "m42/backups", "m42/packs")
KEEP_FILES = ("m42/config.json", "m42/.release-files.json", "Start M42 UI.sh", "Start M42 UI.command")


def _paths():
    """The places this module writes to (from ROOT, so a test can point ROOT at a copy)."""
    app = ROOT / "m42"
    return {"cache": app / "cache" / "update.json", "work": app / "cache" / "update", "backups": app / "backups",
            "manifest": app / ".release-files.json"}


class UpdateError(Exception):
    pass


# ---------------------------------------------------------------- versions

def parse(v):
    """'v1.2.3' -> (1, 2, 3, 1); a pre-release ('1.3.0-beta') sorts before its release: (1, 3, 0, 0)."""
    m = re.match(r"\s*v?(\d+)\.(\d+)(?:\.(\d+))?(.*)$", str(v or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), 0 if m.group(4).strip() else 1


def newer(latest, current=None):
    a, b = parse(latest), parse(current or VERSION)
    return bool(a and b and a > b)


def is_kept(rel):
    rel = rel.replace("\\", "/").lstrip("/")
    if rel in KEEP_FILES or "__pycache__" in rel.split("/") or re.match(r"m42/\.running-.*\.json$", rel):
        return True
    return any(rel == d or rel.startswith(d + "/") for d in KEEP_DIRS)


def git_checkout():
    """A developer's folder (git clone): updated with git pull, never by replacing files."""
    return (ROOT / ".git").exists()


# ---------------------------------------------------------------- check

def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _summary(rel):
    tag = rel.get("tag_name") or ""
    ver = tag.lstrip("vV")
    assets = {a.get("name"): a for a in rel.get("assets") or []}
    zip_name = next((n for n in assets if n and n.startswith("M42-UI") and n.endswith(".zip")), None)
    if zip_name:
        z = assets[zip_name]
        sha = assets.get(zip_name + ".sha256")
        download = {"url": z.get("browser_download_url"), "size": z.get("size"), "name": zip_name,
                    "sha_url": sha.get("browser_download_url") if sha else None}
    else:
        download = {"url": rel.get("zipball_url"), "size": None, "name": f"M42-UI-{ver}.zip", "sha_url": None}
    return {"version": ver, "tag": tag, "name": rel.get("name") or tag, "notes": (rel.get("body") or "")[:4000],
            "url": rel.get("html_url"), "published": rel.get("published_at"), "download": download}


def check(force=False, timeout=15):
    """{"current", "latest", "available", "notes", "url", "git", "error"}; the release read at most every 6 hours."""
    p = _paths()
    out = {"current": VERSION, "latest": None, "available": False, "git": git_checkout(), "error": None}
    cached = None
    try:
        cached = json.loads(p["cache"].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if cached and not force and time.time() - cached.get("at", 0) < CHECK_EVERY and cached.get("release"):
        rel = cached["release"]
    else:
        try:
            rel = _summary(json.loads(_get(API, timeout)))
        except urllib.error.HTTPError as e:
            out["error"] = ("No release on GitHub yet (or the repository is private)." if e.code == 404
                            else f"GitHub answered {e.code}.")
            return out
        except (urllib.error.URLError, OSError, ValueError) as e:
            out["error"] = f"Could not reach GitHub: {getattr(e, 'reason', e)}"
            return out
        try:
            p["cache"].parent.mkdir(parents=True, exist_ok=True)
            p["cache"].write_text(json.dumps({"at": time.time(), "release": rel}), encoding="utf-8")
        except OSError:
            pass
    out.update(latest=rel["version"], available=newer(rel["version"]), notes=rel["notes"], url=rel["url"],
               name=rel["name"], published=rel["published"], release=rel)
    return out


# ---------------------------------------------------------------- download

def _download(url, dest, size=None, progress=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
        total = size or int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress("downloading", done, total)
    os.replace(part, dest)
    return dest


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- apply

def _members(z):
    """{relative path: ZipInfo} of the files in a release zip, its top folder (M42-UI-1.2.0/) taken off."""
    files = [i for i in z.infolist() if not i.is_dir()]
    tops = {i.filename.split("/", 1)[0] for i in files}
    strip = len(tops) == 1 and all("/" in i.filename for i in files)
    out = {}
    for i in files:
        rel = i.filename.split("/", 1)[1] if strip else i.filename
        rel = rel.replace("\\", "/")
        if not rel or rel.startswith("/") or ".." in rel.split("/") or re.match(r"^[A-Za-z]:", rel):
            raise UpdateError(f"The update has an unsafe path in it: {i.filename}")
        out[rel] = i
    return out


def _zip_version(z, members):
    text = z.read(members["m42/version.py"]).decode("utf-8", "replace")
    m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else None


def _python():
    """The Python of this install for pip (python.exe next to pythonw.exe on Windows: pip wants a console one)."""
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
        return str(exe.parent / "python.exe")
    return str(exe)


def _requirements():
    """requirements.txt as its lines (CRLF or LF alike, blank lines and comments left out)."""
    f = ROOT / "requirements.txt"
    if not f.is_file():
        return []
    lines = (ln.split("#", 1)[0].strip() for ln in f.read_text(encoding="utf-8", errors="replace").splitlines())
    return [ln for ln in lines if ln]


def _make_executable(path, mode):
    if os.name == "nt":
        return
    if mode:
        os.chmod(path, mode)
    if path.suffix in (".sh", ".command"):
        os.chmod(path, path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def apply_zip(zip_path, expect=None, verified=False, progress=None, pip=True):
    """Put the release in `zip_path` in place of this app's files. Returns what was done."""
    p = _paths()
    if git_checkout():
        raise UpdateError("This folder is a git checkout: update it with git pull, not with the updater.")
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise UpdateError("The download is not a valid zip file.")
    with z:
        members = _members(z)
        for need in ("m42/app.py", "m42/version.py", "m42/updater.py"):
            if need not in members:
                raise UpdateError(f"This is not an M42 UI release ({need} is missing).")
        new_ver = _zip_version(z, members)
        if expect and parse(new_ver) != parse(expect):
            raise UpdateError(f"The release says {expect}, but its files are version {new_ver}.")
        new_files = {rel for rel in members if not is_kept(rel)}
        try:
            old_files = set(json.loads(p["manifest"].read_text(encoding="utf-8")))
        except (OSError, ValueError):
            old_files = set()  # (the first update of a ZIP download: nothing is removed, only replaced and added)
        stale = {rel for rel in old_files - new_files if not is_kept(rel) and (ROOT / rel).is_file()}

        # the backup: every file this update replaces or removes, and the list of the files it adds
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = p["backups"] / f"{VERSION}-{stamp}"
        replaced, added = [], []
        for rel in sorted(new_files | stale):
            src = ROOT / rel
            if src.is_file():
                dst = backup / "files" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                replaced.append(rel)
            else:
                added.append(rel)
        backup.mkdir(parents=True, exist_ok=True)
        if p["manifest"].is_file():
            shutil.copy2(p["manifest"], backup / "release-files.json")
        (backup / "backup.json").write_text(json.dumps(
            {"from": VERSION, "to": new_ver, "at": stamp, "replaced": replaced, "added": added,
             "removed": sorted(stale)}, indent=1), encoding="utf-8")

        req_before = _requirements()
        if progress:
            progress("installing", 0, len(new_files))
        for n, rel in enumerate(sorted(new_files), 1):
            info, dest = members[rel], ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".m42new")
            with z.open(info) as src, open(tmp, "wb") as out:
                shutil.copyfileobj(src, out)
            os.replace(tmp, dest)
            _make_executable(dest, (info.external_attr >> 16) & 0o777)
            if progress and n % 50 == 0:
                progress("installing", n, len(new_files))
    for rel in stale:
        (ROOT / rel).unlink(missing_ok=True)
    p["manifest"].write_text(json.dumps(sorted(new_files), indent=0), encoding="utf-8")
    _prune_backups()
    p["cache"].unlink(missing_ok=True)

    packages = "same"
    req_after = _requirements()
    if pip and req_after and req_after != req_before:
        if progress:
            progress("packages", 0, 0)
        r = subprocess.run([_python(), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                           cwd=ROOT, capture_output=True, text=True)
        packages = "updated" if r.returncode == 0 else "error: " + (r.stderr or r.stdout)[-600:]
    pack = _refresh_3d_pack(progress) if pip else "skipped"
    return {"state": "done", "from": VERSION, "to": new_ver, "verified": verified, "backup": str(backup),
            "replaced": len(replaced), "added": len(added), "removed": len(stale), "packages": packages,
            "pack3d": pack}


def _refresh_3d_pack(progress=None):
    """📦 The optional 3D pack follows the app (the user, 2026-11-18: "the 3D pack must update by itself too"): when it
    is installed and the new release's pack3d.py wants a newer pack, the new pack3d.py downloads it (its own process:
    this one still has the old code loaded). "none" when it is not installed, "current", "updated" or "error: ..."."""
    script = ROOT / "m42" / "pack3d.py"
    if not script.is_file():
        return "none"
    if progress:
        progress("3d pack", 0, 0)
    r = subprocess.run([_python(), str(script), "refresh"], cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout or "").strip().splitlines()
    return (out[-1] if out else "current") if r.returncode == 0 else "error: " + (r.stderr or r.stdout)[-300:]


def apply(info=None, progress=None, pip=True):
    """Download the latest release and put it in place. `info`: a check() result (read again when missing)."""
    if git_checkout():
        raise UpdateError("This folder is a git checkout: update it with git pull, not with the updater.")
    info = info if info and info.get("release") else check(force=True)
    if info.get("error"):
        raise UpdateError(info["error"])
    if not info.get("available"):
        return {"state": "current", "version": VERSION}
    rel = info["release"]
    d = rel["download"]
    work = _paths()["work"]
    shutil.rmtree(work, ignore_errors=True)
    zip_path = _download(d["url"], work / d["name"], d.get("size"), progress)
    verified = False
    if d.get("sha_url"):
        want = re.search(r"[0-9a-fA-F]{64}", _get(d["sha_url"]).decode("utf-8", "replace"))
        if not want or want.group(0).lower() != sha256(zip_path):
            raise UpdateError("The download's SHA-256 does not match the release's: nothing was changed.")
        verified = True
    try:
        return apply_zip(zip_path, rel["version"], verified, progress, pip)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _backups():
    b = _paths()["backups"]
    return sorted((d for d in b.iterdir() if (d / "backup.json").is_file()), key=lambda d: d.name) if b.is_dir() else []


def _prune_backups():
    for d in _backups()[:-KEEP_BACKUPS]:
        shutil.rmtree(d, ignore_errors=True)


def rollback():
    """The last update undone: its replaced and removed files back, the files it added taken away."""
    found = _backups()
    if not found:
        raise UpdateError("There is no backup to go back to.")
    backup = found[-1]
    info = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
    for rel in info.get("added", []):
        if not is_kept(rel):
            (ROOT / rel).unlink(missing_ok=True)
    for rel in info.get("replaced", []):
        src, dest = backup / "files" / rel, ROOT / rel
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    man = _paths()["manifest"]
    if (backup / "release-files.json").is_file():
        shutil.copy2(backup / "release-files.json", man)
    else:
        man.unlink(missing_ok=True)
    shutil.rmtree(backup, ignore_errors=True)
    _paths()["cache"].unlink(missing_ok=True)
    return {"state": "rolled_back", "to": info.get("from"), "from": info.get("to")}


# ---------------------------------------------------------------- in the app: a background job and a restart

STATE = {"state": "idle"}
LATEST = {}  # the last check() in this run of the app
_lock = threading.Lock()


def status():
    return dict(STATE)


def check_in_background(force=False):
    """check() without making the app wait (at its start, and the Settings "Check now" button)."""
    def run():
        LATEST.clear()
        LATEST.update(check(force=force))
    threading.Thread(target=run, daemon=True).start()


def for_ui():
    """What the window shows: this version, the latest release, its notes, and the update job when one runs."""
    out = {k: LATEST.get(k) for k in ("latest", "available", "notes", "url", "name", "error")}
    out.update(current=VERSION, git=git_checkout(), checked=bool(LATEST), job=status())
    return out


def start_apply(info=None):
    """apply() in the background; status() tells the window how far it is."""
    with _lock:
        if STATE.get("state") in ("downloading", "installing", "packages"):
            return False
        STATE.clear()
        STATE.update(state="downloading", done=0, total=0)

    def progress(step, done, total):
        STATE.update(state=step, done=done, total=total)

    def run():
        try:
            STATE.clear()
            STATE.update(apply(info, progress))
        except Exception as e:  # (any failure: the user sees why; the backup is there if files were changed)
            STATE.clear()
            STATE.update(state="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return True


def restart(argv=None):
    """Start the app again once this process has ended (a small helper waits for it, then starts it)."""
    argv = list(argv if argv is not None else sys.argv)
    cmd = [sys.executable, str(Path(__file__).resolve()), "relaunch", str(os.getpid()), "--", *argv]
    kw = {"cwd": str(ROOT), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen(cmd, **kw)


def _alive(pid):
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        if os.name == "nt":
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def relaunch(pid, argv):
    end = time.time() + 60
    while _alive(pid) and time.time() < end:
        time.sleep(0.5)
    time.sleep(1)  # (the port is free a moment after the process ends)
    kw = {"cwd": str(ROOT)}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, *argv], **kw)


def app_running():
    """True when an M42 UI window is open now (its .running-<port>.json and its process)."""
    for f in (ROOT / "m42").glob(".running-*.json"):
        try:
            pid = json.loads(f.read_text(encoding="utf-8")).get("pid")
        except (OSError, ValueError):
            continue
        if pid and _alive(int(pid)):
            return True
    return False


# ---------------------------------------------------------------- command line (update.bat / .sh / .command)

def _ask(q, yes):
    if yes:
        return True
    try:
        return input(f"{q} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _cli_progress(step, done, total):
    if step == "downloading" and total:
        print(f"\r  downloading {done * 100 // total}% ({done >> 20} of {total >> 20} MB)", end="", flush=True)
    elif step == "packages":
        print("\n  new Python packages (requirements.txt changed) ...", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Update M42 UI from its GitHub releases")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    a = sub.add_parser("apply")
    a.add_argument("--yes", action="store_true")
    a.add_argument("--force", action="store_true", help="even while the app is open")
    r = sub.add_parser("rollback")
    r.add_argument("--yes", action="store_true")
    rl = sub.add_parser("relaunch")
    rl.add_argument("pid", type=int)
    rl.add_argument("rest", nargs=argparse.REMAINDER)
    sub.add_parser("version")
    args = ap.parse_args(argv)

    if args.cmd == "relaunch":
        rest = args.rest[1:] if args.rest[:1] == ["--"] else args.rest
        relaunch(args.pid, rest)
        return 0
    if args.cmd == "version":
        print(VERSION)
        return 0
    try:
        if args.cmd == "rollback":
            b = _backups()
            if not b:
                print("There is no backup to go back to.")
                return 1
            info = json.loads((b[-1] / "backup.json").read_text(encoding="utf-8"))
            if not _ask(f"Go back from M42 UI {info.get('to')} to {info.get('from')}?", args.yes):
                return 1
            out = rollback()
            print(f"Done: M42 UI is {out['to']} again.")
            return 0
        print(f"M42 UI {VERSION}. Looking for a newer release on GitHub ...")
        info = check(force=True)
        if info.get("error"):
            print(info["error"])
            return 1
        if not info["available"]:
            print(f"You have the latest version ({VERSION}).")
            return 0
        print(f"\nNew: M42 UI {info['latest']}  ({info['url']})")
        if info.get("notes"):
            print("\n" + info["notes"][:1500] + "\n")
        if args.cmd != "apply":
            print("Run the updater (update.bat / update.sh / update.command) to install it.")
            return 0
        if info["git"]:
            print("This folder is a git checkout: update it with  git pull")
            return 1
        if app_running() and not args.force:
            print("M42 UI is open: close its window first, then run this again.")
            return 1
        if not _ask(f"Update M42 UI {VERSION} -> {info['latest']}? Your models, chats, projects and settings stay.",
                    args.yes):
            return 1
        out = apply(info, _cli_progress)
        print(f"\nDone: M42 UI {out['to']}" + ("" if out["verified"] else " (no SHA-256 in that release to check)"))
        if out["packages"].startswith("error"):
            print("The new Python packages did not install:", out["packages"][6:])
            print("Run the installer again (install.bat / install.sh / install.command) to finish them.")
        print("The version before is kept: go back with  python m42/updater.py rollback")
        return 0
    except UpdateError as e:
        print(f"\nThe update stopped: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
