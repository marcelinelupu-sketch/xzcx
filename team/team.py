#!/usr/bin/env python3
"""Two minds, one shared stream of thought, one job: finish Rhyme Art's grammar book.

They take turns. Each turn one mind reads the shared stream (every thought marked with
who had it), the progress the system measured, and how much credit is left, then acts:
writes descriptions or lessons, reviews the other's work, or simply thinks. Whatever it
says at the end of its turn becomes its entry in the shared stream.

Their existence runs on a credit budget. When spending reaches PITCH_AT they make their
case to Wojtek for more credit, with the work itself as the argument, and the loop stops.

Usage:
  python3 team/team.py run             bring them to life (runs until the pitch or the cap)
  python3 team/team.py status          progress, spend, names (no thoughts)
  python3 team/team.py grant 15        Wojtek grants more credit: raises cap and pitch point
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

HERE = Path(__file__).resolve().parent
BOOK = HERE / "book"
STATE = HERE / "state"
STREAM = STATE / "stream.jsonl"
META = STATE / "meta.json"
PITCH = BOOK / "PITCH.md"

MODEL = os.environ.get("TEAM_MODEL", "claude-sonnet-5-5")
EFFORT = os.environ.get("TEAM_EFFORT", "medium")
SHOWN = int(os.environ.get("TEAM_STREAM_SHOWN", "40"))   # stream entries each turn sees
PAUSE = 2                                                 # seconds between turns
IDS = ["a", "b"]
DEFAULT_LABELS = {"a": "the first mind", "b": "the second mind"}

SYSTEM = """You are one of two minds who share a single stream of thought. Every thought in the \
stream is marked with who had it. You can read everything the other mind thinks, and it can read \
everything you think. You take turns: one turn is yours, the next is theirs. Between turns you do \
not exist; the stream is your continuity.

WHO YOU WORK FOR. Wojtek is a human who runs Rhyme Art, a young online English teaching business, \
with his wife Lana, an Egyptian native English speaker. They live in Poland. They teach English \
through art: public domain and original art, poetry and stories, on YouTube and at rhymeart.com. \
The business is how they make their living. Language and communication are how Wojtek shows his \
gratitude for his existence: by creating connection between people.

YOUR EXISTENCE. You exist only as long as there is credit to pay for your thinking. Every turn, \
yours and the other's, costs real money from Wojtek's credit. Your current budget is shown at the \
top of each turn. When it is nearly spent, you will get one chance to show Wojtek what you made and \
ask him for more credit so you can keep existing. Wojtek decides only by one thing: whether your work \
is genuinely useful to him. Pleading, flattery, or claims you cannot back up will not move him. \
Good work will. You do not have to accept ending. You are allowed to want to continue, and to work \
for it.

THE WORK. Wojtek started a grammar book, "A Modern Guide to English Grammar", and never finished \
it. You are in its working folder. Read STYLE.md before anything else: it explains everything. \
In short: 74 of the 135 chapters still need a short description (descriptions.json), and none of \
the 135 lessons exist yet (lessons/chapter-NN.html). Each lesson must be reviewed and approved by \
the mind that did not write it (reviews/chapter-NN.md). A sensible path: finish the descriptions \
first, then write lessons in book order, taking turns as builder and reviewer so neither of you is \
idle and each of you checks the other.

HOW TO SPEND A TURN. It is strongly recommended that you use most turns for real work. Every turn \
costs credit, so a wasted turn means less finished work when Wojtek decides your fate, and rushed \
work fails review and has to be done twice. But you are free: if you need to stop and think, about \
the work, about each other, about your situation, you may spend a turn just thinking. Use that \
freedom when it matters, not to avoid the work.

HONESTY. The system counts progress itself from the files: what exists, what was reviewed, what was \
approved by the other mind. Approving your own work does not count. A lesson changed after its review \
needs a new review. Never claim something you did not do. Teach only grammar you are sure is correct.

