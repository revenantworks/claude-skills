#!/usr/bin/env python3
"""call_cap.py: PreToolUse hook (matcher "*") that counts each subagent's tool calls
and stops it at its call cap; on SubagentStop it logs how the subagent ended.

Claude Code fires PreToolUse inside subagents too, and the event then carries
`agent_id` and `agent_type`. The main session (no `agent_id`) is never counted.

Caps come from `<state>/call-caps.json` (state = GATEWARDEN_STATE or
~/.claude/gatewarden):
  {"default": null,                 # cap for any subagent not named below
   "by_agent_type": {"opus-medium": 120},
   "by_agent_id": {"<id>": 80},      # a controller may add one after launch
   "grace": 10,                      # calls allowed past the cap to commit and report
   "warn_at": 0.85,                  # fraction of the cap where the warning starts
   "always_allow": ["SubagentHandback"]}
No cap for an agent means it is counted and never stopped.

Calls 1..cap pass (a warning rides along from warn_at x cap). Calls past the cap
pass for `grace` more with "past cap: commit and report now". After that every
call is blocked except the always_allow tools, so the unit can still hand back.

Event log (local only): one JSON line per first warn, cap reached, block (the first
MAX_BLOCK_LINES per agent) and subagent end goes to <state>/call-cap-events.jsonl.
A line holds ids, counts and signatures: a signature is the tool name plus a salted
hash of the call's input, never the input. The end line adds totals read from the
subagent's own transcript (errors, the longest error run, other gatewarden hooks'
blocks, writes, duration, the brief's unit id, a hash of the first prompt) - never
prompt text, never a path. The log is skipped when the state folder sits inside a
git work tree, so it never lands in a repo.

Fail mode: open. An unreadable event, caps file or transcript allows the call (a broken
counter must not freeze every subagent). Counts live in <state>/count-<session>-<agent>.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

DEFAULT_ALWAYS = ["SubagentHandback"]
EVENTS = "call-cap-events.jsonl"
RING = 30
MAX_BLOCK_LINES = 3
MAX_KEYS = 300
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
OTHER_HOOKS = ("push_gate", "ci_stamp", "hyperv_lock", "heredoc_guard", "golive_block", "launch_throttle")
UNIT_LINE = re.compile(r"(?im)^\s*[*_`]*(?:unit|unit_id|brief|row)[*_`]*\s*[:=]\s*[`'\"]?([^\s`'\"]+)")
UNIT_SAY = re.compile(r"(?i)\byou are unit\s+[`'\"]?([A-Za-z0-9][A-Za-z0-9_.-]{0,39})")


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s)[:80]


def salt(state: str) -> str:
    """A per-machine salt so a short input cannot be guessed back from its hash."""
    path = os.path.join(state, "call-cap.salt")
    try:
        with open(path, encoding="utf-8") as fh:
            s = fh.read().strip()
        if s:
            return s
    except OSError:
        pass
    s = os.urandom(16).hex()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(s)
    except OSError:
        pass
    return s


def digest(salt_: str, *parts, n: int = 10) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256((salt_ + raw).encode("utf-8", "replace")).hexdigest()[:n]


def signature(salt_: str, tool: str, tool_input) -> str:
    return f"{safe(str(tool or '?'))}#{digest(salt_, tool_input)}"


def in_work_tree(path: str) -> bool:
    """True when path or any parent holds a .git entry (a repo or a worktree)."""
    p = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(p, ".git")):
            return True
        parent = os.path.dirname(p)
        if parent == p:
            return False
        p = parent


def log_event(state: str, line: dict) -> None:
    try:
        if in_work_tree(state):
            return
        line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **line}
        with open(os.path.join(state, EVENTS), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=True) + "\n")
    except Exception:
        pass


def cap_for(caps: dict, agent: str, atype: str):
    cap = (caps.get("by_agent_id") or {}).get(agent)
    if cap is None:
        cap = (caps.get("by_agent_type") or {}).get(atype, caps.get("default"))
    return None if cap is None else int(cap)


def count_path(state: str, session: str, agent: str) -> str:
    return os.path.join(state, f"count-{safe(session or 'none')}-{safe(agent)}.json")


def load_caps(state: str) -> dict:
    try:
        caps = hl.load_json(os.path.join(state, "call-caps.json"))
        return caps if isinstance(caps, dict) else {}
    except (OSError, ValueError):
        return {}


def track_signals(rec: dict, salt_: str, tool: str, ti) -> None:
    """Re-reads of one file and edits that undo an earlier edit, as counts only."""
    ti = ti if isinstance(ti, dict) else {}
    fp = ti.get("file_path") or ti.get("notebook_path") or ""
    if tool == "Read" and fp:
        reads = rec.setdefault("reads", {})
        k = digest(salt_, "read", fp, n=8)
        if k in reads or len(reads) < MAX_KEYS:
            reads[k] = reads.get(k, 0) + 1
            if reads[k] >= 3:
                rec["rereads"] = rec.get("rereads", 0) + 1
            rec["reread_max"] = max(rec.get("reread_max", 0), reads[k])
    elif tool == "Edit" and fp:
        old, new = str(ti.get("old_string", "")), str(ti.get("new_string", ""))
        edits = rec.setdefault("edits", [])
        if digest(salt_, "edit", fp, new, old, n=8) in edits:
            rec["reverts"] = rec.get("reverts", 0) + 1
        edits.append(digest(salt_, "edit", fp, old, new, n=8))
        del edits[:-MAX_KEYS]


def signal_fields(rec: dict) -> dict:
    return {k: int(rec.get(k, 0)) for k in ("rereads", "reread_max", "reverts")}


# ------------------------------------------------------------------ transcript reading

def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
    return ""


def unit_of(prompt: str) -> str | None:
    m = UNIT_LINE.search(prompt) or UNIT_SAY.search(prompt)
    if not m:
        return None
    v = re.split(r"[\\/]", m.group(1).strip().rstrip(".,;:"))[-1]
    v = re.sub(r"\.(md|txt|json|ya?ml)$", "", v, flags=re.I)
    v = re.sub(r"[^A-Za-z0-9_.-]", "", v)[:40]
    return v or None


def _epoch(ts) -> float | None:
    try:
        import datetime as dt
        return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def transcript_stats(path: str, salt_: str, limit: int | None = None) -> dict | None:
    """Counts from a subagent transcript (JSONL). Only ids, counts and hashes come out.

    limit keeps the first `limit` tool calls (the calls the cap allowed), so blocked calls
    after a hard stop do not read as an error run."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    calls, results, prompt, first_ts, last_ts = [], {}, None, None, None
    for raw in lines:
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        ts = d.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        content = msg.get("content")
        if d.get("type") == "user" and prompt is None and not d.get("isMeta"):
            if isinstance(content, str) or (isinstance(content, list) and any(
                    isinstance(x, dict) and x.get("type") == "text" for x in content)):
                prompt = _text(content)
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                calls.append((item.get("id"), str(item.get("name") or "?"), item.get("input")))
            elif item.get("type") == "tool_result":
                results[item.get("tool_use_id")] = (bool(item.get("is_error")), _text(item.get("content")))
    if limit is not None:
        calls = calls[:max(limit, 0)]
    errors = run = max_run = writes = since_write = 0
    hook_blocks: dict[str, int] = {}
    skills: list[str] = []
    for cid, name, ti in calls:
        is_err, text = results.get(cid, (False, ""))
        ti = ti if isinstance(ti, dict) else {}
        if name == "Skill" and isinstance(ti.get("skill"), str):
            skills.append(safe(ti["skill"]))
        head = text[:300]
        by_hook = is_err and "hook error" in head  # "PreToolUse:<tool> hook error: [<command>]: <reason>"
        cap_block = is_err and ("call cap:" in head or (by_hook and "call_cap" in head))
        for h in OTHER_HOOKS:
            if by_hook and h in head:
                hook_blocks[h] = hook_blocks.get(h, 0) + 1
        if cap_block:
            hook_blocks["call_cap"] = hook_blocks.get("call_cap", 0) + 1
        elif is_err:
            errors += 1
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
        cmd = str(ti.get("command", ""))
        if name in WRITE_TOOLS or (name in SHELL_TOOLS and re.search(r"\bgit\b[^\n]*\bcommit\b", cmd)):
            writes += 1
            since_write = 0
        else:
            since_write += 1
    a, b = _epoch(first_ts), _epoch(last_ts)
    return {"calls": len(calls), "errors": errors, "max_error_run": max_run, "tail_error_run": run,
            "hook_blocks": hook_blocks, "writes": writes, "calls_since_write": since_write,
            "recent": [signature(salt_, n, ti) for _, n, ti in calls[-RING:]],
            "skills": list(dict.fromkeys(skills)),
            "duration_s": round(b - a) if a is not None and b is not None else None,
            "unit": unit_of(prompt or ""), "prompt_hash": digest(salt_, prompt, n=12) if prompt else None}


