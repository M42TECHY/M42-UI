"""Managed llama.cpp backend: M42 starts/stops llama-server itself.

Benchmarked on Ryzen 5 5600G (Qwen2.5-Coder 7B Q4_K_M):
  Vulkan build with -ngl 0  -> prompt 66 t/s (iGPU does big batches), generation 10.2 t/s (CPU)
  --spec-type ngram-simple  -> 2x faster generation when the reply repeats the prompt (code edits)
  A 0.5B draft model made generation slower here (both models compete for RAM bandwidth).
"""
import ctypes
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import hardware

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "llama.cpp" / "vulkan" / "llama-server.exe"
import places  # noqa: E402  (the models folder chosen on this PC)
MODELS_DIR = places.models_dir()
LOG = Path(__file__).resolve().parent / "logs" / "llama-server.log"
# saved prompt caches (~90 MB each). Its own folder for flash attention off: the KV cache layout differs, so the
# caches saved with -fa on must not be restored
SLOT_DIR = Path(__file__).resolve().parent / "cache" / "slots-nofa"
HOLD_FILE = "held-chat.slot"  # the chat's cache, saved around a side request (see hold_cache)
PORT = 8080
URL = f"http://127.0.0.1:{PORT}/v1"
PREFIX = "llama.cpp/"
OLLAMA_STORE = Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")
MODELS = {  # dropdown name -> (GGUF copy in models/, same weights in the Ollama library)
    "coder-7b": ("qwen2.5-coder-7b-instruct-q4_k_m.gguf", "qwen2.5-coder", "7b"),
    "coder-3b": ("qwen2.5-coder-3b-instruct-q4_k_m.gguf", "qwen2.5-coder", "3b"),
    "chat-8b": ("qwen3-8b-q4_k_m.gguf", "qwen3", "8b"),  # general: conversation, research, Tanglish
    # Qwen3.5 (2026), only as GGUF files in models/ (D: HDD: the first load is slower)
    "q35-4b": ("Qwen3.5-4B-Q4_K_M.gguf", None, None),
    "q35-2b": ("Qwen3.5-2B-Q4_K_M.gguf", None, None),  # an 8 GB PC's model (firstrun.py picks it at install)
    "q35-9b": ("Qwen3.5-9B-Q4_K_M.gguf", None, None),
    # IBM Granite 4.2 3B (Aug 2026, Apache-2.0): LiveCodeBench v6 69.7 in IBM's card (probably thinking on); a
    # 2.24 GB file, so ~2x the 7B's generation speed here. Run without thinking (minutes per answer on this CPU)
    "granite-3b": ("granite-4.2-3b-Q4_K_M.gguf", None, None),
}
# flash attention OFF: measured on a 1,900-token edit prompt here, generation granite-3b 10.4 -> 15.2 tok/s,
# q35-4b 8.6 -> 11.1 (prefill 67 -> 104/s), coder-7b 9.0 -> 10.1. (It was on since the first setup.)
FLASH_ATTN = "off"
NO_THINKING = ["--reasoning", "off"]  # Qwen3 / 3.5 "thinking" costs minutes of tokens on a CPU
# q35-9b: the iGPU (Vulkan) fails to allocate with the default 512-token batch; 128 works (prefill 54 t/s
# vs 31 on the CPU alone, measured with llama-bench)
EXTRA_ARGS = {"chat-8b": NO_THINKING, "q35-4b": NO_THINKING, "q35-2b": NO_THINKING, "q35-9b": NO_THINKING + ["-ub", "128"],
              "granite-3b": NO_THINKING}
