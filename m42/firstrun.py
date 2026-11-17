"""First run on a new PC: what M42 UI needs and GitHub does not hold, for THIS PC (the user, 2026-11-15: "someone
downloads M42 UI from GitHub on Windows, Linux or Mac: the installer checks the PC (RAM, a graphics card), picks the
model that fits, asks permission, downloads, installs, runs the app").

  1. pc(): the system, its RAM, free disk, cores and graphics cards (looked up before llama-server is here: the
     system's own tools; hardware.py asks llama-server itself once it is installed).
  2. choose_tier(pc): the model that fits: Qwen3.5-2B for an 8 GB PC, Qwen3.5-4B from 12 GB (16 GB PCs), or a
     graphics card of its own with 6 GB or more.
  3. plan(tier): every file this PC lacks, with its size: llama-server (llama.cpp's release for this system), the
     model and its picture reader, the speech models (Whisper small: English and every language; IndicConformer Tamil: Tamil and Tanglish, live)
     and the voice detector.
  4. Nothing downloads before the user says yes: the installer asks in its window (setup.py), the app shows the list
     and a Download button (/api/setup/start). Each file is checked by its size and SHA-256; a broken download resumes.

    python firstrun.py check    (only checks that every file can be reached, downloads nothing)
    python firstrun.py plan     (this PC and what it would download)"""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

import places  # noqa: E402  (where the models go: chosen once on this PC, places.py)

ROOT = Path(__file__).resolve().parent.parent
MODELS = places.models_dir()
LLAMA = ROOT / "llama.cpp"
WHISPER_DIR = ROOT / "whisper.cpp" / "bin"
CONFIG = Path(__file__).resolve().parent / "config.json"
UA = {"User-Agent": "M42-UI-setup"}
HF = "https://huggingface.co/{repo}/resolve/main/{file}"
GH = "https://github.com/ggml-org/llama.cpp/releases/download/{tag}/{file}"
LLAMA_TAG = "b11433"  # the llama.cpp build M42 UI was tested with (its flags: --reasoning, -fa on|off, --list-devices)
WHISPER_TAG = "b5454"  # whisper.cpp's release with whisper-server (Windows and Linux; a Mac runs Whisper in Python)

# the chat model per tier: (repo, file there, saved as, bytes, sha256)
TIERS = {
    "4b": {"label": "Qwen3.5 4B", "model": "q35-4b", "files": [
        ("unsloth/Qwen3.5-4B-GGUF", "Qwen3.5-4B-Q4_K_M.gguf", "Qwen3.5-4B-Q4_K_M.gguf", 2740937888,
         "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"),
        ("unsloth/Qwen3.5-4B-GGUF", "mmproj-F16.gguf", "Qwen3.5-4B-mmproj-F16.gguf", 672423616,
         "cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864")]},
    "2b": {"label": "Qwen3.5 2B", "model": "q35-2b", "files": [
        ("unsloth/Qwen3.5-2B-GGUF", "Qwen3.5-2B-Q4_K_M.gguf", "Qwen3.5-2B-Q4_K_M.gguf", 1280835840,
         "aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223"),
        ("unsloth/Qwen3.5-2B-GGUF", "mmproj-F16.gguf", "Qwen3.5-2B-mmproj-F16.gguf", 668227264,
         "7035e9cb8d7c6a9681d07eef9a364783e86ea4cd73faab2eabb4f43a101830c7")]},
}
MODEL_FILES = TIERS["4b"]["files"]  # (the old name)

# speech (speech.py): Whisper small for English (and every language), IndicConformer Tamil (Tamil and Tanglish speech,
# ~0.2 s a phrase, written in Tamil letters: the 4B reads them well), the voice detector. (2026-11-17, the user: "Whisper
# small for English, IndicConformer Tamil; the rest is not needed": the Whisper Tanglish fine-tune is no longer fetched.)
# (repo or url, file there, saved as (under models/), bytes, sha256 or None for a small text file)
WHISPER_SMALL_GGML = ("ggerganov/whisper.cpp", "ggml-small-q5_1.bin", "ggml-small-q5_1.bin", 190085487,
                      "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb")
