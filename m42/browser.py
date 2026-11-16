"""check_page: open an HTML page in headless Chrome/Edge and report JavaScript errors.

For web projects this is what run_command is for Python: proof that the code works, instead of the model
saying so. A copy of the page with a small error collector at the top of <head> is written next to the
original (so relative paths still work), loaded with --dump-dom, and deleted again. alert / confirm / prompt
don't block there (a button that only shows an alert hung the check for 45 s): they return at once and count as
the button doing something. The collector records
load errors (missing script/css/images), runtime errors, unhandled promise rejections and console.error,
and presses the arrow keys, Space and Enter so keyboard handlers in games run too.
"""
import html
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from tools import ToolError

PROFILE = Path(__file__).resolve().parent / "cache" / "browser-check"
REPORT_AT_MS = 2500  # virtual time: the page and its game loop run this long before the report is written
TIMEOUT = 45

COLLECTOR = """<script>(function(){var E=[];function add(m){if(E.length<30)E.push(String(m).slice(0,300));}
var A=0;window.alert=function(){A++;};window.confirm=function(){A++;return true;};window.prompt=function(m,d){A++;return d||'';};
window.addEventListener('error',function(e){var t=e.target;if(t&&t!==window&&(t.src||t.href)){add('Failed to load '+
(t.getAttribute('src')||t.getAttribute('href')));}else{add((e.message||'Error')+(e.filename?' ('+e.filename.split('/').pop()
.split('?')[0]+' line '+e.lineno+')':''));}},true);
window.addEventListener('unhandledrejection',function(e){add('Unhandled promise rejection: '+((e.reason&&e.reason.message)||e.reason));});
var ce=console.error;console.error=function(){add('console.error: '+[].map.call(arguments,String).join(' '));return ce.apply(console,arguments);};
var cw=console.warn,W={};console.warn=function(){var m=[].map.call(arguments,String).join(' ');if(!W[m]&&Object.keys(W).length<8){W[m]=1;add('console.warn: '+m.slice(0,120));}return cw.apply(console,arguments);};
var T={};['fillText','strokeText'].forEach(function(f){var o=window.CanvasRenderingContext2D&&CanvasRenderingContext2D.prototype[f];if(!o)return;
CanvasRenderingContext2D.prototype[f]=function(t){var s=String(t);if(/NaN|undefined|null|\\[object /.test(s)&&!T[s]){T[s]=1;add('Canvas text shows "'+s.slice(0,60)+'"');}
if(/game\\s*over|you\\s*(lose|lost|win|won)\\b/i.test(s)&&!T.__end){T.__end=1;add('Canvas shows "'+s.slice(0,40)+'" within 2 seconds of the start (before anyone has played)');}return o.apply(this,arguments);};});
function keys(){['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' ','Enter','a','d'].forEach(function(k,i){setTimeout(function(){
var o={key:k,code:k===' '?'Space':(k.length===1?'Key'+k.toUpperCase():k),bubbles:true};
try{document.dispatchEvent(new KeyboardEvent('keydown',o));setTimeout(function(){document.dispatchEvent(new KeyboardEvent('keyup',o));},80);}catch(x){}},300+i*150);});}
function start(){var b=[].slice.call(document.querySelectorAll('button,[role=button],input[type=button]')).filter(function(x){
return /\\b(start|play|begin|new game)\\b/i.test(x.textContent||x.value||'');})[0];if(b){try{b.click();}catch(x){add((x&&x.message)||String(x));}}}
var D=[],K=0;function snap(){var v=[].map.call(document.querySelectorAll('input,textarea,select,output'),function(x){return x.value;}).join('|');
return ((document.body&&document.body.innerText)||'')+'|'+v+'|'+[].map.call(document.documentElement.attributes,function(a){return a.name+a.value;}).join()+'|'+[].map.call(document.querySelectorAll('.show,.active,.selected,.open,.collapsing,.collapsed,.was-validated,.is-invalid,.m42-form-done,[aria-pressed=true]'),function(e){return e.tagName+(e.textContent||'').slice(0,12);}).join();}
var L=[];function layout(bs){var R=[];bs.forEach(function(b){var r=b.getBoundingClientRect();if(!r.width||!r.height)return;
var row=R.filter(function(x){return Math.abs(x.top-r.top)<r.height/2;})[0];if(!row){row={top:r.top,items:[]};R.push(row);}
row.items.push({x:r.left,l:(b.textContent||b.value||'?').trim().slice(0,12)});});R.sort(function(a,b){return a.top-b.top;});
return R.map(function(row){return row.items.sort(function(a,b){return a.x-b.x;}).map(function(i){return i.l;});});}
function clicks(){if(!window.__m42c||document.querySelector('canvas'))return;var bs=[].slice.call(document.querySelectorAll('button,input[type=button],input[type=submit],[role=button]')).slice(0,40);
try{L=layout(bs);}catch(x){}
bs.forEach(function(b,i){setTimeout(function(){var before=snap(),a0=A;try{b.click();}catch(x){add((x&&x.message)||String(x));}K++;
var l=(b.textContent||b.value||'').trim();if(!l&&!b.getAttribute('aria-label')&&!b.title)add('A button has no label (button '+(i+1)+')');
if(snap()===before&&A===a0)D.push(l||('button '+(i+1)));var s=snap();var m=s.match(/NaN|undefined|Infinity|\\[object \\w+\\]/);
if(m&&s.split(m[0]).length>before.split(m[0]).length&&!T['v'+m[0]]){T['v'+m[0]]=1;add('After clicking "'+l+'" the page shows "'+m[0]+'"');}},500+i*45);});}
function go(){setTimeout(start,150);keys();clicks();setTimeout(ended,280);}
function ended(){var o=document.getElementById('overlay');if(!o)return;var s=getComputedStyle(o);
if(s.display!=='none'&&s.visibility!=='hidden'&&/win|game\\s*over|clear|lose|lost/i.test(o.innerText||''))
add('The win / game-over screen (#overlay) shows right at the start, before anyone has played: the win or lose condition is true from the first frame');}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',go);}else{go();}
setTimeout(function(){var b=document.body,p=document.createElement('pre');p.id='__m42_report';p.textContent=JSON.stringify({
errors:E,dead:D,clicked:K,layout:L,title:document.title,canvas:document.querySelectorAll('canvas').length,elements:document.querySelectorAll('body *').length,
text:((b&&b.innerText)||'').replace(/\\s+/g,' ').slice(0,200),ux:typeof __m42ux==='function'?__m42ux():null});(b||document.documentElement).appendChild(p);},%d);})();</script>"""

