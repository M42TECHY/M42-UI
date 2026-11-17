"""The default web kit for the websites M42 builds: Bootstrap 5.3 + Bootstrap Icons, jQuery, SweetAlert2,
Toastr and anime.js, shipped in bundled/ (offline, no CDN), plus a theme M42 computes itself.

The user's idea (2026-10-25): a 7B coder writing its own CSS breaks layouts and spaces everything differently;
with Bootstrap it only names classes (row, col-md-4, card, btn-primary) and the grid, spacing and responsive
layout come out right. The checks follow the embedded rule: from the library's own files, not hand lists:
  - a class the code uses must exist in the CSS that is loaded (bootstrap.min.css, the icons, style.css), so a
    Bootstrap 4 name (ml-3, data-toggle) or an invented one (btn-gradient, bi-facebok) is found without a model;
  - Swal.x / toastr.x / anime.x / bootstrap.x must be a name the library file has;
  - only what the code uses is wired (jQuery only if $ is used or Toastr needs it), the rest is left out;
  - a phone-width render measures overflow, text contrast, images without alt, inputs without labels, the h1.
"""
import colorsys
import contextlib
import difflib
import hashlib
import json
import re
import shutil
from pathlib import Path

BUNDLED = Path(__file__).resolve().parent / "bundled"
THEME_FILE = "lib/m42-theme.css"

# in load order; "use": when the code needs it; "needs": another kit library it runs on
KIT = [
    {"name": "Bootstrap 5.3.3", "css": ["bootstrap.min.css"], "js": [], "use": r"."},
    {"name": "Bootstrap Icons 1.11.3", "css": ["bootstrap-icons.min.css"], "js": [], "use": r"\bbi-[a-z0-9]",
     "fonts": ["fonts/bootstrap-icons.woff2", "fonts/bootstrap-icons.woff"]},
    # Lucide 1.59.0 (ISC): ~1,900 more icons with search tags (croissant, sandwich, dumbbell...): icons.py picks them
    {"name": "Lucide 1.59.0", "css": ["lucide.css"], "js": [], "use": r"\blc-[a-z0-9]", "fonts": ["fonts/lucide.woff2"]},
    {"name": "Toastr 2.1.4", "css": ["toastr.min.css"], "js": [], "use": r"\btoastr\s*\."},
    {"name": "jQuery 3.7.1", "css": [], "js": ["jquery.min.js"], "use": r"(?<![\w$])\$\s*[.(]|\bjQuery\b",
     "global": "$"},
    {"name": "Bootstrap JS", "css": [], "js": ["bootstrap.bundle.min.js"],
     "use": r"\bdata-bs-\w|\bbootstrap\s*\.\s*[A-Z]|\.(?:modal|tooltip|popover|collapse|carousel|dropdown)\s*\(",
     "global": "bootstrap"},
    {"name": "SweetAlert2 11.14.5", "css": [], "js": ["sweetalert2.all.min.js"], "use": r"\bSwal\s*\.", "global": "Swal"},
    {"name": "Toastr JS", "css": [], "js": ["toastr.min.js"], "use": r"\btoastr\s*\.", "global": "toastr",
     "needs": "jquery.min.js"},
    {"name": "anime.js 3.2.2", "css": [], "js": ["anime.min.js"], "use": r"\banime\s*[.(]", "global": "anime"},
    # 3D scenes (only on a page whose request asked for 3D: data-m42-3d): three.js r128 (MIT) and M42's own 3D kit
    {"name": "three.js r128", "css": [], "js": ["three.min.js"], "use": r"data-m42-3d", "global": "THREE"},
    # a model file in the scene (the user's .glb / .stl, or one found online): three.js's own loaders (r128, MIT)
    {"name": "three.js GLTFLoader", "css": [], "js": ["GLTFLoader.js"], "use": r"&quot;model&quot;:\s*&quot;[^&]*\.gl(?:b|tf)&quot;",
     "needs": "three.min.js"},
    {"name": "three.js STLLoader", "css": [], "js": ["STLLoader.js"], "use": r"&quot;model&quot;:\s*&quot;[^&]*\.stl&quot;",
     "needs": "three.min.js"},
    {"name": "M42 3D", "css": [], "js": ["m42-3d.js"], "use": r"data-m42-3d", "global": "M42_3D", "needs": "three.min.js"},
    # M42's own premium components and motion for any page (bundled/m42-ui.*): last, so it styles over the rest
    {"name": "M42 UI", "css": ["m42-ui.css"], "js": ["m42-ui.js"], "use": r"\bm42-[a-z]|\bM42UI\b", "global": "M42UI",
     # the web fonts of the looks (Google Fonts, OFL; @font-face in m42-ui.css): copied with it, loaded only when used
     "fonts": ['fonts/poppins-600.woff2', 'fonts/poppins-700.woff2', 'fonts/inter-400.woff2', 'fonts/inter-600.woff2', 'fonts/playfair-display-700.woff2', 'fonts/lato-400.woff2', 'fonts/lato-700.woff2', 'fonts/space-grotesk-600.woff2', 'fonts/nunito-400.woff2', 'fonts/nunito-700.woff2', 'fonts/anton-400.woff2']},
]
KIT_FILES = [f for k in KIT for f in k["css"] + k["js"]]
KIT_GLOBALS = {k["global"]: k["js"][0] for k in KIT if k.get("global")}

PLAN_NOTE = """M42 loads a web kit for this site itself: Bootstrap 5.3 (+ Bootstrap Icons), jQuery, SweetAlert2,
Toastr, anime.js and M42 UI (premium parts and motion: navbar, heroes, search / booking card, result rows, picks,
summary box, cards, forms, stat cards, charts). Don't list them under libraries. Plan the page the way real sites of
THIS kind are built (a booking site: search hero, results, picking, a form, summary; a restaurant:
menu tabs, reservation; a portfolio: work gallery, about, contact), not one recipe for every site; mobile first;
premium, not plain."""

UI_NOTE = """M42 UI (premium look and motion for ANY page; it is loaded: use its classes, don't restyle them).
Build the page from the sections listed for it (the way real sites of this kind are built), using the parts that
fit; a part this kind of site needs that M42 UI lacks (a seat map, a menu board, a timetable), write it yourself
inside <div class="m42-card"> and style it only with var(--m42-accent), var(--m42-surface), var(--m42-border),
var(--m42-text), var(--m42-muted), var(--m42-radius), var(--m42-shadow) so it matches.
- <body class="m42-ui">; M42 sets light / dark and the style itself (no light / dark button on the page).
- Navbar: <nav class="navbar navbar-expand-lg m42-nav"><div class="container"><a class="navbar-brand" href="#">
  <i class="bi bi-..."></i> Name</a> + Bootstrap's toggler and collapse with <a class="nav-link" href="#section-id">.
- Hero, the kind given for the page: <header class="m42-hero is-search | is-split | is-centered | is-compact |
  is-image"><div class="container"> <span class="m42-eyebrow">..</span> <h1>.. <span class="m42-gradient-text">key
  words</span></h1> <p class="lead">..</p> then for is-search a search / booking card:
  <form class="m42-search"><div><label class="form-label" for="from">From</label><input id="from" class="form-control">
  </div> ...more fields... <button class="m42-btn"><i class="bi bi-search"></i> Search</button></form>; for others
  <div class="m42-actions"><a class="m42-btn" href="#..">Main action</a><a class="m42-btn-ghost" href="#..">..</a>
  </div>; is-split puts a <div class="m42-visual"> in a second column; is-compact for apps and tools.
- Sections: <section id=".." class="m42-section"> (m42-section-alt to alternate) <div class="container">
  <div class="m42-section-head"><span class="m42-eyebrow">..</span><h2>..</h2><p>..</p></div> + what it holds:
  results (rows to choose from: trips, doctors, products): <div class="m42-results"><div class="m42-item"><div><h3>Name</h3>
  <div class="m42-meta"><span><i class="bi bi-clock"></i> 21:30</span>..</div></div><div>details</div>
  <div class="m42-price-tag">₹899<small>per seat</small><button class="m42-btn mt-2">Select</button></div></div></div>
  filters: <div class="m42-chips" data-single><button class="m42-chip-btn active">All</button>..</div>
  picks (seats, slots, sizes): <div class="m42-pick-grid" id="seats" data-max="6" style="--m42-cols:5">
  <button class="m42-pick" data-value="A1">A1</button> <button class="m42-pick taken">A2</button>
  <span class="m42-pick gap"></span>..</div>; it selects itself and fires "m42:change" with detail.selected
  (M42UI.picked('seats') gives the values)
  summary (booking, cart, order): <aside class="m42-summary"><div class="m42-row"><span>Seats</span><b id="..">
  </b></div>..<div class="m42-total"><span>Total</span><span id="total">₹0</span></div></aside>
  tabs: Bootstrap nav-pills; cards: <div class="m42-feature"> (icon chip, h3, p); prices: <div class="m42-price">;
  reviews: <div class="m42-quote">; steps: <ol class="m42-steps">; images: <div class="m42-gallery">; numbers:
  <span data-m42-count="1200" data-suffix="+">0</span>; a closing band: <div class="m42-cta">; tables:
  <table class="m42-table">; labels: <span class="m42-badge">; FAQ: Bootstrap accordion; <footer class="m42-footer">.
- Forms: <form class="m42-form"> with Bootstrap form-label / form-control and `required`: M42 UI validates it and
  shows the sent message itself (data-m42-done="Booked! Your ticket is on its way"); no submit handler of your own
  unless it really sends data (then data-m42-own on the form).
- Motion is automatic (scroll reveal, count-up, ripple, navbar on scroll, progress bar, back-to-top): don't add
  your own for the same things. Real, specific text for every part (no lorem ipsum)."""

ICON_HINTS = [  # words in an item -> a Bootstrap Icons name that exists (for the examples only)
    (r"temp", "bi-thermometer-half"), (r"humid|moist", "bi-droplet"), (r"rain|precip", "bi-cloud-rain"),
    (r"wind", "bi-wind"), (r"pressure|barometer", "bi-speedometer2"), (r"visib", "bi-eye"), (r"clear sky|sunny", "bi-sun"), (r"snow", "bi-snow"), (r"storm|thunder", "bi-cloud-lightning-rain"), (r"user|member|customer|client|people", "bi-people"), (r"order|cart|sale", "bi-bag-check"),
    (r"revenue|income|profit|price|amount|payment", "bi-currency-rupee"), (r"session|visit|traffic|view", "bi-activity"),
    (r"server|cpu|load|memory|disk", "bi-cpu"), (r"stock|inventory|product", "bi-box-seam"), (r"time|uptime", "bi-clock"),
    (r"battery|power|volt|energy", "bi-lightning-charge"), (r"light|lux", "bi-brightness-high"), (r"speed|rpm", "bi-speedometer2"),
    (r"message|mail|ticket", "bi-envelope"), (r"error|alert|warn", "bi-exclamation-triangle"), (r"rating|star|review", "bi-star"),
    (r"plant|leaf|leaves|flower|garden|crop|farm|agri", "bi-flower1"), (r"tree|forest|eco|green", "bi-tree"),
    (r"water|tank|level|liquid|drop", "bi-droplet-half"), (r"soil|ground|earth", "bi-globe-asia-australia"),
    (r"sun|weather|day", "bi-sun"), (r"cloud", "bi-cloud"), (r"bell|notif", "bi-bell"), (r"wifi|network|signal", "bi-wifi"),
    (r"home|house", "bi-house"), (r"setting|config|gear", "bi-gear"), (r"profile|account|person|admin", "bi-person"),
    (r"calendar|date|event|schedule", "bi-calendar"), (r"location|map|place|address", "bi-geo-alt"),
    (r"phone|call|contact", "bi-telephone"), (r"heart|love|like|health", "bi-heart"), (r"security|shield|safe", "bi-shield-check"),
    (r"delivery|truck|ship", "bi-truck"), (r"book|course|study|school|education", "bi-book"), (r"doctor|hospital|clinic", "bi-hospital"),
    (r"camera|photo|image|gallery", "bi-camera"), (r"music|song|audio", "bi-music-note"), (r"game|play", "bi-controller"),
    (r"\bcars?\b|vehicle|taxi", "bi-car-front"), (r"carrot|vegetable|veggie|onion|tomato|garlic|ginger|chil+i|pepper|ingredient|spice|cucumber|potato|bean|lentil|dal|grain|corn|rice|wheat|flour|mushroom|cabbage|spinach|beet|radish|\bpeas?\b|fruit|mango|banana|peach|berr|grape|orange|lemon|lime|coconut", "bi-basket"), (r"pizza|\bpie\b", "bi-pie-chart-fill"), (r"burger|sandwich|snack|food|meal|dish|restaurant", "bi-egg-fried"), (r"bowl|soup|noodle|rice|curry|salad|ramen|mug|drink|juice", "bi-cup-hot"), (r"bottle|oil|sauce", "bi-droplet"), (r"utensil|cutlery|fork|spoon|kitchen|cook|chef|grill", "bi-fire"), (r"cookie|biscuit", "bi-cookie"), (r"knife", "bi-scissors"), (r"coffee|tea|cafe", "bi-cup-hot"),
    (r"tool|repair|service", "bi-tools"), (r"idea|light|bulb|lamp", "bi-lightbulb"), (r"chat|comment", "bi-chat-dots"),
    (r"search|find", "bi-search"), (r"chart|graph|trend|analytic|report", "bi-graph-up")]


def _icon_for(name):
    return next((icon for rx, icon in ICON_HINTS if re.search(rx, name, re.I)), "bi-graph-up")


ICON_USE_RX = re.compile(r"""(?<![\w-])(bi-[a-z0-9-]+)(?![\w-])""")


def fix_icons(html):
    """Icon names Bootstrap Icons doesn't have, replaced by M42 (no model round): by what the name means
    ("bi-plant" -> bi-flower1; a spelling match gave "did you mean bi-play?"), else a near spelling, else a dot.
    Returns (html, {wrong: right})."""
    icons = _bundled_classes("bootstrap-icons.min.css")
    if not icons:
        return html, {}
    out = {}
    for name in dict.fromkeys(ICON_USE_RX.findall(html or "")):
        if name in icons or name in ("bi-x",):
            continue
        words = name[3:].replace("-", " ")
        right = next((icon for rx, icon in ICON_HINTS if re.search(rx, words, re.I) and icon in icons), None)
        if not right:
            close = difflib.get_close_matches(name, [i for i in icons if i.startswith("bi-")], n=1, cutoff=0.86)
            # by the words of the name in the icon sets (icons.py: "bi-bread" -> a Lucide croissant), not a black dot
            right = close[0] if close else (_icons.best(words) or "bi-stars")
        out[name] = right
    for wrong, right in out.items():
        html = re.sub(r"(?<![\w-])" + re.escape(wrong) + r"(?![\w-])", right, html)
    return html, out


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "item"


