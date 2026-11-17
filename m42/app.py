"""M42 UI — a local AI that designs and builds web pages in a folder (desktop app entry point).

Runs a localhost-only HTTP server for the UI and opens it as a standalone Edge app window.
Usage: python app.py [--port 8765] [--no-window]
"""
import argparse
import base64
import contextlib
import json
import mimetypes
import os
import queue
import re
import secrets
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sitedit  # noqa: E402
import webkit  # noqa: E402
import learn  # noqa: E402
import firstrun  # noqa: E402  (a new PC: the model and llama-server downloaded by themselves)
import llamacpp  # noqa: E402  (before modelhub: they import each other)
import modelhub  # noqa: E402
import web  # noqa: E402
import webclone  # noqa: E402
import designref  # noqa: E402
import llm  # noqa: E402
import speech  # noqa: E402  (🎤 Whisper on this PC)
import updater  # noqa: E402  (new versions from the GitHub releases)
import browser  # noqa: E402  (a Chromium browser for the window on Linux / macOS)
import projects  # noqa: E402
import sessions  # noqa: E402
import agent as agent_module  # noqa: E402
from agent import Agent  # noqa: E402
from tools import ToolError, Workspace  # noqa: E402

APP_DIR = Path(__file__).resolve().parent
UI_DIR = APP_DIR / "ui"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_CONFIG = {
    "base_url": "http://127.0.0.1:11434/v1",  # Ollama / LM Studio / other; llama.cpp/* models use llamacpp.URL
    "model": "llama.cpp/auto",  # Qwen3.5-4B for everything (llamacpp.AUTO_TARGETS)
    "api_key": "",
    "temperature": 0.2,
    "max_tokens": 2048,
    "ctx_tokens": 16384,
    "max_steps": 25,
    "max_fix_attempts": 3,
    "native_tools": True,
    "approve_commands": True,
    "approve_edits": False,
    "web_enabled": True,
    # free photo libraries for the pages (photos.py); empty: Openverse (no key) is used
    "pexels_key": "",
    "speech_engine": "indic-ta",  # 🎤 indic-ta (IndicConformer Tamil: Tamil and Tanglish, live, ~0.2 s) / small (Whisper small: English)
    "pixabay_key": "",
    "update_check": True,  # look for a newer M42 UI release on GitHub when the app opens (updater.py)
    "workspace": str((APP_DIR.parent / "workspace").resolve()),
}
EDITABLE_KEYS = set(DEFAULT_CONFIG) - {"workspace"}
PROMPT_KEYS = ("model", "base_url", "ctx_tokens", "web_enabled", "native_tools")  # change => re-warm


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig")))  # -sig: tolerate a BOM
        except ValueError:
            print("config.json is invalid; using defaults")
    if llamacpp.is_local(cfg["model"]) and cfg["model"] not in llamacpp.available_models():
        cfg["model"] = "llama.cpp/auto"  # an old or missing model name: the 4B
    Path(cfg["workspace"]).mkdir(parents=True, exist_ok=True)
    return cfg


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")



class State:
    token = secrets.token_urlsafe(24)
    port = 8765
    config = None
    agent = None
    last_seen = time.time()
    goodbye_at = None
    running_session = None  # the chat whose request is running now (the window may show another one)
    llama = None
    warm = {"state": "idle", "seconds": None, "for": None}
    prepare_gen = 0
    session = None
    model_lock = threading.Lock()
    last_kind = None  # auto mode: "chat" or "code" model used for the last message
    own_shots = set()  # 📷 pictures M42 took of its own preview (their fingerprints): a correction, not a reference
    jobs = {}  # project id -> literature matrix / gaps job status
    server = None  # the HTTP server (an update's restart shuts it down)




def auto_target(kind):
    """The model an Auto mode uses for `kind` ("chat" / "code"). Code in a general chat (a whole program in one
    answer, with no project files or build checks around it) goes to the 7B coder: granite-3b's calculator ignored
    every digit, and with a screenshot it "fixed" a layout by changing nothing."""
    target = llamacpp.targets(State.config["model"])[kind]
    return target






VIEW_IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")  # shown as pictures in the file viewer
# "Open in app" from the file viewer (a project file): documents and pictures only, never a program or script
OPEN_KINDS = VIEW_IMAGES + (".svg", ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".md", ".csv",
                            ".html", ".htm", ".ino")
DOC_UPLOADS = APP_DIR / "cache" / "doc-uploads"  # documents attached in a chat
DOC_CHECKS = APP_DIR / "cache" / "doc-checks"    # their plagiarism reports and humanized copies
DOC_WORDS = 2500  # of a document given to the model with a question: 6000 words were 10,600 tokens, ~105 s to read
DOC_PLAG_RX = re.compile(r"plagi\w*|plagar\w*|copy check|similarity|originality|turnitin|copied", re.I)
DOC_HUMAN_RX = re.compile(r"humani[sz]\w*|human (la|style|mathiri|like)|rewrite (it )?natural\w*|ai detect\w*", re.I)


IMAGE_ASK_RX = re.compile(
    r"\b(image|images|picture|pic|photo|padam|poster|banner|cover|illustration|wallpaper|artwork|logo)\b.{0,40}"
    r"\b(create|generate|draw|make|design|panni|pannu|pannunga|kudu|kutu|kodu|tha|thaa|venum|vennum|varai\w*)\b|"
    r"\b(draw|varai\w*|generate|create)\b.{0,30}\b(image|picture|padam|poster|illustration|logo)\b", re.I)
NOT_PICTURE_RX = re.compile(r"diagram|chart|graph|flow ?chart|plot|uml|architecture|sprite|icon|element", re.I)
CHAT_IMAGES = APP_DIR / "cache" / "chat-images"
THIS_RX = re.compile(r"\b(this|that|the same|above|itha|intha|athe|antha|athu|mela)\b", re.I)
# Steps, not a free prompt: q35-4b wrote "futuristic station, solar panels, data transmission tower, hyper-local
# climate visualization" for an ESP32 weather node: a tower the report never mentions filled all 4 pictures, and the
# abstract words drew nothing.
PICTURE_PROMPT = """You plan one picture for an image generator, for what the user asked (use the project / document
below when the picture is about it).
1. objective: in one line, what the project does for people (its main aim).
2. subject: the ONE physical thing that shows that aim best, as it really looks (e.g. the device the project builds,
   with its real parts), not a symbol.
3. details: 2-4 other things a camera would see that show the aim: the project's real parts, what it measures shown as
   physical instruments, the people or screens that use its result. Only things the project really has. Turn ideas
   that cannot be seen (AI, prediction, security, data, smart) into something visible (e.g. a phone screen showing a
   chart) or leave them out.
4. setting: where it is, the weather and light, in a few words.
The subject must be big in the picture: for a hardware / device project show the device close up (or its parts laid
out on a desk), not a far-away landscape where small parts disappear. Short, concrete words. The generator cannot
write text, letters or exact diagrams."""
PICTURE_SCHEMA = {"type": "object", "properties": {
    "objective": {"type": "string", "maxLength": 200},
    "subject": {"type": "string", "maxLength": 120},
    "details": {"type": "array", "minItems": 2, "maxItems": 4, "items": {"type": "string", "maxLength": 80}},
    "setting": {"type": "string", "maxLength": 100},
    "style": {"type": "string", "enum": ["digital illustration", "photograph", "flat vector illustration", "3d render",
                                         "watercolor painting"]}},
    "required": ["objective", "subject", "details", "setting", "style"]}
SEEN_ANYWHERE = {"screen", "laptop", "phone", "smartphone", "monitor", "dashboard", "person", "people", "farmer",
                 "student", "engineer", "hand", "table", "desk", "chart", "graph", "map"}
PLAIN_WORDS = {"small", "large", "white", "black", "blue", "green", "metal", "plastic", "with", "showing", "mounted",
               "near", "next", "beside", "under", "over", "from", "that", "this", "their", "real", "simple", "modern",
               "compact", "tiny", "box", "pole", "device", "unit", "module"}




# Part names an image model has never learned ("ESP32" drew nothing: a plain box on a pole), as they look. With these
# a test drew blue circuit boards, sensor modules, wires and a glowing screen (2026-10-13).
PART_LOOKS = [
    (r"(esp32|esp8266|nodemcu)(-\w+)*", "small blue circuit board with a black microchip"),
    (r"arduino(?: uno| nano| mega)?", "blue circuit board with a black chip and pin headers"),
    (r"raspberry pi\s*\d*", "small green computer board with USB ports"),
    (r"dht\s?-?(11|22)(?: sensor)?", "small white sensor module with grille holes"),
    (r"bm[pe]\s?-?\d{3}(?: sensor)?", "tiny purple sensor board"),
    (r"(oled|tft)(?: display| screen)?", "small glowing screen"),
    (r"lcd(?: 16x2| display| screen)?", "small green LCD screen"),
    (r"(cup )?anemometers?", "cup anemometer"),
    (r"(tipping[- ]bucket )?rain (gauge|sensor)s?", "rain gauge funnel"),
    (r"soil moisture (sensor|probe)s?", "fork-shaped metal soil probe"),
    (r"(hc-?sr04|ultrasonic sensor)s?", "sensor with two round silver eyes"),
    (r"pir( motion)?( sensor)?", "white dome motion sensor"),
    (r"relay(?: module)?s?", "blue relay module"),
    (r"servo(?: motor)?s?", "small blue servo motor"),
    (r"breadboards?", "white breadboard with colorful jumper wires"),
    (r"(gsm|sim\d{3}\w*|lora)(?: module)?s?", "small radio module with an antenna"),
]


HOLDERS = r"(?:sensor |weather |iot )*(?:box|node|unit|station|device|kit|enclosure|case|system|prototype)"












EMBED_RX = re.compile(r"\b(esp32\w*|esp-32|esp8266|esp-?idf|nodemcu|arduino|uno|nano|raspberry pi pico|pico|rp2040|iot|"
                      r"embedded|micro-?controllers?|mcu|stm32\w*|blue ?pill|pic\d{2}\w*|pic32\w*|dspic\w*|atmega\w*|"
                      r"attiny\w*|avr|8051|at89\w*|n76\w*|ms51\w*|nuvoton|nuc\d{3}\w*|m0\d{2}\w*|msp430\w*|cortex-?m\d|"
                      r"gpio|uart|usart|i2c|spi|pwm|adc|isr|timer ?interrupt|register.?level|bare.?metal|keil|xc8|"
                      r"mplab|sdcc|platformio|led blink|blink(?:ing)? (?:an? )?led|firmware)\b", re.I)
# a request to write an embedded program ("led blink code", "uart driver kutu"): always the embedded flow, the words
# decide (every chip goes chip -> datasheet -> code -> pins -> circuit -> compile; a question with no ask is the chat's)
EMBED_PROGRAM_RX = re.compile(r"\b(code|coding|program|programme|firmware|sketch|driver|blink|circuit|cricuit|wiring|"
                              r"schematic|interface|interfacing|project)\b", re.I)
# the spellings people type ("enakku cricuit kutu" went to a normal chat that asked for "more details")
EMBED_ASK_RX = re.compile(r"\b(circuit|cricuit|circut|curcuit|circiut|cirucit|sircuit|cricut|circuits|wiring|wireing|"
                          r"connections?|conection|schematic|diagram|code|program|firmware|sketch|project|build|make|"
                          r"create|design|venum|vennum|venu|pannu|panni|tha|thaa|kudu|kodu|kutu|kudunga|kuduga|thaanga|"
                          r"ready)\b", re.I)
EMBEDDED_DIR = APP_DIR / "cache" / "embedded"
PREVIEWS = APP_DIR / "cache" / "previews"  # ▶ Run: one folder per page shown in the popup


# a page to look at the data on ("IoT project ku Web dashboard Html la ... panni kutu", 2026-10-25): the iot +
# project words sent it to "Which microcontroller?" in the circuit flow; a web page is a build / code task
WEB_UI_RX = re.compile(r"\b(web\s*(?:dashboard|page|site|app|ui|interface)|website|webpage|web-page|html|css|"
                       r"front-?end|landing page|admin panel)\b", re.I)
# ...unless the microcontroller's own program is asked for too (an ESP32 web server serving that page)
FIRMWARE_TOO_RX = re.compile(r"\b(firmware|sketch|circuit|cricuit|wiring|schematic|web\s*server|webserver|"
                             r"arduino\s+code|esp\w*\s+code|code\s+for\s+(?:the\s+)?(?:esp|arduino|nodemcu))", re.I)