SPECS = [{"type": "function", "function": {
    "name": "check_page",
    "description": "Open an HTML page of the project in a headless browser for a few seconds (it also presses "
                   "arrow keys, Space and Enter) and report JavaScript errors and files that failed to load. "
                   "Use it after writing or changing a web page, like run_command for Python.",
    "parameters": {"type": "object", "properties": {
        "path": {"type": "string", "description": "The HTML file, e.g. 'index.html'"},
    }, "required": ["path"]},
}}]
NAMES = {"check_page"}


def find_browser():
    candidates = []
    for base in filter(None, [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                              os.environ.get("LOCALAPPDATA")]):
        # Chrome first: on this PC Edge exits at once in headless mode
        candidates += [Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                       Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"]
    # macOS: the browsers in /Applications
    for app_ in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"):
        candidates.append(Path("/Applications") / f"{app_}.app" / "Contents" / "MacOS" / app_)
    for p in candidates:
        if p.exists():
            return str(p)
    return (shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("google-chrome-stable")
            or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("microsoft-edge")
            or shutil.which("msedge") or shutil.which("brave-browser"))


def _with_collector(text, clicks=False, ux=False):
    script = (COLLECTOR % REPORT_AT_MS).replace(chr(10), "")  # one line: the page keeps its line numbers
    if ux:  # the web kit's phone-width measurements (overflow, contrast, alt, labels, h1), run with the report
        import webkit
        script = "<script>window.M42_STILL=1;" + webkit.UX_JS.replace(chr(10), "") + "</script>" + script
    if clicks:  # also click every button and note the ones that change nothing (a page with no canvas)
        script = "<script>window.__m42c=1</script>" + script
    for rx in (r"<head\b[^>]*>", r"<html\b[^>]*>"):
        m = re.search(rx, text, re.I)
        if m:
            return text[:m.end()] + script + text[m.end():]
    return script + text


def check(page, clicks=False, ux=False):
    """Load one HTML file; returns {"ok", "errors", "canvas", "elements", "title", "text"}; with clicks also
    "dead" (labels of buttons that changed nothing) and "clicked"; with ux the page is 390 px wide (a phone) and
    "ux" holds what webkit.UX_JS measured."""
    page = Path(page)
    browser = find_browser()
    if not browser:
        raise ToolError("No Chrome or Edge found for the browser check")
    tmp = page.with_name(f".m42-check-{uuid.uuid4().hex[:8]}.html")
    tmp.write_text(_with_collector(page.read_text(encoding="utf-8", errors="replace"), clicks, ux),
                   encoding="utf-8")
    PROFILE.mkdir(parents=True, exist_ok=True)
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                            "--disable-extensions", "--mute-audio", "--allow-file-access-from-files",
                            f"--user-data-dir={PROFILE}", f"--virtual-time-budget={REPORT_AT_MS + 1500}"]
                           + (["--window-size=390,844"] if ux else []) + ["--dump-dom", tmp.resolve().as_uri()],
                           capture_output=True, timeout=TIMEOUT, creationflags=flags)
        dom = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "errors": [f"The page did not finish within {TIMEOUT}s (an endless loop in the "
                                        "script, or a blocking alert/prompt)"], "canvas": 0, "elements": 0,
                "title": "", "text": ""}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    m = re.search(r'<pre id="__m42_report">(.*?)</pre>', dom, re.S)
    if not m:
        return {"ok": False, "errors": ["The page never finished running its scripts (it crashed or an endless "
                                        "loop blocked it)"], "canvas": 0, "elements": 0, "title": "", "text": ""}
    report = json.loads(html.unescape(m.group(1)))
    # the copy's own name shows up in error locations: report the real file name
    report["errors"] = [e.replace(tmp.name, page.name) for e in report["errors"]]
    report["ok"] = not report["errors"]
    return report


