"""🧩 Models page: new GGUF models on Hugging Face that fit this PC, for chat and for code, downloaded into models/
(on D:) and usable in M42 right away ("🔀 My auto": your chat model + your code model).

Only quantized copies of models from known labs (Qwen, Google, Meta, Mistral, IBM, DeepSeek...), published by the
usual GGUF uploaders, are listed: the newest uploads are mostly personal fine-tunes and merges. Size and speed come
from this PC: the file must fit in RAM next to Windows, and generation here is bound by RAM bandwidth (~45 GB/s
measured: ~35 GB/s effective), so tok/s ≈ 35 / GB read per token (only the active experts of a MoE)."""
import ctypes
import struct
import hashlib
import json
import os
import re
import shutil
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import llamacpp

APP_DIR = Path(__file__).resolve().parent
CACHE = APP_DIR / "cache" / "modelhub.json"
CACHE_TTL = 12 * 3600
API = "https://huggingface.co/api"
UA = {"User-Agent": "M42-local-AI/1.0"}
AUTHORS = ["unsloth", "bartowski", "lmstudio-community", "ggml-org", "Qwen"]  # preferred first
LABS = {"qwen", "meta-llama", "google", "mistralai", "microsoft", "ibm-granite", "deepseek-ai", "openai", "nvidia",
        "allenai", "huggingfacetb", "zai-org", "thudm", "inclusionai", "openbmb", "liquidai", "tiiuae", "coherelabs",
        "cohereforai", "servicenow-ai", "moonshotai", "bigcode", "baidu", "tencent", "stepfun-ai", "minimaxai",
        "swiss-ai", "aleph-alpha", "ai21labs", "internlm", "upstage", "nousresearch", "xiaomimimo", "kwaipilot",
        "arcee-ai", "bytedance-seed", "apple", "salesforce", "lgai-exaone", "sarvamai", "mistral-ai"}
# Hugging Face's task / tags of a repo that is not a chat or code model (Qwen-Image-2.1-GGUF: text-to-image, a
# diffusion denoiser llama.cpp cannot run, was offered as a "chat" model)
NOT_LLM = {"text-to-image", "image-to-image", "image-generation", "text-to-video", "image-to-video", "video-generation",
           "text-to-speech", "text-to-audio", "automatic-speech-recognition", "audio-to-audio", "diffusers",
           "feature-extraction", "sentence-similarity", "image-segmentation", "depth-estimation", "unconditional-image-generation"}


def not_llm(r):
    """The repo is an image / video / speech / embedding model, by its own task and tags."""
    return bool(({r.get("pipeline_tag")} | set(r.get("tags") or [])) & NOT_LLM)


def gguf_arch(path):
    """general.architecture from a GGUF's header ("qwen2", "qwen35", "granite"...), or None: a GGUF without it (a
    diffusion denoiser for stable-diffusion.cpp) is not a model llama.cpp can chat with."""
    sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"GGUF":
                return None
            f.read(4)
            _, nkv = struct.unpack("<QQ", f.read(16))

            def text():
                n, = struct.unpack("<Q", f.read(8))
                return f.read(n).decode("utf-8", "replace")

            def skip(t):
                if t == 8:
                    text()
                elif t == 9:
                    at, n = struct.unpack("<IQ", f.read(12))
                    for _ in range(n):
                        skip(at)
                else:
                    f.read(sizes[t])
            for _ in range(min(nkv, 64)):
                key = text()
                t, = struct.unpack("<I", f.read(4))
                if key == "general.architecture" and t == 8:
                    return text()
                skip(t)
    except (OSError, struct.error, KeyError):
        return None
    return None


SKIP_RX = re.compile(r"embed|rerank|guard|safety|tts|whisper|asr|ocr|abliterat|uncensor|nsfw|roleplay|\brp\b|merge|"
                     r"mmproj|reward|\bprm\b|classifier|-base\b|preview-only", re.I)
CODE_RX = re.compile(r"coder|codestral|devstral|starcoder|codegemma|deepcoder|code-?llama|codeqwen|\bswe\b|"
                     r"seed-coder|\bcode\b", re.I)
