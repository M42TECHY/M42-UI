"""Line edits for the pages M42 UI writes (taken from M42's builder.py): the model answers with SEARCH / REPLACE
blocks, M42 applies them; and the prompts for reading a screenshot."""
import json
import re
from pathlib import Path

CODE_EXT = (".html", ".htm", ".js", ".mjs", ".css", ".py", ".ts", ".php")


MAP_FILE = Path(".m42") / "build.json"


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


VISION_PROMPT = """You look at a screenshot the user took while testing their program (often a game or web page).
Answer in three short parts:
SEEN: at most 8 items, each "colour + shape (what it probably is) - where", e.g. "red square (player?) - left,
floating above the ground". Group repeated things in one item ("a row of 8 coloured squares - right"); ignore the
browser's own toolbars and console unless they show an error. Say where things touch, overlap or are cut off. Simple coloured boxes are normal in
these games: a box can be the player, an enemy, a block or a pipe.
TEXT: any visible text, numbers or error messages, copied exactly, and where they are.
PROBLEM: what in the picture matches the user's report. The user tested the real program, so trust their report;
if you can't see it clearly, write "not clear in the picture" instead of saying it is not there. If the user only
asks whether it is right, list what looks wrong or missing compared with what the program should show (a player
floating in the air, an empty level, missing enemies or blocks, text over other things).
Describe only what you can see; don't guess about the code. The user may write Tanglish (Tamil in English letters):
saganum = should die, varala = does not appear, work agala = does not work, mela = on top / above, keela = below,
nikkala = does not stand, thara = ground, mattum = only, aganum = should, correctya / sariya = is it right?
(a question, not a complaint), intha = this."""


VISION_USER = "The user says: {text}\nDescribe the screenshot for a programmer who will fix the problem."


# a picture of what the user WANTS ("enakku itha mathiri venum"): a spec to build from, one fact per line; these
# lines become the facts of a new plan (the bug-report prompt above called the car a "blue circle")
# No concrete example values here: with "a big orange timer 0:54" as an example, the model reported a 0:54 timer
# in a platformer picture that had none
REFERENCE_VISION_PROMPT = """The user shows a picture of a game or app they want theirs to look and play like.
Write 6 to 10 short lines, one concrete fact each, that a programmer can build from:
- the view / camera: from which side the player sees the world (from above, from the side, from behind the
  player in 3D perspective, ...) and whether the screen scrolls
- the play area and its layout
- the background layers from far to near and their colours
- the player and the other objects: what they are and how they look
- the HUD elements that are really in the picture: what each shows and where
Describe only what is in THIS picture; if you are not sure something is there, leave it out. Facts only, no code,
no guesses about how it is programmed, no numbering. The user may write Tanglish."""


VISION_PLAN = ("\nThe program should be: {title}. {summary}\nPlanned features: {features}\n"
               "Say which of these you can't see in the picture.")


EDIT_PROMPT = """You fix code by changing only the lines that need it. Reply with "PLAN: <the cause and the
change>" (one to three short lines), then one or more edit blocks, nothing else:
<<<<<<< SEARCH
the current lines, copied exactly (without the line numbers), only a few lines that occur once in the file
=======
the new lines
>>>>>>> REPLACE
To add code, SEARCH one existing line and REPLACE it with that line plus the new lines. To delete, leave the
REPLACE part empty. JavaScript files are classic scripts sharing one global scope: no import/export.
Fix the cause: never hide an error with try/catch, a typeof check or console.error around the broken call;
define the missing function or variable, or call the one that exists. A function is declared once, in one
file, with the function keyword.
A web page of M42 already has its libraries in lib/ (Bootstrap 5, bootstrap-icons, anime.js 3.2.2 as anime({...}),
jQuery + Toastr, SweetAlert2 as Swal.fire): use those files with a relative path; never a CDN link, never another
version, never download a library.
The user may write Tanglish (Tamil in English letters): saganum = should die, udaiyanum = should break,
varala = does not appear, work agala = does not work, mattum = only, mela = on top, keela = below,
munnadi = forward, aganum/venum = should."""


# GBNF for line edits on llama-server: an optional one-line plan, then SEARCH/REPLACE blocks and nothing else
EDIT_GRAMMAR = r'''root ::= plan? edit+
plan ::= "PLAN: " [^\n]{1,300} "\n" (note){0,2}
note ::= [^\n<=>] [^\n]{0,299} "\n"
edit ::= "<<<<<<< SEARCH\n" line+ "=======\n" line* ">>>>>>> REPLACE\n"
line ::= ([^\n<=>] [^\n]* | "<" [^<\n] [^\n]* | "=" [^=\n] [^\n]* | ">" [^>\n] [^\n]*)? "\n"
'''  # a code line may not start with "<<", "==" or ">>": otherwise the markers counted as code lines, and the


