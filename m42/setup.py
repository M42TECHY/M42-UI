"""M42 UI's installer, step 2 (the user, 2026-11-15): the install script for this system (install.bat, install.sh,
install.command) has set up Python and its packages; this checks the PC, picks the model that fits, shows what it
will download with the sizes, asks, downloads, makes the launcher, and starts the app.

    python m42/setup.py              ask before each step
    python m42/setup.py --yes        no questions (the model that fits this PC)
    python m42/setup.py --tier 2b    the 2B whatever the PC (or --tier 4b)
    python m42/setup.py --no-speech  no speech models (the mic button stays off)
    python m42/setup.py --no-start   do not start the app at the end
Only the standard library is used here (firstrun.py)."""
import argparse
import os
import platform
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import firstrun  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GB = 2 ** 30


def ask(question, yes, default=True):
    if yes:
        return default
    hint = "[Y/n]" if default else "[y/N]"
    try:
        a = input(f"{question} {hint} ").strip().lower()
    except EOFError:
        return default
    return default if not a else a in ("y", "yes", "aam", "ama", "s")


def size(n):
    return f"{n / GB:.1f} GB" if n >= GB else f"{max(1, round(n / 2 ** 20))} MB"


def show_pc(info):
    print(f"\n  System   {info['system']} ({info['arch']})")
    print(f"  Memory   {info['ram_gb']:g} GB RAM")
    print(f"  Disk     {info['free_gb']:g} GB free where the models go ({firstrun.MODELS})")
    print(f"  CPU      {info['cores']} threads")
    cards = info["gpus"]
    if cards:
        for g in cards:
            kind = "built into the processor" if g["integrated"] else (f"{g['vram_gb']:g} GB" if g["vram_gb"] else "its own memory")
            print(f"  Graphics {g['name']} ({kind})")
    else:
        print("  Graphics none found: the model runs on the processor")


def progress(stop):
    while not stop.is_set():
        s = firstrun.state
        total, done = s.get("total") or 0, s.get("done") or 0
        pct = int(done * 100 / total) if total else 0
        bar = "#" * (pct // 4) + "-" * (25 - pct // 4)
        sys.stdout.write(f"\r  [{bar}] {pct:3d}%  {size(done)} of {size(total)}  {str(s.get('step') or '')[:40]:40}")
        sys.stdout.flush()
        stop.wait(1)
    sys.stdout.write("\n")


def make_launcher():
    """A launcher next to the app that starts it with this Python (the .venv the install script made)."""
    py = Path(sys.executable)
    if os.name == "nt":
        return ROOT / "Start M42 UI.vbs"  # (it finds .venv itself)
    app = ROOT / "m42" / "app.py"
    if platform.system() == "Darwin":
        f = ROOT / "Start M42 UI.command"
    else:
        f = ROOT / "Start M42 UI.sh"
    f.write_text(f'#!/bin/sh\ncd "$(dirname "$0")"\nexec "{py}" "{app}" "$@"\n', encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if platform.system() == "Linux":  # an entry in the apps menu
        apps = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "applications"
        try:
            apps.mkdir(parents=True, exist_ok=True)
            icon = ROOT / "m42" / "ui" / "favicon-256.png"
            (apps / "m42-ui.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=M42 UI\nComment=Build web pages with a local AI\n"
                f'Exec="{f}"\nIcon={icon}\nTerminal=false\nCategories=Development;\n', encoding="utf-8")
        except OSError:
            pass
    return f


def main():
    ap = argparse.ArgumentParser(description="M42 UI setup: the model and tools for this PC")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--tier", choices=list(firstrun.TIERS))
    ap.add_argument("--no-speech", action="store_true")
    ap.add_argument("--no-start", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    print("M42 UI setup\n============\nChecking this PC...")
    info = firstrun.pc()
    show_pc(info)
    if not info["supported"]:
        print(f"\nThere is no llama.cpp build for {info['system']} {info['arch']}. Put a llama-server in llama.cpp/cpu/ "
              "or set M42_LLAMA_SERVER to one, then run this again.")
        return 1
    tier, why = firstrun.choose_tier(info)
    if a.tier:
        tier, why = a.tier, "chosen with --tier"
    print(f"\n  Model    {firstrun.TIERS[tier]['label']}: {why}")
    if not a.tier and not a.yes:
        other = "2b" if tier == "4b" else "4b"
        if not ask(f"  Use {firstrun.TIERS[tier]['label']}? (no = {firstrun.TIERS[other]['label']})", False):
            tier = other
    items = firstrun.plan(tier, speech=not a.no_speech)
    if not items:
        print("\nEverything is already here.")
    else:
        by, total = firstrun.sizes(items)
        print(f"\nTo download ({size(total)}, from Hugging Face and GitHub):")
        for i in items:
            print(f"  - {i['label']:44} {size(i['size']) if i['size'] else 'about 45 MB'}")
        if total > info["free_gb"] * GB * .95:
            print(f"\nNot enough disk space: {size(total)} needed, {info['free_gb']:g} GB free.")
            return 1
        if not ask(f"\nDownload these {len(items)} files now?", a.yes):
            print("Nothing was downloaded. Run this again when you are ready (or press Download in the app).")
            return 0
        firstrun.save_tier(tier)
        stop = threading.Event()
        t = threading.Thread(target=progress, args=(stop,), daemon=True)
        t.start()
        ok = firstrun.run(items)
        stop.set()
        t.join()
        if not ok:
            print(f"\nThe download stopped: {firstrun.state.get('error')}\nRun this again: it resumes where it stopped.")
            return 1
        print("Downloaded and checked (sizes and SHA-256).")
    firstrun.save_tier(tier)
    launcher = make_launcher()
    print(f"\nReady. Start M42 UI with: {launcher.name}")
    if not a.no_start and ask("Start M42 UI now?", a.yes):
        app = ROOT / "m42" / "app.py"
        if os.name == "nt":
            pyw = Path(sys.executable).with_name("pythonw.exe")
            subprocess.Popen([str(pyw if pyw.exists() else sys.executable), str(app)], cwd=str(ROOT),
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        else:
            subprocess.Popen([sys.executable, str(app)], cwd=str(ROOT), start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Starting... the window opens in a few seconds.")
        time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
