"""The Technisite clone from the log: no script -> no 'buttons changed nothing'; alert() buttons -> no 45 s hang;
a calculator with a script and dead digits -> still flagged."""
from pathlib import Path
import os, sys, tempfile, time
os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent
NAV = '<div class="navbar"><div>Technisite Solutions</div><nav><a href="#">Home</a></nav><button>Get Consultation</button></div>'
HERO = '<div class="hero"><h1>We Build the Future</h1><button>Get a Free Consultation →</button></div>'
plain = f"```html\n<!DOCTYPE html><html><head><style>body{{margin:0}}</style></head><body>{NAV}{HERO}</body></html>\n```"
alerts = plain.replace("<button>Get Consultation</button>", "<button onclick=\"alert('Consultation requested!')\">Get Consultation</button>") \
              .replace("<button>Get a Free", "<button onclick=\"alert('Free!')\">Get a Free")
calc = ("```html\n<!DOCTYPE html><html><body><input id=d><button>1</button><button>2</button><button>3</button>"
        "<script>document.title='calc';</script></body></html>\n```")
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False, "approve_commands": False})
for name, page in [("landing page, no script", plain), ("buttons with alert()", alerts), ("calculator, dead digits", calc)]:
    t = time.time()
    problem, note = a._chat_page_check(page, lambda e: None, "clone this site")
    print(f"{name:26} {time.time() - t:4.1f}s | problem: {(problem or '-')[:110]!r} | note: {(note or '-')[:50]!r}")