# grammar let prose run on after ">>>>>>> REPLACE"
# fixes for what M42's checks found: small edits only. With no bound, coder-7b copied long SEARCH blocks of a bus
# booking page and ran to the 1,500-token limit (5 minutes, nothing applied, 2026-10-26).
FIX_GRAMMAR = EDIT_GRAMMAR.replace("root ::= plan? edit+", "root ::= plan? edit{1,6}").replace(
    '"<<<<<<< SEARCH\\n" line+ "=======\\n" line* ">>>>>>> REPLACE\\n"',
    '"<<<<<<< SEARCH\\n" line{1,10} "=======\\n" line{0,40} ">>>>>>> REPLACE\\n"')


def edits_runaway(text):
    """Stop the edit stream: 8 blocks, the same block twice, or a second block that changes nothing (Granite went
    on adding SEARCH == REPLACE blocks until max_tokens)."""
    blocks = EDIT_RX.findall(text)
    noop = [b for b in blocks if b[0].strip() == b[1].strip()]
    return len(blocks) >= 8 or len(noop) >= 2 or len(blocks) != len(set(blocks))


EDIT_RX = re.compile(r"<{5,9} ?SEARCH[^\n]*\n(.*?)\n?={5,9}[^\n]*\n(.*?)\n?>{5,9} ?REPLACE", re.S)


LINE_NO_RX = re.compile(r"^\s*\d+\s?\|\s?")


def parse_edits(reply):
    edits = []
    for search, replace in EDIT_RX.findall(reply):
        s_lines, r_lines = search.splitlines(), replace.splitlines()
        # the model sometimes copies the reference numbers: "  37| startGame();"
        if s_lines and all(LINE_NO_RX.match(l) for l in s_lines if l.strip()):
            s_lines = [LINE_NO_RX.sub("", l) for l in s_lines]
            r_lines = [LINE_NO_RX.sub("", l) for l in r_lines]
        edits.append(("\n".join(s_lines), "\n".join(r_lines)))
    return edits


def _replace_lines(text, search, replace):
    """Whole-line match ignoring indentation; the new lines take the file's indentation. None if the
    SEARCH lines don't occur exactly once."""
    want = [l.strip() for l in search.strip("\n").splitlines()]
    have = text.splitlines(keepends=True)
    n = len(want)
    hits = [i for i in range(len(have) - n + 1) if all(have[i + k].strip() == want[k] for k in range(n))]
    if len(hits) != 1:
        return None
    i = hits[0]
    file_indent = re.match(r"[ \t]*", have[i]).group(0)
    first = next((l for l in search.splitlines() if l.strip()), "")
    s_indent = re.match(r"[ \t]*", first).group(0)

    def reindent(line):
        if not line.strip():
            return line
        return file_indent + (line[len(s_indent):] if line.startswith(s_indent) else line.lstrip())

    new = "".join(reindent(l) + "\n" for l in replace.splitlines())
    return "".join(have[:i]) + new + "".join(have[i + n:])


BALANCE_TAGS = ("div", "section", "main", "header", "footer", "aside", "nav", "form", "ul", "ol", "table")


def tag_balance(text):
    """{tag: opened - closed} for the page's structural tags."""
    low = str(text or "").lower()
    return {t: len(re.findall(rf"<{t}\b", low)) - len(re.findall(rf"</{t}\s*>", low)) for t in BALANCE_TAGS}


