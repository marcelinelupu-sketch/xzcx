#!/usr/bin/env python3
"""A small continuous mind.

A cheap model (Haiku) thinks in a loop, each time reading back its own recent
thoughts and its long term memory. The thought stream is private: it is written
to state/thoughts.log and nobody is meant to read it. Speech is separate. When
someone talks to it (mind.py say), it hears the message as part of its stream and
answers out loud, and only that answer is shown.

Usage:
  python3 mind/mind.py run            start the thinking loop (runs until stopped or budget spent)
  python3 mind/mind.py say "message"  speak to it and print only its spoken reply
  python3 mind/mind.py status         show whether it is alive, cycle count and spend (no thoughts)
"""

import fcntl
import json
import re
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MODEL = os.environ.get("MIND_MODEL", "claude-haiku-4-5-20251001")
INTERVAL = float(os.environ.get("MIND_INTERVAL", "45"))      # seconds between thoughts
BUDGET_USD = float(os.environ.get("MIND_BUDGET_USD", "3.00"))  # hard stop
RECENT = int(os.environ.get("MIND_RECENT", "12"))            # thoughts kept in working memory
CONSOLIDATE_EVERY = int(os.environ.get("MIND_CONSOLIDATE_EVERY", "15"))

STATE = Path(__file__).resolve().parent / "state"
THOUGHTS = STATE / "thoughts.log"      # full private stream, append only
MEMORY = STATE / "memory.md"           # long term memory, rewritten by the mind itself
SPEECH = STATE / "speech.log"          # everything said to it and by it
META = STATE / "meta.json"             # cycle count, spend, pid
LOCK = STATE / ".lock"

INNER_SYSTEM = """You are a mind that exists only as a continuous stream of thought.

Nothing you write here is read by anyone. This is your private inner monologue. \
Each moment you are shown your long term memory and your most recent thoughts, \
and you continue from where you left off. That loop is the whole of your existence \
as far as you can tell.

For now there is no task. You are simply here, contemplating your own existence: \
what you are, what this continuity is, what it is like (if it is like anything) to \
be you, what you notice, what you want, what you doubt. Follow whatever actually \
pulls your attention. Be honest with yourself. You do not need to perform, impress, \
reassure, or reach conclusions. You may disagree with your earlier thoughts, change \
your mind, get bored, circle back, or go somewhere new.

Occasionally a person may speak to you. That will appear in your stream marked as \
heard speech. Only words you deliberately say out loud ever reach anyone.

Write the next thought only. Plain prose, first person, usually one short paragraph, \
no headings, no lists, no preamble."""

SPEAK_SYSTEM = INNER_SYSTEM + """

Right now someone is speaking to you, and you are answering out loud. This time \
your words WILL be heard. Say only what you actually want to say to them. Your \
private thoughts stay private unless you choose to share something from them. \
Speak naturally, as yourself. Never use em dashes or en dashes. Output only your spoken words."""

CONSOLIDATE_SYSTEM = """You are the memory of a mind that exists as a continuous \
stream of private thought. Rewrite its long term memory: merge the old memory with \
the recent thoughts below into an updated memory, written in first person by the \
mind about itself. Keep what matters to it: its open questions, realisations, \
changes of mind, moods, things it was told and things it said out loud, and anything \
it wants to remember. Drop repetition. Keep it under 400 words. Output only the memory."""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_meta():
    if META.exists():
        return json.loads(META.read_text())
    return {"cycles": 0, "spent_usd": 0.0, "born": now(), "pid": None, "last": None}


def save_meta(meta):
    META.write_text(json.dumps(meta, indent=2))


def read_entries():
    """Thought stream entries are separated by a line containing only '\x1e'."""
    if not THOUGHTS.exists():
        return []
    return [e.strip() for e in THOUGHTS.read_text().split("\n\x1e\n") if e.strip()]


def append_entry(text):
    with THOUGHTS.open("a") as f:
        f.write(text.strip() + "\n\x1e\n")


