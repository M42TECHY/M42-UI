"""UIGEN-T2 pages as M42 page plans (2026-11-09): each dataset page (an HTML + Tailwind answer to a request,
uiexamples.py) is read section by section, with no model, into the plan the 4B writes (pagebuild.PLAN_SCHEMA): its
hero, and each section's part (cards, prices, reviews, steps, faq, stats, gallery, form, cta), title and items with
their real names, texts and prices. Two uses:
- example(request): the plan of the dataset page most like the request, shown to the 4B as a worked example of how
  full a real page of this kind is (its plans had 3-4 thin items where UIGEN's pages have 6 with prices and quotes);
- build(): every page's plan in knowledge/uigen-t2/plans.jsonl ("prompt -> plan" pairs: data to fine-tune the 4B
  later, and counts of which sections pages of a kind have)."""
import json
import re

import uiexamples

PLANS = uiexamples.DIR / "plans.jsonl"
PRICE_RX = re.compile(r"(?:[$₹€£]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:USD|INR|Rs\.?))")
NUM_RX = re.compile(r"^\s*([$₹€£]?)\s?(\d[\d,]*(?:\.\d+)?)\s*([%+kKmM★]*|\w{0,6})\s*$")
UNIT_RX = re.compile(r"/\s?(mo|month|yr|year|night|person|plate|each|kg|hr|hour|session|week)\b", re.I)
KIND = [("reviews", re.compile(r"testimonial|review|what (our|people|clients|customers)\b.*\bsay|love us|feedback", re.I)),
        ("faq", re.compile(r"\bfaq|frequently|questions", re.I)),
        ("steps", re.compile(r"how it works|steps?\b|process|get started in", re.I)),
        ("prices", re.compile(r"pricing|plans?\b|membership|packages?|subscriptions?", re.I)),
        ("gallery", re.compile(r"gallery|portfolio|our work|showcase|photos", re.I)),
        ("stats", re.compile(r"\bstats|numbers|by the numbers|achievements|impact", re.I))]


def _text(el, n=90):
    return " ".join((el.get_text(" ") if el is not None else "").split())[:n]


def _number(s):
    m = NUM_RX.match(str(s or ""))
    if not m:
        return None
    try:
        v = float(m.group(2).replace(",", ""))
    except ValueError:
        return None
    return {"value": int(v) if v.is_integer() else v, "prefix": m.group(1), "suffix": m.group(3).strip()}


def _item(el):
    """One card of a grid: its heading, its text, a price / number, an icon or a picture."""
    h = el.find(["h3", "h4", "h5", "h2", "strong", "dt", "summary"])
    title = _text(h, 50)
    ps = [p for p in el.find_all(["p", "dd", "blockquote", "span"]) if _text(p) and _text(p) != title and not p.find(["p", "div"])]
    text = next((_text(p, 140) for p in ps if len(_text(p)) > 12 and not PRICE_RX.fullmatch(_text(p))), "")
    whole = _text(el, 400)
    it = {"title": title, "text": text}
    price = PRICE_RX.search(whole)
    if price:
        v = _number(re.sub(r"USD|INR|Rs\.?", "", price.group(0)).strip())
        if v:
            it["value"] = v["value"]
            u = UNIT_RX.search(whole[price.end():price.end() + 16])
            if u:
                it["unit"] = "/" + u.group(1).lower()
    elif title and _number(title):  # a stat: "1,200+" over "Happy customers"
        v = _number(title)
        it.update(title=text[:40] or title, text="", value=v["value"], unit=v["suffix"])
    feats = [_text(li, 40) for li in el.find_all("li")][:5]
    if feats:
        it["meta"] = feats
    if el.find("img"):
        it["photo"] = True
    if el.find("blockquote") or re.match(r"^[\"“]", text):
        it["quote"] = True
    return it if (it["title"] or it["text"]) else None


def _grid(sec):
    """The biggest group of 2+ alike children in the section (its cards), as items."""
    best = []
    for g in sec.find_all(["div", "ul", "dl", "ol"]):
        kids = [c for c in g.find_all(recursive=False) if c.name in ("div", "article", "li", "a", "figure", "details", "blockquote")]
        if len(kids) >= 2 and len(kids) > len(best) and all(len(_text(k, 600)) < 600 for k in kids):
            items = [i for i in (_item(k) for k in kids) if i]
            if len(items) >= 2:
                best = items
    return best[:8]


