"""🧭 Page flows: how a premium landing page of each KIND of business runs, top to bottom (the user, 2026-11-14: "a rule
set first: for a landing page, what comes under the hero, then under that... and it must be dynamic: a school's flow
differs from a lawyer's, a hospital's, a hotel's; research it").

Data, not code: researched from industry practice (2026-11-14: school, law firm, hospital, hotel, restaurant, gym,
real estate, dental, salon / spa, wedding planner, SaaS, e-commerce, courses, construction, travel, nonprofit, events
and hero patterns; sources in FLOW_SOURCES). The 4B reads the request, picks the kind nearest to it (or composes a flow
from the nearest kinds for a business not here), and plans the page by its flow; the rules are a guide it adapts,
never words matched in the request. A kind can be added here at any time.

ROLES are the jobs a section does on a page (one widget family each); a kind's flow is its roles in order, with what
each must hold for that business ("need": the widget's content), and the one action the page leads to (goal)."""

# ---- the jobs a section can do (each will have its own premium widgets: widgets for a role are interchangeable)
ROLES = {
    "hero": "the first screen: who it is, what it promises, the one action; a strong picture of the business",
    "trust": "a quick proof row right under the hero: numbers, ratings, years, partner logos, awards",
    "offer": "what is offered: services, products, packages, programs, rooms, dishes, plans (each with its own name)",
    "why": "why choose it: 3-6 reasons that are this business's own strengths, each with a fact",
    "process": "how it works / the steps from the first contact to the result (3-5 steps)",
    "showcase": "its work seen: a gallery, portfolio, projects, before-after, campus or property photos",
    "people": "the people behind it: doctors, lawyers, teachers, trainers, stylists, chef, team, with roles",
    "proof": "what clients say: reviews, testimonials, case results, ratings",
    "pricing": "prices / plans / packages with what each includes, one marked as the usual choice",
    "listings": "things to browse and pick: properties, tours, courses, products, with a filter or search",
    "schedule": "time-based: timetable, class schedule, agenda, events calendar, opening hours",
    "impact": "the difference it makes: impact numbers and one real story (nonprofits, schools, hospitals)",
    "faq": "the questions a visitor asks before acting, answered",
    "location": "where and when: address, map, hours, how to reach, contact numbers",
    "action": "the closing call: one strong line and the main action (book, enrol, call, buy, donate), often with a form",
}

