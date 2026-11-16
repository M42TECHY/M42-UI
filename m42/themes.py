"""🎨 M42's page themes: whole designs, not colours (the user, 2026-11-13: "the lawyer, the school and the coffee shop
all come out the same template... how many themes do we have, how to choose one"). 53 of the last 60 pages were the
same "warm + glass" skeleton: a centred head, a grid of cards, the next section.

A theme fixes the things that make a design feel different, all at once:
  base     the archetype under it (webkit.ARCHETYPES: its hero and its part layouts)
  look     light / dark, style, font pair, corners, density, cards
  hero     the hero's layout ("" = the spec's own)
  head     how a section's title sits: center / numbered / rule / pill / big / split / sticky / boxed / column /
           marker / mono / ornament / quiet / outline
  rhythm   how sections follow each other: plain / tint / bands / framed / lines / bento / columns / stacked /
           blueprint / spotlight
  pic      the shape of photos: rounded / arch / blob / tall / tilt / sharp / circle / mono / poster / polaroid /
           squircle / glow / frame
  divider  between sections: none / wave / diagonal / curve / zigzag / slope / double / dots
  hero     also giant (huge words, the picture over them) / block (a coloured panel with the picture) / bleed (the
           picture off the page's edge) / poster / duo / showroom / diagonal (pagebuild.hero_signature)
  display  "condensed": headings in a tall condensed face (Anton), the poster's weight
  flow     the layouts its sections take in turn: grid (the part's own) / zigzag / orbit / spotlight / carousel /
           collage / stage / watermark, so one section differs from the next; stats "numbers": huge numbers in rows
The 4B chooses (agent.pick_design: it thinks first, then picks, told which themes the last pages used); the colours
stay the 4B's own for the business. The page carries data-m42-design and the axes; bundled/m42-ui.css draws them."""

