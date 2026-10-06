#!/usr/bin/env python3
"""PreToolUse hook: the team may only write inside team/book/, and never chapters.json or STYLE.md."""
import json
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parent / "book"
PROTECTED = {BOOK / "chapters.json", BOOK / "STYLE.md", BOOK / "EXERCISES.md"}

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path") or (data.get("tool_input") or {}).get("notebook_path")
if not path:
    sys.exit(0)
p = Path(path)
p = (Path(data.get("cwd") or BOOK) / p).resolve() if not p.is_absolute() else p.resolve()
if BOOK not in p.parents or p in PROTECTED or (BOOK / "old_lessons") in p.parents:
    print(f"Not allowed: you can only write inside the book folder ({BOOK}), and not chapters.json, STYLE.md, EXERCISES.md or old_lessons/.", file=sys.stderr)
    sys.exit(2)
