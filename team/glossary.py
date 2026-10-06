#!/usr/bin/env python3
"""Builds the book's glossary: every word with meaning, everywhere it is read, gets a simple English
definition for its meaning in that sentence and a translation into the TOC's 30 languages.

1. Collects every word occurrence (lessons, exercise texts, TOC titles and descriptions) with
   vocabtag.walk, so keys match exactly what build.py will underline.
2. New words: Opus reads up to 8 sentences per word, finds its distinct meanings in this book,
   writes a definition and translations for each, and says which sentence uses which meaning.
3. Words with more than one meaning: every occurrence is assigned to its meaning by Opus.
4. Known words with one meaning: new occurrences get that meaning without a model call.

Incremental: run it again after content changes; only new words and occurrences cost anything.
Output: team/vocab/glossary.json. Then run build.py.

Usage: python3 team/glossary.py [--workers 6] [--batch 16]
"""

import json
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import vocabtag  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "vocab" / "glossary.json"
MODEL = "claude-opus-5-5"
LANGS = {"sq": "Albanian", "ar": "Arabic", "bs": "Bosnian", "bg": "Bulgarian", "hr": "Croatian", "cs": "Czech",
         "da": "Danish", "nl": "Dutch", "et": "Estonian", "fi": "Finnish", "fr": "French", "de": "German",
         "el": "Greek", "hu": "Hungarian", "it": "Italian", "lv": "Latvian", "lt": "Lithuanian", "mk": "Macedonian",
         "no": "Norwegian (Bokmal)", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
         "sr": "Serbian (Cyrillic)", "sk": "Slovak", "sl": "Slovenian", "es": "Spanish", "sv": "Swedish",
         "tr": "Turkish", "uk": "Ukrainian"}

DISCOVER = """You build the glossary of an English grammar book for learners (A1 to C2). Every English \
word given to you appears in the book; you see sample sentences where it is used.

For each word:
1. Decide whether it should be skipped: skip only people's names, single letters, abbreviations used as \
labels, and non-words. Grammar terms (noun, verb, tense...) are NOT skipped.
2. Find its distinct meanings AS USED IN THESE SENTENCES (usually one). Do not list meanings that do not \
appear in the sentences.
3. For each meaning write "def": a very simple English definition a beginner understands, at most 12 \
words, for that meaning only. If the word is an inflected form, start with the base: "fell: past of fall, \
went down to the ground" style is good ("past of fall: ...").
4. For each meaning give "tr": the translation of the word in that meaning into every listed language: \
one short natural translation (a word or a few words) a learner would understand, matching the form where \
natural (plural for plurals, past for past forms). Use the correct script for each language.
5. "samples": map every sample number to the index of its meaning.

Output only JSON: {"<word>": {"skip": false, "senses": [{"def": "...", "tr": {"<code>": "..."}}], \
"samples": {"<n>": 0}}}. Every word, every language code. Never use em dashes or en dashes."""

ASSIGN = """For each sentence, decide which meaning of the given English word it uses. Output only JSON: \
{"<key>": <meaning index>} for every key."""

lock = threading.Lock()


