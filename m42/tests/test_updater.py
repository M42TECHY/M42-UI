"""Updates (updater.py), with no internet: a copy of an install in a temp folder is updated from a release zip
(file:// stands in for GitHub). The new files go in, the user's files stay (settings, models, workspace, the launcher
the installer made), a file the old release had and the new one has not is removed, its SHA-256 is checked, an unsafe
or wrong-version zip is refused, a git checkout is never touched, and rollback puts the version before back."""
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import updater  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def release_zip(path, version, files, top=True):
    with zipfile.ZipFile(path, "w") as z:
        for rel, text in files.items():
            info = zipfile.ZipInfo((f"M42-UI-{version}/" if top else "") + rel)
            info.external_attr = (0o100755 if rel.endswith((".sh", ".command")) else 0o100644) << 16
            z.writestr(info, text)
    return path


# ---- versions
check("v1.2.0 is newer than 1.1.9", updater.newer("v1.2.0", "1.1.9"))
check("1.0.0 is not newer than 1.0.0", not updater.newer("1.0.0", "1.0.0"))
check("a pre-release sorts before its release", updater.parse("1.3.0-beta") < updater.parse("1.3.0"))
check("not a version: never newer", not updater.newer("latest", "1.0.0"))
check("the user's files are kept", all(updater.is_kept(p) for p in (
    "m42/config.json", "models/a.gguf", "workspace/x/index.html", ".venv/bin/python", "m42/sessions/1.json",
    "Start M42 UI.sh", "m42/.running-8765.json", "m42/__pycache__/app.cpython-312.pyc")))
check("the app's files are replaced", not any(updater.is_kept(p) for p in (
    "m42/app.py", "m42/ui/app.js", "install.sh", "README.md", "update.command")))

# ---- an install in a temp folder
real_root, real_version = updater.ROOT, updater.VERSION
tmp = Path(tempfile.mkdtemp())
root = tmp / "M42-UI"
updater.ROOT, updater.VERSION = root, "0.9.0"
old = {"m42/app.py": "old app", "m42/version.py": 'VERSION = "0.9.0"\n', "m42/updater.py": "old updater",
       "m42/old_only.py": "gone in 1.0.0", "install.sh": "old installer", "requirements.txt": "pillow\n"}
for rel, text in old.items():
    write(root, rel, text)
mine = {"m42/config.json": '{"model": "mine"}', "models/model.gguf": "weights", "workspace/site/index.html": "my page",
        "Start M42 UI.sh": "my launcher", ".venv/marker": "venv"}
for rel, text in mine.items():
    write(root, rel, text)
write(root, "m42/.release-files.json", json.dumps(sorted(old)))

new = {"m42/app.py": "new app", "m42/version.py": 'VERSION = "1.0.0"\n', "m42/updater.py": "new updater",
       "m42/new_file.py": "added in 1.0.0", "install.sh": "new installer", "update.command": "#!/bin/sh\n",
       "requirements.txt": "pillow\n", "m42/config.json": '{"model": "release default"}',
       "models/other.gguf": "not from a release"}
zip_path = release_zip(tmp / "M42-UI-1.0.0.zip", "1.0.0", new)
digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
(tmp / "M42-UI-1.0.0.zip.sha256").write_text(f"{digest}  M42-UI-1.0.0.zip\n", encoding="utf-8")

# a GitHub answer, read from the cache (no internet)
rel = updater._summary({"tag_name": "v1.0.0", "name": "M42 UI 1.0.0", "body": "- faster builds", "html_url": "u",
                        "assets": [{"name": "M42-UI-1.0.0.zip", "browser_download_url": zip_path.as_uri(),
                                    "size": zip_path.stat().st_size},
                                   {"name": "M42-UI-1.0.0.zip.sha256",
                                    "browser_download_url": (tmp / "M42-UI-1.0.0.zip.sha256").as_uri()}]})
