"""Design references for a web page (the user, 2026-10-27: "whatever web design I ask for, look at how real designs
of that kind are made and build from that: dynamic, not static"). For every page / site request:
  - the reference: screenshots the user attached (from Dribbble or anywhere, taken by the user), else the home pages
    of real public sites of that kind (or public live demos), found by a web search and captured with headless
    Chrome. Design galleries (Dribbble, Behance, Pinterest...) are never fetched by M42: their terms forbid
    automated access, so the user brings those shots;
  - its pixels (profile): light / dark, its colours, how busy it is;
  - its design, read by the vision model (BRIEF_SCHEMA): layout, hero, its sections top to bottom, cards, corners,
    style, fonts. Structure and feel only: no text, picture or logo of the reference goes into the page;
  - after the build, the page's own screenshot is compared with the reference (check), and the look corrected once.
The templates (pagebuild.py) are only the parts; what goes where, and how it looks, comes from the reference."""
import base64
import colorsys
import io
import hashlib
import json
import os
import re
import urllib.parse
from pathlib import Path

import pagebuild
import webkit

GALLERY_RX = re.compile(r"(^|\.)(dribbble|behance|pinterest|awwwards|muz|uplabs|figma|canva|envato|themeforest|"
                        r"freepik|shutterstock|unsplash)\.", re.I)
NOT_SITE_RX = re.compile(r"(^|\.)(wikipedia|wikihow|youtube|facebook|instagram|twitter|x|linkedin|reddit|quora|medium|"
                         r"github|stackoverflow|stackexchange|amazon|flipkart|justdial|yelp|tripadvisor|indiamart|"
                         r"glassdoor|naukri|play\.google|apps\.apple|google|bing|duckduckgo)\.", re.I)
ARTICLE_RX = re.compile(r"/(blog|blogs|news|article|articles|wiki|top-|best-|list|guide|how-to|tag|category|"
                        r"\d{4}/\d{2})", re.I)
DEMO_RX = re.compile(r"demo|preview|live", re.I)

QUERY_SCHEMA = {"type": "object", "properties": {
    "kind": {"type": "string", "maxLength": 40}, "app": {"type": "boolean"}}, "required": ["kind", "app"]}
QUERY_PROMPT = """What kind of website does the user want? kind: 2-4 English words naming the business or product
(e.g. "<food> restaurant", "<product> shop admin dashboard", "<trade> portfolio": the user's own). app: true when
it is a screen used after signing in (an admin panel, a dashboard, a management system), false for a public site."""

LAYOUTS = ("top-nav", "sidebar", "split-screen", "single-column")
HEROES = ("search", "split", "centered", "image", "compact", "none")
# colour families by hue (degrees): the vision model names the reference's main colour, the pixels give its shade
HUES = {"red": (345, 15), "orange": (15, 40), "yellow": (40, 65), "green": (65, 160), "teal": (160, 195), "blue": (195, 235),
        "indigo": (235, 262), "purple": (262, 300), "pink": (300, 345)}
NEAR = {"purple": ("purple", "indigo", "pink"), "indigo": ("indigo", "purple", "blue"), "blue": ("blue", "indigo", "teal"),
        "teal": ("teal", "green", "blue"), "green": ("green", "teal"), "yellow": ("yellow", "orange"), "orange": ("orange", "red", "yellow"),
        "red": ("red", "pink", "orange"), "pink": ("pink", "red", "purple")}
# what a reference's top strip can hold, read left to right (the page's bar is built from it in that order)
HEADER_BITS = ("title", "search", "notifications", "messages", "mail", "favorites", "cart", "settings", "help", "calendar",
               "apps", "user", "language", "theme", "date", "location", "button")
BRIEF_SCHEMA = {"type": "object", "properties": {
    "match": {"type": "string", "enum": ["yes", "no"]},
    "covered": {"type": "string", "enum": ["yes", "no"]},
    "layout": {"type": "string", "enum": list(LAYOUTS)},
    "hero": {"type": "string", "enum": list(HEROES)},
    "sections": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 60}},
    "cards": {"type": "string", "enum": ["glass", "shadow", "outlined", "flat"]},
    "corners": {"type": "string", "enum": ["sharp", "rounded", "pill"]},
    "style": {"type": "string", "enum": ["glass", "minimal", "bold", "elegant", "playful"]},
    "font": {"type": "string", "enum": ["modern", "elegant", "tech", "friendly"]},
    "mood": {"type": "string", "maxLength": 60},
    "theme": {"type": "string", "enum": ["light", "dark"]},
    "menu": {"type": "string", "enum": ["text sidebar", "icon rail", "top bar", "none"]},
    "accent": {"type": "string", "enum": list(HUES) + ["brown", "black", "grey"]},
    "header": {"type": "array", "maxItems": 10, "items": {"type": "string", "enum": list(HEADER_BITS)}},
    "topic": {"type": "string", "maxLength": 60},
    "screen": {"type": "string", "maxLength": 30}},
    "required": ["match", "covered", "layout", "hero", "sections", "cards", "corners", "style", "font", "mood", "theme", "menu", "header", "accent", "topic", "screen"]}
BRIEF_PROMPT = """You look at a screenshot of a web page and write down its DESIGN (not its words) as JSON, so that
a different page can be built with the same structure and feel and its own content.
- match: "yes" when the screenshot is the page of a real site or app of the kind the user wants; "no" when it is
  something else (a shop selling templates or themes, a website builder, an article, an error page), or when a
  popup, an offer, a cookie banner or an overlay covers the page so its design can't be seen.
- covered: "yes" when a popup box, an offer / ad picture or a dark overlay sits over the middle of the page.
- layout: top-nav (a menu bar across the top), sidebar (a menu down the left, like an app), split-screen (two
  halves, e.g. a sign-in page), single-column.
- hero: the first block under the menu: image (the heading written ON a big photo that fills the width), split
  (the heading on one side and a picture on the OTHER side), centered (a big centred heading on a plain or gradient
  background, no photo), search (a big search card), compact (a small title row, as in apps), none.
- sections: the blocks you SEE in this screenshot under the hero, top to bottom, each in your own few words about
  its shape and what it holds (how many cards, a table, a form, tabs, a photo grid...). Only what is really there.
- cards: glass (see-through, blurred), shadow (white with soft shadows), outlined (thin borders, no shadow), flat.
- corners: sharp, rounded, pill (very round buttons and cards).
- style: glass (translucent, gradients), minimal (flat, much white space, few colours), bold (big type, strong
  colour blocks), elegant (serif headings, quiet, thin lines), playful (round, bright, fun).
- font: modern (clean sans-serif), elegant (serif), tech (narrow, geometric), friendly (rounded, soft).
- mood: 2-5 words.
- theme: is the page itself (not the room or board around it) light or dark?
- menu: the page's main menu: "text sidebar" (icons with words down the left), "icon rail" (a narrow column of
  icons only, no words), "top bar" (links across the top), "none".
- header: EVERY thing in the strip across the very top of the page (above the cards), LEFT TO RIGHT: "title" (a
  page name like "Dashboard"), "search" (a search box), "notifications" (a bell), "messages" (a chat bubble),
  "mail" (an envelope), "favorites" (a heart), "cart", "settings" (a gear), "help" (?), "calendar", "apps" (a
  grid), "user" (a person's photo or name), "language" (EN), "theme" (a light / dark switch), "date" (today's
  date), "location" (a pin with a place), "button" (a button like "Download app"); [] when there is no strip.
- accent: the page's own main colour, the one of its buttons, its active menu item, its chart lines and its
  number tiles (not the background around the page, not a photo): purple, blue, green...
- topic: what the page in the picture is about, 2-6 words (the product, business or things it shows: "smart home
  device control", "online clothes shop"), as exact as the picture's own names show (its brand, its machines, its
  products), not its design.
- screen: which screen of its site or app this is, 1-3 words, as its own heading or highlighted menu entry says
  ("Dashboard", "Orders", "Order detail", "Home", "Product page"); an ID or a person's name in the heading is the
  KIND of screen ("ORD-1042" is "Order detail")."""


# ---- finding real sites ------------------------------------------------------------------------------------

def query_messages(request, spec):
    title = (spec or {}).get("title") or ""
    return [{"role": "system", "content": QUERY_PROMPT},
            {"role": "user", "content": f"User request: {request[:500]}\nThe page: {title}"}]


# ---- 📚 the user's own reference library (priority 1), then open-source template demos on GitHub (priority 2) -------
# <app folder>/design-refs/<kind>/*.png|jpg|webp: shots a user saved (M42 UI does not use them: GitHub templates instead).
# The folder whose name fits the request is used; its pictures take turns, one per request.
LIBRARY = Path(__file__).resolve().parent.parent / "design-refs"
LIBRARY_KINDS = ("admin-dashboard", "analytics-dashboard", "iot-dashboard", "ecommerce", "pos", "restaurant",
                 "hotel-booking", "school", "hospital", "portfolio", "landing-page", "blog", "mobile-app", "login")
PICTURE_EXT = (".png", ".jpg", ".jpeg", ".webp")
GENERIC_RX = re.compile(r"admin|dashboard|panel|page|site|website|web|app|mobile|management|system|portal|landing")
README = """M42 design reference library
============================
Put the design shots you like in the folder of their kind (PNG / JPG / WEBP, full size: small thumbnails lose
the icons and rows M42 reads). Make any new folder you want: its name is matched with what you ask for
("school-admin", "car-rental", "crypto-dashboard"...). Words in a folder name are split by - or _.

When you ask for a page WITHOUT attaching a picture, M42 looks here first: the best-fitting folder, one picture
from it (they take turns). Only when no folder fits, or the folder is empty, M42 looks on GitHub for open-source
template demos of that kind.
"""


def make_library():
    """The library's folders and README (only what is missing; nothing in it is changed)."""
    for k in LIBRARY_KINDS:
        (LIBRARY / k).mkdir(parents=True, exist_ok=True)
    readme = LIBRARY / "README.txt"
    if not readme.exists():
        readme.write_text(README, encoding="utf-8")


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 1}


def _fits(token, words):
    """'dashboard' fits 'dashboards'; 'ecommerce' fits 'e-commerce' through the joined words."""
    return any(token == w or (len(token) >= 4 and len(w) >= 4 and (w.startswith(token) or token.startswith(w)))
               for w in words)


def catalog_words():
    """{folder: the words of its pictures' notes} from the library's catalog.json (each picture: its kind and what
    is in it), {} without one."""
    try:
        cat = json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for path, entry in cat.items():
        folder = path.split("/")[0]
        if folder != "components" and isinstance(entry, dict):
            out.setdefault(folder, set()).update(_words(entry.get("notes")))
    return out


def catalog_notes(folder):
    """{file name: what the picture shows} for one library folder, from catalog.json (a video's still: its video's
    note)."""
    try:
        cat = json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for path, entry in cat.items():
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == folder and isinstance(entry, dict):
            out[parts[1]] = entry.get("notes") or ""
            if entry.get("frame"):
                out[entry["frame"].split("/")[-1]] = entry.get("notes") or ""
    return out


CHOOSE_SCHEMA = {"type": "object", "properties": {"best": {"type": "array", "items": {"type": "integer"}, "maxItems": 3}},
                 "required": ["best"]}


def choose_messages(request, options):
    """The chat model picks the design references that suit the request, from their notes (text only, cheap)."""
    lines = "\n".join(f"{n}. {note or f.name}" for n, (f, note) in enumerate(options))
    return [{"role": "system", "content": "You pick design reference pictures for a web page. Each option is a note on "
                                          "what one picture shows. Choose the ones whose subject and mood suit the "
                                          "user's page best (a coffee shop: food, drinks, a cafe, warm products; not "
                                          "a software platform), best first. Only pictures of the same kind of business or "
                                          "product: when none is (a coffee shop and only corporate, construction or "
                                          "software pages), answer {\"best\": []}. Answer {\"best\": [numbers]}."},
            {"role": "user", "content": f"The page: {request[:300]}\n\nOptions:\n{lines}"}]


def catalog_entry(path):
    """The catalog.json entry of one library picture (a video's still: its video's entry), {} without one: its notes
    and, for a long landing page, its sections from top to bottom."""
    try:
        cat = json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    key = f"{Path(path).parent.name}/{Path(path).name}"
    return next((e for k, e in cat.items() if isinstance(e, dict) and (k == key or e.get("frame") == key)), {})


def page_folders():
    """{folder: a few of its pictures' notes} for every whole-page folder of the library that has pictures."""
    out = {}
    for d in sorted(p for p in LIBRARY.iterdir() if p.is_dir() and p.name != "components" and not p.name.startswith("_")):
        here = {f.name for f in d.iterdir() if f.is_file() and f.suffix.lower() in PICTURE_EXT}
        if here:  # the notes of the pictures still there (the user takes pictures out of a folder)
            notes = [n.split(";")[0][:40] for f, n in catalog_notes(d.name).items() if n and f in here]
            out[d.name] = ", ".join(list(dict.fromkeys(notes))[:3])[:110]  # short: ~20 folders read on the CPU
    return out


def folder_messages(request, folders):
    """The chat model picks the library folder for the request from the folders' names (text only, ~3 s on the CPU:
    "cafe website" -> restaurant, "gym app" -> health-fitness, where no word of the request is in a folder name).
    The names only: with their notes the prompt was 560 tokens, 20 s, and the picks were the same."""
    lines = "\n".join(f"{n}. {name}" for n, (name, _) in enumerate(folders))
    return [{"role": "system", "content": "You pick the design reference folder for a web page: the kind of page and its "
                                          "subject. Best first. Answer {\"best\": [numbers]}."},
            {"role": "user", "content": f"The page: {request[:300]}\n\nFolders:\n{lines}"}]


