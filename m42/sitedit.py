"""A built site changed later by what the user says (the user, 2026-10-27: "after a web design, any correction I say
goes to the right file and edits it correctly").

The build keeps the site in .m42/site.json: the request, the look, the pages and each page's plan and spec. A
correction is then:
  1. located by the chat model (LOCATE_SCHEMA): which page, which section, what kind of change;
  2. applied to the plan (a section rewritten / added / removed / moved / its widget changed, the colours, the
     brand), and only the pages it touches rendered again by M42's templates: no HTML written by a model, the
     other pages untouched;
  3. what a plan can't say ("other": a line of text, a small style) is a line edit on that one page's file, and the
     edit is kept with the page, so a later re-render of it keeps it.
"""
import copy
import difflib
import json
import re
from pathlib import Path

import themes

SITE_FILE = ".m42/site.json"
ACTIONS = ("edit_section", "add_section", "remove_section", "move_section", "swap_sections", "change_widget", "look",
           "brand", "resize_section", "motion", "design", "button_text", "scene_part", "photos", "other")


def path(root):
    return Path(root) / SITE_FILE


def load(root):
    p = path(root)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("pages") else None


def save(root, site):
    p = path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(site, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def new_site(asked, look, files, built, single=False):
    """built: [(plan, page spec, file)]; files: [(name, file)] (the site's menu) or None for one page."""
    return {"asked": asked, "look": copy.deepcopy(look or {}), "files": [list(x) for x in files or []], "single": single,
            "pages": [{"file": f, "plan": _plain(plan), "spec": _plain(pspec), "hand_edits": []} for plan, pspec, f in built]}


def _plain(x):
    return json.loads(json.dumps(x, default=str))


def page(site, f):
    return next((p for p in site["pages"] if p["file"] == f), None)


def _grams(text):
    t = " " + " ".join(re.findall(r"[a-z0-9]+", str(text or "").lower())) + " "
    return {t[i:i + 3] for i in range(len(t) - 2)}


def near_words(site, said, limit=3):
    """The sentences on the site the user's words quote ("'Any device with internet access' irukkira idathula innum oru
    point add pannu"), found by their letters (spelling slips from speech to text kept): [(page, section or "hero" /
    "brand", where, sentence)], best first. The section summary the model sees has no paragraphs or items' texts, so
    a quoted sentence was not found there (the user, 2026-11-13)."""
    have = _grams(said)
    if len(have) < 6:
        return []
    found = []
    for pg in site.get("pages") or []:
        plan = pg.get("plan") or {}
        rows = [("brand", "the site name", (plan.get("brand") or {}).get("name"))]
        h = plan.get("hero") or {}
        rows += [("hero", f"the hero's {k}", h.get(k)) for k in ("eyebrow", "title", "accent", "lead")]
        for k, s in enumerate(plan.get("sections") or []):
            head = f'section {k} ({s.get("part")} "{s.get("title") or ""}")'
            rows += [(k, f"{head}, its {f}", s.get(f)) for f in ("eyebrow", "title", "lead")]
            for n, it in enumerate(s.get("items") or []):
                if isinstance(it, dict):
                    rows += [(k, f'{head}, item {n + 1} "{str(it.get("title") or "")[:40]}", its {f}', it.get(f))
                             for f in ("title", "text", "meta", "quote") if isinstance(it.get(f), str)]
        for where, label, text in rows:
            g = _grams(text)
            if len(g) < 8:  # (a word or two: matched by chance)
                continue
            both = len(g & have)
            score = both / len(g)  # how much of the sentence is in the user's words (or a long part of it quoted)
            if score >= .6 or (both >= 25 and score >= .4):
                found.append((score, pg["file"], where, label, str(text)[:120]))
    found.sort(key=lambda x: -x[0])
    return [x[1:] for x in found[:limit]]


def outline(site, budget=6000):
    """The site as the chat model sees it to place a change: every page with its menu bar, its hero and each section
    in full (eyebrow, title, lead, every item's own words), then the look. In full, not a summary (the user,
    2026-11-13: "a sentence I say from the page: the model must see it to find it"); a long page's item texts are
    cut shorter to stay near `budget` letters a page."""
    names = dict((f, n) for n, f in site.get("files") or [])
    lines = []
    for pg in site["pages"]:
        lines.append(f'{pg["file"]}' + (f' ({names[pg["file"]]})' if pg["file"] in names else "") + ":")
        b, h = pg["plan"].get("brand") or {}, pg["plan"].get("hero") or {}
        if b.get("name"):  # (shown first and on its own: "title change X to Y" with X the site's name changed a
            # section's title, its name sat at the end of the look line, 2026-11-13)
            lines.append(f'  menu bar: the site name (brand) "{b["name"]}", also the browser tab title and the footer name')
        if h.get("title"):
            hero = " | ".join(str(h.get(k)) for k in ("eyebrow", "title", "accent", "lead") if h.get(k))
            lines.append(f'  big heading at the top (hero): {hero}')
        secs = pg["plan"].get("sections") or []
        total = sum(len(str(i.get(f) or "")) for x in secs for i in x.get("items") or [] if isinstance(i, dict)
                    for f in ("title", "text", "meta", "quote"))
        cut = 160 if total < budget else max(40, int(160 * budget / max(total, 1)))
        sc = pg["plan"].get("scene3d")
        if isinstance(sc, dict):  # (its parts by name: "the Complete collection bar" is its caption and its card)
            caps = [b.get("caption") for b in sc.get("beats") or [] if b.get("caption")]
            card = sc.get("card") if isinstance(sc.get("card"), dict) else None
            lines.append("  3D scene in the hero: its things " + ", ".join(str(o).replace("_", " ") for o in sc.get("objects") or [])
                         + (f'; its step captions (shown one by one): {" / ".join(caps)}' if caps else "")
                         + (f'; its progress card with a bar: "{card.get("title")}" ({" -> ".join(card.get("states") or [])})' if card else "")
                         + (f'; its labels by its things: {", ".join(x for x in sc.get("labels") or [] if x)}' if any(sc.get("labels") or []) else ""))
        for k, x in enumerate(secs):
            head = " | ".join(str(x.get(f)) for f in ("eyebrow", "title", "lead") if x.get(f))
            its = [it for it in x.get("items") or [] if isinstance(it, dict)]
            pics = sum(1 for it in its if it.get("photo"))
            lines.append(f'  {k}. {x.get("part")}: {head}' + (f' [{len(its)} items, {pics} with a photo]' if its else "")
                         + (f' [button: {x["button"]}]' if x.get("button") else ""))
            for n, it in enumerate(its, 1):
                words = " - ".join(str(it.get(f))[:cut] for f in ("title", "text", "meta", "quote") if isinstance(it.get(f), str) and it.get(f))
                if words:
                    lines.append(f'     item {n}: {words}' + ("" if it.get("photo") else " (no photo)" if x.get("part") in ("image_cards", "cards", "gallery", "list_thumbs") else ""))
        if h.get("actions"):
            lines.append(f'  hero buttons: {", ".join(str(a) for a in h["actions"])}')
    lk = site.get("look") or {}
    lines.append(f'Look: {lk.get("theme", "light")} theme, colours {", ".join(lk.get("colors") or []) or "default"}'
                 + (f', design theme "{lk["design"]}"' if lk.get("design") else "")
                 + (f' (other themes that fit this site: {", ".join(lk["design_options"])})' if lk.get("design_options") else ""))
    return "\n".join(lines)


def locate_schema(site, parts):
    files = [p["file"] for p in site["pages"]]
    return {"type": "object", "properties": {"english": {"type": "string", "maxLength": 400},
        "understood": {"type": "string", "maxLength": 260},
        "expected": {"type": "string", "maxLength": 260},  # (said before the changes: the 4B decides after reading)
        "changes": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
        "type": "object", "properties": {
            "page": {"type": "string", "enum": files},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "section": {"type": "integer", "minimum": -1, "maximum": 30},
            "part": {"type": "string", "enum": [""] + list(parts)},
            "position": {"type": "integer", "minimum": -1, "maximum": 30},
            "colors": {"type": "array", "maxItems": 3, "items": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}},
            "theme": {"type": "string", "enum": ["", "light", "dark"]},
            "background": {"type": "string", "pattern": "^(#[0-9a-fA-F]{6})?$"},
            "size": {"type": "string", "enum": ["", "narrow", "medium", "wide", "full"]},
            "items": {"type": "string", "enum": ["", "add", "remove", "change"]},
            "align": {"type": "string", "enum": ["", "left", "center", "right"]},
            "name": {"type": "string", "maxLength": 40},
            "design": {"type": "string", "enum": [""] + list(themes.ALL)},
            "items_at": {"type": "array", "maxItems": 12, "items": {"type": "integer", "minimum": 1, "maximum": 40}},
            "count": {"type": "integer", "minimum": 0, "maximum": 20},
            "scene_part": {"type": "string", "enum": ["", "captions", "card", "labels", "scene"]},
            "what": {"type": "string", "maxLength": 160}},
        "required": ["page", "action", "section", "part", "position", "colors", "theme", "background", "size", "align", "items",
                     "items_at", "count", "scene_part", "name", "design", "what"]}},
        },
        "required": ["english", "understood", "expected", "changes"]}