FIRMWARE_ROUNDS = 3
MAX_REVIEWS = 2  # a logic review of the first file that compiles, and again of the file that fixes its points
CODE_BLOCK_RX = re.compile(r"```(?:cpp|c\+\+|arduino|c|ino)?\s*\n(.*?)```", re.S)




ARDUINO_ERR_RX = re.compile(r"\.ino:\d+(:\d+)?:\s*(fatal )?error:|Compilation error|failed to compile|"
                            r"exit status 1|was not declared in this scope", re.I)




CODE_FIRST_PROMPT = """You write the firmware for the {part} ({core}{clock}){board}, in {fw}.
Rules:
{rules}
The file starts with its pin map, between `// ---- Pin map ----` and `// ---- end of pin map ----`: one line per
signal wired to the chip, `#define NAME <what the code uses> // pin <the chip's pin name, e.g. PA5 / RB0 / PB5>: <what
is connected>`. M42 checks these pins against the chip and draws the circuit from them: every wired pin is in it and
the code uses these defines (other defines are fine; only pin lines have the `// pin` comment).
{pins}
The program must:
{features}
Parts wired to the chip:
{parts}
Write the whole file in one ```{lang} block, then at most 3 short lines on how to build and flash it."""
NO_REG_CHECK = ("stm32-hal", "esp-idf")  # their API names (GPIO_PIN_13, GPIO_NUM_2) are not in the register files




CHANGE_RX = re.compile(r"\b(add|remove|delete|change|replace|instead|innum|also|extra|another|update|modify|edit|move|"
                       r"maathu|mathu|maattu|maatru|serthu|sethu|sei|eduthudu|edu|kooti|koottu|kammi|kurai|fix|sari ?pannu|"
                       r"increase|decrease|faster|slower|speed|thappu|wrong)\b", re.I)




PARTS_CHANGE_RX = re.compile(r"\b(add|remove|delete|another|extra|innum oru|innoru|serthu|sethu|kooti|eduthudu|"
                             r"vendam|venam|without)\b", re.I)
VERIFY_SCHEMA = {"type": "object", "properties": {
    "ok": {"type": "string", "enum": ["yes", "no"]},
    "why": {"type": "string", "maxLength": 300},
    "facts": {"type": "string", "maxLength": 400},
    "changes": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 160}}},
    "required": ["ok", "why", "facts", "changes"]}



















ASKED_PIN_RX = re.compile(r"\b(?:pin|gpio|io|d)\s*-?\s*(\d{1,2})\b|\b((?:R|P)[A-K]\d{1,2}|P\d\.\d)(?![\w.])|\b(A\d{1,2})\b", re.I)










COMPILE_ASK_RX = re.compile(r"^\s*(re-?)?(compile|build)\b|\b(compile|build) (pannu|panni|it|again|pannunga|now)\b", re.I)




COMPILE_ERR_RX = re.compile(r"\.(?:ino|c|cpp|h):\d+(:\d+)?:\s*(fatal )?error:|Compilation error|failed to compile|"
                            r"exit status 1|was not declared in this scope|undefined reference|\berror\s*(?:C\d+|\[\w+\]|:)",
                            re.I)




GAME_MAX_TOKENS = 7000  # a whole canvas game in one answer (4,096 cut the Mario game off; context is 16,384)
KIND_TITLE = {"game": "The game in the picture", "error": "The error in the picture", "circuit": "The circuit in the picture",
              "result": "The results in the picture", "document": "The text in the picture"}


def design_refs(message, spec, emit, images=None, model=None):
    out = _design_refs(message, spec, emit, images, model)
    # looked now, not the second call after the data-source answer (both GitHub references skipped returned the spec
    # itself: a test by identity left the 2026-11-09 benchmark run without its example)
    if spec and not spec.get("ref_done") and not State.agent.stop_event.is_set():
        out = State.agent.with_plan_example(message, out, emit)
    if spec and spec.get("recipe") and isinstance(out, dict):
        out = dict(out, hero=spec.get("hero"), sections=spec.get("sections"))
        if out.get("ref_layout") not in (None, "top-nav", "single-column"):
            out["ref_layout"] = "top-nav"
    return out


def _design_refs(message, spec, emit, images=None, model=None):
    """The design of a page / site from references (designref.py; the user, 2026-10-27: "look at how real designs
    of that kind are made, then build: dynamic, not static"): the screenshots the user attached, else real public
    sites of that kind that M42 finds and captures. The vision model reads their design; the spec gets their
    layout, hero, section order and look. Returns the spec (unchanged when there is no reference)."""
    agent = State.agent
    if spec and spec.get("ref_done"):  # already from a reference (before the data-source question was asked)
        return spec
    agent._design_ref = agent._ref_grid = None
    # the coder for the cards the widget library lacks (agent.custom_cards), loaded only if a page needs one
    # (web: the 4B for every kind; it was the 7B coder for "code")
    agent.load_model = lambda kind, em: ((auto_target("chat") if switch_web(em) else None)
                                         if llamacpp.is_auto(State.config["model"]) else State.config["model"])
    if not spec or agent.stop_event.is_set():
        return spec
    vision = llamacpp.vision_model(auto_target("chat"))
    refs = [u for u in images or [] if isinstance(u, str) and IMAGE_URL_RX.match(u)][:3]
    agent._ref_kind = None if refs else ""  # None: the user's own shots (always used); find_design_refs sets the kind
    agent._ref_entry = {}
    # (no GitHub template lookup since 2026-11-10: of 7 requests tried, its demos fitted 2, and the reading took
    # ~90 s; a picture the user attaches is the reference, else M42 designs the page itself)
    if not refs:  # no picture anywhere: the design data of this kind of product (uiux.py), where the 4B guessed
        return dict(agent.design_data(message, spec, emit, model=model), ref_done=True)  # looked once: not again after the data-source answer
    if not vision or not switch_model(vision, "chat", emit, vision=True):
        try:  # no vision file: the pixels still give light / dark, colours and density
            return designref.merge(spec, [], [designref.profile(r) for r in refs], message)
        except (OSError, ValueError):
            return spec
    out = agent.read_design_refs(message, spec, refs, emit, vision)
    if isinstance(out, dict) and not out.get("ref_done") and not agent.stop_event.is_set():
        # every reference found was skipped as no page of this kind (both GitHub demos, 2026-11-10): M42's own design,
        # as when none is found (the 4B's own grey colours stayed)
        out = dict(agent.design_data(message, out, emit, model=model), ref_done=True)
    return out


NO_FOLDER = "Open a project folder first (Project → a folder): M42 UI builds the pages in it and changes them there."


def reuse_existing(message, images, emit, decided=None):
    """A page asked for in a folder that already has one (agent.existing_build decides, the reason is shown): the
    same request (and picture) again is drawn anew from its saved plan in seconds; a change is an edit; a new picture
    for the same site keeps its content; another page backs the old one up first. True when it is handled here."""
    agent = State.agent
    refs = [u for u in images or [] if isinstance(u, str) and IMAGE_URL_RX.match(u)][:3]
    agent._raw_message, agent._ref_hash, agent._old_content = message, designref.fingerprint(refs[0]) if refs else "", ""
    agent._understood = False  # (this request is read anew: agent.understand)
    agent.use_intent({})
    # a 📷 picture of the page itself (the user, 2026-11-12: "menu overlay aguthu paru" with it was read as a new design
    # and the whole page built again): a correction of that page
    owns = [r for r in refs if designref.fingerprint(r) in State.own_shots]
    photos = [r for r in refs if r not in owns]  # (with a 📷 of the page: the user's own photo to put on it)
    own = bool(owns)
    roles = {}
    if refs and not decided and agent.workspace.roots and sitedit.load(agent.workspace.roots[0][1]):
        # what each picture is FOR, the model deciding (the user, 2026-11-13: "to take its design, to modify the page,
        # to take one part of it: the 4B must understand it, no word rules")
        roles, rwhy = agent.picture_roles(message, refs, owns, sitedit.load(agent.workspace.roots[0][1]), emit,
                                          model=llamacpp.vision_model(auto_target("chat")))
    if roles:
        kinds = set(roles.values())
        decision = ("new" if "new_page" in kinds else "restyle" if "redesign" in kinds else
                    "question" if kinds <= {"question"} else "edit")
        why = rwhy or {"new": "a new page like your picture", "restyle": "your page in the picture's design",
                       "question": "a question about your picture", "edit": "a change to your page with your picture"}[decision]
        pick = lambda *r: [u for i, u in enumerate(refs) if roles.get(i) in r]  # noqa: E731
        shots, photos, adds, styles, colours = pick("correct_page"), pick("photo"), pick("add_part"), pick("style_part"), pick("colours")
    else:
        decision, why = decided or agent.existing_build(message, refs, model=llamacpp.vision_model(auto_target("chat")) if refs else None,
                                                        own_shot=own)
        shots, photos, adds, styles, colours = (owns[:1], photos, [], [], []) if own else ([], [], refs, [], [])
    if not decision:
        return False
    if decision == "unclear":  # (mic noise: "டும்ம் சுந்தர்ஹோ ந" started a new build, 2026-11-13)
        emit({"type": "assistant_start"})
        emit({"type": "assistant_text", "text": f"🤔 I could not make out a request in that ({why}). Nothing was changed: say it again?"})
        return True
    emit({"type": "note", "message": f"♻ {why}"})
    root = agent.workspace.roots[0][1]
    if decision == "redraw":
        agent.edit_site(message, emit, redraw="drawn again from the saved plan with the latest templates; your changes kept")
        return True
    if decision == "edit":  # (with a picture: what is added or changed is drawn as the part of it the user means; a
        # 📷 of the page itself is shown to the line edit, to see what is wrong)
        agent._edit_refs, agent._edit_shot, agent._edit_photos = adds, (shots[0] if shots else None), photos
        agent._edit_styles, agent._edit_colours = styles, colours
        agent._edit_reading = why  # (the first reading, to the locate step: "பேர மாத்து லேர்ன் ஹப் னு வை" was read as a
        # rename here and as a section's change there, 2026-11-13)
        try:
            agent.edit_site(message, emit)
        finally:
            agent._edit_reading = ""
            agent._edit_refs, agent._edit_shot, agent._edit_photos, agent._edit_styles, agent._edit_colours = [], None, [], [], []
        return True
    if decision == "question":  # a question about the page: answered, nothing changed (no tools)
        agent.answer_about_site(message, emit)
        return True
    site = sitedit.load(root)
    if decision == "restyle" and site:
        agent._old_content = sitedit.content_text(site)
    saved = agent.backup_site(root)
    if saved:
        emit({"type": "note", "message": f"♻ The page there now is saved in {saved} (its pages, plan and pictures)"})
    return False


def page_mark(marks):
    """A mark on a 📷 of the preview, as a place on the page: {"page": file, "x", "y": its middle in the page's own
    pixels, "width": the width the page was drawn at}; None without one. (The marked picture alone was read as the
    section below the mark, 2026-11-12.)"""
    for m in marks or []:
        try:
            box, size = [float(v) for v in m["box"]], [float(v) for v in m["size"]]
            width, scroll = float(m["width"]), float(m.get("scroll") or 0)
            k = width / size[0] if size[0] else 1
            page = Path(str(m.get("page") or "index.html")).name
            if not re.fullmatch(r"[\w .-]+\.html?", page):
                page = "index.html"
            return {"page": page, "x": (box[0] + box[2]) / 2 * k, "y": scroll + (box[1] + box[3]) / 2 * k, "width": round(width),
                    "x0": box[0] * k, "x1": box[2] * k, "y0": scroll + box[1] * k, "y1": scroll + box[3] * k,
                    "vy0": box[1] * k, "vy1": box[3] * k}  # (on the screen: a menu bar that stays at the top when scrolled)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    return None


def web_request(message, emit, decided=None):
    """A page or site in the open folder: its spec (and its one question), the design reference (a picture the user
    gave, else an open-source template on GitHub, else M42's own design), the page plan, then M42 builds it."""
    agent = State.agent
    model = auto_target("chat") if llamacpp.is_auto(State.config["model"]) else None
    kept = agent.resumed(message)  # 💾 a cut-off build continued: its spec as it was (no model call again)
    if kept and kept.get("spec"):
        spec = kept["spec"]
        emit({"type": "note", "message": f"♻ Continuing the cut-off build from its last finished step ({kept['stage']}): "
                                         "the page's spec and skeleton kept, not decided again"})
    else:
        if reuse_existing(message, [], emit, decided):
            return
        spec = agent._page_spec(message, emit, model=model)
        if agent.stop_event.is_set() or agent.ask_page_question(message, spec, emit):
            return
        spec = design_refs(message, spec, emit, model=model)
        if spec and not agent.stop_event.is_set():
            agent.run_checkpoint("spec", message, spec=spec)
    built = agent.page_from_plan(message, spec, emit, model=model) if spec else False
    if built == "rules" and switch_web(emit):
        agent.finish_plan_page(message, emit)
    elif not built and switch_web(emit):
        agent.page_spec = spec or False
        agent.run(message, emit)