def dash_note(spec=None):
    """How to build the dashboard's parts, with THIS page's items as the examples (a fixed weather example was
    copied into an admin panel: "Humidity" gauge, "Temperature,Humidity" chart, 2026-10-26)."""
    items = [i for i in ((spec or {}).get("items") or []) if i.get("source") in ("reading", "computed")][:6]
    names = [i["name"] for i in items] or ["Metric A", "Metric B", "Metric C"]
    stats = "\n".join(f'  <div class="m42-stat" id="{_slug(n)}" data-label="{n}" data-unit="" data-icon="{_icon_for(n)}"></div>'
                      for n in names[:4])
    first, second = _slug(names[0]), _slug(names[min(1, len(names) - 1)])
    return f"""M42 UI for a dashboard (the parts below use THIS page's items; units, thresholds and icons are yours to set):
- Header: <div class="m42-head"><div><h1>Title</h1><p>subtitle</p></div><div class="m42-head-side">
  <span class="m42-clock"></span><span class="m42-status" id="conn"></span><span class="m42-updated"></span></div></div>, then <div class="m42-grid"> with the parts:
{stats}
  (empty: M42 UI builds each card: icon, count-up value, delta, sparkline; data-warn / data-bad colour it)
- A percentage that fills up: <div class="m42-gauge" id="..." data-label="..." data-unit="%" data-max="100" data-icon="bi-..."></div>
- History: <div class="m42-chart m42-span-2" id="trend" data-label="..." data-series="{names[0]},{names[min(1, len(names) - 1)]}"></div>
- A computed result (a prediction, an alert, a summary): <div class="m42-banner m42-span-2" id="..."></div>
- Lists of records: <table class="m42-table"> in a <div class="m42-card">.
- In JS feed every part: M42UI.set('{first}', value); M42UI.gauge(id, value); M42UI.push('trend', [a, b]);
  M42UI.banner(id, {{title, text, icon: 'bi-...', tone: 'good' | 'warn' | 'bad'}}); M42UI.status('conn', 'online');
  M42UI.touch(); sample / demo values: M42UI.demo('{second}', base, spread) sets that card itself and returns the value.
- Icons are Bootstrap Icons names (bi-people, bi-cpu, bi-bag-check...): real names only."""


DASH_NOTE = dash_note()  # (the generic one, for code that has no spec)

FILE_NOTE = """Web kit (M42 loads these files itself: never add <script> or <link> tags or CDN links for them):
- Bootstrap 5.3: build layout and components with its classes (container, row, col-md-6, navbar navbar-expand-lg,
  card, btn btn-primary, form-control, d-flex, gap-3, py-5, shadow-sm, rounded-3). Bootstrap 5 names only: ms-/me-
  (not ml-/mr-), data-bs-toggle / data-bs-target (not data-toggle), text-start, fw-bold, visually-hidden.
- The theme colour is set already: btn-primary, bg-primary, text-primary, link colours use it. style.css is
  only for what Bootstrap has no class for (a hero background, a custom section); keep it short, no colour
  hex codes for brand elements, and every class you invent must be defined there.
- Bootstrap Icons: <i class="bi bi-envelope"></i> (real icon names only).
- jQuery 3.7: $(...) for DOM and events.
- SweetAlert2: Swal.fire({title, text, icon: 'success' | 'error' | 'warning' | 'info' | 'question',
  showCancelButton: true}).then(r => { if (r.isConfirmed) ... }) for confirmations and important messages.
- Toastr: toastr.success('Saved'), toastr.error('...'), toastr.info('...') for short notices after an action.
- anime.js 3: anime({targets: '.card', translateY: [20, 0], opacity: [0, 1], delay: anime.stagger(100),
  easing: 'easeOutQuad'}); subtle, and the content must stay visible if it never runs.
- Every page: <meta name="viewport" content="width=device-width, initial-scale=1">, a navbar that collapses on
  phones, exactly one h1, alt text on images, a <label> for every input."""

GAME_RX = re.compile(r"\b(game|games|mario|platformer|runner|shooter|arcade|snake|tetris|pong|flappy|"
                     r"canvas|three\.?js|phaser|pixi|babylon|p5\.?js|kaboom|webgl)\b", re.I)
# the user chose another stack (or none): their words win
OWN_STACK_RX = re.compile(r"\b(tailwind|bulma|materiali[sz]e|foundation|semantic[- ]ui|uikit|react|vue|angular|"
                          r"svelte|next\.?js|nuxt|vanilla|pure\s+(?:css|js|javascript|html))\b|"
                          r"\b(?:no|without|illama|illamal|vendam|venam)\s+(?:any\s+)?(?:bootstrap|librar\w*|framework)|"
                          r"\b(?:bootstrap|librar\w*|framework)\s+(?:venam|vendam|illama|illamal|use\s+pannatha)", re.I)


def wants_kit(request):
    """A website or web app (not a canvas game), and the user didn't name another stack."""
    return not GAME_RX.search(request or "") and not OWN_STACK_RX.search(request or "")


def drop_kit_libraries(libs):
    """The planner listed bootstrap.min.css / jquery.js itself: the kit has them already."""
    bases = {re.split(r"[.\-]", f)[0] for f in KIT_FILES} | {"bootstrap", "jquery", "sweetalert", "sweetalert2",
                                                            "toastr", "anime", "animejs"}
    return [l for l in libs if re.split(r"[.\-@]", Path(l).name.lower())[0] not in bases]


# ---- the theme -------------------------------------------------------------------------------------------

COLOUR_WORDS = [  # (words, hue) English and Tanglish
    (r"blue|neela\w*|neelam", 218), (r"navy", 225), (r"indigo", 240), (r"purple|violet|oodha\w*|ootha\w*", 265),
    (r"pink|rose", 335), (r"red|sivapp?u\w*|maroon", 355), (r"orange|aarenj\w*", 24), (r"yellow|manjal|gold\w*", 45),
    (r"green|pachai|pacha|emerald", 150), (r"teal|cyan|aqua", 182),
    # "coffee" only as a colour ("coffee colour", "coffee brown"): a coffee SHOP was taken as "you asked for coffee" and
    # the reference's own browns were dropped for made-up olive / purple (2026-11-03)
    (r"brown|coffee[- ]?(?:colou?r|brown|tone|shade)", 25),
]
KIND_WORDS = [  # the kind of site, when no colour is named: a usual colour for it
    (r"restaurant|food|cafe|coffee|bakery|hotel|biryani|kitchen|catering", 18),
    (r"hospital|clinic|medical|doctor|health|pharma|dental", 182),
    (r"bank|finance|insurance|loan|account|invest", 222),
    (r"farm|agri\w*|organic|nature|garden|eco|plant", 145),
    (r"school|college|education|course|academy|learn\w*|tuition", 214),
    (r"salon|beauty|fashion|boutique|wedding|bridal|jewel\w*", 330),
    (r"tech|software|startup|saas|ai\b|app\b|cloud|digital|agency", 248),
    (r"travel|tour\w*|holiday|resort", 196),
    (r"weather|climate|rain\w*|forecast", 205),
    (r"iot|sensor\w*|monitor\w*|dashboard|smart home", 212),
    (r"gym|fitness|sport\w*", 8),
]
HUES = [218, 248, 265, 182, 150, 12, 335, 200]


def _hex(rgb):
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgb)


def luminance(rgb):
    def lin(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def pick_hue(request, title=""):
    """(hue, why): a colour the user named, else the usual colour for the kind of site, else a steady pick."""
    text = f"{request} {title}".lower()
    for words, hue in COLOUR_WORDS:
        m = re.search(r"\b(" + words + r")\b", text)
        if m:
            return hue, f"you asked for {m.group(1)}"
    for words, hue in KIND_WORDS:
        m = re.search(r"\b(" + words + r")", text)
        if m:
            return hue, f"a usual colour for a {m.group(1)} site"
    seed = int(hashlib.md5((title or request or "site").lower().encode()).hexdigest(), 16)
    return HUES[seed % len(HUES)], "picked for this site"


WHITE, INK = (1.0, 1.0, 1.0), (0x21 / 255, 0x25 / 255, 0x29 / 255)


def palette(hue, sat=0.68):
    """The primary colour and the text on it, with WCAG contrast >= 4.5 computed, not guessed: white text on a
    colour dark enough for it; for light hues (yellow) where that would turn brown, dark text instead."""
    h = (hue % 360) / 360
    for light in [x / 100 for x in range(52, 24, -1)]:
        rgb = colorsys.hls_to_rgb(h, light, sat)
        if contrast(rgb, WHITE) >= 4.6:
            break
    # yellow and gold turn brown dark enough for white text (and any hue near black does): keep the colour
    # bright and put dark text on it
    if light < 0.30 or 35 <= hue % 360 <= 75:
        for light in [x / 100 for x in range(50, 70)]:
            rgb = colorsys.hls_to_rgb(h, light, sat)
            if contrast(rgb, INK) >= 4.8:
                break
        on = INK
    else:
        on = WHITE
    hover = colorsys.hls_to_rgb(h, max(0.0, light - 0.07), sat)
    soft = colorsys.hls_to_rgb(h, 0.95, min(sat, 0.6))
    border = colorsys.hls_to_rgb(h, 0.85, min(sat, 0.6))
    emphasis = colorsys.hls_to_rgb(h, 0.25, sat)
    return {"primary": rgb, "on": on, "hover": hover, "soft": soft, "border": border, "emphasis": emphasis,
            "contrast": round(contrast(rgb, on), 2), "hue": hue}


def theme_css(pal):
    rgb = lambda c: ", ".join(str(round(v * 255)) for v in c)  # noqa: E731
    p, on, hv = _hex(pal["primary"]), _hex(pal["on"]), _hex(pal["hover"])
    return f"""/* M42 theme: computed for this site (primary {p}, text on it {on}, contrast {pal['contrast']}:1).
   Written by M42 each build: change the colour by asking M42, or override it in style.css. */
:root {{
  --bs-primary: {p}; --bs-primary-rgb: {rgb(pal['primary'])};
  --bs-primary-text-emphasis: {_hex(pal['emphasis'])}; --bs-primary-bg-subtle: {_hex(pal['soft'])};
  --bs-primary-border-subtle: {_hex(pal['border'])};
  --bs-link-color: {p}; --bs-link-color-rgb: {rgb(pal['primary'])};
  --bs-link-hover-color: {hv}; --bs-link-hover-color-rgb: {rgb(pal['hover'])};
  --bs-border-radius: .6rem; --bs-border-radius-lg: .9rem; --bs-border-radius-sm: .4rem;
  --bs-focus-ring-color: rgba({rgb(pal['primary'])}, .25);
}}
.btn-primary {{
  --bs-btn-color: {on}; --bs-btn-bg: {p}; --bs-btn-border-color: {p};
  --bs-btn-hover-color: {on}; --bs-btn-hover-bg: {hv}; --bs-btn-hover-border-color: {hv};
  --bs-btn-active-color: {on}; --bs-btn-active-bg: {hv}; --bs-btn-active-border-color: {hv};
  --bs-btn-disabled-color: {on}; --bs-btn-disabled-bg: {p}; --bs-btn-disabled-border-color: {p};
  --bs-btn-focus-shadow-rgb: {rgb(pal['primary'])};
}}
.btn-outline-primary {{
  --bs-btn-color: {p}; --bs-btn-border-color: {p};
  --bs-btn-hover-color: {on}; --bs-btn-hover-bg: {p}; --bs-btn-hover-border-color: {p};
  --bs-btn-active-color: {on}; --bs-btn-active-bg: {hv}; --bs-btn-active-border-color: {hv};
  --bs-btn-focus-shadow-rgb: {rgb(pal['primary'])};
}}
.text-bg-primary, .badge.bg-primary {{ color: {on} !important; }}
.form-control:focus, .form-select:focus {{ border-color: {_hex(pal['border'])}; box-shadow: 0 0 0 .25rem rgba({rgb(pal['primary'])}, .25); }}
.form-check-input:checked {{ background-color: {p}; border-color: {p}; }}
.nav-pills {{ --bs-nav-pills-link-active-bg: {p}; --bs-nav-pills-link-active-color: {on}; }}
.pagination {{ --bs-pagination-active-bg: {p}; --bs-pagination-active-border-color: {p}; --bs-pagination-color: {p}; }}
.dropdown-menu {{ --bs-dropdown-link-active-bg: {p}; --bs-dropdown-link-active-color: {on}; }}
.progress, .progress-stacked {{ --bs-progress-bar-bg: {p}; }}
.list-group {{ --bs-list-group-active-bg: {p}; --bs-list-group-active-border-color: {p}; --bs-list-group-active-color: {on}; }}
h1, h2, h3, .display-1, .display-2, .display-3, .display-4, .display-5, .display-6 {{ font-weight: 700; letter-spacing: -.01em; }}
.card {{ --bs-card-border-color: rgba(0, 0, 0, .07); }}
section[id] {{ scroll-margin-top: 4.5rem; }}
html {{ scroll-behavior: smooth; }}
"""


STYLES = ("glass", "minimal", "bold", "elegant", "playful")
FONTS = {  # (headings, body): the bundled web fonts (Google Fonts, OFL: lib/fonts, offline), then system fonts
    "modern": ('"Poppins", "Segoe UI Variable Display", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif',
               '"Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif'),
    "elegant": ('"Playfair Display", Constantia, "Palatino Linotype", Georgia, "Times New Roman", serif',
                '"Lato", "Segoe UI", Candara, system-ui, -apple-system, sans-serif'),
    "tech": ('"Space Grotesk", Bahnschrift, "DIN Alternate", "Segoe UI", system-ui, sans-serif',
             '"Inter", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif'),
    "friendly": ('"Nunito", "Trebuchet MS", Candara, "Segoe UI", system-ui, sans-serif',
                 '"Nunito", Candara, "Segoe UI", system-ui, -apple-system, sans-serif'),
}
DARK_WORDS_RX = re.compile(r"\b(dark|night|black|neon|cyber|gaming|hacker|admin|dashboard|monitor\w*|crypto|"
                           r"glass\w*|futuristic|sexy)\b", re.I)


def _rgb(hexs):
    h = hexs.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _readable(rgb, hue):
    """The colour, nudged until white (or, for yellow-ish hues, dark) text on it reads at 4.5:1 or more."""
    h, light, sat = colorsys.rgb_to_hls(*rgb)
    for _ in range(40):
        c = colorsys.hls_to_rgb(h, light, sat)
        if contrast(c, WHITE) >= 4.6 and not (35 <= hue % 360 <= 75 and light < .45):
            return c, WHITE
        if 35 <= hue % 360 <= 75 and contrast(c, INK) >= 4.8:
            return c, INK
        light = light - .02 if not 35 <= hue % 360 <= 75 else min(.75, light + .02)
    return palette(hue)["primary"], palette(hue)["on"]


# the page's whole design, not only its colours (the user, 2026-11-11: a headphone shop came out as the bakery's page):
# "product" (Apple-like product page), "editorial" (a law firm, a consultancy, luxury, fashion), "warm" (a local
# business), "saas", "bold", "portfolio" (the last three use the general templates for now)
ARCHETYPES = ("warm", "product", "editorial", "saas", "bold", "portfolio")
LOOK_EXTRA = {"corners": ("sharp", "rounded", "pill"), "density": ("airy", "balanced", "dense"),
              "cards": ("glass", "shadow", "outlined", "flat")}


def make_look(request, title="", look=None):
    """The page's whole look: its 3 colours (from the spec's look: the content and what such sites use; else the
    usual colour for its kind), light / dark, style and fonts. Every site no longer came out the same blue glass.
    {"primary", "on", "accent2", "accent3", "theme", "style", "font", "why", "contrast", "hue"}."""
    look = _themes.apply(look or {})  # 🎨 the 4B's theme (themes.py): its whole design over the look, its colours kept
    hue, why = pick_hue(request, title)
    if "named_colours" in INTENT:  # the colours the user named, as the model read them (any language, any shade)
        named = None
        colors = list(INTENT["named_colours"]) + [c for c in look.get("colors") or [] if c not in INTENT["named_colours"]]
    else:
        named = re.search(r"\b(" + "|".join(w for w, _ in COLOUR_WORDS) + r")\b", (request or "").lower())
        colors = [] if named else list(look.get("colors") or [])  # a colour the user named wins over the model's
    if colors:
        r, g, b = _rgb(colors[0])
        hue = round(colorsys.rgb_to_hls(r, g, b)[0] * 360)
        why = look.get("why") or "picked for this site's content"
        primary, on = _readable((r, g, b), hue)
        if ("named_colours" in INTENT or look.get("why") == "changed by the user") and contrast((r, g, b), INK) >= 4.5 \
                and contrast((r, g, b), WHITE) < 4.6:
            # a light colour the USER named stays that colour, with dark text on it (light blue #60a5fa was made a dark
            # #076eed for white text: "light blue" asked, a dark blue seen, 2026-11-17)
            primary, on = (r, g, b), INK
        if look.get("exact"):  # a reference's own colour stays as it is (#44bddd became #1b7c96 for white text on it):
            c = (r, g, b)  # the text on it is dark or white, whichever reads; text in the colour uses its ink shade
            if max(contrast(c, INK), contrast(c, WHITE)) >= 4.5:
                primary, on = c, (INK if contrast(c, INK) >= contrast(c, WHITE) else WHITE)
    else:
        pal = palette(hue)
        primary, on = pal["primary"], pal["on"]

    def second(i, shift):
        if len(colors) > i:
            c = _rgb(colors[i])
            ch = colorsys.rgb_to_hls(*c)[0] * 360
            _, cl, cs = colorsys.rgb_to_hls(*c)
            # a real second colour: not the first one again, and not a grey / near-white (#ecf0f1 was given as the
            # secondary of a bus booking page: invisible in its gradients and charts)
            if min(abs(ch - hue), 360 - abs(ch - hue)) >= 18 and cs >= .3 and .25 <= cl <= (.92 if look.get("exact") else .75):
                return c  # (a reference's pastel chart colours, its lavender and yellow, are real colours of it)
            # the field's palette gave a shade of the first colour (a hotel's dark and light blue, a bakery's browns,
            # 2026-11-11): a shade of that colour, not a new hue (+38 made hotels, law firms, SaaS and music pages all
            # the same purple #8049df, and a bakery yellow-green and pink)
            pl = colorsys.rgb_to_hls(*primary)[1]
            src = (ch, cl, cs) if cs >= .3 else next(
                ((h * 360, l, sat) for h, l, sat in (colorsys.rgb_to_hls(*_rgb(x)) for x in colors)
                 if sat >= .3 and min(abs(h * 360 - hue), 360 - abs(h * 360 - hue)) >= 18), None)
            shade = src is None or cs >= .3  # (a grey's stand-in from the palette's other colour keeps its lightness)
            if src is None:  # greys only (a portfolio's #18181b / #3f3f46): a shade of the first colour
                src = (hue, pl, .45)
            if src:
                sh, sl, ss = src
                step = .18 if shift < 180 else .32
                if shade and abs(sl - pl) < .1:  # too close to the first one to tell apart: lighter / darker
                    sl = pl + step if pl < .5 else pl - step
                return colorsys.hls_to_rgb((sh % 360) / 360, min(.72, max(.3, sl)), min(.85, max(.45, ss)))
        if look.get("exact") and colors:
            # a reference of one colour family (a coffee shop's browns): its other colours are shades of it, not new
            # hues (+38 / +300 gave the coffee menu olive and purple cards, 2026-11-03)
            return colorsys.hls_to_rgb(((hue + (14 if shift < 180 else -10)) % 360) / 360, .5 if shift < 180 else .66, .55)
        return colorsys.hls_to_rgb(((hue + shift) % 360) / 360, .58, .7)
    a2, a3 = second(1, 38), second(2, 300)
    theme = (INTENT.get("named_theme") or look.get("theme")
             or ("dark" if "named_theme" not in INTENT and DARK_WORDS_RX.search(request or "") else "light"))
    if "named_theme" not in INTENT and re.search(r"\b(light|white|bright)\s*(theme|mode|background|bg)?\b", request or "", re.I) \
            and not re.search(r"\bdark\b", request or "", re.I):
        theme = "light"  # (the words, only when the model was not asked)
    style = INTENT.get("named_style") or look.get("style") or "glass"
    if "named_style" not in INTENT:
        for word, st in (("glass", "glass"), ("minimal", "minimal"), ("bold", "bold"), ("luxury", "elegant"),
                         ("elegant", "elegant"), ("kids", "playful"), ("playful", "playful")):  # the user's own word wins
            if re.search(r"\b" + word + r"\w*", request or "", re.I):
                style = st
                break
    font = look.get("font") or {"elegant": "elegant", "playful": "friendly", "bold": "modern"}.get(style, "modern")
    arch = look.get("archetype") if look.get("archetype") in ARCHETYPES else ""
    look = dict(look)
    if look.get("design") in _themes.ALL:  # a theme sets style, font, corners... itself (noir is dark editorial)
        font = look.get("font") or font
    elif arch == "product":  # a product page: dark, quiet, big spaces, no card shadows (unless the user said light)
        if user_theme(request, "light") != "light":
            theme = "dark"
        style, font = ("minimal" if style == "glass" else style), (look.get("font") if look.get("font") in ("modern", "tech") else "modern")
        look.update(density="airy", cards="flat", corners=look.get("corners") if look.get("corners") in ("rounded", "pill") else "rounded")
    elif arch == "editorial":  # serif, light paper, sharp lines, outlined blocks
        if user_theme(request, "dark") != "dark":
            theme = "light"
        style, font = "elegant", "elegant"
        look.update(density="airy", cards="outlined", corners="sharp")
    elif arch == "saas":  # crisp: outlined cards, a tech or modern font, the 4B's theme
        style = "minimal" if style in ("glass", "playful", "elegant") else style
        font = look.get("font") if look.get("font") in ("modern", "tech") else "tech"
        look.update(density="balanced", cards="outlined", corners="rounded")
    elif arch == "bold":  # loud: big type, pill buttons, flat colour
        style, font = "bold", "modern"
        look.update(density="balanced", cards="flat", corners="pill")
    elif arch == "portfolio":  # quiet: the work speaks, sharp and airy, no shadows
        style = "minimal"
        font = look.get("font") if look.get("font") in ("modern", "elegant") else "modern"
        look.update(density="airy", cards="flat", corners="sharp")
    return {"primary": _hex(primary), "on": _hex(on), "accent2": _hex(a2), "accent3": _hex(a3), "theme": theme,
            "style": style, "font": font, "why": why, "contrast": round(contrast(primary, on), 2), "hue": hue,
            # from a reference design (designref.py): how round, how dense, what kind of cards
            **{k: look[k] for k in ("corners", "density", "cards") if look.get(k) in LOOK_EXTRA[k]},
            **({"archetype": arch} if arch else {}), **({"bg": page_bg(look.get("bg"), theme)} if page_bg(look.get("bg"), theme) else {}),
            **({"design": look["design"], **_themes.axes(look["design"])} if look.get("design") in _themes.ALL else {})}


def page_bg(hexc, theme):
    """The page's own background colour (a reference's cream, the user's "background light cream ah maathu") when it
    fits the theme: a light one on a light page, a dark one on a dark page; else "" (the theme's own)."""
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(hexc or "")):
        return ""
    light = colorsys.rgb_to_hls(*_rgb(hexc))[1]
    return hexc.lower() if (light >= .86 if theme != "dark" else light <= .16) else ""


