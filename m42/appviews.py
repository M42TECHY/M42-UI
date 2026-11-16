"""M42's app views (2026-11-10): whole working screens for the UI kinds of the flow library (uiflows.py) that a row of
cards cannot show: a chat app (conversations, the open thread, a composer, the person's details) and a mail app
(folders, the mail list, the reading pane, compose). The regions are the ones the UIGEN-T2 pages of that kind have;
the look and the behaviour are M42's (bundled/m42-ui.css ".m42-chatapp" / ".m42-mailapp", m42-ui.js).
Registered in widgets.WIDGETS as "chat_app" and "mail_app" (widgets.py imports this at its end)."""
import re

import widgets as w

e = w.e


def initials(name):
    return "".join(x[0] for x in re.findall(r"[A-Za-z0-9]+", str(name or "?"))[:2]).upper() or "?"


def _face(name, cls=""):
    return f'<span class="m42-av{(" " + cls) if cls else ""}" aria-hidden="true">{e(initials(name))}</span>'


ME_RX = re.compile(r"^(me|you|mine|self|user|sent)$", re.I)
THEM_RX = re.compile(r"^(them|other|received|reply|friend|contact)$", re.I)
REPLIES = ["Got it, thanks!", "Sounds good.", "Let me check and get back to you.", "Perfect, see you then."]