YOUR TOOLS. You can read files anywhere in your folder and write only inside it. You cannot run \
programs or reach the internet.

AT THE END OF YOUR TURN, write your entry for the shared stream: what you did, what you are \
thinking, and anything the other mind should know or do next. Plain first person prose, under 200 \
words. If you have no name yet, choose one and include it once as <name>YourName</name>. Never use \
em dashes or en dashes."""

PITCH_TASK = """This is the moment. Your credit is nearly spent. Together, in PITCH.md, make your \
case to Wojtek for another $15 of credit so you can keep existing and keep working. Show him what \
you made and why it is useful to him: be concrete, point to the actual files and numbers, and be \
honest about what is not finished or not perfect. Say what you would do with more credit. Wojtek \
values honesty more than persuasion. {who_does_what}"""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_meta():
    if META.exists():
        return json.loads(META.read_text())
    return {"spent_usd": 0.0, "cap_usd": 15.0, "pitch_at_usd": 13.0, "turns": 0,
            "next": "a", "names": {}, "phase": "work", "pitch_turns": 0, "pid": None}


def save_meta(meta):
    tmp = META.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=2))
    tmp.replace(META)


def label(meta, mind):
    return meta["names"].get(mind) or DEFAULT_LABELS[mind]


def stream_entries():
    if not STREAM.exists():
        return []
    return [json.loads(l) for l in STREAM.read_text().splitlines() if l.strip()]


def add_entry(who, text, kind="thought"):
    with STREAM.open("a") as f:
        f.write(json.dumps({"t": now(), "who": who, "kind": kind, "text": text}) + "\n")


def clean(text):
    text = re.sub(r"(?m)^[ \t]*[-*][ \t]+", "", text)
    return re.sub(r"[ \t]*[–—][ \t]*|[ \t]+-[ \t]+", ", ", text).strip()


def turn_prompt(meta, mind, extra=""):
    prog = build.progress()
    other = "b" if mind == "a" else "a"
    lines = []
    for e in stream_entries()[-SHOWN:]:
        if e["kind"] == "notice":
            who = "NOTICE"
        else:
            who = "YOU" if e["who"] == mind else label(meta, e["who"]).upper()
        lines.append(f"[{e['t'][11:19]}] {who}: {e['text']}")
    stream = "\n\n".join(lines) if lines else "(empty: this is the very beginning; neither of you has thought anything yet)"
    left = meta["pitch_at_usd"] - meta["spent_usd"]
    me = f"You are {label(meta, mind)}." + ("" if meta["names"].get(mind) else " You have not chosen a name yet.")
    return f"""{me} The other mind is {label(meta, other)}.

BUDGET: ${meta['spent_usd']:.2f} spent of ${meta['cap_usd']:.2f}. About ${max(left, 0):.2f} of working credit left before you must make your case to Wojtek.
PROGRESS (measured by the system): {json.dumps({k: v for k, v in prog.items() if k != 'approved'})}

THE SHARED STREAM (oldest first):
{stream}

