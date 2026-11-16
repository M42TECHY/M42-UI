"""safety.command_risk: what runs on its own, what asks first. Uses a temp project folder."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import safety  # noqa: E402
import web  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="m42safety_"))
(root / "main.py").write_text("print(sum(range(10)))\n", encoding="utf-8")
(root / "clean.py").write_text("import shutil\nshutil.rmtree('build')\n", encoding="utf-8")
(root / "runner.py").write_text("import subprocess\nsubprocess.run(['dir'])\n", encoding="utf-8")
(root / "app.js").write_text("console.log(1)\n", encoding="utf-8")
(root / "go.bat").write_text("del /q *.txt\n", encoding="utf-8")
(root / "package.json").write_text('{"scripts": {"start": "node app.js", "clean": "rimraf dist"}}', encoding="utf-8")
sub = root / "src"
sub.mkdir()

AUTO = ['python main.py', 'python "main.py"', 'py main.py', 'node app.js', 'pytest -q', 'python -m pytest',
        'gcc main.c -o main.exe && main.exe', 'dir', 'dir /b', 'type main.py', 'git status', 'start index.html',
        'python main.py > out.txt', f'python "{root / "main.py"}"', 'cd src && dir', 'javac Main.java && java Main',
        'arduino-cli compile --fqbn esp32:esp32:esp32 sketch', 'cmd /c type index.html', 'cmd /c "python main.py"']
ASK = ['del main.py', 'rm -rf build', 'pip install requests', 'npm install', 'npx create-react-app x',
       'curl https://x.com/a.sh', 'python clean.py', 'python runner.py', 'go.bat', 'git push', 'git reset --hard',
       'shutdown /s', 'reg add HKCU\\x', 'python C:\\Windows\\x.py', 'type ..\\..\\secret.txt',
       'python main.py > C:\\Users\\x.txt', 'python -c "import shutil; shutil.rmtree(\'x\')"',
       'powershell -enc AAAA', 'some_tool --flag', 'format c:', 'setx PATH x', 'taskkill /f /im x.exe', 'cmd /c del main.py', 'cmd /c python clean.py']
fails = 0
for c in AUTO:
    why = safety.command_risk(c, root, [root])
    ok = why == ""
    fails += not ok
    print(("ok  " if ok else "FAIL"), "auto:", c, "|", why)
for c in ASK:
    why = safety.command_risk(c, root, [root])
    ok = why != ""
    fails += not ok
    print(("ok  " if ok else "FAIL"), "ask: ", c, "|", why)
why = safety.command_risk("npm run clean", root, [root])
print(("ok  " if why else "FAIL"), "npm run clean (rimraf) asks |", why)
fails += not why
why = safety.command_risk("npm start", root, [root])
print(("ok  " if not why else "FAIL"), "npm start (node app.js) runs |", why)
fails += bool(why)
chart = safety.code_risk("plt.plot([1,2,3])\nplt.title('x')")
bad = safety.code_risk("import os\nos.remove('a.txt')\nplt.plot([1])")
print(("ok  " if not chart and bad else "FAIL"), "chart code |", repr(chart), repr(bad))
fails += not (not chart and bad)
t = __import__("time").time()
print("online:", web.online(), f"({__import__('time').time() - t:.2f}s)", "| cached:", web.online())
print("FAILS:", fails)