# how the user speaks (Tamil letters, Tanglish, speech to text): language knowledge for the 4B, never a rule in code;
# shared by the locate step (it writes the request in English itself) and agent.TAMIL_TO_ENGLISH
LANGUAGE = """The user's request about their web page is in Tamil (Tamil letters), Tanglish (Tamil in English
letters: "venum" = I want it; "venam" / "venaam" / "vendam" / "venna" / "vena" = I do NOT want it, take it away; "podu" /
"potu" = put; "maathu" = change; "illa" / "varala" = it is not there / not showing) or English, often by speech to text.
When the page is given, read the request with it: a thing the page ALREADY HAS, named by the user, is rarely asked to be
added again; they want it changed or taken away. In Tamil letters:
Tamil words, and English words written in Tamil letters ("கோர்ஸ்" = course, "செக்ஷன்" = section, "கலர்" = colour,
"ஹப்" = hub, "லெட்டர்" = letter, "அனிமி ஜேஎஸ்" / "அனிமே ஜேஎஸ்" = anime.js, a library's name). Sounds made while
thinking ("ஆஹ்", "அஹ்", "உம்", "ஆ") are not words: leave them out. Edit words: "ஸ்வாப்" / "சுவாப்" / "சஇ" / "இடம்
மாத்து" = swap (two things change places, never "combine" or "merge"); "ரிமூவ்" / "நீக்கு" / "தூக்கு" / "வேணாம்" / "வேணா" / "வேண்ணா" = remove (do not want it);
"மேல" = above / first, "கீழ" = below / after; "பட்டன்" = button; "கிராஃப்" / "கிராப்" = graph; "அனிமேஷன்" = animation. In Tamil the new value comes right before "-னு / -ன்னு / -nu" and the verb after it ("X-னு மாத்து" =
"change it to X"; "X அப்படின்னு இருக்கற Y" = "the Y that says X")."""


