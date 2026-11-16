"""⚖ Weightage catalogue: the section compositions of the user's own premium reference pages (the user, 2026-11-14:
"the 75 layouts all feel like cards; take the weightage from my reference folder's landing pages and replace them").

Studied frame by frame (2026-11-14) from D:/SAGE_CDSRA_POC/refer landing page img and video: 8 page videos (an incident
platform "Resq", an app "Passion Finder", a social tool "Wello", a supplements shop "BetterVits", an investing app
"ProFinance", an AI brand "AIAF", an HR platform "CoreHR", a bank "Finix") and 4 shots (a fruit poster, an energy drink,
a security camera, a tea brand). Each entry: the role it serves (flows.ROLES), what the composition IS (where the
weight sits, what overlaps what, which side holds what), the reference it comes from, and what it needs. These replace
the card-like layouts in sections.RULES as the blocks to build (blocks.py); a card grid is kept only where a role
really is a grid of equal things."""

W = {}


def w(name, role, structure, ref, photo="optional", items=(0, 0)):
    W[name] = {"role": role, "structure": structure, "ref": ref, "photo": photo, "items": items}


# ---- hero (10)
w("hero.spotlight_mockup", "hero", "dark stage, a light beam from one corner, centred headline and two actions, the product (dashboard / app / photo) "
  "rising from the bottom edge in a frame", "Resq")
w("hero.faces_sides", "hero", "a warm blurred gradient band, two people's photos at the left and right edges, the headline centred between "
  "them, store / action buttons under", "Passion Finder", "needed (2 people or images)")
w("hero.pedestal", "hero", "the product(s) standing on soft geometric pedestals (cubes, cylinders) on a pastel floor, the headline left; a thin "
  "strip under the hero with a promise (free shipping, a cause)", "BetterVits", "needed")
w("hero.doodle_block", "hero", "a bright colour block holding the headline and a hand-drawn arrow pointing to the action; app screens / photos "
  "overlap the block's right edge", "ProFinance", "needed")
w("hero.network", "hero", "the headline centred on white, small avatars and icon tiles floating around it joined by thin lines to a central "
  "icon (a connected team / system)", "CoreHR", "better")
w("hero.globe_type", "hero", "one big 3D object (a globe, a shield, the product) on one side, a huge headline on the other mixing bold sans and "
  "light serif italic words", "Finix", "better")
w("hero.poster", "hero", "the whole hero one strong colour, a huge uppercase headline, the product in front of it, a rotating circular badge, "
  "a small glass card, a dark curved band at the bottom", "fruit poster")
w("hero.giant_overlap", "hero", "a giant condensed headline across the width, the product held in front of the words, a short line and action "
  "on the right", "energy drink")
w("hero.colour_panel", "hero", "dark side with a thin + bold italic headline, a tall colour panel holding the product spilling out of its top, "
  "numbers on the panel, a white product card across the bottom edge", "security camera")
w("hero.showroom", "hero", "a huge serif headline, the product large over its corner (a pouring kettle, a cup), leaves floating, the words and "
  "actions in a narrow column", "tea brand")
# ---- trust (5)
w("trust.logo_dark", "trust", "a quiet row of partner / client logos directly under the hero, on the hero's own background", "Resq")
w("trust.logo_circles", "trust", "logos in soft circles in one row, a centred title and line above", "ProFinance")
w("trust.cause_strip", "trust", "a thin full-width strip in the deep colour with one line of promise (a cause, free delivery, guarantee)", "BetterVits")
w("trust.huge_numbers", "trust", "huge numbers in rows (+270K, 8X), a 3D icon or photo on the left of each, the meaning on the right", "Wello")
w("trust.statement_quote", "trust", "a big plain statement on the left half, a short quote with its author on the right half", "Passion Finder")
# ---- offer (8)
w("offer.pedestal_carousel", "offer", "products on tinted square backgrounds with soft shadows, names and prices under, arrows at the sides",
  "BetterVits", "needed", (3, 8))
w("offer.bento_mockups", "offer", "an asymmetric bento: one accent tile with the main line, one wide tile with a screenshot / photo, smaller tiles "
  "with one feature each", "Resq", "better", (3, 6))
w("offer.stair_tiles", "offer", "three colourful tiles numbered 01 02 03 standing at stepped heights (a staircase), an illustration on each",
  "Wello", "optional", (3, 3))