# Speculative decoding: a small model of the same family (same tokenizer) guesses the next tokens, the big one
# checks them all in one pass. Generation is bound by RAM bandwidth here (~10 tok/s for a 7B), so the checked
# guesses are the speed-up; every token is still the big model's choice, so the output doesn't change.
DRAFTS = {"coder-7b": "qwen2.5-coder-0.5b-instruct-q8_0.gguf", "coder-3b": "qwen2.5-coder-0.5b-instruct-q8_0.gguf"}
# Measured once on a 300-token HTML answer from coder-7b (2026-10-14): no draft 9.4 tok/s; 8 guesses with no
# cut-off 8.4 (slower: the 0.5B shares the RAM bandwidth and kept guessing unlikely tokens); 6 guesses, stop when
# the draft is under 75% sure: 12.6 tok/s, 81% of guesses accepted (4 at 0.6: 11.5, 6 at 0.85: 11.9)
DRAFT_MAX = 6  # tokens guessed at a time
DRAFT_P_MIN = 0.75  # stop guessing when the draft model is less sure than this
SPEC_TYPE = "draft-simple,ngram-simple"  # the draft model, and the copy-from-the-prompt guesses (edits) as before


# copy-from-the-prompt guesses (n-gram) for the models that edit code: a fix repeats most of the old file. On the
# chat models they were mostly wrong (4-8% accepted on the 9B's replies) and cost speed (6.2 -> 5.0 tok/s)
NGRAM_MODELS = {"coder-7b", "coder-3b", "granite-3b"}


def thinks(target):
    """The model has a thinking mode (M42 runs it with thinking off and can turn it on for one request)."""
    key = target[len(PREFIX):] if (target or "").startswith(PREFIX) else target
    return all(a in (EXTRA_ARGS.get(key) or []) for a in NO_THINKING)


def spec_args(key):
    """--spec-type for `key`: the draft model (+ n-gram) for the coders that have one, n-gram for the other code
    models (built in, or downloaded for code on the Models page), nothing for chat models."""
    if draft_args(key):
        return ["--spec-type", SPEC_TYPE]
    custom = (_read_custom().get("models") or {}).get(key) or {}
    if key in NGRAM_MODELS or custom.get("kind") == "code":
        return ["--spec-type", "ngram-simple"]
    return []


def draft_args(key):
    """The draft-model arguments for `key`, or [] when it has none (or its file isn't in models/)."""
    name = DRAFTS.get(key)
    path = (MODELS_DIR / name) if name else None
    if not path or not path.exists():
        return []
    return ["-md", str(path), "-ngld", "0", "--spec-draft-n-max", str(DRAFT_MAX), "-td", "6",
            "--spec-draft-p-min", str(DRAFT_P_MIN)]
# models loaded with their image file every time: reloading the 4B with it to read a reference cost 13 s in the
# middle of each web request (2026-11-03, the user: "already 4b la thana irukku"). The 9B keeps loading it only for
# a picture (with it kept, its text prefill fell from 52 to 21.6 t/s on the iGPU)
VISION_ALWAYS = {"q35-4b", "q35-2b"}
AUTO = PREFIX + "auto"  # M42 UI: one model for everything
# Qwen3.5-4B writes the page plans, reads the reference pictures and writes the page code (M42 UI, 2026-11-05:
# no 7B coder: as fast per token here, and a model switch cost 10-30 s each time)
AUTO_TARGETS = {"chat": PREFIX + "q35-4b", "code": PREFIX + "q35-4b"}
AUTO_COMBOS = {AUTO: AUTO_TARGETS}


def is_auto(model):
    return model in AUTO_COMBOS


def targets(model):
    """The chat / code models of an Auto choice (the first Auto for anything else)."""
    return AUTO_COMBOS.get(model, AUTO_TARGETS)


def set_port(port):
    """Use another port (e.g. a second M42 instance for testing next to the user's)."""
    global PORT, URL, LOG
    PORT = int(port)
    URL = f"http://127.0.0.1:{PORT}/v1"
    LOG = LOG.with_name(f"llama-server-{PORT}.log")


def is_local(model):
    return (model or "").startswith(PREFIX)


# multimodal projectors in models/ (screenshots in reports). The 9B's is optional: with it, "Auto quality" reads
# pictures with the 9B itself instead of switching to the 4B (~40 s each way)
VISION = {"q35-4b": "Qwen3.5-4B-mmproj-F16.gguf", "q35-2b": "Qwen3.5-2B-mmproj-F16.gguf", "q35-9b": "Qwen3.5-9B-mmproj-F16.gguf"}