PAGE_BG = {"light": (0xf3 / 255, 0xf6 / 255, 0xfb / 255), "dark": (0x07 / 255, 0x0b / 255, 0x16 / 255)}


def ink(hexc, theme):
    """The colour as TEXT on the page's background: darkened (light theme) or lightened (dark) until it reads at
    4.5:1. A yellow brand (#fade73, from a reference) wrote "Master new recipes" in yellow on near-white."""
    bg = PAGE_BG.get(theme, PAGE_BG["light"])
    h, light, sat = colorsys.rgb_to_hls(*_rgb(hexc))
    for _ in range(50):
        c = colorsys.hls_to_rgb(h, light, sat)
        if contrast(c, bg) >= 5.2:  # a margin: cards and panels are a shade off the page background
            return _hex(c)
        light = max(0, light - .02) if theme != "dark" else min(1, light + .02)
    return _hex(colorsys.hls_to_rgb(h, light, sat))


def on_colour(hexc):
    """The text colour on a fill: dark on a pale one (a pastel from a reference), white on a strong one."""
    c = _rgb(hexc)
    return _hex(INK) if contrast(c, INK) >= contrast(c, WHITE) else "#ffffff"


def deep(hexc):
    """A dark shade of a colour that white text reads on (4.6:1): the bands with white words (a hero with no photo,
    the call-to-action band) were the brand colour itself, and a beige brand left the words unreadable."""
    h, light, sat = colorsys.rgb_to_hls(*_rgb(hexc))
    for _ in range(60):
        c = colorsys.hls_to_rgb(h, light, min(sat, .7))
        if contrast(c, WHITE) >= 4.6:
            return _hex(c)
        light -= .02
    return "#1f2937"


def look_css(lk):
    """The page's look as CSS variables for Bootstrap and M42 UI."""
    rgb = lambda h: ", ".join(str(round(v * 255)) for v in _rgb(h))  # noqa: E731
    head, body = FONTS.get(lk["font"], FONTS["modern"])
    # the deep shades from the strong colours: a pale brand colour (beige #f5f5dc) is a background, its shade olive
    strong = [c for c in (lk["primary"], lk["accent2"], lk["accent3"]) if colorsys.rgb_to_hls(*_rgb(c))[1] <= .8] or [lk["primary"]]
    d1, d2, d3 = deep(strong[0]), deep(strong[1 % len(strong)]), deep(strong[2 % len(strong)])
    return (f":root {{ --bs-primary: {lk['primary']}; --bs-primary-rgb: {rgb(lk['primary'])}; --bs-link-color: {lk['primary']}; "
            f"--bs-link-color-rgb: {rgb(lk['primary'])}; --m42-on-accent: {lk['on']}; "
            f"--m42-accent-2: {lk['accent2']}; --m42-accent-2-rgb: {rgb(lk['accent2'])}; "
            f"--m42-accent-3: {lk['accent3']}; --m42-accent-3-rgb: {rgb(lk['accent3'])}; "
            f"--m42-on-accent-2: {on_colour(lk['accent2'])}; --m42-on-accent-3: {on_colour(lk['accent3'])}; "
            f"--m42-font: {body}; --m42-font-head: {head}; "
            f"--m42-accent-ink: {ink(lk['primary'], lk['theme'])}; --m42-accent-2-ink: {ink(lk['accent2'], lk['theme'])}; "
            f"--m42-accent-3-ink: {ink(lk['accent3'], lk['theme'])}; "
            f"--m42-deep: {d1}; --m42-deep-2: {d2}; --m42-deep-3: {d3};"
            + (f" --m42-bg: {lk['bg']};" if lk.get("bg") else "") + " }\n"
            f".btn-primary {{ --bs-btn-bg: {lk['primary']}; --bs-btn-border-color: {lk['primary']}; --bs-btn-color: {lk['on']}; "
            f"--bs-btn-hover-bg: {lk['primary']}; --bs-btn-hover-color: {lk['on']}; --bs-btn-active-bg: {lk['primary']}; }}\n"
            f"body {{ font-family: var(--m42-font); }}")


def make_theme(request, title="", look=None):
    """{"hue", "why", "primary", "on", "contrast", "css", "look"} for this site (build: lib/m42-theme.css; chat:
    the same CSS put into the page by wire_chat_page)."""
    lk = make_look(request, title, look)
    pal = palette(lk["hue"])
    if lk["primary"] != _hex(pal["primary"]):  # the look's own colour: Bootstrap's buttons etc. follow it too
        pal = dict(pal, primary=_rgb(lk["primary"]), on=_rgb(lk["on"]), hover=colorsys.hls_to_rgb(
            *(lambda h, l, s: (h, max(0, l - .07), s))(*colorsys.rgb_to_hls(*_rgb(lk["primary"])))),
            contrast=lk["contrast"])
    if (look or {}).get("assets"):  # 💎 the chosen UI assets stay with the look through every rebuild of the theme
        lk["assets"] = list(look["assets"])
    return {"hue": lk["hue"], "why": lk["why"], "primary": lk["primary"], "on": lk["on"], "contrast": lk["contrast"],
            "css": theme_css(pal) + "\n" + look_css(lk), "look": lk}


THEME_TAG_RX = re.compile(r"<style\b[^>]*\bid\s*=\s*[\"']m42-theme[\"'][^>]*>.*?</style>\s*", re.S | re.I)


