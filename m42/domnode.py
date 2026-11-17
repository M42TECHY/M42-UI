"""🧩 A page's elements as nodes with their place in the file's own text (start, end offsets), a short map of them
for the 4B (its "skeleton": each block's tag, id, first classes and its words), and a node changed by splicing its
text alone into the file: every other byte of the page stays as it was (no parser writes the page again).

The 4B reads the map and picks the node; M42 never looks for words. (The user's idea, 2026-11-17: "DOM skeleton
indexing, two-pass routing": a section first, then the one block in it.)"""
import difflib
import hashlib
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "param"}
# not shown on the map: drawing parts and text-level tags whose words go to their block
HIDDEN = {"svg", "path", "g", "circle", "rect", "line", "polyline", "polygon", "defs", "use", "symbol", "br", "wbr",
          "meta", "link", "base", "title", "head", "html", "noscript"}
INLINE = {"span", "b", "strong", "em", "i", "small", "sup", "sub", "u", "mark", "abbr", "code", "kbd", "s", "label"}
SECTIONS = ("header", "section", "footer", "nav", "main", "aside")
ATTR_SHOWN = ("data-bs-target", "data-bs-toggle", "placeholder", "type", "href", "alt", "src", "name", "for", "role")


class _Indexer(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text, self.nodes, self.stack = text, [], []
        self.line_at = [0]
        for m in re.finditer("\n", text):
            self.line_at.append(m.end())

    def _off(self):
        line, col = self.getpos()
        return self.line_at[line - 1] + col

    def _open(self, tag, attrs, closed):
        start = self._off()
        raw = self.get_starttag_text() or ""
        n = {"id": len(self.nodes) + 1, "tag": tag, "attrs": {k: (v or "") for k, v in attrs},
             "start": start, "open_end": start + len(raw), "end": None, "line": self.getpos()[0],
             "parent": self.stack[-1]["id"] if self.stack else 0, "kids": [], "words": []}
        self.nodes.append(n)
        if self.stack:
            self.stack[-1]["kids"].append(n["id"])
        if closed or tag in VOID:
            n["end"] = n["open_end"]
        else:
            self.stack.append(n)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        if not any(x["tag"] == tag for x in self.stack):
            return  # (a stray closing tag: it closes nothing)
        at = self._off()
        close = self.text.find(">", at)
        end = close + 1 if close >= 0 else len(self.text)
        while self.stack:
            x = self.stack.pop()
            if x["tag"] == tag:
                x["end"] = end
                break
            x["end"] = at  # (an element left open: it ends where its parent closes)

    def handle_data(self, data):
        if self.stack and data.strip() and self.stack[-1]["tag"] not in ("script", "style"):
            self.stack[-1]["words"].append(" ".join(data.split()))

    def close(self):
        super().close()
        for x in self.stack:
            x["end"] = len(self.text)
        self.stack = []


def index(text):
    """Every element of the page: {id, tag, attrs, start, open_end, end, line, parent, kids, words}; ids in the
    file's order from 1. The same text always gives the same ids."""
    p = _Indexer(str(text or ""))
    try:
        p.feed(p.text)
        p.close()
    except (AssertionError, ValueError):
        pass
    for n in p.nodes:
        if n["end"] is None:
            n["end"] = len(p.text)
    return {n["id"]: n for n in p.nodes}


def signature(text):
    return hashlib.sha1(str(text or "").encode("utf-8", "ignore")).hexdigest()[:12]


def source(text, node):
    return text[node["start"]:node["end"]]


def splice(text, node, new):
    """The page with this node's text put in place of the old, every other byte as it was."""
    return text[:node["start"]] + new + text[node["end"]:]


def all_words(nodes, nid, limit=200):
    """The words in a node and every node in it, in order, short."""
    out, todo = [], [nid]
    while todo and sum(len(w) for w in out) < limit:
        n = nodes[todo.pop(0)]
        if n["tag"] in ("script", "style") or n["tag"] in HIDDEN - {"title"}:
            continue
        out += n["words"]
        todo = n["kids"] + todo
    return " | ".join(out)


def size(nodes, nid):
    """How many elements a node holds (itself included)."""
    k, todo = 0, [nid]
    while todo:
        n = nodes[todo.pop()]
        k += 1
        todo += n["kids"]
    return k


def _label(n):
    a = n["attrs"]
    cls = a.get("class", "").split()
    s = n["tag"] + (f'#{a["id"]}' if a.get("id") else "") + ("." + ".".join(cls[:2]) if cls else "")
    extra = []
    for k in ATTR_SHOWN:
        v = a.get(k)
        if v and not (k == "type" and n["tag"] not in ("input", "button")):
            v = v.rsplit("/", 1)[-1] if k == "src" else v
            extra.append(f'{k}="{v[:40]}"')
    return s + (" " + " ".join(extra[:3]) if extra else "")


def body_nodes(nodes):
    """The ids of the elements right in <body> (or the page's top elements when it has no body)."""
    body = next((n for n in nodes.values() if n["tag"] == "body"), None)
    if body:
        return list(body["kids"])
    return [n["id"] for n in nodes.values() if n["parent"] == 0 and n["tag"] not in ("html", "head")]


def skeleton(nodes, roots, lines=140, leaf=7, depth=7):
    """The map the 4B reads: one line per block, "[id] tag#id.class "its words"", children indented. A small block
    (up to `leaf` elements in it) is one line with all its words; repeated blocks beyond the first 6 of the same kind
    are said in one line. At most `lines` lines (deeper blocks folded first)."""
    for d in range(depth, 1, -1):
        out = []

        def walk(nid, lvl):
            n = nodes[nid]
            if n["tag"] in HIDDEN or n["tag"] in ("script", "style", "template"):
                return
            small = size(nodes, nid) <= leaf or lvl >= d or n["tag"] in INLINE
            words = all_words(nodes, nid, 90) if small else " | ".join(n["words"])
            words = words[:90] + ("…" if len(words) > 90 else "")
            out.append("  " * lvl + f"[{nid}] <{_label(n)}>" + (f' "{words}"' if words else ""))
            if small:
                return
            kids = [k for k in n["kids"] if nodes[k]["tag"] not in HIDDEN | {"script", "style", "template"}]
            seen = {}
            for k in kids:
                sig = _label(nodes[k]).split(" ")[0]
                seen[sig] = seen.get(sig, 0) + 1
                if seen[sig] == 7:
                    rest = [x for x in kids[kids.index(k):] if _label(nodes[x]).split(" ")[0] == sig]
                    out.append("  " * (lvl + 1) + f"[{rest[0]}..{rest[-1]}] {len(rest)} more <{sig}> like the ones above")
                if seen[sig] >= 7:
                    continue
                walk(k, lvl + 1)

        for r in roots:
            walk(r, 0)
        if len(out) <= lines or d == 2:
            return "\n".join(out[:lines])
    return ""


def section_of(nodes, nid):
    """The section the node is in: the nearest header / section / footer / nav / aside round it (itself too), else
    its block right under <body> / <main>."""
    n, top = nodes.get(nid), nid
    while n:
        if n["tag"] in ("section", "header", "footer", "nav", "aside"):
            return n["id"]
        p = nodes.get(n["parent"])
        if not p or p["tag"] in ("body", "main", "html"):
            return top
        top, n = p["id"], p
    return top


def in_lines(nodes, a, b):
    """The outermost nodes whose text is all within lines a..b (1-based)."""
    inside = {i for i, n in nodes.items() if a <= n["line"] and n["line"] <= b and n["tag"] not in HIDDEN}
    return [i for i in sorted(inside) if nodes[i]["parent"] not in inside]


def find_like(nodes, tag, words):
    """A node of this tag whose words start like these (a node picked on a preview of the page as it was)."""
    def flat(x):
        return " ".join(str(x or "").replace("|", " ").split()).lower()
    words = flat(words)[:40]
    if not words:
        return None
    for i, n in nodes.items():
        if n["tag"] == tag and flat(all_words(nodes, i, 160)).startswith(words):
            return i
    return None


UNIT_TAGS = ("section", "header", "footer", "nav", "aside")
HEAD_UNITS = ("style", "script", "link", "title", "meta")


def units(text, nodes=None):
    """The page's parts that a drawing from the plan changes as a whole: each outermost section / header / footer /
    nav / aside, and each <style>, <script>, <link>, <title>, <meta> not inside one. [(key, node)] in the file's
    order; the key is the tag (+ its id) and its count, the same on the old drawing, the new one and the file."""
    nodes = nodes or index(text)
    out, count, taken = [], {}, set()
    for n in nodes.values():
        if n["parent"] in taken:
            taken.add(n["id"])
            continue
        if n["tag"] in UNIT_TAGS or n["tag"] in HEAD_UNITS:
            k = n["tag"]  # (by place, not by id: a renamed section's id changes with its title)
            count[k] = count.get(k, 0) + 1
            out.append((f"{k}@{count[k]}", n))
            taken.add(n["id"])
    return out


def frame(text, us):
    """The page with each unit's text taken out: what holds the units (the layout's wrappers, columns)."""
    out, last = [], 0
    for k, n in us:
        out.append(text[last:n["start"]])
        out.append(f"\0{k}\0")
        last = n["end"]
    out.append(text[last:])
    return "".join(out)


def merge_render(old, new, current):
    """🧩 A page drawn again from its plan, put into the page AS IT IS NOW part by part: only the parts the plan
    changed (old drawing -> new drawing) are spliced into the current file, every other part as the file has it
    (the user's own edits, the block edits, the fixes stay byte for byte: the HTML is the truth, 2026-11-17).
    None when the drawing changed what holds the parts (a section added, removed, moved, resized) or a changed
    part is not in the file: the caller draws the whole page and carries the edits over instead."""
    if not old or not new or current is None:
        return None
    if old == new:
        return current
    uo, un = units(old), units(new)
    if [k for k, _ in uo] != [k for k, _ in un]:
        return None
    cur = dict(units(current))
    changes = []
    for (k, a), (_k, b) in zip(uo, un):
        tb = source(new, b)
        if source(old, a) == tb:
            continue
        if k not in cur:
            return None
        # (the user changed something in this part too: both kept where they touch different elements of it)
        both = merge3(source(old, a), tb, source(current, cur[k]))
        changes.append((cur[k], tb if both is None else both))
    out = current
    for n, t in sorted(changes, key=lambda x: -x[0]["start"]):
        out = out[:n["start"]] + t + out[n["end"]:]
    fo, fn = frame(old, uo), frame(new, un)
    if fo != fn:  # what holds the parts changed too (a link to a renamed section): those lines, if the file has them
        a_, b_ = fo.splitlines(keepends=True), fn.splitlines(keepends=True)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_, b_, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            was, now = "".join(a_[i1:i2]), "".join(b_[j1:j2])
            if "\0" in was or "\0" in now or not was.strip() or out.count(was) != 1:
                return None  # (a part added / removed / moved, or lines the file no longer has as drawn)
            out = out.replace(was, now, 1)
    return out


def _parts(text):
    """One element's text: (its frame with each child element as a mark, [the children's texts], [their tags])."""
    nodes = index(text)
    top = nodes.get(1)
    if not top or top["start"] != len(text) - len(text.lstrip()) or top["end"] < len(text.rstrip()):
        return None
    kids = [nodes[k] for k in top["kids"]]
    out, last = [], 0
    for i, n in enumerate(kids):
        out.append(text[last:n["start"]])
        out.append(f"\0{i}\0")
        last = n["end"]
    out.append(text[last:])
    return "".join(out), [source(text, n) for n in kids], [n["tag"] for n in kids]


def merge3(old, new, cur, depth=0):
    """One element changed two ways: old -> new (the plan) and old -> cur (the user). Both kept when they touch
    different elements in it (each child merged the same way); None when they touch the same one."""
    if old == new:
        return cur
    if old == cur or new == cur:
        return new
    if depth > 14:
        return None
    po, pn, pc = _parts(old), _parts(new), _parts(cur)
    if not (po and pn and pc) or not (po[2] == pn[2] == pc[2]):
        return None
    fo, fn, fc = po[0], pn[0], pc[0]
    fr = fc if fo == fn else fn if fo == fc else None
    if fr is None:
        return None
    for i, (ko, kn, kc) in enumerate(zip(po[1], pn[1], pc[1])):
        m = merge3(ko, kn, kc, depth + 1)
        if m is None:
            return None
        fr = fr.replace(f"\0{i}\0", m, 1)
    return fr


def add_class(text, nodes, ids, cls):
    """The page with this class added to these nodes' opening tags (only those bytes change)."""
    out = text
    for i in sorted({i for i in ids if i in nodes}, key=lambda i: -nodes[i]["start"]):
        n = nodes[i]
        tag = out[n["start"]:n["open_end"]]
        m = re.search(r'\sclass\s*=\s*"([^"]*)"', tag)
        if m and cls in m.group(1).split():
            continue
        new = (tag[:m.start(1)] + (m.group(1) + " " + cls).strip() + tag[m.end(1):]) if m else \
            re.sub(r"(\s*/?>)$", f' class="{cls}"' + r"\1", tag, count=1)
        out = out[:n["start"]] + new + out[n["open_end"]:]
    return out


def annotate(text, attr="data-m42-n"):
    """The page with each element in its body marked with its node id (for the preview only: a click on the page
    says which node it is). The file itself never gets these."""
    nodes = index(text)
    body = next((n for n in nodes.values() if n["tag"] == "body"), None)
    out, last = [], 0
    for n in nodes.values():
        if body and not (body["start"] < n["start"] < body["end"]):
            continue
        if n["tag"] in ("script", "style", "template") or n["tag"] in HIDDEN:
            continue
        at = n["open_end"] - 1
        at -= 1 if text[at - 1:at] == "/" else 0
        if at <= last or text[at] not in ">/":
            continue
        out.append(text[last:at])
        out.append(f' {attr}="{n["id"]}"')
        last = at
    out.append(text[last:])
    return "".join(out)


def strip(text, attr="data-m42-n"):
    return re.sub(r'\s' + re.escape(attr) + r'="\d+"', "", text)


def hooks(page_text, node_text):
    """The ids and classes in this node the page's scripts or CSS selectors name: a rewrite of the node must keep
    them (a coder renamed a class the script reads: its button did nothing, 2026-11-17)."""
    scripts = " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", page_text, re.S | re.I))
    keep = set()
    for v in re.findall(r'\bid="([^"]+)"', node_text):
        if re.search(r"['\"#]" + re.escape(v) + r"\b", scripts) or f'"#{v}"' in page_text or f"#{v}" in page_text.replace(f'id="{v}"', ""):
            keep.add("#" + v)
    for cl in re.findall(r'\bclass="([^"]+)"', node_text):
        for c in cl.split():
            if re.search(r"['\".]" + re.escape(c) + r"\b", scripts):
                keep.add("." + c)
    for v in re.findall(r'\b(data-[\w-]+)=', node_text):
        if v != "data-m42-n" and v in scripts:
            keep.add("[" + v + "]")
    return keep


def lost_hooks(page_text, old, new):
    have = hooks(page_text, new) | {"#" + v for v in re.findall(r'\bid="([^"]+)"', new)} \
        | {"." + c for cl in re.findall(r'\bclass="([^"]+)"', new) for c in cl.split()} \
        | {"[" + v + "]" for v in re.findall(r'\b(data-[\w-]+)=', new)}
    return sorted(hooks(page_text, old) - have)
