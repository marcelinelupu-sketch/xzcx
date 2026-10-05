# How to write for this book

This is "A Modern Guide to English Grammar" by Rhyme Art. Readers are people learning English, from complete beginners (A1) to advanced (C2). Many of them read slowly in their second language. Everything you write must be easy to read, correct, and kind.

`chapters.json` lists all 135 chapters in order: number, section, part, level (CEFR), title, and description if one exists. Never edit it.

## 1. Descriptions (descriptions.json)

74 chapters have no description yet. Write them into `descriptions.json` as `{"<chapter number>": "description"}`. Keep the descriptions that are already in chapters.json as they are.

Match the existing style exactly. Real examples from the book:

- The Basics: "Every word in English has a job. In this section, we explore each type of word and what its job is."
- Articles: "Small words placed before a noun that point to its amount and familiarity."
- Personal Pronouns: "The words used instead of a name, depending on who or what you are talking about."
- Countable and Uncountable Nouns: "Why you can say 'two apples' but not 'two informations'."
- Adverbs of Frequency: "How often something happens."
- Used To and Would: "When the past is no longer true."
- Present Continuous: "When something is in progress."
- The Empty "It": "When 'it' doesn't refer to anything."

Rules: one short sentence, often a fragment. Plain everyday words. Say what the thing is for, not its technical definition. A good description makes a learner think "oh, I need that". Use `<strong>` only rarely, for one key word.

## 2. Lessons (lessons/chapter-NN.html)

One file per chapter, named with two digits: `chapter-07.html`, `chapter-115.html`. Write only the lesson body; the page header, navigation and design are added automatically. The very first line must be:

```html
<!-- author: YourName -->
```

### Shape of a good lesson

1. A `lead` paragraph: what this is and why it matters, in one or two simple sentences.
2. The idea, explained step by step with `h2` headings. One idea per section.
3. Lots of short, natural examples. Highlight the grammar point with `<mark>`.
4. Common mistakes, shown side by side.
5. A short practice section with answers hidden.
6. A short summary.

Keep the level right: an A1 lesson uses only very simple words and short sentences; a C1 lesson can say more, but must still be clear. Explain like a patient teacher talking to one student. Prefer examples over terminology. Length: usually 500 to 1200 words of English. Part intros and section intros are shorter overviews that tell the learner what is coming in that part.

### Components (use these class names exactly)

```html
<p class="lead">Nouns are words for people, places, things and ideas.</p>

<h2>What is a noun?</h2>
<p>Normal paragraph text.</p>

<div class="rule"><p><strong>Rule:</strong> Add <mark>-s</mark> to most nouns to make them plural.</p></div>

<div class="examples">
  <p>I have two <mark>cats</mark>.</p>
  <p>She lives in <mark>London</mark>.</p>
</div>

<div class="compare">
  <p class="wrong">I need an advice.</p>
  <p class="right">I need some advice.</p>
</div>

<div class="tip"><p>Short helpful note.</p></div>

<div class="table-wrap"><table class="grid">
  <tr><th>Singular</th><th>Plural</th></tr>
  <tr><td>cat</td><td>cats</td></tr>
</table></div>

<div class="practice"><ol>
  <li>Choose: I saw ___ elephant. (a / an)
    <details><summary>Answer</summary><p><strong>an</strong> elephant, because "elephant" starts with a vowel sound.</p></details></li>
</ol></div>

<div class="summary"><ul>
  <li>One short line per key point.</li>
</ul></div>
```

Do not add `<style>`, `<script>`, `<html>`, `<head>` or `<body>`. Do not invent new classes.

## 3. Reviews (reviews/chapter-NN.md)

Review the other mind's lessons, never your own. Start the file with:

```
VERDICT: APPROVED
Reviewer: YourName
```

or `VERDICT: CHANGES NEEDED`, then a short list of exactly what to fix. Check: is every grammar statement correct? Are the examples natural English? Is it right for the level? Is it clear and kind? Are the practice answers correct? Is the format right? Approve only what you would be proud to show a real student. A lesson that changes after review needs a new review.

## 4. Always

- American spelling, as in the existing book.
- Never use em dashes or en dashes. Use commas, full stops, or brackets.
- Correctness over speed. A wrong grammar rule taught to a learner does real harm.
