# frogsdream tool plugin contract

Every generator (bingo, word search, scavenger hunt, word scramble, bedtime chart, reward chart) is a
plugin that plugs into one shared shell. The word scramble maker is the reference implementation:
`source/static/assets/js/scramble.js`, `source/tools/scramble.controls.html`, `source/css/50-tool-scramble.css`.
Copy its shape. The bingo caller is a different kind of page and may skip parts of this contract (see the end).

## Files a tool owns

| File | Purpose |
|---|---|
| `source/static/assets/js/<tool>.js` | The plugin. File name from `site.json` `tools[].js` (bingo.js, wordsearch.js, scavenger.js, scramble.js, routine-chart.js, reward-chart.js, caller.js). Budget: 30 KB. |
| `source/tools/<id>.controls.html` | HTML for the tool's own option controls only. `<id>` is the tool id from `site.json` (bingo, wordsearch, scavenger, scramble, routine, reward, caller). |
| `source/css/50-tool-<id>.css` | Styles for the tool's sheets and any custom controls. Budget: about 1.6 KB after minification (all CSS together must stay under 25 KB; the foundation uses about 13.5 KB). Prefix every class with a short tool prefix (`sc-` for scramble). |
| `source/test_<id>.py` or `.mjs` (optional) | Build-time tests the spec asks for (word search placement, bingo uniqueness, 90-ball strips). |

Do not edit `toolkit.js`, `site.js`, `print.js`, `pdf.js`, `rng.js`, the base CSS partials or `build.py`.
Ask the foundation owner if the shell needs something new.

## What build.py emits on every tool page and themed page

```html
<body class="has-tool">
...
<section class="tool no-ads" id="tool" data-tool="scramble" aria-label="Word Scramble Maker">
  <script type="application/json" id="fd-data">{...page data, see below...}</script>
  <form class="tool-controls" id="fd-form">
    #fd-title      text input, pre-filled with the theme's toolTitle
    #fd-words      textarea, the theme items one per line;  #fd-count badge;  #fd-msg message line
    <details class="opts" open><div class="opts-body">
      <div data-tool-partial> YOUR tools/<id>.controls.html IS INSERTED HERE </div>
      #fd-paper (letter | a4)   #fd-ink (ink saver)   #fd-stamp (frog stamp)
    </div></details>
    #fd-seed (hidden)
    .tool-actions: #fd-generate (submit), #fd-print, #fd-pdf
    .tool-more:    #fd-share, #fd-reset, [data-embed-open] (only if the tool has an embed page)
  </form>
  <div class="tool-preview"><p id="fd-status"></p><div class="sheets" id="fd-sheets" data-paper="letter"></div></div>
</section>
```

Scripts load with `defer` in this order: `config.js, site.js, rng.js, print.js, pdf.js, toolkit.js, <tool>.js`.

The inline page data (`#fd-data`) is:

```json
{
  "tool": "scramble", "path": "/word-scramble/christmas/", "url": "https://frogsdream.com/word-scramble/christmas/",
  "title": "Christmas Word Scramble",          // toolTitle
  "lines": ["Reindeer", "Snowman"],              // items as textarea lines
  "items": ["Reindeer", "Snowman"],              // items exactly as in the content JSON (objects kept)
  "options": {"puzzles": 1, "bank": true},       // the page's defaultOptions
  "theme": true,                                 // false on the main tool page and embed pages
  "slug": "christmas", "section": "word-scramble", "noun": "words",
  "toolUrl": "https://frogsdream.com/word-scramble-maker/", "embed": false
}
```

## Your controls partial

Plain HTML using the shared classes. Every input needs a `name` (that name is the option key) and a
visible `<label>`. Ids must be unique on the page; prefix them (`sc-`). Shared classes:
`.field` (label + input), `.row` (two fields side by side), `.check` (checkbox row with label).
Set the default state in HTML (`value=`, `checked`, `selected`); the page's `defaultOptions` override it.

```html
<div class="row">
  <div class="field"><label for="sc-puzzles">Puzzles</label><input type="number" id="sc-puzzles" name="puzzles" min="1" max="10" value="1"></div>
  <div class="field"><label for="sc-case">Letters</label><select id="sc-case" name="case">...</select></div>
</div>
<label class="check"><input type="checkbox" id="sc-hint" name="hint"> Hint: show the first letter</label>
```

The toolkit reads options generically: checkbox gives a boolean, number and range give a number clamped to
`min`/`max`, radio gives the checked value, select and text give the string.

## Your plugin: `FD.tool.register(def)`

