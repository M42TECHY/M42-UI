"""⚖ App weightage: the compositions of the user's own premium APP references (the user, 2026-11-14: "the premium
weightage of tables, charts... we took them separately: refer to them for the admin / CRM / ERP / POS / CMS rules").

Studied 2026-11-14 from D:/SAGE_CDSRA_POC (210 pictures as contact sheets): refer img (15 whole dashboards: POS,
HR shifts, food ordering, health, trading, restaurant, time tracker, recipes, cooking, booking, gaming, cleaning,
smart home, school), chart refer img (45), data list ref img (44), form control refer img (32), commerce marketing
refer img (38), communication refer img (16). Each entry: the part it is (screenparts.RULES), what the composition IS,
the folder it comes from, and the widget that draws it now (widgets.py), or new=True when M42 has no drawing of it
yet (to be built, batch by batch, like the landing blocks)."""

W = {}


def w(name, part, structure, ref, widget="", new=False):
    W[name] = {"part": part, "structure": structure, "ref": ref, "widget": widget, "new": new}


# ---- whole screens (refer img): how the parts sit together
w("screen.pos_split", "invoice", "category tabs over a product grid (photo tiles, price, stock) on the left two thirds; the current sale as a "
  "right panel: lines with qty, subtotal / discount / tax, total, a big Checkout; a bottom bar of actions (scan barcode, discount, note)",
  "refer img: ShopFlow POS", "invoice")
w("screen.greeting_banner", "head", "a wide rounded banner at the top: 'Hello, name' + one line of what needs attention, an illustration or "
  "photo at its right, one action", "refer img: cleaning, school, recipes, Skillery", "banner")
w("screen.ops_tiles_tasks", "kpi_tiles", "small KPI tiles each with a thin progress bar and a target ('82 % of 90 %'), a trend chart with a dark "
  "tooltip, an upcoming-shifts list and a current-tasks list with priority pills beside it", "refer img: HR performance", "kpi_tiles")
w("screen.score_center", "gauge", "one big score in the middle of a decorative ring (89 % overall), metric tiles with tiny sparklines round it, a "
  "one-line verdict under it", "refer img: health ring", "", True)
w("screen.dark_trading", "area_chart", "dark surface, the balance huge with its change, a glowing area chart, a calculator form card beside it, a "
  "markets list with flags and +/- coloured values", "refer img: Littlebee", "area_chart")
w("screen.restaurant_ops", "kpi_tiles", "KPI tiles with a coloured fill bar each, a bar chart with one bar highlighted and a value tooltip, a "
  "photo list of stores, recent activity with status pills, top dishes as horizontal bars", "refer img: D.CC", "kpi_tiles")
w("screen.tracker_board", "kanban", "coloured project tiles in a row on top, kanban columns under them, a week schedule with coloured blocks "
  "at the bottom", "refer img: Jiron time tracker", "kanban")
w("screen.booking_desk", "calendar", "KPI tiles with tinted icon squares, a reservation area chart with a callout, a month calendar with "
  "booked days ringed, check-in / out rings, latest reviews", "refer img: Travelgo", "calendar")
w("screen.home_controls", "device_cards", "device cards with switches at their top right, a light control with a brightness slider, an AC "
  "dial (round gauge with +/-), a power line chart, members as avatars, a camera photo", "refer img: smart home", "device_cards")
w("screen.school_office", "kpi_tiles", "a banner with an illustration, KPI row with changes, an attendance donut, grouped bars by class, a "
  "mini month calendar, agenda, tasks, a smooth area chart of activity", "refer img: SchoolHub", "kpi_tiles")
# ---- charts (chart refer img)
w("chart.grouped_bars", "bar_chart", "bars grouped per period in 2-3 colours with a legend, values as small pills above the tallest",
  "chart refer img: deep work, financial analytics", "bar_chart")
w("chart.highlight_bar", "bar_chart", "muted bars with ONE bar in the accent and a dark value bubble over it", "chart refer img: revenue, earning report", "bar_chart")
w("chart.stacked_gradient", "bar_chart", "stacked bars with gradient segments, rounded tops", "chart refer img: focus time, deals by stage", "", True)
w("chart.smooth_area_tooltip", "area_chart", "a smooth curve with a gradient fill, a vertical guide line and a dark tooltip card on the hovered "
  "point, the previous period dashed", "chart refer img: portfolio, cash flow, reservations", "area_chart")
