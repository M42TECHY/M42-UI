"""🔍 An edit seen on the page, before and after (the user, 2026-11-16: "a dynamic edit approach that works for every
page": four photos were found but one showed, an animation was added that looked the same as before, and M42 said
both were done).

Every edit runs the same loop (agent.edit_site): the 4B says what the visitor should SEE when it is done (expected),
M42 does the change, then this module measures the page as drawn (headless Chrome: each part's photos, its repeated
things (cards, rows), its words, buttons, how it moves) and takes its picture, before and after. The facts are
counted here, never judged: what they mean for the user's words is the 4B's call (agent._judge_edit), and when it is
not done the 4B picks another way to draw or move the part from OPTIONS (data: what each way shows), tried again.

No word lists here: facts only (a picture's size on the page, a card's words, which motion a part has).
"""
import contextlib
import html as htmlmod
import json
import os
import re
import subprocess
import uuid
from pathlib import Path

FACTS_JS = r"""<script>window.M42_STILL=1;(function(){
function txt(e){return ((e&&e.innerText)||'').replace(/\s+/g,' ').trim();}
function seen(x){var b=x.getBoundingClientRect(),c=getComputedStyle(x);return b.width>=40&&b.height>=40&&c.display!=='none'&&c.visibility!=='hidden'&&+c.opacity>0;}
function run(){
var H=document.documentElement,sy=window.scrollY||0;
var all=[].slice.call(document.querySelectorAll('nav.m42-nav, header, section, footer'));
var secs=all.filter(function(s){return !all.some(function(o){return o!==s&&o.contains(s);});});
var pageReveal=H.getAttribute('data-m42-motion')==='none'?'none':(H.getAttribute('data-m42-reveal')||'none');
var pageHover=H.getAttribute('data-m42-hover')||'none';
var out=secs.map(function(s,i){
 var r=s.getBoundingClientRect();
 var imgs=[].slice.call(s.querySelectorAll('img')).filter(seen).map(function(im){var b=im.getBoundingClientRect();
  return {src:im.getAttribute('src')||'',w:Math.round(b.width),h:Math.round(b.height)};});
 var best=[];
 [].slice.call(s.querySelectorAll('*')).forEach(function(p){if(p.children.length<2)return;var g={};
  [].forEach.call(p.children,function(c){var k=c.tagName+'.'+(c.classList[0]||'');(g[k]=g[k]||[]).push(c);});
  Object.keys(g).forEach(function(k){if(g[k].length>=2&&g[k].length>best.length&&g[k].some(function(c){return txt(c);}))best=g[k];});});
 var cards=best.slice(0,12).map(function(c){var im=[].filter.call(c.querySelectorAll('img'),seen)[0];
  return {text:txt(c).slice(0,100),photo:im?(im.getAttribute('src')||''):''};});
 var own=s.getAttribute('data-m42-sec-reveal'),ownH=s.getAttribute('data-m42-sec-hover');
 var R=window.M42Reveal;
 return {key:s.id||(s.tagName.toLowerCase()+'-'+i),tag:s.tagName.toLowerCase(),
  title:txt(s.querySelector('h1,h2')).slice(0,90),eyebrow:txt(s.querySelector('.m42-eyebrow')).slice(0,60),
  block:s.getAttribute('data-m42-block')||s.getAttribute('data-m42-comp')||'',
  text:txt(s).slice(0,1200),imgs:imgs.slice(0,16),cards:cards,
  buttons:[].slice.call(s.querySelectorAll('a.m42-btn,a.m42-btn-ghost,button,.btn')).map(txt).filter(Boolean).slice(0,8),
  reveal:own||pageReveal,own_reveal:own||'',hover:ownH||pageHover,own_hover:ownH||'',
  moving:R?R.items(s).length:0,hovering:R?R.hoverItems(s).length:0,
  top:Math.round(r.top+sy),height:Math.round(r.height)};});
var cs=getComputedStyle(H),bs=getComputedStyle(document.body);
var page={motion:H.getAttribute('data-m42-motion')||'',reveal:pageReveal,hover:pageHover,
 hero_in:H.getAttribute('data-m42-hero-in')||'',theme:H.getAttribute('data-m42-theme')||'',
 accent:(cs.getPropertyValue('--m42-accent')||cs.getPropertyValue('--bs-primary')||'').trim(),
 bg:bs.backgroundColor,font:(bs.fontFamily||'').split(',')[0],
 brand:txt(document.querySelector('.navbar-brand,.m42-brand')).slice(0,60),title:document.title,
 height:Math.round(Math.max(H.scrollHeight,document.body.scrollHeight))};
var p=document.createElement('pre');p.id='__m42_facts';p.style.display='none';
p.textContent=JSON.stringify({page:page,sections:out});document.body.appendChild(p);}
addEventListener('load',function(){setTimeout(run,400);});})();</script>"""

