"""Projects: a name, any number of folders, and instructions for the model. Chats link to a project
by id (or to none: a general chat with no folders). Saved as JSON files in m42/projects/."""
import json
import re
import time
import uuid
from pathlib import Path

DIR = Path(__file__).resolve().parent / "projects"
NEW_FOLDERS_ROOT = Path(__file__).resolve().parent.parent / "projects"  # where "New folder" creates folders
ID_RX = re.compile(r"[0-9a-f]{12}")
NAME_RX = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class Project:
    def __init__(self, name, folders=None, instructions="", id=None, created=None, updated=None):
        self.id = id or uuid.uuid4().hex[:12]
        self.name = name
        self.folders = [str(Path(f).resolve()) for f in (folders or [])]
        self.instructions = instructions
        self.created = created or time.time()
        self.updated = updated or self.created

    def to_dict(self):
        return {"id": self.id, "name": self.name, "folders": self.folders, "instructions": self.instructions,
                "created": self.created, "updated": self.updated}

    def save(self, touch=True):
        DIR.mkdir(exist_ok=True)
        if touch:
            self.updated = time.time()
        tmp = DIR / f"{self.id}.tmp"
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(DIR / f"{self.id}.json")

    def add_folder(self, path):
        p = str(Path(path).resolve())
        if not Path(p).is_dir():
            raise ValueError(f"Folder not found: {path}")
        if p.lower() not in (f.lower() for f in self.folders):
            self.folders.append(p)

    def remove_folder(self, path):
        p = str(Path(path).resolve()).lower()
        self.folders = [f for f in self.folders if f.lower() != p]


def load(project_id):
    if not ID_RX.fullmatch(project_id or ""):
        return None
    try:
        d = json.loads((DIR / f"{project_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return Project(d["name"], d.get("folders"), d.get("instructions", ""), d["id"], d.get("created"),
                   d.get("updated"))


def list_all():
    out = []
    for p in DIR.glob("*.json"):
        proj = load(p.stem)
        if proj:
            out.append(proj.to_dict())
    out.sort(key=lambda d: d["updated"], reverse=True)
    return out


def find_by_folder(folder):
    target = str(Path(folder).resolve()).lower()
    for d in list_all():
        if any(f.lower() == target for f in d["folders"]):
            return load(d["id"])
    return None


def delete(project_id):
    if ID_RX.fullmatch(project_id or ""):
        (DIR / f"{project_id}.json").unlink(missing_ok=True)


def create_folder(name):
    """Make a new empty folder under <M42>/projects/ for the user (never overwrites)."""
    clean = NAME_RX.sub("", (name or "").strip()).strip(". ")
    if not clean:
        raise ValueError("Give the folder a name")
    NEW_FOLDERS_ROOT.mkdir(exist_ok=True)
    path = NEW_FOLDERS_ROOT / clean
    n = 2
    while path.exists():
        path = NEW_FOLDERS_ROOT / f"{clean}-{n}"
        n += 1
    path.mkdir()
    return path
