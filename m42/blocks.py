"""🧱 Premium blocks: the ready widgets of each section role (sections.RULES), drawn by M42 and filled by the 4B (the user,
2026-11-14: "100-150 ready premium widgets; a hero gets ~20, each section ~20; the 4B only fills them").

Each block declares what it needs (BLOCKS[name]["needs"]: how many items, whether photos are needed), so the 4B picks
only blocks its content fits (no photo layout for a section without photos, no 3-item grid for 8 items). A block is
drawn from the plan's section (title, eyebrow, lead, items: title / text / meta / value / unit / badge / photo / icon).
Its CSS is in bundled/m42-ui.css under ".m42-b-". Built in batches, each looked at before the next:
  batch 1 (2026-11-14): people and proof, rebuilt the same day from the reference pages' compositions (weights.py);
  batch 2: hero and trust; batch 3: offer and why; batch 4: process, showcase, pricing, listings;
  batch 5: schedule, impact, faq, location, action."""
import html as _html
import re

import widgets
from widgets import ic


def e(x):
    return _html.escape(str(x if x is not None else ""), quote=True)


def _pb():
    import pagebuild  # (pagebuild draws pages with these blocks; imported when drawn)
    return pagebuild


def head(sec, center=True):
    return _pb().head(sec, center)


def _items(sec, lo=0, hi=12):
    return [it for it in (sec.get("items") or []) if isinstance(it, dict)][:hi]


def _initials(name):
    w = [x for x in str(name or "").replace(".", " ").split() if x[:1].isalpha()]
    return "".join(x[0] for x in w[:2]).upper() or "•"


def _role(it):
    m = [str(x) for x in it.get("meta") or [] if str(x).strip().lower() != str(it.get("title") or "").strip().lower()]
    return m[0] if m else str(it.get("badge") or "")  # (never the name again: a real build wrote "Priya & Ravi / Priya & Ravi")


def _fact(it):
    m = it.get("meta") or []
    return str(m[1]) if len(m) > 1 else ""


def face(it, cls, k=0):
    """A person's photo, else a premium monogram (their initials on the theme's tint, in the same shape): never an
    empty frame."""
    p = widgets.photo(it, cls)
    if p:
        return p
    return f'<div class="{cls} m42-b-mono" style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)"><span>{e(_initials(it.get("title")))}</span></div>'


def stars(it, n=None):
    v = n if n is not None else it.get("value")
    try:
        r = max(1, min(5, round(float(v or 5))))
    except (TypeError, ValueError):
        r = 5
    return f'<span class="m42-b-stars" aria-label="{r} of 5">{"★" * r}<i>{"★" * (5 - r)}</i></span>'


# ---------------------------------------------------------------------------------------------------- people
# (rebuilt 2026-11-14 from the reference pages' compositions, weights.py: no card grids)
def _sign(it):
    return f'<div class="m42-b-sign"><b>{e(it.get("title"))}</b><span>{e(_role(it))}</span></div>'