def library_pick(kind, asked, app, choose=None, choose_folder=None):
    """(picture path, folder name) from the user's library for this request, or None. The folder with the most of
    its name's words in the kind / request (an app request also fits a folder named admin / dashboard); its
    pictures in turn (the last one used is kept in .m42-used.json)."""
    if not LIBRARY.is_dir():
        return None
    words = _words(kind) | _words(asked)
    joined = re.sub(r"[^a-z0-9]", "", (kind or "") + (asked or "").lower())
    notes = catalog_words()
    best = None
    # whole-page folders only: components/ holds single parts (a product card, a date picker) that are no page design
    for d in sorted(p for p in LIBRARY.iterdir() if p.is_dir() and p.name != "components" and not p.name.startswith("_")):
        pics = sorted(f for f in d.iterdir() if f.is_file() and f.suffix.lower() in PICTURE_EXT)
        if not pics:
            continue
        tokens = [t for t in re.split(r"[-_\s]+", d.name.lower()) if t]
        # the subject ("school", "hospital") weighs more than the kind words every request has ("admin dashboard"):
        # "school admin" goes to school/, a "hospital admin" with no hospital/ pictures to admin-dashboard/
        score = sum((0.5 if GENERIC_RX.fullmatch(t) else 2) for t in tokens
                    if _fits(t, words) or (len(t) >= 5 and t in joined))
        if app and any(t in ("admin", "dashboard", "panel") for t in tokens):
            score += 0.5
        # what the folder's pictures show, from catalog.json ("smart home" finds iot-dashboard/, "crypto"
        # finance-dashboard/): a subject word there counts, less than one in the folder's own name
        seen = {w for w in notes.get(d.name, set()) if len(w) >= 4 and not GENERIC_RX.fullmatch(w)}
        score += min(2, sum(1 for w in words if len(w) >= 4 and not GENERIC_RX.fullmatch(w) and w in seen))
        if score and (not best or (score, len(pics)) > (best[0], len(best[2]))):
            best = (score, d, pics)
    # the chat model picks the folder by what the words mean (the word match above found nothing for "cafe website"
    # and mobile-app/ for "gym app"); the word match stays when it can't
    if choose_folder:
        folders = list(page_folders().items())
        try:
            ranked = [i for i in choose_folder(folders) if 0 <= i < len(folders)]
        except Exception:  # noqa: BLE001
            ranked = []
        if ranked:
            d = LIBRARY / folders[ranked[0]][0]
            best = (0, d, sorted(f for f in d.iterdir() if f.is_file() and f.suffix.lower() in PICTURE_EXT))
    if not best:
        return None
    _, d, pics = best
    used_file = LIBRARY / ".m42-used.json"
    try:
        used = json.loads(used_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        used = {}
    names = [p.name for p in pics]
    last = used.get(d.name)
    pick = pics[(names.index(last) + 1) % len(pics)] if last in names else pics[0]
    # the picture that suits the request (the coffee shop got the folder's AI SaaS shot, by turns): a chooser that
    # reads the pictures' catalog notes (the chat model) decides; the turn order only breaks ties / when it can't
    notes = catalog_notes(d.name)
    if choose and notes:
        options = [(f, notes.get(f.name, "")) for f in pics]
        try:
            ranked = [i for i in choose(options) if 0 <= i < len(pics)]
        except Exception:  # noqa: BLE001  (a chooser that fails leaves the turn order)
            ranked = None
        if ranked == []:
            # none of the folder's pictures is this kind of business (a coffee shop got the corporate Avers shot,
            # 2026-11-03): no library picture; the design data and the UI dataset's similar page come instead
            return None
        if ranked:
            pick = next((pics[i] for i in ranked if pics[i].name != last), pics[ranked[0]])
    used[d.name] = pick.name
    try:
        used_file.write_text(json.dumps(used, indent=1), encoding="utf-8")
    except OSError:
        pass
    return pick, d.name


TALL = 2.2  # a picture taller than 2.2 widths is a whole long page (a full-page screenshot of a landing page)


def trim_blank(im):
    """A full-page screenshot without the empty end: a capture of a page with scroll animations kept 8,000-26,000 px
    of blank (and only the floating "to top" button) after the footer."""
    import numpy as np
    step = max(1, im.height // 4000)
    a = np.asarray(im.convert("L").resize((200, max(1, im.height // step))), dtype=np.int16)
    # blank: a plain row of the page's own end colour (a plain navy band of a section is no blank)
    flat = ((a.max(1) - a.min(1)) < 6) & (np.abs(a.mean(1) - np.median(a[-max(1, len(a) // 50):])) < 6)
    need = max(20, int(im.width * 0.8) // step)
    start = None
    for i, v in enumerate(list(flat) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            # a long blank with (almost) nothing after it, and the page above it at least one screen
            if i - start >= need and (~flat[start:]).mean() < 0.05 and start * step >= im.width:
                return im.crop((0, 0, im.width, start * step))
            start = None
    return im


def page_sheet(im, max_side=1800):
    """A long page laid out in columns, read top to bottom, left to right (like a contact sheet): the vision model
    sees every section large enough to read, where the whole page made 1,800 px tall was a 108 px wide strip."""
    from PIL import Image
    cols = max(2, min(6, round(im.height / im.width / TALL)))
    cw = max_side // cols - 12
    small = im.resize((cw, max(1, round(im.height * cw / im.width))))
    ch = -(-small.height // cols)
    sheet = Image.new("RGB", (cols * (cw + 12), ch), im.getpixel((2, 2)))
    for c in range(cols):
        sheet.paste(small.crop((0, c * ch, cw, min(small.height, (c + 1) * ch))), (c * (cw + 12), 0))
    if max(sheet.size) > max_side:
        sheet.thumbnail((max_side, max_side))
    return sheet


def is_long(path):
    """The picture is a whole long page (it goes to the vision model as a page_sheet)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None  # a full-page screenshot is 1,600 x 52,000
    with Image.open(path) as im:
        return im.height > TALL * im.width


def as_png(path, out_dir, max_side=1800):
    """A library picture as a PNG for the vision model (a JPG / WEBP sent as PNG was refused: HTTP 400); a very big
    one made smaller; a whole long page (a full-page screenshot) without its blank end, in columns (page_sheet)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    # three "Dustrilox - Construction & Industry HTML..." shots share their first 40 letters: a short hash keeps them apart
    out = Path(out_dir) / (Path(path).stem[:32] + "-" + hashlib.md5(Path(path).name.encode()).hexdigest()[:6] + "-ref.png")
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.height > TALL * im.width:
            im = trim_blank(im)
            if im.height > TALL * im.width:
                im = page_sheet(im, max_side)
        if max(im.size) > max_side:
            im.thumbnail((max_side, max_side))
        im.save(out)
    return str(out)


SHEET_NOTE = ("This reference is ONE long landing page cut into columns: read the first column top to bottom, then the "
              "next column. The top of the first column is its header and hero; the end of the last column is its footer.")


GITHUB_SEARCH = "https://api.github.com/search/repositories"
HOSTED_DEMO_RX = re.compile(r"github\.io|vercel\.app|netlify\.app|pages\.dev|onrender\.com|demo|preview|live", re.I)


def github_queries(kind, app):
    """From the most exact to the most general: "school admin dashboard template", "admin dashboard template"..."""
    words = [w for w in re.findall(r"[a-z0-9]+", (kind or "").lower()) if w not in ("template", "website", "site")]
    tail = "dashboard template" if app else "website template"
    out = []
    for n in range(len(words), 0, -1):
        q = " ".join(words[-n:])
        out.append(q + " template" if "dashboard" in q or not app else q + " " + tail)
    out.append("admin " + tail if app else "landing page template")
    return list(dict.fromkeys(out))


def github_demos(kind, app, get, limit=4):
    """Open-source templates of this kind with a live demo: [(demo url, "owner/repo", licence)], most stars first.
    `get` fetches JSON (modelhub._get). The repo's own homepage field is its demo; a docs or shop page is skipped
    by the reading after the capture."""
    out, seen = [], set()
    for q in github_queries(kind, app):
        try:
            d = get(f"{GITHUB_SEARCH}?q={urllib.parse.quote(q)}+in:name,description,topics&sort=stars&order=desc&per_page=30")
        except (OSError, ValueError):
            break  # no connection / rate limit: the next priority
        for r in d.get("items") or []:
            home = str(r.get("homepage") or "").strip()
            if not home.startswith("http") or "github.com" in home or r.get("archived") or r["full_name"] in seen:
                continue
            if not HOSTED_DEMO_RX.search(home + " " + str(r.get("description") or "")):
                continue
            seen.add(r["full_name"])
            out.append((home, r["full_name"], ((r.get("license") or {}).get("spdx_id") or "no licence")))
            if len(out) >= limit:
                return out
        if out:
            return out
    return out


# the sites the design search looks in, written by the user (e.g. ["example.com", "demo.example.org"]); empty: the
# whole web. A site listed here must not be in GALLERY_RX / NOT_SITE_RX, or its results are dropped
REF_SITES = ["pinterest.com"]


def search_for(kind, app):
    """The web search for real examples, by M42 (a real run's own query, "... website examples", found a website
    builder's site and a template shop): a public site's own home page, or an app's live demo."""
    kind = " ".join(str(kind or "").split())[:40] or "website"
    query = f"{kind} live demo" if app else f"{kind} official website"
    if REF_SITES:
        query += " (" + " OR ".join(f"site:{s}" for s in REF_SITES) + ")"
    return query


def candidates(results, limit=3):
    """Home pages (or live demos) of real sites from search results: no design galleries, no social / Q&A /
    marketplace / encyclopedia sites, no article pages; one per site."""
    out, hosts = [], set()
    for r in results or []:
        parts = urllib.parse.urlsplit(str(r.get("url") or ""))
        host = parts.netloc.lower()
        if (parts.scheme not in ("http", "https") or not host or host in hosts or GALLERY_RX.search(host)
                or NOT_SITE_RX.search(host) or ARTICLE_RX.search(parts.path)):
            continue
        demo = DEMO_RX.search(host + parts.path)
        if not demo and len([x for x in parts.path.split("/") if x]) > 1:
            continue  # a page deep in a site (colorlib.com/wp/...: a list of templates): its home page is no example
        hosts.add(host)
        out.append(f"{parts.scheme}://{host}{parts.path if demo else '/'}")
        if len(out) >= limit:
            break
    return out


# ---- the pixels ----------------------------------------------------------------------------------------------

def _image(src, first_screen=False):
    from PIL import Image
    if str(src).startswith("data:"):
        im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1])))
    else:
        im = Image.open(src)
    im = im.convert("RGB")
    w, h = im.size
    if h > 500:
        im = im.crop((0, 0, w, int(h * .95)))  # a taskbar in a full-screen capture
    im = _unframe(im)
    if first_screen:  # the same window-shaped part of every capture (a long page and a 1280x800 shot alike)
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * .7))))
        im.thumbnail((480, 480))
        return im
    im.thumbnail((240, 240))
    return im


def _unframe(im):
    """A design shot shown on a coloured backdrop (Dribbble shots are: the UI card on a purple board): the backdrop
    is cut away, so the page's own colours count (the board's dull purple became a real run's brand colour). The
    card = the rows and columns where most pixels differ from the backdrop (the corner's colour); it is cut only
    when the backdrop shows on all four sides, so a page's own coloured menu bar or photo is never cut."""
    small = im.copy()
    small.thumbnail((320, 320))
    sw, sh = small.size
    px = small.load()

    def uniform(cells):  # a plain strip at the edge (a black bar under a capture)
        first = cells[0]
        return sum(sum((a - b) ** 2 for a, b in zip(c, first)) ** .5 < 12 for c in cells) / len(cells) >= .95
    y0, y1 = 0, sh
    while y1 - y0 > 2 and uniform([px[x, y1 - 1] for x in range(sw)]) and px[0, y1 - 1] != px[1, 1]:
        y1 -= 1
    corner = px[1, 1]
    far = lambda p: sum((a - b) ** 2 for a, b in zip(p, corner)) ** .5 > 25  # noqa: E731  (a pale board too)
    rows = [y for y in range(y0, y1) if sum(far(px[x, y]) for x in range(sw)) / sw >= .5]
    cols = [x for x in range(sw) if sum(far(px[x, y]) for y in range(y0, y1)) / max(1, y1 - y0) >= .5]
    if not rows or not cols:
        return im

    def run(idx):  # the longest stretch (gaps of 3 allowed): a dark 1 px edge or a black bar is no part of the card
        best, cur = [], [idx[0]]
        for a in idx[1:]:
            if a - cur[-1] <= 3:
                cur.append(a)
            else:
                best, cur = max(best, cur, key=len), [a]
        best = max(best, cur, key=len)
        return best[0], best[-1] + 1
    (top, bottom), (left, right) = run(rows), run(cols)
    margin = lambda a, total: a >= .02 * total  # noqa: E731
    # the board shows on at least three sides (a shot is often cut off at the bottom)
    if sum((margin(top - y0, sh), margin(y1 - bottom, sh), margin(left, sw), margin(sw - right, sw))) < 3:
        return im
    if (bottom - top) * (right - left) < .3 * sw * sh:
        return im
    k = im.width / sw
    return im.crop((int(left * k), int(top * k), int(right * k), int(bottom * k)))


def _lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    r, g, b = rgb
    return .2126 * ch(r) + .7152 * ch(g) + .0722 * ch(b)


def _hue(hexs):
    r, g, b = (int(hexs[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def hue_gap(a, b):
    d = abs(_hue(a) - _hue(b)) % 360
    return min(d, 360 - d)


def shades(src):
    """{family: "#hex"}: each colour family's strong shade in the picture (a line, a button, a tile's icon), the
    median of its saturated mid-tone pixels; pale tints and the greys left out."""
    from PIL import Image
    im = _image(src)
    im.thumbnail((360, 360))
    px = list(im.getdata())
    by = {}
    for r, g, b in px:
        h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if sat < .25 or not .22 <= l <= .72:
            continue
        deg = h * 360
        fam = next((f for f, (a, z) in HUES.items() if (a <= deg < z if a < z else deg >= a or deg < z)), None)
        if fam:
            by.setdefault(fam, []).append((sat, (r, g, b)))
    out = {}
    for fam, ps in by.items():
        if len(ps) >= .0015 * len(px):
            ps = [p for _, p in sorted(ps, reverse=True)[:max(1, len(ps) // 2)]]  # the stronger half: not the pale edges
            out[fam] = "#" + "".join(f"{sorted(c)[len(c) // 2]:02x}" for c in zip(*ps))
    return out


def profile(src):
    """{"theme", "bg", "colors" (up to 3 accent colours, most used first, hues apart), "density", "busy"}:
    light / dark from the background (the most used colour), accents = the saturated colours that cover a real
    part of the page, density = how much of the page is not background."""
    from PIL import Image
    im = _image(src)
    q = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:48]
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    cols = [(tuple(pal[i * 3:i * 3 + 3]), c / total) for c, i in counts]
    bg = cols[0][0] if cols else (255, 255, 255)
    px = list(im.getdata())

    def vivid(p):
        h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in p))
        # ... or a clear pastel (the school shot's lavender and yellow chart colours: light, but plainly a colour)
        return (s >= .35 and .18 <= l <= .82) or (s >= .6 and l <= .92)
    # the accents from the vivid pixels alone (quantized with the greys, a small green button merged into them)
    sat = [p for p in px if vivid(p)]
    accents = []
    # the brand colour: the vivid colour that fills the top strip (a coloured menu bar), before the photo's colours
    top = _image(src, first_screen=True)
    top = top.crop((0, 0, top.width, max(1, int(top.height * .12))))
    tpx = [p for p in top.getdata() if vivid(p)]
    if len(tpx) > .3 * top.width * top.height:
        ti = Image.new("RGB", (len(tpx), 1))
        ti.putdata(tpx)
        tq = ti.quantize(colors=2, method=Image.Quantize.MEDIANCUT)
        tpal = tq.getpalette()[:6]
        c, i = max(tq.getcolors())
        accents.append("#%02x%02x%02x" % tuple(tpal[i * 3:i * 3 + 3]))
    if sat:
        si = Image.new("RGB", (len(sat), 1))
        si.putdata(sat)
        sq = si.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        spal = sq.getpalette()[:24]
        def strength(ci):  # a strong mid-tone (a button, a toggle) over a large pale tint of it
            r, g, b = (v / 255 for v in spal[ci[1] * 3:ci[1] * 3 + 3])
            _, l, sat = colorsys.rgb_to_hls(r, g, b)
            return ci[0] * sat * max(.1, 1 - abs(l - .5) * 1.6)
        for c, i in sorted(sq.getcolors() or [], key=strength, reverse=True):
            rgb = tuple(spal[i * 3:i * 3 + 3])
            hexs = "#%02x%02x%02x" % rgb
            if c / len(px) >= .003 and vivid(rgb) and all(hue_gap(hexs, a) >= 28 for a in accents):
                accents.append(hexs)
            if len(accents) == 3:
                break
        # slots left: by hue (the colour wheel in 15° steps), so a smaller colour of its own is not swallowed by the
        # main one's shades (the school shot: 8 groups were all its cyan; its lavender and yellow charts were lost)
        if len(accents) < 3:
            bins = {}
            for q in sat:
                bins.setdefault(int(colorsys.rgb_to_hls(*(v / 255 for v in q))[0] * 24) % 24, []).append(q)
            for n, group in sorted(bins.items(), key=lambda kv: -len(kv[1])):
                if len(group) / len(px) < .002:
                    break
                rgb = tuple(sorted(c[k] for c in group)[len(group) // 2] for k in range(3))
                hexs = "#%02x%02x%02x" % rgb
                if vivid(rgb) and all(hue_gap(hexs, a) >= 28 for a in accents):
                    accents.append(hexs)
                if len(accents) == 3:
                    break
    busy = sum(1 for p in px if sum((a - b) ** 2 for a, b in zip(p, bg)) ** .5 > 45) / max(1, len(px))
    # density = how much drawn detail (text, lines, borders) per area, from the edges of the first screen: M42's own
    # pages measure .033-.074; a crowded admin template or a news site is far above, a quiet landing page below
    from PIL import ImageFilter
    g = _image(src, first_screen=True).convert("L")
    edges = list(g.filter(ImageFilter.FIND_EDGES).getdata())
    detail = sum(1 for e in edges if e > 40) / max(1, len(edges))
    return {"theme": "dark" if _lum(bg) < .2 else "light", "bg": "#%02x%02x%02x" % bg, "colors": accents, "shades": shades(src),
            "density": "airy" if detail < .03 else "dense" if detail > .085 else "balanced", "busy": round(busy, 3),
            "detail": round(detail, 3)}


def blank(prof):
    """A capture with nothing on it (an error page, a cookie wall over white, a page still loading)."""
    return prof["busy"] < .04


# ---- the design, read by the vision model -----------------------------------------------------------------

def brief_messages(image, request, kind="", note=""):
    want = f"The user wants: {request[:400]}" + (f"\nThe kind of site: {kind}" if kind else "") + (f"\n{note}" if note else "")
    return [{"role": "system", "content": BRIEF_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"{want}\nWrite down this reference page's design."},
                {"type": "image_url", "image_url": {"url": image}}]}]


def clean_brief(raw):
    raw = raw if isinstance(raw, dict) else {}
    pick = lambda k, allowed, d: raw.get(k) if raw.get(k) in allowed else d  # noqa: E731
    secs = [" ".join(str(x.get("what") if isinstance(x, dict) else x or "").split())[:60]
            for x in raw.get("sections") or []][:8]
    return {"match": raw.get("match") != "no" and raw.get("covered") != "yes", "layout": pick("layout", LAYOUTS, "top-nav"), "hero": pick("hero", HEROES, ""),
            "cards": pick("cards", ("glass", "shadow", "outlined", "flat"), "shadow"),
            "corners": pick("corners", ("sharp", "rounded", "pill"), "rounded"),
            "style": pick("style", webkit.STYLES, ""), "font": pick("font", tuple(webkit.FONTS), ""),
            "mood": " ".join(str(raw.get("mood") or "").split())[:60], "sections": [x for x in secs if x],
            "topic": " ".join(str(raw.get("topic") or "").split())[:60],
            "screen": " ".join(str(raw.get("screen") or "").split())[:30],
            "theme": raw.get("theme") if raw.get("theme") in ("light", "dark") else "",
            "menu": raw.get("menu") if raw.get("menu") in ("text sidebar", "icon rail", "top bar", "none") else "",
            "accent": raw.get("accent") if raw.get("accent") in HUES else "",
            "header": None if isinstance(raw.get("header"), list) and len(set(raw["header"])) >= 7 else [x for x in dict.fromkeys(raw.get("header") or []) if x in HEADER_BITS] if isinstance(raw.get("header"), list) else None}


# words that name a kind of page or ask for one, not what it is about ("intha mathiri oru site pannu admin dashboard")
FILLER_RX = re.compile(r"\b(intha|indha|itha|ithe|athe|mathiri|maathiri|madhiri|pola|like|this|that|same|design|oru|"
                       r"onnu|ennaku|enakku|enaku|pannu|pannunga|panni|kudu|kutu|venum|vennum|vendum|create|make|build|"
                       r"want|need|please|pls|a|an|the|for|with|of|my|me|site|website|web|page|webpage|app|application|"
                       r"admin|dashboard|panel|portal|ui|ux|template|layout|style|look|nalla|super|premium|modern|"
                       r"simple|beautiful|la|le|ku|ah|da|bro|na|ok|and|in|on|clone|copy|replicate|re-?create|exact|exactly|html|"
                       r"css|code|pixel|perfect|to|apadiye|apdiye|appadiye|ithula|ithila|ithil|athula|irukka|irukkura|irukkira|"
                       r"irukura|ready|readya|some|any|good|nice|kudunga|kodu|thaa|tha|venam|neat|clean|new|one|create|"
                       r"layouts|templates|designs|pages|sites|maadhiri|matheri|mathri|madhri|mathiri|maathiri)\b", re.I)


def generic(request):
    """The request names no subject of its own (only "a site / an admin dashboard like this"): the topic then comes
    from the user's reference picture (a smart home dashboard shot gave a "Tamil Nadu Bus Admin")."""
    words = re.sub(r"https?://\S+|www\.\S+", " ", (request or "").lower())
    return not re.search(r"[a-z]{3,}", FILLER_RX.sub(" ", words))


THEME_WORDS_RX = re.compile(r"\b(dark|light|white|black|night)\b", re.I)


def merge(spec, briefs, profiles, request):
    """The spec with the reference's design: its layout, hero, look (light / dark, colours, style, font, corners,
    cards, density) and the order of its sections, given to the plan as the structure to follow. The user's own
    words win (a colour or dark / light they named, a style word)."""
    spec = dict(spec or {})
    # one reference gives both its design and its colours (briefs[i] and profiles[i] are the same picture): the first
    # one that was read and not blank; else whatever there is
    pairs = [(b, p) for b, p in zip(briefs, profiles) if b and p and not blank(p)]
    # a public page read with no hero at all was most often hidden behind something: the others first
    pairs.sort(key=lambda bp: bp[0].get("hero") == "none" and bp[0].get("layout") == "top-nav")
    b, p = pairs[0] if pairs else (next((x for x in briefs if x), None) or {},
                                   next((x for x in profiles if x and not blank(x)), None))
    look = dict(spec.get("look") or {})
    if p:
        if not THEME_WORDS_RX.search(request or ""):
            look["theme"] = p["theme"]
        if p["colors"]:
            look["colors"] = (p["colors"] + [c for c in look.get("colors") or [] if c not in p["colors"]])[:3]
            look["exact"] = True  # the picture's own colours: the page keeps them as they are (not darkened)
        look["density"] = p["density"]
        if p.get("bg"):  # the page's own background (a cream admin came out grey-blue, 2026-11-12); make_look keeps it
            look["bg"] = p["bg"]  # only when it fits the theme
    if b and b.get("theme") and not THEME_WORDS_RX.search(request or ""):
        look["theme"] = b["theme"]  # the vision model sees the page; the pixels also count the room around a photo
    # the main colour the vision model names (the Travelgo shot: "purple"; its pixels' biggest colour was the pink room
    # around the board, a brown site came out), in the shade the picture has
    fam = next((f for f in NEAR.get((b or {}).get("accent") or "", ()) if f in ((p or {}).get("shades") or {})), None)
    if fam:
        main = p["shades"][fam]
        # the others a colour of their own, not the main one again in another shade (#44bddd, #3abadb)
        look["colors"] = [main] + [c for c in look.get("colors") or [] if hue_gap(c, main) >= 28][:2]
    if b:
        for k in ("style", "font", "corners", "cards"):
            if b.get(k):
                look[k] = b[k]
        if b.get("hero"):
            spec["hero"] = b["hero"]
        spec["ref_layout"] = b["layout"]
        if b.get("header") is not None:
            spec["top_bar"] = b["header"]  # the reference's own top strip: only what it shows (the user: no bar on every page)
        if b.get("sections"):
            spec["reference"] = "; ".join(b["sections"])
    look["why"] = "taken from the reference design"
    spec["ref_done"] = True
    spec["look"] = look
    return spec


def summary(spec):
    lk = spec.get("look") or {}
    bits = [spec.get("ref_layout"), f"hero {spec['hero']}" if spec.get("hero") else "", lk.get("theme"), lk.get("style"),
            f"{lk['corners']} corners" if lk.get("corners") else "", f"{lk['cards']} cards" if lk.get("cards") else "",
            lk.get("density"), " ".join(lk.get("colors") or [])]
    return " · ".join(b for b in bits if b)


# ---- the check after the build ----------------------------------------------------------------------------

def check(page_prof, ref_prof):
    """What the built page's screenshot does differently from the reference: [(key, value to set, words)]."""
    if not page_prof or not ref_prof or blank(ref_prof):
        return []
    out = []
    if page_prof["theme"] != ref_prof["theme"]:
        out.append(("theme", ref_prof["theme"], f"the page is {page_prof['theme']}, the reference {ref_prof['theme']}"))
    # the reference's main colour must be among the page's colours (its own first one may be a pale background tint)
    if ref_prof["colors"] and page_prof["colors"] and min(hue_gap(ref_prof["colors"][0], c) for c in page_prof["colors"]) > 35:
        out.append(("colors", ref_prof["colors"], f"its main colour {page_prof['colors'][0]} is far from the "
                                                  f"reference's {ref_prof['colors'][0]}"))
    order = ("airy", "balanced", "dense")
    if abs(order.index(page_prof["density"]) - order.index(ref_prof["density"])) == 2:
        out.append(("density", ref_prof["density"], f"the page is {page_prof['density']}, the reference "
                                                    f"{ref_prof['density']}"))
    return out


def save_ref(image, folder, name):
    """An attached reference (a data URL) as a PNG file, for the check after the build."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    out = Path(folder) / name
    if str(image).startswith("data:"):
        out.write_bytes(base64.b64decode(str(image).split(",", 1)[1]))
        return out
    return Path(image)


def apply(spec, diffs, request=""):
    """The spec's look corrected by what check() found (a light / dark the user named stays)."""
    look = dict((spec or {}).get("look") or {})
    for key, value, _ in diffs:
        if key == "theme" and THEME_WORDS_RX.search(request or ""):
            continue
        look[key] = value
    return dict(spec or {}, look=look)


# ---- the reference's cards and their grid (Step 1: from the pixels, no model) -------------------------------

def _mode(px):
    """The most used colour of some pixels (in steps of 8)."""
    import numpy as np
    q = (px.reshape(-1, 3) // 8)
    keys, counts = np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2], return_counts=True)
    k = int(keys[counts.argmax()])
    return np.array([k // 1024, k // 32 % 32, k % 32]) * 8 + 4, counts.max() / max(1, q.shape[0])


def _card_boxes(arr, x0, y0, x1, y1, root_w, root_h, depth=0, bg=None):
    """The cards of a region by an XY-cut on its gutters (rows / columns of nothing but the page background):
    a part whose own colour is not the page's is a card surface and is not cut further; a part of the page's
    colour (white cards with only a border on a white page) is cut again inside, until no gutter is left."""
    import numpy as np
    sub = arr[y0:y1, x0:x1]
    if sub.size == 0 or depth > 7:
        return []
    if bg is None:
        bg, _ = _mode(sub)
    busy = np.sqrt(((sub - bg) ** 2).sum(axis=2)) > 14  # a soft card shadow (8-12) is still a gutter
    out = []
    for axis, total in ((1, root_h), (0, root_w)):  # rows first (bands top to bottom), then columns
        prof = busy.sum(axis=axis)
        size = busy.shape[1 - axis]
        gut = prof <= max(1, .004 * size)
        segs, cur = [], None
        for i, g in enumerate(gut):
            if not g and cur is None:
                cur = i
            elif g and cur is not None:
                segs.append((cur, i))
                cur = None
        if cur is not None:
            segs.append((cur, len(gut)))
        # gutters narrower than a few pixels are spaces between words, not between cards
        merged = []
        for a, b in segs:
            if merged and a - merged[-1][1] < max(3, .008 * total):
                merged[-1] = (merged[-1][0], b)
            else:
                merged.append((a, b))
        if len(merged) > 1 or (merged and (merged[0][0] > 2 or merged[0][1] < len(gut) - 2)):
            for a, b in merged:
                bx = (x0, y0 + a, x1, y0 + b) if axis == 1 else (x0 + a, y0, x0 + b, y1)
                out += _region(arr, bx, root_w, root_h, depth, bg)
            return out
    return [(x0, y0, x1, y1)]


def _region(arr, box, root_w, root_h, depth, bg):
    """A part between gutters: a card (its own surface colour, or too small to hold cards), or cut again."""
    import numpy as np
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w < .06 * root_w or h < .04 * root_h:
        return [("small", box)]
    sub = arr[y0:y1, x0:x1]
    col, share = _mode(sub)
    if np.sqrt(((col - bg) ** 2).sum()) > 7 and share > .6:  # a surface of its own colour: a card (or a panel of cards)
        inner = _card_boxes(arr, x0 + 1, y0 + 1, x1 - 1, y1 - 1, root_w, root_h, depth + 1, bg=col)
        cards = [b for b in inner if not (isinstance(b, tuple) and b and b[0] == "small")]
        if len(cards) >= 2 and depth < 2 and w * h > .3 * root_w * root_h:  # a panel holding cards (a grey main area)
            return cards
        return [box]
    return _card_boxes(arr, x0, y0, x1, y1, root_w, root_h, depth + 1, bg=bg)


def _merge_stacks(boxes, W, H):
    """Rows of one list on a white card on a white page come out as thin boxes one under another: boxes in the same
    column (left and right edges within 3%) with small gaps between them are one card."""
    boxes = sorted(boxes, key=lambda b: (b[0], b[1]))
    out = []
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        for k, o in enumerate(out):
            if (abs(o[0] - b[0]) < .03 * W and abs(o[2] - b[2]) < .06 * W and 0 <= b[1] - o[3] < .07 * H
                    and max(o[3] - o[1], b[3] - b[1]) < .09 * H):  # list rows, not two cards
                out[k] = (min(o[0], b[0]), o[1], max(o[2], b[2]), b[3])
                break
        else:
            out.append(b)
    return out


def _cut(boxes, idx):
    """An XY-cut of the boxes: columns where a vertical gutter crosses them all, else rows where a horizontal one
    does; a leaf when one box is left. {"dir": "cols" | "rows", "children": [...], "box": (x0, y0, x1, y1)} or
    {"leaf": i, "box": ...}."""
    bx = lambda ids: (min(boxes[i][0] for i in ids), min(boxes[i][1] for i in ids),  # noqa: E731
                      max(boxes[i][2] for i in ids), max(boxes[i][3] for i in ids))
    if len(idx) == 1:
        return {"leaf": idx[0], "box": boxes[idx[0]]}
    for d, a, b in (("cols", 0, 2), ("rows", 1, 3)):
        groups, end = [], None
        for i in sorted(idx, key=lambda i: boxes[i][a]):
            # a gutter before this box: a shadow, or a card grown to its gutter (_grow), may overlap up to 3%
            # (1.5% left the D.CC shot's grid as one column of 6 cards: its Stores card ran 1.7% into the next row)
            if end is None or boxes[i][a] > end - .03:
                groups.append([i])
                end = boxes[i][b]
            else:
                groups[-1].append(i)
                end = max(end, boxes[i][b])
        if len(groups) > 1:
            kids = []
            for g in groups:  # rows inside rows are one list of rows (the same for columns)
                k = _cut(boxes, g)
                kids += k["children"] if k.get("dir") == d else [k]
            return {"dir": d, "children": kids, "box": bx(idx)}
    return {"dir": "rows", "children": [{"leaf": i, "box": boxes[i]} for i in sorted(idx, key=lambda i: (boxes[i][1], boxes[i][0]))],
            "box": bx(idx)}


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / float((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter or 1)


def _surfaces(img):
    """Card boxes by their surfaces (OpenCV): the inside of a flat card is one unbroken area of one colour, so the
    parts of the picture between edges are labelled; big, well-filled ones are cards, an area holding two or more
    of them is a panel (left out), one touching the picture's sides all round is the page or its board."""
    import cv2
    import numpy as np
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 12, 36)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    masks = [(edges == 0).astype(np.uint8)]
    # a white card on a near-white page has almost no edge: each main surface colour on its own (exact, +-3)
    q = (img // 4).reshape(-1, 3).astype(np.int32)
    keys, counts = np.unique(q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2], return_counts=True)
    k5 = np.ones((5, 5), np.uint8)
    for k in keys[np.argsort(-counts)][:10]:
        if counts[np.where(keys == k)[0][0]] < .004 * W * H:
            break
        c = np.array([k // 4096, k // 64 % 64, k % 64]) * 4 + 2
        m = (np.abs(img.astype(np.int32) - c).max(axis=2) <= 3).astype(np.uint8)
        # closed: stripes and text inside a pastel card don't split it; eroded: a hair-thin border (#fafafa on
        # white) with anti-aliased gaps still keeps a card apart from the page
        k3 = np.ones((3, 3), np.uint8)
        # closed first: stripes and text inside a pastel card don't split it
        masks.append(cv2.erode(cv2.morphologyEx(m, cv2.MORPH_CLOSE, k5), k3, iterations=2))
        if int(c.max()) - int(c.min()) <= 25:  # white / grey: also only eroded (closing joined white cards on a white
            masks.append(cv2.erode(m, k3, iterations=2))  # page across their hair-thin borders: the cooking reference)
    # a white card on a white page with only a soft shadow round it (the smart-home shot's "Main door"): the shadow
    # is 245-254, so only pure white is card, and the shadow keeps each card apart
    strict = ((img.min(axis=2) == 255) & (img.max(axis=2) == 255)).astype(np.uint8)
    stats_all, extra = [], []
    if strict.mean() > .2:
        n, lab, stats, _ = cv2.connectedComponentsWithStats(cv2.erode(strict, np.ones((3, 3), np.uint8), iterations=1), connectivity=4)
        extra += [stats[i] for i in range(1, n)]
    for m in masks:
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
        stats_all += [stats[i] for i in range(1, n)]
    # a photo card (the smart-home shot's security camera) is no flat surface: a block busy all over, square-edged
    g = gray.astype(np.float32)
    mu = cv2.blur(g, (7, 7))
    busy = (np.sqrt(np.maximum(cv2.blur(g * g, (7, 7)) - mu * mu, 0)) > 6).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(busy, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), connectivity=4)
    photos = [s for s in stats[1:] if s[4] / float(s[2] * s[3]) >= .8 and s[2] >= .12 * W and s[3] >= .1 * H]
    extra += photos
    # a big card that is anything but the page's own colour, whole (the Jiron shot's week calendar: white on a page
    # 11 off white, cut in two by its grey "today" column, so no one surface): page-coloured gutters keep cards apart
    q4 = (img // 4).reshape(-1, 3).astype(np.int32)
    kk, cc = np.unique(q4[:, 0] * 4096 + q4[:, 1] * 64 + q4[:, 2], return_counts=True)
    k0 = kk[cc.argmax()]
    page_c = np.array([k0 // 4096, k0 // 64 % 64, k0 % 64]) * 4 + 2
    offp = (np.abs(img.astype(np.int32) - page_c).max(axis=2) > 5).astype(np.uint8)
    offp = cv2.morphologyEx(offp, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(offp, connectivity=4)
    extra += [st for st in stats[1:] if .08 * W * H <= st[2] * st[3] <= .4 * W * H  # a card, not a whole board (ClothIQ's)
              and st[4] / float(st[2] * st[3]) >= .8]
    cand, small = [], []
    inside = lambda a, b: a != b and b[0] - 3 <= a[0] and b[1] - 3 <= a[1] and a[2] <= b[2] + 3 and a[3] <= b[3] + 3  # noqa: E731
    base = len(stats_all)
    for k, (x, y, w, h, area) in enumerate(stats_all + extra):
        if k == base:
            n_base = len(cand)
        if k >= base and any(inside((x, y, x + w, y + h), o) for o in cand[:n_base]):
            continue  # pure white / a photo only adds cards: a white part of a found card (an agenda row) is not one
        if k < base and .025 * W <= w < .3 * W and .025 * H <= h < .12 * H and area >= .0012 * W * H and x > 1 and y > 1                 and area / float(w * h) >= .35 and not any(_iou((x, y, x + w, y + h), o) > .7 for o in small):
            small.append((int(x), int(y), int(x + w), int(y + h)))  # a chip, a pill, a round icon button
        if w < .07 * W or h < .05 * H or area < .006 * W * H:
            continue
        if x <= 1 or y <= 1 or x + w >= W - 1 or w * h > .6 * W * H:
            continue  # the page, the board around a shot, its decoration (cards stay off the left, top and right edges)
        if area / float(w * h) < .35:
            continue  # a thin outline, not a surface
        box = (int(x), int(y), int(x + w), int(y + h))
        if not any(_iou(box, o) > .8 for o in cand):  # found by both passes
            cand.append(box)
    keep = []
    for c in cand:
        kids = [d for d in cand if inside(d, c)]
        if len(kids) >= 2 and not _holds_items(c, kids, W * H):
            continue  # a panel holding cards
        if any(inside(c, o) and (len([d for d in cand if inside(d, o)]) < 2 or _holds_items(o, [d for d in cand if inside(d, o)], W * H))
               for o in cand):
            continue  # a block inside one card (its chart area, its image, an event on its calendar): the card stands for it
        keep.append(c)
    # rows of three or more alike small things (flag chips, step pills, an icon grid, - 2 + EU): one card each;
    # alone each was too small to be a card and the reference lost them (the cooking shot)
    for row in _rows_of(small, W, H):
        box = (min(b[0] for b in row) - 2, min(b[1] for b in row) - 2, max(b[2] for b in row) + 2, max(b[3] for b in row) + 2)
        if not any(inside(box, k) or _iou(box, k) > .3 for k in keep) and box[0] > .12 * W:
            keep.append(box)
    _surfaces.rail = _rail(small, W, H)
    return keep


def _rows_of(small, W, H):
    """Groups of 3+ small boxes in one line: centres level, heights alike, small gaps between them."""
    rows = []
    for b in sorted(small, key=lambda b: (b[1] + b[3]) / 2):
        cy, h = (b[1] + b[3]) / 2, b[3] - b[1]
        for r in rows:
            last = max(r, key=lambda o: o[2])
            ry, rh = (r[0][1] + r[0][3]) / 2, r[0][3] - r[0][1]
            if abs(cy - ry) < .02 * H and .6 < h / rh < 1.6 and min(abs(b[0] - o[2]) for o in r) < .05 * W:
                r.append(b)
                break
        else:
            rows.append([b])
    return [r for r in rows if len(r) >= 3]


def _grow(img, boxes):
    """Each card grown up and down to its gutters: a part of a card found alone (a chart's curve cut the weather
    shot's "Live conditions" card in two, and only the numbers under it were found) is grown while the rows
    above / below it are still card (not the page's own colour, or with something drawn on them), up to the
    next box."""
    import numpy as np
    H, W = img.shape[:2]
    inside = np.zeros((H, W), bool)
    for b in boxes:
        inside[b[1]:b[3], b[0]:b[2]] = True
    rest = img[~inside]
    if rest.size == 0:
        return boxes
    bg, _ = _mode(rest.astype(np.int32))
    img = img.astype(np.int32)
    lo, hi = min(b[1] for b in boxes), max(b[3] for b in boxes)  # never past the cards' own span (a photo's room)
    out = []
    for k, b in enumerate(boxes):
        x0, y0, x1, y1 = b
        others = [o for j, o in enumerate(boxes) if j != k and o[0] < x1 and o[2] > x0]
        own, _ = _mode(img[y0:y1, x0:x1].reshape(-1, 3))  # the card's own colour

        def gutter(y):
            seg = img[y, x0 + 2:x1 - 2]
            if seg.size == 0 or (np.sqrt(((seg - bg) ** 2).sum(axis=1)) <= 8).mean() >= .9:
                return True
            # one flat colour that is not the card's: the page between cards (the school shot's grey gaps were
            # taken for card, as "the page's colour" came out as its backdrop / white menu: a tile grew into the banner)
            mid = np.median(seg, axis=0)
            if not ((np.abs(seg - mid).max(axis=1) <= 6).mean() >= .9 and np.abs(mid - own).max() > 5):
                return False
            # ... and the same colour carries on just outside the card at that height (a chart's flat fill inside a
            # card stops at the card's edge: fitshop's "Total Orders" was cut at its curve)
            sides = [img[y, x] for x in (x0 - 4, x1 + 3) if 0 <= x < W]
            return any(np.abs(px - mid).max() <= 8 for px in sides)

        def blocked(y):
            return any(o[1] <= y < o[3] for o in others)
        top, bottom = y0, y1
        while top > lo and not gutter(top - 1) and not blocked(top - 1) and y0 - top < .4 * H:
            top -= 1
        while bottom < hi and not gutter(bottom) and not blocked(bottom) and bottom - y1 < .4 * H:
            bottom += 1
        out.append((x0, top, x1, bottom))
    return out


def _element_grid(els, cards_, W, H):
    """4+ alike elements in 2+ rows and 2+ columns (the POS shot's 8 product cards) are ONE grid card: the pixel
    finder cut it into a strip of photos and a strip of words per row (three "lists" came out). The boxes inside it,
    and those right under it within its width (the last row's words), go into it."""
    area = lambda b: max(1.0, (b[2] - b[0]) * (b[3] - b[1]))  # noqa: E731
    inter = lambda a, b: max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))  # noqa: E731
    big = [e for e in els if e[2] - e[0] >= .06 * W and e[3] - e[1] >= .08 * H]
    best = []
    for e in big:
        w, h = e[2] - e[0], e[3] - e[1]
        alike = [o for o in big if abs((o[2] - o[0]) - w) < .25 * w and abs((o[3] - o[1]) - h) < .25 * h]
        uniq = []
        for o in alike:  # one per place (the model gives a card and its photo both)
            if all(inter(o, u) < .5 * area(o) for u in uniq):
                uniq.append(o)
        cols = {round((o[0] + o[2]) / 2 / (w * .6)) for o in uniq}
        rows = {round((o[1] + o[3]) / 2 / (h * .6)) for o in uniq}
        # a full rectangle only: every row as many as the others, in the same columns (Travelgo's number tiles over
        # two other cards, the weather shot's 8 hours over 7 days were taken for grids)
        cells = {(round((o[0] + o[2]) / 2 / (w * .6)), round((o[1] + o[3]) / 2 / (h * .6))) for o in uniq}
        full = len(cells) == len(uniq) == len(cols) * len(rows)
        if full and len(uniq) >= 4 and len(cols) >= 2 and len(rows) >= 2 and len(uniq) > len(best):
            best = uniq
    if not best:
        return cards_
    g = [min(o[0] for o in best), min(o[1] for o in best), max(o[2] for o in best), max(o[3] for o in best)]
    inside = [c for c in cards_ if inter(c, g) >= .5 * area(c)]
    for c in inside:
        g = [min(g[0], c[0]), min(g[1], c[1]), max(g[2], c[2]), max(g[3], c[3])]
    below = [c for c in cards_ if c not in inside and c[0] >= g[0] - .02 * W and c[2] <= g[2] + .02 * W
             and -.02 * H <= c[1] - g[3] < .015 * H]
    for c in inside + below:
        g = [min(g[0], c[0]), min(g[1], c[1]), max(g[2], c[2]), max(g[3], c[3])]
    _element_grid.found = (tuple(int(v) for v in g), len(best))  # cards() marks it: a grid of len(best) items
    return [c for c in cards_ if c not in inside and c not in below] + [tuple(int(v) for v in g)]


def _with_elements(im, content, W, H, left):
    """The pixel finder's cards with the UI element model's finds (uidetect: the cooking shot's photo cards, step
    pills, date picker and row of ingredient icons have no surface of their own, and were missed):
      - a big element outside every card (a photo card, a tile) is a card;
      - small elements outside every card, near each other, are one block (a row of steps, a picker, an icon grid);
      - a block touching a card along its column (the rest of a list found to its first row) grows that card.
    Elements above every card are the page's head (read on its own: designref.top_messages), not cards."""
    import numpy as np
    import cv2
    import uidetect
    els = [e for e in uidetect.elements(im) if e[0] >= left - 2]
    if not els or not content:
        return content
    area = lambda b: max(1.0, (b[2] - b[0]) * (b[3] - b[1]))  # noqa: E731
    inter = lambda a, b: max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))  # noqa: E731
    cards_ = _element_grid(els, [tuple(b) for b in content], W, H)
    arr = np.asarray(im)
    white = lambda e: (arr[int(e[1]):int(e[3]), int(e[0]):int(e[2])].min(axis=2) >= 235).mean()  # noqa: E731
    # a big element mostly white with words on it is a heading (the cooking shot's "What dish do you want to cook
    # today?" became a card), not a card; a photo or a coloured tile is
    big = [e for e in els if e[2] - e[0] >= .07 * W and e[3] - e[1] >= .07 * H and white(e) < .6]
    for e in sorted(big, key=area, reverse=True):
        if all(inter(e, c) < .3 * area(e) for c in cards_) and sum(inter(c, e) >= .7 * area(c) for c in cards_) < 2:
            cards_.append(tuple(int(v) for v in e))
    head = min(c[1] for c in cards_) - .01 * H
    rest = [e for e in els if e[1] >= head and all(inter(e, c) < .5 * area(e) for c in cards_)]
    mask = np.zeros((H, W), np.uint8)
    gx, gy = int(.012 * W), int(.012 * H)
    for e in rest:
        mask[max(0, int(e[1]) - gy):int(e[3]) + gy, max(0, int(e[0]) - gx):int(e[2]) + gx] = 1
    n, lab = cv2.connectedComponents(mask, connectivity=8)
    groups = {}
    for e in rest:
        k = lab[min(H - 1, int((e[1] + e[3]) / 2)), min(W - 1, int((e[0] + e[2]) / 2))]
        groups.setdefault(k, []).append(e)
    for members in groups.values():
        g = (int(min(e[0] for e in members)), int(min(e[1] for e in members)), int(max(e[2] for e in members)), int(max(e[3] for e in members)))
        if len(members) < 2 or g[2] - g[0] < .08 * W or g[3] - g[1] < .025 * H:
            continue
        # its card: the one it overlaps most; else one it touches end to end in its column (a gap of 1.5% at most:
        # cards one under another stand ~2% apart; with 3% ClothIQ's badge card grew over the chart above it)
        over = max(range(len(cards_)), key=lambda k: inter(g, cards_[k]))
        host = over if inter(g, cards_[over]) >= .3 * area(g) else None
        if host is None:
            near = []
            for k, c in enumerate(cards_):
                ox = min(g[2], c[2]) - max(g[0], c[0])
                gap = min(abs(g[1] - c[3]), abs(c[1] - g[3]))
                if gap < .015 * H and ox > .6 * min(g[2] - g[0], c[2] - c[0]):
                    near.append((gap, k))
            host = min(near)[1] if near else None
        if host is not None:  # the card grows up / down to it, keeping its own width (a chef icon at the chart's
            c = cards_[host]   # end widened the cooking shot's right column into the middle one: the grid mixed them)
            cards_[host] = (c[0], min(c[1], g[1]), c[2], max(c[3], g[3]))
        else:
            cards_.append(g)
    return cards_


def _tile_rows(boxes, W, H):
    """3+ small tiles alike side by side in one line (872 New Booking, 285 Schedule Room, 53 Check In, 78 Check Out;
    Air purifier, Android TV, Geyser, Smart Cleaner) are one card: read as one row of tiles, the plan fills each
    tile. Read one by one, each became its own "Total 0" panel (a real run)."""
    rows, used = [], set()
    for i, b in enumerate(boxes):
        if i in used or (b[3] - b[1]) > .2 * H or (b[2] - b[0]) > .3 * W:
            continue
        row = [j for j, o in enumerate(boxes) if j not in used and abs(o[1] - b[1]) < .02 * H and abs(o[3] - b[3]) < .02 * H
               and abs((o[2] - o[0]) - (b[2] - b[0])) < .2 * (b[2] - b[0])]
        if len(row) >= 3:
            xs = sorted(row, key=lambda j: boxes[j][0])
            gaps = [boxes[xs[k + 1]][0] - boxes[xs[k]][2] for k in range(len(xs) - 1)]
            if max(gaps) < .05 * W:  # side by side, nothing between them
                used.update(row)
                rows.append(tuple(f(boxes[j][n] for j in row) for f, n in ((min, 0), (min, 1), (max, 2), (max, 3))))
    return [b for i, b in enumerate(boxes) if i not in used] + rows


def _glyph_rail(img, x_cards=None):
    """An icon rail drawn as plain glyphs (no round buttons: the weather shot): in the left band, 4+ icon-sized
    marks one under another in one column. A text menu's icon and word run together into a wide mark, no rail.
    Only marks left of every card count (the fitshop shot's round country flags in a list were read as a rail)."""
    import cv2
    import numpy as np
    H, W = img.shape[:2]
    band = img[:, :int(.16 * W)]
    edges = cv2.Canny(cv2.cvtColor(band, cv2.COLOR_RGB2GRAY), 40, 120)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
    n, _, stats, cent = cv2.connectedComponentsWithStats(edges, connectivity=8)
    marks = [(cent[i][0], cent[i][1]) for i in range(1, n)
             if .02 * W <= stats[i][2] <= .07 * W and .02 * W <= stats[i][3] <= .07 * W and .55 <= stats[i][2] / stats[i][3] <= 1.8
             and (x_cards is None or stats[i][0] + stats[i][2] <= x_cards)]
    if len(marks) < 4:
        return False
    xs = sorted(x for x, _ in marks)
    best = max(len([x for x in xs if abs(x - c) < .02 * W]) for c in xs)
    col = [m for m in marks if abs(m[0] - sorted(xs)[len(xs) // 2]) < .02 * W]
    ys = sorted(y for _, y in col)
    spread = (ys[-1] - ys[0]) / H if len(ys) > 1 else 0
    return bool(best >= 4 and spread > .3)  # (a numpy bool would not go into JSON)


def _menu_column(img, x_cards):
    """A menu down the left drawn without a surface of its own (the smart-home shot: an icon and a word under it,
    Dashboard / Devices / Activity / Settings): left of every card, 4+ marks one under another in one column."""
    import cv2
    import numpy as np
    H, W = img.shape[:2]
    if x_cards < .08 * W:
        return False
    band = img[:, :int(x_cards) - 2]
    edges = cv2.Canny(cv2.cvtColor(band, cv2.COLOR_RGB2GRAY), 40, 120)
    edges = cv2.dilate(edges, np.ones((5, 9), np.uint8), iterations=1)
    n, _, stats, cent = cv2.connectedComponentsWithStats(edges, connectivity=8)
    marks = [(cent[i][0], cent[i][1]) for i in range(1, n)
             if .012 * W <= stats[i][2] <= x_cards and .01 * H <= stats[i][3] <= .12 * H]
    for cx, _ in marks:
        col = sorted(y for x, y in marks if abs(x - cx) < .025 * W)
        if len(col) >= 4 and (col[-1] - col[0]) > .3 * H:
            return True
    return False


def _rail(small, W, H):
    """An icon rail: 4+ round buttons one under another near the left edge (the cooking shot's menu)."""
    left = [b for b in small if (b[0] + b[2]) / 2 < .15 * W and abs((b[2] - b[0]) - (b[3] - b[1])) < .4 * (b[2] - b[0])]
    if len(left) < 4:
        return False
    xs = sorted((b[0] + b[2]) / 2 for b in left)
    return xs[-1] - xs[0] < .04 * W or len([x for x in xs if abs(x - xs[len(xs) // 2]) < .02 * W]) >= 4


def _open_sections(arr, cards_, W, H, page=None):
    """Sections with no card surface (titles, lists and charts straight on the page, apart only by white space):
    the bands of the page below the first card that no card covers, cut at their wide empty gutters. The fitshop
    shot's "Top destinations / Sales Analytics / Product sales" came out as six pieces of their insides."""
    import numpy as np
    if not cards_:
        return []
    flat = arr.reshape(-1, 3)
    keys, counts = np.unique((flat // 8).astype(np.int32) @ np.array([1024, 32, 1]), return_counts=True)
    k = keys[counts.argmax()]
    bg = np.array([k // 1024, k // 32 % 32, k % 32]) * 8 + 4  # the page's own colour: its most common one
    ink = np.abs(arr.astype(np.int32) - bg).max(axis=2) > 24
    px0, py0, px1, py1 = (int(v) for v in (page or (0, 0, W, H)))
    m = max(2, int(.012 * W))  # outside the page, and the window's own border round it, is no content
    ink[:, :px0 + m] = ink[:, max(0, px1 - m):] = False
    ink[:py0] = ink[max(0, py1 - m):] = False
    covered = np.zeros(H, bool)
    for b in cards_:  # a card and its soft shadow just under it
        covered[int(b[1]):min(H, int(b[3] + .012 * H))] = True
    start = int(min(b[1] for b in cards_))  # above the first card: the top bar and heading (read on their own)
    bands, y = [], start
    while y < H:
        if covered[y]:
            y += 1
            continue
        y2 = y
        while y2 < H and not covered[y2]:
            y2 += 1
        if y2 - y >= .15 * H:
            bands.append((y, y2))
        y = y2
    out = []
    for y0, y1 in bands:
        cols = ink[y0:y1].mean(axis=0)
        x, gap = 0, max(6, int(.022 * W))
        chunks, cx = [], None
        empty = 0
        for x in range(W):
            if cols[x] > .002:
                if cx is None:
                    cx = x
                empty, last = 0, x
            elif cx is not None:
                empty += 1
                if empty >= gap:
                    chunks.append((cx, last + 1))
                    cx, empty = None, 0
        if cx is not None:
            chunks.append((cx, last + 1))
        # a strip too narrow to be a section (a table's number columns, as far from its names as the sections are
        # from each other) joins the nearest one beside it
        while len(chunks) > 1:
            n = next((i for i, c in enumerate(chunks) if c[1] - c[0] < .12 * W), None)
            if n is None:
                break
            left = chunks[n][0] - chunks[n - 1][1] if n > 0 else None
            right = chunks[n + 1][0] - chunks[n][1] if n + 1 < len(chunks) else None
            j = n - 1 if right is None or (left is not None and left <= right) else n + 1
            a, b = sorted((n, j))
            chunks[a:b + 1] = [(chunks[a][0], chunks[b][1])]
        for x0, x1 in chunks:
            rows = np.where(ink[y0:y1, x0:x1].mean(axis=1) > .002)[0]
            if not len(rows):
                continue
            box = (x0, y0 + rows[0], x1, y0 + rows[-1] + 1)
            if box[2] - box[0] >= .12 * W and box[3] - box[1] >= .15 * H:
                out.append(tuple(int(v) for v in box))
    return out


def _titled_groups(content, surf, W, H):
    """An open panel's parts as one card: a thin title strip with no background of its own and the borderless pieces
    right under it in its column (a "Report on this week" title, its donut and its two-column legend were four
    cards, 2026-11-12). Pieces with their own background (cards) are never joined: they are cards themselves."""
    surfaces = {tuple(int(v) for v in b) for b in surf}
    own = lambda b: tuple(int(v) for v in b) in surfaces  # noqa: E731
    boxes = sorted(content, key=lambda b: (b[1], b[0]))
    used, out = set(), []
    for i, t in enumerate(boxes):
        if i in used or own(t) or (t[3] - t[1]) >= .06 * H:
            continue
        grp, bottom = [i], t[3]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            if j in used or own(b) or b[1] < t[3] - .005 * H:
                continue
            if not (t[0] - .03 * W <= b[0] < t[0] + .3 * W) or b[1] - bottom > .035 * H:
                continue
            if (b[3] - b[1]) < .06 * H and abs(b[0] - t[0]) < .02 * W:
                break  # the next title: its own card
            grp.append(j)
            bottom = max(bottom, b[3])
        if len(grp) >= 2:
            used.update(grp)
            g = [boxes[k] for k in grp]
            out.append(type(t)((min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))))
    return [b for k, b in enumerate(boxes) if k not in used] + out


def _join_halves(content):
    """Two pieces side by side that overlap and cover the same height are one card (the school banner: its flat
    left half by the pixels, its 3D picture on the right by the element model)."""
    out = list(content)
    joined = True
    while joined:
        joined = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                ov_x = min(a[2], b[2]) - max(a[0], b[0])
                ov_y = min(a[3], b[3]) - max(a[1], b[1])
                if ov_x > 0 and ov_y >= .8 * min(a[3] - a[1], b[3] - b[1])                         and ov_x < .5 * min(a[2] - a[0], b[2] - b[0]):  # (one inside the other is not this)
                    out[i] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    del out[j]
                    joined = True
                    break
            if joined:
                break
    return out


def _holds_items(box, kids, whole=None):
    """A card with items drawn in it (the Jiron shot's week calendar: 3+ small event blocks, each a few % of it), not
    a panel round cards (its cards are big parts of it: the school shot's four number tiles are a quarter each)."""
    area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
    small = [k for k in kids if (k[2] - k[0]) * (k[3] - k[1]) < .12 * area]
    if whole and area > .4 * whole:  # a whole board of small cards (ClothIQ's main area) is a panel, not one card
        return False
    return len(kids) >= 3 and len(small) >= 2 * len(kids) / 3


def _drop_top_bar(content, W, H, page_top=0, arr=None):
    """The page's top bar drawn as a strip of its own (search + menu + icons on white: the Boltz and Ethan Brooks
    shots) is no card: the topmost box when it is thin, wide and at the page's top. The short pieces right under it
    (the heading's own controls: Boltz's weather + "Filter Periode", Ethan's name line) go with it. The top bar is
    read on its own from the page's top down to the first card left."""
    if len(content) < 3:
        return content
    top = min(content, key=lambda b: b[1])
    span = max(b[2] for b in content) - min(b[0] for b in content)
    # thin (Ethan's bar ran into its name line: .114 of the shot), wide, right at the page's top
    if not ((top[3] - top[1]) < .125 * H and (top[2] - top[0]) >= .45 * span and top[1] - page_top < .08 * H):
        return content
    if arr is not None:  # a coloured surface there is a banner (the school shot's blue one), not a bar of controls
        c, _ = _mode(arr[int(top[1]):int(top[3]), int(top[0]):int(top[2])].reshape(-1, 3).astype(int))
        if int(c.max()) - int(c.min()) > 40:
            return content
    rest = [b for b in content if b != top]
    head = [b for b in rest if (b[3] - b[1]) < .07 * H and b[1] < top[3] + .06 * H]
    left = [b for b in rest if b not in head]
    return left if len(left) >= 2 else rest


def _page_frame(arr):
    """Where the page itself is in a shot (fractions x0, y0, x1, y1), or None when it fills the picture. Dribbble
    shots put the page on a backdrop (a plain colour around it) and often in a browser window: its bar (the three
    round window buttons, the address) is no part of the page. The fitshop shot: the bar + menu + heading were read
    as one card, and the "top bar" read was the empty backdrop above the window."""
    import numpy as np
    H, W = arr.shape[:2]
    a = arr.astype(np.int32)
    b = max(4, int(.012 * min(H, W)))
    x0, y0, x1, y1 = 0, 0, W, H
    # a backdrop: smooth all round (one colour or a soft gradient), its pixels like their neighbours along each edge
    sides = [a[:b].mean(axis=0), a[-b:].mean(axis=0), a[:, :b].mean(axis=1), a[:, -b:].mean(axis=1)]
    # no jump anywhere along it (a window's edge crossing a side is a jump; a gradient never is)
    smooth = [np.abs(np.diff(s, axis=0)).max() < 10 for s in sides]  # top, bottom, left, right
    # a smooth side unlike the top one is the page itself running off the shot (a white page end on a blue backdrop)
    # (compared where the two sides meet: a gradient backdrop is another colour at the far side, not at the corner)
    k = max(3, int(.05 * min(H, W)))
    near = lambda p, q: np.abs(p.mean(axis=0) - q.mean(axis=0)).max() < 24  # noqa: E731
    corner = [True, near(sides[1][:k], sides[2][-k:]), near(sides[2][:k], sides[0][:k]), near(sides[3][:k], sides[0][-k:])]
    smooth = [ok and c for ok, c in zip(smooth, corner)]
    # the window may run off one edge of the shot (the school and Boltz shots end mid-page): three backdrop sides
    # with the top one among them are enough; the open side is the page's
    if smooth[0] and sum(smooth) >= 3:
        # each pixel against the backdrop beside it: its row's ends and its column's ends (a gradient changes across
        # the picture; a window on it differs from all of them)
        far = lambda ref: np.abs(a - ref).max(axis=2) > 12  # noqa: E731  (the school shot's page is 22 off its backdrop)
        refs = [sides[0][None, :, :], sides[1][None, :, :], sides[2][:, None, :], sides[3][:, None, :]]
        off = np.ones((H, W), bool)
        for ok, ref in zip(smooth, refs):
            if ok:
                off &= far(ref)
        rows, cols = np.where(off.mean(axis=1) > .3)[0], np.where(off.mean(axis=0) > .3)[0]
        if len(rows) and len(cols):
            fx0, fy0, fx1, fy1 = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1
            if .4 < (fx1 - fx0) * (fy1 - fy0) / (W * H) < .97:
                x0, y0, x1, y1 = fx0, fy0, fx1, fy1
    # a browser window's bar: red, amber and green dots side by side near the page's top left corner
    import cv2
    top = arr[y0:y0 + int(.1 * (y1 - y0)), x0:x0 + int(.15 * (x1 - x0))]
    if top.size:
        hsv = cv2.cvtColor(np.ascontiguousarray(top), cv2.COLOR_RGB2HSV)
        hue, sat, val = hsv[..., 0].astype(int), hsv[..., 1], hsv[..., 2]
        strong = (sat > 120) & (val > 150)
        ys = []
        for lo, hi in ((0, 8), (12, 30), (40, 80)):  # red, amber, green (OpenCV hue is 0-179)
            m = strong & (hue >= lo) & (hue <= hi)
            if lo == 0:
                m |= strong & (hue >= 170)
            if m.sum() < 6:
                ys = []
                break
            ys.append(np.where(m)[0].mean())
        if ys and max(ys) - min(ys) < .02 * (y1 - y0):
            y0 += int(2 * (sum(ys) / 3) + 2)  # the dots sit in the middle of the bar
    if (x0, y0, x1, y1) == (0, 0, W, H):
        return None
    return x0 / W, y0 / H, x1 / W, y1 / H


def cards(src, width=1000, least=2):
    """The reference's card grid: {"sidebar": bool, "tree": the XY-cut of the content cards (fractions of the
    picture), "boxes": [(x0, y0, x1, y1) fractions], reading order = the tree's leaves}; None when no grid."""
    import numpy as np
    from PIL import Image
    if str(src).startswith("data:"):
        im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1])))
    else:
        im = Image.open(src)
    im = im.convert("RGB")
    im = im.resize((width, max(1, round(im.height * width / im.width))))
    arr = np.asarray(im)
    H, W = arr.shape[:2]
    # where the page is (not the backdrop round it, not a browser window's bar): the picture itself is not cut to it
    # (the cooking shot's cards fell apart into 19 pieces when it was), the page's edges are used below
    frame = _page_frame(arr)
    fpx = (frame[0] * W, frame[1] * H, frame[2] * W, frame[3] * H) if frame else (0, 0, W, H)
    raw = _surfaces(arr)
    if frame:  # the page's own background inside the window (as wide as the page: its top with the menu and heading,
        # its bottom round open sections), no card
        raw = [b for b in raw if not (b[0] <= fpx[0] + .012 * W and b[2] >= fpx[2] - .012 * W)]
    if len(raw) < least:
        return None
    import cv2
    ink = cv2.Canny(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY), 40, 120)
    inked = lambda b: ink[b[1]:b[3], b[0]:b[2]].mean() / 255  # noqa: E731
    # a strip at the bottom edge with little drawn in it: the board's decoration (a desk); a card cut by the picture's
    # edge (the Travelgo shot's "Latest customer review": a photo, words, stars) stays
    def outside(b):  # past the board the other boxes make (the smart-home shot's purple corner circle)
        rest = [o for o in raw if o is not b]
        return bool(rest) and (b[2] > max(o[2] for o in rest) + .02 * W or b[0] < min(o[0] for o in rest) - .02 * W)
    raw = [b for b in raw if not (b[3] >= .97 * H and b[1] > .82 * H and (inked(b) < .02 or outside(b)))]
    raw = _merge_stacks(raw, W, H)  # list rows one under another: one card
    # the menu down the left: a tall narrow box there, or several boxes inside a left band no other box enters
    side = [b for b in raw if (b[2] - b[0]) < .2 * W and (b[3] - b[1]) > .5 * H and b[0] < .2 * W]
    if not side:
        band = max([b[2] for b in raw if b[2] < .24 * W] + [0])
        left = [b for b in raw if b[2] <= band]
        if band and len(left) >= 2 and not any(b[0] < band < b[2] for b in raw) and sum(b[3] - b[1] for b in left) > .4 * H:
            side = left
    sx = max([b[2] for b in side] + [0])  # anything inside the menu's band (its logo, its footer) is the menu too
    content = [b for b in raw if b not in side and not (side and b[2] <= sx + .01 * W)]
    # overlapping finds of one card (a JPEG's noise splits a card into parts that overlap): the bigger one stays;
    # with overlaps the cut found no gutter and stacked every card full width (the weather shot, a real run)
    area = lambda b: (b[2] - b[0]) * (b[3] - b[1])  # noqa: E731
    inter = lambda a, b: max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))  # noqa: E731
    # a box holding two or more others is a panel around cards: it goes, the cards stay
    content = [b for b in content if len([o for o in content if o != b and inter(o, b) >= .7 * area(o)]) < 2
               or _holds_items(b, [o for o in content if o != b and inter(o, b) >= .7 * area(o)], W * H)]
    holders = [b for b in content if _holds_items(b, [o for o in content if o != b and inter(o, b) >= .7 * area(o)], W * H)]
    content = [b for b in content if not any(h != b and inter(b, h) >= .7 * area(b) for h in holders)]
    kept = []
    for b in sorted(content, key=lambda b: -area(b)):  # the rest overlapping a bigger one by 30%+: a part of that card
        if all(inter(b, k) < .3 * area(b) for k in kept):
            kept.append(b)
    content = kept
    # a header strip above every card (a search box, "Download app"), one or two in its line: the page's top bar
    tall = [b for b in content if (b[3] - b[1]) >= .1 * H]
    if len(content) > 2 and tall:
        top = min(b[1] for b in tall)
        strips = [b for b in content if (b[3] - b[1]) < .1 * H and b[3] <= top + .01 * H]
        if 0 < len(strips) <= 2:
            content = [b for b in content if b not in strips]
    content = _grow(arr, content)
    # nothing drawn in it: no card (the Travelgo shot's pink arc above the board was read as a "Room temperature" gauge)
    content = [b for b in content if inked(b) >= .008]
    _element_grid.found = None
    surf = list(content)
    content = _with_elements(im, content, W, H, sx if side else min(b[0] for b in content) - .02 * W)
    opened = _open_sections(arr, surf, W, H, fpx)
    if opened:  # the open sections stand for the pieces found inside them
        within = lambda b, s: max(0, min(b[2], s[2]) - max(b[0], s[0])) * max(0, min(b[3], s[3]) - max(b[1], s[1])) \
            >= .6 * (b[2] - b[0]) * (b[3] - b[1])  # noqa: E731
        content = [b for b in content if not any(within(b, s) for s in opened)] + opened
    content = _tile_rows(content, W, H)
    content = _join_halves(content)
    content = _drop_top_bar(content, W, H, fpx[1], arr)
    content = _titled_groups(content, surf, W, H)  # (after the top bar is gone: a heading row is no title of a card)
    if len(content) < least:
        return None
    boxes = [(b[0] / W, b[1] / H, b[2] / W, b[3] / H) for b in content]
    tree = _cut(boxes, list(range(len(boxes))))
    order = []

    def walk(n):
        if "leaf" in n:
            order.append(n["leaf"])
        else:
            for c in n["children"]:
                walk(c)
    walk(tree)
    remap = {old: new for new, old in enumerate(order)}

    def renum(n):
        return {"leaf": remap[n["leaf"]], "box": n["box"]} if "leaf" in n else dict(n, children=[renum(c) for c in n["children"]])
    rail = bool(getattr(_surfaces, "rail", False)) or _glyph_rail(arr, min(b[0] for b in content))
    menu = bool(side) or rail or _menu_column(arr, min(b[0] for b in content))
    side_color = None
    x0c = min(b[0] for b in content)
    if menu and x0c > .14 * W:  # the band just left of the cards: the menu's own colour
        band = arr[int(.2 * H):int(.8 * H), int(x0c - .12 * W):int(x0c - .02 * W)].reshape(-1, 3)
        med = np.median(band, axis=0)
        if _lum(tuple(int(v) for v in med)) < .3:
            side_color = "#%02x%02x%02x" % tuple(int(v) for v in med)
    found = getattr(_element_grid, "found", None)
    grid_cells = {}  # card number -> how many alike items in rows and columns it holds (a product grid)
    for k, b in enumerate(boxes[i] for i in order):
        if found and _iou(tuple(v * s for v, s in zip(b, (W, H, W, H))), found[0]) > .6:
            grid_cells[k] = found[1]
    # the menu's own strip (read on its own for its words): from the page's left edge to just before the cards
    side_box = ((fpx[0] / W, fpx[1] / H, max(fpx[0] / W + .02, x0c / W - .005), fpx[3] / H)
                if menu and x0c - fpx[0] > .06 * W else None)
    return {"sidebar": menu, "rail": rail, "side_color": side_color, "grid_cells": grid_cells, "tree": renum(tree),
            "boxes": [boxes[i] for i in order], "page_top": frame[1] if frame else None, "side_box": side_box}


def bands(src, known=(), side_box=None, gap=.012):
    """The picture's parts outside its cards (a title row with a search box, a profile strip, a sidebar's user card,
    a badge): the cards blanked out, what is left is cut where a row of the picture is empty; the sidebar apart from
    the page. Each a (x0, y0, x1, y1) box in fractions; the ones mostly under the cards are left out."""
    import cv2
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1]))) if str(src).startswith("data:") else Image.open(src)
    im = im.convert("RGB")
    W, H = im.size
    gray = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    ink = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 20, 60) > 0
    for b in known:
        ink[int(b[1] * H):int(b[3] * H) + 1, int(b[0] * W):int(b[2] * W) + 1] = False
    sx = int(side_box[2] * W) if side_box else 0
    out = []
    for x0, x1 in ([(0, sx), (sx + 1, W)] if sx else [(0, W)]):
        part = ink[:, x0:x1]
        rows = part.sum(1) > 2
        y, n = 0, len(rows)
        while y < n:
            if not rows[y]:
                y += 1
                continue
            y0 = last = y
            while y < n and (rows[y] or y - last < gap * H):
                if rows[y]:
                    last = y
                y += 1
            cols = np.where(part[y0:last + 1].sum(0) > 0)[0]
            if len(cols) and last - y0 > .012 * H and cols[-1] - cols[0] > .04 * W:
                box = ((x0 + cols[0]) / W, y0 / H, (x0 + cols[-1]) / W, last / H)
                area = (box[2] - box[0]) * (box[3] - box[1])
                under = sum(max(0, min(box[2], k[2]) - max(box[0], k[0])) * max(0, min(box[3], k[3]) - max(box[1], k[1])) for k in known)
                if under < .5 * area:
                    out.append(tuple(round(float(v), 4) for v in box))
    return out


def crop(src, box, pad=.006):
    """A card of the reference as a PNG data URL (for the vision model to read it alone)."""
    from PIL import Image
    if str(src).startswith("data:"):
        im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1])))
    else:
        im = Image.open(src)
    im = im.convert("RGB")
    w, h = im.size
    c = im.crop((max(0, int((box[0] - pad) * w)), max(0, int((box[1] - pad) * h)), min(w, int((box[2] + pad) * w)),
                 min(h, int((box[3] + pad) * h))))
    c.thumbnail((768, 768))
    buf = io.BytesIO()
    c.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---- each card of the reference, read on its own (Step 2) -------------------------------------------------

# the parts of one item of a list card (its row template): what the row shows, left to right
ROW_KINDS = ("photo", "photo with words on it", "icon", "title", "text", "meta", "number", "price", "pill", "progress bar", "ring",
             "avatar", "stars", "button", "arrow", "stepper", "checkbox", "edit", "delete")


def clean_item(raw):
    """A row template from the 4B: known parts, each once (it repeats them), a title in it, at most 6."""
    raw = [k for k in raw if k in ROW_KINDS] if isinstance(raw, list) else []
    # small facts with icons ("#4587 · ⏱ Wait 9 min") the 4B read as "number, number, icon" (the D.CC activity rows):
    # an icon after the title, or a number said twice, is meta
    seen_title = False
    fixed = []
    for k in raw:
        seen_title = seen_title or k == "title"
        if (k == "icon" and seen_title) or (k == "number" and raw.count("number") > 1):
            k = "meta"
        fixed.append(k)
    out = []
    for k in fixed:
        if k not in out:
            out.append(k)
    if out and "title" not in out:
        pos = next((n + 1 for n, k in enumerate(out) if k in ("photo", "icon", "avatar")), 0)
        out.insert(pos, "title")
    return out[:6] if len(out) >= 2 else []


def item_words(row):
    """The row template in words for the page's plan: which fields each item needs."""
    need = {"photo": "icon", "photo with words on it": "icon", "icon": "icon", "title": "title", "text": "text",
            "meta": "meta = 2-3 short facts (a time, an id, a place)", "number": "value", "price": "value + unit (the price)",
            "pill": "badge = a status word (Open, Completed, Pending...)", "progress bar": "value = a percent", "ring": "value = a percent",
            "avatar": "title = a person's name", "stars": "value = rating 1-5", "button": "", "arrow": "",
            "stepper": "meta = [how many, e.g. \"1\"]", "delete": ""}
    return ", ".join(dict.fromkeys(need[k] for k in row if need.get(k)))


def card_schema():
    import widgets
    return {"type": "object", "properties": {
        "widget": {"type": "string", "enum": list(widgets.WIDGETS) + ["custom"]},
        "title": {"type": "string", "maxLength": 40},
        "what": {"type": "string", "maxLength": 110},
        "count": {"type": "integer", "minimum": 0, "maximum": 12},
        "icons": {"type": "array", "items": {"type": "string", "maxLength": 20}, "maxItems": 6},
        "chart": {"type": "string", "enum": ["yes", "no"]},
        "arrangement": {"type": "string", "enum": ["rows one under another", "columns side by side", "grid", "one big item"]},
        # how the card is drawn inside (the D.CC shot: striped bars, a progress bar under each number, an arrow and a
        # "This Month" picker on each card, status pills, photos): easy yes / no looks, the widget draws them
        "header": {"type": "string", "enum": ["plain", "arrow button", "dropdown", "dropdown and arrow"]},
        "progress_bar": {"type": "string", "enum": ["yes", "no"]},
        "bars": {"type": "string", "enum": ["none", "plain", "striped", "one highlighted"]},
        "boxes": {"type": "string", "enum": ["yes", "no"]},
        "status_pills": {"type": "string", "enum": ["yes", "no"]},
        "photos": {"type": "string", "enum": ["yes", "no"]},
        "item": {"type": "array", "maxItems": 7, "items": {"type": "string", "enum": list(ROW_KINDS)}},
        "tone": {"type": "string", "enum": ["plain", "tinted", "filled with the main colour", "photo background"]},
        "blocks": {"type": "array", "minItems": 1, "maxItems": 7, "items": {"type": "string", "enum": list(widgets.BLOCKS)}},
        "tiles": {"type": "integer", "minimum": 0, "maximum": 12}},
        "required": ["widget", "title", "what", "count", "icons", "chart", "arrangement", "header", "progress_bar", "bars",
                     "boxes", "status_pills", "photos", "item", "tone", "blocks", "tiles"]}


TOP_ICONS = ("search", "notifications", "messages", "mail", "favorites", "cart", "settings", "help", "user", "language", "date")


def top_schema():
    """The strip above the reference's cards, read on its own (crop): a yes / no for each thing, so the 4B can't
    copy the whole list (a real run gave the cooking shot a search, bell, chat, mail, heart, cart, gear and ? it
    does not have), and the shape of its heading: a greeting line, a big heading, a row of chips."""
    return {"type": "object", "properties": dict(
        {k: {"type": "string", "enum": ["yes", "no"]} for k in TOP_ICONS},
        heading={"type": "string", "maxLength": 80},
        greeting={"type": "string", "enum": ["yes", "no"]},
        buttons={"type": "integer", "minimum": 0, "maximum": 4},
        chips={"type": "integer", "minimum": 0, "maximum": 8}),
        "required": list(TOP_ICONS) + ["heading", "greeting", "buttons", "chips"]}


TOP_PROMPT = ("You look at the TOP strip of a web page (above its cards). For each thing answer yes ONLY when you clearly "
              "see it there: search (a search box), notifications (a bell), messages (a chat bubble), mail (an envelope), "
              "favorites (a heart), cart, settings (a gear), help (a ? icon), user (a person's photo or name), language "
              "(ONE small \"EN\" picker; a row of several flags with words is chips, not this), date (today's date). heading: "
              "the biggest words at the top, as written (\"Dashboard\", \"What dish do you want to cook?\"), \"\" when "
              "none. greeting: a small line like \"Hello, John\" above it? buttons: how many buttons with words (\"Hold "
              "Sale\", \"Download App\"), not chips? chips: how many round chips / pill buttons with "
              "a word each sit in one row there (cuisines with flags, categories, room tabs); 0 when none.")


SIDE_SCHEMA = {"type": "object", "properties": {
    "items": {"type": "array", "maxItems": 16, "items": {"type": "object", "properties": {
        "label": {"type": "string", "maxLength": 24}, "group": {"type": "string", "maxLength": 20}},
        "required": ["label", "group"]}},
    "active": {"type": "string", "maxLength": 24}},
    "required": ["items", "active"]}
SIDE_PROMPT = ("You look at the LEFT MENU of a web page (a cut-out of it). List its menu entries top to bottom, each "
               "with the exact words written on it (label). group = the small heading written above that entry's "
               "block (like MENU, MAIN, OTHER, FINANCE), \"\" when there is none. active = the label of the entry that "
               "is highlighted (a filled or coloured background), \"\" if none. Only words you can read in the picture; "
               "leave out the logo / app name, a person's name and e-mail, and buttons at the bottom. "
               'Answer {"items": [{"label": "...", "group": "..."}], "active": "..."}.')


def side_messages(image):
    return [{"role": "system", "content": SIDE_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": "The left menu:"},
                                         {"type": "image_url", "image_url": {"url": image}}]}]


def clean_side(raw, brand=""):
    """The menu's entries [{"label", "group", "active"}] as read: each once, short, not the brand; [] when the
    read is unusable (fewer than 3 entries: an icon rail has no words to read)."""
    raw = raw if isinstance(raw, dict) else {}
    out, seen = [], set()
    for it in raw.get("items") or []:
        if not isinstance(it, dict):
            continue
        label = " ".join(str(it.get("label") or "").split())[:24]
        key = label.lower()
        if not label or key in seen or (brand and key == brand.lower()) or "@" in label or not re.search(r"[A-Za-z]", label):
            continue
        seen.add(key)
        group = " ".join(str(it.get("group") or "").split())[:20]
        out.append({"label": label, "group": group if group.lower() != key else ""})
    active = " ".join(str(raw.get("active") or "").split()).lower()
    for it in out:
        it["active"] = bool(active) and it["label"].lower() == active
    return out[:14] if len(out) >= 3 else []


def top_messages(image):
    return [{"role": "system", "content": TOP_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": "The top of the page:"},
                                         {"type": "image_url", "image_url": {"url": image}}]}]


def clean_top(raw):
    """(top bar bits in the order a bar shows them, the heading's shape {"big", "greeting", "chips"})."""
    raw = raw if isinstance(raw, dict) else {}
    seen = [k for k in TOP_ICONS if raw.get(k) == "yes"]
    if len(seen) >= 8:  # every thing "seen": the list was copied, not read
        seen = []
    words = len(str(raw.get("heading") or "").split())  # its shape only (the words are the reference's, not the page's)
    chips = raw.get("chips") if isinstance(raw.get("chips"), int) else 0
    if chips >= 3 and "language" in seen:  # a row of flags with names is chips, not a language picker
        seen.remove("language")
    bits = ((["title"] if 1 <= words <= 3 else []) + [k for k in ("search",) if k in seen]
            + (["button"] if isinstance(raw.get("buttons"), int) and raw["buttons"] > 0 else []) + [k for k in seen if k != "search"])
    head = {"big": words >= 4, "greeting": raw.get("greeting") == "yes", "chips": max(0, min(8, chips))}
    return bits, head


def card_prompt():
    import widgets
    looks = "\n".join(f"- {k}: {v}" for k, v in widgets.LOOKS.items())
    return ("You look at ONE card cut from a dashboard screenshot and say which widget it is, so M42 can draw the same "
            "kind of card. widget: the one from this list that matches what you SEE (custom only when none does):\n" + looks +
            "\ntitle: the card's heading as written (or a short name). what: what it shows, concretely (how many rows / "
            "tiles / lines, what the numbers are about). count: how many items, rows, tiles or series it has. icons: "
            "what its icons show, one word each (calendar, bookmark, login, fan, snow...). chart: does it draw a graph, a "
            "curve or bars? arrangement: how its items sit: rows one under another, columns side by side, a grid, or "
            "one big item. header: what sits right of the card's title: nothing, a small arrow button (↗), a "
            "dropdown (\"This Month ▾\"), or both. progress_bar: a bar under a number showing how full it is? bars: the "
            "chart's or list's bars: none, plain, striped / hatched, or all pale with one highlighted. boxes: is each "
            "number or row in its own tinted box? status_pills: small coloured word pills (Completed, Pending, Open)? "
            "photos: are there photos (food, places, people) in it? item: when the card is a list or a set of alike items, "
            "the parts of ONE item from left to right (photo, photo with words on it, icon, title, text, meta = small facts "
            "with icons like time or an id, number, price, pill, progress bar, ring, avatar, stars, button, arrow, stepper "
            "= a - number + picker, delete = a bin icon); [] when "
            "the card has no alike items. tone: the card's background: plain (white / light), tinted (a pale colour), filled "
            "with the main colour (a coloured banner), or a photo behind its words. blocks: what the card is made of, top to "
            "bottom, as you SEE it (a round dish photo beside its name, then a grid of 6 ingredient tiles, then a button: "
            "round photo, heading, tile grid, button; a weekly report: heading, date range, donut, legend; a promo: big "
            "text, text, button, cut-out person photo). tiles: how many tiles its tile grid has (0 when none).")


def card_messages(image, kind=""):
    return [{"role": "system", "content": card_prompt()},
            {"role": "user", "content": [{"type": "text", "text": "The card" + (f" (from a {kind} page)" if kind else "") + ":"},
                                         {"type": "image_url", "image_url": {"url": image}}]}]


def clean_card(raw):
    import widgets
    raw = raw if isinstance(raw, dict) else {}
    w = raw.get("widget") if raw.get("widget") in widgets.WIDGETS or raw.get("widget") == "custom" else "custom"
    # the easy questions check the hard one (a 4B picking 1 of 56 widgets took "Live conditions", a curve over
    # three numbers, for metric_pair and a list of searched places for forecast columns: the weather shot)
    chart = raw.get("chart") == "yes"
    arr = str(raw.get("arrangement") or "")
    if chart and w in ("metric_pair", "kpi_tiles", "hbars", "rings", "weather_now", "custom"):
        w = "chart_stats"
    elif arr.startswith("rows") and w in ("forecast", "hourly", "image_cards", "category_chips", "kpi_tiles"):
        w = "list_thumbs"
    elif arr.startswith("columns") and w in ("list_thumbs", "agenda", "timeline", "notifications"):
        w = "image_cards"  # (side-by-side items are no list of rows: the model's own two answers disagree)
    # (no word rules on the model's description any more, 2026-11-12: "wherever there is thinking, the 4B decides"; a
    # card it can't name with one widget is drawn from the blocks it lists: is_composed below)
    what = str(raw.get("what") or "")
    count = max(0, min(12, int(raw.get("count") or 0))) if str(raw.get("count") or "0").isdigit() else 0
    look = {"header": {"arrow button": "arrow", "dropdown": "dropdown", "dropdown and arrow": "both"}.get(raw.get("header"), ""),
            "progress": raw.get("progress_bar") == "yes", "bars": raw.get("bars") if raw.get("bars") in ("striped", "one highlighted") else "",
            "boxes": raw.get("boxes") == "yes", "pills": raw.get("status_pills") == "yes", "photos": raw.get("photos") == "yes"}
    look["row"] = clean_item(raw.get("item"))
    blocks = [b for b in dict.fromkeys(raw.get("blocks") or []) if b in widgets.BLOCKS][:7]
    if not chart and set(blocks) & CHART_BLOCKS:
        # the model's own "no chart" wins over the blocks it listed (a list of recent orders with status pills came
        # with "donut, legend" and was drawn as a donut, 2026-11-12): its rows, when it said what each row holds
        blocks = [b for b in blocks if b not in CHART_BLOCKS]
        if look["row"] and not set(blocks) & {"rows", "tile grid", "table", "chips"}:
            blocks.append("rows")
    tone =raw.get("tone") if raw.get("tone") in ("tinted", "filled with the main colour", "photo background") else ""
    if tone and "avatars" in blocks and not set(blocks) & {"rows", "tile grid", "table", "chips"}:
        # one person on a coloured banner is its picture, not a list of people (a promo's woman was "avatars")
        blocks = [("cut-out person photo" if b == "avatars" else b) for b in blocks]
    if blocks and raw.get("title") and not set(blocks) & {"heading", "big text"}:
        # the card has a title the blocks left out: it heads the card (a banner's big words)
        blocks.insert(0, "big text" if tone == "filled with the main colour" else "heading")
    if blocks:  # (kept for every card: a flat strip of only a title is a heading, shape_card)
        look["blocks"] = blocks
    one = str(raw.get("arrangement") or "").startswith("one") or str(raw.get("count") or "") in ("0", "1")
    if is_composed(w, blocks, tone, one):  # a card no single widget draws: drawn from its own blocks (widgets.w_composed)
        look.update(blocks=blocks, tone=tone, tiles=max(0, min(12, int(raw.get("tiles") or 0))) if str(raw.get("tiles") or "0").isdigit() else 0,
                    was=w, photos=look.get("photos") or bool(set(blocks) & widgets.PHOTO_BLOCKS))
        w = "composed"
    if w in ("device_cards", "empty_state", "image_cards") and set(look["row"]) & {"price", "stepper", "delete"} and "photo with words on it" not in look["row"]:
        w = "list_thumbs"  # rows with a price, a - 1 + and a bin (the POS shot's cart) are a list, not devices with switches
    return {"widget": w, "look": {k: v for k, v in look.items() if v}, "title": " ".join(str(raw.get("title") or "").split())[:40],
            "what": " ".join(what.split())[:110],
            "count": count,
            "icons": [" ".join(str(i).split())[:20] for i in raw.get("icons") or [] if str(i).strip()][:6]}


CHART_BLOCKS = {"donut", "rings", "bars", "line chart", "legend"}
# what a widget must show to be that widget (a "calendar" with no month grid is a date range over a chart)
WIDGET_NEEDS = {"calendar": "month calendar", "upload": "upload box", "donut": "donut", "rings": "rings", "map_card": "map",
                "data_table": "table", "line_chart": "line chart", "area_chart": "line chart", "bar_chart": "bars", "hbars": "bars"}
BLOCK_FAMILY = {"photo": "media", "round photo": "media", "cut-out person photo": "media", "tile grid": "set", "rows": "set",
                "chips": "set", "avatars": "set", "table": "set", "donut": "chart", "rings": "chart", "bars": "chart",
                "line chart": "chart", "legend": "chart", "big number": "number", "progress bar": "number",
                "date range": "time", "month calendar": "time", "map": "map", "form fields": "form", "search box": "form",
                "upload box": "form"}


def is_composed(widget, blocks, tone, one=False):
    """True when no one widget draws the card: it mixes kinds of content (a photo and a grid of tiles; a date range
    and a donut), it is a coloured or photo banner, or the widget picked lacks the block that makes it that widget."""
    if not blocks:
        return False
    fams = {BLOCK_FAMILY[b] for b in blocks if b in BLOCK_FAMILY}
    if tone in ("filled with the main colour", "photo background") and widget not in ("kpi_tiles", "stats", "metric_pair"):
        return True
    if widget in WIDGET_NEEDS and WIDGET_NEEDS[widget] not in blocks:
        return True
    if len(fams - {"time"}) >= 2 or ("time" in fams and fams - {"time"} and "month calendar" not in blocks):
        return True
    if one and fams == {"media"}:  # one thing with its photo (a dish card: photo, name, a line, a time): a photo card,
        return True                # not a list of one that repeats the card's own title
    return widget == "custom" and bool(fams)


def side_card_box(src, side_box, bottom):
    """A card in the sidebar under its menu (a coloured "Share your recipe / Upload now" box, a profile, a promo):
    the lowest run of rows in the sidebar's column that differ clearly from its background, at least 7% of the
    picture tall, below the column's top 40%. (x0, y0, x1, y1) as fractions, or None."""
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1]))) if str(src).startswith("data:") else Image.open(src)
    im = im.convert("RGB")
    w, h = im.size
    x0, y0, x1 = side_box[0], side_box[1], side_box[2]
    y1 = max(bottom, side_box[3])
    a = np.asarray(im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))).astype(int)
    if a.shape[0] < 20 or a.shape[1] < 20:
        return None
    flat = a.reshape(-1, 3)
    vals, counts = np.unique(flat // 8, axis=0, return_counts=True)
    bg = vals[counts.argmax()] * 8 + 4
    diff = np.abs(a - bg).sum(axis=2) > 70
    rows = diff.mean(axis=1) > .2
    runs, start = [], None
    for i, on in enumerate(list(rows) + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append((start, i))
            start = None
    joined = []  # rows of one card broken by a white button or a line of text in it: one run
    for r in runs:
        if joined and r[0] - joined[-1][1] < .025 * h:
            joined[-1] = (joined[-1][0], r[1])
        else:
            joined.append(r)
    runs = joined
    H = a.shape[0]
    runs = [r for r in runs if r[0] > H * .4 and (r[1] - r[0]) >= .07 * h]
    if not runs:
        return None
    r0, r1 = runs[-1]
    cols = np.where(diff[r0:r1].mean(axis=0) > .3)[0]
    cx0, cx1 = (cols.min(), cols.max()) if cols.size else (0, a.shape[1] - 1)
    # a photo standing out above the card (a salad over the box) belongs to it: its run just above, close by
    above = [r for r in runs[:-1] if r0 - r[1] < .03 * h]
    if above:
        r0 = above[-1][0]
    return (x0 + cx0 / w, y0 + r0 / h, x0 + (cx1 + 1) / w, y0 + r1 / h)


READ_VERSION = 7  # bumped when the reading changes: older saved readings (and pages built from them) are read again
READS = Path(__file__).resolve().parent / "cache" / "ref-reads"
if os.environ.get("M42_MEMORY_DIR"):  # a test (or a separate profile): its own saved readings, not the app's
    READS = Path(os.environ["M42_MEMORY_DIR"]) / "ref-reads"


def fingerprint(src):
    """The picture's own fingerprint (its bytes), the same for the same picture however it is attached."""
    try:
        data = base64.b64decode(str(src).split(",", 1)[1]) if str(src).startswith("data:") else Path(src).read_bytes()
    except (OSError, ValueError, IndexError):
        return ""
    return hashlib.sha1(data).hexdigest()[:16]


def saved_read(src, what):
    """A reading of this picture made before ("brief" / "grid"), or None (2026-11-12: the same picture in the same
    folder was read card by card again, about 3 minutes)."""
    fp = fingerprint(src)
    f = READS / f"{fp}-{what}.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8")) if fp and f.exists() else None
    except (OSError, ValueError):
        return None
    return d.get("data") if isinstance(d, dict) and d.get("v") == READ_VERSION else None


