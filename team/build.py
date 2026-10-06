#!/usr/bin/env python3
"""Build the grammar book and measure everyone's progress from the files themselves.

Writers (two Sonnets) produce, inside team/book/:
  lessons/chapter-NN.html     lesson body, first line <!-- author: NAME -->
  reviews/chapter-NN.md       peer review: "VERDICT: APPROVED" or "VERDICT: CHANGES NEEDED"
The exercise team (Opus expert + Sonnet exercise writer) produces:
  blueprints/chapter-NN.md    the expert's plan for the chapter's exercises
  checks/lesson-NN.md         expert grammar check of the lesson: "VERDICT: PASS" or "VERDICT: FIX NEEDED"
  exercises/chapter-NN.json   the exercises (format in EXERCISES.md)
  checks/exercises-NN.md      expert check of the exercises: "VERDICT: PASS" or "VERDICT: FIX NEEDED"

Output: team/site/ (toc.html, chapter-NN.html, assets/). Vocabulary index: team/vocab/.

Usage:
  python3 team/build.py           build the site and print progress
  python3 team/build.py status    print progress only
"""

import hashlib
import html as htmlmod
import json
import pickle
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vocabtag  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE_TOC = HERE / "source" / "toc_original.html"
BOOK = HERE / "book"
SITE = HERE / "site"
STATIC = HERE / "static"
TEMPLATE = HERE / "template" / "lesson.html"
REFS = HERE / "references"
VOCAB = HERE / "vocab"
NGRAM_CACHE = HERE / "state" / "ref_ngrams.pkl"
NGRAM = 6
TYPES = {"choice", "gap", "order", "error"}


def clean(text):
    """Owner rule: no em or en dashes in anything the team writes."""
    return re.sub(r"[ \t]*[–—][ \t]*", ", ", text)


def chapters():
    return json.loads((BOOK / "chapters.json").read_text())


def descriptions():
    p = BOOK / "descriptions.json"
    try:
        return {str(k): clean(v).strip() for k, v in json.loads(p.read_text()).items() if str(v).strip()}
    except (OSError, ValueError, AttributeError):
        return {}


def path(kind, n):
    return {
        "lesson": BOOK / "lessons" / f"chapter-{n:02d}.html",
        "review": BOOK / "reviews" / f"chapter-{n:02d}.md",
        "blueprint": BOOK / "blueprints" / f"chapter-{n:02d}.md",
        "lesson_check": BOOK / "checks" / f"lesson-{n:02d}.md",
        "exercises": BOOK / "exercises" / f"chapter-{n:02d}.json",
        "exercise_check": BOOK / "checks" / f"exercises-{n:02d}.md",
    }[kind]


def mtime(p):
    return p.stat().st_mtime if p.exists() else None


def verdict(p, after):
    """(verdict, current). current = written after the thing it judges was last changed."""
    if not p.exists():
        return None, False
    m = re.search(r"VERDICT:?\**\s*\**\s*(APPROVED|PASS(?:ED)?|CHANGES? NEEDED|NEEDS? CHANGES?|FIX(?:ES)? NEEDED|NEEDS? FIX(?:ES)?|FAIL(?:ED)?)", p.read_text(), re.I)
    raw = m.group(1).upper() if m else "UNCLEAR"
    v = ("APPROVED" if raw == "APPROVED" else "PASS" if raw.startswith("PASS") else
         "UNCLEAR" if raw == "UNCLEAR" else "FIX NEEDED" if "FIX" in raw or raw.startswith("FAIL") else "CHANGES NEEDED")
    return v, (after is not None and mtime(p) >= after)


def author_of(n):
    p = path("lesson", n)
    if not p.exists():
        return None
    m = re.match(r"\s*<!--\s*author:\s*(.*?)\s*-->", p.read_text())
    return m.group(1).strip() if m else None


# ---------- copyright overlap ----------

