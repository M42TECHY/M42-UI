"""M42's flow library (2026-11-10): how real UIs of a kind are laid out, taken from the UIGEN-T2 pages (uiexamples.py:
40,409 "request -> HTML + Tailwind page" pairs, Apache-2.0). The user: "their models know a chat box, an inbox, a
3D site; we only use what we have. Take the flow from there, and show it better than they do."
A flow is the page's regions and what each holds: a side list (its heading, its entries), a top bar (title, search,
buttons), the main part (a message thread, a list of rows, a board, an editor, a grid of cards, a table, a player),
a pane beside it, a composer at the bottom. For each kind in KINDS the flows of its closest pages are counted into
one entry of knowledge/uigen-t2/flows.json (python uiflows.py build); a request of another kind gets the flow of
its own closest pages (flow_of). The 4B reads the flow as words before it writes the spec; for the kinds M42 has an
app template for (APP: chat, mail), M42 builds that template with the flow's own parts (its folders, its panes)."""
import collections
import json
import re
import sqlite3

import uiexamples

FILE = uiexamples.DIR / "flows.json"
# kind -> (words in a request that ask for it, the search in the dataset)
KINDS = {
    "chat": (r"chat\w*|messag\w+|messenger|whatsapp|conversations?|\bdm\b", "chat application conversations list message thread"),
    "mail": (r"e?-?mail\w*|inbox|mail ?box", "email client inbox folders reading pane"),
    "kanban": (r"kanban|task board|trello", "kanban board columns drag cards"),
    "notes": (r"notes?|notepad|text editor|markdown editor|editor", "notes app editor sidebar list"),
    "music": (r"music|audio player|spotify|playlist", "music player playlist now playing"),
    "video": (r"video (?:player|streaming|editor)|youtube|netflix", "video player streaming related list"),
    "calendar": (r"calendar|schedul\w+|planner", "calendar app month view events"),
    "feed": (r"social|feed|timeline|twitter|instagram", "social media feed posts composer"),
    "files": (r"file manager|drive|dropbox|documents?", "file manager folders grid upload"),
    "shop": (r"e-?commerce|product page|cart|checkout", "ecommerce product listing filters cart"),
    "dashboard": (r"dashboard|admin|analytics", "admin dashboard sidebar charts table"),
    "todo": (r"to-?do|tasks?|checklist", "todo list app add task filter"),
    "map": (r"maps?|tracking|location", "map view sidebar locations list"),
    "forum": (r"forum|community|q&a|discussion", "forum threads categories replies"),
    "settings": (r"settings|preferences|profile", "settings page sections toggles profile"),
    "booking": (r"booking|reservation|appointment", "booking interface select date time summary"),
    "weather": (r"weather|forecast", "weather app current conditions forecast"),
    "blog": (r"blog|article|news", "blog home posts categories sidebar"),
    "login": (r"log ?in|sign ?(?:in|up)|auth", "login page form social sign in"),
    "gallery": (r"gallery|photos?|portfolio", "photo gallery grid lightbox"),
}
APP = {"chat": ("Chat", "chat_app"), "mail": ("Mail", "mail_app")}  # the kinds M42 has an app template for
SIDE_RX = re.compile(r"\bw-(?:1/[345]|2/5|4[48]|5[26]|6[04]|72|80|96)\b|sidebar|\bside\b")
WORD_RX = re.compile(r"^[A-Za-z][A-Za-z &/-]{1,22}$")


def _labels(el, limit=8):
    """The short words a region's entries carry (its buttons, links, list rows): "Inbox", "Sent", "Starred"."""
    out = []
    for x in el.find_all(["a", "button", "li", "span", "h3", "h4"]):
        t = " ".join(x.get_text(" ").split())
        t = re.sub(r"\s*\d+\+?$", "", t).strip()
        if WORD_RX.match(t) and t.lower() not in [o.lower() for o in out]:
            out.append(t)
        if len(out) >= limit:
            break
    return out


HAS = [("chart", r"chart\.js|new chart\(|apexcharts|<canvas|recharts|d3\."), ("popup", r"\bmodal\b|dialog"),
       ("tabs", r"\btabs?\b|role=\"tab\""), ("drag and drop", r"draggable|dragstart|sortable"), ("upload", r"type=\"file\"|dropzone|upload"),
       ("map", r"leaflet|mapbox|google\.maps|<iframe[^>]+maps"), ("video", r"<video|youtube\.com/embed"), ("audio", r"<audio|new audio\("),
       ("table", r"<table"), ("form", r"<form"), ("dark mode", r"dark:|theme-toggle|darkmode|dark-mode"), ("carousel", r"carousel|swiper|slider"),
       ("accordion", r"accordion|<details"), ("3d", r"three\.js|three\.min|webgl|perspective\(|rotatey|rotate3d|preserve-3d"),
       ("animation", r"@keyframes|animate-|gsap|aos\.|transition-"), ("local storage", r"localstorage"), ("search", r"type=\"search\"|placeholder=\"search")]


