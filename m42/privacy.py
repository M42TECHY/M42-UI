"""No personal information on any page M42 makes (the user, 2026-11-12: "mobile number, mail ID, address, PAN, Aadhaar:
none of it may be in a page; put example ones"). Real-looking details the model wrote, or copied off a reference
picture (an order screen's "admin@3dsite.in · 9999999999", "2/408, Bose Colony ... 626189"), become clearly fake ones:

    e-mail      -> hello@example.com            (example.com / .org / .net addresses stay)
    phone       -> +91 98765 XXXXX              (mobile, +country code, landline)
    Aadhaar     -> XXXX XXXX 1234
    PAN         -> ABCDE1234F
    card number -> XXXX XXXX XXXX 1234
    address     -> door number 12, PIN 600001   (only on a line that reads as an address)

scrub_text: a plain string. scrub_html: a page (its <script> / <style> blocks are left as they are). scrub_obj: a
page plan (every string in it). scrub_file: what a file should hold, by its kind."""
import re

EMAIL_RX = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
# a phone number: +country code and its groups, an Indian mobile (10 digits from 6-9, maybe +91 / 0 before it), or a
# landline (044-2345 6789); never inside a longer number
PHONE_RX = re.compile(r"(?<![\w+])(?:(?:\+\d{1,3}[\s.-]?)(?:\(?\d{2,5}\)?[\s.-]?){2,4}\d{2,5}"
                      r"|(?:0|91[\s-]?)?[6-9]\d{4}[\s.-]?\d{5}"
                      r"|0\d{2,4}[\s-]\d{3,4}[\s-]?\d{4})(?![\w])")
AADHAAR_RX = re.compile(r"(?<![\w])[2-9]\d{3}[\s-]\d{4}[\s-]\d{4}(?![\w])")
# 12 digits written together are an Aadhaar only where the words say so (an order or version number has 12 digits too)
AADHAAR_WORD_RX = re.compile(r"(aadha+r|\buid\b)([^\n\d]{0,20})([2-9]\d{11})(?![\w.,])", re.I)
PAN_RX = re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Za-z0-9])")
CARD_RX = re.compile(r"(?<![\w])\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}(?![\w])")
# an address line: an address word with a door number ("2/408," / "No. 14") or a 6-digit PIN code
ADDRESS_WORDS = (r"street|st\.|road|rd\.|nagar|colony|layout|lane|avenue|cross|main road|salai|veedhi|theru|"
                 r"apartment|apartments|flat|floor|block|sector|phase|near|opp\.?|district|taluk|village|post|"
                 r"tamil nadu|kerala|karnataka|andhra|telangana|maharashtra|delhi|chennai|bengaluru|bangalore|"
                 r"mumbai|hyderabad|kolkata|pune|coimbatore|madurai|sivakasi|trichy|salem|pin|pincode")
ADDRESS_RX = re.compile(r"\b(" + ADDRESS_WORDS + r")\b", re.I)
# a door number: "2/408," or "No. 14" (not "Open 24/7", not "no. of orders")
DOOR_RX = re.compile(r"(?<![\w/])\d{1,4}\s*/\s*\d{1,4}[A-Za-z]?(?=\s*,)|\bno\.?\s*\d{1,4}(?:\s*/\s*\d{1,4})?[A-Za-z]?\b", re.I)
PIN_RX = re.compile(r"(?<![\w.,₹$])[1-9]\d{2}\s?\d{3}(?![\w.,%])")

SAFE_DOMAINS = ("example.com", "example.org", "example.net", "example.in")


def _email(m):
    return m.group(0) if m.group(1).lower() in SAFE_DOMAINS else "hello@example.com"


def _address(line):
    """A line that reads as an address: its door number and PIN made example ones."""
    if not ADDRESS_RX.search(line):
        return line
    line = DOOR_RX.sub("12", line)
    return PIN_RX.sub("600001", line)


def scrub_text(text):
    if not isinstance(text, str) or not text:
        return text
    out = EMAIL_RX.sub(_email, text)
    out = CARD_RX.sub("XXXX XXXX XXXX 1234", out)
    out = AADHAAR_RX.sub("XXXX XXXX 1234", out)
    out = AADHAAR_WORD_RX.sub(lambda m: m.group(1) + m.group(2) + "XXXX XXXX 1234", out)
    out = PAN_RX.sub("ABCDE1234F", out)
    out = PHONE_RX.sub("+91 98765 XXXXX", out)
    return "\n".join(_address(line) for line in out.split("\n"))


def scrub_obj(x):
    """Every string in a plan (dicts and lists, any depth)."""
    if isinstance(x, str):
        return scrub_text(x)
    if isinstance(x, list):
        return [scrub_obj(v) for v in x]
    if isinstance(x, dict):
        return {k: scrub_obj(v) for k, v in x.items()}
    return x


SKIP_RX = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>)", re.S | re.I)
TEXT_RX = re.compile(r">([^<]+)<")
ATTR_RX = re.compile(r"""\b(href|title|alt|placeholder|value|content|aria-label|data-[\w-]+)=(["'])(.*?)\2""", re.S | re.I)


def _attr(name, value):
    low = value.lower()
    if low.startswith("mailto:"):
        return "mailto:hello@example.com"
    if low.startswith("tel:"):
        return "tel:+919876500000"
    if name.lower() == "href":
        return value  # (a link: its address is no personal detail)
    return scrub_text(value)


def scrub_html(html):
    """A page: the words between tags and the attribute values people can see or follow (mailto:, tel:, titles,
    placeholders); its scripts and styles left as they are."""
    if not isinstance(html, str) or not html:
        return html
    parts = SKIP_RX.split(html)
    for i in range(0, len(parts), 2):  # (odd parts are the script / style blocks)
        p = TEXT_RX.sub(lambda m: ">" + scrub_text(m.group(1)) + "<", parts[i])
        p = ATTR_RX.sub(lambda m: f"{m.group(1)}={m.group(2)}{_attr(m.group(1), m.group(3))}{m.group(2)}", p)
        parts[i] = p
    return "".join(parts)


def scrub_file(path, content):
    """What a file should hold: pages scrubbed as pages; data and text files as text; code, styles and M42's own
    records (.m42/) as they are."""
    name = str(path).lower().replace("\\", "/")
    if "/.m42/" in name or name.startswith(".m42/"):
        return content
    if name.endswith((".html", ".htm")):
        return scrub_html(content)
    if name.endswith((".json", ".md", ".txt", ".csv")):
        return scrub_text(content)
    return content
