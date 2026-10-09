#!/usr/bin/env python3
"""warden_review.py: read gatewarden's event log and set each rule's mode. Stdlib only.

Every hook starts in watch: it logs what it would have stopped and lets the work run. Rules
marked hard (a force or delete push, destroying a VM, going live) are guard in every mode:
no entry moves them, and `set` and `snooze` refuse them (warden audit K7-4-05).
This script is the only thing that moves a rule, and it moves one only on the owner's command.

  python warden_review.py                      # the weekly report (last 7 days)
  python warden_review.py report --days 28
  python warden_review.py set <rule> watch|nudge|guard [--days N]
  python warden_review.py reset <rule>         # back to the shipped default
  python warden_review.py snooze <rule> <days> # watch only, until the date
  python warden_review.py mark <rule> real|noise   # label this week's hits
  python warden_review.py status

A rule is `<hook>` or `<hook>.<rule>` (push_gate.no_ci); a hook entry covers its soft rules.
A watch or nudge entry expires after --days (default 30, at most 90), then the rule returns to
its shipped default; a guard entry does not expire (tightening never lapses into a relaxation).
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

DAY = 86400.0
KNOWN = {
    "push_gate.irreversible": True, "push_gate.unreadable": True, "golive_block": True, "hyperv_lock": True,
    "push_gate.no_intent": False, "push_gate.range": False, "push_gate.head": False,
    "push_gate.no_ci": False, "push_gate.shape": True, "heredoc_guard": False, "heredoc_guard.stdin": True,
    "call_cap": False, "launch_throttle.ceiling": False, "launch_throttle.stop": False,
}
HOOKS = {r.split(".", 1)[0] for r in KNOWN}
SET_DAYS, MAX_DAYS = 30.0, 90.0


def hard_rules_of(name: str) -> list[str]:
    """The hard rules a rule or hook name covers: itself when hard, or a hook's hard rules."""
    return sorted(r for r, h in KNOWN.items() if h and (r == name or r.split(".", 1)[0] == name))


def check_settable(name: str, verb: str) -> str:
    """'' when `set`/`snooze` may write an entry for `name`; else the refusal."""
    if name not in KNOWN and name not in HOOKS:
        return f"{name} is not a gatewarden rule. Known: {', '.join(sorted(KNOWN))}."
    if KNOWN.get(name):
        return (f"{name} is a hard rule: guard in every mode, and no modes entry changes it. "
                f"If the owner wants the act, the owner runs it in their own terminal. Nothing to {verb}.")
    covered = [r for r in KNOWN if r.split(".", 1)[0] == name]
    if name in HOOKS and covered and all(KNOWN[r] for r in covered):
        return f"every rule of {name} is hard: guard in every mode. Nothing to {verb}."
    return ""


def read_events(days: float) -> list[dict]:
    since = time.time() - days * DAY
    rows = []
    for path in (hl.events_path() + ".1", hl.events_path()):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if float(r.get("at", 0)) >= since:
                        rows.append(r)
        except OSError:
            pass
    return rows


def save_modes(cfg: dict) -> None:
    os.makedirs(os.path.dirname(hl.modes_path()) or ".", exist_ok=True)
    cfg.setdefault("default", "watch")
    cfg["updated"] = time.strftime("%Y-%m-%d")
    hl.write_json_atomic(hl.modes_path(), cfg)


def suggest(rule: str, hard: bool, mode: str, rows: list[dict], labels: dict) -> str:
    hits = len(rows)
    sessions = len({r.get("session") for r in rows})
    days = len({time.strftime("%Y-%m-%d", time.localtime(float(r.get("at", 0)))) for r in rows})
    real, noise = int(labels.get("real", 0)), int(labels.get("noise", 0))
    marked = real + noise
    if hard:
        return f"always guard (irreversible or outward); stopped {hits} time(s)" if hits else "always guard"
    if marked and noise / marked >= 0.3 and mode != "watch":
        return f"suggest: set {rule} watch — {noise} of {marked} marked hits were noise"
    if mode == "watch" and hits >= 3 and sessions >= 2 and hits / max(days, 1) <= 5:
        return (f"suggest: set {rule} nudge — it would have stopped {hits} calls in {sessions} sessions; "
                "nudge tells Claude without stopping you")
    if mode == "watch" and hits > 0:
        return f"keep watching ({hits} hit(s); promotion needs 3 in 2 sessions)"
    if mode == "nudge" and real >= 2 and noise == 0:
        return f"suggest: set {rule} guard — you marked {real} hits real and none noise"
    if mode == "nudge" and hits:
        return "keep nudging; mark hits real or noise to decide on guard"
    if mode == "guard" and hits >= 10:
        return f"suggest: set {rule} nudge — it stopped you {hits} times; fix the rule or relax it"
    return ""


