"""🧭 App flows: how a premium WORK app of each kind is laid out (the user, 2026-11-14: "admin panel, CRM, ERP, POS, CMS,
dashboard: set rules for those too, from the premium weightage already taken from my reference folders").

The landing pages' flows.py answers "what comes under the hero"; an app is used, not read, so its flow answers:
who works on it, the one job they do many times a day (the MAIN tool, the screen's biggest part), what they check
while doing it (the supporting parts), and the other screens of the app. Researched from how real products of each
kind are built and from the user's reference folders (D:/SAGE_CDSRA_POC: refer img, chart refer img, data list ref
img, form control refer img, commerce marketing refer img, communication refer img; 2026-11-14). The 4B reads the
request, picks the nearest kind and adapts it; never words matched in the request. Parts are pagebuild / widgets
parts (screenparts.RULES has each one's rules, app_weights.W its premium compositions)."""

# kind -> {"label", "fits", "users", "work", "main": (part, what it shows), "parts": [(part, need), ...], "screens": [...]}
# parts: the dashboard's supporting parts in order after the main tool; screens: the app's other pages (name: main part)
FLOWS = {
    "pos": {
        "label": "Point of sale", "fits": "shop / cafe / restaurant / pharmacy billing counters, retail POS",
        "users": "a cashier at the counter, all day", "work": "make a bill fast: tap products, change quantities, take payment",
        "main": ("invoice", "the bill being made: lines with qty steppers, rate, line total; discount, tax, total; Pay with cash / card / UPI"),
        "parts": [("category_chips", "product categories to filter the grid (All first)"),
                  ("image_cards", "the products to tap: photo, name, price, stock left; a search box over them"),
                  ("kpi_tiles", "today: sales, bills, average bill, items sold"),
                  ("data_table", "recent bills: bill no, time, items, total, payment, status pill")],
        "screens": ["Orders: data_table", "Products: data_table", "Customers: data_table", "Reports: bar_chart"],
    },
    "crm": {
        "label": "CRM / sales", "fits": "sales CRM, lead management, real-estate / agency CRM, deal pipelines",
        "users": "sales reps and their manager", "work": "move deals and leads forward stage by stage, follow up on time",
        "main": ("kanban", "the pipeline: columns per stage (New, Qualified, Proposal, Won), deal cards with value, owner, next step"),
        "parts": [("kpi_tiles", "total leads, qualified, pipeline value, conversion rate, each with its change"),
                  ("funnel", "leads by stage, how many move to the next"),
                  ("task_list", "today's follow-ups: call / email / meeting with the lead and time"),
                  ("data_table", "recent leads: name, company, owner, stage pill, value, last activity"),
                  ("bar_chart", "won revenue by month")],
        "screens": ["Leads: data_table", "Deals: kanban", "Contacts: data_table", "Activities: timeline", "Reports: funnel"],
    },
    "erp": {
        "label": "ERP / operations", "fits": "manufacturing / plant / trading ERP, back office of a company",
        "users": "operations and finance managers", "work": "watch orders, stock, production and money across the company",
        "main": ("data_table", "open orders / work orders: number, customer, item, qty, due date, stage pill, owner"),
        "parts": [("kpi_tiles", "revenue, open orders, stock value, overdue invoices"),
                  ("area_chart", "sales vs purchases over months"),
                  ("progress_list", "production lines / warehouses with their load or fill level"),
                  ("gantt", "production schedule: jobs over days"),
                  ("alerts", "low stock, overdue payments, machine faults")],
        "screens": ["Sales orders: data_table", "Purchase: data_table", "Inventory: data_table", "Production: gantt", "Accounts: data_table"],
    },
    "cms": {
        "label": "CMS / content", "fits": "blog / news / site content management, media library",
        "users": "editors and writers", "work": "write, review and publish content on schedule",
        "main": ("data_table", "posts: title, author, category, status pill (Draft, In review, Published), date, views"),
        "parts": [("kpi_tiles", "published, drafts, in review, views this week"),
                  ("calendar", "the publishing calendar with posts on their days"),
                  ("files", "the media library: recent images and files with type and size"),
                  ("comments", "latest comments to approve")],
        "screens": ["Posts: data_table", "Editor: form", "Media: files", "Comments: comments", "Settings: form"],
    },
    "analytics": {
        "label": "Analytics dashboard", "fits": "business / web / marketing / SaaS analytics, reports",
        "users": "managers and analysts", "work": "see how the business is doing and why, compare periods",
        "main": ("area_chart", "the main measure over time with the previous period, a range switch (7d / 30d / 12m)"),
        "parts": [("kpi_tiles", "4 headline numbers with their change vs last period and a small trend"),
                  ("donut", "the split of the main measure by source / channel / segment"),
                  ("heatmap", "activity by day and hour"),
                  ("hbars", "top items (pages, products, campaigns) by the measure"),
                  ("data_table", "the detail rows behind the numbers")],
        "screens": ["Overview: area_chart", "Reports: data_table", "Funnels: funnel", "Audience: donut"],
    },
    "ecommerce_admin": {
        "label": "Online store admin", "fits": "e-commerce / D2C store back office, marketplace seller panel",
        "users": "the store owner and staff", "work": "fulfil orders and keep products in stock",
        "main": ("data_table", "orders: order no, customer, items, total, payment pill, fulfilment pill, date"),
        "parts": [("kpi_tiles", "revenue, orders, conversion, average order value"),
                  ("line_chart", "sales over the month"),
                  ("list_thumbs", "top products with photo, sold count and stock"),
                  ("order_tracker", "an order moving: placed, packed, shipped, delivered"),
                  ("review_list", "latest product reviews")],
        "screens": ["Orders: data_table", "Products: data_table", "Customers: data_table", "Discounts: data_table", "Analytics: line_chart"],
    },
    "inventory": {
        "label": "Inventory / warehouse", "fits": "stock management, warehouse, store room, spare parts",
        "users": "store keepers and purchase staff", "work": "know what is in stock, what is low, receive and issue goods",
        "main": ("data_table", "stock items: SKU, name, category, qty with a level bar, reorder level, location, status pill"),
        "parts": [("kpi_tiles", "items, stock value, low-stock items, pending purchase orders"),
                  ("alerts", "items below reorder level"),
                  ("progress_list", "warehouses / bins with how full they are"),
                  ("bar_chart", "stock in vs out by week"),
                  ("timeline", "latest movements: received, issued, transferred")],
        "screens": ["Items: data_table", "Purchase orders: data_table", "Movements: timeline", "Suppliers: data_table"],
    },
    "hospital": {
        "label": "Hospital / clinic (HMS)", "fits": "hospital, clinic, dental, diagnostic centre management",
        "users": "front desk, doctors, nurses", "work": "run today's appointments and patients, beds and staff",
        "main": ("week_schedule", "today's / this week's appointments per doctor: time slots with the patient and the visit type"),
        "parts": [("kpi_tiles", "patients today, appointments, beds free, revenue today"),
                  ("data_table", "patient queue: token, name, age, doctor, status pill (Waiting, In consult, Done)"),
                  ("progress_list", "wards with beds occupied of total"),
                  ("bar_chart", "patients per department this week"),
                  ("team", "doctors on duty with their speciality and room")],
        "screens": ["Appointments: calendar", "Patients: data_table", "Doctors: team", "Billing: invoice", "Pharmacy: data_table"],
    },
    "school": {
        "label": "School ERP", "fits": "school / college / coaching centre management",
        "users": "the school office, teachers, the principal", "work": "attendance, fees, timetable and results",
        "main": ("week_schedule", "the timetable: periods by day with subject, class and teacher"),
        "parts": [("kpi_tiles", "students, attendance today %, fees collected, pending fees"),
                  ("donut", "attendance today: present, absent, late"),
                  ("bar_chart", "class-wise average marks"),
                  ("data_table", "fee dues: student, class, amount, due date, status pill"),
                  ("agenda", "today's events and meetings")],
        "screens": ["Students: data_table", "Attendance: data_table", "Fees: data_table", "Exams: data_table", "Timetable: week_schedule"],
    },
    "hr": {
        "label": "HR / payroll", "fits": "HRMS, payroll, recruitment, employee management",
        "users": "HR staff and managers", "work": "people records, leave, attendance, payroll and hiring",
        "main": ("data_table", "employees: name with photo, role, department, status pill, joined, manager"),
        "parts": [("kpi_tiles", "headcount, present today, on leave, open positions"),
                  ("task_list", "leave requests to approve with dates"),
                  ("kanban", "hiring pipeline: applied, interview, offer, hired"),
                  ("donut", "headcount by department"),
                  ("bar_chart", "payroll cost by month: gross pay, deductions, net pay"),
                  ("calendar", "holidays, birthdays, leaves this month")],
        "screens": ["Employees: data_table", "Leave: data_table", "Payroll: data_table", "Recruitment: kanban"],
    },
    "lms": {
        "label": "Learning (LMS)", "fits": "online courses, training portals, student dashboards",
        "users": "learners (and instructors)", "work": "continue courses, finish lessons and assignments",
        "main": ("project_cards", "courses in progress: cover, title, lessons done of total with a progress bar, Continue"),
        "parts": [("kpi_tiles", "courses, hours learned, certificates, streak"),
                  ("bar_chart", "learning hours by day"),
                  ("task_list", "assignments due with dates"),
                  ("leaderboard", "top learners this week"),
                  ("agenda", "live classes today")],
        "screens": ["My courses: project_cards", "Catalogue: image_cards", "Assignments: task_list", "Certificates: list_thumbs"],
    },
    "project": {
        "label": "Project / task management", "fits": "project management, agency work, task trackers",
        "users": "a team and its lead", "work": "plan and move tasks to done on time",
        "main": ("kanban", "tasks by status (To do, In progress, Review, Done): title, tag, assignees, due date, priority"),
        "parts": [("kpi_tiles", "active projects, tasks done, overdue, team velocity"),
                  ("gantt", "the project timeline by phase"),
                  ("rings", "completion by project"),
                  ("timeline", "recent activity: who did what"),
                  ("avatars", "the team with their workload")],
        "screens": ["Board: kanban", "Timeline: gantt", "List: task_list", "Files: files", "Team: team"],
    },
    "booking": {
        "label": "Bookings / reservations", "fits": "hotel PMS, salon / spa / turf / studio bookings, appointments",
        "users": "the front desk", "work": "fill the calendar, check guests in and out",
        "main": ("calendar", "the bookings calendar: rooms / staff by day with the booked slots"),
        "parts": [("kpi_tiles", "bookings today, check-ins, occupancy %, revenue"),
                  ("data_table", "arrivals today: guest, room / service, time, status pill"),
                  ("rings", "occupancy by room type"),
                  ("line_chart", "bookings over the month"),
                  ("review_list", "latest guest reviews")],
        "screens": ["Calendar: calendar", "Bookings: data_table", "Guests: data_table", "Rooms: device_cards"],
    },
    "restaurant": {
        "label": "Restaurant / kitchen admin", "fits": "restaurant back office, kitchen display, food delivery admin",
        "users": "the manager and the kitchen", "work": "take orders to the kitchen and out on time",
        "main": ("kanban", "live orders by stage (New, Cooking, Ready, Served / Out for delivery): table or order no, items, time"),
        "parts": [("kpi_tiles", "orders today, revenue, tables occupied, average prep time"),
                  ("bar_chart", "orders by hour"),
                  ("hbars", "top dishes today"),
                  ("progress_list", "tables / sections with their status"),
                  ("review_list", "latest reviews")],
        "screens": ["Orders: kanban", "Menu: data_table", "Tables: device_cards", "Reports: bar_chart"],
    },
    "finance": {
        "label": "Finance / banking / accounting", "fits": "banking, fintech wallets, accounting, expense, invoicing",
        "users": "the account holder or the accountant", "work": "see balances, money in and out, pay and get paid",
        "main": ("area_chart", "cash flow: income vs expenses over months"),
        "parts": [("kpi_tiles", "balance, income, expenses, savings, each with its change"),
                  ("data_table", "transactions: date, party, category, amount (+/- coloured), status pill"),
                  ("donut", "spending by category"),
                  ("progress_list", "budgets / goals with how much is used"),
                  ("quick_actions", "send, request, pay bill, top up")],
        "screens": ["Transactions: data_table", "Invoices: data_table", "Cards: device_cards", "Reports: bar_chart"],
    },
    "logistics": {
        "label": "Logistics / fleet", "fits": "shipments, courier, fleet tracking, supply chain",
        "users": "dispatchers and operations", "work": "track shipments and vehicles, act on delays",
        "main": ("map_card", "shipments / vehicles on a map with their routes and status"),
        "parts": [("kpi_tiles", "active shipments, on time %, delayed, delivered today"),
                  ("data_table", "shipments: id, from → to, carrier, ETA, status pill"),
                  ("order_tracker", "one shipment's steps: picked up, in transit, out for delivery, delivered"),
                  ("donut", "shipment status split"),
                  ("alerts", "delays and exceptions")],
        "screens": ["Shipments: data_table", "Fleet: device_cards", "Map: map_card", "Reports: bar_chart"],
    },
    "iot": {
        "label": "Devices / smart home / monitoring", "fits": "smart home, IoT, machines, servers, energy monitoring",
        "users": "the owner or an operator", "work": "see each device's state and control it",
        "main": ("device_cards", "devices with their live reading, on / off switch and status"),
        "parts": [("kpi_tiles", "devices online, power used today, alerts, temperature"),
                  ("line_chart", "the main reading over the day"),
                  ("gauge", "the one level that matters (temperature, load, battery)"),
                  ("switch_list", "scenes / rules to switch"),
                  ("alerts", "device warnings")],
        "screens": ["Devices: device_cards", "Rooms / sites: device_cards", "Energy: line_chart", "Automations: switch_list"],
    },
    "helpdesk": {
        "label": "Helpdesk / support inbox", "fits": "customer support tickets, shared inbox, chat support",
        "users": "support agents", "work": "answer and close tickets / chats quickly",
        "main": ("chat_app", "the inbox: conversations list, the open thread, the customer's details beside it"),
        "parts": [("kpi_tiles", "open tickets, first reply time, solved today, CSAT"),
                  ("data_table", "tickets: id, subject, customer, priority pill, status pill, agent, updated"),
                  ("bar_chart", "tickets per day"),
                  ("leaderboard", "agents by tickets solved")],
        "screens": ["Inbox: chat_app", "Tickets: data_table", "Customers: data_table", "Reports: bar_chart"],
    },
    "admin": {
        "label": "General business admin", "fits": "any small business admin panel not above",
        "users": "the owner and staff", "work": "see today's business and act on what needs attention",
        "main": ("data_table", "the business's main records (orders / bookings / requests) with status pills and actions"),
        "parts": [("kpi_tiles", "the 4 numbers the owner watches every day"),
                  ("line_chart", "the main activity over time"),
                  ("task_list", "what needs action today"),
                  ("donut", "the split that matters (by type / status)"),
                  ("timeline", "recent activity")],
        "screens": ["Records: data_table", "Customers: data_table", "Reports: bar_chart", "Settings: form"],
    },
}