# general model families (a lab's niche releases, e.g. GUI agents or user simulators, are left out)
FAMILY_RX = re.compile(r"^(?:[a-z0-9-]+_)?(qwen|llama|gemma|mistral|ministral|magistral|devstral|codestral|phi|granite|"
                       r"deepseek|glm|olmo|smollm|exaone|falcon|command|c4ai|nemotron|hunyuan|ernie|minicpm|lfm|mimo|"
                       r"kimi|seed|gpt-oss|apertus|aya|internlm|ling|starcoder|codegemma|qwq|step|minimax|sarvam|hermes|kat)",
                       re.I)
# where to look: each uploader's newest repos, and searches that reach coder models older than those
SEARCHES = ["", "coder", "qwen", "gemma", "llama", "granite", "phi", "mistral", "deepseek", "glm"]
SOURCES = [f"author={a}" + (f"&search={q}" if q else "") for a in AUTHORS for q in SEARCHES]
PER_FAMILY = 2  # at most two of one family per list (four MiMo variants filled the chat list)
MIN_PARAMS_B = 1.0  # smaller ones (135M) can't follow M42's instructions
MIN_FILE_GB = 0.8  # below this a "model" file is a projector or a tiny model
BIG_PER_KIND = 5  # newest models that need more RAM: for a future upgrade
QUANTS = ["Q4_K_M", "Q4_K_S", "IQ4_XS", "Q4_0", "Q5_K_M"]  # the first one a repo has, as one file
BANDWIDTH_GBS = 35  # effective: q35-4b 2.6 GB x 11.1, q35-9b 5.3 GB x 6.1, granite-3b 2.1 GB x 15.2 tok/s
# tok/s measured on this PC (generation; coder-7b with its draft), shown instead of the estimate
MEASURED = {"coder-7b": 11.9, "q35-4b": 11.1, "q35-9b": 6.1, "granite-3b": 15.2}
MAX_AGE_DAYS = 400
PER_KIND = 12
REPO_RX = re.compile(r"^[\w.-]+/[\w.-]+$")
FILE_RX = re.compile(r"^[\w.+-]+\.gguf$")
_jobs = {}
_lock = threading.Lock()


# ---- this PC -----------------------------------------------------------------------------------------------------