def page_with_reference(message, images, emit, vision):
    """"intha mathiri design la oru restaurant site pannu" + a screenshot (a Dribbble shot the user saved): the
    picture is the design reference, not a page to copy. Spec, its design from the picture, the page plan, M42's
    templates (a site of several pages in a project folder)."""
    agent = State.agent
    agent.stop_event.clear()  # a Stop pressed during an earlier request
    if reuse_existing(message, images, emit):
        return
    agent.understand(message, emit, image=images[0] if images else None, model=vision)
    agent._ref_read = ([], [])
    # the picture first: its design, and what it is about. "intha mathiri oru site pannu admin dashboard" with a smart
    # home dashboard shot became a "Tamil Nadu Bus Admin" when only its design was taken: with no subject in the
    # words, the picture's own topic is the subject (the user's words win when they name one)
    design_refs(message, {"title": ""}, emit, images=images, model=vision)
    briefs, profiles = agent._ref_read
    topic = next((b["topic"] for b in briefs if b and b.get("topic")), "")
    if not topic and getattr(agent, "_ref_grid", None):  # no topic read: the reference's own cards say what it is
        topic = "a dashboard with " + ", ".join(s["name"] for s in agent._ref_grid["sections"][:5])
    asked = message
    it = webkit.INTENT
    if it.get("subject") and it.get("names_subject") is False:  # the model read the words as "this design": the picture's subject
        asked = f"{message} (about: {it['subject']}, as in the reference picture)"
        emit({"type": "note", "message": f"🎨 Your words name no subject: the page is about what your picture shows ({it['subject']})"})
    elif topic:  # the model decides between the words and the picture
        asked = f"{message} (the reference picture shows: {topic}; that is the subject unless the request names another)"
    grid = getattr(agent, "_ref_grid", None)  # the picture's own cards: the spec is made from them, no web search
    part = None
    if it.get("picture_part") and images:  # ONE part of the picture asked for ("intha queue card mattum pannu"): that card
        part = agent.pick_picture_part(message, images, it["picture_part"], emit, vision)
        if part:
            agent._ref_grid = grid = None
            agent._ref_pages = None
            if topic and topic.lower() not in asked.lower():  # what the picture is of (its "Print queue" became
                asked = f"{asked} (from a picture of: {topic})"  # office printers' toner without it)
    picture = "\n".join(f"- {s['name']} ({s['part'].replace('_', ' ')}): {s['what']}" for s in (grid or {}).get("sections") or [])
    if part:
        picture = "\n".join(f"- {s['name']} ({s['part'].replace('_', ' ')}): {s['what']}  [the ONLY parts of the page, as in the picture]"
                            for s in part.get("sections") or [part["section"]])
    if not picture:
        picture = "\n".join(f"- {x}" for b in briefs if b for x in b.get("sections") or [])
    shots = getattr(agent, "_ref_pages", None)  # the pictures are the screens of one app: each its own page
    if shots:
        picture = "\n".join(f"- {s['name']} ({s['part'].replace('_', ' ')}): {s['what']}  [the {p['name']} page]"
                            for p in shots["ref_pages"] for s in p["sections"])
    spec = agent._page_spec(asked, emit, model=vision, picture=picture)
    if spec and (briefs or profiles):
        spec = designref.merge(spec, briefs, profiles, asked)
    if spec and getattr(agent, "_ref_grid", None):  # the reference's own cards, in its grid
        spec = dict(spec, **agent._ref_grid)
    if spec and shots:  # a page per picture, the pictures' own menu
        spec = dict(spec, **shots)
    if spec and part:  # the page is that one card, drawn as in the picture (its kind, its blocks, its look)
        spec = dict(spec, sections=[{k: s0[k] for k in ("name", "what", "part", "look", "count") if k in s0}
                                    for s0 in part.get("sections") or [part["section"]]],
                    hero="compact", ref_grid=None, recipe=None, app_pages=None, ref_pages=None, only_part=True)
    message = asked
    if agent.stop_event.is_set() or agent.ask_page_question(message, spec, emit):
        return
    built = agent.page_from_plan(message, spec, emit, model=vision) if spec else False
    auto = llamacpp.is_auto(State.config["model"])
    if built == "rules" and switch_web(emit):
        agent.finish_plan_page(message, emit)
    if not built and switch_web(emit):
        agent.page_spec = spec or False
        agent.run(message, emit)






def stamp():
    return time.strftime("%Y%m%d-%H%M")


def allowed_media(path, workspace):
    """A picture the UI may load: one M42 saved for this chat (cache/chat-images) or one in a project folder."""
    p = Path(path).resolve()
    if p.suffix.lower() not in (".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif", ".bmp") or not p.is_file():
        return None
    roots = [CHAT_IMAGES.resolve()] + [r.resolve() for _, r in workspace.roots]
    return p if any(r == p.parent or r in p.parents for r in roots) else None


def clone_site(message, emit):
    """"intha site clone pannu https://..." without a screenshot: M42 opens the site, takes the picture itself, and
    the page is rebuilt from it like from a screenshot (plus the site's own texts)."""
    url = web.urls_in(message)[0]
    pid = "site_" + secrets.token_hex(3)
    emit({"type": "progress", "id": pid, "text": f"🌐 Opening {url}"})
    CHAT_IMAGES.mkdir(parents=True, exist_ok=True)
    shot = webclone.live_snapshot(url, str(CHAT_IMAGES / f"{stamp()}-{secrets.token_hex(2)}-site.png"))
    if not shot:
        emit({"type": "progress", "id": pid, "done": True, "text": f"🌐 Could not open {url}"})
        emit({"type": "error", "message": f"M42 could not open {url} (no connection, a private address, or the site "
                                          "refused). Send a screenshot of the page instead."})
        return
    emit({"type": "progress", "id": pid, "done": True, "text": f"🌐 Opened {url}"})
    emit({"type": "image", "path": shot, "files": [shot], "caption": f"The live site, opened by M42: {url}"})
    vision = llamacpp.vision_model(auto_target("chat"))
    if switch_model(vision, "chat", emit, vision=True):
        # the site is the design reference and M42 builds the page in its own templates (the user, 2026-10-27:
        # "clone / ithe mathiri, whatever I say, build it"), not the coder copying the picture
        page_with_reference(message, [webclone.to_data_url(shot)], emit, vision)


def _clone_page():
    """The page the last clone run wrote: the project's index.html, or the newest chat page."""
    roots = State.agent.workspace.roots
    if roots:
        return roots[0][1] / "index.html"
    pages = sorted(agent_module.CHAT_PAGES.glob("page-*.html"), key=lambda p: p.stat().st_mtime) \
        if agent_module.CHAT_PAGES.exists() else []
    return pages[-1] if pages else None


def _render(page):
    CHAT_IMAGES.mkdir(parents=True, exist_ok=True)
    return webclone.snapshot(page, CHAT_IMAGES / f"{stamp()}-{secrets.token_hex(2)}-page.png")


CLONE_FIX = """[M42 looked at your page in a browser and compared it with the reference]
It does not look like the reference yet:
{diffs}

Your page now:
```html
{code}
```
Write the complete corrected file{where}. Keep every text; fix the colours, backgrounds and layout above."""


def clone_check_and_fix(message, reference, emit, rounds=1, extra=""):
    """Render the page, compare it with the reference (colours region by region + CSS traps), and send the coder
    back with the differences (the technisite.in clone was white with black triangles; the browser check had said
    "no errors"). Returns the differences still left."""
    agent = State.agent
    diffs = []
    for attempt in range(rounds + 1):
        page = _clone_page()
        if not page or not page.is_file():
            return []
        shot = _render(page)
        code = page.read_text(encoding="utf-8", errors="replace")
        seen = webclone.compare(reference, shot) if reference and shot else []
        traps = webclone.code_traps(code)
        if reference and shot and not any("black areas" in d for d in seen):
            # the picture shows no black shapes: a fill-less SVG in the code is drawn over or unused
            traps = [t for t in traps if not t.startswith("a data: SVG pattern has shapes without a fill")]
        diffs = seen + traps
        diffs += [extra] if extra and attempt == 0 else []
        if shot:
            emit({"type": "image", "path": str(shot), "files": [str(shot), str(page)],
                  "caption": ("M42's page, rendered" + (" (after the fix)" if attempt else "")
                              + (": still different from the reference" if diffs else ": close to the reference"))})
        if not diffs or attempt == rounds or agent.stop_event.is_set():
            break
        emit({"type": "check", "message": "👀 Compared with the reference:\n" + "\n".join(f"- {d}" for d in diffs)})
        where = " with write_file as index.html" if agent.workspace.roots else " in one ```html block"
        agent.run(CLONE_FIX.format(diffs="\n".join(f"- {d}" for d in diffs), code=code[:12000], where=where), emit,
                  routing=False, research=False)
    agent.last_clone = {"reference": reference, "message": message}
    return diffs


def clone_again(message, emit):
    """The user says the clone doesn't look like the site yet: compare again and fix (their words go along)."""
    clone = State.agent.last_clone
    left = clone_check_and_fix(clone.get("message", ""), clone.get("reference"), emit, rounds=1,
                               extra=f"the user says: \"{message}\"")
    emit({"type": "note", "message": ("Still different:\n" + "\n".join(f"- {d}" for d in left)) if left
          else "👀 M42's page now matches the reference's colours and layout checks."})
    emit({"type": "done", "no_verify": True})


def build_clone(message, spec, colours, emit, auto, reference=None):
    """The page in the screenshot rebuilt as one index.html, then compared with the reference and fixed once."""
    agent = State.agent
    roots = agent.workspace.roots
    t = webclone.task(spec, colours, bool(webclone.POLISH_RX.search(message or "")), bool(roots))
    if not switch_web(emit):
        return
    agent.run(t, emit, routing=False, research=False)
    # up to two fixes: the first one fixed technisite's colours (9 differences -> 2), the hero stayed in a row
    left = clone_check_and_fix(message, reference, emit, rounds=2)
    if left:
        emit({"type": "note", "message": "Still different from the reference:\n" + "\n".join(f"- {d}" for d in left)
              + "\nSay \"innum same ah illa\" and M42 compares and fixes it again."})




CREATIVE_PROMPT = """You write the prompt for an image generator (Stable Diffusion) for the picture the user asks for.
The user may write in Tanglish and misspell words: read what they mean ("cyberbunk city" = a cyberpunk city).
- subjects: the main things the user asked to see, in English, spelled right (e.g. ["cat", "cyberpunk city"])
- main: the main subject with what it is doing, at most 8 words (e.g. "a cat walking")
- prompt: one picture, at most 40 words, comma-separated: the subjects FIRST, exactly as the user wants them (what
  they are doing), then the setting, light, colours and mood that fit. Never replace the user's subject with
  something else. No text or letters in the picture.
- style: the look that fits (photograph, digital illustration, 3d render, anime, oil painting, watercolor...)"""
CREATIVE_SCHEMA = {"type": "object", "properties": {
    "subjects": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string", "maxLength": 40}},
    "main": {"type": "string", "maxLength": 60},
    "prompt": {"type": "string", "maxLength": 300}, "style": {"type": "string", "maxLength": 40}},
    "required": ["subjects", "main", "prompt", "style"]}






BACKDROP_PROMPT = """The user attached a photo of a product and wants it on a new background. Write:
- product: what the product is, in 1-4 words
- backdrop: the EMPTY scene only, as an image-generator prompt of at most 25 words: a real-looking place with a
  surface in front for the product to stand on (a polished stone or wooden tabletop, a display stand...) and a softly
  blurred place behind it, with the colours, light and mood from the user's words. The place must suit the product
  and the people who buy it (where it is shown, sold or used): a watch belongs in a boutique, on a dresser or a
  desk, never in a kitchen or bathroom. Never name the product or put any object on the surface: the product is
  added afterwards.
- variations: 3 more scenes in the same spirit (other places / materials / light), at most 15 words each."""
BACKDROP_SCHEMA = {"type": "object", "properties": {
    "product": {"type": "string", "maxLength": 40}, "backdrop": {"type": "string", "maxLength": 200},
    "variations": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "string", "maxLength": 120}}},
    "required": ["product", "backdrop", "variations"]}