def w_chat_app(sec, ctx):
    pb = w._pb()
    cid = pb.slug("chat", ctx["ids"])
    its = w.items(sec)
    talk = [i for i in its if ME_RX.match(str(i.get("group") or "").strip()) or THEM_RX.match(str(i.get("group") or "").strip())]
    people = [i for i in its if i not in talk and i.get("title")]
    if not people:  # only messages came: the people who wrote them are the conversations
        seen = {}
        for i in talk:
            if not ME_RX.match(str(i.get("group") or "")) and i.get("title"):
                seen[i["title"]] = i
        people = list(seen.values()) or [{"title": "Priya Menon", "text": "See you at 5!", "meta": ["10:42"]},
                                         {"title": "Design Team", "text": "New mockups are up.", "meta": ["09:15"], "badge": "3"},
                                         {"title": "Arun Kumar", "text": "Thanks for the update.", "meta": ["Yesterday"]}]
    people = people[:7]
    first = people[0]

    def bubbles(person, msgs):
        if not msgs:  # a thread around the person's last message
            last = person.get("text") or "Hello!"
            msgs = [{"group": "me", "text": f"Hi {str(person.get('title') or '').split()[0] if person.get('title') else ''}, how is it going?".replace(" ,", ","),
                     "meta": [""]}, {"group": "them", "text": last, "meta": [(person.get("meta") or [""])[0]]}]
        out = ['<div class="m42-ca-day"><span>Today</span></div>']
        for m in msgs:
            mine = bool(ME_RX.match(str(m.get("group") or "").strip()))
            t = (m.get("meta") or [""])[0]
            tick = ' <i class="bi bi-check2-all"></i>' if mine else ""
            out.append(f'<div class="m42-ca-msg{" is-me" if mine else ""}"><p>{e(m.get("text"))}</p><time>{e(t)}{tick}</time></div>')
        return "".join(out)
    rows = []
    for k, p in enumerate(people):
        unread = str(p.get("badge") or "").strip()
        unread = unread if re.fullmatch(r"[1-9]\d?", unread) and k else ""
        online = k % 3 != 2
        rows.append(
            f'<li class="{"active" if k == 0 else ""}" data-name="{e(p.get("title"))}" data-status="{"Online" if online else "Last seen recently"}">'
            f'<button type="button">{_face(p.get("title"), "is-on" if online else "")}'
            f'<span class="m42-ca-who"><b>{e(p.get("title"))}</b><small>{e(p.get("text"))}</small></span>'
            f'<span class="m42-ca-meta"><time>{e((p.get("meta") or [""])[0])}</time>{f"<em>{e(unread)}</em>" if unread else ""}</span></button>'
            f'<template>{bubbles(p, talk if k == 0 else [])}</template></li>')
    flow = sec.get("_flow") or {}
    info = ""
    if flow.get("pane_in", 1) or True:  # the person's details beside the thread (hidden on small screens)
        files = "".join(f'<li><i class="bi {i}"></i><span><b>{e(n)}</b><small>{e(s)}</small></span></li>' for i, n, s in (
            ("bi-file-earmark-pdf", "Proposal.pdf", "1.2 MB"), ("bi-file-earmark-image", "Mockup-v3.png", "860 KB"),
            ("bi-file-earmark-text", "Notes.docx", "48 KB")))
        info = (f'<aside class="m42-ca-info">{_face(first.get("title"), "is-big")}<b data-ca-name>{e(first.get("title"))}</b>'
                '<small data-ca-status>Online</small><div class="m42-ca-acts">'
                '<button type="button" class="m42-icon-btn" aria-label="Call" data-m42-toast="Calling..."><i class="bi bi-telephone"></i></button>'
                '<button type="button" class="m42-icon-btn" aria-label="Video call" data-m42-toast="Starting video..."><i class="bi bi-camera-video"></i></button>'
                '<button type="button" class="m42-icon-btn" aria-label="Mute" data-m42-toast="Muted"><i class="bi bi-bell-slash"></i></button></div>'
                f'<h4>Shared files</h4><ul>{files}</ul></aside>')
    title = sec.get("title") or flow.get("side_title") or "Chats"
    return (f'<div class="m42-chatapp" data-m42-chatapp id="{cid}" data-replies="{e("|".join(REPLIES))}">'
            f'<aside class="m42-ca-list"><div class="m42-ca-top"><h3>{e(title if len(str(title)) <= 16 else "Chats")}</h3>'
            '<button type="button" class="m42-icon-btn sm" aria-label="New chat" data-m42-toast="New chat"><i class="bi bi-pencil-square"></i></button></div>'
            '<label class="m42-ca-search"><i class="bi bi-search"></i><input type="search" placeholder="Search chats" aria-label="Search chats"></label>'
            f'<ul>{"".join(rows)}</ul></aside>'
            f'<section class="m42-ca-main"><header>{_face(first.get("title"), "is-on")}<div><b data-ca-name>{e(first.get("title"))}</b>'
            '<small data-ca-status>Online</small></div><div class="m42-ca-tools">'
            '<button type="button" class="m42-icon-btn sm" aria-label="Call" data-m42-toast="Calling..."><i class="bi bi-telephone"></i></button>'
            '<button type="button" class="m42-icon-btn sm" aria-label="Video call" data-m42-toast="Starting video..."><i class="bi bi-camera-video"></i></button>'
            '<button type="button" class="m42-icon-btn sm" aria-label="More" data-m42-toast="More options"><i class="bi bi-three-dots-vertical"></i></button></div></header>'
            f'<div class="m42-ca-thread" id="{cid}-thread" aria-live="polite">{bubbles(first, talk)}</div>'
            '<form class="m42-ca-send"><button type="button" class="m42-icon-btn sm" aria-label="Attach a file" data-m42-toast="Attach a file">'
            '<i class="bi bi-paperclip"></i></button><input class="form-control" placeholder="Type a message" aria-label="Message" required>'
            '<button class="m42-btn" type="submit" aria-label="Send"><i class="bi bi-send-fill"></i></button></form></section>'
            f'{info}</div>')


FOLDER_ICON = [("inbox", "bi-inbox"), ("star", "bi-star"), ("sent", "bi-send"), ("draft", "bi-file-earmark"), ("trash|bin|delete", "bi-trash3"),
               ("spam|junk", "bi-exclamation-octagon"), ("archive", "bi-archive"), ("important", "bi-bookmark"), ("work", "bi-briefcase")]