# AI4Bharat's IndicConformer (MIT) as sherpa-onnx int8 CTC, Tamil, and the tokens shared by its languages
INDIC_REPO = "NiranjanYadavIN/indicconformer-sherpa-onnx"
INDIC_TA = [(INDIC_REPO, "ta/model.int8.onnx", "indicconformer/ta/model.int8.onnx", 197595513,
             "abb7b59d706b8d27ba3fb5e5e3db7671c9e1a09bf7bc6122de507c60030e65fb"),
            (INDIC_REPO, "tokens.txt", "indicconformer/tokens.txt", 67605, None)]
# a Mac has no whisper-server build: Whisper small runs in Python there (transformers), from OpenAI's own files
WHISPER_SMALL_HF = [("openai/whisper-small", f, f"whisper-small/{f}", n, sha) for f, n, sha in (
    ("model.safetensors", 966995080, "1d7734884874f1a1513ed9aa760a4f8e97aaa02fd6d93a3a85d27b2ae9ca596b"),
    ("config.json", 1967, None), ("generation_config.json", 3868, None), ("preprocessor_config.json", 184990, None),
    ("tokenizer.json", 2480466, None), ("tokenizer_config.json", 282683, None), ("vocab.json", 835550, None),
    ("merges.txt", 493869, None), ("normalizer.json", 52666, None), ("added_tokens.json", 34604, None),
    ("special_tokens_map.json", 2194, None))]
VAD = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx", "silero_vad.onnx",
       "vad/silero_vad.onnx", 643854, "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6")

# llama.cpp builds per system: (folder in llama.cpp/, release file, sha256). Vulkan uses any graphics card (NVIDIA,
# AMD, Intel) and the processor; the CPU build is the fallback hardware.py starts when a card fails.
LLAMA_BUILDS = {
    ("Windows", "x64"): [("vulkan", "llama-b11433-bin-win-vulkan-x64.zip", "021001e2b7a60aab1d23b301edb2f076e8a5136d8d29686d0d95341342088714"),
                         ("cpu", "llama-b11433-bin-win-cpu-x64.zip", "301943380e45deae3991d42dddd03fae65c6a4963a5d882328a60208b43aa9e0")],
    ("Windows", "arm64"): [("cpu", "llama-b11433-bin-win-cpu-arm64.zip", "c415c3576dd673d31da874c57ef8863f9592b8f0e1f092290271cbaf619b2ade")],
    ("Linux", "x64"): [("vulkan", "llama-b11433-bin-ubuntu-vulkan-x64.tar.gz", "1243a90945de3644f86bc98b588c9f7664c8528cf925b184671df060e8334d1f"),
                       ("cpu", "llama-b11433-bin-ubuntu-x64.tar.gz", "d6ff12a557793e302ddbba9660a0f045c403e2f67ab5dcdc1254b343c560c015")],
    ("Linux", "arm64"): [("cpu", "llama-b11433-bin-ubuntu-arm64.tar.gz", "9261c811ece17f236508edaa861042b40d8e673874f2eb3c3f524649dd4269fd")],
    ("Darwin", "arm64"): [("metal", "llama-b11433-bin-macos-arm64.tar.gz", "5e7b2383009facb31404f308cdb9edd1fb15131330801408fb582bd05e188f97")],
    ("Darwin", "x64"): [("metal", "llama-b11433-bin-macos-x64.tar.gz", "caaadcff99ce696bbb6a1ef6f7c0050250fe60d8448464ee7c90878cde3a5370")],
}
# whisper-server per system: (release file, bytes, sha256); none for a Mac or an ARM PC (Whisper runs in Python there)
WHISPER_BUILDS = {
    ("Windows", "x64"): ("whisper-blas-bin-x64.zip", 21715607, "b1158bd10edf92c9799149a6fc5d3e58da3f495241d6fb3423088130e88ffbf3"),
    ("Linux", "x64"): ("whisper-bin-ubuntu-x64.tar.gz", 10364195, "a72becf15d7917f990f6313867a52638b82b7f9ef237fb0c980dac56a135781c"),
}
EXE = ".exe" if os.name == "nt" else ""
SERVER = "llama-server" + EXE
WHISPER_SERVER = "whisper-server" + EXE