def ask(system, prompt, effort="medium"):
    cmd = ["claude", "-p", "--model", MODEL, "--effort", effort, "--system-prompt", system, "--tools", "",
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--output-format", "json", prompt]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
    data = json.loads(r.stdout)
    text = data.get("result") or ""
    m = re.search(r"\{.*\}", text, re.S)
    return (json.loads(m.group(0)) if m else {}), float(data.get("total_cost_usd") or 0)


def collect():
    """All occurrences: {key: (word, context)} in reading order."""
    occ = {}
    counter = {}
    descs = build.descriptions()
    for c in build.chapters():
        n = c["n"]
        _, o = vocabtag.walk(vocabtag.toc_text(c, c["desc"] or descs.get(str(n), "")), f"T{n}", counter)
        occ.update({k: (w, ctx) for k, w, ctx in o})
        lp = build.path("lesson", n)
        if lp.exists():
            html = vocabtag.strip_manual(re.sub(r"^\s*<!--.*?-->", "", lp.read_text(), count=1))
            _, o = vocabtag.walk(html, f"L{n}", counter)
            occ.update({k: (w, ctx) for k, w, ctx in o})
        data, errs = build.load_exercises(n)
        if data is not None:
            for obj, f in vocabtag.exercise_fields(data):
                _, o = vocabtag.walk(obj[f], f"X{n}", counter)
                occ.update({k: (w, ctx) for k, w, ctx in o})
    return occ


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    batch = int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 16
    g = json.loads(OUT.read_text()) if OUT.exists() else {"senses": {}, "words": {}, "occ": {}}
    occ = collect()
    by_word = {}
    for k, (w, ctx) in occ.items():
        by_word.setdefault(k.split("|")[1], []).append((k, ctx))
    print(f"{len(occ)} occurrences, {len(by_word)} distinct words, {len(g['words'])} already known", flush=True)
    cost = [0.0]

    # 2. discover new words
    new = [w for w in by_word if w not in g["words"]]
    batches = []
    for i in range(0, len(new), batch):
        chunk = {}
        for w in new[i:i + batch]:
            seen, samples = set(), []
            for k, ctx in by_word[w]:
                if ctx not in seen:
                    seen.add(ctx)
                    samples.append((k, ctx))
            step = max(1, len(samples) // 8)
            chunk[w] = samples[::step][:8]
        batches.append(chunk)

    def discover(chunk):
        payload = {w: {str(j): ctx for j, (k, ctx) in enumerate(s)} for w, s in chunk.items()}
        prompt = "Languages: " + json.dumps(LANGS) + "\n\nWords and sample sentences:\n" + json.dumps(payload, ensure_ascii=False, indent=1)
        for attempt in range(3):
            try:
                res, c = ask(DISCOVER, prompt)
                break
            except Exception as e:  # retry transient failures
                print("discover error", e, flush=True)
                res, c = {}, 0.0
        with lock:
            cost[0] += c
            for w, s in chunk.items():
                r = res.get(w)
                if not isinstance(r, dict):
                    continue
                if r.get("skip"):
                    g["words"][w] = {"skip": True, "senses": []}
                    continue
                sids = []
                for si, sense in enumerate(r.get("senses") or []):
                    sid = f"{re.sub(r'[^a-z]', '', w)[:20]}{len(g['senses'])}"
                    g["senses"][sid] = {"word": w, "def": sense.get("def", ""), "tr": sense.get("tr", {})}
                    sids.append(sid)
                if not sids:
                    continue
                g["words"][w] = {"skip": False, "senses": sids}
                for j, (k, ctx) in enumerate(s):
                    idx = (r.get("samples") or {}).get(str(j), 0)
                    g["occ"][k] = sids[idx] if isinstance(idx, int) and idx < len(sids) else sids[0]
            OUT.parent.mkdir(exist_ok=True)
            OUT.write_text(json.dumps(g, ensure_ascii=False))
            print(f"discovered {len(g['words'])} words, ${cost[0]:.2f}", flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(discover, batches))

    # 3 and 4. assign every remaining occurrence
    assign_jobs = []
    for w, items in by_word.items():
        info = g["words"].get(w)
        if not info or info.get("skip"):
            continue
        todo = [(k, ctx) for k, ctx in items if k not in g["occ"]]
        if not todo:
            continue
        if len(info["senses"]) == 1:
            for k, _ in todo:
                g["occ"][k] = info["senses"][0]
        else:
            for i in range(0, len(todo), 60):
                assign_jobs.append((w, info["senses"], todo[i:i + 60]))

    def assign(job):
        w, sids, todo = job
        meanings = {i: g["senses"][sid]["def"] for i, sid in enumerate(sids)}
        prompt = f"Word: {w}\nMeanings: {json.dumps(meanings)}\nSentences: " + json.dumps({k: ctx for k, ctx in todo}, ensure_ascii=False, indent=1)
        try:
            res, c = ask(ASSIGN, prompt, effort="low")
        except Exception as e:
            print("assign error", e, flush=True)
            res, c = {}, 0.0
        with lock:
            cost[0] += c
            for k, _ in todo:
                idx = res.get(k, 0)
                g["occ"][k] = sids[idx] if isinstance(idx, int) and 0 <= idx < len(sids) else sids[0]

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(assign, assign_jobs))
    OUT.write_text(json.dumps(g, ensure_ascii=False))
    missing = [s for s in g["senses"].values() if len(s.get("tr", {})) < len(LANGS)]
    print(f"done: {len(g['senses'])} meanings, {len(g['occ'])} occurrences mapped, {len(missing)} meanings with missing languages, ${cost[0]:.2f}")


if __name__ == "__main__":
    main()
