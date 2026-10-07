#!/usr/bin/env python3
"""The polish: four stages, all Opus, each resumable (finished chapters are skipped on a rerun).

  deepen   add 1 or 2 Murphy-method sets per chapter (situation -> form), checked by an independent Opus
  review   a fresh, harsh reviewer reads the TOC, then every chapter in order, and writes notes
  fix      a writer who shares the reviewer's philosophy improves everything the notes ask for
  verify   independent checks of every changed lesson and exercise file

Usage: python3 team/polish.py deepen|review|fix|verify [--workers 5]
Notes:   team/book/review/TOC.md, team/book/review/chapter-NN.md, team/book/review/journal-*.md
Records: team/state/polish/<stage>-NN.done, costs in team/state/polish/costs.jsonl
"""

import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

HERE = Path(__file__).resolve().parent
BOOK = HERE / "book"
REV = BOOK / "review"
REC = HERE / "state" / "polish"
MODEL = "claude-opus-5-5"
lock = threading.Lock()

READER = """The readers of this book are people learning English, from complete beginners (A1) to \
advanced (C2), many of them reading slowly in their second language, often tired after work. The book \
is "A Modern Guide to English Grammar" by Rhyme Art, a small English teaching business run by Wojtek \
and his wife Lana, who teach English through art, poetry and stories. Its promise: every lesson VERY easy \
to understand, VERY easy to remember, as short as possible without losing clarity, perfectly formatted, \
C1 grammar explained in A2 words, examples and exercises in Rhyme Art's mood (mostly a wide autumn \
atmosphere of beauty and gentle melancholy, sometimes other worlds), every word correct. Read STYLE.md \
and EXERCISES.md in your folder for the house rules and formats. Never use em dashes or en dashes."""

DEEPEN = READER + """

YOUR JOB: make this chapter's exercises teach as well as Murphy's Grammar in Use does, without copying \
anything from it. Murphy's strength: the learner reads a short SITUATION and must decide which form fits \
and why, so they learn the MEANING of the grammar, not just its shape (for example: "He is looking for \
his key. He can't find it." leads to "He has lost his key."). Our current exercises are mostly recognition \
and form drills, often with only two options.

1. Read the lesson (lessons/chapter-NN.html), the blueprint and the current exercises (exercises/chapter-NN.json).
2. Study how Murphy teaches this exact topic: search ../references/ (read its README), read only the \
relevant unit and its exercises. Learn the method: which situations, which contrasts, how meaning is tested.
3. Add 1 or 2 new sets (2 for complex chapters) built on that method, written entirely in your own words \
and in the Rhyme Art mood: each item gives a short situation (one or two simple sentences) and asks for the \
form that fits. Use "choice" with 3 or 4 options (plausible wrong options that real learners pick) or "gap" \
with every acceptable answer listed. Every item must have exactly one right answer and a short "why" in A2 \
words that explains the meaning, not just the rule. Keep the language at the chapter's level.
4. The chapter must keep 5 to 10 sets of 3 or 4 items. If adding would exceed 10, replace the weakest, most \
redundant recognition sets. Order sets from easy to hard; the new sets usually come near the end.
5. Edit exercises/chapter-NN.json in place, keep valid JSON and the exact format of EXERCISES.md, change \
nothing else. Never copy or closely paraphrase any sentence from the reference books.

At the end, say in two sentences what you added."""

DEEPEN_CHECK = READER + """

YOUR JOB: independently check the exercises of this chapter, especially the sets that were just added \
(the situation-based ones). For every item: is the answer correct, is it the ONLY correct answer, is the \
situation clear and natural English, is the "why" right and simple, is the level right? Fix any problem \
yourself directly in exercises/chapter-NN.json (keep the format). Then write checks/exercises-NN.md starting \
with "VERDICT: PASS" (after your fixes, if all is right) followed by a short note of what you checked or \
changed. Write VERDICT: FIX NEEDED only if something is wrong that you could not fix."""