def hardware():
    """RAM (what Windows can use; the iGPU keeps some), free space where models go, CPU threads, and the largest
    model file that still leaves room for Windows, the app and the context."""
    ram = 0.0
    if os.name == "nt":
        class Mem(ctypes.Structure):
            _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong) for n in ("total", "avail", "tp", "ap", "tv", "av", "ae")]
        m = Mem()
        m.len = ctypes.sizeof(Mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            ram = m.total / 2 ** 30
    else:  # Linux / macOS
        import firstrun
        ram = firstrun.ram_gb()
    llamacpp.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(llamacpp.MODELS_DIR).free / 2 ** 30
    budget = max(2.0, ram - 5.0) if ram else 8.0
    return {"ram_gb": round(ram, 1), "free_gb": round(free, 1), "cpus": os.cpu_count() or 0,
            "max_file_gb": round(budget, 1), "folder": str(llamacpp.MODELS_DIR), "bandwidth_gbs": BANDWIDTH_GBS}


def params(name):
    """(total billions, active billions) from a name: 'Qwen3.6-35B-A3B' -> (35, 3); '7B' -> (7, 7)."""
    m = re.search(r"(?<![\d.A-Za-z])(\d+(?:\.\d+)?)\s*([bBtT])(?:[-_]A(\d+(?:\.\d+)?)[bB])?(?![a-z])", name)
    if not m:
        return None, None
    total = float(m.group(1)) * (1000 if m.group(2) in "tT" else 1)
    if m.group(3):
        return total, float(m.group(3))
    return total, total


def speed(size_gb, name):
    total, active = params(name)
    read = size_gb * (active / total if total and active and active < total else 1)
    return round(BANDWIDTH_GBS / max(read, 0.3) * 0.95, 1)


# ---- Hugging Face ------------------------------------------------------------------------------------------------

def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _base(tags):
    for t in tags or []:
        if t.startswith("base_model:quantized:"):
            return t.split(":", 2)[2]
    for t in tags or []:
        if t.startswith("base_model:") and t.count(":") == 1:
            return t.split(":", 1)[1]
    return ""


def _candidates():
    """Recent GGUF repos of the usual uploaders whose base model is a known lab's general model, one per base."""
    seen, out = set(), []
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    def listing(source):
        try:
            return _get(f"{API}/models?{source}&filter=gguf&sort=createdAt&direction=-1&limit=100")
        except (OSError, ValueError):
            return []
    with ThreadPoolExecutor(8) as pool:
        found = [r for repos in pool.map(listing, SOURCES) for r in repos]
    for r in found:
        if True:
            rid, tags = r.get("id", ""), r.get("tags") or []
            author, name = (rid.split("/", 1) + [""])[:2]
            if author not in AUTHORS:
                continue
            base = _base(tags) or (rid if author == "Qwen" else "")
            org = base.split("/")[0].lower()
            created = r.get("createdAt") or ""
            try:
                ts = time.mktime(time.strptime(created[:19], "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                ts = 0
            if (not base or org not in LABS or SKIP_RX.search(rid) or ts < cutoff or not FAMILY_RX.match(name)
                    or r.get("pipeline_tag") not in (None, "text-generation", "image-text-to-text") or not_llm(r)):
                continue
            key = base.lower().removesuffix("-gguf")
            if key in seen:
                continue
            total, _ = params(name)
            if total is not None and total < MIN_PARAMS_B:
                continue
            seen.add(key)
            lic = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), "")
            out.append({"repo": rid, "base": base, "created": created[:10], "ts": ts, "downloads": r.get("downloads", 0),
                        "likes": r.get("likes", 0), "license": lic, "vision": r.get("pipeline_tag") == "image-text-to-text"})
    out.sort(key=lambda c: -c["ts"])
    return out[:120]


def _pick_file(c):
    """The Q4-ish single file of a repo, with its size and SHA-256 (None if the repo only has split files)."""
    try:
        tree = _get(f"{API}/models/{c['repo']}/tree/main")
    except (OSError, ValueError):
        return None
    files = {f["path"]: f for f in tree if f.get("type") == "file" and f["path"].lower().endswith(".gguf")
             and "mmproj" not in f["path"].lower() and not re.search(r"-\d{5}-of-\d{5}", f["path"])}
    total, _ = params(c["repo"])
    if not any(q.lower() in p.lower() for p in files for q in QUANTS):
        if total and total * 0.6 > 9:  # only split files: a big model, listed with the RAM it would need
            return dict(c, file="", size_gb=round(total * 0.6, 1), bytes=0, sha256="", quant="Q4 (split)",
                        released=c["created"], big=True)
        return None
    for q in QUANTS:
        for path, f in files.items():
            if q.lower() in path.lower():
                lfs = f.get("lfs") or {}
                size = lfs.get("size") or f.get("size") or 0
                if (total and size / 2 ** 30 < total * 0.4) or size / 2 ** 30 < MIN_FILE_GB:
                    return None  # not the whole model (a 106B model's 2.5 GB part, a projector)
                try:  # when the model itself came out (re-uploads of Llama-2 looked new)
                    released = (_get(f"{API}/models/{c['base']}").get("createdAt") or c["created"])[:10]
                except (OSError, ValueError):
                    released = c["created"]
                return dict(c, file=path, size_gb=round(size / 2 ** 30, 2), bytes=size, sha256=lfs.get("oid", ""),
                            quant=q, released=released)
    return None


def search(query, limit=15):
    """The user's own search ("qwen3.8 coder", "gemma 4"): GGUF repos from the usual uploaders or a lab itself,
    most downloaded first, each with its Q4 file, size, speed here and whether it fits (else the RAM it needs)."""
    words = [w.lower() for w in re.findall(r"[\w.+]+", query or "")][:6]
    if not words or len("".join(words)) < 2:
        return []
    # Hugging Face matches the text inside the name as typed ("qwen3.5 coder" finds nothing): search the longest
    # word, then keep the names that have every word
    repos = _get(f"{API}/models?search={urllib.parse.quote(max(words, key=len))}&filter=gguf&sort=downloads"
                 f"&direction=-1&limit=100")
    trusted = {a.lower() for a in AUTHORS} | LABS
    cands = []
    for r in repos:
        rid, tags = r.get("id", ""), r.get("tags") or []
        flat = re.sub(r"[-_ ]", "", rid.lower())
        if (rid.split("/")[0].lower() not in trusted or SKIP_RX.search(rid) or not_llm(r)
                or not all(re.sub(r"[-_ ]", "", w) in flat for w in words)):
            continue
        cands.append({"repo": rid, "base": _base(tags) or rid, "created": (r.get("createdAt") or "")[:10], "ts": 0,
                      "downloads": r.get("downloads", 0), "likes": r.get("likes", 0),
                      "license": next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), ""),
                      "vision": r.get("pipeline_tag") == "image-text-to-text"})
        if len(cands) >= limit:
            break
    hw = hardware()
    with ThreadPoolExecutor(6) as pool:
        found = [p for p in pool.map(_pick_file, cands) if p]
    for p in found:
        p["kind"] = "code" if CODE_RX.search(p["repo"]) else "chat"
        p["installed"] = bool(p["file"]) and (llamacpp.MODELS_DIR / p["file"]).is_file()
        p["fits"] = not p.get("big") and p["size_gb"] <= hw["max_file_gb"]
        p["tok_s"] = speed(p["size_gb"], p["repo"])
        p["fit"] = ("good" if p["tok_s"] >= 8 else "slow" if p["tok_s"] >= 4 else "very slow") if p["fits"] else \
            "too big"
        p["needs_ram_gb"] = int(p["size_gb"] + 5.5)
    return found