PPT_RX = re.compile(r"\b(ppt|pptx|power ?point|slides?|silde?s?|presentation)\b", re.I)
SLIDES_PROMPT = """You make a presentation from a document. Write {n} content slides that walk through the document
in its own order (for a report, e.g.: problem and motivation, objectives, existing work, proposed system, architecture,
method, results or expected results, plan, conclusion: whatever the document actually has). Each slide: a short title
and 3-5 bullets of at most 14 words each. Use only facts from the document; keep its numbers, names and terms. No
bullet may repeat another slide. Also give the presentation title and a one-line subtitle."""
















def switch_session(session):
    """Make `session` current: the agent gets its conversation and its project (or none)."""
    State.session = session
    proj = projects.load(session.project_id) if session.project_id else None
    if session.project_id and not proj:
        session.project_id = None  # its project was deleted: keep it as a general chat
    State.agent.load(session.messages, proj.to_dict() if proj else None)
    for ev in reversed(session.ui or []):  # the firmware project of this chat (⑦): follow-ups and fixes go on from it
        if ev.get("type") == "embedded_project" and Path(ev["project"].get("file", "")).is_file():
            State.agent.last_chip_code = ev["project"]
            break
    # a plan shown but not built yet survives a restart: "pannu" in this chat still builds it
    for ev in reversed(session.ui or []):
        if ev.get("type") == "build_step":
            break
        if ev.get("type") == "plan":
            State.agent.last_plan = ev.get("plan")
            break


def reload_project_if_current(proj):
    """Folders or instructions changed: the open chat of that project sees them right away."""
    if State.session.project_id == proj.id:
        State.agent.load(State.session.messages, proj.to_dict())


def session_payload():
    s = State.session
    folders = [{"alias": a, "path": str(r)} for a, r in State.agent.workspace.roots]
    interrupted = None  # (M42 UI has no step-by-step Build mode)
    busy_here = State.agent.busy.locked()  # this chat's request is running right now, not cut off
    cut_off = None if busy_here or not s.running else {"text": s.running.get("shown") or s.running.get("text"),
                                                       "started": s.running.get("started")}
    run = State.running_session if busy_here else None
    return dict(s.meta(), ui=s.ui, project=State.agent.project, folders=folders, interrupted=interrupted,
                cut_off=cut_off, live=bool(run is not None and run is s), running_id=run.id if run is not None else None,
                resumable=bool(cut_off) and resume_point(s) is not None)


def view_payload(s):
    """Another chat looked at while a request runs in its own chat: shown as it is, nothing switched (the agent
    keeps the running chat's conversation and project)."""
    proj = projects.load(s.project_id) if s.project_id else None
    run = State.running_session
    return dict(s.meta(), ui=s.ui, project=proj.to_dict() if proj else None, folders=[], interrupted=None, cut_off=None,
                live=False, view_only=True, running_id=run.id if run is not None else None)


def resume_point(s):
    """A request cut off (the app closed, a power cut) whose page build kept its steps: what is kept, else None."""
    run = s.running or {}
    roots = State.agent.workspace.roots if State.agent else []
    if not run or not roots:
        return None
    try:
        return State.agent.resume_info(roots[0][1], run.get("text") or "")
    except (OSError, ValueError, AttributeError):
        return None




def project_payload(proj):
    return dict(proj.to_dict(), chats=sessions.list_all(project_id=proj.id),
                missing=[f for f in proj.folders if not Path(f).is_dir()])


IMAGE_URL_RX = re.compile(r"^data:image/(png|jpeg|webp);base64,")
# ▶ the cut-off request continued: "continue", "resume", "thodaru" (and in Tamil letters)
CONTINUE_RX = re.compile(r"^\s*(?:▶\s*)?(continue|resume|go on|thodaru|thodarnthu|thodar|தொடரு|தொடர்|கன்டினியூ|கண்டினியூ)\b", re.I)


def save_shots(images):
    """Keep a report's screenshots in the project (.m42/reports/), so the report log points at them."""
    roots = State.agent.workspace.roots
    if not roots:
        return []
    folder = roots[0][1] / ".m42" / "reports"
    saved = []
    try:
        folder.mkdir(parents=True, exist_ok=True)
        for i, url in enumerate(images, 1):
            head, data = url.split(",", 1)
            ext = {"png": "png", "jpeg": "jpg", "webp": "webp"}[IMAGE_URL_RX.match(head + ",").group(1)]
            path = folder / f"shot-{time.strftime('%Y%m%d-%H%M%S')}-{i}.{ext}"
            path.write_bytes(base64.b64decode(data))
            saved.append(str(path.relative_to(roots[0][1])).replace("\\", "/"))
    except (OSError, ValueError, KeyError):
        pass
    return saved


def switch_model(target, kind, emit, vision=False, warm=True):
    """Load `target` for the next part of a request (a request with screenshots uses the vision model, then
    the coder), with the same notes as the automatic switch."""
    agent = State.agent
    key = target[len(llamacpp.PREFIX):] if llamacpp.is_local(target) else None
    if key and State.llama.model == key and State.llama.state == "ready" and (State.llama.vision == bool(vision)
                                                                           or key in llamacpp.VISION_ALWAYS):
        agent.model_override = target if llamacpp.is_auto(State.config["model"]) else None
        return True
    started = time.time()
    shown = "vision" if vision else kind  # "to read the picture": the 9B chat model can't, so this is the 4B
    emit({"type": "model_switch", "state": "start", "to": target, "kind": shown})
    try:
        activate(target, vision, warm)
    except llm.LLMError as e:
        emit({"type": "error", "message": f"Could not load {target}: {e}"})
        return False
    emit({"type": "model_switch", "state": "done", "to": target, "kind": shown, "secs": round(time.time() - started, 1)})
    State.last_kind = kind
    return True


def switch_web(emit):
    """A web page / site / card is written by the chat model (the 4B) only, never the 7B coder (the user, 2026-11-03:
    "web design ku ellame 4B mattum": the coder took too long). The 4B stays as it is loaded (with or without its
    vision file: no reload for that)."""
    if not llamacpp.is_auto(State.config["model"]):
        return True
    target = auto_target("chat")
    key = target[len(llamacpp.PREFIX):] if llamacpp.is_local(target) else None
    if key and State.llama.model == key and State.llama.state == "ready":
        State.agent.model_override = target
        State.last_kind = "chat"
        return True
    return switch_model(target, "chat", emit, warm=False)


def keep_awake(on):
    """While a request runs, tell Windows not to sleep (the screen may still turn off), like a media player
    does. ES_CONTINUOUS | ES_SYSTEM_REQUIRED; ES_CONTINUOUS alone clears it. Per thread, so it is set and
    cleared on the request's own thread."""
    if os.name != "nt":  # macOS: caffeinate while it runs; Linux: systemd-inhibit (when there)
        global _awake
        if on and _awake is None:
            cmd = (["caffeinate", "-i", "-w", str(os.getpid())] if sys.platform == "darwin" else
                   ["systemd-inhibit", "--what=idle:sleep", "--who=M42 UI", "--why=a request is running", "sleep", "infinity"]
                   if shutil.which("systemd-inhibit") else None)
            if cmd and shutil.which(cmd[0]):
                try:
                    _awake = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except OSError:
                    _awake = None
        elif not on and _awake is not None:
            _awake.terminate()
            _awake = None
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 if on else 0x80000000)
    except (OSError, AttributeError):
        pass


_awake = None  # (Linux / macOS: the process that keeps the PC awake while a request runs)


def activate(model, vision=False, warm=True):
    """Load `model` (a concrete model, not "auto") and get its prompt cache ready: restored from disk
    in ~1 s when saved before, otherwise warmed (~30 s) and saved. Returns warm-up seconds.
    vision: load it with its image projector and skip the warm-up (the screenshot prompt is different)."""
    cfg = State.config
    with State.model_lock:
        State.agent.model_override = model if llamacpp.is_auto(cfg["model"]) else None
        State.warm = {"state": "loading", "seconds": None, "for": model}
        if llamacpp.is_local(model):
            freed = llm.unload_ollama_models(cfg["base_url"])  # don't keep two 7B models in RAM
            if freed:
                print(f"Unloaded from Ollama: {', '.join(freed)}")
            # the image file only when a picture needs it: loaded always (to skip the reload for the first picture),
            # the 9B read text at 21.6 tok/s instead of 52 (the projector takes the iGPU's memory): 254 s for a
            # 5,500-token chat
            if not State.llama.ensure(model, cfg.get("ctx_tokens", 16384), vision=vision):
                State.warm = {"state": "error", "seconds": None, "for": model}
                raise llm.LLMError(State.llama.error or f"could not start {model}")
        else:
            State.llama.stop()  # free ~5 GB of RAM when using another backend
        if vision or not warm:  # screenshots, builds and fixes don't use the chat prompt cache: no ~30 s warm-up
            State.warm = {"state": "ready", "seconds": 0.0, "for": model, "restored": False}
            return 0.0
        State.warm = {"state": "warming", "seconds": None, "for": model}
        cache_file = f"{State.agent.prompt_signature()}.bin"
        restored = llamacpp.is_local(model) and State.llama.restore_prompt_cache(cache_file)
        # Restored: skip the warm-up request. On Qwen3.5 (hybrid recurrent layers) a request that repeats the
        # cached prompt exactly is processed again from scratch (~60 s measured); the next real message only
        # adds tokens to the restored cache.
        secs = 0.0 if restored else State.agent.warm_up()
        if llamacpp.is_local(model) and not restored:
            State.llama.save_prompt_cache(cache_file)  # next start restores this in seconds
        State.warm = {"state": "ready", "seconds": secs, "for": model, "restored": restored}
        print(f"Ready: {model} in {secs}s" + (" (prompt cache restored from disk)" if restored else ""))
        return secs


def auto_target(kind=None):
    """In auto mode: the concrete model for a kind ("chat" / "code"); otherwise the selected model."""
    if not llamacpp.is_auto(State.config["model"]):
        return State.config["model"]
    return llamacpp.targets(State.config["model"])[kind or State.last_kind or "chat"]


def shortname(model):
    return (model or "?").replace(llamacpp.PREFIX, "")


def loaded_model():
    """The model that can answer right now without a switch (for the quick task decision), or None while one is
    loading: then the words decide."""
    if not llamacpp.is_local(State.config["model"]) and not llamacpp.is_auto(State.config["model"]):
        return State.config["model"]  # another backend (Ollama): no load to wait for here
    if State.llama.state == "ready" and State.llama.model:
        return llamacpp.PREFIX + State.llama.model
    return None


@contextlib.contextmanager
def held_cache():
    """Around a short side request to the loaded model (the task decision, a lesson): its cache of this chat is
    saved first and put back after (~1-2 s), so the next answer doesn't re-read the whole chat (~30 s+)."""
    held = llamacpp.is_local(State.agent.active_model()) and State.llama.hold_cache()
    try:
        yield
    finally:
        if held:
            State.llama.restore_prompt_cache(llamacpp.HOLD_FILE)


agent_module.SIDE_CACHE = held_cache


TASK_LABELS = {"answer": "💬 Answer in the chat", "code": "💻 Write code", "build": "🏗 Plan a project build",
               "embedded": "🔌 Circuit + firmware", "image": "🎨 Draw a new picture", "photo_edit": "🎨 Edit the photo"}


def prepare_backend():
    """Load the selected model (auto mode: the chat model) and warm its prompt cache. Runs in a thread."""
    State.prepare_gen += 1
    gen = State.prepare_gen

    def work():
        try:
            activate(auto_target())
        except llm.LLMError as e:
            if gen == State.prepare_gen:
                State.warm = dict(State.warm, state="error")
                print(f"Warm-up failed: {e}")

    threading.Thread(target=work, daemon=True).start()


def pick_folder(initial, title=None):
    """Native folder picker via tkinter (stdlib). Returns '' if cancelled or unavailable."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return ""
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # the dialog is owned by this window, so it opens above M42
    root.update()
    try:
        return filedialog.askdirectory(parent=root, initialdir=initial, mustexist=True,
                                       title=title or PICKER_TITLE) or ""
    finally:
        root.destroy()


PICKER_TITLE = "Choose a project folder"


def pick_model_file(initial):
    """Native file picker for a 🔌 plugin model. Returns '' if cancelled or unavailable."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return ""
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        return filedialog.askopenfilename(parent=root, initialdir=initial, title="Choose a model file", filetypes=[
            ("Models", "*.onnx *.safetensors *.pth *.pt *.ckpt"), ("All files", "*.*")]) or ""
    finally:
        root.destroy()


AUDIO_URL_RX = re.compile(r"^data:audio/(wav|x-wav|wave|mpeg|mp3|flac|x-flac|ogg|webm|mp4|x-m4a|m4a|aac);base64,")