def wire_chat_page(html, theme):
    """M42 makes a chat page whole itself, whatever the model forgot: the kit tags for what the page uses (Bootstrap
    Icons for bi- classes, M42 UI for m42- classes, SweetAlert2 for Swal...; icons that never showed, 2026-10-26),
    the page's theme / look (colours, dark / light, style, fonts) and <body class="m42-ui">."""
    if not html or not WHOLE_PAGE_RX.search(html):
        return html
    probe = re.sub(r"<link\b[^>]*>|<script\b[^>]*\bsrc=[^>]*>\s*</script>", " ", html, flags=re.I)
    want = used_files({"index.html": probe})  # (data-icon="bi-people" counts: M42 UI draws it with the icon font)
    have = " ".join(re.findall(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", html, re.I)).lower()
    css_tags = [f'<link rel="stylesheet" href="{CDN[f]}">' for f in want if f.endswith(".css") and f.lower() not in have
                and Path(CDN[f]).name.lower() not in have]
    js_tags = [f'<script src="{CDN[f]}"></script>' for f in want if f.endswith(".js") and f.lower() not in have
               and Path(CDN[f]).name.lower() not in have]
    if css_tags:
        html = re.sub(r"</head>", lambda m: "\n".join(css_tags) + "\n" + m.group(0), html, count=1, flags=re.I) \
            if re.search(r"</head>", html, re.I) else "\n".join(css_tags) + "\n" + html
    if js_tags:  # before the page's own inline scripts, which use them
        first = re.search(r"<script\b(?![^>]*\ssrc=)[^>]*>", html, re.I)
        tags = "\n".join(js_tags) + "\n"
        html = html[:first.start()] + tags + html[first.start():] if first else \
            re.sub(r"</body>", lambda m: tags + m.group(0), html, count=1, flags=re.I)
    html = kit_scripts_first(html)
    html, _ = fix_icons(html)
    lk = (theme or {}).get("look")
    if lk:
        html = THEME_TAG_RX.sub("", html)
        style = f'<style id="m42-theme">\n{look_css(lk)}\n</style>\n'  # last in <head>: over the model's own colours
        html = re.sub(r"</head>", lambda m: style + m.group(0), html, count=1, flags=re.I) if re.search(
            r"</head>", html, re.I) else style + html
    hero = (lk or {}).get("hero")
    if hero and hero != "none":  # the hero the spec gave this kind of site (search card, big photo...)
        m = re.search(r"<(header|section|div)\b[^>]*class\s*=\s*[\"'][^\"']*\bm42-hero\b[^\"']*[\"']", html, re.I)
        # (an archetype's own hero, is-editorial: the spec's "image" added to it made a hotel's editorial hero a
        # purple image band with its numbers' labels unreadable, 2026-11-11)
        if m and not re.search(r"\bis-(search|split|centered|image|compact|product|editorial|saas|bold|portfolio|giant|block|bleed|poster|duo|showroom|diagonal)\b", m.group(0)):
            tag = re.sub(r"\bm42-hero\b", f"m42-hero is-{hero}", m.group(0), count=1)
            html = html[:m.start()] + tag + html[m.end():]
    return set_look(html, lk)


SRC_TAG_RX = re.compile(r"""[ \t]*<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>\s*</script>[ \t]*\n?""", re.I)


def kit_scripts_first(html):
    """Library scripts (the kit, or any src script) the page put AFTER its own inline script move up before it:
    the page's script ran first and stopped with "M42UI is not defined" (a real page, 2026-10-26), every card
    left on its loading shimmer."""
    first = re.search(r"<script\b(?![^>]*\ssrc=)[^>]*>\s*\S", html or "", re.I)
    if not first:
        return html
    late = [m for m in SRC_TAG_RX.finditer(html) if m.start() > first.start()]
    if not late:
        return html
    for m in reversed(late):
        html = html[:m.start()] + html[m.end():]
    tags = "".join(m.group(0).strip() + "\n" for m in late)
    first = re.search(r"<script\b(?![^>]*\ssrc=)[^>]*>\s*\S", html, re.I)
    line_start = html.rfind("\n", 0, first.start()) + 1
    return html[:line_start] + tags + html[line_start:]


def set_look(html, lk):
    """<html data-m42-theme=".." data-m42-style=".."> from the page's look, and <body class="m42-ui"> on a page that
    uses M42 UI (built sites get these in index.html; chat pages through wire_chat_page)."""
    if lk:
        attrs = f'data-m42-theme="{lk["theme"]}" data-m42-style="{lk["style"]}"' + "".join(
            f' data-m42-{k}="{lk[k]}"' for k in ("corners", "density", "cards", "design") + _themes.AXES + _themes.APP_AXES if lk.get(k))
        if lk.get("assets"):  # 💎 the premium treatments chosen for this theme (ui_assets.py)
            attrs += f' data-m42-a="{" ".join(str(x) for x in lk["assets"])}"'
        m = re.search(r"<html\b[^>]*>", html, re.I)
        if m:
            tag = re.sub(r"\sdata-m42-(?:theme|style|corners|density|cards|design|head|rhythm|pic|divider|display|side|frame|kpi|panel|table|banner|tabbar|a)\s*=\s*[\"'][^\"']*[\"']", "", m.group(0))
            html = html[:m.start()] + tag[:-1].rstrip() + " " + attrs + ">" + html[m.end():]
    if re.search(r"\bm42-", html):
        m = re.search(r"<body\b[^>]*>", html, re.I)
        if m and not re.search(r"\bm42-ui\b", m.group(0)):
            tag = m.group(0)
            tag = re.sub(r"class\s*=\s*([\"'])", lambda c: f"class={c.group(1)}m42-ui ", tag, count=1) if re.search(
                r"class\s*=", tag, re.I) else tag[:-1] + ' class="m42-ui">'
            html = html[:m.start()] + tag + html[m.end():]
    return html


# ---- which kit files the code uses ---------------------------------------------------------------------

def used_files(texts):
    """The kit files to load for the project's code, in load order (CSS, then JS)."""
    code = "\n".join(t for f, t in texts.items() if not f.startswith("lib/"))
    want = []
    for k in KIT:
        if re.search(k["use"], code):
            want += k["css"] + k["js"]
            if k.get("needs") and k["needs"] not in want:
                want.append(k["needs"])
    return [f for f in KIT_FILES if f in want]  # the kit's own order: jQuery before Toastr


MANIFEST = "lib/.m42-kit.json"  # the hash of every kit file M42 put in lib/: a newer kit replaces only those


def _sha(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def sync_files(root, wanted, theme_text):
    """Copy the kit files the code uses into lib/, bring older copies M42 put there up to the shipped version, and
    leave out the rest. A file someone changed (its hash isn't the one M42 wrote) is never replaced or removed: an
    updated m42-ui.js never reached a folder that had the first one (2026-10-25). Returns (added, removed) names."""
    lib = Path(root) / "lib"
    man_path = Path(root) / MANIFEST
    try:
        manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.is_file() else {}
    except (OSError, ValueError):
        manifest = {}
    fonts = [f for k in KIT for f in k.get("fonts", []) if set(k["css"]) & set(wanted)]
    added, removed = [], []
    for name in KIT_FILES + [f for k in KIT for f in k.get("fonts", [])]:
        target, source = lib / name, BUNDLED / name
        if not source.is_file():
            continue
        want = name in wanted or name in fonts
        ours = target.is_file() and (manifest.get(name) == _sha(target) or target.read_bytes() == source.read_bytes())
        if want and (not target.exists() or (ours and target.read_bytes() != source.read_bytes())):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest[name] = _sha(target)
            if name in KIT_FILES:
                added.append(name)
        elif not want and ours:
            target.unlink()
            manifest.pop(name, None)
            if name in KIT_FILES:
                removed.append(name)
    if manifest or man_path.exists():
        man_path.parent.mkdir(parents=True, exist_ok=True)
        man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    theme = Path(root) / THEME_FILE
    if theme_text and (not theme.exists() or theme.read_text(encoding="utf-8", errors="replace") != theme_text):
        theme.parent.mkdir(parents=True, exist_ok=True)
        theme.write_text(theme_text, encoding="utf-8")
    return added, removed


LINK_RX = re.compile(r"""[ \t]*<link\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>[ \t]*\n?""", re.I)


def wire_css(html, kit_css):
    """The kit's stylesheets (and the theme) before the project's own, in order; CDN copies of kit libraries and
    kit files the code no longer uses are dropped. A viewport meta tag is added when the page has none."""
    kit_bases = {re.split(r"[.\-]", f)[0] for f in KIT_FILES}

    def keep(m):
        href = m.group(1).strip()
        if not re.search(r"\.css(\?|#|$)", href, re.I) and "stylesheet" not in m.group(0).lower():
            return m.group(0)
        name = Path(href.split("?")[0]).name.lower()
        if href.startswith("lib/") and (name in KIT_FILES or href == THEME_FILE):
            return ""  # re-added below in order
        if re.match(r"^(https?:)?//", href, re.I) and re.split(r"[.\-@]", name)[0] in kit_bases | {"bootstrap"}:
            return ""  # a CDN Bootstrap next to the local one
        return m.group(0)

    html = LINK_RX.sub(keep, html)
    tags = "".join(f'    <link rel="stylesheet" href="{h}">\n' for h in [f"lib/{c}" for c in kit_css] + [THEME_FILE])
    first = re.search(r"""[ \t]*<link\b[^>]*rel\s*=\s*["']?stylesheet""", html, re.I)
    if first:
        html = html[:first.start()] + tags + html[first.start():]
    elif re.search(r"</head>", html, re.I):
        html = re.sub(r"</head>", tags + "</head>", html, count=1, flags=re.I)
    else:
        html = tags + html
    if not re.search(r"""<meta[^>]+name\s*=\s*["']viewport""", html, re.I):
        meta = '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        m = re.search(r"<head\b[^>]*>\n?", html, re.I)
        html = html[:m.end()] + meta + html[m.end():] if m else meta + html
    return html


def local_kit(html):
    """A line edit that linked a kit library from the web (anime.js 4 from a CDN, 2026-11-11): the tag points at the
    kit's own file in lib/ instead (the version the page's code is written for); a second tag for one file goes."""
    names = {(re.split(r"[.\-@]", Path(f).name.lower())[0], Path(f).suffix): f for f in KIT_FILES}

    def fix(m):
        src = m.group(2).strip()
        if not re.match(r"^(https?:)?//", src, re.I):
            return m.group(0)
        low = src.lower()
        base = re.split(r"[.\-@]", Path(low.split("?")[0]).name)[0]
        base = "anime" if "anime" in low else "sweetalert2" if "sweetalert" in low else base
        f = names.get((base, ".js" if m.group(1).lower() == "script" else ".css"))
        if not f:
            return m.group(0)
        return m.group(0).replace(m.group(2), "lib/" + f)
    html = re.sub(r"""<(script|link)\b[^>]*\b(?:src|href)\s*=\s*["']([^"']+)["'][^>]*>""", fix, html, flags=re.I)
    seen = set()

    def once(m):
        key = m.group(1).lower().lstrip("./")
        if key in seen:
            return ""
        seen.add(key)
        return m.group(0)
    return re.sub(r"""[ \t]*<script\b[^>]*\bsrc\s*=\s*["']((?:\./)?lib/[^"']+)["'][^>]*>\s*</script>[ \t]*\n?""", once,
                  html, flags=re.I)


def drop_cdn_scripts(html):
    """<script src="https://cdn.../bootstrap.bundle.min.js">: the kit's local copy is loaded instead."""
    bases = {re.split(r"[.\-]", f)[0] for f in KIT_FILES} | {"sweetalert2", "animejs"}

    def keep(m):
        src = m.group(1).strip()
        if re.match(r"^(https?:)?//", src, re.I):
            name = Path(src.split("?")[0]).name.lower()
            if re.split(r"[.\-@]", name)[0] in bases:
                return ""
        return m.group(0)
    return re.sub(r"""[ \t]*<script\b[^>]*\bsrc\s*=\s*["']([^"']*)["'][^>]*>\s*</script>[ \t]*\n?""", keep, html,
                  flags=re.I)


# ---- checks from the libraries' own files --------------------------------------------------------------

# a class in a selector, the second one of ".m42-pick.gap" too (not ".5rem": a class name can't start with a digit)
CLASS_RX = re.compile(r"(?<!-)\.(-?[A-Za-z_][\w-]*)")
CLASS_ATTR_RX = re.compile(r"""\bclass(?:Name)?\s*=\s*(?:"([^"]*)"|'([^']*)')""")
ICON_ATTR_RX = re.compile(r"""data-icon\s*=\s*["'](bi-[\w-]+)["']|\bicon\s*:\s*["'](bi-[\w-]+)["']""")
CLASS_CALL_RX = re.compile(r"""\b(?:classList\.(?:add|remove|toggle|replace)|addClass|toggleClass)\s*\(([^)]*)\)""")
STRING_RX = re.compile(r"""(["'`])((?:(?!\1)[^\\\n]|\\.)*)\1""")
TOKEN_RX = re.compile(r"-?[A-Za-z_][\w-]*$")
_CSS_CACHE = {}


def css_classes(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"url\([^)]*\)", " ", text)
    return set(CLASS_RX.findall(text))


def _bundled_classes(name):
    if name not in _CSS_CACHE:
        p = BUNDLED / name
        _CSS_CACHE[name] = css_classes(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else set()
    return _CSS_CACHE[name]


def used_classes(texts):
    """{class: first file that uses it}: class="..." in pages and in JS templates, classList / addClass calls."""
    out = {}
    for f, t in texts.items():
        if f.startswith("lib/") or not f.endswith((".html", ".htm", ".js")):
            continue
        if f.endswith(".js"):  # JS: only class="..." inside strings and class calls
            t = re.sub(r"/\*.*?\*/|(?<![:\"'`])//[^\n]*", " ", t, flags=re.S)
        else:
            t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
        groups = [a or b for a, b in CLASS_ATTR_RX.findall(t)]
        for args in CLASS_CALL_RX.findall(t):
            groups += [s for _, s in STRING_RX.findall(args)]
        # M42 UI's data-icon="bi-..." and icon: 'bi-...' in M42UI.banner become icon classes: checked the same way
        groups += [a or b for a, b in ICON_ATTR_RX.findall(t)]
        for g in groups:
            for c in g.split():
                if TOKEN_RX.match(c) and "${" not in c:
                    out.setdefault(c, f)
    return out


def _hooks(texts):
    """Classes the project's JS selects by (.reveal in querySelectorAll('.reveal'), $('.card')): markers, fine
    without any CSS."""
    js = "\n".join(t for f, t in texts.items() if not f.startswith("lib/") and f.endswith((".js", ".html", ".htm")))
    hooks = set()
    for _, s in STRING_RX.findall(js):
        hooks |= set(CLASS_RX.findall(s))
    hooks |= set(re.findall(r"""(?:getElementsByClassName|classList\.contains|hasClass)\s*\(\s*["']([\w-]+)""", js))
    return hooks


def bs4_hint(c):
    """The Bootstrap 5 name of a Bootstrap 4 class (renamed in 5.0), or of another library that is not loaded."""
    m = re.fullmatch(r"([mp])([lr])-((?:sm|md|lg|xl|xxl)-)?(\w+)", c)
    if m:
        return f"{m.group(1)}{'s' if m.group(2) == 'l' else 'e'}-{m.group(3) or ''}{m.group(4)}"
    m = re.fullmatch(r"(float|text|border|rounded)-((?:sm|md|lg|xl|xxl)-)?(left|right)", c)
    if m:
        return f"{m.group(1)}-{m.group(2) or ''}{'start' if m.group(3) == 'left' else 'end'}"
    m = re.fullmatch(r"badge-(primary|secondary|success|danger|warning|info|light|dark)", c)
    if m:
        return f"text-bg-{m.group(1)}"
    m = re.fullmatch(r"font-weight-(bold|bolder|normal|light|lighter)", c)
    if m:
        return f"fw-{m.group(1)}"
    if re.fullmatch(r"fa[srbl]?|fa-[\w-]+", c):
        return "Font Awesome is not loaded: Bootstrap Icons is, e.g. <i class=\"bi bi-star\"></i>"
    return {"font-italic": "fst-italic", "sr-only": "visually-hidden", "sr-only-focusable": "visually-hidden-focusable",
            "badge-pill": "rounded-pill", "btn-block": "w-100", "form-group": "mb-3", "form-row": "row g-3",
            "custom-select": "form-select", "custom-control": "form-check", "custom-checkbox": "form-check",
            "custom-control-input": "form-check-input", "custom-control-label": "form-check-label",
            "custom-switch": "form-check form-switch", "custom-range": "form-range", "custom-file": "form-control",
            "input-group-append": "put the button directly inside .input-group",
            "input-group-prepend": "put the text directly inside .input-group", "no-gutters": "g-0",
            "jumbotron": "p-5 mb-4 bg-body-tertiary rounded-3", "card-deck": "row row-cols-1 row-cols-md-3 g-4",
            "card-columns": "row row-cols-1 row-cols-md-3 g-4", "media": "d-flex", "media-body": "flex-grow-1 ms-3",
            "embed-responsive": "ratio ratio-16x9", "close": "btn-close", "dropdown-menu-right": "dropdown-menu-end",
            "dropdown-menu-left": "dropdown-menu-start", "thead-dark": "table-dark", "thead-light": "table-light",
            "text-muted-light": "text-body-secondary",
            "navbar-light": "put it away: in 5.3 a navbar is light by default (data-bs-theme=\"dark\" for a dark one)"
            }.get(c, "")


def class_problems(texts, lib_css, extra_css=()):
    """Classes the code uses that no loaded stylesheet defines and no script selects: a Bootstrap 4 name, an
    icon that doesn't exist, a class of a framework that isn't loaded, or an invented one with a framework
    prefix (btn-gradient). Plain custom names (hero-section) are left alone. {file: [problem]}."""
    kit = set()
    for name in lib_css:
        kit |= _bundled_classes(name)
    if any("data-m42-3d" in t for t in texts.values()):  # 🧊 m42-3d.js puts its own CSS in (.m42-3d, its card, labels)
        kit |= _kit_3d_classes()
    own = set()
    for t in extra_css:  # the stylesheets of libraries the user asked for (lib/swiper-bundle.min.css)
        own |= css_classes(t)
    for f, t in texts.items():
        if f.endswith(".css"):
            own |= css_classes(t)
        elif f.endswith((".html", ".htm")):
            own |= {c for block in re.findall(r"<style\b[^>]*>(.*?)</style>", t, re.S | re.I) for c in css_classes(block)}
    families = {}
    for c in kit:
        families[c.split("-")[0]] = families.get(c.split("-")[0], 0) + 1
    families = {k for k, n in families.items() if n >= 3}
    hooks = _hooks(texts)
    bad = {}
    for c, f in used_classes(texts).items():
        if c in kit or c in own or c in hooks:
            continue
        hint = bs4_hint(c)
        close = difflib.get_close_matches(c, [k for k in kit if k.split("-")[0] == c.split("-")[0]], n=1, cutoff=0.8)
        if hint or close or c.split("-")[0] in families:
            bad.setdefault(f, []).append(c + (f" (Bootstrap 5: {hint})" if hint and not hint.startswith(("Font", "put"))
                                              else f" ({hint})" if hint else f" (did you mean {close[0]}?)" if close
                                              else ""))
    out = {}
    for f, t in texts.items():  # the page's own CSS re-styling Bootstrap's grid (.container {width: 80%}): it
        # overflowed on a phone in a real run, the grid can't work under it
        css = t if f.endswith(".css") else "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", t, re.S | re.I)) \
            if f.endswith((".html", ".htm")) else ""
        hit = sorted({m.group(1) for m in GRID_RULE_RX.finditer(re.sub(r"/\*.*?\*/", " ", css, flags=re.S))
                      if m.group(1) in kit})
        if hit:
            out.setdefault(f, []).append(
                f"Fix in {f}: the page's CSS changes the layout of Bootstrap's own {', '.join('.' + h for h in hit)} "
                "(width / margin / display / flex), which breaks Bootstrap's grid on phones: remove those rules and "
                "lay it out with Bootstrap classes (container, row, col-12 col-md-6 col-lg-3, g-3)")
    for f, cs in bad.items():
        out.setdefault(f, []).append(
            f"Fix in {f}: these classes are in no loaded stylesheet (Bootstrap 5.3, Bootstrap Icons or the project's "
            f"CSS), so they do nothing: {', '.join(cs[:12])}. Use the real Bootstrap 5 class, or define the class "
            f"in style.css.")
    return out


GRID_RULE_RX = re.compile(r"(?:^|[}\s,])\.(container(?:-\w+)?|row|col(?:-\w+)*)\s*\{[^}]*\b(?:width|margin|display|flex"
                          r"|float|padding)\s*:", re.M)
BS4_DATA_RX = re.compile(r"\bdata-(toggle|target|dismiss|ride|slide|slide-to|parent|spy|offset|placement|"
                         r"backdrop|keyboard|interval)\s*=", re.I)
# not a file name: ".../toastr.min.js" in a script tag read as a call to toastr.min (a real run, 2026-10-25)
API_RX = re.compile(r"(?<![\w$./@-])(Swal|toastr|anime|bootstrap)\s*\.\s*([A-Za-z_$][\w$]*)(?![\w$]*\.(?:js|css)\b)")
_LIB_TEXT = {}


def _lib_text(name):
    if name not in _LIB_TEXT:
        p = BUNDLED / name
        _LIB_TEXT[name] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return _LIB_TEXT[name]


def api_problems(texts):
    """Library calls that don't exist in the version M42 ships, checked against the library file itself
    (Swal.alert, toastr.show, bootstrap.Modals), plus the APIs that changed: swal() of SweetAlert 1, `type:` in
    Swal.fire (now `icon:`), Bootstrap 4 data-toggle attributes, anime.js v4's animate(). {file: [problem]}."""
    out = {}
    for f, t in texts.items():
        if f.startswith("lib/") or not f.endswith((".html", ".htm", ".js")):
            continue
        probs = []
        for m in sorted(set(BS4_DATA_RX.findall(t)), key=str.lower)[:6]:
            probs.append(f"Fix in {f}: data-{m} is Bootstrap 4; Bootstrap 5 needs data-bs-{m.lower()}")
        if re.search(r"(?<![\w$.])swal\s*\(", t):
            probs.append(f"Fix in {f}: swal(...) is the old SweetAlert 1 API; SweetAlert2 is loaded: "
                         "Swal.fire({title, text, icon})")
        if re.search(r"Swal\.fire\(\s*\{[^}]*\btype\s*:", t, re.S):
            probs.append(f"Fix in {f}: Swal.fire({{type: ...}}) is old: SweetAlert2 11 uses icon: 'success' | 'error' | "
                         "'warning' | 'info' | 'question'")
        if re.search(r"""\bfrom\s+["']animejs["']|(?<![\w$.])anime\.animate\s*\(""", t):
            probs.append(f"Fix in {f}: that is the anime.js 4 API; anime.js 3.2 is loaded: anime({{targets, ...}})")
        seen = set()
        for g, name in API_RX.findall(t):
            lib = KIT_GLOBALS.get(g)
            if not lib or (g, name) in seen:
                continue
            seen.add((g, name))
            if not re.search(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])", _lib_text(lib)):
                probs.append(f"Fix in {f}: {g}.{name} does not exist in {lib} (the version M42 loads)")
        if probs:
            out[f] = probs
    return out


def kit_problems(texts, lib_css, extra_css=()):
    out = class_problems(texts, lib_css, extra_css)
    for f, ps in api_problems(texts).items():
        out.setdefault(f, []).extend(ps)
    return out


# ---- what the phone-width render measured ------------------------------------------------------------

def _file_for(desc, texts, prefer_css=False):
    """The file an element described as tag#id.class1.class2 belongs to: where its id or class is."""
    marks = re.findall(r"#([\w-]+)", desc) + re.findall(r"\.([\w-]+)", desc)
    order = sorted(texts, key=lambda f: (not f.endswith(".css") if prefer_css else not f.endswith((".html", ".htm")),
                                         f != "index.html"))
    for mark in marks:
        for f in order:
            if f.startswith("lib/"):
                continue
            if re.search(r"(?<![\w-])" + re.escape(mark) + r"(?![\w-])", texts[f]):
                return f
    return "index.html" if "index.html" in texts else next(iter(texts), "index.html")


def ux_problems(ux, texts):
    """{file: [problem]} from the UX part of a phone-width (390 px) browser report."""
    out = {}
    if not ux:
        return out

    def add(f, p):
        out.setdefault(f, []).append(f"Fix in {f}: {p}")
    if ux.get("scroll", 0) > 4:
        who = ux.get("wide") or []
        f = _file_for(who[0], texts, prefer_css=True) if who else "index.html"
        add(f, f"on a phone (390 px wide) the page is {ux['scroll']} px wider than the screen, so it scrolls sideways"
               + (f"; too wide: {', '.join(who[:3])}" if who else "") + ". Use Bootstrap columns (col-12 col-md-6), "
               "img-fluid, max-width: 100%, no fixed widths in px")
    for c in (ux.get("contrast") or [])[:4]:
        f = _file_for(c["el"], texts, prefer_css=True)
        add(f, f"text \"{c['text']}\" ({c['el']}) has contrast {c['ratio']}:1 on its background, it needs "
               f"{c['need']}:1 to be readable: darker text or a lighter background (or text-white on a dark one)")
    if ux.get("noalt"):
        add("index.html" if "index.html" in texts else _file_for(ux["noalt"][0], texts),
            f"{len(ux['noalt'])} image(s) have no alt text: {', '.join(ux['noalt'][:4])}")
    if ux.get("nolabel"):
        add(_file_for(ux["nolabel"][0], texts), f"input(s) without a label: {', '.join(ux['nolabel'][:4])}; give each "
            "a <label for=...> (or visually-hidden label, or aria-label)")
    if ux.get("dialog"):  # nobody clicked anything in this render: the page opened it itself
        add(_file_for("", texts), f"a SweetAlert2 dialog (\"{ux['dialog']}\") opens by itself while the page loads (in an "
                                  "update loop it opens again every time): a failed or missing reading is a small Toastr "
                                  "notice or a status text, with demo readings shown; Swal is for answers to the user's "
                                  "own actions")
    h1 = ux.get("h1")
    if h1 is not None and h1 != 1:
        add("index.html" if "index.html" in texts else next(iter(texts)),
            "the page has no h1 (the main heading, once)" if h1 == 0 else f"the page has {h1} h1 headings: keep one, "
            "make the others h2")
    return out


UX_JS = """function __m42ux(){try{var R={scroll:0,wide:[],contrast:[],noalt:[],nolabel:[],h1:0};
function d(e){var s=e.tagName.toLowerCase();if(e.id)s+='#'+e.id;var c=(typeof e.className==='string'?e.className:'').trim().split(/\\s+/).filter(Boolean).slice(0,3);if(c.length)s+='.'+c.join('.');return s;}
function vis(e){var r=e.getBoundingClientRect();if(!r.width||!r.height)return false;for(var x=e;x&&x.nodeType===1;x=x.parentElement){var s=getComputedStyle(x);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.9)return false;}return true;}
var W=window.innerWidth,de=document.documentElement;R.scroll=Math.max(0,de.scrollWidth-W);
if(R.scroll>4){[].slice.call(document.querySelectorAll('body *')).forEach(function(e){if(R.wide.length>=3)return;var r=e.getBoundingClientRect();
if(r.right>W+4&&r.width>0){var p=e.parentElement,pr=p&&p.getBoundingClientRect();if(!pr||pr.right<=W+4||p===document.body)R.wide.push(d(e)+' ('+Math.round(r.width)+' px)');}});}
function rgb(s){var m=/rgba?\\(([^)]+)\\)/.exec(s||'');if(!m)return null;var p=m[1].split(/[\\s,\\/]+/).filter(Boolean).map(parseFloat);return [p[0],p[1],p[2],p.length>3?p[3]:1];}
function lum(c){var a=[c[0],c[1],c[2]].map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];}
function mix(t,b){var a=t[3];return [t[0]*a+b[0]*(1-a),t[1]*a+b[1]*(1-a),t[2]*a+b[2]*(1-a),1];}
function bgs(e){var top=[],G=null,under=[];for(var x=e;x&&x.nodeType===1;x=x.parentElement){var s=getComputedStyle(x),im=s.backgroundImage,c=rgb(s.backgroundColor);
if(!G&&im&&im!=='none'){if(/url\\(/.test(im))return null;var g=(im.match(/rgba?\\([^)]+\\)/g)||[]).map(rgb).filter(function(c){return c&&c[3]>=0.9;});if(!g.length&&/gradient/.test(im))return null;if(g.length){G=g;if(c&&c[3]>0)under.push(c);if(c&&c[3]>=0.99)break;continue;}}
if(c&&c[3]>0){(G?under:top).push(c);if(c[3]>=0.99)break;}}
var base=[255,255,255,1];for(var i=under.length-1;i>=0;i--)base=mix(under[i],base);
var out=[];(G||[[0,0,0,0]]).forEach(function(g){var b=G?mix(g,base):base;for(var i=top.length-1;i>=0;i--)b=mix(top[i],b);out.push(b);});return out;}
function bg(e){var B=bgs(e);return B?B[0]:null;}
var seen={},n=0;[].slice.call(document.querySelectorAll('body *')).forEach(function(e){if(n>500||R.contrast.length>=6)return;
var t=[].filter.call(e.childNodes,function(c){return c.nodeType===3&&c.textContent.trim().length>1;}).map(function(c){return c.textContent.trim();}).join(' ');
if(!t||/^(SCRIPT|STYLE|NOSCRIPT|OPTION)$/.test(e.tagName)||!vis(e))return;n++;var s=getComputedStyle(e),B=bgs(e),f0=rgb(s.color);if(!B||!f0||/text/.test(s.webkitBackgroundClip||s.backgroundClip||''))return;
var r=99,wb=null;B.forEach(function(b){var f=mix(f0,b),l1=lum(f),l2=lum(b),q=(Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);if(q<r){r=q;wb=b;}});var px=parseFloat(s.fontSize),big=px>=24||(px>=18.6&&parseInt(s.fontWeight)>=700),need=big?3:4.5;
if(r<need-0.05){var k=d(e);if(!seen[k]){seen[k]=1;var P=[],x=e;for(var i=0;x&&x!==document.body&&i<5;i++,x=x.parentElement){if(x.id){P.unshift('#'+x.id);break;}var cl=(typeof x.className==='string'?x.className:'').trim().split(/\\s+/).filter(function(c){return /^m42-/.test(c);})[0];P.unshift(x.tagName.toLowerCase()+(cl?'.'+cl:''));}R.contrast.push({el:k,text:t.slice(0,40),ratio:Math.round(r*100)/100,need:need,fg:f0.slice(0,4),bg:wb?wb.slice(0,3):null,path:P.join(' ')});}}});
var LIB='.swal2-container,#toast-container';
[].slice.call(document.images).forEach(function(i){if(!i.hasAttribute('alt')&&!i.closest(LIB))R.noalt.push(d(i)+(i.getAttribute('src')?' '+i.getAttribute('src').split('/').pop().slice(0,40):''));});
[].slice.call(document.querySelectorAll('input,select,textarea')).forEach(function(i){var ty=(i.type||'').toLowerCase();if(/hidden|submit|button|reset|image/.test(ty))return;
var ok=i.closest(LIB)||i.getAttribute('aria-label')||i.getAttribute('aria-labelledby')||i.title||i.closest('label')||(i.id&&document.querySelector('label[for="'+i.id+'"]'));if(!ok)R.nolabel.push(d(i));});
var sw=document.querySelector('.swal2-popup');if(sw&&vis(sw)){var st=sw.querySelector('.swal2-title');R.dialog=((st&&st.textContent)||'').trim().slice(0,40)||'dialog';}
R.h1=document.querySelectorAll('h1').length;return R;}catch(x){return {error:String(x)};}}"""


# ---- a page given in the chat (no project folder): the same kit from the CDN, local copies for M42's check ----

CDN = {  # the exact versions in bundled/ (checked on jsdelivr, 2026-10-25)
    "bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "bootstrap-icons.min.css": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    "toastr.min.css": "https://cdn.jsdelivr.net/npm/toastr@2.1.4/build/toastr.min.css",
    "jquery.min.js": "https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js",
    "bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    "sweetalert2.all.min.js": "https://cdn.jsdelivr.net/npm/sweetalert2@11.14.5/dist/sweetalert2.all.min.js",
    "toastr.min.js": "https://cdn.jsdelivr.net/npm/toastr@2.1.4/build/toastr.min.js",
    "anime.min.js": "https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js",
    # M42's own: not on a CDN; the saved copy M42 checks (and tells the user about) has it in lib/
    "m42-ui.css": "m42-ui.css",
    "m42-ui.js": "m42-ui.js",
    "lucide.css": "lucide.css",
    # 🧊 only on a page with a 3D scene (data-m42-3d): three.js r128 and its loaders, M42's own 3D kit
    "three.min.js": "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js",
    "GLTFLoader.js": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js",
    "STLLoader.js": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js",
    "m42-3d.js": "m42-3d.js",
}
THREE_D_FILES = ("three.min.js", "GLTFLoader.js", "STLLoader.js", "m42-3d.js")
PAGE_ASK_RX = re.compile(r"\b(html|website|web\s*site|web\s*page|webpage|web\s*app|web\s*dashboard|dashboard|"
                         r"landing\s*page|portfolio|home\s*page|admin\s*(?:panel|page|site)|ui\s*design|front-?end|"
                         r"(?:booking|login|signup|sign\s*up|product|shop|store|blog|contact|about)\s*page)\b", re.I)


def site_request(text):
    """A web site / page / web app to build in a project folder (not a canvas game, no other stack): it is built
    from a page plan like a chat page, not by the game-style build plan ("admin page for a retail shop" got wiki
    searches and "Missing: camera and scrolling / enemies", 2026-10-26)."""
    return wants_kit(text) and bool(PAGE_ASK_RX.search(text or "") or re.search(
        r"\b(page|site|app|portal|panel|system)\b", text or "", re.I))
LIVE_RX = re.compile(r"\b(dashboard|admin|monitor\w*|live|real[- ]?time|sensors?|iot|readings?|tracker|status)\b", re.I)
# readings that come from somewhere (a device, an API): only then a data source, a fetch, the question
DEVICE_RX = re.compile(r"\b(iot|sensors?|esp\w*|arduino|nodemcu|raspberry|device|mqtt|thingspeak|firebase|blynk|"
                       r"api|endpoint|real[- ]?time|live data|live readings?|readings?|telemetry|plc|scada)\b", re.I)


def chat_page_request(text):
    """A web page asked for in the chat (no project folder) that the kit fits: not a game, no other stack."""
    return bool(PAGE_ASK_RX.search(text or "")) and wants_kit(text)


def theme_snippet(theme):
    """The theme in a few lines the model copies into its <style>."""
    p, on = theme["primary"], theme["on"]
    r, g, b = (int(p[i:i + 2], 16) for i in (1, 3, 5))
    return (f":root {{ --bs-primary: {p}; --bs-primary-rgb: {r}, {g}, {b}; --bs-link-color: {p}; }}\n"
            f".btn-primary {{ --bs-btn-bg: {p}; --bs-btn-border-color: {p}; --bs-btn-color: {on}; "
            f"--bs-btn-hover-bg: {p}; --bs-btn-hover-color: {on}; --bs-btn-active-bg: {p}; }}\n"
            f".btn-outline-primary {{ --bs-btn-color: {p}; --bs-btn-border-color: {p}; --bs-btn-hover-bg: {p}; "
            f"--bs-btn-hover-color: {on}; }}")


def live_note(request):
    """Where a dashboard's values come from: a device / API (fetch + demo readings) or sample data made in JS."""
    if live_kind(request) == "device":
        return ("\n- It shows live readings: a <script> updates every value (fetch from a const API_URL every few "
                "seconds; when it can't be reached, changing demo readings with M42UI.demo), the time of the last update, "
                "and whatever the user asked to be worked out from the readings is computed in JS, not fixed text.")
    if live_kind(request) != "none":
        return ("\n- Its numbers are realistic sample data made in JS that changes every few seconds (M42UI.demo), "
                "no fetch and no data source: it must look alive.")
    return ""


def chat_note(request, theme, spec=None):
    """What the coder is told for a page in the chat: the kit's CDN tags and rules. The theme colours, the look
    (dark / light, style, fonts) and any kit tag the page forgets are put in by M42 itself (wire_chat_page)."""
    css = "\n".join(f'<link rel="stylesheet" href="{CDN[f]}">' for f in KIT_FILES if f.endswith(".css") and f not in THREE_D_FILES)
    js = "\n".join(f'<script src="{CDN[f]}"></script>' for f in KIT_FILES if f.endswith(".js") and f not in THREE_D_FILES)
    look = (theme or {}).get("look") or {}
    return (f"\n\n[M42 web kit for this page: write ONE complete index.html in a single ```html block. In <head> put "
            f"exactly these stylesheet tags (leave out the ones the page doesn't use):\n{css}\nand right before "
            f"</body> these scripts in this order (only the ones the page uses; Toastr needs jQuery):\n{js}\n"
            f"M42 adds the theme itself (colours {theme['primary']}, {look.get('accent2', '')}, {look.get('accent3', '')}; "
            f"{look.get('theme', 'light')}, {look.get('style', 'glass')} style): use var(--m42-accent) in your own CSS, "
            "never other brand colours.\n"
            + FILE_NOTE.split("\n", 1)[1]
            + "\n- Every item the user listed must be on the page and work." + live_note(request) + "\n"
            + UI_NOTE + ("\n" + dash_note(spec) if live_kind(request) != "none" else "") + "]")


def file_note(request, spec=None):
    """The kit rules for one file of a built site: Bootstrap & co., M42 UI, and its live-data parts for a dashboard."""
    return FILE_NOTE + "\n" + UI_NOTE + live_note(request) + ("\n" + dash_note(spec) if live_kind(request) != "none" else "")


def localize(html, folder):
    """A copy of the page for M42's own check: the kit's CDN URLs point at local copies in folder/lib (offline,
    and the class / API checks read the same files). Returns (html, kit CSS files the page loads)."""
    used = []
    for name, url in CDN.items():
        rx = re.compile(r"""(["'])(?:\./|lib/)?""" + re.escape(url) + r"""(["'])""")  # m42-ui.css: a bare name
        if rx.search(html):
            html = rx.sub(lambda m: m.group(1) + "lib/" + name + m.group(2), html)
            used.append(name)
    if used:
        sync_files(folder, set(KIT_FILES), "")  # every kit file once; pages of later chats use them too
    return html, [f for f in used if f.endswith(".css")]


INTENT = {}  # the model's decisions about the page being built (uiflows.intent_of): set by agent.use_intent


def user_theme(request, word):
    """The light / dark the USER asked for: the model's reading; the word only when it was not asked."""
    if "named_theme" in INTENT:
        return INTENT["named_theme"]
    rx = r"\b(light|white|bright)\b" if word == "light" else r"\bdark\b"
    return word if re.search(rx, request or "", re.I) else ""


def live_kind(request):
    """The page's numbers: "none", "demo" or "device", as the model decided; the words only when it was not asked."""
    if INTENT.get("live") in ("none", "demo", "device"):
        return INTENT["live"]
    return "device" if DEVICE_RX.search(request or "") else "demo" if LIVE_RX.search(request or "") else "none"


def app_asked(request):
    """An app screen (a dashboard, an admin panel, a tool), as the model decided; the words only when it was not asked."""
    import pagebuild
    if INTENT.get("layout") in ("site to read", "app screen"):
        return INTENT["layout"] == "app screen"
    return bool(pagebuild.APP_RX.search(request or ""))


def static_values_problem(request, html):
    """A dashboard / monitor whose values are fixed text: no script at all. Only where readings come from somewhere
    (a device, a sensor, an API): a recipe or school "dashboard" with no source was told to fetch an API_URL and fake
    readings (2026-11-12); its numbers are content."""
    if live_kind(request) != "device":
        return []
    if live_kind(request) != "none" and not re.search(r"<script\b(?![^>]*\ssrc=)[^>]*>\s*\S", html, re.I):
        return ["The page has no script, so its values are fixed text and never change: add a <script> that "
                "updates them from readings (fetch from a const API_URL every few seconds, with changing demo "
                "readings when it can't be reached) and computes what the user asked for from them"]
    if live_kind(request) != "none" and re.search(r"\bfetch\s*\(|\$\.(?:ajax|get|getJSON)\s*\(", html) \
            and not re.search(r"Math\.random\s*\(|M42UI\.demo\s*\(", html):
        # the device isn't there while the page is tried (or built): "N/A" everywhere shows nothing working
        return ["When API_URL can't be reached the page shows no readings at all: in the fetch's catch, show "
                "changing demo readings (Math.random around normal values, marked 'Demo data') and run every "
                "computed item on them, so the page works before the device is connected"]
    return []


THEN_RX = re.compile(r"\.then\(\s*(?:\(\s*([A-Za-z_$][\w$]*)\s*\)|([A-Za-z_$][\w$]*))\s*=>")


def promise_scope_problems(html):
    """A later .then() using the earlier .then()'s parameter (fetch(..).then(response => response.json())
    .then(data => { ... response.ok ... })): it isn't defined there, so the page stops with a ReferenceError the
    moment real data arrives. A real page (2026-10-25); the browser check never saw it (no device answered)."""
    out = []
    ms = list(THEN_RX.finditer(html or ""))
    for a, b in zip(ms, ms[1:]):
        between = html[a.end():b.start()]
        if re.search(r"\bfetch\s*\(|\bfunction\b|;\s*\n", between):
            continue  # not one chain
        p1, p2 = a.group(1) or a.group(2), b.group(1) or b.group(2)
        end = re.search(r"\.then\(|\.catch\(|\n\s*\}\s*\n", html[b.end():])
        body = html[b.end():b.end() + (end.start() if end else 2000)]
        if p1 != p2 and re.search(r"(?<![\w$.])" + re.escape(p1) + r"\s*\.", body) and not re.search(
                r"\b(?:let|const|var)\s+" + re.escape(p1) + r"\b", html):
            out.append(f"In the .then({p2} => ...) after .then({p1} => ...), `{p1}` is not defined (it is only the "
                       f"first callback's parameter), so the page stops with a ReferenceError as soon as real data "
                       f"comes: check {p1}.ok in the first .then (throw if not ok) and use only {p2} in the second")
    return out[:2]


# ---- the page's spec: a one-line request becomes the details a page needs (the user's idea, 2026-10-25) ------
# "weather ... Tempture Humitity, rain percentage, weather pritection ... panni kutu" gave fixed numbers and a
# "Weather Protection" box: nobody had worked out where the readings come from or what "pritection" (prediction)
# is computed from. M42 writes that spec first, asks only what it can't know, and checks the page against it.

SPEC_PROMPT = """You write the spec of ONE web page for a small coding model, from the user's request.
The user may write Tanglish (Tamil in English letters) and misspell words: read each word as the word the
context needs (next to "weather", "pritection" is "prediction"; "Tempture" is temperature; "Humitity" humidity).
- items: every thing the user asked to see or do on the page, in their order, in correct English, then the few
  things this kind of page normally needs (e.g. a dashboard: last-updated time; a shop: cart). Each item is ONE
  concrete thing named as it appears on the page ("Total users", "Revenue this month", "Add user button"), never a
  group like "Dashboard overview" or "Quick actions".
  shows: what it shows and how (a big number with unit, a gauge, a chart of the last hour, a form, a list).
  source: "reading" (comes from the data), "computed" (worked out in JS from the readings), "input" (the user
  types or clicks it), or "fixed" (text that doesn't change).
- data: only for a page that shows readings from a device or an API the user mentioned. where: the source if the
  user named one (an ESP32 / device IP, ThingSpeak, Firebase, MQTT, a URL), else "". fields: the reading names in
  JSON. An admin panel, shop or site with no device: realistic sample data made in JS, no data source.
- rules: how each computed item is worked out, with concrete numbers (e.g. "Rain prediction: 'Rain likely' when
  humidity > 80 and rain > 60, 'Cloudy' when humidity > 65, else 'Clear'").
- layout: one line (how it looks on a phone).
- hero: the first screen real sites of this kind have: "search" (a search / booking card: travel, rentals, jobs,
  real estate), "split" (text + a picture / product), "centered" (a statement: portfolio, event, agency),
  "image" (a big photo: restaurant, hotel, tourism), "compact" (a tool, an app, a dashboard), or "none" (the page
  IS one screen of its own with no heading band: a sign-in / login or sign-up page, a single form, a chat screen; a
  login page is its form beside the brand, not a landing page about logging in).
- sections: the page's sections top to bottom, the way real sites of THIS kind are built (follow the web text):
  name (as on the page), what (what it holds, concretely), part: the M42 UI part that fits ("search", "results",
  "picks", "summary", "chips", "tabs", "cards", "prices", "reviews", "steps", "gallery", "stats", "form", "table",
  "faq", "cta") or "custom" (something this kind of site needs that those don't cover, like a seat map or a
  timetable: the idea, not a topic to borrow; say in what how it looks). Not one recipe for every
  site. A landing page or a business's site has 5-7 sections, as a premium one does: what it offers, why choose it
  (its proof: numbers, years, people), how it works or a gallery of its work, what people say, questions, the
  call to act; a page of 2-3 sections looks empty. (An app screen or a single form keeps what it needs.)
- look: what suits THIS page's content and audience (and what the web text shows for pages like it), so every
  site doesn't look the same: theme "light" or "dark" by the subject's mood ("dark" for night, fireworks and
  festivals, nightlife, gaming, music, cinema, luxury tech, space; "light" for food, health, schools, family, shops,
  travel by day); style "glass" (frosted cards, glows), "minimal" (flat, calm),
  "bold" (big type, strong gradients), "elegant" (serif headings, refined, luxury) or "playful" (round, colourful);
  font "modern", "elegant", "tech" or "friendly"; colors: 3 hex colours that fit the content (primary, secondary,
  accent), the subject's own colours, e.g. a spa: sage #7c9a82, sand #c8a97e, clay #c47a5a; a cyber security tool:
  #22d3ee, #6366f1, #a3e635; fireworks: #dc2626, #f59e0b, #facc15; a dairy: #1d4ed8, #fef3c7, #16a34a;
  corners "sharp" (serious, editorial, tools), "rounded" or "pill" (soft, friendly, kids, food); density "airy"
  (luxury, portfolio, landing pages: big spaces), "balanced", "dense" (dashboards, tables, admin); cards "shadow",
  "outlined" (crisp, minimal), "flat" (calm, editorial) or "glass" (glass style); why: a few words. Follow the user's words first (a colour, "dark", "glass", "luxury").
  archetype: the whole page's kind of design: "product" (one product or a gadget to sell: headphones, a phone, a
  watch, a car, a device; or "like Apple"), "editorial" (a law firm, a consultancy, finance advisors, an architect,
  luxury, fashion, a magazine; "like Vogue"), "warm" (a local business: a bakery, a cafe, a salon, a shop, a clinic),
  "saas" (software, an app, a startup tool), "bold" (an event, a festival, kids, a game), "portfolio" (a photographer,
  an artist, a studio). For an admin page or an app screen: "saas".
- question: ONE short question, only when something the page can't work without is missing and can't be
  guessed (where a device's or API's readings come from). Empty otherwise. Never ask about colours, layout or style."""

PARTS = ("search", "results", "picks", "summary", "chips", "tabs", "cards", "prices", "reviews", "steps", "gallery",
         "stats", "form", "table", "faq", "cta")
import icons as _icons  # noqa: E402
import themes as _themes  # noqa: E402
import widgets as _widgets  # noqa: E402  (M42's widget library: calendar, donut, toggles, data table, popup...)
PARTS = PARTS + tuple(_widgets.WIDGETS)

SPEC_SCHEMA = {"type": "object", "properties": {
    "title": {"type": "string", "maxLength": 60},
    "items": {"type": "array", "minItems": 1, "maxItems": 12, "items": {"type": "object", "properties": {
        "name": {"type": "string", "maxLength": 40}, "shows": {"type": "string", "maxLength": 140},
        "source": {"type": "string", "enum": ["reading", "computed", "input", "fixed"]}},
        "required": ["name", "shows", "source"]}},
    "data": {"type": "object", "properties": {"where": {"type": "string", "maxLength": 120},
                                              "fields": {"type": "array", "items": {"type": "string"}, "maxItems": 10}},
             "required": ["where", "fields"]},
    "rules": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 6},
    "layout": {"type": "string", "maxLength": 200},
    "hero": {"type": "string", "enum": ["search", "split", "centered", "image", "compact", "none"]},
    "sections": {"type": "array", "maxItems": 9, "items": {"type": "object", "properties": {
        "name": {"type": "string", "maxLength": 40}, "what": {"type": "string", "maxLength": 160},
        "part": {"type": "string", "enum": list(PARTS) + ["custom"]}}, "required": ["name", "what", "part"]}},
    "look": {"type": "object", "properties": {
        "theme": {"type": "string", "enum": ["light", "dark"]},
        "style": {"type": "string", "enum": ["glass", "minimal", "bold", "elegant", "playful"]},
        "font": {"type": "string", "enum": ["modern", "elegant", "tech", "friendly"]},
        "colors": {"type": "array", "items": {"type": "string", "maxLength": 9}, "minItems": 3, "maxItems": 3},
        # the design tokens (like a UIGEN page's own tokens at its top, 2026-11-09): how round, how much room, what cards
        "corners": {"type": "string", "enum": list(LOOK_EXTRA["corners"])},
        "density": {"type": "string", "enum": list(LOOK_EXTRA["density"])},
        "cards": {"type": "string", "enum": list(LOOK_EXTRA["cards"])},
        "archetype": {"type": "string", "enum": list(ARCHETYPES)},
        "why": {"type": "string", "maxLength": 80}},
        "required": ["archetype", "theme", "style", "font", "colors", "corners", "density", "cards", "why"]},
    "question": {"type": "string", "maxLength": 200}},
    "required": ["title", "items", "data", "rules", "layout", "hero", "sections", "look", "question"]}