def words(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmlmod.unescape(text)
    return re.findall(r"[a-z0-9']+", text.lower())


def h(gram):
    return int.from_bytes(hashlib.blake2b(gram.encode(), digest_size=8).digest(), "big")


def ref_ngrams():
    if NGRAM_CACHE.exists():
        return pickle.loads(NGRAM_CACHE.read_bytes())
    grams = set()
    for p in REFS.glob("*.md"):
        if p.name == "README.md":
            continue
        w = words(p.read_text(errors="ignore"))
        grams.update(h(" ".join(w[i:i + NGRAM])) for i in range(len(w) - NGRAM + 1))
    NGRAM_CACHE.parent.mkdir(exist_ok=True)
    NGRAM_CACHE.write_bytes(pickle.dumps(grams))
    return grams


def overlaps(text, grams):
    w = words(text)
    hits = []
    for i in range(len(w) - NGRAM + 1):
        if h(" ".join(w[i:i + NGRAM])) in grams:
            hits.append(" ".join(w[i:i + NGRAM]))
    # very common teaching phrases are tolerated if they are only one isolated hit
    return hits if len(hits) >= 2 else []


# ---------- exercises ----------

def load_exercises(n):
    p = path("exercises", n)
    if not p.exists():
        return None, ["missing"]
    try:
        data = json.loads(p.read_text())
    except ValueError as e:
        return None, [f"invalid JSON: {e}"]
    errs = []
    sets = data.get("sets") if isinstance(data, dict) else None
    if not isinstance(sets, list) or not sets:
        return None, ["no sets"]
    if not 5 <= len(sets) <= 10:
        errs.append(f"{len(sets)} sets (must be 5 to 10)")
    for si, s in enumerate(sets):
        items = s.get("items") or []
        if not 3 <= len(items) <= 4:
            errs.append(f"set {si + 1}: {len(items)} items (must be 3 or 4)")
        for ii, it in enumerate(items):
            t = it.get("type") or s.get("type")
            where = f"set {si + 1} item {ii + 1}"
            if t not in TYPES:
                errs.append(f"{where}: unknown type {t!r}")
                continue
            try:
                if t == "choice":
                    assert isinstance(it["options"], list) and 2 <= len(it["options"]) <= 5
                    assert 0 <= int(it["answer"]) < len(it["options"])
                    assert it.get("q")
                elif t == "gap":
                    assert "___" in it["q"] and it["answer"]
                elif t == "order":
                    assert isinstance(it["words"], list) and len(it["words"]) >= 2 and it["answer"]
                    ans = it["answer"] if isinstance(it["answer"], list) else [it["answer"]]
                    for a in ans:
                        assert sorted(re.sub(r"\s+", " ", a).strip().split(" ")) == sorted(it["words"]), "answer must use exactly the given words"
                elif t == "error":
                    assert isinstance(it["segments"], list) and len(it["segments"]) >= 2
                    assert 0 <= int(it["answer"]) < len(it["segments"]) and it.get("fix")
            except (KeyError, AssertionError, ValueError, TypeError) as e:
                errs.append(f"{where} ({t}): malformed {e}".strip())
    return data, errs


# ---------- vocabulary ----------

VSPAN = re.compile(r'<span class="v" data-def="([^"]+)">(.*?)</span>', re.S)


def vocab_id(word, definition):
    return hashlib.sha1(f"{word.strip().lower()}|{definition.strip().lower()}".encode()).hexdigest()[:10]


def tag_vocab(text, found, context_of):
    def sub(m):
        d, w = m.group(1), m.group(2)
        wid = vocab_id(re.sub(r"<[^>]+>", "", w), d)
        if wid not in found:
            found[wid] = {"word": re.sub(r"<[^>]+>", "", w), "def": htmlmod.unescape(d), "context": context_of(m)}
        return f'<span class="v" data-id="{wid}" data-def="{d}">{w}</span>'
    return VSPAN.sub(sub, text)


def sentence_around(text, m):
    plain_before = re.sub(r"<[^>]+>", "", text[max(0, m.start() - 300):m.start()])
    plain_after = re.sub(r"<[^>]+>", "", text[m.end():m.end() + 300])
    before = re.split(r"(?<=[.!?])\s|\n", plain_before)[-1]
    after = re.split(r"(?<=[.!?])\s|\n", plain_after)[0]
    return htmlmod.unescape((before + re.sub(r"<[^>]+>", "", m.group(2)) + after).strip())[:300]


def glossary():
    try:
        return json.loads((VOCAB / "glossary.json").read_text())
    except (OSError, ValueError):
        return {"senses": {}, "words": {}, "occ": {}}


def tagger(g, used):
    def rep(key, word):
        sid = g["occ"].get(key)
        if not sid or sid not in g["senses"]:
            return None
        used.add(sid)
        return f'<span class="v" data-id="{sid}">{word}</span>'
    return rep


def vocab_payload(g, used):
    return {sid: {"def": g["senses"][sid]["def"], "tr": g["senses"][sid].get("tr", {})} for sid in sorted(used)}


def build_toc_vocab(g, descs):
    per_chapter, used, counter = {}, set(), {}
    for c in chapters():
        n = c["n"]
        _, occ = vocabtag.walk(vocabtag.toc_text(c, c["desc"] or descs.get(str(n), "")), f"T{n}", counter)
        m = {}
        for key, word, ctx in occ:
            sid = g["occ"].get(key)
            lw = key.split("|")[1]
            if sid in g["senses"] and lw not in m:
                m[lw] = sid
                used.add(sid)
        per_chapter[n] = m
    js = ("window.TOCVOCAB = " + json.dumps(per_chapter, ensure_ascii=False) + ";\n"
          "window.VOCAB = " + json.dumps(vocab_payload(g, used), ensure_ascii=False) + ";\n")
    (SITE / "assets" / "toc-vocab.js").write_text(js)


# ---------- progress ----------

def progress(writers=None, detail=False):
    writers = writers or {}
    chs = chapters()
    descs = descriptions()
    grams = ref_ngrams()
    missing_desc = [c["n"] for c in chs if not c["desc"] and str(c["n"]) not in descs]
    rows = {}
    for c in chs:
        n = c["n"]
        lp = path("lesson", n)
        r = {"lesson": lp.exists()}
        if r["lesson"]:
            lt = mtime(lp)
            v, cur = verdict(path("review", n), lt)
            lesson_by = writers.get(f"lessons/chapter-{n:02d}.html") or author_of(n)
            review_by = writers.get(f"reviews/chapter-{n:02d}.md")
            r["peer"] = ("approved" if v == "APPROVED" and cur and review_by != lesson_by else
                         "changes" if v == "CHANGES NEEDED" and cur else
                         "self-approved (does not count)" if v == "APPROVED" and cur else "awaiting")
            ev, ecur = verdict(path("lesson_check", n), lt)
            r["expert"] = "pass" if ev == "PASS" and ecur else "fix" if ev == "FIX NEEDED" and ecur else "awaiting"
            r["copy_flags"] = overlaps(lp.read_text(), grams)[:3]
            r["vocab_words"] = len(VSPAN.findall(lp.read_text()))
        r["blueprint"] = path("blueprint", n).exists()
        data, errs = load_exercises(n)
        if data is not None or errs != ["missing"]:
            r["exercise_errors"] = errs[:5]
            xt = mtime(path("exercises", n))
            xv, xcur = verdict(path("exercise_check", n), xt)
            r["exercise_check"] = "pass" if xv == "PASS" and xcur else "fix" if xv == "FIX NEEDED" and xcur else "awaiting"
            if data is not None:
                r["exercise_copy_flags"] = overlaps(json.dumps(data), grams)[:3]
        rows[n] = r

    def L(cond):
        return [n for n, r in rows.items() if cond(r)]

    summary = {
        "descriptions_missing": missing_desc,
        "lessons_written": len(L(lambda r: r["lesson"])),
        "lessons_finished (peer approved AND expert passed)": len(L(lambda r: r.get("peer") == "approved" and r.get("expert") == "pass")),
        "lessons_awaiting_peer_review": L(lambda r: r["lesson"] and r["peer"] == "awaiting"),
        "lessons_needing_changes_from_peer_review": L(lambda r: r.get("peer") == "changes"),
        "lessons_awaiting_expert_check (peer approved)": L(lambda r: r.get("peer") == "approved" and r.get("expert") == "awaiting"),
        "lessons_needing_fixes_from_expert": L(lambda r: r.get("expert") == "fix"),
        "lessons_flagged_for_copying_reference_books": {n: r["copy_flags"] for n, r in rows.items() if r.get("copy_flags")},
        "lessons_not_yet_written": L(lambda r: not r["lesson"]),
        "blueprints_written": len(L(lambda r: r["blueprint"])),
        "chapters_ready_for_exercises (lesson passed, blueprint written, no exercises yet)": L(lambda r: r.get("expert") == "pass" and r["blueprint"] and "exercise_check" not in r),
        "chapters_with_passed_lesson_but_no_blueprint": L(lambda r: r.get("expert") == "pass" and not r["blueprint"]),
        "exercises_written": len(L(lambda r: "exercise_check" in r)),
        "exercises_finished (expert passed, valid)": len(L(lambda r: r.get("exercise_check") == "pass" and not r.get("exercise_errors"))),
        "exercises_with_format_errors": {n: r["exercise_errors"] for n, r in rows.items() if r.get("exercise_errors")},
        "exercises_awaiting_expert_check": L(lambda r: r.get("exercise_check") == "awaiting"),
        "exercises_needing_fixes_from_expert": L(lambda r: r.get("exercise_check") == "fix"),
        "exercises_flagged_for_copying_reference_books": {n: r["exercise_copy_flags"] for n, r in rows.items() if r.get("exercise_copy_flags")},
        "total_chapters": len(chs),
    }
    if detail:
        summary["rows"] = rows
    return summary


# ---------- site ----------

TOC_PATCH = """
<link rel="stylesheet" href="assets/toc-progress.css">
<script src="assets/progress-config.js"></script>
<script src="assets/progress.js"></script>
<script src="assets/toc-progress.js"></script>
<script src="assets/toc-vocab.js"></script>
<script src="assets/book.js"></script>
</body>"""


def build_toc(descs):
    html = SOURCE_TOC.read_text()
    start = html.index("const BANNERS = [")
    end = html.index("\n];", start) + 3
    block = html[start:end]
    js = block + """
const D = JSON.parse(process.argv[1]); let n = 0;
for (const b of BANNERS) { n++; if (!b.intro.desc && D[n]) b.intro.desc = D[n];
  for (const p of b.parts) for (const c of p.chapters) { n++; if (!c.desc && D[n]) c.desc = D[n]; } }
process.stdout.write(JSON.stringify(BANNERS, null, 1));
"""
    out = subprocess.run(["node", "-e", js, json.dumps(descs)], capture_output=True, text=True, check=True).stdout
    html = html[:start] + "const BANNERS = " + out + ";" + html[end:]
    return html.replace("</body>", TOC_PATCH, 1)


def build(only_finished=False):
    SITE.mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    for f in STATIC.iterdir():
        shutil.copy(f, SITE / "assets" / f.name)
    descs = descriptions()
    (SITE / "toc.html").write_text(build_toc(descs))
    prog = progress(detail=True)
    rows = prog["rows"]
    chs = chapters()
    by_n = {c["n"]: c for c in chs}
    tpl = TEMPLATE.read_text()
    g = glossary()
    build_toc_vocab(g, descs)
    existing = [c["n"] for c in chs if path("lesson", c["n"]).exists()]
    if only_finished:
        existing = [n for n in existing if rows[n].get("peer") == "approved" and rows[n].get("expert") == "pass"]
    for n in existing:
        c = by_n[n]
        used, counter = set(), {}
        rep = tagger(g, used)
        raw = re.sub(r"^\s*<!--\s*author:.*?-->\s*", "", path("lesson", n).read_text(), count=1)
        body, _ = vocabtag.walk(clean(vocabtag.strip_manual(raw)), f"L{n}", counter, rep)
        ex_json = "null"
        data, errs = load_exercises(n)
        if data is not None and not errs and rows[n].get("exercise_check") == "pass":
            for obj, f in vocabtag.exercise_fields(data):
                obj[f], _ = vocabtag.walk(clean(obj[f]), f"X{n}", counter, rep)
            ex_json = clean(json.dumps(data, ensure_ascii=False)).replace("</", "<\\/")
        page_vocab = vocab_payload(g, used)
        crumb = " · ".join(x for x in (c["section"], c["part"]) if x)
        desc = c["desc"] or descs.get(str(n), "")
        i = existing.index(n)
        prev = f'<a class="prev" href="chapter-{existing[i-1]:02d}.html"><span class="label">Previous</span>{by_n[existing[i-1]]["title"]}</a>' if i > 0 else ""
        nxt = f'<a class="next" href="chapter-{existing[i+1]:02d}.html"><span class="label">Next</span>{by_n[existing[i+1]]["title"]}</a>' if i + 1 < len(existing) else ""
        page = (tpl.replace("{{TITLE}}", c["title"]).replace("{{CRUMB}}", crumb).replace("{{NUM}}", str(n))
                .replace("{{DESC}}", desc).replace("{{LEVEL}}", f'<span class="level">{c["cefr"]}</span>' if c["cefr"] else "")
                .replace("{{PREV}}", prev).replace("{{NEXT}}", nxt)
                .replace("{{VOCAB}}", json.dumps(page_vocab, ensure_ascii=False).replace("</", "<\\/"))
                .replace("{{EXERCISES}}", ex_json).replace("{{BODY}}", body))
        (SITE / f"chapter-{n:02d}.html").write_text(page)
    return len(existing)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(progress(), indent=2))
    else:
        pages = build(only_finished="--finished" in sys.argv)
        print(f"built toc.html and {pages} lesson pages into {SITE}")