LOCATE_PROMPT = """A website was built from plans; the user now asks for a change. Find WHERE it goes and WHAT kind of
change it is. The site (each page's sections, numbered from 0) is given with the request, after these rules.

Words that SAY what is wrong ("menu overlay aguthu", "text cut aaguthu", "card sariya illa", "overlap aaguthu",
"varala") are a problem to fix on the page as it is, never something to add.
Answer {{"changes": [...]}}, one entry per separate change (most requests are one), each:
- page: the file the change is on (a change to every page: the first page).
- action:
  edit_section: change a section's content (its words, items, numbers, title, add or remove an item in it);
  add_section: a new section (part = its kind; position = the number it will have: before section 2 is 2, after
  section 2 is 3, -1 = at the end; "munnadi" / "mela" / "before" = before, "apram" / "keela" / "after" = after);
  never for a thing put INTO the top menu bar, the sidebar, the page's header or the footer (that is other);
  remove_section: take a WHOLE section away ("Recent Leads remove pannu", "intha section venaam"); taking an item
  out of a section is edit_section with items "remove";
  move_section: put a section elsewhere (position = its new number);
  swap_sections: two sections change places ("swap", "A first then B", "idam maathu"): section = one, position =
  the other's number. ONE entry for a swap, never two moves;
  change_widget: show a section as another kind (part = the new kind: a table as cards, a donut as bars...), also
  when the user asks it to show something its kind can't draw (progress bars: progress_list; a meter: gauge; a
  chart over time: line_chart / bar_chart; a table: data_table);
  look: the site's colours, its page background or light / dark (colors = 1-3 hex colours of its buttons, menu and
  charts, only when the user names a colour for them, else []: the NEW colour first, in its own hue (red #dc2626,
  blue / neela #2563eb, green / pachai #16a34a, yellow / manjal #eab308, orange #f97316, purple #7c3aed, pink
  #ec4899, gold #d4a017, black #111827), never the site's colour now; background = the page's background colour as a hex
  ONLY when the user's words say "background" (cream #f5efe6, white #ffffff, light grey #f3f4f6), else "" (a
  colour or a theme change leaves the background as it is); theme = "light" / "dark" only when the words say it,
  else "");
  brand: the site's name (name = the NEW name the user asks for, never the name it has now; written in English
  letters as a site name is, also when the user says it in Tamil letters): the name in the menu bar, the browser tab's title and the
  footer, all at once. A request that renames the site, or changes its "title" / "name" / logo words when they are
  the site's name (brand) above, is brand, never edit_section;
  resize_section: how wide ONE section is and where it sits ("antha table ah center la vai", "width kammi pannu", "full
  width"): size = narrow / medium / wide / full, align = left / center / right ("" for what the user did not say).
  Never for a colour, a theme or the page background (those are look), never for something INSIDE a section (a
  button, a title, an icon moved or aligned there is other);
  design: the whole site's THEME / template / design changed ("vera theme", "theme maathu", "innoru design try
  pannu", "template pudhusa venum", "magazine style la maathu", "Bento theme"): design = the theme the user names or
  the one that fits their words best (the themes: THEMES_LIST); for just "another one", the first of the other
  themes that fit this site (named in its Look line), else "". Not for a
  colour or light / dark alone (that is look);
  motion: how the page or a section moves or answers: animations, anime.js, effects when scrolled to, hover, numbers
  counting up, a toast / popup / alert, a back-to-top button, a reading bar (section = that section, -1 = the page);
  photos: real photos for a section's cards, or for some of them (items_at): asked for, or said to be missing ("its
  image does not show"). Look at the page above: the cards marked "(no photo)" are the ones that lack one. A picture
  asked for is never change_widget (the section's kind stays) and never edit_section (the words do not draw photos);
  scene_part: take a part of the hero's 3D scene away (scene_part = "captions": its step lines; "card": the progress
  card with its bar; "labels": the words by its things; "scene": the whole 3D scene);
  button_text: the words on a button changed ("Pay now button-ah Checkout-nu maathu"; name = the NEW words);
  other: anything else on the page (a word in the menu, a button's colour or size, ONE thing inside a section moved:
  "X card la Y button ah right side la vai" is other, not resize_section), and how a section LOOKS: its
  CSS, style, colours inside it, spacing, how things inside it line up ("table css sariya varala", "cards align
  aagala"): the content stays, so not edit_section or change_widget. Also anything added to or changed in the top
  menu bar, the sidebar, the page's header or the footer (a clock, a badge, a status light, a search box, a link):
  other, with section = -1.
- section: the section's number on that page (-1 when none). "this / that / same section", "intha / antha section"
  is the one changed last (named with the site, when there is one); so is a follow-up that names no section ("innum 3 add pannu", "add 3 more", "one more").
- part: for add_section / change_widget, else "".
- items: for edit_section, what happens to the section's items: "add" (new ones next to the ones there: "innoru point
  add pannu", "3 more"), "remove" (some taken away), "change" (their words or numbers), "" (no item changes).
- items_at: the item numbers (as listed above) the change is about, when it is about some items only (a card named,
  "the 3rd one"); [] for the whole section.
- count: for items "add", how many new items the user asks for ("4 more" = 4; "innoru" / "one more" = 1); else 0.
- scene_part: for scene_part, which part; else "".
- what: the change in a few plain English words.
And understood (before the changes): ONE plain sentence saying what M42 will do, where, in the page's own names
("Remove the section 'Recent Leads'", "Add 4 more products to 'Premium Fireworks Collection'", "Find photos for the 3
cards without one in 'Top Treatments'"). Read the user's MEANING, in any language or spelling, speech slips included
(a thing the page ALREADY HAS, named by the user, is rarely asked to be added again: they want it changed or taken away):
what they want changed, and whether they want something added, taken away, changed, moved or shown.
And expected (after understood): ONE sentence saying what a visitor will SEE on the page when it is done, the result,
not the action, with what must stay ("The 4 cards in 'Explore Our Collection' each show a photo of their own product,
their names and prices still there"; "The 'Bestsellers' rows come in one after another when scrolled to, unlike the
rest of the page"). M42 looks at the page after the change and checks it against this."""