FLOW_SOURCES = [
    "the user's reference folders (2026-11-14): refer img (POS, HR shifts, food, health, finance, restaurant, time tracker, "
    "recipes, cooking, booking, gaming, cleaning, smart home, school), chart refer img, data list ref img, form control "
    "refer img, commerce marketing refer img, communication refer img",
    "nngroup.com/articles/dashboards-preattentive", "uxdesign.cc data tables and dashboards", "Material / Carbon / Atlassian "
    "design systems: data table, empty states, notification and form guidance",
]


def menu():
    return "\n".join(f"- {k}: {f['label']} ({f['fits']})" for k, f in FLOWS.items())


def guide(kind):
    """The kind's app flow as plain lines for the 4B ("" for an unknown kind)."""
    f = FLOWS.get(kind)
    if not f:
        return ""
    part, what = f["main"]
    return (f"This kind of app ({f['label']}): used by {f['users']}; the work done on it many times a day: {f['work']}.\n"
            f"Its MAIN tool (first, the biggest part): {part} — {what}.\n"
            "Then, in order, what supports that work (part: what it holds for this business):\n"
            + "\n".join(f"- {p}: {need}" for p, need in f["parts"])
            + "\nThe app's other screens (for its menu): " + "; ".join(f["screens"])
            + "\n(A guide from how the best apps of this kind are built: keep the main tool first, adapt what each part "
              "holds to this business, leave out a part it has nothing for.)")


