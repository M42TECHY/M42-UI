"""Real photos for the pages M42 UI builds (the hero, product / menu cards, blog and portfolio covers, the gallery):
searched on free photo libraries, downloaded into the site's images/ folder (so the site still works offline),
made smaller, and credited in images/CREDITS.txt and the page footer.

Sources, in order (the user, 2026-11-05: "Pexels + Pixabay"):
- Pexels (pexels.com/api): free API key, Settings → pexels_key. Credit the photographer and Pexels.
- Pixabay (pixabay.com/api/docs): free API key, Settings → pixabay_key. Its terms ask for downloaded copies
  (no hot-linking), which is what this does.
- No key, all online and free (the user, 2026-11-11: "online first, no offline photo pack"):
  1. StockSnap's CC0 photos (stocksnap.io, from the user's stock list: free to use, no credit needed), searched through
     Openverse (api.openverse.org);
  2. Wikimedia Commons (its own API: answers in about a second when Openverse gives 504s or takes 10-16 s): photos
     whose licence allows commercial use and changes (CC0, public domain, CC BY, CC BY-SA), wide ones, no logos;
  3. the rest of Openverse, the same licences.
  Every photo is credited as its licence asks (images/CREDITS.txt and the footer).
Unsplash is not used: its API terms require showing the photos from its own servers (no offline copies).

No faces for people: a "team" card keeps its initials (a stock photo would pass off a stranger as the team)."""
import concurrent.futures
import hashlib
import threading
import time
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = "M42-UI (local website builder)"
PEOPLE_RX = re.compile(r"\b(team|founder|ceo|staff|baristas?|chefs?|doctors?|teachers?|members?|people|about us)\b", re.I)
FILLER_RX = re.compile(r"\b(i|need|want|this|that|like|same|please|give|me|us|landing|page|website|web|site|pannu|panni|venum|vennum|oru|create|make|build|design|ui|ux|app|tracking|sharing|"
                       r"for|with|the|a|an|my|our|and|home|homepage|template|modern|premium|nalla|super)\b", re.I)


def _get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def pexels(query, key, orientation="landscape"):
    q = urllib.parse.urlencode({"query": query, "per_page": 6, "orientation": orientation})
    data = json.loads(_get(f"https://api.pexels.com/v1/search?{q}", {"Authorization": key}))
    return [{"url": p["src"]["large2x" if orientation == "landscape" else "large"], "by": p.get("photographer") or "",
             "page": p.get("url") or "", "source": "Pexels", "licence": "Pexels licence", "alt": p.get("alt") or query}
            for p in data.get("photos") or []]


def pixabay(query, key, orientation="horizontal"):
    q = urllib.parse.urlencode({"key": key, "q": query[:100], "image_type": "photo", "safesearch": "true",
                                "per_page": 6, "orientation": orientation})
    data = json.loads(_get(f"https://pixabay.com/api/?{q}"))
    return [{"url": h.get("largeImageURL") or h.get("webformatURL"), "by": h.get("user") or "", "page": h.get("pageURL") or "",
             "source": "Pixabay", "licence": "Pixabay content licence", "alt": h.get("tags") or query}
            for h in data.get("hits") or []]


OPENVERSE_OK = {"cc0", "pdm", "by", "by-sa"}


OPENVERSE_DOWN = {"until": 0.0}  # Openverse answered 504 or nothing in 10-16 s (2026-11-11): skipped a while after


def openverse(query, orientation="wide", source=""):
    if time.time() < OPENVERSE_DOWN["until"]:
        return []
    args = {"q": query, "license_type": "commercial,modification", "page_size": 8, "category": "photograph",
            "aspect_ratio": orientation, "mature": "false"}  # (photographs: no diagrams / posters)
    if source:
        args = {"q": query, "source": source, "license": "cc0", "page_size": 8, "mature": "false"}
    try:
        data = json.loads(_get(f"https://api.openverse.org/v1/images/?{urllib.parse.urlencode(args)}", timeout=15))
    except (OSError, ValueError):
        OPENVERSE_DOWN["until"] = time.time() + 300  # the page's other photos from Wikimedia Commons, not 15 s each
        raise
    out = []
    for r in data.get("results") or []:
        lic = str(r.get("license") or "").lower()
        if lic in OPENVERSE_OK and r.get("url"):
            out.append({"url": r["url"], "by": r.get("creator") or "", "page": r.get("foreign_landing_url") or "",
                        "source": r.get("source") or "Openverse",
                        "licence": ("CC0" if lic == "cc0" else "public domain" if lic == "pdm" else f"CC {lic.upper()}")
                        + (f" {r.get('license_version')}" if r.get("license_version") and lic not in ("cc0", "pdm") else ""),
                        "alt": r.get("title") or query})
    return out


