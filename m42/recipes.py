"""The section order of a site to read (a landing page, a shop's or a cafe's website), decided by M42 and not by the
4B (2026-11-10). A benchmark run of "a landing page for a custom T-shirt design tool" came out as the tool itself
(an upload box, a form, rows of "0MB limit") with no features, testimonials or pricing: the 4B picks the sections
from the words, and one odd pick spoils the page. Real pages of a kind share an order (hero > what it does > how it
works > plans > what customers say > questions > the call), so M42 gives that order, with how many items each
section holds, and the 4B writes what is in them: names, texts, prices, quotes.
Only for a site asked for in words (agent.SITE_ASK_RX) that is no app (pagebuild.APP_RX) and has no picture of the
user's: an app page and a reference picture keep the sections they have."""
import re

# (name, what the 4B writes there, part, how many items)
FEATURES = ("Features", "what it does for the visitor: 6 features, each a short title, one specific sentence and an icon", "cards", 6)
REVIEWS = ("Testimonials", "3 customers: text = what they say (one or two sentences, specific), title = the person's name, "
           "meta = [their role or city], value = rating 4-5", "reviews", 3)
FAQ = ("Questions", "5 questions a visitor really asks before buying, each with a clear answer in the text", "faq", 5)
CTA = ("Final call", "one strong line, a short lead and the button", "cta", 0)
RECIPES = {
    "saas": ("split", [
        FEATURES,
        ("How it works", "3 steps from the start to the result, each a short title and one sentence", "steps", 3),
        ("Pricing", "3 plans (a free one first when the request names one): title, value = monthly price, unit, "
                    "meta = 4 things the plan includes, badge \"Popular\" on the middle one", "prices", 3),
        REVIEWS, FAQ, CTA]),
    "device": ("split", [
        FEATURES,
        ("In numbers", "4 real figures of the product (battery hours, range, devices supported, setup minutes): title, "
                       "value = the number (never 0), unit", "stats", 4),
        ("Set up", "3 steps from the box to working, each a short title and one sentence", "steps", 3),
        REVIEWS, FAQ, CTA]),
    "food": ("image", [
        ("Menu", "the dishes / bakes / drinks the request is about (its specials, its menu): 6, each with its own name, "
                 "a one-line text and value = price, unit = what one costs", "image_cards", 6),
        ("Why us", "3 reasons people come here (fresh, local, how it is made), each a title, a sentence and an icon", "cards", 3),
        REVIEWS,
        ("Visit us", "the address, the opening hours and the phone as 3 items (title = which, text = the detail)", "cards", 3),
        CTA]),
    "shop": ("split", [
        ("Products", "6 products of this shop, each with its own name, a one-line text and value = price, unit", "image_cards", 6),
        ("Why buy here", "4 benefits (delivery, returns, quality, support), each a title, a sentence and an icon", "cards", 4),
        REVIEWS,
        ("Questions", "4 questions a buyer asks (delivery, payment, returns), each with its answer in the text", "faq", 4),
        CTA]),
    "service": ("image", [
        ("Services", "6 services offered, each a short title, one specific sentence and an icon", "cards", 6),
        ("How it works", "3 steps from the first call to the finished job, each a short title and one sentence", "steps", 3),
        ("Packages", "3 packages: title, value = price, unit, meta = 4 things included, badge \"Popular\" on one", "prices", 3),
        REVIEWS,
        ("Questions", "4 questions a client asks before booking, each with its answer in the text", "faq", 4),
        ("Book", "the form to book or enquire: fields name, phone, what they need, a date; and the button", "form", 0)]),
    "portfolio": ("centered", [
        ("Selected work", "6 projects: title, one line on what was made and for whom, tags = 2 skills used", "cards", 6),
        ("What I do", "4 services or skills, each a title, a sentence and an icon", "cards", 4),
        ("In numbers", "3 figures (years of work, projects, clients): title, value = the number (never 0), unit", "stats", 3),
        REVIEWS,
        ("Contact", "the form to write: fields name, email, message; and the button", "form", 0)]),
    "general": ("split", [
        FEATURES,
        ("How it works", "3 steps from the start to the result, each a short title and one sentence", "steps", 3),
        REVIEWS, FAQ, CTA]),
}
# the first that fits: what is sold as software first ("a bakery ordering app", "a T-shirt design tool")
KINDS = [
    ("saas", r"tools?|apps?|software|saas|platform|streaming|startup|plugin|extension|api|ai|crm|builder|generator|editor"),
    ("portfolio", r"portfolio|resume|cv|freelanc\w*|personal (?:web)?site"),
    ("device", r"device|gadget|smart ?home|smart ?watch|watch|headphones?|earbuds|speaker|drone|camera|robot|scooter|e-?bike|"
               r"wearable|hardware|product launch"),
    ("food", r"baker\w*|cafe|coffee|restaurant|sweets?|juice|pizza|biryani|tea|ice ?cream|cater\w*|mess|food|"
             r"cake\w*|dhaba|tiffin|kitchen|pub"),
    ("service", r"salon|parlou?r|spa|gym|fitness|yoga|clinic|hospital|dental|dentist|doctor|lawyer|law firm|agency|"
                r"construction|builders?|interior\w*|travels?|tours?|photograph\w*|wedding|events?|cleaning|repair\w*|"
                r"plumb\w*|electrician|school|college|academy|coaching|tuition|institute|real ?estate|consult\w*|"
                r"rentals?|coworking|studio|hotel|resort|lodge|laundry|pest|movers|driving|garage|mechanic|service centre|service center"),
    ("shop", r"shops?|stores?|boutique|crackers?|jewell?\w*|textiles?|sarees?|fashion|furniture|electronics|mobiles?|"
             r"grocer\w*|supermarket|florist|flowers?|book ?(?:store|shop)|toys?|e-?commerce|mart|showroom|nursery|pharmacy|medicals?"),
]
ONE_PAGE_RX = re.compile(r"\b(landing|one[ -]?page|single[ -]?page|click-?through)\b", re.I)
EXTRA = [  # a section the user's own words ask for that the recipe lacks
    (r"pricing|plans?\b|packages?|subscriptions?", ("Pricing", "3 plans: title, value = price, unit, meta = 4 things included, "
                                                    "badge \"Popular\" on one", "prices", 3)),
    (r"contact|enquir\w*|inquir\w*|book(?:ing)?|reserv\w*|appointment|sign ?up|register|newsletter|wait ?list",
     ("Get in touch", "the form the request asks for: its fields (name, phone or email, what they need) and the button", "form", 0)),
    (r"faq|questions", FAQ),
    (r"steps|how it works|process", ("How it works", "3 steps from the start to the result, each a short title and one sentence", "steps", 3)),
    (r"stats|numbers|counters?", ("In numbers", "3 real figures: title, value = the number (never 0), unit", "stats", 3)),
]