```js
FD.tool.register({
  id: 'scramble',          // tool id, also the localStorage key fd:<id>
  noun: 'words',           // count badge label ("24 words")
  hint: 'One word per line.',           // default message under the list
  init: function (els, data) {},        // optional, runs once before the first render
  parse: function (lines, state, ctx) { // optional: turn textarea lines into items
    // ctx.warn(msg) shows a friendly warning; ctx.error(msg) blocks rendering and shows the message.
    return items;                        // ctx.items is set to this
  },
  build: function (state, ctx) {        // required: ALL randomness happens here, using ctx.rand / ctx.sub()
    return model;                        // plain data; the same model feeds the preview and the PDF
  },
  render: function (model, ctx) {       // required: draw the preview; must not use randomness
    var body = ctx.sheet();              // appends one page, returns its .sheet-body element
    ctx.header(body, model.title, 'Puzzle 1');  // standard sheet header with the Name line
    body.appendChild(FD.h('p', { cls: 'sc-how', text: '...' }));
  },
  pdf: function (model, P, ctx) {       // required: draw the same pages with jsPDF (may return a Promise)
    var y = P.header(model.title, 'Puzzle 1');
    P.font('body', 11).textColor('ink').text('...', P.box.x, y);
    P.addPage();
  }
});
```

**state** = `{ title, words: [lines], options: {...}, paper: 'letter'|'a4', ink: bool, stamp: bool, seed: uint32 }`.

**ctx** = `{ state, seed, rand, sub(...keys), paper, ink, stamp, data, items, warn, error, sheet(opts), header(body, title, sub, opts) }`.

* `ctx.rand()` is a seeded mulberry32 stream. `ctx.sub('card', 7)` returns an independent seeded stream,
  so card 7 is identical whenever the seed is identical, regardless of how many cards came before.
* `ctx.sheet({ key: true, cls: 'x', label: 'aria label' })` adds a page frame with the credit line
  "Made free at frogsdream.com" (8pt grey) and the frog stamp when enabled. Fill the returned body.
  Never add the credit yourself.
* `ctx.header(body, title, sub, { key: true, noName: true })` renders the standard title row,
  the "ANSWER KEY" badge and the Name line.

### Sheet sizing and styling

Sheets are real paper size in CSS (`8.5in x 11in` or `210mm x 297mm`) with a 0.4in padding that
matches the printed margin. Lay out in `in`, `pt` or `mm` units so preview and print match exactly.
Content area: Letter 7.7in x 9.9in, A4 7.47in x 10.59in (after the credit band).
The toolkit scales the preview to fit the screen with a CSS transform; print removes the transform.
Use the sheet color variables so ink saver mode works automatically:
`--k` ink, `--a` accent, `--a2` light accent, `--soft` fill, `--ln` line, `--hl` highlight.
Shared sheet classes: `.sh-head`, `.sh-title`, `.sh-sub`, `.sh-name`, `.sh-key`.
Output must fit on its page: `.sheet` has `overflow:hidden`, so shrink fonts (auto-fit) rather than overflow.
Printed output is always on white.

### Helpers available

* `FD.h(tag, attrs, ...children)` builds DOM. `attrs.cls` sets the class, `attrs.text` the text, `attrs.html` the inner HTML, other keys become attributes.
* `FD.frogSVG(className)` returns the mascot as an inline SVG string (use it for a bingo FREE square, never emoji).
* `FD.rng`: `create(seed)`, `shuffle(arr, rand)`, `int(rand, lo, hi)`, `pick(arr, rand)`, `hash(str)`, `derive(...)`, `newSeed()`.
* `FD.print`: `PAPER` sizes (`wIn`, `hIn`, `wPt`, `hPt`), `defaultPaper()`, `setPage(paper)`, `print(paper)`, `fit(sheetsEl)`.
* `FD.esc(str)`, `FD.toast(msg)`, `FD.copy(text)`, `FD.modal(title, html)`.

### PDF API (`pdf.js`)

`P` is created by the toolkit (jsPDF is lazy-loaded from cdnjs only when the user clicks Download PDF):

| Member | Meaning |
|---|---|
| `P.doc` | the raw jsPDF document, unit `pt` |
| `P.W`, `P.H`, `P.M` | page width, height, margin (28.8pt = 0.4in) |
| `P.box` | `{x, y, w, h}` content area inside the margins, minus a 0.3in band for the credit |
| `P.ink`, `P.stamp` | ink saver and frog stamp flags |
| `P.font(kind, size)` | `'display'` (embedded Fredoka, falls back to Helvetica bold), `'body'`, `'bold'`, `'italic'` |
| `P.fill(name)`, `P.stroke(name)`, `P.textColor(name)` | names: `ink`, `accent`, `accent2`, `soft`, `line`, `muted`, `highlight`, `white` (automatically grey in ink saver mode) |
| `P.text(t, x, y, opts)`, `P.center(t, cx, y)` | text, cleaned to the WinAnsi character set |
| `P.width(t, size)`, `P.fit(t, maxW, maxSize, minSize)`, `P.wrap(t, maxW)` | measuring, auto-fit, wrapping |
| `P.roundRect(x, y, w, h, r, style)` | style `'S'`, `'F'` or `'FD'` |
| `P.header(title, sub, {key, noName})` | standard header, returns the y below it |
| `P.frog(x, y, size)` | vector mascot |
| `P.addPage()` | new page (the first page already exists) |