def pick_gguf(initial):
    """Native file picker for the user's own model (.gguf). Returns '' if cancelled or unavailable."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return ""
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        return filedialog.askopenfilename(parent=root, initialdir=initial, title="Choose your model (.gguf)",
                                          filetypes=[("GGUF model", "*.gguf"), ("All files", "*.*")]) or ""
    finally:
        root.destroy()


class Handler(BaseHTTPRequestHandler):
    server_version = "M42"

    def log_message(self, fmt, *args):
        pass

    # ---- helpers ------------------------------------------------------------

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def _authorized(self, query):
        # Block other websites (CSRF / DNS rebinding) from driving the agent.
        host = self.headers.get("Host", "")
        if host not in (f"127.0.0.1:{State.port}", f"localhost:{State.port}"):
            return False
        token = self.headers.get("X-M42-Token") or query.get("t", [""])[0]
        return secrets.compare_digest(token, State.token)

    # ---- routing ------------------------------------------------------------

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path.startswith("/preview/"):  # ▶ Run: a chat page in the popup's sandboxed iframe
            return self._preview(url.path)
        if not url.path.startswith("/api/"):
            return self._static(url.path)
        if not self._authorized(query):
            return self._send(403, {"error": "forbidden"})
        State.last_seen = time.time()
        State.goodbye_at = None
        cfg, agent = State.config, State.agent
        if url.path == "/api/media":  # a chart made in this chat (cache/charts or the project's figures/)
            p = allowed_media(query.get("path", [""])[0], agent.workspace)
            if not p:
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            return self._send(200, p.read_bytes(), "image/svg+xml" if p.suffix.lower() == ".svg" else ctype)
        if url.path == "/api/page/download":  # ⬇ the page as a zip: index.html + the CSS / JS it uses
            data = webkit.preview_zip(PREVIEWS, query.get("id", [""])[0])
            if data is None:
                return self._send(404, {"error": "That preview is gone; press ▶ Run again."})
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="m42-page.zip"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if url.path == "/api/status":
            local = llamacpp.available_models()
            out = {"model": cfg["model"], "local_models": local, "warm": State.warm, "setup": firstrun.status(),
                   "active_model": agent.active_model(), "models_new": modelhub.new_count(),
                   "custom": llamacpp.AUTO_COMBOS.get(llamacpp.MY_AUTO),
                   "combos": {c["id"]: c for c in llamacpp.combos()},  # their names in the model list
                   "speech_plugin": "whisper" if speech.available() else None,  # 🎤 speech to text on this PC
                   "speech_engines": speech.engines(), "speech_engine": State.config.get("speech_engine"),
                   "update": updater.for_ui()}  # ⬆ a newer M42 UI on GitHub, and the update when one runs
            try:
                out["models"] = llm.list_models(cfg["base_url"], cfg.get("api_key") or None)
                remote_error = None
            except llm.LLMError as e:
                out["models"], remote_error = [], str(e)
            if llamacpp.is_local(cfg["model"]):
                out["model_found"] = cfg["model"] in local
                out["ok"] = State.llama.state in ("ready", "loading")
                out["error"] = State.llama.error
                out["backend_state"] = State.llama.state
            else:
                out["model_found"] = cfg["model"] in out["models"]
                out["ok"] = remote_error is None
                out["error"] = remote_error
                out["backend_state"] = "ready" if remote_error is None else "error"
            return self._send(200, out)
        if url.path == "/api/config":
            return self._send(200, {k: v for k, v in cfg.items()})
        if url.path == "/api/update":  # ⬆ this version, the latest release, and the update while it runs
            return self._send(200, updater.for_ui())
        if url.path == "/api/sessions":
            names = {p["id"]: p["name"] for p in projects.list_all()}
            chats = [dict(s, project_name=names.get(s["project_id"])) for s in sessions.list_all()]
            return self._send(200, {"current": State.session.id, "sessions": chats})
        if url.path == "/api/session":
            return self._send(200, session_payload())
        if url.path == "/api/session/live":  # 📡 a running request's events from the n-th on (a window that came back)
            q = parse_qs(url.query)
            run, sid = State.running_session, (q.get("id") or [""])[0]
            try:
                start = max(0, int((q.get("from") or ["0"])[0]))
            except ValueError:
                start = 0
            busy = State.agent.busy.locked() and run is not None and run.id == sid
            if busy:
                ui = run.ui
            else:  # (finished: the chat as saved; the one the window shows when it is the current one)
                done = State.session if State.session.id == sid else sessions.load(sid)
                ui = (done.ui or []) if done else []
            return self._send(200, {"busy": busy, "running_id": run.id if run is not None else None,
                                    "events": ui[start:start + 400], "total": len(ui)})
        if url.path == "/api/projects":
            counts = {}
            for s in sessions.list_all():
                counts[s["project_id"]] = counts.get(s["project_id"], 0) + 1
            items = [dict(p, chat_count=counts.get(p["id"], 0)) for p in projects.list_all()]
            return self._send(200, {"projects": items, "current": State.session.project_id})
        if url.path == "/api/project":
            proj = projects.load(query.get("id", [""])[0])
            if not proj:
                return self._send(404, {"error": "Project not found"})
            return self._send(200, project_payload(proj))
        if url.path == "/api/models/search":  # 🔎 the user's own Hugging Face search (Models page, Custom picker)
            try:
                return self._send(200, {"results": modelhub.search(query.get("q", [""])[0]),
                                        "hardware": modelhub.hardware(), "jobs": modelhub.jobs()})
            except (OSError, ValueError) as e:
                return self._send(200, {"results": [], "error": f"Could not reach Hugging Face: {e}"})
        if url.path == "/api/models/local":  # the ⚙ Custom picker: every model on this PC, size and speed
            items = llamacpp.local_info()
            for m in items:  # measured here when known; else the estimate (+25% with a draft: 9.4 -> 11.9 measured)
                key = m["model"][len(llamacpp.PREFIX):]
                m["measured"] = key in modelhub.MEASURED
                m["tok_s"] = modelhub.MEASURED.get(key) or round(
                    modelhub.speed(m["size_gb"], m["model"]) * (1.25 if m["draft"] else 1), 1)
            return self._send(200, {"models": items, "custom": llamacpp.AUTO_COMBOS.get(llamacpp.MY_AUTO),
                                    "combos": llamacpp.combos(),
                                    "auto": llamacpp.AUTO_TARGETS})
        if url.path == "/api/models/hub":  # the 🧩 Models page
            out = {"hardware": modelhub.hardware(), "jobs": modelhub.jobs(),
                   "my_auto": llamacpp.AUTO_COMBOS.get(llamacpp.MY_AUTO),
                   "combos": llamacpp.combos(),
                   "installed": [dict(m, key=llamacpp.PREFIX + k) for k, m in
                                 (llamacpp._read_custom().get("models") or {}).items()
                                 if (llamacpp.MODELS_DIR / m.get("file", "")).is_file()],
                   "builtin": {k: llamacpp.PREFIX + v for k, v in llamacpp.AUTO_TARGETS.items()}}
            if query.get("jobs_only", [""])[0] != "1":
                try:
                    data = modelhub.scan(refresh=query.get("refresh", [""])[0] == "1")
                    seen = modelhub.seen_set()
                    for kind in ("chat", "code"):
                        for p in data[kind]:
                            p["installed"] = (llamacpp.MODELS_DIR / p["file"]).is_file()
                            p["new"] = seen is not None and p["repo"] not in seen
                    out.update(data)
                    modelhub.mark_seen(data)  # shown now: no longer counted as new
                except (OSError, ValueError) as e:
                    out["error"] = f"Could not reach Hugging Face: {e}"
            return self._send(200, out)
        if url.path == "/api/learned":  # the 🧠 Learned panel
            try:
                return self._send(200, learn.listing())
            except (sqlite3.Error, OSError, ValueError) as e:
                return self._send(500, {"error": f"Could not read M42's memory: {e}"})
        # (?project=<id>: that project's folders, for the 📁 files panel beside a project's page; else this chat's)
        ws = agent.workspace
        if query.get("project", [""])[0] and url.path in ("/api/tree", "/api/file"):
            proj = projects.load(query["project"][0])
            if not proj:
                return self._send(404, {"error": "Project not found"})
            ws = Workspace(proj.folders)
        if url.path == "/api/tree":
            return self._send(200, {"folders": [{"alias": a, "path": str(r)} for a, r in ws.roots], "items": self._tree(ws)})
        if url.path == "/api/file":
            try:
                p = ws.resolve(query.get("path", [""])[0])
                if not p.is_file():
                    return self._send(404, {"error": "not a file"})
                ext = p.suffix.lower()
                shown = {"path": ws.rel(p), "abs": str(p), "size": p.stat().st_size}
                if ext in VIEW_IMAGES or ext == ".pdf":  # drawn by the window itself from /api/media
                    return self._send(200, dict(shown, kind="pdf" if ext == ".pdf" else "image"))
                if ext == ".svg":  # the picture, with its code one click away
                    return self._send(200, dict(shown, kind="svg",
                                                content=p.read_bytes()[:400_000].decode("utf-8", "replace")))
                data = p.read_bytes()[:400_000]
                if b"\0" in data[:8000]:
                    return self._send(200, {"path": ws.rel(p), "binary": True, "content": ""})
                return self._send(200, {"path": ws.rel(p),
                                        "content": data.decode("utf-8", "replace")})
            except ToolError as e:
                return self._send(400, {"error": str(e)})
        return self._send(404, {"error": "unknown endpoint"})

    def do_POST(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not self._authorized(query):
            return self._send(403, {"error": "forbidden"})
        State.last_seen = time.time()
        body = self._json_body()
        agent = State.agent
        if url.path == "/api/bye":
            State.goodbye_at = time.time()
            return self._send(200, {"ok": True})
        State.goodbye_at = None
        if url.path == "/api/chat":
            images = body.get("images")
            if isinstance(images, list) and images:  # screenshots: the vision model reads them first
                return self._chat_with_images(body.get("message", "").strip(), images, body.get("shots"), body.get("marked"),
                                              body.get("marks"), pick=body.get("pick"))
            sel = body.get("lines")
            if isinstance(sel, dict) and sel.get("path"):  # 📁 lines selected in a file: only those lines changed
                ask = str(body.get("message") or "").strip()
                if not State.agent.workspace.roots:
                    return self._send(400, {"error": NO_FOLDER})
                try:
                    a, b = int(sel.get("start") or 1), int(sel.get("end") or sel.get("start") or 1)
                except (TypeError, ValueError):
                    return self._send(400, {"error": "which lines?"})
                a, b = min(a, b), max(a, b)
                path = str(sel["path"])
                return self._stream(ask, f"✏ {path} · " + (f"line {a}" if a == b else f"lines {a}–{b}") + f": {ask}", "chat",
                                    lambda emit: State.agent.edit_lines(path, a, b, ask, emit), warm=False)
            return self._chat(body.get("message", "").strip(), verify=bool(body.get("verify")), pick=body.get("pick"))
        if url.path == "/api/page/preview":  # ▶ Run: save the page (kit as local files) for the popup
            html = str(body.get("html") or "")
            if not html.strip() or len(html) > 2_000_000:
                return self._send(400, {"error": "No page to run"})
            try:
                roots = State.agent.workspace.roots if State.agent else []
                pid = webkit.make_preview(html, PREVIEWS, roots[0][1] if roots else None)
            except OSError as e:
                return self._send(500, {"error": f"Could not save the preview: {e}"})
            return self._send(200, {"id": pid, "url": f"/preview/{pid}/index.html",
                                    "download": f"/api/page/download?id={pid}"})
        if url.path == "/api/speech/warm":  # 🎤 pressed: the speech model loads while the user speaks
            if speech.available():
                threading.Thread(target=speech.start, args=(State.config.get("speech_engine"),), daemon=True).start()
            return self._send(200, {"ok": speech.available()})
        if url.path == "/api/speech/diag":  # 🎤 how a mic session went (levels, phrases): in logs/app.log, to see why
            d = {k: body.get(k) for k in ("secs", "n", "max", "floor", "loud", "finals", "drafts", "errors")}
            print(f"[mic] {State.config.get('speech_engine')}: " + ", ".join(f"{k}={round(v, 4) if isinstance(v, float) else v}" for k, v in d.items()), flush=True)
            return self._send(200, {"ok": True})
        if url.path == "/api/speech":  # 🎤 a recording -> its words (Whisper, on this PC)
            if not speech.available():
                return self._send(200, {"ok": False, "error": "the speech model is not installed"})
            audio = str(body.get("audio") or "")
            try:
                wav = base64.b64decode(audio.split(",", 1)[1] if audio.startswith("data:") else audio)
                if len(wav) < 1000 or len(wav) > 60_000_000:
                    raise ValueError("no recording")
                text, secs = speech.transcribe(wav, str(body.get("language") or "auto"), engine=State.config.get("speech_engine"),
                                               prompt=str(body.get("prompt") or "")[-400:], best=bool(body.get("final")))
                print(f"[mic] {len(wav) // 32000:.0f}s of audio -> {len(text)} letters in {secs}s", flush=True)
            except (ValueError, OSError, RuntimeError) as e:
                return self._send(200, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "text": text, "seconds": secs, "engine": speech.label(State.config.get("speech_engine"))})
        if url.path == "/api/file/save":  # 💾 a file typed into in the 📁 files panel (Ctrl+S / Save)
            agent = State.agent
            if agent.busy.locked():
                return self._send(409, {"error": "M42 is changing files right now: save again when it finishes."})
            ws = agent.workspace
            if body.get("project"):
                proj = projects.load(str(body["project"]))
                if not proj:
                    return self._send(404, {"error": "Project not found"})
                ws = Workspace(proj.folders)
            content = body.get("content")
            if not isinstance(content, str) or len(content) > 5_000_000:
                return self._send(400, {"error": "no text to save"})
            try:
                p = ws.resolve(str(body.get("path") or ""))
                if not p.is_file():
                    return self._send(404, {"error": "that file is not there any more"})
                res = ws.write_file(ws.rel(p), content)  # (the old one kept as a backup; no personal details, as always)
            except (ToolError, OSError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"ok": True, "path": res.get("path"), "summary": res.get("summary")})
        if url.path == "/api/undo":  # ↶ a change put back (its files as they were before it)
            agent = State.agent
            if agent.busy.locked():
                return self._send(409, {"error": "M42 is working on a request: wait for it to finish, then undo."})
            if not agent.workspace.roots:
                return self._send(400, {"error": NO_FOLDER})
            try:
                done = agent.undo(str(body.get("id") or ""))
            except (ToolError, OSError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            root = agent.workspace.roots[0][1]
            site = sitedit.load(root) or {}
            pages = [p["file"] for p in site.get("pages") or []] or [n for n in done if n.endswith(".html")]
            out = {"restored": done}
            if pages:
                pid = webkit.make_preview_folder(root, PREVIEWS, pages + (["css/theme.css"] if (Path(root) / "css" / "theme.css").is_file() else []))
                first = next((n for n in done if n.endswith(".html")), pages[0])
                out.update(url=f"/preview/{pid}/{first}", download=f"/api/page/download?id={pid}", id=pid)
            State.session.record({"type": "note", "message": "↶ Undone: " + ", ".join(n for n in done if not n.startswith(".m42")) + " put back as they were"})
            return self._send(200, out)
        if url.path == "/api/page/shot":  # 📷 the preview as the user sees it, a picture for the message box
            return self._preview_shot(body)
        if url.path == "/api/models/custom":  # ⚙ a chat + code pair the user picked, with its name
            try:
                if body.get("name"):
                    cid = llamacpp.save_combo(str(body["name"]), str(body.get("chat", "")), str(body.get("code", "")),
                                              str(body.get("id", "")))
                else:
                    cid = llamacpp.set_custom_auto(str(body.get("chat", "")), str(body.get("code", "")))
            except (OSError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"custom": llamacpp.AUTO_COMBOS.get(llamacpp.MY_AUTO), "model": cid,
                                    "combos": llamacpp.combos()})
        if url.path == "/api/models/combo/delete":
            try:
                cid = str(body.get("id", ""))
                llamacpp.delete_combo(cid)
            except (OSError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            if State.config.get("model") == cid:  # the combo in use is gone: back to the first Auto
                State.config["model"] = llamacpp.AUTO
                save_config(State.config)
            return self._send(200, {"combos": llamacpp.combos(), "model": State.config.get("model")})
        if url.path == "/api/models/pick_local":  # 📁 your own model: choose the .gguf, see what it is
            path = str(body.get("path") or "") or pick_gguf(State.config.get("last_gguf_dir") or str(Path.home()))
            if not path:
                return self._send(200, {"cancelled": True})
            State.config["last_gguf_dir"] = str(Path(path).parent)
            save_config(State.config)
            try:
                return self._send(200, {"info": modelhub.inspect_gguf(path), "folder": str(llamacpp.MODELS_DIR)})
            except (OSError, ValueError, struct.error) as e:
                return self._send(400, {"error": str(e)})
        if url.path == "/api/models/import":  # ... then moved / copied into models/ and set for chat or code
            try:
                job = modelhub.import_local(str(body.get("path", "")), str(body.get("kind", "")),
                                            str(body.get("mode", "")))
                return self._send(200, {k: v for k, v in job.items() if k != "stop"})
            except (OSError, ValueError, struct.error) as e:
                return self._send(400, {"error": str(e)})
        if url.path in ("/api/models/download", "/api/models/cancel", "/api/models/use"):
            try:
                if url.path.endswith("download"):  # the user pressed Download and confirmed name, size and source
                    job = modelhub.start(str(body.get("repo", "")), str(body.get("file", "")), body.get("bytes"),
                                         str(body.get("sha256", "")), str(body.get("kind", "")))
                    return self._send(200, {k: v for k, v in job.items() if k != "stop"})
                if url.path.endswith("cancel"):
                    modelhub.cancel(str(body.get("file", "")))
                    return self._send(200, {"ok": True})
                llamacpp.use_custom(str(body.get("model", "")), str(body.get("kind", "")))
                return self._send(200, {"my_auto": llamacpp.AUTO_COMBOS.get(llamacpp.MY_AUTO)})
            except (OSError, ValueError) as e:
                return self._send(400, {"error": str(e)})
        if url.path == "/api/learned/forget":
            try:
                learn.forget(str(body.get("kind", "")), int(body.get("id", 0)))
            except (sqlite3.Error, OSError, ValueError, TypeError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"ok": True})
        if url.path == "/api/approve":
            return self._send(200, {"ok": agent.answer_approval(body.get("id"), body.get("allow"))})
        if url.path == "/api/learn/edit":  # 🧠 "was this edit right?": a yes is learned, a no is not
            try:
                kept = agent.learn_from_edit(str(body.get("id") or ""), bool(body.get("right")))
            except (sqlite3.Error, OSError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"ok": True, "learned": kept})
        if url.path == "/api/learn/confirm":  # 🧠 the user's yes / no to a rule M42 learned (kept pending till then)
            try:
                fn = learn.confirm_design if body.get("kind") == "design" else learn.confirm_lesson
                ok = fn(int(body.get("id")), bool(body.get("keep")))
            except (sqlite3.Error, OSError, ValueError, TypeError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, {"ok": ok})
        if url.path == "/api/setup/start":  # ⬇ the user said yes to the first-run download list
            if firstrun.start(consent=True):
                def after_setup():
                    while firstrun.status()["state"] == "running":
                        time.sleep(2)
                    if firstrun.status()["state"] == "done":
                        llamacpp.refresh_auto()  # (the model just downloaded: the 2B on an 8 GB PC)
                        prepare_backend()
                threading.Thread(target=after_setup, daemon=True).start()
            return self._send(200, firstrun.status())
        if url.path == "/api/stop":
            agent.stop()
            return self._send(200, {"ok": True})
        if url.path == "/api/sessions/truncate":  # ✎ a message edited and sent again: it and all after it go
            end = time.time() + 15  # (the request it stopped is still finishing)
            while agent.busy.locked() and time.time() < end:
                time.sleep(.1)
            if agent.busy.locked():
                return self._send(409, {"error": "M42 is still stopping the last request; try again in a moment"})
            sess, nth = State.session, body.get("nth")
            users = [i for i, ev in enumerate(sess.ui) if ev.get("type") == "user"]
            if not isinstance(nth, int) or not 0 <= nth < len(users):
                return self._send(400, {"error": "that message is not in this chat"})
            del sess.ui[users[nth]:]
            # the model's conversation: cut at that message, found by its words (page builds don't add every request
            # to it, so a count would cut the wrong place); not found: left as it is
            words = " ".join(str(body.get("words") or "").split())[:80]
            if words:
                for i in range(len(sess.messages) - 1, -1, -1):
                    m = sess.messages[i]
                    if m.get("role") == "user" and words in " ".join(str(m.get("content") or "").split()):
                        del sess.messages[i:]  # (in place: the agent holds this same list)
                        break
            sess.save()
            return self._send(200, {"ok": True, "events": len(sess.ui)})
        if url.path == "/api/sessions/open" and agent.busy.locked():
            # 👀 a request runs: another chat is shown as it is (nothing switched); the running chat, back to it, live
            run = State.running_session
            if run is not None and body.get("id") == run.id:
                return self._send(200, session_payload())
            s = sessions.load(body.get("id", ""))
            if not s:
                return self._send(404, {"error": "Chat not found"})
            return self._send(200, view_payload(s))
        if url.path.startswith(("/api/sessions/", "/api/projects/")) and agent.busy.locked():
            return self._send(409, {"error": "M42 is working in another chat; wait for it, or stop it first"})
        if url.path == "/api/sessions/new":  # project_id: chat inside that project; none: general chat
            pid = body.get("project_id") or None
            if pid and not projects.load(pid):
                return self._send(404, {"error": "Project not found"})
            switch_session(sessions.Session(pid))
            return self._send(200, session_payload())
        if url.path == "/api/sessions/open":
            s = sessions.load(body.get("id", ""))
            if not s:
                return self._send(404, {"error": "Chat not found"})
            switch_session(s)
            return self._send(200, session_payload())
        if url.path == "/api/sessions/delete":
            sid = body.get("id", "")
            sessions.delete(sid)
            if sid == State.session.id:
                switch_session(sessions.Session(State.session.project_id))
            return self._send(200, {"ok": True, "current": State.session.id})
        if url.path == "/api/sessions/rename":
            if body.get("id") == State.session.id:
                State.session.title = (body.get("title") or "").strip()[:80] or State.session.title
                State.session.save()
                return self._send(200, {"ok": True})
            return self._send(200, {"ok": sessions.rename(body.get("id", ""), body.get("title", ""))})
        if url.path == "/api/config":
            before = {k: State.config.get(k) for k in PROMPT_KEYS}
            for k, v in body.items():
                if k in EDITABLE_KEYS and isinstance(v, (str, int, float, bool)):
                    want = type(DEFAULT_CONFIG[k])
                    State.config[k] = v if want is bool else want(v)
            save_config(State.config)
            if any(State.config.get(k) != before[k] for k in PROMPT_KEYS):
                prepare_backend()  # new model or new system prompt: (re)load and re-warm
            return self._send(200, State.config)
        if url.path.startswith("/api/update/"):  # ⬆ the M42 UI update (updater.py)
            return self._update_action(url.path.rsplit("/", 1)[1])
        if url.path.startswith("/api/projects/"):
            return self._project_action(url.path.rsplit("/", 1)[1], body)
        return self._send(404, {"error": "unknown endpoint"})

    def _update_action(self, action):
        if action == "check":
            updater.check_in_background(force=True)
            return self._send(200, {"ok": True})
        if action == "apply":
            if State.agent.busy.locked():
                return self._send(409, {"error": "M42 UI is working on a request: update when it has finished."})
            if updater.git_checkout():
                return self._send(409, {"error": "This folder is a git checkout: update it with git pull."})
            updater.start_apply(updater.LATEST if updater.LATEST.get("available") else None)
            return self._send(200, {"ok": True})
        if action == "restart":
            if updater.status().get("state") not in ("done", "rolled_back"):
                return self._send(409, {"error": "There is no finished update to restart into."})
            updater.restart(sys.argv)
            self._send(200, {"ok": True})
            State.agent.stop()
            threading.Timer(0.8, State.server.shutdown).start()  # (the answer reaches the window first)
            return None
        if action == "rollback":
            if State.agent.busy.locked():
                return self._send(409, {"error": "M42 UI is working on a request: wait until it has finished."})
            try:
                out = updater.rollback()
            except updater.UpdateError as e:
                return self._send(409, {"error": str(e)})
            updater.STATE.clear()
            updater.STATE.update(out)
            return self._send(200, out)
        return self._send(404, {"error": "unknown endpoint"})

    def _project_action(self, action, body):
        if action == "new" and body.get("pick"):
            # Like Claude desktop: choose a folder -> it becomes a project -> a new chat opens in it.
            path = pick_folder(State.config.get("last_pick_dir") or str(Path.home()))
            if not path:
                return self._send(200, {"cancelled": True})
            folder = Path(path).resolve()
            proj = projects.find_by_folder(folder)  # reuse the project that already has this folder
            created = proj is None
            if created:
                proj = projects.Project(folder.name or str(folder), [folder])
                proj.save()
            State.config["last_pick_dir"] = str(folder.parent)
            save_config(State.config)
            switch_session(sessions.Session(proj.id))
            return self._send(200, dict(session_payload(), project_created=created))
        if action == "new":
            name = (body.get("name") or "").strip()[:60] or "New project"
            proj = projects.Project(name)
            proj.save()
            return self._send(200, project_payload(proj))
        proj = projects.load(body.get("id", ""))
        if not proj:
            return self._send(404, {"error": "Project not found"})
        if action == "update":
            if "name" in body:
                proj.name = (body.get("name") or "").strip()[:60] or proj.name
            if "instructions" in body:
                proj.instructions = str(body.get("instructions") or "")[:4000]
        elif action == "add_folder":
            try:
                if body.get("create"):  # brand-new empty folder under <M42>/projects/
                    path = projects.create_folder(body["create"])
                elif body.get("pick"):
                    start = proj.folders[0] if proj.folders else str(projects.NEW_FOLDERS_ROOT.parent)
                    path = pick_folder(start)
                    if not path:
                        return self._send(200, project_payload(proj))  # dialog cancelled
                else:
                    path = Path(body.get("path") or "").expanduser()
                proj.add_folder(path)
            except (ValueError, OSError) as e:
                return self._send(400, {"error": str(e)})
        elif action == "remove_folder":  # only unlinks it from the project; the folder is untouched
            proj.remove_folder(body.get("path", ""))
        elif action == "delete":  # its chats are kept and become general chats
            for s in sessions.list_all(project_id=proj.id):
                chat = sessions.load(s["id"])
                if chat:
                    chat.project_id = None
                    chat.save(touch=False)
            projects.delete(proj.id)
            if State.session.project_id == proj.id:
                State.session.project_id = None
                switch_session(State.session)
            return self._send(200, {"ok": True})
        else:
            return self._send(404, {"error": "unknown project action"})
        proj.save()
        reload_project_if_current(proj)
        return self._send(200, project_payload(proj))

    # ---- endpoints ----------------------------------------------------------









    def _chat_with_images(self, message, images, shots=None, marked=None, marks=None, pick=None):
        """A message with pictures: the pictures are the design reference of the page / site (its layout, look and
        colours; the content is the user's own), or the page to rebuild ("clone this")."""
        if not State.agent.workspace.roots:
            return self._send(400, {"error": NO_FOLDER})
        vision = llamacpp.vision_model(auto_target("chat"))
        if not vision:
            return self._send(400, {"error": "Pictures need the vision file models/Qwen3.5-4B-mmproj-F16.gguf."})
        flags = [(bool((shots or [])[k]) if k < len(shots or []) else False,
                  bool((marked or [])[k]) if k < len(marked or []) else False) for k in range(len(images))]
        keep = [k for k, u in enumerate(images) if isinstance(u, str) and IMAGE_URL_RX.match(u) and len(u) < 12_000_000][:3]
        images, flags = [images[k] for k in keep], [flags[k] for k in keep]
        if not images:
            return self._send(400, {"error": "Only PNG, JPEG or WebP pictures (up to 3)."})
        for u, (own, _m) in zip(images, flags):  # a 📷 of the page itself (marked or not): a correction of that page
            if own:
                with contextlib.suppress(OSError, ValueError):
                    State.own_shots.add(designref.fingerprint(u))
        shown = (message or "(picture)") + f"  🖼×{len(images)}" + ("  ✏ marked" if any(m for _o, m in flags) else "")
        if any(m for _o, m in flags):  # the user marked the part to look at: the picture sent is that part
            message = (message + " " if message else "") + ("(the picture is only the part the user marked in red on "
                                                             "it: look at and change only that part)")
        save_shots(images)
        auto = llamacpp.is_auto(State.config["model"])

        def work(emit):
            agent = State.agent
            if not switch_model(vision, "chat", emit, vision=True):
                return
            if webclone.wants_clone(message):  # "intha page apdiye pannu": the page in the picture, rebuilt
                spec = agent.describe_images(message, images, emit, vision, system=webclone.SPEC_PROMPT, max_tokens=900,
                                             title="The page in the picture")
                return build_clone(message, spec, webclone.palette(images[0]), emit, auto, reference=images[0])
            agent._edit_marked = any(m for _o, m in flags)  # (a marked part: its section found from the picture)
            agent._edit_mark = page_mark(marks)  # (a mark on a 📷: the very place on the page)
            agent._edit_pick = agent.pick_node(pick) if pick else None  # (🎯 the part clicked on the page: the change is there)
            try:
                return page_with_reference(message, images, emit, vision)
            finally:
                agent._edit_marked, agent._edit_mark, agent._edit_pick = False, None, None

        return self._stream(message or "picture", shown, None, work)

    def _chat(self, message, verify=False, pick=None):
        """Every message is about the web page / site in the open folder: a change to it (sitedit), the answer to
        its one question, a page to clone from a URL, or a new page / site (spec -> reference -> plan -> built)."""
        agent = State.agent
        if firstrun.state["state"] == "running":  # (a new PC: the model is still on its way)
            st = firstrun.status()
            pct = int(st["done"] * 100 / st["total"]) if st.get("total") else 0
            return self._send(400, {"error": f"M42 UI is getting ready (first run): {st.get('step') or 'downloading'} {pct}%. "
                                             "Your request can be sent when it finishes."})
        if firstrun.state["state"] in ("needs_consent", "error") and firstrun.core_missing():
            return self._send(400, {"error": "The AI model is not on this PC yet: press Download in the box at the top "
                                             "(it asks before downloading anything)."})
        if not agent.workspace.roots:
            return self._send(400, {"error": NO_FOLDER})
        cut = State.session.running
        if cut and CONTINUE_RX.match(message or "") and len(message.split()) <= 4 and not agent.busy.locked():
            # ▶ "continue" on a request cut off (the app closed, a power cut): that request again, its finished steps
            # kept (agent.resumed), from where it stopped
            message = cut.get("text") or message
            agent._resume = True
            self._resuming = True
            if not sitedit.load(agent.workspace.roots[0][1]) or agent.resume_info(agent.workspace.roots[0][1], message):
                return self._stream(message, "🎨 " + message, "chat", lambda emit: web_request(message, emit))
        ppage = getattr(agent, "pending_page", None)
        if ppage and len(message.split()) <= 20 and not webkit.chat_page_request(message):
            # the answer to the page spec's question ("192.168.1.50/data la JSON", "demo"): the page, with it
            agent.pending_page = None
            agent.page_spec = webkit.with_answer(ppage["spec"], message)

            def answered(emit):
                agent.page_spec = design_refs(ppage["message"], agent.page_spec, emit)
                built = agent.page_from_plan(ppage["message"], agent.page_spec, emit) if agent.page_spec else False
                if built == "rules":
                    agent.finish_plan_page(ppage["message"], emit)
                elif not built:
                    agent.run(ppage["message"], emit)
            return self._stream(message, "📝 " + message, "chat", answered)
        last_clone = getattr(agent, "last_clone", None)
        if last_clone and webclone.AGAIN_RX.search(message) and len(message.split()) <= 20:
            return self._stream(message, "👀 " + message, "chat", lambda emit: clone_again(message, emit), warm=False)
        if webclone.wants_clone(message) and web.urls_in(message) and llamacpp.vision_model() and agent._web_enabled():
            return self._stream(message, "🌐 " + message, None, lambda emit: clone_site(message, emit))
        if not sitedit.load(agent.workspace.roots[0][1]):  # an empty folder: a page to build
            return self._stream(message, "🎨 " + message, "chat", lambda emit: web_request(message, emit))

        picked = agent.pick_node(pick) if pick else None
        if picked and message:  # 🎯 the user clicked a part of the preview and says what to change in it: an edit there

            def edit_picked(emit):
                agent.stop_event.clear()
                agent._edit_pick = picked
                try:
                    return agent.edit_site(message, emit)
                finally:
                    agent._edit_pick = None
            return self._stream(message, f'🎯 {message}', "chat", edit_picked, warm=False)

        def routed(emit):
            """What the message is for the site here, as the model decides it (an edit, the same page again, another page,
            a question), then that path (the user, 2026-11-12: "the 4B thinks and decides; no word rules")."""
            agent.stop_event.clear()
            decided = agent.existing_build(message, [])
            if decided[0] == "edit":
                emit({"type": "note", "message": f"♻ {decided[1]}"})
                return agent.edit_site(message, emit)
            if decided[0] == "unclear":  # (mic noise read as words: nothing is built or changed)
                emit({"type": "assistant_start"})
                emit({"type": "assistant_text", "text": f"🤔 I could not make out a request in that ({decided[1]}). Nothing was changed: say it again?"})
                return
            if decided[0] == "question":  # answered, nothing changed (the general agent edited files by hand)
                return agent.answer_about_site(message, emit)
            return web_request(message, emit, decided)
        return self._stream(message, message, "chat", routed, warm=False)

    def _stream(self, message, shown, kind, work, warm=True):
        """Run work(emit) for chat, plan and build: NDJSON stream to the UI, one request at a time,
        auto-mode model switch (kind 'chat' or 'code'), and the chat saved afterwards."""
        agent = State.agent
        if not message:
            return self._send(400, {"error": "empty message"})
        if not agent.busy.acquire(blocking=False):
            return self._send(409, {"error": "Agent is already working on a request"})
        agent.stop_event.clear()  # a Stop from an earlier request (llm.STOP would end this one's model calls at once)
        session = State.session
        State.running_session = session  # (the chat this request belongs to, whichever one the window shows)
        session.name_from(message)
        started_at = time.time()
        if getattr(self, "_resuming", False):  # ▶ the cut-off request continued: said so in the chat
            shown = "▶ Continue: " + (shown or message)[:200]
        session.record({"type": "user", "text": shown, "time": started_at})
        session.running = {"text": message, "shown": shown, "started": started_at, "kind": kind}
        try:  # (kept at once: the app closed in the first seconds still shows it, cut off, with ▶ Continue)
            session.save()
        except OSError:
            pass
        totals = {"tokens": 0, "gen_s": 0.0, "calls": 0}  # every model call of this request, for the summary
        writer_thread = outbox = None
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            last_save = [time.time()]

            def emit(event):
                if event.get("type") == "stats":
                    totals["calls"] += 1
                    totals["tokens"] += event.get("tokens") or 0
                    if event.get("gen_s"):
                        totals["gen_s"] += event["gen_s"]
                    elif event.get("tok_per_s") and event.get("tokens"):
                        totals["gen_s"] += event["tokens"] / event["tok_per_s"]
                if event.get("type") != "reading":  # live progress only (every 1.5 s), not worth replaying
                    session.record(event)
                # save the chat every few seconds while it runs: after a power cut the whole request was lost
                # (the save is atomic: a temp file, then a rename)
                if event.get("type") not in ("delta", "progress") and time.time() - last_save[0] > 5:
                    last_save[0] = time.time()
                    try:
                        session.save()
                    except OSError:
                        pass
                # Never write to the window from here: with the screen off Edge stopped reading the stream, the
                # socket filled up and the whole run waited until someone moved the mouse. A writer thread
                # sends the events; the agent keeps working whatever the window does.
                outbox.put((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))

            def writer():
                while True:
                    line = outbox.get()
                    if line is None:
                        return
                    if ui_gone.is_set():
                        continue
                    try:
                        self.wfile.write(line)
                        self.wfile.flush()
                    except OSError:
                        # the window went to another chat, or was closed: the work goes on (the user, 2026-11-15: "another
                        # chat and back, it was cut"); its events are in the chat, and a window that comes back to it
                        # follows them again (/api/session/live). Only Stop stops it.
                        ui_gone.set()

            outbox, ui_gone = queue.Queue(), threading.Event()
            writer_thread = threading.Thread(target=writer, daemon=True)
            writer_thread.start()
            keep_awake(True)

            if kind and llamacpp.is_auto(State.config["model"]):  # kind None: the work switches models itself
                # Auto mode: code questions go to the coder model, everything else to the chat model.
                target = auto_target(kind)
                # (also when the server still has the image file from a picture: text goes back to the fast load)
                if agent.model_override != target or State.llama.state != "ready" or (
                        State.llama.vision and State.llama.model not in llamacpp.VISION_ALWAYS):  # (the 4B keeps it)
                    started = time.time()
                    emit({"type": "model_switch", "state": "start", "to": target, "kind": kind})
                    try:
                        activate(target, warm=warm)
                    except llm.LLMError as e:
                        emit({"type": "error", "message": f"Could not load {target}: {e}"})
                        return
                    emit({"type": "model_switch", "state": "done", "to": target, "kind": kind,
                          "secs": round(time.time() - started, 1)})
                State.last_kind = kind
            try:
                work(emit)
            except Exception as e:  # keep the server alive; report to UI
                traceback.print_exc()
                emit({"type": "error", "message": f"Internal error: {type(e).__name__}: {e}"})
            # when it was asked, when it finished, and how much the model wrote over the whole request
            emit({"type": "request_done", "started": started_at, "finished": time.time(),
                  "secs": round(time.time() - started_at, 1), "tokens": totals["tokens"], "calls": totals["calls"],
                  "tok_per_s": round(totals["tokens"] / totals["gen_s"], 1) if totals["gen_s"] > 0.5 else None})
        finally:
            session.running = None  # finished (or stopped on purpose): nothing to continue
            keep_awake(False)
            if writer_thread:  # deliver what's left (waits while a frozen window catches up), then end
                outbox.put(None)
                writer_thread.join()
            try:
                session.save()
            except OSError as e:
                print(f"Could not save chat: {e}")
            State.running_session = None
            agent._resume = False  # (only the continued request uses the kept steps)
            agent.busy.release()
        self.close_connection = True

    def _tree(self, ws=None):
        """Files of the current project (or of `ws`). Several folders: each one is a top-level node."""
        ws = ws or State.agent.workspace
        items = []
        for alias, root in ws.roots:
            indent = 0
            if ws.multi:
                items.append({"path": alias, "name": alias, "dir": True, "level": 0, "root": True})
                indent = 1
            for p, level in ws.walk(root, 6):
                items.append({"path": ws.rel(p), "name": p.name, "dir": p.is_dir(), "level": level + indent})
                if len(items) >= 1500:
                    return items
        return items

    def _preview_shot(self, body):
        """📷 in the preview's bar (the user, 2026-11-12: "a screenshot icon: we take the shot and tell the correction"):
        the preview page drawn by headless Chrome at the pane's width, the part on screen (its scroll), as a JPEG data
        URL the message box attaches. Only a page of M42's own previews."""
        import io as _io
        m = re.fullmatch(r"/preview/([\w-]+)/(.+)", urlparse(str(body.get("url") or "")).path)
        page = webkit.preview_file(PREVIEWS, m.group(1), unquote(m.group(2))) if m else None
        if not page or page.suffix.lower() not in (".html", ".htm"):
            return self._send(404, {"error": "No preview page to take a picture of"})
        w = max(320, min(1920, int(float(body.get("width") or 1280))))
        h = max(300, min(1400, int(float(body.get("height") or 800))))
        top = max(0, min(6000, int(float(body.get("scroll") or 0))))
        still = page.with_name(f".m42-shot-{secrets.token_hex(3)}.html")  # (motion stopped: everything shown, as it is)
        png = PREVIEWS / f".shot-{secrets.token_hex(4)}.png"
        try:
            still.write_text(page.read_text(encoding="utf-8").replace("<head>", "<head><script>window.M42_STILL=1</script>", 1),
                             encoding="utf-8")
            if not webclone.snapshot(still, png, width=w, height=top + h):
                return self._send(500, {"error": "The browser could not draw the page"})
            from PIL import Image
            im = Image.open(png).convert("RGB")
            im = im.crop((0, max(0, im.height - h), im.width, im.height))  # the part that was on screen
            if im.width > 1280:
                im = im.resize((1280, round(im.height * 1280 / im.width)))
            out = _io.BytesIO()
            im.save(out, "JPEG", quality=85)
        except (OSError, ValueError) as e:
            return self._send(500, {"error": f"The picture could not be made: {e}"})
        finally:
            for f in (still, png):
                with contextlib.suppress(OSError):
                    f.unlink()
        image = "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()
        with contextlib.suppress(OSError, ValueError):
            State.own_shots.add(designref.fingerprint(image))
        return self._send(200, {"image": image})

    def _preview(self, path):
        """/preview/<id>/<file>: only that preview's own folder, no token (the page's scripts could read it from
        their URL; this route gives them nothing but their own files), only from this PC's own address."""
        if self.headers.get("Host", "") not in (f"127.0.0.1:{State.port}", f"localhost:{State.port}"):
            return self._send(403, b"forbidden", "text/plain")
        parts = path.split("/", 3)  # "", "preview", id, rest
        p = webkit.preview_file(PREVIEWS, parts[2] if len(parts) > 2 else "", unquote(parts[3]) if len(parts) > 3 else "")
        if not p:
            return self._send(404, b"not found", "text/plain")
        ctype = ({".woff2": "font/woff2", ".woff": "font/woff"}.get(p.suffix.lower())
                 or mimetypes.guess_type(p.name)[0] or "application/octet-stream")
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        # the sandboxed frame's origin is "null": fonts are fetched with CORS, and without this the icon font
        # never loaded (every icon an empty box, 2026-10-26). Only this preview's own files are served here.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        p = (UI_DIR / rel).resolve()
        if UI_DIR not in p.parents or not p.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        return self._send(200, p.read_bytes(), ctype)


def find_edge():
    """A Chromium browser for the app window: Edge on Windows (always there), else Chrome / Chromium / Brave (Linux,
    macOS); None: the default browser opens it as a tab."""
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.environ.get("LOCALAPPDATA")):
        if base:
            p = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if p.exists():
                return str(p)
    return shutil.which("msedge") or browser.find_browser()


