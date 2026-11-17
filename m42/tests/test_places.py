"""📦 Where the models go (the user, 2026-11-17): a ZIP unzipped anywhere asks once, before anything downloads, how much
room the models need and where they go; a drive without the room is refused; the folder is kept for this PC (the app's
config and the user's own settings), so another copy of the app asks nothing. No download here."""
from pathlib import Path
import os
import sys
import tempfile

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
os.environ.pop("M42_MODELS_DIR", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import places  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


tmp = Path(tempfile.mkdtemp())
app1, app2, home = tmp / "app1", tmp / "app2", tmp / "home"
for d in (app1, app2):
    (d / "models").mkdir(parents=True)
real = (places.CONFIG, places.DEFAULT, places.user_settings)


def as_copy(app):  # this test's "copy of the app" (its own config, its own models/), the same user
    places.CONFIG, places.DEFAULT = app / "config.json", app / "models"
    places.user_settings = lambda: home / "settings.json"


as_copy(app1)
import firstrun  # noqa: E402
import llamacpp  # noqa: E402
import speech  # noqa: E402

check("a fresh PC: no folder chosen", not places.chosen() and places.saved() == "")
need = 3_600_000_000
folder, enough = places.suggest(need)
check("suggested: the app's own models/ when its drive has the room", folder == str(places.DEFAULT) and enough, folder)
check("a drive too small: refused, in words", "Not enough space" in places.check(tmp / "x", 10 ** 15), places.check(tmp / "x", 10 ** 15))
check("a relative path: refused", places.check("models", need) != "")
check("a folder with the room: fine", places.check(tmp / "m42-models", need) == "")
chosen_dir = tmp / "m42-models"
places.save(chosen_dir)
check("kept in the app's config", places._read(places.CONFIG).get("models_dir") == str(chosen_dir.resolve()))
check("kept in the user's settings", places._read(home / "settings.json").get("models_dir") == str(chosen_dir.resolve()))
check("every module now uses it", firstrun.MODELS == chosen_dir.resolve() and llamacpp.MODELS_DIR == chosen_dir.resolve()
      and speech.MODELS == chosen_dir.resolve() and speech.VAD_MODEL.parent.parent == chosen_dir.resolve())
as_copy(app2)  # another copy of the app, unzipped elsewhere: finds the folder, asks nothing
check("another copy: the same folder, nothing asked", places.chosen() and places.models_dir() == chosen_dir.resolve())
(home / "settings.json").unlink()
check("a fresh copy, no settings: asked", not places.chosen())
(places.DEFAULT / "Qwen3.5-4B-Q4_K_M.gguf").write_bytes(b"x")
check("an old install with its models in models/: never asked", places.chosen())
(places.DEFAULT / "Qwen3.5-4B-Q4_K_M.gguf").unlink()

# the app's Download with a folder that has no room: nothing starts, the reason is said
real_free = places.free_bytes
places.free_bytes = lambda p: 10 ** 6
started = firstrun.start(consent=True, folder=str(tmp / "small"))
check("no room: the download does not start", not started and firstrun.state["state"] == "error"
      and "Not enough space" in firstrun.state["error"], firstrun.state)
places.free_bytes = real_free
info = firstrun.place_info(firstrun.plan_in(tmp / "empty"))
check("the note's numbers: GB needed and the room, each drive's free GB",
      info["need_gb"] > 0 and info["room_gb"] > info["need_gb"] and info["drives"], {k: info[k] for k in ("need_gb", "room_gb")})

places.CONFIG, places.DEFAULT, places.user_settings = real
places.apply()
print("FAILS:", fails)
sys.exit(1 if fails else 0)
