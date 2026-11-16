"""The icon for any item, by what it is: Bootstrap Icons (bundled, ~2,000) and Lucide (bundled, ISC, ~1,900 icons
with search tags: croissant, sandwich, cake-slice, dumbbell, tractor...). The 4B names icons that don't exist
("bi-bread", "bi-wine" on a bakery page, 2026-11-05: drawn as black dots); M42 picks one from the item's own words,
then from its section's and the site's words (a "Masala Vada" on a bakery page: a bakery icon)."""
import functools
import json
import re
from pathlib import Path

BUNDLED = Path(__file__).resolve().parent / "bundled"
STOP = set("the and with for from your our you are fresh new best daily special specials item items today hot top more "
           "get all one two per each made home page site total".split())


def _stem(w):
    """berries -> berry, boxes -> box, vegetables -> vegetable, class -> class."""
    if len(w) <= 3 or w.endswith(("ss", "us", "is")):
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if re.search(r"(x|ch|sh)es$", w):
        return w[:-2]
    return w[:-1] if w.endswith("s") else w


def _words(text):
    return [_stem(w) for w in re.findall(r"[a-z]{3,}", str(text or "").lower()) if w not in STOP]


@functools.lru_cache(maxsize=None)
def bootstrap():
    css = (BUNDLED / "bootstrap-icons.min.css").read_text(encoding="utf-8", errors="replace")
    return frozenset(re.findall(r"\.(bi-[a-z0-9-]+)::?before", css))


@functools.lru_cache(maxsize=None)
def lucide():
    """{lc-name: its name words and tags (stemmed)} for the bundled Lucide font."""
    try:
        tags = json.loads((BUNDLED / "lucide-tags.json").read_text(encoding="utf-8"))
        css = (BUNDLED / "lucide.css").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return {}
    have = set(re.findall(r"\.(lc-[a-z0-9-]+)::before", css))
    return {f"lc-{n}": frozenset(_words(n.replace("-", " ")) + [w for t in ts for w in _words(t)])
            for n, ts in tags.items() if f"lc-{n}" in have}


def valid(name):
    return name in bootstrap() or name in lucide()


def _score(words, name_words, tag_words):
    s = 0
    for w in words:
        if w in name_words:
            s += 3
        elif w in tag_words:
            s += 2
        elif len(w) >= 5 and any(len(t) >= 5 and (t.startswith(w[:5]) or w.startswith(t[:5])) for t in name_words):
            s += 2  # vegetarian ~ vegetable (the icon's own name)
        elif any(len(t) >= 5 and w.startswith(t) for t in tag_words):
            s += 1.5  # photography ~ photo (a tag)
    return s


@functools.lru_cache(maxsize=4096)
def best(text, context=""):
    """The best icon class for an item's words, else for its context's words; None when nothing fits."""
    for t, need in ((text, 2), (context, 2)):
        words = _words(t)
        if not words:
            continue
        top, pick = 0, None
        for name, ws in lucide().items():
            own = set(_words(name[3:].replace("-", " ")))
            s = _score(words, own, ws)
            if s > top or (s == top and pick and len(name) < len(pick)):
                top, pick = s, name
        for name in bootstrap():
            own = set(_words(name[3:].replace("-", " ")))
            s = _score(words, own, set())
            if s > top:
                top, pick = s, name
        if pick and top >= need:
            return pick
    return None


def fits(name, text):
    """True when the icon has to do with the words (its own name or its tags): a video camera for "NutriTrack recipe"
    does not (2026-11-12: a recipe app's brand drew a camera)."""
    words = _words(text)
    if not name or not words:
        return False
    own = set(_words(str(name)[3:].replace("-", " ")))
    return _score(words, own, lucide().get(name, frozenset())) > 0



def ranked(text, context="", n=4):
    """The n icons whose names and tags hold most of the label's words (then its context's), best first: real icons
    the model chooses from (agent._pick_icons), never a name it makes up."""
    out = []
    for t in (text, context):
        words = _words(t)
        if not words:
            continue
        scored = []
        for name, ws in lucide().items():
            sc = _score(words, set(_words(name[3:].replace("-", " "))), ws)
            if sc > 0:
                scored.append((sc, -len(name), name))
        for name in bootstrap():
            sc = _score(words, set(_words(name[3:].replace("-", " "))), set())
            if sc > 0 and not name.endswith(("-fill", "-circle", "-square")):
                scored.append((sc, -len(name), name))
        for _sc, _l, name in sorted(scored, reverse=True):
            if name not in out:
                out.append(name)
            if len(out) >= n:
                return out
    return out