def app_data_dir():
    """M42's own folder for the window's profile: %LOCALAPPDATA%\\M42, ~/Library/Application Support/M42, ~/.local/share/M42."""
    if os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "M42"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "M42"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "M42"


def open_window(url):
    """Open the UI as a chromeless app window with its own profile, so we can tell when it closes."""
    browser = find_edge()
    if not browser:
        import webbrowser
        webbrowser.open(url)
        return None
    profile = app_data_dir() / "window-profile"
    profile.mkdir(parents=True, exist_ok=True)
    # The window keeps reading the stream when the screen turns off or it's hidden behind other windows
    # (Edge throttles such pages; the run then seemed to stop until the mouse moved).
    return subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={profile}",
                             "--window-size=1320,860", "--no-first-run",
                             "--no-default-browser-check", "--disable-features=Translate,IntensiveWakeUpThrottling",
                             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                             "--disable-backgrounding-occluded-windows"])


def watch_for_exit(server, window):
    """Shut down when the window process exits, or shortly after the page says goodbye.
    With an old M42 window still open, Edge hands the new window to that running Edge and the launcher process
    exits at once: M42 read that as "window closed", shut down 2 s after starting, and the page said "Failed to
    fetch". A launcher that ends within 20 s is such a hand-off: M42 then stays up while its page keeps calling."""
    started, handed_off = time.time(), False
    while True:
        time.sleep(1)
        busy = State.agent.busy.locked()
        if window is not None and not handed_off and window.poll() is not None:
            if time.time() - started < 20:
                handed_off = True
                print("The window was handed to an Edge that was already running: M42 stays up while its page is open.")
            elif busy:  # the window closed mid-request: the request finishes (opening M42 again shows it live), then
                # M42 closes when no window has called for 90 s (the user, 2026-11-15: "closed by mistake, it started over")
                handed_off = True
                print("The window closed while M42 was working: the request goes on; open M42 again to follow it.")
            else:
                break
        if State.goodbye_at and time.time() - State.goodbye_at > 4 and not busy:
            break
        if handed_off and time.time() - State.last_seen > 90 and not busy:  # the page stopped calling: closed
            break
    print("Window closed - shutting down.")
    State.agent.stop()
    server.shutdown()


