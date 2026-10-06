#!/usr/bin/env python3
"""Translate every marked vocabulary word into the TOC's 30 languages, in context.

Reads team/vocab/index.json (written by build.py: word, definition, sentence), writes
team/vocab/translations.json ({id: {lang: translation}}). Only missing entries are sent.
Then run build.py again so the pages carry the translations.

Usage: python3 team/translate.py [--batch 40]
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOCAB = HERE / "vocab"
LANGS = {"sq": "Albanian", "ar": "Arabic", "bs": "Bosnian", "bg": "Bulgarian", "hr": "Croatian", "cs": "Czech",
         "da": "Danish", "nl": "Dutch", "et": "Estonian", "fi": "Finnish", "fr": "French", "de": "German",
         "el": "Greek", "hu": "Hungarian", "it": "Italian", "lv": "Latvian", "lt": "Lithuanian", "mk": "Macedonian",
         "no": "Norwegian", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sr": "Serbian (Cyrillic)",
         "sk": "Slovak", "sl": "Slovenian", "es": "Spanish", "sv": "Swedish", "tr": "Turkish", "uk": "Ukrainian"}
SYSTEM = """You are a professional translator for an English learning book. For each English word or \
phrase, give the translation that matches its meaning in the given sentence and definition, in each \
requested language. Translate the meaning in this context only: one short natural translation per \
language (a word or a few words, the dictionary form a learner would look up; if the English is a \
specific form like a plural or past tense, a matching form is welcome). Never explain. Output only JSON: \
{"<id>": {"<lang code>": "translation", ...}, ...} with every id and every language code."""


def main():
    batch = int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 40
    index = json.loads((VOCAB / "index.json").read_text())
    out_p = VOCAB / "translations.json"
    done = json.loads(out_p.read_text()) if out_p.exists() else {}
    todo = [k for k in index if len(done.get(k, {})) < len(LANGS)]
    print(f"{len(todo)} words to translate", flush=True)
    total = 0.0
    for i in range(0, len(todo), batch):
        chunk = {k: {"word": index[k]["word"], "definition": index[k]["def"], "sentence": index[k]["context"]} for k in todo[i:i + batch]}
        prompt = ("Languages: " + json.dumps(LANGS) + "\n\nWords:\n" + json.dumps(chunk, ensure_ascii=False, indent=1))
        cmd = ["claude", "-p", "--model", "claude-sonnet-5-5", "--effort", "low", "--system-prompt", SYSTEM,
               "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
               "--output-format", "json", prompt]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        data = json.loads(r.stdout)
        total += float(data.get("total_cost_usd") or 0)
        text = data.get("result") or ""
        m = re.search(r"\{.*\}", text, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except ValueError:
            got = {}
        for k, v in got.items():
            if k in chunk and isinstance(v, dict):
                done.setdefault(k, {}).update({l: str(t).strip() for l, t in v.items() if l in LANGS and str(t).strip()})
        out_p.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        print(f"batch {i // batch + 1}: {len(got)} words, total ${total:.2f}", flush=True)
    print(f"done, ${total:.2f}")


if __name__ == "__main__":
    main()
