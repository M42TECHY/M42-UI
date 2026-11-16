"""UI code examples for a card M42's widget library lacks: the Tesslate UIGEN-T2 dataset (41,170 "UI request ->
HTML + Tailwind page" pairs, Apache-2.0, huggingface.co/datasets/Tesslate/UIGEN-T2, downloaded 2026-11-03 to
knowledge/uigen-t2/). The pages are indexed once (sqlite FTS5: the request and the page's visible words); for a card
the best page is found and only the part of it that is like the card is cut out (a whole page is ~9,000 characters:
too long for the CPU to read in a prompt), shown to the coder as a layout idea (agent.custom_cards)."""
import re
import sqlite3
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "knowledge" / "uigen-t2"
DATA, DB = DIR / "UIGEN-T2.parquet", DIR / "index.sqlite"
CODE_RX = re.compile(r"```(?:html)?\s*\n(.*?)```", re.S | re.I)
STOP = set("a an the and or for with of to in on at by from this that these your our build create design make ui page app "
           "web website responsive modern beautiful clean simple card section using use pannu panni venum vennum oru "
           "onnu kudu enakku ennaku nalla super premium".split())


def _html(response):
    """The page's HTML from an answer (its biggest code block that is HTML)."""
    blocks = [b for b in CODE_RX.findall(response or "") if "<" in b]
    return max(blocks, key=len) if blocks else ""


def _slim(html):
    """Without what a layout idea doesn't need: scripts, styles, long SVG paths, comments, blank lines."""
    html = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", "", html)
    html = re.sub(r'(?i)\s(d|points|viewBox)="[^"]{40,}"', r' \1="…"', html)
    return re.sub(r"\n\s*\n+", "\n", html).strip()


def build(progress=print):
    """The index (once, ~2 minutes): one row per page with HTML, its request and its words."""
    import pyarrow.parquet as pq
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE page(id INTEGER PRIMARY KEY, prompt TEXT, html TEXT)")
    con.execute("CREATE VIRTUAL TABLE words USING fts5(prompt, text, content='')")
    table = pq.read_table(DATA, columns=["prompt", "response"])
    n = 0
    for batch in table.to_batches(2000):
        for prompt, response in zip(batch.column("prompt").to_pylist(), batch.column("response").to_pylist()):
            html = _slim(_html(response))
            if len(html) < 400:
                continue
            n += 1
            text = re.sub(r"<[^>]+>", " ", html)
            con.execute("INSERT INTO page VALUES (?, ?, ?)", (n, prompt or "", html))
            con.execute("INSERT INTO words(rowid, prompt, text) VALUES (?, ?, ?)", (n, prompt or "", " ".join(text.split())[:6000]))
        progress(f"{n} pages indexed")
    con.commit()
    con.close()
    tmp.replace(DB)
    return n


def ready():
    return DB.exists()


def _terms(text):
    return [w for w in dict.fromkeys(re.findall(r"[a-z]{3,}", str(text or "").lower())) if w not in STOP][:12]


def search(what, limit=5):
    """[(id, prompt, html)] of the pages most like the card (its request words weigh more than the page's words)."""
    terms = _terms(what)
    if not terms or not ready():
        return []
    con = sqlite3.connect(DB)
    try:
        q = " OR ".join(f'"{t}"' for t in terms)
        rows = con.execute("SELECT rowid FROM words WHERE words MATCH ? ORDER BY bm25(words, 4.0, 1.0) LIMIT ?", (q, limit)).fetchall()
        return [con.execute("SELECT id, prompt, html FROM page WHERE id = ?", (r[0],)).fetchone() for r in rows]
    finally:
        con.close()