def save_read(src, what, data):
    fp = fingerprint(src)
    if not fp or data is None:
        return
    try:
        READS.mkdir(parents=True, exist_ok=True)
        (READS / f"{fp}-{what}.json").write_text(json.dumps({"v": READ_VERSION, "data": data}, default=float), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass


def plain_card(src, box):
    """True when the card is drawn white / light grey (little colour in it: the school shot's number tiles), False
    for tinted tiles (Travelgo's, ClothIQ's): the picture's own pixels, not the vision model's guess."""
    import numpy as np
    from PIL import Image
    if str(src).startswith("data:"):
        im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1])))
    else:
        im = Image.open(src)
    im = im.convert("RGB")
    w, h = im.size
    a = np.asarray(im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))).astype(int)
    if not a.size:
        return False
    colour = (a.max(axis=2) - a.min(axis=2)) > 25
    return bool(colour.mean() < .12 and a.mean() > 215)


def shape_card(card, box, img_wh, cells=0):
    """The card's kind by its box, which the vision model can't see in a crop: a grid of alike items the element
    model found (the POS shot's 8 products, read as a list of rows) is a photo grid; a flat strip (5:1 or flatter:
    its category tabs, read as a list) is a row of chips."""
    w = (box[2] - box[0]) * img_wh[0]
    h = max(1e-6, (box[3] - box[1]) * img_wh[1])
    look = dict(card.get("look") or {})
    if cells:
        look.pop("row", None)
        return dict(card, widget="image_cards" if look.get("photos") or card["widget"] in ("list_thumbs", "image_cards") else "quick_actions",
                    count=cells, look=look)
    blocks = set((card.get("look") or {}).get("blocks") or [])
    if w / h >= 6 and blocks and blocks <= {"heading", "big text", "text", "button", "meta"}:
        # a flat strip with only a title (and a "View more"): the heading of the cards under it, not a card
        return dict(card, widget="composed", look=dict(look, blocks=[b for b in look.get("blocks") or [] if b != "button"] or ["heading"], strip=True))
    if w / h >= 5 and card["widget"] in ("list_thumbs", "quick_actions", "category_chips", "notifications"):
        look.pop("row", None)
        return dict(card, widget="category_chips", look=look)
    return card


