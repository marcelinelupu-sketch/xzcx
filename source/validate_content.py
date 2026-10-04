#!/usr/bin/env python3
"""Validate Frog's Dream content JSON files.

Usage:
  python3 source/validate_content.py FILE [FILE...]       check specific files
  python3 source/validate_content.py --all                check every content file
  options: --content DIR (default source/content), --no-similarity, --quiet

Checks: JSON syntax, required fields per page type, title 50-60 chars,
meta description 140-160 chars, prose word counts, item counts and item sanity,
FAQ count, related slugs, hub slugs, internal links, banned dash characters,
and (for themed pages) 5-word shingle similarity < 0.25 and no shared sentence
longer than 12 words against every other themed page.
Exit code 1 if any error.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdlib  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--content", default=str(fdlib.CONTENT))
    ap.add_argument("--no-similarity", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="hide warnings")
    a = ap.parse_args(argv)
    content = Path(a.content)
    cat = fdlib.Catalog(content)
    files = [Path(f) for f in a.files]
    if a.all:
        files = sorted(content.rglob("*.json"))
    if not files:
        ap.print_help()
        return 2
    n_err = n_warn = 0
    for f in files:
        if not f.exists():
            print(f"ERROR {f}: file not found")
            n_err += 1
            continue
        rep = fdlib.validate_file(f, cat, content)
        status = "FAIL" if rep.errors else "ok  "
        if rep.errors or (rep.warnings and not a.quiet):
            print(f"{status} {f}")
        else:
            print(f"{status} {f}")
        for e in rep.errors:
            print(f"   ERROR: {e}")
        if not a.quiet:
            for w in rep.warnings:
                print(f"   warn:  {w}")
        n_err += len(rep.errors)
        n_warn += len(rep.warnings)

    if not a.no_similarity:
        themed = {str(f.resolve()) for f in files if fdlib.classify(f, content)[0] == "theme"}
        if themed:
            sims, dupes = fdlib.similarity_report(content, None)

            def mine(x, y):
                return a.all or str(Path(x).resolve()) in themed or str(Path(y).resolve()) in themed

            sims = [s for s in sims if mine(s[0], s[1])]
            dupes = [d for d in dupes if mine(d[0], d[1])]
            for x, y, j in sims:
                print(f"ERROR similarity {j:.2f} >= 0.25 between {x} and {y}")
                n_err += 1
            for x, y, s in dupes:
                print(f"ERROR shared sentence (>12 words) in {x} and {y}: \"{s[:110]}...\"")
                n_err += 1
    print(f"\n{len(files)} file(s), {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