WIDTH = 1280
FIRST_HEIGHT = 6000  # the window: the page's facts and its picture are measured in the same one
MAX_HEIGHT = 12000


def _copy(page):
    """A copy of the page next to it (its relative paths work) with the facts script, motion settled, every photo
    loaded now (a lazy photo below the window never loads in a headless picture)."""
    page = Path(page)
    text = page.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r'\sloading="lazy"', "", text)
    m = re.search(r"<head\b[^>]*>", text, re.I)
    text = text[:m.end()] + FACTS_JS + text[m.end():] if m else FACTS_JS + text
    tmp = page.with_name(f".m42-see-{uuid.uuid4().hex[:8]}.html")
    tmp.write_text(text, encoding="utf-8")
    return tmp


def _chrome(args, timeout=60):
    """Headless Chrome with its own empty profile: two Chromes on one profile hand the page to the first and exit
    at once (the app's own browser check ran beside this one, 2026-11-16: "the page could not be opened")."""
    import tempfile

    import browser
    exe = browser.find_browser()
    if not exe:
        return None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(prefix="m42-see-") as profile:
        try:
            return subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                                   "--no-default-browser-check", "--disable-extensions", "--mute-audio",
                                   "--allow-file-access-from-files", f"--user-data-dir={profile}"] + args,
                                  capture_output=True, timeout=timeout, creationflags=flags)
        except (OSError, subprocess.TimeoutExpired):
            return None


def _facts_at(tmp, height):
    r = _chrome([f"--window-size={WIDTH},{height}", "--virtual-time-budget=3000", "--dump-dom", tmp.resolve().as_uri()])
    if not r:
        return None
    m = re.search(r'<pre id="__m42_facts"[^>]*>(.*?)</pre>', r.stdout.decode("utf-8", "replace"), re.S)
    if not m:
        return None
    try:
        return json.loads(htmlmod.unescape(m.group(1)))
    except ValueError:
        return None


def see(page, picture=True):
    """The page as drawn: {"page": {...}, "sections": [...], "image": PIL image or None, "window": height}, or None when
    no browser could open it. Each section: key, title, eyebrow, block, text, imgs (photos a visitor sees, 40 px and
    more, their files checked), cards (its largest group of repeated things, each with its words and photo), buttons,
    reveal / hover (its own or the page's), moving / hovering (how many of its things move), top / height."""
    page = Path(page)
    if not page.is_file():
        return None
    tmp = _copy(page)
    try:
        height = FIRST_HEIGHT
        got = _facts_at(tmp, height)
        if got and got["page"].get("height", 0) > height + 40:
            height = min(MAX_HEIGHT, got["page"]["height"] + 40)
            got = _facts_at(tmp, height) or got
        if not got:
            return None
        for s in got["sections"]:  # a photo whose file is missing shows a broken box: not a photo
            for im in s["imgs"]:
                im["file"] = _exists(page, im["src"])
            s["imgs"] = [im for im in s["imgs"] if im["file"]]
            for c in s["cards"]:
                if c["photo"] and not _exists(page, c["photo"]):
                    c["photo"] = ""
        got["window"] = height
        got["image"] = _picture(tmp, height) if picture else None
        return got
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def _exists(page, src):
    if not src or src.startswith(("data:", "http:", "https:", "//")):
        return bool(src)
    return (page.parent / src.split("?")[0].split("#")[0]).is_file()