SPEC_STOP = {"with", "from", "the", "and", "status", "value", "level", "card", "section", "page", "display", "show",
             "last", "time", "data", "info", "information", "current", "live", "chart", "panel", "box",
             # how a value is shown, not what it is ("Rain percentage" is a "%" on the page)
             "percentage", "percent", "rate", "reading", "readings", "meter", "gauge", "indicator", "graph", "count",
             "number", "amount", "list", "button", "form", "field",
             # groups and words of layout, not things on the page ("Dashboard overview", "Quick actions")
             "overview", "quick", "actions", "summary", "main", "area", "widget", "widgets", "header", "footer",
             "toggle", "theme", "dashboard", "navigation", "sidebar", "menu", "grid", "cards", "metrics", "stats",
             # the widget an item is made of: "Route selection dropdown" is a <select>, "Date picker" an
             # <input type="date"> (both were there and reported missing, a whole page written again, 2026-10-26)
             "dropdown", "picker", "selection", "selector", "select", "calendar", "slider", "modal", "popup",
             "tabs", "input", "inputs", "fields", "checkbox", "radio", "textbox", "options", "option", "view"}


QUERY_SCHEMA = {"type": "object", "properties": {"query": {"type": "string", "maxLength": 100}}, "required": ["query"]}


def query_messages(request):
    """A web search for what a good page of this kind has (like a game's reference search)."""
    return [{"role": "system", "content": (
        "The user wants a web page (they may write Tanglish and misspell words). Write ONE short English web search "
        "query, spelling corrected, that finds how real sites of this kind are built (their sections and flow, top "
        "to bottom), how they look and what they show, in the form '<the user's kind of site> website homepage "
        "sections <its main features> design'. About the user's site only (a page with no subject named: what the "
        "request and its reference describe, never a made-up topic). No site names, no 'html code'.")},
        {"role": "user", "content": request[:800]}]


