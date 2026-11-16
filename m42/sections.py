"""🧩 Section rules: how each ROLE of a page (flows.ROLES) is designed at a premium level (the user, 2026-11-14: "for every
section, a rule set: what comes in it, its shapes, its layout, its alignment, which side what goes, what design; a
premium rule set").

Data the 4B and M42's widgets follow: for each role its job, what it must hold (content), the layouts a premium page
uses for it (each will be a ready widget: its structure, alignment, shapes and when it suits), the rules every layout
of it keeps, and what never to do. TERMS maps the words a flow uses (hours, members, trainers, transformations...) to
their role, so any business's section finds its rules. Grounded in the user's premium reference shots (2026-11-14:
giant headlines with the product in front, a colour panel beside dark words, products on soft half-circles, numbers
in huge rows, collages) and in common landing-page practice.

Shared premium rules (every role): one idea per section; a clear head (eyebrow, title, one line); a visual weight that
differs from the section before; whitespace that frames, never empty halves; real photos of the business or none;
text left-aligned when it runs over 2 lines (centred only for short heads and statements); 8 px spacing steps;
2-3 type sizes per section; one accent action per section at most."""

COMMON = [
    "One idea per section; its head = eyebrow (2-3 words) + title (max ~8 words) + one line.",
    "Each section's visual weight differs from the one before (big photo → text-led → cards → band).",
    "Whitespace frames the content: no empty half of the screen, no column squeezed to fit.",
    "Paragraphs left-aligned; centre only short heads, statements and numbers.",
    "Photos are the business's own subject; a section with none uses its icon/number design, never an empty frame.",
    "One accent action per section at most; the page's main action repeats in hero, middle and end.",
    "Mobile: one column, the visual above the words, tap targets 44 px+, nothing side by side under 768 px.",
]

