# Rhyme Art Grammar Book: handoff

"A Modern Guide to English Grammar" for edu.rhymeart.com. This document is for whoever (human or AI) puts the book on the platform and connects learner progress to the server.

## 1. What is in the site folder

```
toc.html                 the book's contents page (Wojtek's original design, extended)
chapter-01.html ... chapter-135.html
assets/
  book.css               design of the chapter pages
  book.js                vocabulary popups and the exercise engine
  progress.js            RhymeProgress: records what the learner did (THE PLUG, see section 3)
  progress-config.js     the only file you edit to connect a server
  toc-progress.js/.css   connects the TOC checkmarks and "viewed" dots to RhymeProgress
  toc-vocab.js           glossary data for the TOC words
```

Everything is static HTML, CSS and JavaScript. No build step is needed on the server. Upload the folder as it is (Cloudflare Pages, or a static route of the existing project). All pages must be served from the same origin so they share `localStorage`.

## 2. How the book behaves

- **Language:** the learner picks a language on the TOC welcome screen. It is stored in `localStorage["bLang"]` (codes: sq ar bs bg hr cs da nl et fi fr de el hu it lv lt mk no pl pt ro ru sr sk sl es sv tr uk). Every page reads it.
- **Vocabulary:** every word with meaning (not grammar words like the, is, of, she) is underlined with a dotted line, in the TOC, the lessons and the exercise texts. Hover (or first tap on a phone) shows a simple English definition for the meaning in that sentence. Click (or second tap) shows the translation into the learner's language. The clickable parts of exercises are never underlined.
- **Exercises:** each chapter has 5 to 10 sets of 3 or 4 items: multiple choice, write the missing word, put the words in order, click the mistake. Wrong answers can be retried; only the first attempt counts for the score.
- **Completion rule:** a chapter is complete when every exercise item is answered and at least 80% were right on the first attempt. A chapter without exercises is complete when it is opened. Below 80%, the learner can reset the chapter's exercises and try again.
- **TOC:** a chapter the learner opened gets a small gold dot after its number; a completed chapter gets its checkmark automatically. The TOC's own manual checkmark buttons still work as before (they are stored separately in `localStorage["bProgress"]`).

## 3. Connecting progress to the server (the plug)

`progress.js` keeps the full progress state in `localStorage["rhymeGrammarProgress"]`, so the book works with no server at all. To store it on the learner's account, connect ONE of these in `assets/progress-config.js`. Nothing else in the book needs to change.

### Option A: an endpoint (simplest)

```js
window.RHYME_PROGRESS_ENDPOINT = "/api/grammar-progress";
```

- `GET /api/grammar-progress` → returns the learner's saved state as JSON (format below), or `null` / 404 if none. Called once when any page opens; the result is merged into the local state.
- `POST /api/grammar-progress` with body `{ "event": {...}, "state": {...} }` → save. Sent after every change.
- Requests are sent with `credentials: "include"`, so the existing session cookie (Google OAuth or email/password login) identifies the user. The endpoint must look up the user from the session and reject requests without one (401). The book ignores errors, so a logged-out learner simply keeps progress locally.

### Option B: a custom adapter (for anything else)

```js
window.RhymeProgressAdapter = {
  load: async () => { /* return the saved state object, or null */ },
  save: async (state, event) => { /* store it */ }
};
```

### Option C: listen without changing anything

Every change is also broadcast in the page:

```js
window.addEventListener("rhyme-progress", (e) => {
  const { event, state } = e.detail;   // see formats below
});
```

### The state format

```json
{
  "version": 1,
  "updatedAt": "2026-10-06T12:00:00.000Z",
  "chapters": {
    "58": {
      "viewedAt": "2026-10-06T11:58:02.000Z",
      "total": 24,
      "items": { "s0i0": { "firstCorrect": true, "attempts": 1, "solved": true } },
      "complete": true,
      "completedAt": "2026-10-06T12:00:00.000Z",
      "score": 0.92
    }
  }
}
```

`items` keys are `s<set index>i<item index>`. `score` is the share right on the first attempt (null for chapters without exercises).

### The events

| type | extra fields | when |
|---|---|---|
| `lesson_viewed` | `chapter`, `first` (true on the very first visit) | every time a chapter page opens |
| `exercise_answered` | `chapter`, `item`, `correct`, `firstAttempt` | every answer, right or wrong |
| `chapter_completed` | `chapter`, `score` | once, when the completion rule is met |
| `exercises_reset` | `chapter` | the learner chose to try a chapter's exercises again |

All events also carry `type` and `at` (ISO time).

### Merging rule (already implemented)

When a server copy is loaded, it is merged with the local copy so nothing is lost: a chapter complete anywhere stays complete, the earliest view time wins, and existing first attempts are never overwritten.

### Suggested storage for a Cloudflare Worker with D1

Simplest: one row per learner with the whole state (it is small, under 100 KB even for a finished book).

```sql
CREATE TABLE grammar_progress (
  user_id    TEXT PRIMARY KEY,
  state      TEXT NOT NULL,          -- the JSON state above
  updated_at TEXT NOT NULL
);
CREATE TABLE grammar_events (          -- optional, for the learning dashboard
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    TEXT NOT NULL,
  type       TEXT NOT NULL,
  chapter    INTEGER,
  payload    TEXT NOT NULL,          -- the full event JSON
  at         TEXT NOT NULL
);
CREATE INDEX grammar_events_user ON grammar_events(user_id, at);
```

The Worker: on `GET`, read the session, return `state` for that user. On `POST`, read the session, store `body.state` (or merge server side with the same rule), and append `body.event` to `grammar_events`. The dashboard can then read completion per chapter from `state` and activity over time from `grammar_events`.

## 4. How the book was made, and how to change it

The source lives in `team/` (not in the public git repository, because the book is unpublished Rhyme Art material). Key files:

- `book/lessons/chapter-NN.html`: lesson bodies (components described in `book/STYLE.md`).
- `book/exercises/chapter-NN.json`: exercises (format in `book/EXERCISES.md`).
- `book/descriptions.json`: TOC descriptions added to Wojtek's original TOC.
- `vocab/glossary.json`: every word sense with definition and 30 translations, and which occurrence uses which sense.
- `build.py`: builds `site/` from all of the above and checks progress, format and copying from the reference books.
- `glossary.py`: updates the glossary after text changes (only new words cost anything). Run it, then `build.py`.

To fix a lesson or an exercise: edit the file, run `python3 team/glossary.py` (if words changed), then `python3 team/build.py`, then upload `team/site/`.

## 5. Known limits

- Every lesson was written by AI, peer reviewed by AI, and checked by a stronger AI; every exercise was checked the same way. That catches most mistakes, not all. **A human teacher should read every chapter before students see it.**
- Translations into Polish, German, Spanish, French, Russian and the other large languages are good. Smaller languages (for example Albanian, Macedonian, Latvian, Bosnian) are weaker and were not checked by a native speaker.
- The reference books (Murphy, Williams) were used only to study teaching methods. Every lesson and exercise was automatically compared with them, and anything sharing 6 or more words in a row was rewritten.
- Learner progress lives in the browser until the server plug is connected.