w("chart.multi_line_legend", "line_chart", "3-4 thin lines (one per platform / source) with a legend of coloured dots and their totals",
  "chart refer img: follower growth", "line_chart")
w("chart.donut_center", "donut", "a thick donut with rounded ends, the total or main % in the middle, legend with values beside it",
  "chart refer img: shipment status, campaign, household expenses", "donut")
w("chart.radial_bands", "rings", "concentric progress bands (3-4 rings) with labels, like an activity ring", "chart refer img: team workload, expenses", "rings")
w("chart.semi_gauge", "gauge", "a half ring in a gradient with the value in the middle and the min / max under it", "chart refer img: score 6.8, risk 68 %", "gauge")
w("chart.heatmap_grid", "heatmap", "a grid of rounded cells in one hue from light to deep, days by hours / departments by days", "chart refer img: department risk, reports", "heatmap")
w("chart.funnel_bars", "funnel", "stage bars side by side with counts and the drop % between them, the conversion rate above", "chart refer img: funnels, deals", "funnel")
w("chart.sankey_flow", "funnel", "flows from sources to categories as ribbons (cash flow, traffic)", "chart refer img: cash flow", "", True)
w("chart.map_bubbles", "map_card", "a world / country map with bubbles or pins sized by value, a side list of the top places", "chart refer img: travel expenses, CO2, logistics", "map_card")
w("chart.kpi_sparkline", "kpi_tiles", "a KPI tile with a tiny sparkline or mini bars under the value and the change as a pill", "chart refer img: dashboard overview, sales hub", "kpi_tiles")
w("chart.big_number_card", "kpi_tiles", "a dark glossy card with one big number, a micro chart and a coloured % ring", "chart refer img: neo widgets", "", True)
w("chart.horizontal_ranking", "hbars", "a ranked list with long rounded bars and values at their ends", "refer img: top dishes; chart refer img: department performance", "hbars")
# ---- data lists (data list ref img)
w("list.grouped_table", "data_table", "a table grouped by period (This month / Next month) with collapsible groups, checkboxes, people avatars, "
  "status pills in soft colours, a total row", "data list ref img: Planora", "data_table")
w("list.pill_table", "data_table", "a clean table with a toolbar (tabs All / Draft / Paid / Overdue with counts, search, filter), soft status "
  "pills, row menu (…), pagination", "data list ref img: invoices, team members", "data_table")
w("list.people_table", "data_table", "rows of people: avatar + name + role, task counts as chips, an access pill, View profile", "data list ref img: team members", "data_table")
w("list.filter_popover", "data_table", "a filter row of chips above the table; a popover with field / condition / value and Apply", "form control refer img: orders filter", "", True)
w("list.alert_feed", "alerts", "alerts with a severity tag (Critical / Warning), who, what, risk score, a View details link; tabs by severity",
  "data list ref img: interventions", "alerts")
w("list.pastel_kanban", "kanban", "pastel-tinted columns (to do, in progress, review, done), cards with priority tag, title, note, progress bar, "
  "avatars and counts", "data list ref img: NovaBoard, Kaniva", "kanban")
w("list.activity_cards", "timeline", "a timeline whose events are tinted cards (by source: email, task, Slack), with a quote line and tags",
  "data list ref img: activity timeline", "timeline")
w("list.gantt_rings", "gantt", "a project timeline (bars per person over months) beside radial workload rings", "data list ref img: Nexus, Nova", "gantt")
w("list.file_manager", "files", "recent files as big type-coloured tiles, then an all-files table (name, type, size, date, status), storage ring",
  "data list ref img: file manager, My Cloud", "files")
w("list.applicant_steps", "order_tracker", "each record a row with a stepper of its stages (Applied, Shortlist, Interview, Offer) and the "
  "current one coloured", "data list ref img: hiring; commerce: fulfilment", "order_tracker")