RULES = {
    "hero": {
        "job": "In 3 seconds: who this is, what it promises, the one thing to do next.",
        "content": ["headline 4-9 words, the visitor's gain, not the company name", "one supporting line (max 20 words)",
                    "one main action + optional second (ghost)", "2-3 proof numbers or a rating", "one strong visual of the business"],
        "layouts": {
            "split_visual": {"structure": "words left (55%), visual right (45%) bleeding to the edge or on a soft shape",
                             "align": "words left-aligned, visual vertically centred", "shape": "visual in an arch, circle, blob or rounded panel; 1-2 floating proof chips on it",
                             "suits": "most businesses; clinics, salons, schools, agencies", "photo": "needed"},
            "giant_type": {"structure": "a huge headline across the width (2 lines), the visual rising over its last line, proof and actions in a row under",
                           "align": "centred headline, the row split left / right", "shape": "visual cut-out or rounded, overlapping the text",
                           "suits": "bold brands, events, gyms, products, fashion", "photo": "needed (or a 3D object)"},
            "colour_panel": {"structure": "dark or plain side with thin + bold headline; a tall colour panel on the other side holding the visual and numbers; a white card crossing the bottom edge",
                             "align": "words left, panel right", "shape": "panel radius 28-36 px; the visual spilling out of its top",
                             "suits": "tech products, gyms, premium services, finance", "photo": "needed"},
            "full_bleed": {"structure": "a full-screen photo with a dark gradient, words over it bottom-left",
                           "align": "left, bottom third", "shape": "none: the photo is the shape",
                           "suits": "hotels, resorts, travel, restaurants, real estate", "photo": "needed, high quality"},
            "search_led": {"structure": "a headline over a search / booking box (dates, guests, location, budget) on a photo or colour",
                           "align": "centred box, words above", "shape": "the box a rounded card with shadow, fields in one row",
                           "suits": "hotels, travel, real estate, hospitals (find a doctor), course catalogues", "photo": "optional"},
            "centered_statement": {"structure": "a short centred statement, actions under, a product shot or collage below",
                                   "align": "centred", "shape": "the visual in a browser frame, device or rounded card",
                                   "suits": "software, apps, nonprofits, launches", "photo": "optional"},
            "person_portrait": {"structure": "the person (doctor, lawyer, coach, artist) large on one side, their promise and credentials on the other",
                                "align": "words left, portrait right", "shape": "portrait in an arch or on a soft shape, a credential chip",
                                "suits": "law, clinics, coaches, photographers, personal brands", "photo": "needed (a person)"},
        },
        "rules": ["Height 70-90% of the screen on desktop; the next section's top peeks in.",
                  "Headline the biggest text on the page; the accent word in the brand colour or italic.",
                  "Proof (numbers, rating) visible without scrolling.", "Never a carousel of messages; one message."],
        "never": ["the company name as the headline", "3+ buttons", "stock photo unrelated to the business", "text over a busy photo without a shade"],
    },
    "trust": {
        "job": "Right under the hero: make the promise believable at a glance.",
        "content": ["3-5 numbers with labels (years, members, patients, projects, ratings)", "or 5-8 partner / client / accreditation logos"],
        "layouts": {
            "number_row": {"structure": "3-5 big numbers in a row, label under each, thin dividers", "align": "centred per item",
                           "shape": "no cards; numbers 2.5-4 rem, counting up", "suits": "everyone", "photo": "no"},
            "logo_strip": {"structure": "a muted row of logos (grey, colour on hover), a short line before it", "align": "centred, evenly spaced",
                           "shape": "logos same height (28-36 px)", "suits": "SaaS, agencies, B2B, manufacturing", "photo": "no"},
            "badge_band": {"structure": "a coloured band with icon + number pairs", "align": "centred",
                           "shape": "full-width band, icons in soft circles", "suits": "schools, hospitals, gyms", "photo": "no"},
            "rating_bar": {"structure": "big rating (4.9★) + review count + 3 short quotes in a row", "align": "rating left, quotes right",
                           "shape": "stars in gold, quotes in light cards", "suits": "restaurants, salons, clinics, hotels", "photo": "no"},
        },
        "rules": ["Real, specific numbers (500+ weddings, 12 years), never round boasts alone.", "Short and low: 120-200 px tall."],
        "never": ["more than 5 numbers", "numbers without labels", "a full section head over a trust row"],
    },
    "offer": {
        "job": "What can be bought / joined: each item with its own name and the gain.",
        "content": ["3-8 items: name, one line of what it is / solves, price or 'from' if it has one, a photo or icon",
                    "each item's own action (book, view, enquire)"],
        "layouts": {
            "stage_rows": {"structure": "one item per row on a soft half-circle, its photo round on the arc, name big beside it, price under; rows alternate sides",
                           "align": "alternating left / right", "shape": "half-circle arcs in theme tints, round photos with a white ring",
                           "suits": "packages, signature items, rooms, premium services (2-4 items)", "photo": "needed"},
            "image_cards": {"structure": "3 or 4 cards: photo on top (4:3), name, line, price, small action",
                            "align": "card text left", "shape": "radius 16-24 px, soft shadow, photo zoom on hover",
                            "suits": "rooms, dishes, products, courses, tours (3-8 items)", "photo": "needed"},
            "icon_cards": {"structure": "3-6 cards: icon in a tinted circle, name, two lines, a link",
                           "align": "left", "shape": "outlined or soft cards; icons 48-56 px",
                           "suits": "services, practice areas, specialities without photos", "photo": "no"},
            "bento": {"structure": "tiles of different sizes: the main item large (2x2), others small around it",
                      "align": "grid", "shape": "radius 20 px, one tile in the accent", "suits": "SaaS features, agencies, tech", "photo": "optional"},
            "list_menu": {"structure": "a two-column menu: name ...... price, one line under, categories as tabs",
                          "align": "names left, prices right", "shape": "hairline dividers, serif names",
                          "suits": "restaurants, salons, clinics' treatments", "photo": "no"},
            "carousel": {"structure": "a sliding row of tall cards with arrows top-right", "align": "head left, arrows right",
                         "shape": "cards 4:5, radius 20 px", "suits": "many products, tours, models (5-10 items)", "photo": "needed"},
            "tabs_by_group": {"structure": "tabs (levels, categories, days) above a grid of the group's items", "align": "tabs centred, items left",
                              "shape": "pill tabs", "suits": "schools' programs, colleges' courses, menus", "photo": "optional"},
        },
        "rules": ["Every item named for what it is (Full Planning, Deluxe Room), never 'Service 1'.",
                  "Prices in the same place on every item; 'from' when it varies.", "3 or 4 per row on desktop, never 5+."],
        "never": ["items with the same photo", "a grid of 2 lonely items", "long paragraphs on cards"],
    },
    "why": {
        "job": "Why this one and not another: 3-6 reasons that are its own.",
        "content": ["3-6 reasons: a title (3-5 words) + one line with a fact", "optional: one photo of the place or people"],
        "layouts": {
            "photo_beside_list": {"structure": "a tall photo one side (with a floating fact chip), the reasons as an icon list on the other",
                                  "align": "photo left, list right (or swapped)", "shape": "photo in an arch or rounded 24 px",
                                  "suits": "schools, clinics, hotels, gyms", "photo": "needed"},
            "orbit": {"structure": "one round photo in the middle, the reasons around it (2-3 each side), numbered",
                      "align": "left column right-aligned, right column left-aligned", "shape": "circle with a dashed ring",
                      "suits": "products, tech, premium services", "photo": "needed"},
            "numbered_grid": {"structure": "3 or 6 reasons in a grid, each with a big outlined number 01-06",
                              "align": "left", "shape": "no cards, a hairline top border", "suits": "law, finance, agencies, editorial brands", "photo": "no"},
            "feature_rows": {"structure": "2-3 big rows: photo and words changing sides, each a reason told fully",
                             "align": "alternating", "shape": "rounded photos 4:3", "suits": "SaaS, products, hospitals", "photo": "needed"},
            "watermark_list": {"structure": "a huge faded word behind (WHY), a photo, a numbered list 001-004 with hairlines",
                               "align": "photo left, list right", "shape": "watermark 15-20 vw, 6% opacity", "suits": "bold brands, gyms, fashion", "photo": "needed"},
        },
        "rules": ["Reasons are facts (24x7 emergency, NABH accredited), not adjectives (best, quality).", "Icons all from one family."],
        "never": ["more than 6 reasons", "the same words as the offer section"],
    },
    "process": {
        "job": "Take away the fear of starting: what happens, step by step.",
        "content": ["3-5 steps: short verb title + one line", "optional: time each step takes"],
        "layouts": {
            "row_line": {"structure": "numbered circles in a row joined by a line, title and line under each",
                         "align": "centred per step", "shape": "circles 48 px in the accent", "suits": "admissions, onboarding, services", "photo": "no"},
            "timeline": {"structure": "a vertical line down the middle, steps as cards on alternate sides",
                         "align": "alternating", "shape": "node circles on the line, rounded cards", "suits": "wedding journeys, cases, treatments", "photo": "no"},
            "big_numbers": {"structure": "columns, each under a huge outlined number 01-04", "align": "left", "shape": "outlined numerals 5-7 rem",
                            "suits": "agencies, SaaS, construction", "photo": "no"},
            "sticky_side": {"structure": "the head sticks on the left while steps scroll on the right", "align": "head left, steps right",
                            "shape": "steps with hairlines", "suits": "law, consulting, finance", "photo": "no"},
        },
        "rules": ["3-5 steps only; the last step is the result the visitor wants.", "Each step starts with a verb."],
        "never": ["steps without an end result", "more than 5 steps"],
    },
    "showcase": {
        "job": "Let the work be seen: proof by picture (gallery, portfolio, projects, campus, transformations, before-after).",
        "content": ["4-9 photos of real work with short captions", "for before-after: pairs", "for projects: name, place, one fact"],
        "layouts": {
            "masonry": {"structure": "photos of mixed heights in 3 columns, caption on hover", "align": "grid",
                        "shape": "radius 12-20 px, no borders", "suits": "weddings, photographers, salons, food", "photo": "needed (6+)"},
            "collage": {"structure": "3-4 overlapping photos beside the words and a short list", "align": "words left, collage right",
                        "shape": "photos with white borders, slight overlaps", "suits": "schools, hotels, travel, NGOs", "photo": "needed (3+)"},
            "before_after": {"structure": "pairs side by side or a slider, a caption with the treatment / program and time",
                             "align": "pairs centred", "shape": "equal crops, a divider handle", "suits": "gyms (transformations), dental, salons, renovation", "photo": "needed (pairs)"},
            "project_cards": {"structure": "large cards: photo, project name, place, one number; 2 per row",
                              "align": "text left", "shape": "16:10 photos, radius 20 px", "suits": "construction, real estate, agencies (case studies)", "photo": "needed"},
            "film_strip": {"structure": "one wide row of photos that scrolls sideways", "align": "full width",
                           "shape": "tall photos 3:4", "suits": "events, restaurants, resorts", "photo": "needed (5+)"},
        },
        "rules": ["Only the business's own kind of photos; the best first.", "Captions short (2-5 words)."],
        "never": ["stock photos of other trades", "icons in place of a gallery", "photos of different styles mixed without care"],
    },
    "people": {
        "job": "Faces behind the business: trust in people (doctors, lawyers, teachers, trainers, stylists, chef, team, principal).",
        "content": ["2-8 people: photo, name, role, one credential (experience, speciality)",
                    "for one leader: a portrait and a message (principal's message, founder's note)"],
        "layouts": {
            "portrait_cards": {"structure": "cards with a tall portrait (4:5), name and role under, social links on hover",
                               "align": "centred text", "shape": "portraits in arches or rounded 20 px", "suits": "doctors, trainers, stylists, faculty", "photo": "needed"},
            "leader_message": {"structure": "one portrait large, a message in quotes beside it, name and signature line",
                               "align": "portrait left, message right", "shape": "arch portrait, big quote mark", "suits": "schools (principal), founders, NGOs", "photo": "needed"},
            "compact_row": {"structure": "round photos in a row with name and role", "align": "centred", "shape": "circles 96-120 px",
                            "suits": "large teams, agencies", "photo": "needed"},
            "credential_list": {"structure": "no photos: names with role, experience and speciality in a clean list", "align": "left",
                                "shape": "hairline rows", "suits": "law firms, CA firms (when no photos)", "photo": "no"},
        },
        "rules": ["Same photo style for everyone (crop, background).", "Credentials specific (MS Ortho, 15 yrs)."],
        "never": ["stock models as staff", "people without roles"],
    },
    "proof": {
        "job": "Other people's words: the visitor believes them more than the business.",
        "content": ["3-6 testimonials: 1-3 sentences, specific result, name, role / place, rating", "optional: one with a photo or video"],
        "layouts": {
            "big_quote": {"structure": "one large quote in the spotlight (with photo), 2-3 small ones beside it", "align": "big left, small right",
                          "shape": "big quote mark, the main card in the accent", "suits": "everyone", "photo": "optional"},
            "wall": {"structure": "masonry of quote cards of different heights, the first one coloured", "align": "grid",
                     "shape": "radius 16-20 px", "suits": "many reviews: SaaS, restaurants, courses", "photo": "no"},
            "slider": {"structure": "one quote at a time, large, with arrows and dots", "align": "centred", "shape": "serif quote, avatar under",
                       "suits": "luxury, weddings, hotels", "photo": "optional"},
            "rating_summary": {"structure": "the overall rating big on the left (4.9, 320 reviews, stars), quotes on the right",
                               "align": "split", "shape": "stars gold", "suits": "clinics, salons, restaurants, hotels", "photo": "no"},
            "results_cards": {"structure": "case results: the number won or achieved big, the client's line under", "align": "left",
                              "shape": "cards with a big figure", "suits": "law, finance, agencies, coaching (toppers)", "photo": "no"},
        },
        "rules": ["Specific words (what changed), real-sounding names and places.", "On a themed page this section often becomes the deep colour band."],
        "never": ["vague praise only ('great service')", "more than 6 on the home page"],
    },
    "pricing": {
        "job": "Make choosing easy: 2-4 options, what each includes, the usual choice clear.",
        "content": ["2-4 plans: name, price + unit (per month, per person), 4-6 inclusions, one marked 'Most chosen'",
                    "optional: a note (GST, custom quotes)"],
        "layouts": {
            "featured_middle": {"structure": "3 plans side by side, the middle one raised on the deep colour", "align": "text left in each",
                                "shape": "middle card scaled 1.04, radius 24 px", "suits": "gyms, SaaS, courses, salons", "photo": "no"},
            "compare_table": {"structure": "one table: plans as columns, inclusions as rows with ticks", "align": "feature names left, ticks centred",
                              "shape": "the chosen column tinted", "suits": "SaaS, insurance, schools' fees, packages with many inclusions", "photo": "no"},
            "package_rows": {"structure": "each package a wide row: name and line left, inclusions middle, price and action right",
                             "align": "three columns", "shape": "hairlines", "suits": "weddings, events, tours", "photo": "optional"},
            "from_cards": {"structure": "cards with 'from ₹...' and a short list, one action each", "align": "left", "shape": "soft cards",
                           "suits": "clinics, salons, construction", "photo": "optional"},
        },
        "rules": ["Same unit on every plan; the usual choice marked.", "Inclusions as short ticks."],
        "never": ["more than 4 plans", "hidden prices behind 'contact us' when they are known"],
    },
    "listings": {
        "job": "Let the visitor browse and pick: properties, tours, courses, products, models, categories.",
        "content": ["6-12 items: photo, name, 2-3 facts (price, size, place, duration), tag", "filters or a search above"],
        "layouts": {
            "filter_grid": {"structure": "filter chips / search above a grid of cards", "align": "chips left, grid", "shape": "cards 4:3 photos, tags on the photo",
                            "suits": "real estate, courses, products", "photo": "needed"},
            "category_tiles": {"structure": "large tiles with a photo and the category name over it", "align": "name bottom-left",
                               "shape": "radius 20 px, dark gradient", "suits": "shops, travel destinations", "photo": "needed"},
            "map_list": {"structure": "a list on the left, a map on the right", "align": "split", "shape": "list rows with thumbnails",
                         "suits": "real estate, branches, hospitals' locations", "photo": "optional"},
            "logo_grid": {"structure": "a grid of logos or names (sponsors, industries served)", "align": "centred", "shape": "light tiles",
                          "suits": "events (sponsors), manufacturing (industries)", "photo": "no"},
        },
        "rules": ["Facts in the same order on every card.", "A clear empty state when nothing matches."],
        "never": ["cards without a price or key fact", "more than 12 on the home page"],
    },
    "schedule": {
        "job": "Time: when (timetables, class schedule, agenda, events, opening hours, batch timings).",
        "content": ["days / times with what happens", "for hours: each day's hours, today highlighted", "for events: date, title, place"],
        "layouts": {
            "week_grid": {"structure": "days as columns, time slots as rows, classes as coloured blocks", "align": "grid",
                          "shape": "rounded blocks in the theme tints", "suits": "gyms, yoga, coaching batches", "photo": "no"},
            "agenda_list": {"structure": "time on the left, session title and speaker on the right, day tabs above", "align": "two columns",
                            "shape": "hairlines, tabs as pills", "suits": "events, conferences, schools' events", "photo": "no"},
            "hours_card": {"structure": "a card: each day with hours, today in bold, 'open now' dot", "align": "days left, hours right",
                           "shape": "card with soft shadow beside the map / address", "suits": "restaurants, clinics, salons, shops", "photo": "no"},
            "event_cards": {"structure": "date block (day big, month small) + title + place + action", "align": "left",
                            "shape": "the date in an accent square", "suits": "schools, NGOs, temples, communities", "photo": "optional"},
        },
        "rules": ["Today / the next item highlighted.", "Times in one format (9:00 AM)."],
        "never": ["a schedule as a paragraph", "past events on the home page"],
    },
    "impact": {
        "job": "Show the difference made: what a gift or a choice achieves.",
        "content": ["1-3 impact numbers with what they mean", "one real story (photo, name, before / after)"],
        "layouts": {
            "numbers_story": {"structure": "big impact numbers on one side, one story with photo on the other", "align": "split",
                              "shape": "numbers huge, story in a card", "suits": "nonprofits, hospitals, schools", "photo": "needed"},
            "counter_band": {"structure": "a full-width deep band with 3 counters and one line", "align": "centred", "shape": "band in the deep colour",
                             "suits": "everyone with impact data", "photo": "no"},
            "gift_ladder": {"structure": "what each amount does (₹500 feeds 10 children...) as steps", "align": "left",
                            "shape": "steps with amounts in the accent", "suits": "nonprofits", "photo": "optional"},
        },
        "rules": ["Numbers say what changed for people, not only how big the organisation is."],
        "never": ["numbers without a meaning"],
    },
    "faq": {
        "job": "Answer the doubts that stop the visitor acting.",
        "content": ["4-8 questions a visitor really asks (fees, timing, process, policy), short clear answers"],
        "layouts": {
            "accordion": {"structure": "questions as rows that open, the first open", "align": "left, max 760 px wide, centred block",
                          "shape": "hairlines or soft cards, a plus that turns", "suits": "everyone", "photo": "no"},
            "split_faq": {"structure": "head and a contact line on the left (sticky), questions on the right", "align": "split",
                          "shape": "accordion right", "suits": "services, law, finance, clinics", "photo": "no"},
            "two_columns": {"structure": "questions and answers shown open in two columns", "align": "left", "shape": "no boxes",
                            "suits": "short answers, SaaS, events", "photo": "no"},
        },
        "rules": ["Questions in the visitor's words.", "Answers 1-3 sentences."],
        "never": ["more than 8 on the home page", "marketing in place of answers"],
    },
    "location": {
        "job": "Where and how to reach: address, map, hours, phones, directions, branches.",
        "content": ["address, phone, email, hours, a map", "for many branches: a list"],
        "layouts": {
            "map_card": {"structure": "a map filling one side, a card with address / hours / phone / directions over or beside it",
                         "align": "map right, card left", "shape": "card radius 20 px with shadow", "suits": "restaurants, clinics, salons, hotels", "photo": "no"},
            "contact_columns": {"structure": "3 columns: visit, call, write, each with an icon and details", "align": "centred",
                                "shape": "icons in tinted circles", "suits": "everyone", "photo": "no"},
            "branches_list": {"structure": "a list of branches with area, phone, timings; a map", "align": "split",
                              "shape": "rows with hairlines", "suits": "hospitals, chains, schools with campuses", "photo": "no"},
        },
        "rules": ["Phone tappable, address copyable.", "Hours with today highlighted."],
        "never": ["a map without the written address"],
    },
    "action": {
        "job": "Close the page: one strong line and the main action (book, enrol, call, buy, donate), often with a form.",
        "content": ["a headline (the gain once more), one line", "the main action, optionally a short form (3-5 fields)",
                    "a reassurance (no fees, reply in 24 h)"],
        "layouts": {
            "band_cta": {"structure": "a full-width band in the accent / deep colour, headline and action centred", "align": "centred",
                         "shape": "band with a soft pattern or glow", "suits": "everyone", "photo": "no"},
            "form_split": {"structure": "words and reassurances on the left, a short form card on the right", "align": "split",
                           "shape": "form card raised with shadow", "suits": "clinics, schools, law, wedding, construction", "photo": "optional"},
            "photo_cta": {"structure": "a full-width photo with a shade, the headline and action over it", "align": "centred or left",
                          "shape": "the photo is the shape", "suits": "hotels, travel, events, restaurants", "photo": "needed"},
        },
        "rules": ["The same action words as the hero.", "A form asks only what is needed to reply."],
        "never": ["a second different action", "a form of more than 6 fields"],
    },
}

