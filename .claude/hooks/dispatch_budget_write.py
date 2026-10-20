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

The rig-aware turbo (owner 2026-10-20, observation 0470; it reverses the
2026-10-16 "no cap" ruling). Turbo lifts the spend throttle, never a machine
limit, so this writer refuses every turbo file that could stand for "no cap":

  - `--parallel none` is refused in every mode. Rig-aware turbo writes no
    number: the ledger guard keeps writers at 6 and all units at 12, and its
    rig gate bounds each heavy launch. A number stays 0 to 12, and in turbo
    (the "lower number" answer) 0 to 6. Entering turbo with no `--parallel`
    drops a number kept from the old file (a pace `--parallel 2` once capped
    turbo at 6); a turbo renewal keeps the user's own lower number.
  - A turbo `--ttl` is at most 2 h (one check interval); other modes keep 5 h.
  - A turbo file never expires past the next Overnight start (22:00
    user-local) and is not written inside Overnight (22:00-09:00), unless
    `--night-order "<the user's words>"` records that the user ordered turbo
    for the night. The order is kept until the next 09:00 user-local.
  - Renewing turbo (the file already says turbo) is a check: it needs
    `--landed N` (rows landed since the last check) and a reading under 15
    minutes old (`--owner-reading`, or a usage-windows file written in the last
    15 minutes). Each renewal appends to `turbo_checks`; the second check in a
    row with 0 landed writes `"mode": "normal"` instead and says so.
  - `top_tier_open` is false unless `--top-open --owner-word "<quote>"` is
    given on this write; the quote and the time go in beside it.
  - A key outside the schema is dropped and named on stderr (a field no reader
    enforces gives false comfort: `parallel_split`, 2026-10-19).
  - `stop_bands.stop` above 95 (or below 50) is refused, and a slow band above
    the stop band; `--stop-band` / `--slow-band` set them.
  - Every file carries `"writer": "dispatch_budget_write"` and
    `content_sha256`, the SHA-256 of the file's canonical JSON without that
    key. The ledger guard reads a turbo file without a valid stamp as no turbo.

The file is `DISPATCH_BUDGET_FILE` or ~/.dispatch/budget-decision.json, or
`--file PATH`. The usage-windows file is `--windows-file`, else
CLAUDE_USAGE_WINDOWS, else ~/.claude/usage-windows.json. The write is atomic
(temp file, then rename). `--dry-run` prints the JSON and writes nothing.
`--selftest` exercises every rule against a temp file. Rig tooling, not skill
package content: the skill ships no code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODES = ("normal", "pace", "turbo", "overnight", "owner-away", "reset-eve")
CEILING_LIMIT = 12          # the same ceiling dispatch_ledger_guard.py clamps numbers to
TURBO_LOWER_LIMIT = 6       # turbo's "lower number" answer: n <= 6 (the guard holds it as written)
REFUSED_WORDS = ("none", "null", "no cap", "nocap", "unlimited")
MAX_TTL_SECONDS = 5 * 3600  # the file never outlives a 5-hour window
TURBO_MAX_TTL_SECONDS = 2 * 3600   # turbo: one check interval
READING_MAX_AGE = 15 * 60   # a turbo renewal needs a reading this fresh
OVERNIGHT_START_HOUR = 22   # pacewright modes.md, Overnight: 22:00-09:00 user-local
OVERNIGHT_END_HOUR = 9
STOP_RANGE = (50.0, 95.0)   # a file may tighten the stop band, never relax it
WRITER_ID = "dispatch_budget_write"
STAMP_KEY = "content_sha256"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
FORBIDDEN = ("--written-at", "--expires-at", "--written_at", "--expires_at")
SCHEMA_KEYS = frozenset((
    "schema", "written_at", "expires_at", "mode", "basis", "spend_allowed_now", "parallel_ceiling",
    "unit_ceiling_tokens", "top_tier_open", "top_tier_owner_word", "top_tier_opened_at",
    "hosted_ci_allowed", "stop_bands", "meter_budgets", "target_pct", "target_at", "owner_reading",
    "lane_pt_per_hour", "turbo_checks", "turbo_night_order", "writer", STAMP_KEY))


