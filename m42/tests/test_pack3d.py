"""The optional 3D pack (pack3d.py), with no internet: a small pack in a temp folder is zipped, "downloaded" from a
file:// URL (standing in for the GitHub release), its SHA-256 checked, unpacked; modelsearch.library() then knows its
models (the bundled ones win a shared name), a scene's pack model is copied with its CC BY credit line, the page's
footer credits it, a wrong SHA-256 or an unsafe zip changes nothing, and the 4B's fallback list leaves the pack out."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import modelsearch  # noqa: E402
import pack3d  # noqa: E402
import pagebuild  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 12
tmp = Path(tempfile.mkdtemp())
src = tmp / "src"
for rel in ("modern_restaurant_cafe/espresso_machine.glb", "hospital/hospital_bed.glb", "office/apple.glb"):
    (src / rel).parent.mkdir(parents=True, exist_ok=True)
    (src / rel).write_bytes(GLB)
cred = {"modern_restaurant_cafe/espresso_machine.glb": {"name": "Espresso Machine", "url": "https://polyfork.dev/asset/e-1"},
        "hospital/hospital_bed.glb": {"name": "Hospital Bed", "url": "https://polyfork.dev/asset/h-1"},
        "office/apple.glb": {"name": "Apple", "url": "https://polyfork.dev/asset/a-1"}}
(src / "credits.json").write_text(json.dumps(cred), encoding="utf-8")
(src / "pack.json").write_text(json.dumps({"version": "1", "models": 3}), encoding="utf-8")


def make_zip(path, extra=None):
    with zipfile.ZipFile(path, "w") as z:
        for p in src.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(src).as_posix())
        for n, data in (extra or {}).items():
            z.writestr(n, data)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path.as_uri()


real = pack3d.PACK, modelsearch.PACK
pack3d.PACK = modelsearch.PACK = tmp / "installed" / "models3d"
modelsearch._library, modelsearch._credits = None, None
try:
    check("no pack: status says so", not pack3d.status()["installed"])
    url = make_zip(tmp / "M42-3D-pack.zip")
    st = pack3d.install(url=url)
    check("install from the release zip (SHA-256 checked)", st["installed"] and st["models"] == 3, st)

    lib = modelsearch.library()
    check("the pack's models are in the library", "espresso_machine" in lib and "hospital_bed" in lib)
    check("a name the bundled packs have stays the bundled one", "apple" in lib and not modelsearch.in_pack("apple"), lib.get("apple"))
    check("a pack model is known as one", modelsearch.in_pack("espresso_machine"))
    check("the catalog has them for the 3D scene", "espresso_machine" in modelsearch.catalog()["objects"])

    site = tmp / "site"
    files = modelsearch.library_files(["espresso_machine", "apple"], site)
    check("a scene's pack model is copied beside the page", (site / files["espresso_machine"]).is_file(), files)
    credit = (site / "models" / "CREDITS.txt").read_text(encoding="utf-8")
    check("its CC BY credit line is in models/CREDITS.txt",
          "Espresso Machine by Polyfork (https://polyfork.dev/asset/e-1), CC BY 4.0" in credit, credit)
    c = modelsearch.credits(list(files))
    check("credits(): only the pack's models", c == [{"name": "Espresso Machine", "url": "https://polyfork.dev/asset/e-1"}], c)
    html = pagebuild.model_credits({"scene3d": {"credits": c}})
    check("the footer credits it, with the licence link", "Espresso Machine" in html and "by Polyfork" in html
          and "creativecommons.org/licenses/by/4.0" in html, html)
    check("no pack model: no footer line", pagebuild.model_credits({"scene3d": {"objects": ["cup"]}}) == "")

    # bad zips change nothing
    Path(str(tmp / "M42-3D-pack.zip") + ".sha256").write_text("0" * 64, encoding="utf-8")
    try:
        pack3d.install(url=url)
        check("a wrong SHA-256 is refused", False)
    except RuntimeError as e:
        check("a wrong SHA-256 is refused, the pack stays", "SHA-256" in str(e) and pack3d.status()["models"] == 3, e)
    bad = make_zip(tmp / "bad.zip", {"../evil.txt": "x"})
    try:
        pack3d.install(url=bad)
        check("an unsafe zip is refused", False)
    except RuntimeError as e:
        check("an unsafe zip is refused", "unsafe" in str(e) and not (tmp / "evil.txt").exists(), e)

    import agent  # noqa: E402
    cat = {"objects": sorted(modelsearch.catalog()["objects"])}
    fallback = agent.Agent._kit_shortlist(agent.Agent.__new__(agent.Agent), cat, "zzqx", "", {})
    check("the 4B's fallback list (nothing matched) leaves the pack out", "espresso_machine" not in fallback and fallback, len(fallback))
    told = agent.Agent._kit_shortlist(agent.Agent.__new__(agent.Agent), cat, "espresso machine", "", {})
    check("a pack model is found by its name", "espresso_machine" in told, told[:5])

    pack3d.remove()
    check("remove(): gone", not pack3d.status()["installed"])
finally:
    pack3d.PACK, modelsearch.PACK = real
    modelsearch._library, modelsearch._credits = None, None
print("\nall ok" if not fails else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