def spec_messages(request, reference="", picture="", flow=""):
    user = request[:1500]
    if flow.strip():  # M42's flow library (uiflows.py): the regions real UIs of this kind have
        user += ("\n\nHow real UIs of this kind are laid out (M42's flow library; the page's sections follow these regions, "
                 "each with the part that shows it):\n" + flow.strip()[:900])
    if picture.strip():  # the user's reference picture: its cards ARE the page; no web ideas on top of it
        user += ("\n\nThe user's reference picture shows exactly these cards (the page has these and nothing else: the "
                 "items are what they show; add no other features):\n" + picture.strip()[:2500])
    elif reference.strip():
        user += ("\n\nFrom the web, about pages like this (ideas for items and rules; the user's request comes first, "
                 "and nothing here is the user's data source):\n" + reference.strip()[:2500])
    return [{"role": "system", "content": SPEC_PROMPT}, {"role": "user", "content": user}]


SOURCE_RX = re.compile(r"https?://\S+|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/\S*)?|\b(?:thingspeak|firebase|mqtt|blynk|"
                       r"adafruit\s*io|google\s*sheets?|node-?red|supabase|websocket)\b", re.I)


def spec_from_cards(request, sections):
    """A spec made from a reference picture's cards alone (designref's grid: name, part, what), when the model's spec
    can't be used: each card is an item and a section; the subject from the request's "(about: ...)"."""
    m = re.search(r"\((?:about|the reference picture shows): ([^;,)]+)", request or "")
    title = (m.group(1) if m else re.sub(r"\s*\(.*", "", request or ""))[:60].strip().title() or "Dashboard"
    raw = {"title": title,
           "items": [{"name": s.get("name") or s.get("part", "").replace("_", " "), "shows": s.get("what") or "",
                      "source": "fixed"} for s in sections],
           "rules": [], "layout": "", "hero": "none", "question": "",
           "sections": [{"name": s.get("name") or "", "what": s.get("what") or "", "part": s.get("part") or "custom"}
                        for s in sections]}
    return clean_spec(raw, request)