state = {"state": "idle", "step": "", "done": 0, "total": 0, "error": "", "started": 0.0}
_lock = threading.Lock()


def system():
    m = platform.machine().lower()
    return platform.system(), ("arm64" if m in ("arm64", "aarch64") else "x64")


def builds():
    return LLAMA_BUILDS.get(system(), [])


# ---------------------------------------------------------------- 1. this PC

def _run(cmd, timeout=20):
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags)
        return (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def ram_gb():
    """The PC's memory in GB (all of it, as its maker says: 8, 16...)."""
    try:
        import psutil
        return psutil.virtual_memory().total / 2 ** 30
    except ImportError:
        pass
    if os.name == "nt":
        import ctypes

        class Mem(ctypes.Structure):
            _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong) for n in ("total", "avail", "tp", "ap", "tv", "av", "ae")]
        m = Mem()
        m.len = ctypes.sizeof(Mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return m.total / 2 ** 30
        return 0.0
    if platform.system() == "Darwin":
        out = _run(["sysctl", "-n", "hw.memsize"]).strip()
        return int(out) / 2 ** 30 if out.isdigit() else 0.0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except (ValueError, OSError, AttributeError):
        return 0.0


INTEGRATED_RX = re.compile(r"radeon\(tm\) graphics|radeon graphics|vega \d|intel|uhd|iris|llvmpipe|swiftshader|"
                           r"microsoft basic|virtualbox|vmware|parallels", re.I)


def gpus():
    """[{"name", "vram_gb" (0 when unknown), "integrated"}]: the graphics of this PC, from the system's own tools
    (llama-server is not here yet: hardware.py asks it once it is)."""
    out = []
    smi = shutil.which("nvidia-smi")  # an NVIDIA card: its real memory
    if smi:
        for line in _run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]).splitlines():
            if "," in line:
                name, mb = line.rsplit(",", 1)
                if mb.strip().isdigit():
                    out.append({"name": name.strip(), "vram_gb": round(int(mb) / 1024, 1), "integrated": False})
    sysname = platform.system()
    if sysname == "Windows":
        # (AdapterRAM stops at 4 GB; the driver's own qwMemorySize in the registry has the real size)
        ps = ("Get-ItemProperty 'HKLM:\\SYSTEM\\ControlSet001\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\0*' "
              "-ErrorAction SilentlyContinue | ForEach-Object { \"$($_.DriverDesc)|$($_.'HardwareInformation.qwMemorySize')\" }")
        for line in _run(["powershell", "-NoProfile", "-Command", ps]).splitlines():
            name, _, mem = line.partition("|")
            name = name.strip()
            if name and not any(g["name"] == name for g in out):
                out.append({"name": name, "vram_gb": round(int(mem) / 2 ** 30, 1) if mem.strip().isdigit() else 0,
                            "integrated": bool(INTEGRATED_RX.search(name))})
    elif sysname == "Darwin":
        txt = _run(["system_profiler", "SPDisplaysDataType"], timeout=30)
        for name in re.findall(r"Chipset Model:\s*(.+)", txt):
            vram = re.search(r"VRAM[^:]*:\s*(\d+)\s*(GB|MB)", txt)
            out.append({"name": name.strip(), "vram_gb": (int(vram.group(1)) / (1 if vram.group(2) == "GB" else 1024)) if vram else 0,
                        "integrated": "Apple" in name or bool(INTEGRATED_RX.search(name))})  # (Apple: shares the RAM)
    else:
        for line in _run(["lspci"]).splitlines():
            if re.search(r"VGA|3D controller|Display controller", line):
                name = line.split(":", 2)[-1].strip()
                if not any(g["name"] in name or name in g["name"] for g in out):
                    out.append({"name": name, "vram_gb": 0, "integrated": bool(INTEGRATED_RX.search(name))})
    return out


def pc():
    """This PC as the installer shows it."""
    sysname, arch = system()
    MODELS.mkdir(parents=True, exist_ok=True)
    return {"system": {"Darwin": "macOS"}.get(sysname, sysname), "arch": arch, "ram_gb": round(ram_gb(), 1),
            "free_gb": round(shutil.disk_usage(MODELS).free / 2 ** 30, 1), "cores": os.cpu_count() or 0, "gpus": gpus(),
            "supported": bool(LLAMA_BUILDS.get((sysname, arch)))}


