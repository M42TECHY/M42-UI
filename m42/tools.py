"""Workspace-confined tools the agent can call: list, read, write, edit, search, run."""
import difflib
import fnmatch
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import privacy

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode",
                "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".m42"}
BACKUP_DIR = Path(".m42") / "backups"


def _atomic_write(p, text):
    """Write to a temp file, then rename: after a power cut the file is the old one or the new one, never
    half of it."""
    tmp = p.with_name(p.name + ".m42tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, p)  # inside each project folder: the old version of every changed file
MAX_READ_CHARS = 24000
MAX_OUTPUT_CHARS = 8000
MAX_DIFF_LINES = 400

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List files and folders in the workspace as a tree.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Folder relative to workspace. Default '.'"},
            "depth": {"type": "integer", "description": "How many levels deep (1-4). Default 2"},
        }},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file. Optionally only a line range.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer"},
            "end_line": {"type": "integer"},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create a NEW file with the given content. To change a file that already exists, use "
                       "edit_file (only the lines that change); write_file over an existing file is only for a "
                       "complete rewrite the user asked for.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Change an existing file: old_text (a few lines copied exactly, appearing once) is "
                       "replaced by new_text. Use it for every change to an existing file, one call per place; "
                       "the rest of the file stays as it is.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        }, "required": ["path", "old_text", "new_text"]},
    }},
    {"type": "function", "function": {
        "name": "search",
        "description": "Search file contents in the workspace with a regex. Returns path:line: text.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "Folder to search. Default '.'"},
            "glob": {"type": "string", "description": "Filename filter, e.g. '*.py'"},
        }, "required": ["pattern"]},
    }},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Run a Windows cmd command in the workspace folder (e.g. 'python main.py', "
                       "'pytest -q', 'gcc main.c -o main.exe && main.exe'). Returns exit code and output.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "description": "Seconds, default 60, max 600"},
            "folder": {"type": "string", "description": "Folder to run in, e.g. 'backend' in a project "
                                                        "with several folders. Default: the first folder"},
        }, "required": ["command"]},
    }},
]

TOOL_NAMES = {t["function"]["name"] for t in TOOL_SPECS}
FILE_CHANGING = {"write_file", "edit_file"}


class ToolError(Exception):
    pass


def _clip(text, limit):
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n... [{len(text) - limit} chars cut] ...\n" + text[-half:]


def _read_text(path):
    data = path.read_bytes()
    if b"\0" in data[:8000]:
        raise ToolError(f"{path.name} looks like a binary file")
    return data.decode("utf-8", "replace")


def _unescape_if_needed(text):
    """Small models sometimes double-escape file content in JSON, so a whole file arrives as one line with
    literal backslash-n sequences (SyntaxError when run). Only repair that clear case."""
    if isinstance(text, str) and "\n" not in text and text.count("\\n") >= 2:
        return (text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
                .replace('\\"', '"').replace("\\'", "'"))
    return text


def _diff(rel, old, new):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                      f"a/{rel}", f"b/{rel}", lineterm=""))
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"... ({len(lines) - MAX_DIFF_LINES} more diff lines)"]
    return "\n".join(lines), added, removed


