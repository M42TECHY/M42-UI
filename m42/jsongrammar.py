"""⚡ A JSON schema as a GBNF grammar for llama-server, with NO whitespace between JSON's parts.

Why (2026-11-16): with the server's own json_schema the 4B writes pretty JSON (a newline and indentation before every
key). A page plan measured 2,109 tokens pretty and 1,171 compact: 44% of the plan's ~200 s of writing was spaces.
This grammar allows only compact JSON, so every structured call writes the same content in fewer tokens.

It covers what M42's schemas use: object (properties, required: the required ones first, then the optional ones, as
llama.cpp's own converter orders them), array (items, minItems, maxItems), string (maxLength, enum, the colour
patterns), integer (minimum, maximum), number, boolean, null. Anything else returns None: that call keeps the server's
json_schema (no change in what it may answer).
"""
import json
import re

CHAR = r'[^"\\\x7F\x00-\x1F] | "\\" (["\\bfnrt/] | "u" [0-9a-fA-F]{4})'
NUMBER = r'"-"? ([0-9] | [1-9] [0-9]{0,15}) ("." [0-9]{1,16})? ([eE] [-+]? [0-9]{1,15})?'
INTEGER = r'"-"? ([0-9] | [1-9] [0-9]{0,15})'
VALUE = ('value ::= object | array | string | number | ("true" | "false" | "null")\n'
         'object ::= "{" ( string ":" sp value ("," sp string ":" sp value)* )? "}"\n'
         'array ::= "[" ( value ("," sp value)* )? "]"\n'
         'string ::= "\\"" char* "\\""\n'
         f'number ::= {NUMBER}\n')
# the patterns M42's schemas use, as grammar (a pattern not here: the server's json_schema is kept)
PATTERNS = {
    "^#[0-9a-fA-F]{6}$": '"\\"#" [0-9a-fA-F]{6} "\\""',
    "^(#[0-9a-fA-F]{6})?$": '"\\"" ("#" [0-9a-fA-F]{6})? "\\""',
}
INT_SPAN = 400  # an integer range up to this wide is listed value by value (exact), a wider one is any integer


class Unsupported(Exception):
    pass


def _lit(text):
    """A GBNF literal for exact text."""
    return json.dumps(text, ensure_ascii=False)


def to_gbnf(schema):
    """The grammar (str) for `schema`, or None when it uses something this converter does not cover."""
    rules, n = {}, [0]

    def rule(body, hint="r"):
        for name, b in rules.items():  # (the same body once)
            if b == body:
                return name
        n[0] += 1
        name = f"{re.sub(r'[^a-z0-9]', '-', hint.lower())[:20] or 'r'}-{n[0]}"
        rules[name] = body
        return name

    def gen(s, hint="v"):
        if not isinstance(s, dict):
            raise Unsupported(repr(s)[:40])
        if "enum" in s:
            vals = s["enum"]
            if not vals:
                raise Unsupported("empty enum")
            return "(" + " | ".join(_lit(json.dumps(v, ensure_ascii=False)) for v in vals) + ")"
        unknown = set(s) - {"type", "properties", "required", "items", "minItems", "maxItems", "maxLength", "enum",
                            "pattern", "minimum", "maximum", "description", "title", "default"}
        if unknown:
            raise Unsupported(", ".join(sorted(unknown)))
        t = s.get("type")
        if t == "string":
            if s.get("pattern"):
                if s["pattern"] not in PATTERNS:
                    raise Unsupported("pattern " + s["pattern"])
                return PATTERNS[s["pattern"]]
            m = s.get("maxLength")
            return '"\\"" char' + (f"{{0,{int(m)}}}" if isinstance(m, int) else "*") + ' "\\""'
        if t == "integer":
            lo, hi = s.get("minimum"), s.get("maximum")
            if isinstance(lo, int) and isinstance(hi, int) and lo <= hi and hi - lo <= INT_SPAN:
                # longest first: "10" is tried before "1"
                vals = sorted((str(v) for v in range(lo, hi + 1)), key=lambda x: (-len(x), x))
                return rule("(" + " | ".join(_lit(v) for v in vals) + ")", hint + "-int")
            return rule(INTEGER, "integer")
        if t == "number":
            return rule(NUMBER, "number")
        if t == "boolean":
            return '("true" | "false")'
        if t == "null":
            return '"null"'
        if t == "array":
            item = rule(gen(s.get("items") or {"type": "string"}, hint + "-item"), hint + "-item") \
                if s.get("items") is not None else "value"
            lo, hi = int(s.get("minItems") or 0), s.get("maxItems")
            hi = int(hi) if isinstance(hi, int) else None
            if hi is not None and hi < lo:
                raise Unsupported("maxItems < minItems")
            if hi == 0:
                return '"[" "]"'
            more = (f'("," sp {item}){{{max(lo - 1, 0)},{hi - 1}}}' if hi is not None else
                    (f'("," sp {item}){{{lo - 1},}}' if lo > 1 else f'("," sp {item})*'))
            body = f"{item} {more}"
            return f'"[" {body} "]"' if lo >= 1 else f'"[" ( {body} )? "]"'
        if t == "object" or (t is None and "properties" in s):
            props = s.get("properties")
            if not props:
                return "object"
            req = [k for k in props if k in (s.get("required") or [])]
            opt = [k for k in props if k not in req]
            kv = {k: f'{_lit(json.dumps(k))} ":" sp {rule(gen(props[k], hint + "-" + k), hint + "-" + k)}' for k in props}
            if not opt:
                return '"{" ' + ' "," sp '.join(kv[k] for k in req) + ' "}"'
            # the optional ones after the required ones, each may be left out, in order
            def tail(keys):  # after something was written: ("," kv)? for each, in order
                return " ".join(f'("," sp {kv[k]})?' for k in keys)
            if req:
                return '"{" ' + ' "," sp '.join(kv[k] for k in req) + f" {tail(opt)} " + '"}"'
            start = rule(kv[opt[-1]], hint + "-start")  # nothing written yet: this one first, or one of the later ones
            for i in range(len(opt) - 2, -1, -1):
                start = rule(f"{kv[opt[i]]} {tail(opt[i + 1:])} | {start}", hint + "-start")
            return f'"{{" ( {start} )? "}}"'
        raise Unsupported(f"type {t!r}")

    try:
        root = gen(schema, "root")
    except Unsupported:
        return None
    # sp: one space after ":" and "," is allowed (": [" is how the model writes JSON on one line, and the space joins
    # the next token: free); newlines and indentation are not (each a token of its own)
    lines = [f"root ::= {root}"] + [f"{k} ::= {v}" for k, v in rules.items()] + [f"char ::= {CHAR}", 'sp ::= " "?']
    if any(re.search(r"\b(value|object)\b", v) for v in [root] + list(rules.values())):
        lines.append(VALUE.strip())
    return "\n".join(lines) + "\n"
