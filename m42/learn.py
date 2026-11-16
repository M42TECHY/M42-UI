"""M42 gets better the more it is used (a self-improving agent: memory, skill library, tool making, lessons).

1. Knowledge memory: an answer M42 looked up on the web is kept; the same question later gets it back (offline too).
2. Skill library: code that ran without errors (or firmware that passed M42's checks) is kept with the request;
   a similar request later starts from it, so the small model doesn't solve it from scratch again.
3. Tool making: the model can write a new tool (a Python `run(args)` function); after the user's OK and a test
   run it is kept and offered to the model like the built-in tools.
4. Lessons: when the user says an answer was wrong, the model writes the lesson in one line; similar requests
   later get the lessons.

Everything is in one SQLite file (memory/learned.db) with a full-text index; the user sees and deletes items in
the 🧠 Learned panel. Nothing leaves the PC."""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DIR = Path(os.environ.get("M42_MEMORY_DIR") or APP_DIR / "memory")  # tests use their own folder
DB = DIR / "learned.db"
TOOLS_DIR = DIR / "tools"
LIMITS = {"facts": 2000, "skills": 500, "lessons": 300, "tools": 30, "design": 200}
MAX_TOOLS_OFFERED = 8
MAX_TOOL_CODE = 6000  # a helper, not a program (a 13,600-character game was put in one)
TOOL_NAME_RX = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
STOP = set("""a an the and or but if then else of to in on at by for with from into about as is are was were be been
being it its this that these those i you he she we they me my your our their what which who whom how why when where
can could should would will shall may might must do does did done have has had not no yes so very just also than
too some any all each more most other such only own same few both again further once here there please give make
write create show tell explain need want using use used get got one two three new code program function
ena enna epdi epadi eppadi sollu solu pannu panni kudu kodu kutu tha thaa venum vennum oru intha itha antha athu
ithu la ku um ah nu da pa panna aagala agala aguthu aaguthu en yen irukku iruku irukka vachu sollunga
theriyala purila eppo epo evlo evvalavu enga yaar ethu etha mattum kooda kuda illa ila na naan nee ungal enakku
unakku ok sari seri""".split())
_lock = threading.Lock()


def stem(w):
    """pins -> pin, working -> work, libraries -> library (enough for matching a question asked again)."""
    if w[-1:].isdigit() or len(w) <= 4:
        return w
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("s", "")):
        if w.endswith(suf) and not w.endswith("ss") and len(w) - len(suf) >= 3:
            return w[:-len(suf)] + rep
    return w