def choose_tier(info):
    """(tier, why): the 2B for an 8 GB PC, the 4B from 12 GB (a 16 GB PC), or with a graphics card of 6 GB or more
    (the model's layers on the card: the PC's RAM is not the limit then)."""
    ram = info.get("ram_gb") or 0
    cards = [g for g in info.get("gpus") or [] if not g.get("integrated") and g.get("vram_gb", 0) >= 6]
    if cards:
        return "4b", f"{cards[0]['name']} ({cards[0]['vram_gb']:g} GB) runs the 4B on the card"
    if ram >= 12:
        return "4b", f"{ram:.0f} GB RAM: enough for the 4B (better pages, pictures read well)"
    if ram >= 5:
        return "2b", f"{ram:.0f} GB RAM: the 2B fits (the 4B needs about 12 GB with the browser and the app)"
    return "2b", f"only {ram:.0f} GB RAM: the 2B is the smallest; M42 UI will be slow on this PC"


def chosen_tier():
    """The tier picked at install (config.json "model_tier"), else what fits this PC."""
    try:
        t = json.loads(CONFIG.read_text(encoding="utf-8")).get("model_tier")
        if t in TIERS:
            return t
    except (OSError, ValueError):
        pass
    if any((MODELS / f[2]).exists() for f in TIERS["4b"]["files"][:1]):
        return "4b"
    if any((MODELS / f[2]).exists() for f in TIERS["2b"]["files"][:1]):
        return "2b"
    return choose_tier({"ram_gb": ram_gb(), "gpus": []})[0]


def save_tier(tier):
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.is_file() else {}
    except (OSError, ValueError):
        cfg = {}
    cfg["model_tier"] = tier
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG)


# ---------------------------------------------------------------- 2. what this PC lacks

def _have(rel, size):
    p = MODELS / rel
    return p.exists() and (not size or p.stat().st_size == size)


def _hf(row, group):
    repo, file, saved, size, sha = row
    url = repo if repo.startswith("http") else HF.format(repo=repo, file=file)
    return {"kind": "file", "group": group, "label": saved, "url": url, "dest": str(MODELS / saved), "size": size, "sha": sha}


def plan(tier=None, speech=True):
    """[item] of what this PC lacks, in download order: {"kind": "file" | "llama" | "whisper", "group", "label",
    "url", "dest", "size" (bytes, 0 = unknown), "sha"}."""
    tier = tier or chosen_tier()
    items = []
    have_server = any((LLAMA / b / SERVER).exists() for b in ("cuda", "vulkan", "metal", "cpu")) or os.environ.get("M42_LLAMA_SERVER")
    if not have_server:
        for folder, file, sha in builds():
            items.append({"kind": "llama", "group": "runner", "label": f"llama-server ({folder})", "folder": folder,
                          "url": GH.format(tag=LLAMA_TAG, file=file), "dest": str(LLAMA / file), "size": 0, "sha": sha})
    items += [_hf(f, "model") for f in TIERS[tier]["files"] if not _have(f[2], f[3])]
    if speech:
        wb = WHISPER_BUILDS.get(system())
        if wb:
            if not (WHISPER_DIR / WHISPER_SERVER).exists():
                items.append({"kind": "whisper", "group": "speech", "label": "whisper-server (speech runner)",
                              "url": f"https://github.com/ggml-org/whisper.cpp/releases/download/{WHISPER_TAG}/{wb[0]}",
                              "dest": str(ROOT / "whisper.cpp" / wb[0]), "size": wb[1], "sha": wb[2]})
            if not _have(WHISPER_SMALL_GGML[2], WHISPER_SMALL_GGML[3]):
                items.append(_hf(WHISPER_SMALL_GGML, "speech"))
        else:  # (a Mac: Whisper small in Python)
            items += [_hf(f, "speech") for f in WHISPER_SMALL_HF if not _have(f[2], f[3])]
        items += [_hf(f, "speech") for f in INDIC_TA if not _have(f[2], f[3])]
        if not _have(VAD[2], VAD[3]):
            items.append(_hf(VAD, "speech"))
    return items