def kind(request):
    low = (request or "").lower()
    return next((k for k, rx in KINDS if re.search(r"\b(?:" + rx + r")\b", low)), "general")


def one_page(request):
    """A landing page is one page: no site map (a run built Features / Templates / Pricing pages beside it)."""
    return bool(ONE_PAGE_RX.search(request or ""))


# what each kind of block holds, for the 4B to write with THIS site's own content (the block itself comes from the
# request: the 4B's spec, or the dataset pages of this kind)
HOLDS = {"cards": ("what this site offers: 6 items, each a short title, one specific sentence and an icon", 6),
         "image_cards": ("the things this site shows or sells: 6, each with its own name, a one-line text and a price if it has one", 6),
         "steps": ("3-4 steps, each a short title and one sentence", 3), "prices": ("3 plans: title, value = price, unit, meta = 4 "
         "things included, badge \"Popular\" on one", 3), "reviews": ("3 people: text = what they say (specific), title = the "
         "person's name, meta = [who they are], value = rating 4-5", 3), "faq": ("4-5 questions a visitor of this site asks, each with "
         "its answer in the text", 5), "stats": ("3-4 real figures of this site: title, value = the number (never 0), unit", 4),
         "gallery": ("6 pictures of this site's world: title and an icon", 6), "team": ("4 people: name, role", 4),
         "form": ("the form this site needs: its own fields and the button", 0), "cta": ("one strong line, a short lead and the button", 0)}