def budget_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    override = os.environ.get("DISPATCH_BUDGET_FILE")
    return Path(override) if override else Path.home() / ".dispatch" / "budget-decision.json"


def windows_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    override = os.environ.get("CLAUDE_USAGE_WINDOWS")
    return Path(override) if override else Path.home() / ".claude" / "usage-windows.json"


def parse_ttl(text: str, limit: int = MAX_TTL_SECONDS) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([hm])\s*", text or "")
    if not m:
        raise ValueError(f"--ttl {text!r}: use a number of hours or minutes, such as 2h or 90m")
    secs = int(m.group(1)) * (3600 if m.group(2) == "h" else 60)
    if not 0 < secs <= limit:
        raise ValueError(f"--ttl {text!r}: must be above 0 and at most {limit // 3600}h"
                         + (" in turbo (one check interval)" if limit == TURBO_MAX_TTL_SECONDS else ""))
    return secs


def _iso(ts: float) -> str:
    return time.strftime(ISO_FMT, time.gmtime(ts))


def _parse_iso(text) -> float | None:
    try:
        return datetime.strptime(str(text), ISO_FMT).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _local_at(now: float, hour: int, days: int = 0) -> float:
    """The epoch time of `hour`:00 user-local on now's local date plus `days`."""
    lt = datetime.fromtimestamp(now)
    return (datetime(lt.year, lt.month, lt.day, hour) + timedelta(days=days)).timestamp()


def overnight_state(now: float) -> tuple[bool, float, float]:
    """(inside Overnight now, the next Overnight start, the next Overnight end), user-local."""
    hour = datetime.fromtimestamp(now).hour
    start_today = _local_at(now, OVERNIGHT_START_HOUR)
    inside = hour >= OVERNIGHT_START_HOUR or hour < OVERNIGHT_END_HOUR
    next_start = start_today if now < start_today else _local_at(now, OVERNIGHT_START_HOUR, 1)
    end_today = _local_at(now, OVERNIGHT_END_HOUR)
    next_end = end_today if now < end_today else _local_at(now, OVERNIGHT_END_HOUR, 1)
    return inside, next_start, next_end


def content_hash(d: dict) -> str:
    """SHA-256 of the canonical JSON of `d` without its stamp key (the ledger guard repeats this)."""
    body = {k: v for k, v in d.items() if k != STAMP_KEY}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def fresh_reading(args: argparse.Namespace, now: float) -> str | None:
    """Where this write's fresh usage reading comes from, or None when it has none."""
    if args.owner_reading is not None:
        return "owner reading"
    try:
        data = json.loads(windows_path(args.windows_file).read_text(encoding="utf-8"))
        ts = data.get("written_at")
        if isinstance(ts, (int, float)) and not isinstance(ts, bool) and -300 <= now - ts <= READING_MAX_AGE:
            if any(isinstance(data.get(k), dict) for k in ("five_hour", "seven_day")):
                return "usage-windows file"
    except Exception:
        pass
    return None