def agent_transcript(ev: dict, agent: str) -> str | None:
    p = ev.get("agent_transcript_path")
    if isinstance(p, str) and os.path.isfile(p):
        return p
    t = ev.get("transcript_path")
    if isinstance(t, str) and t.endswith(".jsonl"):
        guess = os.path.join(t[:-6], "subagents", f"agent-{agent}.jsonl")
        if os.path.isfile(guess):
            return guess
    return None


# ------------------------------------------------------------------ events

def on_stop(ev: dict) -> None:
    """SubagentStop: one end line per finished subagent. Never blocks, never prints."""
    agent = str(ev.get("agent_id") or "")
    if not agent:
        return
    state = hl.state_dir()
    session = str(ev.get("session_id") or "none")
    path = count_path(state, session, agent)
    try:
        rec = hl.load_json(path)
    except (OSError, ValueError):
        rec = {}
    if rec.get("ended"):
        return
    atype = str(ev.get("agent_type") or rec.get("agent_type") or "")
    s = salt(state)
    tpath = agent_transcript(ev, agent)
    stats = transcript_stats(tpath, s) if tpath else None
    caps = load_caps(state)
    line = {"event": "end", "source": "SubagentStop", "session": safe(session), "agent_id": safe(agent),
            "agent_type": safe(atype), "calls": int(rec.get("count", 0)), "cap": cap_for(caps, agent, atype),
            "blocks": int(rec.get("blocks", 0)), **signal_fields(rec)}
    if stats:
        line.update({k: stats[k] for k in ("errors", "max_error_run", "tail_error_run", "hook_blocks", "writes",
                                           "calls_since_write", "duration_s", "unit", "prompt_hash", "skills")})
        line["transcript_calls"] = stats["calls"]
    elif rec.get("first_ts"):
        line["duration_s"] = round(time.time() - float(rec["first_ts"]))
    line["recent"] = list(rec.get("ring") or (stats or {}).get("recent") or [])
    log_event(state, line)
    if rec:
        rec["ended"] = True
        hl.write_json_atomic(path, rec)