def regions(html, full=""):
    """One page's flow: {"side": [...labels] | None, "side_title", "bar": bool, "search": bool, "main": kind, "pane": bool,
    "composer": bool, "has": [...], "parts": [...]}. full: the page with its scripts (the index keeps it without them)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    sides = [el for el in body.find_all(["aside", "nav", "div"]) if (el.name == "aside" or (
        el.name in ("div", "nav") and SIDE_RX.search(" ".join(el.get("class") or []) + " " + str(el.get("id") or ""))))
        and not el.find_parent("aside") and len(el.get_text(" ").split()) < 400]
    side = sides[0] if sides else None
    head = side.find(["h1", "h2", "h3"]) if side else None
    low = (full or html).lower()
    script = " ".join(re.findall(r"(?is)<script\b[^>]*>(.*?)</script>", full or ""))[:20000].lower()
    text = body.get_text(" ").lower() + " " + re.sub(r"[^a-z0-9 .!?'\"]+", " ", script)
    classes = " ".join(" ".join(el.get("class") or []) for el in body.find_all(True)[:400]) + " " + " ".join(re.findall(r"class(?:name)?=[\"'`]([^\"'`]+)", script))[:6000]
    holders = " ".join(str(i.get("placeholder") or "") for i in body.find_all(["input", "textarea"])).lower()
    # a chat thread: a box to type a message in, or bubbles with one square corner beside chat words ("Your message"
    # in a contact form is no chat: a coffee shop's page was read as a thread)
    chat_words = bool(re.search(r"\b(chats?|conversations?|messages|online|typing|delivered|seen)\b", text))
    main = ("thread" if re.search(r"type (?:a |your )?message here|type a message|write a message|typing\.\.\.|is typing", text + " " + holders)
            or (re.search(r"rounded-b[rl]-none|rounded-t[rl]-none", classes) and chat_words)
            else "calendar" if re.search(r"\bsun\b.{0,12}\bmon\b.{0,12}\btue\b|\bmon\b.{0,12}\btue\b.{0,12}\bwed\b", text, re.S)
            else "editor" if body.find("textarea") and len(body.find_all("textarea")) <= 2 and body.find(attrs={"contenteditable": True}) or
            (body.find("textarea") and re.search(r"editor|notes?|markdown", text))
            else "board" if re.search(r"to ?do\b.*in progress.*(?:done|complete)|backlog", text, re.S) or "kanban" in classes
            else "table" if body.find("table")
            else "player" if re.search(r"now playing|bi-play|fa-play|play_arrow", text + classes)
            else "canvas" if body.find("canvas")
            else "grid" if re.search(r"\bgrid-cols-[2-6]\b", classes)
            else "list")
    composer = bool(any(f.find(["input", "textarea"]) and f.find("button") and len(f.find_all(["input", "textarea"])) == 1
                        and not re.search(r"search|city|location|email", str(f.find(["input", "textarea"]).get("placeholder") or ""), re.I)
                        and f.find(["input", "textarea"]).get("type") not in ("search", "email")
                        for f in body.find_all(["form", "div", "footer"]) if len(f.find_all(True)) <= 8))
    return {"side": _labels(side) if side else None, "side_title": " ".join(head.get_text(" ").split())[:24] if head else "",
            "bar": bool(body.find("header")) or bool(re.search(r"\b(sticky|fixed) top-0\b", classes)),
            "search": bool(body.find("input", attrs={"placeholder": re.compile("search", re.I)}) or body.find("input", attrs={"type": "search"})),
            "main": main, "pane": len(sides) >= 2, "composer": composer,
            "has": [name for name, rx in HAS if re.search(rx, low)], "parts": uiexamples._outline_of(html)[:8]}


PART_KIND_RX = re.compile(r"^(header|footer|section|[a-z][a-z-]{2,20})\b")


def _usual_parts(flows):
    """The blocks most of the pages have, in their usual order: "hero > features (cards) > pricing > footer"."""
    seen, place = collections.Counter(), collections.defaultdict(list)
    for f in flows:
        names = []
        for k, part in enumerate(f.get("parts") or []):
            m = PART_KIND_RX.match(str(part).lower())
            name = m.group(1) if m else ""
            if name and name not in names:
                names.append(name)
                place[name].append(k)
        seen.update(names)
    n = len(flows)
    keep = [x for x, c in seen.items() if c * 5 >= n and x != "section"]
    return sorted(keep, key=lambda x: sum(place[x]) / len(place[x]))[:8]


def merge(flows, pages):
    """Several pages' flows as one entry: how many of them have each region, their most usual main part, the side
    entries most of them name."""
    n = len(flows)
    if not n:
        return None
    labels = collections.Counter(l.title() if l.islower() else l for f in flows for l in (f["side"] or []))
    return {"pages": n, "from": pages[:3], "side_in": sum(bool(f["side"]) for f in flows),
            "side": [l for l, c in labels.most_common(8) if c >= 2] or [l for l, _ in labels.most_common(5)],
            "side_title": collections.Counter(f["side_title"] for f in flows if f["side_title"]).most_common(1)[0][0]
            if any(f["side_title"] for f in flows) else "",
            "bar_in": sum(f["bar"] for f in flows), "search_in": sum(f["search"] for f in flows),
            "main": collections.Counter(f["main"] for f in flows).most_common(1)[0][0],
            "pane_in": sum(f["pane"] for f in flows), "composer_in": sum(f["composer"] for f in flows),
            "mains": dict(collections.Counter(f["main"] for f in flows).most_common(4)),
            "has": [h for h, c in collections.Counter(h for f in flows for h in f.get("has") or []).most_common(8) if c * 4 >= n],
            "parts": _usual_parts(flows)}


MAIN_WORDS = {"thread": "the open conversation: message bubbles (the other person's left, the user's own right), newest at the bottom",
              "editor": "a writing area with a toolbar above it", "board": "columns of cards (to do / in progress / done)",
              "table": "a table of rows with actions", "player": "the player: cover, title, progress bar, play controls",
              "canvas": "a canvas / drawing area", "calendar": "a month grid of days with the events in them", "grid": "a grid of cards", "list": "a list of rows, one per entry"}


def words(kind, f):
    """The flow as the 4B reads it (and the user sees it in the chat)."""
    half = f["pages"] / 2
    bits = []
    if f["side_in"] >= half:
        bits.append("left: a side list" + (f" “{f['side_title']}”" if f["side_title"] else "")
                    + (f" ({', '.join(f['side'][:6])})" if f["side"] else ""))
    if f["bar_in"] >= half:
        bits.append("top: a bar with the title" + (", a search box" if f["search_in"] >= half else "") + " and action buttons")
    bits.append("centre: " + MAIN_WORDS[f["main"]])
    if f["composer_in"] >= half:
        bits.append("bottom: a box to type in with a send / add button")
    if f["pane_in"] >= half:
        bits.append("right: a pane with the details of what is open")
    if f.get("has"):
        bits.append("usually with: " + ", ".join(f["has"][:6]))
    return f"{kind} UI ({f['pages']} pages of this kind): " + "; ".join(bits)


DB = uiexamples.DIR / "flows.sqlite"
DOC = uiexamples.DIR / "FLOWS.md"
# a kind of UI named in a request: "<one or two words> <type>" ("task management dashboard", "recipe app", "twitter clone")
TYPES = ("app|application|dashboard|page|interface|ui|tool|platform|website|site|system|clone|player|editor|tracker|manager|viewer|"
         "board|feed|builder|calculator|form|widget|component|gallery|portal|panel|store|shop|blog|portfolio|game|planner|"
         "generator|converter|simulator|visualizer|client|marketplace|forum|wizard|screen|menu|table|chart|map|calendar|"
         "timeline|quiz|survey|checkout|cart|profile|settings|login|signup|onboarding|modal|navbar|sidebar|footer|hero|card|"
         "carousel|slider|section")
KIND_RX = re.compile(r"\b((?:[a-z][a-z0-9-]+ ){1,2})(" + TYPES + r")s?\b")
SKIP = set("a an the and or for with of to in on at by from this that these your our my its create build design make develop "
           "implement generate construct clone replicate craft produce responsive modern beautiful clean simple interactive "
           "dynamic advanced complex basic minimal elegant sleek fully full custom complete comprehensive detailed "
           "sophisticated highly featuring like similar inspired using use multi single new online web mobile".split())


def page_kinds(prompt):
    """The kinds of UI a dataset request names: "Build a kanban board with drag and drop" -> ["kanban board"]."""
    out = []
    for m in KIND_RX.finditer((prompt or "").lower()):
        words = [w for w in m.group(1).split() if w not in SKIP]
        if words:
            for key in (" ".join(words[-2:]) + " " + m.group(2), words[-1] + " " + m.group(2)):
                if key not in out:
                    out.append(key)
    return out[:6]


def build(progress=print):
    """The whole library (once, ~20 minutes): every dataset page's flow in flows.sqlite (id = its id in the index), then
    every kind of UI the requests name with its merged flow in flows.json, and FLOWS.md to read."""
    import pyarrow.parquet as pq
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE flow(id INTEGER PRIMARY KEY, prompt TEXT, kinds TEXT, r TEXT)")
    table = pq.read_table(uiexamples.DATA, columns=["prompt", "response"])
    n = bad = 0
    for batch in table.to_batches(1000):
        for prompt, response in zip(batch.column("prompt").to_pylist(), batch.column("response").to_pylist()):
            full = uiexamples._html(response)
            html = uiexamples._slim(full)
            if len(html) < 400:  # (the same pages, in the same order, as the index: uiexamples.build)
                continue
            n += 1
            try:
                r = regions(html, full)
            except (ValueError, RecursionError, AttributeError):
                bad += 1
                continue
            con.execute("INSERT INTO flow VALUES (?, ?, ?, ?)", (n, prompt or "", "|".join(page_kinds(prompt)), json.dumps(r, ensure_ascii=False)))
        con.commit()
        progress(f"{n} pages read ({bad} not readable)")
    con.execute("CREATE INDEX flow_kinds ON flow(kinds)")
    con.commit()
    con.close()
    tmp.replace(DB)
    return summarize(progress)


def _rows(where="", args=()):
    con = sqlite3.connect(DB)
    try:
        return con.execute("SELECT id, prompt, kinds, r FROM flow " + where, args).fetchall()
    finally:
        con.close()


def summarize(progress=print, least=12):
    """flows.json and FLOWS.md from flows.sqlite: the curated kinds (KINDS: all their pages) and every kind the
    requests name on `least` pages or more."""
    rows = _rows()
    by_kind = collections.defaultdict(list)
    for _id, prompt, kinds_, r in rows:
        for k in (kinds_ or "").split("|"):
            if k:
                by_kind[k].append((prompt, r))
    out = {"pages": len(rows), "curated": {}, "kinds": {}}
    for kind, (rx, _query) in KINDS.items():
        hit = [(p, json.loads(r)) for _i, p, _k, r in rows if re.search(r"\b(?:" + rx + r")\b", (p or "").lower())]
        f = merge([r for _p, r in hit], [p[:110] for p, _r in hit])
        if f:
            out["curated"][kind] = dict(f, words=words(kind, f))
    for kind, hit in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        if len(hit) < least:
            continue
        f = merge([json.loads(r) for _p, r in hit], [p[:110] for p, _r in hit])
        out["kinds"][kind] = dict(f, words=words(kind, f))
    FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# M42 flow library\n\nFrom {len(rows)} UIGEN-T2 pages (Apache-2.0). {len(out['curated'])} main kinds and "
             f"{len(out['kinds'])} kinds named in the requests ({least}+ pages each). Each line: where things are on pages of that kind.\n",
             "## Main kinds\n"]
    for kind, f in out["curated"].items():
        lines.append(f"- **{kind}** ({f['pages']} pages): {f['words'].split(': ', 1)[1]}"
                     + (f" | blocks: {' > '.join(f['parts'])}" if f["parts"] else ""))
    lines.append("\n## Every kind in the requests\n")
    for kind, f in out["kinds"].items():
        lines.append(f"- **{kind}** ({f['pages']}): {f['words'].split(': ', 1)[1]}")
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    global _lib
    _lib = None
    progress(f"{len(rows)} pages, {len(out['curated'])} main kinds, {len(out['kinds'])} kinds")
    return len(rows), len(out["curated"]), len(out["kinds"])


_lib = None


def library():
    global _lib
    if _lib is None:
        try:
            _lib = json.loads(FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _lib = {}
        if "curated" not in _lib:
            _lib = {"pages": 0, "curated": {}, "kinds": {}}
    return _lib


def kinds(request):
    """The main kinds the request names, in its order: "chat box and mail box website" -> ["chat", "mail"]."""
    low = (request or "").lower()
    found = []
    for kind, (rx, _) in KINDS.items():
        m = re.search(r"\b(?:" + rx + r")\b", low)
        if m:
            found.append((m.start(), kind))
    return [k for _, k in sorted(found)]


def nearest(request, limit=16):
    """The merged flow of the dataset pages closest to the request (the index's search, their flows from flows.sqlite)."""
    ids = [(i, p) for i, p, _h in uiexamples.search(request, limit=limit)]
    if not ids or not DB.exists():
        return None
    got = {i: r for i, _p, _k, r in _rows(f"WHERE id IN ({','.join('?' * len(ids))})", [i for i, _ in ids])}
    flows = [json.loads(got[i]) for i, _ in ids if i in got]
    return merge(flows, [p[:110] for i, p in ids if i in got])


def find(request):
    """Which flows a request gets, [(kind, flow)], at most 3:
    1. the kinds its own words name that the library has ("recipe app", "kanban board": the most exact first);
    2. the main kinds it names (chat, mail, dashboard...);
    3. else the flow of the dataset pages closest to it."""
    lib = library()
    low = " " + re.sub(r"[^a-z0-9]+", " ", (request or "").lower()) + " "
    out = []
    named = [k for k in lib["kinds"] if f" {k} " in low or f" {k}s " in low]
    for k in sorted(named, key=lambda k: (-len(k.split()), -lib["kinds"][k]["pages"]))[:2]:
        out.append((k, lib["kinds"][k]))
    for k in kinds(request):
        if k in lib["curated"] and not any(k in name for name, _ in out):
            out.append((k, lib["curated"][k]))
    if out:
        return out[:3]
    try:
        f = nearest(request) if uiexamples.ready() else None
    except (sqlite3.Error, OSError, ValueError, ImportError):
        f = None
    return [("", dict(f, words=words("This kind of", f)))] if f and f["pages"] >= 4 else []


ENHANCE_SCHEMA = {"type": "object", "properties": {
    "enhanced": {"type": "string", "maxLength": 600}, "query": {"type": "string", "maxLength": 100},
    "subject": {"type": "string", "maxLength": 40},
    "related": {"type": "array", "items": {"type": "string", "maxLength": 24}, "maxItems": 8},
    "purpose": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 3},
    "kind": {"type": "string", "maxLength": 30},
    # what the page is, decided by the model (the user, 2026-11-12: "wherever there is thinking, the 4B decides; no word
    # rules"): these answers replace the word lists that guessed them (APP_RX, LIVE_RX, DEVICE_RX, colour words...)
    "names_subject": {"type": "boolean"},
    "layout": {"type": "string", "enum": ["site to read", "app screen"]},
    "pages": {"type": "integer", "minimum": 1, "maximum": 8},
    "live": {"type": "string", "enum": ["none", "demo", "device"]},
    "named_colours": {"type": "array", "items": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}, "maxItems": 3},
    "named_theme": {"type": "string", "enum": ["", "light", "dark"]},
    "named_style": {"type": "string", "enum": ["", "glass", "minimal", "bold", "elegant", "playful"]},
    "long_read": {"type": "boolean"},
    "moving_background": {"type": "boolean"},
    "three_d": {"type": "boolean"},
    "picture_part": {"type": "string", "maxLength": 60}},
    "required": ["enhanced", "query", "subject", "related", "kind", "names_subject", "layout", "pages", "live", "named_colours",
                 "named_theme", "named_style", "long_read", "moving_background", "three_d", "picture_part"]}