# ---- 🦴 the skeleton: where each part of a kind sits (the user, 2026-11-15: "find the flow first; then its rule set and
# where its columns are, correctly, for any POS / ERP / CRM / SaaS / dashboard / admin: that is what everything is built on").
# Rows top to bottom; each row = columns of 12 (span, the parts stacked in that column, "sticky" for one that stays in
# view while the page scrolls). Every part of the kind's flow is in its layout; the main tool sits where its work is done.
LAYOUTS = {
    "pos": [[(7, ["category_chips", "image_cards", "kpi_tiles"]), (5, ["invoice"], "sticky")],
            [(12, ["data_table"])]],
    "crm": [[(12, ["kpi_tiles"])], [(12, ["kanban"])],
            [(8, ["data_table"]), (4, ["task_list"])], [(6, ["funnel"]), (6, ["bar_chart"])]],
    "erp": [[(12, ["kpi_tiles"])], [(8, ["data_table"]), (4, ["alerts"])],
            [(8, ["area_chart"]), (4, ["progress_list"])], [(12, ["gantt"])]],
    "cms": [[(12, ["kpi_tiles"])], [(8, ["data_table"]), (4, ["comments"])], [(8, ["calendar"]), (4, ["files"])]],
    "analytics": [[(12, ["kpi_tiles"])], [(8, ["area_chart"]), (4, ["donut"])],
                  [(6, ["hbars"]), (6, ["heatmap"])], [(12, ["data_table"])]],
    "ecommerce_admin": [[(12, ["kpi_tiles"])], [(12, ["data_table"])],
                        [(8, ["line_chart"]), (4, ["list_thumbs"])], [(6, ["order_tracker"]), (6, ["review_list"])]],
    "inventory": [[(12, ["kpi_tiles"])], [(8, ["data_table"]), (4, ["alerts"])],
                  [(8, ["bar_chart"]), (4, ["progress_list"])], [(12, ["timeline"])]],
    "hospital": [[(12, ["kpi_tiles"])], [(8, ["week_schedule"]), (4, ["data_table"])],
                 [(6, ["bar_chart"]), (6, ["progress_list"])], [(12, ["team"])]],
    "school": [[(12, ["kpi_tiles"])], [(8, ["week_schedule"]), (4, ["agenda"])],
               [(4, ["donut"]), (8, ["bar_chart"])], [(12, ["data_table"])]],
    "hr": [[(12, ["kpi_tiles"])], [(8, ["data_table"]), (4, ["task_list"])],
           [(8, ["bar_chart"]), (4, ["donut"])], [(8, ["kanban"]), (4, ["calendar"])]],
    "lms": [[(12, ["kpi_tiles"])], [(8, ["project_cards"]), (4, ["agenda"])],
            [(8, ["bar_chart"]), (4, ["leaderboard"])], [(12, ["task_list"])]],
    "project": [[(12, ["kpi_tiles"])], [(12, ["kanban"])], [(8, ["gantt"]), (4, ["rings"])],
                [(8, ["timeline"]), (4, ["avatars"])]],
    "booking": [[(12, ["kpi_tiles"])], [(8, ["calendar"]), (4, ["data_table"])],
                [(8, ["line_chart"]), (4, ["rings"])], [(12, ["review_list"])]],
    "restaurant": [[(12, ["kpi_tiles"])], [(12, ["kanban"])], [(8, ["bar_chart"]), (4, ["hbars"])],
                   [(6, ["progress_list"]), (6, ["review_list"])]],
    "finance": [[(12, ["kpi_tiles"])], [(8, ["area_chart"]), (4, ["quick_actions", "donut"])],
                [(8, ["data_table"]), (4, ["progress_list"])]],
    "logistics": [[(12, ["kpi_tiles"])], [(8, ["map_card"]), (4, ["order_tracker"])],
                  [(8, ["data_table"]), (4, ["alerts", "donut"])]],
    "iot": [[(12, ["kpi_tiles"])], [(12, ["device_cards"])], [(8, ["line_chart"]), (4, ["gauge"])],
            [(6, ["switch_list"]), (6, ["alerts"])]],
    "helpdesk": [[(12, ["kpi_tiles"])], [(12, ["chat_app"])], [(8, ["data_table"]), (4, ["leaderboard"])],
                 [(12, ["bar_chart"])]],
    "admin": [[(12, ["kpi_tiles"])], [(8, ["data_table"]), (4, ["task_list"])],
              [(8, ["line_chart"]), (4, ["donut"])], [(12, ["timeline"])]],
}
PART_NAMES = {"invoice": "Current bill", "category_chips": "Categories", "image_cards": "Products", "kpi_tiles": "Today",
              "kanban": "Pipeline", "task_list": "Tasks", "funnel": "Funnel", "bar_chart": "By month", "area_chart": "Trend",
              "line_chart": "Trend", "progress_list": "Levels", "gantt": "Schedule", "alerts": "Alerts", "comments": "Comments",
              "calendar": "Calendar", "files": "Media", "donut": "Split", "hbars": "Top items", "heatmap": "Activity",
              "list_thumbs": "Top products", "order_tracker": "Order status", "review_list": "Reviews", "timeline": "Activity",
              "week_schedule": "This week", "team": "On duty", "agenda": "Today", "project_cards": "In progress",
              "leaderboard": "Leaderboard", "rings": "Completion", "avatars": "Team", "quick_actions": "Quick actions",
              "map_card": "Live map", "device_cards": "Devices", "gauge": "Level", "switch_list": "Scenes",
              "chat_app": "Inbox", "data_table": "Records"}