def words(text):
    """Keywords of a text (lower case, no stop words, simple stems), in order, without repeats."""
    seen, out = set(), []
    for w in re.findall(r"[a-z0-9][a-z0-9+#._-]*[a-z0-9+#]|[a-z0-9]", (text or "").lower()):
        w = w.strip("._-")
        if w in STOP:
            continue
        w = stem(w)
        if len(w) >= 2 and w not in STOP and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _db():
    DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, question TEXT, answer TEXT, sources TEXT,
            created REAL, used INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, title TEXT, kind TEXT, files TEXT, proof TEXT,
            created REAL, used INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY, situation TEXT, lesson TEXT, created REAL,
            used INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tools (id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT, params TEXT,
            code TEXT, created REAL, used INTEGER DEFAULT 0);
        CREATE VIRTUAL TABLE IF NOT EXISTS idx USING fts5(kind UNINDEXED, ref UNINDEXED, text,
            tokenize='unicode61');
    """)
    return con


@contextmanager
def _open():
    """One connection per use: committed, then closed (an open file would stay locked on Windows)."""
    with _lock:
        con = _db()
        try:
            with con:
                yield con
        finally:
            con.close()


def _index(con, kind, ref, text):
    con.execute("DELETE FROM idx WHERE kind=? AND ref=?", (kind, str(ref)))
    con.execute("INSERT INTO idx (kind, ref, text) VALUES (?, ?, ?)", (kind, str(ref), " ".join(words(text))))


def _search(con, kind, text, limit=5, need=0.5, min_hits=2):
    """Rows of `kind` whose indexed words cover at least `need` of the query's keywords (and at least
    `min_hits` of them), best first."""
    keys = words(text)[:24]
    if not keys:
        return []
    query = " OR ".join('"' + k.replace('"', "") + '"' for k in keys)
    try:
        hits = con.execute("SELECT ref, text, bm25(idx) AS s FROM idx WHERE idx MATCH ? AND kind=? ORDER BY s "
                           "LIMIT 20", (query, kind)).fetchall()
    except sqlite3.OperationalError:
        return []
    out = []
    for h in hits:
        have = set(h["text"].split())
        hits_n = sum(k in have for k in keys)
        cover = hits_n / len(keys)
        if cover >= need and hits_n >= min(min_hits, len(keys)):
            out.append((cover, int(h["ref"])))
    out.sort(key=lambda x: -x[0])
    return [ref for _, ref in out[:limit]]


def _similar(con, kind, text, need):
    found = _search(con, kind, text, limit=1, need=need)
    return found[0] if found else None


def _prune(con, table):
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 - table names are constants
    extra = n - LIMITS[table]
    if extra > 0:
        old = [r[0] for r in con.execute(f"SELECT id FROM {table} ORDER BY used, created LIMIT ?", (extra,))]  # noqa: S608
        for i in old:
            _delete(con, table, i)


def _delete(con, table, ref):
    con.execute(f"DELETE FROM {table} WHERE id=?", (ref,))  # noqa: S608
    con.execute("DELETE FROM idx WHERE kind=? AND ref=?", (table, str(ref)))


def _used(con, table, ids):
    for i in ids:
        con.execute(f"UPDATE {table} SET used = used + 1 WHERE id=?", (i,))  # noqa: S608


# ---- 1. knowledge memory -----------------------------------------------------------------------------------------

def add_fact(question, answer, sources):
    """Keep an answer that came from the web. The same question again replaces the older answer."""
    question, answer = " ".join((question or "").split())[:600], (answer or "").strip()[:4000]
    if len(words(question)) < 2 or len(answer) < 80:
        return None
    with _open() as con:
        old = _similar(con, "facts", question, need=0.8)
        if old:
            _delete(con, "facts", old)
        cur = con.execute("INSERT INTO facts (question, answer, sources, created) VALUES (?, ?, ?, ?)",
                          (question, answer, json.dumps(list(sources or [])[:6]), time.time()))
        _index(con, "facts", cur.lastrowid, question)
        _prune(con, "facts")
        return cur.lastrowid


def recall_facts(question, limit=2):
    """'' or a note with earlier web answers to (almost) the same question."""
    with _open() as con:
        ids = _search(con, "facts", question, limit=limit, need=0.7)
        if not ids:
            return ""
        rows = [con.execute("SELECT * FROM facts WHERE id=?", (i,)).fetchone() for i in ids]
        _used(con, "facts", ids)
    parts = []
    for r in rows:
        when = time.strftime("%d %b %Y", time.localtime(r["created"]))
        src = ", ".join(json.loads(r["sources"] or "[]")[:3])
        parts.append(f"Q: {r['question']}\nA ({when}): {r['answer'][:900]}" + (f"\nSources: {src}" if src else ""))
    return ("\n\n[M42 memory: M42 looked this up on the web before. Use it if it answers the question (it may be "
            "out of date; check the web again if the user asks for current information):]\n" + "\n\n".join(parts))


# ---- 2. skill library --------------------------------------------------------------------------------------------

def add_skill(title, kind, files, proof):
    """Keep code that worked. files: [(name, code)]. A similar request again replaces the older skill."""
    files = [(str(n), str(c)) for n, c in files if c and len(c) < 60_000][:4]
    title = " ".join((title or "").split())[:300]
    if not files or len(words(title)) < 2:
        return None
    with _open() as con:
        old = _similar(con, "skills", title, need=0.85)
        if old:
            _delete(con, "skills", old)
        cur = con.execute("INSERT INTO skills (title, kind, files, proof, created) VALUES (?, ?, ?, ?, ?)",
                          (title, kind, json.dumps(files), proof, time.time()))
        _index(con, "skills", cur.lastrowid, title + " " + kind + " " + " ".join(n for n, _ in files))
        _prune(con, "skills")
        return cur.lastrowid


LAST_SKILL = None


def recall_skill(request, kind=None, max_chars=2500):
    """'' or a note with the code of the closest earlier skill (one, kept short: it is read on every step)."""
    with _open() as con:
        ids = _search(con, "skills", request, limit=3, need=0.5)
        rows = [con.execute("SELECT * FROM skills WHERE id=?", (i,)).fetchone() for i in ids]
        rows = [r for r in rows if r and (not kind or r["kind"] == kind)][:1]
        if not rows:
            return ""
        _used(con, "skills", [rows[0]["id"]])
    global LAST_SKILL  # (id, its code): forgotten later if the code copied from it turns out wrong
    LAST_SKILL = (rows[0]["id"], "\n".join(c for _, c in json.loads(rows[0]["files"])))
    r, left, code = rows[0], max_chars, []
    for name, text in json.loads(r["files"]):
        if left <= 200:
            break
        piece = text if len(text) <= left else text[:left] + "\n... (rest left out)"
        code.append(f"--- {name} ---\n{piece}")
        left -= len(piece)
    return (f"\n\n[M42 skill library: code that worked before for a similar request (\"{r['title'][:120]}\"; "
            f"{r['proof']}). Reuse the parts that fit; this request may differ, so adapt it:]\n" + "\n".join(code))


# ---- 4. lessons --------------------------------------------------------------------------------------------------

CORRECTION_RX = re.compile(
    r"\b(wrong|incorrect|not (right|correct|working|what i (asked|wanted))|doesn'?t work|didn'?t work|no,|"
    r"thappu|thapu|tappu|sari ?illa|sariyilla|sariya illa|work aagala|work agala|velai seyyala|ithu illa|"
    r"athu illa|naan ketathu|na ketathu|nan sonnathu|bug|mistake|tharuthala|varala)\b", re.I)
LESSON_PROMPT = """The user corrected M42's previous answer. Write ONE general lesson (max 25 words) that M42 should
follow next time in a similar situation, e.g. "When a pasted report ends with 'ithu ena', explain it; don't start
building." If the user only asked for a small change, not a correction of a mistake, set useful to false."""