def vision_file(key):
    p = MODELS_DIR / VISION[key] if key in VISION else None
    if not p or not p.exists():
        return None
    st = p.stat()
    # big enough, and not still growing (a download in progress would make llama-server fail to start)
    return p if st.st_size > 100_000_000 and time.time() - st.st_mtime > 30 else None


def vision_model(prefer=None):
    """The model that can look at images, if its projector file is there: `prefer` (the chat model the user chose)
    when it can, else the first that can."""
    key = (prefer or "")[len(PREFIX):] if is_local(prefer) else None
    if key in VISION and vision_file(key) and model_path(key):
        return PREFIX + key
    return next((PREFIX + k for k in VISION if vision_file(k) and model_path(k)), None)


def model_path(key):
    """Prefer Ollama's blob (same GGUF; on this PC it sits on the NVMe SSD: ~3 s load vs ~32 s from
    the HDD copy in models/). Fall back to the copy if Ollama's model was removed."""
    if key not in MODELS:
        return None
    copy, name, tag = MODELS[key]
    if not name:
        p = MODELS_DIR / copy
        return p if p.exists() and p.stat().st_size > 100_000_000 else None  # not while still downloading
    manifest = OLLAMA_STORE / "manifests" / "registry.ollama.ai" / "library" / name / tag
    try:
        layers = json.loads(manifest.read_text(encoding="utf-8"))["layers"]
        digest = next(l["digest"] for l in layers if l["mediaType"].endswith(".model"))
        blob = OLLAMA_STORE / "blobs" / digest.replace(":", "-")
        if blob.exists():
            return blob
    except (OSError, ValueError, KeyError, StopIteration):
        pass
    p = MODELS_DIR / copy
    return p if p.exists() else None


def available_models():
    if not hardware.builds():
        return []
    found = [PREFIX + k for k in MODELS if model_path(k)]
    autos = [name for name, combo in AUTO_COMBOS.items() if all(t in found for t in combo.values())]
    return autos + found


def base_url_for(config):
    return URL if is_local(config.get("model")) else config["base_url"]


class _KillOnCloseJob:
    """Windows job object: child processes die when M42 exits, even if it crashes."""

    def __init__(self):
        self.handle = None
        if os.name != "nt":
            return
        k32 = ctypes.windll.kernel32
        self.handle = k32.CreateJobObjectW(None, None)

        class LIMIT(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                        ("SchedulingClass", ctypes.c_uint32)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rb", "wb", "ob")]

        class EXT(ctypes.Structure):
            _fields_ = [("Basic", LIMIT), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        info = EXT()
        info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info))

    def add(self, proc):
        if self.handle:
            ctypes.windll.kernel32.AssignProcessToJobObject(self.handle, int(proc._handle))
        elif os.name != "nt":  # Linux / macOS: no job objects; the server is stopped when M42 exits
            import atexit
            atexit.register(lambda: proc.poll() is None and proc.terminate())


