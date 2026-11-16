"""A web page made to look like a screenshot the user shows ("ithe clone onnu pannu html la kojam super ya").

The screenshot went to the bug-report reader ("PROBLEM: ... it's not working well"), which also listed the Windows
taskbar and "Activate Windows" as page content, and the coder then taught "Step 1: Create the HTML Structure" in the
chat with a styles.css and logo.png that didn't exist. Here the vision model writes a design spec (sections top to
bottom, exact texts, layout), the colours are measured from the pixels (a 4B vision model guesses hex badly), the
coder writes one self-contained index.html, and a screenshot of the result is shown next to the reference.
"""
import base64
import io
import os
import re
import subprocess
from pathlib import Path

CLONE_RX = re.compile(r"\b(clone|copy|replicate|re-?create|same (design|ui|look|page|site|style)|it?he? mathiri|"
                      r"itha mathiri|ithu pola|like this|look like this|redesign)\b", re.I)
WEB_RX = re.compile(r"\b(html|site|website|web ?page|page|landing|ui|design|frontend|front-end|css|portfolio)\b", re.I)
# after a clone: "athe mathiri ila", "innum same ah illa", "sari illa", "not like the site"
AGAIN_RX = re.compile(r"\b(mathiri|maathiri|madhiri|pola)\s*(ila|illa|illai|varala|illaye)\b|\bsame\s*(ah|a)?\s*(ila|illa)|"
                      r"\b(sari|correct)\s*(ah|a)?\s*(ila|illa|varala)|\bnot (the )?same\b|\bnot like\b|\bdifferent\b|"
                      r"\bmatch\w*\s*(aagala|agala|illa|ila)|\b(innum|still)\b.{0,20}\b(ila|illa|wrong|different)\b",
                      re.I)
POLISH_RX = re.compile(r"\b(super|better|nice|nalla|azhaga|beautiful|modern|premium|improve|kojam)\b", re.I)

SPEC_PROMPT = """The user shows a screenshot of a web page they want rebuilt in HTML. Describe the PAGE as a design
spec a programmer can build from. Leave out of the sections everything that is not the page: the Windows taskbar,
browser tabs and address bar, scroll bars, "Activate Windows" text (the address goes only in the LINKS line at
the end). Write, top to bottom, one block per section:
SECTION <name> (e.g. NAVBAR, HERO, FEATURES, FOOTER): layout (what is left / centre / right, how many columns or
cards), background (colour or gradient direction), every text in it EXACTLY as written (in quotes), and for each
button or link its text and look (filled / outline, rounded, colour). Then one line FONTS: serif or sans-serif,
which texts are bold or large. Short lines, no advice, no guesses about problems."""


# copying the picture itself, not taking it as a design reference ("ithe mathiri oru web page pannu" with a shot is
# a page LIKE it: the reference flow, designref.py, in M42's own templates; the user, 2026-10-27)
EXACT_RX = re.compile(r"\b(clone|copy|replicate|re-?create|exact(ly)?|same to same|pixel[- ]?perfect)\b", re.I)


def wants_clone(message):
    return bool(CLONE_RX.search(message or "") and WEB_RX.search(message or ""))


def wants_exact(message):
    """The user asks for the picture's page itself (its texts as written), not a page like it."""
    return bool(EXACT_RX.search(message or "") and WEB_RX.search(message or ""))


def palette(data_url, n=8):
    """The page's colours from the pixels, most used first: [("#5b2a86", 41.0), ...]. The bottom strip (a taskbar
    in a full-screen capture) is left out."""
    from PIL import Image
    raw = base64.b64decode(data_url.split(",", 1)[1])
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    im = im.crop((0, 0, w, int(h * 0.95))) if h > 500 else im
    im.thumbnail((320, 320))
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    out = []
    for c, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        share = 100 * c / total
        if share >= 2:
            out.append((f"#{r:02x}{g:02x}{b:02x}", round(share, 1)))
    return out


def task(spec, colours, polish, project):
    pal = ", ".join(f"{h} ({s:g}%)" for h, s in colours)
    where = ("Write it with write_file as index.html in the project (replace the old one if there is one), then check "
             "it with check_page. Don't explain steps or show the code in the chat: write the file."
             if project else "Give the complete file in one ```html block, then one short line on how to open it.")
    return (f"Build a web page that looks like the user's reference screenshot"
            + (" and is a little more polished (smooth hover effects, soft shadows, a gentle fade-in)" if polish else "")
            + f".\n\nWhat the reference shows, top to bottom:\n{spec}\n\nColours measured from the screenshot, most used "
              f"first: {pal}. Use these for the backgrounds, text and buttons.\n\nRules: one file index.html with the CSS "
              "in a <style> tag and any script in a <script> tag. No image files or other files that don't exist: draw "
              "logos and icons with CSS, inline SVG or emoji. Use the texts exactly as listed. Responsive: it must also "
              f"look right at a phone width. {where}"
            + ("\n\nThe live site was opened too (below): where the screenshot is unclear, use the live site's exact "
               "texts, menu items and sections." if "[The web pages the picture" in spec else ""))