def lesson_schema():
    return {"type": "object", "properties": {"useful": {"type": "boolean"},
                                             "lesson": {"type": "string", "maxLength": 200}},
            "required": ["useful", "lesson"]}


def lesson_messages(previous_request, previous_answer, correction):
    return [{"role": "system", "content": LESSON_PROMPT},
            {"role": "user", "content": f"Previous request: {previous_request[:500]}\n\nM42's answer (start): "
                                        f"{previous_answer[:700]}\n\nThe user then said: {correction[:500]}"}]


def _lessons_pending(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(lessons)").fetchall()}
    if cols and "pending" not in cols:
        con.execute("ALTER TABLE lessons ADD COLUMN pending INTEGER DEFAULT 1")  # (never confirmed: pending)


def confirm_lesson(lesson_id, keep):
    """The user's answer to a pending lesson (from a correction): kept or forgotten."""
    with _open() as con:
        _lessons_pending(con)
        if not con.execute("SELECT 1 FROM lessons WHERE id=?", (int(lesson_id),)).fetchone():
            return False
        if keep:
            con.execute("UPDATE lessons SET pending=0 WHERE id=?", (int(lesson_id),))
        else:
            _delete(con, "lessons", int(lesson_id))
        return True


def add_lesson(situation, lesson):
    """A lesson from the user's correction, PENDING until the user confirms it (confirm_lesson)."""
    lesson = " ".join((lesson or "").split())[:240]
    if len(words(lesson)) < 3:
        return None
    with _open() as con:
        _lessons_pending(con)
        old = _similar(con, "lessons", lesson, need=0.8)
        if old:
            _delete(con, "lessons", old)
        cur = con.execute("INSERT INTO lessons (situation, lesson, created, pending) VALUES (?, ?, ?, 1)",
                          (" ".join((situation or "").split())[:400], lesson, time.time()))
        _index(con, "lessons", cur.lastrowid, situation + " " + lesson)
        _prune(con, "lessons")
        return cur.lastrowid


def recall_lessons(request, limit=3):
    with _open() as con:
        _lessons_pending(con)
        ids = _search(con, "lessons", request, limit=limit, need=0.25, min_hits=3)
        rows = [con.execute("SELECT lesson FROM lessons WHERE id=? AND pending=0", (i,)).fetchone() for i in ids]
        _used(con, "lessons", ids)
    rows = [r["lesson"] for r in rows if r]
    return ("\n\n[Lessons M42 learned from the user's earlier corrections; follow them:]\n"
            + "\n".join(f"- {x}" for x in rows)) if rows else ""


# ---- 2b. design lessons: what M42 learns from looking at its own pages ----------------------------------------------
# (the user, 2026-11-14: "did it learn anything? other prompts must come out as well"): after a build, the vision model
# looks at the page (agent._vision_review); a fix it makes is kept only when the page before and after shows it better.
# Either way the 4B writes ONE general rule from it, for any business (worked = the fix made it better; not worked =
# that way of fixing made it worse), and the next builds read the rules of their kind (a landing page / an app screen)
# before they plan and before they look.

DESIGN_LESSON_PROMPT = """M42 built a page and then looked at it as a premium designer. It saw a problem and tried a fix;
the page before and after the fix were compared. Write ONE general rule (max 30 words) for building future pages of
ANY business, so this problem does not come back: no business names, no words from this page, about how such a page
should be planned or drawn. If the fix made the page worse, the rule says what not to do. If there is no general
rule in it (a one-off typo, a taste matter), useful = false."""


def design_lesson_schema():
    return {"type": "object", "properties": {"useful": {"type": "boolean"}, "rule": {"type": "string", "maxLength": 220}},
            "required": ["useful", "rule"]}


def design_lesson_messages(kind, request, problem, fix, worked):
    return [{"role": "system", "content": DESIGN_LESSON_PROMPT},
            {"role": "user", "content": f"The page: {kind} for {request[:200]}\nThe problem seen: {problem[:300]}\n"
                                        f"The fix tried: {fix[:300]}\nResult: "
                                        + ("the page was better after it (kept)" if worked else "the page was worse after it (taken back)")}]


# (the user, 2026-11-16: "it learned before I said the change was right, and the next page came out with it": a rule
# is kept PENDING and used only after the user confirms it; the rules learned before this, never confirmed, are
# pending too)
def _design_table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS design (id INTEGER PRIMARY KEY, kind TEXT, situation TEXT, rule TEXT,
                   worked INTEGER, seen INTEGER DEFAULT 1, created REAL, used INTEGER DEFAULT 0)""")
    cols = {r[1] for r in con.execute("PRAGMA table_info(design)").fetchall()}
    if "pending" not in cols:
        con.execute("ALTER TABLE design ADD COLUMN pending INTEGER DEFAULT 1")  # (the old ones: never confirmed)


def confirm_design(rule_id, keep):
    """The user's answer to a pending rule: kept (used from now on) or forgotten. True when it was there."""
    with _open() as con:
        _design_table(con)
        if not con.execute("SELECT 1 FROM design WHERE id=?", (int(rule_id),)).fetchone():
            return False
        if keep:
            con.execute("UPDATE design SET pending=0 WHERE id=?", (int(rule_id),))
        else:
            con.execute("DELETE FROM design WHERE id=?", (int(rule_id),))
            con.execute("DELETE FROM idx WHERE kind='design' AND ref=?", (str(int(rule_id)),))
        return True


def add_design_lesson(kind, situation, rule, worked):
    """A design rule learned from a page M42 looked at (kind: "landing" / "app"); a rule like one there is replaced
    (the newest wording, its count kept). Returns its id, or None."""
    rule = " ".join((rule or "").split())[:260]
    if len(words(rule)) < 4:
        return None
    with _open() as con:
        _design_table(con)
        old = _similar(con, "design", f"{kind} {rule}", need=0.7)
        seen = 1
        if old:
            row = con.execute("SELECT seen FROM design WHERE id=?", (old,)).fetchone()
            seen = (row["seen"] if row else 0) + 1
            con.execute("DELETE FROM design WHERE id=?", (old,))
            con.execute("DELETE FROM idx WHERE kind='design' AND ref=?", (str(old),))
        cur = con.execute("INSERT INTO design (kind, situation, rule, worked, seen, created, pending) VALUES (?, ?, ?, ?, ?, ?, 1)",
                          (kind, " ".join((situation or "").split())[:300], rule, 1 if worked else 0, seen, time.time()))
        _index(con, "design", cur.lastrowid, f"{kind} {situation} {rule}")
        n = con.execute("SELECT COUNT(*) FROM design").fetchone()[0]
        if n > 200:
            for (i,) in con.execute("SELECT id FROM design ORDER BY seen, used, created LIMIT ?", (n - 200,)).fetchall():
                con.execute("DELETE FROM design WHERE id=?", (i,))
                con.execute("DELETE FROM idx WHERE kind='design' AND ref=?", (str(i),))
        return cur.lastrowid


def recall_design(kind, request="", limit=5):
    """The design rules of this kind of page for a prompt ("" when none yet): the ones nearest the request, then the
    ones seen most often."""
    with _open() as con:
        _design_table(con)
        near = _search(con, "design", f"{kind} {request}", limit=limit, need=0.15, min_hits=1) if request else []
        rows = [con.execute("SELECT id, rule, worked FROM design WHERE id=? AND kind=? AND pending=0", (i, kind)).fetchone() for i in near]
        rows = [r for r in rows if r]
        if len(rows) < limit:
            have = {r["id"] for r in rows}
            rows += [r for r in con.execute("SELECT id, rule, worked FROM design WHERE kind=? AND pending=0 ORDER BY seen DESC, created DESC LIMIT ?",
                                            (kind, limit * 2)).fetchall() if r["id"] not in have][:limit - len(rows)]
        _used(con, "design", [r["id"] for r in rows])
    if not rows:
        return ""
    return ("\n\nRules M42 learned from looking at its own pages (follow them):\n"
            + "\n".join(f"- {r['rule']}" for r in rows))


def design_listing(limit=50):
    """[(kind, rule, worked, seen)] newest first, for the Learned panel."""
    with _open() as con:
        _design_table(con)
        return [(r["kind"], r["rule"], bool(r["worked"]), r["seen"]) for r in
                con.execute("SELECT kind, rule, worked, seen FROM design ORDER BY created DESC LIMIT ?", (limit,)).fetchall()]

# ---- 3. tool making ----------------------------------------------------------------------------------------------

MAKE_TOOL_SPEC = {"type": "function", "function": {
    "name": "make_tool",
    "description": "Save a small reusable helper as an M42 tool (a Python function M42 can call later), when the "
                   "user asks for a tool: a unit converter, a resistor / LED calculator, a parser for a file "
                   "format. Never use it to deliver what the user asked for (a game, a page, an app, a program): "
                   "write that as code in your answer. Standard library only, under 150 lines. The user approves "
                   "it once; M42 tests it with `example` first.",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string", "description": "snake_case, e.g. 'resistor_for_led'"},
        "description": {"type": "string", "description": "What it does and returns, one sentence"},
        "parameters": {"type": "object", "description": "JSON schema of the arguments, e.g. {\"type\": \"object\", "
                                                        "\"properties\": {\"volts\": {\"type\": \"number\"}}}"},
        "code": {"type": "string", "description": "Python source defining def run(args): ... that returns a string"},
        "example": {"type": "object", "description": "Arguments for the first test run"},
    }, "required": ["name", "description", "parameters", "code", "example"]}}}