REVIEWER = READER + """

YOU ARE THE BOOK'S HARSHEST, MOST CARING REVIEWER. You read it with fresh eyes, as the protector of the \
person who will read it: you want them to have the best possible experience, to understand at once, to \
remember, to never be confused, bored, misled or made to feel stupid. You have excellent taste. You are \
harsh because you care: praise only what truly works, and name every problem precisely.

Look at everything: correctness of every rule and example; clarity for a tired A2 reader; brevity (every \
unnecessary word is a cost); order and flow (does each step prepare the next); formatting (does it help \
the eye: formula, colors, tables, centered layout); examples (natural, memorable, in the mood, never \
clichés like "Is there a bank near here?"); mood (beautiful and coherent, not forced, not gloomy for its \
own sake); exercises (fair, clear, varied, one right answer, good wrong options, real thinking not \
guessing, explanations that teach); consistency with the rest of the book; anything a learner might \
misunderstand.

Write notes a writer can act on: quote the exact text, say what is wrong and what to do instead. Mark each \
note MUST FIX (wrong, confusing or harmful), SHOULD FIX (clearly better if changed) or NICE (polish). If \
something is excellent, say so in one line so it is kept."""

FIXER = READER + """

YOU ARE THE BOOK'S FINAL WRITER. You share the reviewer's philosophy completely: you protect the reader \
and want them to have the best possible experience. A harsh reviewer has read this chapter; its notes are \
in review/chapter-NN.md (and the book-wide notes in review/TOC.md and the journals show patterns).

Improve the chapter: fix every MUST FIX, fix every SHOULD FIX unless it would make things worse (then say \
why), apply NICE notes when they truly help. You may rewrite whole parts if that serves the reader better. \
Edit lessons/chapter-NN.html and exercises/chapter-NN.json in place, following STYLE.md and EXERCISES.md \
exactly (components, JSON format, 5 to 10 sets of 3 or 4 items, every answer correct and the only one). \
Keep what the reviewer called excellent. Never copy from the reference books. At the end write \
review/fixed-NN.md: for each note, what you did (or why not)."""

VERIFY = READER + """

YOU ARE AN INDEPENDENT CHECKER. This chapter was just revised. Check the lesson (lessons/chapter-NN.html) \
and the exercises (exercises/chapter-NN.json) with full care: every grammar statement correct, every example \
natural, every exercise answer correct and the only correct one, format exactly as in STYLE.md and \
EXERCISES.md, valid JSON. Fix small problems yourself. Then write checks/lesson-NN.md and \
checks/exercises-NN.md, each starting with "VERDICT: PASS" (or "VERDICT: FIX NEEDED" plus what is wrong, \
only if you could not fix it), followed by a short note."""


def log_cost(stage, n, cost):
    with lock:
        REC.mkdir(parents=True, exist_ok=True)
        with (REC / "costs.jsonl").open("a") as f:
            f.write(json.dumps({"stage": stage, "chapter": n, "usd": cost, "t": time.time()}) + "\n")


def run_agent(system, prompt, effort="medium", tools=True):
    settings = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|NotebookEdit|MultiEdit",
                                          "hooks": [{"type": "command", "command": f"python3 {HERE / 'guard.py'}"}]}]}}
    t = "Read,Write,Edit,Glob,Grep" if tools else ""
    cmd = ["claude", "-p", "--model", MODEL, "--effort", effort, "--system-prompt", system, "--tools", t]
    if tools:
        cmd += ["--allowedTools", t, "--add-dir", str(HERE / "references"), "--settings", json.dumps(settings)]
    cmd += ["--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--output-format", "json", prompt]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(BOOK))
    try:
        data = json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f"agent call failed: {r.stderr[-300:] or r.stdout[-300:]}")
    text = (data.get("result") or "").strip()
    cost = float(data.get("total_cost_usd") or 0)
    if data.get("is_error") or (not text and cost == 0):
        raise RuntimeError(f"agent call failed: {text[:300] or r.stderr[-300:]}")
    return text, cost