# ---- the flows: kind -> {"label", "fits", "goal", "mood", "hero", "flow": [(role, need), ...]}
# (hero: the hero's job for this kind: "search" = a search / booking box in it; "proof" = proof in it; "visual" = a big
# picture of the place / product; "people" = the person / team)
FLOWS = {
    "school": {
        "label": "School", "fits": "schools, play schools, kindergartens, CBSE / ICSE / state board schools",
        "goal": "book a campus visit / apply for admission", "mood": "warm, safe, proud, bright", "hero": "visual",
        "flow": [("hero", "the school's promise to parents, a campus or children photo, Apply / Book a visit"),
                 ("trust", "years, students, board results %, awards, student-teacher ratio"),
                 ("offer", "academic programs by level (pre-primary, primary, middle, senior) or streams"),
                 ("why", "safety, teachers, labs, sports, values: each with a fact"),
                 ("showcase", "campus life: classrooms, labs, sports, events photos"),
                 ("people", "principal's message with photo, key teachers"),
                 ("process", "the admission steps: enquiry, visit, test / interaction, admission"),
                 ("proof", "what parents say"),
                 ("schedule", "upcoming events / academic calendar highlights"),
                 ("faq", "fees, transport, timings, age criteria"),
                 ("action", "apply now / book a campus tour with a short form")]},
    "college": {
        "label": "College / coaching / courses", "fits": "colleges, coaching centres, tuition, online courses, training institutes",
        "goal": "enrol / book a free demo class", "mood": "ambitious, credible, clear", "hero": "proof",
        "flow": [("hero", "the outcome promised (results, careers), with a proof line, Enrol / Free demo"),
                 ("trust", "selections / placements, students trained, success %, years"),
                 ("offer", "courses or batches with duration, mode, level"),
                 ("why", "faculty, method, material, results"),
                 ("people", "faculty with subjects and experience"),
                 ("proof", "toppers / alumni with results and words"),
                 ("pricing", "fees per course or batch, what is included"),
                 ("schedule", "batch timings / next batch dates"),
                 ("faq", "eligibility, refund, online / offline, materials"),
                 ("action", "enrol / book a demo form")]},
    "law": {
        "label": "Law firm / advocate", "fits": "law firms, advocates, legal consultants, notaries",
        "goal": "book a consultation", "mood": "serious, trustworthy, calm authority", "hero": "people",
        "flow": [("hero", "what the firm does for whom, in one clear line; Book a consultation; a calm photo of the team or office"),
                 ("trust", "years of practice, cases handled, success rate, bar memberships"),
                 ("offer", "practice areas, each with what it covers"),
                 ("why", "experience, approach, confidentiality, results"),
                 ("people", "the advocates with their practice and experience"),
                 ("proof", "case results and client words"),
                 ("process", "how a case goes: consult, strategy, representation, resolution"),
                 ("faq", "fees, first consultation, documents needed"),
                 ("action", "consultation form with phone")]},
    "hospital": {
        "label": "Hospital / multi-speciality", "fits": "hospitals, multi-speciality centres, diagnostic centres, nursing homes",
        "goal": "book an appointment / find a doctor", "mood": "caring, clean, reassuring, capable", "hero": "search",
        "flow": [("hero", "care promise; quick tasks in it: find a doctor, book appointment, emergency number"),
                 ("trust", "beds, doctors, specialities, accreditations (NABH), years"),
                 ("offer", "specialities / centres of excellence"),
                 ("people", "senior doctors with speciality and experience"),
                 ("why", "technology, 24x7 emergency, insurance, care"),
                 ("impact", "patients treated, surgeries, one patient story"),
                 ("proof", "patient testimonials"),
                 ("location", "emergency contact, address, map, visiting hours, insurance partners"),
                 ("faq", "appointments, insurance, reports, visiting"),
                 ("action", "book an appointment form")]},
    "clinic": {
        "label": "Clinic / dental / specialist", "fits": "dental clinics, skin / eye / physio clinics, single-doctor practices",
        "goal": "book an appointment", "mood": "gentle, clean, modern, personal", "hero": "people",
        "flow": [("hero", "the doctor or care promise with a warm photo, Book appointment"),
                 ("trust", "years, patients treated, ratings, certifications"),
                 ("offer", "treatments with what they solve"),
                 ("people", "the doctor(s) with qualifications"),
                 ("showcase", "before-after results or the clinic"),
                 ("why", "painless care, technology, hygiene, timings"),
                 ("proof", "patient reviews"),
                 ("pricing", "treatment prices or 'starting from'"),
                 ("location", "address, hours, map"),
                 ("action", "booking form")]},
    "hotel": {
        "label": "Hotel / resort / homestay", "fits": "hotels, resorts, homestays, villas, lodges",
        "goal": "book a stay (check availability)", "mood": "inviting, restful, aspirational", "hero": "search",
        "flow": [("hero", "a big photo of the place; a booking box (dates, guests) right in it"),
                 ("trust", "ratings, awards, best rate guarantee"),
                 ("offer", "rooms / suites with photo, size, price per night"),
                 ("why", "the stay's highlights: view, pool, food, location"),
                 ("showcase", "gallery of the property, rooms, food, surroundings"),
                 ("listings", "experiences / activities nearby"),
                 ("proof", "guest reviews"),
                 ("location", "map, how to reach, check-in times, policies"),
                 ("faq", "check-in, pets, cancellation, parking"),
                 ("action", "book now")]},
    "restaurant": {
        "label": "Restaurant / cafe / bakery", "fits": "restaurants, cafes, bakeries, cloud kitchens, sweet shops, bars",
        "goal": "reserve a table / order online", "mood": "appetising, warm, lively", "hero": "visual",
        "flow": [("hero", "a mouth-watering food or place photo; Reserve / Order"),
                 ("offer", "signature dishes / menu highlights with prices"),
                 ("why", "the story: chef, ingredients, origin, what makes it special"),
                 ("showcase", "food and ambience gallery"),
                 ("proof", "reviews and ratings"),
                 ("schedule", "opening hours, specials by day, events"),
                 ("location", "address, map, phone, hours"),
                 ("action", "reservation / order buttons")]},
    "gym": {
        "label": "Gym / fitness / yoga / sports", "fits": "gyms, fitness studios, yoga, martial arts, sports academies, dance",
        "goal": "book a free trial / join", "mood": "energetic, bold, motivating", "hero": "visual",
        "flow": [("hero", "an energetic training photo, the promise, Free trial / Join now"),
                 ("trust", "members, trainers, years, transformations"),
                 ("offer", "programs / classes with what each trains"),
                 ("why", "equipment, coaches, community, results"),
                 ("people", "trainers with speciality"),
                 ("showcase", "transformations (before-after) or the space"),
                 ("pricing", "membership plans, one highlighted"),
                 ("schedule", "class timetable"),
                 ("proof", "member stories"),
                 ("action", "free trial form")]},
    "salon": {
        "label": "Salon / spa / beauty", "fits": "salons, spas, beauty parlours, barbers, nail and makeup studios",
        "goal": "book an appointment", "mood": "elegant, relaxing, polished", "hero": "visual",
        "flow": [("hero", "a beautiful result photo, the promise, Book now"),
                 ("offer", "service categories with starting prices"),
                 ("showcase", "gallery of real work / before-after"),
                 ("people", "stylists / therapists"),
                 ("why", "products used, hygiene, experience"),
                 ("pricing", "packages / memberships"),
                 ("proof", "client reviews"),
                 ("location", "address, hours"),
                 ("action", "booking")]},
    "wedding": {
        "label": "Wedding / event planner", "fits": "wedding planners, event managers, decorators, caterers for events",
        "goal": "book a consultation", "mood": "romantic, luxurious, joyful", "hero": "visual",
        "flow": [("hero", "a dreamy wedding photo, the promise, Book a consultation"),
                 ("trust", "weddings done, years, happy couples, cities"),
                 ("offer", "services / packages: full planning, partial, day-of, destination"),
                 ("showcase", "portfolio of real weddings by style or venue"),
                 ("process", "planning journey: consult, design, plan, the day"),
                 ("pricing", "packages with what each includes (or starting from)"),
                 ("proof", "couples' words"),
                 ("faq", "budget, booking ahead, destinations, vendors"),
                 ("action", "enquiry form with date and guests")]},
    "realestate": {
        "label": "Real estate / builder", "fits": "real estate agencies, builders, developers, property consultants",
        "goal": "enquire / book a site visit", "mood": "aspirational, solid, trustworthy", "hero": "search",
        "flow": [("hero", "a striking property photo with a property search (location, type, budget)"),
                 ("listings", "featured properties with price, area, location"),
                 ("trust", "projects delivered, families, years, RERA"),
                 ("offer", "services: buy, sell, rent, home loans, interiors"),
                 ("why", "transparency, legal checks, locations, support"),
                 ("people", "agents / the builder's team"),
                 ("proof", "buyer testimonials"),
                 ("action", "site visit / enquiry form")]},
    "saas": {
        "label": "Software / SaaS / app", "fits": "software products, SaaS tools, mobile apps, startups' products",
        "goal": "start a free trial / book a demo", "mood": "clear, modern, confident", "hero": "visual",
        "flow": [("hero", "the outcome in one line, a product screenshot, Start free / Book a demo"),
                 ("trust", "customer logos, users, ratings"),
                 ("why", "the problem and how it is solved"),
                 ("offer", "key features (4-6), each with its benefit"),
                 ("process", "how it works in 3 steps"),
                 ("proof", "customer stories with results"),
                 ("pricing", "2-3 plans, the middle highlighted"),
                 ("faq", "security, setup, cancel, support"),
                 ("action", "the final trial / demo call")]},
    "shop": {
        "label": "Shop / e-commerce / brand", "fits": "online shops, boutiques, product brands, D2C stores, retail",
        "goal": "shop now / buy", "mood": "desirable, fresh, easy", "hero": "visual",
        "flow": [("hero", "the hero product or collection, the offer, Shop now"),
                 ("listings", "top categories"),
                 ("offer", "bestsellers / new arrivals with prices"),
                 ("why", "quality, delivery, returns, payment safety"),
                 ("showcase", "the brand story / lookbook"),
                 ("proof", "customer reviews with ratings"),
                 ("action", "newsletter / offer signup")]},
    "construction": {
        "label": "Construction / contractor / interiors", "fits": "builders, contractors, civil works, interior designers, architects, renovators",
        "goal": "get a quote / free consultation", "mood": "solid, precise, capable", "hero": "visual",
        "flow": [("hero", "a finished project photo, what they build, Get a quote"),
                 ("trust", "projects completed, sq.ft built, years, clients"),
                 ("offer", "services with what each covers"),
                 ("showcase", "featured projects with photos"),
                 ("process", "from consultation to handover"),
                 ("why", "quality, timelines, materials, warranty"),
                 ("proof", "client testimonials"),
                 ("action", "quote request form")]},
    "travel": {
        "label": "Travel / tours", "fits": "travel agencies, tour operators, holiday planners, pilgrimage tours",
        "goal": "enquire / book a tour", "mood": "adventurous, dreamy, joyful", "hero": "search",
        "flow": [("hero", "a breathtaking destination photo with a trip search (where, when)"),
                 ("listings", "popular destinations"),
                 ("offer", "tour packages with days, price, highlights"),
                 ("why", "custom plans, support, safety, value"),
                 ("trust", "travellers served, destinations, ratings"),
                 ("proof", "traveller stories"),
                 ("faq", "visa, payment, cancellation"),
                 ("action", "plan my trip enquiry")]},
    "nonprofit": {
        "label": "Nonprofit / NGO / trust", "fits": "NGOs, charities, trusts, foundations, community groups, temples' trusts",
        "goal": "donate / volunteer", "mood": "hopeful, human, sincere", "hero": "visual",
        "flow": [("hero", "a real human photo, what it does in one plain line, Donate"),
                 ("impact", "what a gift achieves, impact numbers"),
                 ("offer", "programs / causes"),
                 ("showcase", "one real story with photos"),
                 ("trust", "registrations (80G, 12A), ratings, partners"),
                 ("people", "founders / volunteers"),
                 ("action", "donate / volunteer with amounts")]},
    "event": {
        "label": "Event / conference / festival", "fits": "conferences, summits, concerts, festivals, workshops, exhibitions",
        "goal": "buy tickets / register", "mood": "exciting, bold, urgent", "hero": "visual",
        "flow": [("hero", "the event name, date, venue, a countdown, Get tickets"),
                 ("trust", "attendees, speakers, sessions, past editions"),
                 ("people", "speakers / artists with photos"),
                 ("schedule", "agenda by day and time"),
                 ("pricing", "ticket tiers"),
                 ("listings", "sponsors / partners"),
                 ("location", "venue, map, travel"),
                 ("faq", "refunds, entry, parking"),
                 ("action", "register / buy tickets")]},
    "agency": {
        "label": "Agency / IT services / consultancy", "fits": "digital agencies, IT companies, consultancies, marketing and design studios",
        "goal": "book a call / get a proposal", "mood": "smart, confident, modern", "hero": "proof",
        "flow": [("hero", "the result delivered for clients, a proof line, Book a call"),
                 ("trust", "client logos, projects, years, ratings"),
                 ("offer", "services with outcomes"),
                 ("showcase", "case studies with results"),
                 ("process", "how they work"),
                 ("people", "the team / leadership"),
                 ("proof", "client testimonials"),
                 ("action", "contact / proposal form")]},
    "creative": {
        "label": "Photographer / artist / personal portfolio", "fits": "photographers, artists, designers, freelancers, personal brands, coaches",
        "goal": "book / hire / contact", "mood": "personal, artful, distinctive", "hero": "people",
        "flow": [("hero", "the person or their best work, a one-line identity, Book / Contact"),
                 ("showcase", "selected work, large"),
                 ("offer", "services / what they do"),
                 ("why", "about: story, style, approach"),
                 ("proof", "client words / brands worked with"),
                 ("pricing", "packages or 'starting from'"),
                 ("action", "booking / contact form")]},
    "finance": {
        "label": "Finance / insurance / CA / bank", "fits": "chartered accountants, tax consultants, insurance agents, finance companies, banks, loans",
        "goal": "free consultation / apply", "mood": "secure, precise, trustworthy", "hero": "proof",
        "flow": [("hero", "the financial outcome promised, Get a free consultation"),
                 ("trust", "clients, years, amount managed, certifications"),
                 ("offer", "services / products (tax, audit, insurance, loans)"),
                 ("why", "expertise, compliance, transparency, support"),
                 ("process", "how it works"),
                 ("people", "the experts"),
                 ("proof", "client testimonials"),
                 ("faq", "fees, documents, timelines"),
                 ("action", "consultation form")]},
    "auto": {
        "label": "Automobile / dealership / service", "fits": "car and bike dealerships, service centres, rentals, auto parts",
        "goal": "book a test drive / service", "mood": "powerful, sleek, reliable", "hero": "visual",
        "flow": [("hero", "the vehicle big, the offer, Book a test drive / service"),
                 ("listings", "models / vehicles with price"),
                 ("offer", "services: sales, service, finance, insurance"),
                 ("why", "genuine parts, trained technicians, warranty"),
                 ("trust", "vehicles sold / serviced, years, ratings"),
                 ("proof", "customer reviews"),
                 ("location", "showroom, hours, map"),
                 ("action", "test drive / service booking")]},
    "industry": {
        "label": "Manufacturing / B2B / industrial", "fits": "manufacturers, exporters, industrial suppliers, factories, B2B products",
        "goal": "request a quote", "mood": "robust, precise, global", "hero": "proof",
        "flow": [("hero", "what they make and for whom, Request a quote"),
                 ("trust", "capacity, clients, countries, certifications (ISO)"),
                 ("offer", "product range with specs"),
                 ("why", "quality control, capacity, delivery, R&D"),
                 ("showcase", "the facility / process photos"),
                 ("listings", "industries served"),
                 ("proof", "client logos and words"),
                 ("action", "quote request form")]},
}