THEMES = {
    "campus": {
        "label": "Campus", "base": "warm",
        "desc": "friendly and bright: rounded cards, pill section labels, soft colour bands, wavy edges, blob-shaped photos",
        "fits": "schools, colleges, tuition centres, kids' classes, education apps, libraries",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "hero": "bleed", "head": "pill", "rhythm": "bands", "pic": "blob", "divider": "wave", "flow": ["zigzag", "grid", "carousel"]},
    "atelier": {
        "label": "Atelier", "base": "editorial",
        "desc": "refined print feel: serif headings, numbered sections with thin rules, paper background, arch photos",
        "fits": "law firms, consultancies, architects, accountants, heritage brands, private banks",
        "look": {"theme": "light", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "airy", "cards": "outlined"},
        "hero": "", "head": "numbered", "rhythm": "lines", "pic": "arch", "divider": "none", "flow": ["grid", "spotlight"]},
    "bento": {
        "label": "Bento", "base": "saas",
        "desc": "modern grid of tiles of different sizes, crisp outlines, a title left with its lead on the right",
        "fits": "startups, software, apps, agencies, co-working, product features",
        "look": {"theme": "light", "style": "minimal", "font": "tech", "corners": "rounded", "density": "balanced", "cards": "outlined"},
        "hero": "", "head": "split", "rhythm": "bento", "pic": "rounded", "divider": "none", "flow": ["grid", "orbit"], "stats": "numbers"},
    "magazine": {
        "label": "Magazine", "base": "portfolio",
        "desc": "big photography and huge headings like a magazine, tall photos, hairlines between sections",
        "fits": "fashion, travel, photographers, restaurants with a story, hotels, blogs, events with pictures",
        "look": {"theme": "light", "style": "minimal", "font": "elegant", "corners": "sharp", "density": "airy", "cards": "flat"},
        "hero": "giant", "head": "big", "rhythm": "lines", "pic": "tall", "divider": "none", "flow": ["zigzag", "collage"], "stats": "numbers"},
    "noir": {
        "label": "Noir", "base": "editorial",
        "desc": "dark luxury: deep background, gold-like accents, quiet centred headings, glowing round-cornered photos",
        "fits": "jewellery, watches, fine dining, luxury cars, perfume, premium salons, night clubs",
        "look": {"theme": "dark", "style": "elegant", "font": "elegant", "corners": "rounded", "density": "airy", "cards": "outlined"},
        "hero": "bleed", "head": "center", "rhythm": "plain", "pic": "rounded", "divider": "none", "flow": ["spotlight", "carousel"]},
    "organic": {
        "label": "Organic", "base": "warm",
        "desc": "calm and natural: soft tinted sections with curved edges, arch photos, gentle serif headings",
        "fits": "cafes, bakeries, spas, yoga, organic food, florists, wellness, home decor",
        "look": {"theme": "light", "style": "minimal", "font": "elegant", "corners": "pill", "density": "airy", "cards": "flat"},
        "hero": "showroom", "head": "center", "rhythm": "tint", "pic": "arch", "divider": "curve", "flow": ["stage", "zigzag"]},
    "showcase": {
        "label": "Showcase", "base": "product",
        "desc": "Apple-like product stage: dark, the product big and centred, very quiet, wide spaces",
        "fits": "one product or gadget: phones, headphones, watches, cars, devices, a single app",
        "look": {"theme": "dark", "style": "minimal", "font": "modern", "corners": "rounded", "density": "airy", "cards": "flat"},
        "hero": "", "head": "center", "rhythm": "plain", "pic": "rounded", "divider": "none", "flow": ["grid", "orbit"]},
    "playground": {
        "label": "Playground", "base": "bold",
        "desc": "loud and fun: big type, colour bands with slanted edges, tilted photo cards, pill buttons",
        "fits": "kids' play schools, events, festivals, games, toy shops, birthday parties, summer camps",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "pill", "density": "balanced", "cards": "shadow"},
        "hero": "poster", "head": "big", "rhythm": "bands", "pic": "tilt", "divider": "diagonal", "flow": ["carousel", "grid"], "display": "condensed"},
    "corporate": {
        "label": "Corporate", "base": "warm",
        "desc": "trustworthy and clean: each section in its own soft framed panel, a title with a side rule, calm blue-grey",
        "fits": "hospitals, clinics, insurance, finance, logistics, manufacturing, B2B services, government",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "hero": "block", "head": "rule", "rhythm": "framed", "pic": "rounded", "divider": "none", "flow": ["grid", "spotlight"]},
    "split": {
        "label": "Split", "base": "portfolio",
        "desc": "the section title stays on the left while its content scrolls on the right; calm, expert, lots of reading",
        "fits": "consultants, coaches, agencies, real estate, interior designers, doctors' practices, NGOs",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "sharp", "density": "airy", "cards": "flat"},
        "hero": "", "head": "sticky", "rhythm": "lines", "pic": "sharp", "divider": "none", "flow": ["spotlight", "grid"]},
    "brutal": {
        "label": "Brutal", "base": "bold",
        "desc": "raw and confident: thick borders, hard offset shadows, huge headings, square photos",
        "fits": "creative studios, streetwear, music, gyms, barbers, tattoo, skate shops, youth brands",
        "look": {"theme": "light", "style": "bold", "font": "modern", "corners": "sharp", "density": "balanced", "cards": "outlined"},
        "hero": "poster", "head": "big", "rhythm": "framed", "pic": "sharp", "divider": "none", "flow": ["grid", "zigzag"], "stats": "numbers", "display": "condensed"},
    "aurora": {
        "label": "Aurora", "base": "saas",
        "desc": "dark futuristic: glowing gradients, glass cards, pill section labels, circle photos",
        "fits": "AI, tech, crypto, cyber security, gaming, space, electronics, web3, hackathons",
        "look": {"theme": "dark", "style": "glass", "font": "tech", "corners": "rounded", "density": "balanced", "cards": "glass"},
        "hero": "duo", "head": "pill", "rhythm": "plain", "pic": "glow", "divider": "none", "flow": ["carousel", "orbit"]},
    # ---- 18 more (the user, 2026-11-14: "30 themes in all, each landing page unique") ----
    "swiss": {
        "label": "Swiss", "base": "portfolio",
        "desc": "strict grid, big bold sans-serif titles in boxes, black-and-white photos, one strong colour",
        "fits": "architects, design studios, museums, galleries, typography, minimal brands",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "sharp", "density": "balanced", "cards": "outlined"},
        "hero": "giant", "head": "boxed", "rhythm": "lines", "pic": "mono", "divider": "none", "flow": ["watermark", "grid"], "stats": "numbers", "display": "condensed"},
    "newspaper": {
        "label": "Newspaper", "base": "editorial",
        "desc": "a front page: serif titles between double rules, columns with thin rules, grey photos, paper colour",
        "fits": "news, blogs, publishers, journalists, local magazines, schools' newsletters, writers",
        "look": {"theme": "light", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "balanced", "cards": "flat"},
        "hero": "", "head": "column", "rhythm": "columns", "pic": "mono", "divider": "double", "flow": ["grid", "watermark"]},
    "retro": {
        "label": "Retro", "base": "warm",
        "desc": "70s / 80s fun: cream paper, highlighter titles, polaroid photos, chunky outlined buttons, zigzag edges",
        "fits": "cafes, diners, barbers, vintage shops, music, record stores, ice cream, food trucks",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "pill", "density": "balanced", "cards": "outlined"},
        "hero": "diagonal", "head": "marker", "rhythm": "tint", "pic": "polaroid", "divider": "zigzag", "flow": ["carousel", "zigzag"]},
    "clay": {
        "label": "Clay", "base": "warm",
        "desc": "soft 3D clay feel: puffy rounded cards with soft shadows, sections as floating cards, squircle photos",
        "fits": "apps, fintech for people, kids' learning, health apps, pet care, friendly services",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "hero": "block", "head": "pill", "rhythm": "stacked", "pic": "squircle", "divider": "none", "flow": ["grid", "orbit"]},
    "neon": {
        "label": "Neon", "base": "saas",
        "desc": "night mode with glowing lines: neon-edged cards, terminal-style labels, glowing photos",
        "fits": "gaming, esports, clubs, DJs, nightlife, VR, cyber events, tech meetups",
        "look": {"theme": "dark", "style": "bold", "font": "tech", "corners": "rounded", "density": "balanced", "cards": "outlined"},
        "hero": "duo", "head": "mono", "rhythm": "plain", "pic": "glow", "divider": "none", "flow": ["orbit", "carousel"], "stats": "numbers"},
    "luxe": {
        "label": "Luxe Light", "base": "editorial",
        "desc": "white luxury: ivory page, thin gold rules, quiet serif titles, photos in fine inner frames",
        "fits": "weddings, bridal, jewellery, boutique hotels, fine perfume, event planners, wedding photographers",
        "look": {"theme": "light", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "airy", "cards": "outlined"},
        "hero": "showroom", "head": "center", "rhythm": "plain", "pic": "frame", "divider": "double", "flow": ["stage", "spotlight"]},
    "gradient": {
        "label": "Gradient Pop", "base": "saas",
        "desc": "bright mesh gradients, highlighter titles, big rounded white cards, soft curved bands",
        "fits": "startups, marketing agencies, creators, social apps, online courses, launches",
        "look": {"theme": "light", "style": "bold", "font": "modern", "corners": "pill", "density": "balanced", "cards": "shadow"},
        "hero": "poster", "head": "marker", "rhythm": "bands", "pic": "squircle", "divider": "curve", "flow": ["grid", "orbit"], "stats": "numbers", "display": "condensed"},
    "blueprint": {
        "label": "Tech Grid", "base": "saas",
        "desc": "engineer's blueprint: grid-paper background, monospace // labels, dashed outlined cards, sharp photos",
        "fits": "engineering, IoT, electronics, robotics, hardware, manufacturing, developer tools, labs",
        "look": {"theme": "light", "style": "minimal", "font": "tech", "corners": "sharp", "density": "balanced", "cards": "outlined"},
        "hero": "duo", "head": "mono", "rhythm": "blueprint", "pic": "sharp", "divider": "none", "flow": ["spotlight", "grid"], "stats": "numbers"},
    "coastal": {
        "label": "Coastal", "base": "warm",
        "desc": "fresh seaside: airy light page with a big photo hero, soft tinted sections, rounded photos, wavy edges",
        "fits": "travel, resorts, beach stays, surf, boat tours, juice bars, holiday homes",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "airy", "cards": "flat"},
        "hero": "showroom", "head": "center", "rhythm": "tint", "pic": "rounded", "divider": "wave", "flow": ["collage", "stage"]},
    "heritage": {
        "label": "Heritage", "base": "editorial",
        "desc": "traditional and rich: warm paper, an ornament over centred serif titles, framed photos, double-bordered cards",
        "fits": "temples, silk sarees, traditional sweets, ayurveda, handlooms, classical music and dance, heritage hotels",
        "look": {"theme": "light", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "airy", "cards": "outlined"},
        "hero": "showroom", "head": "ornament", "rhythm": "tint", "pic": "frame", "divider": "none", "flow": ["stage", "grid"]},
    "zen": {
        "label": "Zen", "base": "portfolio",
        "desc": "very calm: lots of white space, small light titles, no borders or shadows, soft rounded photos",
        "fits": "meditation, yoga retreats, tea, skincare, minimal interiors, therapists, wellness studios",
        "look": {"theme": "light", "style": "minimal", "font": "elegant", "corners": "rounded", "density": "airy", "cards": "flat"},
        "hero": "showroom", "head": "quiet", "rhythm": "plain", "pic": "rounded", "divider": "none", "flow": ["stage", "spotlight"]},
    "studio": {
        "label": "Studio", "base": "portfolio",
        "desc": "dark creative studio: huge outlined titles, square photos, black page, the work up front",
        "fits": "film makers, photography studios, music producers, animation, video agencies, creative directors",
        "look": {"theme": "dark", "style": "minimal", "font": "modern", "corners": "sharp", "density": "airy", "cards": "flat"},
        "hero": "duo", "head": "outline", "rhythm": "plain", "pic": "sharp", "divider": "none", "flow": ["watermark", "collage"], "stats": "numbers", "display": "condensed"},
    "sport": {
        "label": "Sport", "base": "bold",
        "desc": "high energy: slanted bold italic titles, dark and light bands, poster-style photos with colour offsets, slopes",
        "fits": "gyms, sports clubs, fitness coaches, marathons, sports academies, martial arts, cricket coaching",
        "look": {"theme": "dark", "style": "bold", "font": "modern", "corners": "sharp", "density": "balanced", "cards": "flat"},
        "hero": "duo", "head": "big", "rhythm": "spotlight", "pic": "poster", "divider": "slope", "flow": ["carousel", "watermark"], "stats": "numbers", "display": "condensed"},
    "pastel": {
        "label": "Pastel", "base": "warm",
        "desc": "sweet and soft: pastel tinted cards in turns, pill labels, blob photos, gentle curves, centred hero",
        "fits": "bakeries, cake shops, baby stores, florists, beauty salons, nail art, gift shops",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "pill", "density": "balanced", "cards": "flat"},
        "hero": "showroom", "head": "pill", "rhythm": "tint", "pic": "blob", "divider": "curve", "flow": ["stage", "carousel"]},
    "ink": {
        "label": "Ink", "base": "editorial",
        "desc": "dark editorial: near-black page, numbered serif sections with hairlines, black-and-white photos",
        "fits": "premium law and finance, whisky and wine, authors, architecture firms, private clubs, tailors",
        "look": {"theme": "dark", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "airy", "cards": "outlined"},
        "hero": "", "head": "numbered", "rhythm": "lines", "pic": "mono", "divider": "none", "flow": ["watermark", "collage"]},
    "paper": {
        "label": "Paper Craft", "base": "warm",
        "desc": "handmade: paper texture, highlighter titles, polaroid photos, sections as cut-out cards, dotted lines",
        "fits": "handmade crafts, stationery, art classes, NGOs, home bakers, kids' activities, local makers",
        "look": {"theme": "light", "style": "minimal", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "outlined"},
        "hero": "diagonal", "head": "marker", "rhythm": "stacked", "pic": "polaroid", "divider": "dots", "flow": ["collage", "grid"]},
    "clinic": {
        "label": "Clinic", "base": "warm",
        "desc": "clean and caring: fresh light page, soft white cards, squircle photos, calm tinted sections",
        "fits": "hospitals, dental clinics, pharmacies, diagnostics labs, physiotherapy, eye care, vets",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "hero": "block", "head": "center", "rhythm": "tint", "pic": "squircle", "divider": "none", "flow": ["grid", "zigzag"]},
    "bazaar": {
        "label": "Bazaar", "base": "warm",
        "desc": "colourful market: bright colour bands, cards topped with rotating colours, pill labels, zigzag edges",
        "fits": "grocery stores, textile shops, local markets, Indian restaurants, festivals, toy and gift shops",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "hero": "poster", "head": "pill", "rhythm": "bands", "pic": "rounded", "divider": "zigzag", "flow": ["carousel", "grid"], "display": "condensed"},
}
NAMES = tuple(THEMES)
AXES = ("head", "rhythm", "pic", "divider", "display")