def snippet(html, what, max_chars=2200):
    """The part of a page that is like the card: the smallest block (section / div / article...) that holds most of
    the card's words and fits in max_chars."""
    from bs4 import BeautifulSoup
    terms = _terms(what)
    soup = BeautifulSoup(html, "html.parser")
    best, top = None, (0, 0)
    for el in soup.find_all(["section", "article", "aside", "div", "table", "form", "ul", "nav", "main"]):
        s = str(el)
        if len(s) > max_chars or len(s) < 200:
            continue
        text = el.get_text(" ").lower()
        score = (sum(1 for t in terms if t in text), len(s))  # most words, then the biggest that fits
        if score > top:
            best, top = s, score
    if best is None:
        body = soup.body or soup
        best = str(body)[:max_chars]
    return best


def example(what, max_chars=2200):
    """(the request of the page it is from, an HTML snippet like the card) or None. The card's name (before ":")
    must be in the page's request or the part cut out: "Sankey flow" found a meditation app's onboarding "flow"
    (the data has no sankey), which is no example of it."""
    name = _terms(str(what or "").split(":")[0]) or _terms(what)[:1]
    for _id, prompt, html in search(what):
        part = snippet(html, what, max_chars)
        if part and len(part) >= 200 and any(t in f"{prompt} {part}".lower() for t in name[:1]):  # its first word: "sankey", not "flow"
            return prompt, part
    return None


def _outline_of(html):
    """A page's sections top to bottom, each in a few words: its heading and what it holds ("6 cards with prices",
    "a form", "a picture"), from the HTML (no model)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    blocks = [el for el in soup.find_all(["header", "section", "footer"]) if not el.find_parent(["section", "header", "footer"])]
    out = []
    for el in blocks:
        h = el.find(["h1", "h2", "h3"])
        title = " ".join((h.get_text(" ") if h else "").split())[:50]
        grid = max((len([c for c in g.find_all(recursive=False) if c.name in ("div", "article", "li", "a")])
                    for g in el.find_all(class_=re.compile(r"\bgrid\b|\bflex-wrap\b"))), default=0)
        text = el.get_text(" ")
        parts = []
        if grid >= 3:
            parts.append(f"{grid} cards" + (" with prices" if re.search(r"[$₹€£]\s?\d", text) else ""))
        if el.find(["form", "input"]):
            parts.append("a form")
        if el.find("img"):
            parts.append("pictures")
        if el.find(["button", "a"], class_=re.compile(r"\b(bg-|btn|rounded-full)")):
            parts.append("buttons")
        kind = el.name if el.name != "section" else (el.get("id") or "section")
        out.append(f"{kind}: {title or '-'}" + (f" ({', '.join(parts)})" if parts else ""))
    return out[:10]


def outline(request):
    """(the page's request, its sections in a few words each) of the dataset page most like the request ("coffee shop
    landing page" -> a cafe page's hero, menu cards with prices, testimonials...), or None. Its subject word must be
    in that page's request. The 4B plans the page with it where there is no reference picture."""
    terms = _terms(request)
    if not terms:
        return None
    for _id, prompt, html in search(request, limit=8):
        # the subject word, and a second word of the request when it has one ("construction company": not a no-code
        # app builder's "logic construction")
        low = (prompt or "").lower()
        if terms[0] not in low or sum(1 for t in terms if t in low) < min(2, len(terms)):
            continue
        secs = _outline_of(html)
        if len(secs) >= 3:
            return prompt, secs
    return None


def download(progress=print):
    """The dataset file (~308 MB) from Hugging Face into knowledge/uigen-t2/."""
    import urllib.request
    DIR.mkdir(parents=True, exist_ok=True)
    url = "https://huggingface.co/datasets/Tesslate/UIGEN-T2/resolve/main/UIGEN-T2.parquet"
    tmp = DATA.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as out:
        total, done = int(r.headers.get("Content-Length") or 0), 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if done % (32 << 20) < (1 << 20):
                progress(f"{done >> 20} / {total >> 20} MB")
    tmp.replace(DATA)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["download"]:
        download()
    elif sys.argv[1:] == ["build"]:
        print(build(), "pages indexed")
    else:
        print("python uiexamples.py download | build")