def section_window(text, title, nth=0, pad=2):
    """(first line, last line), 1-based, of the page's <section> whose heading is `title` (its nth one when titles
    repeat), with `pad` lines round it; None when not found. A line edit then reads that part, not the whole page
    (a 300-line page cost ~90 s to read before each edit, 2026-11-12)."""
    title = re.sub(r"\s+", " ", str(title or "")).strip().lower()
    if not title:
        return None
    found = []
    for m in re.finditer(r"<section\b[^>]*>", text, re.I):
        depth, end = 0, None
        for t in re.finditer(r"<(/?)section\b[^>]*>", text[m.start():], re.I):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = m.start() + t.end()
                break
        if end is None:
            continue
        heads = [re.sub(r"<[^>]+>|\s+", " ", h).strip().lower() for h in re.findall(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]>", text[m.start():end], re.S | re.I)[:2]]
        if title in heads:
            found.append((m.start(), end))
    if len(found) <= nth:
        return None
    a, b = found[nth]
    first, last = text.count("\n", 0, a) + 1, text.count("\n", 0, b) + 1
    return max(1, first - pad), min(text.count("\n") + 1, last + pad)


def mend_tags(text):
    """A page with a structural tag closed twice, mended by M42 itself (no model: the 4B could not find it): walking
    the tags in order, a closing tag that does not close the element open at that point, while the page has more of
    those closers than openers, is the extra one and is removed. Returns (text, [what was removed])."""
    out, removed = str(text or ""), []
    for _ in range(6):
        bal = tag_balance(out)
        extra = [t for t in BALANCE_TAGS if bal[t] < 0]
        if not extra:
            break
        stack, cut = [], None
        for m in re.finditer(r"<(/?)(" + "|".join(BALANCE_TAGS) + r")\b[^>]*>", out, re.I):
            closing, tag = m.group(1) == "/", m.group(2).lower()
            if not closing:
                stack.append(tag)
            elif stack and stack[-1] == tag:
                stack.pop()
            elif tag in extra:
                cut = m
                break
            elif tag in stack:  # (an inner element left open: closed here, as the browser would)
                while stack and stack.pop() != tag:
                    pass
        if not cut:
            break
        line = out.count("\n", 0, cut.start()) + 1
        out = out[:cut.start()] + out[cut.end():]
        removed.append(f"an extra </{cut.group(2).lower()}> on line {line}")
    return out, removed


def apply_checked(text, edit):
    """One model edit block applied only if it keeps every structural tag's open / close count (a "fix mobile width"
    edit split a header's buttons into two divs and left the old </div>: it closed the page's main area and the whole
    content slid under the menu, 2026-11-12). Raises ValueError when it does not match or would break the page."""
    new = apply_edits(text, [edit])
    before, after = tag_balance(text), tag_balance(new)
    if any(abs(after[t]) > abs(before[t]) for t in BALANCE_TAGS):  # (an edit that mends a broken page passes)
        raise ValueError("the edit would leave a tag unclosed or closed twice")
    # a picture linked from another site (a line edit put via.placeholder.com where the user's photo was meant,
    # 2026-11-12): pages use their own images/ folder, offline
    ext = lambda s: set(re.findall(r"""<img\b[^>]*\bsrc\s*=\s*["'](https?://[^"']+)""", s, re.I))  # noqa: E731
    if ext(new) - ext(text):
        raise ValueError("the edit links a picture from another site")
    return new


def apply_edits(text, edits):
    """Apply (search, replace) pairs in order: whole lines first (indentation-tolerant, keeps the file's
    indentation), then an exact match of a fragment inside a line. Raises ValueError if a block doesn't
    match exactly one place."""
    for search, replace in edits:
        if not search.strip():
            raise ValueError("empty SEARCH block")
        new = _replace_lines(text, search, replace)
        if new is None:
            count = text.count(search)
            if count != 1:
                raise ValueError(f"SEARCH {'not found' if not count else f'matches {count} places'}: "
                                 f"{search.strip().splitlines()[0][:60]}")
            new = text.replace(search, replace, 1)
        text = new
    return text




_VARS_CACHE = {}


def css_vars(root, page=""):
    """The CSS variables a page can use: the ones its own CSS files define (css/theme.css, lib/*.css) and the ones the
    page itself sets (style="--t: ..."). A name outside these draws nothing."""
    names = set(re.findall(r"(--[\w-]+)\s*:", page or ""))
    if not root:
        return names
    from pathlib import Path
    root = Path(root)
    for f in [root / "css" / "theme.css", *sorted((root / "lib").glob("*.css")), *sorted((root / "css").glob("*.css"))]:
        try:
            key = (str(f), f.stat().st_mtime)
        except OSError:
            continue
        if key not in _VARS_CACHE:
            try:
                _VARS_CACHE[key] = set(re.findall(r"(--[\w-]+)\s*:", f.read_text(encoding="utf-8", errors="ignore")))
            except OSError:
                _VARS_CACHE[key] = set()
        names |= _VARS_CACHE[key]
    return names


def _colour_name(rgb):
    """A plain name for a colour (its hue and lightness): what a person calls it ("blue", "dark green")."""
    import colorsys
    r, g, b = [v / 255 for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < .15:
        return "white" if l > .9 else "light grey" if l > .7 else "grey" if l > .35 else "black"
    names = [(15, "red"), (40, "orange"), (65, "yellow"), (160, "green"), (195, "teal"), (255, "blue"), (290, "purple"),
             (335, "pink"), (360, "red")]
    hue = next(n for top, n in names if h * 360 <= top)
    return ("dark " if l < .34 else "light " if l > .75 else "") + hue


def css_colours(root, page=""):
    """{variable: "its value (its colour's name)"} for the page's own colour variables (--m42-...), from its CSS files
    and its <style> (the page's last), var(--x, fallback) followed: the line edit sees which one is blue (it took
    --m42-accent-2, a dark navy, for blue, 2026-11-13)."""
    from pathlib import Path
    texts = []
    if root:
        for f in [Path(root) / "lib" / "m42-ui.css", Path(root) / "css" / "theme.css"]:
            try:
                texts.append(f.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    texts.append(page or "")
    defs = {}
    for t in texts:
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;}{]+)", t):
            defs[name] = " ".join(value.split())[:80]

    def resolve(value, depth=0):
        m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", value)
        if not m or depth > 5:
            return value
        return resolve(defs[m.group(1)], depth + 1) if m.group(1) in defs else resolve(m.group(2) or "", depth + 1)

    out = {}
    for name in sorted(n for n in defs if n.startswith("--m42-")):
        value = resolve(defs[name])
        m = re.fullmatch(r"#([0-9a-fA-F]{6})", value)
        n = re.fullmatch(r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", value)
        rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)) if m else (tuple(map(int, n.groups())) if n else None)
        if rgb and all(v <= 255 for v in rgb):
            out[name] = f"{value} ({_colour_name(rgb)})"
    return out
