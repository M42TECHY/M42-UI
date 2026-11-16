"""⚖ App blocks: the premium compositions of an app screen's parts (app_weights.W), drawn by M42, each in its column of the
kind's skeleton (appflows.LAYOUTS; the user, 2026-11-15: "how the premium weightage sits inside each column, for each
prompt: check it on the POS first"). Like the landing blocks (blocks.py): each composition declares what it needs, the
ones a part's content fits are its candidates, one is chosen per part (pick: by the content and the theme, the others
kept as alternatives). CSS under ".m42-a-" in bundled/m42-ui.css.

Batch 1 (2026-11-15), the POS: its categories, the products to tap, today's numbers, the bill, the recent bills."""
import hashlib
import html as _html

import widgets
from widgets import ic

TINTS = widgets.TINTS


def e(x):
    return _html.escape(str(x if x is not None else ""), quote=True)


def _items(sec, hi=12):
    return [i for i in (sec.get("items") or []) if isinstance(i, dict)][:hi]


def _money(v, unit="₹"):
    return widgets.amount(v, unit if unit in ("₹", "$", "€", "£") else "₹")


def _stock(i):
    """An item's stock fact ("24 left") from its meta, or ""."""
    for m in i.get("meta") or []:
        s = str(m)
        if any(c.isdigit() for c in s) and any(w in s.lower() for w in ("left", "stock", "in stock", "pcs", "units", "qty")):
            return s
    return ""


def _cat(i):
    return str(i.get("badge") or i.get("group") or "")


# ---------------------------------------------------------------------------------------------------- categories
def chips_pill_counts(sec, ctx):
    """ShopFlow POS: the categories as rounded pills, an icon and a count each, "All" first and filled; a pill filters
    the product tiles under it (data-cat)."""
    its = _items(sec, 9)
    total = sum(int(widgets.num(i.get("value"))) for i in its if widgets.num(i.get("value")))
    pills = (f'<button type="button" class="m42-a-pill is-on" data-m42-cat="*"><i class="bi bi-grid"></i>All'
             + (f'<em>{total}</em>' if total else "") + "</button>")
    pills += "".join(f'<button type="button" class="m42-a-pill" data-m42-cat="{e(i.get("title"))}"><i class="bi {ic(i.get("icon"), "bi-tag")}"></i>'
                     f'{e(i.get("title"))}' + (f'<em>{int(widgets.num(i.get("value")))}</em>' if widgets.num(i.get("value")) else "") + "</button>"
                     for i in its if str(i.get("title") or "").strip().lower() != "all")
    return f'<div class="m42-a-pills" data-m42-cats>{pills}</div>'


def chips_icon_tiles(sec, ctx):
    """Category tiles in a row: a tinted square icon over the name and its count; the open one in the accent."""
    its = [i for i in _items(sec, 8) if str(i.get("title") or "").strip().lower() != "all"]
    total = sum(int(widgets.num(i.get("value"))) for i in its if widgets.num(i.get("value")))
    tiles = (f'<button type="button" class="m42-a-ctile is-on" style="--t:var(--m42-accent-rgb)" data-m42-cat="*"><span><i class="bi bi-grid"></i></span>'
             f'<b>All</b>' + (f'<small>{total} items</small>' if total else "") + "</button>")
    tiles += "".join(f'<button type="button" class="m42-a-ctile" style="--t:{TINTS[(k + 1) % 3]}" data-m42-cat="{e(i.get("title"))}">'
                    f'<span><i class="bi {ic(i.get("icon"), "bi-tag")}"></i></span><b>{e(i.get("title"))}</b>'
                    + (f'<small>{int(widgets.num(i.get("value")))} items</small>' if widgets.num(i.get("value")) else "") + "</button>"
                     for k, i in enumerate(its))
    return f'<div class="m42-a-ctiles" data-m42-cats>{tiles}</div>'


# ---------------------------------------------------------------------------------------------------- products to tap
def _add_btn(i):
    return (f'<button type="button" class="m42-a-add" data-m42-add data-name="{e(i.get("title"))}" data-rate="{widgets.num(i.get("value")):g}" '
            f'aria-label="Add {e(i.get("title"))} to the bill"><i class="bi bi-plus-lg"></i></button>')