ENHANCE_PROMPT = """The user asks for a web page in a few words (maybe Tanglish, maybe misspelt). Write it out in full, the way
a good designer would read it, as JSON:
- enhanced: 3-5 sentences in English: what the page is for and who visits it, the sections such a page has top to
  bottom (with what each shows for THIS subject), what it must let the visitor do, the feel. Only what this request
  needs: nothing a page of this subject would not have.
- query: one web search (English) for how real pages of exactly this are built.
- subject: WHAT the page is about, 1-3 words, singular, never the kind of page: "school", "coffee shop", "hr employee",
  "project management", "smart agriculture", "cold storage" (never "dashboard", "admin panel", "website", "app").
- related: 4-8 words of the SAME field as the subject, from the closest to the widest: other names of the same
  business or thing and its parts ("school": academy, college, students, teachers, education; "smart agriculture":
  farm, crop, irrigation, greenhouse, agriculture; "gym": fitness center, membership, workout). Never a neighbouring
  field with other things in it ("smart home" for a farm, "cloud storage" for a cold room, "travel" for a hotel admin).
- purpose: 0-3 words for what the page is for when that is no subject ("launch", "booking", "membership", "portfolio").
- kind: the kind of UI, 1-3 words ("landing page", "dashboard", "app", "admin panel", "website", "chat app").
Then decide, by the MEANING of the request (and the picture, when one is given):
- names_subject: true when the user's own words say what the page is about; false when they only point at a picture
  ("i need this", "ithe mathiri vennum", "same design with awesome UX"): then subject comes from the picture.
- layout: "site to read" (a landing page, a business / product / school site, a portfolio, a blog: visitors scroll it)
  or "app screen" (a dashboard, an admin panel, a tracker, a tool, an app's screen: people work in it). A SYSTEM or
  software to manage, track, record or run something (a "management system", an ERP, a CRM, a POS, an inventory /
  stock / billing / booking / attendance / payroll system, anything to "track" or "manage") is an app screen even
  when the words never say dashboard; a site to read only when they ask for a website or landing page visitors read.
- pages: how many separate pages the user asks for (1 unless they ask for several, "5 pages", "home and about page").
- live: "none" for every site to read (its prices, counts and facts are content) and for most app screens;
  "demo" only for a monitor / live dashboard whose numbers keep changing with no source named; "device" only when the
  words name where readings come from (a device, a sensor, ESP32, an API, a database).
The next four report ONLY what the USER'S WORDS ask; not what you would choose (that is decided later):
- named_colours: one hex per colour the user names, in that colour's own hue (red #dc2626, blue / neela #2563eb,
  green / pachai #16a34a, yellow / manjal #eab308, orange #f97316, purple #7c3aed, pink #ec4899, gold #d4a017,
  black #111827); [] when the words name no colour.
- named_theme: "light" or "dark" only when the words say it ("dark theme", "white background"); else "".
- named_style: a style only when the words say it ("glass", "minimal", "luxury" = elegant, "kids" = playful); else "".
- moving_background: true only when the words ask for an animated / moving / particle / interactive background.
- three_d: true only when the words ask for 3D (a 3D site / page / hero, 3D models or animation, three.js, "3டி",
  "முப்பரிமாண"); false when they do not say it (the page is then made without 3D).
- long_read: true only for a page read top to bottom (an article, a blog post, documentation, a long guide).
- picture_part: when the words point at ONE part of the picture to build ("intha chart mattum", "antha orders card
  maadhiri", "the calendar in this", "right side queue"): that part in a few words as it is in the picture ("the
  print queue card"); "" when the whole picture is meant or there is no picture."""