# top-level definitions in classic scripts (they share one global scope)
TOP_DEF_RX = re.compile(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(|^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", re.M)
TOP_CONST_RX = re.compile(r"^const\s+([A-Za-z_$][\w$]*)\s*=", re.M)
SCRIPT_SRC_RX = re.compile(r"""<script[^>]*\ssrc\s*=\s*["']([^"'?#]+)["']""", re.I)
INLINE_SCRIPT_RX = re.compile(r"<script\b(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.I | re.S)


def lint(page):
    """Wiring mistakes that load without errors but break the program, found without running it:
    a function defined but never used, the same global defined in two files (the later file silently
    replaces it), and a const that is assigned again. A small model made all three in one game."""
    page = Path(page)
    html_text = page.read_text(encoding="utf-8", errors="replace")
    sources = {page.name: "\n".join(INLINE_SCRIPT_RX.findall(html_text))}
    for src in SCRIPT_SRC_RX.findall(html_text):
        p = (page.parent / src)
        vendored = src.startswith("lib/") or ".min." in src  # libraries: not the project's own code
        if not re.match(r"^(https?:)?//", src, re.I) and not vendored and p.is_file() and p.stat().st_size < 500_000:
            sources[src] = p.read_text(encoding="utf-8", errors="replace")
    everything = html_text + "\n" + "\n".join(t for n, t in sources.items() if n != page.name)
    defined = {}
    for name, text in sources.items():
        for m in TOP_DEF_RX.finditer(text):
            defined.setdefault(m.group(1) or m.group(2), []).append(name)
    problems = []
    for ident, files in defined.items():
        if len(files) > 1 and len(set(files)) > 1:
            problems.append(f"{ident} is defined in {' and '.join(dict.fromkeys(files))}: scripts share one global "
                            f"scope, so the one loaded last replaces the other. Keep one.")
    for ident, files in defined.items():
        uses = len(re.findall(r"(?<![\w$])" + re.escape(ident) + r"(?![\w$])", everything))
        if uses <= len(files) and not ident.startswith("_"):
            problems.append(f"{ident} ({files[0]}) is defined but never used: call it where it belongs.")
    problems += loop_problems(sources)
    for name, text in sources.items():
        for c in TOP_CONST_RX.findall(text):
            # not "enemy => ..." (an arrow parameter) and not "let enemy = ..." (a local of the same name)
            # comments out first: "// Add input handling" + the "= {" left by removing "const input" read as
            # "input = {" and flagged a const that is never reassigned
            code = re.sub(r"/\*.*?\*/|(?<![:\"'])//[^\n]*", " ", everything, flags=re.S)
            rest = re.sub(r"\b(?:const|let|var)\s+" + re.escape(c) + r"\b(\s*=(?!=))?", " ", code)
            if re.search(r"(?<![\w$.])" + re.escape(c) + r"\s*(?:[-+*/%]?=(?![=>])|\+\+|--)", rest):
                problems.append(f"{c} ({name}) is a const but is assigned again later: use let.")
    return problems[:12]


FUNC_START_RX = re.compile(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", re.M)
REPEAT_RX = re.compile(r"\b(requestAnimationFrame|setInterval)\s*\(\s*([A-Za-z_$][\w$]*)?")
CALL_RX = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(")
UPDATE_CALL_RX = re.compile(r"(?<![\w$])update\w*\s*\(|\.update\w*\s*\(", re.I)


def _body_end(text, start):
    """Index after the brace block that opens at text[start - 1] (strings and comments are not skipped:
    good enough for generated game code)."""
    depth = 1
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return i + 1
    return len(text)


def loop_problems(sources):
    """A game whose repeating loop never calls update(): it draws one frozen frame (a player hanging in the
    air, keys doing nothing) with no error at all. Seen in a real build: requestAnimationFrame(draw) repeated
    only draw(), and gameLoop() ran update() once. Reported only when every repeated callback is a plain
    top-level function, so the call graph is known."""
    bodies, repeats = {}, []
    for name, text in sources.items():
        for m in FUNC_START_RX.finditer(text):
            bodies[m.group(1)] = (name, text[m.end():_body_end(text, m.end())])
        for m in REPEAT_RX.finditer(text):
            repeats.append((name, m.group(1), m.group(2)))
    if not any(UPDATE_CALL_RX.search(body) for _, body in bodies.values()) and not any(
            re.search(r"\bupdate\w*\s*\(", t) for t in sources.values()):
        return []  # no update step anywhere: maybe not a game
    if not repeats:
        loop = next((n for n in ("gameLoop", "loop", "update") if n in bodies), None)
        if loop:  # name the file, so the fix goes there
            return [f"Nothing repeats: {loop}() in {bodies[loop][0]} runs once (no requestAnimationFrame or "
                    f"setInterval anywhere), so the game freezes. {loop}() must call update() and draw() and end "
                    f"with requestAnimationFrame({loop})."]
        return []
    if any(not target or target not in bodies for _, _, target in repeats):
        return []  # an arrow function or a method: can't follow it, so don't guess
    seen, todo = set(), [target for _, _, target in repeats]
    while todo:
        fn = todo.pop()
        if fn in seen or fn not in bodies:
            continue
        seen.add(fn)
        todo += [c for c in CALL_RX.findall(bodies[fn][1]) if c in bodies]
    if any(UPDATE_CALL_RX.search(bodies[fn][1]) for fn in seen):
        return []
    where = ", ".join(dict.fromkeys(f"{kind}({target}) in {file}" for file, kind, target in repeats))
    return [f"The game loop never calls update(): only {where} repeats, so it draws one frozen frame (the "
            f"player hangs in the air and keys do nothing). Make one loop function that calls update() then "
            f"draw() and ends with requestAnimationFrame(itself); draw() must not call requestAnimationFrame."]


def report_text(rel, rep):
    found = [f"{len(rep['errors'])} error(s)"] if rep["errors"] else []
    found += [f"{len(rep['lint'])} code problem(s)"] if rep.get("lint") else []
    head = f"Browser check of {rel}: " + (", ".join(found) or "no JavaScript errors")
    info = (f"(title '{rep['title']}', {rep['elements']} elements" + (f", {rep['canvas']} canvas" if rep["canvas"]
                                                                      else "") + ")")
    counts = {}
    for e in rep["errors"]:
        counts[e] = counts.get(e, 0) + 1
    lines = [head + " " + info] + [f"- {e}" + (f" (x{n})" if n > 1 else "") for e, n in counts.items()]
    if rep.get("lint"):
        lines.append("Code problems (the page loads, but these break the program):")
        lines += [f"- {p}" for p in rep["lint"]]
    if rep.get("text"):
        lines.append(f"Visible text: {rep['text']}")
    return "\n".join(lines)


def call(name, args, workspace):
    if name != "check_page":
        raise ToolError(f"Unknown tool {name}")
    p = workspace.resolve(args.get("path") or "index.html")
    if not p.is_file() or p.suffix.lower() not in (".html", ".htm"):
        raise ToolError(f"{args.get('path')} is not an HTML file in the project")
    rep = check(p)
    rep["lint"] = lint(p)
    rep["ok"] = rep["ok"] and not rep["lint"]
    text = report_text(workspace.rel(p), rep)
    return {"summary": text.split("\n", 1)[0], "content": text, "output": text, "ok_run": rep["ok"],
            "report": rep}