w("list.podium", "leaderboard", "a podium of the top 3 (2-1-3) with avatars and scores, the rest as a ranked list under it", "data list ref img: leaderboard", "", True)
w("list.integration_cards", "integrations", "app cards with logo, connected pill, a line, tags, Manage / Connect", "data list ref img: integrations", "integrations")
w("list.course_cards", "project_cards", "course cards with a cover photo, category tag, title, lessons, instructor, progress", "data list ref img: Skillery", "project_cards")
w("list.invoice_editor", "invoice", "an invoice editor: client, dates, item rows (qty, rate, total), notes, with a live preview beside it, "
  "Save draft / Send", "data list ref img: create invoice, Flowly", "invoice")
w("list.wizard_steps", "form", "a stepper across the top (Choose date, campsite, RV, Check), each step a card, Next / Back", "data list ref img: booking wizard", "stepper")
w("list.pricing_compare", "data_table", "plan columns with prices on top and feature rows with ticks", "data list ref img: pricing", "")
# ---- forms (form control refer img)
w("form.settings_tabs", "form", "settings with tabs (Billing, Profile, Security...), plan cards to switch, billing history as a table with "
  "checkboxes", "form control refer img: settings / billing", "form")
w("form.date_range", "form", "a search bar of fields (from, to, dates, guests) with a two-month range picker under it", "form control refer img: cruise", "", True)
w("form.payment_cards", "form", "saved cards as small card pictures to pick (radio), card limits as sliders with toggles, Add new card",
  "form control refer img: cards; commerce: payment method", "", True)
w("form.otp_split", "form", "a split screen: the form card on one side (email, then a 4-6 box code), a picture or brand art on the other",
  "form control refer img: sign-in, OTP", "form")
w("form.onboarding_steps", "form", "a few short steps (account, personal info, OTP, location) each one screen with progress", "form control refer img: onboarding", "stepper")
w("form.control_dial", "gauge", "a round dial with +/- for a set value (temperature) and mode chips under it", "form control refer img: smart home", "control_card")
w("form.slider_card", "sliders", "a tinted card with one big value and a slider (brightness 47 %), mode buttons under", "form control refer img: light", "sliders")
# ---- commerce (commerce marketing refer img)
w("commerce.checkout_split", "form", "checkout in two columns: contact / shipping / payment on the left, the order summary with item thumbs, "
  "subtotal, delivery, total and a dark Pay button on the right", "commerce marketing refer img: Optopia, prints", "", True)
w("commerce.filter_grid", "image_cards", "a product grid with a filter rail (price range histogram, star rating, brands checkboxes, delivery "
  "toggle), wish hearts on tiles", "commerce marketing refer img: MLC", "image_cards")
w("commerce.payment_select", "form", "payment methods as selectable rows (card logo, masked number, expiry, Set default / Edit), Add new card",
  "commerce marketing refer img: payment method", "", True)
w("commerce.media_player", "media_player", "a compact player card with cover, title, progress and controls", "commerce marketing refer img: music widgets", "media_player")
# ---- communication (communication refer img)
w("comm.notification_panel", "notifications", "a panel with tabs (View all, Verified, Mentions), each item avatar + who did what + when, "
  "inline file cards and Accept / Decline buttons", "communication refer img: notifications", "notifications")
w("comm.empty_orbit", "empty_state", "an empty state with avatars orbiting an icon, a title, a line and two actions (Create invite link, Add user)",
  "communication refer img: add your first user", "empty_state")
w("comm.inbox_three_pane", "chat_app", "three panes: folders / inboxes, conversation list with unread dots, the open thread with bubbles", "communication refer img: inbox, messages", "chat_app")
w("comm.ai_assistant", "chat_app", "an assistant panel beside the dashboard: suggestions as chips, a chat with the AI, a composer", "communication refer img: Omago AI; chart refer img: WorkPilot", "", True)
w("comm.command_search", "empty_state", "a command palette / search with no results: an icon, 'No results', clear / upload actions, key hints", "communication refer img: search", "", True)


def by_part(part):
    return {n: x for n, x in W.items() if x["part"] == part}


def missing():
    """The compositions M42 cannot draw yet (to build next)."""
    return [n for n, x in W.items() if x["new"]]


def guide(part):
    """The premium compositions of a part, for the 4B planning it ("" when none)."""
    xs = by_part(part)
    return "; ".join(x["structure"] for x in xs.values())[:700]