def scan(refresh=False):
    """The list for the page (cached for 12 h): {"chat": [...], "code": [...], "scanned": time}."""
    if not refresh:
        try:
            data = json.loads(CACHE.read_text(encoding="utf-8"))
            if time.time() - data.get("scanned", 0) < CACHE_TTL:
                return data
        except (OSError, ValueError):
            pass
    hw = hardware()
    with ThreadPoolExecutor(6) as pool:
        picked = [p for p in pool.map(_pick_file, _candidates()) if p]
    lists, families, big = {"chat": [], "code": []}, {}, {"chat": [], "code": []}
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - MAX_AGE_DAYS * 86400))
    picked.sort(key=lambda p: p["released"], reverse=True)  # newest models first
    for p in picked:
        if p["released"] < cutoff:
            continue
        kind = "code" if CODE_RX.search(p["repo"]) else "chat"
        if p.get("big") or p["size_gb"] > hw["max_file_gb"]:  # for later: the RAM it needs (file + ~5 GB)
            if len(big[kind]) < BIG_PER_KIND:
                big[kind].append(dict(p, needs_ram_gb=int(p["size_gb"] + 5.5)))
            continue
        fam = FAMILY_RX.match(p["repo"].split("/")[1]).group(1).lower()
        if families.get(fam, 0) >= PER_FAMILY:
            continue
        p["tok_s"] = speed(p["size_gb"], p["repo"])
        p["fit"] = "good" if p["tok_s"] >= 8 else "slow" if p["tok_s"] >= 4 else "very slow"
        if len(lists[kind]) < PER_KIND:
            lists[kind].append(p)
            families[fam] = families.get(fam, 0) + 1
    data = dict(lists, big=big, scanned=time.time())
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


# ---- new since the user last looked ------------------------------------------------------------------------------

SEEN = APP_DIR / "cache" / "modelhub-seen.json"  # the models the Models page has shown (not "new" any more)


def _listed(data):
    return [p["repo"] for kind in ("chat", "code") for p in data.get(kind, [])]