LOCATE_LANGUAGE = """

First of all, english: the request written in plain English, the same meaning, nothing added (names and the
words to put on the page stay as written, in quotes). The user's language:
""" + LANGUAGE


def last_note(site):
    """ (page, section) the last edit changed: "intha section" in the next request means it."""
    la = site.get("last") or {}
    pg = page(site, la.get("page"))
    k = la.get("section")
    if not pg or not isinstance(k, int) or not 0 <= k < len(pg["plan"].get("sections") or []):
        return ""
    sec = pg["plan"]["sections"][k]
    return f': {pg["file"]} section {k} ({sec.get("part")} "{sec.get("title") or ""}")'


def locate_messages(site, message, shot=None):
    """shot: the user's 📷 of the page (what they see wrong), shown to the model with the words."""
    ask = f"The user asks: {message}"
    if shot:
        ask = [{"type": "text", "text": ask + "\nThe user's screenshot of the page as it looks now:"},
               {"type": "image_url", "image_url": {"url": shot}}]
    # ⚡ the rules first, the same for every edit, the site and the request after them: llama-server keeps the rules'
    # tokens in its prompt cache (--cache-ram), so they are not read again (2026-11-16: the site map at the top made
    # all 3,250 tokens new each edit, 29 s before the first word; measured with it at the end: 1,872 cached, 8.6 s)
    site_text = f"The site (each page's sections, numbered from 0):{chr(10)}{outline(site)}"
    last = last_note(site)
    site_text += f"{chr(10)}The section changed last{last}." if last else ""
    if isinstance(ask, list):
        ask[0]["text"] = site_text + chr(10) + chr(10) + ask[0]["text"]
    else:
        ask = site_text + chr(10) + chr(10) + ask
    return [{"role": "system", "content": (LOCATE_PROMPT + LOCATE_LANGUAGE).replace("{{", "{").replace("}}", "}").replace(
        "THEMES_LIST", "; ".join(f"{n} ({t['desc'][:60]})" for n, t in (themes.APP_THEMES if themes.is_app((site.get("look") or {}).get("design")) else themes.THEMES).items()))},
            {"role": "user", "content": ask}]


SECTION_PROMPT = """You rewrite ONE section of a web page as JSON (its kind, eyebrow, title, lead, items), changed as the
user asks and otherwise as it is: keep every item and word the user did not ask to change. "N more" / "innum N"
items means the items grow by N (the ones there stay). Real content, no placeholder words. The section now:
{current}"""


def section_messages(current, message, part="", context="", items="", count=0):
    """context: what the site is about and the page's other sections (a gauge added to a 3D shop's dashboard was
    written as a "Newsletter" with only the user's words to go on, 2026-11-12), and what the part's fields are."""
    import widgets
    cur = json.dumps({k: v for k, v in (current or {}).items() if not k.startswith("_") and k != "html"}, ensure_ascii=False)
    # how many new items: the 4B's own reading of the request ("innum 4" = 4; no word rule, 2026-11-16)
    n = (len((current or {}).get("items") or []) + int(count)) if count and current else None
    fields = widgets.NOTES.get(part or (current or {}).get("part") or "", "")
    ask = ((f"{context}\n" if context else "") + f"The user asks: {message}" + (f"\nIts kind is now: {part}." if part else "")
           + (f"\nThis kind is drawn from these fields (fill every one, with real numbers for this site): {fields}" if fields else "")
           + ((f"\nWrite ONLY the new item(s) in items: exactly {max(1, (n or 0) - len(current.get('items') or []))}, "
               "each a new one like the ones there (M42 keeps the ones there)") if items == "add" and current else
              (f"\nThe section must end with exactly {n} items: the {len(current.get('items') or [])} it has and "
               f"{n - len(current.get('items') or [])} new ones." if n else "")))
    return [{"role": "system", "content": SECTION_PROMPT.format(current=cur if current else "(a new section)")},
            {"role": "user", "content": ask}]


def drop_leaf(tree, k):
    """The reference grid without leaf k (the cards after it move up one: leaf i = section i)."""
    def walk(n):
        if "leaf" in n:
            if n["leaf"] == k:
                return None
            return dict(n, leaf=n["leaf"] - (n["leaf"] > k))
        kids = [c for c in (walk(c) for c in n["children"]) if c]
        if not kids:
            return None
        return kids[0] if len(kids) == 1 else dict(n, children=kids)
    return walk(tree) if tree else tree


def _spec_secs(pg):
    """The page spec's sections kept in step with the plan's (render() fits the plan to them)."""
    secs = pg["spec"].get("sections") or []
    return secs if isinstance(secs, list) else []


def _vivid(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) > 40


def _key(item):
    return " ".join(str((item or {}).get("title") or (item or {}).get("text") or "").lower().split())


