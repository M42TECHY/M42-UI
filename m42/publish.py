"""📦 Publish from this PC with git alone (the user, 2026-11-18: "I can't log in to GitHub and change tags for every
update: do it from here"). It sets the version, commits, pushes a tag, and GitHub Actions does the rest
(.github/workflows/release.yml, 3d-pack.yml); then it waits for the release and checks its files.

    python m42/publish.py app 1.0.1 --notes "Faster builds; the 3D scenes use the 3D pack"
    python m42/publish.py 3d-pack --notes "Two more kits"
    python m42/publish.py status          the version here, the latest release, the 3D pack release

For the maintainer (it needs a clean main branch that can be pushed); users never run it."""
import argparse
import calendar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "M42TECHY/M42-UI"
API = f"https://api.github.com/repos/{REPO}"
VERSION_FILE = ROOT / "m42" / "version.py"
PACK_FILE = ROOT / "m42" / "pack3d.py"
TESTS = ["test_updater.py", "test_pack3d.py"]


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stderr or r.stdout}")
    return r.stdout.strip()


def api(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "M42-UI publish", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code}
    except OSError as e:
        return {"error": str(e)}


def parse(v):
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(v).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def current_version():
    return re.search(r'^VERSION = "([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"), re.M).group(1)


def pack_version():
    return re.search(r'^VERSION = "([^"]+)"', PACK_FILE.read_text(encoding="utf-8"), re.M).group(1)


def set_value(path, value):
    raw = path.read_bytes()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    text = raw.decode("utf-8")
    new = re.sub(r'^VERSION = "[^"]+"', f'VERSION = "{value}"', text, count=1, flags=re.M)
    path.write_bytes(new.replace("\r\n", "\n").replace("\n", nl.decode()).encode("utf-8"))


def ready(own):
    """On main, `own` (the file this step changes) not changed by hand, main up to date: else a clear stop. Other
    files not committed yet are only named: a release is made from the commits alone, so they are not in it."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise SystemExit(f"On branch {branch}: publish from main.")
    dirty = git("status", "--porcelain")
    rel = own.relative_to(ROOT).as_posix()
    if any(line[3:].strip() == rel for line in dirty.splitlines()):
        raise SystemExit(f"{rel} has changes not committed yet: commit them first.")
    if dirty:
        print("Not committed yet, so NOT in this release:\n" + dirty)
    git("fetch", "--tags", "origin")
    behind = git("rev-list", "--count", "HEAD..origin/main")
    if behind != "0":
        raise SystemExit(f"origin/main has {behind} commit(s) this PC has not: pull first.")


def run_tests():
    for t in TESTS:
        r = subprocess.run([sys.executable, str(ROOT / "m42" / "tests" / t)], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        print(f"  {t}: {'ok' if r.returncode == 0 else 'FAILED'}")
        if r.returncode:
            raise SystemExit((r.stdout or "")[-1500:] + (r.stderr or "")[-800:])


def wait_for(tag, files, since=0.0, minutes=10):
    """The release `tag` with all `files` on it (uploaded after `since`, a time.time()): its URL, or None."""
    end = time.time() + minutes * 60
    while time.time() < end:
        rel = api(f"/releases/tags/{tag}")
        if not rel.get("error"):
            have = {a["name"]: a for a in rel.get("assets") or []}
            fresh = all(n in have and have[n].get("state") == "uploaded" and
                        calendar.timegm(time.strptime(have[n]["updated_at"], "%Y-%m-%dT%H:%M:%SZ")) >= since - 120
                        for n in files)
            if fresh:
                return rel.get("html_url")
        time.sleep(20)
        print("  ...waiting for GitHub Actions", flush=True)
    return None


def publish_app(version, notes):
    want, have = parse(version), parse(current_version())
    if not want:
        raise SystemExit(f"Not a version: {version} (like 1.0.1)")
    latest = api("/releases/latest")
    last = parse(latest.get("tag_name", "")) if not latest.get("error") else None
    if last and want <= last:
        raise SystemExit(f"{version} is not newer than the latest release ({'.'.join(map(str, last))}).")
    if have and want < have:
        raise SystemExit(f"{version} is older than this folder's version ({'.'.join(map(str, have))}).")
    version = ".".join(map(str, want))
    tag = f"v{version}"
    if git("tag", "-l", tag):
        raise SystemExit(f"The tag {tag} is already here: it was published (or tried) before.")
    ready(VERSION_FILE)
    print("Tests:")
    run_tests()
    if want != have:  # (a version already set and committed, as 1.0.2 was: released as it is)
        set_value(VERSION_FILE, version)
        git("add", str(VERSION_FILE))
        git("commit", "-m", f"Version {version}\n\n{notes}".strip() + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git("tag", "-a", tag, "-m", notes or f"M42 UI {version}")
    start = time.time()
    git("push", "origin", "main")
    git("push", "origin", tag)
    print(f"Pushed {tag}: GitHub Actions is making the release.")
    url = wait_for(tag, [f"M42-UI-{version}.zip", f"M42-UI-{version}.zip.sha256"], start, 10)
    latest = api("/releases/latest").get("tag_name")
    if not url:
        raise SystemExit(f"No release yet after 10 minutes: see https://github.com/{REPO}/actions")
    print(f"Released: {url}\nLatest on GitHub: {latest}" + ("" if latest == tag else "  (NOT this one: check it)"))


def publish_pack(notes):
    ready(PACK_FILE)
    new = str(int(pack_version()) + 1)
    set_value(PACK_FILE, new)
    git("add", str(PACK_FILE))
    git("commit", "-m", f"3D pack {new}\n\n{notes}".strip() + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    tag = f"3d-pack-v{new}"
    git("tag", "-a", tag, "-m", notes or f"3D pack {new}")
    start = time.time()
    git("push", "origin", "main")
    git("push", "origin", tag)
    print(f"Pushed {tag}: GitHub Actions builds the pack from Polyfork (about 20-30 minutes).\n"
          "Apps get it after their next app update (publish an app version with this commit in it).")
    url = wait_for("3d-pack", ["M42-3D-pack.zip", "M42-3D-pack.zip.sha256"], start, 60)
    print(f"3D pack {new} is on {url}" if url else f"Not there yet: see https://github.com/{REPO}/actions")


def show_status():
    latest = api("/releases/latest")
    pack = api("/releases/tags/3d-pack")
    print(f"This folder: M42 UI {current_version()}, 3D pack {pack_version()}")
    print(f"Latest release: {latest.get('tag_name') or latest.get('error')}")
    if not pack.get("error"):
        print("3D pack release: " + ", ".join(f"{a['name']} ({a['size'] >> 20} MB, {a['updated_at']})" for a in pack.get("assets") or []))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    a = sub.add_parser("app")
    a.add_argument("version")
    a.add_argument("--notes", default="")
    p = sub.add_parser("3d-pack")
    p.add_argument("--notes", default="")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.what == "app":
        publish_app(args.version, args.notes)
    elif args.what == "3d-pack":
        publish_pack(args.notes)
    else:
        show_status()


if __name__ == "__main__":
    main()
