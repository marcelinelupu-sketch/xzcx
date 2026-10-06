# How to write lessons for this book

"A Modern Guide to English Grammar" by Rhyme Art. Readers are learning English, from A1 to C2, often slowly, in their second language.

The goal of every lesson: **a tired A2 learner understands it in under a minute and remembers it tomorrow.** Even C1 and C2 grammar is explained with A2 words.

`chapters.json` lists all 135 chapters (number, section, part, level, title, description). Never edit it. `old_lessons/` holds the first drafts of chapters 1 to 94: correct but too long and too plain. Use them as raw material, never as the standard.

## The rules

1. **As short as possible, never less clear.** Cut every sentence that does not teach. No introductions, no "In this lesson", no summaries, no tips unless the concept truly needs one. Typical length: 80 to 250 words of English. Part intros and section intros: a few lines and the overview table.
2. **Show, don't tell.** One formula, then examples. Explain in words only what the formula and examples cannot show.
3. **A2 words only** in explanations, at every level. Grammar terms only when needed, and explained the first time.
4. **Formatting serves understanding.** Same colors for the same roles everywhere. Center what should be seen at a glance.
5. **Correct.** Teach only what you are sure of. A wrong rule harms a real learner.
6. **The vibe:** examples live in an autumn atmosphere: falling leaves, rain on windows, letters, candles, long evenings, memory, longing, small beautiful sadness. Vary it widely; sometimes leave autumn completely (the sea, a night city, snow, a desert, early spring) so it never feels stuck. The mood comes from the scene, not from difficult words. At A1: "The leaves fall. She does not open the letter." At C1 the language can be literary. Every example must still make sense and sound natural.
7. American spelling. Never use em dashes or en dashes.

## Components (use these exactly; nothing else)

First line of every file: `<!-- author: YourName -->`

```html
<p class="lead">One or two sentences: what it is and when we use it.</p>

<div class="formula"><span class="s">I / you / we / they</span> <b>+</b> <span class="vb">verb</span> <b>+</b> <span class="o">object</span></div>

<div class="examples">
  <p><span class="s">She</span> <span class="vb">writes</span> a letter every autumn.</p>
  <p>The rain <mark>has stopped</mark>.</p>
</div>

<h2>Short heading</h2>
<p>Only when a second idea is needed.</p>

<div class="compare">
  <p class="wrong">She don't like rain.</p>
  <p class="right">She doesn't like rain.</p>
</div>

<div class="table-wrap"><table class="grid">
  <tr><th>Positive</th><th>Negative</th></tr>
  <tr><td>I walk</td><td>I don't walk</td></tr>
</table></div>
```

Role colors (use inside formulas, examples and tables, always for the same role):
`<span class="s">` subject, `<span class="vb">` verb or verb form, `<span class="o">` object or complement, `<span class="x">` the extra part (time word, adverb, particle). Use `<mark>` for the one thing to notice in an example. Do not color everything; color what the lesson is about.

Use `compare` only for mistakes learners really make. Tables are for patterns that are easier to see in rows and columns. Everything in tables is centered automatically.

## Vocabulary

Do not add any vocabulary markup. The system automatically underlines every word with meaning and gives it a simple definition and a translation into the learner's language. Write naturally; avoid rare words where a simpler one works. If old lessons contain <span class="v" ...> markup, it is removed automatically.

## Reviews (reviews/chapter-NN.md)

Review the other writer's lessons, never your own:

```
VERDICT: APPROVED
```
or `VERDICT: CHANGES NEEDED` followed by exactly what to fix. Check: correct? as short as possible? clear in one minute for an A2 reader? formatting right and helpful? examples natural and in the vibe? no copying from the reference books? A lesson changed after review needs a new review.

The expert (Opus) also checks every approved lesson (checks/lesson-NN.md). If it says FIX NEEDED, fix the lesson; it then needs a new peer review and a new expert check.

## Reference books

`../references/` holds Murphy's two Grammar in Use books and Williams' Style. Read its README first. Use them to check rules and to see how a topic is best taught and what learners get wrong. Never copy or closely paraphrase their sentences or examples. The build flags any text sharing 6 or more words in a row with them; flagged lessons must be rewritten.