def build(existing: dict, args: argparse.Namespace, now: float, notes: list | None = None) -> dict:
    notes = [] if notes is None else notes
    d = dict(existing) if isinstance(existing, dict) else {}
    was_turbo = d.get("mode") == "turbo"
    for key in sorted(k for k in d if k not in SCHEMA_KEYS):
        notes.append(f"dropped key {key!r}: it is not in the budget file schema, and no reader enforces it")
        del d[key]
    d.setdefault("schema", 1)
    if args.mode:
        if args.mode not in MODES:
            raise ValueError(f"--mode {args.mode!r}: one of {', '.join(MODES)}")
        d["mode"] = args.mode
    turbo = d.get("mode") == "turbo"
    if args.parallel is not None:
        word = str(args.parallel).strip().lower()
        if word in REFUSED_WORDS:
            raise ValueError(f"--parallel {args.parallel}: there is no no-cap file (owner 2026-10-20). "
                             "Rig-aware turbo writes no number (writers 6, all units 12, every heavy "
                             f"launch through the rig gate); a lower cap is a number 0 to {CEILING_LIMIT}")
        try:
            n = int(word)
        except ValueError:
            raise ValueError(f"--parallel {args.parallel!r}: a whole number 0 to {CEILING_LIMIT}") from None
        if not 0 <= n <= CEILING_LIMIT:
            raise ValueError(f"--parallel {n}: 0 to {CEILING_LIMIT}")
        if turbo and n > TURBO_LOWER_LIMIT:
            raise ValueError(f"--parallel {n} in turbo: the turbo answer is rig-aware (no --parallel: writers "
                             f"6, all units 12) or a lower number, at most {TURBO_LOWER_LIMIT} (pacewright "
                             "modes.md, Turbo)")
        d["parallel_ceiling"] = n
    elif turbo and not was_turbo:
        # Entering turbo with no --parallel is the rig-aware answer: a pace or reset-eve number kept
        # from the old file would cap turbo at 6 (RV-SKILLS-WF F10). A renewal keeps the user's own
        # lower number.
        d.pop("parallel_ceiling", None)
    if "parallel_ceiling" in d and d["parallel_ceiling"] is None:
        del d["parallel_ceiling"]   # an old no-cap file: readers fall back to their default
    if args.basis is not None:
        d["basis"] = args.basis
    if args.target_pct is not None or args.target_at is not None:
        if args.target_pct is None or args.target_at is None:
            raise ValueError("--target-pct and --target-at go together")
        if not 0 < args.target_pct <= 100:
            raise ValueError(f"--target-pct {args.target_pct}: above 0 and at most 100")
        t_at = _parse_iso(args.target_at)
        if t_at is None:
            raise ValueError(f"--target-at {args.target_at!r}: use {ISO_FMT} in UTC")
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

    # Stop bands: a file may tighten them, never relax them (pacewright SKILL.md section 5).
    bands = dict(d.get("stop_bands") or {}) if isinstance(d.get("stop_bands"), dict) else {}
    if args.stop_band is not None:
        bands["stop"] = args.stop_band
    if args.slow_band is not None:
        bands["slow"] = args.slow_band
    stop = bands.get("stop")
    if stop is not None:
        if isinstance(stop, bool) or not isinstance(stop, (int, float)) or not STOP_RANGE[0] <= stop <= STOP_RANGE[1]:
            raise ValueError(f"stop_bands.stop {stop!r}: 50 to 95; a file never relaxes the 95 stop "
                             "(set --stop-band 95 or lower)")
    slow = bands.get("slow")
    if slow is not None:
        if isinstance(slow, bool) or not isinstance(slow, (int, float)) or not 0 < slow <= (stop if stop is not None else STOP_RANGE[1]):
            raise ValueError(f"stop_bands.slow {slow!r}: above 0 and at most the stop band")
    if bands:
        d["stop_bands"] = bands

    # The top tier: closed unless this write carries the user's quoted word.
    if args.top_open:
        if not (args.owner_word or "").strip():
            raise ValueError("--top-open needs --owner-word \"<the user's words>\": the top tier opens only on them")
        d["top_tier_open"] = True
        d["top_tier_owner_word"] = args.owner_word.strip()
        d["top_tier_opened_at"] = _iso(now)
    else:
        if args.owner_word:
            raise ValueError("--owner-word goes with --top-open")
        d["top_tier_open"] = False
        d.pop("top_tier_owner_word", None)
        d.pop("top_tier_opened_at", None)

    ttl = parse_ttl(args.ttl, TURBO_MAX_TTL_SECONDS if turbo else MAX_TTL_SECONDS)
    expires = now + ttl
    if turbo:
        inside, next_start, next_end = overnight_state(now)
        order = d.get("turbo_night_order") if isinstance(d.get("turbo_night_order"), dict) else None
        if args.night_order is not None:
            if not args.night_order.strip():
                raise ValueError("--night-order needs the user's words, quoted")
            order = {"quote": args.night_order.strip(), "at": _iso(now), "until": _iso(next_end)}
        order_live = order is not None and (_parse_iso(order.get("until")) or 0) > now
        if not order_live:
            d.pop("turbo_night_order", None)
            if inside:
                raise ValueError("turbo is not written inside Overnight (22:00-09:00 user-local) unless the "
                                 "user ordered turbo for the night: add --night-order \"<their words>\"")
            if expires > next_start:
                raise ValueError(f"a turbo file never expires past the Overnight start ({_iso(next_start)}); "
                                 f"use a ttl of at most {max(1, int((next_start - now) // 60))}m, or "
                                 "--night-order \"<the user's words>\" when the user ordered turbo for the night")
        else:
            d["turbo_night_order"] = order
        checks = [c for c in (d.get("turbo_checks") or []) if isinstance(c, dict)] if was_turbo else []
        if was_turbo:
            if args.landed is None:
                raise ValueError("renewing turbo is a check: give --landed <rows landed since the last check>")
            if args.landed < 0:
                raise ValueError(f"--landed {args.landed}: 0 or more")
            source = fresh_reading(args, now)
            if source is None:
                raise ValueError("renewing turbo needs a reading under 15 minutes old: --owner-reading <pct>, "
                                 "or a usage-windows file written in the last 15 minutes")
            checks.append({"at": _iso(now), "landed": args.landed, "reading": source})
            checks = checks[-6:]
            if len(checks) >= 2 and checks[-1]["landed"] == 0 and checks[-2]["landed"] == 0:
                notes.append("turbo dropped to normal: two checks in a row landed 0 rows (pacewright modes.md, Turbo)")
                d["mode"] = "normal"
                turbo = False
        elif args.landed is not None:
            checks = [{"at": _iso(now), "landed": args.landed, "reading": fresh_reading(args, now) or "none"}]
        if turbo:
            d["turbo_checks"] = checks
    if not turbo:
        d.pop("turbo_checks", None)
        d.pop("turbo_night_order", None)
    d["written_at"] = _iso(now)
    d["expires_at"] = _iso(expires)
    d["writer"] = WRITER_ID
    d.pop(STAMP_KEY, None)
    d[STAMP_KEY] = content_hash(d)
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
    p.add_argument("--parallel")   # a number 0..CEILING_LIMIT
    p.add_argument("--ttl", default="2h")
    p.add_argument("--basis")
    p.add_argument("--target-pct", type=float)
    p.add_argument("--target-at")
    p.add_argument("--clear-target", action="store_true")
    p.add_argument("--owner-reading", type=float)
    p.add_argument("--lane-rate", type=float)
    p.add_argument("--landed", type=int)
    p.add_argument("--top-open", action="store_true")
    p.add_argument("--owner-word")
    p.add_argument("--night-order")
    p.add_argument("--stop-band", type=float)
    p.add_argument("--slow-band", type=float)
    p.add_argument("--windows-file")
    p.add_argument("--file")
    p.add_argument("--dry-run", action="store_true")
    return p


