"""Chats, saved as JSON files in m42/sessions/. A chat belongs to a project (project_id) or to none
(a general chat with no folders).

A chat keeps two lists:
  messages - the model conversation (what the agent sends to the LLM)
  ui       - the UI event log (user bubbles, answers, tool cards) so a chat can be re-displayed
"""
import json
import re
import time
import uuid
from pathlib import Path

DIR = Path(__file__).resolve().parent / "sessions"
ID_RX = re.compile(r"[0-9a-f]{12}")


class Session:
    def __init__(self, project_id=None, id=None, title="New chat", created=None, updated=None,
                 messages=None, ui=None, legacy_workspace=None, running=None):
        self.id = id or uuid.uuid4().hex[:12]
        self.project_id = project_id
        self.title = title
        self.created = created or time.time()
        self.updated = updated or self.created
        self.messages = messages if messages is not None else []
        self.ui = ui if ui is not None else []
        self.legacy_workspace = legacy_workspace  # chats saved before projects existed
        # the request being worked on; still set after a restart = it was cut off (power cut, app closed)
        self.running = running

    @property
    def path(self):
        return DIR / f"{self.id}.json"

    def meta(self):
        return {"id": self.id, "title": self.title, "project_id": self.project_id,
                "created": self.created, "updated": self.updated}

    def record(self, event):
        """Keep UI events for replay. Streaming deltas and pending approvals are not needed."""
        if event.get("type") not in ("delta", "approval"):
            self.ui.append(event)

    def name_from(self, text):
        if self.title == "New chat":
            text = " ".join(text.split())
            self.title = text[:48] + ("…" if len(text) > 48 else "")

    def save(self, touch=True):
        if not self.messages and not self.ui and not self.running:  # don't litter the list with empty chats
            # (a chat's first build has no model messages until it ends: it was never saved while it ran, so an app
            # closed mid-build lost the chat and the request started over, 2026-11-15)
            return
        DIR.mkdir(exist_ok=True)
        if touch:
            self.updated = time.time()
        data = dict(self.meta(), messages=self.messages, ui=self.ui, running=self.running)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


def load(session_id):
    if not ID_RX.fullmatch(session_id or ""):
        return None
    try:
        d = json.loads((DIR / f"{session_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return Session(d.get("project_id"), id=d["id"], title=d.get("title", "Chat"), created=d.get("created"),
                   updated=d.get("updated"), messages=d.get("messages", []), ui=d.get("ui", []),
                   legacy_workspace=d.get("workspace"), running=d.get("running"))


def list_all(project_id=None, limit=300):
    """Chat metadata, newest first. project_id filters to one project's chats."""
    out = []
    for p in DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if project_id and d.get("project_id") != project_id:
            continue
        out.append({k: d.get(k) for k in ("id", "title", "project_id", "created", "updated")})
    out.sort(key=lambda s: s["updated"] or 0, reverse=True)
    return out[:limit]


def delete(session_id):
    if ID_RX.fullmatch(session_id or ""):
        (DIR / f"{session_id}.json").unlink(missing_ok=True)
        return True
    return False


def rename(session_id, title):
    s = load(session_id)
    if not s:
        return False
    s.title = (title or "").strip()[:80] or s.title
    s.save(touch=False)
    return True


def migrate_legacy(projects_module):
    """Chats from before projects existed stored a folder: put each folder's chats in a project."""
    for p in DIR.glob("*.json"):
        s = load(p.stem)
        if not s or s.project_id or not s.legacy_workspace:
            continue
        proj = projects_module.find_by_folder(s.legacy_workspace)
        if not proj and Path(s.legacy_workspace).is_dir():
            proj = projects_module.Project(Path(s.legacy_workspace).name, [s.legacy_workspace])
            proj.save()
        if proj:
            s.project_id = proj.id
            s.save(touch=False)