# the words flows and businesses use for a section, and the role whose rules it follows (any language: the 4B maps
# its own words to these; this list is what the flows use)
TERMS = {
    "hours": "schedule", "opening hours": "schedule", "timetable": "schedule", "class schedule": "schedule", "agenda": "schedule",
    "events": "schedule", "batch timings": "schedule", "calendar": "schedule",
    "location": "location", "map": "location", "contact": "location", "branches": "location", "visit us": "location",
    "members": "trust", "numbers": "trust", "stats": "trust", "achievements": "trust", "awards": "trust", "logos": "trust", "partners": "trust",
    "programs": "offer", "programmes": "offer", "classes": "offer", "services": "offer", "packages": "offer", "rooms": "offer",
    "menu": "offer", "dishes": "offer", "treatments": "offer", "practice areas": "offer", "specialities": "offer", "courses": "offer",
    "features": "offer", "products": "offer", "bestsellers": "offer",
    "why": "why", "why choose us": "why", "about": "why", "our story": "why", "values": "why",
    "trainers": "people", "doctors": "people", "team": "people", "faculty": "people", "teachers": "people", "stylists": "people",
    "advocates": "people", "speakers": "people", "principal": "people", "founder": "people", "chef": "people",
    "transformations": "showcase", "before after": "showcase", "gallery": "showcase", "portfolio": "showcase", "projects": "showcase",
    "campus life": "showcase", "case studies": "showcase", "lookbook": "showcase",
    "testimonials": "proof", "reviews": "proof", "what parents say": "proof", "case results": "proof", "toppers": "proof", "stories": "proof",
    "plans": "pricing", "fees": "pricing", "membership": "pricing", "tickets": "pricing", "prices": "pricing",
    "properties": "listings", "destinations": "listings", "categories": "listings", "models": "listings", "sponsors": "listings",
    "steps": "process", "how it works": "process", "admission process": "process", "journey": "process",
    "impact": "impact", "faq": "faq", "questions": "faq",
    "apply": "action", "book": "action", "enquiry": "action", "donate": "action", "cta": "action",
}


