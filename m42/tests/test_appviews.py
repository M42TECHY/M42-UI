"""App views (appviews.py, 2026-11-10): the chat screen and the mail screen render from a plan (and from an empty
one), run without errors (opening a conversation, sending, folders), and pass the phone-width / contrast check in
light and dark. Screenshots: tests/uikit/appview_*.png. The flow library (uiflows.py) names a request's kinds."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import browser  # noqa: E402
import pagebuild  # noqa: E402
import uiflows  # noqa: E402
import webclone  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


CHAT = {"part": "chat_app", "eyebrow": "", "title": "Chats", "lead": "", "items": [
    {"title": "Priya Menon", "text": "See you at 5 then!", "meta": ["10:42"], "group": "list"},
    {"title": "Design Team", "text": "New mockups are in the folder.", "meta": ["09:15"], "badge": "3", "group": "list"},
    {"title": "Arun Kumar", "text": "Thanks for the quick reply.", "meta": ["Yesterday"], "group": "list"},
    {"title": "Meera V", "text": "Invoice sent.", "meta": ["Mon"], "badge": "1", "group": "list"},
    {"title": "Priya Menon", "text": "Are we still on for today?", "meta": ["10:30"], "group": "them"},
    {"title": "Me", "text": "Yes, the cafe near the office at 5.", "meta": ["10:36"], "group": "me"},
    {"title": "Priya Menon", "text": "See you at 5 then!", "meta": ["10:42"], "group": "them"}]}
MAIL = {"part": "mail_app", "eyebrow": "", "title": "Mail", "lead": "", "items": [
    {"title": "Priya Menon", "text": "Project update — The new designs are ready for review. Tell me what you think.", "meta": ["10:42"], "badge": "Work", "group": "inbox"},
    {"title": "Billing", "text": "Your invoice is ready — Invoice #4021 for October is attached.", "meta": ["09:15"], "badge": "Finance", "group": "inbox"},
    {"title": "Arun Kumar", "text": "Lunch on Friday? — Shall we try the new place near the office?", "meta": ["Yesterday"], "badge": "Personal", "group": "inbox"},
    {"title": "HR Team", "text": "Holiday list — The holiday calendar for next year is out.", "meta": ["Mon"], "badge": "Work", "group": "inbox"},
    {"title": "Me", "text": "Re: Quote — Please find the revised quote attached.", "meta": ["Sun"], "badge": "Work", "group": "sent"}]}


def plan(sec):
    return {"brand": {"name": "ChatMail", "icon": "bi-chat-dots"},
            "hero": {"eyebrow": "", "title": "", "accent": "", "lead": "", "actions": [], "fields": [], "stats": []},
            "sections": [dict(sec, items=[dict(i) for i in sec["items"]])], "footer": "ChatMail"}


check("the request's kinds, in its order", uiflows.kinds("chat box and  mail box website design") == ["chat", "mail"],
      uiflows.kinds("chat box and  mail box website design"))
check("their app pages", [p["part"] for p in uiflows.app_pages("chat box and mail box website design")] == ["chat_app", "mail_app"])
check("a bakery landing page has no app page", uiflows.app_pages("landing page for a local bakery") == [])
tmp = Path(tempfile.mkdtemp())
webkit.sync_files(tmp, set(webkit.KIT_FILES), "")
out = Path(__file__).resolve().parent / "uikit"
for name, sec, marks in (("chat", CHAT, ("m42-chatapp", "Priya Menon", "See you at 5 then!", "is-me")),
                         ("mail", MAIL, ("m42-mailapp", "Project update", "Inbox", "Compose"))):
    for theme_name in ("light", "dark"):
        theme = webkit.make_theme("chat and mail app", look={"theme": theme_name, "style": "minimal", "font": "modern",
                                                             "colors": ["#2563eb", "#6366f1", "#059669"]})
        spec = {"hero": "none", "sections": [{"name": name, "what": "", "part": sec["part"]}]}
        html = pagebuild.render(plan(sec), spec, theme, "chat box and mail box website")
        check(f"{name} {theme_name}: its parts are on the page", all(m in html for m in marks), [m for m in marks if m not in html])
        probs = webkit.kit_problems({"index.html": html}, ["bootstrap.min.css", "bootstrap-icons.min.css", "lucide.css", "m42-ui.css"])
        probs = [p for ps in probs.values() for p in ps] + webkit.duplicate_ids(html)
        check(f"{name} {theme_name}: no unknown class / duplicate id", not probs, probs)
        local, _ = webkit.localize(html, tmp)
        f = tmp / f"{name}_{theme_name}.html"
        f.write_text(local, encoding="utf-8")
        if browser.find_browser():
            r = browser.check(f, clicks=True)
            check(f"{name} {theme_name}: runs without errors", not r["errors"], r["errors"])
            ux = webkit.ux_problems(browser.check(f, ux=True).get("ux"), {"index.html": html})
            check(f"{name} {theme_name}: phone-width / contrast clean", not ux, ux)
            still = tmp / f"{name}_{theme_name}_still.html"
            still.write_text(local.replace("<head>", "<head><script>window.M42_STILL=1</script>", 1), encoding="utf-8")
            webclone.snapshot(still, out / f"appview_{name}_{theme_name}.png", 1280, 900)
empty = pagebuild.render(plan({"part": "chat_app", "title": "", "items": []}), {"hero": "none"}, theme, "chat app")
check("an empty chat plan still shows conversations", "m42-ca-msg" in empty and "m42-ca-who" in empty)
empty = pagebuild.render(plan({"part": "mail_app", "title": "", "items": []}), {"hero": "none"}, theme, "mail app")
check("an empty mail plan still shows mails", "m42-ma-row" in empty)
print("FAILS:", fails)