def products_tap_tiles(sec, ctx):
    """ShopFlow POS: the products as square tiles to tap: the photo (or the icon on its tint), the name, the price big,
    the stock as a small pill, a round + that adds it to the bill; a search box over them."""
    tiles = "".join(f'<article class="m42-a-tile" style="--t:{TINTS[k % 3]}" data-cat="{e(_cat(i))}">'
                    f'<div class="m42-a-tile-pic">' + (widgets.photo(i, "m42-a-tile-img") or f'<i class="bi {ic(i.get("icon"), "bi-bag")}"></i>')
                    + (f'<span class="m42-a-stock">{e(_stock(i))}</span>' if _stock(i) else "") + "</div>"
                    f'<b>{e(i.get("title"))}</b><div class="m42-a-tile-foot"><strong>{_money(i.get("value"), i.get("unit"))}</strong>{_add_btn(i)}</div></article>'
                    for k, i in enumerate(_items(sec, 12)))
    return (f'<div class="m42-a-prod"><label class="m42-topsearch m42-a-search"><i class="bi bi-search"></i><input type="search" '
            f'placeholder="Search or scan a product…" aria-label="Search products" data-m42-prod-search></label><div class="m42-a-tiles">{tiles}</div></div>')


def products_list_rows(sec, ctx):
    """Many products, little room: compact rows, a round thumb, the name and stock, the price, a + to add."""
    rows = "".join(f'<li data-cat="{e(_cat(i))}"><span class="m42-a-thumb" style="--t:{TINTS[k % 3]}">'
                   + (widgets.photo(i, "m42-a-thumb-img") or f'<i class="bi {ic(i.get("icon"), "bi-bag")}"></i>') + "</span>"
                   f'<div><b>{e(i.get("title"))}</b><small>{e(_stock(i) or i.get("text") or "")}</small></div>'
                   f'<strong>{_money(i.get("value"), i.get("unit"))}</strong>{_add_btn(i)}</li>' for k, i in enumerate(_items(sec, 14)))
    return (f'<div class="m42-a-prod"><label class="m42-topsearch m42-a-search"><i class="bi bi-search"></i><input type="search" '
            f'placeholder="Search or scan a product…" aria-label="Search products" data-m42-prod-search></label><ul class="m42-a-rows">{rows}</ul></div>')


# ---------------------------------------------------------------------------------------------------- today's numbers
def _bars(seed):
    h = hashlib.md5(str(seed).encode("utf-8")).digest()
    return "".join(f'<i style="--h:{35 + b % 60}%"></i>' for b in h[:9])


def _trend(i):
    t = str(i.get("badge") or "")
    if not t:
        return ""
    down = t.startswith("-") or "↓" in t
    return f'<em class="{"down" if down else "up"}"><i class="bi bi-arrow-{"down" if down else "up"}-right"></i>{e(t.lstrip("+-↑↓ "))}</em>'


def kpi_sparkline(sec, ctx):
    """chart refer img (sales hub): a KPI tile with the value big, its change as a pill, mini bars under it."""
    tiles = "".join(f'<div class="m42-a-kpi" style="--t:{TINTS[k % 3]}"><span>{e(i.get("title"))}</span>'
                    f'<b>{_money(i.get("value"), i.get("unit")) if (i.get("unit") or "") in ("₹", "$") else e(widgets.fmt(i.get("value")))}'
                    f'<small>{e("" if (i.get("unit") or "") in ("₹", "$") else i.get("unit") or "")}</small></b>{_trend(i)}'
                    f'<div class="m42-a-spark">{_bars(i.get("title"))}</div></div>' for k, i in enumerate(_items(sec, 4)))
    return f'<div class="m42-a-kpis">{tiles}</div>'


def kpi_progress_target(sec, ctx):
    """refer img (HR performance, restaurant ops): each tile with a thin coloured bar to its target."""
    return widgets.w_kpi_tiles(dict(sec, title="", eyebrow="", lead="", _look={"progress": True}), ctx)


def kpi_compact_strip(sec, ctx):
    """The numbers in one slim strip under the products (a cashier's screen: room for the work), hairlines between."""
    cells = "".join(f'<div><span>{e(i.get("title"))}</span><b>{_money(i.get("value"), i.get("unit")) if (i.get("unit") or "") in ("₹", "$") else e(widgets.fmt(i.get("value")))}'
                    f'{e("" if (i.get("unit") or "") in ("₹", "$") else i.get("unit") or "")}</b>{_trend(i)}</div>' for i in _items(sec, 4))
    return f'<div class="m42-a-strip">{cells}</div>'


# ---------------------------------------------------------------------------------------------------- the bill
def bill_pos_panel(sec, ctx):
    """refer img: ShopFlow POS: the current sale as the right panel (lines, qty, totals, payment, a big Pay)."""
    return widgets.w_invoice(sec, ctx)


