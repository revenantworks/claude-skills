#!/usr/bin/env python3
"""dispatch_budget_write.py -- write pacewright's budget decision file with
timestamps read from the clock, never typed (observation 0343).

A controller once wrote a planned launch time (15:40Z) into `written_at` at
15:29Z, and a pace display read the fresh file as stale. A rule in the skill
text was in context and broken twice in one session, so the stamp is now made
here: `written_at` and `expires_at` come from the system clock inside this one
command, and there is no flag that accepts a literal time for either.

    python dispatch_budget_write.py --mode reset-eve --parallel 7 --ttl 2h \
        --basis "weekly 92% at 16:24Z" --target-pct 98 --target-at 2026-10-07T22:00:00Z

Every field not given is kept from the existing file (meter_budgets, stop_bands
and so on); the two stamps are always rewritten. `--owner-reading 93` records
the owner's weekly reading with read_at = now, so the reset-eve line in
dispatch_gate.py prefers it over a lagging meter file (observation 0350).
`--target-pct` / `--target-at` carry the owner's goal (observation 0350);
`--lane-rate` carries the measured points per lane-hour (observation 0349).

The file is `DISPATCH_BUDGET_FILE` or ~/.dispatch/budget-decision.json, or
`--file PATH`. The write is atomic (temp file, then rename). `--dry-run` prints
the JSON and writes nothing. `--selftest` exercises every rule against a temp
file. Rig tooling, not skill package content: the skill ships no code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

MODES = ("normal", "pace", "turbo", "overnight", "owner-away", "reset-eve")
CEILING_LIMIT = 12          # the same ceiling dispatch_ledger_guard.py clamps to
MAX_TTL_SECONDS = 5 * 3600  # the file never outlives a 5-hour window
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
FORBIDDEN = ("--written-at", "--expires-at", "--written_at", "--expires_at")


def budget_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    override = os.environ.get("DISPATCH_BUDGET_FILE")
    return Path(override) if override else Path.home() / ".dispatch" / "budget-decision.json"


def parse_ttl(text: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([hm])\s*", text or "")
    if not m:
        raise ValueError(f"--ttl {text!r}: use a number of hours or minutes, such as 2h or 90m")
    secs = int(m.group(1)) * (3600 if m.group(2) == "h" else 60)
    if not 0 < secs <= MAX_TTL_SECONDS:
        raise ValueError(f"--ttl {text!r}: must be above 0 and at most 5h")
    return secs


def _iso(ts: float) -> str:
    return time.strftime(ISO_FMT, time.gmtime(ts))


def build(existing: dict, args: argparse.Namespace, now: float) -> dict:
    d = dict(existing) if isinstance(existing, dict) else {}
    d.setdefault("schema", 1)
    if args.mode:
        if args.mode not in MODES:
            raise ValueError(f"--mode {args.mode!r}: one of {', '.join(MODES)}")
        d["mode"] = args.mode
    if args.parallel is not None:
        if not 0 <= args.parallel <= CEILING_LIMIT:
            raise ValueError(f"--parallel {args.parallel}: 0 to {CEILING_LIMIT}")
        d["parallel_ceiling"] = args.parallel
    if args.basis is not None:
        d["basis"] = args.basis
    if args.target_pct is not None or args.target_at is not None:
        if args.target_pct is None or args.target_at is None:
            raise ValueError("--target-pct and --target-at go together")
        if not 0 < args.target_pct <= 100:
            raise ValueError(f"--target-pct {args.target_pct}: above 0 and at most 100")
        try:
            from datetime import datetime, timezone
            t_at = datetime.strptime(args.target_at, ISO_FMT).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            raise ValueError(f"--target-at {args.target_at!r}: use {ISO_FMT} in UTC") from None
        if t_at <= now:
            raise ValueError(f"--target-at {args.target_at} is already past")
        d["target_pct"] = args.target_pct
        d["target_at"] = args.target_at
    if args.clear_target:
        d.pop("target_pct", None)
        d.pop("target_at", None)
    if args.owner_reading is not None:
        if not 0 <= args.owner_reading <= 100:
            raise ValueError(f"--owner-reading {args.owner_reading}: 0 to 100")
        d["owner_reading"] = {"weekly_pct": args.owner_reading, "read_at": _iso(now)}
    if args.lane_rate is not None:
        if not 0 < args.lane_rate <= 10:
            raise ValueError(f"--lane-rate {args.lane_rate}: above 0 and at most 10 pt/h")
        d["lane_pt_per_hour"] = args.lane_rate
    ttl = parse_ttl(args.ttl)
    d["written_at"] = _iso(now)
    d["expires_at"] = _iso(now + ttl)
    return d


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".budget-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write((json.dumps(data, indent=2) + "\n").encode("utf-8"))
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Write the budget decision file, stamped from the clock.")
    p.add_argument("--mode")
    p.add_argument("--parallel", type=int)
    p.add_argument("--ttl", default="2h")
    p.add_argument("--basis")
    p.add_argument("--target-pct", type=float)
    p.add_argument("--target-at")
    p.add_argument("--clear-target", action="store_true")
    p.add_argument("--owner-reading", type=float)
    p.add_argument("--lane-rate", type=float)
    p.add_argument("--file")
    p.add_argument("--dry-run", action="store_true")
    return p


def run(argv: list, now: float | None = None) -> tuple[int, str]:
    bad = [a for a in argv if a.split("=", 1)[0] in FORBIDDEN]
    if bad:
        return 2, ("dispatch_budget_write: written_at and expires_at come from the clock in this "
                   "command and cannot be typed (observation 0343); drop " + ", ".join(bad) +
                   " and set --ttl instead.")
    try:
        args = parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 2), "dispatch_budget_write: bad arguments"
    now = time.time() if now is None else now
    path = budget_path(args.file)
    try:
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        existing = {}
    try:
        data = build(existing, args, now)
    except ValueError as e:
        return 2, f"dispatch_budget_write: {e}"
    text = json.dumps(data, indent=2)
    if args.dry_run:
        return 0, text
    write_atomic(path, data)
    return 0, f"dispatch_budget_write: wrote {path} (written_at {data['written_at']}, expires_at {data['expires_at']})"


def selftest() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "b.json"
        f.write_text(json.dumps({"schema": 1, "meter_budgets": {"gh_api": {"remaining": 4800}},
                                 "written_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
        before = time.time()
        code, _ = run(["--file", str(f), "--mode", "pace", "--parallel", "3", "--ttl", "90m"])
        d = json.loads(f.read_text(encoding="utf-8"))
        from datetime import datetime, timezone
        w = datetime.strptime(d["written_at"], ISO_FMT).replace(tzinfo=timezone.utc).timestamp()
        e = datetime.strptime(d["expires_at"], ISO_FMT).replace(tzinfo=timezone.utc).timestamp()
        if code != 0 or abs(w - before) > 5:
            problems.append(f"written_at {d.get('written_at')} is not the clock (exit {code})")
        if e - w != 90 * 60:
            problems.append(f"expires_at is not written_at + ttl ({e - w} s)")
        if d.get("meter_budgets", {}).get("gh_api", {}).get("remaining") != 4800:
            problems.append("an untouched field (meter_budgets) was not kept")
        if d.get("mode") != "pace" or d.get("parallel_ceiling") != 3:
            problems.append("mode or parallel_ceiling was not written")
        for forged in (["--written-at", "2026-10-06T15:40:00Z"], ["--expires-at=2026-10-06T17:40:00Z"]):
            code, msg = run(["--file", str(f)] + forged)
            if code != 2 or "observation 0343" not in msg:
                problems.append(f"a typed stamp {forged[0]} was not refused (exit {code})")
        now = 1_791_390_240.0  # 2026-10-07 16:24:00Z
        code, out = run(["--file", str(f), "--dry-run", "--target-pct", "98", "--target-at",
                         "2026-10-07T22:00:00Z", "--owner-reading", "92", "--lane-rate", "0.22"], now=now)
        dd = json.loads(out) if code == 0 else {}
        if dd.get("target_pct") != 98 or dd.get("target_at") != "2026-10-07T22:00:00Z":
            problems.append(f"the target fields were not written (exit {code}: {out[:200]})")
        if dd.get("owner_reading") != {"weekly_pct": 92, "read_at": "2026-10-07T16:24:00Z"}:
            problems.append(f"owner_reading is not stamped from the clock: {dd.get('owner_reading')}")
        if dd.get("lane_pt_per_hour") != 0.22:
            problems.append("lane_pt_per_hour was not written")
        if json.loads(f.read_text(encoding="utf-8")).get("target_pct") is not None:
            problems.append("--dry-run wrote the file")
        for label, extra in (("a past target", ["--target-pct", "98", "--target-at", "2026-10-07T10:00:00Z"]),
                             ("a half target", ["--target-pct", "98"]),
                             ("a target over 100", ["--target-pct", "120", "--target-at", "2026-10-07T22:00:00Z"]),
                             ("a ceiling over the limit", ["--parallel", "40"]),
                             ("an unknown mode", ["--mode", "burn"]),
                             ("a ttl over 5h", ["--ttl", "6h"]),
                             ("a ttl of a clock time", ["--ttl", "15:40"])):
            code, _ = run(["--file", str(f), "--dry-run"] + extra, now=now)
            if code != 2:
                problems.append(f"{label} was accepted (exit {code})")
    if problems:
        for p in problems:
            print(f"DISPATCH_BUDGET_WRITE SELFTEST FAIL: {p}")
        return 2
    print("dispatch_budget_write selftest: OK (clock stamps, ttl expiry, kept fields, two typed-stamp "
          "refusals, target/owner-reading/lane-rate fields, dry run, 7 refused inputs)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    code, msg = run(sys.argv[1:])
    print(msg, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