def merge_items(old, new, mode):
    """A section rewritten for an item change, its items made safe (the user, 2026-11-12: "innoru point add pannu"
    left one item where there were four: the 4B wrote only the new one). mode, as the model decided: "add" keeps
    every old item and adds the new ones (and the section's own words); "change" puts back the old items the
    rewrite dropped; "remove" / "" take the rewrite as it is."""
    olds = [i for i in (old or {}).get("items") or [] if isinstance(i, dict)]
    news = [i for i in (new or {}).get("items") or [] if isinstance(i, dict)]
    if mode == "add":
        have = {_key(i) for i in olds}
        added = [i for i in news if _key(i) and _key(i) not in have]
        return dict(old, items=olds + added)
    if mode == "change" and len(news) < len(olds):
        by = {_key(i): i for i in news}
        kept = [by.pop(_key(i), i) for i in olds]  # each old item, or its changed self
        return dict(new, items=kept + list(by.values()))
    return new


KEEP_ALWAYS = ("_slot", "_main", "_role", "_side", "_shape", "_flow")  # its place on the page, whatever its content
KEEP_SAME_PART = ("_block", "_look")  # how it is drawn: only while it is still the same kind


def _carry(old, new):
    """A section written again keeps what was decided about its place (the CRM's Recent Leads, rewritten for a
    request, lost its place in the skeleton and slid under the others, 2026-11-15); its composition is picked again."""
    for key in KEEP_ALWAYS:
        if key in old and key not in new:
            new[key] = copy.deepcopy(old[key])
    if new.get("part") == old.get("part"):
        for key in KEEP_SAME_PART:
            if key in old and key not in new:
                new[key] = copy.deepcopy(old[key])
    new.pop("_comp", None)
    new.pop("_comp_alts", None)
    if new.get("_block"):  # ("innum 4 products": 14 items in a block made for 3-8 showed no change, 2026-11-16)
        try:
            import blocks
            if not blocks.fits(new["_block"], new):
                cands = blocks.candidates(blocks.BLOCKS[new["_block"]]["role"], new)
                if cands:
                    new["_block"] = cands[0]
                else:
                    new.pop("_block", None)
        except (ImportError, KeyError):
            pass


# ---------------------------------------------------------------- a change in plain words, for the 4B's second look
def describe_change(site, ch):
    """What a located change will do, said plainly with the page's own names (the 4B checks it against the user's words:
    no word rules, 2026-11-16)."""
    pg = page(site, ch.get("page")) or (site["pages"][0] if site.get("pages") else {"plan": {}})
    secs = (pg.get("plan") or {}).get("sections") or []
    k = ch.get("section", -1)
    # the section as the page map names it: its number and ALL its words (label | title), so the check sees the same
    # names as the user (said "Shop by Category", the label; told only the title "Explore Our Collection", the check
    # took them for two parts and the right reading was doubted, 2026-11-16)
    title = (lambda n: f'section {n} "' + " | ".join(str(secs[n].get(f)) for f in ("eyebrow", "title") if secs[n].get(f))
             + f'" ({secs[n].get("part")})' if isinstance(n, int) and 0 <= n < len(secs) else "the page")
    act, what = ch.get("action"), str(ch.get("what") or "")
    at = [i for i in ch.get("items_at") or [] if isinstance(i, int)]
    its = (f"items {', '.join(str(i) for i in at)} of " if at else "")
    if act == "remove_section":
        return f"remove the whole section {title(k)}"
    if act == "edit_section":
        mode = ch.get("items") or ""
        return (f"add {ch.get('count') or 'some'} new items to {title(k)}" if mode == "add" else
                f"take {its or 'some items of '}{title(k)} away" if mode == "remove" else f"rewrite the words of {its}{title(k)} ({what})")
    if act == "add_section":
        return f"add a new {ch.get('part') or 'cards'} section" + (f" before {title(ch.get('position'))}" if isinstance(ch.get("position"), int) and 0 <= ch["position"] < len(secs) else " at the end")
    if act == "move_section":
        return f"move {title(k)} to place {(ch.get('position') or 0) + 1}"
    if act == "swap_sections":
        return f"swap the places of {title(k)} and {title(ch.get('position'))}"
    if act == "change_widget":
        cur = secs[k].get("part") if 0 <= (k if isinstance(k, int) else -1) < len(secs) else ""
        return f"show {title(k)} as a {str(ch.get('part') or '').replace('_', ' ')} instead of a {str(cur).replace('_', ' ')}"
    if act == "photos":
        return f"find real photos for {its or 'the cards of '}{title(k)}"
    if act == "scene_part":
        return f"take the hero 3D scene's {ch.get('scene_part') or 'part'} away"
    if act == "look":
        return "change the site's look: " + ", ".join(x for x in [", ".join(ch.get("colors") or []), ch.get("theme") or "",
                                                                 f'background {ch["background"]}' if ch.get("background") else ""] if x)
    if act == "brand":
        return f'rename the site to "{ch.get("name")}"'
    if act == "button_text":
        return f'change a button\'s words to "{ch.get("name")}" ({what})'
    if act == "design":
        return f'change the whole design to the theme "{ch.get("design")}"'
    if act == "resize_section":
        return f"make {title(k)} {ch.get('size') or ''} {('at the ' + ch['align']) if ch.get('align') else ''}".strip()
    if act == "motion":
        return f"add motion to {title(k)}: {what}"
    return f"a small change on the page: {what}"


def _compact(text):
    """Words compared as written, letters and digits only ("Shop Now" = "shop now" = "SHOP-NOW"): a comparison, not a
    word list (it was dropped with the word rules on 2026-11-16 and the button rename broke)."""
    return re.sub(r"[\W_]+", "", str(text or "")).lower()


