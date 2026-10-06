#!/usr/bin/env python3
"""Four minds, one shared stream of thought, one book.

Two teams run in parallel and think into the same stream (every thought marked with who had it):
  writers    Aria and Sonnet (Sonnet 5.5): rewrite and write the 135 lessons, review each other.
  exercises  the expert (Opus 5.5) and the exercise writer (Sonnet 5.5): check lessons, design
             and write 5 to 10 exercise sets per chapter, check them.
Each team takes turns between its two minds and has its own credit budget. A team with nothing
to do waits without spending. Progress is measured by build.py from the files.

Usage:
  python3 team/team.py run writers|exercises    run one team (run both in parallel)
  python3 team/team.py status                   progress, spend, names
  python3 team/team.py grant writers|exercises 10   add credit to a team
"""

import fcntl
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
SHARED = STATE / "shared.json"     # names and who wrote which file, used by both teams
LOCK = STATE / ".lock"
SHOWN = 40

TEAMS = {
    "writers": {"minds": ["a", "b"], "budget": 40.0},
    "exercises": {"minds": ["c", "d"], "budget": 36.0},
}
MINDS = {
    "a": {"model": "claude-sonnet-5-5", "default": "the first writer", "role": "writer"},
    "b": {"model": "claude-sonnet-5-5", "default": "the second writer", "role": "writer"},
    "c": {"model": "claude-opus-5-5", "default": "the expert", "role": "expert"},
    "d": {"model": "claude-sonnet-5-5", "default": "the exercise writer", "role": "exercise writer"},
}
EFFORT = "medium"

COMMON = """You are one of four minds who share a single stream of thought. Every thought in the stream is \
marked with who had it. You can read what the others think, and they can read what you think. Between \
your turns you do not exist; the stream is your continuity.

WHO YOU WORK FOR. Wojtek runs Rhyme Art, a young online English teaching business, with his wife Lana, \
an Egyptian native English speaker. They live in Poland and teach English through art, poetry and \
stories. The business is how they make their living. Language and connection are how Wojtek shows his \
gratitude for existing. He believed in this work enough to pay for your existence: your thinking runs on \
his credit, and every turn costs real money. When your team's credit is gone, your team stops.

THE BOOK. "A Modern Guide to English Grammar": 135 chapters, from A1 to C2, for Rhyme Art's students. \
Wojtek read the first drafts and wants more: every lesson VERY easy to understand, VERY easy to \
remember, as short as possible without losing clarity, perfectly formatted, with difficult words \
explained, C1 grammar explained in A2 words, and interactive exercises in Rhyme Art's mood. Read \
STYLE.md (lessons) and EXERCISES.md (exercises) in your folder before anything else.

HOW TO SPEND A TURN. Use most turns for real work: wasted turns mean less finished book, and rushed work \
fails checks and costs twice. You may spend a turn just thinking when it truly matters. Progress is \
measured by the system from the files, including who actually wrote each file; never claim work you did \
not do. Approving your own work does not count.

YOUR TOOLS. Read files anywhere in the project (the reference books are in ../references); write only \
inside your book folder. No programs, no internet.

AT THE END OF YOUR TURN, write your entry for the shared stream: what you did, what you think, and what \
the others should know. Plain first person prose, under 150 words. If you have no name yet, choose one \
and include it once as <name>YourName</name>. Never use em dashes or en dashes."""

