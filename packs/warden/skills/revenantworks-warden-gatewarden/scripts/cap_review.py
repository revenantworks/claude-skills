#!/usr/bin/env python3
"""cap_review.py: read call_cap's local event log and say, for each block, whether the
cap stopped a runaway agent or a working one too early. Read-only; stdlib only
(DuckDB optional, for --duckdb).

  python cap_review.py [--since YYYY-MM-DD] [--transcripts DIR] [--state DIR]
                       [--json] [--out FILE] [--duckdb [FILE]] [--min-units 20]

Verdicts per block:
  runaway   - the last calls repeat (one signature LOOP_REPEAT+ times in the last
              LOOP_WINDOW calls, or LOOP_DISTINCT or fewer distinct signatures there), or
              ERROR_RUN+ consecutive tool errors, or a writing agent made no write or
              commit in its last STALL calls;
  premature - none of those, the last calls are mostly distinct, and writes or commits
              continued: the cap was too low for the job;
  unclear   - neither pattern holds (a read-only agent with no write evidence lands here).

Proposals: a premature block proposes ceil(observed calls x 1.25) for its agent type; an
agent type with --min-units or more finished, non-runaway units proposes ceil(highest
run x 1.25). Both come out as one complete call-caps.json for the owner to copy in. This
script never writes the live caps file, and refuses any output path inside a git work tree.
Exit: 0 report printed, 3 no event log, 4 crash.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "hooks"))
import call_cap as cc  # noqa: E402

LOOP_WINDOW = 12
LOOP_REPEAT = 5
LOOP_DISTINCT = 3
DISTINCT_PROGRESS = 0.75
ERROR_RUN = 5
STALL = 25
MARGIN = 1.25


def state_dir(arg: str | None) -> str:
    return arg or os.environ.get("GATEWARDEN_STATE") or os.path.join(os.path.expanduser("~"), ".claude", "gatewarden")


def load_events(state: str, since: str | None) -> list[dict] | None:
    path = os.path.join(state, cc.EVENTS)
    if not os.path.isfile(path):
        return None
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if isinstance(d, dict) and (not since or str(d.get("ts", "")) >= since):
                out.append(d)
    return out


def transcript_index(root: str | None) -> dict[str, str]:
    idx: dict[str, str] = {}
    if not root:
        return idx
    for dirpath, _, files in os.walk(os.path.expanduser(root)):
        for f in files:
            if f.startswith("agent-") and f.endswith(".jsonl"):
                idx.setdefault(f[6:-6], os.path.join(dirpath, f))
    return idx


def loop_of(ring: list[str]) -> str | None:
    tail = list(ring)[-LOOP_WINDOW:]
    if len(tail) < 6:
        return None
    top, n = Counter(tail).most_common(1)[0]
    if n >= LOOP_REPEAT:
        return f"{top} repeated {n}x in the last {len(tail)} calls"
    distinct = len(set(tail))
    if len(tail) >= 9 and distinct <= LOOP_DISTINCT:
        return f"{distinct} distinct calls cycling through the last {len(tail)} ({', '.join(sorted(set(tail)))})"
    return None


def classify(ring: list[str], stats: dict | None) -> tuple[str, list[str]]:
    """(verdict, evidence) from the signature ring and optional transcript counts."""
    ev, runaway = [], False
    loop = loop_of(ring)
    if loop:
        runaway = True
        ev.append(f"loop: {loop}")
    if stats and max(stats.get("max_error_run") or 0, stats.get("tail_error_run") or 0) >= ERROR_RUN:
        runaway = True
        ev.append(f"error run: {max(stats.get('max_error_run') or 0, stats.get('tail_error_run') or 0)} consecutive tool errors")
    if stats and (stats.get("writes") or 0) > 0 and (stats.get("calls_since_write") or 0) >= STALL:
        runaway = True
        ev.append(f"stall: no write or commit in the last {stats['calls_since_write']} calls")
    if runaway:
        return "runaway", ev
    tail = list(ring)[-LOOP_WINDOW:]
    distinct = len(set(tail)) / len(tail) if tail else 0.0
    ring_writes = sum(1 for s in ring if s.split("#", 1)[0] in cc.WRITE_TOOLS)
    writes_on = ring_writes > 0 or bool(stats and (stats.get("writes") or 0) > 0
                                          and (stats.get("calls_since_write") or 0) < STALL)
    ev.append(f"{len(set(tail))}/{len(tail)} distinct in the last {len(tail)} calls")
    if ring_writes:
        ev.append(f"{ring_writes} write call(s) in the last {len(ring)}")
    elif stats and stats.get("writes"):
        ev.append(f"{stats['writes']} write/commit call(s), last one {stats.get('calls_since_write')} calls before the end")
    if tail and distinct >= DISTINCT_PROGRESS and writes_on:
        return "premature", ev
    if not writes_on:
        ev.append("no write evidence")
    return "unclear", ev


def target_skill(verdict: str, stats: dict | None) -> str | None:
    if verdict == "premature":
        return "dispatchwright"
    if verdict == "runaway":
        skills = (stats or {}).get("skills") or []
        return skills[-1] if skills else "dispatchwright"
    return None


def warnings(line: dict, stats: dict | None) -> list[str]:
    out = []
    src = {**line, **(stats or {})}
    if src.get("rereads"):
        out.append(f"re-reads {src['rereads']} (one file {src.get('reread_max')}x)")
    if src.get("reverts"):
        out.append(f"reverted edits {src['reverts']}")
    if src.get("errors"):
        out.append(f"errors {src['errors']}")
    hb = {k: v for k, v in (src.get("hook_blocks") or {}).items() if k != "call_cap"}
    if hb:
        out.append("hook blocks " + ", ".join(f"{k} {v}" for k, v in sorted(hb.items())))
    return out


def review(events: list[dict], tindex: dict[str, str], salt_: str) -> dict:
    groups: dict[tuple, dict] = {}
    for e in events:
        g = groups.setdefault((e.get("session"), e.get("agent_id")), {"block": None, "end": None, "cap": None})
        kind = e.get("event")
        if kind == "block" and g["block"] is None:
            g["block"] = e
        elif kind == "end":
            g["end"] = e
        elif kind == "cap":
            g["cap"] = e
    blocks, ends = [], []
    for (session, agent), g in groups.items():
        end, blk = g["end"], g["block"]
        if blk:
            limit = int(blk.get("count", 1)) - 1
            stats = None
            if agent in tindex:
                stats = cc.transcript_stats(tindex[agent], salt_, limit=limit)
            elif end and "errors" in end:
                stats = end
            verdict, evidence = classify(blk.get("recent") or [], stats)
            observed = max(int(blk.get("count", 0)), int((end or {}).get("calls", 0)))
            blocks.append({"session": session, "agent_id": agent, "agent_type": blk.get("agent_type"),
                           "count": blk.get("count"), "cap": blk.get("cap"), "grace": blk.get("grace"),
                           "observed": observed, "verdict": verdict, "evidence": evidence,
                           "warnings": warnings(blk, stats), "target_skill": target_skill(verdict, stats),
                           "unit": (stats or end or {}).get("unit"),
                           "prompt_hash": (stats or end or {}).get("prompt_hash"),
                           "transcript": agent in tindex})
        if end:
            verdict, evidence = classify(end.get("recent") or [], end if "errors" in end else None)
            ends.append({"session": session, "agent_id": agent, "agent_type": end.get("agent_type"),
                         "calls": int(end.get("calls", 0)), "blocked": bool(blk), "verdict": verdict,
                         "evidence": evidence, "warnings": warnings(end, None), "unit": end.get("unit"),
                         "duration_s": end.get("duration_s")})
    return {"blocks": blocks, "ends": ends}


def propose(caps: dict, result: dict, min_units: int) -> tuple[dict, list[str]]:
    new = json.loads(json.dumps(caps or {}))
    by_type = new.setdefault("by_agent_type", {})
    why, wanted = [], {}
    for b in result["blocks"]:
        t = b.get("agent_type")
        if b["verdict"] == "premature" and t:
            p = math.ceil(b["observed"] * MARGIN)
            cur = by_type.get(t, new.get("default"))
            if cur is None or p > int(cur):
                wanted[t] = max(wanted.get(t, 0), p)
                why.append(f"{t}: {cur} -> {p} (premature block at {b['observed']} calls, +25%)")
    per_type: dict[str, list[int]] = {}
    for e in result["ends"]:
        if e["verdict"] != "runaway" and not e["blocked"] and e.get("agent_type"):
            per_type.setdefault(e["agent_type"], []).append(e["calls"])
    for t, runs in sorted(per_type.items()):
        if len(runs) >= min_units:
            p = math.ceil(max(runs) * MARGIN)
            if t in wanted:
                p = max(p, wanted[t])
            cur = by_type.get(t, new.get("default"))
            if cur is None or int(cur) != p:
                wanted[t] = p
                why.append(f"{t}: {cur} -> {p} ({len(runs)} finished units, highest normal run {max(runs)}, +25%)")
    by_type.update(wanted)
    return new, why


def refuse_path(path: str, live_caps: str) -> str | None:
    p = os.path.abspath(path)
    if os.path.normcase(p) == os.path.normcase(os.path.abspath(live_caps)):
        return "refused: that is the live caps file; the owner copies the proposal in"
    if cc.in_work_tree(os.path.dirname(p) or "."):
        return "refused: the path is inside a git work tree; the log and its outputs stay off every repo"
    return None


def build_duckdb(state: str, target: str) -> str:
    try:
        import duckdb  # optional; never installed by this script
    except ImportError:
        return "duckdb not installed; skipped (duckrunner or DuckDB can read the JSONL directly)"
    con = duckdb.connect(target)
    try:
        con.execute("CREATE OR REPLACE TABLE events AS SELECT * FROM read_json_auto(?, format='newline_delimited')",
                    [os.path.join(state, cc.EVENTS)])
    finally:
        con.close()
    return f"duckdb cache written: {target} (table events)"


def render(result: dict, why: list[str], proposal: dict | None) -> str:
    out = ["## Blocks", ""]
    if result["blocks"]:
        out += ["| agent | type | unit | blocked at | cap+grace | verdict | evidence | warnings | observation target |",
                "|---|---|---|---|---|---|---|---|---|"]
        for b in result["blocks"]:
            out.append(f"| {b['agent_id']} | {b['agent_type'] or '-'} | {b['unit'] or '-'} | {b['count']} | "
                       f"{b['cap']}+{b['grace']} | **{b['verdict']}** | {'; '.join(b['evidence'])} | "
                       f"{'; '.join(b['warnings']) or '-'} | {b['target_skill'] or '-'} |")
        for b in result["blocks"]:
            if b["verdict"] == "runaway":
                out.append(f"\n- Runaway {b['agent_id']}: {'; '.join(b['evidence'])}. Change the brief or the "
                           f"skill step ({b['target_skill']}): add a stop condition for the repeated call or the "
                           "failing command, and say what to do instead of retrying.")
            if not b["transcript"]:
                out.append(f"- {b['agent_id']}: no transcript read (pass --transcripts); verdict from signatures"
                           " and the end line only.")
    else:
        out.append("No block in the log for this window.")
    runaway_ends = [e for e in result["ends"] if e["verdict"] == "runaway" and not e["blocked"]]
    flagged = [e for e in result["ends"] if e["warnings"]]
    out += ["", "## Finished units", "",
            f"{len(result['ends'])} finished; {sum(e['blocked'] for e in result['ends'])} after a block; "
            f"{len(runaway_ends)} with a runaway pattern that finished under the cap; "
            f"{len(flagged)} with warning signals."]
    for e in runaway_ends + [e for e in flagged if e not in runaway_ends]:
        out.append(f"- {e['agent_id']} ({e['agent_type'] or '-'}, {e['calls']} calls): {e['verdict']}; "
                   f"{'; '.join(e['evidence'] + e['warnings'])}")
    out += ["", "## Proposed caps", ""]
    if proposal is not None and why:
        out += [f"- {w}" for w in why]
        out += ["", "Complete call-caps.json for the owner to copy in (nothing was written):", "", "```json",
                json.dumps(proposal, indent=2), "```"]
    else:
        out.append("No change proposed.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--since", help="ISO date; events before it are ignored")
    ap.add_argument("--transcripts", help="folder holding subagent transcripts (searched for agent-<id>.jsonl)")
    ap.add_argument("--state", help="gatewarden state folder (default GATEWARDEN_STATE or ~/.claude/gatewarden)")
    ap.add_argument("--caps", help="caps file to base the proposal on (default <state>/call-caps.json)")
    ap.add_argument("--min-units", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="write the proposed caps file here (never the live one, never in a repo)")
    ap.add_argument("--duckdb", nargs="?", const="", help="also build a local DuckDB cache (default beside the log)")
    a = ap.parse_args()
    state = state_dir(a.state)
    events = load_events(state, a.since)
    if events is None:
        print(f"NOT-RUN: no event log at <state>/{cc.EVENTS}; install the updated call_cap.py first.")
        return 3
    live = os.path.join(state, "call-caps.json")
    try:
        caps = cc.hl.load_json(a.caps or live)
    except (OSError, ValueError):
        caps = {}
    salt_ = cc.salt(state) if os.path.isdir(state) else ""
    result = review(events, transcript_index(a.transcripts), salt_)
    proposal, why = propose(caps if isinstance(caps, dict) else {}, result, a.min_units)
    if a.json:
        print(json.dumps({**result, "proposal_reasons": why, "proposal": proposal if why else None}, indent=2))
    else:
        print(render(result, why, proposal))
    if a.out and why:
        bad = refuse_path(a.out, live)
        if bad:
            print(bad, file=sys.stderr)
            return 2
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(proposal, indent=2) + "\n")
        print(f"\nwrote {a.out}; copy it over the live caps file yourself.")
    if a.duckdb is not None:
        target = a.duckdb or os.path.join(state, "call-cap-events.duckdb")
        bad = refuse_path(target, live)
        print(bad if bad else build_duckdb(state, target), file=sys.stderr if bad else sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"CRASH: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(4)