def block_needs(blocks, tiles=0):
    """What the plan writes for a card drawn from its blocks (a recipe card's items are its ingredients, not the
    recipe itself: the plan wrote one item "Spicy Ramen" and its tile grid showed one tile, 2026-11-12)."""
    b, out = set(blocks), []
    if "tile grid" in b:
        out.append(f"items = the {tiles or 6} small things in its tiles (e.g. ingredients), each title + icon, not the card's own name")
    elif "rows" in b:
        out.append("items = its rows, each title, text, value + unit")
    elif b & {"donut", "rings", "bars", "line chart", "legend"}:
        out.append("items = the chart's parts, each title, value + unit")
    elif "chips" in b:
        out.append("items = its chips, each title + icon")
    elif "big number" in b:
        out.append("items = [the number: title, value + unit]")
    if "date range" in b:
        out.append("eyebrow = the date range")
    if b & {"button", "buttons"}:
        out.append("button = its button's words")
    if "meta" in b or ("button" in b and "tile grid" in b):
        out.append("meta = 1-2 small facts (a time, kcal)")
    return ("Write: " + "; ".join(out) + ".") if out else ""


_OCR = []


def words(src):
    """The words printed in the picture, each with its box: [(text, (x0, y0, x1, y1) in fractions)], read once per
    picture (RapidOCR on the CPU, ~4 s; kept with the picture's other readings)."""
    done = saved_read(src, "words")
    if done is not None:
        return [(t, tuple(b)) for t, b in done]
    try:
        from PIL import Image
        import numpy as np
        if not _OCR:
            from rapidocr_onnxruntime import RapidOCR
            _OCR.append(RapidOCR())
        im = Image.open(io.BytesIO(base64.b64decode(str(src).split(",", 1)[1]))) if str(src).startswith("data:") else Image.open(src)
        im = im.convert("RGB")
        W, H = im.size
        found, _ = _OCR[0](np.array(im))
    except Exception:  # (no OCR on this PC, or a picture it can't read: the parts are listed without their words)
        return []
    out = []
    for pts, text, score in found or []:
        text = " ".join(str(text).split())
        if float(score) < .8 or len(text) < 2 or not re.search(r"[^\W\d_]{2}", text):
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append((text, (round(min(xs) / W, 4), round(min(ys) / H, 4), round(max(xs) / W, 4), round(max(ys) / H, 4))))
    save_read(src, "words", out)
    return out