def enhance_messages(request, image=None):
    """The request (and the user's reference picture, when there is one: what it shows tells what an "i need this"
    is about and whether it is a site or an app screen) for the model to read in full."""
    user = request[:600] if not image else [{"type": "text", "text": request[:600] + "\n(The user's reference picture:)"},
                                             {"type": "image_url", "image_url": {"url": image}}]
    return [{"role": "system", "content": ENHANCE_PROMPT}, {"role": "user", "content": user}]


INTENT_KEYS = ("names_subject", "layout", "pages", "live", "named_colours", "named_theme", "named_style", "long_read",
               "moving_background", "three_d", "picture_part")


def intent_of(enh):
    """The model's decisions about the page from its reading of the request ({} when it gave none)."""
    if not isinstance(enh, dict) or "layout" not in enh:
        return {}
    out = {k: enh[k] for k in INTENT_KEYS if k in enh}
    out["named_colours"] = [c for c in out.get("named_colours") or [] if re.fullmatch(r"#[0-9a-fA-F]{6}", str(c))][:3]
    out["pages"] = max(1, min(8, int(out.get("pages") or 1))) if str(out.get("pages") or "1").isdigit() else 1
    out["subject"] = str(enh.get("subject") or "")
    return out


def _fts_words(text):
    """FTS terms of a phrase: its words; two or more as a phrase in quotes."""
    words = re.findall(r"[a-z0-9]+", str(text or "").lower())
    words = [w for w in words if w not in ("page", "website", "site", "ui", "the", "a", "an", "for", "of")]
    if not words:
        return ""
    return '"' + " ".join(words) + '"' if len(words) > 1 else words[0]