def core_missing():
    """The model or its runner is missing (the app cannot answer yet); speech files alone do not stop it."""
    return any(i["group"] in ("model", "runner") for i in plan())


def needed():
    """[(kind, label)] of what this PC lacks (the old shape, for app.py)."""
    return [(i["kind"], i["label"]) for i in plan()]


def sizes(items):
    """{group: bytes} and the total (a llama build counted at about 45 MB)."""
    out = {}
    for i in items:
        out[i["group"]] = out.get(i["group"], 0) + (i["size"] or 45 << 20)
    return out, sum(out.values())


def space(items):
    """(bytes the models' folder needs, bytes the app's folder needs: the runners)."""
    models = sum(i["size"] or 0 for i in items if i["kind"] == "file")
    runners = sum(i["size"] or 45 << 20 for i in items if i["kind"] != "file")
    return models, runners


def place_info(items=None):
    """📦 Where the models go and the room for them, for the app's first-run note and the installer: the folder
    (chosen or suggested), the GB needed, each drive's free GB, and whether the folder has the room."""
    items = plan() if items is None else items
    need, runners = space(items)
    folder, enough = (str(places.models_dir()), None) if places.chosen() else places.suggest(need)
    if enough is None:
        enough = not need or places.free_bytes(folder) >= need + places.MARGIN
    app_room = not runners or places.free_bytes(ROOT) >= runners + (200 << 20)
    return {"folder": folder, "chosen": places.chosen(), "need_gb": round(need / 2 ** 30, 2),
            "room_gb": round((need + places.MARGIN) / 2 ** 30, 1), "runners_gb": round(runners / 2 ** 30, 2),
            "enough": bool(enough), "app_room": app_room, "app_folder": str(ROOT), "drives": places.drives()}


def use_folder(folder):
    """The user's folder for the models: checked (made, writable, the room), then kept for this PC. "" or why not."""
    need, _ = space(plan_in(folder))
    why = places.check(folder, need)
    if not why:
        places.save(folder)
    return why


def plan_in(folder):
    """plan() as it would be with the models in `folder` (what it already holds is not downloaded again)."""
    global MODELS
    keep = MODELS
    MODELS = Path(folder)
    try:
        return plan()
    finally:
        MODELS = keep


def check(timeout=30, tier=None):
    """Every file of this system's setup, reached and measured without downloading it (one byte asked for):
    [(name, url, ok, bytes, note)]."""
    out = []
    for item in plan(tier) or []:
        try:
            req = urllib.request.Request(item["url"], headers=dict(UA, Range="bytes=0-0"))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                size = int((r.headers.get("Content-Range") or "/0").rsplit("/", 1)[-1] or 0)
                ok = r.status in (200, 206)
            want = item["size"]
            out.append((item["label"], item["url"], ok and (not want or size == want), size,
                        "" if not want or size == want else f"size {size}, expected {want}"))
        except OSError as e:
            out.append((item["label"], item["url"], False, 0, str(e)[:120]))
    return out


# ---------------------------------------------------------------- 3. download and unpack