def words_in(found, box, limit=160):
    """The words whose middle is inside the box, in reading order, as one short line."""
    got = [t for t, b in sorted(found, key=lambda w: (round(w[1][1], 2), w[1][0]))
           if box[0] <= (b[0] + b[2]) / 2 <= box[2] and box[1] <= (b[1] + b[3]) / 2 <= box[3]]
    return ", ".join(dict.fromkeys(got))[:limit]


def card_boxes(src, sections):
    """Each read card's box, for a picture read before the boxes were kept (the same pixels give the same cards)."""
    if not sections or all(s.get("box") for s in sections):
        return
    try:
        g = cards(src, least=1) or {}
    except (OSError, ValueError, ImportError):
        return
    boxes = (g.get("boxes") or [])[:10]
    main = [s for s in sections if not s.get("side")]
    for s, b in zip(main, boxes):
        s.setdefault("box", [round(float(v), 4) for v in b])
    side = [s for s in sections if s.get("side") and not s.get("box")]
    if side and g.get("side_box") and boxes:
        try:
            sb = side_card_box(src, g["side_box"], max(b[3] for b in boxes))
        except (OSError, ValueError, IndexError):
            sb = None
        if sb:
            side[0]["box"] = [round(float(v), 4) for v in sb]


def seen(section):
    """What the vision model saw in a card (its "what" without M42's notes for the plan writer: Blocks / Write / Each item)."""
    if section.get("seen"):
        return section["seen"]
    what = re.sub(r"^(Blocks: [^.]*\.\s*)?(Write: .*?\.\s+(?=[A-Z]))?(Each item: [^.]*\.\s*)?", "", str(section.get("what") or ""))
    return re.sub(r"\s*\(icons: [^)]*\)?.*$", "", what).strip()