def _part(title, items, sec):
    words = f"{title} {sec.get('id') or ''}"
    for part, rx in KIND:
        if rx.search(words):
            if part == "prices" and sum("value" in i for i in items) < 2:
                continue
            return part
    if sec.find("form") or len(sec.find_all("input")) >= 2:
        return "form"
    if items:
        if sum(i.get("quote", False) for i in items) >= 2:
            return "reviews"
        if sum("value" in i and not i.get("text") for i in items) >= 3:
            return "stats"
        if sum(1 for i in items if "value" in i) >= 2:
            return "prices" if sum(1 for i in items if i.get("meta")) >= 2 else "image_cards"
        if sum(i.get("photo", False) for i in items) >= len(items) - 1:
            return "gallery" if not any(i.get("text") for i in items) else "image_cards"
        return "cards"
    return "cta" if sec.find(["a", "button"]) else ""


def to_plan(prompt, html):
    """The page as an M42 plan, or None when it has too little to show (its content made by a script)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    # its <section>s; else each h1 / h2 with the biggest block around it that holds no other one (many pages are <div>s)
    blocks = [el for el in body.find_all("section") if not el.find_parent("section")]
    for h in ([] if len(blocks) >= 2 else body.find_all(["h1", "h2"])):
        if h.find_parent(["nav", "footer"]):
            continue
        el = h
        while el.parent is not None and el.parent is not body and el.parent.name not in ("html", "[document]") \
                and len(el.parent.find_all(["h1", "h2"])) == 1:
            el = el.parent
        if el not in blocks:
            blocks.append(el)
    blocks += body.find_all("footer")[-1:]
    title = _text(soup.find("title"), 40)
    hero, sections, footer = None, [], ""
    for k, el in enumerate(blocks):
        # the hero: the block with the h1, or the first block's big heading (an h1 that is only the logo in the bar)
        h1 = el.find("h1") or (el.find(["h2", "h3"]) if k == 0 and el.name != "footer" else None)
        if hero is None and h1 is not None and not h1.find_parent("nav"):
            lead = next((_text(p, 160) for p in el.find_all("p") if len(_text(p)) > 20), "")
            acts = [_text(a, 24) for a in el.find_all(["a", "button"]) if 2 < len(_text(a)) <= 24 and not a.find_parent("nav")][:2]
            hero = {"title": _text(h1, 70), "lead": lead, "actions": acts, "photo": bool(el.find("img"))}
            continue
        if el.name == "footer":
            footer = next((_text(p, 90) for p in el.find_all("p") if _text(p)), "")
            continue
        if el.name == "header":
            continue
        h = el.find(["h2", "h3"])
        stitle = _text(h, 50)
        items = _grid(el)
        part = _part(stitle, items, el)
        if not part:
            continue
        sec = {"part": part, "title": stitle}
        seen = {_text(t, 600) for i in items for t in [None]} | {i.get("text", "")[:140] for i in items}
        lead = next((_text(p, 140) for p in el.find_all("p", recursive=True) if len(_text(p)) > 25 and _text(p, 140) not in seen
                     and not any(_text(p, 140)[:60] in (i.get("text") or "") for i in items)), "")
        if lead:
            sec["lead"] = lead
        if part == "form":
            sec["fields"] = [(_text(lb, 24) or str(i.get("placeholder") or i.get("name") or ""))[:24]
                             for lb, i in zip(el.find_all("label") or [None] * 9, el.find_all(["input", "textarea", "select"]))][:6]
        elif items:
            sec["items"] = [{k: v for k, v in i.items() if k not in ("photo", "quote") and v not in ("", None, [])} for i in items]
        sections.append(sec)
    if not hero or len(sections) < 2:
        return None
    return {"request": prompt, "brand": title, "hero": hero, "sections": sections[:9], "footer": footer}


def richness(plan):
    """How much real content a converted plan has: sections with 3+ items, priced items, filled texts."""
    if not plan:
        return 0
    its = [i for s in plan["sections"] for i in s.get("items") or []]
    return (sum(1 for s in plan["sections"] if len(s.get("items") or []) >= 3) * 3 + sum("value" in i for i in its)
            + sum(1 for i in its if len(i.get("text") or "") > 20) + len({s["part"] for s in plan["sections"]}))


def compact(plan, max_items=6):
    """The plan as short JSON for a prompt (~1,500 characters)."""
    out = {"hero": {k: plan["hero"][k] for k in ("title", "lead", "actions") if plan["hero"].get(k)}, "sections": []}
    for s in plan["sections"][:7]:
        c = {k: s[k] for k in ("part", "title", "lead", "fields") if s.get(k)}
        if s.get("items"):
            c["items"] = [{k: (v[:3] if isinstance(v, list) else v[:80] if isinstance(v, str) else v) for k, v in i.items()}
                          for i in s["items"][:max_items]]
        out["sections"].append(c)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def example(request, limit=12):
    """(the dataset page's request, its plan as short JSON) for the page most like the request with real content
    (the richest of the close matches), or None. The request's subject word must be in that page's request."""
    terms = uiexamples._terms(request)
    if not terms:
        return None
    best, top = None, 0
    for _id, prompt, html in uiexamples.search(request, limit=limit):
        low = (prompt or "").lower()
        if terms[0] not in low or sum(1 for t in terms if t in low) < min(2, len(terms)):
            continue
        try:
            plan = to_plan(prompt, html)
        except (ValueError, RecursionError):
            continue
        r = richness(plan)
        if r > top:
            best, top = plan, r
    if (not best or top < 8) and re.search(r"landing|website|home ?page|\bsite\b", request or "", re.I):
        # no full page of this subject (the dataset's "t-shirt design tool" pages are apps): the fullest landing page
        # among the closest ones; one with a word of the subject first. It shows how FULL a page is, never its topic
        for _id, prompt, html in (uiexamples.search("landing page " + " ".join(terms), limit=40)
                                  + uiexamples.search("landing page product features testimonials pricing", limit=20)):
            low = (prompt or "").lower()
            if "landing" not in low:
                continue
            try:
                plan = to_plan(prompt, html)
            except (ValueError, RecursionError):
                continue
            r = richness(plan) + (6 if any(t in low for t in terms if t != "landing") else 0)
            if r > top:
                best, top = plan, r
    if not best or top < 8:
        return None
    s = compact(best)
    while len(s) > 1800 and best["sections"]:  # the prompt stays small for the CPU (~450 tokens)
        best = dict(best, sections=best["sections"][:-1])
        s = compact(best, 5)
    return best["request"], s


def example_from(ids):
    """(request, plan as short JSON) of the fullest of these dataset pages (uiflows.match's), or None."""
    import sqlite3
    if not ids:
        return None
    con = sqlite3.connect(uiexamples.DB)
    try:
        rows = con.execute(f"SELECT id, prompt, html FROM page WHERE id IN ({','.join('?' * len(ids[:40]))})", ids[:40]).fetchall()
    finally:
        con.close()
    best, top = None, 0
    for _id, prompt, html in rows:
        try:
            plan = to_plan(prompt, html)
        except (ValueError, RecursionError):
            continue
        r = richness(plan)
        if r > top:
            best, top = plan, r
    if not best or top < 6:
        return None
    s = compact(best)
    while len(s) > 1800 and best["sections"]:
        best = dict(best, sections=best["sections"][:-1])
        s = compact(best, 5)
    return best["request"], s


def build(progress=print):
    """Every dataset page that converts into a plan with content, one JSON line each (~41,000 pages: ~15 minutes)."""
    import sqlite3
    con = sqlite3.connect(uiexamples.DB)
    n = kept = 0
    tmp = PLANS.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as out:
        for _id, prompt, html in con.execute("SELECT id, prompt, html FROM page"):
            n += 1
            try:
                plan = to_plan(prompt, html)
            except (ValueError, RecursionError):
                plan = None
            if plan and richness(plan) >= 8:
                kept += 1
                out.write(json.dumps(plan, ensure_ascii=False) + "\n")
            if n % 2000 == 0:
                progress(f"{n} pages read, {kept} plans")
    con.close()
    tmp.replace(PLANS)
    return n, kept


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["build"]:
        print(build())
    else:
        r = example(" ".join(sys.argv[1:]) or "local bakery landing page daily specials")
        print(r[0] if r else None)
        print(r[1] if r else "")
