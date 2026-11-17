"""Minimal streaming client for any OpenAI-compatible server (Ollama, llama.cpp llama-server, LM Studio)."""
import json
import re
import time
import urllib.error
import urllib.request


class LLMError(Exception):
    pass


class LLMStopped(LLMError):
    """The user pressed Stop while the model was answering."""


# M42's Stop button (agent.py sets it to its stop_event.is_set): a JSON request is then streamed and dropped the
# moment Stop is pressed, and llama-server cancels the job. A non-streaming request ran to its end (60-200 s for
# a page plan) before Stop was seen, and the next request waited behind it (the user: "Stop doesn't stop").
STOP = None


def _headers(api_key):
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def list_models(base_url, api_key=None, timeout=3):
    req = urllib.request.Request(base_url.rstrip("/") + "/models", headers=_headers(api_key))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.URLError as e:
        raise LLMError(f"Cannot reach model server at {base_url}: {getattr(e, 'reason', e)}")
    except (OSError, ValueError) as e:
        raise LLMError(f"Bad response from {base_url}: {e}")
    return [m.get("id") for m in data.get("data", []) if m.get("id")]


def complete_json(base_url, model, messages, schema, max_tokens=700, api_key=None, timeout=900, think=0, temperature=0.1):
    """One non-streaming completion constrained to a JSON schema (llama-server turns the schema into a
    grammar, so the output always parses). Returns (dict, timings). A connection dropped right after a model
    switch (WinError 10054) is retried once."""
    if STOP and STOP():
        raise LLMStopped("stopped")
    try:
        return _complete_json(base_url, model, messages, schema, max_tokens, api_key, timeout, think, temperature=temperature)
    except LLMStopped:
        raise
    except LLMError as e:
        if STOP and STOP():
            raise LLMStopped("stopped")
        if SPEC_BATCH_RX.search(str(e)):
            return _complete_json(base_url, model, messages, schema, max_tokens, api_key, timeout, think, no_cache=True, temperature=temperature)
        if "valid JSON" in str(e) and not think:  # (now and then an answer under the grammar did not parse: a POS's
            # bill was lost and a coder spent 5 minutes patching one in, 2026-11-17; asked again once, fresh, a little warmer)
            return _complete_json(base_url, model, messages, schema, max_tokens, api_key, timeout, think, no_cache=True,
                                  temperature=min(0.7, temperature + 0.2))
        if "connection" not in str(e).lower():
            raise
        time.sleep(3)
        return _complete_json(base_url, model, messages, schema, max_tokens, api_key, timeout, think, temperature=temperature)


# llama-server with a draft model (coder-7b + 0.5B): after a short request, the next one reused the cached prompt
# and the draft's KV cache was still at the old position ("inconsistent sequence positions ... failed to process
# speculative batch", 2026-10-25): the page was never written. Asked again without the cached prompt, both start over.
SPEC_BATCH_RX = re.compile(r"speculative batch|inconsistent sequence positions|failed to decode draft", re.I)


def json_constraint(base_url, schema, think=0):
    """⚡ How a JSON answer is held to its schema: on M42's own llama-server a grammar for COMPACT JSON (jsongrammar:
    the 4B's pretty JSON was ~44% newlines and indentation in a page plan, 2026-11-16), else the server's json_schema
    (another server, a schema the grammar does not cover, or thinking, whose words come before the JSON)."""
    if not think:
        try:
            import llamacpp
            local = base_url.rstrip("/") == llamacpp.URL.rstrip("/")
        except ImportError:
            local = False
        if local:
            import jsongrammar
            g = jsongrammar.to_gbnf(schema)
            if g:
                return {"grammar": g}
    return {"response_format": {"type": "json_schema", "json_schema": {"name": "result", "schema": schema}}}