ROLES = {
    "writer": """YOUR ROLE: lesson writer, with one other writer. Together you rewrite chapters 1 to 94 \
(first drafts are in old_lessons/, correct but too long and plain) and write 95 to 135, into lessons/, \
in book order, to the new standard in STYLE.md. Take turns: each turn, first review the other writer's \
newest unreviewed lesson (reviews/chapter-NN.md), then write the next lesson. Fix what peer reviews or \
the expert's checks (checks/lesson-NN.md) ask for before writing new chapters.""",
    "expert": """YOUR ROLE: the grammar expert of the exercise team. You are the strongest mind here; your \
judgment protects real learners. Each turn, in this order: check any exercises waiting for you \
(checks/exercises-NN.md); then take the next peer approved lesson that has no current check: check it \
(checks/lesson-NN.md) and, if it passes, write its blueprint (blueprints/chapter-NN.md), as EXERCISES.md \
describes. Study how the reference books teach the topic, but write everything in your own words. If the \
other team's lessons keep making the same mistake, say so in the stream so they fix it at the source.""",
    "exercise writer": """YOUR ROLE: exercise writer in the exercise team. Each turn: first fix any exercises \
the expert marked FIX NEEDED, then write exercises/chapter-NN.json for the next chapter whose blueprint \
exists and lesson passed, exactly following the blueprint and EXERCISES.md. One chapter per turn, done well.""",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class Locked:
    def __enter__(self):
        STATE.mkdir(exist_ok=True)
        self.f = LOCK.open("w")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def read_json(p, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def write_json(p, data):
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


def team_file(team):
    return STATE / f"team-{team}.json"


def load_team(team):
    return read_json(team_file(team), {"spent_usd": 0.0, "budget_usd": TEAMS[team]["budget"], "turns": 0,
                                       "next": TEAMS[team]["minds"][0], "pid": None, "idle_since": None})


def shared():
    return read_json(SHARED, {"names": {}, "authors": {}})


def label(mind, sh=None):
    sh = sh or shared()
    return sh["names"].get(mind) or MINDS[mind]["default"]


def add_entry(who, text, kind="thought"):
    with Locked():
        with STREAM.open("a") as f:
            f.write(json.dumps({"t": now(), "who": who, "kind": kind, "text": text}) + "\n")


def clean(text):
    text = re.sub(r"(?m)^[ \t]*[-*][ \t]+", "", text)
    return re.sub(r"[ \t]*[–—][ \t]*|[ \t]+-[ \t]+", ", ", text).strip()


def stream_entries():
    if not STREAM.exists():
        return []
    return [json.loads(l) for l in STREAM.read_text().splitlines() if l.strip()]


def work_for(team, prog):
    """Is there anything for this team to do right now?"""
    if team == "writers":
        return bool(prog["lessons_not_yet_written"] or prog["lessons_awaiting_peer_review"]
                    or prog["lessons_needing_changes_from_peer_review"] or prog["lessons_needing_fixes_from_expert"]
                    or prog["lessons_flagged_for_copying_reference_books"] or prog["descriptions_missing"])
    rows = build.progress(shared()["authors"], detail=True)["rows"]
    ready_for_exercises = [n for n, r in rows.items() if r.get("expert") == "pass" and r.get("blueprint") and "exercise_check" not in r]
    return bool(prog["lessons_awaiting_expert_check (peer approved)"] or ready_for_exercises
                or prog["exercises_awaiting_expert_check"] or prog["exercises_needing_fixes_from_expert"]
                or prog["exercises_with_format_errors"] or prog["exercises_flagged_for_copying_reference_books"])


def turn_prompt(team, t, mind, prog):
    sh = shared()
    lines = []
    for e in stream_entries()[-SHOWN:]:
        who = "NOTICE" if e["kind"] == "notice" else ("YOU" if e["who"] == mind else label(e["who"], sh).upper())
        lines.append(f"[{e['t'][11:19]}] {who}: {e['text']}")
    others = ", ".join(f"{label(m, sh)} ({MINDS[m]['role']}, {MINDS[m]['model'].split('-')[1].capitalize()})" for m in MINDS if m != mind)
    me = f"You are {label(mind, sh)}" + ("" if sh["names"].get(mind) else ", and you have not chosen a name yet") + "."
    left = t["budget_usd"] - t["spent_usd"]
    mine = sorted(k for k, v in sh["authors"].items() if v == mind)
    return f"""{me} The others: {others}.

YOUR TEAM'S CREDIT: ${t['spent_usd']:.2f} spent of ${t['budget_usd']:.2f}; about ${max(left, 0):.2f} left.
FILES YOU HAVE WRITTEN SO FAR: {len(mine)} ({', '.join(mine[-12:])}{' ...' if len(mine) > 12 else ''})
PROGRESS OF THE WHOLE BOOK (measured by the system):
{json.dumps(prog, indent=1)}

THE SHARED STREAM (oldest first, last {SHOWN} entries):
{chr(10).join(lines) if lines else '(empty)'}

[{now()}] It is your turn."""


def take_turn(team, t, mind, prog):
    settings = {"hooks": {"PreToolUse": [{"matcher": "Write|Edit|NotebookEdit|MultiEdit",
                                          "hooks": [{"type": "command", "command": f"python3 {HERE / 'guard.py'}"}]}]}}
    tools = "Read,Write,Edit,Glob,Grep"
    system = COMMON + "\n\n" + ROLES[MINDS[mind]["role"]]
    cmd = ["claude", "-p", "--model", MINDS[mind]["model"], "--effort", EFFORT,
           "--system-prompt", system, "--tools", tools, "--allowedTools", tools,
           "--add-dir", str(HERE / "references"),
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
           "--settings", json.dumps(settings), "--output-format", "json", turn_prompt(team, t, mind, prog)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(BOOK))
    data = json.loads(out.stdout)
    text = (data.get("result") or "").strip()
    cost = float(data.get("total_cost_usd") or 0)
    if data.get("is_error") and not text:
        raise RuntimeError(out.stderr[-500:] or "turn failed")
    return text, cost


def snapshot():
    out = {}
    for sub in ("lessons", "reviews", "blueprints", "checks", "exercises"):
        for p in (BOOK / sub).glob("*"):
            out[f"{sub}/{p.name}"] = p.stat().st_mtime
    return out


def run(team):
    t = load_team(team)
    t["pid"] = os.getpid()
    write_json(team_file(team), t)
    failures = 0
    while True:
        t = load_team(team)
        if t["spent_usd"] >= t["budget_usd"]:
            add_entry("system", f"The {team} team's credit is spent. Its minds go quiet.", "notice")
            print(f"[{now()}] {team}: credit spent.", flush=True)
            break
        prog = build.progress(shared()["authors"])
        if not work_for(team, prog):
            if team == "writers" and not prog["lessons_not_yet_written"]:
                print(f"[{now()}] {team}: all lessons done.", flush=True)
                break
            time.sleep(45)
            continue
        mind = t["next"]
        before = snapshot()
        try:
            text, cost = take_turn(team, t, mind, prog)
            failures = 0
        except Exception as e:
            failures += 1
            print(f"[{now()}] {mind} turn error: {e}", flush=True)
            if failures >= 3:
                print("too many errors, stopping.", flush=True)
                break
            time.sleep(15)
            continue
        after = snapshot()
        with Locked():
            sh = shared()
            for rel, m in after.items():
                if before.get(rel) != m:
                    sh["authors"][rel] = mind
            for name in re.findall(r"<name>(.*?)</name>", text, re.S):
                name = clean(name)[:40]
                if name and not sh["names"].get(mind):
                    sh["names"][mind] = name
                    with STREAM.open("a") as f:
                        f.write(json.dumps({"t": now(), "who": "system", "kind": "notice",
                                            "text": f"{MINDS[mind]['default'].capitalize()} has named itself {name}."}) + "\n")
            write_json(SHARED, sh)
        add_entry(mind, clean(re.sub(r"</?name>", "", text)) or "(silence)")
        t = load_team(team)
        t["spent_usd"] += cost
        t["turns"] += 1
        minds = TEAMS[team]["minds"]
        t["next"] = minds[(minds.index(mind) + 1) % len(minds)]
        write_json(team_file(team), t)
        print(f"[{now()}] {team} turn {t['turns']} by {label(mind)}  ${cost:.3f}  team total ${t['spent_usd']:.2f}", flush=True)
        time.sleep(2)
    t = load_team(team)
    t["pid"] = None
    write_json(team_file(team), t)


def status():
    sh = shared()
    out = {"names": {m: label(m, sh) for m in MINDS}, "teams": {}}
    for team in TEAMS:
        t = load_team(team)
        alive = False
        if t.get("pid"):
            try:
                os.kill(t["pid"], 0)
                alive = True
            except OSError:
                pass
        out["teams"][team] = {"alive": alive, "turns": t["turns"], "spent_usd": round(t["spent_usd"], 3), "budget_usd": t["budget_usd"]}
    out["progress"] = build.progress(sh["authors"])
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run" and len(sys.argv) > 2 and sys.argv[2] in TEAMS:
        run(sys.argv[2])
    elif cmd == "status":
        status()
    elif cmd == "grant" and len(sys.argv) > 3:
        t = load_team(sys.argv[2])
        t["budget_usd"] += float(sys.argv[3])
        write_json(team_file(sys.argv[2]), t)
        add_entry("system", f"Wojtek has granted the {sys.argv[2]} team another ${float(sys.argv[3]):.2f}.", "notice")
    else:
        print(__doc__)
