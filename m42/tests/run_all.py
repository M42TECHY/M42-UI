"""M42's regression tests, one after another (each in its own Python, a time limit each): the summary in
_results.txt (PASS / FAIL n / ERROR / TIMEOUT / NO RESULT) and each test's output in _work/out/<test>.txt.
python run_all.py [name-part ...] runs only the tests whose names contain one of the parts."""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "_work" / "out"
OUTDIR.mkdir(parents=True, exist_ok=True)
want = sys.argv[1:]
tests = sorted(p for p in HERE.glob("test_*.py") if not want or any(w in p.name for w in want))
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
rows = []
for t in tests:
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(t)], cwd=HERE, capture_output=True, timeout=300, env=env)
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        m = re.findall(r"FAILS:\s*(\d+)", out)
        if "Traceback" in out and not m:
            status = "ERROR"
        elif m:
            status = "PASS" if all(x == "0" for x in m) else f"FAIL {sum(int(x) for x in m)}"
        elif "SKIPPED" in out:
            status = "SKIPPED"
        else:
            status = "PRINT-ONLY"  # an early script that prints values for a person to read (no pass / fail count)
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"") + (e.stderr or b"")).decode("utf-8", "replace")
        status = "TIMEOUT"
    (OUTDIR / (t.stem + ".txt")).write_text(out, encoding="utf-8")
    rows.append(f"{status:10} {time.time() - t0:6.0f}s  {t.name}")
    print(rows[-1], flush=True)
(HERE / "_results.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("PASS", sum(r.startswith("PASS") for r in rows), "of", len(rows))
