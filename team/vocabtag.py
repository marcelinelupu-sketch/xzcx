"""Finds every word with meaning in the book's texts, the same way for collecting and for tagging.

A word occurrence gets a stable key "<scope>|<word>|<k>": scope is L<n> (lesson n), X<n> (exercise
texts of chapter n) or T<n> (TOC title and description of chapter n), k counts that word inside the
scope in reading order. glossary.py maps keys to senses; build.py wraps the same occurrences.
"""

import html as htmlmod
import re

WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
BLOCK = re.compile(r"^</?(p|div|td|th|li|h[1-6]|tr|table|ul|ol|br|section|summary|details)\b", re.I)
MANUAL_V = re.compile(r'<span class="v"[^>]*>(.*?)</span>', re.S)

FUNCTION = set("""
a an the this that these those
i me my mine myself you your yours yourself yourselves he him his himself she her hers herself it its itself
we us our ours ourselves they them their theirs themselves one ones oneself
who whom whose which what whatever whoever whichever where when why how
am is are was were be been being have has had having do does did done doing
will would shall should can could may might must ought
not no nor yes
and or but so yet if unless because although though while whereas whether than as
of in on at to for from by with without about against between among into onto out off over under up down
through across along around behind beyond during before after since until till upon within toward towards
near via per except despite
some any all both each every either neither none few many much more most less least several enough other another such
there here then now
s t d ll m re ve
""".split())
CONTRACTIONS = {"n't", "'s", "'re", "'ve", "'ll", "'d", "'m"}


def is_content(word):
    w = word.lower().replace("’", "'")
    if len(w) < 2 and w not in ("i",):
        return False
    base = w.split("'")[0]
    if w in FUNCTION or base in FUNCTION:
        return False
    if base.endswith("n") and w.endswith("n't"):           # don't, won't, can't, isn't...
        return False
    if base in ("don", "won", "can", "isn", "aren", "wasn", "weren", "hasn", "haven", "hadn", "doesn",
                "didn", "wouldn", "shouldn", "couldn", "mustn", "needn", "shan", "mightn", "let"):
        return False
    return True


def strip_manual(html):
    return MANUAL_V.sub(r"\1", html)


def walk(html, scope, counter, replace=None):
    """Yields nothing; returns (new_html, occurrences). occurrences: list of (key, word, context).
    replace(key, word) -> replacement html or None."""
    tokens = re.split(r"(<[^>]+>)", html)
    skip = 0
    skip_tag = None
    block = 0
    block_text = {}
    found = []          # (token index, start, end, key, word, block)
    for i, tok in enumerate(tokens):
        if tok.startswith("<"):
            low = tok.lower()
            if skip:
                if low.startswith("<" + skip_tag):
                    skip += 1
                elif low.startswith("</" + skip_tag):
                    skip -= 1
                continue
            if low.startswith(("<script", "<style")) or re.match(r'<span[^>]*class="[^"]*\b(v|term|term-title)\b', low):
                skip_tag = "span" if low.startswith("<span") else low[1:7].strip()
                skip = 1
            if BLOCK.match(low):
                block += 1
            continue
        text = htmlmod.unescape(tok)
        block_text[block] = block_text.get(block, "") + text
        if skip:
            continue
        for m in WORD.finditer(tok):
            w = m.group(0)
            if not is_content(w):
                continue
            lw = w.lower().replace("’", "'")
            k = counter.get((scope, lw), 0)
            counter[(scope, lw)] = k + 1
            found.append((i, m.start(), m.end(), f"{scope}|{lw}|{k}", w, block))
    occ = []
    for i, s, e, key, w, b in found:
        ctx = re.sub(r"\s+", " ", block_text.get(b, "")).strip()
        occ.append((key, w, ctx[:240]))
    if replace is None:
        return html, occ
    by_tok = {}
    for i, s, e, key, w, b in found:
        by_tok.setdefault(i, []).append((s, e, key, w))
    for i, spans in by_tok.items():
        tok = tokens[i]
        for s, e, key, w in sorted(spans, reverse=True):
            rep = replace(key, w)
            if rep:
                tok = tok[:s] + rep + tok[e:]
        tokens[i] = tok
    return "".join(tokens), occ


def exercise_fields(data):
    """The exercise texts that are read, never clicked: set titles and instructions, item questions
    (except clickable parts, which live in other fields) and explanations. Yields (setter, text)."""
    for s in data.get("sets", []):
        for f in ("title", "instruction"):
            if isinstance(s.get(f), str):
                yield s, f
        for it in s.get("items", []):
            for f in ("q", "why"):
                if isinstance(it.get(f), str):
                    yield it, f


def toc_text(chapter, desc):
    return f"<p>{chapter['title']}</p><p>{desc or ''}</p>"