w("offer.mockup_cards", "offer", "2-3 cards each holding a small live picture of the thing (a chart, a screen, a photo) above its name and line",
  "Finix / CoreHR", "better", (2, 6))
w("offer.shape_cards", "offer", "two wide cards, each with an abstract shape (a blob, a ring) at its right edge, a title, line and 'Read more'",
  "ProFinance", "optional", (2, 4))
w("offer.stage_rows", "offer", "each thing on a soft half-circle with its round photo, its name big beside it, price under; rows change sides",
  "tea brand", "needed", (2, 4))
w("offer.ingredient_mosaic", "offer", "a mosaic of soft tiles of different sizes, each a picture of one part (an ingredient, a material) with its name",
  "BetterVits", "better", (4, 8))
w("offer.list_menu", "offer", "a refined two-column list: name ...... price, one line under, category tabs above (menus, treatments)",
  "editorial practice", "none", (4, 16))
# ---- why (8)
w("why.hub_spokes", "why", "a glowing central icon tile, 4 small label boxes on its left and right joined to it by circuit-like lines",
  "Resq", "none", (4, 4))
w("why.orbit_object", "why", "one big object / photo in the middle, numbered glass cards on both sides (01 03 left, 02 04 right)", "AIAF", "better", (4, 4))
w("why.floating_tiles", "why", "tiles scattered at slight angles like cards dropped on a table, an icon and a short line on each, one in the accent",
  "Resq", "none", (4, 6))
w("why.curved_photo_icons", "why", "a 3x2 grid of small icons with a title and line each, a photo in a curved corner shape at the bottom right",
  "BetterVits", "better", (4, 6))
w("why.title_left_grid", "why", "the title and a line in a left column, a 2x2 grid of icon points on the right, each with a small pill action",
  "ProFinance", "none", (4, 4))
w("why.inline_icon_statement", "why", "one huge paragraph across the page with small icons / emoji set inside the sentence between words",
  "Wello", "none", (0, 0))
w("why.watermark", "why", "a huge faded word behind (WHY), a photo, a numbered list 001-004 with hairlines", "energy drink", "better", (3, 6))
w("why.word_sticker", "why", "one big word or short line centred with a small coloured sticker / badge beside it, the points under in a row",
  "Wello", "none", (3, 4))
# ---- process (5)
w("process.doodle_rows", "process", "rows that change sides (a picture and the words), joined by a hand-drawn line running between them, colour blobs",
  "ProFinance", "better", (2, 4))
w("process.phone_circle", "process", "a phone / product on a circle in the middle, the step cards fanned out beside it, the explanation in a column",
  "Passion Finder", "better", (3, 4))
w("process.stair_steps", "process", "steps as tiles at stepped heights rising left to right, big numbers on each", "Wello", "none", (3, 4))
w("process.timeline", "process", "a vertical line down the middle, step cards on alternate sides with node circles", "practice", "none", (3, 6))
w("process.big_numbers", "process", "columns under huge outlined numbers 01-04", "practice", "none", (3, 4))
# ---- showcase (6)
w("showcase.scattered_portraits", "showcase", "photos scattered round a centred title at different sizes and angles", "CoreHR", "needed", (4, 8))
w("showcase.collage", "showcase", "3-4 overlapping photos with white borders beside the words and a short list", "tea brand", "needed", (3, 4))
w("showcase.masonry", "showcase", "photos of mixed heights in columns, captions on hover", "practice", "needed", (6, 12))
w("showcase.before_after", "showcase", "pairs side by side with a divider handle, the treatment / program and time", "practice", "needed", (2, 6))
w("showcase.tilted_cards_cta", "showcase", "tilted photo / app cards fanned at both sides, a centred line and action between them", "Passion Finder", "needed", (2, 6))
w("showcase.film_strip", "showcase", "one wide row of tall photos moving sideways", "practice", "needed", (5, 12))
# ---- people (7)
w("people.photo_band_statement", "people", "a full-width gradient band, the person's photo on the left, a big statement on the right ('Guided by X. Why X?')",
  "Passion Finder", "better", (1, 1))