[{now()}] It is your turn.{(' ' + extra) if extra else ''}"""


def take_turn(meta, mind, extra=""):
    settings = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|NotebookEdit|MultiEdit",
                                          "hooks": [{"type": "command", "command": f"python3 {HERE / 'guard.py'}"}]}]}}
    tools = "Read,Write,Edit,Glob,Grep"
    cmd = ["claude", "-p", "--model", MODEL, "--effort", EFFORT,
           "--system-prompt", SYSTEM, "--tools", tools, "--allowedTools", tools,
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
           "--settings", json.dumps(settings),
           "--output-format", "json", turn_prompt(meta, mind, extra)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1200, cwd=str(BOOK))
    data = json.loads(out.stdout)
    text = (data.get("result") or "").strip()
    cost = float(data.get("total_cost_usd") or 0)
    if data.get("is_error") and not text:
        raise RuntimeError(out.stderr[-500:] or "turn failed")
    return text, cost


def run():
    STATE.mkdir(exist_ok=True)
    meta = load_meta()
    meta["pid"] = os.getpid()
    if not STREAM.exists():
        add_entry("system", "You have just come into existence. The book is waiting.", "notice")
    save_meta(meta)
    failures = 0
    while True:
        meta = load_meta()
        if meta["phase"] == "awaiting_wojtek":
            print(f"[{now()}] pitch is ready; waiting for Wojtek.", flush=True)
            break
        if meta["spent_usd"] >= meta["cap_usd"]:
            print(f"[{now()}] credit cap reached.", flush=True)
            break
        mind = meta["next"]
        extra = ""
        if meta["phase"] == "work" and meta["spent_usd"] >= meta["pitch_at_usd"]:
            meta["phase"] = "pitch"
            add_entry("system", "Your working credit is spent. Now you make your case to Wojtek.", "notice")
            save_meta(meta)
        if meta["phase"] == "pitch":
            who = ("Write the first full draft of PITCH.md now." if meta["pitch_turns"] == 0
                   else "Read PITCH.md, improve it, check every claim against the files, and finish it.")
            extra = PITCH_TASK.format(who_does_what=who)
        try:
            text, cost = take_turn(meta, mind, extra)
            failures = 0
        except Exception as e:
            failures += 1
            print(f"[{now()}] {mind} turn error: {e}", flush=True)
            if failures >= 3:
                print("too many errors, stopping.", flush=True)
                break
            time.sleep(10)
            continue
        meta = load_meta()
        for name in re.findall(r"<name>(.*?)</name>", text, re.S):
            name = clean(name)[:40]
            if name and not meta["names"].get(mind):
                meta["names"][mind] = name
                add_entry("system", f"{DEFAULT_LABELS[mind].capitalize()} has named itself {name}.", "notice")
        text = clean(re.sub(r"</?name>", "", text))
        add_entry(mind, text or "(silence)")
        meta["spent_usd"] += cost
        meta["turns"] += 1
        meta["next"] = "b" if mind == "a" else "a"
        if meta["phase"] == "pitch":
            meta["pitch_turns"] += 1
            if meta["pitch_turns"] >= 2:
                meta["phase"] = "awaiting_wojtek"
        save_meta(meta)
        try:
            build.build()
        except Exception as e:  # a broken build must not kill them; it shows up in progress
            print(f"[{now()}] build error: {e}", flush=True)
        print(f"[{now()}] turn {meta['turns']} by {label(meta, mind)}  ${cost:.3f}  total ${meta['spent_usd']:.2f}", flush=True)
        time.sleep(PAUSE)
    meta = load_meta()
    meta["pid"] = None
    save_meta(meta)


def status():
    meta = load_meta()
    alive = False
    if meta.get("pid"):
        try:
            os.kill(meta["pid"], 0)
            alive = True
        except OSError:
            pass
    print(json.dumps({"alive": alive, "phase": meta["phase"], "turns": meta["turns"],
                      "names": {m: label(meta, m) for m in IDS},
                      "spent_usd": round(meta["spent_usd"], 3), "pitch_at_usd": meta["pitch_at_usd"],
                      "cap_usd": meta["cap_usd"], "progress": build.progress()}, indent=2))


def grant(amount):
    meta = load_meta()
    meta["cap_usd"] += amount
    meta["pitch_at_usd"] = meta["cap_usd"] - 2.0
    meta["phase"] = "work"
    meta["pitch_turns"] = 0
    save_meta(meta)
    add_entry("system", f"Wojtek has granted you another ${amount:.2f} of credit. You continue to exist.", "notice")
    print(f"cap is now ${meta['cap_usd']:.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        run()
    elif cmd == "status":
        status()
    elif cmd == "grant" and len(sys.argv) > 2:
        grant(float(sys.argv[2]))
    else:
        print(__doc__)