# the clone of technisite.in: a data: SVG with fill="#8d66ae" (the # ends the URL: black triangles over the page),
# background-image after background (the gradient gone: a white page under white text), a hero in a flex row
CODE_TRAPS = [
    (re.compile(r"url\(\s*['\"]?data:image/svg\+xml;utf8,[^)]*#", re.I),
     "a data: SVG URL contains a raw '#' (e.g. fill=\"#8d66ae\"): the URL ends there and the shapes draw black. "
     "Write %23 instead of # inside data: URLs, or drop the pattern"),
    (re.compile(r"data:image/svg\+xml[^)]*<(path|polygon|circle|rect|ellipse)\b(?![^>]*\bfill=)[^>]*/?>", re.I),
     "a data: SVG pattern has shapes without a fill colour, and SVG shapes are black by default (big black "
     "shapes over the page). Give them fill='%23ffffff' with low opacity, or drop the pattern"),
    (re.compile(r"\.hero[^{]*\{(?![^}]*flex-direction)[^}]*display\s*:\s*flex[^}]*\}", re.I),
     "the hero is display:flex without flex-direction: column, so the heading, the text and the button sit side "
     "by side in one row. Add flex-direction: column (and text-align: center)"),
    (re.compile(r"background\s*:\s*[^;]*gradient[^;]*;[^}]*background-image\s*:", re.I | re.S),
     "background-image comes after the gradient in the same rule and replaces it (the gradient is gone). Put "
     "both in one background: line, e.g. background: url(...), linear-gradient(...)"),
]


def code_traps(html):
    """Known CSS mistakes that the browser check can't see (no error, just a wrong page)."""
    return [msg for rx, msg in CODE_TRAPS if rx.search(html or "")]


def _image(src):
    from PIL import Image
    if isinstance(src, str) and src.startswith("data:"):
        return Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1]))).convert("RGB")
    return Image.open(src).convert("RGB")


def compare(reference, result):
    """How the rendered page differs from the reference, region by region, in words for the coder (empty when
    close enough). reference / result: a PNG path or a data: URL."""
    if not reference or not result:  # no picture of one of them (the browser couldn't render the page)
        return []
    try:
        ref, res = _image(reference), _image(result)
    except (OSError, ValueError):
        return []
    if ref.height > 500:
        ref = ref.crop((0, 0, ref.width, int(ref.height * 0.95)))  # a taskbar in a full-screen capture
    size = (160, 100)
    ref, res = ref.resize(size), res.resize(size)
    regions = [("the navbar (top strip)", (0, 0, 160, 12)), ("the left of the main area", (0, 12, 53, 85)),
               ("the centre of the main area", (53, 12, 107, 85)), ("the right of the main area", (107, 12, 160, 85)),
               ("the bottom of the page", (0, 85, 160, 100))]

    def mean(im, box):
        px = list(im.crop(box).getdata())
        return tuple(sum(c[i] for c in px) // len(px) for i in range(3))

    def share(im, test):
        px = list(im.getdata())
        return sum(1 for p in px if test(p)) / len(px)

    hexc = lambda c: "#%02x%02x%02x" % c  # noqa: E731
    out = []
    for name, box in regions:
        a, b = mean(ref, box), mean(res, box)
        if sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5 > 90:
            out.append(f"{name}: the reference is {hexc(a)}, yours renders {hexc(b)}")
    white = lambda p: min(p) > 225  # noqa: E731
    black = lambda p: max(p) < 30  # noqa: E731
    if share(res, white) > 0.45 and share(ref, white) < 0.15:
        out.append(f"your page is mostly white ({share(res, white):.0%} of it); the reference is not (its "
                   f"background is {hexc(mean(ref, (0, 12, 160, 85)))}): the background is missing")
    if share(res, black) - share(ref, black) > 0.15:
        out.append(f"large black areas cover {share(res, black):.0%} of your page (not in the reference): shapes "
                   "that lost their colour")
    return out


def live_snapshot(url, out_png, width=1280, height=800):
    """A picture of the real site the user pointed to (headless Chrome, its own empty profile), for the colours and
    to show next to the result. Public addresses only. Returns the path or None."""
    import tempfile

    import browser
    import web
    exe = browser.find_browser()
    if not exe:
        return None
    try:
        web._check_public(url)
    except Exception:  # ToolError: a local / private address, or a name that doesn't resolve
        return None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(prefix="m42-site-") as profile:
        try:
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                            f"--window-size={width},{height}", f"--screenshot={out_png}",
                            "--virtual-time-budget=6000", url], capture_output=True, timeout=90, creationflags=flags)
        except (OSError, subprocess.TimeoutExpired):
            return None
    return out_png if Path(out_png).is_file() and Path(out_png).stat().st_size > 2000 else None


def to_data_url(png_path):
    return "data:image/png;base64," + base64.b64encode(Path(png_path).read_bytes()).decode()


def snapshot(html_path, out_png, width=1280, height=800):
    """A picture of the finished page (headless Chrome), to compare with the reference. Returns the path or None."""
    import browser
    exe = browser.find_browser()
    if not exe or not Path(html_path).is_file():
        return None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
                        f"--screenshot={out_png}", "--virtual-time-budget=2500", Path(html_path).resolve().as_uri()],
                       capture_output=True, timeout=60, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out_png if Path(out_png).is_file() else None