# words that name the same kind of UI ("admin panel" pages are also called dashboards, back offices): a kind is searched
# as any of its group's words. ("management" is no kind: "itinerary management" found travel sites for a hotel admin.)
KIND_GROUPS = [("admin", "dashboard", "panel", "backoffice", "back-office", "console", "cms"),
               ("landing", "homepage", "website", "site"), ("app", "application", "mobile"),
               ("store", "shop", "ecommerce", "e-commerce", "marketplace", "storefront"), ("blog", "magazine", "news"),
               ("booking", "reservation", "scheduler", "scheduling"), ("chat", "messaging", "messenger"),
               ("portfolio", "personal", "showcase", "gallery")]
FILLER = {"page", "the", "a", "an", "for", "of", "and", "to", "with", "ui", "web", "online", "new", "my", "our"}
COMMON = 400  # a word in more requests than this ("design" 12,058, "dashboard" 5,082, "smart" 505) is never searched alone
_df = {}


def df(word):
    """How many dataset requests hold the word (or the prefix "word*"), counted once."""
    if word not in _df:
        con = sqlite3.connect(uiexamples.DB)
        try:
            _df[word] = con.execute("SELECT count(*) FROM words WHERE words MATCH ?", (f"prompt:{word}",)).fetchone()[0]
        except sqlite3.Error:
            _df[word] = 0
        finally:
            con.close()
    return _df[word]


def kind_words(kind):
    words = {w for w in re.findall(r"[a-z0-9-]+", str(kind or "").lower()) if w not in FILLER and len(w) > 2}
    for g in KIND_GROUPS:
        if words & set(g):
            words |= set(g)
    return words


def _kind_terms(kind):
    return ['"' + t + '"' if "-" in t else t for t in sorted(kind_words(kind))]


def _words(text, drop=()):
    return [w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if w not in FILLER and w not in drop and len(w) > 1]


def _prefix(w):
    """A word with its other forms: "course" -> course*, "photographer" -> photograph* (photography). A short word only
    with its plural: "crop*" found photo editors' cropping, "farm*" a DeFi page's yield farming."""
    if len(w) <= 5:
        return f"({w} OR {w}s)" if not w.endswith("s") else w
    stem = re.sub(r"(ers?|ing|ists?|es|s)$", "", w)  # (not "y": "beauty" -> beaut* found "beautiful")
    return (stem if len(stem) >= 5 else w) + "*"