def roles_of(name):
    """Every role a section's name points to, in TERMS order ("Location & Hours": schedule, location)."""
    n = " ".join(str(name or "").lower().split())
    if n in RULES:
        return [n]
    return list(dict.fromkeys(([TERMS[n]] if n in TERMS else []) + [r for t, r in TERMS.items() if t in n]))


def role_of(name):
    """The role a section's name points to (TERMS, then the roles' own names), or ""."""
    n = " ".join(str(name or "").lower().split())
    if n in RULES:
        return n
    if n in TERMS:
        return TERMS[n]
    hits = [r for t, r in TERMS.items() if t in n]
    return hits[0] if hits else ""


def guide(role, mood="", photos=True):
    """A role's rules as plain lines for the 4B: its job, content, the layouts that suit (with or without photos), the
    rules and the never-dos."""
    r = RULES.get(role)
    if not r:
        return ""
    lays = [(n, l) for n, l in r["layouts"].items() if photos or not l["photo"].startswith("needed")]
    return (f"Section role {role}: {r['job']}\nIt holds: " + "; ".join(r["content"]) + "\nLayouts a premium page uses for it:\n"
            + "\n".join(f"- {n}: {l['structure']} (align: {l['align']}; shape: {l['shape']}; suits: {l['suits']})" for n, l in lays)
            + "\nRules: " + " ".join(r["rules"]) + "\nNever: " + "; ".join(r["never"]))


def brief(role):
    """A role's rules in one short line for the 4B writing a section's content (its job, what it holds, its rules;
    the layout is chosen after, from the blocks its content fits), or ""."""
    r = RULES.get(role)
    if not r:
        return ""
    return f"{role}: {r['job']} It holds: {'; '.join(r['content'])}. {' '.join(r['rules'][:2])} Never: {'; '.join(r['never'][:3])}."


def layout_count():
    return sum(len(r["layouts"]) for r in RULES.values())