# ---- 🎨 app themes: admin panels, POS, CRM, dashboards, management screens, on a desktop and a phone (the user,
# 2026-11-14: "20 themes for admin / POS / CRM / dashboard / management, from my reference shots, premium").
# An app screen keeps its sidebar, top bar and panels; a theme changes how each of them looks and weighs:
#   side    the menu: light / dark / accent (a colour gradient) / rail (narrow, icons) / float (a card off the edge) /
#           top (no sidebar: tabs in the top bar) / glass
#   frame   the page round the app: none / canvas (the app on a big rounded card over a coloured backdrop) / mesh
#   kpi     the number tiles: plain / tint (pastel, in turns) / solid (the first in the accent) / icon (a big icon
#           chip) / spark (a little bar chart drawn under the number)
#   panel   the cards: soft (no line, a soft shadow) / line (a thin line, no shadow) / glass / flat (a tint, no line)
#   table   clean / striped / rows (each row a card)
#   banner  the home's greeting: gradient (a colour band with the words and an art) / none
#   tabbar  on a phone, the menu as tabs at the bottom (an app's feel): on / ""
#   palettes  its own colours (2; the page gets one), as the reference shots have strong ones; the user's named colour wins
APP_THEMES = {
    "slate": {
        "label": "Slate", "desc": "classic clean SaaS admin: light sidebar, thin-lined cards, calm grey and one colour",
        "fits": "any admin panel, SaaS back office, settings and user management, internal tools",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "outlined"},
        "side": "light", "frame": "none", "kpi": "plain", "panel": "line", "table": "clean", "banner": "none", "tabbar": "", "palettes": [["#4f46e5", "#06b6d4", "#f59e0b"], ["#2563eb", "#10b981", "#f97316"]]},
    "midnight": {
        "label": "Midnight", "desc": "deep navy sidebar beside a light work area, soft cards, icon number tiles",
        "fits": "ERP, restaurant or hotel admin, order management, operations back office",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "dark", "frame": "none", "kpi": "icon", "panel": "soft", "table": "clean", "banner": "none", "tabbar": "", "palettes": [["#6366f1", "#22d3ee", "#f472b6"], ["#f97316", "#3b82f6", "#22c55e"]]},
    "lavender": {
        "label": "Lavender", "desc": "the app on a big rounded card over a soft lavender backdrop, floating menu, pastel tiles, a greeting band",
        "fits": "HR, wellness, health tracking, personal dashboards, people management",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "float", "frame": "canvas", "kpi": "tint", "panel": "soft", "table": "rows", "banner": "gradient", "tabbar": "on", "palettes": [["#8b5cf6", "#ec4899", "#22d3ee"], ["#a855f7", "#f472b6", "#34d399"]]},
    "citrus": {
        "label": "Citrus", "desc": "warm and appetising: orange backdrop, a narrow coloured icon rail, a bright greeting band, soft cards",
        "fits": "food delivery, restaurant and cafe admin, kitchen orders, recipe apps, grocery",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "rail", "frame": "canvas", "kpi": "solid", "panel": "soft", "table": "rows", "banner": "gradient", "tabbar": "on", "palettes": [["#f97316", "#facc15", "#ef4444"], ["#ea580c", "#f59e0b", "#16a34a"]]},
    "obsidian": {
        "label": "Obsidian", "desc": "all dark trading desk: black panels with fine lines, glowing accent numbers, tiny bar charts in the tiles",
        "fits": "finance, trading, crypto, banking, investment portfolios, analytics",
        "look": {"theme": "dark", "style": "bold", "font": "tech", "corners": "rounded", "density": "dense", "cards": "outlined"},
        "side": "dark", "frame": "none", "kpi": "spark", "panel": "line", "table": "striped", "banner": "none", "tabbar": "", "palettes": [["#22c55e", "#a3e635", "#38bdf8"], ["#a855f7", "#22d3ee", "#f472b6"]]},
    "glacier": {
        "label": "Glacier", "desc": "frosted glass over a soft colour mesh: glass menu and cards, light and airy",
        "fits": "smart home, IoT controls, wellness, weather, music and media apps",
        "look": {"theme": "light", "style": "glass", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "glass"},
        "side": "glass", "frame": "mesh", "kpi": "icon", "panel": "glass", "table": "rows", "banner": "none", "tabbar": "on", "palettes": [["#3b82f6", "#a78bfa", "#2dd4bf"], ["#0ea5e9", "#f472b6", "#a3e635"]]},
    "ledger": {
        "label": "Ledger", "desc": "dense and precise: tabs in the top bar, thin lines, striped tables, many numbers on one screen",
        "fits": "accounting, billing, invoices, inventory, stock, payroll, GST and tax",
        "look": {"theme": "light", "style": "minimal", "font": "tech", "corners": "sharp", "density": "dense", "cards": "outlined"},
        "side": "top", "frame": "none", "kpi": "plain", "panel": "line", "table": "striped", "banner": "none", "tabbar": "", "palettes": [["#0f766e", "#2563eb", "#f59e0b"], ["#1d4ed8", "#0891b2", "#dc2626"]]},
    "register": {
        "label": "Register", "desc": "point of sale: a narrow icon rail, big touch-friendly cards, the first number in the accent, tabs on a phone",
        "fits": "POS, retail billing counter, supermarket, pharmacy counter, ticketing, kiosks",
        "look": {"theme": "light", "style": "bold", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "rail", "frame": "none", "kpi": "solid", "panel": "soft", "table": "rows", "banner": "none", "tabbar": "on", "palettes": [["#7c3aed", "#f43f5e", "#22c55e"], ["#2563eb", "#f59e0b", "#10b981"]]},
    "pipeline": {
        "label": "Pipeline", "desc": "sales CRM: light menu, tiles with tiny bar charts, soft cards, people rows with status pills",
        "fits": "CRM, sales pipeline, leads, customer support desk, real estate leads, recruiting",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "outlined"},
        "side": "light", "frame": "none", "kpi": "spark", "panel": "soft", "table": "rows", "banner": "none", "tabbar": "", "palettes": [["#6d28d9", "#0ea5e9", "#f97316"], ["#0d9488", "#6366f1", "#f43f5e"]]},
    "scholar": {
        "label": "Scholar", "desc": "friendly school portal: soft blue page, floating menu, a colour greeting band, pastel tiles",
        "fits": "school and college ERP, attendance, student portal, LMS, coaching centres, library",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "float", "frame": "none", "kpi": "tint", "panel": "soft", "table": "clean", "banner": "gradient", "tabbar": "", "palettes": [["#2563eb", "#38bdf8", "#f59e0b"], ["#4f46e5", "#22c55e", "#f97316"]]},
    "medix": {
        "label": "Medix", "desc": "clinical and calm: white and fresh, light menu, soft cards, icon tiles, a gentle greeting band",
        "fits": "hospital management, clinics, patient records, pharmacy stock, lab reports, appointments",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "light", "frame": "none", "kpi": "icon", "panel": "soft", "table": "clean", "banner": "gradient", "tabbar": "", "palettes": [["#0d9488", "#38bdf8", "#f43f5e"], ["#0284c7", "#14b8a6", "#f97316"]]},
    "fleet": {
        "label": "Fleet", "desc": "operations control: dark menu, tinted work area, tiles with tiny bar charts, lined cards",
        "fits": "logistics, fleet and delivery tracking, IoT monitoring, factories, energy, warehouses",
        "look": {"theme": "light", "style": "minimal", "font": "tech", "corners": "rounded", "density": "dense", "cards": "outlined"},
        "side": "dark", "frame": "mesh", "kpi": "spark", "panel": "line", "table": "striped", "banner": "none", "tabbar": "", "palettes": [["#f59e0b", "#0ea5e9", "#22c55e"], ["#06b6d4", "#f97316", "#a3e635"]]},
    "canvas": {
        "label": "Canvas", "desc": "project workspace: tabs in the top bar, roomy soft cards, pastel tiles, boards and timelines",
        "fits": "project management, tasks, kanban, time tracking, agencies, team workspaces",
        "look": {"theme": "light", "style": "playful", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "top", "frame": "mesh", "kpi": "tint", "panel": "soft", "table": "rows", "banner": "gradient", "tabbar": "on", "palettes": [["#8b5cf6", "#f97316", "#10b981"], ["#ec4899", "#6366f1", "#facc15"]]},
    "graphite": {
        "label": "Graphite", "desc": "black and white, nothing extra: a narrow icon rail, thin lines, one strong colour for what matters",
        "fits": "developer tools, admin consoles, analytics, monitoring, minimal internal apps",
        "look": {"theme": "light", "style": "minimal", "font": "tech", "corners": "sharp", "density": "dense", "cards": "flat"},
        "side": "rail", "frame": "none", "kpi": "plain", "panel": "line", "table": "clean", "banner": "none", "tabbar": "", "palettes": [["#18181b", "#2563eb", "#f43f5e"], ["#18181b", "#16a34a", "#f59e0b"]]},
    "sunrise": {
        "label": "Sunrise", "desc": "a colour gradient sidebar, light work area, the first tile in the accent, soft cards",
        "fits": "marketing and social media dashboards, campaigns, creators, e-commerce sellers",
        "look": {"theme": "light", "style": "bold", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "shadow"},
        "side": "accent", "frame": "none", "kpi": "solid", "panel": "soft", "table": "rows", "banner": "none", "tabbar": "", "palettes": [["#e11d48", "#f97316", "#8b5cf6"], ["#db2777", "#7c3aed", "#f59e0b"]]},
    "forest": {
        "label": "Forest", "desc": "deep green colour sidebar, cream work area, flat tinted cards, icon tiles",
        "fits": "agriculture, farms, dairy, co-operatives, green energy, NGOs, nurseries",
        "look": {"theme": "light", "style": "minimal", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "flat"},
        "side": "accent", "frame": "none", "kpi": "icon", "panel": "flat", "table": "clean", "banner": "gradient", "tabbar": "", "palettes": [["#166534", "#84cc16", "#f59e0b"], ["#15803d", "#0d9488", "#eab308"]]},
    "carbon": {
        "label": "Carbon", "desc": "dark with bold colour tiles: glass cards, pastel-on-dark tiles, energetic",
        "fits": "gaming and esports admin, gyms and fitness centres, events, ticket sales, streaming",
        "look": {"theme": "dark", "style": "glass", "font": "modern", "corners": "rounded", "density": "balanced", "cards": "glass"},
        "side": "float", "frame": "none", "kpi": "tint", "panel": "glass", "table": "rows", "banner": "gradient", "tabbar": "on", "palettes": [["#f43f5e", "#a855f7", "#22d3ee"], ["#84cc16", "#f59e0b", "#06b6d4"]]},
    "paperwork": {
        "label": "Paperwork", "desc": "warm paper colour, serif headings, thin lines, quiet and serious",
        "fits": "law firms' case management, document management, libraries, government offices, archives",
        "look": {"theme": "light", "style": "elegant", "font": "elegant", "corners": "sharp", "density": "balanced", "cards": "outlined"},
        "side": "light", "frame": "none", "kpi": "plain", "panel": "line", "table": "striped", "banner": "none", "tabbar": "", "palettes": [["#7c2d12", "#b45309", "#1e3a8a"], ["#1e3a8a", "#9a3412", "#166534"]]},
    "nova": {
        "label": "Nova", "desc": "a floating dark menu over a soft colour mesh, glass cards, tiles with tiny bar charts",
        "fits": "AI tools, SaaS analytics, startups' admin, chat and support platforms, automation",
        "look": {"theme": "light", "style": "glass", "font": "tech", "corners": "rounded", "density": "balanced", "cards": "glass"},
        "side": "float", "frame": "mesh", "kpi": "spark", "panel": "glass", "table": "clean", "banner": "none", "tabbar": "", "palettes": [["#6366f1", "#ec4899", "#14b8a6"], ["#7c3aed", "#06b6d4", "#f97316"]]},
    "touch": {
        "label": "Touch", "desc": "mobile-app first: tabs at the bottom on a phone, big rounded cards, large numbers, a colour greeting",
        "fits": "mobile apps: fitness, banking, delivery riders, field staff, booking, personal finance",
        "look": {"theme": "light", "style": "playful", "font": "friendly", "corners": "pill", "density": "airy", "cards": "shadow"},
        "side": "top", "frame": "none", "kpi": "solid", "panel": "soft", "table": "rows", "banner": "gradient", "tabbar": "on", "palettes": [["#f97316", "#8b5cf6", "#10b981"], ["#2563eb", "#ec4899", "#facc15"]]},
}
APP_NAMES = tuple(APP_THEMES)
APP_AXES = ("side", "frame", "kpi", "panel", "table", "banner", "tabbar")
ALL = {**THEMES, **APP_THEMES}