# ---------------------------------------------------------------------------------------------------- records
def table_pill_toolbar(sec, ctx):
    """data list ref img (invoices): the table under a toolbar of status tabs with their counts (All, Paid, Pending...),
    a tab shows only its rows; soft status pills; search."""
    counts = {}
    for i in _items(sec, 30):
        b = str(i.get("badge") or "").strip()
        if b:
            counts[b] = counts.get(b, 0) + 1
    tabs = (f'<button type="button" class="is-on" data-m42-tab="*">All <em>{len(_items(sec, 30))}</em></button>'
            + "".join(f'<button type="button" data-m42-tab="{e(b)}">{e(b)} <em>{n}</em></button>' for b, n in list(counts.items())[:4]))
    return f'<div class="m42-a-tabs" data-m42-tabs>{tabs}</div>' + widgets.w_data_table(dict(sec, title="", eyebrow="", lead=""), ctx)


def table_plain(sec, ctx):
    return widgets.w_data_table(dict(sec, title="", eyebrow="", lead=""), ctx)


# ---------------------------------------------------------------------------------------------------- registry
# part: the part it draws; weight: the app_weights composition it is; needs: what its content must have
APPBLOCKS = {
    "chips.pill_counts": {"part": "category_chips", "draw": chips_pill_counts, "weight": "screen.pos_split", "needs": {"items": (2, 9)}},
    "chips.icon_tiles": {"part": "category_chips", "draw": chips_icon_tiles, "weight": "screen.pos_split", "needs": {"items": (3, 8)}},
    "products.tap_tiles": {"part": "image_cards", "draw": products_tap_tiles, "weight": "screen.pos_split", "needs": {"items": (3, 12), "prices": True}},
    "products.list_rows": {"part": "image_cards", "draw": products_list_rows, "weight": "commerce.filter_grid", "needs": {"items": (6, 14), "prices": True}},
    "kpi.sparkline": {"part": "kpi_tiles", "draw": kpi_sparkline, "weight": "chart.kpi_sparkline", "needs": {"items": (2, 4)}},
    "kpi.progress_target": {"part": "kpi_tiles", "draw": kpi_progress_target, "weight": "screen.ops_tiles_tasks", "needs": {"items": (2, 4)}},
    "kpi.compact_strip": {"part": "kpi_tiles", "draw": kpi_compact_strip, "weight": "screen.pos_split", "needs": {"items": (2, 4), "beside_work": True}},
    "bill.pos_panel": {"part": "invoice", "draw": bill_pos_panel, "weight": "screen.pos_split", "needs": {"items": (1, 10)}},
    "table.pill_toolbar": {"part": "data_table", "draw": table_pill_toolbar, "weight": "list.pill_table", "needs": {"items": (3, 30), "status": True}},
    "table.plain": {"part": "data_table", "draw": table_plain, "weight": "list.grouped_table", "needs": {"items": (1, 30)}},
}


def fits(name, sec, beside_work=False):
    b = APPBLOCKS.get(name)
    if not b:
        return False
    its = _items(sec, 99)
    lo, hi = b["needs"]["items"]
    if not lo <= len(its) <= max(hi, lo):
        return False
    if b["needs"].get("prices") and sum(1 for i in its if widgets.num(i.get("value"))) < len(its) / 2:
        return False
    if b["needs"].get("status") and sum(1 for i in its if i.get("badge")) < 2:
        return False
    if b["needs"].get("beside_work") and not beside_work:
        return False
    return True


def candidates(part, sec, beside_work=False):
    return [n for n, b in APPBLOCKS.items() if b["part"] == part and fits(n, sec, beside_work)]


def pick(part, sec, theme_traits=(), beside_work=False, seed=""):
    """The composition for a part: the first that fits, a dense theme (line / striped / plain) taking the quieter one,
    a soft one the richer one; ("", []) when none fits (the part's usual widget then)."""
    cands = candidates(part, sec, beside_work)
    if not cands:
        return "", []
    dense = bool({"line", "striped", "plain"} & set(theme_traits))  # ("clean" is in almost every theme: no sign of density)
    order = {"kpi_tiles": ["kpi.compact_strip", "kpi.sparkline", "kpi.progress_target"] if beside_work else
             (["kpi.progress_target", "kpi.sparkline"] if dense else ["kpi.sparkline", "kpi.progress_target"]),
             "category_chips": ["chips.pill_counts", "chips.icon_tiles"] if dense else ["chips.icon_tiles", "chips.pill_counts"],
             "image_cards": ["products.list_rows", "products.tap_tiles"] if len(_items(sec, 99)) > 9 else ["products.tap_tiles", "products.list_rows"],
             "data_table": ["table.pill_toolbar", "table.plain"]}.get(part, cands)
    ranked = [n for n in order if n in cands] + [n for n in cands if n not in order]
    return ranked[0], ranked[1:]


def draw(name, sec, ctx):
    return APPBLOCKS[name]["draw"](sec, ctx)