def _title(part, what):
    """A section's name from its flow words ("recent bills: bill no, time..." -> "Recent bills"), else the part's."""
    head = what.split(":", 1)[0].strip() if ":" in what else ""
    if head and len(head.split()) <= 3:
        return head[:1].upper() + head[1:]
    return PART_NAMES.get(part, part.replace("_", " ").title())


def skeleton(kind):
    """🦴 The kind's sections in its layout's order, each {"name", "what", "part", "main"?, "slot": (row, col)}, and the
    layout itself [[{"span", "parts", "sticky"}]] (None for an unknown kind). Made by M42 from the rule set, no model:
    the main tool is always there, every part once, each in its column."""
    f, lay = FLOWS.get(kind), LAYOUTS.get(kind)
    if not f or not lay:
        return None
    what = dict(f["parts"])
    what[f["main"][0]] = f["main"][1]
    secs, rows = [], []
    for r, row in enumerate(lay):
        cols = []
        for c, col in enumerate(row):
            span, parts = col[0], col[1]
            cols.append({"span": span, "parts": list(parts), "sticky": len(col) > 2 and col[2] == "sticky"})
            for p in parts:
                sec = {"name": (NAMES.get(kind) or {}).get(p) or _title(p, what.get(p, "")), "what": what.get(p, ""), "part": p, "slot": [r, c]}
                if p == f["main"][0]:
                    sec["main"] = True
                secs.append(sec)
        rows.append(cols)
    return {"kind": kind, "label": f["label"], "users": f["users"], "work": f["work"], "sections": secs, "layout": rows}