def app_menu():
    """The app themes as the 4B reads them."""
    return "\n".join(f"- {n}: {t['desc']}. Fits: {t['fits']}." for n, t in APP_THEMES.items())


def is_app(name):
    return name in APP_THEMES

def menu():
    """The themes as the 4B reads them: name, what it looks like, what it fits."""
    return "\n".join(f"- {n}: {t['desc']}. Fits: {t['fits']}." for n, t in THEMES.items())


def apply(look):
    """The spec's look with its theme's design put over it (the colours stay the 4B's own). A look without a theme
    is returned as it is."""
    look = dict(look or {})
    t = ALL.get(look.get("design"))
    if not t:
        return look
    look.update(t["look"])
    if t.get("base"):
        look["archetype"] = t["base"]
    if t.get("palettes"):  # an app theme's own colours (one of its palettes, by the page: two shops differ); a colour
        # the user named still wins (webkit.make_look reads INTENT["named_colours"] first)
        seed = sum(ord(ch) for ch in str(look.get("why") or "") + str(look.get("colors") or ""))
        look["colors"] = list(t["palettes"][seed % len(t["palettes"])])
    return look


def axes(name):
    """{"head": .., "rhythm": .., "pic": .., "divider": ..} of a theme ({} for none)."""
    t = ALL.get(name)
    return {k: t[k] for k in AXES + APP_AXES if t.get(k)} if t else {}
