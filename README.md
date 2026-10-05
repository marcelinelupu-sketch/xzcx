# frogsdream Printables (frogsdream.com)

Free printable bingo cards, word searches, scavenger hunts, word scrambles, bedtime and reward charts, and an online bingo caller. The site is plain static HTML, CSS and vanilla JavaScript for Hostinger shared hosting. There is no server code, no database and no build step on the server.

The brand is written **frogsdream**: one word, always lowercase, even at the start of a sentence. On the site, in the logo, the OG images and the Mega Pack PDFs it is drawn two-colored ("frogs" green, "dream" purple); `build.py` colors it in page text automatically, so content files just say `frogsdream`.

The full specification is in `source/SPEC.md`. The owner overrides at its top always win (for example: no em dashes or en dashes in any human-readable text).

## What is where

| Path | What it is |
|---|---|
| `public_html/` | The generated website. Its contents are uploaded to Hostinger as they are. Do not edit by hand; rebuild instead. |
| `deliverables/frogsdream-public_html.zip` | The contents of `public_html/` at the zip root (including `.htaccess`), ready to extract inside Hostinger's `public_html`. |
| `deliverables/megapack/` | The paid Mega Pack: the PDF folder and `frogsdream-Mega-Pack.zip`. Not part of the site build; the owner uploads only the zip, unextracted, into `public_html/pack-download-b0b5f94d131b/` on the server. |
| `deliverables/COMPLIANCE-REPORT.md` | The legal, privacy and cookie compliance report, with the decisions left to the owner. |
| `deliverables/OWNER-README.html` | The owner's plain-English setup checklist (hosting, Search Console, Bing, Stripe, AdSense, taxes, expectations). |
| `source/build.py` | Static site generator. Reads content JSON, CSS and static files and writes `public_html/`. |
| `source/fdlib.py` | Shared helpers for the build and the validator (markup, paths, content loading). |
| `source/validate_content.py` | Content rules: word counts, banned characters, word list sizes, 5-word shingle similarity. |
| `source/content/` | All page content as JSON: `themes/<tool>/<slug>.json`, `hubs/`, `guides/`, `tools/`, `pages/`, `home.json`, `site.json`. Format described in `source/CONTENT-FORMAT.md`. |
| `source/css/` | CSS partials, concatenated in name order into `assets/css/site.css`. |
| `source/static/` | Files copied verbatim to the site root (`assets/js/*.js`, images, fonts, favicon). `assets/js/config.js` is the only file the owner edits on the server. |
| `source/tools/` | Tool option control fragments. The JS contract for tools is in `source/TOOL-CONTRACT.md`. |
| `source/art/` | Scripts that draw the frog mascot, icons and sample images. |
| `source/fonts/` | Fredoka (OFL) font files used by the build and the Mega Pack. |
| `source/indexnow.key` | The IndexNow key. The build writes `<key>.txt` into the site root. Keep it stable. |
| `source/megapack/build_megapack.py` | Generates the Mega Pack PDFs (reportlab, vector, fonts embedded) and its zip. |
| `source/tests/` | Unit and browser tests (90-ball strips, bingo uniqueness, word search placement, bingo generator and caller). |
| `source/qa/` | The full QA suite and its runner `run_all.sh`. Reports go to `source/qa/reports/`. |

## Requirements

- Python 3.11 with Pillow and reportlab (the Mega Pack also uses svglib)
- Node 22 with Playwright and Chromium (browser tests)
- poppler-utils (`pdftotext`, `pdfinfo`, `pdftoppm`)
- Lighthouse is installed into `source/qa/node_modules` automatically on the first QA run

## Rebuild the site

Full build plus every check, then a fresh upload zip (only written if everything passes):

```bash
bash source/qa/run_all.sh
```

Faster run that skips the slow bingo uniqueness test and the all-themes browser pass:

```bash
QUICK=1 bash source/qa/run_all.sh
```

Just the site, no tests:

```bash
python3 source/validate_content.py --all
python3 source/build.py --strict --force      # writes ./public_html
```

## Rebuild the Mega Pack

```bash
python3 source/megapack/build_megapack.py     # PDFs, zip and the /premium/ preview images
```

The output is seeded from each theme slug, so repeated runs give the same pack. Rebuild the site afterwards if the preview images changed.

## Editing content

1. Edit the JSON in `source/content/` (see `source/CONTENT-FORMAT.md`).
2. Run `python3 source/validate_content.py <file>` for a quick check.
3. Run `bash source/qa/run_all.sh` and upload the new zip.

## Legal and payment settings

- **Operator identity** (shown on /privacy/, /terms/ and /contact/ as the law requires) lives only in `source/content/site.json` under `"operator": {"name", "address"}`. An empty name renders `[OWNER FULL NAME]` and the QA prints a WARNING; an empty address is left out.
- **Policy date** for the privacy policy and terms is `"legal": {"updated": "YYYY-MM-DD"}` in `site.json`. Change it only when their wording changes.
- **Mega Pack sales** go through a Stripe Payment Link with Stripe Managed Payments (Link is the merchant of record). `PACK_URL` in `source/static/assets/js/config.js` holds the live link, and the build writes the Buy buttons into the HTML already live. `"packAvailable"` in `site.json` sets the Product availability (InStock or OutOfStock). After payment Stripe redirects to the hidden, noindex page `/pack-download-b0b5f94d131b/`; the owner uploads the zip there by hand.
- **No third-party requests** while `ADSENSE_CLIENT` is empty: jsPDF 2.5.1 is self-hosted in `assets/js/vendor/` with its MIT licence, and the Fredoka font in `assets/fonts/` with `OFL.txt`. The QA fails on any request to another host.
- **On-device storage:** the tools keep user input in `sessionStorage` only (cleared when the tab closes). No cookies or `localStorage` of our own; the QA checks this.

Remember that a fresh upload overwrites the owner's edits on the server (`assets/js/config.js` and `ads.txt`). The name, address and Stripe link are built in, so after a re-upload only `ADSENSE_CLIENT` and the `ads.txt` line need pasting again once AdSense is live. The owner checklist explains this.