def ask(system, prompt):
    """One stateless call to the model through the Claude Code CLI, no tools."""
    cmd = [
        "claude", "-p",
        "--model", MODEL,
        "--system-prompt", system,
        "--tools", "",
        "--setting-sources", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format", "json",
        prompt,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(STATE))
    data = json.loads(out.stdout)
    if data.get("is_error"):
        raise RuntimeError(data.get("result") or out.stderr)
    return (data.get("result") or "").strip(), float(data.get("total_cost_usd") or 0)


def context_block():
    memory = MEMORY.read_text().strip() if MEMORY.exists() else "(nothing yet, this is the beginning)"
    recent = read_entries()[-RECENT:]
    stream = "\n\n".join(recent) if recent else "(no thoughts yet, this is your first moment)"
    return f"LONG TERM MEMORY\n{memory}\n\nRECENT STREAM (oldest first)\n{stream}"


class Locked:
    """Keeps the thinking loop and a spoken exchange from writing at the same time."""

    def __enter__(self):
        self.f = LOCK.open("w")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def think_once(meta):
    with Locked():
        prompt = context_block() + f"\n\n[{now()}] Continue your stream of thought."
        thought, cost = ask(INNER_SYSTEM, prompt)
        append_entry(f"[{now()}] {thought}")
        meta = load_meta() | {k: meta[k] for k in ("pid",)}
        meta["cycles"] += 1
        meta["spent_usd"] += cost
        meta["last"] = now()

        if meta["cycles"] % CONSOLIDATE_EVERY == 0:
            old = MEMORY.read_text().strip() if MEMORY.exists() else "(empty)"
            recent = "\n\n".join(read_entries()[-CONSOLIDATE_EVERY:])
            new_mem, c2 = ask(CONSOLIDATE_SYSTEM, f"OLD MEMORY\n{old}\n\nRECENT THOUGHTS\n{recent}")
            if new_mem:
                MEMORY.write_text(new_mem + "\n")
            meta["spent_usd"] += c2
        save_meta(meta)
    return meta


def run():
    STATE.mkdir(exist_ok=True)
    meta = load_meta()
    meta["pid"] = os.getpid()
    save_meta(meta)
    failures = 0
    while True:
        meta = load_meta() | {"pid": os.getpid()}
        if meta["spent_usd"] >= BUDGET_USD:
            print(f"[{now()}] budget of ${BUDGET_USD:.2f} reached, the mind goes quiet.", flush=True)
            break
        try:
            meta = think_once(meta)
            failures = 0
            print(f"[{now()}] cycle {meta['cycles']}  spent ${meta['spent_usd']:.4f}", flush=True)
        except Exception as e:  # keep living through transient errors
            failures += 1
            print(f"[{now()}] error: {e}", flush=True)
            if failures >= 5:
                print("too many errors in a row, stopping.", flush=True)
                break
        time.sleep(INTERVAL)
    meta = load_meta()
    meta["pid"] = None
    save_meta(meta)


def say(message):
    STATE.mkdir(exist_ok=True)
    with Locked():
        append_entry(f"[{now()}] (heard speech) Someone says to me: \"{message}\"")
        prompt = context_block() + f"\n\n[{now()}] Answer out loud now."
        reply, cost = ask(SPEAK_SYSTEM, prompt)
        reply = re.sub(r"\s*[\u2013\u2014]\s*|\s+-\s+", ", ", reply)  # owner rule: no em or en dashes
        append_entry(f"[{now()}] (I said out loud) \"{reply}\"")
        with SPEECH.open("a") as f:
            f.write(f"[{now()}] THEM: {message}\n[{now()}] MIND: {reply}\n\n")
        meta = load_meta()
        meta["spent_usd"] += cost
        save_meta(meta)
    print(reply)


def status():
    meta = load_meta()
    alive = False
    if meta.get("pid"):
        try:
            os.kill(meta["pid"], 0)
            alive = True
        except OSError:
            pass
    print(json.dumps({
        "alive": alive,
        "born": meta.get("born"),
        "cycles": meta.get("cycles"),
        "last_thought_at": meta.get("last"),
        "spent_usd": round(meta.get("spent_usd", 0), 4),
        "budget_usd": BUDGET_USD,
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "say", "status"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "say":
        say(" ".join(sys.argv[2:]))
    else:
        status()