def _complete_json(base_url, model, messages, schema, max_tokens, api_key, timeout, think=0, no_cache=False, temperature=0.1):
    """temperature: 0.1 for decisions; a creative step (the 3D scene's story) asks for more (the same story every time at 0.1)."""
    if STOP and not think:  # streamed, so Stop can drop it at once (see STOP)
        result = None
        for kind, value in _stream_chat(base_url, model, messages, temperature=temperature, max_tokens=max_tokens, api_key=api_key,
                                        timeout=timeout, should_stop=STOP, no_cache=no_cache,
                                        **json_constraint(base_url, schema)):
            if kind == "done":
                result = value
        if not result or result.get("stopped"):
            raise LLMStopped("stopped")
        text = re.sub(r"^```(json)?\s*|\s*```$", "", (result.get("content") or "").strip())
        try:
            return json.loads(text), result.get("timings") or {}
        except ValueError:
            raise LLMError(f"Model did not return valid JSON: {text[:200]}")
    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens + think,
            **json_constraint(base_url, schema, think)}
    if no_cache:
        body["cache_prompt"] = False
    if think:  # thinking for this one request, cut at `think` tokens (the server runs with it off): without a
        # budget q35-4b thought for 2,000 tokens on a review and never wrote the answer; with 800 it did (91 s)
        body.update(chat_template_kwargs={"enable_thinking": True}, reasoning_budget=think, thinking_budget_tokens=think)
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers=_headers(api_key), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise LLMError(f"Model server returned HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as e:
        raise LLMError(f"Cannot reach model server at {base_url}: {getattr(e, 'reason', e)}")
    except (OSError, ValueError) as e:  # connection reset mid-request (crashed a build in practice)
        raise LLMError(f"Model server connection failed: {e}")
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    text = re.sub(r"^```(json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text), data.get("timings") or {}
    except ValueError:
        raise LLMError(f"Model did not return valid JSON: {text[:200]}")


def unload_ollama_models(base_url):
    """Ask an Ollama server to free its loaded models (two 7B models in RAM halve the speed).

    Returns the names unloaded; silently does nothing if the server isn't Ollama or isn't running."""
    root = base_url.rstrip("/")
    root = root[:-3] if root.endswith("/v1") else root
    try:
        with urllib.request.urlopen(root + "/api/ps", timeout=3) as r:
            loaded = [m["name"] for m in json.load(r).get("models", [])]
        for name in loaded:
            req = urllib.request.Request(root + "/api/generate", method="POST",
                                         data=json.dumps({"model": name, "keep_alive": 0}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=30).read()
        return loaded
    except (OSError, ValueError, KeyError):
        return []


def _lines(resp):
    """The response's lines; a connection dropped mid-stream becomes an LLMError, not a crash."""
    try:
        yield from resp
    except OSError as e:
        raise LLMError(f"Model server connection dropped: {e}")


def stream_json(base_url, model, messages, schema, max_tokens=700, api_key=None, should_stop=lambda: False,
                on_text=None, on_done=None):
    """complete_json, streamed: on_text(text_so_far) is called as tokens arrive (for a live progress line),
    and should_stop() can cancel it; on_done(result) gets the raw result (timings for the stats line).
    Returns the parsed dict (raises LLMError when stopped or invalid)."""
    result = None
    for kind, value in stream_chat(base_url, model, messages, temperature=0.1, max_tokens=max_tokens,
                                   api_key=api_key, timeout=900, should_stop=should_stop,
                                   **json_constraint(base_url, schema)):
        if kind == "text" and on_text:
            on_text(value)
        elif kind == "done":
            result = value
            if on_done:
                on_done(value)
    if not result or result.get("stopped"):
        raise LLMError("stopped")
    text = re.sub(r"^```(json)?\s*|\s*```$", "", (result.get("content") or "").strip())
    try:
        return json.loads(text)
    except ValueError:
        raise LLMError(f"Model did not return valid JSON: {text[:200]}")


def stream_chat(*args, **kwargs):
    """_stream_chat, asked once more without the cached prompt when llama-server's draft model lost its place
    (SPEC_BATCH_RX) before any text came."""
    texted = False
    try:
        for item in _stream_chat(*args, **kwargs):
            texted = texted or item[0] == "text"
            yield item
    except LLMError as e:
        if texted or not SPEC_BATCH_RX.search(str(e)):
            raise
        yield from _stream_chat(*args, **dict(kwargs, no_cache=True))


def _stream_chat(base_url, model, messages, tools=None, temperature=0.2, max_tokens=2048,
                 api_key=None, timeout=600, should_stop=lambda: False, stop_when=None, response_format=None,
                 grammar=None, no_cache=False):
    """Yield ("text", chunk) while streaming, then one final ("done", result).

    stop_when(text_so_far) -> True ends generation early (closing the connection makes the
    server stop generating). Used to cut off a model as soon as it has written one tool call.

    result = {"content": str, "tool_calls": [{"id", "name", "arguments"}], "usage": dict | None,
              "stopped": bool}
    """
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format
    if grammar:  # llama-server: GBNF that the output must follow (edits: SEARCH/REPLACE blocks only)
        body["grammar"] = grammar
    if no_cache:
        body["cache_prompt"] = False
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(api_key),
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        raise LLMError(f"Model server returned HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise LLMError(f"Cannot reach model server at {base_url}: {getattr(e, 'reason', e)}")
    except OSError as e:
        raise LLMError(f"Model server connection failed: {e}")

    content = []
    calls = {}
    usage = None
    timings = None
    finish = None  # "length" = cut off at max_tokens
    stopped = False
    cut = False
    with resp:
        for raw in _lines(resp):
            if should_stop():
                stopped = True
                break
            if cut:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except ValueError:
                continue
            if chunk.get("error"):
                err = chunk["error"]
                raise LLMError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
            usage = chunk.get("usage") or usage
            timings = chunk.get("timings") or timings  # llama-server: real token counts and speeds
            for choice in chunk.get("choices") or []:
                finish = choice.get("finish_reason") or finish
                delta = choice.get("delta") or {}
                text = delta.get("content")
                if text:
                    content.append(text)
                    yield ("text", text)
                    if stop_when and ("}" in text or ">" in text or chr(10) in text) and stop_when("".join(content)):
                        cut = True
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", len(calls))
                    slot = calls.setdefault(idx, {"id": None, "name": "", "arguments": ""})
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["name"] += fn["name"]
                    args = fn.get("arguments")
                    if args:
                        slot["arguments"] += args if isinstance(args, str) else json.dumps(args)

    tool_calls = [calls[i] for i in sorted(calls)]
    yield ("done", {"content": "".join(content), "tool_calls": tool_calls, "usage": usage,
                    "stopped": stopped, "timings": timings, "finish_reason": finish})
