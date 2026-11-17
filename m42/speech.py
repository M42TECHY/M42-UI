"""🎤 Speech to text on this PC, CPU only (the user, 2026-11-12: "Tamil, English, Hindi, Malayalam, Kannada; light, open
source, fast; no GPU needed: half the PCs have none"). Three engines, chosen in Settings:

    small     Whisper small (q5_1, 190 MB) in whisper.cpp's whisper-server: every language and Tanglish, ~3 s for 5 s
    turbo     Whisper large-v3-turbo (q5_0, 550 MB): the most accurate, ~15 s for 5 s on a CPU
    indic-XX  AI4Bharat IndicConformer (CTC, int8, ~200 MB per language) in sherpa-onnx: ~0.2 s for 5 s, writes
              that language's own script (English words in it too); one model per language folder

A whisper-server is started on the first use and kept running (the model stays loaded); IndicConformer is loaded
once into this process. Nothing leaves the PC."""
import atexit
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # M42-UI
EXE = ROOT / "whisper.cpp" / "bin" / ("whisper-server.exe" if os.name == "nt" else "whisper-server")
import places  # noqa: E402  (the models folder chosen on this PC)
MODELS = places.models_dir()
# (turbo, large-v3-turbo, was taken out: ~15 s for 5 s on a CPU; the user, 2026-11-13: "small and IndicConformer only")
WHISPER = {"small": (MODELS / "ggml-small-q5_1.bin", 8179)}
INDIC = MODELS / "indicconformer"
# Whisper from Hugging Face, run by transformers on the CPU: a Mac (no whisper-server build) gets Whisper small itself
# (firstrun.py downloads it there). (2026-11-17, the user tried them all: "IndicConformer Tamil for Tamil, Whisper small
# for English; take the rest away": the Whisper Tanglish fine-tune (WER 52%) and Gemma 4 E2B (~4-8 s a phrase) went.)
HF = {"small-py": (MODELS / "whisper-small", "Whisper small: every language (English best)")}
NAMES = {"ta": "Tamil", "ml": "Malayalam", "kn": "Kannada", "hi": "Hindi", "te": "Telugu", "en": "English"}
LANGUAGES = {"auto", "ta", "en", "hi", "ml", "kn", "te"}

_procs, _indic, _hf, _lock = {}, {}, {}, threading.Lock()


def engines():
    """[{id, label}] of the engines whose files are here."""
    out = [{"id": k, "label": {"small": "Whisper small: every language (English best)"}[k]}
           for k, (m, _p) in WHISPER.items() if EXE.is_file() and m.is_file()]
    out += [{"id": k, "label": lab} for k, (d, lab) in HF.items() if (d / "model.safetensors").is_file()]
    for d in sorted(INDIC.glob("*/model.int8.onnx")) if INDIC.is_dir() else []:
        code = d.parent.name
        out.append({"id": f"indic-{code}", "label": f"IndicConformer {NAMES.get(code, code)}: very fast, {NAMES.get(code, code)} script"})
    return out


def label(engine):
    return next((e["label"].split(":")[0] for e in engines() if e["id"] == _pick(engine)), "speech")


def available():
    return bool(engines())


def _pick(engine):
    ids = [e["id"] for e in engines()]
    return engine if engine in ids else next((k for k in ("small", "small-py") if k in ids), ids[0] if ids else "")


