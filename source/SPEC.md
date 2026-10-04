# OWNER OVERRIDES (take precedence over everything below)

1. NO EM DASHES OR EN DASHES ANYWHERE in any human-readable text the site, PDFs, README or docs contain. That means the characters U+2014 and U+2013 are banned, and so is a spaced hyphen used as a dash (" - "). This includes titles, meta descriptions, headings, prose, UI labels, alt text, JSON-LD strings, PDF text. Do NOT mechanically swap them for colons either. Write sentences the way they would sound spoken aloud, plain and natural. For page titles use natural phrasing, e.g. "Baby Shower Bingo Cards, Free Printable and Customizable" or "Free Printable Baby Shower Bingo Cards". A trailing " | Frog's Dream" brand suffix is allowed where it fits in 60 chars. Hyphens inside compound words (e.g. "90-ball", "free-to-print") are fine. The QA must grep the built output and source content for U+2014 and U+2013 and fail on any hit.
2. About page honesty: say content was written with AI assistance and reviewed for accuracy. Do NOT claim a person checked it.
3. Keep the "Frog's Dream" brand voice warm, clear and natural. US English.
4. Do not commit to git. The orchestrator commits.

# BUILD SPEC

FROG'S DREAM PRINTABLES: BUILD SPEC (static files for Hostinger public_html)

0. GLOBAL RULES (builders follow literally)
- Deliverable: a folder `public_html/` the owner uploads as-is. index.html is the home page.
- Everything is static HTML, CSS and vanilla JS. No frameworks, no build step on the server, no PHP, no database. Builders may use local Python/Node scripts to generate pages from data. Only the generated output goes into public_html. Keep generator scripts in a separate `/source/` folder in the repo, not uploaded.
- A second deliverable folder, `deliverables/megapack/`, holds the paid PDF pack and its ZIP. It must NEVER be placed inside public_html.
- Every page is a folder with index.html, so URLs are clean with trailing slashes: https://frogsdream.com/bingo/baby-shower/ . Canonical host: https://frogsdream.com (non-www, https).
- Language: English (en). US spelling, with A4/UK support (paper size toggle and the 90-ball bingo page). No Polish version.
- Audience: adults (teachers, parents, party hosts, ESL teachers). Copy addresses adults, never children directly, so the site is not 'child-directed' for ad purposes.
- Honesty rules:
  - No fake reviews, testimonials, user counts, 'as seen in' badges, or invented author personas or credentials.
  - The About page states plainly that Frog's Dream is a small independent project, with content written with AI assistance and checked for accuracy.
  - No fabricated statistics. Cite sources for any factual claim (sleep durations: AAP/AASM; frog life cycle: a reputable source).
- Trademarks: no themed pages or words using protected brands or characters (Super Bowl, Disney, Pokémon, Harry Potter, Taboo, Pictionary, Wordle, etc.). Use generic names ('Big Game', 'football party').
- Anti-thin-content rules (critical for indexing and AdSense):
  - Every themed page has a hand-written, theme-specific word list and 350-700 words of unique prose: intro, how to play/use for this occasion, 3+ variations, tips, printing advice, 2-4 FAQs unique to the theme.
  - No reused boilerplate sentences longer than about 12 words across themed pages, apart from the shared tool UI labels and the footer.
  - Builders must run a similarity check: 5-word shingles across all themed pages' main prose, with Jaccard similarity under 0.25 between any two pages. Rewrite offenders.
- No year numbers in titles or URLs. Seasonal pages say 'every December', not '2026'.
- Performance budget:
  - Each HTML page under 60KB.
  - Total CSS under 25KB (one file).
  - Shared JS under 40KB, plus per-tool JS under 30KB.
  - jsPDF is loaded lazily only when the user clicks 'Download PDF'.
  - No render-blocking third-party scripts.
  - Lighthouse target 95+ on mobile for Performance, Accessibility, Best Practices and SEO.
- Accessibility: WCAG 2.1 AA contrast, keyboard operable, labels on all inputs, visible focus, prefers-reduced-motion respected.
- Fonts: system font stack for body. Optionally one self-hosted woff2 display font (e.g. 'Fredoka' or 'Baloo 2', OFL licence) under /assets/fonts/ for headings only, with font-display: swap. No Google Fonts request, for speed and GDPR.
- No analytics cookies. No third-party trackers before AdSense. Google Search Console plus Hostinger stats are enough.

1. SITEMAP / FILE TREE (public_html/)

Root files:
- index.html — home
- 404.html
- .htaccess
- robots.txt
- sitemap.xml
- ads.txt — placeholder, see section 9
- `<indexnow-key>.txt` — builders generate a random 32-hex key, and the file content equals the key
- favicon.svg, favicon.ico (32px), apple-touch-icon.png (180px), site.webmanifest

