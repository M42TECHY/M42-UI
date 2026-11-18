"""M42 UI's installer, step 2 (the user, 2026-11-15): the install script for this system (install.bat, install.sh,
install.command) has set up Python and its packages; this checks the PC, picks the model that fits, shows what it
will download with the sizes, asks, downloads, makes the launcher, and starts the app.

    python m42/setup.py              ask before each step
    python m42/setup.py --yes        no questions (the model that fits this PC)
    python m42/setup.py --tier 2b    the 2B whatever the PC (or --tier 4b)
    python m42/setup.py --no-speech  no speech models (the mic button stays off)
    python m42/setup.py --no-start   do not start the app at the end
    python m42/setup.py --3d-pack    the optional 3D pack too (~20 MB download, ~140 MB on disk; asked, "no" by default)
    python m42/setup.py --models-dir E:/M42-models   where the models go (asked otherwise, once on a PC)
Only the standard library is used here (firstrun.py)."""
import argparse
import shutil
import contextlib
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
import places  # noqa: E402

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
    print("  Disks    " + ", ".join(f"{d['label']} {d['free_gb']:g} GB free" + (" (this app)" if d["app"] else "")
                                  for d in places.drives()))
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
    if platform.system() == "Linux":  # an entry in the apps menu, and an icon on the desktop
        apps = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "applications"
        icon = ROOT / "m42" / "ui" / "favicon-256.png"
        entry = ("[Desktop Entry]\nType=Application\nName=M42 UI\nComment=Build web pages with a local AI\n"
                 f'Exec="{f}"\nIcon={icon}\nTerminal=false\nCategories=Development;\n')
        try:
            apps.mkdir(parents=True, exist_ok=True)
            (apps / "m42-ui.desktop").write_text(entry, encoding="utf-8")
        except OSError:
            pass
        linux_desktop_icon(entry)
    return f


def linux_desktop_icon(entry):
    """🖥 M42 UI's icon on the Linux desktop too (the user, 2026-11-18: "after install, an icon to open it, not a
    command"): the desktop folder as the system names it (xdg-user-dir: "Desktop", "Schreibtisch"...), the launcher
    made executable and marked trusted, so GNOME opens it with no "Allow Launching" step. Nothing when the PC has no
    desktop folder."""
    desk = ""
    if shutil.which("xdg-user-dir"):
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            desk = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=5).stdout.strip()
    desk = Path(desk) if desk and Path(desk) != Path.home() else Path.home() / "Desktop"
    if not desk.is_dir():
        return None
    f = desk / "m42-ui.desktop"
    try:
        f.write_text(entry, encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        return None
    if shutil.which("gio"):
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(["gio", "set", str(f), "metadata::trusted", "true"], capture_output=True, timeout=5)
    return f


def three_d_pack(a):
    """📦 The optional 3D pack (pack3d.py): asked, "no" by default (the user, 2026-11-17: "whoever needs it downloads
    it, else it stays out"); --3d-pack says yes, --no-3d-pack no."""
    import pack3d
    if pack3d.status()["installed"] or a.no_3d_pack:
        return
    print(f"\n  3D pack  about {pack3d.SIZE_MB} MB download ({pack3d.DISK_MB} MB on disk): ~850 free low-poly models (restaurant, hospital, office, lab, hotel,"
          "\n           city, cars, farm...) for the 3D landing pages. Polyfork, CC BY 4.0. Optional: the app works without it.")
    if not (a.three_d_pack or ask("  Download the 3D pack too?", a.yes, default=False)):
        print("  (Later: python m42/pack3d.py install)")
        return
    try:
        st = pack3d.install(pack3d._bar)
        print(f"\n  3D pack ready: {st['models']} models.")
    except (OSError, RuntimeError) as e:
        print(f"\n  The 3D pack did not download ({e}). Later: python m42/pack3d.py install")


def choose_folder(a, tier):
    """📦 Before anything downloads: how much room it needs, and where the models go (the user, 2026-11-17: "the ZIP
    is in Downloads on C:; the models must not fill C:"). Asked once on a PC; --models-dir answers it."""
    need, _ = firstrun.space(firstrun.plan_in(places.DEFAULT) if not a.models_dir else firstrun.plan_in(a.models_dir))
    room = need + places.MARGIN
    folder, enough = places.suggest(need)
    print(f"\n  Space    the models need about {size(room)} free ({size(need)} of files + {size(places.MARGIN)} room "
          "while they download).")
    for d in places.drives():
        ok = d["free_gb"] * GB >= room
        print(f"           {d['label']:4} {d['free_gb']:>7g} GB free  {'ok' if ok else 'too small'}"
              + ("  (this app)" if d["app"] else "") + (f"  -> {d['folder']}" if ok else ""))
    if a.models_dir:
        folder = a.models_dir
    elif not a.yes:
        try:
            got = input(f"  Where should the models go? [Enter = {folder}] ").strip().strip('"')
        except EOFError:
            got = ""
        folder = got or folder
    elif not enough:
        print("  No drive has the room for the models: free some space and run this again.")
        return 1
    while True:
        why = firstrun.use_folder(folder)
        if not why:
            print(f"  Models   {places.models_dir()}")
            return 0
        print(f"  {why}")
        if a.yes or a.models_dir:
            return 1
        try:
            folder = input("  Another folder (empty = stop): ").strip().strip('"')
        except EOFError:
            folder = ""
        if not folder:
            return 1


def main():
    ap = argparse.ArgumentParser(description="M42 UI setup: the model and tools for this PC")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--tier", choices=list(firstrun.TIERS))
    ap.add_argument("--no-speech", action="store_true")
    ap.add_argument("--no-start", action="store_true")
    ap.add_argument("--3d-pack", dest="three_d_pack", action="store_true", help="download the optional 3D pack (~20 MB download)")
    ap.add_argument("--no-3d-pack", dest="no_3d_pack", action="store_true")
    ap.add_argument("--models-dir", dest="models_dir", help="the folder the models go to")
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
    if a.models_dir or not places.chosen():
        if choose_folder(a, tier) != 0:
            return 1
    items = firstrun.plan(tier, speech=not a.no_speech)
    if not items:
        print("\nEverything is already here.")
    else:
        by, total = firstrun.sizes(items)
        print(f"\nTo download ({size(total)}, from Hugging Face and GitHub), models into {firstrun.MODELS}:")
        for i in items:
            print(f"  - {i['label']:44} {size(i['size']) if i['size'] else 'about 45 MB'}")
        need, runners = firstrun.space(items)
        why = places.check(firstrun.MODELS, need) if need else ""
        if why or places.free_bytes(ROOT) < runners + (200 << 20):
            print(f"\n{why or 'Not enough space for the runners in the app folder.'}")
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
    three_d_pack(a)
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