def page_buttons(html):
    """The words on the page's buttons (a <button> or a link styled as one), in order, once each."""
    found = []
    for m in re.finditer(r'<(button|a)\b([^>]*)>(.*?)</\1>', html or "", re.S | re.I):
        if m.group(1).lower() == "a" and not re.search(r'class="[^"]*\bbtn\b', m.group(2)):
            continue
        words = " ".join(re.sub(r"<[^>]+>", " ", m.group(3)).split())
        if words and len(words) <= 40 and words not in found:
            found.append(words)
    return found


def rename_button(site, pg, html, old, new):
    """A button's words changed on the page: in the plan (the hero's actions, a section's button) and in the file's
    buttons (the template's own ones too), kept as a hand edit so a later re-render keeps it. Returns (new html,
    how many changed)."""
    plan = pg["plan"]
    acts = (plan.get("hero") or {}).get("actions") or []
    for i, a in enumerate(acts):
        if _compact(a) == _compact(old):
            acts[i] = new
    for s in plan.get("sections") or []:
        if isinstance(s.get("button"), str) and _compact(s["button"]) == _compact(old):
            s["button"] = new
    n = 0

    def swap(m):
        nonlocal n
        inner = m.group(3)
        words = " ".join(re.sub(r"<[^>]+>", " ", inner).split())
        if _compact(words) != _compact(old):
            return m.group(0)
        if m.group(1).lower() == "a" and not re.search(r'class="[^"]*\bbtn\b', m.group(2)):
            return m.group(0)
        n += 1
        text_only = re.sub(r"(>|^)([^<>]*\S[^<>]*)(<|$)", lambda t: t.group(1) + t.group(2).replace(t.group(2).strip(), new) + t.group(3)
                           if _compact(t.group(2)) == _compact(old) else t.group(0), inner, count=1)
        if text_only == inner:  # (its words split over tags: the words written plain, its icon kept)
            icon = re.search(r"<i\b[^>]*></i>", inner)
            text_only = (icon.group(0) + " " if icon else "") + new
        return f"<{m.group(1)}{m.group(2)}>{text_only}</{m.group(1)}>"
    out = re.sub(r'<(button|a)\b([^>]*)>(.*?)</\1>', swap, html or "", flags=re.S | re.I)
    if n and out != html:
        words = pg.setdefault("button_words", {})  # (put back after a later re-render of the page: agent.edit_site)
        for k_ in [k_ for k_, v_ in words.items() if _compact(v_) == _compact(old)]:
            words[k_] = new  # (renamed twice: the first words go straight to the newest)
        if not any(_compact(v_) == _compact(new) for v_ in words.values()):
            words[old] = new
    return out, n


def button_words_again(pg, html):
    """The button words the user changed earlier, put back on a page drawn again from its plan."""
    for old, new in (pg.get("button_words") or {}).items():
        html, _ = rename_button({}, {"plan": {}}, html, old, new)
    return html


