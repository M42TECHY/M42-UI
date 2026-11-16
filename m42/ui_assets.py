"""💎 UI assets: the premium treatments of each component, chosen for the page's theme (the user, 2026-11-14: "for a
chart, 10-15 assets that make it premium; for a table the same, for the nav bar, the form, the meter... then which
assets suit our theme: that is all").

ASSETS[component][token] = {"what": what it does, "fits": the app-theme traits it suits (themes.APP_THEMES axes:
side, panel, table, kpi, frame, banner values, plus "dark" / "light")}. candidates(component, theme) ranks them by the
theme's traits; the 4B picks a few per component for the page (agent._pick_assets); the page gets them as tokens on
<html data-m42-a="..."> and bundled/m42-ui.css draws each token. Built in batches: chart + table first (2026-11-14); KPI, sidebar, button, form (2026-11-15)."""
import themes

ASSETS = {
    "chart": {
        "c-glow": {"what": "the line glows softly in its colour (a light trail)", "fits": {"dark", "glass", "mesh", "spark"}},
        "c-deepfill": {"what": "a deep gradient fill under the line, fading to nothing", "fits": {"soft", "tint", "gradient", "float"}},
        "c-thin": {"what": "a thin 2 px line, quiet and exact", "fits": {"line", "plain", "clean", "striped", "top"}},
        "c-darktip": {"what": "the value bubble as a dark card with white text", "fits": {"light", "soft", "line", "clean"}},
        "c-glasstip": {"what": "the value bubble as frosted glass", "fits": {"glass", "mesh", "dark"}},
        "c-dashgrid": {"what": "dashed, very light grid lines", "fits": {"line", "clean", "plain", "striped"}},
        "c-nogrid": {"what": "no grid at all, only the curve and its labels", "fits": {"soft", "float", "glass", "tint"}},
        "c-pillbars": {"what": "fully rounded capsule bars", "fits": {"soft", "tint", "float", "rows", "rail"}},
        "c-squarebars": {"what": "crisp bars with small corners", "fits": {"line", "plain", "striped", "top"}},
        "c-gradbars": {"what": "bars in a gradient of the accent, light at the top", "fits": {"gradient", "solid", "accent", "spark"}},
        "c-track": {"what": "each bar on a pale full-height track", "fits": {"soft", "tint", "rows", "light"}},
        "c-onebar": {"what": "all bars muted, the top one in the accent with its value", "fits": {"line", "clean", "soft", "plain", "solid"}},
        "c-pilllegend": {"what": "the legend as small pills with the colour dot", "fits": {"soft", "tint", "rows", "float"}},
        "c-mutedaxis": {"what": "small, muted, upper-case axis labels", "fits": {"line", "plain", "clean", "dark"}},
    },
    "table": {
        "t-softpill": {"what": "status as soft tinted pills with a dot", "fits": {"soft", "tint", "float", "rows", "light"}},
        "t-solidpill": {"what": "status as solid coloured pills with white text", "fits": {"solid", "accent", "gradient"}},
        "t-dotstatus": {"what": "status as a coloured dot and the word, no pill", "fits": {"line", "plain", "clean", "dark"}},
        "t-hairline": {"what": "hairline rules between rows, no fills", "fits": {"line", "clean", "plain", "top"}},
        "t-zebra": {"what": "every other row faintly tinted", "fits": {"striped", "plain", "top"}},
        "t-cardrows": {"what": "each row a rounded card with space between", "fits": {"rows", "soft", "float", "tint", "glass"}},
        "t-tinthead": {"what": "the header row on a tinted band with rounded ends", "fits": {"soft", "tint", "rows", "gradient"}},
        "t-capshead": {"what": "small upper-case, spaced header labels", "fits": {"line", "plain", "clean", "striped", "dark"}},
        "t-hoverlift": {"what": "a row lifts and glows on hover", "fits": {"rows", "soft", "float", "glass", "spark"}},
        "t-hoverbar": {"what": "a row gets an accent bar at its left on hover", "fits": {"line", "clean", "plain", "dark"}},
        "t-boldfirst": {"what": "the first cell bold, the others muted", "fits": {"line", "clean", "soft", "plain"}},
        "t-tabnum": {"what": "numbers in even (tabular) figures, right-aligned", "fits": {"line", "striped", "plain", "clean", "solid", "spark"}},
        "t-roomy": {"what": "taller rows, more air", "fits": {"soft", "float", "glass", "tint"}},
        "t-dense": {"what": "compact rows for many records", "fits": {"striped", "line", "top", "plain"}},
    },
    # batch 2 (2026-11-15): KPI tiles, the sidebar, buttons, form fields. A theme's own axes already shape them (kpi
    # plain / icon / spark / solid; side dark / rail / float...): these are finishing touches on top of it
    "kpi": {
        "k-bignum": {"what": "the number large and tight", "fits": {"plain", "line", "clean", "tint", "light"}},
        "k-gradnum": {"what": "the number in a gradient of the accent", "fits": {"gradient", "spark", "glass", "mesh", "dark"}},
        "k-tabnum": {"what": "numbers in even figures, steady when they change", "fits": {"line", "striped", "plain", "solid"}},
        "k-trendpill": {"what": "the trend as a soft pill with an arrow", "fits": {"soft", "tint", "float", "rows", "light"}},
        "k-trendtext": {"what": "the trend as plain coloured text with an arrow, no pill", "fits": {"line", "plain", "clean", "dark", "striped"}},
        "k-accentedge": {"what": "a thin accent bar along the tile's top edge", "fits": {"line", "plain", "clean", "flat", "striped"}},
        "k-cornerblob": {"what": "a soft circle of the tile's colour in its corner", "fits": {"soft", "tint", "float", "icon", "rows"}},
        "k-glassedge": {"what": "a frosted edge and inner light, like glass", "fits": {"glass", "mesh", "dark", "spark"}},
        "k-capslabel": {"what": "the label in small upper-case letters", "fits": {"line", "plain", "dark", "striped", "clean"}},
        "k-hoverlift": {"what": "the tile lifts with a coloured shadow on hover", "fits": {"soft", "float", "tint", "glass", "rows"}},
    },
    "side": {
        "s-pillactive": {"what": "the open page as a filled accent pill with white words", "fits": {"light", "float", "soft", "glass", "top"}},
        "s-baractive": {"what": "the open page with an accent bar at its left and a faint tint", "fits": {"line", "plain", "clean", "light", "striped"}},
        "s-glowactive": {"what": "the open page glowing softly on a dark menu", "fits": {"dark", "rail", "accent", "glass", "mesh"}},
        "s-softactive": {"what": "the open page on a white card with a small shadow", "fits": {"soft", "tint", "float", "rows", "canvas"}},
        "s-icontile": {"what": "each menu icon in a small rounded tile", "fits": {"soft", "float", "tint", "light", "rows", "glass"}},
        "s-capslabel": {"what": "the menu's group names in small spaced capitals", "fits": {"line", "plain", "dark", "clean", "striped"}},
        "s-hovernudge": {"what": "an entry slides a little to the right on hover", "fits": {"soft", "float", "light", "rows", "line"}},
        "s-footcard": {"what": "the signed-in person at the bottom as a small card", "fits": {"soft", "float", "glass", "tint", "dark", "canvas"}},
    },
    "button": {
        "b-solid": {"what": "buttons in one flat accent colour", "fits": {"line", "plain", "clean", "flat", "striped", "solid"}},
        "b-gradient": {"what": "buttons in a gradient of the accent", "fits": {"gradient", "spark", "glass", "mesh", "tint"}},
        "b-soft": {"what": "secondary buttons as a soft tint of the accent", "fits": {"soft", "tint", "float", "rows", "light"}},
        "b-pill": {"what": "fully rounded buttons", "fits": {"soft", "float", "tint", "glass", "rows"}},
        "b-rounded": {"what": "buttons with gently rounded corners", "fits": {"line", "plain", "clean", "striped", "flat", "solid"}},
        "b-glow": {"what": "a soft coloured shadow under the main button", "fits": {"dark", "glass", "mesh", "spark", "gradient"}},
        "b-flat": {"what": "no shadow, crisp and quiet", "fits": {"line", "plain", "clean", "flat", "striped"}},
        "b-shine": {"what": "a light sweeps across the button on hover", "fits": {"gradient", "spark", "glass", "dark", "solid"}},
        "b-press": {"what": "the button presses in when clicked", "fits": {"soft", "line", "plain", "rows", "flat"}},
    },
    "form": {
        "f-filled": {"what": "fields filled with a faint tint, no border until focused", "fits": {"soft", "tint", "float", "rows", "glass"}},
        "f-outline": {"what": "fields with a clear thin border on white", "fits": {"line", "plain", "clean", "striped", "flat"}},
        "f-underline": {"what": "fields as a single line under the words", "fits": {"line", "clean", "dark"}},
        "f-ring": {"what": "a soft accent ring around the field being typed in", "fits": {"soft", "tint", "float", "light", "rows", "line"}},
        "f-glow": {"what": "the field being typed in glows in the accent", "fits": {"dark", "glass", "mesh", "spark"}},
        "f-pill": {"what": "fully rounded fields", "fits": {"soft", "float", "glass", "tint"}},
        "f-capslabel": {"what": "field labels in small spaced capitals", "fits": {"line", "plain", "dark", "clean", "striped"}},
        "f-roomy": {"what": "taller fields with more air", "fits": {"soft", "float", "glass", "tint"}},
    },
}


