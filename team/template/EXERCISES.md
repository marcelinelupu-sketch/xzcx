# How exercises are made for this book

Every chapter gets **5 to 10 exercise sets, each with 3 or 4 items.** Simple chapters (A1, A2, short topics) get 5 sets. Complex chapters (many forms, many contrasts, C1 and C2) get up to 10. The expert decides the number in the blueprint.

A chapter counts as complete for a learner when every item is answered and at least 80% were right on the first try. So exercises must be fair: one clearly right answer, no tricks, no ambiguity, no grammar the chapter has not taught (earlier chapters are fine).

## Roles

- **The expert (Opus):** for each chapter whose lesson is peer approved:
  1. Checks the lesson's grammar and clarity, writes `checks/lesson-NN.md` with `VERDICT: PASS` or `VERDICT: FIX NEEDED` plus exactly what is wrong. Be strict about correctness, generous about style.
  2. Studies how the reference books teach this topic (search `../references/`, read only the relevant unit): what it covers, which contrasts it builds, which mistakes it targets, how the exercises progress, what kinds of tasks they use. Then writes `blueprints/chapter-NN.md` **in its own words**: the number of sets, and for each set what it trains, the task type, the logic that drives the items (for example "pairs where only the time word changes, so the learner must notice it"), the traps to include, and a mood for the set. No sentences from the books, ever.
  3. Checks finished exercises: `checks/exercises-NN.md` with `VERDICT: PASS` or `VERDICT: FIX NEEDED`. Every answer must be correct and the only correct one, every sentence natural, every set matching the blueprint.
- **The exercise writer (Sonnet):** writes `exercises/chapter-NN.json` from the blueprint and the lesson, and fixes them when the expert asks. It may read the reference books to understand a method, never to copy.

## The vibe

Rhyme Art: art, poetry, feeling, beautiful melancholy, made understandable. Mostly autumn as a wide, changing atmosphere (rain, fading light, letters never sent, an empty train station, the smell of old books, a garden after the first frost) and sometimes a deliberate escape to a completely different world (the sea at night, a desert, a winter city, the first warm day of spring, a concert hall). Not recurring characters: a mood. Each set can have its own small scene, so items in a set feel connected. The mood comes from the situation, not from hard words: at A1 sentences stay short and simple. Every item must make sense and sound like real English.

## Format: exercises/chapter-NN.json

```json
{
  "chapter": 12,
  "sets": [
    {
      "title": "Rain on the window",
      "instruction": "Choose the right word.",
      "type": "choice",
      "items": [
        {"q": "She ___ the window and listens to the rain.", "options": ["open", "opens", "opening"], "answer": 1,
         "why": "She is one person, so the verb takes -s."}
      ]
    },
    {
      "title": "Letters",
      "instruction": "Write the missing word.",
      "type": "gap",
      "items": [
        {"q": "He ___ (not / write) to her anymore.", "answer": ["doesn't write", "does not write"], "why": "Negative with he: doesn't + base form."}
      ]
    },
    {
      "title": "Fading light",
      "instruction": "Put the words in order.",
      "type": "order",
      "items": [
        {"words": ["the", "light", "fades", "slowly"], "answer": ["the light fades slowly"], "why": "Subject, verb, then the adverb."}
      ]
    },
    {
      "title": "Find the mistake",
      "instruction": "Click the wrong part.",
      "type": "error",
      "items": [
        {"segments": ["The leaves", "falls", "in October."], "answer": 1, "fix": "fall", "why": "The leaves is plural, so: fall."}
      ]
    }
  ]
}
```

Rules:
- `choice`: 2 to 5 options, `answer` is the index (0 = first). Use `___` in `q` for the gap.
- `gap`: exactly one `___`; `answer` is a list of every acceptable answer (contractions and full forms). Put hints in brackets in `q` when needed.
- `order`: `answer` must use exactly the words in `words`, separated by single spaces, in lowercase except names and "I". No punctuation in words. List every acceptable order.
- `error`: `segments` split the sentence into 3 to 6 parts; exactly one is wrong; `fix` is its correct form.
- Every item has a short `why` in A2 words: the reason, not just the answer.
- Vary task types within a chapter; the order of sets goes from easy to hard.
- Difficult words can get vocabulary popups exactly like in lessons: `<span class=\"v\" data-def=\"simple definition\">word</span>` (escape the quotes in JSON). Do not mark the word the learner must choose or write.
- Never use em dashes or en dashes. American spelling.
- The build checks the format and flags any text that shares 6 or more words in a row with the reference books.