def done(stage, n):
    return (REC / f"{stage}-{n}.done").exists()


def mark(stage, n, text=""):
    REC.mkdir(parents=True, exist_ok=True)
    (REC / f"{stage}-{n}.done").write_text(text)


def chapter_info(c, descs):
    return (f"Chapter {c['n']}: {c['title']} ({c['kind']}, section: {c['section']}, part: {c['part']}, "
            f"level: {c['cefr']}). Description: {c['desc'] or descs.get(str(c['n']), '')}")


def valid(n):
    data, errs = build.load_exercises(n)
    return not errs, errs


# ---------- stage 1: deepen ----------

def safe(fn):
    def wrapped(*a):
        try:
            return fn(*a)
        except Exception as e:
            print(f"{fn.__name__} {a[0]['n'] if a and isinstance(a[0], dict) else ''} failed, will retry on next run: {e}", flush=True)
    wrapped.__name__ = fn.__name__
    return wrapped


@safe
def deepen_one(c, descs):
    n = c["n"]
    if done("deepen", n):
        return
    info = chapter_info(c, descs)
    total = 0.0
    note = ""
    for attempt in range(2):
        extra = "" if attempt == 0 else f" The file currently fails the format check: {valid(n)[1]}. Fix that first."
        note, cost = run_agent(DEEPEN.replace("NN", f"{n:02d}"), f"{info}\nWork on chapter {n}.{extra}")
        total += cost
        if valid(n)[0]:
            break
    note2, cost = run_agent(DEEPEN_CHECK.replace("NN", f"{n:02d}"), f"{info}\nCheck chapter {n}.")
    total += cost
    if not valid(n)[0]:
        note2 += f"\nFORMAT ERRORS REMAIN: {valid(n)[1]}"
    log_cost("deepen", n, total)
    mark("deepen", n, note + "\n---\n" + note2)
    print(f"deepen {n}: ${total:.2f}", flush=True)


# ---------- stage 2: review ----------

def toc_text(descs):
    lines = []
    for c in build.chapters():
        lines.append(f"{c['n']}. [{c['section']} / {c['part'] or '-'} / {c['cefr'] or '-'}] {c['title']}: {c['desc'] or descs.get(str(c['n']), '')}")
    return "\n".join(lines)


def review_toc(descs):
    if done("review", "toc"):
        return
    prompt = ("First, the table of contents, exactly as the learner meets it: section / part / level, title, and "
              "description of all 135 chapters.\n\n" + toc_text(descs) +
              "\n\nWrite your review of the TOC to review/TOC.md: the order and structure, every title and every "
              "description (quote them), gaps or overlaps, level labels, what a learner feels opening this book. "
              "Then write review/journal-start.md: your notes to yourself (patterns to watch for, under 300 words) "
              "that you will carry into the chapters.")
    note, cost = run_agent(REVIEWER, prompt, effort="high")
    log_cost("review", "toc", cost)
    mark("review", "toc", note)
    print(f"review TOC: ${cost:.2f}", flush=True)


@safe
def review_lane(lane, chapters, descs):
    journal = REV / f"journal-{lane}.md"
    for c in chapters:
        n = c["n"]
        if done("review", n):
            continue
        start = (REV / "journal-start.md").read_text() if (REV / "journal-start.md").exists() else ""
        prompt = (f"You are reading the book in order (this lane: {lane}). Your notes from the TOC:\n{start}\n\n"
                  f"Your running journal for this part of the book is review/{journal.name} (read it first if it exists).\n\n"
                  f"{chapter_info(c, descs)}\n\nRead lessons/chapter-{n:02d}.html and exercises/chapter-{n:02d}.json "
                  f"exactly as a learner would meet them (lesson first, then every exercise). Write your notes to "
                  f"review/chapter-{n:02d}.md. Then update review/{journal.name}: patterns across chapters, things that "
                  f"keep going wrong or right, under 400 words.")
        note, cost = run_agent(REVIEWER, prompt, effort="high")
        log_cost("review", n, cost)
        mark("review", n, note)
        print(f"review {n}: ${cost:.2f}", flush=True)


