#!/usr/bin/env python3
"""launch_throttle.py: PreToolUse hook (matcher Agent|Task|Workflow) that refuses a
new launch when the usage meters sit in the stop band.

Reads two data files, never writes either:
  - the meter reading the statusline writes (GATEWARDEN_USAGE_FILE, default
    ~/.claude/usage-windows.json): `written_at` (epoch seconds) and
    `five_hour` / `seven_day`, each {used_percentage, resets_at};
  - the budget decision a pacing skill may write (GATEWARDEN_BUDGET_FILE, default
    ~/.dispatch/budget-decision.json): `expires_at` (ISO 8601), `stop_bands`
    {slow, stop}, `parallel_ceiling`, `mode`. Used only while unexpired.

Decision, per launch:
  - parallel_ceiling 0 in a live budget decision -> block;
  - either window at or above the stop band (default 95) -> block;
  - either window at or above the slow band (default 80) -> allow with a note
    (one unit at a time, cheaper tier);
  - otherwise allow silently.

Fail mode: open, and it says so. A missing reading, or one older than
GATEWARDEN_USAGE_MAX_AGE seconds (default 900), allows the launch with a
"not enforced" note to Claude and the person watching. The meters exist only on
subscription plans, after a session's first response.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

LAUNCH_TOOLS = {"Agent", "Task", "Workflow"}


def iso_to_epoch(s: str) -> float:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def main() -> None:
    ev, _ = hl.read_event()
    if hl.stood_down("F3B"):
        sys.exit(0)
    try:
        if not ev or ev.get("tool_name") not in LAUNCH_TOOLS:
            hl.allow()
        home = os.path.expanduser("~")
        usage_path = os.environ.get("GATEWARDEN_USAGE_FILE") or os.path.join(home, ".claude", "usage-windows.json")
        budget_path = os.environ.get("GATEWARDEN_BUDGET_FILE") or os.path.join(home, ".dispatch", "budget-decision.json")
        max_age = float(os.environ.get("GATEWARDEN_USAGE_MAX_AGE", "900"))
        slow, stop, ceiling = 80.0, 95.0, None
        try:
            bd = hl.load_json(budget_path)
            if iso_to_epoch(bd.get("expires_at")) > time.time():
                bands = bd.get("stop_bands") or {}
                slow = float(bands.get("slow", slow))
                stop = float(bands.get("stop", stop))
                ceiling = bd.get("parallel_ceiling")
        except Exception:
            pass
        if ceiling is not None and int(ceiling) <= 0:
            hl.block("launch throttle: the live budget decision sets parallel_ceiling 0; nothing launches. "
                     "Commit running work and check the meters before the next launch.", rule="launch_throttle.ceiling")
        try:
            u = hl.load_json(usage_path)
            age = time.time() - float(u.get("written_at", 0))
        except Exception:
            u, age = None, None
        if u is None or age is None or age > max_age:
            why = "no meter reading" if u is None else f"meter reading {int(age // 60)} min old"
            note = f"launch throttle not enforced: {why}. Read the meters before launching more work."
            hl.allow(context=note, message=note)
        readings = {}
        for key in ("five_hour", "seven_day"):
            w = u.get(key) or {}
            if isinstance(w, dict) and w.get("used_percentage") is not None:
                readings[key] = float(w["used_percentage"])
        text = ", ".join(f"{k} {v:g}%" for k, v in readings.items())
        if any(v >= stop for v in readings.values()):
            hl.block(f"launch throttle: stop band ({stop:g}%) reached ({text}). Nothing new launches; "
                     "running writers commit and stop.", rule="launch_throttle.stop")
        if any(v >= slow for v in readings.values()):
            hl.allow(context=f"launch throttle: slow band ({slow:g}%) reached ({text}). "
                             "Launch one unit at a time, on a cheaper tier.")
        hl.allow()
    except SystemExit:
        raise
    except Exception:
        hl.allow()


if __name__ == "__main__":
    main()