def run(argv: list, now: float | None = None) -> tuple[int, str]:
    """(exit code, message). Notes (dropped keys, a drop to normal) go to stderr."""
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
    notes: list = []
    try:
        data = build(existing, args, now, notes)
    except ValueError as e:
        return 2, f"dispatch_budget_write: {e}"
    for n in notes:
        print(f"dispatch_budget_write: {n}", file=sys.stderr)
    text = json.dumps(data, indent=2)
    if args.dry_run:
        return 0, text
    write_atomic(path, data)
    return 0, f"dispatch_budget_write: wrote {path} (written_at {data['written_at']}, expires_at {data['expires_at']})"


def selftest() -> int:
    import contextlib
    import io
    problems = []

    def quiet(argv, now=None):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, out = run(argv, now=now)
        return code, out, err.getvalue()

    def load(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    # A daytime clock: 14:00 user-local today, so every turbo case below sits outside Overnight
    # whatever the machine's time zone.
    day = _local_at(time.time(), 14)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "b.json"
        win = Path(td) / "windows.json"
        no_win = Path(td) / "no-windows.json"
        f.write_text(json.dumps({"schema": 1, "meter_budgets": {"gh_api": {"remaining": 4800}},
                                 "written_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
        before = time.time()
        code, _, _ = quiet(["--file", str(f), "--mode", "pace", "--parallel", "3", "--ttl", "90m"])
        d = json.loads(f.read_text(encoding="utf-8"))
        w = _parse_iso(d["written_at"])
        e = _parse_iso(d["expires_at"])
        if code != 0 or abs(w - before) > 5:
            problems.append(f"written_at {d.get('written_at')} is not the clock (exit {code})")
        if e - w != 90 * 60:
            problems.append(f"expires_at is not written_at + ttl ({e - w} s)")
        if d.get("meter_budgets", {}).get("gh_api", {}).get("remaining") != 4800:
            problems.append("an untouched field (meter_budgets) was not kept")
        if d.get("mode") != "pace" or d.get("parallel_ceiling") != 3:
            problems.append("mode or parallel_ceiling was not written")
        for forged in (["--written-at", "2026-10-06T15:40:00Z"], ["--expires-at=2026-10-06T17:40:00Z"]):
            code, msg, _ = quiet(["--file", str(f)] + forged)
            if code != 2 or "observation 0343" not in msg:
                problems.append(f"a typed stamp {forged[0]} was not refused (exit {code})")
        now = 1_791_390_240.0  # 2026-10-07 16:24:00Z
        code, out, _ = quiet(["--file", str(f), "--dry-run", "--target-pct", "98", "--target-at",
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
                             ("a ttl of a clock time", ["--ttl", "15:40"]),
                             ("no cap outside turbo", ["--mode", "pace", "--parallel", "none"]),
                             ("a ceiling that is a word", ["--mode", "turbo", "--parallel", "lots"])):
            code, _, _ = quiet(["--file", str(f), "--dry-run"] + extra, now=now)
            if code != 2:
                problems.append(f"{label} was accepted (exit {code})")

        # --- the rig-aware turbo (owner 2026-10-20, observation 0470) -------------------------
        t = Path(td) / "t.json"
        no = ["--windows-file", str(no_win)]

        def turbo(extra, now_=day, path=t):
            return quiet(["--file", str(path)] + no + extra, now=now_)

        # R1: no --parallel none, in turbo or out of it; rig-aware turbo writes no number.
        code, out, _ = turbo(["--mode", "turbo", "--parallel", "none", "--ttl", "2h"])
        if code != 2 or "no-cap" not in out:
            problems.append(f"R1: turbo --parallel none was not refused (exit {code}: {out[:160]})")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h"])
        d = load(t)
        if code != 0 or d.get("mode") != "turbo" or "parallel_ceiling" in d:
            problems.append(f"R1: rig-aware turbo entry was not written without a ceiling (exit {code}: {out[:160]})")
        # R2: a turbo ttl is at most 2 h; other modes keep 5 h.
        t.unlink(missing_ok=True)
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "3h"])
        if code != 2 or "at most 2h" not in out:
            problems.append(f"R2: a 3h turbo ttl was not refused (exit {code}: {out[:160]})")
        code, _, _ = turbo(["--mode", "pace", "--ttl", "3h", "--dry-run"])
        if code != 0:
            problems.append(f"R2 control: a 3h pace ttl was refused (exit {code})")
        # R3: never past the next 22:00 user-local, never written inside Overnight, unless the
        # user ordered turbo for the night.
        _, cut, _ = overnight_state(day)
        late = cut - 30 * 60    # 21:30 user-local
        t.unlink(missing_ok=True)
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h"], now_=late)
        if code != 2 or "Overnight start" not in out:
            problems.append(f"R3: a turbo file past 22:00 user-local was accepted (exit {code}: {out[:160]})")
        code, _, _ = turbo(["--mode", "turbo", "--ttl", "20m", "--dry-run"], now_=late)
        if code != 0:
            problems.append(f"R3 control: a turbo file ending before 22:00 was refused (exit {code})")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "1h", "--dry-run"], now_=cut + 3600)
        if code != 2 or "inside Overnight" not in out:
            problems.append(f"R3: a turbo file written at 23:00 user-local was accepted (exit {code}: {out[:160]})")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--night-order", "keep building in turbo"], now_=late)
        d = load(t)
        if code != 0 or (d.get("turbo_night_order") or {}).get("quote") != "keep building in turbo":
            problems.append(f"R3: the user's night order did not let turbo run past 22:00 (exit {code}: {out[:160]})")
        # R4: renewal is a check: --landed N and a reading under 15 minutes old.
        t.unlink(missing_ok=True)
        turbo(["--mode", "turbo", "--ttl", "2h"])
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--owner-reading", "40"], now_=day + 600)
        if code != 2 or "--landed" not in out:
            problems.append(f"R4: a turbo renewal with no --landed was accepted (exit {code}: {out[:160]})")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--landed", "2"], now_=day + 600)
        if code != 2 or "15 minutes" not in out:
            problems.append(f"R4: a turbo renewal with no fresh reading was accepted (exit {code}: {out[:160]})")
        win.write_text(json.dumps({"written_at": int(day + 600) - 1200, "seven_day": {"used_percentage": 40}}),
                       encoding="utf-8")
        code, out, _ = quiet(["--file", str(t), "--windows-file", str(win), "--mode", "turbo", "--ttl", "2h",
                              "--landed", "2"], now=day + 600)
        if code != 2:
            problems.append(f"R4: a 20-minute-old usage-windows file renewed turbo (exit {code}: {out[:160]})")
        win.write_text(json.dumps({"written_at": int(day + 600) - 120, "seven_day": {"used_percentage": 40}}),
                       encoding="utf-8")
        code, out, _ = quiet(["--file", str(t), "--windows-file", str(win), "--mode", "turbo", "--ttl", "2h",
                              "--landed", "2"], now=day + 600)
        d = load(t)
        if code != 0 or [c.get("landed") for c in d.get("turbo_checks", [])] != [2]:
            problems.append(f"R4 control: a renewal with --landed and a 2-minute-old reading failed "
                            f"(exit {code}: {out[:160]}; checks {d.get('turbo_checks')})")
        turbo(["--mode", "turbo", "--ttl", "2h", "--landed", "0", "--owner-reading", "45"], now_=day + 1200)
        code, out, err = turbo(["--mode", "turbo", "--ttl", "2h", "--landed", "0", "--owner-reading", "50"],
                               now_=day + 1800)
        d = load(t)
        if code != 0 or d.get("mode") != "normal" or "dropped to normal" not in err:
            problems.append(f"R4: two checks with 0 landed did not drop turbo to normal (mode {d.get('mode')})")
        # R5: top_tier_open only with --top-open --owner-word "<quote>".
        t.write_text(json.dumps({"schema": 1, "mode": "pace", "top_tier_open": True}), encoding="utf-8")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "1h"])
        d = load(t)
        if code != 0 or d.get("top_tier_open") is not False:
            problems.append(f"R5: a turbo write kept top_tier_open without the user's word ({d.get('top_tier_open')!r})")
        code, out, _ = turbo(["--mode", "pace", "--top-open", "--dry-run"])
        if code != 2:
            problems.append(f"R5: --top-open with no --owner-word was accepted (exit {code})")
        code, out, _ = turbo(["--mode", "pace", "--top-open", "--owner-word", "run the Fable review", "--dry-run"])
        dd = json.loads(out) if code == 0 else {}
        if dd.get("top_tier_open") is not True or dd.get("top_tier_owner_word") != "run the Fable review":
            problems.append(f"R5 control: --top-open --owner-word did not open the top tier (exit {code})")
        # R6: keys outside the schema are stripped and printed.
        t.write_text(json.dumps({"schema": 1, "mode": "pace", "parallel_split": {"evolution": 12}}), encoding="utf-8")
        code, out, err = turbo(["--mode", "pace", "--dry-run"])
        dd = json.loads(out) if code == 0 else {}
        if code != 0 or "parallel_split" in dd or "parallel_split" not in err:
            problems.append(f"R6: an unknown key was not dropped and named (exit {code}; stderr {err[:160]!r})")
        # R7: stop_bands.stop above 95 is refused; a slow band above the stop band too.
        t.write_text(json.dumps({"schema": 1, "mode": "pace", "stop_bands": {"slow": 85, "stop": 97}}), encoding="utf-8")
        code, out, _ = turbo(["--mode", "pace", "--dry-run"])
        if code != 2 or "95" not in out:
            problems.append(f"R7: a kept stop band of 97 was accepted (exit {code}: {out[:160]})")
        code, out, _ = turbo(["--mode", "pace", "--stop-band", "95", "--dry-run"])
        dd = json.loads(out) if code == 0 else {}
        if (dd.get("stop_bands") or {}).get("stop") != 95:
            problems.append(f"R7 control: --stop-band 95 did not repair the file (exit {code}: {out[:160]})")
        code, _, _ = turbo(["--mode", "pace", "--stop-band", "90", "--slow-band", "92", "--dry-run"])
        if code != 2:
            problems.append(f"R7: a slow band above the stop band was accepted (exit {code})")
        # R8: the writer stamps the file with its id and a content hash.
        code, out, _ = turbo(["--mode", "pace", "--stop-band", "95", "--dry-run"])
        dd = json.loads(out) if code == 0 else {}
        if dd.get("writer") != WRITER_ID or dd.get(STAMP_KEY) != content_hash(dd):
            problems.append(f"R8: the file carries no valid writer stamp ({dd.get('writer')!r}, {dd.get(STAMP_KEY)!r})")
        dd["parallel_ceiling"] = 12
        if dd.get(STAMP_KEY) == content_hash(dd):
            problems.append("R8: a hand edit did not change the content hash")
        # R9 (RV-SKILLS-WF F10): entering turbo with no --parallel drops a pace file's number, so the
        # documented `--mode turbo --ttl 2h` is rig-aware turbo (12) and not a stale 2 the guard reads
        # as 6. A renewal keeps the user's own lower number.
        t.write_text(json.dumps({"schema": 1, "mode": "pace", "parallel_ceiling": 2}), encoding="utf-8")
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h"])
        d = load(t)
        if code != 0 or d.get("mode") != "turbo" or "parallel_ceiling" in d:
            problems.append(f"R9: turbo entry kept the pace file's parallel_ceiling {d.get('parallel_ceiling')!r} "
                            f"(exit {code}: {out[:160]})")
        t.unlink(missing_ok=True)
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--parallel", "3"])
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--landed", "1", "--owner-reading", "40"],
                             now_=day + 600)
        d = load(t)
        if code != 0 or d.get("parallel_ceiling") != 3:
            problems.append(f"R9 control: a turbo renewal dropped the user's lower number 3 ({d.get('parallel_ceiling')!r}, "
                            f"exit {code}: {out[:160]})")
        # R10 (F16): the turbo answer is "rig-aware, or a lower number": n <= 6. Other modes keep 0..12.
        t.unlink(missing_ok=True)
        code, out, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--parallel", "8", "--dry-run"])
        if code != 2 or "6" not in out:
            problems.append(f"R10: a turbo --parallel 8 was accepted (exit {code}: {out[:160]})")
        code, _, _ = turbo(["--mode", "turbo", "--ttl", "2h", "--parallel", "6", "--dry-run"])
        if code != 0:
            problems.append(f"R10 control: a turbo --parallel 6 was refused (exit {code})")
        code, _, _ = turbo(["--mode", "pace", "--ttl", "2h", "--parallel", "8", "--dry-run"])
        if code != 0:
            problems.append(f"R10 control: a pace --parallel 8 was refused (exit {code})")
    if problems:
        for p in problems:
            print(f"DISPATCH_BUDGET_WRITE SELFTEST FAIL: {p}")
        return 2
    print("dispatch_budget_write selftest: OK (clock stamps, ttl expiry, kept fields, two typed-stamp "
          "refusals, target/owner-reading/lane-rate fields, dry run, 9 refused inputs; the rig-aware "
          "turbo, owner 2026-10-20: R1 no --parallel none, R2 turbo ttl at most 2h, R3 never past "
          "22:00 user-local or inside Overnight without the user's night order, R4 renewal needs "
          "--landed and a reading under 15 min and two 0-landed checks drop to normal, R5 the top "
          "tier opens only on --top-open --owner-word, R6 unknown keys dropped and named, R7 stop "
          "band above 95 refused, R8 writer id and content hash; RV-SKILLS-WF: R9 turbo entry drops a kept "
          "number and a renewal keeps the user's, R10 a turbo number at most 6; each with its control)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    code, msg = run(sys.argv[1:])
    print(msg, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
