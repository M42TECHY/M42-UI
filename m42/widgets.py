"""M42's widget library: the parts that dashboards and apps are made of (the user, 2026-10-27: "every widget the
reference has must come: calendar, donut, toggles, table, popup... add many"). Each widget is a renderer over the
plan's plain data, so the chat model only fills content and M42 draws it the same quality every time:
  section: title, lead, eyebrow, button, labels (x labels / columns / month), taken (highlighted days), items
  item:    title, text, icon, meta[], value, unit, badge, tags[], group, values[] (a chart series)
NOTES tells the model what each widget reads. Interactive parts work through m42-ui.js data attributes (every
button does something: M42's browser check reports dead ones). Colours come from the page's look (--m42-accent,
-2, -3, their ink); nothing here names a colour."""
import calendar
import datetime
import json
import math
import re

TONES = ("var(--m42-accent)", "var(--m42-accent-2)", "var(--m42-accent-3)", "#f59e0b", "#10b981", "#ef4444")
TINTS = ("var(--m42-accent-rgb)", "var(--m42-accent-2-rgb)", "var(--m42-accent-3-rgb)")
# the text on each of TONES as a fill (a pale reference colour gets dark text)
ONS = ("var(--m42-on-accent, #fff)", "var(--m42-on-accent-2, #fff)", "var(--m42-on-accent-3, #fff)", "#fff", "#fff", "#fff")


def _pb():
    import pagebuild
    return pagebuild


def e(s):
    return _pb().e(s)


def ic(name, fallback="bi-circle"):
    return _pb().icon(name, fallback)


def amount(v, unit=""):
    return _pb().amount(v, unit)


def badge(t):
    return _pb().badge(t)