TOOL_PREFIX = "tool_"


def tool_specs():
    """The learned tools, offered to the model like the built-in ones (the most used first)."""
    try:
        with _open() as con:
            rows = con.execute("SELECT name, description, params FROM tools ORDER BY used DESC, created DESC "
                               "LIMIT ?", (MAX_TOOLS_OFFERED,)).fetchall()
    except sqlite3.Error:
        return []
    specs = []
    for r in rows:
        try:
            params = json.loads(r["params"])
        except ValueError:
            params = {"type": "object", "properties": {}}
        specs.append({"type": "function", "function": {
            "name": TOOL_PREFIX + r["name"], "description": "(made by M42) " + r["description"][:200],
            "parameters": params if isinstance(params, dict) else {"type": "object", "properties": {}}}})
    return specs


def tool_code(name):
    with _open() as con:
        r = con.execute("SELECT code FROM tools WHERE name=?", (name,)).fetchone()
    return r["code"] if r else None


def check_new_tool(args):
    """Problems with a make_tool call, or ''."""
    name = str(args.get("name") or "")
    if not TOOL_NAME_RX.match(name):
        return "name must be snake_case (letters, digits, _), 3-40 characters"
    if not re.search(r"^def run\(\s*args\s*\)\s*:", str(args.get("code") or ""), re.M):
        return "code must define def run(args): returning a string"
    if not isinstance(args.get("parameters"), dict):
        return "parameters must be a JSON schema object"
    if len(str(args.get("code") or "")) > MAX_TOOL_CODE:
        return (f"a tool is a small helper (under {MAX_TOOL_CODE} characters); write a program the user asked for "
                "as code in the answer instead")
    return ""