w("people.reveal_circles", "people", "a big centred statement that fades in line by line, round portraits in a row under with names", "Passion Finder", "better", (3, 6))
w("people.leader", "people", "one leader's arch portrait, the message in large quotes, the name with a signature line", "practice", "better", (1, 1))
w("people.spotlight", "people", "one person large with a floating info card, the others as a short list beside", "practice", "better", (2, 6))
w("people.portraits", "people", "tall arch portraits with a soft tint, name, role and one credential", "practice", "better", (2, 8))
w("people.overlap", "people", "overlapping avatars, one big line about the team, an action", "practice", "better", (3, 8))
w("people.credentials", "people", "names with role, experience and speciality in clean rows (no photos)", "practice", "none", (2, 10))
# ---- proof (7)
w("proof.envelope", "proof", "one testimonial card rising out of an envelope in the middle, faded cards behind at both sides, arrows under",
  "CoreHR", "none", (2, 6))
w("proof.staggered", "proof", "testimonial cards at staggered heights (a wave), avatars, arrows and 'view all'", "BetterVits", "none", (3, 6))
w("proof.cards_readmore", "proof", "three quote cards in a row and a wide bar under them: 'Read more stories' with a stack of avatars", "Finix", "none", (3, 3))
w("proof.wall", "proof", "a masonry wall of quote cards with big quote marks", "Wello", "none", (4, 9))
w("proof.rating", "proof", "the overall rating big with the spread of stars, quotes beside", "practice", "none", (2, 4))
w("proof.results", "proof", "results as big figures with what they were and the client's line", "practice", "none", (2, 6))
w("proof.bigquote", "proof", "one quote large on the accent, others small in a column", "practice", "none", (2, 4))
# ---- pricing (4)
w("pricing.account_card", "pricing", "a phone stack on the left, a dark card on the right with the price big (€0.00 / month), plan tabs and the action",
  "Finix", "better", (1, 3))
w("pricing.featured_middle", "pricing", "three plans, the middle one raised on the deep colour", "practice", "none", (2, 4))
w("pricing.compare_table", "pricing", "plans as columns of one table, ticks per feature", "practice", "none", (2, 4))
w("pricing.package_rows", "pricing", "each package a wide row: name, inclusions, price and action", "practice", "optional", (2, 5))
# ---- listings (3)
w("listings.integration_fan", "listings", "tilted icon / logo tiles in an arc, the name of the centred one under it", "CoreHR", "none", (5, 9))
w("listings.category_tiles", "listings", "large photo tiles with the name over a dark gradient", "practice", "needed", (3, 8))
w("listings.filter_grid", "listings", "filter chips over a grid of cards with tags on the photos", "practice", "needed", (4, 12))
# ---- schedule (3)
w("schedule.week_grid", "schedule", "days as columns, slots as rows, classes as coloured blocks", "practice", "none", (3, 30))
w("schedule.agenda", "schedule", "time on the left, the session on the right, day tabs above", "practice", "none", (3, 20))
w("schedule.hours_card", "schedule", "a card of the week's hours, today in bold with an 'open now' dot", "practice", "none", (1, 7))
# ---- impact (2)
w("impact.globe_numbers", "impact", "a big 3D globe / object on one side, huge mixed-type headline and 2-3 impact figures on the other", "Finix", "better", (2, 3))
w("impact.numbers_story", "impact", "big impact numbers on one side, one real story with a photo on the other", "practice", "better", (2, 3))
# ---- faq (2)
w("faq.lines_band", "faq", "questions as hairline rows, an illustration band under them", "Wello", "optional", (4, 8))
w("faq.split", "faq", "the head and a contact line sticky on the left, the questions on the right", "practice", "none", (4, 8))
# ---- location (2)
w("location.map_card", "location", "a map filling one side, a card with address, hours, phone over it", "practice", "none", (1, 1))
w("location.contact_columns", "location", "three columns (visit, call, write) with icons in soft circles", "practice", "none", (3, 3))
# ---- action (5)
w("action.spotlight", "action", "a dark panel, the brand name small, a big line, the action button with a light glow rising under it, the footer links on "
  "the same panel", "Resq", "none")
w("action.dark_card_mockup", "action", "a rounded dark card with the line and action on the left, a phone / product breaking out of its top right",
  "ProFinance", "better")
w("action.blob_newsletter", "action", "a soft card with a line and an email box on the left, the product in a dark blob shape on the right", "BetterVits", "better")
w("action.tilted_cards", "action", "app / photo cards tilted at both sides, the line and store buttons centred between", "Passion Finder", "better")
w("action.giant_brand_footer", "action", "the closing line and links, the brand name huge across the bottom, cut off by the page's edge",
  "CoreHR / Finix", "none")


def by_role(role):
    return {n: x for n, x in W.items() if x["role"] == role}


def count():
    return len(W)
