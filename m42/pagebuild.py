"""A page built by M42 from a plan (the user, 2026-10-26: "whatever site I ask for, M42 must make it with the premium
look of the page you made"). The work is split by who does it well:
  - the chat model (Qwen3.5 4B, which reads Tanglish and the web) writes the page PLAN: the content of every
    section, real-looking names, times, prices (PLAN_SCHEMA, so the JSON is always valid);
  - M42 builds the HTML from templates, one per part (this file): the layout is the same quality every time,
    the look (colours, style, fonts) is the site's own (webkit.make_theme);
  - behaviour comes from M42 UI's declarative data attributes (filter chips, search, select a row, picks and a
    summary that adds up), so most pages need no code from a model at all.
coder-7b writing whole pages made plain stacks of sections with empty forms, 10-20 minutes with its rewrites."""
import hashlib
import html as _html
import json
import re
from pathlib import Path

import webkit
import icons
import privacy
import themes  # noqa: E402
import widgets

PART_NAMES = webkit.PARTS + ("about", "contact", "custom")
FIELD = {"type": "object", "properties": {
    "label": {"type": "string", "maxLength": 24},
    "type": {"type": "string", "enum": ["text", "date", "select", "number", "email", "tel", "password", "textarea"]},
    "options": {"type": "array", "items": {"type": "string", "maxLength": 24}, "maxItems": 6}},
    "required": ["label", "type"]}
ITEM = {"type": "object", "properties": {
    "title": {"type": "string", "maxLength": 50}, "text": {"type": "string", "maxLength": 160},
    "icon": {"type": "string", "maxLength": 30},
    "meta": {"type": "array", "items": {"type": "string", "maxLength": 32}, "maxItems": 4},
    "value": {"type": "number"}, "unit": {"type": "string", "maxLength": 14},
    "badge": {"type": "string", "maxLength": 16},
    "tags": {"type": "array", "items": {"type": "string", "maxLength": 16}, "maxItems": 3},
    "group": {"type": "string", "maxLength": 20},
    "values": {"type": "array", "items": {"type": "number"}, "maxItems": 12}},
    "required": ["title", "text"]}
SECTION = {"type": "object", "properties": {
    "part": {"type": "string", "enum": list(PART_NAMES)},
    "eyebrow": {"type": "string", "maxLength": 24}, "title": {"type": "string", "maxLength": 60},
    "lead": {"type": "string", "maxLength": 150},
    "items": {"type": "array", "items": ITEM, "maxItems": 12},  # (a chat screen: 5 conversations + 6 messages)
    "filters": {"type": "array", "items": {"type": "string", "maxLength": 16}, "maxItems": 5},
    "fields": {"type": "array", "items": FIELD, "maxItems": 6},
    "labels": {"type": "array", "items": {"type": "string", "maxLength": 12}, "maxItems": 40},
    "taken": {"type": "array", "items": {"type": "string", "maxLength": 8}, "maxItems": 20},
    "cols": {"type": "integer", "minimum": 2, "maximum": 8},
    "price": {"type": "number"}, "button": {"type": "string", "maxLength": 24}},
    "required": ["part", "eyebrow", "title", "lead", "items"]}
PLAN_SCHEMA = {"type": "object", "properties": {
    "brand": {"type": "object", "properties": {"name": {"type": "string", "maxLength": 30},
                                               "icon": {"type": "string", "maxLength": 30}}, "required": ["name", "icon"]},
    "hero": {"type": "object", "properties": {
        "eyebrow": {"type": "string", "maxLength": 50}, "title": {"type": "string", "maxLength": 60},
        "accent": {"type": "string", "maxLength": 40}, "lead": {"type": "string", "maxLength": 170},
        "actions": {"type": "array", "items": {"type": "string", "maxLength": 26}, "maxItems": 2},
        "fields": {"type": "array", "items": FIELD, "maxItems": 5},
        "stats": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {
            "value": {"type": "number"}, "suffix": {"type": "string", "maxLength": 4},
            "label": {"type": "string", "maxLength": 24}}, "required": ["value", "label"]}}},
        "required": ["eyebrow", "title", "accent", "lead", "actions", "fields", "stats"]},
    "sections": {"type": "array", "items": SECTION, "minItems": 2, "maxItems": 12},  # a reference's 10 cards (7 cut its right column)
    "footer": {"type": "string", "maxLength": 90}},
    "required": ["brand", "hero", "sections", "footer"]}


def _no_icons(schema):
    """The plan's schema without the items' and the brand's icon: agent._pick_icons decides every icon after the plan
    (one call for the page), so the plan's own ~130 tokens of icon names were written for nothing (2026-11-16)."""
    import copy
    s = copy.deepcopy(schema)
    s["properties"]["sections"]["items"]["properties"]["items"]["items"]["properties"].pop("icon", None)
    brand = s["properties"]["brand"]
    brand["properties"].pop("icon", None)
    brand["required"] = [k for k in brand["required"] if k != "icon"]
    return s


PLAN_SCHEMA_NO_ICONS = _no_icons(PLAN_SCHEMA)


def bound_names(spec):
    """The spec's sections' names, each once (a second "menu" is "menu (2)"): what the plan's sections are bound to.
    [] when the plan is free (no spec sections, a reference's grid, one part)."""
    rows = [x for x in (spec or {}).get("sections") or [] if isinstance(x, dict)]
    if not rows or (spec or {}).get("ref_grid") or (spec or {}).get("only_part"):
        return []
    names, seen = [], {}
    for x in rows:
        nm = " ".join(str(x.get("name") or x.get("part") or "section").split())[:40]
        seen[nm] = seen.get(nm, 0) + 1
        names.append(nm if seen[nm] == 1 else f"{nm} ({seen[nm]})")
    return names


def bound_schema(base, names):
    """🧩 The plan's schema with exactly one section per spec section, each saying which one it is ("for", first): the
    4B wrote 9 sections for 7 one run and 6 another (a menu twice, Location never), and each section took the part
    of the spec row at its POSITION, so every part after a slip was another's (2026-11-17)."""
    if not names:
        return base
    import copy
    s = copy.deepcopy(base)
    sec = s["properties"]["sections"]
    sec["minItems"] = sec["maxItems"] = len(names)
    item = sec["items"]
    item["properties"] = {"for": {"type": "string", "enum": names}, **item["properties"]}
    item["required"] = ["for"] + [k for k in item["required"] if k != "for"]
    return s


def bind_sections(raw, names):
    """The plan's sections put in the spec's order by their "for" (a second one for the same row left out).
    Returns (the sections, one per name or None where none was written)."""
    out = [None] * len(names)
    for sec in (raw or {}).get("sections") or []:
        if isinstance(sec, dict) and sec.get("for") in names:
            i = names.index(sec["for"])
            if out[i] is None:
                out[i] = {k: v for k, v in sec.items() if k != "for"}
    return out

PLAN_PROMPT = """You write the CONTENT of a web page as JSON; M42 builds the page from it with its own premium
templates, so you only decide what each part says and holds. Follow the page's spec (its sections in order, its
hero kind). Make it feel like a real, busy site of this kind: specific names, places, times, prices, counts,
ratings (never "Item 1", "Lorem"). The user writes Tanglish: Indian context (₹ prices, Indian cities, names and
phone formats) unless they say otherwise. NO PERSONAL DETAILS: every e-mail is hello@example.com, every phone
+91 98765 XXXXX, an address a sample one (12, Sample Street, city, 600001); never a real person's phone, e-mail,
home address, Aadhaar, PAN or card number, even when the request or a picture shows one. Keep every text short and punchy. Every detail the spec gives a thing
(a package's duration and shot count, a room's beds and view, a course's hours) is in that item: its meta (short
facts) or its text. Everything is about THE USER'S site
only: the notes below describe the format, never a topic to borrow.
- brand: the site's name and the Bootstrap Icons name that fits it (bi- + a word for what the site is about).
- hero: eyebrow (a short proof with a number, about this site), title + accent (words, never a colour code; the
  accent words are shown in the gradient colour; together one short promise), lead (one sentence), actions (1-2
  button labels; none for a search hero), fields (only for a "search" hero: what a visitor searches by), stats
  (0-3 numbers: value, suffix like "+" or "★", label).
- a list of products, dishes, rooms, plans or services: 6 items, each with its own name, a one-line text and a price
  (value, and unit = what one costs: "each", "plate", "night"); never the same items again in another section.
- sections, one per spec section, part from the list given; each: eyebrow, title, lead, items, and what the part
  uses (a widget's own needs are listed under "What these widgets read"; values = a list of numbers for a chart): results: items = real rows (title = name, meta = 2-4 short facts, value = price, unit = what the price is for,
  tags = filter words, badge), filters = the chip words; picks: labels = cell names in order ("" for an aisle gap),
  cols, taken = booked ones, price = price per cell; summary: items = the rows to show (title = label); form /
  contact: fields (only the boxes a visitor types in: name, email, password...; never a button or a link like "Login"
  or "Forgot password?") + button (its submit words); cards: items with icon, title, text; prices: items with value, unit, meta = features,
  badge "Popular" on one; reviews: items = text, title = person, meta = [role], value = rating 1-5; steps; gallery:
  items with icon + title; stats: items with title, value, unit, icon; table: labels = column names, items = rows
  (title + meta = cells); faq: items = question + answer; tabs: items with group (the tab name), title, text,
  value; cta: title + lead + button; about: text in lead + items as highlights.
- footer: one line."""


SITEMAP_SCHEMA = {"type": "object", "properties": {"pages": {"type": "array", "minItems": 1, "maxItems": 5, "items": {
    "type": "object", "properties": {
        "name": {"type": "string", "maxLength": 24}, "purpose": {"type": "string", "maxLength": 120},
        "hero": {"type": "string", "enum": ["search", "split", "centered", "image", "compact", "none"]},
        "sections": {"type": "array", "minItems": 1, "maxItems": 6, "items": {"type": "object", "properties": {
            "name": {"type": "string", "maxLength": 40}, "what": {"type": "string", "maxLength": 140},
            "part": {"type": "string", "enum": list(PART_NAMES)}}, "required": ["name", "what", "part"]}}},
    "required": ["name", "purpose", "hero", "sections"]}}}, "required": ["pages"]}
SITEMAP_PROMPT = """The site is built in a project folder, so it can have several pages, like real sites of this kind
(one page for each main thing this site does, named in its own words). List its pages: 2-5, the first is the home page. Each page: name (short, for the menu),
purpose, hero ("compact" for app / admin pages, "none" for a login page) and its sections, top to bottom, with the
part that fits (the same parts as the spec). Follow the user's request and the spec; don't invent extra pages."""


EXIT_RX = re.compile(r"log ?out|sign ?out|exit", re.I)


def menu_pages(spec):
    """The pages a reference's own menu names (its entries in order, at most 5, not "Log out"); [] without one."""
    return [m["label"] for m in (spec or {}).get("side_menu") or [] if not EXIT_RX.search(m["label"])][:5]


def sitemap_messages(request, spec, reference=""):
    user = f"User request: {request[:800]}\n\nThe site's spec:\n{webkit.spec_text(spec)}"
    names = menu_pages(spec)
    if len(names) >= 2:  # the reference design's own menu: those are the pages (the 4B copied the prompt's example)
        user += ("\n\nThe site's pages are EXACTLY these, in this order (the menu of the user's reference design); one "
                 "page each, named exactly so: " + ", ".join(names))
    if reference.strip():
        user += "\n\nWhat real sites of this kind have (web text):\n" + reference.strip()[:1200]
    return [{"role": "system", "content": SITEMAP_PROMPT}, {"role": "user", "content": user}]


def page_files(pages):
    """[(name, file)]: the first page is index.html, the others name.html."""
    out, used = [], {"index"}
    for n, p in enumerate(pages):
        if n == 0:
            out.append((p.get("name") or "Home", "index.html"))
            continue
        stem = re.sub(r"[^a-z0-9]+", "-", str(p.get("name") or "page").lower()).strip("-") or f"page{n}"
        while stem in used:
            stem += "-2"
        used.add(stem)
        out.append((p.get("name") or stem, stem + ".html"))
    return out


def split_files(page, stem):
    """A page for a project folder: its look in css/theme.css (shared by all pages), its own inline scripts in
    js/<stem>.js. Returns (html, theme_css, js)."""
    m = re.search(r"<style id=\"m42-theme\">\n?(.*?)\n?</style>\n?", page, re.S)
    theme = m.group(1) if m else ""
    if m:
        page = page[:m.start()] + '<link rel="stylesheet" href="css/theme.css">\n' + page[m.end():]
    scripts = []

    def take(sm):
        if "data-m42-user" in sm.group(0):
            return sm.group(0)
        scripts.append(sm.group(1).strip())
        return ""
    page = re.sub(r"<script>(.*?)</script>\n?", take, page, flags=re.S)
    js = "\n\n".join(s for s in scripts if s)
    if js:
        page = page.replace("</body>", f'<script src="js/{stem}.js"></script>\n</body>', 1)
    return page, theme, js


def plan_messages(request, spec, reference=""):
    user = (f"This screen is used by {spec['app_for']}.\n" if (spec or {}).get("app_for") else "") + \
        f"User request: {request[:800]}\n\nThe page's spec:\n{webkit.spec_text(spec)}"
    if (spec or {}).get("hero") in ("compact", "none") and webkit.app_asked(request):
        # (no example words: the 4B copied "6 printers running · 14 jobs in queue" onto every page of a site)
        user += ("\nThis is an app screen people work in: hero.title = this screen's own name (1-3 words, the name of "
                 "THIS page), hero.accent = \"\", hero.eyebrow = \"\", hero.lead = one line of what this screen shows now, "
                 "in this business's own numbers (<number> <things> <state> · <number> <things> <state>), hero.actions = "
                 "the one action this screen does most (<verb> <thing>), hero.stats = [].")
    parts = [x["part"] for x in spec.get("sections") or []]
    if parts:
        user += "\nSection parts to use, in order: " + ", ".join(p if p in PART_NAMES else "custom" for p in parts)
        notes = [f"- {p}: {widgets.NOTES[p]}" for p in dict.fromkeys(parts) if p in widgets.NOTES]
        if notes:  # only the widgets this page uses (all 55 would fill the 4B's context)
            user += "\nWhat these widgets read:\n" + "\n".join(notes)
    if spec.get("app_flow") and parts:  # 📐 an app screen: each part's premium rules (screenparts.py) and the common ones
        import screenparts
        briefs = [screenparts.brief(p) for p in dict.fromkeys(parts)]
        user += "\n" + screenparts.common() + "\nEach part's rules:\n" + "\n".join(f"- {b}" for b in briefs if b)
    roles = [x.get("role") for x in spec.get("sections") or [] if isinstance(x, dict)]
    if any(roles):  # 🧩 each section's role in the page's flow and its premium rules (sections.py)
        import sections as secrules
        user += ("\nEach section's role, in order, and the rules of that role (what it must hold): "
                 + ", ".join(r or "-" for r in roles) + "\n" + "\n".join(f"- {secrules.brief(r)}" for r in dict.fromkeys(r for r in roles if r)))
    rh = spec.get("ref_head") or {}
    if rh.get("big"):  # the reference's own head (the cooking shot: "Hello, John", a big question, cuisine chips)
        user += ("\nThe page's head: hero.title is a big, friendly heading (a question or a call, 4-9 words)"
                 + ("; hero.eyebrow a short greeting (\"Hello, Priya\")" if rh.get("greeting") else "")
                 + (f"; hero.actions = exactly {rh['chips']} short category words shown as chips beside it (kinds of what the page is "
                    "about, 1-2 words each), not buttons" if rh.get("chips") else "") + ".")
    if spec.get("old_content"):  # a new design of the site already built here: its own content, kept
        user += ("\n\nThis site already exists with this content. Keep its brand, names, items, prices and words wherever "
                 "the new sections hold them (a section the new design adds gets new content of the same site):\n"
                 + str(spec["old_content"])[:1800])
    if reference.strip():
        user += "\n\nWhat real sites of this kind show (web text, for ideas only):\n" + reference.strip()[:1500]
    ex = spec.get("plan_example")
    if ex:  # a real page of this kind as a plan (uiplans.py, from the UIGEN-T2 pages): how full and specific it is
        user += ("\n\nA finished page like this one, written as a plan (for how FULL it is: as many items, real names, "
                 "prices, quotes and specific texts; the user's site, sections and parts above come first, and never copy "
                 f"its names or places):\n{ex[1]}")
    return [{"role": "system", "content": PLAN_PROMPT}, {"role": "user", "content": user}]


# ---- small helpers ----------------------------------------------------------------------------------------

def e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def slug(s, used):
    base = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:24] or "part"
    if base[0].isdigit():  # "#12-buses" is no CSS selector: the kit's scripts stopped on it
        base = "s-" + base
    out, n = base, 2
    while out in used:
        out, n = f"{base}-{n}", n + 1
    used.add(out)
    return out


def icon(name, fallback="bi-stars"):
    name = str(name or "").strip()
    if name.startswith("lc-"):  # a Lucide icon (icons.py picked it from the item's words)
        return name if icons.valid(name) else fallback
    if name and not name.startswith("bi-"):
        name = "bi-" + name
    return name if re.fullmatch(r"bi-[a-z0-9-]+", name or "") else fallback


STEP_RX = re.compile(r"\b(steps?|how it works|process|workflow|stages?)\b", re.I)
FEATURE_RX = re.compile(r"\b(features?|why choose|benefits?|amenities|what we offer|services?|highlights?)\b", re.I)
# a section that takes the visitor's details ("Booking Form": its fields were drawn as numbered cards, 2026-11-06)
FORM_RX = re.compile(r"\b(form|book(ing)?|reserv\w*|register|sign ?up|enquir\w*|inquir\w*|get in touch|contact us|apply)\b", re.I)
SHOW_RX = re.compile(r"summary|review|status|overview|details|history|confirmation", re.I)  # shows, takes nothing
PLAN_RX = re.compile(r"\b(plans?|pricing|prices?|membership|rates?|tiers?|packages?|subscriptions?)\b", re.I)
FAQ_RX = re.compile(r"\b(faq|questions?|answers?)\b", re.I)
CURRENCY = "₹"  # the page's money sign (render: from the plan and the request: "$" on a US bakery page)
CURRENCY_RX = re.compile(r"[₹$€£¥]|\brs\.?\s?\d|\b(inr|usd|eur|gbp|rupees?|dollars?|euros?|pounds?)\b", re.I)
# a price's unit that is what one costs ("25 each" was drawn "25each" in a stats row, with no ₹)
PRODUCT_UNIT_RX = re.compile(r"(each|piece|pcs?|slice|plate|glass|cup|bowl|pack|box|dozen|serving|portion|ticket|"
                             r"seat|bottle|jar|loaf|scoop|meal)s?", re.I)  # (not kg / hour: 12 kg is a weight)


def page_currency(text):
    m = CURRENCY_RX.search(text or "")
    if not m:
        return "₹"
    t = m.group(0).lower()
    return ("$" if "$" in t or "usd" in t or "dollar" in t else "€" if "€" in t or "eur" in t else
            "£" if "£" in t or "gbp" in t or "pound" in t else "¥" if "¥" in t else "₹")


PRICE_X = 1  # render: dollar-size prices on a rupee page ("₹3.50 / each" for a bakery bun) are drawn as rupees
NO_PRICE_PARTS = {"stats", "kpi_tiles", "ratings", "reviews", "testimonials", "progress", "gauges", "chart", "line_chart",
                  "bar_chart", "donut", "timeline", "steps", "faq", "form"}


def rupee_scale(plan, request=""):
    """85 when the 4B wrote a rupee page's prices in dollars (all small, some with paise: 3.50, 4.25, 12), else 1.
    The page's own prices decide, all of them together, so one page never mixes ₹300 and ₹4."""
    if re.search(r"₹|\brs\.?\s?\d|\b(inr|rupees?)\b", request or "", re.I):
        return 1  # the user wrote rupees: the numbers are theirs
    vals = []
    for sec in [plan.get("hero") or {}] + list(plan.get("sections") or []):
        if sec.get("part") in NO_PRICE_PARTS:
            continue
        for it in sec.get("items") or []:
            unit = str(it.get("unit") or "").strip()
            if not (unit in ("", "₹") or PRODUCT_UNIT_RX.fullmatch(unit) or unit.lower().startswith("per") or unit.startswith("/")):
                continue
            try:
                vals.append(float(str(it.get("value")).replace("₹", "").replace(",", "").strip()))
            except (TypeError, ValueError):
                pass
    if len(vals) >= 2 and max(vals) < 60 and any(v != int(v) for v in vals):
        return 85
    return 1


def nice_price(f):
    step = 5 if f < 100 else 10 if f < 1000 else 50
    return max(step, round(f / step) * step)


def money(v, unit=""):
    if v is None or v == "":
        return ""
    try:
        f = float(str(v).replace(",", "")) if not isinstance(v, (int, float)) else float(v)
    except (TypeError, ValueError):
        m = re.fullmatch(r"\s*₹\s?(\d+(?:\.\d+)?)\s*", str(v))  # "₹3.50" written as text
        if not (m and PRICE_X != 1):
            return e(v)
        f = float(m.group(1))
    if PRICE_X != 1 and CURRENCY == "₹" and 0 < f < 60 and unit.strip() not in ("$", "€", "£", "¥"):
        f = nice_price(f * PRICE_X)
    s = f"{f:,.0f}" if f == int(f) else f"{f:,.2f}"
    if unit.strip() in ("$", "€", "£", "¥", "₹"):
        return f"{unit.strip()}{s}"
    if PRODUCT_UNIT_RX.fullmatch(unit.strip()):
        return f"{CURRENCY}{s}"
    return f"{CURRENCY}{s}" if not unit or "₹" in unit or "per" in unit.lower() or "/" in unit else s


def field_html(f, pid, used, cls=""):
    label = f.get("label") or "Field"
    fid = slug(f"{pid}-{label}", used)
    t = f.get("type") or "text"
    if t == "select":
        opts = "".join(f"<option>{e(o)}</option>" for o in (f.get("options") or ["Any"]))
        control = f'<select id="{fid}" class="form-select" required>{opts}</select>'
    elif t == "textarea":
        control = f'<textarea id="{fid}" class="form-control" rows="3" required></textarea>'
    else:
        control = f'<input id="{fid}" type="{e(t)}" class="form-control" required placeholder="{e(label)}">'
    return f'<div class="{cls}"><label class="form-label" for="{fid}">{e(label)}</label>{control}</div>'


ARCH = {"arch": ""}  # the page being rendered: its archetype (render sets it)
# the archetypes with their own design ("warm", the default, is the variant mix): product (Apple-like), editorial
# (serif, paper), saas (a framed product shot on a grid, bento features), bold (huge type on a full gradient, a moving
# strip, colour tiles), portfolio (a big plain name, the work as an index list, monochrome)
ARCHES = ("product", "editorial", "saas", "bold", "portfolio")
# each archetype's fixed layouts of a part (variant(): no mix inside one design)
ARCH_VARIANT = {("bold", "cards"): 1, ("saas", "steps"): 1, ("bold", "steps"): 1, ("bold", "reviews"): 0,
                ("saas", "reviews"): 2, ("portfolio", "reviews"): 1}