def main():
    ap = argparse.ArgumentParser(description="M42 UI desktop app")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-window", action="store_true", help="Only start the server; print the URL")
    ap.add_argument("--profile", help="Folder for a separate config.json + saved chats (testing)")
    ap.add_argument("--llama-port", type=int, help="Port for the managed llama-server (default 8080)")
    args = ap.parse_args()

    if args.profile:
        global CONFIG_PATH
        prof = Path(args.profile)
        prof.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH = prof / "config.json"
        sessions.DIR = prof / "sessions"
        projects.DIR = prof / "projects"
        projects.NEW_FOLDERS_ROOT = prof / "new-folders"
        learn.DIR = prof / "memory"  # what a test instance learns stays with the test
        learn.DB, learn.TOOLS_DIR = learn.DIR / "learned.db", learn.DIR / "tools"
    if args.llama_port:
        llamacpp.set_port(args.llama_port)

    if os.environ.get("M42_TOKEN"):
        State.token = os.environ["M42_TOKEN"]
    State.port = args.port
    running_file = CONFIG_PATH.with_name(f".running-{args.port}.json")

    try:
        server = Server(("127.0.0.1", args.port), Handler)
    except OSError:
        # Port taken: M42 is probably already running. Open another window onto it instead.
        try:
            info = json.loads(running_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = None
        if info and not args.no_window:
            open_window(info["url"])
        else:
            show_error(f"Port {args.port} is already in use, so M42 can't start.\n\n"
                       "Is M42 already open? Close it first, or start M42 with --port 8770.")
        return
    server.daemon_threads = True
    State.server = server
    url = f"http://127.0.0.1:{args.port}/?t={State.token}"
    running_file.write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")

    State.config = load_config()
    State.agent = Agent(State.config)
    State.llama = llamacpp.LlamaServer()
    sessions.migrate_legacy(projects)  # chats saved before projects existed -> one project per folder
    switch_session(sessions.Session())  # start on a new general chat, like claude.ai
    print(f"M42 running at {url}")
    print(f"Model: {State.config['model']} @ {llamacpp.base_url_for(State.config)}")
    print(f"Projects: {len(projects.list_all())}, chats: {len(sessions.list_all())}")
    # a new PC (M42 UI from GitHub): the model and llama-server are downloaded first, by themselves (firstrun.py); the
    # window shows the progress, and the model loads when they are there
    # (2026-11-15: nothing downloads without the user's yes: the window lists what is missing, with its size, and a
    # Download button; the installer, setup.py, asks the same in its own window)
    firstrun.start()
    if firstrun.status()["state"] == "needs_consent":
        print("First run: missing (waits for the user's yes in the window):", ", ".join(firstrun.status().get("missing") or []))
    if not firstrun.core_missing():
        prepare_backend()  # load the model and warm the prompt cache while the window opens
    modelhub.check_in_background(web.online)  # new models on Hugging Face: "🧩 Models · N new" in the sidebar
    if State.config.get("update_check", True) and not args.profile:  # ⬆ a newer M42 UI release on GitHub
        updater.check_in_background()  # (only its public version info is read; at most every 6 hours)
    if speech.available():  # 🎤 the speech model loaded now, so the first words come while the user speaks (the user,
        # 2026-11-13: the first press typed nothing live: IndicConformer loaded in 8.5 s, Whisper in ~20 s, on first use)
        threading.Thread(target=speech.start, args=(State.config.get("speech_engine"),), daemon=True).start()

    if not args.no_window:
        window = open_window(url)
        threading.Thread(target=watch_for_exit, args=(server, window), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        State.llama.stop()
        running_file.unlink(missing_ok=True)


class Server(ThreadingHTTPServer):
    # http.server sets SO_REUSEADDR, which on Windows lets a second process bind the same busy port
    # (two M42s would silently split requests). Claim the port exclusively instead, so a second
    # launch fails to bind and can open a window onto the running M42.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def show_error(text):
    """Visible error even without a console (pythonw): a Windows message box, plus the log."""
    print(text)
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "M42 UI", 0x10)
    elif sys.platform == "darwin" and shutil.which("osascript"):
        subprocess.run(["osascript", "-e", f"display alert \"M42 UI\" message {json.dumps(text)} as critical"], check=False)
    elif shutil.which("zenity"):
        subprocess.run(["zenity", "--error", "--title=M42 UI", f"--text={text}"], check=False)


def use_log_file_without_console():
    """pythonw has no console (sys.stdout is None): write prints and tracebacks to logs/app.log."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_dir = APP_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log = open(log_dir / "app.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log
    print(f"\n--- M42 started {time.strftime('%Y-%m-%d %H:%M:%S')} ---")


if __name__ == "__main__":
    use_log_file_without_console()
    try:
        main()
    except Exception as e:  # startup crash: tell the user instead of vanishing silently
        traceback.print_exc()
        show_error(f"M42 could not start:\n\n{type(e).__name__}: {e}\n\nDetails: m42\\logs\\app.log")