def _picture(tmp, height):
    out = tmp.with_suffix(".png")
    try:
        _chrome([f"--window-size={WIDTH},{height}", "--virtual-time-budget=3000", f"--screenshot={out}", tmp.resolve().as_uri()], 90)
        if not out.is_file():
            return None
        from PIL import Image
        im = Image.open(out)
        im.load()
        return im.convert("RGB")
    except (ImportError, OSError, ValueError):
        return None
    finally:
        with contextlib.suppress(OSError):
            out.unlink()


# ------------------------------------------------------------------------------------------- which part is which
def _norm(s):
    return " ".join(str(s or "").lower().split())


def section_key(seen, sec, k):
    """The drawn section of a plan section: by its title, else the k-th section between the hero and the footer."""
    if not seen:
        return ""
    t = _norm(sec.get("title")) if isinstance(sec, dict) else ""
    if t:
        for s in seen["sections"]:
            if _norm(s["title"]) == t:
                return s["key"]
    mids = [s for s in seen["sections"] if s["tag"] == "section"]
    return mids[k]["key"] if 0 <= k < len(mids) else ""


def _by_key(seen):
    return {s["key"]: s for s in (seen or {}).get("sections") or []}


# --------------------------------------------------------------------------------------------- facts in words
WORD_RX = re.compile(r"[₹$€£]\s?[\d,]+(?:\.\d+)?|\d[\d,.]*%?|[^\W\d_][\w&'’-]{2,}", re.U)


def _words(text):
    return set(WORD_RX.findall(text or ""))


def describe(s):
    """One drawn part in plain words, for the 4B."""
    if not s:
        return "(not on the page)"
    name = s["title"] or s["eyebrow"] or s["key"]
    with_photo = sum(1 for c in s["cards"] if c["photo"])
    cards = (f'{len(s["cards"])} repeated things (cards / rows), {with_photo} of them with their own photo: '
             + "; ".join(f'[{c["text"][:70]}{" · photo " + c["photo"].split("/")[-1] if c["photo"] else " · no photo"}]'
                         for c in s["cards"][:8])) if s["cards"] else "no repeated things"
    loose = [im for im in s["imgs"] if not any(im["src"] == c["photo"] for c in s["cards"])]
    return (f'"{name}" ({s["tag"]}{", design " + s["block"] if s["block"] else ""}): {len(s["imgs"])} photo(s) shown'
            + (f' ({len(loose)} outside the cards: ' + ", ".join(f'{im["src"].split("/")[-1]} {im["w"]}x{im["h"]}' for im in loose[:3]) + ")" if loose else "")
            + f"; {cards}"
            + (f'; buttons: {", ".join(s["buttons"][:5])}' if s["buttons"] else "")
            + f'; comes in with "{s["reveal"]}"' + (" (its own)" if s["own_reveal"] else " (as the page)")
            + f', {s["moving"]} of its things move in; hover "{s["hover"]}"' + (" (its own)" if s["own_hover"] else " (as the page)")
            + f', {s["hovering"]} things react to the mouse; {s["height"]} px tall')