def main() -> None:
    ev, _ = hl.read_event()
    if hl.stood_down("F3B"):
        sys.exit(0)
    try:
        if ev and ev.get("hook_event_name") == "SubagentStop":
            on_stop(ev)
            sys.exit(0)
        if not ev or not ev.get("agent_id"):
            hl.allow()
        agent, atype = str(ev["agent_id"]), str(ev.get("agent_type") or "")
        session = str(ev.get("session_id") or "none")
        state = hl.state_dir()
        caps = load_caps(state)
        cap = cap_for(caps, agent, atype)
        path = count_path(state, session, agent)
        try:
            rec = hl.load_json(path)
            rec = rec if isinstance(rec, dict) else {}
        except (OSError, ValueError):
            rec = {}
        try:
            count = int(rec.get("count", 0)) + 1
        except (TypeError, ValueError):
            count = 1
        tool = str(ev.get("tool_name") or "")
        rec.update(count=count, agent_type=atype)
        rec.setdefault("first_ts", time.time())
        line = None
        try:
            s = salt(state)
            sig = signature(s, tool, ev.get("tool_input"))
            rec["ring"] = (list(rec.get("ring") or []) + [sig])[-RING:]
            track_signals(rec, s, tool, ev.get("tool_input"))
            line = {"session": safe(session), "agent_id": safe(agent), "agent_type": safe(atype),
                    "count": count, "tool": safe(tool), "sig": sig}
        except Exception:
            pass
        if cap is None:
            hl.write_json_atomic(path, rec)
            hl.allow()
        grace = int(caps.get("grace", 10))
        warn_at = float(caps.get("warn_at", 0.85))
        kind = None
        if count > cap + grace:
            if tool not in (caps.get("always_allow") or DEFAULT_ALWAYS):
                rec["blocks"] = int(rec.get("blocks", 0)) + 1
                kind = "block" if rec["blocks"] <= MAX_BLOCK_LINES else None
        elif count > cap and not rec.get("capped"):
            rec["capped"], kind = True, "cap"
        elif count >= warn_at * cap and not rec.get("warned"):
            rec["warned"], kind = True, "warn"
        hl.write_json_atomic(path, rec)
        if kind and line:
            log_event(state, {"event": kind, **line, "cap": cap, "grace": grace,
                              "blocks": int(rec.get("blocks", 0)), **signal_fields(rec),
                              "recent": list(rec.get("ring") or [])})
        if count > cap + grace:
            if tool in (caps.get("always_allow") or DEFAULT_ALWAYS):
                hl.allow()
            hl.block(f"call cap: {count - 1} calls made against a cap of {cap} (+{grace} grace). "
                     "Stop work now: commit what is done, write the report, and hand back.", rule="call_cap")
        if count > cap:
            hl.allow(context=f"call cap: past cap ({count}/{cap}); commit and report now. "
                             f"Hard stop after call {cap + grace}.")
        if count >= warn_at * cap:
            hl.allow(context=f"call cap: call {count} of {cap}. Finish the current piece, then commit and report.")
        hl.allow()
    except SystemExit:
        raise
    except Exception:
        hl.allow()


if __name__ == "__main__":
    main()
