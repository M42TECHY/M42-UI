"""This PC, and how llama-server is started on it (2026-11-10). M42 UI was tuned on one machine (Ryzen 5 5600G, no
graphics card: -ngl 0, 6 threads, ~8-10 tokens/s). On GitHub it runs on any PC, so the start-up adapts: a graphics
card (an RTX, an RX, an Arc) takes the model's layers (llama.cpp fits as many as its memory holds: -ngl auto) and
generation is several times faster; a PC with only a processor keeps the measured CPU settings, with its own number
of cores. Nothing to set by hand; "gpu": "off" in config.json keeps the model on the processor.
The devices are asked from llama-server itself (--list-devices), so what is listed is what it can really use."""
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "llama-server.exe" if os.name == "nt" else "llama-server"
# the builds in llama.cpp/, the fastest for its hardware first: cuda (NVIDIA; optional, the user may add it), vulkan
# (any graphics card), metal (Apple), cpu
BUILDS = ("cuda", "vulkan", "metal", "cpu")
INTEGRATED_RX = re.compile(r"radeon\(tm\) graphics|radeon graphics|vega \d|intel.*(uhd|iris|hd graphics)|\buhd\b|llvmpipe|"
                           r"swiftshader|microsoft basic", re.I)
DEVICE_RX = re.compile(r"^\s*([A-Za-z]+\d+):\s*(.+?)\s*\((\d+)\s*MiB(?:,\s*(\d+)\s*MiB free)?\)", re.M)
GPU_FAILED = False  # a start with the graphics card failed in this run: the processor from then on
_hw = None


def builds():
    """[(build name, llama-server path)] that exist; a llama-server on the PATH as the last one."""
    out = [(b, ROOT / "llama.cpp" / b / NAME) for b in BUILDS if (ROOT / "llama.cpp" / b / NAME).exists()]
    env = os.environ.get("M42_LLAMA_SERVER")
    if env and Path(env).exists():
        out.insert(0, ("custom", Path(env)))
    found = shutil.which("llama-server")
    if found and not out:
        out.append(("path", Path(found)))
    return out


def cores():
    """The processor's real cores (generation is slower with hyper-threads than without)."""
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return int(n)
    except ImportError:
        pass
    try:
        if os.name == "nt":
            out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"],
                                 capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            if out.strip().isdigit():
                return int(out.strip())
        elif Path("/proc/cpuinfo").exists():
            ids = set(re.findall(r"physical id\s*:\s*(\d+)[\s\S]*?core id\s*:\s*(\d+)", Path("/proc/cpuinfo").read_text()))
            if ids:
                return len(ids)
        else:
            out = subprocess.run(["sysctl", "-n", "hw.physicalcpu"], capture_output=True, text=True, timeout=5).stdout
            if out.strip().isdigit():
                return int(out.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return max(1, (os.cpu_count() or 2) // 2)


def devices(exe):
    """[{"id", "name", "mb", "free_mb", "integrated"}]: what this llama-server can offload to."""
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        env = None if os.name == "nt" else dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(
            x for x in (str(Path(exe).parent), os.environ.get("LD_LIBRARY_PATH", "")) if x))
        r = subprocess.run([str(exe), "--list-devices"], capture_output=True, text=True, timeout=30, creationflags=flags, env=env)
    except (OSError, subprocess.SubprocessError):
        return []
    return [{"id": m.group(1), "name": m.group(2), "mb": int(m.group(3)), "free_mb": int(m.group(4) or m.group(3)),
             "integrated": bool(INTEGRATED_RX.search(m.group(2)))} for m in DEVICE_RX.finditer((r.stdout or "") + "\n" + (r.stderr or ""))]


def detect(refresh=False):
    """{"cores", "builds": [(name, path, devices)]} of this PC, looked up once."""
    global _hw
    if _hw is None or refresh:
        _hw = {"cores": cores(), "builds": [(b, p, [] if b == "cpu" else devices(p)) for b, p in builds()]}
    return _hw


def plan(gpu="auto", need_mb=0):
    """How to start llama-server here: {"exe", "build", "args": [...], "gpu": name | "", "why"}; exe None with no build.
    need_mb: the model file's size (with a card too small for most of it, the processor is as fast and steadier)."""
    hw = detect()
    if not hw["builds"]:
        return {"exe": None, "build": "", "args": [], "gpu": "", "why": "no llama-server found in llama.cpp/"}
    threads = ["-t", str(hw["cores"])]
    if gpu != "off" and not GPU_FAILED:
        for build, exe, devs in hw["builds"]:
            cards = sorted((d for d in devs if not d["integrated"] and d["mb"] >= 3000), key=lambda d: -d["mb"])
            if build == "cuda" and not cards:
                continue
            if cards and (not need_mb or cards[0]["free_mb"] >= need_mb * .45):
                d = cards[0]
                return {"exe": exe, "build": build, "gpu": d["name"],
                        "args": ["--device", d["id"], "-ngl", "auto", "-fa", "on"] + threads,
                        "why": f"{d['name']} ({d['mb'] // 1024} GB): the model's layers on the graphics card, as many as fit"}
    # no graphics card (or only the processor's own graphics): the settings measured on a Ryzen 5 5600G. The Vulkan
    # build with -ngl 0 still reads big prompts on the built-in graphics (66 vs 31 tokens/s); flash attention off
    # generates faster on a processor (8.6 -> 11.1 tokens/s)
    build, exe, _devs = next(((b, p, d) for b, p, d in hw["builds"] if b != "cuda"), hw["builds"][0])
    return {"exe": exe, "build": build, "gpu": "", "args": ["-ngl", "0", "-fa", "off"] + threads,
            "why": f"no graphics card found: the processor, {hw['cores']} cores" if not GPU_FAILED
            else f"the graphics card did not start: the processor, {hw['cores']} cores"}


def summary():
    hw = detect()
    cards = [d for _b, _p, devs in hw["builds"] for d in devs]
    names = list(dict.fromkeys(f"{d['name']} ({d['mb'] // 1024} GB{', built-in' if d['integrated'] else ''})" for d in cards))
    return f"{hw['cores']} cores; graphics: {', '.join(names) or 'none'}; builds: {', '.join(b for b, _p, _d in hw['builds']) or 'none'}"


if __name__ == "__main__":
    print(summary())
    p = plan()
    print(p["build"], " ".join(p["args"]), "|", p["why"])