COMMONS_OK_RX = re.compile(r"^(cc0|public domain|pd\b|cc by(-sa)? \d)", re.I)
TAG_RX = re.compile(r"<[^>]+>")


def commons(query, wide=True):
    """Wikimedia Commons photos for the search: free licences that allow commercial use and changes, wide (or square
    for a card), 1280 px from Commons' own resizer, no logos or maps."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 12,
                                "gsrsearch": f"{query} filetype:bitmap", "prop": "imageinfo",
                                "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1280})
    data = json.loads(_get(f"https://commons.wikimedia.org/w/api.php?{q}", timeout=15))
    out = []
    for pg in sorted(((data.get("query") or {}).get("pages") or {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = str((meta.get("LicenseShortName") or {}).get("value") or "")
        w, h = ii.get("width") or 0, ii.get("height") or 0
        if (not COMMONS_OK_RX.match(lic.strip()) or ii.get("mime") != "image/jpeg" or w < 1000
                or (wide and w < h * 1.25) or re.search(r"\b(logo|map|diagram|chart|poster|sign)\b", pg.get("title", ""), re.I)):
            continue
        out.append({"url": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl") or "",
                    "by": " ".join(TAG_RX.sub(" ", str((meta.get("Artist") or {}).get("value") or "")).split())[:80],
                    "source": "Wikimedia Commons", "licence": lic,
                    "alt": re.sub(r"\.(jpe?g)$", "", str(pg.get("title", ""))[5:], flags=re.I)[:90] or query})
    return out


def search(query, keys, wide=True):
    """Candidates for one photo: Pexels, then Pixabay (with their keys); without a key, online and free: StockSnap's
    CC0 photos, then Wikimedia Commons, then the rest of Openverse."""
    found = []
    if keys.get("pexels_key"):
        try:
            found += pexels(query, keys["pexels_key"], "landscape" if wide else "square")
        except (OSError, ValueError, KeyError):
            pass
    if len(found) < 2 and keys.get("pixabay_key"):
        try:
            found += pixabay(query, keys["pixabay_key"], "horizontal" if wide else "all")
        except (OSError, ValueError, KeyError):
            pass
    if not found and not (keys.get("pexels_key") or keys.get("pixabay_key")):
        try:
            found += openverse(query, source="stocksnap")
        except (OSError, ValueError, KeyError):
            pass
        if len(found) < 2:
            try:
                found += commons(query, wide)
            except (OSError, ValueError, KeyError):
                pass
        if not found:
            try:
                found += openverse(query, "wide" if wide else "square")
            except (OSError, ValueError, KeyError):
                pass
    return found


def save(cand, folder, name, width):
    """The photo downloaded, made at most `width` wide (JPEG), in folder/name.jpg. Returns the file name or None."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(_get(cand["url"], timeout=30)))
        im = im.convert("RGB")
    except (OSError, ValueError):
        return None
    if im.width < 320:
        return None
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)))
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{name}.jpg"
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out.name


CUT_RX = re.compile(r"\b(showcasing|showing|with|featuring|that|which|offering|selling|having|including|where|"
                    r"to|in|at|near|using)\b.*$", re.I)


def subject(request):
    """The site's subject from the request: "bakery landing page pannu" -> "bakery", "Design a landing page for a
    Local Bakery showcasing daily specials." -> "Local Bakery" (the whole sentence found no photo). A request that
    names no topic carries the one read from the user's picture ("i need this with UX (about: recipe sharing and
    tracking app, ...)"): that topic, not "i need this" (which found a shop sign and a car sticker, 2026-11-12)."""
    import webkit
    if webkit.INTENT.get("subject"):  # what the page is about, as the model read the request (and its picture)
        return " ".join(str(webkit.INTENT["subject"]).split())[:40]
    m = re.search(r"\(about:\s*([^,()]+)", request or "")
    if m:
        request = m.group(1)
    text = CUT_RX.sub(" ", re.sub(r"[^\w\s&-]", " ", request or ""))
    return " ".join(FILLER_RX.sub(" ", text).split())[:40]


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:40]
    return s or hashlib.md5(str(text).encode()).hexdigest()[:8]