def _whole(text, drop=(), allow_common=False):
    """The FTS term for all of a phrase's words together: "real estate" -> ("real estate" OR (real* AND estat*))."""
    words = _words(text, drop)
    if not words:
        return ""
    if len(words) == 1:
        # one word that is common in the dataset is no term of a field ("develop*" is in "Develop a responsive..." of
        # every other request; "product", "service", "sales" found e-commerce panels for a salon and a car dealership).
        # The subject alone keeps its word: allow_common
        if df(_prefix(words[0])) > COMMON and not allow_common:
            return ""
        return _prefix(words[0])
    return f'("{" ".join(words)}" OR ({" AND ".join(_prefix(w) for w in words)}))'


_heads = {}


def is_head(word):
    """A word that names a kind of business or thing whatever it is about ("company": travel company, SaaS company,
    tech company...), told from the dataset itself: the requests that hold it have many different words just before
    it. Such a word alone finds any company's page, so it is never a part of the subject searched alone."""
    if word in _heads:
        return _heads[word]
    con = sqlite3.connect(uiexamples.DB)
    try:
        ids = [r[0] for r in con.execute("SELECT rowid FROM words WHERE words MATCH ? LIMIT 400", (f"prompt:{word}",))]
        prompts = [r[0] for r in con.execute(f"SELECT prompt FROM page WHERE id IN ({','.join('?' * len(ids))})", ids)] if ids else []
    except sqlite3.Error:
        prompts = []
    finally:
        con.close()
    before = set()
    for p in prompts:
        ws = re.findall(r"[a-z0-9]+", (p or "").lower())
        before |= {ws[k - 1] for k in range(1, len(ws)) if ws[k] == word and ws[k - 1] not in FILLER}
    # many different words before it, for how often it is used: a head word ("company" 31 requests, ~20 different
    # words before it); a subject word has a few ("coding course", "online course")
    # (measured: company 11 different in 25 requests; course 29 in 204, store 18 in 93, agency 3 in 46)
    _heads[word] = len(prompts) >= 10 and len(before) >= .4 * len(prompts)
    return _heads[word]


def _rare_parts(text, drop=()):
    """The words of a phrase that are rare enough in the dataset to stand alone ("agriculture" of "smart agriculture";
    never "smart", "design", "dashboard")."""
    words = _words(text, drop)
    return [_prefix(w) for w in words if len(words) > 1 and len(w) > 2 and 0 < df(_prefix(w)) <= COMMON and not is_head(w)]


def purpose_words(request, subject="", kind="", related=()):
    """The request's own words that are no subject, kind or filler and rare in the dataset ("launch" of "electric scooter
    launch landing page"): its purpose when the model gave none."""
    taken = set(_words(subject)) | kind_words(kind) | set(_words(kind)) | {w for r in related or [] for w in _words(r)}
    out = []
    for w in _words(request):
        if w not in taken and len(w) > 3 and 0 < df(_prefix(w)) <= COMMON:
            out.append(w)
    return out[:3]