def apply(site, ch, new_section=None):
    """One located change applied to the site's plans. Returns (pages to render again, a note for the user);
    "other" changes nothing here (the caller line-edits the file)."""
    pg = page(site, ch.get("page")) or (site["pages"][0] if site["pages"] else None)
    if not pg:
        return [], "no such page"
    secs = pg["plan"].setdefault("sections", [])
    specs = _spec_secs(pg)
    k = ch.get("section", -1)
    k = k if isinstance(k, int) and 0 <= k < len(secs) else -1
    act = ch.get("action")
    grid = pg["spec"].get("ref_grid") or None
    if act == "edit_section" and k >= 0 and new_section:  # (the old items kept: the model wrote only the new one)
        new_section = merge_items(secs[k], new_section, ch.get("items") or "")
    if act in ("edit_section", "change_widget") and k >= 0 and new_section:
        old = secs[k]
        secs[k] = dict(new_section, part=ch.get("part") or new_section.get("part") or secs[k]["part"]) if act == "change_widget" \
            else dict(new_section, part=new_section.get("part") or secs[k]["part"])
        _carry(old, secs[k])
        if k < len(specs):
            specs[k] = dict(specs[k], part=secs[k]["part"])
        return [pg["file"]], f'{pg["file"]}: section {k + 1} ({secs[k].get("title") or secs[k]["part"]}) changed'
    if act == "add_section" and new_section:
        pos = ch.get("position", -1)
        pos = pos if isinstance(pos, int) and 0 <= pos <= len(secs) and not grid else len(secs)  # a reference grid: after its cards
        secs.insert(pos, new_section)
        ch["_at"] = pos  # where it really went ("antha pudhu table" next means it; a grid page puts it at the end)
        specs.insert(min(pos, len(specs)), {"name": new_section.get("title", ""), "what": "", "part": new_section["part"]})
        return [pg["file"]], f'{pg["file"]}: a {new_section["part"].replace("_", " ")} section added'
    if act == "remove_section" and k >= 0:
        gone = secs.pop(k)
        if k < len(specs):
            specs.pop(k)
        if grid and grid.get("tree"):
            pg["spec"]["ref_grid"] = dict(grid, tree=drop_leaf(grid["tree"], k))
        return [pg["file"]], f'{pg["file"]}: "{gone.get("title") or gone["part"]}" removed'
    if act == "move_section" and k >= 0 and any(x.get("_slot") for x in secs):
        # 🦴 an app screen is drawn by its skeleton's places, not by the list's order: a move is a swap with the section
        # in the place it goes to (the CRM's "Recent Leads first, then Deal Pipeline" moved in the list and showed no
        # change, 2026-11-15)
        pos = ch.get("position", -1)
        if not (isinstance(pos, int) and 0 <= pos < len(secs)) or pos == k:
            return [], "no place to move it to"
        act, ch = "swap_sections", dict(ch, position=pos)
    if act == "swap_sections" and k >= 0:
        j = ch.get("position", -1)
        if not (isinstance(j, int) and 0 <= j < len(secs)) or j == k:
            return [], "no second section to swap with"
        a, b = secs[k], secs[j]
        secs[k], secs[j] = b, a
        # each takes the other's place in the skeleton (its row, its column, its width)
        a["_slot"], b["_slot"] = (list(b["_slot"]) if b.get("_slot") else None), (list(a["_slot"]) if a.get("_slot") else None)
        for x in (a, b):
            if x.get("_slot") is None:
                x.pop("_slot", None)
            x.pop("_comp", None)  # (its composition is picked again for its new column: beside the work or not)
            x.pop("_comp_alts", None)
        if k < len(specs) and j < len(specs):
            sa, sb = specs[k].get("slot"), specs[j].get("slot")
            specs[k], specs[j] = dict(specs[j]), dict(specs[k])
            for idx, sl in ((k, sa), (j, sb)):
                if sl is not None:
                    specs[idx]["slot"] = sl
                else:
                    specs[idx].pop("slot", None)
        return [pg["file"]], (f'{pg["file"]}: "{b.get("title") or b["part"]}" and "{a.get("title") or a["part"]}" '
                              "changed places")
    if act == "move_section" and k >= 0:
        pos = ch.get("position", -1)
        pos = pos if isinstance(pos, int) and 0 <= pos < len(secs) else len(secs) - 1
        secs.insert(pos, secs.pop(k))
        if k < len(specs) and pos < len(specs):
            specs.insert(pos, specs.pop(k))
        return [pg["file"]], f'{pg["file"]}: section {k + 1} moved to place {pos + 1}'
    if act == "scene_part":  # 🧊 a part of the 3D scene taken away (its captions, its card, its labels, or all of it)
        sc = pg["plan"].get("scene3d")
        parts = [ch.get("scene_part")] if ch.get("scene_part") in ("captions", "card", "labels", "scene") else []
        if not isinstance(sc, dict) or not parts:
            return [], "no 3D scene part to take away"
        done = []
        if "scene" in parts:
            pg["plan"].pop("scene3d", None)
            pg["plan"]["scene3d_off"] = True  # (not chosen again when the page is drawn again)
            return [pg["file"]], f'{pg["file"]}: the 3D scene removed'
        if "captions" in parts:
            for b in sc.get("beats") or []:
                b["caption"] = ""
            done.append("its captions")
        if "card" in parts and sc.get("card"):
            sc.pop("card", None)
            sc["card_needed"] = False
            done.append("its progress card")
        if "labels" in parts:
            sc["labels"] = []
            sc["extras"] = [x for x in sc.get("extras") or [] if x != "labels"]
            done.append("its labels")
        return ([pg["file"]], f'{pg["file"]}: the 3D scene without ' + " and ".join(done)) if done else ([], "")
    if act == "resize_section" and not ch.get("size") and not ch.get("align") and (ch.get("background") or ch.get("colors") or ch.get("theme")):
        act = "look"  # (the 4B filed "background colour ah cream ah maathu" under it, with the colour given)
    if act == "resize_section" and k >= 0:  # the section's own width and place (pagebuild.own_reveal draws it)
        size = ch.get("size") if ch.get("size") in ("narrow", "medium", "wide", "full") else ""
        align = ch.get("align") if ch.get("align") in ("left", "center", "right") else ""
        if not size and not align:
            return [], "no width or place in the change"
        cols = max([len(secs[k].get("labels") or [])] + [1 + len(i.get("meta") or []) for i in secs[k].get("items") or []])
        if size == "narrow" and secs[k].get("part") in ("data_table", "table") and cols >= 5:
            size = "medium"  # (a 6-column table at half width cut its Status column off)
        if size:
            secs[k]["size"] = size
        if align:
            secs[k]["align"] = align
        return [pg["file"]], f'{pg["file"]}: section {k + 1} ({secs[k].get("title") or secs[k]["part"]}) is now ' + " and ".join(
            x for x in (f"{size} width" if size else "", f"at the {align}" if align else "") if x)
    if act == "look":
        lk = site.setdefault("look", {})
        # greys are no colour choice (the 4B set "theme dark" with #1a1a1a / #2d2d2d / #4a4a4a: the purple was lost)
        cols = list(dict.fromkeys(c.lower() for c in ch.get("colors") or [] if re.fullmatch(r"#[0-9a-fA-F]{6}", str(c)) and _vivid(c)))
        # (one colour asked: it leads, the page's own others follow; "#ea580c" three times flattened the look, 2026-11-16)
        if cols:
            lk["colors"] = (cols + [c for c in lk.get("colors") or [] if c.lower() not in {x.lower() for x in cols}])[:3]
            # the colours the user named for the page are now THESE (the first request's "named colours" were read
            # before the look's and put first: "theme color light blue" changed nothing, twice, 2026-11-17)
            import webkit
            for p in site["pages"]:
                it = (p.get("spec") or {}).get("intent")
                if isinstance(it, dict) and "named_colours" in it:
                    it["named_colours"] = list(lk["colors"])
            if "named_colours" in webkit.INTENT:
                webkit.INTENT["named_colours"] = list(lk["colors"])
        if ch.get("theme") in ("light", "dark"):
            lk["theme"] = ch["theme"]
            if lk.get("bg"):  # the old page background belonged to the other theme
                lk.pop("bg")
        bg = str(ch.get("background") or "")
        if re.fullmatch(r"#[0-9a-fA-F]{6}", bg):  # the page's background ("background light cream ah maathu")
            lk["bg"] = bg
        if not cols and ch.get("theme") not in ("light", "dark") and not lk.get("bg") == bg:
            return [], "no colour or theme in the change"
        lk["why"] = "changed by the user"
        return [p["file"] for p in site["pages"]], "the look changed on every page (" + ", ".join(
            x for x in cols + [ch.get("theme") or "", f"background {bg}" if bg else ""] if x) + ")"
    if act == "design":  # 🎨 another theme (themes.py) for the whole site: its plans drawn again in it
        lk = site.setdefault("look", {})
        now = lk.get("design") or ""
        family = themes.APP_NAMES if themes.is_app(now) else themes.NAMES  # (an app screen keeps an app theme)
        name = ch.get("design") if ch.get("design") in family and ch.get("design") != now else ""
        if not name:  # "another one": the next of the ones the 4B said fit, then the rest in order
            order = [d for d in (lk.get("design_options") or []) if d in family and d != now]
            names = list(family)
            order += [d for d in names[names.index(now) + 1:] + names[:names.index(now)] if d not in order] if now in names else names
            name = order[0] if order else ""
        if not name:
            return [], "no other theme"
        lk["design"] = name
        lk["design_options"] = [d for d in (lk.get("design_options") or []) if d not in (name, now)] + ([now] if now else [])
        for p in site["pages"]:
            if isinstance((p.get("spec") or {}).get("look"), dict):
                p["spec"]["look"]["design"] = name
        return [p["file"] for p in site["pages"]], f'the theme is now {themes.ALL[name]["label"]} on every page'
    if act == "brand" and str(ch.get("name") or "").strip():
        name = str(ch["name"]).strip()[:40]
        for p in site["pages"]:
            old = str((p["plan"].get("brand") or {}).get("name") or "")
            p["plan"].setdefault("brand", {})["name"] = name
            if old and p["plan"].get("footer") == old:  # the footer that was the name is the new name
                p["plan"]["footer"] = name
            if old:  # the user's line edits on a line with the name (the footer) still fit the renamed page
                p["hand_edits"] = [[str(s).replace(old, name), str(r).replace(old, name)] for s, r in p.get("hand_edits") or []]
                site.setdefault("_renamed", []).append([old, name])  # (and the file's other changes: agent.edit_site)
        return [p["file"] for p in site["pages"]], f'the name is now "{ch["name"]}" on every page'
    return [], ""