check("a release's zip and its .sha256 are found", rel["download"]["sha_url"] and rel["version"] == "1.0.0", rel)
cache = updater._paths()["cache"]
cache.parent.mkdir(parents=True, exist_ok=True)
import time  # noqa: E402
cache.write_text(json.dumps({"at": time.time(), "release": rel}), encoding="utf-8")
info = updater.check()
check("check(): 1.0.0 is available for 0.9.0", info["available"] and info["latest"] == "1.0.0", info)

# a git checkout is never changed
(root / ".git").mkdir()
try:
    updater.apply(info, pip=False)
    check("a git checkout is refused", False)
except updater.UpdateError as e:
    check("a git checkout is refused", "git" in str(e), e)
shutil.rmtree(root / ".git")

# a wrong SHA-256: nothing changes
good_sha = (tmp / "M42-UI-1.0.0.zip.sha256").read_text(encoding="utf-8")
(tmp / "M42-UI-1.0.0.zip.sha256").write_text("0" * 64, encoding="utf-8")
try:
    updater.apply(info, pip=False)
    check("a wrong SHA-256 is refused", False)
except updater.UpdateError as e:
    check("a wrong SHA-256 is refused, nothing changed",
          "SHA-256" in str(e) and (root / "m42/app.py").read_text(encoding="utf-8") == "old app", e)
(tmp / "M42-UI-1.0.0.zip.sha256").write_text(good_sha, encoding="utf-8")

# the update
out = updater.apply(info, pip=False)
check("apply(): done, checked by SHA-256", out["state"] == "done" and out["verified"] and out["to"] == "1.0.0", out)
check("the app's files are the new ones", (root / "m42/app.py").read_text(encoding="utf-8") == "new app"
      and (root / "install.sh").read_text(encoding="utf-8") == "new installer")
check("a new file is added", (root / "m42/new_file.py").is_file())
check("a file the new release has not is removed", not (root / "m42/old_only.py").exists())
check("the user's files stay as they were", all((root / r).read_text(encoding="utf-8") == t for r, t in mine.items()))
check("nothing goes into the user's folders", not (root / "models/other.gguf").exists())
check("the list of the release's files is kept", "m42/new_file.py" in json.loads(
    (root / "m42/.release-files.json").read_text(encoding="utf-8")))
check("the version before is backed up", any((b / "files/m42/app.py").is_file() for b in updater._backups()))
if os.name != "nt":
    check("the .command and .sh files can run (macOS, Linux)", os.stat(root / "update.command").st_mode & stat.S_IXUSR)
check("changed requirements.txt: pip is left to the caller here", out["packages"] == "same", out)
check("the download folder is cleaned", not updater._paths()["work"].exists())

# rollback
back = updater.rollback()
check("rollback: the version before is back", back["to"] == "0.9.0"
      and (root / "m42/app.py").read_text(encoding="utf-8") == "old app"
      and (root / "m42/old_only.py").read_text(encoding="utf-8") == "gone in 1.0.0"
      and not (root / "m42/new_file.py").exists(), back)
check("rollback: the user's files still stay", all((root / r).read_text(encoding="utf-8") == t for r, t in mine.items()))

# refused zips
bad = release_zip(tmp / "bad.zip", "1.0.0", {**new, "../outside.txt": "x"}, top=False)
try:
    updater.apply_zip(bad, "1.0.0", pip=False)
    check("a zip with ../ in a path is refused", False)
except updater.UpdateError as e:
    check("a zip with ../ in a path is refused", "unsafe" in str(e) and not (tmp / "outside.txt").exists(), e)
try:
    updater.apply_zip(zip_path, "2.0.0", pip=False)
    check("a zip of another version is refused", False)
except updater.UpdateError as e:
    check("a zip of another version is refused", "1.0.0" in str(e), e)
try:
    updater.apply_zip(release_zip(tmp / "other.zip", "1.0.0", {"README.md": "x"}), pip=False)
    check("a zip that is not M42 UI is refused", False)
except updater.UpdateError as e:
    check("a zip that is not M42 UI is refused", "not an M42 UI release" in str(e), e)

updater.ROOT, updater.VERSION = real_root, real_version
shutil.rmtree(tmp, ignore_errors=True)
print("\nall ok" if not fails else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