def match(subject, related=(), kind="", limit=40, purpose=(), want=12, request=""):
    """The dataset pages for the request, the closest first, collected tier by tier until there are `want` of them
    (a tier with 2 good pages keeps them: "course + landing" had the 2 best for a coding course, then thrown away):
    1. the whole subject and the kind;  2. a rare part of the subject and the kind ("course" + landing);  3. a related
    word (whole) and the kind;  4. the purpose and the kind ("launch" + landing);  5. the whole subject alone;
    6. a related word alone. Words of the kind are never the subject ("hr dashboard" -> "hr").
    Returns {"tier", "label", "ids", "prompts", "flow"} or None."""
    if not DB.exists() or not uiexamples.ready():
        return None
    # the kind as the request names it: the model wrote "launch page" for "... launch landing page" (no kind group in
    # it): a kind group named in the request is the kind, and the kind's other words ("launch") are its purpose
    grouped = set().union(*KIND_GROUPS)
    own = {w for w in _words(kind) if len(w) > 2}
    if not own & grouped:
        named = [w for w in _words(request) if w in grouped]
        if named:
            purpose = list(purpose or []) + sorted(own)
            kind = " ".join(named)
    kw = kind_words(kind)
    # the subject as the request says it: the model shortened "car dealership" to "dealership", "food delivery orders"
    # to "delivery", "pet grooming salon" to "grooming" (and found Jira's "backlog grooming"). When its subject's words
    # are all in the request, the request's own words around them (no kind, purpose or filler word) are the subject,
    # and the model's short one a related word
    asked = [w for w in _words(request, kw | {w for x in purpose or [] for w in _words(x)}) if w not in ("panel", "page")]
    mine = _words(subject, kw)
    if mine and set(mine) <= set(asked) and len(asked) > len(mine) and len(asked) <= 4:
        related = [subject] + [r for r in related or [] if r != subject]
        subject = " ".join(asked)
    subj = _whole(subject, kw, allow_common=True)
    rel = [t for t in dict.fromkeys(_whole(r, kw) for r in related or []) if t and t != subj][:8]
    parts = [t for t in _rare_parts(subject, kw) if t not in rel]
    # the purpose the model gave (or a kind's own words, above) is searched; the request's other rare words only rank
    # the pages found ("company" of "solar panel installation company" found travel companies' pages)
    purpose = list(purpose or [])
    purp = [t for t in dict.fromkeys(_whole(x, kw) for x in purpose) if t]
    kd = _kind_terms(kind)
    any_of = lambda ts: "(" + " OR ".join(ts) + ")"  # noqa: E731
    tiers = []
    if subj and kd:
        tiers.append(("exact", f"{subject} {kind}", f"prompt:{subj} AND prompt:{any_of(kd)}"))
    if parts and kd:  # the subject's own rare word first ("course" + landing), then its field
        tiers.append(("part", f"{subject} {kind}", f"prompt:{any_of(parts)} AND prompt:{any_of(kd)}"))
    if rel and kd:
        tiers.append(("related", f"{' / '.join(related[:4])} {kind}", f"prompt:{any_of(rel)} AND prompt:{any_of(kd)}"))
    if purp and kd:
        tiers.append(("purpose", f"{' / '.join(purpose)} {kind}", f"prompt:{any_of(purp)} AND prompt:{any_of(kd)}"))
    each = [t for t in dict.fromkeys(_whole(w, kw, allow_common=True) for w in _words(subject, kw)) if t]
    if len(each) > 1 and kd:  # one word of the subject with the kind ("saas" + landing for "saas crm": no page holds both)
        tiers.append(("part", f"{subject} {kind}", f"prompt:{any_of(each)} AND prompt:{any_of(kd)}"))
    if subj:
        tiers.append(("subject", subject, f"prompt:{subj}"))
    if rel:
        tiers.append(("field", " / ".join(related[:4]), f"prompt:{any_of(rel)}"))
    # every tier's pages, then ranked by how much of the request each one's own words hold: a closer tier first, then
    # the subject's and the field's words in it ("machine learning" dashboards hold none of sensor / factory / IoT and
    # go down; an industrial IoT dashboard holds three and comes up), then the kind's
    sw = set(_words(subject, kw))
    rw = {w for r in related or [] for w in _words(r, kw) if df(_prefix(w)) <= COMMON} - sw  # (not "product", "sales")
    # a kind's own topic word ("IoT" of "IoT admin panel": no kind group's) is the request's topic too
    rw |= {w for w in _words(kind) if len(w) > 1 and not any(w in g for g in KIND_GROUPS)} - sw
    pw = {w for x in purpose for w in _words(x, kw)}
    extra = set(purpose_words(request, subject, kind, related)) - pw
    # (the request's own other words count too, a little: "industrial", "monitoring")
    weight = {"exact": 3, "part": 2.5, "related": 2, "purpose": 1.5, "subject": 1, "field": 0.5}
    con = sqlite3.connect(uiexamples.DB)
    try:
        found = {}
        for tier, label, q in tiers:
            try:
                rows = con.execute("SELECT rowid FROM words WHERE words MATCH ? ORDER BY bm25(words, 4.0, 1.0) LIMIT ?",
                                   (q, limit)).fetchall()
            except sqlite3.Error:
                continue
            for r in rows:
                found.setdefault(r[0], (tier, label))
        if not found:
            return None
        prompts = {i: p for i, p in con.execute(f"SELECT id, prompt FROM page WHERE id IN ({','.join('?' * len(found))})", list(found))}
    finally:
        con.close()

    def score(i):
        low = " ".join(_words(prompts.get(i, "")))
        has = lambda ws: sum(1 for w in ws if re.search(r"\b" + re.escape(w[:max(4, len(w) - 2)]), low))  # noqa: E731
        return (has(sw) * 3 + has(rw) * 2 + has(pw) * 2 + has(extra) + bool(has(kw)) * 2 + weight[found[i][0]], -list(found).index(i))
    # pages of the kind asked for first, then the closest (a SaaS CRM's landing page: CRM dashboards held both "saas"
    # and "crm" and came above every SaaS landing page, 2026-11-11)
    fits = {i: (not kind or kind_fits(prompts.get(i, ""), kind)) * (1 + ("landing" in kw and bool(
        re.search(r"\b(landing|homepage)\b", prompts.get(i, ""), re.I)))) for i in found}
    ids = sorted(found, key=lambda i: (fits[i], score(i)), reverse=True)[:limit]
    tier, label = found[ids[0]]
    flows = {i: json.loads(r) for i, _p, _k, r in _rows(f"WHERE id IN ({','.join('?' * len(ids))})", ids)}
    keep = [i for i in ids if i in flows]
    f = merge([flows[i] for i in keep], [prompts.get(i, "")[:110] for i in keep])
    if not f:
        return None
    return {"tier": tier, "label": label, "ids": keep, "prompts": [prompts.get(i, "") for i in keep], "flow": dict(f, words=words(label, f)),
            "topic": sorted(sw | rw | pw), "subject_words": sorted(sw)}


PICK_SCHEMA = {"type": "object", "properties": {"fits": {"type": "array", "items": {"type": "integer"}, "maxItems": 12}},
               "required": ["fits"]}
PICK_PROMPT = """The user wants a web page. Below are numbered requests of pages from a UI library, found by words. Answer
JSON {"fits": [numbers]}: every page that is a good model for the user's page, the best first, up to 8. A page fits
only when BOTH hold:
1. the same kind of UI (a landing page for a landing page; an admin panel / dashboard for an admin panel; an app for an
   app);
2. the same subject, or the same field: its request names the user's subject, another name of it or one of its parts
   (a school and a college or a university: yes; a farm and a crop or irrigation dashboard: yes).
Something next to the subject with other things in it does NOT fit: a smart home panel for a farm, a cloud file storage
for a cold room, a fitness tracker app for a gym's admin, a travel site for a hotel's admin, a general admin template
for an HR panel, a cloud server console for a water tank. Judge by the user's own subject: the words the pages were found
by may be wrong. When none fits: {"fits": []}."""


def pick_messages(request, enhanced, prompts):
    listed = "\n".join(f"{n}. {p[:140]}" for n, p in enumerate(prompts[:12], 1))
    return [{"role": "system", "content": PICK_PROMPT},
            {"role": "user", "content": f"The user's page: {request[:300]}\n{str(enhanced or '')[:500]}\n\nLibrary pages:\n{listed}"}]