def check_layouts():
    """Every kind's layout holds its main tool and each of its parts exactly once, and each row is 12 columns."""
    bad = []
    for k, f in FLOWS.items():
        lay = LAYOUTS.get(k)
        if not lay:
            bad.append(f"{k}: no layout")
            continue
        placed = [p for row in lay for col in row for p in col[1]]
        want = [f["main"][0]] + [p for p, _ in f["parts"]]
        if sorted(placed) != sorted(want):
            bad.append(f"{k}: placed {placed} != flow {want}")
        bad += [f"{k}: row {i} is {sum(c[0] for c in row)} columns" for i, row in enumerate(lay) if sum(c[0] for c in row) != 12]
    return bad


# each kind's own name for each of its parts (the user's skeleton check, 2026-11-15: "Split", "By month", "Levels",
# "Pipeline" for a kitchen's live orders, "Today" twice): what the section is called on THIS kind's screen
NAMES = {
    "pos": {"invoice": "Current bill", "category_chips": "Categories", "image_cards": "Products", "kpi_tiles": "Today",
            "data_table": "Recent bills"},
    "crm": {"kanban": "Deal pipeline", "kpi_tiles": "Sales today", "funnel": "Lead funnel", "task_list": "Today's follow-ups",
            "data_table": "Recent leads", "bar_chart": "Won revenue by month"},
    "erp": {"data_table": "Open orders", "kpi_tiles": "Business today", "area_chart": "Sales vs purchases", "progress_list": "Line load",
            "gantt": "Production schedule", "alerts": "Alerts"},
    "cms": {"data_table": "Posts", "kpi_tiles": "Content today", "calendar": "Publishing calendar", "files": "Media library",
            "comments": "Comments to approve"},
    "analytics": {"area_chart": "Main trend", "kpi_tiles": "Headline numbers", "donut": "Share by channel", "heatmap": "Activity by hour",
                  "hbars": "Top items", "data_table": "Detail"},
    "ecommerce_admin": {"data_table": "Orders", "kpi_tiles": "Store today", "line_chart": "Sales this month", "list_thumbs": "Top products",
                        "order_tracker": "Order status", "review_list": "Latest reviews"},
    "inventory": {"data_table": "Stock items", "kpi_tiles": "Stock today", "alerts": "Below reorder level", "progress_list": "Warehouse fill",
                  "bar_chart": "Stock in vs out", "timeline": "Recent movements"},
    "hospital": {"week_schedule": "Appointments", "kpi_tiles": "Hospital today", "data_table": "Patient queue", "progress_list": "Ward beds",
                 "bar_chart": "Patients by department", "team": "Doctors on duty"},
    "school": {"week_schedule": "Timetable", "kpi_tiles": "School today", "donut": "Attendance today", "bar_chart": "Marks by class",
               "data_table": "Fee dues", "agenda": "Events today"},
    "hr": {"data_table": "Employees", "kpi_tiles": "People today", "task_list": "Leave requests", "kanban": "Hiring pipeline",
           "bar_chart": "Payroll by month",
           "donut": "Headcount by department", "calendar": "Holidays and leaves"},
    "lms": {"project_cards": "My courses", "kpi_tiles": "My learning", "bar_chart": "Learning hours", "task_list": "Assignments due",
            "leaderboard": "Top learners", "agenda": "Live classes today"},
    "project": {"kanban": "Task board", "kpi_tiles": "Projects today", "gantt": "Project timeline", "rings": "Completion by project",
                "timeline": "Recent activity", "avatars": "Team workload"},
    "booking": {"calendar": "Bookings calendar", "kpi_tiles": "Bookings today", "data_table": "Arrivals today", "rings": "Occupancy by room type",
                "line_chart": "Bookings this month", "review_list": "Guest reviews"},
    "restaurant": {"kanban": "Live orders", "kpi_tiles": "Kitchen today", "bar_chart": "Orders by hour", "hbars": "Top dishes",
                   "progress_list": "Tables", "review_list": "Latest reviews"},
    "finance": {"area_chart": "Cash flow", "kpi_tiles": "Balance", "data_table": "Transactions", "donut": "Spending by category",
                "progress_list": "Budgets", "quick_actions": "Quick actions"},
    "logistics": {"map_card": "Live map", "kpi_tiles": "Shipments today", "data_table": "Shipments", "order_tracker": "Shipment status",
                  "donut": "Status split", "alerts": "Delays"},
    "iot": {"device_cards": "Devices", "kpi_tiles": "Home today", "line_chart": "Reading today", "gauge": "Main level",
            "switch_list": "Scenes", "alerts": "Warnings"},
    "helpdesk": {"chat_app": "Inbox", "kpi_tiles": "Support today", "data_table": "Tickets", "bar_chart": "Tickets per day",
                 "leaderboard": "Top agents"},
    "admin": {"data_table": "Records", "kpi_tiles": "Today", "line_chart": "Activity over time", "task_list": "To do today",
              "donut": "By type", "timeline": "Recent activity"},
}

def check_names():
    """Every kind names each of its parts once, and no two sections of a kind share a name."""
    bad = []
    for k, f in FLOWS.items():
        parts = [f["main"][0]] + [p for p, _ in f["parts"]]
        names = NAMES.get(k) or {}
        bad += [f"{k}: no name for {p}" for p in parts if p not in names]
        got = [names.get(p) for p in parts if names.get(p)]
        if len(set(got)) < len(got):
            bad.append(f"{k}: a name twice {got}")
    return bad
