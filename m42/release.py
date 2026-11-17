"""Make the files of a GitHub Release (for the maintainer, not for users).

    python m42/release.py

reads the version from m42/version.py and writes, from the last commit (git archive: only what is in the repository,
nothing from this PC):

    dist/M42-UI-<version>.zip          the app, in a folder M42-UI-<version>/
    dist/M42-UI-<version>.zip.sha256   its SHA-256, which the updater checks before it changes anything

Then on GitHub: Releases -> Draft a new release -> tag v<version> -> attach both files -> Publish. Every M42 UI that
checks for updates sees it within 6 hours (updater.py)."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "m42"))
from version import VERSION  # noqa: E402


def main():
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        print("Note: there are changes not committed yet; the release is made from the last commit only.\n")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    name = f"M42-UI-{VERSION}.zip"
    out = dist / name
    subprocess.run(["git", "archive", "--format=zip", f"--prefix=M42-UI-{VERSION}/", "-o", str(out), "HEAD"],
                   cwd=ROOT, check=True)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (dist / (name + ".sha256")).write_text(f"{digest}  {name}\n", encoding="utf-8")
    print(f"Made {out.relative_to(ROOT)} ({out.stat().st_size >> 20} MB) and its .sha256.")
    print(f"\nOn GitHub: Releases -> Draft a new release -> tag v{VERSION} -> attach both files -> Publish.")


if __name__ == "__main__":
    main()
