"""First run on a new PC (firstrun.py), with nothing downloaded from the internet: an empty install lists the model,
its picture reader and llama-server as missing; a release archive with llama-server in a sub-folder is unpacked to
llama.cpp/<build>/; a file is fetched with a resume and its checksum checked (a local file:// stands in for the web);
a wrong checksum is refused; this PC (which has everything) needs nothing."""
import hashlib
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import firstrun  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


check("this PC has everything: nothing to download", firstrun.needed() == [], firstrun.needed())
real = (firstrun.MODELS, firstrun.LLAMA, firstrun.WHISPER_DIR, firstrun.CONFIG)
tmp = Path(tempfile.mkdtemp())
firstrun.MODELS, firstrun.LLAMA = tmp / "models", tmp / "llama.cpp"
firstrun.WHISPER_DIR, firstrun.CONFIG = tmp / "whisper.cpp" / "bin", tmp / "config.json"
os.environ.pop("M42_LLAMA_SERVER", None)
core = firstrun.plan("4b", speech=False)
check("a new PC: the model, the picture reader and llama-server are missing",
      [i["group"] for i in core].count("model") == 2 and [i["kind"] for i in core].count("llama") >= 1, [i["label"] for i in core])
speech = [i["label"] for i in firstrun.plan("4b") if i["group"] == "speech"]
check("and the speech models: Whisper small, the Tanglish test model, the voice detector",
      any("small" in s for s in speech) and any("tanglish" in s for s in speech) and any("silero" in s for s in speech), speech)
# the model that fits the PC (the user, 2026-11-15: "8 GB: the 2B; 16 GB: the 4B")
check("8 GB RAM: the 2B", firstrun.choose_tier({"ram_gb": 7.8, "gpus": []})[0] == "2b")
check("16 GB RAM (13.9 seen with the iGPU's share): the 4B", firstrun.choose_tier({"ram_gb": 13.9, "gpus": []})[0] == "4b")
check("8 GB RAM with a 8 GB graphics card: the 4B, on the card",
      firstrun.choose_tier({"ram_gb": 8, "gpus": [{"name": "RTX 4060", "vram_gb": 8, "integrated": False}]})[0] == "4b")
check("a built-in graphics chip does not count", firstrun.choose_tier(
    {"ram_gb": 8, "gpus": [{"name": "AMD Radeon(TM) Graphics", "vram_gb": 8, "integrated": True}]})[0] == "2b")
check("the 2B's files when the 2B is chosen", [i["label"] for i in firstrun.plan("2b", speech=False) if i["group"] == "model"]
      == ["Qwen3.5-2B-Q4_K_M.gguf", "Qwen3.5-2B-mmproj-F16.gguf"])
# nothing downloads before the user's yes
check("the app waits for the user's yes", firstrun.start() is False and firstrun.state["state"] == "needs_consent")
st = firstrun.status()
check("the status names them and the size", len(st["missing"]) >= 3 and 2 <= st["gb"] <= 5 and st.get("tier"), st)

# a release archive: llama-server and its libraries one folder down
arc = tmp / "llama-test.zip"
with zipfile.ZipFile(arc, "w") as z:
    z.writestr("build/bin/" + firstrun.SERVER, b"server")
    z.writestr("build/bin/ggml.dll", b"lib")
firstrun.LLAMA.mkdir(parents=True)
firstrun._unpack(arc, firstrun.LLAMA / "vulkan", firstrun.SERVER)
check("unpacked into llama.cpp/vulkan/ with its libraries", (firstrun.LLAMA / "vulkan" / firstrun.SERVER).exists()
      and (firstrun.LLAMA / "vulkan" / "ggml.dll").exists() and not arc.exists())
check("then llama-server is no longer missing", not [i for i in firstrun.plan("4b") if i["kind"] == "llama"])

# a download, resumed, checked (file:// stands in for Hugging Face)
data = os.urandom(300_000)
srcf = tmp / "source.bin"
srcf.write_bytes(data)
dest = tmp / "models" / "model.gguf"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.with_name(dest.name + ".part").write_bytes(data[:100_000])  # a download cut off at a third
firstrun._fetch(srcf.as_uri(), dest, len(data), hashlib.sha256(data).hexdigest(), "test")
check("a cut-off download finishes and matches its checksum", dest.exists() and dest.read_bytes() == data)
bad = tmp / "models" / "bad.gguf"
try:
    firstrun._fetch(srcf.as_uri(), bad, len(data), "0" * 64, "test")
    check("a wrong checksum is refused", False)
except OSError as e:
    check("a wrong checksum is refused", not bad.exists() and "checksum" in str(e), e)
firstrun.MODELS, firstrun.LLAMA, firstrun.WHISPER_DIR, firstrun.CONFIG = real
print("FAILS:", fails)
