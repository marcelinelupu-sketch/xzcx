# frogsdream Printables (frogsdream.com)

Free printable bingo cards, word searches, scavenger hunts, word scrambles, bedtime and reward charts, and an online bingo caller. The site is plain static HTML, CSS and vanilla JavaScript for Hostinger shared hosting. There is no server code, no database and no build step on the server.

The brand is written **frogsdream**: one word, always lowercase, even at the start of a sentence. On the site, in the logo, the OG images and the Mega Pack PDFs it is drawn two-colored ("frogs" green, "dream" purple); `build.py` colors it in page text automatically, so content files just say `frogsdream`.

The full specification is in `source/SPEC.md`. The owner overrides at its top always win (for example: no em dashes or en dashes in any human-readable text).

## What is where

| Path | What it is |
|---|---|
| `public_html/` | The generated website. Its contents are uploaded to Hostinger as they are. Do not edit by hand; rebuild instead. |
| `deliverables/frogsdream-public_html.zip` | The contents of `public_html/` at the zip root (including `.htaccess`), ready to extract inside Hostinger's `public_html`. |
| `deliverables/megapack/` | The paid Mega Pack: the PDF folder and `frogsdream-Mega-Pack.zip`. Never put this inside `public_html/`. |
| `deliverables/OWNER-README.html` | The owner's plain-English setup checklist (hosting, Search Console, Bing, Lemon Squeezy, AdSense, taxes, expectations). |
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

Remember that a fresh upload overwrites the owner's edits on the server (`assets/js/config.js`, `ads.txt` and the name in `privacy/index.html`). The owner checklist explains this.
