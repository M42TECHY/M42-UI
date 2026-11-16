"""Every widget of the library (widgets.py) on one app page: no unknown classes, no duplicate ids, no script
errors, every button does something (M42's click check), clean at phone width; screenshots for a look."""
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
import widgets  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:600])
    fails += not ok


I = lambda **k: k  # noqa: E731
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
DATA = {
    "kpi_tiles": dict(items=[I(title="New Booking", value=872, icon="bi-bookmark", badge="+12%"), I(title="Efficiency", value=82, unit="%", icon="bi-bullseye", text="Target 85%"),
                             I(title="Revenue", value=182000, unit="₹", icon="bi-currency-rupee", badge="-3%"), I(title="Check Out", value=78, icon="bi-box-arrow-left")]),
    "line_chart": dict(labels=MONTHS, items=[I(title="Check in", values=[300, 420, 380, 610, 560, 840, 700, 760]), I(title="Check out", values=[200, 260, 300, 340, 330, 420, 380, 450])]),
    "chart_stats": dict(items=[I(title="Live", values=[30, 42, 55, 50, 44, 48, 62], badge="Dangerous", text="23.8%"),
                               I(title="Humidity", value=78, unit="%", icon="bi-droplet"), I(title="Wind", value=12, unit="km/h", icon="bi-wind"),
                               I(title="Pressure", value=1, unit="kPa", icon="bi-speedometer")]),
    "area_chart": dict(labels=MONTHS, items=[I(title="Hours", values=[60, 140, 90, 120, 80, 150, 110, 130])]),
    "bar_chart": dict(labels=["Mon", "Tue", "Wed", "Thu", "Fri"], items=[I(title="Class 10", values=[95, 70, 80, 92, 68]), I(title="Class 11", values=[75, 88, 60, 82, 55]), I(title="Class 12", values=[85, 82, 88, 74, 48])]),
    "hbars": dict(items=[I(title="Pending", value=234), I(title="Done", value=65), I(title="Finish", value=763)]),
    "donut": dict(items=[I(title="Present", value=80), I(title="Absent", value=20)]),
    "rings": dict(items=[I(title="Check In", value=70), I(title="Check Out", value=30)]),
    "gauge": dict(items=[I(title="Air conditioner", value=24, unit="°", meta=["16 30"]), I(title="Turbo", icon="bi-fan"), I(title="Cool", icon="bi-snow")]),
    "data_table": dict(labels=["Guest", "Room", "Amount", "Status"], button="Add booking",
                       items=[I(title=f"Guest {n}", meta=[f"10{n}"], value=1000 + n * 250, badge=["Paid", "Pending", "Cancelled"][n % 3]) for n in range(1, 9)]),
    "calendar": dict(labels=["October 2026"], taken=["3", "5", "16"], items=[I(title="History 11", text="8:00 - 9:00 AM")]),
    "agenda": dict(items=[I(title="Review test results", text="8:00 - 9:00 AM", group="History 11"), I(title="Lecture on Cold War", text="10:00 - 11:30 AM", group="History 12")]),
    "timeline": dict(items=[I(title="Order placed", text="2 items", meta=["9:12 AM"], icon="bi-bag"), I(title="Packed", text="Warehouse A", meta=["11:40 AM"], icon="bi-box")]),
    "task_list": dict(items=[I(title="Grade essays", text="April 24"), I(title="Update lesson plans", text="April 25", badge="done")]),
    "task_cards": dict(items=[I(title="Quality check - Line A", badge="High", meta=["Production floor - Zone A", "Fathima Noor", "Due 2:00 PM"], value=75)]),
    "progress_list": dict(items=[I(title="Chef's Masterclass", meta=["45 min", "Beginner"], value=95, icon="bi-egg-fried"), I(title="Kitchen Skills 101", meta=["45 min", "Beginner"], value=64)]),
    "list_thumbs": dict(items=[I(title="Lemon Herb Salmon", text="45 min", icon="bi-egg-fried"), I(title="Delicious Pie", text="45 min", icon="bi-cake", value=249, unit="₹")]),
    "avatars": dict(items=[I(title="Admin"), I(title="Dad"), I(title="Mom"), I(title="Brother")]),
    "profile": dict(button="Export data", items=[I(title="Arvind Iyer", text="Day shift · Zone A"), I(title="Current time", text="12:08"), I(title="Next break", text="13:00")]),
    "status_card": dict(title="Plant status", items=[I(title="4/5 lines active", text="96% uptime", badge="Operational", tags=["JB", "DR", "RE"])]),
    "badges": dict(items=[I(title="Quality master", value=100, text="4.8+ rating", badge="Earned"), I(title="Safety champion", value=75, text="6 months", badge="Active")]),
    "review_list": dict(items=[I(title="Ali Muzair", text="Rooms and food were excellent.", value=4, meta=["26/04/2020"])]),
    "notifications": dict(items=[I(title="New booking", text="Room 204", meta=["2m"], icon="bi-calendar-check"), I(title="Payment", text="₹4,200 received", meta=["1h"], icon="bi-cash")]),
    "kanban": dict(labels=["To do", "Doing", "Done"], items=[I(title="Clean room 101", group="To do", badge="High"), I(title="Laundry", group="Doing"), I(title="Check-in desk", group="Done")]),
    "leaderboard": dict(items=[I(title="Priya", value=980, unit="pts"), I(title="Arun", value=870, unit="pts"), I(title="Meena", value=760, unit="pts")]),
    "heatmap": dict(labels=["M", "T", "W", "T", "F", "S", "S"], items=[I(title="Week 1", values=[1, 3, 5, 2, 8, 9, 4]), I(title="Week 2", values=[2, 6, 7, 3, 5, 10, 6])]),
    "files": dict(items=[I(title="invoice-0425.pdf", text="220 KB"), I(title="guests.xlsx", text="48 KB")]),
    "chat": dict(items=[I(title="Front desk", text="Room 204 is ready", meta=["10:02"]), I(title="Me", text="Thanks!", meta=["10:03"], group="me")]),
    "stepper": dict(items=[I(title="Choose room", text="Pick a room type"), I(title="Guest details", text="Who is staying"), I(title="Pay", text="UPI or card")]),
    "category_chips": dict(items=[I(title="Italian", icon="bi-flag"), I(title="French", icon="bi-flag"), I(title="Greek", icon="bi-flag")]),
    "image_cards": dict(items=[I(title="Grilling", icon="bi-fire"), I(title="Roasting", icon="bi-egg-fried"), I(title="Baking", icon="bi-cake")]),
    "media_player": dict(items=[I(title="That's what I like", text="Bruno Mars", value=275), I(title="Perfect", text="Ed Sheeran", value=263)]),
    "device_cards": dict(items=[I(title="Air purifier", icon="bi-wind", badge="on"), I(title="Android TV", icon="bi-tv", badge="on"), I(title="Geyser", icon="bi-droplet-half", badge="off")]),
    "sliders": dict(items=[I(title="Brightness", value=60, unit="%")]),
    "mode_chips": dict(items=[I(title="Turbo", icon="bi-fan"), I(title="Swing", icon="bi-wind"), I(title="Cool", icon="bi-snow"), I(title="Timer", icon="bi-clock")]),
    "time_range": dict(items=[I(title="From", text="11:00 am"), I(title="To", text="08:00 pm")]),
    "quantity": dict(items=[I(title="Amount", value=120, unit="₹", meta=["2"])]),
    "switch_list": dict(items=[I(title="Email alerts", text="New bookings", badge="on"), I(title="SMS", text="Payments", badge="off")]),
    "rating_input": dict(button="Send rating"), "upload": dict(button="Drop ID proof", lead="PDF or JPG"),
    "hourly": dict(items=[I(title="Now", icon="bi-cloud", value=18), I(title="2 PM", icon="bi-cloud", value=19), I(title="4 PM", icon="bi-cloud-rain", value=20)]),
    "forecast": dict(items=[I(title="Sun", icon="bi-sun", value=28, meta=["12°"]), I(title="Mon", icon="bi-cloud-sun", value=26, meta=["11°"])]),
    "weather_now": dict(lead="Reliable forecasts for any location.", items=[I(title="Stormy", text="with partly cloudy", value=18, icon="bi-cloud-lightning", meta=["H 29°", "L 12°"])]),
    "map_card": dict(items=[I(title="Chennai", text="12 km/h NW"), I(title="Madurai", text="8 km/h")]),
    "camera_feed": dict(items=[I(title="Living Room"), I(title="Garage")]),
    "control_card": dict(items=[I(title="Temperature", value=24, unit="°C"), I(title="Cool", icon="bi-snow", badge="on"), I(title="Turbo", icon="bi-fan"), I(title="From", text="11:00 am"), I(title="To", text="08:00 pm")]),
    "banner": dict(title="Your classes grew 30% this year", lead="Keep it up!", button="See report", items=[I(icon="bi-mortarboard", meta=["hello@school.in", "+91 98765 43210"])]),
    "metric_pair": dict(items=[I(title="Check in", value=549, badge="+8%"), I(title="Check out", value=327, badge="-2%")]),
    "countdown": dict(items=[I(title="Sale ends in", value=93784)]),
    "order_tracker": dict(items=[I(title="Ordered", text="9:12", badge="done"), I(title="Packed", text="11:40", badge="done"), I(title="Shipped", text=""), I(title="Delivered", text="")]),
    "invoice": dict(button="Pay now", items=[I(title="Deluxe room", value=3200, meta=["2"]), I(title="Breakfast", value=350, meta=["4"])]),
    "world_list": dict(items=[I(title="India", text="🇮🇳", value=62, unit="%"), I(title="UAE", text="🇦🇪", value=21, unit="%")]),
    "quick_actions": dict(items=[I(title="New booking", icon="bi-plus-circle"), I(title="Check in", icon="bi-box-arrow-in-right"), I(title="Invoice", icon="bi-receipt")]),
    "empty_state": dict(title="No refunds", lead="Refund requests show here.", button="Create refund", items=[I(icon="bi-arrow-counterclockwise")]),
    "breadcrumb": dict(items=[I(title="Home"), I(title="Bookings"), I(title="Room 204")]),
    "modal": dict(title="New guest", button="Add guest", fields=[{"label": "Name", "type": "text"}, {"label": "Phone", "type": "tel"}]),
    "alerts": dict(items=[I(title="Save", text="Saved!", badge="success"), I(title="Delete", text="Delete this booking?", badge="confirm")]),
    "dropdown_filter": dict(filters=["This week", "This month", "This year"]),
    "week_schedule": dict(labels=["Monday 09.08", "Tuesday 10.08"], items=[I(title="Standup", text="09:30 - 10:00", group="Monday", badge="4"),
                                                                          I(title="Review", text="10:30 - 11:30", group="Tuesday")]),
    "project_cards": dict(items=[I(title="UI Designers", text="Screens", meta=["Asha", "Ravi"], badge="2", value=70),
                                 I(title="Backend", text="APIs", meta=["Kavin"], badge="1", value=40)]),
    "team": dict(items=[I(title="Asha Raman", text="Founder"), I(title="Ravi K", text="Designer"), I(title="Meena S", text="Engineer")]),
    "logos": dict(items=[I(title="Bayern"), I(title="Smatrico"), I(title="Burflex"), I(title="Acrevis")]),
    "blog_cards": dict(items=[I(title="Opening day", text="We are open", meta=["29 Feb"], badge="News"),
                              I(title="New menu", text="Six new dishes", meta=["24 Feb"], badge="Food")]),
    "video_band": dict(lead="Two minutes inside our kitchen", button="Watch"),
    "newsletter": dict(lead="One email a month", button="Subscribe"),
    "portfolio": dict(items=[I(title="Bridge", group="Building", icon="bi-signpost-split"), I(title="Mill", group="Industry", icon="bi-gear")]),
    "funnel": dict(items=[I(title="Visitors", value=1200), I(title="Leads", value=300), I(title="Won", value=40)]),
    "gantt": dict(labels=["Jul", "Aug", "Sep", "Oct"], items=[I(title="Research", meta=[0, 2], value=100, text="Asha"),
                                                              I(title="Build", meta=[1, 3], value=40, text="Team")]),
    "comments": dict(items=[I(title="Priya", text="Approved", meta=["2h ago"]), I(title="Arun", text="Moved to Friday", meta=["5h ago"])]),
    "integrations": dict(items=[I(title="Slack", text="Alerts", icon="bi-slack", badge="on"), I(title="Gmail", text="Sync", icon="bi-envelope", badge="off")]),
    # a reference card drawn from its blocks (a recipe: round photo + name, ingredient tiles, a button with a time)
    "composed": dict(title="Spicy Ramen", lead="239 cal", button="Watch", meta=["15 mins"], _look={"blocks": ["round photo", "heading", "tile grid", "button"], "tiles": 6},
                     items=[I(title=t, icon="bi-egg") for t in ("Noodle", "Chicken", "Onion", "Egg", "Leek", "Chilli", "Garlic")]),
}
APP_VIEWS = {"chat_app", "mail_app"}  # whole screens: tests/test_appviews.py
check("sample data for every widget", set(DATA) == set(widgets.WIDGETS) - APP_VIEWS, (set(widgets.WIDGETS) - APP_VIEWS) ^ set(DATA))
check("a note for the model for every widget", set(widgets.NOTES) == set(widgets.WIDGETS), set(widgets.WIDGETS) ^ set(widgets.NOTES))
plan = {"brand": {"name": "Travelgo", "icon": "bi-airplane"},
        "hero": {"eyebrow": "Today", "title": "Dashboard", "accent": "", "lead": "Everything at a glance", "actions": [], "fields": [], "stats": []},
        "sections": [dict(d, part=name, title=name.replace("_", " ").title(), eyebrow="", lead=d.get("lead", ""), items=d.get("items", []))
                     for name, d in DATA.items()], "footer": "Chennai"}