class Workspace:
    """The folders of a project (zero, one or several). With several folders, a path starts with the
    folder's name ("backend/app.py"); a path without one means the first folder."""

    def __init__(self, folders=()):
        if isinstance(folders, (str, Path)):
            folders = [folders]
        self.roots = []  # [(alias, Path)]
        used = set()
        for f in folders:
            p = Path(f).resolve()
            base = p.name or p.drive.rstrip(":") or "folder"
            alias, n = base, 2
            while alias.lower() in used:
                alias, n = f"{base}-{n}", n + 1
            used.add(alias.lower())
            self.roots.append((alias, p))

    @property
    def multi(self):
        return len(self.roots) > 1

    @property
    def root(self):
        return self.roots[0][1] if self.roots else None

    def _need_folder(self):
        if not self.roots:
            raise ToolError("This is a general chat with no project folders, so files can't be used here. "
                            "Answer directly, or tell the user to open a project (sidebar → Projects) "
                            "for file work.")

    def resolve(self, rel):
        self._need_folder()
        rel = (rel or ".").strip().strip('"')
        p = Path(rel)
        if p.is_absolute():
            p = p.resolve()
            if any(p == r or r in p.parents for _, r in self.roots):
                return p
            raise ToolError(f"'{rel}' is outside the project folders")
        root = self.root
        if self.multi and p.parts:
            for alias, r in self.roots:
                if p.parts[0].lower() == alias.lower():
                    root, p = r, Path(*p.parts[1:])
                    break
        elif (p.parts and p.parts[0].lower() == self.roots[0][0].lower()
              and not (root / p.parts[0]).exists()):
            p = Path(*p.parts[1:])  # "myproj/main.py" in project folder "myproj": the prefix is redundant
        q = (root / p).resolve()
        if q != root and root not in q.parents:
            raise ToolError(f"'{rel}' is outside the project folder {root}")
        return q

    def backup(self, p):
        """Copy a file about to be overwritten to <project>/.m42/backups/<time>/<path>, so a model's rewrite
        can always be undone by hand."""
        _, root = self.root_of(p)
        try:
            dest = root / BACKUP_DIR / time.strftime("%Y%m%d-%H%M%S") / p.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        except (OSError, ValueError):
            pass  # a failed backup must not block the edit

    def root_of(self, p):
        for alias, r in self.roots:
            if p == r or r in p.parents:
                return alias, r
        return self.roots[0]

    def rel(self, p):
        alias, r = self.root_of(p)
        sub = p.relative_to(r).as_posix()
        if self.multi:
            return alias if sub == "." else f"{alias}/{sub}"
        return sub

    def _top_level(self, path):
        """True when a multi-folder project is asked about its root (list/search every folder)."""
        return self.multi and (path or ".").strip().strip("./\\") == ""

    def walk(self, start, depth):
        """Yield (path, level) depth-first, folders first, skipping ignored dirs."""
        def rec(folder, level):
            try:
                entries = sorted(folder.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except OSError:
                return
            for e in entries:
                if e.is_dir() and e.name in IGNORED_DIRS:
                    continue
                yield e, level
                if e.is_dir() and level + 1 < depth:
                    yield from rec(e, level + 1)
        yield from rec(start, 0)

    # ---- tools -------------------------------------------------------------

    def list_dir(self, path=".", depth=2):
        self._need_folder()
        depth = max(1, min(int(depth or 2), 4))
        if self._top_level(path):  # one entry per project folder
            starts = [(f"{alias}/", r, 1) for alias, r in self.roots]
            summary = f"Listed {len(self.roots)} project folders"
        else:
            folder = self.resolve(path)
            if not folder.is_dir():
                raise ToolError(f"Not a folder: {path}")
            starts = [(None, folder, 0)]
            summary = f"Listed {self.rel(folder)}"
        out = []
        for header, folder, indent in starts:
            if header:
                out.append(header)
            for e, level in self.walk(folder, depth):
                out.append("  " * (level + indent) + e.name + ("/" if e.is_dir() else ""))
                if len(out) >= 300:
                    break
            if len(out) >= 300:
                out.append("... (truncated)")
                break
        return {"summary": summary, "content": "\n".join(out) or "(empty folder)"}

    def read_file(self, path, start_line=None, end_line=None):
        p = self.resolve(path)
        if not p.is_file():
            raise ToolError(f"File not found: {path}")
        lines = _read_text(p).splitlines()
        total = len(lines)
        s = max(1, int(start_line or 1))
        e = min(total, int(end_line or total))
        body = "\n".join(lines[s - 1:e])
        header = f"[{self.rel(p)} lines {s}-{e} of {total}]\n"
        return {"summary": f"Read {self.rel(p)} ({e - s + 1 if total else 0} lines)",
                "content": header + _clip(body, MAX_READ_CHARS), "path": self.rel(p)}

    def write_file(self, path, content):
        content = _unescape_if_needed(content)
        content = privacy.scrub_file(path, content)  # no personal details in a page (example ones in their place)
        p = self.resolve(path)
        if p.is_dir():
            raise ToolError(f"{path} is a folder")
        old = _read_text(p) if p.exists() else ""
        existed = p.exists()
        if existed and old != content:
            self.backup(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(p, content)
        rel = self.rel(p)
        diff, added, removed = _diff(rel, old, content)
        verb = "Updated" if existed else "Created"
        return {"summary": f"{verb} {rel} (+{added} -{removed})",
                "content": f"{verb} {rel}: {len(content.splitlines())} lines written.",
                "diff": diff, "path": rel, "changed": True}

    def edit_file(self, path, old_text, new_text):
        old_text, new_text = _unescape_if_needed(old_text), _unescape_if_needed(new_text)
        p = self.resolve(path)
        if not p.is_file():
            raise ToolError(f"File not found: {path}. Use write_file to create it.")
        text = _read_text(p)
        if not old_text:
            raise ToolError("old_text is empty")
        count = text.count(old_text)
        if count == 1:
            new = text.replace(old_text, new_text, 1)
        elif count > 1:
            raise ToolError(f"old_text appears {count} times in {path}; include more surrounding lines")
        else:
            new = self._fuzzy_replace(text, old_text, new_text, path)
        new = privacy.scrub_file(path, new)  # (an edit can bring in a real phone / e-mail too)
        if new != text:
            self.backup(p)
        _atomic_write(p, new)
        rel = self.rel(p)
        diff, added, removed = _diff(rel, text, new)
        return {"summary": f"Edited {rel} (+{added} -{removed})",
                "content": f"Edited {rel} successfully.", "diff": diff, "path": rel, "changed": True}

    @staticmethod
    def _fuzzy_replace(text, old_text, new_text, path):
        """Small models often get indentation/trailing spaces wrong: match line-by-line on stripped text."""
        want = [l.strip() for l in old_text.strip("\n").splitlines()]
        have = text.splitlines(keepends=True)
        n = len(want)
        hits = [i for i in range(len(have) - n + 1)
                if all(have[i + k].strip() == want[k] for k in range(n))]
        if len(hits) != 1:
            why = "not found" if not hits else f"matches {len(hits)} places"
            raise ToolError(f"old_text {why} in {path}. Read the file again and copy the exact lines.")
        i = hits[0]
        replacement = new_text
        if have[i + n - 1].endswith("\n") and not replacement.endswith("\n"):
            replacement += "\n"
        return "".join(have[:i]) + replacement + "".join(have[i + n:])

    def search(self, pattern, path=".", glob=None):
        self._need_folder()
        folders = [r for _, r in self.roots] if self._top_level(path) else [self.resolve(path)]
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(pattern), re.IGNORECASE)
        hits = []
        files = (f for folder in folders for f, _ in self.walk(folder, 12))
        for f in files:
            if not f.is_file() or (glob and not fnmatch.fnmatch(f.name, glob)):
                continue
            try:
                if f.stat().st_size > 1_000_000:
                    continue
                text = _read_text(f)
            except (OSError, ToolError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{self.rel(f)}:{n}: {line.strip()[:200]}")
                    if len(hits) >= 100:
                        break
            if len(hits) >= 100:
                hits.append("... (more matches truncated)")
                break
        return {"summary": f"Search '{pattern}': {len(hits)} matches",
                "content": "\n".join(hits) or "No matches."}

    def run_command(self, command, timeout=60, folder=None):
        self._need_folder()
        cwd = self.resolve(folder) if folder else self.root
        if not cwd.is_dir():
            raise ToolError(f"Not a folder: {folder}")
        timeout = max(1, min(int(timeout or 60), 600))
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, creationflags=flags)
        timed_out = False
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill_tree(proc)
            out, _ = proc.communicate()
        output = _clip((out or b"").decode("utf-8", "replace").replace("\r\n", "\n"), MAX_OUTPUT_CHARS)
        code = proc.returncode
        status = f"timed out after {timeout}s" if timed_out else f"exit code {code}"
        return {"summary": f"`{command}` → {status}",
                "content": f"[{status}]\n{output or '(no output)'}",
                "output": output, "ok_run": (not timed_out and code == 0), "changed": True}

    @staticmethod
    def _kill_tree(proc):
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()

    def call(self, name, args):
        if name not in TOOL_NAMES:
            raise ToolError(f"Unknown tool '{name}'. Available: {', '.join(sorted(TOOL_NAMES))}")
        try:
            return getattr(self, name)(**args)
        except TypeError as e:
            raise ToolError(f"Bad arguments for {name}: {e}")