# words that say a page is another kind of UI than the one asked for (a fitness app's screen picked for a gym's
# landing page): by the kind groups, nothing fixed per subject
OTHER_KIND = {"landing": ("app", "application", "dashboard", "admin", "panel", "editor", "tracker", "tool", "interface",
                          # (a tool's own words: "a booking management UI for hotels" is no hotel landing page)
                          "management", "system", "portal", "calendar", "wizard", "filtering", "checkout"),
              "admin": ("landing", "homepage", "website")}


def kind_fits(prompt, kind):
    """The page's request names the kind asked for, or at least no other kind ("Design a fitness app interface..." is
    no landing page)."""
    low = " " + " ".join(_words(prompt)) + " "
    kw = kind_words(kind)
    named = [w for w in kw if f" {w} " in low or f" {w}s " in low]
    # "a travel booking site with date pickers, filters and a booking wizard" is a booking tool, not a landing page
    # ("site" was the only landing word; a hotel's landing page was modelled on it, 2026-11-11)
    if "landing" in kw and named and set(named) <= {"site", "website"} and re.search(
            r" (booking|reservation|scheduler|filter\w*|wizard|checkout|system|interface|management) ", low):
        return False
    if named:
        return True
    if "landing" in kw:  # a landing page's model says so (847 do): "a bookings UI for hotels" or "a virtual classroom
        return False     # platform" is a tool, whatever its subject; with none, the enhanced request leads the page
    for key, others in OTHER_KIND.items():
        if key in kw and any(f" {o} " in low for o in others):
            return False
    return True


def narrow(m, fits, kind=""):
    """The match with only the pages the model picked (numbers from 1, of its first 12) that are of the kind asked for,
    at most 8; None when none is left."""
    idx = [n - 1 for n in dict.fromkeys(int(x) for x in fits or [] if isinstance(x, (int, float))) if 1 <= n <= min(12, len(m["ids"]))]
    idx = [k for k in idx if not kind or kind_fits(m["prompts"][k], kind)]
    # pages that name the subject itself, of the kind asked for, are the closest models: when the model kept none of
    # them (it kept e-commerce admin panels for a restaurant's, with four restaurant dashboards listed above them),
    # they are the ones
    sub = [w[:max(4, len(w) - 2)] for w in m.get("subject_words") or []]
    if sub:
        kw_ = kind_words(kind)
        named = [k for k in range(min(12, len(m["ids"])))
                 if all(re.search(r"\b" + re.escape(t), " ".join(_words(m["prompts"][k]))) for t in sub)
                 and (not kw_ or set(_words(m["prompts"][k])) & kw_)  # the kind named in it too, not only "fits"
                 and (not kind or kind_fits(m["prompts"][k], kind))]
        if named and not set(named) & set(idx):
            idx = named[:4] + idx  # (the model's own picks stay after them: an Airbnb host panel for a hotel's)
    # a page that names nothing of the request's subject or field (a general "admin panel with multi-level navigation"
    # picked for a water tank) is no model of it, whatever the model said
    topic = [w[:max(4, len(w) - 2)] for w in m.get("topic") or []]
    if topic:
        idx = [k for k in idx if any(re.search(r"\b" + re.escape(t), " ".join(_words(m["prompts"][k]))) for t in topic)]
    idx = idx[:8]
    if not idx:
        return None
    ids = [m["ids"][k] for k in idx]
    flows = {i: json.loads(r) for i, _p, _k, r in _rows(f"WHERE id IN ({','.join('?' * len(ids))})", ids)}
    keep = [k for k in idx if m["ids"][k] in flows]
    if not keep:
        return None
    f = primary_flow(m["label"], flows[m["ids"][keep[0]]], m["prompts"][keep[0]], [flows[m["ids"][k]] for k in keep[1:]])
    if f:  # the blocks of the subject's pages (its first 20 matches): what many of them have, the best page may lack
        pool = [i for i in m["ids"][:20]]
        f = dict(f, pool=[(json.loads(r).get("parts") or [])[:12] for _i, _p, _k, r in
                          _rows(f"WHERE id IN ({','.join('?' * len(pool))})", pool)])
    return dict(m, ids=[m["ids"][k] for k in keep], prompts=[m["prompts"][k] for k in keep], flow=f)


def primary_flow(label, best, prompt, others=()):
    """The flow of the ONE page that fits best (the first kept: the model's first pick, or a page naming the subject and
    the kind), its own regions, side entries and parts; the other kept pages only add what they have that it lacks.
    (The user, 2026-11-11: a flow averaged over many pages came out the same sidebar + table + chart for every admin
    panel; a calendar view or a board in one of them was lost in the average.)"""
    f = merge([best], [prompt[:110]])
    if not f:
        return None
    text = words(label, f).replace(f"({f['pages']} pages of this kind)", f"(modelled on: {prompt[:90]})")
    more = collections.Counter(h for o in others for h in o.get("has") or [] if h not in (best.get("has") or []))
    mains = [x for x in dict.fromkeys(o.get("main") for o in others) if x and x != best.get("main")]
    extra = [h for h, c in more.most_common(4) if c >= 1][:3]
    if extra or mains:
        text += "; other pages of this kind also have: " + ", ".join(extra + [MAIN_WORDS[x].split(":")[0] for x in mains[:2]])
    return dict(f, words=text, model_page=prompt[:140], pages=1 + len(others))


def app_pages(request):
    """The pages M42 builds from its own app views for the request: [{"name", "kind", "part", "flow"}]."""
    cur = library()["curated"]
    return [{"name": APP[k][0], "kind": k, "part": APP[k][1], "flow": cur.get(k) or {}} for k in kinds(request) if k in APP]


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["build"]:
        print(build())
    elif sys.argv[1:] == ["summarize"]:
        print(summarize())
    else:
        for k, f in find(" ".join(sys.argv[1:])):
            print(k or "(closest pages)", "|", f["words"], "| has:", f.get("has"), "| blocks:", f.get("parts"))
