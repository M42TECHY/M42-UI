"""No personal details on a page (privacy.py): real-looking phones, e-mails, Aadhaar, PAN, card numbers and address
door numbers / PINs become example ones; prices, dates, order numbers, hours and versions stay as they are."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import privacy  # noqa: E402
import tools  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:200])
    fails += 0 if ok else 1


S = privacy.scrub_text
check("e-mail", S("admin@3dsite.in") == "hello@example.com", S("admin@3dsite.in"))
check("example e-mail kept", S("info@example.com") == "info@example.com")
check("mobile", "98400" not in S("Call 98400 12345") and "XXXXX" in S("Call 98400 12345"), S("Call 98400 12345"))
check("+91 mobile", "XXXXX" in S("+91 9840012345"), S("+91 9840012345"))
check("landline", "2345" not in S("Ph: 044-2345 6789"), S("Ph: 044-2345 6789"))
check("Aadhaar grouped", S("Aadhaar 2345 6789 0123").endswith("XXXX XXXX 1234"))
check("Aadhaar by its word", "567890" not in S("Aadhaar no: 234567890123"))
check("PAN", S("PAN ABCPD1234K") == "PAN ABCDE1234F")
check("card", S("4111 1111 1111 1111") == "XXXX XXXX XXXX 1234")
addr = S("2/408, Bose Colony, Sivakasi, Tamil Nadu 626189")
check("address door and PIN", "408" not in addr and "626189" not in addr, addr)
for keep in ("₹1,24,500", "Order #1024 · 0.5 kg", "2023-10-24", "Open 24/7", "Open 10-22", "Version 202611121234",
             "May 2023 - May 2024", "no. of orders 45", "45,000 users"):
    check(f"kept: {keep}", S(keep) == keep, S(keep))
page = ('<p>Call <a href="tel:9840012345">98400 12345</a> · <a href="mailto:me@gmail.com">me@gmail.com</a></p>'
        '<script>const ID = "9840012345";</script>')
out = privacy.scrub_html(page)
check("page text and links", "gmail" not in out.split("<script>")[0] and "98400" not in out.split("<script>")[0], out)
check("script left as it is", '<script>const ID = "9840012345";</script>' in out)
d = Path(tempfile.mkdtemp())
ws = tools.Workspace([d])
if ws:
    ws.write_file("index.html", "<html><body><p>Mail: owner@gmail.com, 9840012345</p></body></html>")
    saved = (d / "index.html").read_text(encoding="utf-8")
    check("a saved page is scrubbed", "gmail" not in saved and "9840012345" not in saved, saved)
print(f"FAILS: {fails}")
sys.exit(1 if fails else 0)
