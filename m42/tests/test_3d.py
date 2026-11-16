"""🧊 The 3D kit: its catalog read from bundled/m42-3d.js, three.js only on a page with a 3D scene, the hero's stage,
the "three_d" decision in the request's reading. (No model needed.)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import modelsearch  # noqa: E402
import pagebuild  # noqa: E402
import uiflows  # noqa: E402
import webkit  # noqa: E402

FAILS = 0


def check(name, ok, info=""):
    global FAILS
    print(("ok   " if ok else "FAIL ") + name, info if not ok else "")
    FAILS += 0 if ok else 1


cat = modelsearch.catalog()
check("the catalog has 200+ objects", len(cat["objects"]) >= 200, len(cat["objects"]))
check("... the school's own things", all(o in cat["objects"] for o in ("book_stack", "globe", "graduation_cap", "pencil", "atom")))
check("... 20+ stories, pour and build_up among them", len(cat["stories"]) >= 20 and {"pour", "build_up", "orbit"} <= set(cat["stories"]))
check("... 15+ extras", len(cat["extras"]) >= 15 and "steam" in cat["extras"])
check("... liquids", "coffee" in cat["liquids"])

scene = {"objects": ["book_stack", "globe"], "story": "orbit", "extras": ["sparkles"]}
attr = pagebuild.e(json.dumps(scene))
used = webkit.used_files({"index.html": f'<div class="m42-3d" data-m42-3d="{attr}"></div>'})
check("a 3D page loads three.js, then M42 3D", used.index("three.min.js") < used.index("m42-3d.js"), used)
check("... no model loader without a model", "GLTFLoader.js" not in used)
used2 = webkit.used_files({"index.html": f'<div data-m42-3d="{pagebuild.e(json.dumps(dict(scene, model="models/a/b.gltf")))}"></div>'})
check("... GLTFLoader with a .gltf model", "GLTFLoader.js" in used2 and used2.index("three.min.js") < used2.index("GLTFLoader.js"), used2)
plain = webkit.used_files({"index.html": '<header class="m42-hero"><h1>School</h1></header>'})
check("a page without 3D loads no three.js", "three.min.js" not in plain and "m42-3d.js" not in plain, plain)

check("the request's reading has three_d", "three_d" in uiflows.ENHANCE_SCHEMA["properties"] and "three_d" in uiflows.INTENT_KEYS)
check("... it is true only when the words ask for 3D", "true only when the words ask for 3D" in uiflows.ENHANCE_PROMPT)
check("bundled files are there", all((webkit.BUNDLED / f).is_file() for f in ("three.min.js", "m42-3d.js", "GLTFLoader.js", "STLLoader.js")))
src = (Path(pagebuild.__file__)).read_text(encoding="utf-8")
check("the hero draws plan['scene3d'] as a data-m42-3d stage", 'data-m42-3d="' in src and 'plan.get("scene3d")' in src)
kept = pagebuild.clean({"hero": {"title": "School"}, "sections": [], "scene3d": scene}, {})
check("clean() keeps the plan's 3D scene", kept.get("scene3d") == scene, kept.keys())
wired = webkit.wire_chat_page(f'<!DOCTYPE html><html><head></head><body><div class="m42-3d" data-m42-3d="{attr}"></div></body></html>', {})
check("a whole 3D page is wired (three.js tag, no KeyError)", "three.min.js" in wired and "m42-3d.js" in wired)
check("... the coder's note has no three.js", "three.min.js" not in webkit.chat_note("a school page", webkit.make_theme("a school page")))
probs = webkit.class_problems({"index.html": f'<div class="m42-3d" data-m42-3d="{attr}"><canvas></canvas></div>'}, ["m42-ui.css"])
check("the class check knows m42-3d (its CSS comes from m42-3d.js)", not any("m42-3d" in x for v in probs.values() for x in v), probs)
print("FAILS:", FAILS)