FLOW_SOURCES = [
    "cubecreative.design/blog/private-school-marketing/top-school-enrollment-website-pages",
    "paperstreet.com/blog/design-details-of-a-website-home-page", "jurisdigital.com/guides/above-the-fold-law-firm-website-best-practices",
    "tbhcreative.com/blog/hospital-website-design-best-practices", "baymard.com/blog/travel-site-ux-best-practices",
    "merchants.doordash.com/en-us/blog/restaurant-homepage", "cyberoptik.net/blog/best-gym-websites",
    "b12.io/resource-center/website-design/real-estate-web-design-best-practices-for-2026",
    "dentistryiq.com (the 7 most important pages of a dentist's website)", "colorlib.com/wp/beauty-salon-websites",
    "creativemarketing.ai/industries/showcase-portfolio/wedding-planners-photographers", "medium.com/cruip (SaaS landing page)",
    "baymard.com/blog/ecommerce-ux-best-practices", "maven.com/resources/winning-landing-page", "projul.com/blog/construction-website-design-guide",
    "elevationweb.org (anatomy of a nonprofit homepage)", "landingi.com/blog/event-marketing", "blog.logrocket.com/ux-design/hero-section-examples-best-practices",
]


# the kinds whose closing step is a FORM the visitor fills (a booking, an enquiry, a quote), part of each kind's rule
# set (its "action" need above); the others close with a call to act (buy, start a trial, donate, register)
ACTION_FORM = {"school", "college", "law", "hospital", "clinic", "hotel", "restaurant", "gym", "salon", "wedding",
               "realestate", "construction", "travel", "agency", "creative", "finance", "auto", "industry"}


def menu():
    """The kinds as the 4B reads them, to pick the nearest."""
    return "\n".join(f"- {k}: {f['label']} ({f['fits']})" for k, f in FLOWS.items())


def guide(kind):
    """The flow of a kind as plain lines for the 4B ("" for an unknown kind)."""
    f = FLOWS.get(kind)
    if not f:
        return ""
    return (f"This kind of page ({f['label']}): the visitor is led to {f['goal']}; the feel: {f['mood']}.\n"
            "Its sections, top to bottom (the role of each, and what it holds for this business):\n"
            + "\n".join(f"{n + 1}. {r}: {need}" for n, (r, need) in enumerate(f["flow"]))
            + "\n(A guide from how the best pages of this kind are built: keep its order and roles, adapt what each holds "
              "to this business, leave out a role it has nothing for, add one only for a real need.)")
