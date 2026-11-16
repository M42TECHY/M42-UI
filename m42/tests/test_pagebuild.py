"""Pages built by M42 from a plan (pagebuild.py): four kinds of site, plans as the chat model writes them. Each
renders with no JS error, a clean phone-width UX check, the kind's own hero and sections, and working behaviour
(filter, choose a row, picks -> total). Screenshots in scratchpad/uikit/pb_*.png."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import pagebuild  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


BUS = {"brand": {"name": "GoBus", "icon": "bi-bus-front"},
       "hero": {"eyebrow": "2,000+ routes across Tamil Nadu", "title": "Your seat is", "accent": "two taps away",
                "lead": "Compare operators, pick your exact seat and get your ticket on WhatsApp.", "actions": [],
                "fields": [{"label": "From", "type": "text"}, {"label": "To", "type": "text"}, {"label": "Date", "type": "date"}],
                "stats": [{"value": 1200, "suffix": "+", "label": "buses daily"}, {"value": 4.7, "suffix": "★", "label": "rating"}]},
       "sections": [
           {"part": "results", "eyebrow": "Buses", "title": "12 buses Madurai → Chennai", "lead": "Tonight, sorted by departure.",
            "filters": ["AC", "Sleeper", "Night"], "button": "Select seats",
            "items": [{"title": "SRM Travels", "text": "21:30 → 05:15 · 7h 45m", "meta": ["AC Sleeper", "4.6★", "23 seats left"],
                       "value": 899, "unit": "per seat", "tags": ["ac", "sleeper", "night"], "badge": "Fastest"},
                      {"title": "KPN Travels", "text": "22:10 → 06:00 · 7h 50m", "meta": ["AC Seater", "4.3★", "9 seats left"],
                       "value": 749, "unit": "per seat", "tags": ["ac", "night"]},
                      {"title": "Parveen", "text": "06:00 → 13:40 · 7h 40m", "meta": ["Non-AC Seater", "4.1★"], "value": 520,
                       "unit": "per seat", "tags": ["day"]}]},
           {"part": "picks", "eyebrow": "Seats", "title": "Pick your seats", "lead": "Up to 6 seats.", "items": [],
            "taken": ["A3", "B4", "D1"]},
           {"part": "summary", "eyebrow": "", "title": "Booking summary", "lead": "", "button": "Continue",
            "items": [{"title": "Bus", "text": ""}, {"title": "Seats", "text": ""}]},
           {"part": "form", "eyebrow": "Passenger", "title": "Passenger details", "lead": "Ticket sent to your WhatsApp.",
            "button": "Book now", "items": [], "fields": [{"label": "Full name", "type": "text"}, {"label": "Age", "type": "number"},
                                                         {"label": "WhatsApp number", "type": "tel"}]},
           {"part": "faq", "eyebrow": "Help", "title": "Questions", "lead": "",
            "items": [{"title": "Can I cancel?", "text": "Yes, free until 6 hours before departure."},
                      {"title": "Is boarding point shown?", "text": "Yes, on your ticket with a map link."}]}],
       "footer": "Safe travels."}
FOOD = {"brand": {"name": "Spice Route", "icon": "bi-fire"},
        "hero": {"eyebrow": "Madurai since 1998", "title": "Biryani cooked slow,", "accent": "served with soul",
                 "lead": "Seeraga samba rice, hand-ground masala, a four-hour dum.", "actions": ["Book a table", "See the menu"],
                 "fields": [], "stats": [{"value": 25, "suffix": "+", "label": "years"}]},
        "sections": [
            {"part": "tabs", "eyebrow": "Menu", "title": "Today's menu", "lead": "Cooked fresh from 11 am.",
             "items": [{"group": "Biryani", "title": "Mutton dum biryani", "text": "Goat, seeraga samba, 18 spices", "value": 349, "badge": "Chef's pick"},
                       {"group": "Biryani", "title": "Chicken biryani", "text": "Country chicken, mint", "value": 249},
                       {"group": "Starters", "title": "Pepper chicken", "text": "Kolli hills pepper", "value": 220},
                       {"group": "Desserts", "title": "Elaneer payasam", "text": "Tender coconut, jaggery", "value": 120}]},
            {"part": "reviews", "eyebrow": "Reviews", "title": "Loved in Madurai", "lead": "",
             "items": [{"title": "Arun Kumar", "text": "Best mutton biryani outside my grandmother's kitchen.", "meta": ["Food blogger"], "value": 5},
                       {"title": "Priya S", "text": "They catered our wedding for 400 people.", "meta": ["Bride, 2025"], "value": 5}]},
            {"part": "contact", "eyebrow": "Reserve", "title": "Book a table", "lead": "We call to confirm in 10 minutes.",
             "button": "Reserve", "items": [{"title": "Call", "text": "+91 98430 12345", "icon": "bi-telephone"},
                                            {"title": "Visit", "text": "12 Town Hall Road, Madurai", "icon": "bi-geo-alt"}],
             "fields": [{"label": "Name", "type": "text"}, {"label": "Phone", "type": "tel"}, {"label": "Date", "type": "date"},
                        {"label": "Guests", "type": "select", "options": ["2", "4", "6", "8+"]}]}],
        "footer": "Open 11 am - 11 pm"}
FOLIO = {"brand": {"name": "Kavya R", "icon": "bi-vector-pen"},
         "hero": {"eyebrow": "Product designer · Chennai", "title": "I design apps people", "accent": "actually enjoy",
                  "lead": "8 years shaping fintech and health products used by 2M+ people.", "actions": ["See my work", "Contact"],
                  "fields": [], "stats": [{"value": 40, "suffix": "+", "label": "projects"}, {"value": 12, "suffix": "", "label": "awards"}]},
         "sections": [
             {"part": "gallery", "eyebrow": "Work", "title": "Selected work", "lead": "",
              "items": [{"title": "PayNow wallet", "icon": "bi-wallet2", "text": ""}, {"title": "CareBook clinic app", "icon": "bi-heart-pulse", "text": ""},
                        {"title": "Learnly kids", "icon": "bi-book", "text": ""}]},
             {"part": "about", "eyebrow": "About", "title": "Design that earns trust", "lead": "I start with research and end with pixel-perfect handoff.",
              "items": [{"title": "Research", "text": "interviews, usability tests"}, {"title": "Systems", "text": "design tokens, components"}]},
             {"part": "cta", "eyebrow": "", "title": "Have a product in mind?", "lead": "Let's talk this week.", "button": "Email me", "items": []}],
         "footer": "Made with care in Chennai"}
ADMIN = {"brand": {"name": "Pulse Admin", "icon": "bi-speedometer2"},
         "hero": {"eyebrow": "Live", "title": "Good evening,", "accent": "Admin", "lead": "Here's how the store is doing today.",
                  "actions": [], "fields": [], "stats": []},
         "sections": [
             {"part": "stats", "eyebrow": "Today", "title": "Key numbers", "lead": "",
              "items": [{"title": "Revenue", "text": "", "value": 182000, "unit": "₹", "icon": "bi-currency-rupee"},
                        {"title": "Orders", "text": "", "value": 342, "unit": "", "icon": "bi-bag-check"},
                        {"title": "Active users", "text": "", "value": 1290, "unit": "", "icon": "bi-people"}]},
             {"part": "chart", "eyebrow": "Trend", "title": "Orders this hour", "lead": "",
              "items": [{"title": "Orders", "text": "", "value": 40}, {"title": "Returns", "text": "", "value": 8}]},
             {"part": "table", "eyebrow": "Orders", "title": "Latest orders", "lead": "", "labels": ["Customer", "Item", "Amount", "Status"],
              "items": [{"title": "Ravi", "text": "", "meta": ["Phone case", "₹499", "Shipped"]},
                        {"title": "Meena", "text": "", "meta": ["Earbuds", "₹1,999", "Packed"]}]}],
         "footer": "Pulse Admin"}

cases = [("bus", BUS, {"hero": "search"}, "bus ticket booking web page", {"theme": "light", "style": "glass", "font": "modern",
                                                                      "colors": ["#e11d48", "#f59e0b", "#0ea5e9"]}),
         ("food", FOOD, {"hero": "split"}, "biryani restaurant website", {"theme": "light", "style": "elegant", "font": "elegant",
                                                                      "colors": ["#b45309", "#7c2d12", "#65a30d"]}),
         ("folio", FOLIO, {"hero": "centered"}, "designer portfolio website", {"theme": "dark", "style": "bold", "font": "tech",
                                                                           "colors": ["#8b5cf6", "#22d3ee", "#f472b6"]}),
         ("admin", ADMIN, {"hero": "compact"}, "admin dashboard web page", {"theme": "dark", "style": "glass", "font": "modern",
                                                                        "colors": ["#22c55e", "#3b82f6", "#f59e0b"]})]
out = Path(__file__).parent / "uikit"
tmp = Path(tempfile.mkdtemp())
webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
for name, plan, spec, req, look in cases:
    theme = webkit.make_theme(req, look=look)
    theme["look"]["hero"] = spec["hero"]
    page = pagebuild.render(plan, spec, theme, req)
    local, _ = webkit.localize(page, tmp)
    (tmp / f"{name}.html").write_text(local, encoding="utf-8")
    (tmp / f"{name}_still.html").write_text(local.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
    probs = webkit.kit_problems({"index.html": page}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
    probs = [p for ps in probs.values() for p in ps] + webkit.duplicate_ids(page) + webkit.ui_problems(req, page)
    check(f"{name}: no class / id / UI problems in what M42 built", not probs, probs)
    # (an admin dashboard is an app page since 2026-10: its compact head is the app's page head, not a hero)
    check(f"{name}: the kind's hero", f"m42-hero is-{spec['hero']}" in page or (spec["hero"] == "compact" and "m42-pagehead" in page))
    if browser.find_browser():
        r = browser.check(tmp / f"{name}.html", clicks=True)
        check(f"{name}: runs without errors", not r["errors"], r["errors"])
        ux = webkit.ux_problems(browser.check(tmp / f"{name}.html", ux=True).get("ux"), {"index.html": page})
        check(f"{name}: phone-width UX clean", not ux, ux)
        webclone.snapshot(tmp / f"{name}_still.html", out / f"pb_{name}.png", 1280, 1700)
# behaviour on the bus page: filter, choose a row, picks -> total
bus = (tmp / "bus.html").read_text(encoding="utf-8")
probe = bus.replace("</body>", """<script>
setTimeout(function () {
  document.querySelector('[data-filter="sleeper"]').click();
  var shown = [].filter.call(document.querySelectorAll('.m42-item'), function (r) { return r.style.display !== 'none'; }).length;
  document.querySelector('.m42-item [data-m42-choose]').click();
  document.querySelector('.m42-pick[data-value="A1"]').click(); document.querySelector('.m42-pick[data-value="A2"]').click();
  var t = document.querySelector('[data-m42-bind="total"]').textContent, item = document.querySelector('[data-m42-bind="item"]').textContent;
  document.title = JSON.stringify({shown: shown, total: t, item: item});
}, 300);
</script></body>""")
(tmp / "probe.html").write_text(probe, encoding="utf-8")
if browser.find_browser():
    r = browser.check(tmp / "probe.html")
    res = json.loads(r.get("title") or "{}")
    check("bus: 'Sleeper' filter shows only sleeper buses; choosing a bus and 2 seats totals ₹1,798",
          res.get("shown") == 1 and res.get("total") == "₹1,798" and res.get("item") == "SRM Travels", res)
print("FAILS:", fails)