assets/:
- css/site.css
- js/config.js — the ONLY file the owner edits; see section 9
- js/site.js — nav, consent-aware ad loader, 'in season now' block, share buttons, embed modal, year in footer
- js/rng.js — seeded PRNG (mulberry32) plus shuffle; deterministic from a seed so shared URLs reproduce the same cards
- js/print.js — paper size and print helpers
- js/pdf.js — lazy-loads jsPDF from https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js and draws PDFs
- js/bingo.js, js/wordsearch.js, js/scavenger.js, js/scramble.js, js/routine-chart.js, js/reward-chart.js, js/caller.js
- img/frog-mascot.svg plus 4 poses: waving, sleeping, holding a pencil, celebrating. Simple, cute, flat, 2-3 greens with a cream belly; hand-coded SVG.
- img/icons/ — about 36 simple line SVG icons for routine and reward charts: bath, brush teeth, pajamas, potty/toilet, wash hands, book, story, hug, bed, lights off, water glass, snack, toys away, get dressed, shoes, breakfast, backpack, hair brush, vitamins, prayer/quiet time (neutral 'quiet time'), music, sun, moon, star, sticker, trophy, chores (bed-making, dishes, pet feeding, laundry, plants, trash), homework, reading, screen-off, kindness heart. Consistent 2px stroke, 48x48 viewBox, currentColor.
- img/og/ — 1200x630 PNG per tool, per hub and one default. Generated at build time with Pillow: mascot plus title text. Themed pages use their tool's OG image.
- fonts/ (optional)

Tool pages (7), with the primary keyword in brackets:
- /bingo-card-generator/ ['bingo card generator', 'bingo card maker', 'printable bingo cards'] — word/picture-free text bingo plus number bingo modes
- /word-search-maker/ ['word search maker', 'word search generator', 'printable word search']
- /scavenger-hunt-generator/ ['scavenger hunt generator', 'printable scavenger hunt']
- /word-scramble-maker/ ['word scramble maker', 'word scramble generator']
- /bedtime-routine-chart/ ['bedtime routine chart printable', 'toddler bedtime chart']
- /reward-chart-maker/ ['reward chart printable', 'sticker chart maker']
- /bingo-caller/ ['bingo caller online', 'bingo number generator', 'online bingo caller for classroom']

Number bingo landing pages (3), each pre-configuring the bingo tool:
- /bingo/75-ball-bingo-cards/
- /bingo/90-ball-bingo-tickets/ (UK)
- /bingo/number-bingo-1-30-for-kids/

Themed bingo pages: /bingo/<slug>/ — exactly these 50 (plus 3 number pages above = 53):
- baby-shower, gender-reveal-party, bridal-shower, wedding-reception, birthday-party, graduation-party, retirement-party, family-reunion, movie-night
- new-years-eve, valentines-day, st-patricks-day, easter, earth-day, mothers-day, fathers-day, fourth-of-july, summer, back-to-school, last-day-of-school, fall, halloween, thanksgiving, christmas, hanukkah, winter
- road-trip, camping, beach, nature-walk, zoo, frog-and-pond, ocean-animals, farm-animals, dinosaurs, bugs-and-insects, solar-system, weather
- sight-words-kindergarten, sight-words-first-grade, cvc-words, esl-animals, esl-food, esl-colors-and-shapes, esl-classroom-objects, esl-feelings, esl-action-verbs
- addition-facts-to-20 (squares show sums, caller sheet shows problems), multiplication-facts, icebreaker-find-someone-who (human bingo), meeting-buzzword-bingo

Hub: /bingo/ — lists all themes grouped: Parties & Showers, Holidays & Seasons, Classroom, ESL, Outdoors & Travel, Number Bingo.

Themed word search pages: /word-search/<slug>/ — exactly 36:
- frog-life-cycle, pond-animals
- christmas, halloween, thanksgiving, easter, valentines-day, st-patricks-day, spring, summer, fall, winter, back-to-school
- solar-system, weather, ocean-animals, rainforest-animals, farm, dinosaurs, insects, plants-and-flowers, human-body, fruits-and-vegetables, healthy-food, sports, musical-instruments, community-helpers, transportation, kitchen
- baby-shower, bridal-shower, birthday, camping, us-states, countries-of-europe, sight-words

Hub: /word-search/

Themed scavenger hunt pages: /scavenger-hunt/<slug>/ — exactly 18:
- indoor-for-kids, backyard, nature-walk, park, neighborhood-walk, rainy-day, toddler, teen-photo, birthday-party
- christmas-lights, halloween, spring-easter, fall, winter, beach, camping, road-trip, classroom

Hub: /scavenger-hunt/

Themed word scramble pages: /word-scramble/<slug>/ — exactly 10:
- christmas, halloween, thanksgiving, easter, valentines-day, baby-shower, bridal-shower, summer, back-to-school, animals

Hub: /word-scramble/

Bedtime chart variants: /bedtime-routine-chart/<slug>/ — 4:
- toddler-picture-chart, preschool, school-age, morning-and-bedtime-routine

Reward chart variants: /reward-chart-maker/<slug>/ — 5:
- potty-training-chart, chore-chart-for-kids, reading-log-reward-chart, behavior-chart, weekly-sticker-chart

Cross-tool hubs (8). Each has 300-500 words of intro and links grouped by tool:
- /christmas-printables/
- /halloween-printables/
- /baby-shower-games/
- /bridal-shower-games/
- /classroom-games/
- /esl-games/
- /party-games/
- /road-trip-and-outdoor-games/