PHOTO_PARTS = {"image_cards": 600, "cards": 720, "blog_cards": 720, "portfolio": 720, "gallery": 720}


def wanted(plan, request):
    """(where to put it, the search words, wide, width) for every photo a page plan can use."""
    subj = subject(request)
    out = []
    hero = plan.get("hero") or {}
    # the 4B's words given to many cards at once are no card's own (a real build gave all 14 cards "wedding planner":
    # one search ran out of photos on the stats cards and the portfolio got none): those cards search their own words
    said = [" ".join(str(it.get("_q") or "").lower().split()) for sec in plan.get("sections") or [] for it in sec.get("items") or []
            if isinstance(it, dict) and it.get("_q")]
    shared = {q for q in said if said.count(q) > 2}
    if hero and subj:  # the subject alone: "bakery Baked to perfection" found a grey street photo
        out.append((("hero",), str(hero.get("_q") or "").strip() or subj, True, 1600))
    for n, sec in enumerate(plan.get("sections") or []):
        blocks = set((sec.get("_look") or {}).get("blocks") or [])
        if sec.get("part") == "composed" and blocks & {"photo", "round photo", "cut-out person photo"} and sec.get("title"):
            # a reference card with its own photo (a dish beside its name, a person on a banner): the card's words
            q = f"{sec['title']} {subj}".strip() if subj.lower() not in str(sec["title"]).lower() else str(sec["title"])
            out.append((("secphoto", n), q, "photo" in blocks, 900 if "photo" in blocks else 600))
        width = PHOTO_PARTS.get(sec.get("part")) or (720 if sec.get("part") == "composed" and (sec.get("_look") or {}).get("photos")
                                                      and blocks & {"rows", "tile grid"} and not blocks & {"round photo", "cut-out person photo"} else None)
        if not width or PEOPLE_RX.search(f"{sec.get('title')} {sec.get('eyebrow')}"):
            continue
        for k, it in enumerate((sec.get("items") or [])[:8]):
            title = str(it.get("title") or "").strip()
            if title and not PEOPLE_RX.search(title):
                q = title if subj.lower() in title.lower() else f"{title} {subj}".strip()
                own = str(it.get("_q") or "").strip()
                q = own if own and " ".join(own.lower().split()) not in shared else q  # (the 4B's words: agent._photo_words)
                out.append((("sections", n, "items", k), q, sec.get("part") != "image_cards", width))
    # the pictures a page is about search first (its gallery, its offer), the cards a picture only decorates after
    first = {"gallery": 0, "image_cards": 1}
    return sorted(out, key=lambda j: (0 if j[0][0] in ("hero", "secphoto") else 1 + first.get(
        ((plan.get("sections") or [])[j[0][1]] or {}).get("part"), 2)))


