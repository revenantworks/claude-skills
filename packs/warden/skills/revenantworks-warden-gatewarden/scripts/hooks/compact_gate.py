#!/usr/bin/env python3
"""compact_gate.py: PreToolUse hook (matcher "Write|Edit|MultiEdit|NotebookEdit") that refuses a
subagent's write to an existing file when its context was compacted after it last read that file.

Observation 0730 (the autoCompactWindow replay proof, 2026-11-21): an opus-high unit compacted twice
and each time wrote its findings file straight after (a full Write, then an Edit) without reading it
again, though its brief and its launch prompt both said to re-read after any context reset. The
compaction summary named the file, and the unit took the summary as the re-read. A Write over a file
from a summary can drop what the summary did not carry, so the re-read is a gate, not a sentence.

The rule, per call:
- the main session (no `agent_id`) is never gated;
- the hook reads the subagent's own transcript (`agent_transcript_path`; when missing,
  `<session transcript>/subagents/agent-<id>.jsonl`) and finds the last `compact_boundary`;
- no boundary, or a file that does not exist yet: the call runs;
- after the boundary, a `Read` of the same file (a partial read counts; a failed read does not; a
  read in the same batch whose result is not written yet counts), or a `Write` of it that succeeded,
  lets the call run;
- anything else is refused under rule `compact_gate` with "read it again first".

Mode: soft (`compact_gate`), so it follows the modes file like any soft rule: watch logs only, nudge
tells the unit once, guard refuses (exit 2). Paths compare with `/` separators, case folded, resolved
from the event's `cwd`. The log line carries no path (hooklib.log_event writes the reason's first
clause and a fingerprint of the command only).

Fail mode: open. An unreadable event or transcript allows the call; a broken gate must not freeze
every unit's writes.
"""
from __future__ import annotations

import json
import os
import posixpath
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

RULE = "compact_gate"
GATED = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
BOUNDARY = "compact_boundary"
REASON = ("compact_gate: your context was compacted after you last read this file. Read it again "
          "before you write it (and re-read your brief): the compaction summary is not a re-read, and a "
          "write from it can drop what the summary left out.")


def target(ev: dict) -> str:
    ti = ev.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    p = ti.get("file_path") or ti.get("notebook_path") or ""
    return p if isinstance(p, str) else ""


def norm(path: str, cwd: str = "") -> str:
    """One spelling per file: `/` separators, resolved from cwd, `.` and `..` folded, case folded."""
    p = path.strip().replace("\\", "/")
    base = (cwd or "").replace("\\", "/")
    absolute = p.startswith("/") or (len(p) > 1 and p[1] == ":")
    if not absolute and base:
        p = base.rstrip("/") + "/" + p
    return posixpath.normpath(p).casefold()


def transcript_of(ev: dict) -> str | None:
    agent = str(ev.get("agent_id") or "")
    p = ev.get("agent_transcript_path")
    if isinstance(p, str) and os.path.isfile(p):
        return p
    t = ev.get("transcript_path")
    if agent and isinstance(t, str) and t.endswith(".jsonl"):
        guess = os.path.join(t[:-6], "subagents", f"agent-{agent}.jsonl")
        if os.path.isfile(guess):
            return guess
    return None


def is_boundary(d: dict) -> bool:
    return d.get("subtype") == BOUNDARY or d.get("type") == BOUNDARY


def after_last_boundary(path: str) -> list[dict] | None:
    """The transcript records after its last compact_boundary; None when it has none."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    last = None
    for i in range(len(lines) - 1, -1, -1):
        if BOUNDARY not in lines[i]:
            continue
        try:
            d = json.loads(lines[i])
        except ValueError:
            continue
        if isinstance(d, dict) and is_boundary(d):
            last = i
            break
    if last is None:
        return None
    out = []
    for raw in lines[last + 1:]:
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def known_since(records: list[dict], want: str, cwd: str, current_id: str) -> bool:
    """True when, after the boundary, the unit read `want` or wrote it whole with success."""
    calls: list[tuple[str, str, str]] = []  # (id, tool, normalised path)
    results: dict[str, bool] = {}  # tool_use_id -> is_error
    for d in records:
        msg = d.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                inp = item.get("input") if isinstance(item.get("input"), dict) else {}
                fp = inp.get("file_path") or inp.get("notebook_path") or ""
                if isinstance(fp, str) and fp:
                    calls.append((str(item.get("id") or ""), str(item.get("name") or ""), norm(fp, cwd)))
            elif item.get("type") == "tool_result":
                results[str(item.get("tool_use_id") or "")] = bool(item.get("is_error"))
    for cid, name, fp in calls:
        if current_id and cid == current_id:
            break  # only calls made before the one being gated
        if fp != want:
            continue
        if name == "Read" and results.get(cid) is not True:  # done or still pending, not failed
            return True
        if name == "Write" and results.get(cid) is False:  # written whole, and it took
            return True
    return False


def check(ev: dict) -> str | None:
    """The refusal reason, or None to let the call run. Raises nothing."""
    try:
        if not ev or not ev.get("agent_id") or ev.get("tool_name") not in GATED:
            return None
        raw = target(ev)
        if not raw:
            return None
        cwd = str(ev.get("cwd") or "")
        on_disk = raw if os.path.isabs(raw) or not cwd else os.path.join(cwd, raw)
        if not os.path.exists(on_disk):
            return None  # a new file: nothing a summary could have dropped
        path = transcript_of(ev)
        if not path:
            return None
        records = after_last_boundary(path)
        if records is None:
            return None
        if known_since(records, norm(raw, cwd), cwd, str(ev.get("tool_use_id") or "")):
            return None
        return REASON
    except Exception:
        return None


def main() -> None:
    ev, _ = hl.read_event()
    reason = check(ev) if ev else None
    if reason:
        hl.block(reason, rule=RULE)
    hl.allow()


if __name__ == "__main__":
    main()