The toolkit calls `P.save(name)`, which stamps "Made free at frogsdream.com" and the frog on every page.
Do not call `save` yourself.

## What the shell does for you

* **Generate** picks a new seed and rebuilds; any edit to the form re-renders live with the same seed (250 ms debounce).
* **Print** re-renders, injects `@page { size: letter|A4; margin: .4in }` and calls `window.print()`.
  Print CSS hides everything except `.sheets`; each `.sheet-frame` is one printed page.
* **Download PDF** lazy-loads jsPDF, calls your `pdf(model, P, ctx)` with the model of the current preview, then saves `<title-slug>.pdf`.
* **Copy share link**: `<page url>#s=<base64url(JSON {t, w, o, p, i, f, s})>` (title, words, options, paper, ink, stamp, seed).
  Opening it restores the identical sheets. `?seed=123` is also accepted. Canonicals never include these.
* **Reset** restores the page's list and defaultOptions with a new seed.
* **localStorage** `fd:<id>` keeps the last title, list and options (try/catch, never required). It is restored only on the main tool page.
* **Embed pages** (`/embed/<tool>/`) render the same shell without header and footer, with a credit link; share links point to the main tool page.
* Paper defaults from `navigator.language` (en-US gives Letter, everything else A4).
* After each render the document fires `fd:rendered` with `{ pages, seed }` (useful in Playwright tests).
  `FD.tool.model()` and `FD.tool.state()` expose the current model and state.

## Canonical option names (use these in `defaultOptions` and your partial)

| Tool | Options |
|---|---|
| bingo | `mode` (`word`, `75`, `90`, `30`), `grid` (3, 4, 5), `free` (bool), `freeText`, `cards` (1 to 30), `perPage` (1, 2, 4), `repeats` (bool), `caller` (bool, caller sheet), `names` (bool, a name line in each square for find-someone-who bingo) |
| wordsearch | `size` (10 to 20), `difficulty` (`easy`, `medium`, `hard`), `case` (`upper`, `lower`), `showList` (bool), `puzzles` (1 to 10), `key` (bool) |
| scavenger | `layout` (`checklist`, `two-column`, `photo`, `team`), `names` (bool), `timeLimit` (bool), `copies` (1 to 30), `shuffle` (bool), `ageNote` (text) |
| scramble | `puzzles` (1 to 10), `case` (`upper`, `lower`), `hint`, `bank`, `key`, `shuffle` (bools) |
| routine | `layout` (`strip`, `grid`, `weekly`), `palette` (`mint`, `sky`, `peach`, `lavender`, `bw`), `name` (text), `times` (bool), `mascot` (bool) |
| reward | `days` (7, 14, 30), `mark` (`sticker`, `tick`), `goal` (text), `name` (text), `palette`, `weekStart` (`mon`, `sun`) |

### Chart item lines (routine and reward)

Chart steps and tasks are plain strings: `"Label"`, `"Label | 7:30 PM"` (time), `"Label | icon-name"` or
`"Label | icon-name | time"`, where `icon-name` is a file name from `assets/img/icons/` without `.svg`.
A line ending in a colon, such as `"Morning:"`, prints as a group heading.

## Rules every tool must follow

* No randomness outside `build`. Same seed and same inputs must give byte-identical sheets.
* No network requests except jsPDF via `FD.pdf`. No external fonts or images in sheets.
* No ads inside `.tool` (the shell marks it `no-ads`); never add ad markup.
* Keyboard operable, every control labelled, focus visible. No drag and drop dependency.
* Text in the UI and on sheets follows the content rules (no em or en dashes, no spaced hyphen dashes, US English).
* Keep `render` fast (under about 50 ms for typical lists) because it runs on every keystroke.

## The bingo caller

`caller.js` does not use the toolkit. Set `"shell": "custom"` in `content/tools/bingo-caller.json`: build.py
then emits only `<section class="tool tool-custom no-ads" id="tool" data-tool="caller">` containing `#fd-data`
and your `tools/caller.controls.html` partial, and loads just `config.js, site.js, rng.js, caller.js`.
Draw the whole caller UI inside `#tool`. Fetch `/assets/js/themes.json` for the themed list dropdown (every
built theme with slug, section, tool, path, title, items, defaultOptions, season, hubs, related).
Print CSS for the caller is up to you (the page has no `has-tool` class, so normal print styles apply).

## Testing your tool

```
python3 source/build.py --out /tmp/fd-test
cd /tmp/fd-test && python3 -m http.server 8765
```
In Playwright, route `https://cdnjs.cloudflare.com/**` to a local copy of jsPDF 2.5.1 if the sandbox has no
internet (`npm pack jspdf@2.5.1`), then: wait for `.sheet`, click `#fd-generate`, `page.pdf()` with
`emulateMedia({media: 'print'})` and `preferCSSPageSize: true` for print preview, and
`waitForEvent('download')` around a click on `#fd-pdf`.