spec = {"hero": "compact", "ref_layout": "sidebar"}
out = Path(__file__).resolve().parent / "uikit"
tmp = Path(tempfile.mkdtemp())
webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
for theme_name in ("light", "dark"):
    theme = webkit.make_theme("hotel admin dashboard", look={"theme": theme_name, "style": "minimal", "colors": ["#7c3aed", "#10b981", "#f59e0b"],
                                                             "cards": "shadow", "corners": "rounded"})
    page = pagebuild.render(plan, spec, theme, "hotel admin dashboard")
    local, _ = webkit.localize(page, tmp)
    f = tmp / f"w_{theme_name}.html"
    f.write_text(local, encoding="utf-8")
    if theme_name == "light":
        probs = webkit.kit_problems({"index.html": page}, ["bootstrap.min.css", "bootstrap-icons.min.css", "m42-ui.css"])
        probs = [p for ps in probs.values() for p in ps] + webkit.duplicate_ids(page)
        check("no unknown class, icon or duplicate id", not probs, probs)
        missing = [n for n in DATA if f'id="{pagebuild.slug(n.replace("_", " ").title(), set())}"' not in page]
        check("every widget is on the page", not missing, missing)
    if browser.find_browser():
        r = browser.check(f, clicks=True)
        check(f"{theme_name}: runs without errors, no dead buttons", not r["errors"], r["errors"])
        ux = webkit.ux_problems(browser.check(f, ux=True).get("ux"), {"index.html": page})
        check(f"{theme_name}: phone-width UX clean", not ux, ux)
        still = tmp / f"w_{theme_name}_still.html"
        still.write_text(local.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
        webclone.snapshot(still, out / f"widgets_{theme_name}.png", 1440, 7200)
print("FAILS:", fails)