def clean_spec(raw, request):
    """The model's spec, made safe to show and use. A device address the user never wrote is dropped (a guessed
    IP looks real and fails), and a live page with no source gets the question even if the model left it out."""
    items = [{"name": " ".join(str(i.get("name") or "").split())[:40], "shows": " ".join(str(i.get("shows") or "").split())[:140],
              "source": i.get("source") if i.get("source") in ("reading", "computed", "input", "fixed") else "fixed"}
             for i in raw.get("items") or [] if str(i.get("name") or "").strip()][:12]
    data = raw.get("data") or {}
    where = " ".join(str(data.get("where") or "").split())[:120]
    # a source is an address or a service the USER named: coder-7b wrote "Data: ESP32" for a request that never
    # said ESP32, and a guessed IP looks real and fails
    given = SOURCE_RX.findall(request or "")
    if not given or not any(g.lower() in where.lower() for g in given):
        where = ", ".join(dict.fromkeys(given)) if given else ""
    # readings from somewhere only for a device / API page: "admin panel dashboard" got the ESP32 question
    live = any(i["source"] in ("reading", "computed") for i in items) and live_kind(request) == "device"
    # no question before building (the user, 2026-11-11: an IoT admin panel asked for an IP address): a live page
    # without an address the user gave gets changing demo readings and an API_URL to set later
    question = ""
    if live and not where:
        where = "demo readings (API_URL to set later)"
    return {"title": " ".join(str(raw.get("title") or "").split())[:60], "items": items,
            "data": {"where": where, "fields": [str(f)[:30] for f in data.get("fields") or []][:10]} if live else {},
            "rules": [" ".join(str(r).split())[:200] for r in raw.get("rules") or []][:6],
            "layout": " ".join(str(raw.get("layout") or "").split())[:200], "question": question,
            "look": clean_look(raw.get("look")),
            "hero": raw.get("hero") if raw.get("hero") in ("search", "split", "centered", "image", "compact", "none") else "",
            "sections": [{"name": " ".join(str(x.get("name") or "").split())[:40],
                          "what": " ".join(str(x.get("what") or "").split())[:160],
                          "part": x.get("part") if x.get("part") in PARTS + ("custom",) else "custom"}
                         for x in raw.get("sections") or [] if isinstance(x, dict) and str(x.get("name") or "").strip()][:9]}


HEX_RX = re.compile(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def clean_look(look):
    """The spec's look with only known values; colours as #rrggbb (bad ones dropped: M42 fills them in)."""
    look = look if isinstance(look, dict) else {}
    colors = []
    for c in look.get("colors") or []:
        m = HEX_RX.search(str(c))
        if m:
            h = m.group(1)
            colors.append("#" + ("".join(x * 2 for x in h) if len(h) == 3 else h).lower())
    # a brand colour is a colour: the 4B gave a "clean, minimal" site white, light grey and near-black (#ffffff,
    # #f3f4f6, #111827), and the page came out grey: grey buttons, grey icons, a grey gradient (2026-11-10). Whites,
    # greys and blacks are dropped; with none left M42 picks the colours for this kind of site
    def _real(c):
        _, light, sat = colorsys.rgb_to_hls(*_rgb(c))
        return sat >= .18 and .1 <= light <= .9
    colors = [c for c in colors if _real(c)]
    return {"theme": look.get("theme") if look.get("theme") in ("light", "dark") else "",
            "style": look.get("style") if look.get("style") in STYLES else "",
            "font": look.get("font") if look.get("font") in FONTS else "",
            "colors": colors[:3], "why": " ".join(str(look.get("why") or "").split())[:80],
            **{k: look[k] for k in LOOK_EXTRA if look.get(k) in LOOK_EXTRA[k]},
            **({"archetype": look["archetype"]} if look.get("archetype") in ARCHETYPES else {})}


def with_answer(spec, answer):
    """The user's answer to the spec's question: the data source, or demo readings ("demo", "skip", "theriyathu")."""
    demo = re.match(r"\s*(demo|skip|no|illa|theriyathu|teriyadhu|later|apram|venam|vendam)\b", answer or "", re.I)
    where = "demo readings (API_URL to set later)" if demo else answer.strip()[:200]
    if not demo and not SOURCE_RX.search(answer or ""):
        # "esp32ip": a device, no address (a real answer, 2026-10-25): the coder must not write http://esp32ip/
        where += (" (no address given: one line at the top, const API_URL = 'http://192.168.x.x/data' with a comment "
                  "to put the device's IP there; demo readings until it answers)")
    data = dict(spec.get("data") or {}, where=where)
    return dict(spec, data=data, question="")


def spec_text(spec):
    """The spec as the user and the coder read it."""
    lines = [f"Spec: {spec['title']}" if spec.get("title") else "Spec:"]
    lines += [f"- {i['name']} ({i['source']}): {i['shows']}" for i in spec.get("items") or []]
    data = spec.get("data") or {}
    if data:
        lines.append(f"Data: {data.get('where') or 'not given yet'}" + (
            f"; JSON fields: {', '.join(data['fields'])}" if data.get("fields") else ""))
    lines += [f"Rule: {r}" for r in spec.get("rules") or []]
    if spec.get("hero"):
        lines.append(f"Hero: {spec['hero']} (class m42-hero is-{spec['hero']})" if spec["hero"] != "none" else "Hero: none")
    if spec.get("sections"):
        lines.append("Sections, top to bottom:")
        lines += [f"  {n}. {x['name']} [{x['part']}]: {x['what']}" for n, x in enumerate(spec["sections"], 1)]
    if spec.get("layout"):
        lines.append(f"Layout: {spec['layout']}")
    if spec.get("reference") and not spec.get("recipe"):  # designref.merge: what the reference design shows, top to bottom
        lines.append(f"Reference design, its blocks top to bottom (follow this structure where the content fits): "
                     f"{spec['reference']}")
    return "\n".join(lines)


def spec_problems(spec, html):
    """Spec items the page doesn't have: one of the item's own words is in neither its text nor its code ("Rain
    prediction" on a page with a rain % but no prediction)."""
    page = re.sub(r"<[^>]+>", " ", html or "").lower() + " " + (html or "").lower()
    out = []
    for i in (spec or {}).get("items") or []:
        words = [w for w in re.findall(r"[a-z]{4,}", i["name"].lower()) if w not in SPEC_STOP]
        found = sum(w[:max(4, len(w) - 3)] in page for w in words)  # stem: "predict" in predictRain()
        # every word of a short name ("Weather prediction"); a longer one may word it its own way ("Bus route search"
        # was a From / To / Date search card with no "route": reported missing, and the "fix" pasted the form twice)
        long_name = len(re.findall(r"[a-z]+", i["name"].lower())) >= 3  # ("bus" is too short to be a checked word)
        if words and found < (len(words) - 1 if long_name else len(words)):
            out.append(f"The spec's item \"{i['name']}\" ({i['shows']}) is not on the page")
    for x in (spec or {}).get("sections") or []:  # a section is there when one of its own words is (lenient)
        words = [w for w in re.findall(r"[a-z]{4,}", x["name"].lower()) if w not in SPEC_STOP]
        if words and not any(w[:max(4, len(w) - 3)] in page for w in words):
            out.append(f"The page has no section for \"{x['name']}\" ({x['what']}): add it [{x['part']}]")
    return out


# ---- the premium look on every page, and what the user adds themselves --------------------------------------
# "every web page or site, any logic: premium components, experience and look, never a plain static page; and the
# CSS / JS the user asks to add goes in too" (the user, 2026-10-25)

M42_CLASS_RX = re.compile(r"""class\s*=\s*["'][^"']*\bm42-(?:nav|hero|section|feature|price|quote|steps|gallery|cta|"""
                          r"""form|stat|gauge|chart|banner|head|card|btn|table|footer)\b""")


def ui_problems(request, html):
    """A kit page built without M42 UI is the plain page the user doesn't want; on a live page every stat, gauge
    and chart must be fed by the script, or it shows a loading shimmer for ever."""
    out = []
    if not M42_CLASS_RX.search(html or ""):
        out.append("The page doesn't use M42 UI, so it looks plain: build it with its parts (body class m42-ui, "
                   "m42-nav, m42-hero with m42-btn, m42-section + m42-section-head, m42-feature / m42-price / "
                   "m42-quote cards, m42-cta, m42-footer" + ("; m42-head, m42-stat, m42-gauge, m42-chart, m42-banner "
                                                             "for the readings" if live_kind(request) != "none" else "")
                   + ")")
    elif not re.search(r"<body[^>]*class\s*=\s*[\"'][^\"']*\bm42-ui\b", html or "", re.I):
        out.append('Put class="m42-ui" on <body> (the M42 UI look starts there)')
    script = "\n".join(re.findall(r"<script\b(?![^>]*\ssrc=)[^>]*>(.*?)</script>", html or "", re.S | re.I))
    for kind, call in (("m42-stat", "set"), ("m42-gauge", "gauge"), ("m42-chart", "push")):
        for pid in re.findall(r"""<\w+[^>]*class\s*=\s*["'][^"']*\b""" + kind + r"""\b[^"']*["'][^>]*\bid\s*=\s*["']([\w-]+)""",
                              html or "") + re.findall(r"""<\w+[^>]*\bid\s*=\s*["']([\w-]+)["'][^>]*class\s*=\s*["'][^"']*\b"""
                                                       + kind + r"""\b""", html or ""):
            # M42UI.demo('id', ...) sets that card / gauge / chart itself
            if not re.search(r"M42UI\.(?:" + call + r"|demo)\(\s*[\"'`]" + re.escape(pid) + r"[\"'`]", script):
                out.append(f"#{pid} is a {kind} but the script never calls M42UI.{call}('{pid}', ...), so it never "
                           "shows a value")
    return out[:6]


USER_CODE_RX = re.compile(r"```\s*(css|js|javascript)\s*\n(.*?)```|<style\b[^>]*>(.*?)</style>|"
                          r"<script\b(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.S | re.I)


def user_code(request):
    """The CSS and JS the user pasted into the request to be added ("intha css add pannu"): (css, js)."""
    css, js = [], []
    for lang, block, style, script in USER_CODE_RX.findall(request or ""):
        if block.strip():
            (css if lang.lower() == "css" else js).append(block.strip())
        elif style.strip():
            css.append(style.strip())
        elif script.strip():
            js.append(script.strip())
    return "\n\n".join(css), "\n\n".join(js)


def _has(html, code):
    """Is the user's code in the page already (its lines, spaces ignored)?"""
    flat = re.sub(r"\s+", "", html or "")
    lines = [re.sub(r"\s+", "", x) for x in (code or "").splitlines() if len(x.strip()) > 3]
    return all(x in flat for x in lines)


def inject_user_code(html, css, js):
    """The user's own CSS / JS, added by M42 itself if the page doesn't carry it (after the kit, so it wins)."""
    if css and not _has(html, css):
        tag = f'<style data-m42-user>\n{css}\n</style>\n'
        html = re.sub(r"</head>", lambda m: tag + m.group(0), html, count=1, flags=re.I) if re.search(r"</head>", html, re.I) \
            else tag + html
    if js and not _has(html, js):
        tag = f'<script data-m42-user>\n{js}\n</script>\n'
        html = re.sub(r"</body>", lambda m: tag + m.group(0), html, count=1, flags=re.I) if re.search(r"</body>", html, re.I) \
            else html + tag
    return html


def wire_in_answer(answer, theme):
    """wire_chat_page on the last ```html block of a chat answer (what the user copies, runs and downloads)."""
    blocks = list(re.finditer(r"```html?[^\n]*\n(.*?)```", answer or "", re.S | re.I))
    if not blocks:
        return answer
    b = blocks[-1]
    new = wire_chat_page(b.group(1), theme)
    return answer if new == b.group(1) else answer[:b.start(1)] + new + answer[b.end(1):]


def inject_in_answer(answer, css, js):
    """The same for the last ```html block of a chat answer (what the user copies)."""
    blocks = list(re.finditer(r"```html?[^\n]*\n(.*?)```", answer or "", re.S | re.I))
    if not blocks or not (css or js):
        return answer
    b = blocks[-1]
    new = inject_user_code(b.group(1), css, js)
    return answer if new == b.group(1) else answer[:b.start(1)] + new + answer[b.end(1):]


# libraries a user names (their words -> what their tag's URL contains); M42 checks the page really loads them
NAMED_LIBS = [(r"\baos\b|animate on scroll", "AOS", r"\baos\b"), (r"\bswiper\b", "Swiper", "swiper"),
              (r"\bgsap\b|greensock", "GSAP", "gsap"), (r"chart\.?js", "Chart.js", r"chart(?:\.umd|\.min|\.js|@)"),
              (r"typed\.?js", "Typed.js", "typed"), (r"particles\.?js|tsparticles", "particles.js", "particles"),
              (r"\blottie\b", "Lottie", "lottie"), (r"animate\.css", "Animate.css", "animate"),
              (r"font\s*awesome", "Font Awesome", "font-?awesome"), (r"\bglightbox\b", "GLightbox", "glightbox"),
              (r"\bsplide\b", "Splide", "splide"), (r"three\.?js", "three.js", r"\bthree"), (r"\bleaflet\b", "Leaflet", "leaflet"),
              (r"datatables?", "DataTables", "datatables"), (r"\btippy\b", "Tippy.js", "tippy"), (r"\blenis\b", "Lenis", "lenis"),
              (r"scroll\s*reveal", "ScrollReveal", "scrollreveal"), (r"\bvanta\b", "Vanta.js", "vanta"),
              (r"\balpine\b", "Alpine.js", "alpine"), (r"\bisotope\b", "Isotope", "isotope"), (r"\bmasonry\b", "Masonry", "masonry")]


def lib_problems(request, html):
    """A library the user named that the page doesn't load."""
    urls = " ".join(re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", html or "", re.I)).lower()
    out = []
    for asked, name, token in NAMED_LIBS:
        if re.search(asked, request or "", re.I) and not re.search(token, urls):
            out.append(f"The user asked for {name}, but the page doesn't load it: add its CDN tag (cdnjs or jsdelivr, an "
                       f"exact version) and use it for what they asked")
    return out


# ---- ▶ Run in a popup, ⬇ Download as a zip (the user, 2026-10-25) ------------------------------------------------
# A page from the chat runs in M42's window in a sandboxed iframe (no access to M42), served from its own folder
# under a random id (never the M42 token: the page's own scripts can read their URL). The zip has index.html with
# the kit as local files, so it looks the same anywhere, offline too.

PREVIEW_ID_RX = re.compile(r"[0-9a-f]{16}")


def copy_assets(html, src_root, dest):
    """The page's own pictures and files from its project folder (images/x.jpg, css/, js/): the preview showed every
    photo broken, the folder outside had them (2026-11-12). Only files under src_root that the page names."""
    if not src_root:
        return
    src = Path(src_root).resolve()
    for rel in set(re.findall(r"""(?:src|href|url)\s*[=(]\s*["']?((?:\./)?(?:images|img|assets|media|css|js|fonts)/[^"')\s?#]+)""", html or "")):
        f = (src / rel.lstrip("./")).resolve()
        if src in f.parents and f.is_file():
            t = Path(dest) / rel.lstrip("./")
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, t)


def make_preview(html, root, src_root=None):
    """Save a chat page for the preview: root/<id>/index.html (kit tags -> lib/ copies of only what it uses), with the
    pictures it names from the project folder. Returns the id."""
    import secrets
    pid = secrets.token_hex(8)
    folder = Path(root) / pid
    folder.mkdir(parents=True, exist_ok=True)
    local, _ = localize(html, folder)
    used = {n for n in KIT_FILES if f"lib/{n}" in local}
    sync_files(folder, used, "")  # localize copied the whole kit once: keep only this page's files
    (folder / "index.html").write_text(local, encoding="utf-8")
    copy_assets(local, src_root, folder)
    return pid


def preview_file(root, pid, rel):
    """The file a preview asks for, inside its own folder only; None otherwise."""
    if not PREVIEW_ID_RX.fullmatch(pid or ""):
        return None
    base = (Path(root) / pid).resolve()
    p = (base / (rel or "index.html")).resolve()
    return p if base in p.parents and p.is_file() and not p.name.startswith(".") else None


PICK_JS = """<script id="m42-pick">(function(){var on=false,box=null,SIG="%s";
function mark(el){if(!box){box=document.createElement('div');box.style.cssText='position:fixed;pointer-events:none;z-index:2147483647;border:2px solid #f43f5e;border-radius:6px;background:rgba(244,63,94,.10);display:none';document.documentElement.appendChild(box);}
if(!el){box.style.display='none';return;}var r=el.getBoundingClientRect();box.style.display='block';box.style.left=r.left+'px';box.style.top=r.top+'px';box.style.width=r.width+'px';box.style.height=r.height+'px';}
function at(e){return e.target&&e.target.closest?e.target.closest('[data-m42-n]'):null;}
function off(){on=false;mark(null);document.documentElement.style.cursor='';}
addEventListener('message',function(e){if(e.data==='m42:pick-on'){on=true;document.documentElement.style.cursor='crosshair';}else if(e.data==='m42:pick-off')off();});
document.addEventListener('mouseover',function(e){if(on)mark(at(e));},true);
document.addEventListener('click',function(e){if(!on)return;var el=at(e);if(!el)return;e.preventDefault();e.stopPropagation();
var w=(el.innerText||el.getAttribute('alt')||el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').replace(/\\s+/g,' ').trim().slice(0,80);
parent.postMessage({m42pick:{n:+el.getAttribute('data-m42-n'),tag:el.tagName.toLowerCase(),words:w,sig:SIG,
page:location.pathname.split('/').slice(3).join('/')||'index.html'}},'*');off();},true);
addEventListener('keydown',function(e){if(on&&e.key==='Escape'){off();parent.postMessage({m42pick:null},'*');}});})();</script>"""


def pickable(page):
    """🎯 A page for the preview: each block of its body marked with its node id (domnode), and a small script: in
    pick mode (M42's 🎯 button) a click on the page says which block it is. The project's file never has these."""
    import domnode
    marked = domnode.annotate(page)
    js = PICK_JS % domnode.signature(page)
    i = marked.lower().rfind("</body>")
    return marked[:i] + js + marked[i:] if i >= 0 else marked + js


def unpickable(page):
    import domnode
    return domnode.strip(re.sub(r'<script id="m42-pick">.*?</script>', "", page, flags=re.S))


def preview_zip(root, pid):
    """index.html + lib/ (only the files it uses, the icon fonts with their CSS) as zip bytes; None if unknown."""
    import io
    import zipfile
    if not PREVIEW_ID_RX.fullmatch(pid or "") or not (Path(root) / pid / "index.html").is_file():
        return None
    base = Path(root) / pid
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in (".html", ".htm"):
                z.writestr("m42-page/" + p.relative_to(base).as_posix(), unpickable(p.read_text(encoding="utf-8", errors="ignore")))
            elif p.is_file() and not p.name.startswith("."):
                z.write(p, "m42-page/" + p.relative_to(base).as_posix())
    return buf.getvalue()


WHOLE_PAGE_RX = re.compile(r"<!doctype html|<html[\s>]|<body[\s>]", re.I)


# page problems a few line edits can't fix: the page is written again whole for these
STRUCTURAL_RX = re.compile(r"has no script|doesn't use M42 UI|is not on the page|shows no readings at all", re.I)


def duplicate_ids(html):
    """An id used twice: getElementById finds only the first, so the second form / list never works (a line "fix"
    pasted a search form with id="from", "to", "date" into two more places, 2026-10-26)."""
    ids = re.findall(r"""<[a-zA-Z][^>]*?\sid\s*=\s*["']([^"']+)["']""", re.sub(r"<script\b.*?</script>", " ", html or "",
                                                                         flags=re.S | re.I))
    twice = sorted({i for i in ids if ids.count(i) > 1})
    return [f"These ids are used more than once, so only the first of each works: {', '.join(twice[:8])}. Keep one "
            "element per id (remove a pasted copy, or give it its own id)"] if twice else []


def make_preview_folder(src_root, root, files):
    """A site saved in a project folder, for the popup: its pages and their css / js / lib, copied under a random id
    (the folder itself is never served). Returns the id."""
    import secrets
    pid = secrets.token_hex(8)
    dest = Path(root) / pid
    for rel in files:
        s = Path(src_root) / rel
        if s.is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, dest / rel)
    for rel in files:  # each page's pictures (images/), as named in it
        s = Path(src_root) / rel
        if s.is_file() and rel.endswith((".html", ".htm")):
            copy_assets(s.read_text(encoding="utf-8", errors="ignore"), src_root, dest)
            with contextlib.suppress(OSError, ValueError):  # 🎯 its blocks clickable on the preview (the copy only)
                (dest / rel).write_text(pickable(s.read_text(encoding="utf-8")), encoding="utf-8")
    for sub in ("lib", "models"):  # the kit, and the 3D models of a 3D scene (the user's, or found online)
        for p in (Path(src_root) / sub).rglob("*") if (Path(src_root) / sub).is_dir() else []:
            if p.is_file() and not p.name.startswith("."):
                t = dest / p.relative_to(src_root)
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, t)
    return pid