Guides: /guides/<slug>/ — 8, each 1,000-1,800 words, original, with diagrams where useful:
- bingo-patterns — an interactive SVG pattern gallery (lines, four corners, X, blackout, postage stamp, T, L, picture frame, etc.); target 'bingo patterns'
- 75-ball-vs-90-ball-bingo
- how-to-play-bingo-rules
- classroom-bingo-ideas-for-teachers
- esl-vocabulary-games-printable
- how-to-plan-a-scavenger-hunt
- toddler-bedtime-routine — cites AAP/AASM recommended sleep hours by age and links to sources; 'not medical advice' note
- printing-tips-letter-vs-a4

Hub: /guides/

Other pages:
- /premium/ — Mega Pack sales page
- /embed/ — instructions plus copy-paste embed codes
- /embed/bingo/ and /embed/word-search/ — minimal iframe versions, meta robots noindex,follow, with a visible 'Free tool by Frog's Dream – frogsdream.com' link (rel=noopener, target=_blank)
- /about/, /contact/, /privacy/, /terms/, /disclosure/ (ads and affiliate disclosure)

Total: about 155 indexable pages.

2. SHARED PAGE TEMPLATE
- <html lang="en">, meta charset, viewport, theme-color.
- <title>: unique, 50-60 characters.
- Meta description: unique, 140-160 characters.
- <link rel=canonical> with the absolute URL.
- Open Graph tags (og:title, og:description, og:url, og:image absolute, og:type, og:site_name 'Frog's Dream') and twitter:card summary_large_image.
- Header: logo (mascot plus 'Frog's Dream' wordmark) linking to /. Nav: Bingo, Word Search, Scavenger Hunts, Charts, Bingo Caller, Guides. Mobile: CSS-only disclosure menu.
- Breadcrumb trail (visible) plus BreadcrumbList JSON-LD on all non-home pages.
- Footer:
  - tool links, hub links
  - About, Contact, Privacy, Terms, Disclosure
  - 'Privacy choices' link — calls googlefc.showRevocationMessage() if available, else links to /privacy/#choices
  - '© <year> Frog's Dream'
  - 'Everything here is free to print for home, classroom and party use.'
- Print CSS (@media print): hide header, footer, nav, ads, buttons and prose. Print only the generated sheets, each with the bottom credit line 'Made free at frogsdream.com' in 8pt grey. Page breaks between sheets. @page size set from the paper toggle (letter or A4) and margins 0.4in.
- 'In season now' block (home and hubs): static HTML list of all seasonal hubs. site.js reorders it by current month so the next upcoming holiday is first. It still works without JS.

3. TOOL SPECIFICATIONS
Common to all generators:
- Controls: Title (text), word list (textarea, one per line, with live count and validation), options, Paper (US Letter / A4; default from navigator.language: en-US → Letter, otherwise A4), Ink saver (B/W) toggle, Seed (hidden). Buttons: 'Generate', 'Print', 'Download PDF', 'Copy share link', 'Reset to theme list'.
- The share link encodes title, words and options in the URL hash (base64url of JSON). Opening it restores the state. Pages also accept ?seed=.
- Preview renders as HTML/SVG at screen size. Print uses the same DOM.
- Save the last word list per tool in localStorage, wrapped in try/catch. Never required.
- Free-use cap: up to 30 bingo cards per generation, which is plenty for most groups and honestly stated. Under the generator: 'Need 40 ready-made cards for every theme, answer keys and caller sheets in one download? Get the Mega Pack' → /premium/. Hide this line if config.PACK_URL is empty.
- Credit footer on every printed and PDF page: 'Made free at frogsdream.com'.
- An 'Embed this tool' button opens a modal with iframe code: <iframe src="https://frogsdream.com/embed/bingo/" ...> plus a credit <a href="https://frogsdream.com/bingo-card-generator/">Bingo card generator by Frog's Dream</a>.
- Ads never appear inside the tool container, never within 150px of any button, and never print.

3.1 Bingo card generator (bingo.js)
- Modes: Word bingo (default), 75-ball number (B-I-N-G-O columns 1-15, 16-30, etc., free center), 90-ball UK tickets (3x9 grid, 15 numbers per ticket, correct column ranges 1-9, 10-19 ... 80-90, sheets of 6 tickets covering 1-90 exactly once — implement the standard strip algorithm and verify), Number 1-30 kids.
- Word mode options:
  - grid 3x3, 4x4 or 5x5
  - free center on/off with custom free-space text (default 'FREE 🐸' — use the SVG frog, not emoji, in print)
  - number of cards 1-30
  - cards per page: 1, 2 or 4
  - font auto-fit so long words shrink to fit
  - required words = cells per card minus the free space; if the list is shorter, show a friendly warning and allow repeats only if the user ticks 'allow repeats'
- Uniqueness: each card is a seeded shuffle. Guarantee no two cards are identical (hash check).
- Caller sheet: an extra page with all words as a cut-out checklist, plus a 'Call in this order' randomized list.
- Addition-facts theme: squares show answers, caller sheet shows problems (data driven: each item {square, call}).
- Human-bingo theme: squares are 'Find someone who ...' prompts with a blank line for a name.

3.2 Word search maker (wordsearch.js)
- Options:
  - grid 10x10 to 20x20 (default 12 for kids, 15 for adults)
  - difficulty Easy (→, ↓), Medium (+ diagonals ↘ ↗), Hard (all 8 directions including backwards)
  - uppercase/lowercase
  - show word list on/off
  - number of unique puzzles 1-10
  - answer key on/off (key page highlights words with rounded rectangles in SVG)
- Strip spaces and punctuation for placement but show the original in the word list.
- Placement: randomized backtracking with up to 500 attempts per word. If impossible, enlarge the grid by 1 and retry. Never silently drop a word. If a word is longer than the max grid, show an error.
- Fill letters: random A-Z, avoiding accidentally spelling short profanity. Keep a small blocklist and re-roll.
- Build-time test (in /source/): for every themed list at default settings, generate 200 seeds and assert all words are placed.

3.3 Scavenger hunt generator (scavenger.js)
- Items list (one per line, optional 'points' after a | ), layout: checklist with boxes / 2-column checklist / photo hunt (box plus 'snap it' camera-icon column) / team score sheet.
- Options: title, team or player name lines, time limit line, number of copies 1-30, shuffle order per copy on/off (so teams don't follow each other), age note.
- Themed pages hold 20-40 curated items. Include a safety tips paragraph on outdoor pages: adult supervision, stay in sight, no picking protected plants.

3.4 Word scramble maker (scramble.js)
- Scramble each word with a seeded shuffle and guarantee the result is not the original. If the word is under 3 letters, skip it with a warning.
- Options: hint (first letter shown), word bank on/off, answer key, puzzles 1-10.

3.5 Bedtime routine chart (routine-chart.js)
- Pick steps from the icon library (checkbox grid with icon plus editable label). Reorder with up/down buttons, no drag-drop dependency. Optional time per step.
- Child's name ('Mia's Bedtime Routine'), layout vertical strip / 2-column grid / tick-off weekly grid (7 days x steps), colour theme (4 pastel palettes plus B/W), sleepy-frog mascot corner.
- Variant pages pre-select steps: toddler picture chart has 6 steps with big icons and minimal text.

3.6 Reward chart maker (reward-chart.js)
- Tasks (rows) x days (Mon-Sun, or 1-N days), sticker circles or tick boxes, goal line ('When I get __ stickers I earn: ____'), name, palette, week start Monday/Sunday (default from locale).
- Potty-training variant: 'tries' and 'success' rows, 14-day or 30-day grid.

3.7 Bingo caller (caller.js)
- Modes: 75-ball, 90-ball, custom words (paste a list, or load any themed list from a dropdown backed by /assets/js/themes.json).
- Big 'Call next' button (spacebar shortcut), large display, called board grid highlighting called items, last 5 calls, undo, reset, auto-call every N seconds.
- Optional voice using the Web Speech API speechSynthesis (en-US/en-GB voice picker), fullscreen projector mode, state saved in localStorage so a refresh doesn't lose the game.
- 90-ball optional traditional UK calls ('Kelly's eye – number one') as a toggle. Write the list from public-domain tradition; keep it family-friendly.

3.8 Data
- /assets/js/themes.json is generated from /source/themes/*.json. Each theme has: slug, tool, title, h1, metaTitle, metaDescription, items[] (or {square, call}), defaultOptions, season (month numbers), hubs[], related[] (6 slugs).
- Themed HTML pages embed their own list inline in the HTML, as visible text plus a <script type="application/json"> for the tool. That way Google sees the words and the page works without fetching themes.json.

4. THEMED PAGE CONTENT STRUCTURE (each of about 123 pages)
- H1, e.g. 'Baby Shower Bingo Cards (Free Printable Generator)'.
- A 1-2 sentence answer-first intro ('Print up to 30 unique baby shower bingo cards for free...').
- The generator, pre-filled. The top of the page is above the fold on mobile, with the Generate button visible.
- 'The word list' — the visible curated list (24-75 items for bingo, 12-25 for word search, 15-40 for hunts), with a note that it is editable.
- 'How to play [theme] bingo' — unique steps for that occasion. Baby shower: guests fill cards while gifts are opened. Road trip: spot items out the window, etc.
- '3 fun variations', 'Tips for the host/teacher', 'Printing tips' (cardstock, A4/Letter, B/W mode). Printing tips must be theme-adapted, not identical.
- 'FAQ' — 2-4 genuinely relevant Qs, e.g. 'How many cards do I need for a baby shower?' or 'What age is this word search for?'.
- 'More [season/occasion] printables' — 6 related themed links plus the relevant hub plus the main tool.
- Word counts: 350-700 words of prose. Bingo themes with high commercial value (baby-shower, bridal-shower, christmas, halloween, thanksgiving, road-trip, esl-*, sight-words-*) get 600-900.
- Title patterns (vary wording; don't stamp one template on all):
  - Bingo: '[Theme] Bingo Cards – Free Printable & Customizable'
  - Word search: '[Theme] Word Search – Free Printable (with Answer Key)'
  - Scavenger hunt: '[Theme] Scavenger Hunt – Free Printable List'
  - Word scramble: '[Theme] Word Scramble – Free Printable with Answers'

5. HOME PAGE (index.html)
- H1: 'Free Printable Bingo Cards, Word Searches & Party Games'. Subhead: 'Make it, print it, play it – in seconds. No sign-up.'
- Tool cards (7) with mascot illustrations.
- 'In season now' block.
- Popular themes grid (12 links: baby shower bingo, christmas bingo, halloween word search, road trip bingo, esl animals bingo, sight words bingo, bridal shower bingo, nature walk scavenger hunt, frog life cycle word search, potty training chart, toddler bedtime chart, 90-ball tickets).
- Hubs.
- Short 'Why Frog's Dream' section (truthful: free, no sign-up, works on phones and Chromebooks, Letter and A4, prints in black-and-white).
- 300-500 words total prose.
- JSON-LD: WebSite (name, url) and Organization (name 'Frog's Dream', url, logo).

6. STRUCTURED DATA (JSON-LD, valid, no fake ratings)
- Tool pages and themed pages: WebApplication { name, url, applicationCategory: 'EducationalApplication' (or 'GameApplication' for the caller), operatingSystem: 'Any (web browser)', offers {price: '0', priceCurrency: 'USD'}, isAccessibleForFree: true }. NO aggregateRating.
- FAQPage on pages with an FAQ section (Google shows FAQ rich results only for authoritative gov/health sites, but the markup is harmless and helps AI search). The text must exactly match the visible FAQ.
- BreadcrumbList everywhere except home.
- Hubs: CollectionPage plus ItemList of linked pages.
- Guides: Article (headline, datePublished = build date, author {Organization 'Frog's Dream'}, publisher).
- /premium/: Product with offers (price from config shown statically as '$7'; builders put PRICE text in HTML; owner must keep it in sync — note this on the page source). No reviews.
- Validate all with a JSON-LD linter script at build.

7. TECHNICAL SEO FILES
- robots.txt:
  User-agent: *
  Allow: /
  Disallow: /embed/
  Sitemap: https://frogsdream.com/sitemap.xml
  (Note: /embed/ pages are also noindex. Disallowing them is fine because their canonical points to the main tool. Actually, to let Google see noindex, DO NOT disallow /embed/. Final: only 'Allow: /' plus the Sitemap line.)
- sitemap.xml: all indexable URLs, absolute, with <lastmod> = build date. Exclude /embed/* and 404. Under 50K URLs, one file.
- .htaccess (Apache on Hostinger):
  - RewriteEngine On
  - Force HTTPS: RewriteCond %{HTTPS} off → 301
  - www → non-www 301
  - DirectoryIndex index.html
  - ErrorDocument 404 /404.html
  - Add a trailing slash to directory URLs (Apache default with mod_dir)
  - mod_deflate for text/html, text/css, application/javascript, application/json, image/svg+xml
  - mod_expires: css/js/svg/png/woff2 1 year (bust caches with ?v=BUILDHASH query on asset URLs); html 1 hour
  - Headers: X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin
  - Do NOT add a strict Content-Security-Policy (it would break AdSense)
  - Wrap module directives in <IfModule>
- 404.html: friendly mascot, search-free links to the tools and hubs, noindex.
- Canonicals: self-referencing. The share-link hash does not create new URLs. Any ?seed= variant: the canonical points to the clean URL.
- Internal linking:
  - every themed page → its tool, its hub, 1-2 cross-tool hubs, 6 related themes
  - every tool page → its top 12 themes plus hub
  - guides → relevant tools and themes
  - no orphan pages; a build script asserts every indexable URL has 3 or more internal inbound links
- Images: SVG inline or with width/height set, alt text descriptive, lazy-loading below the fold.
- IndexNow: put the key file in root. Provide the owner, in OWNER-README, a ready-made browser URL to ping the home page and sitemap: https://api.indexnow.org/indexnow?url=https://frogsdream.com/&key=KEY

8. MONETIZATION PLACEMENTS
- AdSense (activated only when config.ADSENSE_CLIENT is non-empty):
  - site.js injects <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=CLIENT" crossorigin="anonymous"> on DOMContentLoaded.
  - Owner uses Auto ads in the AdSense UI.
  - Elements that must never host ads get class="no-ads" and data-nosnippet is NOT used. Add a CSS rule so the tool containers have generous padding; also tell the owner to turn OFF 'vignette' and 'side rail' if accidental clicks show up. Auto ads place themselves; we additionally include up to 2 manual slot containers per long page (after the 'How to play' section and before the FAQ), each with label 'Advertisement'. They render only if config.AD_SLOT_IN_ARTICLE is set; otherwise display:none and zero height (no layout shift).
  - No ads on /embed/, /premium/, /privacy/, /terms/, /contact/, or in print.
  - Consent: AdSense's Privacy & messaging (Google-certified, TCF v2.2) EEA/UK/CH message is configured by the owner in the AdSense UI and served automatically by the AdSense tag. The site sets no other cookies, so no separate custom cookie banner is needed. The footer 'Privacy choices' link reopens the Google consent message. The privacy policy explains this.
- Mega Pack (activated only when config.PACK_URL is non-empty, else every premium CTA and the /premium/ nav link are hidden; the /premium/ page itself shows 'Coming soon' and is noindex until a URL is set — implemented via JS adding a meta robots tag is unreliable, so: /premium/ is always indexable with honest copy, and the Buy button shows 'Coming soon' when no URL is set):
  - Buy button is a plain <a href=PACK_URL> (Lemon Squeezy hosted checkout; no lemon.js needed).
  - Price text '$7' is in HTML.
  - /premium/ content: what's inside (exact counts), 3 preview images (PNG renders of real pack pages, watermarked 'SAMPLE'), licence (personal and single-classroom use; no resale), refund line ('Lemon Squeezy handles payment and VAT; if a file doesn't work for you, email us for a refund within 14 days'), FAQ.
- Tip link: optional config.TIP_URL (Ko-fi/Buy Me a Coffee) shown as a small footer link 'Buy the frog a coffee' only if set.
- No Amazon links at launch. The Amazon 3-sales-in-180-days rule makes early signup counterproductive. Leave a documented hook for later.
- /disclosure/ page: explains ads, the paid pack, and that future affiliate links will be labelled.

9. CONFIG AND PLACEHOLDERS (owner edits only these)
/assets/js/config.js:

window.FD_CONFIG = {
  ADSENSE_CLIENT: "",          // e.g. "ca-pub-1234567890123456" — paste after AdSense gives it
  AD_SLOT_IN_ARTICLE: "",      // optional, leave empty
  PACK_URL: "",                // Lemon Squeezy checkout link for the Mega Pack
  PACK_PRICE: "$7",
  TIP_URL: "",                 // optional Ko-fi link
  CONTACT_EMAIL: "hello@frogsdream.com"
};

- ads.txt: ships with one commented line '# Replace with: google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0'. The owner replaces it with his pub ID (AdSense shows the exact line). This also serves as AdSense site verification (the 'ads.txt snippet' method).
- Contact email: hello@frogsdream.com. The owner creates this free mailbox in Hostinger, or forwards it to Gmail.
- The contact page uses a mailto link, assembled by JS to reduce scraping, with the plain address in a <noscript>.
- Privacy policy: GDPR requires naming the data controller. Use placeholder '[OWNER FULL NAME], Poland' plus the email. The owner fills in his name in /privacy/index.html (one spot, marked with a HTML comment 'OWNER: replace'). No address beyond the country needs to be public.
- Builders also produce OWNER-README.html (NOT in public_html; in deliverables/). It is a plain-language checklist of section 'owner_setup_steps', with exact click paths, the IndexNow ping URL, and screenshots-free instructions on editing config.js and ads.txt in the Hostinger File Manager.

10. MEGA PACK (deliverables/megapack/, generated by a Python script with reportlab, fonts embedded)
- Contents:
  - For each of the 50 bingo themes: 40 unique 5x5 cards (or 4x4 for kindergarten themes), 2 per page, in both Letter and A4, plus a caller checklist.
  - 75-ball: 100 unique cards. 90-ball: 20 strips of 6 tickets.
  - All 36 word searches × 2 difficulty levels, each with answer keys.
  - All 10 word scrambles with keys.
  - All 18 scavenger hunts.
  - 6 bedtime and reward chart designs in 4 colours.
- One PDF per theme and paper size, organised in folders. Each page carries the footer 'Frog's Dream Mega Pack – frogsdream.com – personal & classroom use'.
- Also a 1-page 'Start here' PDF.
- ZIP the result: Frogs-Dream-Mega-Pack.zip (Lemon Squeezy max file size is generous; keep under 200MB, ideally under 60MB by using vector PDFs).
- Builders must open-check a random 10% of PDFs: render to PNG and inspect for overflow, missing words, or repeated cards.

11. LEGAL / TRUST PAGES (real content, not lorem)
- /about/: what the site is, who it's for, that it is independent, built with AI assistance and checked by a person, free-use licence, and a contact link. Mascot. No fake founder story.
- /privacy/:
  - controller identity placeholder
  - no accounts
  - localStorage for preferences only (stays on the device)
  - Hostinger server logs
  - Google AdSense cookies and personalisation with a link to Google's 'How Google uses information from sites that use our services'
  - consent via Google's certified CMP and the footer 'Privacy choices' link
  - Lemon Squeezy as merchant of record for purchases (their privacy policy)
  - user rights under GDPR, contact email
  - children: the site is intended for adults; we don't knowingly collect children's data
  - effective date = build date
- /terms/: free-use licence for printables (personal, classroom, non-commercial events; no resale of the generated files as products), no warranty, Mega Pack licence, governing law Poland.
- /disclosure/: ads and paid product disclosure.
- /contact/: email, expected response time 'within a few days'.

12. DESIGN DIRECTION
- Personality: cozy, playful, clean. 'A sleepy little frog who loves games.' Plenty of white space. Rounded corners at 14px. Soft shadows.
- Palette, defined as CSS custom properties:
  --pond #2F8F5B (primary), --lily #8CCB6E, --cream #FFF9EC (page background), --ink #1F2A24 (text), --dusk #3B3A6B (night accent, used for bedtime charts), --sun #F6C445 (highlight), --coral #F07A5A (CTA hover)
  Ensure AA contrast for button text (white on --pond passes).
- Dark mode is optional for UI only. Printed output is always white background.
- Mascot appears small in the header, larger on the home hero, and as a corner stamp on printables (toggleable).
- Mobile first: the 360px width works; the tool controls stack above the preview, and the preview scales to fit width (CSS transform scale on a fixed-size sheet).

13. QA CHECKLIST (builders must pass before handoff)
- Link check: no broken internal links. Every page in the sitemap returns a file.
- Every indexable page has a unique title, meta description, canonical, single H1, and valid JSON-LD.
- Similarity check from section 0 passes. Word lists are reviewed for age-appropriateness and spelling.
- Generators tested in headless Chromium at 360px and 1280px:
  - generate, print preview and PDF download for each tool with each themed list
  - word search placement test passes
  - bingo uniqueness test passes
  - 90-ball strip validity test passes
- PDF download works in Chrome, Firefox and Safari (jsPDF). Print works on Chromebook Chrome.
- With config empty: no ad requests, no premium CTAs, no console errors. With a dummy ADSENSE_CLIENT: the script tag is injected once.
- Lighthouse mobile 95+ on home, one tool page and one themed page.
- Zip public_html for upload: frogsdream-public_html.zip with the folder CONTENTS at the zip root, so the owner extracts directly into public_html. Hostinger File Manager supports extract.

# TRAFFIC PLAN

BAKED INTO THE SITE (zero ongoing work)
1. Long-tail transactional targeting. About 123 themed pages, each aimed at one '[theme] bingo / word search / scavenger hunt / scramble printable' query family. AI Overviews show on only about 8% of these intents. Each page has a real curated list and unique prose, so it clears Google's 'Crawled - currently not indexed' quality filter and AdSense's 'low value content' check.
2. Seasonal recurrence. Christmas, Halloween, Thanksgiving, Easter, Valentine's, St Patrick's, July 4th, back-to-school and last-day-of-school pages, plus year-round shower and party pages. They come back every year with no posting. The 'In season now' block reorders links by month, so the internal emphasis follows the calendar automatically.
3. Self-building backlinks:
   - 'Made free at frogsdream.com' on every printout and PDF.
   - Embed codes with a credit link for teacher, ESL and party blogs.
   - Shareable URLs that restore a custom card set. Teachers paste these into Google Classroom and Pinterest, which creates mentions and links.
4. Strong technical SEO: clean folder URLs, canonicals, sitemap, BreadcrumbList/WebApplication/FAQ JSON-LD, dense hub-and-spoke internal linking (3+ inbound links per page, enforced by the build), sub-60KB pages and Lighthouse 95+.
5. A linkable reference asset: the bingo patterns guide (interactive SVG gallery) and the 75 vs 90-ball explainer. Bingo-hall and party blogs naturally cite these.

ONE-TIME OWNER ACTIONS (about 60-90 minutes total, mostly in week 1)
1. Google Search Console: add a Domain property with the DNS TXT record (Hostinger hPanel → DNS Zone). Submit https://frogsdream.com/sitemap.xml. Then use URL Inspection → 'Request indexing' on the home page, the 7 tool pages and the 8 hubs. There is a daily quota, so spread this over 2-3 days.
2. Bing Webmaster Tools: sign in and 'Import from Google Search Console' (one click). This also feeds DuckDuckGo, Yahoo and ChatGPT search, which rely on the Bing index. Then paste the IndexNow ping URL from OWNER-README into a browser once.
3. Optional directory submissions (about 30-45 minutes once, for backlinks, not traffic): AlternativeTo (list as an alternative to myfreebingocards / Bingo Baker), SaaSHub, Product Hunt as a free tool (a one-day spike at best), and a couple of teacher-resource and free-tool lists. Do not pay for directories.
4. Optional single launch posts, only where the subreddit rules explicitly allow self-promotion or a weekly resource thread: r/ESL_Teachers, r/teachingresources, r/Teachers weekly thread, r/babyshower. One honest post each. No repeated posting or sockpuppets.
5. Pinterest is deliberately NOT relied on, because it needs ongoing pinning. If the owner ever wants a 30-minute one-off, create a business account and pin the 12 seasonal hub OG images once.

TIMING REALITY
- Launch is October 2026. Christmas 2026 pages will probably be too new to rank on Google. Bing may send a little.
- The first realistic Google season is Valentine's, St Patrick's and Easter 2027, then back-to-school 2027.
- The main payoff is Halloween and Christmas 2027, when the pages are about 12 months old.
- Review GSC at month 3 and month 6. Pages with impressions but low CTR can get title tweaks in one more prompt to Claude.

# OWNER SETUP STEPS (for OWNER-README)

1. In Hostinger hPanel, make sure the free SSL certificate is active for frogsdream.com. Then open File Manager → public_html, delete the default placeholder file (default.php or index.php) if present, upload frogsdream-public_html.zip and click Extract. Visit https://frogsdream.com to confirm it loads. (about 10 min)
2. Create the mailbox hello@frogsdream.com in Hostinger Emails, or set up a forward to your Gmail. (about 5 min)
3. In File Manager, open privacy/index.html and replace the one marked placeholder [OWNER FULL NAME] with your name. EU privacy law requires naming who runs the site; no photo or address is needed. (about 2 min)
4. Google Search Console: add a 'Domain' property for frogsdream.com, copy the TXT record into Hostinger DNS Zone, verify, submit sitemap.xml, and request indexing for the home page and the main tool pages listed in OWNER-README. (about 15 min)
5. Bing Webmaster Tools: sign in with Google, import the site from Search Console, then paste the IndexNow ping link from OWNER-README into your browser once. (about 5 min)
6. Lemon Squeezy: sign up, complete identity verification and payout setup (mBank IBAN or PayPal), create a product 'Frog's Dream Mega Pack' at $7, upload Frogs-Dream-Mega-Pack.zip from the deliverables folder (NOT public_html), and copy the product's checkout link into PACK_URL in public_html/assets/js/config.js. If Lemon Squeezy refuses you, use Gumroad the same way. (about 20-30 min, plus their review wait)
7. About 4-8 weeks later, once Search Console shows 20 or more indexed pages: apply to Google AdSense with frogsdream.com. Paste your ca-pub ID into ADSENSE_CLIENT in config.js, and replace the line in ads.txt with the exact line AdSense shows you. Choose 'ads.txt snippet' as the verification method. (about 15 min)
8. Once AdSense approves: turn on Auto ads, and if accidental clicks appear, switch off vignette and side-rail formats. Under Privacy & messaging, create and publish the European regulations (GDPR) consent message (3-option). Fill in the W-8BEN tax form (Poland as tax residence; check the treaty withholding rate it shows). Add your mBank account in PLN and confirm the small test deposit. Later, enter the PIN from the letter Google posts to you. If you are rejected for 'low value content', wait 2-4 weeks and reapply; you can also ask Claude to expand pages. (about 30 min spread over weeks)
9. Optional, one time: submit to AlternativeTo, SaaSHub and Product Hunt (as a free tool), and make one honest post in teacher subreddits that allow it. (about 30-45 min)
10. Monthly, about 5 minutes: glance at Search Console for errors, AdSense for earnings and policy notices, and Lemon Squeezy sales. At months 3, 6 and 12, you can paste the Search Console 'Pages' and 'Queries' reports into a new Claude prompt to have titles improved or new themes added where data shows demand.
11. Taxes: AdSense and Lemon Squeezy income is taxable in Poland even under the działalność nierejestrowana limit (10,813.50 PLN revenue per quarter in 2026). Keep a simple income record and confirm the PIT treatment with an accountant or the tax office once.
12. Later, if Search Console shows about 1,000 or more monthly sessions from the US, UK, Canada and Australia and the site is 4+ months old: apply to Journey by Mediavine for higher ad rates. Ask Claude to wire up their script.

# RISKS AND CAVEATS (summarise honestly in OWNER-README)

- **This is not a money cheat.** The realistic median at month 12 is about $20-100/month. There is a real (about 30-40%) chance it earns under $10/month in year one: industry stats suggest about 73% of new niche sites stay under 1,000 visits/month in year one. The upside of several hundred dollars a month is most likely in Q4 of year 2, if the long tail compounds as it did for Bingo Card Creator and myfreebingocards.
- **Evidence quality.** Many research fetches (Semrush, Similarweb, Ahrefs, Flippa, Indie Hackers) were blocked by the proxy. Traffic and keyword figures come from search-result snippets of those tools, not dashboards. No keyword tool was available for exact long-tail volumes. The themed-page selection rests on category demand and seasonality logic, not measured per-keyword volume. Search Console data after 3-6 months should drive pruning and expansion.
- **New-domain sandbox.** Expect almost nothing from Google for 3-6 months, and possibly 6-12. Launching in October 2026 means Christmas 2026 is likely missed; the first meaningful seasons are spring and back-to-school 2027, and the big one is Q4 2027.
- **Indexing and scaled-content risk.** About 123 themed pages uploaded at once could be judged templated, leaving many 'Crawled - currently not indexed'. Mitigations are built into the spec: unique lists, unique prose, a similarity check, and a moderate page count rather than hundreds. If indexing stalls, the fix is to noindex or merge the weakest pages, not to add more.
- **AdSense.**
  - Approval is not guaranteed; 'low value content' rejections and 2-12 week reviews are common.
  - Ad income at low traffic is small: about $3-6 per 1,000 pageviews on tier-1 traffic.
  - Accidental clicks near buttons can get an account restricted (the Imposter Game case), so ads are kept away from tool controls.
  - EEA traffic needs the Google consent message, or ad fill drops.
- **Paid pack conversion.** 0.1-0.3% of visitors is my planning assumption, not measured. It could be lower. The free tool is deliberately generous (up to 30 cards), because a stingy paywall would hurt rankings and reputation.
- **Lemon Squeezy** was acquired by Stripe, and its successor product lacks built-in digital delivery. It still takes signups as of 2026 with no shutdown date, but a migration to Gumroad may be needed someday (a 15-minute task: swap PACK_URL).
- **Competition.** myfreebingocards, Bingo Baker, thewordsearch, TPT, Etsy and AI-built clone sites already exist. We win only on the long tail, quality (Letter/A4, 90-ball UK, answer keys, B/W ink saver, mobile/Chromebook) and seasonality. Anything good can be copied.
- **Hands-free limits.**
  - The owner must do roughly 1.5-2 hours of one-time identity-bound setup (AdSense, Lemon Squeezy, Search Console, Bing), plus about 5 minutes a month.
  - Nothing in the site goes stale: no prices, no rates, no dated claims. Small-print policy changes from Google or Lemon Squeezy may occasionally need a reaction.
- **Legal and tax.** GDPR requires the privacy policy to name the operator (his name, not his face). Income is taxable in Poland, and a W-8BEN is needed for AdSense. I am not a tax adviser.
- **Content honesty.** The site openly states it was built with AI assistance. No fake reviews, personas, ratings or trademarked themes are used. This avoids deception and policy risk, at the cost of 'trust badges' that some competitors fake.
- **Brand fit.** 'Frog's Dream' is a playful brand, not a keyword. That is fine for printables, but the obvious sleep/dream fit is left for a possible phase-2 /sleep/ section (the runner-up concept). It should be added only after the printables site has earned authority, so the site's topical focus stays clear.