def num(v, d=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def fmt(v):
    v = num(v)
    return f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"


def initials(name):
    return "".join(w[0] for w in str(name or "?").split()[:2]).upper() or "?"


NUM_TEXT_RX = re.compile(r"^\s*[₹$€£]?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(%|[A-Za-z°/ ]{0,12})\s*$")


def items(sec, n=None):
    """The section's items; an item with no value but a number in its text or meta ("45 rooms", "₹12,450", "78%")
    gets that number as its value (a real run: the 4B wrote them as text, the tiles showed "—")."""
    its = []
    for i in sec.get("items") or []:
        if not isinstance(i, dict):
            continue
        if i.get("value") in (None, ""):
            for t in [i.get("text")] + list(i.get("meta") or []):
                m = NUM_TEXT_RX.match(str(t or ""))
                if m:
                    i = dict(i, value=float(m.group(1).replace(",", "")), unit=i.get("unit") or m.group(2).strip() or ("₹" if "₹" in str(t) else ""))
                    break
        its.append(i)
    return its[:n] if n else its


def head(sec):
    """A widget's own small header (title, lead, a badge). In an app panel the panel has it already."""
    if not (sec.get("title") or sec.get("lead")):
        return ""
    return (f'<div class="m42-w-head"><div><h3>{e(sec.get("title"))}</h3>'
            + (f'<p>{e(sec.get("lead"))}</p>' if sec.get("lead") else "") + "</div>"
            + (f'<span class="m42-badge">{e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") else "") + "</div>")


def series(sec):
    """[(name, [numbers])] from the items' values (a value alone is a series of one)."""
    out = []
    for it in items(sec, 3):
        vals = [num(v) for v in (it.get("values") or []) if isinstance(v, (int, float, str))]
        if not vals and it.get("value") not in (None, ""):
            vals = [num(it["value"])]
        if vals:
            out.append((str(it.get("title") or f"Series {len(out) + 1}"), vals[:24]))
    # the numbers checked, not the words (a real run, 2026-11-12): a last point many times every other one is the
    # series' total written as a point (revenue 1,200 ... 4,000, then 45,230: the line shot up); a series far smaller
    # than the main one lies flat on its axis (orders 45-210 beside revenue in thousands): left out of this chart
    fixed = []
    for name, vals in out:
        rest = [abs(v) for v in vals[:-1] if isinstance(v, (int, float))]
        if len(vals) >= 4 and rest and max(rest) > 0 and abs(vals[-1]) > 3 * max(rest):
            vals = vals[:-1]
        fixed.append((name, vals))
    top = max((max((abs(v) for v in vals if isinstance(v, (int, float))), default=0) for _n, vals in fixed), default=0)
    if len(fixed) > 1 and top > 0:
        kept = [(n, v) for n, v in fixed if max((abs(x) for x in v if isinstance(x, (int, float))), default=0) >= .1 * top]
        fixed = kept or fixed[:1]
    return fixed


# ---- charts --------------------------------------------------------------------------------------------------

def _smooth(pts):
    """An SVG path through the points, smoothed (Catmull-Rom as cubic Béziers)."""
    if len(pts) < 2:
        return f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" if pts else ""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(0, i - 1)], pts[i], pts[i + 1]
        p3 = pts[min(len(pts) - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def _scale(vals_list):
    hi = max([max(v) for v in vals_list if v] + [1])
    lo = min([min(v) for v in vals_list if v] + [0])
    lo = min(lo, 0)
    step = 10 ** math.floor(math.log10(max(1e-9, (hi - lo) / 4))) if hi > lo else 1
    for m in (1, 2, 2.5, 5, 10):
        if (hi - lo) / (step * m) <= 4:
            step *= m
            break
    top = math.ceil(hi / step) * step
    return lo, max(top, lo + step), step


def w_line_chart(sec, ctx, area=False):
    its = items(sec, 24)
    if len(its) >= 3 and not any(len(i.get("values") or []) > 1 for i in its) and all(i.get("value") not in (None, "") for i in its):
        # points written as items (120 Jan, 145 Feb, 180 Mar...: a real run showed them as four numbers): one line
        sec = dict(sec, labels=sec.get("labels") or [str(i.get("title") or "") for i in its],
                   items=[{"title": sec.get("title") or "Value", "values": [num(i.get("value")) for i in its], "unit": its[0].get("unit")}])
    ss = series(sec)
    if not ss:  # the plan gave no numbers (a real run: "No data yet" in a weather trend card): a sample curve,
        n = max(6, min(12, len(sec.get("labels") or [])))  # like every other figure on a sample page
        name = str((items(sec) or [{}])[0].get("title") or sec.get("title") or "Trend")
        ss = [(name, [round(50 + 18 * math.sin(i / 1.6) + 4 * math.sin(i * 1.7) + i * 2) for i in range(n)])]
    if max(len(v) for _, v in ss) < 3:  # one number is no trend: shown as the number it is
        return w_metric_pair(dict(sec, items=[dict(i, value=(i.get("values") or [i.get("value")])[-1]) for i in items(sec, 4)]), ctx)
    n = max(len(v) for _, v in ss)
    labels = [str(x) for x in (sec.get("labels") or [])][:n] or guess_labels(sec, n)
    cj = _chartjs(sec, ctx, "line", labels, ss)
    if cj:
        return cj
    # a ruler-straight line (20, 40, 60...: a real run's "Power consumption") is a made-up sample: given the ups
    # and downs a real reading has
    def lively(vals):
        d = vals[1] - vals[0] if len(vals) >= 4 else 0
        if not d or len({round(vals[k + 1] - vals[k], 6) for k in range(len(vals) - 1)}) != 1:
            return vals
        return [round(v + d * .6 * math.sin(k * 2.1), 1) for k, v in enumerate(vals)]
    ss = [(name, lively(vals)) for name, vals in ss]
    lo, hi, step = _scale([v for _, v in ss])
    if sec.get("tight"):  # a small chart without axes (chart_stats): the curve fills it, not 0..max
        flat = [x for _, v in ss for x in v]
        pad = (max(flat) - min(flat)) * .15 or 1
        lo, hi = min(flat) - pad, max(flat) + pad
    W, H = 600, 220

    def pt(i, v, count):
        return (i * W / max(1, count - 1), H - (v - lo) / (hi - lo) * H)
    paths, legend = [], []
    for k, (name, vals) in enumerate(ss):
        pts = [pt(i, v, len(vals)) for i, v in enumerate(vals)]
        col = TONES[k % len(TONES)]
        d = _smooth(pts)
        gid = f"g{ctx['ids'].__len__()}{k}"
        ctx["ids"].add(gid)
        if area or k == 0:
            paths.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{col}" '
                         f'stop-opacity="{.32 if k == 0 else .18}"/><stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>'
                         f'<path d="{d} L{W},{H} L0,{H} Z" fill="url(#{gid})"/>')
        paths.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3" stroke-linecap="round" vector-effect="non-scaling-stroke"/>')
        legend.append(f'<span><i style="background:{col}"></i>{e(name)}</span>')
    name0, vals0 = ss[0]
    top = max(range(len(vals0)), key=lambda i: vals0[i])
    x, y = pt(top, vals0[top], len(vals0))
    tip = (f'<div class="m42-w-tip" style="left:{x / W * 100:.1f}%;top:{y / H * 100:.1f}%"><b>{e(fmt(vals0[top]))}'
           f'{e(ss and items(sec)[0].get("unit") or "")}</b>' + ("" if sec.get("tight") else f'<small>{e(labels[top] if top < len(labels) else "")}</small>') + '</div>')
    ticks = "".join(f"<span>{e(fmt(lo + step * i))}</span>" for i in range(int(round((hi - lo) / step)) + 1))
    xl = "".join(f"<span>{e(l)}</span>" for l in labels)
    return (head(sec) + (f'<div class="m42-w-legend">{"".join(legend)}</div>' if len(ss) > 1 else "")
            + f'<div class="m42-w-chart"><div class="m42-w-y">{ticks}</div><div class="m42-w-plot">'
            f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">{"".join(paths)}</svg>{tip}</div></div>'
            f'<div class="m42-w-x">{xl}</div>')


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def guess_labels(sec, n):
    """A chart's x labels when the plan gave none: the last n months for a monthly / usage chart, days of a week,
    hours of a day; else 1..n (a real run: "Power consumption" read 1 2 3 4 5 6 under a monthly chart)."""
    words = " ".join(str(sec.get(k) or "") for k in ("title", "lead", "eyebrow"))
    words += " " + " ".join(str(i.get("title") or "") + " " + str(i.get("unit") or "") for i in items(sec, 3))
    if re.search(r"hour|today|24h", words, re.I):
        return [f"{(8 + 2 * k) % 24:02d}:00" for k in range(n)]
    if re.search(r"week|daily|\bday", words, re.I) and n <= 7:
        return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][:n]
    if re.search(r"month|year|consum|usage|kwh|revenue|sales|income|bill|trend", words, re.I) and n <= 12:
        import datetime
        m = datetime.date.today().month
        return [MONTHS[(m - n + k) % 12] for k in range(n)]
    return [str(i + 1) for i in range(n)]


def w_area_chart(sec, ctx):
    return w_line_chart(sec, ctx, area=True)


def w_chart_stats(sec, ctx):
    """A line chart with a status pill at its peak and 2-4 numbers with icons under it (the weather shot's "Live
    conditions": a curve, "Dangerous", humidity / wind / pressure)."""
    its = items(sec)
    line = next((i for i in its if i.get("values")), its[0] if its else {"title": "Trend"})
    stats = [i for i in its if i is not line][:4]
    vals = [num(v) for v in line.get("values") or []]
    if len(vals) < 6:  # a few readings (a real run: 78, 75, 72) are a flat line: a day's curve through the last one
        now = vals[-1] if vals else num(line.get("value")) or 50
        amp = max(abs(max(vals) - min(vals)) if vals else 0, abs(now) * .12, 3)
        vals = [round(now + amp * (math.sin(k / 1.5 - 3.2) + .35 * math.sin(k * 1.3)) - amp * (math.sin(10 / 1.5 - 3.2) + .35 * math.sin(13)), 1)
                for k in range(11)]
    line = dict(line, values=vals)
    chart = w_line_chart(dict(sec, title="", lead="", eyebrow="", labels=[], items=[line], tight=True), ctx)
    pill = f'<span class="m42-w-cpill">{badge(line["badge"])}</span>' if line.get("badge") else ""
    trend = f'<span class="m42-w-pill"><i class="bi bi-arrow-up"></i> {e(line.get("text"))}</span>' if line.get("text") else ""
    cells = "".join(f'<div><i class="bi {ic(i.get("icon"), webkit_icon(i.get("title")))}"></i><b>{e(fmt(i.get("value")))}'
                    f'<small>{e(i.get("unit") or "")}</small></b><span>{e(i.get("title"))}</span></div>' for i in stats)
    return (head(sec) + f'<div class="m42-w-cstat">{trend}{pill}{chart}</div>' + (f'<div class="m42-w-cstats">{cells}</div>' if cells else ""))


def webkit_icon(name):
    import webkit
    return webkit._icon_for(str(name or ""))


def w_bar_chart(sec, ctx):
    its = items(sec, 24)
    if len(its) >= 3 and not any(len(i.get("values") or []) > 1 for i in its) and all(i.get("value") not in (None, "") for i in its):
        # bars written as items (Jan 92, Feb 95, Mar 98...: a real run drew 3 of them side by side over one "1"): one series
        sec = dict(sec, labels=sec.get("labels") or [str(i.get("title") or "") for i in its],
                   items=[{"title": sec.get("title") or "Value", "values": [num(i.get("value")) for i in its], "unit": its[0].get("unit")}])
    ss = series(sec)
    if not ss:
        return head(sec)
    n = max(len(v) for _, v in ss)
    labels = [str(x) for x in (sec.get("labels") or [])][:n] or [str(i + 1) for i in range(n)]
    cj = _chartjs(sec, ctx, "bar", labels, ss)
    if cj:
        return cj
    lo, hi, step = _scale([v for _, v in ss])
    groups = []
    style = look(sec).get("bars", "")
    top = max(range(n), key=lambda i: ss[0][1][i] if i < len(ss[0][1]) else 0)
    for i in range(n):
        lit = style != "one highlighted" or i == top
        tip = (f'<span class="m42-w-bartip" style="bottom:calc({max(2, ss[0][1][i] / hi * 100):.1f}% + 8px)">{e(fmt(ss[0][1][i]))}<small>{e(labels[i] if i < len(labels) else "")}</small></span>'
               if style == "one highlighted" and i == top else "")
        bars = tip + "".join(f'<i class="{"is-pale" if not lit else ""}" style="height:{max(2, (vals[i] if i < len(vals) else 0) / hi * 100):.1f}%;background:{TONES[k % 6]}" '
                       f'title="{e(name)}: {e(fmt(vals[i] if i < len(vals) else 0))}"></i>' for k, (name, vals) in enumerate(ss))
        groups.append(f'<div class="m42-w-bar"><div>{bars}</div><span>{e(labels[i] if i < len(labels) else "")}</span></div>')
    legend = "".join(f'<span><i style="background:{TONES[k % 6]}"></i>{e(name)}</span>' for k, (name, _) in enumerate(ss))
    ticks = "".join(f"<span>{e(fmt(step * i))}</span>" for i in range(int(round(hi / step)) + 1))
    return (head(sec) + f'<div class="m42-w-chart is-bars{" is-striped" if style else ""}"><div class="m42-w-y">{ticks}</div><div class="m42-w-bars">{"".join(groups)}</div></div>'
            + (f'<div class="m42-w-legend mt-2">{legend}</div>' if len(ss) > 1 else ""))


def w_hbars(sec, ctx):
    its = items(sec, 6)
    top = max([num(i.get("value")) for i in its] + [1])
    lk = look(sec)
    if lk.get("photos") or lk.get("bars") == "striped":  # the D.CC "Top dishes": a picture, the name, the number, a striped bar
        rows = "".join(f'<div class="m42-w-hrow2" style="--t:{TINTS[k % 3]}">'
                       + (f'<span class="m42-w-thumb is-sm"><i class="bi {ic(i.get("icon"), thumb_icon(i, sec))}"></i></span>' if lk.get("photos") else "")
                       + f'<span class="m42-w-hname">{e(i.get("title"))}</span><b>{e(fmt(i.get("value")))}</b>'
                       f'<div class="m42-w-track is-striped is-marked"><i style="width:{num(i.get("value")) / top * 100:.1f}%"></i></div></div>'
                       for k, i in enumerate(its))
        return head(sec) + f'<div class="m42-w-hbars">{rows}</div>'
    rows = "".join(f'<div class="m42-w-hbar"><div class="d-flex justify-content-between"><span>{e(i.get("title"))}</span>'
                   f'<b>{amount(i.get("value"), i.get("unit") or "") if i.get("unit") else e(fmt(i.get("value")))}</b></div>'
                   f'<div class="m42-w-track"><i style="width:{num(i.get("value")) / top * 100:.1f}%;background:{TONES[k % 6]}"></i></div></div>'
                   for k, i in enumerate(its))
    return head(sec) + f'<div class="m42-w-hbars">{rows}</div>'


def _ring(pct, col, size=120, stroke=12, label=""):
    pct = max(0, min(100, num(pct)))
    return (f'<div class="m42-w-ring" style="--s:{size}px"><svg viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.915" fill="none" '
            f'stroke="rgba(127,127,127,.15)" stroke-width="{stroke / size * 42 * 1.4:.1f}"/><circle cx="21" cy="21" r="15.915" fill="none" '
            f'stroke="{col}" stroke-width="{stroke / size * 42 * 1.4:.1f}" stroke-linecap="round" stroke-dasharray="{pct:.1f} {100 - pct:.1f}" '
            f'transform="rotate(-90 21 21)"/></svg><b>{e(label or f"{fmt(pct)}%")}</b></div>')


def _chartjs(sec, ctx, kind, labels, ss):
    """The chart drawn by Chart.js when the user named it (the user, 2026-11-17: "the JS the user asks for is used"):
    a canvas with its data; m42-ui.js draws it in the theme's colours. "" when the page does not use Chart.js."""
    if "chart.js" not in (ctx.get("libs") or ()):
        return ""
    cfg = {"type": kind, "labels": [str(x) for x in labels], "series": [{"name": str(n), "values": [num(v) for v in vals]} for n, vals in ss]}
    return (head(sec) + f'<div class="m42-w-chartjs"><canvas data-m42-chartjs="{e(json.dumps(cfg, ensure_ascii=False))}" '
            f'role="img" aria-label="{e(sec.get("title") or kind)}"></canvas></div>')


def w_donut(sec, ctx):
    its = items(sec, 6)
    cj = _chartjs(sec, ctx, "doughnut", [i.get("title") for i in its], [(sec.get("title") or "", [i.get("value") for i in its])]) if its else ""
    if cj:
        return cj
    total = sum(num(i.get("value")) for i in its) or 1
    acc, segs = 0, []
    for k, i in enumerate(its):
        p = num(i.get("value")) / total * 100
        segs.append(f'<circle cx="21" cy="21" r="15.915" fill="none" stroke="{TONES[k % 6]}" stroke-width="6" '
                    f'stroke-dasharray="{max(0, p - .6):.2f} {100 - max(0, p - .6):.2f}" stroke-dashoffset="{25 - acc:.2f}"/>')
        acc += p
    center = items(sec)[0] if its else {}
    mid = f"{num(center.get('value')) / total * 100:.0f}%" if its else ""
    legend = "".join(f'<span><i style="background:{TONES[k % 6]}"></i>{e(i.get("title"))} <b>{e(fmt(i.get("value")))}</b></span>'
                     for k, i in enumerate(its))
    return (head(sec) + f'<div class="m42-w-donut"><div class="m42-w-ring" style="--s:170px"><svg viewBox="0 0 42 42">{"".join(segs)}'
            f'</svg><b>{e(mid)}</b></div><div class="m42-w-legend is-col">{legend}</div></div>')


def w_rings(sec, ctx):
    cells = "".join(f'<div class="m42-w-ringcell">{_ring(i.get("value"), TONES[k % 6], 110, 12)}<div><b>{e(fmt(i.get("value")))}%</b>'
                    f'<small>{e(i.get("title"))}</small></div></div>' for k, i in enumerate(items(sec, 4)))
    return head(sec) + f'<div class="m42-w-rings">{cells}</div>'


def w_gauge(sec, ctx):
    its = items(sec)
    main = its[0] if its else {"title": "Value", "value": 50}
    v, lo, hi = num(main.get("value"), 50), 0, 100
    m = re.findall(r"-?\d+(?:\.\d+)?", " ".join(main.get("meta") or []))
    if len(m) >= 2:
        lo, hi = float(m[0]), float(m[1])
    elif v > 100:
        hi = v * 1.5
    gid = _pb().slug("dial", ctx["ids"])
    modes = "".join(f'<button type="button" class="m42-chip-btn{" active" if k == 0 else ""}"><i class="bi {ic(i.get("icon"), "bi-circle")}"></i> '
                    f'{e(i.get("title"))}</button>' for k, i in enumerate(its[1:6]))
    pct = (v - lo) / (hi - lo or 1) * 75
    return (head(sec) + f'<div class="m42-w-gauge" id="{gid}" data-m42-dial data-min="{lo:g}" data-max="{hi:g}" data-value="{v:g}">'
            f'<button type="button" class="m42-icon-btn" data-step="-1" aria-label="Less"><i class="bi bi-dash"></i></button>'
            f'<div class="m42-w-dial"><svg viewBox="0 0 42 42"><circle cx="21" cy="21" r="15.915" fill="none" stroke="rgba(127,127,127,.15)" '
            f'stroke-width="3" stroke-dasharray="75 25" transform="rotate(135 21 21)" stroke-linecap="round"/><circle class="arc" cx="21" cy="21" '
            f'r="15.915" fill="none" stroke="var(--m42-accent)" stroke-width="3" stroke-dasharray="{pct:.1f} {100 - pct:.1f}" '
            f'transform="rotate(135 21 21)" stroke-linecap="round"/></svg><b><span>{e(fmt(v))}</span>{e(main.get("unit") or "")}</b>'
            f'<small>{e(main.get("title"))}</small></div>'
            f'<button type="button" class="m42-icon-btn" data-step="1" aria-label="More"><i class="bi bi-plus"></i></button></div>'
            + (f'<div class="m42-chips justify-content-center mt-3" data-single>{modes}</div>' if modes else ""))


# ---- data ------------------------------------------------------------------------------------------------------

def w_data_table(sec, ctx):
    """A table people work with: search, sort by any column, pages of 6, status pills, view / delete per row."""
    pb = _pb()
    s = pb._reshape(dict(sec, items=[dict(i) for i in items(sec)]), "table")
    body = pb.p_table(dict(s, title="", lead="", eyebrow=""), ctx)
    tid = pb.slug((sec.get("title") or "table") + "-dt", ctx["ids"])
    body = body.replace('<table class="m42-table">', f'<table class="m42-table" id="{tid}">', 1)
    body = body.replace("</tr></thead>", '<th class="text-end">Actions</th></tr></thead>', 1)
    body = re.sub(r"(<tbody>.*?)</tbody>", lambda m: m.group(1).replace(
        "</tr>", '<td class="text-end text-nowrap"><button type="button" class="m42-icon-btn sm" data-m42-view aria-label="View">'
                 '<i class="bi bi-eye"></i></button> <button type="button" class="m42-icon-btn sm" data-m42-remove aria-label="Delete">'
                 '<i class="bi bi-trash3"></i></button></td></tr>') + "</tbody>", body, count=1, flags=re.S)
    return (head(sec) + f'<div class="m42-w-dt" data-m42-dt="{tid}"><div class="d-flex flex-wrap gap-2 justify-content-between mb-3">'
            f'<label class="m42-topsearch m-0"><i class="bi bi-search"></i><input type="search" placeholder="Search…" '
            f'aria-label="Search the table" data-m42-dt-search></label>'
            + (f'<button type="button" class="m42-btn" data-bs-toggle="modal" data-bs-target="#{tid}-add"><i class="bi bi-plus-lg"></i> '
               f'{e(sec.get("button") or "Add")}</button>' if sec.get("button") else "")
            + f'</div>{body}<div class="m42-w-pager" data-m42-dt-pager></div></div>'
            + (_modal(f"{tid}-add", sec.get("button") or "Add", [{"label": c, "type": "text"} for c in
                                                                    (s.get("labels") or ["Name"])[:4] if c], ctx) if sec.get("button") else ""))


def w_calendar(sec, ctx):
    """A month (labels[0] like "March 2030", else this month); taken = the highlighted days; items = its events."""
    today = datetime.date.today()
    year, month = today.year, today.month
    lab = " ".join(sec.get("labels") or [])
    m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\w*\s*(\d{4})?", lab, re.I)
    if m:
        month = [x.lower() for x in calendar.month_name].index(m.group(1).lower())
        year = int(m.group(2) or year)
    marks = sorted({int(x) for x in re.findall(r"\d+", " ".join(str(t) for t in sec.get("taken") or [])) if 1 <= int(x) <= 31})
    if not marks and items(sec):  # events but no days named (a real plan): they are spread over the month
        marks = sorted({min(28, 3 + k * 5 + (k % 2) * 2) for k in range(min(5, len(items(sec))))})
    cid = _pb().slug("cal", ctx["ids"])
    # each highlighted day shows its event's icon in a soft circle of the site's colours (the cooking reference's
    # calendar had a dish on its days; numbers alone looked plain): the events' icons in turn, else the brand's
    icons = [ic(i.get("icon"), "") for i in items(sec) if i.get("icon")] or [""]  # no events with icons: plain marked days
    if len(marks) < len([i for i in items(sec) if i.get("icon")]):
        icons = [""]  # fewer marked days than events (the school shot: day 15 and an agenda of 3): the day keeps its number
    # (the Travelgo shot's calendar: a brand icon on each day showed as black dots)
    icon_of = {d: icons[k % len(icons)] for k, d in enumerate(marks) if icons[k % len(icons)]}
    events = "".join(f'<li style="--c:{TONES[k % 6]}"><b>{e(i.get("title"))}</b><small>{e(i.get("text") or " · ".join(i.get("meta") or []))}</small></li>'
                     for k, i in enumerate(items(sec, 4)))
    return (head(sec) + f'<div class="m42-w-cal" id="{cid}" data-m42-cal data-year="{year}" data-month="{month}" '
            f'data-marks="{e(json.dumps(marks))}" data-icons="{e(json.dumps(icon_of))}" data-today="{today.day if (today.year, today.month) == (year, month) else 0}">'
            '<div class="m42-w-cal-head"><button type="button" class="m42-icon-btn sm" data-cal="-1" aria-label="Previous month">'
            '<i class="bi bi-chevron-left"></i></button><b data-cal-title></b><button type="button" class="m42-icon-btn sm" data-cal="1" '
            'aria-label="Next month"><i class="bi bi-chevron-right"></i></button></div><div class="m42-w-cal-grid" data-cal-grid>'
            + _cal_grid(year, month, marks, today.day if (today.year, today.month) == (year, month) else 0, icon_of)
            + "</div></div>" + (f'<ul class="m42-w-agenda mt-3">{events}</ul>' if events else ""))


CLOCK_RX = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def _minutes(t):
    """"9:30", "09:30 AM", "4 PM" -> minutes from midnight; None when no time."""
    m = CLOCK_RX.search(str(t or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3):
        h = h % 12 + (12 if m.group(3).lower() == "pm" else 0)
    return h * 60 + mi if h < 24 and mi < 60 else None


def w_project_cards(sec, ctx):
    """Coloured project / team cards in a row (the Jiron shot): the people on it as an avatar stack with a count, a
    title, a one-line description, a progress bar along the bottom. items: title, text, meta = people's names,
    badge = how many people, value = progress %."""
    cards = []
    for k, i in enumerate(items(sec, 6)):
        people = [str(m) for m in (i.get("meta") or []) if str(m).strip()][:3] or ["A", "B"]
        stack = "".join(f'<span class="m42-pc-av" style="--k:{n}">{e(initials(m))}</span>' for n, m in enumerate(people))
        count = i.get("badge") or (str(len(i.get("meta") or [])) if i.get("meta") else "")
        pct = max(0.0, min(100.0, num(i.get("value"), 40)))
        cards.append(f'<div class="m42-pc" style="--c:{TONES[k % 4]};--on:{ONS[k % 4]}"><div class="m42-pc-top"><span class="m42-pc-stack">{stack}'
                     + (f'<em>{e(count)}</em>' if count else "")
                     + f'</span><button type="button" class="m42-pc-more" aria-label="More on {e(i.get("title"))}" '
                     f'data-m42-toast="{e(i.get("title"))}" data-kind="info"><i class="bi bi-three-dots-vertical"></i></button></div>'
                     f'<b>{e(i.get("title"))}</b><small>{e(i.get("text") or "")}</small>'
                     f'<div class="m42-pc-bar" role="progressbar" aria-label="{e(i.get("title"))} progress" aria-valuenow="{pct:.0f}" '
                     f'aria-valuemin="0" aria-valuemax="100"><i style="width:{pct:.0f}%"></i></div></div>')
    return head(sec) + f'<div class="m42-pcs" style="--n:{max(1, len(cards))}">{"".join(cards)}</div>'


def w_week_schedule(sec, ctx):
    """A week planner (the Jiron shot): the days across, the hours down, each event a coloured block from its start
    to its end on its day, today's column shaded, a line at the current time, Month / Day / Week tabs.
    labels = the days ("Monday 09.08"), items = events: title, text = "09:30 - 10:30", group = its day, icon, badge
    (people on it)."""
    days = [str(x) for x in (sec.get("labels") or []) if str(x).strip()][:7] or \
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    evs = []
    for k, i in enumerate(items(sec, 14)):
        times = [t for t in (_minutes(x) for x in re.split(r"\s*[-–to]+\s*", str(i.get("text") or ""))) if t is not None]
        start = times[0] if times else 8 * 60 + 30 + 60 * (k % 4)
        end = times[1] if len(times) > 1 and times[1] > start else start + 60
        g = str(i.get("group") or "").lower()
        day = next((n for n, d in enumerate(days) if g and (d.lower().startswith(g[:3]) or g in d.lower())), k % len(days))
        evs.append((day, start, end, k, i))
    lo = (min(e[1] for e in evs) // 30 * 30) if evs else 8 * 60
    hi = (max(e[2] for e in evs) + 29) // 30 * 30 if evs else 12 * 60
    lo, hi = min(lo, 8 * 60 + 30), max(hi, lo + 150)
    slots = (hi - lo) // 30
    today = datetime.date.today().weekday()
    tcol = today if today < len(days) else -1
    head_cells = "".join(f'<div class="m42-ws-day{" is-today" if n == tcol else ""}" style="grid-column:{n + 2}">'
                         f'<b>{e(d.split()[0])}</b><small>{e(" ".join(d.split()[1:]))}</small></div>' for n, d in enumerate(days))
    times = "".join(f'<div class="m42-ws-time" style="grid-row:{r + 2}">{(lo + 30 * r) // 60:02d}:{(lo + 30 * r) % 60:02d}</div>'
                    for r in range(0, slots, 1))
    shade = (f'<div class="m42-ws-today" style="grid-column:{tcol + 2};grid-row:1 / span {slots + 1}"></div>' if tcol >= 0 else "")
    blocks = ""
    for day, start, end, k, i in evs:
        r0 = (start - lo) // 30 + 2
        span = max(1, (end - start + 29) // 30)
        tone = TONES[k % 4]
        blocks += (f'<div class="m42-ws-ev" style="grid-column:{day + 2};grid-row:{r0} / span {span};--c:{tone};--on:{ONS[k % 4]}" '
                   f'title="{e(i.get("title"))} · {e(i.get("text") or "")}">'
                   f'<span class="m42-ws-top"><i class="bi {ic(i.get("icon"), "bi-calendar-event")}"></i>'
                   + (f'<em>{e(i.get("badge"))}</em>' if i.get("badge") else "")
                   + f'</span><b>{e(i.get("title"))}</b><small>{e(i.get("text") or "")}</small></div>')
    now = datetime.datetime.now()
    nm = now.hour * 60 + now.minute
    line = (f'<div class="m42-ws-now" style="grid-column:2 / span {len(days)};grid-row:{(nm - lo) // 30 + 2};'
            f'--y:{(nm - lo) % 30 / 30:.2f}"></div>' if lo <= nm < hi else "")
    tabs = "".join(f'<button type="button" class="m42-ws-tab{" is-on" if t == "Week" else ""}" data-m42-pick="{e(ctx and _pb().slug("ws", ctx["ids"]) or "ws")}">'
                   f'{t}</button>' for t in ("Month", "Day", "Week"))
    return (head(sec) + f'<div class="m42-ws-tabs" role="group" aria-label="Range">{tabs}</div>'
            f'<div class="m42-ws-scroll"><div class="m42-ws" style="--days:{len(days)};--slots:{slots}">'
            f'{shade}{head_cells}{times}{line}{blocks}</div></div>')


def _cal_grid(year, month, marks, today, icon_of=None):
    """The month drawn by M42 itself too (the page's script redraws it on ‹ ›): it reads without JavaScript."""
    icon_of = icon_of or {}
    cells = "".join(f"<span class=\"dow\">{d}</span>" for d in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"))
    for week in calendar.Calendar().monthdayscalendar(year, month):
        for d in week:
            if d in marks and icon_of.get(d):
                k = marks.index(d) % 4
                cells += f'<span class="mark has-icon t{k}" title="{d}" aria-label="{d}"><i class="bi {icon_of[d]}"></i></span>'
                continue
            cls = "mark" if d in marks else "today" if d == today else ""
            cells += f'<span class="{cls}">{d or ""}</span>'
    return cells


def w_agenda(sec, ctx):
    rows = "".join(f'<li style="--c:{TONES[k % 6]}"><div><small>{e(i.get("group") or (i.get("meta") or [""])[0])}</small>'
                   f'<b>{e(i.get("title"))}</b></div><span>{e(i.get("text"))}</span></li>' for k, i in enumerate(items(sec, 6)))
    return head(sec) + f'<ul class="m42-w-agenda">{rows}</ul>'


def w_timeline(sec, ctx):
    rows = "".join(f'<li><i class="bi {ic(i.get("icon"), "bi-dot")}"></i><div><b>{e(i.get("title"))}</b><p>{e(i.get("text"))}</p>'
                   f'<small>{e((i.get("meta") or [""])[0])}</small></div></li>' for i in items(sec, 8))
    return head(sec) + f'<ul class="m42-w-timeline">{rows}</ul>'


def w_task_list(sec, ctx):
    pb = _pb()
    lid = pb.slug((sec.get("title") or "tasks") + "-list", ctx["ids"])
    rows = "".join(_task_row(i, f"{lid}-{n}") for n, i in enumerate(items(sec, 8)))
    return (head(sec) + f'<form class="m42-w-taskadd" data-m42-taskadd="{lid}"><input class="form-control" placeholder="Add a task" '
            f'aria-label="New task" required><button class="m42-btn" type="submit" aria-label="Add task"><i class="bi bi-plus-lg"></i></button></form>'
            f'<ul class="m42-w-tasks" id="{lid}">{rows}</ul>')


def _task_row(i, tid):
    done = re.search(r"done|complete|finished|yes", str(i.get("badge") or ""), re.I)
    return (f'<li><input class="form-check-input" type="checkbox" id="{tid}"{" checked" if done else ""}>'
            f'<label for="{tid}"><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></label>'
            '<button type="button" class="m42-icon-btn sm" data-m42-edit aria-label="Edit"><i class="bi bi-pencil-square"></i></button>'
            '<button type="button" class="m42-icon-btn sm" data-m42-remove aria-label="Delete"><i class="bi bi-trash3"></i></button></li>')


def w_task_cards(sec, ctx):
    cards = []
    for k, i in enumerate(items(sec, 4)):
        metas = "".join(f'<span><i class="bi {ic(_meta_icon(m), "bi-dot")}"></i>{e(m)}</span>' for m in i.get("meta") or [])
        prog = num(i.get("value"), -1)
        cards.append(f'<div class="m42-w-taskcard"><div class="d-flex justify-content-between gap-2"><b><i class="bi {ic(i.get("icon"), "bi-check2-square")}"></i> '
                     f'{e(i.get("title"))}</b>{badge(i["badge"]) if i.get("badge") else ""}</div><div class="m42-w-metas">{metas}</div>'
                     + (f'<div class="m42-w-track mt-2"><i style="width:{max(0, min(100, prog)):.0f}%"></i></div>' if prog >= 0 else "")
                     + '<div class="d-flex gap-2 mt-3"><button type="button" class="m42-btn-ghost" data-m42-toggle-text="Resume|Pause">Pause</button>'
                     '<button type="button" class="m42-btn" data-m42-done>Complete</button></div></div>')
    return head(sec) + f'<div class="m42-w-taskcards">{"".join(cards)}</div>'


def _meta_icon(text):
    t = str(text).lower()
    for rx, name in ((r"due|time|est|\d+:\d+|am|pm|min|hour|\bh\b", "bi-clock"), (r"floor|zone|room|place|location|address|city", "bi-geo-alt"),
                     (r"by |owner|assign|person|staff|@", "bi-person"), (r"equip|machine|tool|station", "bi-gear"),
                     (r"date|day|mon|tue|wed|thu|fri|sat|sun|\d+/\d+", "bi-calendar3"), (r"₹|\$|price|cost|amount", "bi-cash")):
        if re.search(rx, t):
            return name
    return "bi-dot"


def w_progress_list(sec, ctx):
    rows = "".join(f'<li><span class="m42-w-thumb" style="--t:{TINTS[k % 3]}"><i class="bi {ic(i.get("icon"), "bi-journal")}"></i></span>'
                   f'<div><b>{e(i.get("title"))}</b><small>' + " ".join(f'<span class="me-2"><i class="bi {_meta_icon(m)}"></i> {e(m)}</span>' for m in (i.get("meta") or [])[:2])
                   + f'</small></div>{_ring(i.get("value"), TONES[k % 6], 46, 5)}</li>' for k, i in enumerate(items(sec, 6)))
    return head(sec) + f'<ul class="m42-w-plist">{rows}</ul>'


def thumb_icon(i, sec):
    """A row's picture when the plan named no icon: from what the row says ("Heavy Rain" -> a rain cloud, a real run
    showed a picture placeholder for each city), else from the card's title, else a picture."""
    for t in (i.get("text"), i.get("badge"), i.get("title"), sec.get("title"), sec.get("eyebrow")):
        icon = webkit_icon(t) if t else "bi-graph-up"
        if icon != "bi-graph-up":
            return icon
    return "bi-image"


def look(sec):
    """How the reference card is drawn inside (designref.clean_card: header, progress, bars, boxes, pills, photos)."""
    return sec.get("_look") or {}


def bar_pct(i):
    """How full an item's bar is: its "75%" badge, a % value, else None."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(i.get("badge") or "") + " " + str(i.get("text") or ""))
    if m:
        return min(100.0, float(m.group(1)))
    if (i.get("unit") or "").strip() == "%" and i.get("value") not in (None, ""):
        return max(0.0, min(100.0, num(i.get("value"))))
    return None


ROW_PARTS = {"list_thumbs", "notifications", "progress_list", "task_list", "task_cards", "agenda", "timeline", "review_list",
             "leaderboard", "files", "image_cards", "world_list", "switch_list"}


def w_template_rows(sec, ctx):
    """A list card drawn from the reference's own row template (designref.clean_item: the parts of one item, left to
    right): the D.CC "Recent activity" row is a picture, "Status changed", "#4587 · Wait 9 min", a Completed pill;
    the Stores card is pictures with the words on them. Pictures are coloured icon tiles (the user's choice)."""
    row = look(sec).get("row") or []
    out = []
    for k, i in enumerate(items(sec, 8)):
        tint = TINTS[k % 3]
        icon = ic(i.get("icon"), thumb_icon(i, sec))
        meta = [str(m) for m in (i.get("meta") or []) if str(m).strip()][:3]
        if "photo with words on it" in row:  # a picture card with its words on it (Stores: "Xianxo Store", a place, Open)
            out.append(f'<a class="m42-w-ovl" href="#" style="--t:{tint}"><i class="bi {icon} m42-w-ovl-art"></i>'
                       + (f'<span class="m42-w-ovl-pill">{badge(i["badge"])}</span>' if i.get("badge") else "")
                       + f'<b>{e(i.get("title"))}</b>'
                       + (f'<small><i class="bi bi-geo-alt"></i> {e(i.get("text") or (meta or [""])[0])}</small>' if i.get("text") or meta else "")
                       + "</a>")
            continue
        words, side = [], []
        for part in row:
            if part in ("photo", "icon"):
                side.append(("lead", f'<span class="m42-w-thumb{" is-photo" if part == "photo" else ""}" style="--t:{tint}"><i class="bi {icon}"></i></span>'))
            elif part == "avatar":
                side.append(("lead", f'<span class="m42-w-av" style="--t:{tint}">{e(initials(i.get("title")))}</span>'))
            elif part == "title":
                words.append(f'<b>{e(i.get("title"))}</b>')
            elif part == "text" and i.get("text"):
                words.append(f'<small>{e(i.get("text"))}</small>')
            elif part == "meta" and (meta or i.get("text")):
                facts = meta or [i.get("text")]
                words.append('<span class="m42-w-facts">' + "".join(f'<span><i class="bi {_meta_icon(m) if _meta_icon(m) != "bi-dot" else "bi-dot"}"></i>{e(m)}</span>'
                                                                   for m in facts) + "</span>")
            elif part in ("number", "price") and i.get("value") not in (None, ""):
                side.append(("end", f'<b class="m42-w-end">{amount(i.get("value"), i.get("unit") or "") if part == "price" or (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value"))) + e(i.get("unit") or "")}</b>'))
            elif part == "pill" and i.get("badge"):
                side.append(("end", badge(i["badge"])))
            elif part == "progress bar" and i.get("value") not in (None, ""):
                side.append(("end", f'<div class="m42-w-track" style="width:90px"><i style="width:{max(0, min(100, num(i.get("value")))):.0f}%"></i></div>'))
            elif part == "ring" and i.get("value") not in (None, ""):
                side.append(("end", _ring(i.get("value"), TONES[k % 3], 46, 5)))
            elif part == "stars" and i.get("value") not in (None, ""):
                n = int(round(max(0, min(5, num(i.get("value"))))))
                side.append(("end", f'<span class="m42-w-stars">{"★" * n}{"☆" * (5 - n)}</span>'))
            elif part in ("button", "arrow"):
                side.append(("end", '<span class="m42-w-chev"><i class="bi bi-chevron-right"></i></span>'))
            elif part == "stepper":  # - 1 + (a cart row)
                side.append(("end", f'<span class="m42-w-qty" data-m42-qty><button type="button" data-q="-1" aria-label="Less">−</button>'
                                    f'<b>{e(next((m for m in meta if m.strip().isdigit()), "1"))}</b>'
                                    '<button type="button" data-q="1" aria-label="More">+</button></span>'))
            elif part == "checkbox":  # ticked when the item is done (a task list)
                done = bool(re.search(r"done|complete|finished|✓", str(i.get("badge") or ""), re.I))
                side.append(("lead", f'<input type="checkbox" class="form-check-input m42-w-check" aria-label="{e(i.get("title"))} done"'
                                     f'{" checked" if done else ""}>'))
            elif part == "edit":
                side.append(("end", f'<button type="button" class="m42-w-del" aria-label="Edit {e(i.get("title"))}" data-m42-toast="Editing: '
                                    f'{e(i.get("title"))}" data-kind="info"><i class="bi bi-pencil-square"></i></button>'))
            elif part == "delete":
                side.append(("end", '<button type="button" class="m42-w-del" aria-label="Remove" data-m42-remove><i class="bi bi-trash3"></i></button>'))
        lead = "".join(h for where, h in side if where == "lead")
        end = "".join(h for where, h in side if where == "end")
        out.append(f'<div class="m42-w-trow" style="--t:{tint}">{lead}<div class="m42-w-twords">{"".join(words) or "<b>" + e(i.get("title")) + "</b>"}</div>'
                   + (f'<div class="m42-w-tend">{end}</div>' if end else "") + "</div>")
    cls = "m42-w-ovls" if "photo with words on it" in row else "m42-w-trows"
    return head(sec) + f'<div class="{cls}">{"".join(out)}</div>'


def w_list_thumbs(sec, ctx):
    lk = look(sec)
    rows = "".join(f'<a class="m42-w-lt" href="#" data-m42-open style="--t:{TINTS[k % 3]}"><span class="m42-w-thumb{" is-photo" if lk.get("photos") else ""}"><i class="bi {ic(i.get("icon"), thumb_icon(i, sec))}"></i></span>'
                   f'<div><b>{e(i.get("title"))}</b><small>{e(i.get("text") or " · ".join(i.get("meta") or []))}</small></div>'
                   + (f'<span class="m42-w-end">{amount(i.get("value"), i.get("unit") or "")}</span>' if i.get("value") not in (None, "") else "")
                   + (badge(i["badge"]) if lk.get("pills") and i.get("badge") else "")
                   + '<i class="bi bi-chevron-right m42-w-chev"></i></a>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-lts">{rows}</div>'


def w_avatars(sec, ctx):
    people = "".join(f'<div class="m42-w-person"><span class="m42-w-av" style="--t:{TINTS[k % 3]}">{e(initials(i.get("title")))}</span>'
                     f'<small>{e(i.get("title"))}</small></div>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-people">{people}</div>'


def w_profile(sec, ctx):
    its = items(sec)
    me = its[0] if its else {"title": "Guest"}
    info = "".join(f'<div><small>{e(i.get("title"))}</small><b>{e(i.get("text") or fmt(i.get("value")))}</b></div>' for i in its[1:5])
    return (f'<div class="m42-w-profile"><span class="m42-w-av lg">{e(initials(me.get("title")))}</span><div><b>{e(me.get("title"))}</b>'
            f'<small>{e(me.get("text"))}</small></div><div class="m42-w-info">{info}</div>'
            + (f'<button type="button" class="m42-btn-ghost ms-auto" data-m42-toast="{e(sec.get("button"))}: done">'
               f'<i class="bi bi-download"></i> {e(sec.get("button"))}</button>' if sec.get("button") else "") + "</div>")


def w_status_card(sec, ctx):
    its = items(sec)
    st = (its[0].get("badge") if its else "") or sec.get("eyebrow") or "Operational"
    lines = "".join(f'<p>{e(i.get("title"))}{(" · " + e(i.get("text"))) if i.get("text") else ""}</p>' for i in its[:3])
    faces = "".join(f'<span>{e(initials(t))}</span>' for t in (its[0].get("tags") if its else []) or [])
    return (f'<div class="m42-w-status"><h3>{e(sec.get("title") or "Status")}</h3>{badge(st)}{lines}'
            + (f'<div class="m42-avatars mt-2">{faces}</div>' if faces else "") + "</div>")


def w_badges(sec, ctx):
    cards = "".join(f'<div class="m42-w-badgecard"><span class="m42-w-thumb" style="--t:{TINTS[k % 3]}"><i class="bi {ic(i.get("icon"), "bi-award")}"></i></span>'
                    f'<div class="flex-grow-1"><b>{e(i.get("title"))}</b><div class="d-flex align-items-center gap-2"><small>{e(fmt(i.get("value")))}%</small>'
                    f'<div class="m42-w-track flex-grow-1"><i style="width:{max(0, min(100, num(i.get("value")))):.0f}%"></i></div></div>'
                    f'<small class="m42-muted">{e(i.get("text"))}</small></div>{badge(i["badge"]) if i.get("badge") else ""}</div>'
                    for k, i in enumerate(items(sec, 6)))
    return head(sec) + f'<div class="m42-w-badges">{cards}</div>'


def w_review_list(sec, ctx):
    rows = []
    for k, i in enumerate(items(sec, 5)):
        stars = int(round(max(1, min(5, num(i.get("value"), 5)))))
        rows.append(f'<li><span class="m42-w-av" style="--t:{TINTS[k % 3]}">{e(initials(i.get("title")))}</span><div class="flex-grow-1">'
                    f'<div class="d-flex justify-content-between"><b>{e(i.get("title"))}</b><span class="m42-stars">{"★" * stars}'
                    f'<span class="m42-muted">{"★" * (5 - stars)}</span></span></div><small class="m42-muted">{e((i.get("meta") or [""])[0])}</small>'
                    f'<p>{e(i.get("text"))}</p></div><div class="m42-w-acts"><button type="button" class="m42-icon-btn sm is-good" data-m42-approve '
                    f'aria-label="Approve"><i class="bi bi-check-lg"></i></button><button type="button" class="m42-icon-btn sm is-bad" '
                    f'data-m42-remove aria-label="Reject"><i class="bi bi-x-lg"></i></button></div></li>')
    return head(sec) + f'<ul class="m42-w-reviews">{"".join(rows)}</ul>'


def w_notifications(sec, ctx):
    lk = look(sec)
    rows = "".join(f'<li class="is-unread"><span class="m42-w-thumb{" is-photo" if lk.get("photos") else ""}" style="--t:{TINTS[k % 3]}">'
                   f'<i class="bi {ic(i.get("icon"), thumb_icon(i, sec) if lk.get("photos") else "bi-bell")}"></i></span>'
                   f'<div><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></div>'
                   + (badge(i["badge"]) if lk.get("pills") and i.get("badge") else f'<time>{e((i.get("meta") or [""])[0])}</time>') + "</li>"
                   for k, i in enumerate(items(sec, 6)))
    return (head(sec) + f'<ul class="m42-w-notes">{rows}</ul><button type="button" class="m42-btn-ghost w-100 mt-2" data-m42-readall>'
            '<i class="bi bi-check2-all"></i> Mark all as read</button>')


def w_kanban(sec, ctx):
    cols = [str(c) for c in (sec.get("labels") or [])][:4] or sorted({str(i.get("group") or "To do") for i in items(sec)})[:4]
    out = []
    for k, c in enumerate(cols):
        cards = "".join(f'<div class="m42-w-kcard"><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small>'
                        + (badge(i["badge"]) if i.get("badge") else "") + "</div>"
                        for i in items(sec) if str(i.get("group") or cols[0]) == c)
        out.append(f'<div class="m42-w-kcol" style="--c:{TONES[k % 6]}"><h4>{e(c)} <span>{cards.count("m42-w-kcard")}</span></h4>{cards}</div>')
    return head(sec) + f'<div class="m42-w-kanban">{"".join(out)}</div>'


def w_leaderboard(sec, ctx):
    its = sorted(items(sec, 8), key=lambda i: -num(i.get("value")))
    rows = "".join(f'<li><span class="m42-w-rank r{n}">{n}</span><span class="m42-w-av" style="--t:{TINTS[n % 3]}">{e(initials(i.get("title")))}</span>'
                   f'<div><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></div><b class="ms-auto">{e(fmt(i.get("value")))} {e(i.get("unit") or "")}</b></li>'
                   for n, i in enumerate(its, 1))
    return head(sec) + f'<ul class="m42-w-board">{rows}</ul>'


def w_heatmap(sec, ctx):
    rows = items(sec, 7)
    top = max([num(v) for i in rows for v in i.get("values") or []] + [1])
    grid = "".join(f'<div class="m42-w-hrow"><small>{e(i.get("title"))}</small>' + "".join(
        f'<i style="opacity:{.12 + .88 * num(v) / top:.2f}" title="{e(fmt(v))}"></i>' for v in (i.get("values") or [])[:24]) + "</div>" for i in rows)
    xl = "".join(f"<span>{e(l)}</span>" for l in (sec.get("labels") or [])[:24])
    return head(sec) + f'<div class="m42-w-heat">{grid}<div class="m42-w-hrow is-x"><small></small>{xl}</div></div>'


def w_files(sec, ctx):
    rows = "".join(f'<li><span class="m42-w-thumb" style="--t:{TINTS[k % 3]}"><i class="bi {ic(i.get("icon"), _file_icon(i.get("title")))}"></i></span>'
                   f'<div><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></div><button type="button" class="m42-icon-btn sm ms-auto" '
                   f'data-m42-toast="Downloading {e(i.get("title"))}" aria-label="Download"><i class="bi bi-download"></i></button></li>'
                   for k, i in enumerate(items(sec, 6)))
    return head(sec) + f'<ul class="m42-w-files">{rows}</ul>'


def _file_icon(name):
    ext = str(name or "").rsplit(".", 1)[-1].lower()
    return {"pdf": "bi-file-earmark-pdf", "xls": "bi-file-earmark-excel", "xlsx": "bi-file-earmark-excel", "csv": "bi-filetype-csv",
            "doc": "bi-file-earmark-word", "docx": "bi-file-earmark-word", "png": "bi-file-earmark-image", "jpg": "bi-file-earmark-image",
            "zip": "bi-file-earmark-zip"}.get(ext, "bi-file-earmark-text")


def w_chat(sec, ctx):
    pb = _pb()
    cid = pb.slug("chat", ctx["ids"])
    msgs = "".join(f'<div class="m42-w-msg{" is-me" if re.search(r"me|you|admin|staff", str(i.get("group") or ""), re.I) else ""}">'
                   f'<b>{e(i.get("title"))}</b><p>{e(i.get("text"))}</p><time>{e((i.get("meta") or [""])[0])}</time></div>' for i in items(sec, 8))
    return (head(sec) + f'<div class="m42-w-chat" id="{cid}">{msgs}</div><form class="m42-w-taskadd mt-2" data-m42-send="{cid}">'
            '<input class="form-control" placeholder="Type a message" aria-label="Message" required>'
            '<button class="m42-btn" type="submit" aria-label="Send"><i class="bi bi-send"></i></button></form>')


# ---- controls --------------------------------------------------------------------------------------------------

def w_stepper(sec, ctx):
    pb = _pb()
    sid = pb.slug("steps", ctx["ids"])
    its = items(sec, 6) or [{"title": "Step 1"}, {"title": "Step 2"}, {"title": "Step 3"}]
    heads = "".join(f'<li class="{"active" if n == 0 else ""}"><span>{n + 1}</span>{e(i.get("title"))}</li>' for n, i in enumerate(its))
    panes = "".join(f'<div class="m42-w-pane{" active" if n == 0 else ""}"><b>{e(i.get("title"))}</b><p>{e(i.get("text"))}</p></div>'
                    for n, i in enumerate(its))
    return (head(sec) + f'<div class="m42-w-stepper" id="{sid}" data-m42-stepper><ol>{heads}</ol>{panes}<div class="d-flex gap-2 justify-content-end mt-3">'
            '<button type="button" class="m42-btn-ghost" data-go="-1">Back</button><button type="button" class="m42-btn" data-go="1">Next '
            '<i class="bi bi-arrow-right"></i></button></div></div>')


def w_category_chips(sec, ctx):
    chips = "".join(f'<button type="button" class="m42-w-cat{" active" if k == 0 else ""}"><span><i class="bi {ic(i.get("icon"), "bi-tag")}"></i></span>'
                    f'{e(i.get("title"))}</button>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-cats m42-chips" data-single>{chips}</div>'


def photo(i, cls=""):
    """A downloaded photo (photos.py: images/<name>.jpg) for an item, or "" (then its icon is drawn)."""
    src = str(i.get("photo") or "")
    if not re.fullmatch(r"images/[\w.-]+\.jpg", src):
        return ""
    return f'<img class="{cls}" src="{e(src)}" alt="{e(i.get("title") or "")}" loading="lazy" decoding="async">'


def w_image_cards(sec, ctx):
    cards = "".join(f'<div class="m42-w-imgcard{" has-photo" if photo(i) else ""}" style="--t:{TINTS[k % 3]}"><button type="button" class="m42-w-like" data-m42-like aria-label="Like">'
                    f'<i class="bi bi-heart"></i></button>'
                    + (f'<div class="m42-w-art is-photo">{photo(i)}</div>' if photo(i) else f'<div class="m42-w-art"><i class="bi {ic(i.get("icon"), "bi-image")}"></i></div>')
                    + f'<b>{e(i.get("title"))}</b>' + (f'<small>{e(i.get("text"))}</small>' if i.get("text") else "")
                    + (f'<span class="m42-w-end">{amount(i.get("value"), i.get("unit") or "")}</span>' if i.get("value") not in (None, "") else "")
                    + "</div>" for k, i in enumerate(items(sec, 12)))
    return head(sec) + f'<div class="m42-w-imgcards">{cards}</div>'


def w_media_player(sec, ctx):
    its = items(sec, 6) or [{"title": "Track", "text": "Artist", "value": 215}]
    data = json.dumps([{"t": str(i.get("title") or ""), "a": str(i.get("text") or ""), "d": int(num(i.get("value"), 200))} for i in its])
    first = its[0]
    return (head(sec) + f'<div class="m42-w-player" data-m42-player=\'{e(data)}\'><div class="d-flex justify-content-between align-items-start">'
            f'<div><b data-p-title>{e(first.get("title"))}</b><small data-p-artist>{e(first.get("text"))}</small></div>'
            '<button type="button" class="m42-w-like" data-m42-like aria-label="Like"><i class="bi bi-heart"></i></button></div>'
            '<div class="m42-w-track my-2"><i data-p-bar style="width:0%"></i></div><div class="d-flex justify-content-between small m42-muted">'
            '<span data-p-now>0:00</span><span data-p-len></span></div><div class="m42-w-pctl"><button type="button" class="m42-icon-btn sm" data-p="shuffle" '
            'aria-label="Shuffle"><i class="bi bi-shuffle"></i></button><button type="button" class="m42-icon-btn" data-p="-1" aria-label="Previous">'
            '<i class="bi bi-skip-start-fill"></i></button><button type="button" class="m42-w-play" data-p="play" aria-label="Play">'
            '<i class="bi bi-play-fill"></i></button><button type="button" class="m42-icon-btn" data-p="1" aria-label="Next"><i class="bi bi-skip-end-fill">'
            '</i></button><button type="button" class="m42-icon-btn sm" data-p="repeat" aria-label="Repeat"><i class="bi bi-repeat"></i></button></div></div>')


def w_device_cards(sec, ctx):
    pb = _pb()
    cards = []
    for k, i in enumerate(items(sec, 8)):
        on = not re.search(r"off|idle|inactive|no", str(i.get("badge") or "on"), re.I)
        sid = pb.slug((i.get("title") or "device") + "-sw", ctx["ids"])
        cards.append(f'<div class="m42-w-device{"" if on else " is-off"}"><div class="d-flex justify-content-between align-items-start">'
                     f'<i class="bi {ic(i.get("icon"), "bi-lightning-charge")}"></i><div class="form-check form-switch m-0"><input class="form-check-input" '
                     f'type="checkbox" role="switch" id="{sid}" data-m42-device{" checked" if on else ""} aria-label="{e(i.get("title"))} on / off"></div></div>'
                     f'<b>{e(i.get("title"))}</b><small>{e(i.get("text") or ("On" if on else "Off"))}</small></div>')
    return head(sec) + f'<div class="m42-w-devices">{"".join(cards)}</div>'


def w_sliders(sec, ctx):
    pb = _pb()
    rows = []
    for i in items(sec, 5):
        sid = pb.slug((i.get("title") or "level") + "-range", ctx["ids"])
        v = max(0, min(100, num(i.get("value"), 50)))
        rows.append(f'<div class="m42-w-slider"><div class="d-flex justify-content-between"><label for="{sid}">{e(i.get("title"))}</label>'
                    f'<output data-for="{sid}">{v:g}{e(i.get("unit") or "")}</output></div><input type="range" class="form-range" id="{sid}" '
                    f'min="0" max="100" value="{v:g}" data-m42-range data-unit="{e(i.get("unit") or "")}"></div>')
    return head(sec) + "".join(rows)


TIME_RX = re.compile(r"^\s*\d{1,2}[:.]\d{2}\s*(am|pm)?\s*$", re.I)


def w_control_card(sec, ctx):
    """One device's controls in one card (the smart-home shot's "Air Conditioner": a dial with - / +, a row of modes,
    a from / to schedule; "Light Control": a bulb, colour modes, a brightness slider). items[0] is the main control:
    a temperature (unit °) is a dial, anything else a slider; items with a time in text are the schedule; the
    rest are the modes (badge "on" = the chosen one)."""
    its = items(sec, 10)
    main = next((i for i in its if i.get("value") not in (None, "") and not TIME_RX.match(str(i.get("text") or ""))), None)
    times = [i for i in its if TIME_RX.match(str(i.get("text") or ""))][:2]
    modes = [i for i in its if i is not main and i not in times][:5]
    pick = next((k for k, i in enumerate(modes) if re.search(r"^(on|active|selected)$", str(i.get("badge") or ""), re.I)), 0)
    chips = "".join(f'<button type="button" class="m42-w-mode{" active" if k == pick else ""}"><i class="bi {ic(i.get("icon"), webkit_icon(i.get("title")))}"></i>'
                    f'<small>{e(i.get("title"))}</small></button>' for k, i in enumerate(modes))
    dial = main and re.search(r"°|deg|temp|celsius|fahrenheit", str(main.get("unit") or "") + " " + str(main.get("title") or ""), re.I)
    if dial:
        left = w_gauge(dict(sec, title="", lead="", eyebrow="", items=[main]), ctx)
    elif main:
        left = (f'<div class="m42-w-ctl"><span class="m42-w-bulb"><i class="bi {ic(main.get("icon"), webkit_icon(main.get("title")) if webkit_icon(main.get("title")) != "bi-graph-up" else "bi-lightbulb")}"></i></span>'
                + w_sliders(dict(sec, title="", lead="", eyebrow="", items=[main]), ctx) + "</div>")
    else:
        left = ""
    right = ((f'<div><small class="m42-muted d-block mb-2">Modes</small><div class="m42-w-modes m42-chips" data-single>{chips}</div></div>' if chips else "")
             + (f'<div class="mt-3"><small class="m42-muted d-block mb-2">Schedule</small>'
                + w_time_range(dict(sec, title="", lead="", eyebrow="", items=[dict(t, title=t.get("title") or ("From", "To")[n]) for n, t in enumerate(times)]), ctx)
                + "</div>" if times else ""))
    return head(sec) + f'<div class="m42-w-control">{left}' + (f'<div class="m42-w-ctlside">{right}</div>' if right else "") + "</div>"


def w_mode_chips(sec, ctx):
    chips = "".join(f'<button type="button" class="m42-w-mode{" active" if k == 0 else ""}"><i class="bi {ic(i.get("icon"), "bi-circle")}"></i>'
                    f'<small>{e(i.get("title"))}</small></button>' for k, i in enumerate(items(sec, 6)))
    return head(sec) + f'<div class="m42-w-modes m42-chips" data-single>{chips}</div>'


def w_time_range(sec, ctx):
    pb = _pb()
    its = items(sec, 2) or [{"title": "From", "text": "09:00"}, {"title": "To", "text": "18:00"}]
    cells = []
    for i in its:
        sid = pb.slug((i.get("title") or "time") + "-t", ctx["ids"])
        t = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", str(i.get("text") or ""), re.I)
        hh = int(t.group(1)) % 12 + (12 if t and (t.group(3) or "").lower() == "pm" else 0) if t and t.group(3) else int(t.group(1)) if t else 9
        cells.append(f'<div><label class="form-label" for="{sid}">{e(i.get("title"))}</label><input class="form-control" type="time" id="{sid}" '
                     f'value="{hh:02d}:{t.group(2) if t else "00"}"></div>')
    return head(sec) + f'<div class="m42-w-times">{"".join(cells)}</div>'


def w_quantity(sec, ctx):
    rows = "".join(f'<div class="m42-w-qty"><span>{e(i.get("title"))}</span><div data-m42-qty data-price="{num(i.get("value"), 0):g}">'
                   f'<button type="button" class="m42-icon-btn sm" data-q="-1" aria-label="Less"><i class="bi bi-dash"></i></button>'
                   f'<b>{int(num((i.get("meta") or ["1"])[0], 1)) if (i.get("meta") or [""])[0].isdigit() else 1}</b>'
                   f'<button type="button" class="m42-icon-btn sm" data-q="1" aria-label="More"><i class="bi bi-plus"></i></button></div>'
                   + (f'<em data-q-total>{amount(i.get("value"), i.get("unit") or "")}</em>' if i.get("value") not in (None, "") else "")
                   + "</div>" for i in items(sec, 6))
    return head(sec) + f'<div class="m42-w-qtys">{rows}</div>'


def w_switch_list(sec, ctx):
    pb = _pb()
    rows = []
    for i in items(sec, 8):
        sid = pb.slug((i.get("title") or "setting") + "-sw", ctx["ids"])
        on = not re.search(r"off|no|disabled", str(i.get("badge") or "on"), re.I)
        rows.append(f'<li><div><label for="{sid}"><b>{e(i.get("title"))}</b></label><small>{e(i.get("text"))}</small></div>'
                    f'<div class="form-check form-switch m-0"><input class="form-check-input" type="checkbox" role="switch" id="{sid}" '
                    f'data-m42-setting{" checked" if on else ""}></div></li>')
    return head(sec) + f'<ul class="m42-w-switches">{"".join(rows)}</ul>'


def w_rating_input(sec, ctx):
    pb = _pb()
    rid = pb.slug("rating", ctx["ids"])
    stars = "".join(f'<input type="radio" name="{rid}" id="{rid}-{n}" value="{n}"><label for="{rid}-{n}" aria-label="{n} stars">★</label>'
                    for n in range(5, 0, -1))
    return (head(sec) + f'<form class="m42-form" data-m42-done="Thanks for the rating!"><div class="m42-w-stars">{stars}</div>'
            f'<label class="form-label" for="{rid}-t">Your words</label><textarea class="form-control" id="{rid}-t" rows="3"></textarea>'
            f'<button class="m42-btn w-100 mt-3">{e(sec.get("button") or "Send")}</button></form>')


def w_upload(sec, ctx):
    pb = _pb()
    uid = pb.slug("upload", ctx["ids"])
    return (head(sec) + f'<label class="m42-w-drop" for="{uid}"><i class="bi bi-cloud-arrow-up"></i><b>{e(sec.get("button") or "Drop files or browse")}</b>'
            f'<small>{e(sec.get("lead") or "PDF, JPG or PNG")}</small><input type="file" id="{uid}" multiple hidden data-m42-files></label>'
            '<ul class="m42-w-files mt-2" data-files-list></ul>')


def w_hourly(sec, ctx):
    cells = "".join(f'<div class="{"active" if n == 0 else ""}"><small>{e(i.get("title"))}</small><i class="bi {ic(i.get("icon"), "bi-cloud")}"></i>'
                    f'<b>{e(fmt(i.get("value")))}{e(i.get("unit") or "°")}</b></div>' for n, i in enumerate(items(sec, 12)))
    return head(sec) + f'<div class="m42-w-hourly">{cells}</div>'


def w_forecast(sec, ctx):
    cells = "".join(f'<div class="{"active" if n == 0 else ""}"><small>{e(i.get("title"))}</small><i class="bi {ic(i.get("icon"), "bi-sun")}"></i>'
                    f'<b>{e(fmt(i.get("value")))}°</b><span>{e((i.get("meta") or [""])[0])}</span></div>' for n, i in enumerate(items(sec, 12)))
    return head(sec) + f'<div class="m42-w-forecast">{cells}</div>'


def w_weather_now(sec, ctx):
    i = (items(sec) or [{"title": "Clear", "value": 28}])[0]
    chips = "".join(f'<span class="m42-w-pill">{e(m)}</span>' for m in (i.get("meta") or [])[:3])
    return (f'<div class="m42-w-now"><div><div class="m42-w-big">{e(fmt(i.get("value")))}<sup>{e(i.get("unit") or "°")}</sup></div>'
            f'<h3>{e(i.get("title"))}</h3><p>{e(i.get("text"))}</p><div class="d-flex gap-2">{chips}</div></div>'
            f'<i class="bi {ic(i.get("icon"), "bi-cloud-sun")} m42-w-nowicon"></i>'
            + (f'<div class="m42-w-note">{e(sec.get("lead"))}</div>' if sec.get("lead") else "") + "</div>")


def w_map_card(sec, ctx):
    pins = "".join(f'<span class="m42-w-pin" style="left:{18 + (k * 37) % 64}%;top:{24 + (k * 23) % 52}%" title="{e(i.get("title"))}">'
                   f'<i class="bi bi-geo-alt-fill"></i></span>' for k, i in enumerate(items(sec, 6)))
    places = "".join(f'<li><i class="bi bi-geo-alt"></i><b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></li>' for i in items(sec, 4))
    return head(sec) + f'<div class="m42-w-map">{pins}</div><ul class="m42-w-places">{places}</ul>'


def w_camera_feed(sec, ctx):
    """A security camera's live view (the smart-home shot's "Security"): a dark room scene, a REC dot, the room on a
    chip that switches cameras, the time, a full-screen button."""
    rooms = [i.get("title") for i in items(sec, 6) if i.get("title")] or ["Living Room"]
    return head(sec) + (f'<div class="m42-w-cam" data-m42-cam="{e("|".join(rooms))}"><span class="m42-w-rec"><i></i>REC</span>'
                        f'<button type="button" class="m42-w-camroom" aria-label="Switch camera"><span>{e(rooms[0])}</span>'
                        '<i class="bi bi-chevron-down"></i></button><span class="m42-w-camtime">--:--:--</span>'
                        '<button type="button" class="m42-w-camfull" aria-label="Full screen" data-m42-toast="Full screen view" data-kind="info">'
                        '<i class="bi bi-fullscreen"></i></button></div>')


def w_banner(sec, ctx):
    i = (items(sec) or [{}])[0]
    return (f'<div class="m42-w-banner"><div><h3>{e(sec.get("title"))}</h3><p>{e(sec.get("lead"))}</p>'
            + "".join(f'<small><i class="bi {_meta_icon(m) if _meta_icon(m) != "bi-dot" else "bi-info-circle"}"></i> {e(m)}</small>' for m in (i.get("meta") or [])[:2])
            + (f'<a class="m42-btn mt-2" href="#{e(ctx.get("first_id", ""))}">{e(sec.get("button"))}</a>' if sec.get("button") else "")
            + f'</div><i class="bi {ic(i.get("icon"), ctx.get("brand_icon") or "bi-stars")} m42-w-banicon"></i></div>')


def w_metric_pair(sec, ctx):
    cells = "".join(f'<div><b>{"—" if i.get("value") in (None, "") else amount(i.get("value"), i.get("unit") or "") if (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value")))}'
                    f'<small>{e("" if (i.get("unit") or "") in ("₹", "$") else i.get("unit") or "")}</small></b><span>{e(i.get("title"))}</span>'
                    + (f'<em class="{"up" if not str(i.get("badge")).startswith("-") else "down"}">{e(i.get("badge"))}</em>' if i.get("badge") else "")
                    + "</div>" for i in items(sec, 4))
    if look(sec).get("boxes"):
        cells = "".join(f'<a class="m42-w-statbox" href="#" style="--t:{TINTS[k % 3]}"><span>{e(i.get("title"))}</span>'
                        f'<b><i class="bi {ic(i.get("icon"), webkit_icon(i.get("title")))}"></i> '
                        f'{"—" if i.get("value") in (None, "") else amount(i.get("value"), i.get("unit") or "") if (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value")))}'
                        f'</b><i class="bi bi-arrow-up-right m42-w-go"></i></a>' for k, i in enumerate(items(sec, 4)))
        return head(sec) + f'<div class="m42-w-statboxes">{cells}</div>'
    return head(sec) + f'<div class="m42-w-pairs">{cells}</div>'


def w_kpi_tiles(sec, ctx):
    """Number tiles tinted in the page's colours in turn (Travelgo / ClothIQ style): value, label, icon, a trend
    chip (badge "+12%"), a note (text) and a progress bar when the value is a percent."""
    tiles = []
    if look(sec).get("progress"):  # the D.CC tiles: icon + name, the number at the right; "Total 57" and "75%"; a striped bar
        for k, i in enumerate(items(sec, 6)):
            p = bar_pct(i)
            val = amount(i.get("value"), i.get("unit")) if (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value")))
            tiles.append(f'<div class="m42-w-kpi is-bar" style="--t:{TINTS[k % 3]};--c:{TONES[k % 3]}">'
                         f'<div class="m42-w-krow"><span><i class="bi {ic(i.get("icon"), "bi-graph-up")}"></i> {e(i.get("title"))}</span><b>{val}</b></div>'
                         f'<div class="m42-w-krow"><small class="m42-muted">{e(i.get("text") or "")}</small>'
                         f'<strong>{e(i.get("badge") or "")}</strong></div>'
                         + (f'<div class="m42-w-track is-striped"><i style="width:{p:.0f}%"></i></div>' if p is not None else "") + "</div>")
        return head(sec) + f'<div class="m42-w-kpis">{"".join(tiles)}</div>'
    plain = bool(look(sec).get("plain"))
    for k, i in enumerate(items(sec, 6)):
        pct = (i.get("unit") or "").strip() == "%" and 0 <= num(i.get("value")) <= 100
        trend = str(i.get("badge") or "")
        if plain:  # the school shot's tiles: white, a small label with the trend pill beside it, the big number under
            down = trend.startswith("-") or "↓" in trend
            tiles.append(f'<div class="m42-w-kpi is-plain"><div class="d-flex justify-content-between align-items-center gap-2">'
                         f'<span>{e(i.get("title"))}</span>'
                         + (f'<em class="{"down" if down else "up"}"><i class="bi bi-arrow-{"down" if down else "up"}"></i> {e(trend.lstrip("+-↑↓ "))}</em>' if trend else "")
                         + f'</div><b>{amount(i.get("value"), i.get("unit")) if (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value")))}'
                         f'<small>{e("" if (i.get("unit") or "") in ("₹", "$") else i.get("unit") or "")}</small></b>'
                         + (f'<small class="m42-muted">{e(i.get("text"))}</small>' if i.get("text") else "") + "</div>")
            continue
        tiles.append(f'<div class="m42-w-kpi" style="--t:{TINTS[k % 3]};--c:{TONES[k % 3]}"><div class="d-flex justify-content-between align-items-start">'
                     f'<span>{e(i.get("title"))}</span><i class="bi {ic(i.get("icon"), "bi-graph-up")}"></i></div>'
                     f'<b>{amount(i.get("value"), i.get("unit")) if (i.get("unit") or "") in ("₹", "$") else e(fmt(i.get("value")))}'
                     f'<small>{e("" if (i.get("unit") or "") in ("₹", "$") else i.get("unit") or "")}</small></b>'
                     + (f'<div class="m42-w-track{" is-striped" if look(sec).get("progress") else ""}"><i style="width:{bar_pct(i):.0f}%"></i></div>'
                        if pct or (look(sec).get("progress") and bar_pct(i) is not None) else "")
                     + (f'<em class="{"down" if trend.startswith("-") or "↓" in trend else "up"}">{e(trend)}</em>' if trend else "")
                     + (f'<small class="m42-muted">{e(i.get("text"))}</small>' if i.get("text") else "") + "</div>")
    # the reference's tiles side by side in one row (4 in a narrow column wrapped to 3 + 1); on a phone 2 a row
    row = f' is-row" style="--n:{len(tiles)}' if 2 <= len(tiles) <= 5 and ctx.get("ref_grid") else ""
    return head(sec) + f'<div class="m42-w-kpis{row}">{"".join(tiles)}</div>'


def w_countdown(sec, ctx):
    i = (items(sec) or [{"title": "Starts in", "value": 86400}])[0]
    secs = int(num(i.get("value"), 86400))
    cells = "".join(f'<div><b data-cd="{k}">00</b><small>{k}</small></div>' for k in ("days", "hours", "mins", "secs"))
    return head(sec) + f'<div class="m42-w-count" data-m42-countdown="{secs}"><p>{e(i.get("title"))}</p><div>{cells}</div></div>'


def w_order_tracker(sec, ctx):
    its = items(sec, 6)
    done = max([n for n, i in enumerate(its) if re.search(r"done|complete|yes|delivered|shipped|packed", str(i.get("badge") or ""), re.I)] + [0])
    steps = "".join(f'<li class="{"done" if n <= done else ""}"><span><i class="bi {ic(i.get("icon"), "bi-check-lg" if n <= done else "bi-circle")}"></i></span>'
                    f'<b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></li>' for n, i in enumerate(its))
    pct = done / max(1, len(its) - 1) * 100
    return head(sec) + f'<ol class="m42-w-track-steps" style="--p:{pct:.0f}%">{steps}</ol>'


def w_invoice(sec, ctx):
    """A bill being made (screenparts.RULES["invoice"]): the customer, lines with qty steppers and a remove, subtotal,
    GST, the total big, the payment method as three toggles and Pay full width; the steppers change the totals live."""
    its = items(sec, 10)
    rows, sub = "", 0
    for k, i in enumerate(its):
        m0 = str((i.get("meta") or ["1"])[0])
        q = num(m0, 1) if m0.replace(".", "").isdigit() else 1
        rate = num(i.get("value"))
        line = rate * q
        sub += line
        rows += (f'<li class="m42-inv-line" data-rate="{rate:g}"><span class="m42-inv-thumb" style="--t:{TINTS[k % 3]}">'
                 + (photo(i, "m42-inv-img") or f'<i class="bi {ic(i.get("icon"), "bi-bag")}"></i>')
                 + f'</span><div class="m42-inv-name"><b>{e(i.get("title"))}</b><small>{amount(rate, "₹")} each</small></div>'
                 f'<div class="m42-inv-qty"><button type="button" data-m42-inv-step="-1" aria-label="One less">−</button>'
                 f'<span data-m42-inv-q>{q:g}</span><button type="button" data-m42-inv-step="1" aria-label="One more">+</button></div>'
                 f'<b class="m42-inv-amt" data-m42-inv-amt>{amount(line, "₹")}</b>'
                 f'<button type="button" class="m42-inv-del" data-m42-inv-del aria-label="Remove {e(i.get("title"))}">×</button></li>')
    tax = round(sub * .18)
    pays = "".join(f'<label class="m42-inv-pay"><input type="radio" name="{e(sec.get("_id") or "inv")}-pay"{" checked" if n == 0 else ""}>'
                   f'<span><i class="bi {ic_}"></i>{e(t)}</span></label>'
                   for n, (t, ic_) in enumerate((("Cash", "bi-cash-stack"), ("Card", "bi-credit-card"), ("UPI", "bi-qr-code"))))
    return (f'<div class="m42-inv" data-m42-inv data-tax="0.18"><div class="m42-inv-head"><div><h3>{e(sec.get("title") or "Current bill")}</h3>'
            f'<small>{len(its)} items</small></div><button type="button" class="m42-inv-cust" data-m42-toast="Customer: walk-in" data-kind="info">'
            f'<i class="bi bi-person"></i> Walk-in customer</button></div>'
            f'<ul class="m42-inv-lines">{rows}</ul><div class="m42-inv-sum"><span>Subtotal</span><b data-m42-inv-sub>{amount(sub, "₹")}</b>'
            f'<span>GST 18%</span><b data-m42-inv-tax>{amount(tax, "₹")}</b></div>'
            f'<div class="m42-inv-total"><span>Total</span><b data-m42-inv-total>{amount(sub + tax, "₹")}</b></div>'
            f'<div class="m42-inv-pays">{pays}</div>'
            f'<button type="button" class="m42-btn m42-inv-go" data-m42-confirm="Take payment of {amount(sub + tax, "₹")}?">'
            f'<i class="bi bi-check2-circle"></i> {e(sec.get("button") or "Pay now")}</button></div>')


def w_world_list(sec, ctx):
    top = max([num(i.get("value")) for i in items(sec)] + [1])
    rows = "".join(f'<li><span class="m42-w-flag">{e(i.get("text") or initials(i.get("title")))}</span><b>{e(i.get("title"))}</b>'
                   f'<div class="m42-w-track flex-grow-1"><i style="width:{num(i.get("value")) / top * 100:.0f}%;background:{TONES[k % 6]}"></i></div>'
                   f'<small>{e(fmt(i.get("value")))}{e(i.get("unit") or "")}</small></li>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<ul class="m42-w-world">{rows}</ul>'


def w_quick_actions(sec, ctx):
    tiles = "".join(f'<button type="button" class="m42-w-qa" style="--t:{TINTS[k % 3]}" data-m42-toast="{e(i.get("title"))}: opened">'
                    f'<i class="bi {ic(i.get("icon"), "bi-lightning")}"></i><span>{e(i.get("title"))}</span></button>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-qas">{tiles}</div>'


def w_empty_state(sec, ctx):
    i = (items(sec) or [{}])[0]
    return (f'<div class="m42-w-empty"><i class="bi {ic(i.get("icon"), "bi-inbox")}"></i><h3>{e(sec.get("title") or "Nothing here yet")}</h3>'
            f'<p>{e(sec.get("lead"))}</p><button type="button" class="m42-btn" data-m42-toast="{e(sec.get("button") or "Created")}">'
            f'{e(sec.get("button") or "Create")}</button></div>')


def w_breadcrumb(sec, ctx):
    its = items(sec, 5)
    crumbs = "".join(f'<li class="breadcrumb-item{" active" if n == len(its) - 1 else ""}">'
                     + (e(i.get("title")) if n == len(its) - 1 else f'<a href="#">{e(i.get("title"))}</a>') + "</li>" for n, i in enumerate(its))
    return f'<nav aria-label="breadcrumb"><ol class="breadcrumb m-0">{crumbs}</ol></nav>'


def _modal(mid, title, fields, ctx, body=""):
    pb = _pb()
    inputs = "".join(pb.field_html(f, mid, ctx["ids"], "col-12") for f in fields)
    return (f'<div class="modal fade" id="{mid}" tabindex="-1" aria-labelledby="{mid}-t" aria-hidden="true"><div class="modal-dialog modal-dialog-centered">'
            f'<div class="modal-content m42-w-modal"><div class="modal-header"><h3 class="modal-title" id="{mid}-t">{e(title)}</h3>'
            f'<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>'
            f'<form class="m42-form" data-m42-done="Saved!" data-m42-closes><div class="modal-body"><div class="row g-3">{inputs}</div>{body}</div>'
            f'<div class="modal-footer"><button type="button" class="m42-btn-ghost" data-bs-dismiss="modal">Cancel</button>'
            f'<button class="m42-btn">Save</button></div></form></div></div></div>')


def w_modal(sec, ctx):
    """A button that opens a popup (a form from fields, else the items as rows)."""
    pb = _pb()
    mid = pb.slug((sec.get("button") or sec.get("title") or "popup") + "-modal", ctx["ids"])
    fields = sec.get("fields") or [pb._as_field(i) for i in items(sec, 5)] or [{"label": "Name", "type": "text"}]
    return (head(sec) + f'<button type="button" class="m42-btn" data-bs-toggle="modal" data-bs-target="#{mid}"><i class="bi bi-window-plus"></i> '
            f'{e(sec.get("button") or "Open")}</button>' + _modal(mid, sec.get("title") or sec.get("button") or "Details", fields, ctx))


def w_alerts(sec, ctx):
    """Buttons that show the page's messages: a toast, a confirm dialog, an alert (SweetAlert2)."""
    btns = []
    for i in items(sec, 4) or [{"title": "Save", "badge": "success"}]:
        kind = str(i.get("badge") or "success").lower()
        attr = (f'data-m42-confirm="{e(i.get("text") or "Are you sure?")}"' if re.search(r"confirm|delete|danger", kind)
                else f'data-m42-toast="{e(i.get("text") or i.get("title"))}" data-kind="{e(kind if kind in ("success", "warning", "error", "info") else "success")}"')
        btns.append(f'<button type="button" class="{"m42-btn" if not btns else "m42-btn-ghost"}" {attr}><i class="bi {ic(i.get("icon"), "bi-bell")}"></i> '
                    f'{e(i.get("title"))}</button>')
    return head(sec) + f'<div class="d-flex flex-wrap gap-2">{"".join(btns)}</div>'


def w_dropdown_filter(sec, ctx):
    pb = _pb()
    did = pb.slug("filter", ctx["ids"])
    opts = "".join(f'<li><button type="button" class="dropdown-item" data-m42-pick="{did}">{e(f)}</button></li>' for f in (sec.get("filters") or ["All"]))
    return (f'<div class="dropdown"><button class="m42-btn-ghost dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" id="{did}">'
            f'{e((sec.get("filters") or ["All"])[0])}</button><ul class="dropdown-menu">{opts}</ul></div>')


# ---- landing sections (the user's full-page landing shots, 2026-11-03) and app cards of the gap list ----------------

# landing sections drawn on the page itself, not in a card (a site page puts other widgets in a panel)
# a reference card that is not one of the widgets above (a recipe card: a round photo, its name, a grid of ingredient
# tiles, a button; a report: a date range, a donut, its legend; a promo banner filled with the main colour and a photo):
# the vision model lists its BLOCKS top to bottom (designref.card_schema) and this draws them, in the card's tone.
# (2026-11-12, the user: "any reference must come out as it is, not one fixed widget per card")
BLOCKS = ("heading", "big text", "text", "photo", "round photo", "cut-out person photo", "tile grid", "rows", "chips",
          "big number", "donut", "rings", "bars", "line chart", "legend", "progress bar", "date range", "month calendar",
          "button", "buttons", "meta", "search box", "form fields", "avatars", "table", "map", "upload box")
PHOTO_BLOCKS = {"photo", "round photo", "cut-out person photo"}


def _sec_photo(sec):
    src = str(sec.get("photo") or "")
    if re.fullmatch(r"images/[\w.-]+\.jpg", src):
        return src
    return next((str(i.get("photo")) for i in sec.get("items") or [] if re.fullmatch(r"images/[\w.-]+\.jpg", str(i.get("photo") or ""))), "")


def w_composed(sec, ctx):
    look = sec.get("_look") or {}
    blocks = [b for b in look.get("blocks") or [] if b in BLOCKS] or ["heading", "rows"]
    tone = look.get("tone") or "plain"
    its = items(sec, 12)
    pic = _sec_photo(sec)
    alt = e(sec.get("title") or "")
    out, k, used_chart = [], 0, False
    while k < len(blocks):
        b = blocks[k]
        nxt = blocks[k + 1] if k + 1 < len(blocks) else ""
        if b == "round photo" and nxt in ("heading", "big text"):  # a round photo beside the title (a recipe card's dish)
            img = f'<img class="m42-c-round" src="{e(pic)}" alt="{alt}" loading="lazy">' if pic else f'<span class="m42-c-round is-icon"><i class="bi {ic(sec.get("icon"), "bi-image")}"></i></span>'
            meta = " · ".join(e(m) for m in (sec.get("meta") or [])[:2]) or e(sec.get("lead") or "")
            out.append(f'<div class="m42-c-titlerow">{img}<div><h3>{e(sec.get("title"))}</h3>' + (f"<small>{meta}</small>" if meta else "") + "</div></div>")
            k += 2
            continue
        if b == "heading":
            out.append(f'<div class="m42-c-head"><h3>{e(sec.get("title"))}</h3>'
                       + (f'<span class="m42-c-date"><i class="bi bi-calendar3"></i> {e(sec.get("eyebrow"))}</span>' if sec.get("eyebrow") and "date range" in blocks else "")
                       + "</div>" + (f'<p class="m42-c-lead">{e(sec.get("lead"))}</p>' if sec.get("lead") and "text" not in blocks else ""))
        elif b == "big text":
            out.append(f'<h3 class="m42-c-big">{e(sec.get("title"))}</h3>')
        elif b == "text":
            out.append(f'<p class="m42-c-lead">{e(sec.get("lead"))}</p>' if sec.get("lead") else "")
        elif b in ("photo", "round photo"):
            if pic:
                out.append(f'<img class="{"m42-c-photo" if b == "photo" else "m42-c-round is-big"}" src="{e(pic)}" alt="{alt}" loading="lazy">')
        elif b == "cut-out person photo":
            if pic:
                out.append(f'<img class="m42-c-cutout" src="{e(pic)}" alt="{alt}" loading="lazy">')
        elif b == "tile grid":
            n = max(3, min(9, int(look.get("tiles") or 6)))
            shown, more = its[:n], len(its) - n
            if more > 0:
                shown = its[:n - 1]
            tiles = "".join(f'<div class="m42-c-tile">' + (photo(i, "m42-c-tileimg") or f'<i class="bi {ic(i.get("icon"), "bi-circle")}"></i>')
                            + f'<span>{e(i.get("title"))}</span></div>' for i in shown)
            if more > 0:
                tiles += f'<div class="m42-c-tile is-more"><b>+{more + 1} More</b></div>'
            out.append(f'<div class="m42-c-tiles">{tiles}</div>')
        elif b == "rows":
            out.append('<div class="m42-c-rows">' + "".join(
                '<div class="m42-c-row">' + (photo(i, "m42-c-rowimg") or f'<span class="m42-chip"><i class="bi {ic(i.get("icon"), "bi-dot")}"></i></span>')
                + f'<div><b>{e(i.get("title"))}</b>' + (f'<small>{e(i.get("text") or " · ".join(i.get("meta") or []))}</small>' if (i.get("text") or i.get("meta")) else "") + "</div>"
                + (f'<span class="m42-c-end">{amount(i.get("value"), i.get("unit") or "")}</span>' if i.get("value") not in (None, "") else "") + "</div>"
                for i in its[:6]) + "</div>")
        elif b == "chips":
            out.append('<div class="m42-c-chips">' + "".join(f'<span><i class="bi {ic(i.get("icon"), "bi-dot")}"></i>{e(i.get("title"))}</span>' for i in its[:8]) + "</div>")
        elif b == "big number":
            first = its[0] if its else {}
            out.append(f'<div class="m42-c-num"><b>{amount(first.get("value"), first.get("unit") or "")}</b><small>{e(first.get("title"))}</small></div>' if first else "")
        elif b in ("donut", "rings", "bars", "line chart", "month calendar", "table", "map", "upload box", "avatars") and not used_chart:
            w = {"donut": "donut", "rings": "rings", "bars": "bar_chart", "line chart": "line_chart", "month calendar": "calendar",
                 "table": "data_table", "map": "map_card", "upload box": "upload", "avatars": "avatars"}[b]
            used_chart = b in ("donut", "rings", "bars", "line chart")
            out.append(f'<div class="m42-c-widget">{WIDGETS[w](dict(sec, title="", lead="", eyebrow=""), ctx)}</div>')
        elif b == "legend" and not used_chart:
            out.append('<div class="m42-c-legend">' + "".join(f'<span><i style="--t:{TINTS[n % 3]}"></i>{e(i.get("title"))} <b>{amount(i.get("value"), i.get("unit") or "")}</b></span>'
                                                         for n, i in enumerate(its[:6])) + "</div>")
        elif b == "progress bar":
            first = its[0] if its else {}
            pct = max(0, min(100, num(first.get("value"), 60)))
            out.append(f'<div class="m42-c-progress"><i style="width:{pct:.0f}%"></i></div>')
        elif b == "date range" and "heading" not in blocks:
            out.append(f'<span class="m42-c-date"><i class="bi bi-calendar3"></i> {e(sec.get("eyebrow") or "This week")}</span>')
        elif b in ("button", "buttons"):
            label = sec.get("button") or "Open"
            meta = (sec.get("meta") or [])[:1]
            out.append('<div class="m42-c-actions">' + f'<button type="button" class="m42-btn m42-btn-sm"><i class="bi bi-play-circle-fill"></i> {e(label)}</button>'
                       + ('<button type="button" class="m42-btn-ghost m42-btn-sm">More</button>' if b == "buttons" else "")
                       + (f'<small><i class="bi bi-clock"></i> {e(meta[0])}</small>' if meta else "") + "</div>")
        elif b == "meta":
            m = sec.get("meta") or []
            if m and "button" not in blocks and "buttons" not in blocks:
                out.append('<div class="m42-c-meta">' + "".join(f"<span>{e(x)}</span>" for x in m[:3]) + "</div>")
        elif b == "search box":
            out.append('<label class="m42-topsearch w-100"><i class="bi bi-search"></i><input type="search" placeholder="Search…" aria-label="Search" data-m42-find></label>')
        elif b == "form fields":
            fl = sec.get("fields") or [{"label": "Name", "type": "text"}]
            out.append('<div class="m42-c-form">' + "".join(f'<input class="form-control" aria-label="{e(f.get("label"))}" placeholder="{e(f.get("label"))}">' for f in fl[:4]) + "</div>")
        k += 1
    cls = {"filled with the main colour": " is-filled", "tinted": " is-tinted", "photo background": " is-photo-bg"}.get(tone, "")
    side = " has-cutout" if "cut-out person photo" in blocks and pic else ""
    style = f' style="background-image:linear-gradient(90deg,rgba(0,0,0,.55),rgba(0,0,0,.15)),url({e(pic)})"' if tone == "photo background" and pic else ""
    return f'<div class="m42-composed{cls}{side}"{style}>' + "".join(out) + "</div>"


BARE = {"team", "logos", "blog_cards", "portfolio", "composed"}
OWN_BAND = {"video_band", "newsletter"}  # with their own title and words (the page's section head would take them)
SOCIAL = (("bi-facebook", "Facebook"), ("bi-twitter-x", "X"), ("bi-linkedin", "LinkedIn"), ("bi-instagram", "Instagram"))


def w_team(sec, ctx):
    cards = "".join(f'<div class="m42-w-member" style="--t:{TINTS[k % 3]}"><div class="m42-w-mphoto"><span>{e(initials(i.get("title")))}</span>'
                    f'<div class="m42-w-msocial">' + "".join(f'<a href="#" aria-label="{e(i.get("title"))} on {n}"><i class="bi {c}"></i></a>'
                                                             for c, n in SOCIAL[:3]) + '</div></div>'
                    f'<b>{e(i.get("title"))}</b><small>{e(i.get("text"))}</small></div>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-team">{cards}</div>'


def w_logos(sec, ctx):
    logos = "".join(f'<span class="m42-w-logo"><i class="bi {ic(i.get("icon"), ("bi-hexagon", "bi-triangle", "bi-circle-square", "bi-diamond", "bi-asterisk", "bi-octagon")[k % 6])}"></i>'
                    f'{e(i.get("title"))}</span>' for k, i in enumerate(items(sec, 8)))
    return head(sec) + f'<div class="m42-w-logos">{logos}</div>'


def w_blog_cards(sec, ctx):
    cards = []
    for k, i in enumerate(items(sec, 6)):
        meta = list(i.get("meta") or [])
        day, _, mon = str(meta[0] if meta else "").partition(" ")
        cards.append(f'<article class="m42-w-post" style="--t:{TINTS[k % 3]}"><div class="m42-w-pcover">'
                     + (photo(i) or f'<i class="bi {ic(i.get("icon"), thumb_icon(i, sec))}"></i>')
                     + (f'<span class="m42-w-pdate"><b>{e(day)}</b>{e(mon)}</span>' if day else "") + '</div><div class="m42-w-pbody">'
                     + (f'<small class="m42-w-ptag">{e(i.get("badge"))}</small>' if i.get("badge") else "")
                     + f'<h4>{e(i.get("title"))}</h4><p>{e(i.get("text"))}</p>'
                     f'<a href="#" class="m42-w-more" data-m42-toast="Opening: {e(i.get("title"))}">Read more <i class="bi bi-arrow-right"></i></a></div></article>')
    return head(sec) + f'<div class="m42-w-posts">{"".join(cards)}</div>'


def w_video_band(sec, ctx):
    return (f'<div class="m42-w-video"><div><small>{e(sec.get("eyebrow"))}</small><h2>{e(sec.get("title"))}</h2><p>{e(sec.get("lead"))}</p>'
            + (f'<a class="m42-btn" href="#">{e(sec.get("button"))}</a>' if sec.get("button") else "")
            + f'</div><button type="button" class="m42-w-play" data-m42-toast="The video plays here" aria-label="Play the video">'
            '<i class="bi bi-play-fill"></i></button></div>')


def w_newsletter(sec, ctx):
    return (f'<div class="m42-w-news"><div><h3>{e(sec.get("title") or "Stay in the loop")}</h3><p>{e(sec.get("lead"))}</p></div>'
            f'<form class="m42-form m42-w-newsform" data-m42-done="Subscribed: thank you!"><input type="email" class="form-control" required '
            f'placeholder="Your email address" aria-label="Email address"><button class="m42-btn" type="submit">{e(sec.get("button") or "Subscribe")}'
            '</button></form></div>')


def cover_icon(i, sec):
    return f'<i class="bi {ic(i.get("icon"), thumb_icon(i, sec))}"></i>'


def w_portfolio(sec, ctx):
    pb = _pb()
    lid = pb.slug("works", ctx["ids"])
    its = items(sec, 9)
    groups = list(dict.fromkeys(str(i.get("group") or i.get("badge") or "").strip() for i in its if (i.get("group") or i.get("badge"))))[:5]
    chips = ""
    if groups:
        chips = (f'<div class="m42-chips justify-content-center mb-3" data-single data-m42-filter-for="{lid}">'
                 '<button type="button" class="m42-chip-btn active" data-filter="all">All</button>'
                 + "".join(f'<button type="button" class="m42-chip-btn" data-filter="{e(g.lower())}">{e(g)}</button>' for g in groups) + "</div>")
    cards = "".join(f'<figure class="m42-w-work" data-tags="{e(str(i.get("group") or i.get("badge") or "").lower())}" style="--t:{TINTS[k % 3]}">'
                    f'<div class="m42-w-wcover">{photo(i) or cover_icon(i, sec)}</div>'
                    f'<figcaption><small>{e(i.get("group") or i.get("badge") or "")}</small><b>{e(i.get("title"))}</b></figcaption></figure>'
                    for k, i in enumerate(its))
    return head(sec) + chips + f'<div class="m42-w-works" id="{lid}">{cards}</div>'


def w_funnel(sec, ctx):
    its = items(sec, 6)
    top = max([num(i.get("value")) for i in its] + [1])
    rows = "".join(f'<li style="--w:{max(18, 100 * num(i.get("value")) / top):.0f}%;--c:{TONES[k % 6]}"><span class="m42-w-fbar">'
                   f'<b>{e(fmt(i.get("value")))}{e(i.get("unit") or "")}</b></span><small>{e(i.get("title"))}'
                   + (f' · {100 * num(i.get("value")) / num(its[0].get("value"), 1):.0f}%' if k and num(its[0].get("value")) else "")
                   + "</small></li>" for k, i in enumerate(its))
    return head(sec) + f'<ul class="m42-w-funnel">{rows}</ul>'


def w_gantt(sec, ctx):
    labels = [str(x) for x in (sec.get("labels") or [])][:12] or ["W1", "W2", "W3", "W4", "W5", "W6"]
    n = len(labels)
    rows = []
    for k, i in enumerate(items(sec, 8)):
        meta = [num(x) for x in (i.get("meta") or [])[:2]] or [k % n, 2]
        start = max(0, min(n - 1, int(meta[0]) if meta[0] < n else 0))
        span = max(1, min(n - start, int(meta[1]) if len(meta) > 1 and meta[1] else 2))
        done = max(0, min(100, num(i.get("value"))))
        rows.append(f'<div class="m42-w-grow"><small>{e(i.get("title"))}</small><div class="m42-w-gtrack" style="--n:{n}">'
                    f'<span class="m42-w-gbar" style="grid-column:{start + 1} / span {span};--c:{TONES[k % 6]}" title="{e(i.get("text") or "")}">'
                    f'<i style="width:{done:.0f}%"></i><em>{e(i.get("text") or (fmt(done) + "%"))}</em></span></div></div>')
    head_row = "".join(f"<span>{e(x)}</span>" for x in labels)
    return (head(sec) + f'<div class="m42-w-gantt"><div class="m42-w-grow is-x"><small></small><div class="m42-w-gtrack" style="--n:{n}">'
            f'{head_row}</div></div>{"".join(rows)}</div>')


def w_comments(sec, ctx):
    pb = _pb()
    cid = pb.slug("comments", ctx["ids"])
    rows = "".join(f'<li><span class="m42-w-av" style="--t:{TINTS[k % 3]}">{e(initials(i.get("title")))}</span><div><div class="d-flex gap-2 align-items-baseline">'
                   f'<b>{e(i.get("title"))}</b><time>{e((i.get("meta") or [""])[0])}</time></div><p>{e(i.get("text"))}</p>'
                   '<div class="m42-w-cacts"><button type="button" class="m42-w-like" data-m42-like aria-label="Like"><i class="bi bi-heart"></i></button>'
                   '<button type="button" class="m42-w-reply" data-m42-toast="Reply box opened"><i class="bi bi-reply"></i> Reply</button></div></div></li>'
                   for k, i in enumerate(items(sec, 6)))
    return (head(sec) + f'<ul class="m42-w-comments" id="{cid}">{rows}</ul><form class="m42-w-taskadd mt-2" data-m42-send="{cid}">'
            '<input class="form-control" placeholder="Write a comment" aria-label="Comment" required>'
            '<button class="m42-btn" type="submit" aria-label="Post"><i class="bi bi-send"></i></button></form>')


def w_integrations(sec, ctx):
    pb = _pb()
    cards = []
    for k, i in enumerate(items(sec, 8)):
        sid = pb.slug((i.get("title") or "app") + "-on", ctx["ids"])
        on = re.search(r"\bon\b|connected|active", str(i.get("badge") or ""), re.I)
        cards.append(f'<div class="m42-w-integ" style="--t:{TINTS[k % 3]}"><span class="m42-w-thumb"><i class="bi {ic(i.get("icon"), "bi-plug")}"></i></span>'
                     f'<div><label for="{sid}"><b>{e(i.get("title"))}</b></label><small>{e(i.get("text"))}</small></div>'
                     f'<div class="form-check form-switch m-0 ms-auto"><input class="form-check-input" type="checkbox" role="switch" id="{sid}" '
                     f'data-m42-setting{" checked" if on else ""}></div></div>')
    return head(sec) + f'<div class="m42-w-integs">{"".join(cards)}</div>'


WIDGETS = {"composed": w_composed, 
    "kpi_tiles": w_kpi_tiles, "line_chart": w_line_chart, "chart_stats": w_chart_stats, "area_chart": w_area_chart, "bar_chart": w_bar_chart, "hbars": w_hbars,
    "donut": w_donut, "rings": w_rings, "gauge": w_gauge, "data_table": w_data_table, "calendar": w_calendar, "agenda": w_agenda,
    "week_schedule": w_week_schedule, "project_cards": w_project_cards,
    "timeline": w_timeline, "task_list": w_task_list, "task_cards": w_task_cards, "progress_list": w_progress_list,
    "list_thumbs": w_list_thumbs, "avatars": w_avatars, "profile": w_profile, "status_card": w_status_card, "badges": w_badges,
    "review_list": w_review_list, "notifications": w_notifications, "kanban": w_kanban, "leaderboard": w_leaderboard,
    "heatmap": w_heatmap, "files": w_files, "chat": w_chat, "stepper": w_stepper, "category_chips": w_category_chips,
    "image_cards": w_image_cards, "media_player": w_media_player, "device_cards": w_device_cards, "sliders": w_sliders,
    "mode_chips": w_mode_chips, "control_card": w_control_card, "time_range": w_time_range, "quantity": w_quantity, "switch_list": w_switch_list,
    "rating_input": w_rating_input, "upload": w_upload, "hourly": w_hourly, "forecast": w_forecast, "weather_now": w_weather_now,
    "map_card": w_map_card, "camera_feed": w_camera_feed, "banner": w_banner, "metric_pair": w_metric_pair, "countdown": w_countdown,
    "order_tracker": w_order_tracker, "invoice": w_invoice, "world_list": w_world_list, "quick_actions": w_quick_actions,
    "empty_state": w_empty_state, "breadcrumb": w_breadcrumb, "modal": w_modal, "alerts": w_alerts,
    "dropdown_filter": w_dropdown_filter,
    "team": w_team, "logos": w_logos, "blog_cards": w_blog_cards, "video_band": w_video_band, "newsletter": w_newsletter,
    "portfolio": w_portfolio, "funnel": w_funnel, "gantt": w_gantt, "comments": w_comments, "integrations": w_integrations,
}

# what the chat model writes for each (only the notes of the parts a page uses go into its prompt)
NOTES = {"composed": "title, lead, eyebrow (a short label: a date range, a tag), button, meta = 1-2 small facts (a time, kcal), "
                         "photo words in lead; items = the card's tiles / rows / chips / chart parts: title, icon, value + unit", 
    "kpi_tiles": "items = tiles: title (label), value, unit (%, ₹, h...), icon, badge = trend (\"+12%\" / \"-5%\"), text = a small note",
    "line_chart": "labels = 6-12 x labels (months, days, hours); items = 1-3 series: title, values = 6-12 numbers (one per label), unit",
    "area_chart": "like line_chart",
    "chart_stats": "items[0] = the curve: title, values (6-12 numbers), badge (a status word), text (a change like \"23.8%\"); "
                   "items 1-4 = numbers under it: title, value, unit, icon", "bar_chart": "labels = 4-8 x labels; items = 1-3 series: title, values = one number per label",
    "hbars": "items = bars: title, value, unit", "donut": "items = 2-5 slices: title, value (the first is the centre's percent)",
    "rings": "items = 2-4: title, value (a percent)", "gauge": "items[0] = title, value, unit, meta = [\"min max\"]; items 1+ = modes: title, icon",
    "data_table": "labels = column names; items = rows: title (first cell), meta = the other cells, badge = status, value = amount; button = add label",
    "calendar": "labels = [\"Month YYYY\"]; taken = highlighted day numbers; items = events: title, text (time), icon (shown on its day)",
    "project_cards": "items = 3-4 projects / teams: title, text (one line about it), meta = 2-3 people's names, badge = how many people, value = progress %",
    "week_schedule": "labels = the 7 days (\"Monday 09.08\"); items = 6-12 events: title, text = \"09:30 - 10:30\", group = its day, icon, badge = people on it",
    "agenda": "items: title, text (time range), group (subject / tag)", "timeline": "items: title, text, meta = [time], icon",
    "task_list": "items: title, text (date), badge \"done\" for finished", "task_cards": "items: title, badge (priority), meta = 2-4 facts (place, person, due), value (progress %), icon",
    "progress_list": "items: title, meta = [duration, level], value (percent done), icon", "list_thumbs": "items: title, text, icon, value + unit",
    "avatars": "items = people: title (name), text (role)", "profile": "items[0] = person: title, text (role); items 1-4 = facts: title (label), text",
    "status_card": "items[0].badge = status word, items = lines: title, text; items[0].tags = initials of people",
    "badges": "items: title, value (percent), text, badge (Earned / Active), icon", "review_list": "items: title (person), text (review), value (stars 1-5), meta = [date]",
    "notifications": "items: title, text, meta = [time ago], icon", "kanban": "labels = column names; items: title, text, group (its column), badge",
    "leaderboard": "items: title (name), text, value (points), unit", "heatmap": "labels = column labels; items = rows: title, values (0-10 each)",
    "files": "items: title (file name with extension), text (size / date)", "chat": "items = messages: title (sender), text, meta = [time], group \"me\" for the user's own",
    "stepper": "items = steps: title, text", "category_chips": "items: title, icon", "image_cards": "items: title, text, icon, value + unit (price)",
    "media_player": "items = tracks: title, text (artist), value (seconds)", "device_cards": "items: title, icon, badge \"on\" / \"off\", text",
    "sliders": "items: title, value (0-100), unit", "mode_chips": "items: title, icon", "control_card": "items[0] = the main control: title, value, unit (\"°C\" = a dial, \"%\" = a slider), icon; then 2-5 modes: title, icon, badge \"on\" for the chosen one; then 0 or 2 schedule items: title From / To, text \"11:00 am\"", "time_range": "items = 2: title (From / To), text (\"11:00 am\")",
    "quantity": "items: title, value (unit price), unit, meta = [count]", "switch_list": "items: title, text, badge \"on\" / \"off\"",
    "rating_input": "button", "upload": "button, lead (allowed files)", "hourly": "items = hours: title (\"2 PM\"), icon, value, unit",
    "forecast": "items = days: title, icon, value (high), meta = [low]", "weather_now": "items[0]: title (condition), text, value, unit, icon, meta = [\"H 29°\", \"L 12°\"]",
    "map_card": "items = places: title, text", "camera_feed": "items = cameras: title (the room)", "banner": "title, lead, button; items[0]: icon, meta = 1-2 contact lines",
    "metric_pair": "items = 2-4 numbers: title, value, unit, badge (trend)", "countdown": "items[0]: title, value (seconds to go)",
    "order_tracker": "items = steps: title, text (time), badge \"done\" for the ones done", "invoice": "items = lines: title, value (rate), meta = [qty]; button",
    "world_list": "items: title (place), text (a flag emoji or code), value, unit", "quick_actions": "items: title, icon",
    "empty_state": "title, lead, button; items[0].icon", "breadcrumb": "items = path: title", "modal": "button (opens it), title, fields (its form)",
    "alerts": "items = buttons: title, text (the message), badge success / warning / error / confirm", "dropdown_filter": "filters = the options",
    "team": "items = 3-8 people: title (name), text (role)", "logos": "items = 4-8 partner / client names: title, icon",
    "blog_cards": "items = 3 posts: title, text (one line), meta = [\"28 Feb\"], badge (category), icon",
    "video_band": "eyebrow, title, lead, button (a dark band with a play button)", "newsletter": "title, lead, button",
    "portfolio": "items = 4-9 works: title, group (its category: the filter chips), icon",
    "funnel": "items = 3-6 stages, biggest first: title, value, unit", "gantt": "labels = 4-12 time columns (weeks / months); items = tasks: "
              "title, meta = [start column index from 0, columns it spans], value (percent done), text (who / dates)",
    "comments": "items = comments: title (person), text, meta = [time ago]",
    "integrations": "items = connected apps / services: title, text (what it does), icon, badge \"on\" / \"off\"",
}

# panel widths in an app (of 12): a chart wide, a calendar or a list narrow
WIDTH = {"week_schedule": 12, "project_cards": 12, "kpi_tiles": 12, "line_chart": 8, "area_chart": 8, "bar_chart": 8, "heatmap": 8, "data_table": 12, "kanban": 12, "hourly": 12,
         "forecast": 12, "weather_now": 8, "chart_stats": 4, "banner": 8, "invoice": 6, "profile": 12, "device_cards": 8, "control_card": 8, "image_cards": 8, "order_tracker": 12,
         "metric_pair": 6, "category_chips": 8, "chat": 6, "task_cards": 4, "stepper": 6, "badges": 8, "breadcrumb": 12,
         "team": 12, "logos": 12, "blog_cards": 12, "video_band": 12, "newsletter": 12, "portfolio": 12, "gantt": 12, "funnel": 6,
         "comments": 6, "integrations": 8}

# how each looks, for the vision model to name a reference card (designref.CARD_SCHEMA)
LOOKS = {
    "kpi_tiles": "one or more number tiles: a big number, a label, an icon, maybe a trend % or a bar",
    "line_chart": "a line chart (1-3 lines over months / days)",
    "chart_stats": "a line chart with 2-4 numbers with icons in a row under it (live conditions)", "area_chart": "a line chart filled below the line",
    "bar_chart": "vertical bars, often grouped by colour", "hbars": "horizontal progress bars with labels and numbers",
    "donut": "a ring split into coloured parts with a percent in the middle", "rings": "one or two ring gauges with percents",
    "gauge": "a round dial with a value in the middle and - / + buttons (thermostat)", "data_table": "a table with rows and columns",
    "calendar": "a month calendar grid of days", "agenda": "a list of events with times, coloured bars", "timeline": "events on a vertical line",
    "week_schedule": "a week planner: days across the top, hours down the side, coloured event blocks in the grid",
    "project_cards": "a row of coloured cards, each with a stack of round faces, a title, a line of text and a bar along its bottom",
    "task_list": "a list of tasks with checkboxes", "task_cards": "task cards with a priority badge, details and buttons",
    "progress_list": "a list of courses / items each with a small progress ring", "list_thumbs": "rows one under another, each: an icon or picture, a title and a line, a value or an arrow at the end",
    "avatars": "a row of round faces with names", "profile": "a person's photo and name with facts in a row", "status_card": "a status badge (Operational) with lines and faces",
    "badges": "achievement badges with progress bars", "review_list": "reviews with faces, stars and approve / reject buttons",
    "notifications": "a list of alerts with icons and times", "kanban": "columns of task cards", "leaderboard": "a ranked list of people with points",
    "heatmap": "a grid of coloured squares", "files": "a list of files to download", "chat": "chat bubbles and a message box",
    "stepper": "numbered steps (1 Step, 2 Step...)", "category_chips": "round chips with a flag / icon and a word", "image_cards": "colourful cards with a big round food / product picture",
    "media_player": "a music player: song, artist, progress, play buttons", "device_cards": "device cards with an icon and an on / off switch",
    "sliders": "a slider (brightness, volume)", "control_card": "one device's controls together: a dial (- / +) or a slider, a row of mode buttons (Cool, Turbo...), maybe a from / to schedule", "mode_chips": "small icon buttons to pick a mode (Turbo, Cool...)", "time_range": "two time boxes (from / to)",
    "quantity": "a - number + amount picker", "switch_list": "settings with on / off switches", "rating_input": "stars to rate and a text box",
    "upload": "a dashed box to drop files", "hourly": "hours side by side in one row, each: a time, an icon, a value",
    "forecast": "days side by side as columns, each: a day name, a weather icon, high / low",
    "weather_now": "a big temperature with the weather and a photo", "map_card": "a map with pins", "camera_feed": "a security camera's live picture of a room (a photo with a REC dot, a room name, full-screen)", "banner": "a wide coloured banner with a big message and a picture",
    "metric_pair": "two to four numbers side by side with labels", "countdown": "a countdown of days / hours / minutes", "order_tracker": "delivery steps on a line",
    "invoice": "an invoice with items and a total", "world_list": "countries / places with flags and bars", "quick_actions": "a grid of icon buttons",
    "empty_state": "an empty box with an icon and a create button", "breadcrumb": "a path like Home / Bookings", "modal": "a button that opens a form popup",
    "alerts": "buttons that show messages", "dropdown_filter": "a dropdown to filter",
    "team": "team member cards: a big photo, a name, a role, social icons", "logos": "a row of partner / client logos (grey)",
    "blog_cards": "blog / news cards: a picture with a date badge, a category, a title, read more",
    "video_band": "a wide dark photo band with a headline and a round play button",
    "newsletter": "a band with a title and an email box with a Subscribe button",
    "portfolio": "project pictures in a grid with filter chips above (All, Branding, Marketing...)",
    "funnel": "stacked bars getting narrower (visitors -> leads -> sales)", "gantt": "a timeline of task bars across weeks / months",
    "comments": "comments with faces, times, like / reply and a comment box",
    "integrations": "app / service tiles with logos and connect switches",
}


import appviews  # noqa: E402,F401  (chat_app, mail_app: whole app screens, registered into the tables above)