def people_photo_band_statement(sec, ctx):
    """Passion Finder: a full-width gradient band, the person standing out of its top on the left, a big statement right."""
    its = _items(sec, hi=1)
    it = its[0] if its else {"title": sec.get("title")}
    facts = "".join(f'<span class="m42-b-band-fact">{e(x)}</span>' for x in (it.get("meta") or [])[:3])
    return (f'<div class="m42-b-band"><div class="m42-b-band-pic">{face(it, "m42-b-band-img")}</div><div class="m42-b-band-words">'
            + (f'<span class="m42-b-band-eye">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
            + f'<h2>{e(sec.get("title"))}</h2><p>{e(it.get("text") or sec.get("lead") or "")}</p>'
            + (f'<div class="m42-b-band-facts">{facts}</div>' if facts else "") + f'{_sign(it)}</div></div>')


def people_reveal_circles(sec, ctx):
    """Passion Finder: a big centred statement fading line by line, round portraits in a row under (the middle one larger)."""
    its = _items(sec, hi=6)
    mid = len(its) // 2
    row = "".join(f'<figure class="m42-b-rc{" is-mid" if k == mid else ""}">{face(it, "m42-b-rc-img", k)}<figcaption><b>{e(it.get("title"))}</b>'
                  f'<span>{e(_role(it))}</span></figcaption></figure>' for k, it in enumerate(its))
    words = (sec.get("lead") or "").strip()
    return (f'<div class="m42-b-reveal">' + (f'<span class="m42-eyebrow">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
            + f'<p class="m42-b-reveal-text"><b>{e(sec.get("title"))}</b> {e(words)}</p><div class="m42-b-rcs">{row}</div></div>')


def people_leader(sec, ctx):
    """One leader's message: an arch portrait on an offset colour block, the words huge in quotes, a signature."""
    its = _items(sec, hi=1)
    it = its[0] if its else {"title": sec.get("title")}
    return (f'<div class="m42-b-leader"><div class="m42-b-leader-pic"><span class="m42-b-leader-block"></span>{face(it, "m42-b-leader-img")}'
            f'<span class="m42-b-leader-tag">{e(_fact(it) or _role(it))}</span></div>'
            f'<div class="m42-b-leader-words">' + (f'<span class="m42-eyebrow">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "")
            + f'<span class="m42-b-leader-q">“</span><blockquote>{e(it.get("text") or sec.get("lead") or "")}</blockquote>{_sign(it)}</div></div>')


def people_spotlight(sec, ctx):
    """One person large with a floating glass card over the photo's edge, the others as a hairline list beside."""
    its = _items(sec, hi=6)
    if not its:
        return head(sec)
    lead, rest = its[0], its[1:]
    side = "".join(f'<li>{face(it, "m42-b-spot-mini", k + 1)}<div><b>{e(it.get("title"))}</b><span>{e(_role(it))}</span></div>'
                   f'<em>{e(_fact(it))}</em></li>' for k, it in enumerate(rest))
    return (head(sec, center=False) + f'<div class="m42-b-pspot"><div class="m42-b-pspot-main">{face(lead, "m42-b-pspot-img")}'
            f'<div class="m42-b-pspot-card"><span class="m42-b-chip">{e(_role(lead))}</span><b>{e(lead.get("title"))}</b><p>{e(lead.get("text"))}</p>'
            + (f'<em>{e(_fact(lead))}</em>' if _fact(lead) else "") + f'</div></div><ul class="m42-b-pspot-list">{side}</ul></div>')


def people_portraits(sec, ctx):
    """Tall arch portraits at staggered heights (a wave), a soft tinted blob behind each, the name under: no card boxes."""
    figs = "".join(f'<figure class="m42-b-arch" style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)"><div class="m42-b-arch-pic">'
                   f'{face(it, "m42-b-arch-img", k)}</div><figcaption><b>{e(it.get("title"))}</b><span>{e(_role(it))}</span>'
                   + (f'<em>{e(_fact(it))}</em>' if _fact(it) else "") + "</figcaption></figure>" for k, it in enumerate(_items(sec, hi=8)))
    return head(sec) + f'<div class="m42-b-arches">{figs}</div>'


# where the floating faces sit round the centred line (left %, top %), like the reference's connected team
_NET = ((5, 14), (89, 10), (1, 60), (92, 56), (20, 84), (75, 86), (27, -2), (66, -4))


def people_overlap(sec, ctx):
    """CoreHR: the big line about the team centred, the people's faces floating round it joined to it by thin curved lines."""
    its = _items(sec, hi=8)
    dots = "".join(f'<span class="m42-b-net-face" style="left:{x}%;top:{y}%;--d:{k * .4}s">{face(it, "m42-b-net-img", k)}</span>'
                   for k, (it, (x, y)) in enumerate(zip(its, _NET)))
    lines = "".join(f'<path d="M50 26 Q {(x + 50) / 2} {(y + 26) / 2 - 8} {x + 3} {y + 6}" />' for x, y in _NET[:len(its)])
    stack = "".join(f'<span style="z-index:{10 - k}">{face(it, "m42-b-ov-img", k)}</span>' for k, it in enumerate(its[:5]))
    return (f'<div class="m42-b-net"><svg class="m42-b-net-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{lines}</svg>{dots}'
            f'<div class="m42-b-net-core"><span class="m42-b-net-hub"><i class="bi bi-people-fill"></i></span>{head(sec)}'
            f'<div class="m42-b-ov-stack">{stack}</div>'
            + (f'<a class="m42-btn" href="#">{e(sec.get("button"))}</a>' if sec.get("button") else "") + "</div></div>")


def people_credentials(sec, ctx):
    """No photos: an editorial register, big serif initials, name and role, the experience large at the right, hairlines."""
    rows = "".join(f'<li><span class="m42-b-cred-mono">{e(_initials(it.get("title")))}</span><div><b>{e(it.get("title"))}</b>'
                   f'<span>{e(_role(it))}</span></div><p>{e(it.get("text"))}</p><strong>{e(_fact(it))}</strong></li>' for it in _items(sec, hi=10))
    return head(sec, center=False) + f'<ol class="m42-b-creds">{rows}</ol>'


# ---------------------------------------------------------------------------------------------------- proof
def _who(it, k=0):
    return (f'<div class="m42-b-who">{face(it, "m42-b-who-img", k)}<div><b>{e(it.get("title") or "Guest")}</b>'
            f'<span>{e(_role(it))}</span></div></div>')


def _cycle_nav(n):
    return (f'<div class="m42-b-cyc-nav"><button type="button" aria-label="Previous" data-m42-cycle="-1"><i class="bi bi-arrow-left"></i></button>'
            f'<span>{n} stories</span><button type="button" aria-label="Next" data-m42-cycle="1"><i class="bi bi-arrow-right"></i></button></div>')


def _pos(k, n):
    """The place of quote k in a fan of n with the first in front: on, next (right), prev (left), or back."""
    return "is-on" if k == 0 else "is-next" if k == 1 else "is-prev" if k == n - 1 else "is-back"


def proof_envelope(sec, ctx):
    """CoreHR: one testimonial rising out of an envelope in the middle, faded tilted cards behind it at both sides."""
    its = _items(sec, hi=6)
    figs = "".join(f'<figure class="m42-b-cyc-it {_pos(k, len(its))}">{stars(it)}<blockquote>{e(it.get("text"))}</blockquote>{_who(it, k)}</figure>'
                   for k, it in enumerate(its))
    return (head(sec) + f'<div class="m42-b-env m42-b-cyc"><div class="m42-b-env-stage">{figs}</div>'
            f'<div class="m42-b-env-pocket" aria-hidden="true"><span></span></div>{_cycle_nav(len(its))}</div>')


def proof_staggered(sec, ctx):
    """BetterVits: quotes at staggered heights like a wave, the face breaking the top edge of each, arrows beside the title."""
    its = _items(sec, hi=6)
    figs = "".join(f'<figure class="m42-b-wave-it" style="--k:{k}">{face(it, "m42-b-wave-img", k)}{stars(it)}<blockquote>{e(it.get("text"))}</blockquote>'
                   f'<b>{e(it.get("title"))}</b><span>{e(_role(it))}</span></figure>' for k, it in enumerate(its))
    return (f'<div class="m42-b-wavehead">{head(sec, center=False)}<a class="m42-b-viewall" href="#">View all <i class="bi bi-arrow-right"></i></a></div>'
            f'<div class="m42-b-wave">{figs}</div>')


def proof_cards_readmore(sec, ctx):
    """Finix: three quotes in a row, a wide bar under them with a stack of faces and 'Read more stories'."""
    its = _items(sec, hi=6)
    figs = "".join(f'<figure class="m42-b-crm-it"><span class="m42-b-crm-q">“</span><blockquote>{e(it.get("text"))}</blockquote>{_who(it, k)}</figure>'
                   for k, it in enumerate(its[:3]))
    stack = "".join(f'<span style="z-index:{10 - k}">{face(it, "m42-b-ov-img", k)}</span>' for k, it in enumerate(its))
    return (head(sec) + f'<div class="m42-b-crm">{figs}</div><a class="m42-b-crm-bar" href="#"><div class="m42-b-ov-stack">{stack}</div>'
            f'<b>Read more stories</b><span class="m42-b-crm-go"><i class="bi bi-arrow-up-right"></i></span></a>')


def proof_wall(sec, ctx):
    """Wello: a masonry wall of quotes, every few one filled with the accent and its words larger."""
    figs = "".join(f'<figure class="m42-b-wall-it{" is-big" if k % 4 == 0 else ""}">{stars(it)}<blockquote>{e(it.get("text"))}</blockquote>{_who(it, k)}</figure>'
                   for k, it in enumerate(_items(sec, hi=9)))
    return head(sec) + f'<div class="m42-b-wall">{figs}</div>'


def proof_rating(sec, ctx):
    """The overall rating huge (a display figure), the spread of stars under it, the quotes as hairline rows beside."""
    its = _items(sec, hi=4)
    vals = [float(it.get("value")) for it in its if str(it.get("value") or "").replace(".", "", 1).isdigit()] or [5.0]
    avg = round(sum(vals) / len(vals), 1)
    count = sec.get("count") or (len(its) * 37 + 120)
    bars = "".join(f'<li><span>{s}★</span><i style="--w:{w}%"></i></li>' for s, w in ((5, 82), (4, 13), (3, 3), (2, 1), (1, 1)))
    rows = "".join(f'<figure class="m42-b-rq">{stars(it)}<blockquote>{e(it.get("text"))}</blockquote>{_who(it, k)}</figure>' for k, it in enumerate(its[:3]))
    return (f'<div class="m42-b-rating"><div class="m42-b-rating-score">{head(sec, center=False)}<strong>{avg}</strong>{stars({}, avg)}'
            f'<span>from {e(count)} reviews</span><ul class="m42-b-bars">{bars}</ul></div><div class="m42-b-rqs">{rows}</div></div>')


_RES_ICONS = ("bi-trophy-fill", "bi-graph-up-arrow", "bi-people-fill", "bi-patch-check-fill", "bi-lightning-charge-fill", "bi-heart-fill")


def proof_results(sec, ctx):
    """Wello: huge figures in rows, a glossy icon tile left of each and the meaning on the right, hairlines between."""
    rows = "".join(f'<li style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)"><span class="m42-b-res-tile"><i class="bi {ic(it.get("icon"), _RES_ICONS[k % 6])}"></i></span>'
                   f'<strong>{e(it.get("badge") or it.get("value") or "")}<small>{e(it.get("unit") or "")}</small></strong>'
                   f'<div><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p><span>{e(_role(it))}</span></div></li>' for k, it in enumerate(_figs(sec, 6)))
    return head(sec, center=False) + f'<ol class="m42-b-results">{rows}</ol>'


def proof_bigquote(sec, ctx):
    """One quote huge across the accent band with its face, the others small in a column at the side."""
    its = _items(sec, hi=4)
    if not its:
        return head(sec)
    top, rest = its[0], its[1:]
    small = "".join(f'<figure class="m42-b-bqs">{stars(it)}<blockquote>{e(it.get("text"))}</blockquote>{_who(it, k + 1)}</figure>' for k, it in enumerate(rest))
    return (head(sec) + f'<div class="m42-b-bq"><figure class="m42-b-bq-main"><span class="m42-b-bq-mark">“</span><blockquote>{e(top.get("text"))}</blockquote>'
            f'{stars(top)}{_who(top)}</figure><div class="m42-b-bq-side">{small}</div></div>')


# ------------------------------------------------------------------------------------- shared pieces (batch 2 on)
def pic(src, cls, alt=""):
    """A downloaded photo by its path (images/<name>.jpg), or ""."""
    return widgets.photo({"photo": src, "title": alt}, cls)


def _pics(sec):
    """The section's own pictures in order: its photo, its photos, its items' photos (no repeats)."""
    out = []
    for s in [sec.get("photo")] + list(sec.get("photos") or []) + [it.get("photo") for it in _items(sec, hi=99)]:
        if s and s not in out and pic(s, ""):
            out.append(s)
    return out


def acts(sec, ghost=True):
    a = f'<a class="m42-btn" href="#">{e(sec.get("button"))} <i class="bi bi-arrow-right"></i></a>' if sec.get("button") else ""
    b = f'<a class="m42-btn-ghost" href="#">{e(sec.get("button2"))}</a>' if ghost and sec.get("button2") else ""
    return f'<div class="m42-b-acts">{a}{b}</div>' if a or b else ""


def brow(sec, cls="m42-eyebrow"):
    return f'<span class="{cls}">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else ""


def lead(sec, cls="m42-b-lead"):
    return f'<p class="{cls}">{e(sec.get("lead"))}</p>' if sec.get("lead") else ""


def _figure(it):
    """An item's number as written: its badge ("500+"), else its value with its unit."""
    if it.get("badge"):
        return str(it["badge"]) + (str(it.get("unit") or "") if str(it.get("unit") or "") in ("%", "★", "+", "x", "X", "k", "K") else "")
    v = it.get("value")
    u = str(it.get("unit") or "")
    return "" if v in (None, "") else f'{v}{" " if len(u) > 1 and u[:1].isalpha() else ""}{u}'  # ("12 Years", not "12Years")


def money(it):
    """An item's price: its unit as a currency sign before the grouped value, or ""."""
    v = it.get("value")
    if v in (None, ""):
        return ""
    try:
        f = float(v)
        s = f"{f:,.0f}" if f == int(f) else f"{f:,.2f}"
    except (TypeError, ValueError):
        s = str(v)
    u = str(it.get("unit") or "")
    return e(u + s if len(u) <= 1 or u.upper() in ("RS", "RS.", "INR", "USD", "EUR") else f"{s} {u}")


def hstats(sec, n=3, cls=""):
    its = [it for it in _items(sec, hi=n) if _figure(it)]
    if not its:
        return ""
    return (f'<div class="m42-b-hstats {cls}">' + "".join(f'<div><strong>{e(_figure(it))}</strong><span>{e(it.get("title"))}</span></div>' for it in its)
            + "</div>")


def accent(title, n=2):
    """A headline with its first n words marked (the reference's coloured opening words)."""
    w = str(title or "").split()
    return f'<em>{e(" ".join(w[:n]))}</em> {e(" ".join(w[n:]))}' if len(w) > n else e(title)


def mix(title):
    """A headline of two voices: its first half plain, the rest marked (bold sans + light serif italic)."""
    w = str(title or "").split()
    h = (len(w) + 1) // 2
    return f'{e(" ".join(w[:h]))} <em>{e(" ".join(w[h:]))}</em>' if len(w) > 2 else e(title)


def mockdash(sec):
    """A small picture of the business in numbers (a section with no photo): its figures as tiles over a bar chart."""
    its = [it for it in _items(sec, hi=3) if _figure(it)]
    tiles = "".join(f'<div><small>{e(it.get("title"))}</small><b>{e(_figure(it))}</b></div>' for it in its)
    bars = "".join(f'<i style="--h:{h}%"></i>' for h in (38, 62, 45, 80, 56, 92, 70, 48, 84, 64, 76, 58))
    return f'<div class="m42-b-dash"><div class="m42-b-dash-tiles">{tiles}</div><div class="m42-b-dash-bars">{bars}</div></div>'


def frame(sec, src=None):
    """The thing shown in a window frame: its photo, else its numbers as a small dashboard."""
    inner = pic(src, "m42-b-frame-img", sec.get("title")) if src else mockdash(sec)
    return (f'<div class="m42-b-frame"><div class="m42-b-frame-bar"><i></i><i></i><i></i><span>{e(sec.get("brand") or "")}</span></div>{inner}</div>')


def orb(sec, src=None, icon="bi-globe2"):
    """One big round object: the photo as a glossy sphere, else a globe of the theme's colours."""
    inner = pic(src, "m42-b-orb-img", sec.get("title")) if src else f'<span class="m42-b-orb-globe"><i class="bi {ic(sec.get("icon"), icon)}"></i></span>'
    return f'<div class="m42-b-orb">{inner}<span class="m42-b-orb-ring"></span><span class="m42-b-orb-shade"></span></div>'


def ring(text):
    """A rotating circular badge: the words round a circle, a star in the middle."""
    t = e((str(text or "") + " • ") * 3)
    return ('<span class="m42-b-ringbadge" aria-hidden="true"><svg viewBox="0 0 120 120"><defs><path id="m42bring" d="M60 60 m-46 0 a46 46 0 1 1 92 0 a46 46 0 1 1 -92 0"/></defs>'
            f'<text><textPath href="#m42bring" textLength="285">{t}</textPath></text></svg><i class="bi bi-stars"></i></span>')


_ARROW = ('<svg class="m42-b-doodle-arrow" viewBox="0 0 120 70" aria-hidden="true"><path d="M4 12 C 30 60, 70 62, 104 34" /><path d="M88 30 L106 33 L98 50" /></svg>')


# ---------------------------------------------------------------------------------------------------- hero
# (each draws the whole first screen: its own stage and container; the nav sits over it)
def _words(sec, h="h1", title=None, ghost=True):
    return f'{brow(sec)}<{h}>{title if title is not None else e(sec.get("title"))}</{h}>{lead(sec)}{acts(sec, ghost)}'


def hero_spotlight_mockup(sec, ctx):
    """Resq: a dark stage, a light beam from one corner, the headline and two actions centred, the product rising from the bottom."""
    ps = _pics(sec)
    return (f'<div class="m42-b-hero m42-b-h-spot"><span class="m42-b-h-beam"></span><span class="m42-b-h-stars"></span><div class="container">'
            f'{_words(sec, title=accent(sec.get("title")))}<div class="m42-b-h-rise">{frame(sec, ps[0] if ps else None)}</div></div></div>')


def hero_faces_sides(sec, ctx):
    """Passion Finder: a warm blurred gradient band, a picture at each edge, the headline centred between them; a quiet strip under."""
    ps = (_pics(sec) + ["", ""])[:2]
    under = (f'<div class="m42-b-h-under"><div class="container"><b>{e(sec.get("eyebrow") or sec.get("brand") or "")}</b>{hstats(sec)}</div></div>'
             if hstats(sec) else "")
    return (f'<div class="m42-b-hero m42-b-h-faces">{pic(ps[0], "m42-b-h-face is-l")}{pic(ps[1], "m42-b-h-face is-r")}<div class="container">'
            + (f'<span class="m42-b-h-brand">{e(sec.get("brand"))}</span>' if sec.get("brand") else "")
            + f'<h1>{e(sec.get("title"))}</h1>{lead(sec)}{acts(sec)}</div></div>{under}')


def hero_pedestal(sec, ctx):
    """BetterVits: the products standing on soft pedestals on a pastel floor, the headline left; a thin promise strip under."""
    ps = _pics(sec)[:3]
    peds = "".join(f'<div class="m42-b-ped is-{k}">{pic(s, "m42-b-ped-img")}<span class="m42-b-ped-base"></span></div>' for k, s in enumerate(ps))
    strip = sec.get("badge") or ""
    return (f'<div class="m42-b-hero m42-b-h-ped"><div class="container m42-b-h-2col"><div class="m42-b-h-words">{_words(sec)}</div>'
            f'<div class="m42-b-peds">{peds}<span class="m42-b-ped-floor"></span></div></div>'
            + (f'<div class="m42-b-h-strip"><i class="bi bi-patch-check-fill"></i> {e(strip)}</div>' if strip else "") + "</div>")


def hero_doodle_block(sec, ctx):
    """ProFinance: a bright colour block holding the headline, a hand-drawn arrow to the action; pictures overlap its right edge."""
    ps = _pics(sec)[:2]
    cards = "".join(pic(s, f"m42-b-h-tilt is-{k}") for k, s in enumerate(ps))
    return (f'<div class="m42-b-hero m42-b-h-doodle"><div class="container"><div class="m42-b-h-block"><div class="m42-b-h-words">{brow(sec)}'
            f'<h1>{e(sec.get("title"))}</h1>{lead(sec)}<div class="m42-b-h-point">{acts(sec, ghost=False)}{_ARROW}</div></div>'
            f'<div class="m42-b-h-cards">{cards}</div><span class="m42-b-h-blob"></span></div>{hstats(sec)}</div></div>')


_HNET = ((8, 18), (86, 12), (22, 62), (74, 66), (36, 4), (62, 0), (2, 70), (94, 58))
_HICONS = ("bi-lightning-charge-fill", "bi-heart-fill", "bi-star-fill", "bi-shield-check", "bi-chat-heart-fill", "bi-gem", "bi-calendar2-check-fill", "bi-award-fill")


def hero_network(sec, ctx):
    """CoreHR: the headline centred, avatars and icon tiles floating above it joined by thin lines to a central icon."""
    ps, its = _pics(sec), _items(sec, hi=8)
    nodes = []
    for k, (x, y) in enumerate(_HNET[:6]):
        if k % 2 == 0 and k // 2 < len(ps):
            body = pic(ps[k // 2], "m42-b-hn-img")
        else:
            it = its[k % len(its)] if its else {}
            body = (f'<span class="m42-b-hn-tile" style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)"><i class="bi {ic(it.get("icon"), _HICONS[k])}"></i></span>')
        nodes.append(f'<span class="m42-b-hn" style="left:{x}%;top:{y}%;--d:{k * .5}s">{body}</span>')
    lines = "".join(f'<path d="M50 52 Q {(x + 50) / 2} {y + 4} {x + 4} {y + 14}" />' for x, y in _HNET[:6])
    return (f'<div class="m42-b-hero m42-b-h-net"><div class="container"><div class="m42-b-hn-stage"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            f'{lines}</svg>{"".join(nodes)}<span class="m42-b-hn-hub"><i class="bi {ic(sec.get("icon"), "bi-check2-circle")}"></i></span></div>'
            f'<h1>{e(sec.get("title"))}</h1>{lead(sec)}{acts(sec)}</div></div>')


def hero_globe_type(sec, ctx):
    """Finix: one big round object on one side, a huge headline on the other mixing bold sans and light serif italic words."""
    ps = _pics(sec)
    return (f'<div class="m42-b-hero m42-b-h-globe"><div class="container m42-b-h-2col"><div class="m42-b-h-obj">{orb(sec, ps[0] if ps else None)}</div>'
            f'<div class="m42-b-h-words">{_words(sec, title=mix(sec.get("title")))}{hstats(sec)}</div></div></div>')


def hero_poster(sec, ctx):
    """Fruit poster: the whole hero one strong colour, a huge uppercase headline, the product in front of it, a rotating badge,
    a small glass card, a dark curved band at the bottom."""
    ps, its = _pics(sec), [it for it in _items(sec, hi=1) if _figure(it)]
    prod = pic(ps[0], "m42-b-h-prod-img", sec.get("title")) if ps else orb(sec)
    glass = (f'<div class="m42-b-h-glass"><strong>{e(_figure(its[0]))}</strong><span>{e(its[0].get("title"))}</span></div>' if its else "")
    return (f'<div class="m42-b-hero m42-b-h-poster"><div class="container"><h1>{e(sec.get("title"))}</h1><div class="m42-b-h-prod">{prod}'
            f'{ring(sec.get("badge") or sec.get("eyebrow") or sec.get("brand"))}{glass}</div><div class="m42-b-h-side">{lead(sec)}{acts(sec, ghost=False)}</div>'
            f'</div><span class="m42-b-h-curve"></span></div>')


def hero_giant_overlap(sec, ctx):
    """Energy drink: a giant headline across the width, the product held in front of the words, a short line and the action at the right."""
    ps = _pics(sec)
    t = str(sec.get("title") or "")
    prod = pic(ps[0], "m42-b-h-pill-img", t) if ps else orb(sec)
    return (f'<div class="m42-b-hero m42-b-h-giant"><div class="container">{brow(sec)}<h1 style="--n:{max(10, len(t) // 2 + 2)}">{e(t)}</h1>'
            f'<div class="m42-b-h-pill">{prod}</div><div class="m42-b-h-foot">{hstats(sec, 2)}<div class="m42-b-h-side">{lead(sec)}{acts(sec, ghost=False)}</div></div></div></div>')


def hero_colour_panel(sec, ctx):
    """Security camera: a dark side with a thin + bold italic headline, a tall colour panel holding the product spilling out of
    its top, the numbers on the panel, a light card across the bottom edge."""
    ps, its = _pics(sec), [it for it in _items(sec, hi=3) if _figure(it)]
    prod = pic(ps[0], "m42-b-h-panel-img", sec.get("title")) if ps else orb(sec)
    nums = "".join(f'<div><strong>{e(_figure(it))}</strong><span>{e(it.get("title"))}</span></div>' for it in its[:2])
    card = (f'<a class="m42-b-h-card" href="#">{pic(ps[1], "m42-b-h-card-img") if len(ps) > 1 else ""}<div><b>{e(its[-1].get("title") if its else sec.get("brand"))}</b>'
            f'<span>{e((its[-1].get("text") if its else "") or sec.get("badge") or "")}</span></div><i class="bi bi-arrow-up-right"></i></a>')
    return (f'<div class="m42-b-hero m42-b-h-panel"><div class="container m42-b-h-2col"><div class="m42-b-h-words">{_words(sec, title=mix(sec.get("title")))}</div>'
            f'<div class="m42-b-h-tall">{prod}<div class="m42-b-h-nums">{nums}</div></div>{card}</div></div>')


def hero_showroom(sec, ctx):
    """Tea brand: a huge serif headline, the product large over its corner, leaves floating, the words and actions in a narrow column."""
    ps = _pics(sec)
    prod = pic(ps[0], "m42-b-h-show-img", sec.get("title")) if ps else orb(sec)
    leaves = "".join(f'<span class="m42-b-leaf is-{k}"></span>' for k in range(5))
    return (f'<div class="m42-b-hero m42-b-h-show"><div class="container">{brow(sec)}<h1>{mix(sec.get("title"))}</h1>'
            f'<div class="m42-b-h-showpic">{prod}{leaves}</div><div class="m42-b-h-col">{lead(sec)}{acts(sec)}{hstats(sec, 2)}</div></div></div>')


# ---------------------------------------------------------------------------------------------------- trust
_LOGO_ICONS = ("bi-hexagon-fill", "bi-triangle-fill", "bi-circle-half", "bi-diamond-fill", "bi-octagon-fill", "bi-asterisk")


def _logo(it, k):
    return f'<span class="m42-b-logo"><i class="bi {ic(it.get("icon"), _LOGO_ICONS[k % 6])}"></i>{e(it.get("title"))}</span>'


def trust_logo_dark(sec, ctx):
    """Resq: a quiet row of partner / client names right under the hero, one line before it."""
    row = "".join(_logo(it, k) for k, it in enumerate(_items(sec, hi=7)))
    return (f'<div class="m42-b-logos">' + (f'<span class="m42-b-logos-line">{e(sec.get("title"))}</span>' if sec.get("title") else "")
            + f'<div class="m42-b-logos-row">{row}</div></div>')


def trust_logo_circles(sec, ctx):
    """ProFinance: the names in soft circles in one row, a centred title and line above."""
    row = "".join(f'<figure class="m42-b-lc" style="--k:{k}"><span><i class="bi {ic(it.get("icon"), _LOGO_ICONS[k % 6])}"></i></span>'
                  f'<figcaption>{e(it.get("title"))}</figcaption></figure>' for k, it in enumerate(_items(sec, hi=8)))
    return head(sec) + f'<div class="m42-b-lcs">{row}</div>'


def trust_cause_strip(sec, ctx):
    """BetterVits: a thin full-width strip in the deep colour with one line of promise, moving slowly."""
    words = [sec.get("title")] + [it.get("title") for it in _items(sec, hi=6)]
    one = "".join(f'<span><i class="bi bi-stars"></i>{e(x)}</span>' for x in words if x)
    return f'<div class="m42-b-strip"><div class="m42-b-strip-track">{one}{one}</div></div>'


def trust_huge_numbers(sec, ctx):
    """Wello: huge numbers, a glossy icon tile at the corner of each, the meaning under; hairlines between (no boxes)."""
    cells = "".join(f'<div class="m42-b-hn-cell" style="--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)"><span class="m42-b-res-tile"><i class="bi '
                    f'{ic(it.get("icon"), _RES_ICONS[k % 6])}"></i></span><strong>{e(_figure(it))}</strong><b>{e(it.get("title"))}</b>'
                    f'<p>{e(it.get("text"))}</p></div>' for k, it in enumerate(_figs(sec, 4)))
    return head(sec, center=False) + f'<div class="m42-b-hnums">{cells}</div>'


def trust_statement_quote(sec, ctx):
    """Passion Finder: a big plain statement on the left half, a short quote with its author on the right half."""
    its = _items(sec, hi=1)
    it = its[0] if its else {}
    q = it.get("text") or sec.get("lead") or ""
    return (f'<div class="m42-b-sq"><div>{brow(sec)}<h2>{e(sec.get("title"))}</h2></div><figure><blockquote>{e(q)}</blockquote>'
            + (f'<figcaption>{e(it.get("title"))}' + (f' · {e(_role(it))}' if _role(it) else "") + "</figcaption>" if it.get("title") else "") + "</figure></div>")


# ---------------------------------------------------------------------------------------------------- offer
def _t(k):
    """The k-th tint of the theme (its three accents in turn), as a style."""
    return f'--t:var(--m42-accent{["", "-2", "-3"][k % 3]}-rgb)'


_OFFER_ICONS = ("bi-gem", "bi-stars", "bi-flower1", "bi-lightning-charge", "bi-heart", "bi-award", "bi-magic", "bi-box-seam")


def _thing(it, cls, k=0):
    """An item's picture: its photo, else its icon large on its tint (never an empty frame)."""
    p = widgets.photo(it, cls)
    return p or f'<div class="{cls} m42-b-art" style="{_t(k)}"><i class="bi {ic(it.get("icon"), _OFFER_ICONS[k % 8])}"></i></div>'


def _price(it):
    return f'<span class="m42-b-price">{money(it)}</span>' if money(it) else ""


def offer_pedestal_carousel(sec, ctx):
    """BetterVits: the things on tinted square backgrounds with soft shadows, names and prices under, arrows at the sides."""
    figs = "".join(f'<figure class="m42-b-pc-it" style="{_t(k)}"><div class="m42-b-pc-tint">{_thing(it, "m42-b-pc-img", k)}'
                   + (f'<span class="m42-b-chip">{e(it.get("badge"))}</span>' if it.get("badge") else "")
                   + f'</div><figcaption><b>{e(it.get("title"))}</b>{_price(it)}</figcaption></figure>' for k, it in enumerate(_items(sec, hi=8)))
    return (f'<div data-m42-carousel><div class="m42-b-wavehead">{head(sec, center=False)}<div class="m42-b-cyc-nav"><button type="button" data-car="-1" '
            f'aria-label="Previous"><i class="bi bi-arrow-left"></i></button><button type="button" data-car="1" aria-label="Next"><i class="bi bi-arrow-right"></i>'
            f'</button></div></div><div class="m42-b-pc m42-car-track">{figs}</div></div>')


def offer_bento_mockups(sec, ctx):
    """Resq: an asymmetric bento: one accent tile with the main line, one wide tile with a picture, smaller tiles with one thing each."""
    its, ps = _items(sec, hi=6), _pics(sec)
    wide = pic(ps[0], "m42-b-bento-img", sec.get("title")) if ps else mockdash({"items": its})
    small = "".join(f'<div class="m42-b-bento-s" style="{_t(k)}"><span class="m42-b-bento-ic"><i class="bi {ic(it.get("icon"), _OFFER_ICONS[k % 8])}"></i></span>'
                    f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>{_price(it)}</div>' for k, it in enumerate(its))
    return (f'<div class="m42-b-bento"><div class="m42-b-bento-main">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}<span class="m42-b-h-stars"></span></div>'
            f'<div class="m42-b-bento-wide">{wide}</div>{small}</div>')


def offer_stair_tiles(sec, ctx):
    """Wello: three colourful tiles numbered 01 02 03 standing at stepped heights (a staircase), a big icon on each."""
    tiles = "".join(f'<div class="m42-b-stair is-{k}" style="{_t(k)}"><span class="m42-b-stair-n">{k + 1:02d}</span><i class="bi {ic(it.get("icon"), _OFFER_ICONS[k % 8])}"></i>'
                    f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>{_price(it)}</div>' for k, it in enumerate(_items(sec, hi=3)))
    return head(sec) + f'<div class="m42-b-stairs">{tiles}</div>'


def _minichart(k):
    """A small live picture for a thing without a photo: a chart drawn from the theme (a line, bars, a ring in turn)."""
    if k % 3 == 0:
        return ('<svg class="m42-b-mini" viewBox="0 0 200 90" preserveAspectRatio="none" aria-hidden="true"><path class="is-fill" d="M0 70 C 30 60, 45 30, 75 42 S 120 70, 145 34 S 185 14, 200 20 V90 H0 Z" />'
                '<path d="M0 70 C 30 60, 45 30, 75 42 S 120 70, 145 34 S 185 14, 200 20" /></svg>')
    if k % 3 == 1:
        return '<div class="m42-b-mini is-bars">' + "".join(f'<i style="--h:{h}%"></i>' for h in (40, 64, 52, 86, 60, 96, 72)) + "</div>"
    return '<div class="m42-b-mini is-ring"><span></span><b>86%</b></div>'


def offer_mockup_cards(sec, ctx):
    """Finix / CoreHR: cards each holding a small live picture of the thing (its photo, else a chart) above its name and line."""
    cards = "".join(f'<article class="m42-b-mk" style="{_t(k)}"><div class="m42-b-mk-pic">{widgets.photo(it, "m42-b-mk-img") or _minichart(k)}</div>'
                    f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>{_price(it)}</article>' for k, it in enumerate(_items(sec, hi=6)))
    return head(sec) + f'<div class="m42-b-mks">{cards}</div>'


def offer_shape_cards(sec, ctx):
    """ProFinance: wide cards, each with an abstract shape (a blob, a ring) at its right edge, a title, line and 'Read more'."""
    cards = "".join(f'<a class="m42-b-shape is-{k % 4}" href="#" style="{_t(k)}"><span class="m42-b-shape-fig"><i class="bi {ic(it.get("icon"), _OFFER_ICONS[k % 8])}"></i></span>'
                    f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p><span class="m42-b-more">{money(it) or "Read more"} <i class="bi bi-arrow-right"></i></span></a>'
                    for k, it in enumerate(_items(sec, hi=4)))
    return head(sec, center=False) + f'<div class="m42-b-shapes">{cards}</div>'


def offer_stage_rows(sec, ctx):
    """Tea brand: each thing on a soft half-circle with its round photo, its name big beside it, the price under; rows change sides."""
    rows = "".join(f'<div class="m42-b-stage{" is-rev" if k % 2 else ""}" style="{_t(k)}"><div class="m42-b-stage-pic">{_thing(it, "m42-b-stage-img", k)}</div>'
                   f'<div class="m42-b-stage-words"><span class="m42-b-stage-n">{k + 1:02d}</span><h3>{e(it.get("title"))}</h3><p>{e(it.get("text"))}</p>{_price(it)}</div></div>'
                   for k, it in enumerate(_items(sec, hi=4)))
    return head(sec) + f'<div class="m42-b-stages">{rows}</div>'


def offer_ingredient_mosaic(sec, ctx):
    """BetterVits: a mosaic of soft tiles of different sizes, each a picture of one part with its name."""
    tiles = "".join(f'<figure class="m42-b-mo is-{k % 8}" style="{_t(k)}">{_thing(it, "m42-b-mo-img", k)}<figcaption><b>{e(it.get("title"))}</b>'
                    + (f'<span>{e(it.get("text"))}</span>' if k % 8 in (0, 3) and it.get("text") else "") + "</figcaption></figure>" for k, it in enumerate(_items(sec, hi=8)))
    return head(sec) + f'<div class="m42-b-mosaic">{tiles}</div>'


def offer_list_menu(sec, ctx):
    """An editorial price list in two columns: name ...... price, one line under."""
    rows = "".join(f'<li><div><b>{e(it.get("title"))}</b>' + (f'<em>{e(it.get("badge"))}</em>' if it.get("badge") else "")
                   + f'<i></i>{_price(it)}</div><p>{e(it.get("text"))}</p></li>' for it in _items(sec, hi=16))
    return head(sec) + f'<ul class="m42-b-menu">{rows}</ul>'


# ---------------------------------------------------------------------------------------------------- why
_WHY_ICONS = ("bi-shield-check", "bi-lightning-charge", "bi-heart", "bi-award", "bi-people", "bi-clock-history")


def _wic(it, k):
    return f'<i class="bi {ic(it.get("icon"), _WHY_ICONS[k % 6])}"></i>'


def _point(it, k, cls):
    return f'<div class="{cls}" style="{_t(k)}"><span>{_wic(it, k)}</span><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>'


def why_hub_spokes(sec, ctx):
    """Resq: a glowing central icon tile, the reasons as small boxes at its left and right joined to it by circuit-like lines."""
    its = _items(sec, hi=4)
    left = "".join(_point(it, k, "m42-b-spoke") for k, it in enumerate(its) if k % 2 == 0)
    right = "".join(_point(it, k, "m42-b-spoke") for k, it in enumerate(its) if k % 2 == 1)
    wires = ('<svg class="m42-b-wires" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M0 22 H30 V50 H50" /><path d="M0 78 H30 V50" />'
             '<path d="M100 22 H70 V50 H50" /><path d="M100 78 H70 V50" /></svg>')
    return (head(sec) + f'<div class="m42-b-hub"><div class="m42-b-hub-side">{left}</div><div class="m42-b-hub-mid">{wires}<span class="m42-b-hub-core">'
            f'<i class="bi {ic(sec.get("icon"), "bi-stars")}"></i></span></div><div class="m42-b-hub-side">{right}</div></div>')


def _ncard(it, k):
    return f'<div class="m42-b-orbit-card" style="{_t(k)}"><span>{k + 1:02d}</span><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>'


def why_orbit_object(sec, ctx):
    """AIAF: one big object / photo in the middle, numbered glass cards at both sides (01 03 left, 02 04 right), the title beside."""
    its, ps = _items(sec, hi=4), _pics(sec)
    left = "".join(_ncard(it, k) for k, it in enumerate(its) if k % 2 == 0)
    right = "".join(_ncard(it, k) for k, it in enumerate(its) if k % 2 == 1)
    return (f'<div class="m42-b-orbit"><div class="m42-b-orbit-side">{left}</div><div class="m42-b-orbit-mid">{orb(sec, ps[0] if ps else None, "bi-stars")}</div>'
            f'<div class="m42-b-orbit-side is-r"><div class="m42-b-orbit-head">{brow(sec)}<h2>{e(sec.get("title"))}</h2></div>{right}</div></div>')


_TILT = (-7, 5, -3, 8, -5, 4)


def why_floating_tiles(sec, ctx):
    """Resq: tiles scattered at slight angles like cards dropped on a table, an icon and a short line on each, one in the accent."""
    tiles = "".join(f'<div class="m42-b-ft{" is-accent" if k == 1 else ""}" style="--r:{_TILT[k % 6]}deg;--y:{(0, 28, -10, 34, 6, 22)[k % 6]}px;{_t(k)}">'
                    f'<span>{_wic(it, k)}</span><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>' for k, it in enumerate(_items(sec, hi=6)))
    return head(sec) + f'<div class="m42-b-fts">{tiles}</div>'


def _art(sec, cls):
    ps = _pics(sec)
    return pic(ps[0], cls, sec.get("title")) if ps else f'<div class="{cls} m42-b-art"><i class="bi {ic(sec.get("icon"), "bi-stars")}"></i></div>'


def why_curved_photo_icons(sec, ctx):
    """BetterVits: a grid of small icons with a title and line each, a photo in a curved corner shape at the bottom right."""
    pts = "".join(_point(it, k, "m42-b-cp") for k, it in enumerate(_items(sec, hi=6)))
    return (f'<div class="m42-b-curve"><div class="m42-b-curve-words">{head(sec, center=False)}<div class="m42-b-cps">{pts}</div></div>'
            f'<div class="m42-b-curve-pic">{_art(sec, "m42-b-curve-img")}</div></div>')


def why_title_left_grid(sec, ctx):
    """ProFinance: the title and a line in a left column, a 2x2 grid of icon points on the right, each with a small pill."""
    pts = "".join(f'<div class="m42-b-tl" style="{_t(k)}"><span class="m42-b-tl-ic">{_wic(it, k)}</span><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>'
                  + (f'<span class="m42-b-tl-pill">{e(it.get("badge"))}</span>' if it.get("badge") else "") + "</div>" for k, it in enumerate(_items(sec, hi=4)))
    return (f'<div class="m42-b-tlg"><div class="m42-b-tlg-head">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}{acts(sec, ghost=False)}</div>'
            f'<div class="m42-b-tls">{pts}</div></div>')


def why_inline_icon_statement(sec, ctx):
    """Wello: one huge paragraph across the page with small icon stickers set inside the sentence between its words."""
    nt = len(str(sec.get("title") or "").split())
    words = (str(sec.get("title") or "") + " " + str(sec.get("lead") or "")).split()
    its = _items(sec, hi=6)
    icons = [ic(it.get("icon"), _WHY_ICONS[k % 6]) for k, it in enumerate(its)] or list(_WHY_ICONS[:4])
    step = max(3, len(words) // (len(icons) + 1))
    out, n = [], 0
    for k, w in enumerate(words):
        out.append(f"<b>{e(w)}</b>" if k < nt else e(w))
        if (k + 1) % step == 0 and n < len(icons) and k < len(words) - 1:
            out.append(f'<span class="m42-b-inl" style="{_t(n)};--r:{_TILT[n % 6]}deg"><i class="bi {icons[n]}"></i></span>')
            n += 1
    return f'<div class="m42-b-inline">{brow(sec)}<p class="m42-b-inline-text">{" ".join(out)}</p>{acts(sec, ghost=False)}</div>'


def why_watermark(sec, ctx):
    """Energy drink: a huge faded word behind, a photo, the reasons as a numbered list 001-004 with hairlines."""
    word = (str(sec.get("eyebrow") or sec.get("title") or "WHY").split() or ["WHY"])[0]
    rows = "".join(f'<li><span>{k + 1:03d}</span><div><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>{_wic(it, k)}</li>'
                   for k, it in enumerate(_items(sec, hi=6)))
    return (f'<div class="m42-b-wm"><span class="m42-b-wm-word" aria-hidden="true">{e(word)}</span><div class="m42-b-wm-pic">{_art(sec, "m42-b-wm-img")}</div>'
            f'<div class="m42-b-wm-words">{head(sec, center=False)}<ol class="m42-b-wm-list">{rows}</ol></div></div>')


def why_word_sticker(sec, ctx):
    """Wello: one big line centred with a small tilted sticker beside it, the points under in a row with hairlines."""
    pts = "".join(_point(it, k, "m42-b-ws-pt") for k, it in enumerate(_items(sec, hi=4)))
    stick = f'<span class="m42-b-sticker">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else ""
    return f'<div class="m42-b-ws"><h2>{e(sec.get("title"))}{stick}</h2>{lead(sec)}</div><div class="m42-b-ws-pts">{pts}</div>'


# ---------------------------------------------------------------------------------------------------- process
_STEP_ICONS = ("bi-chat-heart", "bi-map", "bi-calendar2-check", "bi-stars", "bi-flag", "bi-trophy")


def _sic(it, k):
    return f'<i class="bi {ic(it.get("icon"), _STEP_ICONS[k % 6])}"></i>'


def process_doodle_rows(sec, ctx):
    """ProFinance: rows that change sides (a picture and the words), joined by a hand-drawn line running between them, colour blobs."""
    rows = "".join(f'<div class="m42-b-dr{" is-rev" if k % 2 else ""}" style="{_t(k)}"><div class="m42-b-dr-pic"><span class="m42-b-dr-blob"></span>'
                   f'{_thing(it, "m42-b-dr-img", k)}</div><div class="m42-b-dr-words"><span class="m42-b-dr-n">Step {k + 1:02d}</span><h3>{e(it.get("title"))}</h3>'
                   f'<p>{e(it.get("text"))}</p></div></div>' for k, it in enumerate(_items(sec, hi=4)))
    line = ('<svg class="m42-b-dr-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            '<path d="M30 4 C 80 12, 85 30, 70 38 S 20 55, 30 66 S 80 85, 70 98" /></svg>')
    return head(sec) + f'<div class="m42-b-drs">{line}{rows}</div>'


def process_phone_circle(sec, ctx):
    """Passion Finder: the thing on a circle in the middle, the step cards fanned out beside it, the explanation in a column."""
    its, ps = _items(sec, hi=4), _pics(sec)
    centre = pic(ps[0], "m42-b-pcir-img", sec.get("title")) if ps else f'<div class="m42-b-pcir-img m42-b-art"><i class="bi {ic(sec.get("icon"), "bi-phone")}"></i></div>'
    fan = "".join(f'<div class="m42-b-fan-it" style="--k:{k};{_t(k)}"><span>{_sic(it, k)}</span><div><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div></div>'
                  for k, it in enumerate(its))
    return (f'<div class="m42-b-pcir"><div class="m42-b-pcir-words">{head(sec, center=False)}{acts(sec, ghost=False)}</div>'
            f'<div class="m42-b-pcir-stage"><span class="m42-b-pcir-disc"></span>{centre}<div class="m42-b-fan">{fan}</div></div></div>')


def process_stair_steps(sec, ctx):
    """Wello: the steps as tiles at stepped heights rising left to right, a big number on each."""
    its = _items(sec, hi=4)
    tiles = "".join(f'<div class="m42-b-ss" style="--k:{k};--n:{len(its)};{_t(k)}"><strong>{k + 1:02d}</strong><span>{_sic(it, k)}</span>'
                    f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>' for k, it in enumerate(its))
    return head(sec, center=False) + f'<div class="m42-b-sss">{tiles}</div>'


def process_timeline(sec, ctx):
    """A vertical line down the middle, the steps on alternate sides with node circles; the line fills as it is reached."""
    rows = "".join(f'<li class="{"is-r" if k % 2 else "is-l"}" style="{_t(k)}"><span class="m42-b-tlx-node">{k + 1}</span><div class="m42-b-tlx-card">'
                   f'<span class="m42-b-tlx-ic">{_sic(it, k)}</span><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>'
                   + (f'<em>{e(it.get("badge") or _role(it))}</em>' if it.get("badge") or _role(it) else "") + "</div></li>" for k, it in enumerate(_items(sec, hi=6)))
    return head(sec) + f'<ol class="m42-b-tlx">{rows}</ol>'


def process_big_numbers(sec, ctx):
    """Columns under huge outlined numbers 01-04, a thin rule joining them."""
    cols = "".join(f'<div class="m42-b-bn" style="{_t(k)}"><strong>{k + 1:02d}</strong><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>'
                   for k, it in enumerate(_items(sec, hi=4)))
    return head(sec, center=False) + f'<div class="m42-b-bns">{cols}</div>'


# ---------------------------------------------------------------------------------------------------- showcase
_SCAT = ((2, 6, 13, -6), (17, 52, 11, 4), (4, 64, 9, 3), (78, 2, 12, 5), (86, 44, 10, -4), (70, 66, 12, -3), (30, 0, 8, 6), (62, 78, 8, -5))


def _cap(it):
    return (f'<figcaption><b>{e(it.get("title"))}</b>' + (f'<span>{e(it.get("text"))}</span>' if it.get("text") else "") + "</figcaption>")


def _shots(sec, hi):
    """The items that have photos (a showcase is pictures)."""
    return [it for it in _items(sec, hi=99) if widgets.photo(it)][:hi]


def showcase_scattered_portraits(sec, ctx):
    """CoreHR: photos scattered round a centred title at different sizes and angles."""
    its = _shots(sec, 8)
    figs = "".join(f'<figure class="m42-b-sc" style="left:{x}%;top:{y}%;width:{w}%;--r:{r}deg;--d:{k * .35}s">{widgets.photo(it, "m42-b-sc-img")}</figure>'
                   for k, (it, (x, y, w, r)) in enumerate(zip(its, _SCAT)))
    return (f'<div class="m42-b-scat">{figs}<div class="m42-b-scat-core"><span class="m42-b-net-hub"><i class="bi {ic(sec.get("icon"), "bi-camera")}"></i></span>'
            f'{head(sec)}{acts(sec, ghost=False)}</div></div>')


def showcase_collage(sec, ctx):
    """Tea brand: 3-4 overlapping photos with white borders beside the words and a short list."""
    its = _shots(sec, 4)
    figs = "".join(f'<figure class="m42-b-col is-{k}">{widgets.photo(it, "m42-b-col-img")}</figure>' for k, it in enumerate(its))
    pts = "".join(f'<li><i class="bi bi-check2-circle"></i>{e(it.get("title"))}</li>' for it in its)
    return (f'<div class="m42-b-collage"><div class="m42-b-col-stage">{figs}</div><div class="m42-b-col-words">{head(sec, center=False)}'
            f'<ul class="m42-b-col-list">{pts}</ul>{acts(sec, ghost=False)}</div></div>')


def showcase_masonry(sec, ctx):
    """Photos of mixed heights in columns, the caption sliding up on hover."""
    figs = "".join(f'<figure class="m42-b-mas is-{k % 3}">{widgets.photo(it, "m42-b-mas-img")}{_cap(it)}</figure>' for k, it in enumerate(_shots(sec, 12)))
    return head(sec) + f'<div class="m42-b-masonry">{figs}</div>'


def showcase_before_after(sec, ctx):
    """Pairs side by side with a divider handle that drags, the treatment / program and its time under."""
    its = [it for it in _shots(sec, 12) if widgets.photo({"photo": it.get("before")})]
    pairs = []
    for b in its[:6]:  # (each item: its "before" photo and its own photo of the same place after)
        a = dict(b, photo=b.get("before"))
        pairs.append(f'<figure class="m42-b-ba"><div class="m42-b-ba-frame" data-m42-ba style="--p:50%">{widgets.photo(b, "m42-b-ba-img")}'
                     f'<div class="m42-b-ba-before">{widgets.photo(a, "m42-b-ba-img")}</div><span class="m42-b-ba-tag is-b">Before</span>'
                     f'<span class="m42-b-ba-tag is-a">After</span><input type="range" min="0" max="100" value="50" aria-label="Before and after"><span class="m42-b-ba-handle">'
                     f'<i class="bi bi-arrows-expand-vertical"></i></span></div><figcaption><b>{e(b.get("title") or a.get("title"))}</b>'
                     f'<span>{e(b.get("text") or a.get("text") or "")}</span></figcaption></figure>')
    return head(sec) + f'<div class="m42-b-bas">{"".join(pairs)}</div>'


def showcase_tilted_cards_cta(sec, ctx):
    """Passion Finder: tilted photo cards fanned at both sides, a centred line and the action between them."""
    its = _shots(sec, 6)
    half = (len(its) + 1) // 2
    side = lambda grp, s: "".join(f'<figure class="m42-b-tc2 is-{s}{k}">{widgets.photo(it, "m42-b-tc2-img")}</figure>' for k, it in enumerate(grp))  # noqa: E731
    return (f'<div class="m42-b-tcta"><div class="m42-b-tcta-side is-l">{side(its[:half], "l")}</div><div class="m42-b-tcta-mid">{brow(sec)}'
            f'<h2>{e(sec.get("title"))}</h2>{lead(sec)}{acts(sec)}</div><div class="m42-b-tcta-side is-r">{side(its[half:], "r")}</div></div>')


def showcase_film_strip(sec, ctx):
    """One wide row of tall photos moving slowly sideways (paused on hover)."""
    figs = "".join(f'<figure class="m42-b-film-it">{widgets.photo(it, "m42-b-film-img")}{_cap(it)}</figure>' for it in _shots(sec, 12))
    return head(sec) + f'<div class="m42-b-film"><div class="m42-b-film-track">{figs}{figs.replace("<figure ", "<figure aria-hidden=\"true\" ")}</div></div>'


# ---------------------------------------------------------------------------------------------------- pricing
def _incl(it, n=6):
    return "".join(f'<li><i class="bi bi-check-lg"></i>{e(x)}</li>' for x in (it.get("meta") or [])[:n])


def _per(it):
    p = str(it.get("per") or "")
    return f'<small>/ {e(p)}</small>' if p else ""


def _btn(sec, it, cls="m42-btn"):
    return f'<a class="{cls}" href="#">{e(it.get("button") or sec.get("button") or "Choose")}</a>'


def pricing_account_card(sec, ctx):
    """Finix: a stack of pictures on the left, a dark card on the right with the price big, plan tabs and the action."""
    its, ps = _items(sec, hi=3), _pics(sec)
    star = _star_plan(its, 0)
    tabs = "".join(f'<button type="button" class="{"is-on" if k == star else ""}" data-m42-plan="{k}">{e(it.get("title"))}</button>' for k, it in enumerate(its))
    panes = "".join(f'<div class="m42-b-acc-pane{" is-on" if k == star else ""}" data-m42-plan-pane="{k}"><strong>{money(it)}{_per(it)}</strong><p>{e(it.get("text"))}</p>'
                    f'<ul>{_incl(it)}</ul></div>' for k, it in enumerate(its))
    stack = "".join(pic(s, f"m42-b-acc-img is-{k}") for k, s in enumerate(ps[:3])) or orb(sec, None, "bi-wallet2")
    return (f'<div class="m42-b-acc"><div class="m42-b-acc-stack">{stack}</div><div class="m42-b-acc-words">{head(sec, center=False)}<div class="m42-b-acc-card">'
            f'<div class="m42-b-acc-tabs" data-m42-plans>{tabs}</div>{panes}{_btn(sec, {})}</div></div></div>')


def _middle_priced(its):
    def num(it):
        try:
            return float(str(it.get("value") or "").replace(",", ""))
        except ValueError:
            return None
    priced = sorted((num(it), k) for k, it in enumerate(its) if num(it) is not None)
    return priced[len(priced) // 2][1] if len(priced) >= 3 else len(its) // 2


def _star_plan(its, none):
    """The plan to raise: the one badged when only one is; when every plan has a badge (a dental page's "Most popular"
    sat on its ₹500 checkup, a wedding's on "Economy"), the middle-priced one; none: when no plan is badged."""
    badged = [k for k, it in enumerate(its) if it.get("badge")]
    if len(badged) == 1:
        return badged[0]
    return _middle_priced(its) if badged else none


def pricing_featured_middle(sec, ctx):
    """Three plans, the usual choice raised in the middle on the deep colour."""
    its = _items(sec, hi=4)
    star = _star_plan(its, len(its) // 2)  # (every plan badged, as a real build did: the usual
    # choice is the middle-priced one, not the first badge (it raised "Basic · Economy" over the dearer ones))
    if len(its) >= 3 and star != 1:
        its = its[:]
        its.insert(1, its.pop(star))
        star = 1
    cards = "".join(f'<div class="m42-b-fm{" is-star" if k == star else ""}">' + (f'<span class="m42-b-fm-badge">{e(it.get("badge"))}</span>' if it.get("badge") else "")
                    + f'<b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p><strong>{money(it)}{_per(it)}</strong><ul>{_incl(it)}</ul>'
                    + _btn(sec, it, "m42-btn" if k == star else "m42-btn-ghost") + "</div>" for k, it in enumerate(its))
    return head(sec) + f'<div class="m42-b-fms">{cards}</div>'


def pricing_compare_table(sec, ctx):
    """The plans as columns of one table, a tick per feature (a feature listed by any plan, ticked where that plan has it)."""
    its = _items(sec, hi=4)
    feats = []
    for it in its:
        for x in it.get("meta") or []:
            if x not in feats:
                feats.append(x)
    star = _star_plan(its, -1)
    th = "".join(f'<th class="{"is-star" if k == star else ""}">' + (f'<span class="m42-b-chip">{e(it.get("badge"))}</span>' if it.get("badge") else "")
                 + f'<b>{e(it.get("title"))}</b><strong>{money(it)}{_per(it)}</strong></th>' for k, it in enumerate(its))
    def cell(f, k, it):
        has = f in (it.get("meta") or [])
        return f'<td class="{"is-star" if k == star else ""}"><i class="bi {"bi-check-circle-fill" if has else "bi-dash"}"></i></td>'
    rows = "".join(f'<tr><td>{e(f)}</td>' + "".join(cell(f, k, it) for k, it in enumerate(its)) + "</tr>" for f in feats[:12])
    foot = "".join(f'<td class="{"is-star" if k == star else ""}">{_btn(sec, it, "m42-btn" if k == star else "m42-btn-ghost")}</td>' for k, it in enumerate(its))
    return head(sec) + f'<div class="m42-b-cmp-wrap"><table class="m42-b-cmp"><thead><tr><th></th>{th}</tr></thead><tbody>{rows}</tbody><tfoot><tr><td></td>{foot}</tr></tfoot></table></div>'


def pricing_package_rows(sec, ctx):
    """Each package a wide row: its picture or number, the name, what it includes, the price and the action."""
    rows = "".join(f'<div class="m42-b-pr{" is-star" if it.get("badge") else ""}" style="{_t(k)}">'
                   + (widgets.photo(it, "m42-b-pr-img") or f'<span class="m42-b-pr-n">{k + 1:02d}</span>')
                   + f'<div class="m42-b-pr-name"><b>{e(it.get("title"))}</b>' + (f'<span class="m42-b-chip">{e(it.get("badge"))}</span>' if it.get("badge") else "")
                   + f'<p>{e(it.get("text"))}</p></div><ul>{_incl(it, 4)}</ul><div class="m42-b-pr-buy"><strong>{money(it)}{_per(it)}</strong>{_btn(sec, it)}</div></div>'
                   for k, it in enumerate(_items(sec, hi=5)))
    return head(sec, center=False) + f'<div class="m42-b-prs">{rows}</div>'


# ---------------------------------------------------------------------------------------------------- listings
def listings_integration_fan(sec, ctx):
    """CoreHR: tilted icon tiles in an arc, the centred one large with its name and line under it; arrows turn the arc."""
    its = _items(sec, hi=9)
    mid = len(its) // 2
    tiles = "".join(f'<button type="button" class="m42-b-arc-it{" is-on" if k == mid else ""}" style="--i:{k - mid};{_t(k)}" data-m42-arc="{k}" '
                    f'data-name="{e(it.get("title"))}" data-text="{e(it.get("text") or "")}" aria-label="{e(it.get("title"))}">'
                    + (widgets.photo(it, "m42-b-arc-img") or f'<i class="bi {ic(it.get("icon"), _LOGO_ICONS[k % 6])}"></i>') + "</button>" for k, it in enumerate(its))
    on = its[mid] if its else {}
    return (head(sec) + f'<div class="m42-b-arc" data-m42-arcs><div class="m42-b-arc-row">{tiles}</div><div class="m42-b-arc-cap"><b>{e(on.get("title"))}</b>'
            f'<span>{e(on.get("text") or "")}</span></div></div>')


def listings_category_tiles(sec, ctx):
    """Large photo tiles with the name over a dark gradient, the first one wide; an arrow that turns on hover."""
    tiles = "".join(f'<a class="m42-b-cat is-{k}" href="#">{widgets.photo(it, "m42-b-cat-img")}<div><b>{e(it.get("title"))}</b>'
                    + (f'<span>{e(it.get("text"))}</span>' if it.get("text") else "") + '</div><i class="bi bi-arrow-up-right"></i></a>'
                    for k, it in enumerate(_shots(sec, 8)))
    return head(sec, center=False) + f'<div class="m42-b-cats">{tiles}</div>'


def listings_filter_grid(sec, ctx):
    """Filter chips over a grid of cards with tags on the photos; a chip shows only its things."""
    its = _items(sec, hi=12)
    tags = []
    for it in its:
        t = str(it.get("badge") or "")
        if t and t not in tags:
            tags.append(t)
    chips = '<button type="button" class="is-on" data-m42-filter="*">All</button>' + "".join(
        f'<button type="button" data-m42-filter="{e(t)}">{e(t)}</button>' for t in tags[:6])
    cards = "".join(f'<article class="m42-b-fg" data-tag="{e(it.get("badge") or "")}"><div class="m42-b-fg-pic">{_thing(it, "m42-b-fg-img", k)}'
                    + (f'<span class="m42-b-chip">{e(it.get("badge"))}</span>' if it.get("badge") else "")
                    + f'</div><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p>{_price(it)}</article>' for k, it in enumerate(its))
    return (f'<div class="m42-b-fgrid" data-m42-filters><div class="m42-b-wavehead">{head(sec, center=False)}<div class="m42-b-chips">{chips}</div></div>'
            f'<div class="m42-b-fgs">{cards}</div></div>')


# ---------------------------------------------------------------------------------------------------- schedule
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _day(it):
    """An item's day (its first meta word that is a weekday) and time (its second meta)."""
    m = [str(x) for x in (it.get("meta") or [])]
    d = next((x[:3].title() for x in m if x[:3].title() in _DAYS), "")
    t = next((x for x in m if any(c.isdigit() for c in x)), "")
    return d, t


def schedule_week_grid(sec, ctx):
    """Days as columns, the times as rows, each thing a coloured block in its day and time."""
    its = [it for it in _items(sec, hi=30) if _day(it)[0]]
    days = [d for d in _DAYS if any(_day(it)[0] == d for it in its)] or list(_DAYS[:5])
    times = sorted({_day(it)[1] for it in its}, key=lambda x: (len(x.split(":")[0]), x))
    cols = "".join(f'<div class="m42-b-wk-day">{d}</div>' for d in days)
    cells = []
    for tm in times:
        cells.append(f'<div class="m42-b-wk-time">{e(tm)}</div>')
        for d in days:
            hit = [(k, it) for k, it in enumerate(its) if _day(it) == (d, tm)]
            cells.append('<div class="m42-b-wk-cell">' + "".join(f'<div class="m42-b-wk-ev" style="{_t(k)}"><b>{e(it.get("title"))}</b><span>{e(it.get("badge") or it.get("text") or "")}</span></div>'
                                                             for k, it in hit) + "</div>")
    return head(sec) + f'<div class="m42-b-wk-wrap"><div class="m42-b-wk" style="--d:{len(days)}"><div></div>{cols}{"".join(cells)}</div></div>'


def schedule_agenda(sec, ctx):
    """Day tabs above, the time on the left and the session on the right, a hairline between."""
    its = _items(sec, hi=20)
    days = []
    for it in its:
        d = _day(it)[0] or "All"
        if d not in days:
            days.append(d)
    tabs = "".join(f'<button type="button" class="{"is-on" if k == 0 else ""}" data-m42-day="{d}">{d}</button>' for k, d in enumerate(days))
    rows = "".join(f'<li data-day="{_day(it)[0] or "All"}"{"" if (_day(it)[0] or "All") == days[0] else " hidden"} style="{_t(k)}"><time>{e(_day(it)[1])}</time><div><b>{e(it.get("title"))}</b>'
                   f'<p>{e(it.get("text"))}</p></div>' + (f'<span class="m42-b-chip">{e(it.get("badge"))}</span>' if it.get("badge") else "") + "</li>"
                   for k, it in enumerate(its))
    return (f'<div class="m42-b-agenda" data-m42-days><div class="m42-b-wavehead">{head(sec, center=False)}<div class="m42-b-chips">{tabs}</div></div>'
            f'<ol class="m42-b-ag">{rows}</ol></div>')


def schedule_hours_card(sec, ctx):
    """A card of the week's hours, today in bold with an 'open now' dot (set by the visitor's clock); the words beside."""
    its = _items(sec, hi=7)
    rows = "".join(f'<li data-m42-dow="{_DAYS.index(_day(it)[0]) if _day(it)[0] in _DAYS else -1}"><span>{e(_day(it)[0] or it.get("title"))}</span>'
                   f'<b>{e(_day(it)[1] or ((it.get("meta") or ["", ""]) + [""])[1] or it.get("text") or "")}</b></li>' for it in its)
    return (f'<div class="m42-b-hours"><div>{head(sec, center=False)}{acts(sec, ghost=False)}</div><div class="m42-b-hours-card" data-m42-hours>'
            f'<div class="m42-b-hours-top"><i class="bi bi-clock"></i><b>Opening hours</b><span class="m42-b-open"><i></i>Open today</span></div><ul>{rows}</ul></div></div>')


# ---------------------------------------------------------------------------------------------------- impact
def impact_globe_numbers(sec, ctx):
    """Finix: a big round object on one side, a huge mixed-type headline and 2-3 impact figures on the other."""
    ps = _pics(sec)
    figs = "".join(f'<div style="{_t(k)}"><strong>{e(_figure(it))}</strong><b>{e(it.get("title"))}</b><p>{e(it.get("text"))}</p></div>'
                   for k, it in enumerate(it for it in _items(sec, hi=3) if _figure(it)))
    return (f'<div class="m42-b-imp"><div class="m42-b-imp-obj">{orb(sec, ps[0] if ps else None)}</div><div class="m42-b-imp-words">{brow(sec)}'
            f'<h2>{mix(sec.get("title"))}</h2>{lead(sec)}<div class="m42-b-imp-figs">{figs}</div></div></div>')


def impact_numbers_story(sec, ctx):
    """Big impact numbers stacked on one side, one real story with its photo on the other."""
    its, ps = _items(sec, hi=3), _pics(sec)
    nums = "".join(f'<li style="{_t(k)}"><strong>{e(_figure(it))}</strong><span>{e(it.get("title"))}</span></li>' for k, it in enumerate(its) if _figure(it))
    it_s = next((it for it in _items(sec, hi=9) if it.get("text") and not _figure(it)), None) or {"text": sec.get("lead"), "title": sec.get("brand")}
    art = pic(ps[0], "m42-b-story-img", sec.get("title")) if ps else ""
    return (f'{head(sec, center=False)}<div class="m42-b-story"><ol class="m42-b-story-nums">{nums}</ol><figure class="m42-b-story-card">{art}'
            f'<figcaption><span class="m42-b-leader-q">“</span><blockquote>{e(it_s.get("text"))}</blockquote>'
            + (f'<b>{e(it_s.get("title"))}</b>' if it_s.get("title") else "") + "</figcaption></figure></div>")


# ---------------------------------------------------------------------------------------------------- faq
def _qa(its, open_first=True):
    return "".join(f'<details class="m42-b-qa"{" open" if k == 0 and open_first else ""}><summary><span>{e(it.get("title"))}</span><i class="bi bi-plus-lg"></i></summary>'
                   f'<p>{e(it.get("text"))}</p></details>' for k, it in enumerate(its))


def faq_lines_band(sec, ctx):
    """Wello: the questions as hairline rows (open one at a time), a soft illustrated band under them with the contact line."""
    band = (f'<div class="m42-b-faqband"><span class="m42-b-faqband-art"><i class="bi bi-chat-heart"></i></span><b>{e(sec.get("lead") or "Still have a question?")}</b>'
            f'{acts(sec, ghost=False)}</div>')
    return (f'<div class="m42-b-faq">{brow(sec)}<h2>{e(sec.get("title"))}</h2><div class="m42-b-qas">{_qa(_items(sec, hi=8))}</div>{band}</div>')


def faq_split(sec, ctx):
    """The head and a contact line sticky on the left, the questions on the right."""
    return (f'<div class="m42-b-fsplit"><div class="m42-b-fsplit-head">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}{acts(sec, ghost=False)}</div>'
            f'<div class="m42-b-qas">{_qa(_items(sec, hi=8))}</div></div>')


# ---------------------------------------------------------------------------------------------------- location
def _contact(sec):
    """The section's contact lines: (icon, label, value, link) from its own fields, else its items."""
    out = []
    for key, icon, label, link in (("address", "bi-geo-alt", "Visit", "https://maps.google.com/?q="), ("phone", "bi-telephone", "Call", "tel:"),
                                   ("email", "bi-envelope", "Write", "mailto:"), ("hours", "bi-clock", "Hours", "")):
        v = str(sec.get(key) or "")
        if v:
            href = (link + (v.replace(" ", "") if link == "tel:" else v)) if link else ""
            out.append((icon, label, v, href))
    if not out:
        out = [(ic(it.get("icon"), "bi-geo-alt"), str(it.get("title") or ""), str(it.get("text") or ""), "") for it in _items(sec, hi=4)]
    return out


def location_map_card(sec, ctx):
    """A map filling the width (the address on Google Maps; a pin picture without an address), a card with the address, hours and phone over it."""
    import urllib.parse
    addr = str(sec.get("address") or "")
    q = urllib.parse.quote(addr)
    lines = "".join(f'<li><i class="bi {i}"></i><div><span>{e(l)}</span>' + (f'<a href="{e(h)}">{e(v)}</a>' if h else f'<b>{e(v)}</b>') + "</div></li>"
                    for i, l, v, h in _contact(sec))
    frame = (f'<iframe class="m42-b-map-frame" title="Map" loading="lazy" referrerpolicy="no-referrer" src="https://maps.google.com/maps?q={q}&amp;output=embed"></iframe>'
             if addr else '<div class="m42-b-map-frame m42-b-map-art"><i class="bi bi-geo-alt-fill"></i></div>')
    return (f'<div class="m42-b-map">{frame}<div class="m42-b-map-card">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}<ul>{lines}</ul>'
            + (f'<a class="m42-btn" href="https://maps.google.com/?q={q}" target="_blank" rel="noopener">Get directions <i class="bi bi-arrow-up-right"></i></a>' if addr else "")
            + "</div></div>")


def location_contact_columns(sec, ctx):
    """Three columns (visit, call, write) with icons in soft circles, each its action."""
    cols = "".join(f'<div class="m42-b-cc" style="{_t(k)}"><span class="m42-b-cc-ic"><i class="bi {i}"></i></span><b>{e(l)}</b><p>{e(v)}</p>'
                   + (f'<a class="m42-b-more" href="{e(h)}">{e({"Visit": "Directions", "Call": "Call now", "Write": "Send a mail"}.get(l, "Open"))} <i class="bi bi-arrow-right"></i></a>' if h else "")
                   + "</div>" for k, (i, l, v, h) in enumerate(_contact(sec)[:4]))
    return head(sec) + f'<div class="m42-b-ccs">{cols}</div>'


# ---------------------------------------------------------------------------------------------------- action
def _links(sec):
    its = _items(sec, hi=6)
    return "".join(f'<a href="#">{e(it.get("title"))}</a>' for it in its)


def action_spotlight(sec, ctx):
    """Resq: a dark panel, the brand small, a big line, the action with a light glow rising under it, the links on the same panel."""
    return (f'<div class="m42-b-act m42-b-a-spot"><span class="m42-b-h-stars"></span><div class="container"><span class="m42-b-a-brand">{e(sec.get("brand") or sec.get("eyebrow") or "")}</span>'
            f'<h2>{e(sec.get("title"))}</h2>{lead(sec)}<div class="m42-b-a-glow">{acts(sec, ghost=False)}<span></span></div>'
            f'<nav class="m42-b-a-links">{_links(sec)}</nav></div></div>')


def action_dark_card_mockup(sec, ctx):
    """ProFinance: a rounded dark card with the line and action on the left, a picture breaking out of its top right."""
    ps = _pics(sec)
    art = pic(ps[0], "m42-b-a-dc-img", sec.get("title")) if ps else frame(sec)
    return (f'<div class="m42-b-a-dc"><div class="m42-b-a-dc-words">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}{acts(sec)}</div>'
            f'<div class="m42-b-a-dc-art">{art}</div><span class="m42-b-a-dc-ring"></span></div>')


def action_blob_newsletter(sec, ctx):
    """BetterVits: a soft card with the line and an email box on the left, the picture in a dark blob on the right."""
    ps = _pics(sec)
    art = pic(ps[0], "m42-b-a-blob-img", sec.get("title")) if ps else f'<span class="m42-b-a-blob-img m42-b-art"><i class="bi {ic(sec.get("icon"), "bi-envelope-heart")}"></i></span>'
    return (f'<div class="m42-b-a-nl"><div class="m42-b-a-nl-words">{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}'
            f'<form class="m42-b-a-form" onsubmit="event.preventDefault();this.classList.add(\'is-sent\')"><input type="email" required placeholder="Your email" aria-label="Your email">'
            f'<button type="submit" class="m42-btn">{e(sec.get("button") or "Join")}</button><span class="m42-b-a-sent"><i class="bi bi-check-circle-fill"></i> Thank you, we will be in touch.</span></form></div>'
            f'<div class="m42-b-a-blob">{art}</div></div>')


def action_tilted_cards(sec, ctx):
    """Passion Finder: picture cards tilted at both sides, the line and the actions centred between them."""
    return showcase_tilted_cards_cta(dict(sec, items=[{"photo": s, "title": sec.get("title")} for s in _pics(sec)][:6]), ctx)


def action_giant_brand_footer(sec, ctx):
    """CoreHR / Finix: the closing line and links, the brand name huge across the bottom, cut off by the page's edge."""
    brand = str(sec.get("brand") or sec.get("eyebrow") or "")
    return (f'<div class="m42-b-act m42-b-a-giant"><div class="container"><div class="m42-b-a-giant-top"><div>{brow(sec)}<h2>{e(sec.get("title"))}</h2>{lead(sec)}{acts(sec)}</div>'
            f'<nav class="m42-b-a-links is-col">{_links(sec)}</nav></div></div><div class="m42-b-a-giant-word" style="--n:{max(4, len(brand))}" aria-hidden="true">{e(brand)}</div></div>')


# ---------------------------------------------------------------------------------------------------- registry
# needs: items (min, max; (0, 0) = it draws from the section's own words); photo: "none" (draws without photos), "better" (photos make it, monograms otherwise),
# "needed" (only with photos); "ref": the reference page the composition comes from (weights.py).
BLOCKS = {
    "people.photo_band_statement": {"role": "people", "draw": people_photo_band_statement, "needs": {"items": (1, 1), "photo": "better"}},
    "people.reveal_circles": {"role": "people", "draw": people_reveal_circles, "needs": {"items": (3, 6), "photo": "better"}},
    "people.leader": {"role": "people", "draw": people_leader, "needs": {"items": (1, 1), "photo": "better"}},
    "people.spotlight": {"role": "people", "draw": people_spotlight, "needs": {"items": (2, 6), "photo": "better"}},
    "people.portraits": {"role": "people", "draw": people_portraits, "needs": {"items": (2, 8), "photo": "better"}},
    "people.overlap": {"role": "people", "draw": people_overlap, "needs": {"items": (3, 8), "photo": "better"}},
    "people.credentials": {"role": "people", "draw": people_credentials, "needs": {"items": (2, 10), "photo": "none"}},
    "proof.envelope": {"role": "proof", "draw": proof_envelope, "needs": {"items": (2, 6), "photo": "none"}},
    "proof.staggered": {"role": "proof", "draw": proof_staggered, "needs": {"items": (3, 6), "photo": "none"}},
    "proof.cards_readmore": {"role": "proof", "draw": proof_cards_readmore, "needs": {"items": (3, 6), "photo": "none"}},
    "proof.wall": {"role": "proof", "draw": proof_wall, "needs": {"items": (4, 9), "photo": "none"}},
    "proof.rating": {"role": "proof", "draw": proof_rating, "needs": {"items": (2, 4), "photo": "none"}},
    "proof.results": {"role": "proof", "draw": proof_results, "needs": {"items": (2, 6), "photo": "none"}},
    "proof.bigquote": {"role": "proof", "draw": proof_bigquote, "needs": {"items": (2, 4), "photo": "none"}},
}


def _reg(name, draw, items=(0, 0), photo="none", pics=0, bleed=False):
    """A block into the registry: its role is its name's first part; pics = how many pictures it needs at least."""
    BLOCKS[name] = {"role": name.split(".")[0], "draw": draw, "needs": {"items": items, "photo": photo, "pics": pics}, "bleed": bleed}


# batch 2 (2026-11-14): hero and trust
_reg("hero.spotlight_mockup", hero_spotlight_mockup, photo="better", bleed=True)
_reg("hero.faces_sides", hero_faces_sides, photo="needed", pics=2, bleed=True)
_reg("hero.pedestal", hero_pedestal, photo="needed", pics=1, bleed=True)
_reg("hero.doodle_block", hero_doodle_block, photo="needed", pics=1, bleed=True)
_reg("hero.network", hero_network, photo="better", bleed=True)
_reg("hero.globe_type", hero_globe_type, photo="better", bleed=True)
_reg("hero.poster", hero_poster, photo="better", bleed=True)
_reg("hero.giant_overlap", hero_giant_overlap, photo="better", bleed=True)
_reg("hero.colour_panel", hero_colour_panel, photo="better", bleed=True)
_reg("hero.showroom", hero_showroom, photo="better", bleed=True)
_reg("trust.logo_dark", trust_logo_dark, (4, 7))
_reg("trust.logo_circles", trust_logo_circles, (4, 8))
_reg("trust.cause_strip", trust_cause_strip, bleed=True)
_reg("trust.huge_numbers", trust_huge_numbers, (2, 4))
_reg("trust.statement_quote", trust_statement_quote, (0, 1))

# batch 3 (2026-11-14): offer and why
_reg("offer.pedestal_carousel", offer_pedestal_carousel, (3, 8), "better")
_reg("offer.bento_mockups", offer_bento_mockups, (3, 6), "better")
_reg("offer.stair_tiles", offer_stair_tiles, (3, 3))
_reg("offer.mockup_cards", offer_mockup_cards, (2, 6), "better")
_reg("offer.shape_cards", offer_shape_cards, (2, 4))
_reg("offer.stage_rows", offer_stage_rows, (2, 4), "better")
_reg("offer.ingredient_mosaic", offer_ingredient_mosaic, (4, 8), "better")
_reg("offer.list_menu", offer_list_menu, (4, 16))
_reg("why.hub_spokes", why_hub_spokes, (4, 4))
_reg("why.orbit_object", why_orbit_object, (4, 4), "better")
_reg("why.floating_tiles", why_floating_tiles, (4, 6))
_reg("why.curved_photo_icons", why_curved_photo_icons, (4, 6), "better")
_reg("why.title_left_grid", why_title_left_grid, (4, 4))
_reg("why.inline_icon_statement", why_inline_icon_statement, (0, 1))  # (it draws the section's words only: a list of reasons would be lost)
_reg("why.watermark", why_watermark, (3, 6), "better")
_reg("why.word_sticker", why_word_sticker, (3, 4))
# batch 4 (2026-11-14): process, showcase, pricing, listings
_reg("process.doodle_rows", process_doodle_rows, (2, 4), "better")
_reg("process.phone_circle", process_phone_circle, (3, 4), "better")
_reg("process.stair_steps", process_stair_steps, (3, 4))
_reg("process.timeline", process_timeline, (3, 6))
_reg("process.big_numbers", process_big_numbers, (3, 4))
_reg("showcase.scattered_portraits", showcase_scattered_portraits, (4, 8), "needed", pics=4)
_reg("showcase.collage", showcase_collage, (3, 4), "needed", pics=3)
_reg("showcase.masonry", showcase_masonry, (6, 12), "needed", pics=6)
_reg("showcase.before_after", showcase_before_after, (2, 6), "needed", pics=2)
_reg("showcase.tilted_cards_cta", showcase_tilted_cards_cta, (2, 6), "needed", pics=2)
_reg("showcase.film_strip", showcase_film_strip, (5, 12), "needed", pics=5)
_reg("pricing.account_card", pricing_account_card, (1, 3), "better")
_reg("pricing.featured_middle", pricing_featured_middle, (2, 4))
_reg("pricing.compare_table", pricing_compare_table, (2, 4))
_reg("pricing.package_rows", pricing_package_rows, (2, 5), "optional")
_reg("listings.integration_fan", listings_integration_fan, (5, 9))
_reg("listings.category_tiles", listings_category_tiles, (3, 8), "needed", pics=3)
_reg("listings.filter_grid", listings_filter_grid, (4, 12), "better")
# batch 5 (2026-11-14): schedule, impact, faq, location, action
_reg("schedule.week_grid", schedule_week_grid, (3, 30))
_reg("schedule.agenda", schedule_agenda, (3, 20))
_reg("schedule.hours_card", schedule_hours_card, (1, 7))
_reg("impact.globe_numbers", impact_globe_numbers, (2, 3), "better")
_reg("impact.numbers_story", impact_numbers_story, (2, 4), "better")
_reg("faq.lines_band", faq_lines_band, (4, 8))
_reg("faq.split", faq_split, (4, 8))
_reg("location.map_card", location_map_card)
_reg("location.contact_columns", location_contact_columns)  # (address, phone, hours, map: from the items)
_reg("action.spotlight", action_spotlight, bleed=True)
_reg("action.dark_card_mockup", action_dark_card_mockup, photo="better")
_reg("action.blob_newsletter", action_blob_newsletter, photo="better")
_reg("action.tilted_cards", action_tilted_cards, photo="needed", pics=2)
_reg("action.giant_brand_footer", action_giant_brand_footer, bleed=True)


# ---------------------------------------------------------------------------------------------------- choosing
# what a block's content must really be, beyond its count (a pricing block with no prices, a week grid with no days
# and times, huge numbers with no numbers would draw empty)
def _priced(its):
    return sum(1 for it in its if money(it)) >= max(2, len(its) // 2)


def _figs(sec, hi):
    """A numbers block's items: those with a number when most have one (a real build drew "Happy / Couples" with no
    number among "12 Years · 500+"), the line under a number dropped when it only repeats it ("12 Years" under "12Years")."""
    its = _items(sec, hi=99)
    got = [it for it in its if _figure(it)]
    its = (got if len(got) >= 2 else its)[:hi]
    norm = lambda x: re.sub(r"[^0-9a-z]", "", str(x).lower())
    return [dict(it, text="") if it.get("text") and norm(it["text"]) == norm(_figure(it)) else it for it in its]


def _figured(its):
    return sum(1 for it in its if _figure(it)) >= 2


def _dated(its):
    return sum(1 for it in its if _day(it)[0]) >= 3


def _said(its):
    return sum(1 for it in its if str(it.get("text") or "").strip()) >= max(1, len(its) // 2)


NEED = {
    "pricing": _priced, "offer.list_menu": _priced, "offer.pedestal_carousel": _priced,
    "trust.huge_numbers": _figured, "impact.globe_numbers": _figured, "impact.numbers_story": _figured, "proof.results": _figured,
    "schedule.week_grid": _dated, "schedule.agenda": _dated, "schedule.hours_card": lambda its: sum(1 for it in its if _day(it)[0]) >= 1,
    "proof": _said, "faq": _said,
    "showcase.before_after": lambda its: sum(1 for it in its if it.get("before")) >= 1,  # (real pairs only: a wedding build put
    # a night stage "before" a sky "after"; the content gives an item's "before" photo when the work really has one)
}


def fits(name, sec):
    """Whether a section's content suits a block: its item count, photos where they are needed, and what its items
    must really be (NEED: prices for a price block, numbers for a numbers block, days for a timetable)."""
    b = BLOCKS.get(name)
    if not b:
        return False
    its = _items(sec, hi=99)
    lo, hi = b["needs"]["items"]
    if hi and not lo <= len(its) <= max(hi, lo):  # ((0, 0): the block draws from the section's own words)
        return False
    if b["needs"]["photo"] == "needed" and len(_pics(sec)) < max(1, b["needs"].get("pics", 0)):
        return False
    need = NEED.get(name) or (NEED.get(b["role"]) if name != "proof.results" else None)
    if need and its and not need(its):
        return False
    return True




def draw(name, sec, ctx):
    return BLOCKS[name]["draw"](sec, ctx)


def by_role(role):
    return [n for n, b in BLOCKS.items() if b["role"] == role]


def candidates(role, sec):
    """The blocks of a role that this section's content fits, the ones its photos make first."""
    names = [n for n in by_role(role) if fits(n, sec)]
    has = bool(_pics(sec))
    if not has and any(BLOCKS[n]["needs"]["photo"] == "none" for n in names):
        # (no photos: a composition made for photos draws big empty monograms (a dental page's doctors were three pale
        # arches "DR · DP · DS"); the designs made to stand without photos are the premium choice then)
        names = [n for n in names if BLOCKS[n]["needs"]["photo"] == "none"]
    return sorted(names, key=lambda n: (0 if has and BLOCKS[n]["needs"]["photo"] in ("needed", "better") else 1
                                        if not has and BLOCKS[n]["needs"]["photo"] == "none" else 2))


def describe(name):
    """A block's composition in words (weights.py), for the 4B choosing."""
    import weights
    w = weights.W.get(name) or {}
    return w.get("structure") or name


def from_hero(plan):
    """The page plan's hero as a block's section: its title with its accent words, eyebrow, lead, two actions, the
    proof numbers as items, its photo first and the page's other photos after (a hero of two faces needs two)."""
    h = plan.get("hero") or {}
    title = " ".join(x for x in (str(h.get("title") or "").strip(), str(h.get("accent") or "").strip()) if x)
    acts_ = [str(a) for a in h.get("actions") or [] if str(a).strip()]
    stats = []
    for st in h.get("stats") or []:
        if isinstance(st, dict) and st.get("label") not in (None, "") and st.get("value") not in (None, ""):
            v = st["value"]
            v = int(v) if isinstance(v, float) and v == int(v) else v
            stats.append({"title": str(st["label"]), "badge": f"{v}{st.get('suffix') or ''}"})
    # the hero's other pictures: the page's real pictures first (its gallery, its offer), a stats card's last
    order = {"gallery": 0, "image_cards": 1}
    more = [it.get("photo") for s in sorted(plan.get("sections") or [], key=lambda s: order.get(s.get("part"), 2))
            for it in s.get("items") or [] if isinstance(it, dict) and it.get("photo")]
    brand = (plan.get("brand") or {}).get("name") or ""
    return {"title": title, "eyebrow": h.get("eyebrow") or "", "lead": h.get("lead") or "", "brand": brand,
            "button": acts_[0] if acts_ else "", "button2": acts_[1] if len(acts_) > 1 else "",
            "badge": stats[0]["badge"] + " " + stats[0]["title"] if stats else "", "photo": h.get("photo") or "",
            "photos": list(dict.fromkeys(p for p in more if p != h.get("photo")))[:5], "items": stats, "icon": (plan.get("brand") or {}).get("icon")}


def from_action(plan, sec):
    """A closing section as an action block's section: its words, its button, the brand, the page's photos and the
    other sections' names as the links of a closing panel."""
    more = [it.get("photo") for s in plan.get("sections") or [] for it in s.get("items") or [] if isinstance(it, dict) and it.get("photo")]
    links = [{"title": s.get("title")} for s in plan.get("sections") or [] if s is not sec and s.get("title")][:6]
    btn = str(sec.get("button") or "").strip().lower()
    own = [it for it in sec.get("items") or [] if isinstance(it, dict) and str(it.get("title") or "").strip().lower() not in ("", btn)
           and str(it.get("title") or "").strip().lower() not in [str(a).strip().lower() for a in (plan.get("hero") or {}).get("actions") or []]]
    hero_acts = [str(a) for a in (plan.get("hero") or {}).get("actions") or [] if str(a).strip()]
    return dict(sec, brand=(plan.get("brand") or {}).get("name") or "", button=sec.get("button") or (hero_acts[0] if hero_acts else ""),
                photos=list(dict.fromkeys(more))[:6], items=own or links)
