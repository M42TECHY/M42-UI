"""Design data for a kind of product when there is no reference picture: bundled/uiux/ holds the CSV data of
ui-ux-pro-max-skill (github.com/nextlevelbuilder/ui-ux-pro-max-skill, MIT, downloaded 2026-11-03): 192 product
types, each with its palette, style, landing page pattern, font pairing mood and what to avoid. The request's words
pick the product type; its palette, light / dark, style, font and section order go into the page spec, where the
4B guessed them before (the user, 2026-11-03: "when there is no reference, use that data")."""
import csv
import functools
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent / "bundled" / "uiux"
STOP_RX = re.compile(r"^(page|site|website|web|app|landing|design|pannu|venum|oru|for|the|and|with|ui|ux|make|build|"
                     r"create|new|nalla|super|premium|modern|my|our|business|company|service|services|admin|panel|dashboard|portal|shop|store|"
                     r"system|management|online)$")


@functools.lru_cache(maxsize=None)
def rows(name):
    try:
        with open(DIR / name, encoding="utf-8", newline="") as fh:
            return tuple(csv.DictReader(fh))
    except OSError:
        return ()


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(w) > 2 and not STOP_RX.match(w)}


def _hit(w, pool):
    """'restaurants' fits 'restaurant', 'bakeries' fits 'bakery' (a plural only: "hospital" is no "hospitality")."""
    stem = lambda x: re.sub(r"(ies|es|s)$", "", x)  # noqa: E731
    return any(w == p or stem(w) == stem(p) for p in pool)


CHOOSE_SCHEMA = {"type": "object", "properties": {"best": {"type": "integer"}}, "required": ["best"]}


def choose_messages(request):
    """The chat model picks the product type by meaning ("coffee shop" -> Bakery/Cafe, "hospital" -> a clinic, not a
    hotel). The list is in the system message, the same each time, so llama-server keeps it cached."""
    names = "\n".join(f'{n}. {r["Product Type"]}' for n, r in enumerate(rows("products.csv")))
    return [{"role": "system", "content": "Pick the product type closest to the web page the user wants (what the business "
                                          "is or does; a shop that sells goods with no type of its own: E-commerce; renting "
                                          "cars: Automotive). -1 if none is close. Answer {\"best\": number}.\n\n" + names},
            {"role": "user", "content": f"The page: {str(request or '')[:300]}"}]


def product(request, choose=None):
    """The product type row that fits the request best: the chat model's pick (choose(messages) -> index), else the
    words (its name's words count most, then its keywords), or None."""
    if choose:
        try:
            i = int(choose(choose_messages(request)))
            if 0 <= i < len(rows("products.csv")):
                return rows("products.csv")[i]
            if i == -1:
                return None
        except Exception:  # noqa: BLE001  (a chooser that fails: the words decide)
            pass
    want = words(request)
    if not want:
        return None
    best, top = None, 0
    for r in rows("products.csv"):
        name = words(r.get("Product Type"))
        keys = [words(k) for k in str(r.get("Keywords") or "").split(",")]
        score = 3 * sum(1 for w in want if _hit(w, name))
        score += 2 * sum(1 for k in keys if k and all(_hit(x, want) for x in k))
        if score > top:
            best, top = r, score
    return best if top >= 2 else None


def _by_type(name, ptype):
    return next((r for r in rows(name) if (r.get("Product Type") or r.get("UI_Category")) == ptype), {})


def sections(pattern):
    """The landing page pattern's sections, top to bottom ("Hero + Testimonials + CTA" -> its Section Order; a
    product's "Feature-Rich Showcase + Social Proof" -> both patterns' sections, once each)."""
    out = []
    for part in [pattern] + str(pattern or "").split(" + "):
        part = part.strip().lower()
        row = next((r for r in rows("landing.csv") if part and (r["Pattern Name"].lower() == part
                    or part in [a.strip().lower() for a in str(r.get("Aliases") or "").split(",")])), None)
        if row:
            for s in re.split(r"\s*>\s*|\s*\d+\.\s+", row.get("Section Order") or ""):
                s = " ".join(s.split()).strip(" ,.")
                if s and s.lower() not in [x.lower() for x in out]:
                    out.append(s)
            if part == str(pattern or "").strip().lower():
                break
    return out[:10]


STYLE_RX = [("glass", r"glass|aurora|liquid"), ("bold", r"brutal|vibrant|cyber|neon|maximal|bold|block|retro|hud|sci-fi|y2k"),
            ("elegant", r"luxury|elegant|editorial|serif|classic|art deco|vintage"),
            ("playful", r"clay|playful|kawaii|cartoon|organic|biophilic|gen z|soft ui|hand"), ("minimal", r"minimal|swiss|flat|clean|accessible|data-dense")]


def style_of(text):
    """The M42 style (webkit.STYLES) of a style name: the one named first in it."""
    text, found = str(text or "").lower(), []
    for style, rx in STYLE_RX:
        m = re.search(rx, text)
        if m:
            found.append((m.start(), style))
    return min(found)[1] if found else ""


def font_of(row):
    """The M42 font family kind (webkit.FONTS) of a font pairing row."""
    cat, head = str(row.get("Category") or "").lower(), str(row.get("Heading Font") or "")
    if "mono" in cat.split("+")[0] or "tech" in cat or re.search(r"Orbitron|Exo|Russo|Syncopate|Share Tech|Space", head):
        return "tech"
    if cat.startswith(("serif", "display serif", "script")) or re.search(r"Playfair|Cormorant|Garamond|Bodoni|Lora|Cinzel|Crimson|Newsreader", head):
        return "elegant"
    if re.search(r"Fredoka|Nunito|Baloo|Varela|Calistoga|Kalam|Caveat|Amatic|Righteous|rounded", head + cat, re.I):
        return "friendly"
    return "modern"


