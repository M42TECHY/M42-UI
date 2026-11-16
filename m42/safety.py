"""Which commands M42 may run on its own and which it asks about first (the "Ask before commands" button is gone).

Runs without asking: building / running / testing the project's own files inside the project folder, and listing
or reading them, when the script itself doesn't delete files, start other programs or change the system.
Asks first: deleting, installing, downloading, system settings, git history changes, paths outside the project,
anything not on the known list, and scripts that do any of those."""
import json
import re
from pathlib import Path

# never without the user: deletes, installs, downloads, system changes, history rewrites
RISKY_RX = re.compile(
    r"\b(del|erase|rd|rmdir|rm|remove-item|format|diskpart|shutdown|restart-computer|reg|regedit|netsh|sc|bcdedit|"
    r"taskkill|stop-process|setx|powercfg|takeown|icacls|cacls|attrib|cipher|mklink|schtasks|wmic|vssadmin|"
    r"winget|choco|scoop|curl|wget|invoke-webrequest|iwr|irm|invoke-restmethod|certutil|bitsadmin|runas|"
    r"set-executionpolicy|move|ren|rename|robocopy|xcopy)\b|"
    r"\b(pip3?|python\s+-m\s+pip|py\s+-m\s+pip)\s+(install|uninstall|download)\b|"
    r"\b(npm|pnpm|yarn)\s+(install|i|add|remove|uninstall|update|publish|link)\b|\bnpx\b|"
    r"\bgit\s+(push|reset|clean|checkout\s+--|restore|rebase|filter-branch|gc|remote|config)\b|"
    r"\b(powershell|pwsh)\b.*\s-(e|enc|encodedcommand)\b|"
    r"\b(https?|ftp)://", re.I)
# what a project normally runs: its own scripts, tests and builds, read-only looks at its files, opening its page
SAFE_START_RX = re.compile(
    r"^(python3?|py|node|deno|pytest|python3?\s+-m\s+(pytest|unittest|py_compile|http\.server)|"
    r"npm\s+(run|test|start)|yarn\s+(run|test|start)|gcc|g\+\+|clang|clang\+\+|javac|java|go\s+(run|build|test|vet)|"
    r"cargo\s+(run|build|test|check)|dotnet\s+(run|build|test)|tsc|"
    r"arduino-cli\s+(compile|board\s+list|core\s+list|lib\s+list)|"
    r"dir|ls|type|cat|more|echo|cd|where|tree|findstr|find|git\s+(status|diff|log|show|branch)|"
    r"(start(\s+\"\")?|explorer)\s+[\"']?[\w./\\ -]+\.html?[\"']?$|"
    r"[\"']?[\w./\\-]+\.(exe|bat|cmd)[\"']?)(\s|$)", re.I)
# inside a script it runs: deleting files, starting programs, the registry, raw OS calls
CODE_RISK = [
    (re.compile(r"\b(shutil\.rmtree|os\.remove|os\.unlink|os\.rmdir|os\.removedirs|send2trash)\b|\.unlink\(|"
                r"\.rmdir\(|\bfs\.(rm|rmSync|unlink|unlinkSync|rmdir|rmdirSync)\b|\brimraf\b"), "deletes files"),
    (re.compile(r"\b(subprocess|os\.system|os\.popen|os\.exec\w*|os\.spawn\w*|child_process|execSync|spawnSync)\b"),
     "starts other programs"),
    (re.compile(r"\b(winreg|_winreg|ctypes\.windll|SetThreadExecutionState)\b"), "changes Windows settings"),
]
CHAIN_RX = re.compile(r"&&|\|\||[|&;]")
SCRIPT_RX = re.compile(r"[\w./\\-]+\.(py|js|mjs|cjs|ts|bat|cmd)\b", re.I)
# an absolute path (C:\..., \\server\...) or a step up out of the folder (..\), also after > (redirect)
PATH_RX = re.compile(r"(?:^|[\s\"'=>])((?:[a-z]:[\\/]|\\\\)[^\s\"'>|&]*|[^\s\"'>|&]*\.\.[\\/][^\s\"'>|&]*)", re.I)


def code_risk(code):
    """What a script does that needs the user's OK, or ''."""
    for rx, why in CODE_RISK:
        if rx.search(code or ""):
            return why
    return ""


def command_risk(command, cwd=None, roots=()):
    """'' when M42 may run `command` on its own, else why it asks first. cwd: the folder it runs in; roots: the
    project folders (a script is read to see what it does; a path outside them needs the user)."""
    cmd = " ".join(str(command or "").split())
    if not cmd:
        return "empty command"
    inner = re.match(r"cmd(?:\.exe)?\s+/[ck]\s+(.+)$", cmd, re.I)  # "cmd /c type index.html": judge what it runs
    if inner:
        return command_risk(inner.group(1).strip().strip('"'), cwd, roots)
    m = RISKY_RX.search(cmd)
    if m:
        return f"it uses '{m.group(0).strip()}' (delete / install / download / system change)"
    for p in PATH_RX.findall(cmd):
        if not _inside(p, cwd, roots):
            return f"it uses a path outside the project folder ({p[:60]})"
    for part in CHAIN_RX.split(cmd):
        part = part.strip()
        if part and not SAFE_START_RX.match(part):
            return f"'{part[:60]}' is not one of the usual run / build / test commands"
    why = code_risk(cmd)  # python -c "import shutil; shutil.rmtree(...)"
    if why:
        return f"the command {why}"
    for name in (m.group(0) for m in SCRIPT_RX.finditer(cmd)):
        why = _script_risk(name, cwd)
        if why:
            return why
    run = re.match(r"(npm|yarn)\s+(?:run\s+([\w:-]+)|(test|start))", cmd, re.I)
    if run:  # a package.json script runs whatever it says
        try:
            table = json.loads((Path(cwd or ".") / "package.json").read_text(encoding="utf-8")).get("scripts") or {}
            scripts = str(table.get(run.group(2) or run.group(3), ""))
        except (OSError, ValueError, AttributeError):
            scripts = ""
        m = RISKY_RX.search(scripts)
        if m:
            return f"a package.json script uses '{m.group(0).strip()}'"
        why = code_risk(scripts)
        if why:
            return f"a package.json script {why}"
    return ""


def _script_risk(name, cwd):
    path = Path(cwd or ".") / name.strip("\"'")
    try:
        code = path.read_text(encoding="utf-8", errors="replace")[:400_000]
    except OSError:
        return ""  # not there: running it fails harmlessly
    if path.suffix.lower() in (".bat", ".cmd"):
        m = RISKY_RX.search(code)
        return f"{path.name} uses '{m.group(0).strip()}'" if m else ""
    why = code_risk(code)
    return f"{path.name} {why}" if why else ""


def _inside(path, cwd, roots):
    """The path lies inside one of the project folders."""
    if not roots:
        return False
    try:
        p = (Path(cwd or ".") / path.strip("\"'")).resolve()
        folders = [Path(r).resolve() for r in roots]
    except (OSError, ValueError):
        return False
    return any(p == f or f in p.parents for f in folders)