def grid_sections(grid, cards_read):
    """The spec's sections from the reference's cards, in the grid's reading order (leaf i = section i)."""
    out = []
    for c in cards_read:
        what = c["what"] + (f" (icons: {', '.join(c['icons'])})" if c["icons"] else "") + (f"; {c['count']} items" if c["count"] else "")
        row = (c.get("look") or {}).get("row")
        blocks = (c.get("look") or {}).get("blocks")
        if blocks:  # a card drawn from its blocks: what each block needs from the plan
            what = f"Blocks: {', '.join(blocks)}. {block_needs(blocks, (c.get('look') or {}).get('tiles'))} " + what
        elif row:  # each item's fields, from its row template (the plan wrote titles only; the reference's rows have more)
            what = f"Each item: {item_words(row)}. " + what
        out.append({"name": c["title"] or c["widget"].replace("_", " ").title(), "what": what[:260], "seen": c["what"][:200], "part": c["widget"],
                    "count": c["count"], "look": c.get("look") or {}, **({"side": True} if c.get("side") else {})})
    return out


def prune(node, n):
    """The grid without the leaves past the n cards that were read (a node left with one child is that child)."""
    if "leaf" in node:
        return node if node["leaf"] < n else None
    kids = [k for k in (prune(c, n) for c in node["children"]) if k]
    if not kids:
        return None
    return kids[0] if len(kids) == 1 else dict(node, children=kids)