def compare(before, after, targets=()):
    """What changed between two looks at a page: (lines about the target parts, lines about OTHER parts that changed,
    keys of the other parts that changed). Facts only."""
    b, a = _by_key(before), _by_key(after)
    tl, ol, okeys = [], [], []
    pb, pa = (before or {}).get("page") or {}, (after or {}).get("page") or {}
    page_d = [f"{k} {pb.get(k)!r} -> {pa.get(k)!r}" for k in ("theme", "accent", "bg", "font", "brand", "title", "reveal", "hover", "hero_in", "motion")
              if pb.get(k) != pa.get(k)]
    if page_d:
        tl.append("The whole page: " + "; ".join(page_d))
    for key in list(dict.fromkeys(list(b) + list(a))):
        x, y = b.get(key), a.get(key)
        if x and not y:
            line = f'"{x["title"] or key}": taken off the page'
        elif y and not x:
            line = f'"{y["title"] or key}": new on the page: {describe(y)}'
        else:
            d = []
            for f in ("title", "eyebrow", "block"):
                if x[f] != y[f]:
                    d.append(f"{f} {x[f]!r} -> {y[f]!r}")
            if len(x["imgs"]) != len(y["imgs"]) or [i["src"] for i in x["imgs"]] != [i["src"] for i in y["imgs"]]:
                d.append(f'photos shown {len(x["imgs"])} -> {len(y["imgs"])}')
            cx, cy = (len(x["cards"]), sum(1 for c in x["cards"] if c["photo"])), (len(y["cards"]), sum(1 for c in y["cards"] if c["photo"]))
            if cx != cy:
                d.append(f"repeated things {cx[0]} ({cx[1]} with a photo) -> {cy[0]} ({cy[1]} with a photo)")
            gone, new = sorted(_words(x["text"]) - _words(y["text"])), sorted(_words(y["text"]) - _words(x["text"]))
            if gone:
                d.append("words no longer shown: " + ", ".join(gone[:18]) + (" ..." if len(gone) > 18 else ""))
            if new:
                d.append("new words: " + ", ".join(new[:18]) + (" ..." if len(new) > 18 else ""))
            if x["buttons"] != y["buttons"]:
                d.append(f'buttons {x["buttons"][:5]} -> {y["buttons"][:5]}')
            for f in ("reveal", "hover"):
                if x[f] != y[f]:
                    d.append(f"{f} {x[f]!r} -> {y[f]!r}")
            if x["moving"] != y["moving"]:
                d.append(f'things moving in {x["moving"]} -> {y["moving"]}')
            if abs(x["height"] - y["height"]) > 60:
                d.append(f'height {x["height"]} -> {y["height"]} px')
            if not d:
                if key in targets:
                    tl.append(f'"{y["title"] or key}": NOTHING changed: {describe(y)}')
                continue
            line = f'"{y["title"] or key}": ' + "; ".join(d)
        if key in targets:
            tl.append(line + (f"\n   now: {describe(a.get(key))}" if a.get(key) else ""))
        else:
            ol.append(line)
            okeys.append(key)
    return tl, ol, okeys


# ---------------------------------------------------------------------------------------------------- pictures
def pair_image(before, after, keys):
    """The changed parts before (left) and after (right), side by side: a PIL image or None."""
    ib, ia = (before or {}).get("image"), (after or {}).get("image")
    if ib is None and ia is None:
        return None
    b, a = _by_key(before), _by_key(after)

    def cut(im, s):
        if im is None or not s or s["height"] <= 0:
            return None
        top, bot = max(0, s["top"]), min(im.height, s["top"] + min(s["height"], 1600))
        return im.crop((0, top, im.width, bot)) if bot - top > 20 else None

    from PIL import Image
    rows = []
    for k in keys[:2]:
        L, R = cut(ib, b.get(k)), cut(ia, a.get(k))
        if L is None and R is None:
            continue
        w = (L or R).width
        L = L or Image.new("RGB", (w, 120), "white")
        R = R or Image.new("RGB", (w, 120), "white")
        side = Image.new("RGB", (L.width + R.width + 30, max(L.height, R.height)), (200, 200, 200))
        side.paste(L, (0, 0))
        side.paste(R, (L.width + 30, 0))
        rows.append(side)
    if not rows:
        return None
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + 30 * (len(rows) - 1)), (200, 200, 200))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + 30
    return out