# a block of a dataset page by its name or id (uiexamples._outline_of: "features", "testimonials", "pricing"...)
BLOCK_PART = [(r"feature|service|benefit|why|offer|program|course|class|facilit|solution|about", "cards"),
              (r"product|menu|special|collection|shop|item|dish|room|propert|listing|catalog", "image_cards"),
              (r"how|step|process|work", "steps"), (r"pric|plan|package|fee|membership", "prices"),
              (r"testimon|review|client|customer|say|love|feedback", "reviews"), (r"faq|question", "faq"),
              (r"stat|number|counter|achiev|impact", "stats"), (r"galler|portfolio|photo|showcase|work", "gallery"),
              (r"contact|enquir|book|reserv|appoint|newsletter|subscribe|sign|register|admission|apply", "form"),
              (r"cta|call|join|start|get", "cta")]
SKIP_BLOCK_RX = re.compile(r"^(header|footer|nav\w*|hero|section|main|top|banner|home)$")


def _block_part(name):
    return next((p for rx, p in BLOCK_PART if re.search(rx, name)), "")


def pool_block(x):
    """("reviews", "customer love") from a dataset page's "reviews: Customer Love (3 cards, pictures)": its kind word,
    or for a general one ("section: What Our Customers Say") its title, read without the notes in brackets; a title
    alone needs a plain word for its kind ("Baked with Love" is no testimonials)."""
    key, _c, rest = x.partition(":")
    title = re.sub(r"\(.*?\)", "", rest).strip(" -")
    key = key.strip()
    if key and not SKIP_BLOCK_RX.match(key):
        return _block_part(key), title
    if not title:
        return "", ""
    part = _block_part(title)
    if part == "reviews" and not re.search(r"testimon|review|say|feedback|customer love|client love", title):
        part = ""
    return part, title


OFTEN = 0.2  # a block one page in five of the subject's pages has is part of such a page


def from_flows(flows):
    """[(name, part)] of the blocks the dataset pages of this kind have, in their usual order: the best page's own,
    then what at least a fifth of the subject's pages have that it lacks (2026-11-11: the best bakery page had no
    testimonials; 4 of the 19 bakery pages have them, 2 of 20 restaurant pages: the bakery's page gets them)."""
    out = []
    for _kind, f in flows or []:
        for b in f.get("parts") or []:
            b = str(b).lower()
            part = "" if SKIP_BLOCK_RX.match(b) else _block_part(b)
            if part and part not in [p for _n, p in out]:
                out.append((b.replace("-", " ").title(), part))
        pool = f.get("pool") or []
        if len(pool) >= 5:
            seen, name = {}, {}
            for n_, parts in enumerate(pool):
                for x in dict.fromkeys(str(x).lower() for x in parts):
                    part, title = pool_block(x)
                    if part and part not in seen.setdefault(n_, set()):
                        seen[n_].add(part)
                        name.setdefault(part, []).append(title)
            for part, names in sorted(name.items(), key=lambda x: -len(x[1])):
                if len(names) / len(pool) >= OFTEN and part not in [p for _n, p in out]:
                    out.append((next((t for t in names if t), part.replace("_", " ")).title(), part))
    return out