_3d_classes = None


def _kit_3d_classes():
    """The classes bundled/m42-3d.js styles in the CSS it puts on the page itself."""
    global _3d_classes
    if _3d_classes is None:
        try:
            js = (BUNDLED / "m42-3d.js").read_text(encoding="utf-8")
            m = re.search(r"st\.textContent = `(.*?)`;", js, re.S)
            _3d_classes = css_classes(m.group(1)) if m else set()
        except OSError:
            _3d_classes = set()
    return _3d_classes


# ---- 📦 a library the user named (agent: their asks, 2026-11-17: "the JS / CSS the user asks for is used"): its npm
# package from jsDelivr, the version resolved once and kept with the page (the same file on every redraw), the files
# kept in m42/cache/libs and copied into the site's lib/ (the page works offline), linked BEFORE M42's own CSS / JS:
# M42's layout stays whole over a framework's CSS, and M42's script finds the library (Chart.js draws its charts)
LIB_CACHE = Path(__file__).resolve().parent / "cache" / "libs"
# a library the user names that has a way of its own to run on a page (data): Tailwind's npm package is its build tool;
# on a page it runs as its browser build, which writes its classes into cascade layers: M42's and Bootstrap's CSS,
# outside any layer, always win over them (the CSS standard), so Tailwind adds and never undoes M42's look (the user,
# 2026-11-17: "their CSS used, no collapse"); its colours and fonts are tied to the page's theme (TAILWIND_THEME)
LIB_ADAPTERS = {"tailwindcss": {"npm": "@tailwindcss/browser", "kind": "js", "tailwind": True}}
TAILWIND_THEME = """<style type="text/tailwindcss">
@theme inline {
  --color-primary: var(--m42-accent, #4f46e5); --color-secondary: var(--m42-accent-2, #06b6d4);
  --color-accent: var(--m42-accent-3, #f59e0b); --color-ink: var(--m42-text, #0f172a); --color-muted: var(--m42-muted, #64748b);
  --color-surface: var(--m42-surface, #ffffff); --color-page: var(--m42-bg, #f8fafc); --color-line: var(--m42-border, #e2e8f0);
  --font-sans: var(--m42-font, ui-sans-serif, system-ui, sans-serif); --radius-lg: var(--m42-radius, 12px);
}
</style>"""
POPULAR_HITS = 1_000_000  # jsDelivr downloads a month a library needs to be fetched (Chart.js: hundreds of millions)
NPM_RX = re.compile(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*$")


def _get_json(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_library(lib):
    """lib: {"name", "npm", "kind", "version"?}. Returns it with "version" and "files" ([(local path, kind)]), or None."""
    import urllib.request
    npm = str(lib.get("npm") or "").strip().lower()
    if npm in LIB_ADAPTERS:  # (its own way to run on a page)
        lib = dict(lib, **LIB_ADAPTERS[npm])
        npm = lib["npm"]
    if not NPM_RX.match(npm) or npm in ("bootstrap", "jquery", "animejs", "sweetalert2", "toastr", "three"):  # (the kit has them)
        return None
    ver = str(lib.get("version") or "")
    if not ver:  # (a well-known library only: "Vanilla JS" found npm's "vanilla" 0.0.5, a stranger's package, 2026-11-17)
        try:
            hits = _get_json(f"https://data.jsdelivr.com/v1/stats/packages/npm/{npm}?period=month").get("hits") or {}
            if int(hits.get("total") or 0) < POPULAR_HITS:
                return None
        except (OSError, ValueError, TypeError):
            return None
        try:
            ver = str(_get_json(f"https://data.jsdelivr.com/v1/packages/npm/{npm}/resolved").get("version") or "")
        except (OSError, ValueError):
            return None
    if not re.match(r"^\d+\.\d+\.\d+", ver):
        return None
    try:
        ep = _get_json(f"https://data.jsdelivr.com/v1/packages/npm/{npm}@{ver}/entrypoints").get("entrypoints") or {}
    except (OSError, ValueError):
        return None
    files = []
    # the entry of its own kind only: a CSS framework's CSS (Tailwind's "js" entry is its Node build, no use on a page)
    adapted = npm in {a["npm"] for a in LIB_ADAPTERS.values()}
    for kind in ([lib.get("kind")] if adapted and lib.get("kind") in ("css", "js") else ["css", "js"]):
        f = (ep.get(kind) or {}).get("file")
        if not f or not re.match(r"^/[\w./@-]+\.(?:js|css)$", f):
            continue
        if kind == "js" and kind != lib.get("kind") and not re.search(r"/dist/|\.min\.js$|umd|browser", f):
            continue  # (the other kind's file only when it is built for a page: a CSS framework's "js" is its Node build)
        dest = LIB_CACHE / f"{npm.replace('/', '__')}@{ver}" / Path(f).name
        if not dest.is_file():
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(f"https://cdn.jsdelivr.net/npm/{npm}@{ver}{f}", timeout=60) as r:
                    data = r.read()
                if len(data) < 200:
                    continue
                dest.write_bytes(data)
            except OSError:
                continue
        files.append((str(dest), kind))
    return dict(lib, npm=npm, version=ver, files=files) if files else None


def link_libraries(html, root, libs):
    """The fetched libraries copied into root/lib/ and linked before M42's own CSS and script."""
    import shutil
    css_tags, js_tags = [], []
    for lib in libs or []:
        for src, kind in lib.get("files") or []:
            name = f"{lib['npm'].replace('/', '__').lstrip('@')}-{lib['version']}-{Path(src).name}"  # (no "@" in a page's URL)
            dest = Path(root) / "lib" / name
            try:
                if not dest.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
            except OSError:
                continue
            if f"lib/{name}" in html:
                continue
            (css_tags if kind == "css" else js_tags).append(
                f'<link rel="stylesheet" href="lib/{name}">' if kind == "css" else f'<script src="lib/{name}"></script>')
    if any(l.get("tailwind") and l.get("files") for l in libs or []) and 'type="text/tailwindcss"' not in html:
        html = html.replace("</head>", TAILWIND_THEME + "\n</head>", 1)  # (Tailwind's colours / fonts = the page's theme)
    if css_tags:  # (FIRST: Bootstrap's and M42's CSS come after it and win where they meet: a framework's reset of the
        # page's base styles does not undo M42's look; its own classes still work)
        m = re.search(r'<link[^>]+rel="stylesheet"[^>]*>', html)
        html = (html[:m.start()] + "\n".join(css_tags) + "\n" + html[m.start():]) if m else html.replace("</head>", "\n".join(css_tags) + "\n</head>", 1)
    if js_tags:
        m = re.search(r'<script[^>]+lib/m42-ui\.js[^>]*>', html)
        html = (html[:m.start()] + "\n".join(js_tags) + "\n" + html[m.start():]) if m else html.replace("</body>", "\n".join(js_tags) + "\n</body>", 1)
    return html


def contrast_fix(c):
    """(selector, colour) for a text the page check found too faint (its colour, its background, the contrast it needs):
    its own colour moved toward black or white, a step at a time, until it reads (2026-11-17: a coder spent 4 minutes
    on one such text and made it worse, 4.25 -> 3.63). None when the check gave no colours. (The browser gives 0-255;
    this file's colours are 0-1.)"""
    fg, bg, path = c.get("fg"), c.get("bg"), str(c.get("path") or "")
    if not (isinstance(fg, list) and len(fg) >= 3 and isinstance(bg, list) and len(bg) >= 3 and path):
        return None
    a = fg[3] if len(fg) > 3 and fg[3] is not None else 1
    back = [float(bg[i]) / 255 for i in range(3)]
    cur = [(float(fg[i]) / 255) * a + back[i] * (1 - a) for i in range(3)]
    need = float(c.get("need") or 4.5) + 0.2
    to = (0.0, 0.0, 0.0) if contrast((0, 0, 0), back) >= contrast((1, 1, 1), back) else (1.0, 1.0, 1.0)
    for k in range(1, 21):
        t = k / 20
        col = tuple(cur[i] + (to[i] - cur[i]) * t for i in range(3))
        if contrast(col, back) >= need:
            return path, _hex(col)
    return path, _hex(to)