# ----------------------------------------------------------------------------------------- the side-effect guard
def _section_span(text, key):
    """(start, end) of <section id="key" ...>...</section> in the page, nested sections counted."""
    m = re.search(r'<section\b[^>]*\bid="' + re.escape(key) + r'"[^>]*>', text)
    if not m:
        return None
    depth, i = 1, m.end()
    for t in re.finditer(r"<(/?)section\b[^>]*>", text[i:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return m.start(), i + t.end()
    return None


def restore_sections(new_text, old_text, keys):
    """The parts the user did not ask about put back as they were (a CTA took another section's new photo,
    2026-11-16). Returns (text, the keys put back)."""
    done = []
    for key in keys:
        a, b = _section_span(new_text, key), _section_span(old_text, key)
        if a and b:
            new_text = new_text[:a[0]] + old_text[b[0]:b[1]] + new_text[a[1]:]
            done.append(key)
    return new_text, done


# --------------------------------------------------------------------------------- the ways a part can be drawn
# what each way of drawing a list of things SHOWS (pagebuild's theme layouts): the 4B chooses one that can show what
# the user asked (data, the facts of each layout's code)
LAYOUT_SHOWS = {
    "grid": "a grid of cards: each card its own photo, name, words and price (up to 8)",
    "zigzag": "big rows changing sides: each thing its own photo, name, words and price (up to 6)",
    "carousel": "a sliding row of tall cards: each its own photo, name, words and price (up to 10)",
    "stage": "big half-circles, one per thing: each its own photo, name, words and price (up to 4)",
    "collage": "up to 4 photos overlapping beside a short list of names and words (no prices)",
    "spotlight": "ONE tall photo beside a numbered list of names, words and prices",
    "orbit": "ONE big photo in the middle, the names and words round it (no prices)",
    "watermark": "ONE photo beside a numbered list of the names only (no words, no prices)",
}
LAYOUT_PARTS = ("cards", "image_cards", "features")
REVEAL_SHOWS = {
    "none": "no entrance",
    "fade-up": "its heading and things fade in, moving up a little, together",
    "stagger": "its cards / rows come in one after another, rising",
    "zoom": "its things grow in from a little smaller",
}
HOVER_SHOWS = {
    "none": "nothing under the mouse",
    "lift": "a card rises a little under the mouse",
    "tilt": "a card tilts in 3D under the mouse",
    "glow": "a card glows in the brand colour under the mouse",
}


def options(sec, drawn, page_facts):
    """The ways this part can be drawn and move, in words, and the enums for the 4B's choice."""
    lines, layouts, blocks_ = [], [], []
    if sec.get("part") in LAYOUT_PARTS:
        layouts = list(LAYOUT_SHOWS)
        lines.append("layout (how its things are laid out; now " + (sec.get("_layout") or "the theme's own") + "):")
        lines += [f"  {k}: {v}" for k, v in LAYOUT_SHOWS.items()]
    if sec.get("_block") or sec.get("_alts"):
        import blocks as blk
        blocks_ = [n for n in [sec.get("_block")] + list(sec.get("_alts") or []) if n in blk.BLOCKS]
        if blocks_:
            lines.append(f'block (its premium design; now {sec.get("_block") or "none"}):')
            lines += [f'  {n}: {blk.describe(n)[:150]} (photos: {blk.BLOCKS[n]["needs"].get("photo")})' for n in blocks_]
    pr, ph = (page_facts or {}).get("reveal", "fade-up"), (page_facts or {}).get("hover", "lift")
    now_r, now_h = (drawn or {}).get("reveal", pr), (drawn or {}).get("hover", ph)
    lines.append(f'reveal (how it comes in when scrolled to; this part now "{now_r}", the rest of the page "{pr}"):')
    lines += [f"  {k}: {v}" for k, v in REVEAL_SHOWS.items()]
    lines.append(f'hover (how its cards answer the mouse; this part now "{now_h}", the rest of the page "{ph}"):')
    lines += [f"  {k}: {v}" for k, v in HOVER_SHOWS.items()]
    return "\n".join(lines), layouts, blocks_