def _alive(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
            return r.status < 500
    except (OSError, urllib.error.URLError):
        return False


def start(engine=None, wait=True, timeout=120):
    """The engine ready (a whisper-server started with its model, or IndicConformer loaded). True when ready."""
    engine = _pick(engine)
    if engine.startswith("indic-") or engine in HF:  # (another engine chosen: Whisper's server stopped, its RAM back)
        with _lock:
            for other, q in list(_procs.items()):
                if q.poll() is None:
                    q.terminate()
    if engine.startswith("indic-"):
        return _indic_rec(engine[6:]) is not None
    if engine in HF:
        return _hf_model(engine) is not None
    if engine not in WHISPER:
        return False
    model, port = WHISPER[engine]
    with _lock:
        p = _procs.get(engine)
        if p is None or p.poll() is not None:
            if _alive(port):
                return True
            for other, q in list(_procs.items()):  # (one Whisper loaded at a time: the RAM of a weak PC)
                if other != engine and q.poll() is None:
                    q.terminate()
            threads = max(2, min(8, (os.cpu_count() or 4) - 2))
            _procs[engine] = subprocess.Popen(
                [str(EXE), "-m", str(model), "--host", "127.0.0.1", "--port", str(port), "-t", str(threads), "-l", "auto", "-nt", "-sns"],
                cwd=str(EXE.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=dict(os.environ, LD_LIBRARY_PATH=os.pathsep.join(  # (Linux: its .so files beside it)
                    x for x in (str(EXE.parent), os.environ.get("LD_LIBRARY_PATH", "")) if x)))
    if not wait:
        return True
    end = time.time() + timeout
    while time.time() < end:
        if _alive(port):
            return True
        if _procs[engine].poll() is not None:
            return False
        time.sleep(0.3)
    return False


def stop():
    with _lock:
        for p in _procs.values():
            if p.poll() is None:
                p.terminate()
        _procs.clear()


atexit.register(stop)  # (the speech servers go when M42 UI does)


_indic_lock = threading.Lock()


def _indic_rec(code):
    with _indic_lock:  # (the warm-up and the first words at once: loaded once, the second waits for it)
        return _indic_load(code)


def _indic_load(code):
    rec = _indic.get(code)
    if rec is None:
        import sherpa_onnx  # (the package, CPU only)
        model = INDIC / code / "model.int8.onnx"
        if not model.is_file():
            return None
        rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=str(model), tokens=str(INDIC / "tokens.txt"),
                                                          num_threads=max(2, min(6, (os.cpu_count() or 4) - 2)),
                                                          decoding_method="greedy_search")
        _indic[code] = rec
    return rec


def _hf_model(engine):
    """(processor, model) of a Hugging Face Whisper, loaded once (transformers, CPU, float32)."""
    with _lock:
        got = _hf.get(engine)
        if got is None:
            os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")  # (no progress bars or notices in logs/app.log)
            os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
            os.environ.setdefault("HF_HUB_OFFLINE", "1")  # (the files are here: nothing fetched)
            import torch
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
            from transformers.utils import logging as _tlog
            _tlog.set_verbosity_error()
            _tlog.disable_progress_bar()
            d = HF[engine][0]
            if not (d / "model.safetensors").is_file():
                return None
            torch.set_num_threads(max(2, min(6, (os.cpu_count() or 4) - 2)))
            got = (WhisperProcessor.from_pretrained(str(d)),
                   WhisperForConditionalGeneration.from_pretrained(str(d), use_safetensors=True).eval())
            try:  # one run on a second of quiet: torch's first run was 4.2 s, the next 0.6 s (the user's first words waited)
                import numpy as np
                with torch.no_grad():
                    got[1].generate(got[0](np.zeros(16000, dtype="float32"), sampling_rate=16000, return_tensors="pt").input_features,
                                    max_new_tokens=4)
            except Exception:  # (a warm-up only)
                pass
            _hf[engine] = got
        return got


def _samples(wav):
    import numpy as np
    with wave.open(BytesIO(wav)) as w:
        rate, width, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16 if width == 2 else np.uint8)
    x = pcm.astype(np.float32) / (32768 if width == 2 else 128) - (0 if width == 2 else 1)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return rate, x


HF_SURE = -1.0  # a mean log-probability under this: not speech (Whisper's own rule of thumb for made-up words)
_TAGS = re.compile(r"\[[^\]]{0,40}\]|\((?:[^)]{0,30}?(?:music|applause|laugh\w*|noise|silence|inaudible)[^)]{0,30})\)|[♪♫]+", re.I)


def clean(text):
    """Speech as text, without what the model writes for sounds ("[Music]", "(applause)", "♪") and without a phrase
    said again and again (a model repeating itself on noise: "9:00-ல 9:00 9:00")."""
    text = " ".join(_TAGS.sub(" ", text or "").split())
    words, out = text.split(), []
    for w in words:  # the same 1-4 words right after themselves: once
        out.append(w)
        for n in (4, 3, 2, 1):
            if len(out) >= 2 * n and [x.strip(".,!?-").lower() for x in out[-n:]] == [x.strip(".,!?-").lower() for x in out[-2 * n:-n]]:
                del out[-n:]
                break
    return " ".join(out).strip(" .,")


VAD_MODEL = MODELS / "vad" / "silero_vad.onnx"


def use_models(d):
    """The models folder changed (places.py: the user chose where the models go): every path made from it again."""
    global MODELS, INDIC, VAD_MODEL
    MODELS = Path(d)
    WHISPER["small"] = (MODELS / "ggml-small-q5_1.bin", WHISPER["small"][1])
    INDIC = MODELS / "indicconformer"
    HF["small-py"] = (MODELS / "whisper-small", HF["small-py"][1])
    VAD_MODEL = MODELS / "vad" / "silero_vad.onnx"