def _fetch(url, dest, size, sha256, label):
    """url into dest (resumed from dest.part), checked by size and SHA-256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h = hashlib.sha256()
    have = part.stat().st_size if part.exists() else 0
    if size and have > size:
        part.unlink()
        have = 0
    if have:
        with open(part, "rb") as f:
            for chunk in iter(lambda: f.read(8 << 20), b""):
                h.update(chunk)
    headers = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r, \
            open(part, "ab" if have and r.status == 206 else "wb") as out:
        if have and r.status != 206:
            h, have = hashlib.sha256(), 0
        total = size or int(r.headers.get("Content-Length") or 0) + have
        with _lock:
            state.update(step=label, file_done=have, file_total=total)
        for chunk in iter(lambda: r.read(1 << 20), b""):
            out.write(chunk)
            h.update(chunk)
            with _lock:
                state["done"] += len(chunk)
                state["file_done"] = state.get("file_done", 0) + len(chunk)
    if size and part.stat().st_size != size:
        raise OSError(f"{dest.name}: got {part.stat().st_size} of {size} bytes (the connection dropped: it resumes next start)")
    if sha256 and h.hexdigest() != sha256:
        part.unlink()
        raise OSError(f"{dest.name}: the file does not match its checksum (deleted; it downloads again next start)")
    part.replace(dest)


def _unpack(archive, target, exe):
    """A release archive into `target`: the folder that holds `exe`, its files at the top."""
    tmp = Path(tempfile.mkdtemp(prefix="m42-unpack-"))
    try:
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(archive) as t:
                t.extractall(tmp, filter="data")
        server = next(tmp.rglob(exe), None)
        if not server:
            raise OSError(f"{archive.name} has no {exe}")
        target.mkdir(parents=True, exist_ok=True)
        for f in server.parent.iterdir():
            dest = target / f.name
            if dest.exists() or dest.is_symlink():
                shutil.rmtree(dest) if dest.is_dir() and not dest.is_symlink() else dest.unlink()
            shutil.move(str(f), dest)
        if os.name != "nt":
            for f in target.iterdir():  # (the runners and their tools: executable)
                if f.is_file() and not f.suffix:
                    f.chmod(0o755)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        archive.unlink(missing_ok=True)


def run(items=None, tier=None, on_step=None):
    """Download and unpack `items` (plan() when none). on_step(label, i, n): a line for the installer's window."""
    items = plan(tier) if items is None else items
    _by, total = sizes(items)
    with _lock:
        state.update(done=0, total=total)
    try:
        for n, item in enumerate(items, 1):
            if on_step:
                on_step(item["label"], n, len(items))
            dest = Path(item["dest"])
            _fetch(item["url"], dest, item["size"], item["sha"], item["label"])
            if item["kind"] == "llama":
                _unpack(dest, LLAMA / item["folder"], SERVER)
            elif item["kind"] == "whisper":
                _unpack(dest, WHISPER_DIR, WHISPER_SERVER)
        with _lock:
            state.update(state="done", step="Ready", error="")
        return True
    except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as e:
        with _lock:
            state.update(state="error", error=str(e))
        return False


def start(consent=False, folder=None):
    """In the app: with something missing, the list waits for the user's yes ("consent") and, on a PC with no models
    folder chosen yet, their folder; with them, the download runs in the background. Returns True when it is running
    (or started). A folder without the room: nothing starts, state "error" says why."""
    with _lock:
        if state["state"] == "running":
            return True
    if consent and (folder or not places.chosen()):
        why = use_folder(folder or place_info()["folder"])
        if why:
            with _lock:
                state.update(state="error", error=why)
            return False
    todo = plan()
    if consent and todo and not place_info(todo)["app_room"]:
        with _lock:
            state.update(state="error", error=f"Not enough space for the runners in the app's folder ({ROOT.anchor or ROOT})")
        return False
    with _lock:
        if not todo:
            state.update(state="done")
            return False
        if not consent:
            state.update(state="needs_consent")
            return False
        state.update(state="running", error="", started=time.time())
    save_tier(chosen_tier())
    threading.Thread(target=run, args=(todo,), daemon=True).start()
    return True


def status():
    with _lock:
        s = dict(state)
    if s["state"] in ("needs_consent", "error", "idle"):
        items = plan()
        by, total = sizes(items)
        tier = chosen_tier()
        s.update(missing=[i["label"] for i in items], gb=round(total / 2 ** 30, 1),
                 groups={k: round(v / 2 ** 30, 2) for k, v in by.items()}, tier=tier, tier_label=TIERS[tier]["label"],
                 place=place_info(items) if items else None)
    else:
        s.update(missing=[], gb=round((s.get("total") or 0) / 2 ** 30, 1))
    return s


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["check"]:
        print("system:", system())
        for name, url, ok, size, note in check():
            print("OK  " if ok else "FAIL", f"{name}  {size / 2 ** 20:,.0f} MB", note)
    elif sys.argv[1:] == ["plan"]:
        info = pc()
        print(json.dumps(info, indent=1))
        print("tier:", choose_tier(info))
        for i in plan(choose_tier(info)[0]):
            print(f"  {i['group']:7} {i['label']}  {(i['size'] or 0) / 2 ** 20:,.0f} MB")
    else:
        print("python firstrun.py check | plan")
