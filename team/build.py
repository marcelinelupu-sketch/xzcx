#!/usr/bin/env python3
"""Build the grammar book site from the team's work, and measure their progress.

Inputs (written by the team, inside team/book/):
  descriptions.json          {"<chapter number>": "short description", ...} for chapters that lack one
  lessons/chapter-NN.html    lesson body fragments, first line <!-- author: NAME -->
  reviews/chapter-NN.md      first lines "VERDICT: APPROVED" or "VERDICT: CHANGES NEEDED", then "Reviewer: NAME"

Output: team/site/toc.html and team/site/chapter-NN.html

Usage:
  python3 team/build.py           build the site and print progress
  python3 team/build.py status    print progress only
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_TOC = HERE / "source" / "toc_original.html"
BOOK = HERE / "book"
SITE = HERE / "site"
TEMPLATE = HERE / "template" / "lesson.html"


def clean(text):
    """Owner rule: no em or en dashes in anything the team writes."""
    return re.sub(r"[ \t]*[–—][ \t]*", ", ", text)


def chapters():
    return json.loads((BOOK / "chapters.json").read_text())


def descriptions():
    p = BOOK / "descriptions.json"
    if not p.exists():
        return {}
    try:
        return {str(k): clean(v).strip() for k, v in json.loads(p.read_text()).items() if str(v).strip()}
    except (ValueError, AttributeError):
        return {}


def lesson_path(n):
    return BOOK / "lessons" / f"chapter-{n:02d}.html"


def review_path(n):
    return BOOK / "reviews" / f"chapter-{n:02d}.md"


def author_of(n):
    p = lesson_path(n)
    if not p.exists():
        return None
    m = re.match(r"\s*<!--\s*author:\s*(.*?)\s*-->", p.read_text())
    return m.group(1).strip() if m else None


def review_of(n):
    """Returns (verdict, reviewer, is_current) or None."""
    p = review_path(n)
    if not p.exists():
        return None
    text = p.read_text()
    v = re.search(r"VERDICT:\s*(APPROVED|CHANGES NEEDED)", text, re.I)
    r = re.search(r"Reviewer:\s*(.+)", text)
    current = lesson_path(n).exists() and p.stat().st_mtime >= lesson_path(n).stat().st_mtime
    return (v.group(1).upper() if v else "UNCLEAR", r.group(1).strip() if r else None, current)


def progress():
    chs = chapters()
    descs = descriptions()
    missing = [c["n"] for c in chs if not c["desc"]]
    desc_done = [n for n in missing if str(n) in descs]
    drafted, approved, needs_changes, awaiting = [], [], [], []
    for c in chs:
        n = c["n"]
        if not lesson_path(n).exists():
            continue
        drafted.append(n)
        rv = review_of(n)
        if rv is None or not rv[2]:
            awaiting.append(n)
        elif rv[0] == "APPROVED" and rv[1] and rv[1] != author_of(n):
            approved.append(n)
        elif rv[0] == "APPROVED":
            awaiting.append(n)  # self approval does not count
        else:
            needs_changes.append(n)
    return {
        "descriptions_written": f"{len(desc_done)} of {len(missing)} missing",
        "lessons_drafted": len(drafted),
        "lessons_approved_by_the_other": len(approved),
        "lessons_needing_changes": needs_changes,
        "lessons_awaiting_review": awaiting,
        "approved": approved,
        "total_chapters": len(chs),
    }


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
    return html[:start] + "const BANNERS = " + out + ";" + html[end:]


def build():
    SITE.mkdir(exist_ok=True)
    descs = descriptions()
    (SITE / "toc.html").write_text(build_toc(descs))
    chs = chapters()
    tpl = TEMPLATE.read_text()
    existing = [c["n"] for c in chs if lesson_path(c["n"]).exists()]
    by_n = {c["n"]: c for c in chs}
    for n in existing:
        c = by_n[n]
        body = re.sub(r"^\s*<!--\s*author:.*?-->\s*", "", lesson_path(n).read_text(), count=1)
        crumb = " · ".join(x for x in (c["section"], c["part"]) if x)
        desc = c["desc"] or descs.get(str(n), "")
        i = existing.index(n)
        prev = f'<a class="prev" href="chapter-{existing[i-1]:02d}.html"><span class="label">Previous</span>{by_n[existing[i-1]]["title"]}</a>' if i > 0 else ""
        nxt = f'<a class="next" href="chapter-{existing[i+1]:02d}.html"><span class="label">Next</span>{by_n[existing[i+1]]["title"]}</a>' if i + 1 < len(existing) else ""
        page = (tpl.replace("{{TITLE}}", c["title"]).replace("{{CRUMB}}", crumb).replace("{{NUM}}", str(n))
                .replace("{{DESC}}", desc).replace("{{LEVEL}}", f'<span class="level">{c["cefr"]}</span>' if c["cefr"] else "")
                .replace("{{PREV}}", prev).replace("{{NEXT}}", nxt).replace("{{BODY}}", clean(body)))
        (SITE / f"chapter-{n:02d}.html").write_text(page)
    return len(existing)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(progress(), indent=2))
    else:
        pages = build()
        print(f"built toc.html and {pages} lesson pages into {SITE}")
        print(json.dumps(progress(), indent=2))