def head(sec, center=True):
    if not (sec.get("title") or sec.get("eyebrow")):
        return ""
    dh = ARCH.get("dhead")
    if dh and dh != "numbered":  # 🎨 the theme's own head (themes.py)
        brow = f'<span class="m42-eyebrow">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else ""
        h2 = f'<h2>{e(sec.get("title"))}</h2>' if sec.get("title") else ""
        lead = f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else ""
        if dh == "split":  # the title on the left, its lead on the right
            return f'<div class="m42-section-head is-split"><div>{brow}{h2}</div>{lead}</div>'
        cls = {"center": "", "pill": " is-pill", "rule": " is-rule text-start ms-0", "big": " is-big text-start ms-0",
               "sticky": " is-sticky text-start ms-0", "boxed": " is-boxed text-start ms-0", "column": " is-column",
               "marker": " is-marker", "mono": " is-mono text-start ms-0", "ornament": " is-ornament", "quiet": " is-quiet",
               "outline": " is-outline text-start ms-0"}.get(dh, "")
        return f'<div class="m42-section-head{cls}">{brow}{h2}{lead}</div>'
    if ARCH["arch"] == "editorial" or dh == "numbered":  # a numbered, left-aligned head with a rule: 01 — Practice areas
        n = ARCH.get("n", 1)
        return (f'<div class="m42-ed-head"><span class="m42-ed-num">{n:02d}</span><div>'
                + (f'<span class="m42-ed-kicker">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
                + (f'<h2>{e(sec.get("title"))}</h2>' if sec.get("title") else "")
                + (f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else "") + "</div></div>")
    if ARCH["arch"] == "portfolio":
        center = False
    if not ARCH["arch"] and ARCH.get("head") == 1:  # (the warm design's second head, by the site's name)
        return (f'<div class="m42-section-head is-rule text-start ms-0">'
                + (f'<span class="m42-eyebrow">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
                + (f'<h2>{e(sec.get("title"))}</h2>' if sec.get("title") else "")
                + (f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else "") + "</div>")
    return (f'<div class="m42-section-head{"" if center else " text-start ms-0"}">'
            + (f'<span class="m42-eyebrow">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
            + (f'<h2>{e(sec.get("title"))}</h2>' if sec.get("title") else "")
            + (f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else "") + "</div>")


# ---- parts ------------------------------------------------------------------------------------------------

def p_results(sec, ctx):
    lid = sec["_id"] + "-list"
    ctx["results_id"] = ctx.get("results_id") or lid
    chips = ""
    if sec.get("filters"):
        chips = (f'<div class="m42-chips" data-single data-m42-filter-for="{lid}">'
                 '<button type="button" class="m42-chip-btn active" data-filter="all">All</button>'
                 + "".join(f'<button type="button" class="m42-chip-btn" data-filter="{e(f.lower())}">{e(f)}</button>'
                           for f in sec["filters"]) + "</div>")
    rows = []
    for it in sec.get("items") or []:
        tags = " ".join(t.lower() for t in (it.get("tags") or []))
        meta = "".join(f"<span>{e(m)}</span>" for m in it.get("meta") or [])
        badge = f' <span class="m42-badge">{e(it["badge"])}</span>' if it.get("badge") else ""
        price = money(it.get("value"), it.get("unit") or "")
        rows.append(
            f'<div class="m42-item" data-tags="{e(tags)}" data-name="{e(it.get("title"))}" data-price="{e(it.get("value") or 0)}">'
            f'<div><h3>{e(it.get("title"))}{badge}</h3><div class="m42-meta">{meta}</div></div>'
            f'<div class="m42-meta">{e(it.get("text"))}</div>'
            f'<div class="m42-price-tag">{price}<small>{e("" if re.fullmatch(r"\s*[₹$€£]\s*", it.get("unit") or "") else it.get("unit") or "")}</small>'
            f'<button type="button" class="m42-btn mt-2" data-m42-choose data-m42-next="{e(ctx.get("next_after", {}).get(sec["_id"], ""))}">'
            f'{e(sec.get("button") or "Select")}</button></div></div>')
    title = (f'<div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">'
             f'<h2 class="h3 m-0">{e(sec.get("title"))}</h2>{chips}</div>'
             + (f'<p class="m42-muted">{e(sec.get("lead"))}</p>' if sec.get("lead") else ""))
    return title + f'<div class="m42-results" id="{lid}">' + "".join(rows) + "</div>"


def p_picks(sec, ctx):
    labels = [str(x) for x in sec.get("labels") or []]
    cols = int(sec.get("cols") or 5)
    if not labels:  # a 2 + aisle + 2 coach of 8 rows
        cols = 5
        labels = [f"{r}{c}" if c else "" for r in "ABCDEFGH" for c in (1, 2, 0, 3, 4)]
    taken = {str(t) for t in sec.get("taken") or []}
    cells = "".join('<span class="m42-pick gap"></span>' if not lab.strip() else
                    f'<button type="button" class="m42-pick{" taken" if lab in taken else ""}" data-value="{e(lab)}"'
                    f'{" disabled" if lab in taken else ""}>{e(lab)}</button>' for lab in labels)
    price = sec.get("price")
    return (f'<div class="m42-card mt-4"><h3 class="h5">{e(sec.get("title") or "Pick")}</h3>'
            + (f'<p class="m42-muted small">{e(sec.get("lead"))}</p>' if sec.get("lead") else "")
            + f'<div class="m42-pick-grid" id="{sec["_id"]}-grid" data-max="6" data-m42-picks'
            + (f' data-price="{e(price)}"' if price else "") + f' style="--m42-cols:{cols}">{cells}</div>'
            '<div class="d-flex gap-3 mt-3 small m42-muted"><span><span class="m42-pick d-inline-block px-2 py-0">A1</span> free</span>'
            '<span><span class="m42-pick selected d-inline-block px-2 py-0">A1</span> yours</span>'
            '<span><span class="m42-pick taken d-inline-block px-2 py-0">A1</span> booked</span></div></div>')


def p_summary(sec, ctx):
    rows = []
    binds = ["item", "picked"]
    for n, it in enumerate(sec.get("items") or [{"title": "Selected"}, {"title": "Seats"}]):
        key = binds[n] if n < len(binds) else ""
        rows.append(f'<div class="m42-row"><span>{e(it.get("title"))}</span><b'
                    + (f' data-m42-bind="{key}"' if key else "") + f'>{e(it.get("text") or "—") if not key else "—"}</b></div>')
    nxt = ctx.get("next_after", {}).get(sec["_id"], "")
    return (f'<aside class="m42-summary"><h3 class="h5">{e(sec.get("title") or "Summary")}</h3>' + "".join(rows)
            + '<div class="m42-total"><span>Total</span><span data-m42-bind="total">₹0</span></div>'
            + f'<a class="m42-btn w-100 mt-3" href="#{e(nxt)}">{e(sec.get("button") or "Continue")}</a></aside>')


def p_form(sec, ctx, contact=False):
    used = ctx["ids"]
    fields = sec.get("fields") or [{"label": "Name", "type": "text"}, {"label": "Phone", "type": "tel"}]
    auth = any(f.get("type") == "password" for f in fields)  # a sign-in card: one narrow column
    body = "".join(field_html(f, sec["_id"], used, "col-md-6" if f.get("type") != "textarea" and not auth else "col-12")
                   for f in fields)
    form = (f'<form class="m42-form m42-card{" mx-auto" if auth else ""}"' + (' style="max-width:460px"' if auth else "")
            + f' data-m42-done="{e(sec.get("lead") or "Done! We will contact you shortly.")}">'
            f'<div class="row g-3">{body}<div class="col-12"><button class="m42-btn w-100">{e(sec.get("button") or "Submit")}'
            '</button></div></div></form>')
    if contact and sec.get("items"):
        info = "".join(f'<div class="m42-feature mb-3"><span class="m42-chip"><i class="bi {icon(it.get("icon"), "bi-telephone")}"></i>'
                       f'</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div>' for it in sec["items"][:3])
        return head(sec) + f'<div class="row g-4"><div class="col-lg-5">{info}</div><div class="col-lg-7">{form}</div></div>'
    return form


def variant(ctx, part, n):
    """Which of n layouts this section gets on a site page: from the site's name, the part and the section's place
    (so two sites differ, and a page built again keeps its layout); 0 on app pages."""
    if ctx.get("layout") != "site" or n < 2:
        return 0
    if ARCH["arch"] in ARCHES:
        return min(n - 1, ARCH_VARIANT.get((ARCH["arch"], part), 0))
    seed = hashlib.md5(f"{ctx.get('site_key', '')}|{part}|{ctx.get('sec_n', 0)}".encode()).hexdigest()
    return int(seed, 16) % n


def p_lineup(sec, ctx):
    """A product page's models side by side: the picture, the name, a line, the price and a button."""
    cards = "".join(f'<div class="col-md-6 col-lg-{12 // min(3, max(1, len(sec.get("items") or [1])))}"><div class="m42-lineup">'
                    + (widgets.photo(it, "m42-lineup-photo") or f'<div class="m42-lineup-art"><i class="bi {icon(it.get("icon"), icon(ctx.get("brand_icon")))}"></i></div>')
                    + f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>'
                    + (f'<div class="m42-lineup-price">{amount(it.get("value"), it.get("unit") or "")}</div>' if it.get("value") not in (None, "") else "")
                    + f'<a class="m42-btn" href="#">{e(sec.get("button") or "Buy")}</a></div></div>'
                    for it in (sec.get("items") or [])[:3])
    return head(sec) + f'<div class="row g-4 justify-content-center">{cards}</div>'


def p_feature_rows(sec, ctx):
    """A product page's features: one wide row each, the picture and the words changing sides (Apple-like)."""
    items = sec.get("items") or []
    rows = []
    for k, it in enumerate(items[:4]):
        pic = (widgets.photo(it, "m42-frow-photo") or
               f'<div class="m42-frow-art"><i class="bi {icon(it.get("icon"), icon(ctx.get("brand_icon")))}"></i></div>')
        rows.append(f'<div class="m42-frow{" is-flip" if k % 2 else ""}"><div class="m42-frow-pic">{pic}</div>'
                    f'<div class="m42-frow-text"><span class="m42-frow-n">{k + 1:02d}</span><h3>{e(it.get("title"))}</h3>'
                    f'<p>{e(it.get("text"))}</p></div></div>')
    rest = "".join(f'<div class="col-md-6 col-lg-3"><div class="m42-frow-mini"><i class="bi {icon(it.get("icon"))}"></i>'
                   f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div></div>' for it in items[4:8])
    return head(sec) + f'<div class="m42-frows">{"".join(rows)}</div>' + (f'<div class="row g-4 mt-2">{rest}</div>' if rest else "")


def p_index(sec, ctx):
    """A portfolio's work: one wide row each, its number, name, a line and an arrow; the picture shows on hover."""
    rows = "".join(f'<a class="m42-pf-row" href="#"><span class="m42-pf-n">{k + 1:02d}</span><h3>{e(it.get("title"))}</h3>'
                   f'<p>{e(it.get("text"))}</p>' + (widgets.photo(it, "m42-pf-peek") or "")
                   + '<i class="bi bi-arrow-up-right"></i></a>' for k, it in enumerate(sec.get("items") or []))
    return head(sec) + f'<div class="m42-pf-index">{rows}</div>'


def marquee(plan):
    """A bold page's moving strip under the hero: the names of what the page offers, twice round."""
    words = [str(it.get("title")) for sec in plan.get("sections") or [] if sec.get("part") in ("cards", "image_cards", "gallery", "prices", "tabs")
             for it in (sec.get("items") or []) if it.get("title") and len(str(it.get("title"))) <= 28][:8]
    if len(words) < 3:
        return ""
    line = "".join(f"<span>{e(w)}</span><i class=\"bi bi-asterisk\"></i>" for w in words)
    return f'<div class="m42-marquee" aria-hidden="true"><div class="m42-marquee-track">{line}{line}</div></div>'


def p_menu_list(sec, ctx):
    """Things with prices as a menu: two columns of rows, the name, a dotted leader and the price, a line under it
    (a small photo when there is one)."""
    rows = "".join('<li class="m42-menu-row">' + (widgets.photo(it, "m42-menu-thumb") or "")
                   + f'<div class="m42-menu-main"><div class="m42-menu-top"><h3>{e(it.get("title"))}</h3><i></i>'
                   + (f'<b>{amount(it.get("value"), it.get("unit") or "")}</b>' if it.get("value") not in (None, "", 0, 0.0) else "")
                   + "</div>" + (f'<p>{e(it.get("text"))}</p>' if it.get("text") else "") + "</div></li>"
                   for it in sec.get("items") or [])
    return head(sec) + f'<ul class="m42-menu">{rows}</ul>'


def p_site_things(sec, ctx):
    """A site's things with prices (rooms, specials, products) by the page's design: a menu for editorial, colour
    tiles for bold, a bento for saas, an index for portfolio; the warm design one of three by the site's name.
    (2026-11-12: a hotel's rooms, a bakery's specials and a headphone line-up were the same pastel tiles.)"""
    arch = ARCH["arch"]
    v = {"editorial": 1, "bold": 2, "saas": 3, "portfolio": 4}.get(arch, variant(ctx, "image_cards", 3))
    if v == 1:
        return p_menu_list(sec, ctx)
    if v == 2:
        return p_cards(sec, dict(ctx, layout="site", _force=1))
    if v == 3:
        return p_cards_bento(sec, ctx)
    if v == 4:
        return p_index(sec, ctx)
    body = PARTS["image_cards"](dict(sec, title="", lead="", eyebrow=""), ctx)
    return head(sec) + f'<div class="m42-panel">{body}</div>'


def p_ed_list(sec, ctx):
    """An editorial page's points: a numbered list in two columns, thin rules, no cards."""
    rows = "".join(f'<li><span>{k + 1:02d}</span><div><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div></li>'
                   for k, it in enumerate(sec.get("items") or []))
    return head(sec) + f'<ol class="m42-ed-list">{rows}</ol>'


def p_cards(sec, ctx):
    items = sec.get("items") or []
    if ARCH["arch"] == "product" and items:
        return p_feature_rows(sec, ctx)
    if ARCH["arch"] == "editorial" and items:
        return p_ed_list(sec, ctx)
    if ARCH["arch"] == "portfolio" and items:
        return p_index(sec, ctx)
    v = ctx.get("_force") or (variant(ctx, "cards", 4) if 2 <= len(items) <= 6 else 0)
    if v == 1:  # colourful tiles: a deep band with the icon on top of each card
        tiles = "".join(f'<div class="col-md-6 col-lg-{12 // min(3, max(1, len(items)))}"><div class="m42-tile" style="--d:var(--m42-deep{["", "-2", "-3"][k % 3]})">'
                        + (widgets.photo(it, "m42-tile-photo") or f'<div class="m42-tile-band"><i class="bi {icon(it.get("icon"))}"></i></div>')
                        + f'<div class="m42-tile-body"><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>'
                        + (f'<div class="m42-tile-price">{amount(it.get("value"), it.get("unit") or "")}</div>' if it.get("value") else "")
                        + "</div></div></div>" for k, it in enumerate(items))
        return head(sec) + f'<div class="row g-4">{tiles}</div>'
    if v == 2:  # a picture beside a list of icon rows
        first = next((it for it in items if widgets.photo(it)), None)
        art = (widgets.photo(first, "m42-splitfeat-photo") if first else
               f'<div class="m42-splitfeat-art"><i class="bi {icon(ctx.get("brand_icon"))}"></i></div>')
        rows = "".join(f'<li><span class="m42-chip"><i class="bi {icon(it.get("icon"))}"></i></span><div><h3>{e(it.get("title"))}</h3>'
                       f'<p>{e(it.get("text"))}</p></div></li>' for it in items)
        return (head(sec) + f'<div class="row g-5 align-items-center"><div class="col-lg-6">{art}</div>'
                f'<div class="col-lg-6"><ul class="m42-splitfeat">{rows}</ul></div></div>')
    if v == 3:  # big numbers 01 02 03
        nums = "".join(f'<div class="col-md-6 col-lg-{12 // min(3, max(1, len(items)))}"><div class="m42-numfeat"><span>{k + 1:02d}</span>'
                       f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div></div>' for k, it in enumerate(items))
        return head(sec) + f'<div class="row g-4">{nums}</div>'
    return p_cards_bento(sec, ctx)


def p_cards_bento(sec, ctx):
    """A bento grid: with 2, 5 or 8 cards the first one leads (twice as wide, in the accent), 4 go two by two,
    so no row ends half empty."""
    items = sec.get("items") or []
    n = len(items)
    lead = n in (2, 5, 8)

    def col(i):
        if n == 1:
            return "col-12"
        if n == 4:
            return "col-md-6"
        return "col-md-6 col-lg-8" if lead and i == 0 else "col-md-6 col-lg-4"
    cards = "".join(f'<div class="{col(i)}"><div class="m42-feature m42-tilt{" is-lead" if lead and i == 0 else ""}{" has-photo" if widgets.photo(it) else ""}">'
                    + widgets.photo(it, "m42-feature-photo")
                    + f'<span class="m42-chip"><i class="bi {icon(it.get("icon"))}"></i></span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>'
                    + (f'<div class="mt-2 fw-bold">{money(it.get("value"), it.get("unit") or "")}</div>' if it.get("value") else "")
                    + "</div></div>" for i, it in enumerate(items))
    return head(sec) + f'<div class="row g-4">{cards}</div>'


def p_rows(sec, ctx):
    """Cards as a compact list (inside an app panel): icon, title, a line, the value or status at the end."""
    rows = []
    for it in sec.get("items") or []:
        end = (amount(it.get("value"), it.get("unit") or "") if it.get("value") not in (None, "")
               else badge(it["badge"]) if it.get("badge") else "")
        sub = it.get("text") or " · ".join(it.get("meta") or [])
        rows.append(f'<div class="m42-row"><span class="m42-chip"><i class="bi {icon(it.get("icon"), webkit._icon_for(str(it.get("title") or "")))}"></i></span>'
                    f'<div><strong>{e(it.get("title"))}</strong>' + (f'<small>{e(sub)}</small>' if sub else "") + "</div>"
                    + (f'<div class="m42-row-end">{end}</div>' if end else "") + "</div>")
    return f'<div class="m42-rows">{"".join(rows)}</div>'


FREE_RX = re.compile(r"\bfree\b", re.I)
STEP_NO_RX = re.compile(r"^\s*(?:step\s*)?\d{1,2}\s*[:.)\-]\s*", re.I)  # "Step 1: Upload" under a circle that says 1


# ---- 🎨 the steps, prices and reviews of a theme: each theme its own (the user, 2026-11-14: "the steps, the prices and
# the reviews look the same in every theme"); spread from the theme's name, so a new theme gets its own at once
PART_STYLES = {"steps": ("list", "row", "timeline", "bigsteps"), "prices": ("cards", "deep", "featured", "compare"),
               "reviews": ("cards", "bigquote", "tint", "wall")}


def design_part(part):
    """The theme's own layout for a steps / prices / reviews section ("" with no theme)."""
    name = ARCH.get("design") or ""
    if not name or not ARCH.get("dhead") or part not in PART_STYLES:
        return ""
    t = themes.THEMES.get(name) or {}
    if (t.get("parts") or {}).get(part):
        return t["parts"][part]
    styles = PART_STYLES[part]
    return styles[int(hashlib.md5(f"{name}|{part}".encode()).hexdigest(), 16) % len(styles)]


def steps_timeline(sec, items):
    """A vertical line down the middle, each step a node on it, the words on alternate sides."""
    rows = "".join(f'<li class="{"is-r" if k % 2 else "is-l"}"><span class="m42-tl-node">{k + 1:02d}</span><div class="m42-tl-card">'
                   f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div></li>' for k, it in enumerate(items))
    return head(sec) + f'<ol class="m42-tl">{rows}</ol>'


def steps_big(sec, items):
    """Huge outlined numbers over each step, side by side."""
    cols = "".join(f'<li><span class="m42-bs-num">{k + 1:02d}</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></li>'
                   for k, it in enumerate(items))
    return head(sec) + f'<ol class="m42-bs" style="--n:{min(4, max(1, len(items)))}">{cols}</ol>'


def prices_featured(sec, items):
    """The plans side by side, the one in the middle (or the badged one) raised on the page's deep colour."""
    badged = [k for k, it in enumerate(items) if it.get("badge")]
    star = badged[0] if len(badged) == 1 else len(items) // 2  # (every plan badged: the middle one leads)
    cards = []
    for k, it in enumerate(items):
        feats = "".join(f'<li><i class="bi bi-check2"></i>{e(m)}</li>' for m in it.get("meta") or it.get("tags") or [])
        free = it.get("value") in (0, 0.0, "0")
        cards.append(f'<div class="m42-pf{" is-star" if k == star else ""}">' + (f'<span class="m42-pf-badge">{e(it.get("badge") or "Most chosen")}</span>' if k == star else "")
                     + f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>'
                     f'<div class="m42-pf-amount">{"Free" if free else money(it.get("value"), "")}<small>{e(it.get("unit") or "")}</small></div>'
                     f'<ul>{feats}</ul><a class="{"m42-btn" if k == star else "m42-btn-ghost"} w-100 justify-content-center" href="#">{e(sec.get("button") or "Choose")}</a></div>')
    return head(sec) + f'<div class="m42-pfs" style="--n:{len(items)}">{"".join(cards)}</div>'


def prices_compare(sec, items):
    """The plans as columns of one table, each feature a row with a tick where the plan has it."""
    feats = list(dict.fromkeys(m for it in items for m in (it.get("meta") or it.get("tags") or [])))
    if len(feats) < 2 or len(items) > 4:
        return prices_featured(sec, items)
    badged = [k for k, it in enumerate(items) if it.get("badge")]
    star = badged[0] if len(badged) == 1 else len(items) // 2  # (every plan badged: the middle one leads)
    head_cells = "".join(f'<th class="{"is-star" if k == star else ""}"><b>{e(it.get("title"))}</b><span class="m42-pc-amount">'
                         f'{money(it.get("value"), "")}<small>{e(it.get("unit") or "")}</small></span></th>' for k, it in enumerate(items))
    rows = "".join(f'<tr><th scope="row">{e(f)}</th>' + "".join(
        f'<td class="{"is-star" if k == star else ""}">' + ('<i class="bi bi-check-circle-fill" aria-label="Included"></i>' if f in (it.get("meta") or it.get("tags") or [])
                                                          else '<span class="m42-pc-no" aria-label="Not included">—</span>') + "</td>"
        for k, it in enumerate(items)) + "</tr>" for f in feats)
    buttons = "".join(f'<td class="{"is-star" if k == star else ""}"><a class="{"m42-btn" if k == star else "m42-btn-ghost"} w-100 justify-content-center" href="#">'
                      f'{e(sec.get("button") or "Choose")}</a></td>' for k, it in enumerate(items))
    return (head(sec) + f'<div class="m42-pc-wrap"><table class="m42-pc"><thead><tr><th></th>{head_cells}</tr></thead>'
            f'<tbody>{rows}</tbody><tfoot><tr><th></th>{buttons}</tr></tfoot></table></div>')


def reviews_wall(sec, items, who, stars):
    """The words of many people as a wall of quotes of different heights (masonry), the first one large."""
    cards = "".join(f'<figure class="m42-rw{" is-big" if k == 0 else ""}"><div class="m42-stars">{stars(it)}</div>'
                    f'<blockquote>{e(it.get("text"))}</blockquote>{who(it)}</figure>' for k, it in enumerate(items[:9]))
    return head(sec) + f'<div class="m42-rws">{cards}</div>'

def p_prices(sec, ctx):
    items = sec.get("items") or []
    cards = []
    dp = design_part("prices")  # 🎨 the theme's own
    if dp == "featured" and len(items) >= 2:
        return prices_featured(sec, items)
    if dp == "compare" and len(items) >= 2:
        return prices_compare(sec, items)
    deep = (dp == "deep") if dp else variant(ctx, "prices", 2) == 1
    if deep and not any(it.get("badge") for it in items) and len(items) >= 2:
        items = [dict(it, badge="Popular") if k == len(items) // 2 else it for k, it in enumerate(items)]
    for it in items:
        featured = bool(it.get("badge"))
        feats = "".join(f"<li>{e(m)}</li>" for m in it.get("meta") or it.get("tags") or [])  # (the 4B: tags)
        free = it.get("value") in (0, 0.0, "0") or (it.get("value") in (None, "") and FREE_RX.search(str(it.get("unit") or "")))
        amount_html = ("Free" if free else f'{money(it.get("value"), "")}<small>{e(it.get("unit") or "")}</small>')  # ("₹0 Free")
        cards.append(f'<div class="col-md-6 col-lg-4"><div class="m42-price{" is-featured" if featured else ""}"'
                     + (f' data-badge="{e(it["badge"])}"' if featured else "")
                     + f'><h3>{e(it.get("title"))}</h3><p class="m42-muted">{e(it.get("text"))}</p>'
                     f'<div class="m42-amount">{amount_html}</div>'
                     f'<ul class="m42-list">{feats}</ul><a class="{"m42-btn" if featured else "m42-btn-ghost"} justify-content-center" '
                     f'href="#">{e(sec.get("button") or "Choose")}</a></div></div>')
    return head(sec) + f'<div class="row g-4 align-items-stretch{" m42-prices-deep" if deep else ""}">{"".join(cards)}</div>'


def p_reviews(sec, ctx):
    items = sec.get("items") or []
    v = variant(ctx, "reviews", 3) if items else 0
    if ARCH["arch"] == "editorial" and items:
        v = 1  # (the big quote)

    def who(it):
        name = it.get("title") or "Guest"
        initials = "".join(w[0] for w in str(name).split()[:2]).upper()
        return (f'<div class="m42-person"><span class="m42-avatar">{e(initials)}</span><div><strong>{e(name)}</strong>'
                f'<span>{e((it.get("meta") or [""])[0])}</span></div></div>')

    def stars(it):
        return "★" * max(1, min(5, int(round(float(it.get("value") or 5)))))
    dp = design_part("reviews")  # 🎨 the theme's own
    if dp == "wall" and len(items) >= 3:
        return reviews_wall(sec, items, who, stars)
    if dp and items:
        v = {"cards": 0, "bigquote": 1, "tint": 2}.get(dp, v)
    if v == 1:  # one big quote in the spotlight, the others small beside it
        top, rest = items[0], items[1:4]
        small = "".join(f'<div class="m42-quote is-small"><div class="m42-stars">{stars(it)}</div><p>{e(it.get("text"))}</p>{who(it)}</div>'
                        for it in rest)
        return (head(sec) + f'<div class="row g-4 align-items-stretch"><div class="col-lg-7"><figure class="m42-spot"><i class="bi bi-quote"></i>'
                f'<blockquote>{e(top.get("text"))}</blockquote><div class="m42-stars">{stars(top)}</div>{who(top)}</figure></div>'
                f'<div class="col-lg-5 d-grid gap-3">{small}</div></div>')
    if v == 2:  # tinted cards with a coloured edge
        cards = "".join(f'<div class="col-md-6 col-lg-4"><div class="m42-quote is-tint" style="--t:var(--m42-deep{["", "-2", "-3"][k % 3]})">'
                        f'<i class="bi bi-quote m42-quote-mark"></i><p>{e(it.get("text"))}</p><div class="m42-stars">{stars(it)}</div>{who(it)}</div></div>'
                        for k, it in enumerate(items))
        return head(sec) + f'<div class="row g-4">{cards}</div>'
    out = []
    for it in sec.get("items") or []:
        name = it.get("title") or "Guest"
        initials = "".join(w[0] for w in str(name).split()[:2]).upper()
        stars = "★" * max(1, min(5, int(round(float(it.get("value") or 5)))))
        role = (it.get("meta") or [""])[0]
        out.append(f'<div class="col-md-6 col-lg-4"><div class="m42-quote"><div class="m42-stars">{stars}</div>'
                   f'<p>{e(it.get("text"))}</p><div class="m42-person"><span class="m42-avatar">{e(initials)}</span>'
                   f'<div><strong>{e(name)}</strong><span>{e(role)}</span></div></div></div></div>')
    return head(sec) + f'<div class="row g-4">{"".join(out)}</div>'


def p_steps(sec, ctx):
    items = [dict(it, title=STEP_NO_RX.sub("", str(it.get("title") or "")) or it.get("title")) for it in sec.get("items") or []]
    dp = design_part("steps")  # 🎨 the theme's own
    if dp == "timeline" and 2 <= len(items) <= 7:
        return steps_timeline(sec, items)
    if dp == "bigsteps" and 2 <= len(items) <= 6:
        return steps_big(sec, items)
    if (dp == "row" if dp else variant(ctx, "steps", 2) == 1) and 2 <= len(items) <= 5:  # numbered circles in a row, joined by a line
        row = "".join(f'<li><span class="m42-stepnum">{k + 1}</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></li>'
                      for k, it in enumerate(items))
        return head(sec) + f'<ol class="m42-steprow" style="--n:{len(items)}">{row}</ol>'
    steps = "".join(f'<li><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></li>' for it in items)
    return (f'<div class="row g-5 align-items-center"><div class="col-lg-5">{head(sec, center=False)}</div>'
            f'<div class="col-lg-7"><ol class="m42-steps">{steps}</ol></div></div>')


def p_gallery(sec, ctx):
    def tile(it):
        art = widgets.photo(it, "m42-gallery-photo") or f'<div class="m42-ph"><i class="bi {icon(it.get("icon"), "bi-image")}"></i></div>'
        return f'<figure>{art}<figcaption>{e(it.get("title"))}</figcaption></figure>'
    return head(sec) + f'<div class="m42-gallery">{"".join(tile(it) for it in sec.get("items") or [])}</div>'


def p_specs(sec, ctx):
    """A product page's numbers as a spec sheet: name on the left, value on the right, thin lines (no "5 Version"
    tiles: a word unit reads as text)."""
    rows = []
    for it in sec.get("items") or []:
        unit, val, txt = str(it.get("unit") or ""), it.get("value"), str(it.get("text") or "")
        num = "" if val in (None, "") else (f"{val:g}" if isinstance(val, (int, float)) else str(val))
        if re.fullmatch(r"[A-Za-z][A-Za-z ]{3,}", unit) and txt:
            shown = txt  # ("4 Rating" for water resistance: its text says IPX4)
        else:
            shown = (f"{num}{'' if not unit or unit in ('%', '★') else ' '}{unit}" if num else txt) or txt
        rows.append(f'<div><dt>{e(it.get("title"))}</dt><dd>{e(shown)}</dd></div>')
    return head(sec) + f'<dl class="m42-specs">{"".join(rows)}</dl>'


def p_stats(sec, ctx):
    if ARCH["arch"] == "product" and not ctx.get("live") and sec.get("items"):
        return p_specs(sec, ctx)
    if ctx.get("live"):  # a dashboard: stat cards that M42 UI fills (demo values here)
        cards, feeds = [], []
        for it in sec.get("items") or []:
            sid = slug(it.get("title") or "stat", ctx["ids"])
            cards.append(f'<div class="m42-stat" id="{sid}" data-label="{e(it.get("title"))}" data-unit="{e(it.get("unit") or "")}"'
                         f' data-icon="{icon(it.get("icon"), "bi-graph-up")}"></div>')
            v = float(it.get("value") or 50)
            whole = v == int(v) and not ctx.get("device")  # a count of orders / staff / units: no 5.6 staff
            feeds.append(f"M42UI.demo('{sid}', {v}, {max(1.0, abs(v) * .08):.1f}{', 0' if whole else ''});")
        ctx["feeds"] += feeds
        return head(sec) + f'<div class="m42-grid">{"".join(cards)}</div>'
    def count(it):  # a currency goes before the number (₹1,82,000), any other unit after it (98%)
        unit = it.get("unit") or ""
        pre = unit if unit in ("₹", "$", "€", "£", "¥") else ""
        unit = (" " + unit) if re.fullmatch(r"[A-Za-z]{3,}.*", unit) else unit  # 100 free, not 100free
        return (f'<span data-m42-count="{e(it.get("value") or 0)}" data-prefix="{e(pre)}" '
                f'data-suffix="{e("" if pre else unit)}">0</span>')
    nums = "".join(f'<div class="col-6 col-md-3"><div class="m42-card text-center"><div class="display-6 fw-bold">'
                   f'{count(it)}</div>'
                   f'<div class="m42-muted">{e(it.get("title"))}</div></div></div>' for it in sec.get("items") or [])
    return head(sec) + f'<div class="row g-4">{nums}</div>'


def p_chart(sec, ctx):
    cid = slug("trend", ctx["ids"])
    names = [it.get("title") for it in (sec.get("items") or [])][:3] or ["Value"]
    bases = [float(it.get("value") or 50) for it in (sec.get("items") or [])][:3] or [50.0]
    ctx["feeds"].append(f"M42UI.demo('{cid}', {json.dumps(bases)}, 6);")
    return head(sec) + (f'<div class="m42-chart" id="{cid}" data-label="{e(sec.get("title") or "Trend")}" '
                        f'data-series="{e(",".join(names))}"></div>')


TONES = (("is-bad", r"cancel|fail|out of stock|overdue|refund|reject|inactive|offline|blocked|expired|unpaid|closed"),
         ("is-warn", r"pending|processing|low|due|waiting|review|hold|partial|draft|limited|break|busy"),
         ("is-good", r"paid|deliver|done|complete|active|in stock|success|open|online|approved|shipped|available|confirmed|new"))


def badge(text):
    """A status word in its colour: Delivered green, Pending amber, Cancelled red (the words themselves, any site)."""
    tone = next((c for c, rx in TONES if re.search(rx, str(text or ""), re.I)), "")
    return f'<span class="m42-badge{" " + tone if tone else ""}">{e(text)}</span>'


def amount(v, unit=""):
    """A value with its unit: ₹ before the number, any other unit after it (12 kg, 98%)."""
    s = money(v, unit)
    if unit and PRODUCT_UNIT_RX.fullmatch(unit.strip()):
        return f"{s} / {e(unit.strip())}"  # ₹25 / each
    return s if s.startswith(("₹", "$", "€", "£", "¥")) or not unit else f"{s} {e(unit)}"


def _as_float(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def p_table(sec, ctx):
    """Rows from whatever the items hold: title, meta cells, else text, the value with its unit, the badge (the 4B
    gave a product table only titles and values, and the table showed one column of names)."""
    items = sec.get("items") or []
    # facts written "Printer: A1" in every row: "Printer" is the column's name, "A1" its cell; a fact that is the row's
    # price or status again ("₹450", "Status: Printing" beside the ₹450 and the Printing pill) is left out (a real
    # 3D shop table had an unnamed column and its price twice, 2026-11-12)
    width = max((len(it.get("meta") or []) for it in items), default=0)
    keys, drop = {}, set()
    for j in range(width):
        col = [str((it.get("meta") or [])[j]) if j < len(it.get("meta") or []) else "" for it in items]
        split = [re.match(r"\s*([A-Za-z][\w /]{0,18}):\s*(.+)", c) for c in col]
        if all(split):
            keys[j] = split[0][1].strip() if len({m[1].strip().lower() for m in split}) == 1 else ""
            col = [m[2].strip() for m in split]
        def same(c, it):  # the row's status pill, or its amount, again
            if c.strip().lower() == str(it.get("badge") or "").strip().lower():
                return True
            digits = re.sub(r"[^\d.]", "", c.replace(",", ""))
            nums = [it.get("value")]  # (the drawn amount only: "values" is no column of the table)
            # a number with its money sign or a short unit ("₹450", "0.5 kg", "85 %") that is the row's drawn value
            return bool(digits) and bool(re.fullmatch(r"\s*[₹$€£]?\s*[\d,.]+\s*[A-Za-z%]{0,4}\.?\s*", c)) \
                and any(n not in (None, "") and _as_float(n) == _as_float(digits) for n in nums)
        if all(same(c, it) for c, it in zip(col, items) if c) and any(col):
            drop.add(j)
            name = keys.get(j) or (list(sec.get("labels") or []) + [""] * (j + 2))[j + 1]
            if name and not all(c.strip().lower() == str(it.get("badge") or "").strip().lower() for c, it in zip(col, items) if c):
                sec = dict(sec, _value_label=name)  # the value's column keeps the name its cells had ("Weight")
        elif j in keys:
            items = [dict(it, meta=[(c if k == j else m) for k, m in enumerate(it.get("meta") or [])]) for it, c in zip(items, col)]
    if keys or drop:
        given = list(sec.get("labels") or [])
        items = [dict(it, meta=[m for j, m in enumerate(it.get("meta") or []) if j not in drop]) for it in items]
        heads = ["Name"] + [keys.get(j) or "" for j in range(width)] if not given else given[:1 + width] + [""] * max(0, 1 + width - len(given))
        sec = dict(sec, items=items, labels=[h for k, h in enumerate(heads) if k - 1 not in drop] + given[1 + width:])
    # a fact that is the row's status again (the 4B wrote "Pending" as a fact and as the pill): the column shown once
    if any(it.get("badge") for it in items):
        width = max((len(it.get("meta") or []) for it in items), default=0)
        same = [j for j in range(width) if all(str((it.get("meta") or [None] * width)[j] if j < len(it.get("meta") or []) else "").strip().lower()
                                               == str(it.get("badge") or "").strip().lower() for it in items)]
        if same:
            items = [dict(it, meta=[m for j, m in enumerate(it.get("meta") or []) if j not in same]) for it in items]
            labels = list(sec.get("labels") or [])
            sec = dict(sec, items=items, labels=[c for j, c in enumerate(labels) if j - 1 not in same])
    metas = max((len(it.get("meta") or []) for it in items), default=0)
    texts = not metas and any(it.get("text") for it in items)
    values = any(it.get("value") not in (None, "") for it in items)
    badges = any(it.get("badge") for it in items)
    unit = next((it.get("unit") for it in items if it.get("unit")), "")
    auto = (["Name"] + ["Details"] + [""] * (metas - 1) + (["Details"] if texts else [])
            + ([sec.get("_value_label") or ("Price" if not unit or "₹" in unit else unit.title())] if values else []) + (["Status"] if badges else []))
    labels = list(sec.get("labels") or [])
    cols = labels + auto[len(labels):] if len(labels) < len(auto) else labels[:max(len(auto), 2)]
    # the 4B's column names in its own order ("..., Status, Total") over cells drawn as "..., amount, status": each name
    # moved over its cells (POS run 4: "table headers not aligned with the data rows", 2026-11-15)
    pos_v = 1 + metas + (1 if texts else 0) if values else None
    pos_b = 1 + metas + (1 if texts else 0) + (1 if values else 0) if badges else None
    for pos, rx in ((pos_b, r"status|state|stage"), (pos_v, r"total|amount|price|value|cost|fee|sum|₹|rs|paid|balance")):
        if pos is not None and pos < len(cols) and not re.search(rx, str(cols[pos]), re.I):
            k = next((j for j, c in enumerate(cols) if j != pos and j > 0 and re.search(rx, str(c), re.I)), None)
            if k is not None:
                cols[pos], cols[k] = cols[k], cols[pos]

    def cells(it):
        out = [e(it.get("title"))] + [e(m) for m in list(it.get("meta") or [])[:metas]]
        out += [""] * (1 + metas - len(out))
        out += [e(it.get("text"))] if texts else []
        out += [amount(it.get("value"), it.get("unit") or "") if it.get("value") not in (None, "") else ""] if values else []
        out += [badge(it["badge"]) if it.get("badge") else ""] if badges else []
        return out + [""] * (len(cols) - len(out))
    status = [bool(re.search(r"status|state|stage", str(c), re.I)) for c in cols]  # Shipped / Pending as coloured pills

    def cell(c, i):
        return badge(_html.unescape(c)) if i < len(status) and status[i] and c and "<" not in c else c
    rows = "".join("<tr>" + "".join(f"<td>{cell(c, i)}</td>" for i, c in enumerate(cells(it)[:len(cols)])) + "</tr>" for it in items)
    return head(sec) + (f'<div class="table-responsive"><table class="m42-table"><thead><tr>'
                        + "".join(f"<th>{e(c)}</th>" for c in cols) + f"</tr></thead><tbody>{rows}</tbody></table></div>")


# the shape the page's spec gave a section in its own words (2026-11-12: a fire crackers spec asked for "a horizontal
# carousel", "an accordion list" and "a multi-step form"; the page drew a grid, a row of steps and a one-step form)
SHAPE_RX = [("carousel", r"carousel|slider|slide ?show|swipe|scroll\w* horizontal|horizontal\w*\W+(?:\w+\W+){0,2}scroll"),
            ("accordion", r"accordion|collaps\w*|expand\w* (?:list|panel|section)"),
            ("multistep", r"multi-?step|wizard|step[- ]by[- ]step form|form in (?:\w+ )?steps")]


def _label_like(name):
    """A name a visitor can read in the menu: not an identifier ("popular_dishes") nor a bare lower-case word ("about"),
    which the 4B sometimes gives as a section's name (a restaurant build, 2026-11-14): the menu then shows the title."""
    n = str(name or "").strip()
    return bool(n) and "_" not in n and n != n.lower()


def shape_of(text):
    return next((k for k, rx in SHAPE_RX if re.search(rx, str(text or ""), re.I)), "")


def p_carousel(sec, ctx):
    """A row that scrolls sideways (snapping card by card, arrows on the sides): gallery photos, products, rooms."""
    def card(it, k):
        pic = (widgets.photo(it, "m42-car-photo") or
               f'<div class="m42-car-art" style="--k:{k % 3}"><i class="bi {icon(it.get("icon"), icon(ctx.get("brand_icon")))}"></i></div>')
        price = (f'<div class="m42-car-price">{amount(it.get("value"), it.get("unit") or "")}</div>'
                 if it.get("value") not in (None, "", 0, 0.0) and sec.get("part") != "reviews" else "")
        return (f'<figure class="m42-car-item">{pic}<figcaption><h3>{e(it.get("title"))}</h3>'
                + (f'<p>{e(it.get("text"))}</p>' if it.get("text") else "") + f"{price}</figcaption></figure>")
    cards = "".join(card(it, k) for k, it in enumerate(sec.get("items") or []))
    return (head(sec) + '<div class="m42-carousel" data-m42-carousel>'
            '<button type="button" class="m42-car-btn is-prev" aria-label="Previous" data-car="-1"><i class="bi bi-chevron-left"></i></button>'
            f'<div class="m42-car-track" tabindex="0">{cards}</div>'
            '<button type="button" class="m42-car-btn is-next" aria-label="Next" data-car="1"><i class="bi bi-chevron-right"></i></button></div>')


def p_accordion(sec, ctx):
    """Steps or points asked for as an accordion: numbered, one open at a time."""
    its = [dict(it, title=f'{k + 1}. {STEP_NO_RX.sub("", str(it.get("title") or ""))}') for k, it in enumerate(sec.get("items") or [])]
    return p_faq(dict(sec, items=its), ctx)


def p_form_steps(sec, ctx):
    """A form asked for in steps: its fields two or three a step, Back / Next, the send button on the last one."""
    fields = sec.get("fields") or []
    size = 2 if len(fields) <= 6 else 3
    chunks = [fields[i:i + size] for i in range(0, len(fields), size)]
    if len(chunks) < 2:
        return head(sec) + p_form(sec, ctx)
    used = ctx["ids"]
    heads = "".join(f'<li class="{"active" if k == 0 else ""}"><span>{k + 1}</span>{e(ch[0].get("label") or f"Step {k + 1}")}</li>'
                    for k, ch in enumerate(chunks))
    panes = "".join(f'<div class="m42-w-pane{" active" if k == 0 else ""}"><div class="row g-3">'
                    + "".join(field_html(f, sec["_id"], used, "col-md-6" if f.get("type") != "textarea" else "col-12") for f in ch)
                    + (f'<div class="col-12"><button class="m42-btn w-100">{e(sec.get("button") or "Submit")}</button></div>'
                       if k == len(chunks) - 1 else "") + "</div></div>" for k, ch in enumerate(chunks))
    return (head(sec) + f'<form class="m42-form m42-card mx-auto" style="max-width:760px" '
            f'data-m42-done="{e(sec.get("lead") or "Done! We will contact you shortly.")}">'
            f'<div class="m42-w-stepper m42-form-steps" data-m42-stepper><ol>{heads}</ol>{panes}'
            '<div class="d-flex gap-2 justify-content-end mt-3"><button type="button" class="m42-btn-ghost" data-go="-1">Back</button>'
            '<button type="button" class="m42-btn" data-go="1">Next <i class="bi bi-arrow-right"></i></button></div></div></form>')


SHAPED = {("carousel", "gallery"): p_carousel, ("carousel", "image_cards"): p_carousel, ("carousel", "cards"): p_carousel,
          ("carousel", "reviews"): p_carousel, ("accordion", "steps"): p_accordion, ("accordion", "cards"): p_accordion,
          ("accordion", "faq"): lambda s, c: p_faq(s, c), ("multistep", "form"): p_form_steps, ("multistep", "contact"): p_form_steps}


def p_faq(sec, ctx):
    aid = sec["_id"] + "-acc"
    items = "".join(f'<div class="accordion-item"><h3 class="accordion-header"><button class="accordion-button{"" if n == 0 else " collapsed"}" '
                    f'type="button" data-bs-toggle="collapse" data-bs-target="#{aid}-{n}">{e(it.get("title"))}</button></h3>'
                    f'<div id="{aid}-{n}" class="accordion-collapse collapse{" show" if n == 0 else ""}" data-bs-parent="#{aid}">'
                    f'<div class="accordion-body">{e(it.get("text"))}</div></div></div>'
                    for n, it in enumerate(sec.get("items") or []))
    return head(sec) + f'<div class="accordion mx-auto" style="max-width:820px" id="{aid}">{items}</div>'


def p_tabs(sec, ctx):
    groups = []
    for it in sec.get("items") or []:
        g = it.get("group") or "All"
        if g not in groups:
            groups.append(g)
    tid = sec["_id"] + "-tabs"
    pills = "".join(f'<li class="nav-item"><button class="nav-link{" active" if n == 0 else ""}" data-bs-toggle="pill" '
                    f'data-bs-target="#{tid}-{n}" type="button">{e(g)}</button></li>' for n, g in enumerate(groups))
    panes = []
    for n, g in enumerate(groups):
        cards = "".join(f'<div class="col-md-6"><div class="m42-item"><div><h3>{e(it.get("title"))}'
                        + (f' <span class="m42-badge">{e(it["badge"])}</span>' if it.get("badge") else "")
                        + f'</h3><div class="m42-meta">{e(it.get("text"))}</div></div><div></div>'
                        f'<div class="m42-price-tag">{money(it.get("value"), it.get("unit") or "₹")}</div></div></div>'
                        for it in sec.get("items") or [] if (it.get("group") or "All") == g)
        panes.append(f'<div class="tab-pane fade{" show active" if n == 0 else ""}" id="{tid}-{n}"><div class="row g-3">{cards}</div></div>')
    return (head(sec) + f'<ul class="nav nav-pills justify-content-center mb-4">{pills}</ul>'
            f'<div class="tab-content">{"".join(panes)}</div>')


def p_cta(sec, ctx):
    photo = ctx.get("hero_photo")
    if ARCH["arch"] == "portfolio":  # a big line and a link, no band
        return (f'<div class="m42-cta is-portfolio"><h2>{e(sec.get("title"))}</h2><p>{e(sec.get("lead"))}</p>'
                f'<a class="m42-pf-link" href="#{e(ctx.get("first_id", ""))}">{e(sec.get("button") or "Get in touch")} '
                '<i class="bi bi-arrow-right"></i></a></div>')
    if ARCH["arch"] in ARCHES:
        return (f'<div class="m42-cta is-{ARCH["arch"]}"><h2>{e(sec.get("title"))}</h2><p>{e(sec.get("lead"))}</p>'
                f'<div class="m42-actions justify-content-center"><a class="m42-btn" href="#{e(ctx.get("first_id", ""))}">'
                f'{e(sec.get("button") or "Get started")}</a></div></div>')
    if photo and variant(ctx, "cta", 2) == 1:  # the band beside the site's photo
        return (f'<div class="m42-cta is-split"><div><h2>{e(sec.get("title"))}</h2><p>{e(sec.get("lead"))}</p>'
                f'<a class="m42-btn" href="#{e(ctx.get("first_id", ""))}">{e(sec.get("button") or "Get started")}</a></div>'
                f'{widgets.photo({"photo": photo, "title": sec.get("title")}, "m42-cta-photo")}</div>')
    return (f'<div class="m42-cta"><h2>{e(sec.get("title"))}</h2><p>{e(sec.get("lead"))}</p>'
            f'<div class="m42-actions justify-content-center"><a class="m42-btn" href="#{e(ctx.get("first_id", ""))}">'
            f'{e(sec.get("button") or "Get started")}</a></div></div>')


def p_about(sec, ctx):
    points = "".join(f'<li><b>{e(it.get("title"))}</b> {e(it.get("text"))}</li>' for it in sec.get("items") or [])
    if ARCH["arch"] == "editorial":
        return (head(sec) + f'<div class="row g-5"><div class="col-lg-7"><ul class="m42-list">{points}</ul></div>'
                f'<div class="col-lg-5"><blockquote class="m42-ed-pull">{e(sec.get("lead") or sec.get("title"))}</blockquote></div></div>')
    return (f'<div class="row g-5 align-items-center"><div class="col-lg-6">{head(sec, center=False)}'
            f'<ul class="m42-list">{points}</ul></div><div class="col-lg-6">{about_visual(sec, ctx)}</div></div>')


DOODLES = Path(__file__).resolve().parent / "bundled" / "doodles"  # Open Doodles by Pablo Stanley, CC0 (opendoodles.com)


def doodles():
    return sorted(p.stem for p in DOODLES.glob("*.svg"))


def doodle_svg(name):
    """An Open Doodle inline, in the page's colours: its pink (#FF5678) is the brand's accent, its black lines the
    text colour, so it follows light / dark. "" when there is none of that name."""
    f = DOODLES / f"{name}.svg"
    if not name or not f.exists():
        return ""
    svg = f.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*>|<!--.*?-->|<title>.*?</title>|<desc>.*?</desc>", "", svg, flags=re.S)
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)
    svg = re.sub(r'fill="#FF5678"', 'fill="var(--m42-accent)"', svg, flags=re.I)
    svg = re.sub(r'(fill|stroke)="#(000000|000)"', r'\1="var(--m42-text)"', svg, flags=re.I)
    svg = re.sub(r'(fill|stroke)="#(FFFFFF|FFF)"', r'\1="var(--m42-surface)"', svg, flags=re.I)
    svg = re.sub(r"\s(id|xlink:href)=\"[^\"]*\"", "", svg)  # (two doodles on a page would share their ids)
    return svg.replace("<svg ", '<svg class="m42-doodle" role="img" aria-label="Illustration" ', 1).strip()


HUMAAANS = Path(__file__).resolve().parent / "bundled" / "humaaans"  # Humaaans by Pablo Stanley (humaaans.com)


def humaaan_svg(place, key):
    """A Humaaans person in the page's colours (its blue clothes in the accent): standing at the top, sitting in the
    About; which one from the site's name, so a page built again keeps it. "" when there are none."""
    files = sorted(HUMAAANS.glob(("sitting" if place == "about" else "standing") + "-*.svg"))
    if not files:
        return ""
    f = files[int(hashlib.md5(f"{key}|{place}".encode()).hexdigest(), 16) % len(files)]
    svg = f.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*>|<!--.*?-->|<title>.*?</title>|<desc>.*?</desc>", "", svg, flags=re.S)
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)
    svg = re.sub(r'fill="#(1F28CF|2B44FF|4059FF|5C63AB)"', 'fill="var(--m42-accent)"', svg, flags=re.I)
    svg = re.sub(r"\s(id|xlink:href)=\"[^\"]*\"", "", svg)
    return ("<!-- Illustration: Humaaans by Pablo Stanley, humaaans.com -->"
            + svg.replace("<svg ", '<svg class="m42-humaaan" role="img" aria-label="Illustration of a person" ', 1).strip())


def art(ctx, brand_icon, place="hero"):
    """The picture of a showcase with no photo: the page's doodle (the 4B's pick, agent._motion: a line drawing for a
    warm, playful page); with none chosen (a clinic, finance, a SaaS page) a Humaaans person on a site page; on an
    app page its icon."""
    svg = doodle_svg(ctx.get("doodle") or "")
    if svg:
        return f'<div class="m42-showcase-art has-doodle">{svg}</div>'
    if ctx.get("people_ok"):
        svg = humaaan_svg(place, ctx.get("site_key") or "")
        if svg:
            return f'<div class="m42-showcase-art has-humaaan">{svg}</div>'
    return f'<div class="m42-showcase-art m42-ph"><i class="bi {brand_icon}"></i></div>'


def about_visual(sec, ctx):
    checks = "".join(f'<li><i class="bi bi-check-circle-fill"></i>{e(it.get("title"))}</li>' for it in (sec.get("items") or [])[:3])
    return (f'<div class="m42-showcase">{art(ctx, icon(ctx["brand_icon"]), "about")}'
            + (f'<div class="m42-float is-a"><ul class="m42-checks">{checks}</ul></div>' if checks else "") + "</div>")


def showcase(plan, ctx):
    """The hero's picture without a photo: the site's own content as layered glass cards over a mesh of its
    colours, the way design shots show a product (an item with its price, the rating with faces, a number)."""
    secs, brand_icon = plan["sections"], icon(ctx["brand_icon"])
    priced = [it for s in secs if s["part"] in ("results", "tabs", "cards", "prices", "table", "image_cards") for it in s["items"]
              if it.get("value") not in (None, "", 0, 0.0) and it.get("title")]
    item = next((it for it in priced if it.get("badge")), priced[0] if priced else None)
    item = item or next((it for s in secs if s["part"] not in ("stats", "reviews", "faq", "form", "logos", "team", "comments", "newsletter")
                         for it in s["items"]
                         if it.get("title")), None)
    floats = []
    if item:
        sub = (item.get("meta") or [""])[0] or str(item.get("text") or "")[:42]
        floats.append(f'<div class="m42-float is-a"><span class="m42-chip"><i class="bi {icon(item.get("icon"), brand_icon)}"></i></span>'
                      f'<div><strong>{e(item.get("title"))}</strong>' + (f'<small>{e(sub)}</small>' if sub else "") + "</div>"
                      + (f'<div class="m42-big ms-auto ps-2">{amount(item.get("value"), item.get("unit") or "")}</div>'
                         if item.get("value") not in (None, "") else "") + "</div>")
    revs = [it for s in secs if s["part"] == "reviews" for it in s["items"]]
    if revs:
        try:
            avg = sum(float(r.get("value") or 5) for r in revs) / len(revs)
        except (TypeError, ValueError):
            avg = 5.0
        faces = "".join(f'<span>{e("".join(w[0] for w in str(r.get("title") or "G").split()[:2]).upper())}</span>' for r in revs[:3])
        names = ", ".join(str(r.get("title") or "").split()[0] for r in revs[:2] if r.get("title"))
        floats.append(f'<div class="m42-float is-b"><div class="m42-avatars">{faces}</div><div><strong>★ {min(avg, 5):.1f} rating</strong>'
                      f'<small>{e(names)} &amp; more</small></div></div>')
    elif plan["hero"].get("eyebrow"):
        floats.append(f'<div class="m42-float is-b"><span class="m42-chip"><i class="bi bi-patch-check-fill"></i></span>'
                      f'<div><strong>{e(plan["hero"]["eyebrow"])}</strong></div></div>')
    st = (plan["hero"].get("stats") or [None])[0]
    if st and st.get("value") not in (None, ""):
        suf = str(st.get("suffix") or "")
        try:
            v = float(st["value"])
            num = f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"
        except (TypeError, ValueError):
            num = str(st["value"])
        num = f"{suf}{num}" if suf in ("₹", "$", "€", "£") else f"{num}{suf}"
        bars = "".join(f'<i style="height:{h}%"></i>' for h in (38, 62, 48, 80, 66, 100))
        floats.append(f'<div class="m42-float is-c"><div><div class="m42-big">{e(num)}</div><small>{e(st.get("label"))}</small></div>'
                      f'<div class="m42-bars">{bars}</div></div>')
    return f'<div class="m42-showcase">{art(ctx, brand_icon)}' + "".join(floats) + "</div>"


def p_search(sec, ctx):
    used = ctx["ids"]
    fields = "".join(field_html(f, sec["_id"], used) for f in sec.get("fields") or [])
    return head(sec) + (f'<form class="m42-search" data-m42-search-for="{e(ctx.get("results_id_hint", ""))}">{fields}'
                        f'<div><button class="m42-btn w-100"><i class="bi bi-search"></i> {e(sec.get("button") or "Search")}'
                        "</button></div></form>")


def p_custom(sec, ctx):
    """A part no template covers: the coder's card (agent.custom_cards, cleaned), else its content as clean cards."""
    if sec.get("html"):
        return head(sec) + f'<div class="m42-custom">{from_tailwind(sec["html"])}</div>'
    return p_cards(sec, ctx)


# Tailwind classes the coder copies from the UIGEN examples (shown as layout ideas), as Bootstrap 5 / M42 UI ones
# (2026-11-11: an attendance page's "Admin Control Center" card came out with flex, justify-between, text-sm, rounded-xl,
# text-var(--m42-muted): none of them exist here, the card was unstyled boxes)
TW_SAME = {"flex": "d-flex", "inline-flex": "d-inline-flex", "grid": "d-grid", "hidden": "d-none", "block": "d-block",
           "inline-block": "d-inline-block", "items-center": "align-items-center", "items-start": "align-items-start",
           "items-end": "align-items-end", "justify-between": "justify-content-between", "justify-center": "justify-content-center",
           "justify-end": "justify-content-end", "justify-start": "justify-content-start", "flex-col": "flex-column",
           "flex-wrap": "flex-wrap", "flex-1": "flex-grow-1", "text-xs": "small", "text-sm": "small", "text-lg": "fs-5",
           "text-xl": "fs-4", "text-2xl": "fs-3", "text-3xl": "fs-2", "text-4xl": "fs-1", "font-bold": "fw-bold",
           "font-semibold": "fw-semibold", "font-medium": "fw-medium", "font-normal": "fw-normal", "uppercase": "text-uppercase",
           "italic": "fst-italic", "text-left": "text-start", "text-right": "text-end", "w-full": "w-100", "h-full": "h-100",
           "min-w-full": "w-100", "rounded": "rounded", "rounded-md": "rounded-2", "rounded-lg": "rounded-3", "rounded-xl": "rounded-4",
           "rounded-2xl": "rounded-4", "rounded-full": "rounded-pill", "shadow": "shadow-sm", "shadow-md": "shadow",
           "shadow-lg": "shadow-lg", "overflow-x-auto": "overflow-auto", "overflow-hidden": "overflow-hidden", "truncate": "text-truncate",
           "relative": "position-relative", "absolute": "position-absolute", "border": "border", "border-b": "border-bottom",
           "border-t": "border-top", "bg-white": "bg-white", "text-white": "text-white", "tracking-wider": "", "leading-tight": "lh-sm",
           "mx-auto": "mx-auto", "text-center": "text-center", "bg-gradient-to-r": "bg-primary bg-gradient",
           "bg-gradient-to-l": "bg-primary bg-gradient", "bg-gradient-to-b": "bg-primary bg-gradient",
           "bg-gradient-to-br": "bg-primary bg-gradient", "opacity-90": "opacity-75", "opacity-80": "opacity-75",
           "opacity-70": "opacity-75", "opacity-60": "opacity-50"}
TW_COLOUR = {"green": "success", "emerald": "success", "red": "danger", "rose": "danger", "yellow": "warning", "amber": "warning",
             "orange": "warning", "blue": "primary", "indigo": "primary", "sky": "info", "cyan": "info", "gray": "secondary",
             "slate": "secondary", "zinc": "secondary"}
TW_SPACE = {"0": "0", "1": "1", "2": "2", "3": "2", "4": "3", "5": "3", "6": "4", "8": "4", "10": "5", "12": "5", "16": "5"}


def from_tailwind(html):
    """The Tailwind classes in a card (from_tailwind('<div class="flex items-center p-4">')) as Bootstrap's; classes with a
    CSS variable inside (text-var(--m42-muted)) and Tailwind-only ones (divide-y) go."""
    def one(c):
        if "var(" in c:  # a CSS variable in a class (bg-var(--m42-accent-3)): the kit's own colour class for it
            kind = c.split("-var(")[0]
            return {"bg": "bg-primary", "border": "border", "text": "text-body-secondary" if "muted" in c else "text-primary"}.get(kind, "")
        if "(" in c or c.startswith(("from-", "to-", "via-", "divide-", "space-", "ring-", "transition", "duration-", "ease-",
                                                     "hover:", "md:", "lg:", "sm:", "focus:", "dark:", "tracking-", "leading-")):
            return ""
        if c in TW_SAME:
            return TW_SAME[c]
        m = re.fullmatch(r"(p|px|py|pt|pb|ps|pe|pl|pr|m|mx|my|mt|mb|ml|mr|gap)-(\d+)", c)
        if m and m.group(2) in TW_SPACE:
            k = {"pl": "ps", "pr": "pe", "ml": "ms", "mr": "me"}.get(m.group(1), m.group(1))
            return f"{k}-{TW_SPACE[m.group(2)]}"
        m = re.fullmatch(r"(text|bg|border)-([a-z]+)-(\d{2,3})", c)
        if m and m.group(2) in TW_COLOUR:
            tone = TW_COLOUR[m.group(2)]
            if m.group(1) == "bg":
                return f"bg-{tone}-subtle" if int(m.group(3)) <= 200 else f"bg-{tone}"
            return f"{m.group(1)}-{tone}" + ("-emphasis" if m.group(1) == "text" else "")  # (text-warning on white: 1.6:1)
        m = re.fullmatch(r"grid-cols-(\d)", c)
        if m:
            return f"row-cols-{m.group(1)}"
        return c

    def fix(m):
        out = []
        for c in m.group(2).split():
            for n in one(c).split():  # ("bg-primary bg-gradient": two)
                if n not in out:
                    out.append(n)
        if "row-cols-" in " ".join(out) and "d-grid" in out:  # a Tailwind grid: Bootstrap's row of columns
            out = ["row"] + [c for c in out if c != "d-grid"]
        return f'{m.group(1)}"{" ".join(out)}"'
    return re.sub(r'(\bclass\s*=\s*)"([^"]*)"', fix, html)


def clean_snippet(html):
    """A model's card HTML made safe to put in a page: no scripts, styles, frames, images, links out or handlers."""
    html = re.sub(r"(?is)<(script|style|iframe|object|svg|noscript)\b.*?</\1\s*>", "", str(html or ""))
    html = re.sub(r"(?is)</?(script|style|iframe|object|embed|link|meta|img|svg|noscript|form|input|base)\b[^>]*>", "", html)
    html = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html)
    html = re.sub(r"(?i)(href|src|action)\s*=\s*([\"'])\s*(javascript:|data:|https?:|//)[^\"']*\2", r'\1="#"', html)
    html = re.sub(r"(?is)</?(html|head|body)\b[^>]*>", "", html)
    return html.strip()[:8000]


PARTS = {"results": p_results, "picks": p_picks, "summary": p_summary, "form": p_form, "cards": p_cards,
         "prices": p_prices, "reviews": p_reviews, "steps": p_steps, "gallery": p_gallery, "stats": p_stats,
         "chart": p_chart, "table": p_table, "faq": p_faq, "tabs": p_tabs, "cta": p_cta, "about": p_about,
         "search": p_search, "chips": p_cards, "custom": p_custom, "contact": lambda s, c: p_form(s, c, contact=True)}
PARTS.update(widgets.WIDGETS)  # calendar, charts, donut, data table, toggles, popup... (widgets.py)
SIDE_WITH_SUMMARY = ("results", "picks", "form")  # shown left of a summary box, in one section


# ---- the page ---------------------------------------------------------------------------------------------

NUMBER_RX = re.compile(r"^\s*(₹|\$|€|£|Rs\.?)?\s*(\d[\d,]*(?:\.\d+)?)\s*([%+★]|[A-Za-z][A-Za-z ]{0,13})?\s*$")
PLACEHOLDER_RX = re.compile(r"^\s*(enter|select|choose|type|pick|search)\b|\.\.\.\s*$|^\s*(0|0\.0+|-+|_+)\s*$", re.I)
FIELD_TYPES = ((r"password|\bpin\b", "password"), (r"date|day|dob", "date"), (r"e-?mail", "email"), (r"phone|mobile|contact no", "tel"),
               (r"price|qty|quantity|stock|amount|count|age|no\.? of", "number"), (r"categor|type|status|role|gender", "select"),
               (r"note|address|message|description|comment", "textarea"))


def _as_number(text):
    """"₹4,25,000" -> (425000, "₹"); "84" -> (84, ""); "2 units left" -> (2, "units left"); None for words."""
    m = NUMBER_RX.match(str(text or ""))
    if not m:
        return None
    v = float(m.group(2).replace(",", ""))
    return (int(v) if v == int(v) else v), ("₹" if (m.group(1) or "").startswith("R") else m.group(1) or m.group(3) or "")


def _as_field(it):
    label = str(it.get("title") or "Field")[:24]
    kind = next((t for rx, t in FIELD_TYPES if re.search(rx, label, re.I)), "text")
    opts = [o.strip()[:24] for o in str(it.get("text") or "").split(",") if o.strip()]
    if len(opts) >= 2 and not PLACEHOLDER_RX.search(str(it.get("text") or "")):  # "Electronics, Fashion, Home"
        return {"label": label, "type": "select", "options": opts[:6]}
    return {"label": label, "type": kind}


PAIR_RX = re.compile(r"([A-Za-z][\w .#()/-]{0,20}):\s*([^|;:]+?)\s*(?=$|[|;]|,\s*[A-Za-z][\w .#()/-]{0,20}:)")


def _pairs(text):
    """"Customer: Rahul Kumar | Items: 3" -> [("Customer", "Rahul Kumar"), ("Items", "3")]."""
    return [(k.strip(), v.strip(" ,")) for k, v in PAIR_RX.findall(str(text or ""))]


def _fit(s):
    """The part a section's own content is: the 4B planner put stats ("₹4,25,000" in text), form fields ("Enter
    name...") and alerts all in "about" boxes with an empty picture (an admin page, 2026-10-27). None: no sign."""
    items = s["items"]

    def input_like(t):  # "Enter name...", "0.00", or the options of a select ("Electronics, Fashion, Home")
        t = str(t or "")
        return bool(PLACEHOLDER_RX.search(t)) or (not _pairs(t) and len([o for o in t.split(",") if 0 < len(o.strip()) <= 18]) >= 3)
    if len(s.get("fields") or []) >= 2 or (len(items) >= 2 and sum(input_like(i.get("text")) for i in items) * 2 >= len(items)):
        return "form"
    if len(items) >= 2 and all(i.get("value") not in (None, "") or _as_number(i.get("text")) for i in items):
        return "stats"
    if len(s.get("labels") or []) >= 2 and any(i.get("meta") for i in items):
        return "table"
    if len(items) >= 2 and sum(bool(_pairs(i.get("text"))) for i in items) * 2 > len(items):  # rows of "Stock: 12"
        return "table"
    return None


def _feeds(part, s):
    """The section has what that part's template needs (a stats part with no numbers would show zeros)."""
    items = s["items"]
    return {"stats": lambda: _fit(dict(s, fields=[])) == "stats", "form": lambda: bool(s.get("fields")) or _fit(s) == "form",
            "table": lambda: bool(items), "picks": lambda: bool(s.get("labels")), "results": lambda: bool(items),
            "chart": lambda: bool(items)}.get(part, lambda: True)()


def _reshape(s, part):
    """The section's content moved to where `part` reads it."""
    if part == "form" and not s.get("fields"):
        s["fields"] = [_as_field(i) for i in s["items"]][:6]
        s["items"] = []
    if part == "table" and not any(i.get("meta") for i in s["items"]) and any(_pairs(i.get("text")) for i in s["items"]):
        keys = []
        for i in s["items"]:
            keys += [k for k, _ in _pairs(i.get("text")) if k not in keys]
        keys = keys[:4]
        for i in s["items"]:
            got = dict(_pairs(i.get("text")))
            i["meta"], i["text"] = [got.get(k, "") for k in keys], ""
        s["labels"] = [(s.get("labels") or ["Name"])[0]] + keys
    elif part == "table" and any(i.get("meta") for i in s["items"]):
        # cells written as "Status: Pending": a column whose cells all name the same thing gets it as its header
        # (a real run's table read "Name / Details / Details / Details" with "Status: Done" in the cells)
        width = max(len(i.get("meta") or []) for i in s["items"])
        labels = list(s.get("labels") or [])
        heads = [labels[0] if labels else "Name"]
        for j in range(width):
            cells = [str((i.get("meta") or [""] * width)[j] if j < len(i.get("meta") or []) else "") for i in s["items"]]
            keys = {k for c in cells if c for k, _ in _pairs(c)[:1]}
            same = len(keys) == 1 and all(len(_pairs(c)) == 1 for c in cells if c)
            if same:
                key = keys.pop()
                for i in s["items"]:
                    m = list(i.get("meta") or [])
                    if j < len(m) and m[j]:
                        m[j] = _pairs(m[j])[0][1]
                    i["meta"] = m
            given = labels[j + 1] if j + 1 < len(labels) else ""
            heads.append(key if same else given if given and given.lower() != "details" else
                         "Time" if all(re.fullmatch(r"\d{1,2}[:.]\d{2}\s*(am|pm)?", c, re.I) for c in cells if c) else "")
        s["labels"] = heads + labels[len(heads):]  # the given names of the columns after the cells (Amount, Status)
    if part == "stats":
        for i in s["items"]:
            if i.get("value") in (None, "") and _as_number(i.get("text")):
                i["value"], unit = _as_number(i.get("text"))
                i["unit"] = i.get("unit") or unit
    return s


def _no_tags(v):
    """Every text without HTML: the plan is content, the templates make the markup (a hero accent came as "boost
    <b>", cut at its maxLength, and showed the tag)."""
    if isinstance(v, dict):
        return {k: (x if k == "html" else _no_tags(x)) for k, x in v.items()}  # html: a cleaned card (clean_snippet)
    if isinstance(v, list):
        return [_no_tags(x) for x in v]
    if isinstance(v, str):
        if "<" in v or "&lt;" in v:
            v = " ".join(re.sub(r"<[^>]*>?|&lt;/?[a-z][^&]*&gt;", " ", v).split())
        # a colour code where words belong ("Welcome back, #00b09b": the hero's accent, a real run); "#402" stays
        if "#" in v:
            cut = re.sub(r"#(?=[0-9a-f]*[a-f])[0-9a-f]{6}\b|#(?=[0-9a-f]*[a-f])[0-9a-f]{3}\b", " ", v, flags=re.I)
            if cut != v:
                v = " ".join(cut.split()).rstrip(" ,;:-")
        return v
    return v


# parts whose things are the page's own things by nature (a POS bill holds the products of the grid beside it; an order's
# steps, a shipment's): never dropped as "the same things again" (a POS bill vanished that way, 2026-11-15)
SHARES_ITEMS = ("invoice", "order_tracker", "summary", "picks")


def clean(plan, spec):
    """The model's plan made safe: known parts only, the spec's hero kind, at least the spec's sections. A part
    that doesn't fit the section's content is changed: first what the content itself is (numbers -> stats, input
    placeholders -> a form), else the part the spec asked for; on an app page (compact / no hero) an "about" box
    has no big empty picture, so it becomes cards."""
    plan = _no_tags(plan if isinstance(plan, dict) else {})
    plan = privacy.scrub_obj(plan)  # no personal details (phone, e-mail, address, Aadhaar, PAN): example ones
    wanted = [x.get("part") for x in (spec or {}).get("sections") or [] if isinstance(x, dict)]
    app_page = (spec or {}).get("hero") in ("compact", "none")
    secs = []
    for n, s in enumerate(x for x in plan.get("sections") or [] if isinstance(x, dict)):
        part = s.get("part") if s.get("part") in PARTS else "custom"
        s = dict(s, items=[dict(i) for i in s.get("items") or [] if isinstance(i, dict)])
        for i in s["items"]:  # "₹/shirt" as a price's unit read "₹499₹/shirt": the money sign is the page's own
            if isinstance(i.get("unit"), str) and re.match(r"\s*[₹$€£¥]\s*\S", i["unit"]):
                i["unit"] = i["unit"].lstrip("₹$€£¥ ")
        s["fields"] = [dict(f, type="password") if re.search(r"password|\bpin\b", str(f.get("label")), re.I) else f
                       for f in s.get("fields") or [] if isinstance(f, dict)]  # a "Password" box typed as text
        want = wanted[n] if n < len(wanted) and wanted[n] in PARTS and wanted[n] != "custom" else None
        if part in ("about", "custom", "cards") or (want and part != want and not _feeds(part, s)):
            fit = _fit(s)
            part = fit or (want if want and _feeds(want, s) else part)
        if part == "about" and app_page:
            part = "cards"
        if (spec or {}).get("recipe") and want and part != want and _feeds(want, s):
            part = want  # M42's own section order for this kind of site (recipes.py): the part it names
        if want == "composed" and (spec or {}).get("ref_grid"):
            part = "composed"  # the reference's own card, drawn from its blocks: the plan gives its words, not its kind
        if want in ("chat_app", "mail_app"):  # an app view M42 put on this page (uiflows.app_pages): with its flow
            part = want
            s["_flow"] = (((spec or {}).get("sections") or [])[n] or {}).get("flow") or {}
        sp = ((spec or {}).get("sections") or [])
        if n < len(sp) and isinstance(sp[n], dict) and sp[n].get("asked_part") and want:
            part = want  # 🧩 the user asked for THIS part (a "Chart.js bar chart of sales"): theirs first; it became a
            s["_asked_part"] = True  # stats row, then photo cards, then a rating block, and no chart (2026-11-17)
        if n < len(sp) and isinstance(sp[n], dict) and sp[n].get("role"):  # 🧩 its role in the page's flow (its blocks follow it)
            s["_role"] = sp[n]["role"]
        if n < len(sp) and isinstance(sp[n], dict) and sp[n].get("slot"):  # 🦴 its place in the app's skeleton (row, column)
            s["_slot"] = list(sp[n]["slot"])
            if sp[n].get("main"):
                s["_main"] = True
        if n < len(sp) and isinstance(sp[n], dict) and shape_of(f'{sp[n].get("name", "")} {sp[n].get("what", "")}'):
            s["_shape"] = shape_of(f'{sp[n].get("name", "")} {sp[n].get("what", "")}')
        if part in ("modal", "empty_state", "alerts", "dropdown_filter", "breadcrumb") and not s.get("fields") and (
                part == "modal" or len(s["items"]) >= 3):
            # (a popup / an empty box / a row of alert buttons with nothing of its own to show)
            words = f"{s.get('title', '')} {s.get('eyebrow', '')}"
            priced = any(i.get("value") not in (None, "") for i in s["items"])
            part = ("form" if FORM_RX.search(words) and not SHOW_RX.search(words) else
                    "prices" if priced and PLAN_RX.search(words) else "steps" if STEP_RX.search(words)
                    else "faq" if FAQ_RX.search(words) else _fit(s) or ("image_cards" if priced else "cards"))
        if part == "picks" and not s.get("labels") and any(i.get("title") for i in s["items"]):
            # "picks" is a grid of seats / slots to pick: the 4B gave it to a coffee shop's menu, its baristas and
            # its address (2026-11-03), drawn as an empty A1..H8 seat grid. Things with prices are product cards
            part = "image_cards" if any(i.get("value") not in (None, "") for i in s["items"]) else "cards"
        secs.append(_reshape(dict(s, part=part), part))
    # the same thing never twice (a POS showed "Fresh Milk" twice in one grid and its product list again as "Best
    # sellers", 2026-11-14): an item that repeats one before it in its section goes; a section whose things are those of
    # one before it (most of their names) goes
    def _key(it):
        return " ".join(str(it.get("title") or "").lower().split()), " ".join(str(it.get("text") or "").lower().split())[:60]
    seen_sets = []
    kept = []
    for sec_ in secs:
        uniq, keys = [], set()
        for it in sec_.get("items") or []:
            k = _key(it)
            if k[0] and k in keys:
                continue
            keys.add(k)
            uniq.append(it)
        sec_["items"] = uniq
        names = {k[0] for k in keys if k[0]}
        if len(names) >= 3 and sec_["part"] not in SHARES_ITEMS and any(len(names & prev) >= .8 * len(names) for prev in seen_sets):
            continue
        if names:
            seen_sets.append(names)
        kept.append(sec_)
    secs = kept
    # stats are counts, not things with a price: the 4B gave the bakery's 4 specials again as a "Ready to Eat" stats
    # row ("25each", "40slice"). The same items as an earlier section: dropped; priced things: product cards
    seen_titles = []
    kept = []
    for x in secs:
        titles = {str(i.get("title") or "").strip().lower() for i in x["items"] if i.get("title")}
        if x["part"] == "stats" and titles and any(titles <= t for t in seen_titles):
            continue  # (only after a section of the same things with prices: see below)
        if (len(titles) >= 3 and x["part"] in ("image_cards", "cards", "gallery", "results", "tabs")
                and any(len(titles & t) >= .6 * len(titles) for t in seen_titles)):
            continue  # the same rooms / products again under another title (a hotel's "See the Details", 2026-11-11)
        if x["part"] in ("stats", "metric_pair") and any(PRODUCT_UNIT_RX.fullmatch(str(i.get("unit") or "").strip())
                                                         for i in x["items"]):
            x = dict(x, part="image_cards")
        elif x["part"] == "stats" and FEATURE_RX.search(f"{x.get('title', '')} {x.get('eyebrow', '')}"):
            x = dict(x, part="cards")
        elif x["part"] == "stats" and not any(isinstance(i.get("value"), (int, float)) and i["value"] for i in x["items"]):
            x = dict(x, part="cards")  # no number in any of them: the row read "0MB limit", "0 pixels" (2026-11-10)
        if titles and x["part"] in ("image_cards", "cards", "prices", "results", "picks", "table", "gallery"):
            seen_titles.append(titles)
        kept.append(x)
    secs = kept
    if wanted and all(p in ("chat_app", "mail_app") for p in wanted):
        extra = [i for x in secs[len(wanted):] for i in x["items"] if str(i.get("group") or "").strip().lower() in ("me", "them")]
        secs = secs[:len(wanted)]
        if extra and secs and secs[0]["part"] == "chat_app" and not any(
                str(i.get("group") or "").strip().lower() in ("me", "them") for i in secs[0]["items"]):
            secs[0]["items"] = secs[0]["items"] + extra  # the thread it wrote in the section after
    popups = [x for x in secs if x["part"] == "modal"]
    for x in popups[1:]:  # one popup per page: the others are a form on the page
        x["part"] = "form"
    if not any(x["part"] in ("picks", "results") for x in secs):  # a summary totals what was picked: nothing to pick
        secs = [dict(x, part="cards") if x["part"] == "summary" else x for x in secs]  # (a "Total ₹0 / Continue" box)
    hero = dict(plan.get("hero") or {})
    if " ".join(str(hero.get("accent") or "").lower().split()) == " ".join(str(hero.get("title") or "").lower().split()):
        hero["accent"] = ""  # (the 4B gave the same words twice: "FORGE YOUR STRENGTH FORGE YOUR STRENGTH", 2026-11-14)
    if isinstance(hero.get("stats"), list):  # "15 Old", "45 of", "15 Roas": the 4B put words into the suffix
        hero["stats"] = [dict(st, suffix=st.get("suffix") if STAT_SUFFIX_RX.fullmatch(str(st.get("suffix") or "")) else "")
                         for st in hero["stats"] if isinstance(st, dict)]
    return {"brand": plan.get("brand") or {"name": (spec or {}).get("title") or "Site", "icon": "bi-stars"},
            "hero": hero, "sections": secs, "footer": plan.get("footer") or "",
            **({"scene3d": plan["scene3d"]} if isinstance(plan.get("scene3d"), dict) else {})}  # 🧊 kept for the hero


STAT_SUFFIX_RX = re.compile(r"|\+|%|★|[kKM]\+?|x|/5|/10|h|hrs?|yrs?|min|₹|\$|€|£|°C?|L|cr", re.I)


# an app, not a site to read: a sidebar, a top bar and panels side by side (Dribbble-style admin / dashboard shots)
APP_RX = re.compile(r"\b(admin|dashboard|panel|crm|erp|back ?office|console|inventory|billing|pos|monitor\w*|analytics|"
                    r"management system|tracker)\b", re.I)
PERSON_RX = re.compile(r"\b(admin|crm|erp|shop|store|inventory|billing|pos|office|school|clinic|hotel)\b", re.I)
NAV_ICONS = ((r"log ?out|sign ?out|exit", "bi-box-arrow-right"),  # before "log" (history) and "sign" (sign in)
             (r"dash|overview|summary", "bi-grid-1x2"), (r"home", "bi-house"), (r"profile|my account", "bi-person-circle"),
             (r"log ?in|sign|account", "bi-box-arrow-in-right"),
             # the words of an admin's own menu (a reference's menu is read as it is: Students, Attendance, Finance...)
             (r"student|pupil|learner", "bi-mortarboard"), (r"attendance|present|absent", "bi-person-check"),
             (r"financ|fund|budget|wallet|fee", "bi-wallet2"), (r"notice|announce", "bi-megaphone"),
             (r"notif|alert", "bi-bell"), (r"librar|ebook", "bi-book"), (r"exam|grade|result|mark", "bi-clipboard-check"),
             (r"transport|bus|vehicle|fleet", "bi-bus-front"), (r"patient", "bi-person-heart"),
             (r"about", "bi-info-circle"), (r"class|course|lesson|learn|train", "bi-journal-bookmark"),
             (r"instructor|teacher|chef|doctor|trainer|staff|team", "bi-person-badge"), (r"contact", "bi-envelope"),
             (r"book|reserv|appointment|schedule|calendar", "bi-calendar-check"), (r"gallery|photo", "bi-images"),
             (r"blog|news|article", "bi-pencil-square"), (r"pric|plan", "bi-tag"), (r"faq|help|support", "bi-question-circle"),
             (r"service", "bi-grid"), (r"shop|store|cart", "bi-bag"), (r"menu|dish|food", "bi-egg-fried"),
             (r"device|room|sensor", "bi-cpu"), (r"hour|time|now|today|live", "bi-clock"),
             (r"week|outlook|forecast|day|month", "bi-calendar-week"), (r"weather|storm|rain|sun|cloud|sky|temperature", "bi-cloud-sun"),
             (r"wind|air|flow", "bi-wind"), (r"recipe|cook|kitchen|meal|food|dish|menu", "bi-egg-fried"), (r"location|place|city|map|search", "bi-geo-alt"), (r"message|chat|inbox", "bi-chat-dots"), (r"activity|log|history", "bi-clock-history"),
             (r"order|invoice|bill", "bi-receipt"), (r"product|stock|inventor|catalog", "bi-box-seam"),
             (r"customer|user|member|staff|people|team", "bi-people"), (r"report|analytic|insight", "bi-bar-chart"),
             (r"setting|config", "bi-gear"), (r"sale|revenue|payment", "bi-currency-rupee"))


def menu_label(name, size=24):
    """A menu entry's words: without a bracket ("Print Volume (Last 7 Days)" -> "Print Volume"), whole words only."""
    text = " ".join(re.sub(r"\s*[\(\[].*?[\)\]]", "", str(name or "")).split()) or str(name or "")
    if len(text) <= size:
        return text
    return text[:size].rsplit(" ", 1)[0] if " " in text[:size] else text[:size]


NAV_PICKS = {}  # the menu's icons the model chose for this page (agent._pick_icons: plan["nav_icons"]), set by render


def nav_icon(name):
    """A menu entry's icon: the one the model chose for it; else from its words (the generic chart icon was on About,
    Classes and Instructors alike)."""
    if str(name).strip().lower() in NAV_PICKS:
        return NAV_PICKS[str(name).strip().lower()]
    i = next((i for rx, i in NAV_ICONS if re.search(rx, str(name), re.I)), None) or webkit._icon_for(str(name))
    return "bi-circle" if i == "bi-graph-up" and not re.search(r"chart|graph|trend|analytic|report|stat", str(name), re.I) else i


def app_width(s):
    """Columns (of 12) a panel takes: numbers across the top, a chart / list wide, a form or a short list narrow."""
    part = s["part"]
    if part == "data_table":  # a table of a few columns sits beside a list (a 3D shop's jobs beside its filament)
        cols = max(len(s.get("labels") or []), 2 + max((len(i.get("meta") or []) for i in s.get("items") or []), default=0))
        return 12 if cols > 5 else 7
    if part in widgets.WIDGETS:
        return widgets.WIDTH.get(part, 4)
    if part == "table":
        cols = max(len(s.get("labels") or []), 1 + max((len(i.get("meta") or []) for i in s["items"]), default=0)
                   + any(i.get("value") not in (None, "") for i in s["items"]) + any(i.get("badge") for i in s["items"]))
        return 12 if cols > 5 else 7
    return {"stats": 12, "chart": 8, "results": 8, "picks": 8, "form": 4 if len(s.get("fields") or []) <= 4 else 6,
            "contact": 6, "cards": 4, "about": 4, "summary": 4, "faq": 6, "search": 4}.get(part, 12)


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CLOCK_RX = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])?\s*$")


def next_label(last, prev):
    """The label after `last` in a series: the next day ("Thu" -> "Fri"), the next time as far on as the step
    before it ("2 PM", "3 PM" -> "4 PM"; "10:00 AM", "12:00 PM" -> "02:00 PM"), the next number; else ""."""
    for d, day in enumerate(DAYS):
        for form in (day, day[:3]):
            if last.strip().lower() == form.lower():
                nxt = DAYS[(d + 1) % 7]
                return nxt if form == day else nxt[:3]
    def mins(t):
        m = CLOCK_RX.match(t)
        if not m:
            return None
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").upper()
        return ((h % 12 + (12 if ap == "PM" else 0)) if ap else h) * 60 + mi
    a, b = mins(last), mins(prev)
    if a is not None:
        step = (a - b) % 1440 if b is not None and (a - b) % 1440 else 60
        t = (a + step) % 1440
        m = CLOCK_RX.match(last)
        h, mi = divmod(t, 60)
        if m.group(3):
            ap = "AM" if h < 12 else "PM"
            hh = h % 12 or 12
            hh = f"{hh:02d}" if len(m.group(1)) == 2 else str(hh)
            return f"{hh}:{mi:02d} {ap}" if m.group(2) else f"{hh} {ap}"
        return f"{h:02d}:{mi:02d}" if m.group(2) else str(h)
    if re.fullmatch(r"\d+", last.strip()):
        return str(int(last) + 1)
    return ""


def fill_series(sec, n):
    """A series card (hours, days) with as many cells as the reference's card has: the plan's cells, then the next
    hours or days with the plan's own cells' look and nearby values."""
    its = list(sec.get("items") or [])
    n = min(int(n or 0), 12)
    if not its or len(its) >= n:
        return sec
    out = list(its)
    while len(out) < n:
        k = len(out)
        title = next_label(str(out[-1].get("title") or ""), str(out[-2].get("title") or "") if k > 1 else "")
        if not title:
            break
        v = out[-1].get("value")
        try:
            v = round(float(v) + (-1, 1, -2, 2, 0)[k % 5])
        except (TypeError, ValueError):
            pass
        out.append(dict(its[k % len(its)], title=title, value=v))
    return dict(sec, items=out)


DASH_RX = re.compile(r"\b(dashboard|panel|portal|admin|monitor|tracker|analytics|console|iot)\b", re.I)
FIND_PARTS = {"data_table", "table", "list_thumbs", "task_list", "task_cards", "files", "review_list", "leaderboard",
              "world_list", "notifications", "kanban", "agenda", "cards", "results", "image_cards", "faq", "timeline"}


TOP_ICONS = {"notifications": ("bi-bell", "Notifications", True), "messages": ("bi-chat-dots", "Messages", True),
             "mail": ("bi-envelope", "Mail", True), "favorites": ("bi-heart", "Favorites", True), "cart": ("bi-cart3", "Cart", True),
             "settings": ("bi-gear", "Settings", False), "help": ("bi-question-circle", "Help", False),
             "calendar": ("bi-calendar3", "Calendar", False), "apps": ("bi-grid-3x3-gap", "Apps", False)}


def top_bits(secs, ctx, request, home):
    """What this page's top bar holds. A reference's own top strip decides (its search, bell, person...), else the
    page: a search box where there is a list to search, the bell and the signed-in person on a dashboard's home,
    the theme switch with them. A page needing none of it (a contact form) has no top bar (the user, 2026-10-27:
    "the top bar comes on every page, static; only where the page needs it")."""
    ref = ctx.get("top_bar")
    findable = any(s["part"] in FIND_PARTS for s in secs) or len(secs) >= 6
    if ref is not None:
        bits = [b for b in ref if b != "search" or findable or home]
        # a page other than the home page keeps the reference's icons and person, not its title or its button
        return bits if home else [b for b in bits if b not in ("title", "button", "date", "location")]
    bits = ["search"] if findable else []
    if home and (PERSON_RX.search(request or "") or DASH_RX.search(request or "")):
        bits += ["notifications", "user"]  # (no light / dark button: the page has the theme chosen for it)
    return bits


def side_menu_html(menu, secs, pages=None, current=None):
    """The reference's menu entries as the page's menu: an entry naming a part of the page goes to it (Calendar ->
    the calendar card), the others say they open (no dead link); the group headings (MENU, OTHER) over their blocks;
    the entry the reference highlights is the active one (else the first)."""
    words = lambda t: {w for w in re.findall(r"[a-z]{3,}", str(t).lower())}  # noqa: E731
    active = next((k for k, m in enumerate(menu) if m.get("active")), 0)
    files = {str(name).lower(): f for name, f in pages or []}
    if pages:  # a site: the entry that is this page is the active one
        active = next((k for k, m in enumerate(menu) if files.get(m["label"].lower()) == current), -1)
    out, group = [], None
    for k, m in enumerate(menu):
        if m.get("group") and m["group"] != group:
            out.append(f'<div class="m42-side-label">{e(m["group"])}</div>')
        group = m.get("group") or group
        f = files.get(m["label"].lower())
        if f:
            out.append(f'<a class="m42-side-link{" active" if k == active else ""}" href="{e(f)}" title="{e(m["label"])}"'
                       + (' aria-current="page"' if k == active else "")
                       + f'><i class="bi {nav_icon(m["label"])}"></i><span>{e(m["label"])}</span></a>')
            continue
        if pages:
            out.append(f'<a class="m42-side-link" href="#" title="{e(m["label"])}" data-m42-toast="{e(m["label"])} opens here" '
                       f'data-kind="info"><i class="bi {nav_icon(m["label"])}"></i><span>{e(m["label"])}</span></a>')
            continue
        target = next((s for s in secs if words(m["label"]) & (words(s.get("title")) | words(s["part"].replace("_", " ")))), None)
        # the highlighted entry is the page's top (its first part: the scroll marker shows it there, not Calendar)
        target = target or (secs[0] if k == active and secs else None)
        href = "#" + target["_id"] if target else "#"
        out.append(f'<a class="m42-side-link{" active" if k == active else ""}" href="{e(href)}" title="{e(m["label"])}"'
                   + ("" if target or k == active else f' data-m42-toast="{e(m["label"])} opens here" data-kind="info"')
                   + f'><i class="bi {nav_icon(m["label"])}"></i><span>{e(m["label"])}</span></a>')
    return "".join(out)


def this_year(text):
    """A footer's copyright year is this year (the 4B copied "© 2021" off a reference picture)."""
    import datetime
    now = datetime.date.today().year
    return re.sub(r"(©\s*|copyright\s*)(20\d\d)\b", lambda m: m.group(1) + str(now), str(text or ""), flags=re.I)


def app_layout(plan, ctx, pages, current, request):
    """Sidebar (the pages, or the sections of a one-page dashboard), a top bar (menu, search, status, theme), the
    page head, then the parts as panels packed in rows of 12 columns: no row ends half empty."""
    secs, brand, h = plan["sections"], plan["brand"], plan["hero"]
    links = ([(name, f, f == current) for name, f in pages] if pages else
             [(s.get("title") or s["part"].title(), "#" + s["_id"], n == 0) for n, s in enumerate(secs)
              if s["part"] not in ("cta", "summary", "banner", "kpi_tiles", "stats", "metric_pair", "breadcrumb")][:7])
    if not pages and ctx.get("app_screens"):  # 🧭 the app's screens (appflows.py), each to its part on this page when it
        # has one (a POS's Orders: its sales table), the dashboard first; the menu read "Checkout #8921", "Sales over Last 24 Hours"
        first_ = secs[0]["_id"] if secs else ""
        links = [("Dashboard", "#" + first_, True)]
        for scr in ctx["app_screens"][:6]:
            name, _, part = str(scr).partition(":")
            to = next((x["_id"] for x in secs if x["part"] == part.strip()), "")
            links.append((name.strip(), "#" + (to or first_), False))
    nav = "".join(f'<a class="m42-side-link{" active" if act else ""}" href="{e(href)}" title="{e(name)}"'
                  + (' aria-current="page"' if act and pages else "")
                  + f'><i class="bi {nav_icon(name)}"></i><span>{e(menu_label(name))}</span></a>' for name, href, act in links)
    groups = []
    if ctx.get("side_menu"):  # the reference's own menu (Dashboard, Teachers, Students...), its groups; in a site its
        # entries are the pages (the others say they open)
        nav, groups = side_menu_html(ctx["side_menu"], secs, pages, current), [m["group"] for m in ctx["side_menu"]]
    initials = "".join(w[0] for w in str(brand.get("name") or "M").split()[:2]).upper()
    foot = (f'<div class="m42-side-foot"><span class="m42-me">{e(initials)}</span><div><strong>Admin</strong>'
            f'<small>{e(brand.get("name"))}</small></div></div>' if PERSON_RX.search(request or "") else "")
    sc = ((ctx.get("ref_grid") or {}).get("side_color") or "") if ctx.get("dark_side_ok") else ""
    side = (f'<aside class="m42-side offcanvas-lg offcanvas-start{" m42-side-dark" if sc else ""}" id="m42side" tabindex="-1" aria-label="Menu"'
            + (f' style="--m42-side-bg:{e(sc)}"' if sc else "") + '><div class="offcanvas-body">'
            f'<div class="d-flex align-items-center justify-content-between"><a class="m42-side-brand" href="{"index.html" if pages else "#"}">'
            f'<span class="m42-chip"><i class="bi {icon(brand.get("icon"))}"></i></span><span class="m42-side-name">{e(brand.get("name"))}</span></a>'
            '<button type="button" class="btn-close d-lg-none" data-bs-dismiss="offcanvas" data-bs-target="#m42side" aria-label="Close"></button></div>'
            + ("" if groups and groups[0] else '<div class="m42-side-label">Menu</div>')
            + f'<nav class="m42-side-nav">{nav}</nav>'
            + "".join(f'<div class="m42-side-card">{PARTS[sc["part"]](sc, ctx) if sc["part"] in PARTS else ""}</div>' for sc in secs if sc.get("_side"))
            + f'{foot}</div></aside>')
    home = not pages or current == pages[0][1]
    bits = top_bits(secs, ctx, request, home)
    at = themes.APP_THEMES.get(ARCH.get("design") or "") or {}  # 🎨 the app theme (themes.APP_THEMES, the 4B's pick)
    tabs = links[:5]
    topnav = ""
    if at.get("side") == "top":  # the menu as tabs in the top bar, the brand at its left (no sidebar)
        topnav = (f'<a class="m42-topbrand" href="{"index.html" if pages else "#"}"><span class="m42-chip"><i class="bi {icon(brand.get("icon"))}"></i></span>'
                  f'<b>{e(brand.get("name"))}</b></a><nav class="m42-topnav d-none d-lg-flex">'
                  + "".join(f'<a class="{"active" if act else ""}" href="{e(href)}">{e(menu_label(name))}</a>' for name, href, act in links[:6]) + "</nav>")
        bits = list(bits) or ["search", "bell", "user"]
    tabbar = ("" if not at.get("tabbar") or len(tabs) < 2 else
              '<nav class="m42-tabbar d-lg-none" aria-label="Tabs">' + "".join(
                  f'<a class="{"active" if act or (k == 0 and not any(x[2] for x in tabs)) else ""}" href="{e(href)}"><i class="bi {nav_icon(name)}"></i>'
                  f'<span>{e(" ".join(str(menu_label(name)).split()[:1])[:11])}</span></a>'
                  for k, (name, href, act) in enumerate(tabs)) + "</nav>")  # (a tab says one word: "Print Volu..." was cut)
    # the feed's status only where a device / API is fetched (its script sets it): on a page with demo numbers it
    # said "Connecting…" for ever (the user: "why connect in it at all")
    live = ctx.get("device") and ctx["live"] and (home or bool(bits))
    # a reference with its own top strip ("Dashboard", search, icons, the person, EN): the page's title is in the
    # bar, as there, not a title row under it
    # the page's title is in the bar where the reference has it there ("Dashboard" at its left), not a row under it
    in_bar = home and "title" in bits
    first_act = (h.get("actions") or [""])[0]

    def bit(b):
        """One thing of the bar, as the reference shows it (read left to right; the bar keeps that order)."""
        if b == "title":
            return f'<h1 class="m42-toptitle">{e(h.get("title") or brand.get("name"))}</h1>'
        if b == "search":
            return ('<label class="m42-topsearch"><i class="bi bi-search"></i><input type="search" placeholder="Search…" '
                    'aria-label="Search this page" data-m42-find></label>')
        if b == "date":
            return '<span class="m42-muted small d-none d-md-inline m42-today"></span>'
        if b == "theme":  # (the user, 2026-11-12: no light / dark button on the pages)
            return ""
        if b == "user":
            return (f'<span class="m42-topuser"><span class="m42-me">{e(initials)}</span><span class="d-none d-md-block"><b>'
                    f'{"Admin" if PERSON_RX.search(request or "") else "My account"}</b><small>{e(brand.get("name"))}</small></span></span>')
        if b == "language":
            return ('<button type="button" class="m42-topchip" data-m42-toast="Language: English" data-kind="info">EN '
                    '<i class="bi bi-chevron-down"></i></button>')
        if b == "location":
            return f'<span class="m42-topchip"><i class="bi bi-geo-alt"></i> {e(plan.get("footer") or brand.get("name"))}</span>'
        if b == "button":
            return f'<a class="m42-btn" href="#{e(secs[0]["_id"] if secs else "")}">{e(first_act or "Get started")}</a>'
        if b in TOP_ICONS:
            ic_, label, dot = TOP_ICONS[b]
            return (f'<button type="button" class="m42-icon-btn" aria-label="{label}" data-m42-toast="No new {label.lower()}" '
                    f'data-kind="info"><i class="bi {ic_}"></i>' + ('<span class="m42-dot"></span>' if dot else "") + "</button>")
        return ""
    left = [b for b in bits if b in ("title", "search")]
    right = [b for b in bits if b not in left]
    tools = ("".join(bit(b) for b in left) + '<div class="ms-auto d-flex align-items-center gap-2">'
             + ('<span class="m42-status" id="conn"></span><span class="m42-updated d-none d-md-inline"></span>' if live else "")
             + "".join(bit(b) for b in right)
             + '</div>')
    menu_btn = ('<button class="m42-icon-btn d-lg-none" type="button" data-bs-toggle="offcanvas" '
                'data-bs-target="#m42side" aria-controls="m42side" aria-label="Menu"><i class="bi bi-list"></i></button>')
    # nothing for a top bar on this page: only the phone's menu button (the sidebar is off screen there)
    top = (f'<header class="m42-topbar">{menu_btn}{topnav}{tools}</header>' if bits or live else
           f'<header class="m42-topbar d-lg-none">{menu_btn}</header>')
    first = next((s["_id"] for s in secs), "")
    actions = "".join(f'<a class="{"m42-btn" if n == 0 else "m42-btn-ghost"}" href="#{first}">{e(a)}</a>'
                      for n, a in enumerate(h.get("actions") or []))
    title = (f'<h1>{e(h.get("title") or brand.get("name"))}'
             + (f' <span class="m42-gradient-text">{e(h.get("accent"))}</span>' if h.get("accent") else "") + "</h1>")
    pagehead = (f'<div class="m42-pagehead"><div>' + (f'<span class="m42-badge">{e(h.get("eyebrow"))}</span>' if h.get("eyebrow") else "")
                + title + (f'<p>{e(h.get("lead"))}</p>' if h.get("lead") else "") + "</div>"
                + (f'<div class="m42-actions m-0">{actions}</div>' if actions else "") + "</div>")
    kpis = ""
    rh = ctx.get("ref_head") or {}
    if home and rh.get("big"):  # the reference's own head: a greeting, a big heading, a row of chips (the cooking shot)
        chips = [a for a in (h.get("actions") or []) if a][:max(rh.get("chips") or 0, 0)] or (h.get("actions") or [])[:rh.get("chips") or 0]
        pagehead = (f'<div class="m42-pagehead is-big"><div>' + (f'<p class="m42-hello">{e(h.get("eyebrow") or "Hello")}</p>' if rh.get("greeting") else "")
                    + f'<h1>{e(h.get("title") or brand.get("name"))}</h1></div>'
                    + (f'<div class="m42-chips m42-headchips" data-single>' + "".join(
                        f'<button type="button" class="m42-chip-btn{" active" if k == 0 else ""}"><i class="bi {nav_icon(c)}"></i> {e(c)}</button>'
                        for k, c in enumerate(chips)) + "</div>" if chips else "") + "</div>")
    elif home and at.get("banner") == "gradient":  # 🎨 the app theme's greeting band: the words and an art
        art = (widgets.photo(dict(h, title=h.get("title")), "m42-hb-img") if widgets.photo(h) else
               f'<div class="m42-hb-icons"><span><i class="bi {icon(brand.get("icon"))}"></i></span>'
               + "".join(f'<span class="is-s"><i class="bi {nav_icon(name)}"></i></span>' for name, _h, _a in links[1:3]) + "</div>")
        pagehead = (f'<div class="m42-hello-band"><div class="m42-hb-text"><span class="m42-hb-hi">{e(h.get("eyebrow") or "Welcome back")}</span>'
                    f'<h1>{e(h.get("title") or brand.get("name"))}' + (f' <span>{e(h.get("accent"))}</span>' if h.get("accent") else "") + "</h1>"
                    + (f'<p>{e(h.get("lead"))}</p>' if h.get("lead") else "")
                    + (f'<div class="m42-actions m-0">{actions}</div>' if actions else "") + f'</div><div class="m42-hb-art">{art}</div></div>')
    elif in_bar:  # the title is in the top bar, as in the reference
        pagehead = ""
    elif ctx.get("ref_grid") and ctx["ref_grid"].get("tree"):  # the reference's cards are the page: a slim head (a real run:
        # "Clear skies for tomorrow" in big letters and two number tiles above a weather reference that has neither)
        acts = "" if "button" in bits else "".join(f'<a class="m42-btn-ghost" href="#{first}">{e(a)}</a>' for a in (h.get("actions") or [])[:1])
        pagehead = (f'<div class="m42-pagehead is-slim"><div><h1>{e(h.get("title") or brand.get("name"))}</h1>'
                    + (f'<p>{e(h.get("lead"))}</p>' if h.get("lead") else "") + "</div>"
                    + (f'<div class="m42-actions m-0">{acts}</div>' if acts else "") + "</div>")
    elif h.get("stats") and not any(s["part"] in ("stats", "kpi_tiles", "metric_pair") for s in secs):
        def kpi(st):
            suf = str(st.get("suffix") or "")
            pre = suf if suf in ("₹", "$", "€", "£") else ""
            return (f'<div class="col-6 col-lg-3"><div class="m42-panel m42-kpi"><small class="m42-muted">{e(st.get("label"))}</small>'
                    f'<strong data-m42-count="{e(st.get("value") or 0)}" data-prefix="{e(pre)}" data-suffix="{e("" if pre else suf)}">0</strong></div></div>')
        kpis = f'<div class="row g-3 mb-3">{"".join(kpi(st) for st in h["stats"][:4])}</div>'
    def panel(sec):
        part = sec["part"]
        if part == "composed":  # a reference card drawn from its own blocks: it is the panel, with its own title
            strip = (sec.get("_look") or {}).get("strip")  # (a title strip over the cards under it: no panel round it)
            return (f'<section id="{sec["_id"]}" class="{"m42-c-strip" if strip else "m42-panel is-composed"}"{own_reveal(sec)}>'
                    f'{PARTS[part](sec, ctx)}</section>')
        bare = dict(sec, eyebrow="", title="", lead=sec.get("lead") if part == "form" else "")
        if part == "cta":  # in an app a closing banner is a row of actions, not a big empty box
            inner = (f'<div class="m42-actions m-0"><a class="m42-btn" href="#{e(ctx.get("first_id", ""))}">'
                     f'{e(sec.get("button") or "Open")}</a></div>')
        elif sec.get("_comp"):  # ⚖ its premium composition (appblocks.py), chosen for its column
            import appblocks
            inner = appblocks.draw(sec["_comp"], bare, ctx) if sec["_comp"] in appblocks.APPBLOCKS else PARTS[part](bare, ctx)
        else:
            if part in widgets.ROW_PARTS and (sec.get("_look") or {}).get("row"):  # the reference's own row: its parts, in its order
                inner = widgets.w_template_rows(bare, ctx)
            else:
                inner = (p_rows if part in ("cards", "about") else PARTS[part])(bare, ctx)
        if part == "device_cards" and len(sec.get("items") or []) == 1:  # one device is a tile (the smart-home shot's
            # Air purifier / Android TV): no panel with a title round a card with the same title
            return f'<section id="{sec["_id"]}" class="m42-tilecell"{own_reveal(sec)}>{PARTS[part](bare, ctx)}</section>'
        if part in ("stats", "kpi_tiles", "project_cards", "banner", "weather_now"):  # tiles and banners are cards themselves
            if part in ("banner", "weather_now"):  # their own title and words are the card
                inner = PARTS[part](sec, ctx)
            return f'<section id="{sec["_id"]}" class="m42-tilecell"{own_reveal(sec)}>{inner}</section>'
        lk = sec.get("_look") or {}
        # the reference card's own head: a "This Month" picker and / or an arrow to open it, in place of a badge
        tools = ((f'<button type="button" class="m42-topchip" data-m42-toast="Showing this month" data-kind="info"><i class="bi bi-calendar3"></i> '
                  f'{e(sec.get("eyebrow") or "This Month")} <i class="bi bi-chevron-down"></i></button>' if lk.get("header") in ("dropdown", "both") else "")
                 + (f'<a class="m42-icon-btn" href="#{sec["_id"]}" aria-label="Open {e(sec.get("title"))}"><i class="bi bi-arrow-up-right"></i></a>'
                    if lk.get("header") in ("arrow", "both") else ""))
        if sec.get("_comp") == "bill.pos_panel":  # (the bill has its own head: "Current bill" was written twice)
            return f'<section id="{sec["_id"]}" class="m42-panel is-main is-bill" data-m42-comp="bill.pos_panel"{own_reveal(sec)}>{inner}</section>'
        phead = (f'<div class="m42-panel-head"><div><h2>{e(sec.get("title"))}</h2>'
                 + (f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else "") + "</div>"
                 + (f'<div class="d-flex gap-2 align-items-center">{tools}</div>' if tools else
                    f'<span class="m42-badge">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "") + "</div>")
        comp = f' data-m42-comp="{e(sec["_comp"])}"' if sec.get("_comp") else ""
        return f'<section id="{sec["_id"]}" class="m42-panel{" is-main" if sec.get("_main") else ""}"{comp}{own_reveal(sec)}>{phead}{inner}</section>'

    def packed(group):
        """Panels in rows of 12 columns: no row ends half empty."""
        rows, cur, tot = [], [], 0
        for sec in group:
            w = 12 if sec.get("size") in SIZES or sec.get("align") in ALIGNS else app_width(sec)  # (its own row)
            if sec.get("_main"):  # the screen's main tool (a POS's bill, a CRM's board): the widest card of its row
                w = max(w, 8)
            if cur and tot + w > 12:
                cur[-1][1] += 12 - tot
                rows.append(cur)
                cur, tot = [], 0
            cur.append([sec, w])
            tot += w
        if cur:
            cur[-1][1] += 12 - tot
            rows.append(cur)
        return "".join(f'<div class="col-12 col-lg-{w}">{panel(sec)}</div>' for row in rows for sec, w in row)

    def grid(node):
        """The reference's own grid (designref.cards): columns as wide as its, cards stacked as in it."""
        if "leaf" in node:
            if node["leaf"] >= len(secs):
                return ""
            sec = secs[node["leaf"]]
            counts = ctx.get("ref_counts") or []
            if sec["part"] == "kpi_tiles" and node["leaf"] < len(counts) and counts[node["leaf"]] <= 1:
                sec = dict(sec, items=sec["items"][:1])  # the reference's card is one tile: one tile here too
            elif sec["part"] in ("hourly", "forecast") and node["leaf"] < len(counts):
                sec = fill_series(sec, counts[node["leaf"]])  # 9 hours in the reference: 9 here, not the plan's 5
            return panel(sec)
        def present(k):  # a column the plan wrote no card for is left out (no empty column on the page)
            return k["leaf"] < len(secs) if "leaf" in k else any(present(c) for c in k["children"])
        kids = [k for k in node["children"] if present(k)]
        if not kids:
            return ""
        if node["dir"] == "rows":
            return '<div class="m42-stack">' + "".join(grid(k) for k in kids) + "</div>"
        widths = [max(.01, k["box"][2] - k["box"][0]) for k in kids]
        spans = [max(2, round(12 * w / sum(widths))) for w in widths]
        while sum(spans) > 12:
            spans[spans.index(max(spans))] -= 1
        spans[-1] += 12 - sum(spans)
        return ('<div class="row g-3">' + "".join(f'<div class="col-12 col-lg-{sp}">{grid(k)}</div>' for k, sp in zip(kids, spans))
                + "</div>")
    tree = ctx.get("ref_grid") and ctx["ref_grid"].get("tree")
    if tree:
        leaves = []

        def collect(n):
            if "leaf" in n:
                leaves.append(n["leaf"])
            else:
                for c in n["children"]:
                    collect(c)
        collect(tree)
        rest = [sc for i, sc in enumerate(secs) if i not in leaves and not sc.get("_side")]
        body = grid(tree) + (f'<div class="row g-3 mt-0">{packed(rest)}</div>' if rest else "")
    elif ctx.get("app_layout") and any(sc.get("_slot") for sc in secs):
        # 🦴 the kind's skeleton: each row's columns as wide as its rule set says, each column's parts stacked in it, a
        # sticky column (a POS's bill) staying in view; a section the plan wrote with no place goes in rows after them
        group = [sc for sc in secs if not sc.get("_side")]
        import appblocks
        import ui_assets
        traits = ui_assets.traits(ARCH.get("design") or "")
        for sc in group:  # ⚖ each part's premium composition for its place: beside the work (a sticky column in its row) or not
            if not sc.get("_comp") and sc.get("_slot"):
                r_ = sc["_slot"][0]
                row_ = ctx["app_layout"][r_] if r_ < len(ctx["app_layout"]) else []
                beside = any(c.get("sticky") for c in row_) and not (row_[sc["_slot"][1]] if sc["_slot"][1] < len(row_) else {}).get("sticky")
                comp, alts = appblocks.pick(sc["part"], sc, traits, beside, sc.get("title") or "")
                if comp:
                    sc["_comp"], sc["_comp_alts"] = comp, alts
        used, out_rows = set(), []
        for r, row in enumerate(ctx["app_layout"]):
            cols = []
            for c, col in enumerate(row):
                here = [i for i, sc in enumerate(group) if i not in used and sc.get("_slot") == [r, c]]
                if not here:
                    continue
                used.update(here)
                inner = "".join(panel(group[i]) for i in here)
                inner = f'<div class="m42-work-side">{inner}</div>' if col.get("sticky") else (f'<div class="m42-stack">{inner}</div>' if len(here) > 1 else inner)
                cols.append((col.get("span") or 12, inner))
            if not cols:
                continue
            if sum(s for s, _ in cols) < 12:  # (a column left out: the others share its width)
                spare = 12 - sum(s for s, _ in cols)
                cols[-1] = (cols[-1][0] + spare, cols[-1][1])
            out_rows.append("".join(f'<div class="col-12 col-xl-{s}">{h}</div>' for s, h in cols))
        rest = [sc for i, sc in enumerate(group) if i not in used]
        body = f'<div class="row g-3">{"".join(out_rows)}{packed(rest)}</div>'
    else:
        group = [sc for sc in secs if not sc.get("_side")]
        mi = next((i for i, sc in enumerate(group) if sc.get("_main") and sc["part"] == "invoice"), None)
        pick = [i for i, sc in enumerate(group) if sc["part"] in ("category_chips", "image_cards", "results")][:2]
        pick += [i for i, sc in enumerate(group) if sc["part"] in ("kpi_tiles", "stats")][:1] if pick else []  # (today's numbers
        # under the products, beside the tall bill: no empty half under them)
        if mi is not None and pick:  # (the user's POS reference: the products to tap beside the bill being made; a real
            # POS build put the bill full width and the products under it as a bare list, 2026-11-14)
            left = "".join(panel(group[i]) for i in pick)
            pair = (f'<div class="col-12 col-xl-7"><div class="m42-stack">{left}</div></div>'
                    f'<div class="col-12 col-xl-5"><div class="m42-work-side">{panel(group[mi])}</div></div>')
            rest = [sc for i, sc in enumerate(group) if i != mi and i not in pick]
            body = f'<div class="row g-3">{pair}{packed(rest)}</div>'
        else:
            body = f'<div class="row g-3">{packed(group)}</div>'
    words = [brand.get("name")] + ([this_year(plan.get("footer"))] if plan.get("footer") and plan.get("footer") != brand.get("name") else [])
    foot_line = f'<div class="m42-app-foot">{" · ".join(e(w) for w in words)}</div>'
    return (side + f'<div class="m42-main">{top}<main class="m42-content">{pagehead}{kpis}'
            f'{body}{foot_line}</main>{tabbar}</div>')


def auth_layout(plan, ctx, sec, pages):
    """A sign-in page: the brand on a panel of its colours beside the form (no menu, no other sections)."""
    brand, h = plan["brand"], plan["hero"]
    form = p_form(sec, ctx)
    back = '<p class="m42-muted small mt-4 text-center"><a href="index.html">← Back to the home page</a></p>' if pages else ""
    lines = "".join(f'<li><i class="bi bi-check-circle-fill"></i>{e(st.get("label"))}</li>' for st in (h.get("stats") or [])[:3])
    art = (f'<aside class="m42-auth-art"><a class="m42-side-brand" href="{"index.html" if pages else "#"}"><span class="m42-chip">'
           f'<i class="bi {icon(brand.get("icon"))}"></i></span>{e(brand.get("name"))}</a>'
           f'<div><h2>{e(h.get("title") or "Welcome back")} {e(h.get("accent"))}</h2>'
           + (f'<p>{e(h.get("lead"))}</p>' if h.get("lead") else "") + "</div>"
           # 🧊 a 3D sign-in page (the request asked for 3D): the scene on the brand's panel, beside the form
           + (f'<div class="m42-3d is-auth" role="img" aria-label="{e(plan["scene3d"].get("alt") or "")}" '
              f'data-m42-3d="{e(json.dumps(plan["scene3d"], ensure_ascii=False))}"><canvas></canvas></div>'
              if isinstance(plan.get("scene3d"), dict) else "")
           + f'<small>© {e(brand.get("name"))} · {e(plan.get("footer"))}</small></aside>')
    return (f'<div class="m42-auth">{art}<main class="m42-auth-form"><div>'
            f'<h1 class="h2 fw-bold mb-1">{e(sec.get("title") or "Sign in")}</h1>'
            + (f'<p class="m42-muted mb-4">{e(sec.get("eyebrow"))}</p>' if sec.get("eyebrow") and sec.get("eyebrow") != sec.get("title") else '<div class="mb-4"></div>')
            + f'{form}{back}</div></main></div>')


# ---- 🎨 a theme's own layouts (themes.py "flow" / "stats"): the weight of each section changes, not only its skin
# (the user, 2026-11-14: "every page has the same weightage: big photo hero, 3 cards, steps, 3 prices"; real landing
# pages put one big product with points round it, huge numbers in rows, a collage, rows changing sides)

def _lx_art(it, ctx, cls):
    """An item's photo, else its icon on a tinted disc."""
    return widgets.photo(it, cls) or (f'<div class="{cls} m42-lx-art"><i class="bi {icon(it.get("icon"), icon(ctx.get("brand_icon")))}"></i></div>')


def _lx_end(it, sec):
    return (f'<div class="m42-lx-price">{amount(it.get("value"), it.get("unit") or "")}</div>' if it.get("value") not in (None, "") else "")


def lay_zigzag(sec, ctx):
    """Big rows, the picture and the words changing sides (a tea brand's products on big circles)."""
    rows = "".join(
        f'<div class="m42-lx-zz{" is-flip" if k % 2 else ""}"><div class="m42-lx-zz-pic"><span class="m42-lx-disc"></span>{_lx_art(it, ctx, "m42-lx-zz-img")}</div>'
        f'<div class="m42-lx-zz-text"><span class="m42-lx-no">{k + 1:02d}</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>{_lx_end(it, sec)}</div></div>'
        for k, it in enumerate((sec.get("items") or [])[:6]))
    return head(sec) + f'<div class="m42-lx-zigzag">{rows}</div>'


def lay_orbit(sec, ctx):
    """One big picture in the middle, the points round it, numbered (an AI robot with 4 reasons around it)."""
    items = (sec.get("items") or [])[:6]
    centre = next((it for it in items if widgets.photo(it)), None) or (ctx.get("hero_photo") and {"photo": ctx["hero_photo"], "title": sec.get("title")})
    pic = widgets.photo(centre, "m42-lx-orbit-img") if centre else f'<div class="m42-lx-orbit-img m42-lx-art"><i class="bi {icon(ctx.get("brand_icon"))}"></i></div>'
    half = (len(items) + 1) // 2
    side = lambda its, off: "".join(f'<div class="m42-lx-pt"><span class="m42-lx-no">{off + k + 1:02d}</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div>'
                                    for k, it in enumerate(its))
    return (head(sec) + f'<div class="m42-lx-orbit"><div class="m42-lx-side">{side(items[:half], 0)}</div>'
            f'<div class="m42-lx-centre"><span class="m42-lx-ring"></span>{pic}</div><div class="m42-lx-side">{side(items[half:], half)}</div></div>')


def lay_spotlight(sec, ctx):
    """A tall picture held on one side, a numbered list with hairlines on the other (001 Great taste ...)."""
    items = (sec.get("items") or [])[:8]
    first = next((it for it in items if widgets.photo(it)), None)
    pic = widgets.photo(first, "m42-lx-spot-img") if first else f'<div class="m42-lx-spot-img m42-lx-art"><i class="bi {icon(ctx.get("brand_icon"))}"></i></div>'
    rows = "".join(f'<li><span class="m42-lx-no">{k + 1:03d}</span><div><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p></div>{_lx_end(it, sec)}</li>'
                   for k, it in enumerate(items))
    return head(sec) + f'<div class="m42-lx-spot"><div class="m42-lx-spot-pic">{pic}</div><ol class="m42-lx-spot-list">{rows}</ol></div>'


def lay_carousel(sec, ctx):
    """Tall cards in a row that slides, arrows at the top (pick your flavour / best sellers)."""
    cid = (sec.get("_id") or "c") + "-track"
    cards = "".join(f'<article class="m42-lx-card"><div class="m42-lx-card-pic">{_lx_art(it, ctx, "m42-lx-card-img")}</div>'
                    f'<div class="m42-lx-card-body"><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>{_lx_end(it, sec)}</div></article>'
                    for it in (sec.get("items") or [])[:10])
    move = lambda d: (f'onclick="var t=document.getElementById(\'{cid}\');t.scrollBy({{left:{d}*t.clientWidth*0.8,behavior:\'smooth\'}})"')
    arrows = (f'<div class="m42-lx-arrows"><button type="button" aria-label="Previous" {move(-1)}><i class="bi bi-arrow-left"></i></button>'
              f'<button type="button" aria-label="Next" {move(1)}><i class="bi bi-arrow-right"></i></button></div>')
    return f'<div class="m42-lx-carhead">{head(dict(sec))}{arrows}</div><div class="m42-lx-track" id="{cid}" tabindex="0">{cards}</div>'


def lay_collage(sec, ctx):
    """The photos as an overlapping collage beside the words, the points as a short list under them."""
    items = (sec.get("items") or [])[:6]
    pics = [it for it in items if widgets.photo(it)][:4]
    if len(pics) < 3:
        return lay_zigzag(sec, ctx)
    tiles = "".join(f'<figure class="m42-lx-col-{k}">{widgets.photo(it, "m42-lx-col-img")}</figure>' for k, it in enumerate(pics))
    pts = "".join(f'<li><i class="bi {icon(it.get("icon"))}"></i><div><b>{e(it.get("title"))}</b><span>{e(it.get("text"))}</span></div></li>' for it in items)
    return (f'<div class="m42-lx-collage"><div class="m42-lx-col-words">{head(sec)}<ul class="m42-lx-col-list">{pts}</ul></div>'
            f'<div class="m42-lx-col-pics">{tiles}</div></div>')


def lay_numbers(sec, ctx):
    """The numbers huge, one per row, the icon before and the words after (8X · +40h)."""
    def count(it):
        if it.get("shown"):  # the 4B's own short figure ("15+ Years", "₹25L+"): as written, not 25,000,000INR
            return f'<strong class="is-shown">{e(it["shown"])}</strong>'
        unit = str(it.get("unit") or "")
        pre = unit if unit in ("₹", "$", "€", "£", "¥") else ""
        return (f'<strong><span data-m42-count="{e(it.get("value") or 0)}" data-prefix="{e(pre)}" '
                f'data-suffix="{e("" if pre else unit)}">0</span></strong>')
    rows = "".join(f'<div class="m42-lx-num"><span class="m42-chip"><i class="bi {icon(it.get("icon"))}"></i></span>{count(it)}'
                   f'<div><b>{e(it.get("title") or it.get("label") or "")}</b>' + (f'<p>{e(it.get("text"))}</p>' if it.get("text") else "") + "</div></div>"
                   for it in (sec.get("items") or [])[:5])
    return head(sec) + f'<div class="m42-lx-nums">{rows}</div>'


# ---- 🎨 signature heroes (the user's premium references, 2026-11-14: one colour filling the hero, huge words with
# the product in front of them, a thin + bold headline on a dark side with a colour panel, a big serif headline with
# the product over it, a diagonal colour split): their weight, not their pictures
def _sig_bits(plan, ctx, h):
    """The first thing the page shows (a section item with a photo) for the floating card; the hero's numbers."""
    first = None
    for s in plan.get("sections") or []:
        for it in s.get("items") or []:
            if widgets.photo(it):
                first = (s, it)
                break
        if first:
            break
    return first


def _sig_stats(h, cls):
    out = "".join(f'<div class="{cls}"><strong data-m42-count="{e(st.get("value") or 0)}" data-suffix="{e(st.get("suffix") or "")}">0</strong>'
                  f'<span>{e(st.get("label"))}</span></div>' for st in (h.get("stats") or [])[:3])
    return out


def hero_signature(kind, plan, ctx, h, eyebrow, actions, visual, secs):
    title_txt, accent_txt = str(h.get("title") or ""), str(h.get("accent") or "")
    lead = f'<p class="lead">{e(h.get("lead"))}</p>' if h.get("lead") else ""
    first_id = secs[0]["_id"] if secs else ""
    acts = list(h.get("actions") or [])
    brand = str((plan.get("brand") or {}).get("name") or "")
    fc = _sig_bits(plan, ctx, h)
    if kind == "poster":
        badge = (f'<a class="m42-hp-badge" href="#{first_id}" aria-label="{e(acts[1] if len(acts) > 1 else "More")}"><svg viewBox="0 0 120 120" aria-hidden="true">'
                 f'<defs><path id="m42hpc" d="M60,60 m-45,0 a45,45 0 1,1 90,0 a45,45 0 1,1 -90,0"/></defs>'
                 f'<text><textPath href="#m42hpc">{e((brand + " · " + (acts[1] if len(acts) > 1 else "Learn more") + " · ") * 2)}</textPath></text></svg>'
                 f'<i class="bi bi-arrow-up-right"></i></a>')
        card = ""
        if fc:
            card = (f'<a class="m42-hp-card" href="#{fc[0]["_id"]}">{widgets.photo(fc[1], "m42-hp-card-img")}'
                    f'<b>{e(acts[0] if acts else fc[1].get("title"))}</b><span class="m42-hp-go"><i class="bi bi-arrow-right"></i></span></a>')
        band = (f'<div class="m42-hp-band"><div class="m42-hp-band-l"><b>{e(accent_txt or title_txt)}</b>{lead}</div>'
                f'<a class="m42-hp-more" href="#{first_id}">{e(acts[1] if len(acts) > 1 else "Explore more")} <i class="bi bi-arrow-down"></i></a>'
                f'<div class="m42-hp-band-r">{_sig_stats(h, "m42-hp-stat")}</div></div>')
        short = len(f"{title_txt} {accent_txt}".strip()) <= 26  # (a short headline: the product rises over its last line)
        return (f'<div class="m42-hp{" is-short" if short else ""}">{eyebrow}<h1 class="m42-hp-title">{e(title_txt)} <span>{e(accent_txt)}</span></h1>'
                f'<div class="m42-hp-stage"><div class="m42-hp-obj">{visual}</div>{card}{badge}</div>'
                f'<div class="m42-actions justify-content-center m42-hp-acts">{actions}</div>{band}</div>')
    if kind == "duo":
        words = title_txt.split()
        thin, bold = (title_txt, accent_txt) if accent_txt else (" ".join(words[:max(1, len(words) // 2)]), " ".join(words[max(1, len(words) // 2):]))
        card = ""
        if fc:
            it = fc[1]
            val = amount(it.get("value"), it.get("unit") or "") if it.get("value") not in (None, "") else ""
            card = (f'<a class="m42-hd-card" href="#{fc[0]["_id"]}">{widgets.photo(it, "m42-hd-card-img")}<div><small>{e(fc[0].get("title") or "")}</small>'
                    f'<b>{e(it.get("title"))}</b>' + (f'<strong>{val}</strong>' if val else "") + '</div><span class="m42-hd-go"><i class="bi bi-arrow-up-right"></i></span></a>')
        return (f'<div class="m42-hd"><div class="m42-hd-text">{eyebrow}<h1><span class="m42-hd-thin">{e(thin)}</span> <span class="m42-hd-bold">{e(bold)}</span></h1>'
                f'{lead}<div class="m42-actions">{actions}</div></div>'
                f'<div class="m42-hd-panel"><div class="m42-hd-obj">{visual}</div><div class="m42-hd-stats">{_sig_stats(h, "m42-hd-stat")}</div></div>{card}</div>')
    if kind == "showroom":
        return (f'<div class="m42-hs"><span class="m42-hs-dot is-a"></span><span class="m42-hs-dot is-b"></span><span class="m42-hs-dot is-c"></span>'
                f'<div class="m42-hs-words">{eyebrow}<h1>{e(title_txt)} <em>{e(accent_txt)}</em></h1></div>'
                f'<div class="m42-hs-obj"><span class="m42-hs-disc"></span>{visual}</div>'
                f'<div class="m42-hs-side">{lead}<div class="m42-actions">{actions}</div><div class="m42-hs-stats">{_sig_stats(h, "m42-hs-stat")}</div></div></div>')
    # diagonal
    dots = "".join(f'<span style="background:var(--m42-accent{x})"></span>' for x in ("", "-2", "-3"))
    big = (h.get("stats") or [{}])[0]
    return (f'<div class="m42-hg"><div class="m42-hg-obj">{visual}</div><div class="m42-hg-text">{eyebrow}<h1>{e(title_txt)} <span>{e(accent_txt)}</span></h1>'
            f'{lead}<div class="m42-hg-dots">{dots}</div>'
            + (f'<div class="m42-hg-big"><strong data-m42-count="{e(big.get("value") or 0)}" data-suffix="{e(big.get("suffix") or "")}">0</strong>'
               f'<span>{e(big.get("label"))}</span></div>' if big.get("label") else "")
            + f'<div class="m42-actions">{actions}</div></div></div>')


def lay_stage(sec, ctx):
    """Each thing on a huge soft half-circle, its name big above, the price and a button under it (a tea brand's
    tins, one per screen)."""
    rows = []
    for k, it in enumerate((sec.get("items") or [])[:4]):
        val = amount(it.get("value"), it.get("unit") or "") if it.get("value") not in (None, "") else ""
        rows.append(f'<div class="m42-lx-stage{" is-flip" if k % 2 else ""}" style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)">'
                    f'<h3>{e(it.get("title"))}</h3><div class="m42-lx-stage-pic"><span class="m42-lx-stage-arc"></span>{_lx_art(it, ctx, "m42-lx-stage-img")}</div>'
                    f'<div class="m42-lx-stage-foot"><p>{e(it.get("text"))}</p>' + (f'<strong>{val}</strong>' if val else "") + "</div></div>")
    return head(sec) + f'<div class="m42-lx-stages">{"".join(rows)}</div>'


def lay_watermark(sec, ctx):
    """A huge faded word behind (WHY), a photo, a numbered list with hairlines (001 GREAT TASTE)."""
    items = (sec.get("items") or [])[:6]
    word = (str(sec.get("eyebrow") or sec.get("title") or "").split() or ["·"])[0][:8]
    first = next((it for it in items if widgets.photo(it)), None)
    pic = widgets.photo(first, "m42-lx-wm-img") if first else ""
    rows = "".join(f'<li><span class="m42-lx-no">{k + 1:03d}</span><b>{e(it.get("title"))}</b></li>' for k, it in enumerate(items))
    return (f'<div class="m42-lx-wm"><span class="m42-lx-wm-word" aria-hidden="true">{e(word)}</span>'
            f'<div class="m42-lx-wm-head">{head(sec)}</div><div class="m42-lx-wm-body"><div class="m42-lx-wm-pic">{pic}</div>'
            f'<ol class="m42-lx-wm-list">{rows}</ol></div></div>')

def lay_grid(sec, ctx):
    """A grid of cards, each its own photo (else its icon), name, words and price: the layout chosen in an edit when
    each thing must show its own photo (a theme's own drawing of a site's things can be a text menu, 2026-11-16)."""
    cards = "".join(f'<article class="m42-lx-card"><div class="m42-lx-card-pic">{_lx_art(it, ctx, "m42-lx-card-img")}</div>'
                    f'<div class="m42-lx-card-body"><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>{_lx_end(it, sec)}</div></article>'
                    for it in (sec.get("items") or [])[:8])
    return head(sec) + f'<div class="m42-lx-grid">{cards}</div>'


LAYOUTS = {"grid": lay_grid, "zigzag": lay_zigzag, "orbit": lay_orbit, "spotlight": lay_spotlight, "carousel": lay_carousel,
           "collage": lay_collage, "numbers": lay_numbers, "stage": lay_stage, "watermark": lay_watermark}


FIGURE_RX = re.compile(r"\s*[₹$€£]?\s*\d[\d,.]*\s*[%+kKLMx★]*")  # a title that is a figure: "15+ Years", "₹25L+", "98%"
PHOTO_LAYOUTS = {"orbit": lambda n: 1, "spotlight": lambda n: 1, "watermark": lambda n: 1, "collage": lambda n: 3,
                 "stage": lambda n: (n + 1) // 2}  # (how many of its things need a photo)
LAYOUT_WEIGHT = {"stage": 9, "zigzag": 8, "orbit": 7, "watermark": 6, "spotlight": 5, "carousel": 4, "collage": 3, "grid": 2}


def design_layout(sec, ctx):
    """The section drawn in its theme's own layout (its turn in the theme's flow, so the next one differs), or ""
    for the part's usual layout."""
    own = sec.get("_layout")  # the layout the 4B chose for this section in an edit (editcheck.LAYOUT_SHOWS): over the
    if own and sec["part"] in ("cards", "image_cards", "features") and ctx.get("layout") == "site":  # theme's turn
        if own in LAYOUTS and own != "numbers":
            return LAYOUTS[own](sec, ctx)
    t = themes.THEMES.get(ARCH.get("design") or "")
    if not t or not ARCH.get("dhead") or ctx.get("layout") != "site":
        return ""
    items = sec.get("items") or []
    # things that are figures (15+ years, 500+ weddings, ₹25L+: each a number with its value) are numbers, whatever
    # part the 4B gave them: on a stage they came out as big titles with photos piled on them (2026-11-14)
    figures = len(items) >= 2 and all(it.get("value") not in (None, "") and FIGURE_RX.match(str(it.get("title") or "")) for it in items)
    if figures and sec["part"] in ("cards", "image_cards", "features", "stats") and len(items) <= 5:
        return lay_numbers(dict(sec, items=[dict(it, shown=str(it.get("title") or ""), title=it.get("text") or it.get("title"), text="")
                                            for it in items]), ctx)
    if sec["part"] in ("cards", "image_cards", "features") and 2 <= len(items) <= 8:
        flow = t.get("flow") or ["grid"]
        # the page's first things get the theme's heaviest layout (a wedding planner's packages as a 4-photo collage
        # looked plain beside the same packages on big half-circles, 2026-11-14); the lighter ones after it
        flow = sorted(flow, key=lambda f: -LAYOUT_WEIGHT.get(f, 0))
        # a layout made of photos only where the section has them (an orbit round an empty circle, 2026-11-14)
        pics = sum(1 for it in items if widgets.photo(it))
        flow = [f for f in flow if f not in PHOTO_LAYOUTS or pics >= PHOTO_LAYOUTS[f](len(items))] or ["grid"]
        k = ctx.get("_things", 0)
        ctx["_things"] = k + 1
        kind = flow[k % len(flow)]
        return LAYOUTS[kind](sec, ctx) if kind in LAYOUTS and kind != "grid" else ""  # (a theme's "grid": its own drawing)
    if sec["part"] == "stats" and t.get("stats") == "numbers" and 2 <= len(items) <= 5:
        return lay_numbers(sec, ctx)
    return ""

BLOCK_TAG_RX = re.compile(r"><(/?(?:section|aside|header|main|footer|nav|article|form|table|thead|tbody|tr|ul|ol|li|h[1-6]|p|div)\b)")
RAW_RX = re.compile(r"(<(script|style|pre|textarea)\b.*?</\2>)", re.S | re.I)


def tidy(html):
    """The page one block per line (sections, cards, rows...): it came out with the whole body on one line, so a
    later line edit (a correction to the built site) had to repeat the whole body and broke on any change in it.
    Inline tags stay together; script, style, pre and textarea are left as they are."""
    parts = RAW_RX.split(html)
    out, skip = [], 0
    for k, part in enumerate(parts):
        if skip:
            skip -= 1
            continue
        if RAW_RX.fullmatch(part or ""):
            out.append(part)
            skip = 1  # the group's tag name comes next in split()'s list
        else:
            out.append(BLOCK_TAG_RX.sub(lambda m: ">\n<" + m.group(1), part))
    return "".join(out)


def assign_icons(plan, request=""):
    """Every item's icon from its own words when the 4B named none or one that doesn't exist ("bi-bread",
    "bi-wine": black dots on the bakery page), else from its section's and the site's words (icons.py)."""
    import photos  # (its subject(): "Design a landing page for a Local Bakery..." -> "Local Bakery", no plane icon)
    site = f"{(plan.get('brand') or {}).get('name', '')} {photos.subject(request)}"
    brand = plan.get("brand") or {}
    if not icons.valid(icon(brand.get("icon"), "")) or (not icons.fits(icon(brand.get("icon"), ""), site) and icons.best(site)):
        brand["icon"] = icons.best(site) or "bi-stars"  # (an icon that has nothing to do with the site: the site's own)
    for sec in plan.get("sections") or []:
        ctx = f"{sec.get('title', '')} {sec.get('eyebrow', '')} {site}"
        for it in sec.get("items") or []:
            name = icon(it.get("icon"), "")
            if not icons.valid(name):
                it["icon"] = icons.best(f"{it.get('title', '')} {it.get('text', '')}", ctx) or "bi-stars"


FOOT_CUT_RX = re.compile(r"(?:©|\(c\)|copyright)\s*\d{0,4}|all rights reserved\.?|privacy policy|terms(?: of (?:service|use))?|"
                         r"\b(?:19|20)\d\d\b", re.I)


def site_footer(plan, secs, pages, current, social, short=None):
    """A site's footer: the brand with its line and the social links, the page's sections (or the site's pages), a
    contact column from the plan's own contact details, and the year (the 4B wrote "© 2023 ... | Privacy Policy |
    Terms" as one line of text)."""
    import datetime
    brand, short = plan["brand"], short or {}
    line = " ".join(FOOT_CUT_RX.sub(" ", str(plan.get("footer") or "")).replace("|", " ").split()).strip(" ·.,-")
    if line.lower() in ("", str(brand.get("name") or "").lower()):
        line = str((plan.get("hero") or {}).get("lead") or "")
    if pages:
        links = "".join(f'<li><a href="{e(f)}">{e(name)}</a></li>' for name, f in pages[:6])
    else:
        links = "".join(f'<li><a href="#{s["_id"]}">{e(short.get(id(s)) or (s.get("title") or "")[:28])}</a></li>'
                        for s in secs[:6] if s["part"] not in ("cta", "summary") and (s.get("title") or short.get(id(s))))
    words = " ".join(str(i.get("text") or "") + " " + " ".join(str(m) for m in i.get("meta") or [])
                     for s in secs for i in s.get("items") or []) + " " + str(plan.get("footer") or "")
    phone = re.search(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b", words)
    mail = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", words)
    contact = "".join(x for x in (
        f'<li><i class="bi bi-telephone"></i> <a href="tel:{e(re.sub(r"[^0-9+]", "", phone.group(0)))}">{e(phone.group(0))}</a></li>' if phone else "",
        f'<li><i class="bi bi-envelope"></i> <a href="mailto:{e(mail.group(0))}">{e(mail.group(0))}</a></li>' if mail else ""))
    legal = '<li><a href="#">Privacy</a></li><li><a href="#">Terms</a></li>'
    cols = (f'<div class="col-lg-5"><a class="m42-foot-brand" href="#"><i class="bi {icon(brand.get("icon"))}"></i> {e(brand.get("name"))}</a>'
            f'<p>{e(line[:150])}</p>{social}</div>'
            f'<div class="col-6 col-lg-3"><h5>{"Pages" if pages else "Explore"}</h5><ul>{links}</ul></div>'
            f'<div class="col-6 col-lg-4"><h5>{"Contact" if contact else "Company"}</h5><ul>{contact or legal}</ul></div>')
    return (f'<footer class="m42-footer is-site"><div class="container"><div class="row g-4">{cols}</div>'
            f'<div class="m42-foot-end"><span>© {datetime.date.today().year} {e(brand.get("name"))}. All rights reserved.</span>'
            + (f'<span><a href="#">Privacy</a> · <a href="#">Terms</a></span>' if contact else "") + "</div></div></footer>")


MOTION = {"level": ("none", "subtle", "lively"), "hero": ("none", "fade", "words", "slide"),
          "reveal": ("none", "fade-up", "stagger", "zoom"), "hover": ("none", "lift", "tilt", "glow"),
          "notify": ("none", "toast", "popup"),
          "backdrop": ("none", "fireworks", "particles", "stars", "bubbles", "waves", "aurora")}


SIZES = {"narrow": 50, "medium": 66, "wide": 83, "full": 100}
ALIGNS = {"left": "margin-right:auto", "center": "margin-inline:auto", "right": "margin-left:auto"}


def own_reveal(sec):
    """A section's own reveal (an edit: "intha section ku animation"), over the page's choice (m42-ui.js), and its own
    width / place (an edit: "table ah center la vai, width kammi pannu": a line edit put text-center on every table)."""
    out = f' data-m42-sec-reveal="{sec["reveal"]}"' if sec.get("reveal") in MOTION["reveal"] else ""
    if sec.get("hover") in MOTION["hover"]:  # (its own hover: an edit, the check's second try, 2026-11-16)
        out += f' data-m42-sec-hover="{sec["hover"]}"'
    size, align = sec.get("size"), sec.get("align")
    if size in SIZES or align in ALIGNS:
        width = SIZES.get(size, 100 if size == "full" else 66 if align in ("center", "right") else 100)
        out += f' style="max-width:{width}%;{ALIGNS.get(align, ALIGNS["center"])}" data-m42-size="{size or ""}"'
    return out


def motion_of(spec, layout="site"):
    """The page's motion and notices (spec["motion"], the 4B's choice, agent._motion), each value checked; without a
    choice: a site gets subtle motion and dialogs, an admin page its cards and charts coming in and corner notes."""
    m = (spec or {}).get("motion") if isinstance((spec or {}).get("motion"), dict) else {}
    base = ({"level": "subtle", "hero": "none", "reveal": "fade-up", "hover": "lift", "counters": True, "notify": "toast", "confirm": True}
            if layout == "app" else
            {"level": "subtle", "hero": "fade", "reveal": "fade-up", "hover": "lift", "counters": True, "notify": "popup", "confirm": False})
    base.update(progress=False, to_top=False, backdrop="none")
    out = dict(base)
    for k, allowed in MOTION.items():
        if m.get(k) in allowed:
            out[k] = m[k]
    for k in ("counters", "confirm", "progress", "to_top"):
        if isinstance(m.get(k), bool):
            out[k] = m[k]
    return out


def render(plan, spec, theme, request="", pages=None, current="index.html"):
    """The whole page (CDN kit tags; wire_chat_page then adds the look and fixes what needs it)."""
    global CURRENCY
    NAV_PICKS.clear()
    NAV_PICKS.update({k: v for k, v in (plan.get("nav_icons") or {}).items() if icons.valid(v)})
    if (spec or {}).get("intent") and not webkit.INTENT:
        webkit.INTENT.update(spec["intent"])  # (a saved page drawn again: the decisions made when it was built)
    plan = clean(plan, spec)
    CURRENCY = page_currency(f"{request} {json.dumps(plan, ensure_ascii=False)}")
    global PRICE_X
    PRICE_X = rupee_scale(plan, request) if CURRENCY == "₹" else 1
    assign_icons(plan, request)
    ids, ctx = set(), {}
    # the libraries the user named (agent: their asks), by npm name: a part that has a way to use one, uses it
    ctx["libs"] = {str(l.get("npm") or "").lower() for l in (spec or {}).get("libraries") or [] if isinstance(l, dict)}
    hero_kind = (spec or {}).get("hero") or ("search" if (plan["hero"].get("fields")) else "split")
    if (hero_kind == "compact" and current == "index.html" and widgets.photo(plan["hero"]) and not webkit.app_asked(request)
            and (spec or {}).get("ref_layout") != "sidebar"):
        # a site's home page with a photo is no app page: its hero shows the photo (the site map gave the T-shirt and
        # coworking home pages a compact app head, and their photo was never seen, 2026-11-06)
        hero_kind = "image"
    secs = plan["sections"]
    for s in secs:
        s["_id"] = slug(s.get("title") or s["part"], ids)
    if (spec or {}).get("ref_grid"):  # how each reference card is drawn inside (designref.clean_card "look"), card i = section i
        for s, x in zip(secs, (spec or {}).get("sections") or []):
            if isinstance(x, dict) and x.get("look"):
                s["_look"] = x["look"]
            if isinstance(x, dict) and x.get("side"):
                s["_side"] = True
    ARCH["arch"] = ((theme or {}).get("look") or {}).get("archetype") or (((spec or {}).get("look") or {}).get("archetype") or "")
    ARCH["head"] = int(hashlib.md5(str((plan.get("brand") or {}).get("name") or request).encode()).hexdigest(), 16) % 2
    if ARCH["arch"] not in ARCHES or (hero_kind in ("compact", "none") and webkit.app_asked(request)):
        ARCH["arch"] = ""  # (an admin page or an app screen keeps its app layout: "saas" there is only its look)
    # 🎨 the page's theme (themes.py, the 4B's pick): how a section's title sits; its hero's layout
    _lk = (theme or {}).get("look") or {}
    ARCH["design"] = _lk.get("design") or ""
    ARCH["dhead"] = (_lk.get("head") or "") if ARCH["design"] and not (hero_kind in ("compact", "none") and webkit.app_asked(request)) else ""
    _dhero = (themes.THEMES.get(ARCH["design"]) or {}).get("hero") if ARCH["dhead"] else ""
    if _dhero and hero_kind not in ("search", "compact", "none"):
        hero_kind = _dhero
    ctx["side_menu"] = (spec or {}).get("side_menu") or []  # the reference's own menu entries, as read
    ctx["doodle"] = ((spec or {}).get("motion") or {}).get("doodle") if isinstance((spec or {}).get("motion"), dict) else ""
    ctx.update(site_key=(plan.get("brand") or {}).get("name") or request, hero_photo=(plan.get("hero") or {}).get("photo"),
               # a page with a real hero is a site page (a CRM's landing page too: "CRM" is an app word)
               people_ok=hero_kind not in ("compact", "none") and webkit.live_kind(request) == "none")
    ctx.update(dark_side_ok=(theme.get("look") or {}).get("theme") != "dark", ref_head=(spec or {}).get("ref_head"), top_bar=(spec or {}).get("top_bar"), ref_grid=(spec or {}).get("ref_grid"), ref_counts=[x.get("count", 0) for x in (spec or {}).get("sections") or []
                                                                 if isinstance(x, dict)], ids=ids, feeds=[], live=webkit.live_kind(request) != "none", device=bool(webkit.live_kind(request) == "device"), brand_icon=plan["brand"].get("icon"),
               first_id=secs[0]["_id"] if secs else "", next_after={})
    for n, s in enumerate(secs):  # "Select" / "Continue" go to the next section
        ctx["next_after"][s["_id"]] = secs[n + 1]["_id"] if n + 1 < len(secs) else ""
    ctx["results_id_hint"] = next((s["_id"] + "-list" for s in secs if s["part"] == "results"), "")
    ctx["app_screens"] = (spec or {}).get("app_screens") or []
    ctx["app_layout"] = (spec or {}).get("app_layout") or None  # 🦴 the skeleton's columns (appflows.LAYOUTS)

    rows = (spec or {}).get("sections") or [] if (spec or {}).get("recipe") else []  # M42's section order: its names
    short = {id(s): rows[k]["name"] for k, s in enumerate(secs) if k < len(rows) and rows[k].get("part") == s["part"]
             and not rows[k].get("role_named") and _label_like(rows[k]["name"])}  # (a section the 4B named only by its role ("trust"): the menu shows its title)
    nav_links = "".join(f'<li class="nav-item"><a class="nav-link" href="#{s["_id"]}">'
                        f'{e(short.get(id(s)) or (s.get("eyebrow") or s.get("title") or "")[:18])}</a></li>'
                        for s in secs[:5] if s["part"] not in ("cta", "summary"))
    nav_cta = ""
    if rows and not pages and (plan["hero"].get("actions") or [None])[0]:  # a landing page: its call in the bar too
        goal = next((s["_id"] for s in secs if s["part"] in ("prices", "form", "contact")), secs[-1]["_id"] if secs else "")
        nav_cta = (f'<li class="nav-item ms-lg-2"><a class="m42-btn m42-btn-sm" href="#{goal}">'
                   f'{e(str(plan["hero"]["actions"][0])[:22])}</a></li>')
    if pages:  # a site of several pages (a project folder): the menu is the pages
        nav_links = "".join(f'<li class="nav-item"><a class="nav-link{" active" if f == current else ""}" href="{e(f)}"'
                            + (' aria-current="page"' if f == current else "") + f'>{e(name)}</a></li>' for name, f in pages)
    brand = plan["brand"]
    nav = (f'<nav class="navbar navbar-expand-lg m42-nav"><div class="container">'
           f'<a class="navbar-brand" href="#"><i class="bi {icon(brand.get("icon"))}"></i> {e(brand.get("name"))}</a>'
           '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#m42nav" aria-label="Menu">'
           '<span class="navbar-toggler-icon"></span></button><div class="collapse navbar-collapse" id="m42nav">'
           f'<ul class="navbar-nav ms-auto align-items-lg-center gap-lg-1">{nav_links}'
           + ('<li class="nav-item ms-lg-2"><span class="m42-status" id="conn"></span></li>'
              '<li class="nav-item ms-lg-2"><span class="m42-updated"></span></li>' if ctx["live"] else "") + nav_cta +
           "</ul></div></div></nav>")

    h = plan["hero"]
    def hero_count(st):  # "₹" goes before the number (the 4B wrote it as the suffix: 12,450₹)
        suf = str(st.get("suffix") or "")
        pre = suf if suf in ("₹", "$", "€", "£") else ""
        return (f'<strong class="fs-3" data-m42-count="{e(st.get("value") or 0)}" data-prefix="{e(pre)}" '
                f'data-suffix="{e("" if pre else suf)}">0</strong>')
    stats = "".join(f'<div>{hero_count(st)}<div class="m42-muted">{e(st.get("label"))}</div></div>' for st in h.get("stats") or [])
    stats = f'<div class="d-flex gap-4 flex-wrap mt-4{" justify-content-center" if hero_kind in ("search", "centered") else ""}">{stats}</div>' if stats else ""
    first = secs[0]["_id"] if secs else ""
    actions = "".join(f'<a class="{"m42-btn" if n == 0 else "m42-btn-ghost"}" href="#{first}">{e(a)}'
                      + (' <i class="bi bi-arrow-right"></i>' if n == 0 else "") + "</a>" for n, a in enumerate(h.get("actions") or []))
    long_title = len(f'{h.get("title") or ""} {h.get("accent") or ""}') > 34
    long_cls = ' class="is-long"' if long_title else ""
    title = (f'<h1{long_cls}>{e(h.get("title"))} '
             f'<span class="m42-gradient-text">{e(h.get("accent"))}</span></h1>')
    eyebrow = f'<span class="m42-eyebrow"><i class="bi bi-stars"></i> {e(h.get("eyebrow"))}</span>' if h.get("eyebrow") else ""
    lead = f'<p class="lead">{e(h.get("lead"))}</p>' if h.get("lead") else ""
    arch = ARCH["arch"]
    scene3d = plan.get("scene3d") if isinstance(plan.get("scene3d"), dict) else None
    def proof_chips():  # 🎨 the hero's own numbers floating on its picture (depth: "flat design lacks depth", the 4B's
        # look against the user's premium shots, 2026-11-14)
        return "".join(f'<div class="m42-proof is-{"ab"[k]}"><b>{e(st.get("value"))}{e(st.get("suffix") or "")}</b><span>{e(st.get("label"))}</span></div>'
                       for k, st in enumerate((h.get("stats") or [])[:2]) if st.get("label"))
    if hero_kind in ("giant", "block", "bleed", "poster", "duo", "showroom", "diagonal"):
        # 🎨 a theme's hero with its own weight (themes.py): giant words with the picture over them, a coloured block
        # holding the picture and the numbers, or the picture running off the page's edge
        if scene3d:
            visual = (f'<div class="m42-3d" role="img" aria-label="{e(scene3d.get("alt") or h.get("title") or "")}" '
                      f'data-m42-3d="{e(json.dumps(scene3d, ensure_ascii=False))}"><canvas></canvas></div>')
        elif widgets.photo(h):
            visual = widgets.photo(dict(h, title=h.get("title")), "m42-hx-img") + (proof_chips() if hero_kind in ("showroom", "bleed", "giant", "diagonal") else "")
        else:
            visual = showcase(plan, ctx)
        acts = f'<div class="m42-actions">{actions}</div>' if actions else ""
        if hero_kind in ("poster", "duo", "showroom", "diagonal"):
            body = hero_signature(hero_kind, plan, ctx, h, eyebrow, actions, visual, secs)
        elif hero_kind == "giant":
            body = (f'<div class="m42-hx-giant"><div class="m42-hx-top">{eyebrow}{title}</div><div class="m42-hx-visual">{visual}</div>'
                    f'<div class="m42-hx-foot"><div>{lead}{acts}</div>{stats}</div></div>')
        elif hero_kind == "block":
            body = (f'<div class="m42-hx-block"><div class="m42-hx-text">{eyebrow}{title}{lead}{acts}</div>'
                    f'<div class="m42-hx-panel"><div class="m42-hx-visual">{visual}</div>{stats}</div></div>')
        else:
            body = (f'<div class="m42-hx-bleed"><div class="m42-hx-text">{eyebrow}{title}{lead}{acts}{stats}</div>'
                    f'<div class="m42-hx-visual"><span class="m42-hx-disc"></span>{visual}</div></div>')
    elif scene3d and hero_kind != "none":
        # 🧊 a 3D scene beside the words (the request asked for 3D; the 4B chose its objects, story and extras:
        # agent.scene_3d); bundled/m42-3d.js draws it with three.js, the page's own colours
        alt = e(scene3d.get("alt") or h.get("title") or "")
        body = (f'<div class="row align-items-center g-5"><div class="col-lg-6">{eyebrow}{title}{lead}'
                f'<div class="m42-actions">{actions}</div>{stats}</div><div class="col-lg-6">'
                f'<div class="m42-3d" role="img" aria-label="{alt}" data-m42-3d="{e(json.dumps(scene3d, ensure_ascii=False))}"><canvas></canvas></div>'
                f'</div></div>')
        hero_kind = "split"
    elif arch == "product" and hero_kind not in ("search", "none"):
        # Apple-like: the words centred, the product big under them, its numbers in a quiet row
        shot = (widgets.photo(dict(h, title=h.get("title")), "m42-product-photo") if widgets.photo(h) else art(ctx, icon(ctx["brand_icon"])))
        body = (f'<div class="text-center">{eyebrow}{title}{lead}<div class="m42-actions justify-content-center">{actions}</div></div>'
                f'<div class="m42-product-shot">{shot}</div>'
                + (stats.replace("d-flex gap-4", "d-flex gap-5 justify-content-center m42-product-stats") if stats else ""))
        hero_kind = "product"
    elif arch == "editorial" and hero_kind not in ("search", "none"):
        # serif, left-aligned, a rule; the photo wide under it
        side = "".join(f'<li><b>{e(st.get("value"))}{e(st.get("suffix") or "")}</b><span>{e(st.get("label"))}</span></li>'
                       for st in h.get("stats") or [])
        body = (f'<div class="row g-5 align-items-end"><div class="col-lg-8">{eyebrow}{title}{lead}'
                f'<div class="m42-actions">{actions}</div></div>'
                + (f'<div class="col-lg-4"><ul class="m42-ed-facts">{side}</ul></div>' if side else "") + "</div>"
                + (f'<figure class="m42-ed-photo">{widgets.photo(dict(h, title=h.get("title")), "m42-ed-photo-img")}</figure>' if widgets.photo(h) else ""))
        hero_kind = "editorial"
    elif arch == "saas" and hero_kind not in ("search", "none"):
        # centred words over a grid, the product in a browser frame under them (Linear / Vercel-like)
        shot = (widgets.photo(dict(h, title=h.get("title")), "m42-saas-photo") if widgets.photo(h) else showcase(plan, ctx))
        body = (f'<div class="text-center m42-saas-top">{eyebrow}{title}{lead}<div class="m42-actions justify-content-center">{actions}</div></div>'
                f'<div class="m42-saas-frame"><div class="m42-saas-bar"><span></span><span></span><span></span></div>'
                f'<div class="m42-saas-screen">{shot}</div></div>'
                + (stats.replace("d-flex gap-4", "d-flex gap-5 justify-content-center m42-saas-stats") if stats else ""))
        hero_kind = "saas"
    elif arch == "bold" and hero_kind not in ("search", "none"):
        # huge type on the page's own full gradient; the photo, when there is one, as a tilted card
        pic = (f'<div class="col-lg-5"><div class="m42-bold-pic">{widgets.photo(dict(h, title=h.get("title")), "m42-bold-photo")}</div></div>'
               if widgets.photo(h) else "")
        body = (f'<div class="row align-items-center g-5"><div class="{"col-lg-7" if pic else "col-12 text-center"}">{eyebrow}{title}{lead}'
                f'<div class="m42-actions{"" if pic else " justify-content-center"}">{actions}</div>{stats}</div>{pic}</div>')
        hero_kind = "bold"
    elif arch == "portfolio" and hero_kind not in ("search", "none"):
        # a big plain name, a line, the links; the photo wide under it
        body = (f'<div class="m42-pf-top">{eyebrow}{title}{lead}<div class="m42-actions">{actions}</div></div>'
                + (f'<figure class="m42-pf-photo">{widgets.photo(dict(h, title=h.get("title")), "m42-pf-photo-img")}</figure>' if widgets.photo(h) else ""))
        hero_kind = "portfolio"
    elif hero_kind == "search":
        fields = "".join(field_html(f, "hero", ids) for f in (h.get("fields") or [{"label": "Search", "type": "text"}]))
        body = (eyebrow + title + lead + f'<form class="m42-search" data-m42-search-for="{ctx["results_id_hint"]}">{fields}'
                '<div><button class="m42-btn w-100"><i class="bi bi-search"></i> Search</button></div></form>' + stats)
    elif hero_kind == "split" and widgets.photo(h):  # a real photo (photos.py) with the site's first item over it
        visual = (f'<div class="m42-showcase has-photo">{widgets.photo(dict(h, title=h.get("title")), "m42-hero-photo")}'
                  + "".join(re.findall(r'<div class="m42-float is-a">.*?</div></div>', showcase(plan, ctx))[:1]) + "</div>")
        body = (f'<div class="row align-items-center g-5"><div class="col-lg-6">{eyebrow}{title}{lead}'
                f'<div class="m42-actions">{actions}</div>{stats}</div><div class="col-lg-6">{visual}</div></div>')
    elif hero_kind == "split":
        visual = showcase(plan, ctx)
        body = (f'<div class="row align-items-center g-5"><div class="col-lg-6">{eyebrow}{title}{lead}'
                f'<div class="m42-actions">{actions}</div>{stats}</div><div class="col-lg-6">{visual}</div></div>')
    else:
        body = eyebrow + title + lead + (f'<div class="m42-actions">{actions}</div>' if actions else "") + stats
    kind = hero_kind if hero_kind in ("search", "split", "centered", "image", "compact", "giant", "block", "bleed", "poster", "duo",
                                   "showroom", "diagonal") + ARCHES else "centered"
    bg = ""
    if kind in ("centered", "image", "search") and widgets.photo(h) and not arch:  # the photo behind the hero's words
        # (inline: a url() inside a CSS variable is read from lib/m42-ui.css's folder, lib/images/: no photo)
        kind, bg = ("image" if kind != "search" else kind), (' style="background-image: linear-gradient(90deg, rgba(10, 8, 6, .78), '
                                                             f'rgba(10, 8, 6, .3)), url({e(h["photo"])})"')
    if long_title:  # (every kind of hero: "Your Perfect Smile, Engineered With Precision" took 5 lines in a split hero
        # whose heading had no "is-long", 2026-11-16)
        body = re.sub(r'<h1(?: class="([^"]*)")?>', lambda m: m.group(0) if "is-long" in (m.group(1) or "") else
                      '<h1 class="' + ((m.group(1) + " ") if m.group(1) else "") + 'is-long">', body, count=1)
    hero = "" if hero_kind == "none" else f'<header class="m42-hero is-{kind}{" has-photo" if bg else ""}"{bg}><div class="container">{body}</div></header>' + (marquee(plan) if kind == "bold" else "")
    import blocks  # (🧱 the premium blocks: they draw with this module's head)
    hb = (plan.get("hero") or {}).get("_block")
    if hb in blocks.BLOCKS and hero_kind not in ("none", "compact", "search") and not webkit.app_asked(request):
        # 🧱 the hero chosen from the user's premium references (agent._pick_blocks): it draws its own stage
        hero = f'<header class="m42-b-herowrap" data-m42-block="{e(hb)}">{blocks.draw(hb, blocks.from_hero(plan), ctx)}</header>'

    auth_sec = next((s for s in secs if s["part"] in ("form", "contact")
                     and any(f.get("type") == "password" for f in s.get("fields") or [])), None)
    ref_layout = (spec or {}).get("ref_layout")  # from the reference design (designref.py): it decides, else the words
    layout = ("auth" if auth_sec and (hero_kind == "none" or ref_layout == "split-screen") else
              "app" if ref_layout == "sidebar" or (ref_layout not in ("top-nav", "single-column")
                                                  and webkit.app_asked(request) and hero_kind in ("compact", "none"))
              else "site")
    ctx["layout"] = layout  # (variant(): site sections get their layouts, app pages the first one)
    if layout == "site" and hero_kind == "none" and secs:
        # a page that is one app view (a chat screen, a mail screen: appviews.py) has no hero: its heading for screen
        # readers and the outline, and the section close under the menu
        hero = f'<h1 class="visually-hidden">{e(secs[0].get("title") or brand.get("name"))}</h1>'
    if layout == "auth":
        body = auth_layout(plan, ctx, auth_sec, pages)
    elif layout == "app":
        body = app_layout(plan, ctx, pages, current, request)
    out, n, alt = [], 0, False
    # 🎨 one deep band in the middle of a themed page (contrast: light, deep, light), on what proves the business (what
    # people say, else its numbers), the one nearest the middle
    proofs = [x for x in secs if x["part"] in ("reviews", "stats")] if ARCH.get("design") and layout == "site" else []
    proofs = [x for x in proofs if not x.get("_block")]  # (a premium block has its own colours)
    band_sec = min(proofs, key=lambda x: abs(secs.index(x) - len(secs) / 2)) if proofs and len(secs) >= 4 else None
    while n < len(secs) and layout == "site":
        s = secs[n]
        bleed = False
        # results / picks / a form followed by a summary: one section, the summary beside them (sticky)
        group = [s]
        while (group[-1]["part"] in SIDE_WITH_SUMMARY and n + len(group) < len(secs)
               and secs[n + len(group)]["part"] in SIDE_WITH_SUMMARY + ("summary",)):
            group.append(secs[n + len(group)])
            if group[-1]["part"] == "summary":
                break
        ctx["sec_n"] = n
        ARCH["n"] = n + 1
        lay = design_layout(s, ctx) if not (len(group) > 1 and group[-1]["part"] == "summary") else ""
        if s.get("_block") in blocks.BLOCKS and len(group) == 1:  # 🧱 its premium block (agent._pick_blocks)
            b = blocks.BLOCKS[s["_block"]]
            inner = blocks.draw(s["_block"], blocks.from_action(plan, s) if b["role"] == "action" else s, ctx)
            bleed = bool(b.get("bleed"))
            sid = s["_id"]
            n += 1
        elif len(group) > 1 and group[-1]["part"] == "summary":
            left = "".join(f'<div id="{g["_id"]}" class="mb-4">' + PARTS[g["part"]](g, ctx) + "</div>" for g in group[:-1])
            inner = (f'<div class="row g-4"><div class="col-lg-8">{left}</div>'
                     f'<div class="col-lg-4" id="{group[-1]["_id"]}">{PARTS["summary"](group[-1], ctx)}</div></div>')
            sid = group[0]["_id"] + "-wrap"
            n += len(group)
        elif (s.get("_shape"), s["part"]) in SHAPED:  # the shape the spec asked for (a carousel, an accordion, steps)
            ctx["sec_n"] = n
            ARCH["n"] = n + 1
            inner = SHAPED[(s["_shape"], s["part"])](s, ctx)
            sid = s["_id"]
            n += 1
        elif lay:  # 🎨 the theme's own layout for it
            ctx["sec_n"] = n
            ARCH["n"] = n + 1
            inner = lay
            sid = s["_id"]
            n += 1
        elif s["part"] in widgets.OWN_BAND:  # a band that is a section of its own (video, newsletter): its own words
            inner = PARTS[s["part"]](s, ctx)
            sid = s["_id"]
            n += 1
        elif s["part"] == "image_cards" and ARCH["arch"] == "product":  # a product page's line-up
            ARCH["n"] = n + 1
            inner = p_lineup(s, ctx)
            sid = s["_id"]
            n += 1
        elif s["part"] == "image_cards":  # a site's things with prices: by the design (p_site_things)
            ctx["sec_n"] = n
            ARCH["n"] = n + 1
            inner = p_site_things(s, ctx)
            sid = s["_id"]
            n += 1
        elif s["part"] in widgets.WIDGETS:  # a widget on a site page: the section's big head, the widget in a card
            body = PARTS[s["part"]](dict(s, title="", lead="", eyebrow=""), ctx)
            inner = head(s) + (body if s["part"] in widgets.BARE else f'<div class="m42-panel">{body}</div>')
            sid = s["_id"]
            n += 1
        else:
            ctx["sec_n"] = n
            ARCH["n"] = n + 1
            inner = PARTS[s["part"]](s, ctx)
            if s["part"] in ("results", "picks", "summary", "form"):
                inner = head(s) + inner if s["part"] in ("picks", "summary", "form") else inner
            sid = s["_id"]
            n += 1
        cls = ("m42-section" + (" m42-section-alt" if alt else "") + (" is-app" if s["part"] in ("chat_app", "mail_app") else "")
               + (" is-band" if s is band_sec else ""))
        if s.get("_block") in blocks.BLOCKS and sid == s["_id"]:
            cls += " m42-b-sec" + (" m42-b-bleed" if bleed else "")
        tag = f' data-m42-block="{e(s["_block"])}"' if s.get("_block") in blocks.BLOCKS and sid == s["_id"] else ""
        out.append(f'<section id="{sid}" class="{cls}"{tag}{own_reveal(s)}>' + (inner if bleed else f'<div class="container">{inner}</div>') + "</section>")
        alt = not alt
    social = ('<span class="m42-social"><a href="#" aria-label="Instagram"><i class="bi bi-instagram"></i></a>'
              '<a href="#" aria-label="WhatsApp"><i class="bi bi-whatsapp"></i></a></span>')
    footer = (f'<footer class="m42-footer"><div class="container d-flex justify-content-between flex-wrap gap-3">'
              f'<span><i class="bi {icon(brand.get("icon"))}"></i> {e(brand.get("name"))} · {e(plan.get("footer"))}</span>'
              f'{social}</div></footer>')
    if layout == "site" and len(secs) >= 3:
        footer = site_footer(plan, secs, pages, current, social, short)
    feeds = ""
    data = (spec or {}).get("data") or {}
    if ctx["feeds"] and data.get("fields") and webkit.live_kind(request) == "device":
        # readings from a device / API: fetched every few seconds, demo values while it can't be reached
        where = data.get("where") or ""
        url = where if re.match(r"https?://", where) else ("http://" + where.split()[0] if re.match(r"\d+\.\d+\.\d+\.\d+", where)
                                                          else "http://192.168.x.x/data")
        sets = []
        for f in data["fields"]:
            sid = next((i for i in ids if f.lower()[:4] in i), None)
            if sid:
                sets.append(f"if (d[{json.dumps(f)}] != null) M42UI.set('{sid}', d[{json.dumps(f)}]);")
        feeds = ("<script>\nconst API_URL = " + json.dumps(url) + ";  // your device's address\n"
                 "function m42Demo() {\n  " + "\n  ".join(ctx["feeds"]) + "\n}\n"
                 "async function m42Tick() {\n  try {\n    const r = await fetch(API_URL);\n    if (!r.ok) throw new Error(r.status);\n"
                 "    const d = await r.json();\n    " + "\n    ".join(sets) + "\n    M42UI.status('conn', 'online');\n"
                 "  } catch (err) {\n    m42Demo();\n    M42UI.status('conn', 'demo');\n  }\n  M42UI.touch();\n}\n"
                 "for (let i = 0; i < 30; i++) m42Demo();\nm42Tick();\nsetInterval(m42Tick, 5000);\n</script>\n")
    elif ctx["feeds"]:
        feeds = ("<script>\nfunction m42Tick() {\n  " + "\n  ".join(ctx["feeds"]) + "\n  M42UI.touch();\n}\n"
                 "for (var i = 0; i < 30; i++) m42Tick();\nsetInterval(m42Tick, 3000);\n</script>\n")
    C = webkit.CDN
    mo = motion_of(spec, layout)
    whole = nav + hero + "".join(out) + (body if layout != "site" else "")
    # the libraries this page's choice needs (the 4B's, agent._motion): anime.js for motion, Toastr for corner notes,
    # SweetAlert2 for dialogs and for the widgets that ask before they act
    # (the model said "asks before deleting" for a law firm's landing page: a yes-first dialog only where the page has
    # such an action, a delete / remove button or a widget that asks)
    acts = bool(re.search(r"data-m42-(confirm|view|alert|remove)|bi-trash", whole))
    swal = mo["notify"] == "popup" or (mo["confirm"] and acts) or acts
    css_more = (f'<link rel="stylesheet" href="{C["toastr.min.css"]}">\n' if mo["notify"] == "toast" else "")
    any_own = any(x.get("reveal") not in (None, "", "none") for x in plan.get("sections") or [])
    js_more = ((f'<script src="{C["anime.min.js"]}"></script>\n' if mo["level"] != "none" or any_own else "")
               # (Toastr is a jQuery plugin: jQuery only on the pages that chose its notes)
               + (f'<script src="{C["jquery.min.js"]}"></script>\n<script src="{C["toastr.min.js"]}"></script>\n'
                  if mo["notify"] == "toast" else "")
               + (f'<script src="{C["sweetalert2.all.min.js"]}"></script>\n' if swal else ""))
    attrs = " ".join(f'data-m42-{k}="{e(v)}"' for k, v in (("motion", mo["level"]), ("hero-in", mo["hero"]), ("reveal", mo["reveal"]),
                                                           ("hover", mo["hover"]), ("counters", "1" if mo["counters"] else "0"),
                                                           ("notify", mo["notify"]), ("progress", "1" if mo["progress"] else "0"),
                                                           ("to-top", "1" if mo["to_top"] else "0"),
                                                           ("backdrop", mo["backdrop"] if layout == "site" else "none")))
    if ARCH["arch"] and layout == "site":
        attrs += f' data-m42-archetype="{ARCH["arch"]}"'
    page = (f'<!DOCTYPE html>\n<html lang="en" {attrs}>\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{e(brand.get("name"))}</title>\n'
            f'<link rel="stylesheet" href="{C["bootstrap.min.css"]}">\n<link rel="stylesheet" href="{C["bootstrap-icons.min.css"]}">\n'
            f'<link rel="stylesheet" href="{C["m42-ui.css"]}">\n{css_more}</head>\n'
            + (f'<body class="m42-ui {"m42-app" if layout == "app" else "m42-signin"}'
               f'{" is-rail" if layout == "app" and ((spec or {}).get("ref_grid") or {}).get("rail") else ""}">\n{body}\n'
               if layout != "site" else
               f'<body class="m42-ui">\n{nav}\n{hero}\n' + "\n".join(out) + f"\n{footer}\n")
            + f'<script src="{C["bootstrap.bundle.min.js"]}"></script>\n{js_more}'
            f'<script src="{C["m42-ui.js"]}"></script>\n{feeds}</body>\n</html>\n')
    return tidy(webkit.wire_chat_page(page, theme))