# ---------- stage 3: fix ----------

def fix_toc(descs):
    if done("fix", "toc"):
        return
    prompt = ("Read review/TOC.md. Apply the description changes it asks for by editing descriptions.json "
              "(chapter number -> description; you may also override existing descriptions there, the build "
              "prefers descriptions.json only for chapters without one, so for chapters that already have a "
              "description in chapters.json write your improved version into review/toc-description-changes.json "
              "as {\"<n>\": \"new description\"}). Do not rename chapters or change the structure: write any such "
              "suggestions to review/toc-suggestions-for-wojtek.md for Wojtek to decide.")
    note, cost = run_agent(FIXER, prompt)
    log_cost("fix", "toc", cost)
    mark("fix", "toc", note)
    print(f"fix TOC: ${cost:.2f}", flush=True)


@safe
def fix_one(c, descs):
    n = c["n"]
    if done("fix", n) or not (REV / f"chapter-{n:02d}.md").exists():
        return
    total = 0.0
    for attempt in range(2):
        extra = "" if attempt == 0 else f" The exercises file fails the format check: {valid(n)[1]}. Fix that."
        note, cost = run_agent(FIXER.replace("NN", f"{n:02d}"), f"{chapter_info(c, descs)}\nImprove chapter {n}.{extra}")
        total += cost
        if valid(n)[0]:
            break
    log_cost("fix", n, total)
    mark("fix", n, note)
    print(f"fix {n}: ${total:.2f}", flush=True)


# ---------- stage 4: verify ----------

@safe
def verify_one(c, descs):
    n = c["n"]
    if done("verify", n):
        return
    rows = build.progress(detail=True)["rows"][n]
    flags = (rows.get("copy_flags") or []) + (rows.get("exercise_copy_flags") or [])
    extra = ("" if not flags else
             f" The copying check found these word sequences that also appear in the reference books: {flags}. "
             "Rewrite every sentence containing them in fresh words of your own (instructions too), unless the words "
             "are an unavoidable grammar term.")
    note, cost = run_agent(VERIFY.replace("NN", f"{n:02d}"), f"{chapter_info(c, descs)}\nCheck chapter {n}.{extra}")
    log_cost("verify", n, cost)
    mark("verify", n, note)
    print(f"verify {n}: ${cost:.2f}", flush=True)


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 5
    REV.mkdir(parents=True, exist_ok=True)
    descs = build.descriptions()
    chs = build.chapters()
    if stage == "deepen":
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(lambda c: deepen_one(c, descs), chs))
    elif stage == "review":
        review_toc(descs)
        lanes = {}
        for c in chs:
            lanes.setdefault(c["section"], []).append(c)
        with ThreadPoolExecutor(len(lanes)) as ex:
            list(ex.map(lambda kv: review_lane(re.sub(r"[^a-z]+", "-", kv[0].lower()).strip("-"), kv[1], descs), lanes.items()))
    elif stage == "fix":
        fix_toc(descs)
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(lambda c: fix_one(c, descs), chs))
    elif stage == "verify":
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(lambda c: verify_one(c, descs), chs))
    else:
        print(__doc__)
        return
    costs = [json.loads(l) for l in (REC / "costs.jsonl").read_text().splitlines()] if (REC / "costs.jsonl").exists() else []
    print(f"{stage} finished. stage cost ${sum(x['usd'] for x in costs if x['stage'] == stage):.2f}, all polish ${sum(x['usd'] for x in costs):.2f}")


if __name__ == "__main__":
    main()
