"""A page asked in the chat gets a spec first (the user's idea, 2026-10-25): items in correct English ("pritection"
-> prediction), the data source, the rules for computed items, the layout. Only what can't be guessed (where a live
page's readings come from) is asked; the answer continues the request; the page is checked against the spec."""
from pathlib import Path
import os
import sys
import tempfile

os.environ["M42_MEMORY_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent  # noqa: E402
import llm  # noqa: E402
import webkit  # noqa: E402

fails = 0


def check(name, ok, extra=""):
    global fails
    print(("ok  " if ok else "FAIL"), name, str(extra)[:300])
    fails += not ok


USER = ("weather monitor system IoT project ku Web dashboard Html la Super ya Tempture Humitity ,rain percentage, "
        "weather pritection ellam vara mathiri panni kutu")
RAW = {"title": "IoT Weather Dashboard",
       "items": [{"name": "Temperature", "shows": "big number in °C", "source": "reading"},
                 {"name": "Humidity", "shows": "percent with a bar", "source": "reading"},
                 {"name": "Rain percentage", "shows": "percent circle", "source": "reading"},
                 {"name": "Weather prediction", "shows": "Rain likely / Cloudy / Clear with an icon", "source": "computed"},
                 {"name": "Last updated", "shows": "time of the last reading", "source": "computed"}],
       "data": {"where": "http://192.168.4.1/data", "fields": ["temperature", "humidity", "rain"]},
       "rules": ["Weather prediction: 'Rain likely' when humidity > 80 and rain > 60, 'Cloudy' when humidity > 65, "
                 "else 'Clear'"],
       "layout": "navbar, 4 cards in a row (one column on a phone), prediction banner, footer", "question": ""}

spec = webkit.clean_spec(RAW, USER)
check("an IP the user never wrote is dropped; no question: demo readings (2026-11-11)",
      spec["data"]["where"].startswith("demo readings") and spec["question"] == "", spec["data"])
check("a source the user gave is kept, no question", not webkit.clean_spec(
    dict(RAW, data={"where": "ThingSpeak channel", "fields": []}), USER + " thingspeak la irukku")["question"])
check("'demo' as the answer: demo readings", "demo readings" in webkit.with_answer(spec, "demo")["data"]["where"])
check("the spec reads as text", "Weather prediction (computed)" in webkit.spec_text(spec) and "Rule:" in
      webkit.spec_text(spec))
page = "<html><body><h1>Weather</h1><p>Temperature</p><p>Humidity</p><p>Rain</p><p>Weather Protection</p>" \
       "<span id=updated>Last updated</span><script>x()</script></body></html>"
probs = webkit.spec_problems(spec, page)
check("'Weather Protection' instead of the prediction: the prediction item is missing", len(probs) == 1
      and "Weather prediction" in probs[0], probs)
check("a page that has it (predictWeather()) passes",
      not webkit.spec_problems(spec, page.replace("x()", "predictWeather()")))

# the flow: spec -> question -> answer -> page with the spec in the coder's prompt
specs, prompts = [], []


def fake_json(base_url, model, messages, schema, **k):
    specs.append(messages[-1]["content"])
    return RAW, {}


def fake_stream(base_url, model, messages, tools=None, **k):
    prompts.append(messages[-1]["content"])
    text = "```html\n<!DOCTYPE html><html><body><h1>W</h1><p>Temperature Humidity Rain updated predict</p></body></html>\n```"
    yield ("text", text)
    yield ("done", {"content": text, "tool_calls": [], "usage": None, "stopped": False, "finish_reason": "stop"})


llm.complete_json, llm.stream_chat = fake_json, fake_stream
a = agent.Agent({"base_url": "x", "model": "m", "web_enabled": False})
a.load([], None)
ev = []
a.run(USER, ev.append)
texts = [e["text"] for e in ev if e.get("type") == "assistant_text"]
check("no question before building (2026-11-11)", not a.pending_page, texts[-1:])
# what app.py did with an answer, when there was a question: the source given is still used
a.page_spec = webkit.with_answer(webkit.clean_spec(RAW, USER), "ESP32 192.168.1.50/data la JSON tharum")
a.pending_page = None
ev = []
prompts.clear()
specs.clear()  # (the first run built the page at once, with demo readings)
a.run(USER, ev.append)
check("the coder gets the spec with the user's source", prompts and "[The page's spec" in prompts[0]
      and "192.168.1.50/data" in prompts[0] and "Rule: Weather prediction" in prompts[0], prompts[:1])
check("no second spec call for the answered request", len(specs) == 0, len(specs))
print("FAILS:", fails)