def new_count():
    """How many models in the last scan the user hasn't seen on the page (from the cache: no network)."""
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    try:
        seen = set(json.loads(SEEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return 0  # the first time: nothing is "new" until the page has been opened once
    return sum(r not in seen for r in _listed(data))


def seen_set():
    """The repos already shown, or None before the page was ever opened (then nothing is marked new)."""
    try:
        return set(json.loads(SEEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def mark_seen(data):
    try:
        seen = set(json.loads(SEEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        seen = set()
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen | set(_listed(data)))), encoding="utf-8")


def check_in_background(online):
    """At app start: refresh the list when the 12-hour cache is old (and there is a connection), quietly."""
    def work():
        try:
            if online():
                scan()
        except (OSError, ValueError) as e:
            print(f"Model check skipped: {e}")
    threading.Thread(target=work, daemon=True).start()


# ---- download ----------------------------------------------------------------------------------------------------

def key_for(repo):
    """A short model name for M42's list, from the repo: unsloth/Qwen3.6-7B-Instruct-GGUF -> qwen3.6-7b-instruct."""
    base = re.sub(r"-gguf$", "", repo.split("/")[-1].lower())
    base = re.sub(r"[^a-z0-9.]+", "-", base).strip("-")[:36] or "model"
    key, n = base, 2
    while key in llamacpp.MODELS and llamacpp.custom_repo(key) != repo:  # a built-in or another repo has it
        key, n = f"{base}-{n}", n + 1
    return key


def start(repo, file, size, sha256, kind):
    """Download in the background into models/ (resumes a .part file, checks the size and SHA-256), then add the
    model to M42's list. Returns the job."""
    if not REPO_RX.match(repo or "") or not FILE_RX.match(file or ""):
        raise ValueError("not a Hugging Face model file")
    if kind not in ("chat", "code"):
        raise ValueError("kind must be chat or code")
    size = int(size or 0)
    need = size / 2 ** 30 + 1
    free = hardware()["free_gb"]
    if size <= 0 or free < need:
        raise ValueError(f"Not enough space: {need:.1f} GB needed, {free:.1f} GB free on {llamacpp.MODELS_DIR.drive}")
    with _lock:
        job = _jobs.get(file)
        if job and job["state"] == "downloading":
            return job
        job = _jobs[file] = {"repo": repo, "file": file, "kind": kind, "state": "downloading", "done": 0,
                             "total": size, "error": "", "stop": False, "started": time.time()}
    threading.Thread(target=_download, args=(job, sha256), daemon=True).start()
    return job


def cancel(file):
    with _lock:
        if file in _jobs:
            _jobs[file]["stop"] = True


def jobs():
    with _lock:
        return {f: {k: v for k, v in j.items() if k != "stop"} for f, j in _jobs.items()}


def _download(job, sha256):
    final = llamacpp.MODELS_DIR / job["file"]
    part = final.with_name(final.name + ".part")
    url = f"https://huggingface.co/{job['repo']}/resolve/main/{urllib.parse.quote(job['file'])}"
    h = hashlib.sha256()
    try:
        have = part.stat().st_size if part.exists() else 0
        if have > job["total"]:
            part.unlink()
            have = 0
        if have:  # resume: the hash covers what is already there
            with open(part, "rb") as f:
                for chunk in iter(lambda: f.read(8 << 20), b""):
                    h.update(chunk)
        job["done"] = have
        headers = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r, \
                open(part, "ab" if have and r.status == 206 else "wb") as out:
            if have and r.status != 206:  # the server sent the whole file again
                h, job["done"] = hashlib.sha256(), 0
            for chunk in iter(lambda: r.read(1 << 20), b""):
                if job["stop"]:
                    job["state"] = "stopped"
                    return
                out.write(chunk)
                h.update(chunk)
                job["done"] += len(chunk)
        if job["done"] != job["total"]:
            raise OSError(f"got {job['done']} of {job['total']} bytes (connection lost?): press Download to resume")
        if sha256 and h.hexdigest() != sha256:
            part.unlink()
            raise OSError("the file's SHA-256 does not match Hugging Face's: deleted, download it again")
        part.replace(final)
        if gguf_arch(final) in (None, "clip"):  # downloaded, but not a model llama.cpp chats with (an image denoiser, a projector)
            raise ValueError(f"{final.name} is not a chat / code model (its file names no language-model "
                             "architecture): it is kept in the models folder but not added to the model list")
        key = key_for(job["repo"])
        llamacpp.add_custom(key, job["file"], job["kind"], job["repo"])
        job.update(state="done", key=llamacpp.PREFIX + key)
    except (OSError, ValueError) as e:
        job.update(state="error", error=str(e))


# ---- the user's own GGUF (a model they made or got elsewhere): checked, moved / copied into models/, listed -------
GGUF_TYPES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}  # value type -> bytes (8: string)


def inspect_gguf(path):
    """What the file is, from its GGUF header: {path, file, size_gb, arch, name, context, chat_template, fits,
    warnings}. Raises ValueError when it is not a model M42 can load (not GGUF, a vision projector...)."""
    import struct
    p = Path(path)
    if not p.is_file() or p.suffix.lower() != ".gguf":
        raise ValueError("choose a .gguf model file")
    size = p.stat().st_size
    meta, want = {}, ("general.architecture", "general.name", "general.type", "tokenizer.chat_template")
    with open(p, "rb") as f:
        if f.read(4) != b"GGUF":
            raise ValueError(f"{p.name} is not a GGUF file (its first bytes are not GGUF)")
        version, _tensors, kvs = struct.unpack("<IQQ", f.read(20))
        if version < 2:
            raise ValueError(f"{p.name} is an old GGUF v{version}: convert it again with a newer llama.cpp")

        def string():
            n = struct.unpack("<Q", f.read(8))[0]
            return f.read(n)

        for _ in range(min(kvs, 10000)):
            key = string().decode("utf-8", "replace")
            vtype = struct.unpack("<I", f.read(4))[0]
            if vtype == 8:
                val = string()
                if key in want:
                    meta[key] = val.decode("utf-8", "replace")
            elif vtype == 9:  # an array (the tokenizer's 150k tokens): skipped
                atype, n = struct.unpack("<IQ", f.read(12))
                if atype == 8:
                    for _ in range(n):
                        f.seek(struct.unpack("<Q", f.read(8))[0], 1)
                else:
                    f.seek(GGUF_TYPES.get(atype, 1) * n, 1)
            elif vtype in GGUF_TYPES:
                raw = f.read(GGUF_TYPES[vtype])
                if key.endswith(".context_length"):
                    meta["context"] = int.from_bytes(raw, "little")
            else:
                break  # an unknown type: what was read so far is enough
    arch = meta.get("general.architecture", "?")
    if arch == "clip" or meta.get("general.type") == "mmproj" or "mmproj" in p.name.lower():
        raise ValueError(f"{p.name} is a vision part (mmproj), not a model: choose the main .gguf")
    gb = size / 2 ** 30
    hw = hardware()
    warnings = []
    if gb > hw["max_file_gb"]:
        warnings.append(f"{gb:.1f} GB is more than this PC can run well (up to {hw['max_file_gb']} GB)")
    if size < 100_000_000:
        raise ValueError(f"{p.name} is only {size / 2 ** 20:.0f} MB: too small to be a whole model")
    if not meta.get("tokenizer.chat_template"):
        warnings.append("no chat template inside: llama.cpp will use a default one, answers may look odd")
    proj = mmproj_for(p)
    return {"path": str(p), "file": p.name, "size_gb": round(gb, 2), "arch": arch,
            "name": meta.get("general.name") or p.stem, "context": meta.get("context"),
            "chat_template": bool(meta.get("tokenizer.chat_template")), "tok_s": speed(gb, p.name),
            "mmproj": str(proj) if proj else None, "mmproj_gb": round(proj.stat().st_size / 2 ** 30, 2) if proj else 0,
            "in_folder": p.parent.resolve() == llamacpp.MODELS_DIR.resolve(),
            "same_drive": p.drive.lower() == llamacpp.MODELS_DIR.drive.lower(), "warnings": warnings}


def _base_name(name):
    """"Qwen3.5-4B.Q4_K_M.gguf" and "Qwen3.5-4B.F16-mmproj.gguf" -> "qwen3.5-4b": the model's name without the
    quant / projector parts, to pair a model with its own vision part (another model's would not load)."""
    n = name.lower().removesuffix(".gguf")
    n = re.sub(r"(^|[._-])mmproj([._-]|$)", r"\1", n)
    n = re.split(r"[._-](?:i?q\d\w*|f16|bf16|f32|fp16)(?:[._-]|$)", n)[0]
    return n.strip("._-")


def mmproj_for(model):
    """The vision part (mmproj) next to a model file, with the same model name, or None."""
    model = Path(model)
    base = _base_name(model.name)
    found = [f for f in model.parent.glob("*.gguf") if f != model and "mmproj" in f.name.lower()
             and _base_name(f.name) == base and f.stat().st_size > 50_000_000]
    return sorted(found, key=lambda f: ("f16" not in f.name.lower(), f.stat().st_size))[0] if found else None


def local_key(name):
    """A short name for M42's list: "My-Tamil-Coder Q4_K_M.gguf" -> "my-tamil-coder-q4_k_m"."""
    base = re.sub(r"[^a-z0-9._]+", "-", name.lower().removesuffix(".gguf")).strip("-._")[:36] or "my-model"
    key, n = base, 2
    while key in llamacpp.MODELS and key not in llamacpp.CUSTOM_KEYS:  # never a built-in's name
        key, n = f"{base}-{n}", n + 1
    return key


def import_local(path, kind, mode, vision=True):
    """The user's GGUF into models/ ("move": the file leaves its old place; "copy": it stays there too), with its
    vision part (mmproj) when one sits next to it, then in the model list and set for chat or code in ⚙ Custom.
    A move on the same drive is instant; otherwise a background job like a download (progress, Stop)."""
    if kind not in ("chat", "code") or mode not in ("move", "copy"):
        raise ValueError("kind must be chat or code, mode move or copy")
    info = inspect_gguf(path)
    srcs = [Path(info["path"])] + ([Path(info["mmproj"])] if vision and info.get("mmproj") else [])
    names = [re.sub(r"[^\w.+-]+", "_", s.name) for s in srcs]
    if not all(FILE_RX.match(n) for n in names):
        raise ValueError(f"cannot use the file name {srcs[0].name}")
    dests = [llamacpp.MODELS_DIR / n for n in names]
    file = names[0]
    total = sum(s.stat().st_size for s in srcs)
    job = {"repo": f"your file: {srcs[0]}", "file": file, "kind": kind, "state": "copying" if mode == "copy" else "moving",
           "done": 0, "total": total, "error": "", "stop": False, "started": time.time(),
           "source": str(srcs[0]), "mode": mode, "mmproj": names[1] if len(names) > 1 else None}
    if info["in_folder"]:  # already in models/: only listed
        job.update(state="done", done=total)
    elif any(d.exists() for d in dests):
        taken = next(d for d in dests if d.exists())
        raise ValueError(f"{taken.name} is already in {llamacpp.MODELS_DIR}: rename your file or remove the old one first")
    elif mode == "copy" or not info["same_drive"]:
        free = hardware()["free_gb"]
        if free < total / 2 ** 30 + 1:
            raise ValueError(f"Not enough space: {total / 2 ** 30 + 1:.1f} GB needed, {free:.1f} GB free on "
                             f"{llamacpp.MODELS_DIR.drive}")
    with _lock:
        old = _jobs.get(file)
        if old and old["state"] in ("copying", "moving", "downloading"):
            return old
        _jobs[file] = job
    if job["state"] == "done":
        _finish_import(job, dests[0])
    elif mode == "move" and info["same_drive"]:  # the same drive: a rename, instant
        for s_, d in zip(srcs, dests):
            os.replace(s_, d)
        job["done"] = total
        _finish_import(job, dests[0])
    else:
        threading.Thread(target=_copy, args=(job, srcs, dests), daemon=True).start()
    return job


def _copy(job, srcs, dests):
    parts = [d.with_name(d.name + ".part") for d in dests]
    try:
        for src, part in zip(srcs, parts):
            with open(src, "rb") as fi, open(part, "wb") as fo:
                for chunk in iter(lambda: fi.read(8 << 20), b""):
                    if job["stop"]:
                        raise InterruptedError
                    fo.write(chunk)
                    job["done"] += len(chunk)
            if part.stat().st_size != src.stat().st_size:
                raise OSError("the copy's size does not match the file: try again")
        for part, d in zip(parts, dests):
            part.replace(d)
        if job["mode"] == "move":  # only after full, checked copies
            for src in srcs:
                src.unlink()
        _finish_import(job, dests[0])
    except InterruptedError:
        for part in parts:
            part.unlink(missing_ok=True)  # the user's files are untouched
        job["state"] = "stopped"
    except (OSError, ValueError) as e:
        for part in parts:
            part.unlink(missing_ok=True)
        job.update(state="error", error=str(e))


def _finish_import(job, dest):
    if gguf_arch(dest) in (None, "clip"):
        raise ValueError(f"{dest.name} is not a chat / code model (its file names no language-model architecture)")
    key = local_key(dest.name)
    for k, m in (llamacpp._read_custom().get("models") or {}).items():
        if m.get("file") == dest.name:  # the same file again: its old name
            key = k
    proj = job.get("mmproj") or (mmproj_for(dest).name if mmproj_for(dest) else None)
    llamacpp.add_custom(key, dest.name, job["kind"], job["repo"], mmproj=proj)
    llamacpp.use_custom(llamacpp.PREFIX + key, job["kind"])
    job.update(state="done", key=llamacpp.PREFIX + key, vision=bool(proj))