def traits(theme_name):
    """The traits of an app theme (its axes' values, dark or light), or the landing theme's few."""
    t = themes.APP_THEMES.get(theme_name) or themes.ALL.get(theme_name) or {}
    out = {str(v) for k, v in t.items() if k in ("side", "frame", "kpi", "panel", "table", "banner") and v}
    out.add("dark" if t.get("side") == "dark" or "dark" in str(t.get("base") or "") else "light")
    return out


def candidates(component, theme_name, n=6):
    """The component's assets that best suit the theme, best first."""
    tr = traits(theme_name)
    scored = sorted(ASSETS.get(component, {}).items(), key=lambda kv: -len(kv[1]["fits"] & tr))
    return [k for k, v in scored if v["fits"] & tr][:n] or [k for k, _ in scored[:n]]


def default(theme_name, per=4):
    """M42's own pick when the 4B was not reached: the best few per component."""
    return [t for c in ASSETS for t in candidates(c, theme_name, per)]


def describe(component, tokens):
    return "; ".join(f"{t} = {ASSETS[component][t]['what']}" for t in tokens if t in ASSETS.get(component, {}))


# one choice per group (a line glows OR is thin; a status is a soft pill OR a solid one OR a dot); "" = none of them
GROUPS = {
    "chart": {"line": ["c-glow", "c-deepfill", "c-thin"], "tip": ["c-darktip", "c-glasstip"], "grid": ["c-dashgrid", "c-nogrid"],
              "bars": ["c-pillbars", "c-squarebars", "c-gradbars", "c-track"], "focus": ["c-onebar", ""], "legend": ["c-pilllegend", ""],
              "axis": ["c-mutedaxis", ""]},
    "table": {"status": ["t-softpill", "t-solidpill", "t-dotstatus"], "rows": ["t-hairline", "t-zebra", "t-cardrows"],
              "head": ["t-tinthead", "t-capshead"], "hover": ["t-hoverlift", "t-hoverbar"], "first": ["t-boldfirst", ""],
              "numbers": ["t-tabnum", ""], "density": ["t-roomy", "t-dense", ""]},
    "kpi": {"number": ["k-bignum", "k-gradnum", "k-tabnum"], "trend": ["k-trendpill", "k-trendtext"],
            "edge": ["k-accentedge", "k-cornerblob", "k-glassedge", ""], "label": ["k-capslabel", ""], "hover": ["k-hoverlift", ""]},
    "side": {"active": ["s-pillactive", "s-baractive", "s-glowactive", "s-softactive"], "icons": ["s-icontile", ""],
             "labels": ["s-capslabel", ""], "hover": ["s-hovernudge", ""], "foot": ["s-footcard", ""]},
    "button": {"fill": ["b-solid", "b-gradient"], "second": ["b-soft", ""], "shape": ["b-pill", "b-rounded"],
               "depth": ["b-glow", "b-flat"], "motion": ["b-shine", "b-press", ""]},
    "form": {"field": ["f-filled", "f-outline", "f-underline"], "focus": ["f-ring", "f-glow"], "shape": ["f-pill", ""],
             "labels": ["f-capslabel", ""], "size": ["f-roomy", ""]},
}

# what never goes with a theme's own axis (a dark menu's open page on a white card; a glass edge on a plain light tile)
CLASH = {"s-softactive": {"dark", "rail", "accent"}, "s-pillactive": {"rail", "accent"}, "s-glowactive": {"light"},
         "f-underline": {"rows", "soft", "float"}, "k-glassedge": {"light", "plain"}}


def ranked_groups(theme_name):
    """{component: {group: [tokens, best for this theme first]}} for the 4B's choice."""
    tr = traits(theme_name)
    out = {}
    for c, gs in GROUPS.items():
        out[c] = {g: sorted([o for o in opts if not (CLASH.get(o, set()) & tr)] or opts,
                            key=lambda t: -len(ASSETS[c][t]["fits"] & tr) if t else -.5) for g, opts in gs.items()}
        # ("" = none of them: it beats a treatment that suits none of the theme's traits)
    return out


def best(theme_name):
    """M42's own pick: the best of each group for the theme."""
    return [opts[0] for gs in ranked_groups(theme_name).values() for opts in gs.values() if opts[0]]