def run_tool_code(code, args, cwd=None, timeout=60):
    """Run a tool's code in its own Python process (isolated mode, time limit). Returns (ok, text)."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOLS_DIR / f"run_{hashlib.sha1(code.encode()).hexdigest()[:12]}.py"
    path.write_text(code + "\n\nif __name__ == '__main__':\n    import json as _j, sys as _s\n"
                    "    _a = _j.loads(_s.stdin.read() or '{}')\n    print(str(run(_a))[:20000])\n", encoding="utf-8")
    try:
        p = subprocess.run([sys.executable, "-I", str(path)], input=json.dumps(args or {}), capture_output=True,
                           text=True, timeout=timeout, cwd=str(cwd or TOOLS_DIR), encoding="utf-8",
                           errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout} s"
    out = (p.stdout or "").strip()
    if p.returncode:
        return False, ((p.stderr or "").strip()[-1500:] or out[-800:] or f"exit code {p.returncode}")
    return True, out or "(no output)"


def add_tool(name, description, params, code):
    with _open() as con:
        old = con.execute("SELECT id FROM tools WHERE name=?", (name,)).fetchone()
        if old:
            _delete(con, "tools", old["id"])
        cur = con.execute("INSERT INTO tools (name, description, params, code, created) VALUES (?, ?, ?, ?, ?)",
                          (name, " ".join(str(description).split())[:300], json.dumps(params), code, time.time()))
        _index(con, "tools", cur.lastrowid, name.replace("_", " ") + " " + description)
        _prune(con, "tools")
        return cur.lastrowid


def tool_used(name):
    with _open() as con:
        con.execute("UPDATE tools SET used = used + 1 WHERE name=?", (name,))


# ---- the 🧠 Learned panel ----------------------------------------------------------------------------------------

def listing():
    with _open() as con:
        return {
            "facts": [dict(id=r["id"], title=r["question"], detail=r["answer"][:400], created=r["created"],
                           used=r["used"]) for r in con.execute("SELECT * FROM facts ORDER BY created DESC")],
            "skills": [dict(id=r["id"], title=r["title"], detail=f"{r['kind']} · {r['proof']} · "
                            + ", ".join(n for n, _ in json.loads(r["files"])), created=r["created"], used=r["used"])
                       for r in con.execute("SELECT * FROM skills ORDER BY created DESC")],
            "lessons": [dict(id=r["id"], title=r["lesson"], detail=r["situation"], created=r["created"],
                             used=r["used"]) for r in con.execute("SELECT * FROM lessons ORDER BY created DESC")],
            "tools": [dict(id=r["id"], title=r["name"], detail=r["description"] + "\n\n" + r["code"][:1500],
                           created=r["created"], used=r["used"])
                      for r in con.execute("SELECT * FROM tools ORDER BY created DESC")],
            "design": [dict(id=r["id"], title=("✅ " if r["worked"] else "❌ ") + r["rule"],
                            detail=f'{"App screens" if r["kind"] == "app" else "Landing pages"} · seen {r["seen"]}× · from: {r["situation"]}',
                            created=r["created"], used=r["used"])
                       for r in con.execute("SELECT * FROM design ORDER BY created DESC")] if con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='design'").fetchone() else [],
        }


def forget(kind, ref):
    if kind not in LIMITS:
        raise ValueError("unknown kind")
    with _open() as con:
        _delete(con, kind, int(ref))