def apply(spec, request, flows=()):
    """The page's sections, dynamic for what is asked (the user, 2026-11-10: "whatever is asked, only what it needs,
    nothing unrelated"): the 4B's own sections for this request first (a school's Admissions and Principal's message),
    then the blocks the dataset pages of this kind have that the spec lacks (uiflows: a landing page's features and
    testimonials), the closing call last; each with how many items it holds. Only when both give fewer than 3 is a
    general recipe used. A site's items stay as fixed content: no readings, no rules for a script, no data question."""
    own = [dict(x, part="about" if x.get("part") == "summary" else x.get("part"))  # (a bakery's "About [summary]")
           for x in spec.get("sections") or [] if str(x.get("name") or "").strip()
           and not DROP_RX.match(str(x.get("name")).strip()) and x.get("part") not in ("modal", "custom")]
    # the 4B's own sections: a message or a contact block holds a few things, not a grid of six
    rows = [{"name": x["name"], "what": x.get("what") or "", "part": x["part"],
             "n": 3 if x["part"] == "cards" else HOLDS.get(x["part"], ("", 0))[1]} for x in own]
    have = {_topic(r["name"], r["part"]) or r["part"] for r in rows}
    blocks = from_flows(flows)
    first, last = [], []
    for name, part in blocks:
        t = _topic(name, part) or part
        if t in have or part in ("form", "cta") and any(r["part"] in ("form", "cta") for r in rows):
            continue
        have.add(t)
        row = {"name": name, "what": HOLDS[part][0], "part": part, "n": HOLDS[part][1]}
        # what proves it and answers doubts (testimonials, questions) and the call close a page; the rest leads it
        (last if part in ("reviews", "faq", "form", "cta") else first).append(row)
    body = [r for r in rows if r["part"] not in ("form", "cta")]
    while first and len(first) + len(body) + len(last) > 8:  # too many: the dataset's lead blocks go first, not the
        first.pop()                                              # proof that closes the page or the 4B's own
    rows = first + body + last + [r for r in rows if r["part"] in ("form", "cta")]
    if len(rows) < 3:  # too little from both: the general order of its kind
        _hero, base = RECIPES[kind(request)]
        rows = keep_own([{"name": n, "what": w, "part": p, "n": c} for n, w, p, c in base], own)
    ends = [r for r in rows if r["part"] in ("form", "cta")]
    rows = [r for r in rows if r["part"] not in ("form", "cta")][:8] + ends[:1]
    hero = spec.get("hero") if spec.get("hero") in ("split", "image", "centered", "search") else "split"
    return dict(spec, hero=hero, recipe=kind(request), rules=[], question="", data={},
                items=[dict(i, source="fixed") for i in spec.get("items") or []], sections=rows)


TOPICS = [("form", r"\b(form|enquir\w*|inquir\w*|contact|book\w*|reserv\w*|appointments?|apply|register|sign ?up|get in touch|visit)\b"),
          ("reviews", r"\b(testimonials?|reviews?|says?|feedback|parents|customers)\b"), ("faq", r"\b(faqs?|questions?)\b"),
          ("stats", r"\b(stats|statistics|numbers|figures|counters?|achievements?)\b"),
          ("gallery", r"\b(galler\w*|photos?|campus life|moments)\b"), ("steps", r"\b(steps?|how it works|process)\b"),
          ("prices", r"\b(pricing|prices?|plans?|packages?|fees?)\b"), ("about", r"\b(about|story|principal\W*s?|founders?|mission|who we)\b")]
DROP_RX = re.compile(r"^(hero|header|nav\w*|footer|name|title|logo|\w+ name)$", re.I)


def _topic(name, part):
    words = str(name or "").lower()
    return next((t for t, rx in TOPICS if re.search(rx, words)), "")


def keep_own(rows, own):
    """A general recipe's rows with the 4B's own sections none of them covers, before the closing call."""
    have = {_topic(r["name"], r["part"]) or r["part"] for r in rows}
    extra = []
    for x in own:
        t = _topic(x["name"], x["part"]) or x["name"].lower()
        if t in have:
            continue
        have.add(t)
        extra.append({"name": x["name"], "what": x.get("what") or "", "part": x["part"], "n": HOLDS.get(x["part"], ("", 0))[1]})
    at = len(rows) - 1 if rows and rows[-1]["part"] in ("cta", "form") else len(rows)
    return rows[:at] + extra + rows[at:]


LISTS = ("cards", "image_cards", "steps", "prices", "reviews", "faq", "stats")


def thin(plan, spec):
    """[(index in plan["sections"], recipe row)] of the sections that came with too few items for their part (fewer
    than 3, or under half of what the recipe holds)."""
    out = []
    rows = (spec or {}).get("sections") or []
    for n, s in enumerate(plan.get("sections") or []):
        row = rows[n] if n < len(rows) else None
        if not row or not row.get("n") or row["part"] not in LISTS or s.get("part") not in LISTS:
            continue
        if len(s.get("items") or []) < max(3, (row["n"] + 1) // 2):
            out.append((n, row))
    return out