def add_to_plan(plan, request, root, keys, emit=None, cache=None):
    """The plan's hero and items get a "photo" (images/<name>.jpg), found and downloaded in parallel. Returns the
    credits [{file, by, source, licence, page}]. cache: {search words: file} shared by the pages of one site."""
    cache = {} if cache is None else cache
    folder = Path(root) / "images"
    jobs = wanted(plan, request)
    used, lock = set(), threading.Lock()  # (six hotel rooms: six photos, not one search's first photo six times)
    names = set()  # the files given out on this page: four cards with the same words wrote one file over each other,
    # and when the look took it off one card the other three showed a broken picture (2026-11-14)

    subj = subject(request)

    def one(job):
        where, q, wide, width = job
        if q in cache:
            return where, cache[q], None
        got = _one(where, q, wide, width)
        if got[1] is None and where[0] == "sections" and subj and q.endswith(subj) and len(q) > len(subj) + 2:
            got = _one(where, q[:-len(subj)].strip(), wide, width)  # ("Sunset Cruise hotel": nothing; "Sunset Cruise")
            if got[2]:
                got[2]["query"] = q
        if got[1] is None and where[0] == "sections" and len(where) == 4:  # (the card's own name alone: the 4B's
            # "master bedroom ceiling fan spinning" found nothing, "Ceiling Fan" finds nine, 2026-11-18)
            try:
                own = str(plan["sections"][where[1]]["items"][where[3]].get("title") or "").strip()
            except (IndexError, KeyError, TypeError):
                own = ""
            if own and " ".join(own.lower().split()) != " ".join(q.lower().split()):
                got = _one(where, own, wide, width)
                if got[2]:
                    got[2]["query"] = q
        return got

    def _one(where, q, wide, width):
        words = q.split()
        # fewer words when nothing is found ("Custom T-Shirt Design Tool" -> "T-Shirt Design Tool" -> ...)
        # (the hero only: a card that drops its own words would get the site's generic photo)
        shortest = max(0, len(words) - 3) if where[0] == "hero" else len(words) - 1
        for n in range(len(words), shortest, -1):
            found = search(" ".join(words[len(words) - n:]), keys, wide)
            for k, cand in enumerate(found[:6]):
                with lock:
                    if cand["url"] in used:
                        continue
                    used.add(cand["url"])
                with lock:
                    stem, n_ = _slug(q), 2
                    while stem in names:
                        stem, n_ = f"{_slug(q)}-{n_}", n_ + 1
                    names.add(stem)
                name = save(cand, folder, stem, width)
                if name:
                    # the hero's next photos: the vision check takes one of them when this one is not about the site
                    # (the vision check takes one of them when this one is not about it: the hero's and every card's)
                    alts = [c for c in found[k + 1:k + 4] if c["url"] not in used]
                    return where, f"images/{name}", dict(cand, file=f"images/{name}", query=q, alts=alts, width=width)
            if found:
                break
        return where, None, None

    credits, got = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        got = list(pool.map(one, jobs))
    # a card with no photo of its own, in a section where most have one: another photo of the site's subject (and the
    # section's), not every card's photo dropped (2026-11-12: a fire crackers gallery had 2 of 3 photos and showed
    # three icon tiles, the same tiles as a hotel's rooms and a bakery's specials)
    by_sec = {}
    for k, (where, path, _c) in enumerate(got):
        if where[0] == "sections":
            by_sec.setdefault(where[1], []).append(k)
    for n, ks in by_sec.items():
        missing = [k for k in ks if not got[k][1]]
        if not missing or len(missing) * 2 > len(ks):
            continue
        sec = (plan.get("sections") or [])[n]
        pool_q = [q for q in (f"{sec.get('title') or ''} {subj}".strip(), subj) if q]
        cands = []
        for q in dict.fromkeys(pool_q):
            cands += search(q, keys, jobs[missing[0]][2])
        for k in missing:
            where, q, wide, width = jobs[k]
            for cand in cands:
                with lock:
                    if cand["url"] in used:
                        continue
                    used.add(cand["url"])
                name = save(cand, folder, _slug(q), width)
                if name:
                    got[k] = (where, f"images/{name}", dict(cand, file=f"images/{name}", query=q))
                    break
    # a section's cards all with photos or none (photos on 2 of 4 cards and icons on the others looked broken)
    whole = {}
    for where, path, _ in got:
        if where[0] == "sections":
            whole.setdefault(where[1], []).append(bool(path))
    for where, path, credit in got:
        if not path or (where[0] == "sections" and not all(whole[where[1]])):
            continue
        target = plan
        for step in where[:-1] if where[0] not in ("hero", "secphoto") else ():
            target = target[step]
        if where[0] == "secphoto":
            plan["sections"][where[1]]["photo"] = path
        elif where[0] == "hero":
            plan.setdefault("hero", {})["photo"] = path
        else:
            target[where[-1]]["photo"] = path
        if credit:
            cache[credit["query"]] = path
            credits.append(credit)
    if emit and jobs:
        emit({"type": "progress", "id": "photos_" + _slug(request)[:12], "done": True,
              "text": f"📷 {sum(1 for _ in credits)} photo(s) downloaded into images/"
              + ("" if keys.get("pexels_key") or keys.get("pixabay_key") else " (free photos: StockSnap, Wikimedia Commons; a Pexels / Pixabay key in Settings finds more)")})
    return credits


def write_credits(root, credits):
    """images/CREDITS.txt: every photo, who took it, its licence and page (kept from earlier pages too)."""
    f = Path(root) / "images" / "CREDITS.txt"
    old = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    lines = [l for l in old if l.strip()]
    for c in credits:
        line = f"{c['file']}: {c.get('alt', '')[:60]} | by {c.get('by') or 'unknown'} | {c['source']} | {c['licence']} | {c.get('page', '')}"
        if not any(l.startswith(c["file"] + ":") for l in lines):
            lines.append(line)
    if lines:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("Photos used on this site\n\n" + "\n".join(l for l in lines if not l.startswith("Photos used")) + "\n",
                     encoding="utf-8")


def footer_note(credits):
    sources = sorted({c["source"] for c in credits})
    return ("Photos: " + ", ".join(sources) + " (see images/CREDITS.txt)") if sources else ""