def report(days: float) -> str:
    cfg = hl.load_modes()
    labels = cfg.get("labels") if isinstance(cfg.get("labels"), dict) else {}
    rows = read_events(days)
    rules = dict(KNOWN)
    for r in rows:
        rules.setdefault(r.get("rule", "?"), bool(r.get("hard")))
    out = [f"gatewarden — last {days:g} days · modes file: {hl.modes_path()}",
           f"{'rule':26} {'mode':6} {'hits':>4}  suggestion"]
    count = 0
    for rule in sorted(rules):
        hard = rules[rule]
        mode = hl.mode_for(rule, hard)
        mine = [r for r in rows if r.get("rule") == rule]
        s = suggest(rule, hard, mode, mine, labels.get(rule) or {})
        if s.startswith("suggest"):
            count += 1
        out.append(f"{rule:26} {mode:6} {len(mine):>4}  {s}")
    out.append(f"{count} suggestion(s). Apply one with: python warden_review.py set <rule> <mode>")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    verb = argv[0] if argv else "report"
    cfg = hl.load_modes()
    if verb == "report":
        try:
            days = float(argv[argv.index("--days") + 1]) if "--days" in argv else 7.0
        except (IndexError, ValueError):
            days = -1.0
        if not 0 < days <= 3650:
            print("warden_review: report --days must be a number of days above 0.", file=sys.stderr)
            return 2
        print(report(days))
        return 0
    if verb == "status":
        for rule, hard in sorted(KNOWN.items()):
            print(f"{rule:26} {hl.mode_for(rule, hard)}{'  (hard)' if hard else ''}")
        return 0
    if verb == "set" and len(argv) in (3, 5) and argv[2] in hl.MODES and (len(argv) == 3 or argv[3] == "--days"):
        rule, mode = argv[1], argv[2]
        why = check_settable(rule, "set")
        if why:
            print(f"warden_review: {why}", file=sys.stderr)
            return 2
        try:
            days = float(argv[4]) if len(argv) == 5 else SET_DAYS
        except ValueError:
            days = 0.0
        if not 0 < days <= MAX_DAYS:
            print(f"warden_review: --days must be above 0 and at most {MAX_DAYS:g}.", file=sys.stderr)
            return 2
        until = time.time() + days * DAY
        cfg.setdefault("rules", {})[rule] = "guard" if mode == "guard" else {"mode": mode, "until": until}
        save_modes(cfg)
        print(f"{rule} is now {mode}" + ("." if mode == "guard" else
              f" until {time.strftime('%Y-%m-%d %H:%M', time.localtime(until))}; then its shipped default."))
        held = hard_rules_of(rule)
        if held:
            print(f"Hard rules stay guard whatever this entry says: {', '.join(held)}.")
        return 0
    if verb == "reset" and len(argv) == 2:
        (cfg.get("rules") or {}).pop(argv[1], None)
        (cfg.get("snooze") or {}).pop(argv[1], None)
        save_modes(cfg)
        print(f"{argv[1]} is back to its shipped default.")
        return 0
    if verb == "snooze" and len(argv) == 3:
        why = check_settable(argv[1], "snooze")
        if why:
            print(f"warden_review: {why}", file=sys.stderr)
            return 2
        try:
            days = float(argv[2])
        except ValueError:
            days = 0.0
        # Validated before anything is saved (V-K8w F12): `inf` once wrote a snooze that never ended.
        if not 0 < days <= MAX_DAYS:  # NaN and Infinity fail this test too
            print(f"warden_review: snooze days must be above 0 and at most {MAX_DAYS:g}.", file=sys.stderr)
            return 2
        until = time.time() + days * DAY
        cfg.setdefault("snooze", {})[argv[1]] = until
        save_modes(cfg)
        print(f"{argv[1]} watches only until {time.strftime('%Y-%m-%d %H:%M', time.localtime(until))} "
              "(hard rules are never snoozed).")
        return 0
    if verb == "mark" and len(argv) == 3 and argv[2] in ("real", "noise"):
        lab = cfg.setdefault("labels", {}).setdefault(argv[1], {"real": 0, "noise": 0})
        lab[argv[2]] = int(lab.get(argv[2], 0)) + 1
        save_modes(cfg)
        print(f"{argv[1]}: real {lab['real']}, noise {lab['noise']}.")
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