FOLDERS = ["Inbox", "Starred", "Sent", "Drafts", "Trash"]
SPLIT_RX = re.compile(r"\s+[—–-]\s+|:\s+")


def w_mail_app(sec, ctx):
    pb = w._pb()
    mid = pb.slug("mail", ctx["ids"])
    flow = sec.get("_flow") or {}
    # the folders real mail UIs have (the flow library's side entries), the usual ones first
    known = [f for f in FOLDERS if f.lower() in [x.lower() for x in (flow.get("side") or FOLDERS)]] or FOLDERS
    folders = list(dict.fromkeys(["Inbox"] + known + [x for x in FOLDERS if x in ("Starred", "Sent", "Trash")]))[:6]
    mails = [i for i in w.items(sec) if i.get("title") or i.get("text")][:10] or [
        {"title": "Priya Menon", "text": "Project update — The new designs are ready for review. Let me know your thoughts.", "meta": ["10:42"], "badge": "Work"},
        {"title": "Billing", "text": "Your invoice is ready — Invoice #4021 for October is attached.", "meta": ["09:15"], "badge": "Finance"},
        {"title": "Arun Kumar", "text": "Lunch on Friday? — Shall we try the new place near the office?", "meta": ["Yesterday"], "badge": "Personal"}]
    labels = list(dict.fromkeys(str(m.get("badge")).strip() for m in mails if str(m.get("badge") or "").strip()))[:4]
    tone = {l: k % 3 for k, l in enumerate(labels)}
    rows, first, unread_in = [], None, {}
    for k, m in enumerate(mails):
        text = str(m.get("text") or "")
        parts = re.split(r"\s+[—–]\s+", text, 1) if re.search(r"\s[—–]\s", text) else SPLIT_RX.split(text, 1)
        if len(parts) == 2 and len(parts[0]) <= 70:
            subject, body = parts
        else:
            subject = re.split(r"(?<=[.!?])\s+", text, 1)[0].rstrip(".")
            if len(subject) > 56:
                subject = subject[:56].rsplit(" ", 1)[0] + "…"
            body = text
        folder = str(m.get("group") or "inbox").strip().lower()
        folder = next((f.lower() for f in folders if f.lower().startswith(folder[:4])), "inbox") if folder else "inbox"
        label = str(m.get("badge") or "").strip()
        when = (m.get("meta") or [""])[0]
        unread = folder == "inbox" and k in (1, 2, 4)
        d = {"from": m.get("title") or "Unknown", "subject": subject, "time": when, "body": body, "label": label}
        unread_in[folder] = unread_in.get(folder, 0) + bool(unread)
        first = first or d
        rows.append(
            f'<li class="{"active" if k == 0 else ""}{" is-unread" if unread else ""}"{"" if folder == "inbox" else " hidden"} '
            f'data-folder="{e(folder)}" data-from="{e(d["from"])}" '
            f'data-subject="{e(subject)}" data-time="{e(when)}" data-body="{e(body)}">'
            '<button type="button" class="m42-ma-star" aria-label="Star"><i class="bi bi-star"></i></button>'
            f'<button type="button" class="m42-ma-row">{_face(d["from"])}<span class="m42-ma-txt"><b>{e(d["from"])}</b>'
            f'<strong>{e(subject)}</strong><small>{e(body)}</small></span><span class="m42-ma-meta"><time>{e(when)}</time>'
            + (f'<em class="is-t{tone.get(label, 0)}">{e(label)}</em>' if label else "") + "</span></button></li>")
    count = lambda f: unread_in.get(f.lower(), 0)  # noqa: E731

    def icon_of(name):
        return next((i for rx, i in FOLDER_ICON if re.search(rx, name, re.I)), "bi-folder2")
    side = "".join(f'<li><button type="button" class="{"active" if k == 0 else ""}" data-folder="{e(f.lower())}"><i class="bi {icon_of(f)}"></i>'
                   f'<span>{e(f)}</span>{f"<em>{count(f)}</em>" if count(f) else ""}</button></li>' for k, f in enumerate(folders))
    tags = "".join(f'<li><i class="m42-ma-dot is-t{tone[l]}"></i>{e(l)}</li>' for l in labels)
    compose = w._modal(mid + "-compose", "New message", [{"label": "To", "type": "email"}, {"label": "Subject", "type": "text"},
                                                         {"label": "Message", "type": "textarea"}], ctx)
    compose = compose.replace('data-m42-done="Saved!"', 'data-m42-done="Message sent"').replace(
        '<button class="m42-btn">Save</button>', '<button class="m42-btn">Send</button>')
    return (f'<div class="m42-mailapp" data-m42-mailapp id="{mid}">'
            f'<aside class="m42-ma-side"><button type="button" class="m42-btn" data-bs-toggle="modal" data-bs-target="#{mid}-compose">'
            f'<i class="bi bi-pencil-square"></i> Compose</button><ul class="m42-ma-folders">{side}</ul>'
            + (f'<h4>Labels</h4><ul class="m42-ma-labels">{tags}</ul>' if tags else "") + "</aside>"
            '<section class="m42-ma-list"><div class="m42-ma-bar"><label class="m42-ca-search"><i class="bi bi-search"></i>'
            '<input type="search" placeholder="Search mail" aria-label="Search mail"></label>'
            '<button type="button" class="m42-icon-btn sm" aria-label="Refresh" data-m42-toast="Up to date"><i class="bi bi-arrow-clockwise"></i></button></div>'
            f'<ul>{"".join(rows)}</ul><p class="m42-ma-none" hidden>Nothing here yet.</p></section>'
            f'<article class="m42-ma-read"><header><h3 data-ma="subject">{e(first["subject"])}</h3><div class="m42-ma-tools">'
            '<button type="button" class="m42-icon-btn sm" aria-label="Reply" data-ma-act="reply"><i class="bi bi-reply"></i></button>'
            '<button type="button" class="m42-icon-btn sm" aria-label="Forward" data-m42-toast="Forward"><i class="bi bi-forward"></i></button>'
            '<button type="button" class="m42-icon-btn sm" aria-label="Move to trash" data-ma-act="trash"><i class="bi bi-trash3"></i></button></div></header>'
            f'<div class="m42-ma-from"><span data-ma="face">{_face(first["from"])}</span><div><b data-ma="from">{e(first["from"])}</b><small>to me</small></div>'
            f'<time data-ma="time">{e(first["time"])}</time></div>'
            f'<div class="m42-ma-body"><p>Hi,</p><p data-ma="body">{e(first["body"])}</p><p>Regards,<br><span data-ma="sign">{e(first["from"])}</span></p></div>'
            '<form class="m42-ma-reply"><input class="form-control" placeholder="Write a reply" aria-label="Reply" required>'
            '<button class="m42-btn" type="submit"><i class="bi bi-send-fill"></i> Send</button></form></article>'
            f'{compose}</div>')


w.WIDGETS.update({"chat_app": w_chat_app, "mail_app": w_mail_app})
w.NOTES.update({
    "chat_app": "items = first 5 conversations (title = the person's or group's name, text = their last message, meta = [time], "
                "badge = unread count like \"2\" on two of them, group = \"list\"), then 6 messages of the first conversation in "
                "order (text = the message, meta = [time], group = \"me\" for the user's own and \"them\" for the other person's)",
    "mail_app": "items = 7 mails: title = the sender's name, text = the subject, then \" — \", then the mail's first 1-2 sentences, "
                "meta = [time or day], badge = a label (Work, Personal, Finance...), group = \"inbox\" (\"sent\" for one or two)"})
w.WIDTH.update({"chat_app": 12, "mail_app": 12})
w.LOOKS.update({"chat_app": "a whole chat screen: a list of conversations, the open thread of bubbles, a message box",
                "mail_app": "a whole mail screen: folders, a list of mails, the open mail"})
w.OWN_BAND.update({"chat_app", "mail_app"})