def voice_only(wav):
    """🎙 The parts of a recording where someone speaks (Silero VAD, on the CPU, a few ms): music, a fan, a TV and the
    quiet between words left out (the user, 2026-11-13: "background music came out as words: only the voice").
    (WAV bytes of just the speech, its seconds) — (b"", 0) when no one speaks; the WAV as it is without the model."""
    if not VAD_MODEL.is_file():
        return wav, None
    try:
        import numpy as np
        import sherpa_onnx
        rate, x = _samples(wav)
        if rate != 16000:
            x = np.interp(np.linspace(0, len(x), int(len(x) * 16000 / rate), endpoint=False), np.arange(len(x)), x).astype("float32")
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = str(VAD_MODEL)
        # 0.5: the user's words came through cut ("சாப்பிட்டியா" lost its end at 0.7, 2026-11-13); a bit of music that
        # passes is written "[Music]", which clean() takes out
        cfg.silero_vad.threshold = 0.5
        cfg.silero_vad.min_silence_duration = 0.3
        cfg.silero_vad.min_speech_duration = 0.25
        cfg.sample_rate = 16000
        vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=max(30, len(x) / 16000 + 5))
        win = cfg.silero_vad.window_size
        x = np.asarray(x, dtype=np.float32)
        for i in range(0, len(x), win):
            vad.accept_waveform(x[i:i + win])
        vad.flush()
        # each piece of speech taken from the recording with 0.25 s more on both sides: a word's first and last sounds
        # (soft ones the detector does not count) stay with it; pieces that meet are one
        spans, pad = [], int(16000 * 0.25)
        while not vad.empty():
            a = max(0, int(vad.front.start) - pad)
            e = min(len(x), int(vad.front.start) + len(vad.front.samples) + pad)
            if spans and a <= spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], e)
            else:
                spans.append([a, e])
            vad.pop()
        gap = np.zeros(int(16000 * 0.15), dtype=np.float32)
        parts = [p for a, e in spans for p in (x[a:e], gap)]
    except Exception:  # (no VAD: the recording as it is)
        return wav, None
    if not parts:
        return b"", 0.0
    y = np.concatenate(parts)
    b = BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    return b.getvalue(), round(len(y) / 16000, 2)


def transcribe(wav, language="auto", prompt="", engine=None, best=False):
    """The words in a WAV (16 kHz mono, as the app records it), only its speech (voice_only). Returns (text, seconds).
    prompt: the words said before it (context for Whisper); best: a finished phrase (read more carefully than a draft)."""
    engine = _pick(engine)
    if not start(engine):
        raise RuntimeError("the speech model could not be started")
    t = time.time()
    wav, _secs = voice_only(wav)
    if not wav:  # no one spoke: nothing written (the models wrote "[Music]" or made words up from it)
        return "", round(time.time() - t, 2)
    if engine.startswith("indic-"):
        rec = _indic_rec(engine[6:])
        rate, x = _samples(wav)
        s = rec.create_stream()
        s.accept_waveform(rate, x)
        rec.decode_stream(s)
        import unicodedata  # (a vowel sign with no letter before it, "் ரிமோட", is the model's slip: not shown)
        words = []
        for w in s.result.text.split():
            while w and unicodedata.category(w[0]).startswith("M"):
                w = w[1:]
            if w:
                words.append(w)
        return clean(" ".join(words)), round(time.time() - t, 2)
    if engine in HF:
        import torch
        proc, model = _hf_model(engine)
        rate, x = _samples(wav)
        if rate != 16000:  # (the app records 16 kHz; anything else made so)
            import numpy as np
            x = np.interp(np.linspace(0, len(x), int(len(x) * 16000 / rate), endpoint=False), np.arange(len(x)), x).astype("float32")
        # (2026-11-16, "Tanglish is often wrong": a finished phrase is read with 4 beams, a draft stays greedy and fast.
        # The words said before are NOT given as a prompt here: tried, this fine-tune (trained without prompts) wrote
        # the prompt back and made words up after it ("Sister" "Sister"...); whisper.cpp's Whisper small takes it)
        extra = {"num_beams": 4} if best else {}
        with torch.no_grad():
            out = model.generate(proc(x, sampling_rate=16000, return_tensors="pt").input_features, max_new_tokens=220,
                                 return_dict_in_generate=True, output_scores=True, **extra)
        text = " ".join(proc.batch_decode(out.sequences, skip_special_tokens=True)[0].split())
        try:  # the model's own sureness: words made up from music or noise come with a low one (the user, 2026-11-13:
            # "[Music] [Music]", "9:00-ல 9:00" from the room's sounds)
            if extra.get("num_beams") and getattr(out, "sequences_scores", None) is not None:
                sure = float(out.sequences_scores[0])  # (beams: their own mean log-probability)
            else:
                lp = model.compute_transition_scores(out.sequences, out.scores, normalize_logits=True)[0]
                sure = float(lp[torch.isfinite(lp)].mean()) if len(lp) else 0.0
        except Exception:
            sure = 0.0
        return ("" if sure < HF_SURE else clean(text)), round(time.time() - t, 2)
    language = language if language in LANGUAGES else "auto"
    boundary = "m42" + uuid.uuid4().hex
    fields = {"response_format": "json", "temperature": "0", "language": language}
    if prompt:
        fields["prompt"] = prompt
    body = b""
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="speech.wav"\r\n'
             "Content-Type: audio/wav\r\n\r\n").encode() + wav + f"\r\n--{boundary}--\r\n".encode()
    port = WHISPER[engine][1]
    req = urllib.request.Request(f"http://127.0.0.1:{port}/inference", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return clean(" ".join(str(data.get("text") or "").split())), round(time.time() - t, 1)