def fonts(prow):
    """The font pairing that suits the product type (its words against each pairing's "best for" and mood)."""
    want = words(" ".join(str(prow.get(k) or "") for k in ("Product Type", "Keywords", "Primary Style Recommendation", "Color Palette Focus")))
    best, top = None, 0
    for r in rows("typography.csv"):
        pool = words(f'{r.get("Best For")} {r.get("Mood/Style Keywords")}')
        score = sum(1 for w in want if _hit(w, pool))
        if score > top:
            best, top = r, score
    return best


def _lum(hexs):
    h = str(hexs or "").lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return 1.0
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return .2126 * r + .7152 * g + .0722 * b


def advice(request, choose=None):
    """{product, colors (primary, secondary, accent), theme, style, font, fonts, pattern, sections, avoid, why} for the
    request's kind of product, or None when no product type fits."""
    p = product(request, choose)
    if not p:
        return None
    ptype = p["Product Type"]
    col, why = _by_type("colors.csv", ptype), _by_type("ui-reasoning.csv", ptype)
    t = fonts(p) or {}
    hexes = [c for c in (col.get("Primary"), col.get("Secondary"), col.get("Accent")) if re.fullmatch(r"#[0-9a-fA-F]{6}", str(c or ""))]
    style = style_of(p.get("Primary Style Recommendation"))
    return {"product": ptype, "colors": [c.lower() for c in hexes],
            "theme": "dark" if col.get("Background") and _lum(col["Background"]) < .3 else "light",
            "style": style, "font": font_of(t) if t else "", "fonts": f'{t.get("Heading Font")} + {t.get("Body Font")}' if t else "",
            "pattern": p.get("Landing Page Pattern") or "", "sections": sections(p.get("Landing Page Pattern")),
            "avoid": " ".join(str(why.get("Anti_Patterns") or "").split())[:120],
            "why": " ".join(str(p.get("Color Palette Focus") or "").split())[:60]}


GENERIC_KEYS = {"buy", "sell", "shop", "store", "products", "product", "retail", "commerce", "ecommerce", "e", "app", "apps",
                "website", "online", "business", "services", "service", "platform", "tool", "users", "user", "brand"}


def specific(a, request):
    """True when the product type the data matched names the request's own subject (a hotel page: Hotel/Hospitality,
    "hotel" in its name); False for a type that only fits in general (fire crackers: E-commerce, whose words are buy,
    shop, store: its green palette is no firework's)."""
    row = next((r for r in rows("products.csv") if r["Product Type"] == a.get("product")), None)
    if not row:
        return False
    want = words(request)
    own = words(row["Product Type"]) | {w for k in str(row.get("Keywords") or "").split(",") for w in words(k)}
    return any(_hit(w, own - GENERIC_KEYS) for w in want)


COLOUR_RX = re.compile(r"#[0-9a-f]{3,6}\b|\b(blue|navy|indigo|purple|violet|pink|rose|red|maroon|orange|yellow|gold|green|"
                       r"teal|cyan|aqua|brown|black|white|neela\w*|sivapp?u\w*|manjal|pachai)\b", re.I)
THEME_RX = re.compile(r"\b(dark|light|night|white)\b", re.I)
STYLE_WORD_RX = re.compile(r"\b(glass\w*|minimal\w*|bold|elegant|luxury|playful|neon|cyber\w*)\b", re.I)


def apply(spec, request, choose=None):
    """The spec with the product type's look and section order where the user's words name none. Returns
    (spec, advice or None)."""
    a = advice(request, choose)
    if not a or not isinstance(spec, dict):
        return spec, None
    look = dict(spec.get("look") or {})
    # the data's palette and light / dark only for a type that is this subject (2026-11-11: a fire crackers page took
    # E-commerce's green and light: the model's own festive look for its subject was thrown away); else the model's
    # look stays, the data gives its fonts and section order
    a["specific"] = fits = specific(a, request)
    import webkit
    it = webkit.INTENT
    named_col = bool(it.get("named_colours")) if "named_colours" in it else bool(COLOUR_RX.search(request or ""))
    named_theme = bool(it.get("named_theme")) if "named_theme" in it else bool(THEME_RX.search(request or ""))
    named_style = bool(it.get("named_style")) if "named_style" in it else bool(STYLE_WORD_RX.search(request or ""))
    own_colors = len([c for c in look.get("colors") or [] if re.fullmatch(r"#[0-9a-fA-F]{6}", str(c))]) >= 2
    if not named_col and len(a["colors"]) == 3 and (fits or not own_colors):
        look["colors"], look["why"] = a["colors"], f'{a["product"]}: {a["why"]}'
    if not named_theme and (fits or look.get("theme") not in ("light", "dark")):
        look["theme"] = a["theme"]
    if not named_style and (fits or not look.get("style")):
        look.update({k: a[k] for k in ("style", "font") if a[k]})
    spec = dict(spec, look=look, uiux=a)
    if a["sections"] and not spec.get("reference"):
        spec["reference"] = "; ".join(a["sections"])
    return spec, a


def summary(a):
    if not a.get("specific", True):
        return (f'{a["product"]} (only close in general: the page keeps its own colours and light / dark for its subject); '
                f'fonts like {a["fonts"] or "-"}; sections: {" > ".join(a["sections"][:6]) or a["pattern"]}')
    return (f'{a["product"]}: colours {", ".join(a["colors"])}, {a["theme"]}, {a["style"] or "-"} style, fonts like {a["fonts"] or "-"}; '
            f'sections: {" > ".join(a["sections"][:6]) or a["pattern"]}' + (f'; avoid: {a["avoid"]}' if a["avoid"] else ""))