def carry_edits(rendered, current, context=2):
    """[(search, replace)]: every change made to a page's file since M42 drew it from its plan (the build's line fixes,
    its rules' script, the user's own edits), to make again on the page drawn anew. (2026-11-11: "the student table's
    CSS" re-drew an attendance page from its plan and its 63 lines of fixes and rules were lost: the page fell apart.)"""
    if not rendered or not current or rendered == current:
        return []
    a, b = rendered.splitlines(keepends=True), current.splitlines(keepends=True)
    out = []
    for group in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(context):
        i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
        search, replace = "".join(a[i1:i2]), "".join(b[j1:j2])
        # (not inside M42's theme block: it is written from the site's look on every redraw; a hand edit of it, carried
        # over, put the old colour back over the user's new "light blue", 2026-11-17)
        if search.strip() and 'id="m42-theme"' not in search and not _in_theme_block(rendered, search):
            out.append([search, replace])
    return out


def _in_theme_block(page, text):
    """Is this text (a few lines of the page) inside its <style id="m42-theme"> block?"""
    m = re.search(r'<style id="m42-theme">.*?</style>', page or "", re.S)
    if not m:
        return False
    at = (page or "").find(text.strip()[:200])
    return at >= 0 and m.start() <= at < m.end()


def content_text(site, limit=1800):
    """The site's own content in short (its name, its head, each section's title and its items' names): what a new
    design of the same site keeps."""
    lines = []
    for pg in site.get("pages") or []:
        plan = pg.get("plan") or {}
        b, h = plan.get("brand") or {}, plan.get("hero") or {}
        lines.append(f'{pg["file"]}: brand "{b.get("name", "")}"; head "{h.get("title", "")} {h.get("accent", "")}" - {h.get("lead", "")}')
        for x in plan.get("sections") or []:
            its = ", ".join(str(i.get("title") or "") + (f' ({i.get("value")}{i.get("unit") or ""})' if i.get("value") not in (None, "") else "")
                            for i in (x.get("items") or [])[:8] if i.get("title"))
            lines.append(f'  - {x.get("title") or x.get("part")}: {its}')
    return "\n".join(lines)[:limit]


WORD_RX = re.compile(r"[a-z]{3,}")
STOP = set("the and for with this that page site website landing make create build design need want like same please give "
           "pannu panni venum vennum oru intha indha mathiri pola ready about reference picture shows subject unless request "
           "names another".split())
# words about how good it should look, not what it is about ("i need this website design with awesome UX" names no
# subject: it is the site in this folder, 2026-11-12)
STOP |= set("awesome nice good great best better premium beautiful modern super cool clean simple elegant stunning amazing "
            "professional responsive attractive creative unique perfect fancy look looks feel animation animations ui ux "
            "using use done again".split())


def words(text):
    return {w for w in WORD_RX.findall(str(text or "").lower()) if w not in STOP}


def same_words(a, b):
    """Two requests that ask the same thing (most of their own words shared, or both name nothing)."""
    wa, wb = words(a), words(b)
    if not wa and not wb:
        return True
    return bool(wa and wb) and len(wa & wb) >= .75 * max(len(wa), len(wb))