def _gpu_setting():
    """ "auto" (a graphics card is used when there is one) or "off", from config.json's "gpu"."""
    try:
        return str(json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8")).get("gpu") or "auto")
    except (OSError, ValueError):
        return "auto"


class LlamaServer:
    def __init__(self):
        self.proc = None
        self.model = None
        self.state = "stopped"  # stopped | loading | ready | error
        self.error = ""
        self.vision = False  # started with the image projector
        self.hardware = {}  # how it was started on this PC (hardware.plan)
        self._lock = threading.Lock()
        self._job = _KillOnCloseJob()

    def ensure(self, model, ctx_tokens=16384, vision=False):
        """Make sure llama-server is running `model` (e.g. 'llama.cpp/coder-7b'). Blocks until ready.
        vision: also load the model's image projector (only for screenshots: it adds ~0.7 GB and a slower
        load). Only while a picture is read: the next text request loads the model again without it."""
        with self._lock:
            key = model[len(PREFIX):]
            vision = vision_file(key) if (vision or key in VISION_ALWAYS) else None
            if (self.proc and self.proc.poll() is None and self.model == key and self.state == "ready"
                    and self.vision == bool(vision)):  # the image file only while a picture is read: kept
                # loaded, it took the iGPU's memory and the 9B read text at 21.6 tok/s instead of 52
                return True
            self._stop_locked()
            gguf = model_path(key)
            # this PC's own start-up (hardware.py): a graphics card takes the layers, else the processor's settings
            hw = hardware.plan(_gpu_setting(), need_mb=(gguf.stat().st_size >> 20) if gguf else 0)
            if gguf is None or not hw["exe"]:
                self.state, self.error = "error", f"llama.cpp model files for '{key}' not found"
                return False
            self.hardware = hw
            LOG.parent.mkdir(exist_ok=True)
            args = [str(hw["exe"]), "-m", str(gguf), "--alias", model, "--host", "127.0.0.1", "--port", str(PORT)] + hw["args"] + [
                    "-c", str(int(ctx_tokens)), "--jinja", "-np", "1",
                    "--no-webui"] + spec_args(key) + ["--cache-reuse", "256",
                    "--cache-ram", "1024", "--slot-save-path", str(SLOT_DIR)] + EXTRA_ARGS.get(key, []) + draft_args(key)
            if vision:  # Qwen3.5 sees images with its projector; 512 tokens per image keeps CPU encoding short
                args += ["--mmproj", str(vision), "--image-max-tokens", "512"]
            SLOT_DIR.mkdir(parents=True, exist_ok=True)
            log = open(LOG, "w", encoding="utf-8", errors="replace")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            env = None if os.name == "nt" else dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(  # (its .so files beside it)
                x for x in (str(Path(hw["exe"]).parent), os.environ.get("LD_LIBRARY_PATH", "")) if x))
            self.proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, creationflags=flags, env=env)
            self._job.add(self.proc)
            self.model, self.state, self.error, self.vision = key, "loading", "", bool(vision)
            proc = self.proc
        deadline = time.time() + 180
        while time.time() < deadline:
            if proc.poll() is not None:
                if hw["gpu"] and not hardware.GPU_FAILED:
                    # the graphics card could not take it (a driver, its memory): once more on the processor, and the
                    # processor for the rest of this run
                    hardware.GPU_FAILED = True
                    return self.ensure(model, ctx_tokens, bool(vision))
                self.state, self.error = "error", f"llama-server exited (see {LOG})"
                return False
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                    if r.status == 200:
                        self.state = "ready"
                        return True
            except OSError:
                pass
            time.sleep(0.5)
        self.state, self.error = "error", "llama-server did not become ready in 180 s"
        return False

    def _slot_action(self, action, filename):
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/slots/0?action={action}", method="POST",
                                     data=json.dumps({"filename": filename}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status == 200
        except OSError:
            return False

    def restore_prompt_cache(self, filename):
        """Load a saved KV cache (seconds) instead of re-reading the system prompt (~27 s on CPU)."""
        return (SLOT_DIR / filename).exists() and self._slot_action("restore", filename)

    def save_prompt_cache(self, filename):
        ok = self._slot_action("save", filename)
        caches = sorted(SLOT_DIR.glob("*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in caches[4:]:  # keep the 4 most recent prompts (model / workspace / settings combos)
            old.unlink(missing_ok=True)
        return ok

    def hold_cache(self, filename=HOLD_FILE):
        """Save the model's cache as it is now (this chat so far) before a short side request (the task decision,
        a lesson), so restore_prompt_cache(HOLD_FILE) puts the whole chat back instead of re-reading it. Not a
        .bin: the pruning of saved prompts above leaves it alone."""
        return self.state == "ready" and self._slot_action("save", filename)

    def stop(self):
        with self._lock:
            self._stop_locked()

    def _stop_locked(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc, self.model, self.state, self.vision = None, None, "stopped", False


# ---- models downloaded from the 🧩 Models page (modelhub.py) -------------------------------------------------------
CUSTOM_FILE = Path(os.environ.get("M42_MODELS_FILE") or MODELS_DIR / "m42-models.json")  # (the env: tests) {"models": {key: {file, kind, repo, added}}, "auto": {chat, code}}
MY_AUTO = PREFIX + "auto-my"  # "🔀 My auto": the chat and code models the user picked on the Models page
_KEY_RX = re.compile(r"^[a-z0-9][a-z0-9._-]{1,40}$")
_SLUG_RX = re.compile(r"^[a-z0-9][a-z0-9-]{0,24}$")
COMBO_NAMES = {}  # "llama.cpp/auto-my-tamil" -> "Tamil" (the name the user gave the pair)
_FILE_RX = re.compile(r"^[\w.+-]+\.gguf$")


def _read_custom():
    try:
        data = json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_custom():
    """Add the downloaded models to MODELS (thinking off, like the other chat models) and the user's own Auto."""
    data = _read_custom()
    for key, m in (data.get("models") or {}).items():
        if _KEY_RX.match(key) and _FILE_RX.match(str(m.get("file", ""))) and (key not in MODELS or key in CUSTOM_KEYS):
            path = MODELS_DIR / m["file"]
            from modelhub import gguf_arch  # (modelhub imports this module: here, when it is needed)
            if path.exists() and gguf_arch(path) in (None, "clip"):
                continue  # not a model llama.cpp chats with (Qwen-Image's denoiser was listed as a chat model)
            MODELS[key] = (m["file"], None, None)
            big = path.exists() and path.stat().st_size > 5 * 2 ** 30  # like q35-9b: the iGPU needs a smaller batch
            EXTRA_ARGS.setdefault(key, NO_THINKING + (["-ub", "128"] if big else []))
            CUSTOM_KEYS.add(key)
            if _FILE_RX.match(str(m.get("mmproj", ""))):  # its vision part: it reads pictures itself
                VISION[key] = m["mmproj"]
    # the user's chat + code pairs: "auto" is the first one (⚙ Custom, "llama.cpp/auto-my"), "combos" the named ones
    # ("llama.cpp/auto-my-tamil"); each is an Auto of its own in the model list
    known = [PREFIX + k for k in MODELS]
    for cid in [c for c in AUTO_COMBOS if c == MY_AUTO or c.startswith(MY_AUTO + "-")]:
        AUTO_COMBOS.pop(cid, None)
        COMBO_NAMES.pop(cid, None)
    pairs = [(MY_AUTO, data.get("auto_name") or "Custom", data.get("auto") or {})] + [
        (f"{MY_AUTO}-{slug}", c.get("name") or slug, c) for slug, c in (data.get("combos") or {}).items()
        if _SLUG_RX.match(slug) and isinstance(c, dict)]
    for cid, name, c in pairs:
        if c.get("chat") in known and c.get("code") in known:
            AUTO_COMBOS[cid] = {"chat": c["chat"], "code": c["code"]}
            COMBO_NAMES[cid] = name
    return data


def combos():
    """The user's chat + code pairs, for the picker and the model list: [{id, name, chat, code}]."""
    return [{"id": cid, "name": COMBO_NAMES.get(cid, "Custom"), **AUTO_COMBOS[cid]}
            for cid in AUTO_COMBOS if cid == MY_AUTO or cid.startswith(MY_AUTO + "-")]


def save_combo(name, chat, code, combo_id=""):
    """A named pair (new, or the one `combo_id` names): any two models on this PC. Returns its id."""
    name = " ".join(str(name or "").split())[:30]
    if not name:
        raise ValueError("give the combo a name")
    local = [PREFIX + k for k in MODELS if model_path(k)]
    if chat not in local or code not in local:
        raise ValueError("pick two models that are on this PC")
    data = _read_custom()
    same = next((c["id"] for c in combos() if c["name"].lower() == name.lower()), None)
    if same and same != combo_id:
        raise ValueError(f"a combo called “{name}” is there already: edit that one or pick another name")
    if combo_id == MY_AUTO or (not combo_id and not data.get("auto")):  # the first pair stays ⚙ Custom's
        data["auto"], data["auto_name"] = {"chat": chat, "code": code}, name
        cid = MY_AUTO
    else:
        group = data.setdefault("combos", {})
        slug = combo_id[len(MY_AUTO) + 1:] if combo_id.startswith(MY_AUTO + "-") else ""
        if slug not in group:
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:20] or "combo"
            slug, n = base, 2
            while slug in group:
                slug, n = f"{base}-{n}", n + 1
        group[slug] = {"name": name, "chat": chat, "code": code}
        cid = f"{MY_AUTO}-{slug}"
    _write_custom(data)
    return cid


def delete_combo(combo_id):
    data = _read_custom()
    if combo_id == MY_AUTO:
        data.pop("auto", None)
        data.pop("auto_name", None)
    elif combo_id.startswith(MY_AUTO + "-") and combo_id[len(MY_AUTO) + 1:] in (data.get("combos") or {}):
        del data["combos"][combo_id[len(MY_AUTO) + 1:]]
    else:
        raise ValueError("no such combo")
    _write_custom(data)


def custom_repo(key):
    return ((_read_custom().get("models") or {}).get(key) or {}).get("repo")


def add_custom(key, file, kind, repo, mmproj=None):
    data = _read_custom()
    data.setdefault("models", {})[key] = dict({"file": file, "kind": kind, "repo": repo, "added": time.time()},
                                              **({"mmproj": mmproj} if mmproj else {}))
    _write_custom(data)


def use_custom(model, kind):
    """The model for chat or code in "🔀 My auto" (the other slot starts as the normal Auto's)."""
    if kind not in ("chat", "code") or model not in [PREFIX + k for k in MODELS]:
        raise ValueError("unknown model")
    data = _read_custom()
    auto = data.get("auto") or dict(AUTO_COMBOS.get(MY_AUTO) or AUTO_TARGETS)
    auto[kind] = model
    data["auto"] = auto
    _write_custom(data)


def set_custom_auto(chat, code):
    """"⚙ Custom" in the model list: any two models on this PC, one for chat and one for code."""
    return save_combo(_read_custom().get("auto_name") or "Custom", chat, code, MY_AUTO)


def local_info():
    """The models on this PC with their file size (for the Custom picker)."""
    out = []
    for key in MODELS:
        path = model_path(key)
        if path:
            out.append({"model": PREFIX + key, "size_gb": round(path.stat().st_size / 2 ** 30, 2),
                        "vision": key in VISION, "draft": bool(draft_args(key))})
    return out


def _write_custom(data):
    tmp = CUSTOM_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(CUSTOM_FILE)
    load_custom()


CUSTOM_KEYS = set()

def _tier_model():
    """The Auto model of this PC: the one the installer picked (config.json "model_tier": 2b on an 8 GB PC), else the
    4B, else the 2B, whichever file is here."""
    try:
        tier = json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8")).get("model_tier")
    except (OSError, ValueError):
        tier = None
    order = ["q35-2b", "q35-4b"] if tier == "2b" else ["q35-4b", "q35-2b"]
    return next((k for k in order if model_path(k)), None)


_AUTO_FIRST = {k: dict(v) for k, v in AUTO_COMBOS.items()}  # (as written above: the 4B)


def refresh_auto():
    """Auto's models for the files here now (at start, and again after the first-run download)."""
    auto = _tier_model()
    for name, combo in AUTO_COMBOS.items():
        combo.update(_AUTO_FIRST.get(name, {}))
        for role in ("chat", "code"):
            if combo.get(role) == PREFIX + "q35-4b":
                if auto and auto != "q35-4b":  # an 8 GB PC: everything Auto did with the 4B, done by the 2B
                    combo[role] = PREFIX + auto
                elif not auto and role == "chat":  # no Qwen3.5 file at all: auto mode chats with Qwen3-8B again
                    combo[role] = PREFIX + "chat-8b"
    return auto


refresh_auto()

load_custom()  # the models downloaded from the Models page
