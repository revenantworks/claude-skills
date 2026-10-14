#!/usr/bin/env python3
"""dispatch_gate.py — UserPromptSubmit hook for revenantworks-foundation-dispatchwright.

Wired in settings.json as a UserPromptSubmit hook. Reads the hook JSON on stdin
(Claude Code's `{session_id, prompt, cwd, ...}` payload), tests the prompt's text
against the regexes in the sibling file `dispatch_patterns.txt` (one pattern per
line, `re.search`, case-insensitive), and on a match:

  1. Prints one JSON object to stdout carrying `hookSpecificOutput.additionalContext`
     — a note telling the model this turn looks like a fan-out and that
     dispatchwright's target table (tier, model, effort, surface per unit) must be
     produced before any Task/Agent/Workflow call.
  2. Writes a mode-flag file at `~/.claude/dispatch-mode.json` carrying the
     session id and a timestamp. `dispatch_ledger_guard.py` (the paired
     PreToolUse hook) reads this flag to decide whether to enforce the ledger
     requirement on a later Task/Agent/Workflow call in the SAME session.

FAILS OPEN, always, and that is not negotiable. This hook only ever adds context
or writes a small flag file; it never blocks a prompt. Any exception anywhere in
the body is caught and the process exits 0 with no output, so a broken matcher,
a missing patterns file, or an unwritable home directory never blocks an
ordinary turn. It runs on EVERY prompt, and a gate that can block is how the
2026-08-18 incident locked the owner out of a whole session. The guard is the
opposite by design: it fails closed, and only on Task/Agent/Workflow.

Session id and the guard (the 2026-08-18 D1 fix). When the payload carries no
session id this hook writes the sentinel `unknown-session`. The guard reads that
sentinel as "this flag cannot be correlated" and enforces the ledger check
instead of skipping it, rather than handing a session-less dispatch a free pass.
Changing the sentinel here without changing UNCORRELATABLE_SESSION_IDS in the
guard reopens that hole; the selftest below pins the string for that reason.

The usage windows (added 2026-09-17, dispatchwright 1.3.0, pacewright's references/window-fit.md).
The plan turn must fit its wave table into the subscription windows, and only
a statusLine command ever sees those numbers -- usage_windows.py (the sibling
statusline script) writes them to `~/.claude/usage-windows.json` on every
refresh. When this gate fires it appends ONE more line to additionalContext:
the windows and the calibration state when that file is under 15 minutes old,
or a line saying the plan must ask the owner when the file is absent, stale,
or unreadable. It never guesses a number and never blocks on one -- the line
is data for the plan turn, nothing more, and any fault in reading it produces
the must-ask line rather than an exception. `--windows-file PATH` and
`--calibration-file PATH` on argv read fixture files instead of the live ones
and skip the freshness check (a controls runner can hand a file, not a
timestamp); CLAUDE_USAGE_WINDOWS / CLAUDE_USAGE_CALIBRATION override the live
paths with the freshness check kept, for --selftest.

Run `python dispatch_gate.py --selftest` to check the patterns file compiles,
that the samples discriminate, that the flag it writes is one the guard can
read, that the windows line reads a fresh file and asks on a stale or absent
one, and that the hook still exits 0 on every broken input it can be handed.
Stdlib only.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent

# The sentinel written when the payload has no session id. The guard keys on
# this exact string; keep the two in step.
UNKNOWN_SESSION = "unknown-session"

ADDITIONAL_CONTEXT = (
    "dispatchwright gate: this prompt matched a fan-out pattern ({pattern!r}). "
    "Before any Task/Agent/Workflow call this turn, run dispatchwright's Shape "
    "check first (is this really a fan-out, or does the main conversation / one "
    "subagent / a skill do it cheaper?). If it is a fan-out: decompose into units, "
    "tier each one from dispatchwright's own tier table (references/tier-routing.md), "
    "and write a ledger row -- model, effort, surface -- for every unit "
    "BEFORE dispatching it. See revenantworks-foundation-dispatchwright."
)


def patterns_path() -> Path:
    """CLAUDE_DISPATCH_PATTERNS exists so --selftest can point the real main()
    at a temp patterns file without touching the installed one."""
    override = os.environ.get("CLAUDE_DISPATCH_PATTERNS")
    return Path(override) if override else HOOKS_DIR / "dispatch_patterns.txt"


def flag_path() -> Path:
    """Must match dispatch_ledger_guard.flag_path(), including the override."""
    override = os.environ.get("CLAUDE_DISPATCH_FLAG")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "dispatch-mode.json"


def load_patterns() -> list[str]:
    """One regex per line; blank lines and '#' comments ignored."""
    out = []
    for line in patterns_path().read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


# A shell prompt line: PowerShell (`PS ` then a location then `>`), bash/zsh
# (`user@host:~$`), or a bare `$ `. Used only to find the edges of a pasted
# terminal session.
_SHELL_PROMPT = re.compile(r"^\s*(?:PS [^\n>]*>|[\w.-]+@[\w.-]+:[^\n$#]*[$#]|\$ )")


def strip_pasted_terminal(prompt: str) -> str:
    """The prompt with any pasted terminal session removed (observation 0079).

    Owners paste command output back into chat all the time, and output can
    quote this hook's own trigger words -- its selftest success line once did,
    so pasting the proof that the gate worked tripped the gate. Pasted output
    is data, not a request.

    Only the span from the FIRST shell-prompt line to the LAST is dropped, and
    only when there are at least two: text typed before or after the paste is
    still the owner's own words and is still matched. That asymmetry is on
    purpose -- a missed fan-out (observation 0016) costs far more than a stray
    advisory note, so the strip takes only what is unmistakably a transcript.
    """
    lines = prompt.splitlines()
    edges = [i for i, line in enumerate(lines) if _SHELL_PROMPT.match(line)]
    if len(edges) < 2:
        return prompt
    return "\n".join(lines[: edges[0]] + lines[edges[-1] + 1:])


def first_match(prompt: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        try:
            if re.search(pat, prompt, re.I):
                return pat
        except re.error:
            # One bad line must not disarm every pattern after it.
            continue
    return None


def write_flag(session_id: str) -> None:
    path = flag_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id or UNKNOWN_SESSION,
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "written_by": "dispatch_gate.py",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Usage windows (dispatchwright 1.3.0). Duplicated in dispatch_ledger_guard.py
# on purpose: each hook installs alone into ~/.claude/hooks/ and imports nothing
# beside itself.
# ---------------------------------------------------------------------------
WINDOWS_STALE_SECONDS = 15 * 60
WINDOWS_CLOCK_SKEW_SECONDS = 5 * 60
WINDOW_LABELS = (("five_hour", "5h"), ("seven_day", "7d"))


def _argv_path(flag: str) -> Path | None:
    """A fixture path from argv. A relative path that does not exist under the
    cwd is resolved against this hook's own directory, so a controls file can
    say `fixtures/window-fit/<name>` and never an absolute local path (the
    repo's test_release_paths forbids those in tracked files); the fixtures
    are installed beside the hooks for the same reason."""
    argv = sys.argv[1:]
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            p = Path(argv[i + 1])
            if not p.is_absolute() and not p.exists() and (HOOKS_DIR / p).exists():
                return HOOKS_DIR / p
            return p
    return None


def windows_path() -> Path:
    override = os.environ.get("CLAUDE_USAGE_WINDOWS")
    return Path(override) if override else Path.home() / ".claude" / "usage-windows.json"


def calibration_path() -> Path:
    override = os.environ.get("CLAUDE_USAGE_CALIBRATION")
    return Path(override) if override else Path.home() / ".dispatch" / "usage-calibration.json"


def read_windows(path: Path, fixture: bool = False) -> dict | None:
    """The windows file as a dict, or None when absent, unreadable, not an
    object, or (unless fixture) older than WINDOWS_STALE_SECONDS."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if fixture:
        return data
    ts = data.get("written_at")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    age = time.time() - ts
    if not (-WINDOWS_CLOCK_SKEW_SECONDS <= age <= WINDOWS_STALE_SECONDS):
        return None
    return data


def read_calibration(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def calibration_state(cal: dict | None, key: str) -> str:
    """'no calibration', 'one data point (N tokens/%)' or 'K samples (N tokens/%)'."""
    entry = ((cal or {}).get("windows") or {}).get(key) if isinstance((cal or {}).get("windows"), dict) else None
    if not isinstance(entry, dict):
        return "no calibration"
    tpp = entry.get("tokens_per_percent")
    samples = entry.get("samples")
    if isinstance(tpp, bool) or not isinstance(tpp, (int, float)) or tpp <= 0:
        return "no calibration"
    if not isinstance(samples, int) or samples < 1:
        return "no calibration"
    if samples == 1:
        return f"one data point ({int(tpp)} tokens/%)"
    return f"{samples} samples ({int(tpp)} tokens/%)"


def _local(ts, fmt: str) -> str:
    try:
        return time.strftime(fmt, time.localtime(float(ts)))
    except Exception:
        return ""


def windows_line(windows: dict | None, cal: dict | None, path: Path) -> str:
    """The one line the plan turn reads. Never raises."""
    try:
        if windows is None:
            return (
                f"dispatchwright windows: no fresh reading ({path} absent, unreadable, or older "
                f"than {WINDOWS_STALE_SECONDS // 60} min) -- the plan must ASK the owner, one line, "
                "for percent used and reset time for the 5-hour and 7-day windows, and any "
                "per-model window they track, before fitting the table. Never guess a window."
            )
        segs = []
        for key, label in WINDOW_LABELS:
            w = windows.get(key)
            if isinstance(w, dict) and isinstance(w.get("used_percentage"), (int, float)):
                seg = f"{label} {w['used_percentage']}% used"
                when = _local(w.get("resets_at"), "%H:%M" if key == "five_hour" else "%a %H:%M")
                if when:
                    seg += f", resets {when}"
                seg += f"; calibration {calibration_state(cal, key)}"
                segs.append(seg)
            else:
                segs.append(f"{label} not in the reading")
        read_at = _local(windows.get("written_at"), "%H:%M")
        return (
            f"dispatchwright windows (read {read_at} from {path}): " + " · ".join(segs) +
            ". Fill the plan table's window column from these through pacewright's references/window-fit.md; "
            "'no calibration' means ask the owner for that window's allowance in tokens; ask "
            "only for a per-model window the owner tracks by hand."
        )
    except Exception:
        return (
            "dispatchwright windows: the reading could not be interpreted -- the plan must ASK "
            "the owner for percent used and reset time per window before fitting the table."
        )


RESET_EVE_HOURS = 48       # the 7-day window resets within this many hours
RESET_EVE_AIM = 100.0      # owner 2026-10-01: unused weekly allowance is lost; a cut-off at 100% is fine
RESET_EVE_CATCHUP_HOURS = 6  # back on pace within this many hours of reset eve starting
# Weekly points one lane burns per hour. A DEFAULT, not a measurement on this machine: pacewright's
# budget file `lane_pt_per_hour` (from the owner's dated lane-rate table in the local overlay)
# replaces it, and DISPATCH_PT_PER_LANE_HOUR overrides it for a test. The value is the Opus
# build-lane example row in pacewright's references/accounting.md; every printed line that uses it
# says "default", so nobody reads it as this rig's rate (K8a, audit K7-2-23).
DEFAULT_PT_PER_LANE_HOUR = float(os.environ.get("DISPATCH_PT_PER_LANE_HOUR", "0.22"))
LANE_RATE_SOURCE = ("default, not a measurement: pacewright accounting.md example row; "
                    "set lane_pt_per_hour in the budget file")
DEFAULT_CEILING = 6


def _iso(ts) -> float | None:
    """Epoch seconds from `YYYY-MM-DDTHH:MM:SSZ`, else None."""
    if not isinstance(ts, str):
        return None
    try:
        from datetime import datetime, timezone
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


def read_budget(now: float | None = None, path: Path | None = None) -> dict | None:
    """pacewright's budget decision file while unexpired, else None. Never raises."""
    try:
        if path is None:
            override = os.environ.get("DISPATCH_BUDGET_FILE")
            path = Path(override) if override else Path.home() / ".dispatch" / "budget-decision.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        exp = _iso(d.get("expires_at")) if isinstance(d, dict) else None
        if exp is None or exp <= (time.time() if now is None else now):
            return None
        return d
    except Exception:
        return None


def _num(v) -> float | None:
    return None if isinstance(v, bool) or not isinstance(v, (int, float)) else float(v)


def reset_eve_line(windows: dict | None, now: float | None = None, budget: dict | None = None) -> str:
    """On reset eve, the fill target as a line; '' otherwise. Printed on EVERY
    prompt, not only a fan-out one: twice (2026-10-01, 2026-10-06) reset eve was
    a mode label and a prose rule, and the lanes stayed light. Observation 0350:
    the line reads the owner's target (`target_pct` by `target_at`), the file's
    real ceiling and the newest reading, with its age. Never raises."""
    try:
        now = time.time() if now is None else now
        w = (windows or {}).get("seven_day")
        if not isinstance(w, dict):
            return ""
        used, resets = _num(w.get("used_percentage")), _num(w.get("resets_at"))
        if used is None or resets is None:
            return ""
        b = budget if isinstance(budget, dict) else {}
        read_at = _num((windows or {}).get("written_at"))
        # A newer owner reading in the budget file wins over a lagging meter file.
        owner = b.get("owner_reading") if isinstance(b.get("owner_reading"), dict) else {}
        o_pct, o_at = _num(owner.get("weekly_pct")), _iso(owner.get("read_at"))
        if o_pct is not None and o_at is not None and (read_at is None or o_at > read_at):
            used, read_at, src = o_pct, o_at, "owner reading"
        else:
            src = "meter file"
        age = f", read {int((now - read_at) // 60)} min ago from the {src}" if read_at else ""
        ceiling = b.get("parallel_ceiling")
        cap = (f"cap = the budget file parallel_ceiling {ceiling}" if isinstance(ceiling, int)
               and not isinstance(ceiling, bool) else f"cap = {DEFAULT_CEILING} (no unexpired budget file)")
        rate_pl = _num(b.get("lane_pt_per_hour"))
        lane_src = "budget file lane_pt_per_hour" if rate_pl and rate_pl > 0 else LANE_RATE_SOURCE
        rate_pl = rate_pl if rate_pl and rate_pl > 0 else DEFAULT_PT_PER_LANE_HOUR
        hours = (resets - now) / 3600.0
        if not (0 < hours <= RESET_EVE_HOURS):
            return ""
        real = ("REAL WORK ONLY (owner 2026-10-06): each lane must serve a planned row with clear "
                "blockers; never an extra review or filler to burn usage. If nothing real is "
                "unblocked, say so and let the gap stand.")
        t_pct, t_at = _num(b.get("target_pct")), _iso(b.get("target_at"))
        if t_pct is not None and t_at is not None and 0 < t_pct <= 100 and t_at > now:
            # The owner's own goal replaces PACE and the default aim (observation 0350).
            t_hours = (t_at - now) / 3600.0
            when = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(t_at))
            if used >= t_pct:
                return (f"RESET-EVE HOLD (pacewright): 7d {used:g}% used{age}; the owner's target "
                        f"{t_pct:g}% by {when} is met. Launch nothing new to burn usage; {cap}.")
            need = (t_pct - used) / t_hours
            lanes = max(1, int(-(-need // rate_pl)))
            return (f"RESET-EVE FILL (pacewright): 7d {used:g}% used{age}; the owner's target "
                    f"{t_pct:g}% by {when} ({t_hours:.1f} h) needs {need:.2f} pt/h = about {lanes} "
                    f"lanes at ~{rate_pl:g} pt/h each ({lane_src}); {cap}. {real}")
        if used >= RESET_EVE_AIM - 2:
            return ""
        rate = (RESET_EVE_AIM - used) / hours
        # Owner 2026-10-06: once reset eve starts, get back ON or AHEAD of pace first,
        # not just reach the aim by the end. PACE = elapsed share of the 7-day window.
        pace = 100.0 * (1.0 - hours / 168.0)
        gap = used - pace
        catch = ""
        if gap < 0:
            catch_rate = 100.0 / 168.0 + (-gap) / RESET_EVE_CATCHUP_HOURS
            rate = max(rate, catch_rate)
            catch = (f"BEHIND PACE by {-gap:.1f} (PACE {pace:.1f}): catching up within "
                     f"{RESET_EVE_CATCHUP_HOURS} h needs {catch_rate:.2f} pt/h; run at the cap "
                     "until the gap is >= 0, then hold at or above pace. ")
        lanes = max(1, int(-(-rate // rate_pl)))
        if gap >= 0:
            # Owner 2026-10-06: at pace, slow down to match it; do not race past it.
            return (
                f"RESET-EVE HOLD (pacewright): 7d {used:g}% used{age}, resets in {hours:.1f} h; AT/AHEAD OF "
                f"PACE (PACE {pace:.1f}, gap +{gap:.1f}). Hold, do not race: {rate:.2f} pt/h reaches "
                f"{RESET_EVE_AIM:.0f}% at the reset = about {lanes} lane(s) at ~{rate_pl:g} pt/h "
                f"each ({lane_src}). Launch nothing new while the running lanes cover it; {cap}."
            )
        return (
            f"RESET-EVE FILL (pacewright): 7d {used:g}% used{age}, resets in {hours:.1f} h; {catch}aim "
            f"{RESET_EVE_AIM:.0f}% needs {rate:.2f} pt/h = about {lanes} lanes at "
            f"~{rate_pl:g} pt/h each ({lane_src}). Fill to that, not past it ({cap}); re-read the "
            f"meter every tick: overshooting pace is as wrong as lagging it. {real}"
        )
    except Exception:
        return ""


def windows_context() -> str:
    """Fixture paths from argv win; otherwise the live paths with freshness."""
    fixture = _argv_path("--windows-file")
    wpath = fixture or windows_path()
    windows = read_windows(wpath, fixture=fixture is not None)
    cal = read_calibration(_argv_path("--calibration-file") or calibration_path())
    return windows_line(windows, cal, wpath)


def _run_gate(payload, tmp: Path, env_extra: dict | None = None) -> tuple[int, str, Path]:
    """Run this file as the real hook, in a subprocess, against a temp flag and
    a temp patterns file. Asserting on the real exit code is the point: the one
    property this hook must never lose is that it exits 0 no matter what."""
    flag_file = tmp / "flag.json"
    if flag_file.exists():
        flag_file.unlink()
    env = dict(os.environ)
    env["CLAUDE_DISPATCH_FLAG"] = str(flag_file)
    env["CLAUDE_DISPATCH_PATTERNS"] = str(patterns_path())
    # Isolate every case from the live windows file: a fresh reading on the rig
    # must not change what the older cases see.
    env["CLAUDE_USAGE_WINDOWS"] = str(tmp / "no-usage-windows.json")
    env["CLAUDE_USAGE_CALIBRATION"] = str(tmp / "no-usage-calibration.json")
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, flag_file


def selftest() -> int:
    """Exit non-zero if the pattern file is unusable, the two sample prompts
    don't discriminate, the flag written is one the guard cannot use, or the
    hook exits non-zero on any input. Checks the machinery, not live hook I/O:
    the real ~/.claude/dispatch-mode.json is never touched."""
    problems = []
    try:
        patterns = load_patterns()
    except FileNotFoundError:
        print(f"DISPATCH_GATE SELFTEST FAIL: {patterns_path()} not found")
        return 2
    if not patterns:
        problems.append("dispatch_patterns.txt is empty -- the gate would never fire")
    for pat in patterns:
        try:
            re.compile(pat)
        except re.error as e:
            problems.append(f"pattern {pat!r} does not compile: {e}")
    fan_out_sample = "Rebuild the whole estate -- every repo, every skill, sweep all of it."
    ordinary_sample = "Can you fix the typo in the README on line 12?"
    hit = first_match(fan_out_sample, patterns) if patterns else None
    miss = first_match(ordinary_sample, patterns) if patterns else "n/a"
    if not hit:
        problems.append(f"fan-out sample did not match any pattern: {fan_out_sample!r}")
    if miss:
        problems.append(f"ordinary sample matched {miss!r} and should not have: {ordinary_sample!r}")

    # Second positive control, added 2026-09-10 (estate findings
    # dispatch-patterns-miss-reproduced / selftests-pass-but-do-not-cover-the-known-miss /
    # dispatch-gate-patterns-have-no-positive-control-against-a-real-prompt). The
    # ONLY positive control above is a sentence the author wrote to contain the
    # patterns, which can never catch a vocabulary gap -- it is exactly how this
    # gate missed the largest fan-out request this rig has seen (observation 0016).
    # This is that real, verbatim prompt fragment, kept as a standing regression
    # fixture rather than a synthetic example, per the rule that a trigger's test
    # set must sample the requester's distribution, not the author's.
    real_fan_out_sample = (
        "I want to do a complete estate sweep, run that routine but also lets "
        "analyze every skill, project, routine"
    )
    hit2 = first_match(real_fan_out_sample, patterns) if patterns else None
    if not hit2:
        problems.append(
            f"real observed fan-out prompt did not match any pattern (observation 0016 "
            f"regression): {real_fan_out_sample!r}"
        )

    # Third control, added 2026-09-14 (observation 0079): a pasted terminal
    # session. The owner pasted this hook's own --selftest output back into
    # chat; its success line quoted the word the fan-out sample matched, so the
    # proof that the gate worked tripped the gate. This is that real paste,
    # with the account name in the prompt lines replaced by `owner`. Asserted
    # three ways: raw it must still match (or the sample proves nothing about
    # the strip), stripped it must not, and a request typed above the paste
    # must survive the strip.
    pasted_terminal_sample = (
        'PS C:\\Users\\owner> Copy-Item "C:\\path\\to\\claude-skills\\.claude'
        '\\hooks\\dispatch_gate.py" "$HOME\\.claude\\hooks\\dispatch_gate.py"; python '
        '"$HOME\\.claude\\hooks\\dispatch_gate.py" --selftest\n'
        "dispatch_gate selftest: OK (17 pattern(s) armed; fan-out sample matched 'rebuild', real "
        "observed fan-out prompt (observation 0016) matched 'every (skill|plugin|routine|task|hook|"
        "project|repo)', ordinary sample matched nothing; flag readable by the guard, session-less "
        "prompts write the sentinel; exits 0 on all 5 broken-input cases and still fires past an "
        "uncompilable pattern)\n"
        "PS C:\\Users\\owner>"
    )
    if patterns and not first_match(pasted_terminal_sample, patterns):
        problems.append("the pasted-terminal sample no longer contains a trigger word, so it cannot "
                        "prove the strip works; re-capture it")
    pasted_hit = first_match(strip_pasted_terminal(pasted_terminal_sample), patterns) if patterns else None
    if pasted_hit:
        problems.append(f"a pasted terminal session matched {pasted_hit!r}; pasted output is data, "
                        f"not a request (observation 0079)")
    typed_above_paste = "Rebuild the whole estate once you have read this:\n" + pasted_terminal_sample
    if patterns and not first_match(strip_pasted_terminal(typed_above_paste), patterns):
        problems.append("a request typed above a pasted terminal session was stripped with it; only "
                        "the span between the first and last prompt lines may be dropped")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # --- the flag has to be one the guard can act on ------------------
        code, out, flag_file = _run_gate(
            {"session_id": "sess-1", "prompt": fan_out_sample, "cwd": str(tmp)}, tmp
        )
        if code != 0:
            problems.append(f"a matching prompt exited {code}; this hook must always exit 0")
        if not flag_file.exists():
            problems.append("a matching prompt wrote no flag file, so the guard can never arm")
        else:
            flag = json.loads(flag_file.read_text(encoding="utf-8"))
            if flag.get("session_id") != "sess-1":
                problems.append(f"the flag did not record the payload's session id: {flag!r}")
            if not isinstance(flag.get("ts"), (int, float)):
                problems.append("the flag carries no numeric ts, so the guard reads it as stale")
        if "additionalContext" not in out:
            problems.append("a matching prompt printed no additionalContext")

        # D1 pairing: no session id in the payload must still produce a flag
        # carrying the sentinel the guard treats as uncorrelatable. If this
        # wrote an empty session id, or no flag, a session-less fan-out would
        # arm nothing and every Task call that turn would go untiered.
        code, out, flag_file = _run_gate({"prompt": fan_out_sample, "cwd": str(tmp)}, tmp)
        if code != 0:
            problems.append(f"a session-less matching prompt exited {code}; must be 0")
        if not flag_file.exists():
            problems.append("D1: a session-less matching prompt wrote no flag at all")
        else:
            flag = json.loads(flag_file.read_text(encoding="utf-8"))
            if flag.get("session_id") != UNKNOWN_SESSION:
                problems.append(
                    f"D1: a session-less prompt must write the {UNKNOWN_SESSION!r} sentinel the "
                    f"guard keys on, not {flag.get('session_id')!r}"
                )

        # The sentinel is defended twice on purpose -- main() substitutes it and
        # write_flag substitutes it again -- because an empty session id on the
        # flag is a silent hole: the guard would read the flag as belonging to
        # some other session and enforce nothing. Pin both layers, so removing
        # either one is visible here even though the other still covers it.
        direct = tmp / "direct-flag.json"
        os.environ["CLAUDE_DISPATCH_FLAG"] = str(direct)
        try:
            write_flag("")
            if json.loads(direct.read_text(encoding="utf-8")).get("session_id") != UNKNOWN_SESSION:
                problems.append(f"write_flag('') must record the {UNKNOWN_SESSION!r} sentinel")
        finally:
            os.environ.pop("CLAUDE_DISPATCH_FLAG", None)

        # --- an ordinary prompt arms nothing ------------------------------
        code, out, flag_file = _run_gate(
            {"session_id": "sess-1", "prompt": ordinary_sample, "cwd": str(tmp)}, tmp
        )
        if code != 0:
            problems.append(f"an ordinary prompt exited {code}; must be 0")
        if flag_file.exists():
            problems.append("an ordinary prompt armed dispatch mode; it must not")
        if out.strip():
            problems.append(f"an ordinary prompt printed output: {out!r}")

        # --- a pasted terminal session arms nothing, through the real main() ---
        code, out, flag_file = _run_gate(
            {"session_id": "sess-1", "prompt": pasted_terminal_sample, "cwd": str(tmp)}, tmp
        )
        if code != 0:
            problems.append(f"a pasted terminal session exited {code}; must be 0")
        if flag_file.exists() or out.strip():
            problems.append("a pasted terminal session armed dispatch mode through main(); "
                            "strip_pasted_terminal is not wired in")

        # --- fail open on every broken input ------------------------------
        # The bad regex goes FIRST on purpose. With it last, a good pattern
        # earlier in the file matches and re.error never fires, so the case
        # proves nothing -- which is exactly how this fixture read until a
        # mutation test showed it passing against a gate that had no re.error
        # handling at all.
        broken_patterns = tmp / "broken.txt"
        broken_patterns.write_text("[unclosed(\nrebuild\n", encoding="utf-8")
        # A flag path whose parent is a regular file: mkdir throws, which is the
        # real-world shape of an unwritable home directory.
        blocker = tmp / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        fail_open = [
            ("unparseable stdin", "{not json", {}),
            ("empty stdin", "", {}),
            ("stdin that is not an object", "[1, 2, 3]", {}),
            ("a missing patterns file", {"session_id": "s", "prompt": fan_out_sample},
             {"CLAUDE_DISPATCH_PATTERNS": str(tmp / "does-not-exist.txt")}),
            ("an unwritable flag path", {"session_id": "s", "prompt": fan_out_sample},
             {"CLAUDE_DISPATCH_FLAG": str(blocker / "flag.json")}),
        ]
        broken_input_cases = len(fail_open)
        for label, payload, extra in fail_open:
            try:
                code, _, _ = _run_gate(payload, tmp, extra)
            except Exception as e:
                problems.append(f"the selftest itself could not run the {label} case: {e}")
                continue
            if code != 0:
                problems.append(f"{label}: exited {code}. This hook must fail OPEN on every input.")

        # One uncompilable line must not disarm the patterns after it. Exiting 0
        # is not enough here -- a gate that swallows the error and fires nothing
        # also exits 0, and then every fan-out that turn arms no flag and the
        # guard never enforces. So assert the gate still FIRES.
        code, out, flag_file = _run_gate(
            {"session_id": "sess-1", "prompt": fan_out_sample, "cwd": str(tmp)},
            tmp,
            {"CLAUDE_DISPATCH_PATTERNS": str(broken_patterns)},
        )
        if code != 0:
            problems.append(f"a patterns file with a broken regex exited {code}; must be 0")
        if not flag_file.exists() or "additionalContext" not in out:
            problems.append(
                "a broken regex on the first line disarmed the patterns after it: the gate "
                "neither wrote a flag nor added context for a prompt that still matches"
            )

        # --- the usage-windows line (dispatchwright 1.3.0) --------------------
        # The shape is the documented statusline payload as usage_windows.py
        # writes it; only written_at is minted here, the same way the flag's
        # ts is minted above.
        def _windows_file(name: str, written_at: float, five: float = 23.5) -> Path:
            p = tmp / name
            p.write_text(json.dumps({
                "written_at": written_at,
                "model": {"id": "claude-opus-5", "display_name": "Opus"},
                "five_hour": {"used_percentage": five, "resets_at": 1738425600},
                "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
                "spend_limit": None,
            }), encoding="utf-8")
            return p

        fresh_windows = _windows_file("fresh-windows.json", time.time())
        stale_windows = _windows_file("stale-windows.json", time.time() - WINDOWS_STALE_SECONDS - 60)
        corrupt_windows = tmp / "corrupt-windows.json"
        corrupt_windows.write_text("{not json", encoding="utf-8")
        cal_two = tmp / "cal-two.json"
        cal_two.write_text(json.dumps({"windows": {
            "five_hour": {"tokens_per_percent": 41000, "samples": 3},
            "seven_day": {"tokens_per_percent": 250000, "samples": 1},
        }}), encoding="utf-8")
        windows_cases = [
            ("a fresh windows file", {"CLAUDE_USAGE_WINDOWS": str(fresh_windows),
                                      "CLAUDE_USAGE_CALIBRATION": str(cal_two)},
             ("5h 23.5% used", "7d 41.2% used", "3 samples (41000 tokens/%)", "one data point (250000 tokens/%)"),
             ("must ASK",)),
            ("a fresh windows file with no calibration", {"CLAUDE_USAGE_WINDOWS": str(fresh_windows)},
             ("5h 23.5% used", "no calibration"), ("must ASK",)),
            ("a stale windows file", {"CLAUDE_USAGE_WINDOWS": str(stale_windows)},
             ("must ASK",), ("5h 23.5%",)),
            ("an absent windows file", {}, ("must ASK",), ("5h 23.5%",)),
            ("a corrupt windows file", {"CLAUDE_USAGE_WINDOWS": str(corrupt_windows)},
             ("must ASK",), ("5h 23.5%",)),
        ]
        for label, extra, wants, must_nots in windows_cases:
            code, out, flag_file = _run_gate(
                {"session_id": "sess-1", "prompt": fan_out_sample, "cwd": str(tmp)}, tmp, extra
            )
            if code != 0:
                problems.append(f"windows: {label} exited {code}; must be 0")
            if "additionalContext" not in out:
                problems.append(f"windows: {label} lost the base additionalContext")
            for want in wants:
                if want not in out:
                    problems.append(f"windows: {label} -- context lacks {want!r}")
            for must_not in must_nots:
                if must_not in out:
                    problems.append(f"windows: {label} -- context wrongly carries {must_not!r}")
        # Fixture mode on argv skips the freshness check (a controls runner can
        # hand a file but cannot mint a timestamp) and must still exit 0.
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--windows-file", str(stale_windows),
             "--calibration-file", str(cal_two)],
            input=json.dumps({"session_id": "sess-1", "prompt": fan_out_sample, "cwd": str(tmp)}),
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_DISPATCH_FLAG": str(tmp / "argv-flag.json"),
                 "CLAUDE_DISPATCH_PATTERNS": str(patterns_path())},
        )
        if proc.returncode != 0 or "5h 23.5% used" not in proc.stdout:
            problems.append("windows: --windows-file fixture mode did not read the file as current")
        # A windows line must never be a reason to block: an ordinary prompt
        # with a fresh file still arms nothing and prints nothing.
        code, out, flag_file = _run_gate(
            {"session_id": "sess-1", "prompt": ordinary_sample, "cwd": str(tmp)}, tmp,
            {"CLAUDE_USAGE_WINDOWS": str(fresh_windows)},
        )
        if code != 0 or flag_file.exists() or out.strip():
            problems.append("windows: an ordinary prompt with a fresh windows file armed or printed something")

    # --- the reset-eve fill line (2026-10-06) -----------------------------------
    t0 = 1_800_000_000.0
    eve_on = reset_eve_line({"seven_day": {"used_percentage": 69, "resets_at": t0 + 32 * 3600}}, now=t0)
    if "RESET-EVE FILL" not in eve_on or "lanes" not in eve_on:
        problems.append("reset-eve: 69% used with 32 h left printed no fill line")
    if "REAL WORK ONLY" not in eve_on:
        problems.append("reset-eve: the fill line dropped the real-work-only rule")
    if "BEHIND PACE" not in eve_on:
        problems.append("reset-eve: 69% used at PACE ~81 did not say it is behind pace")
    ahead = reset_eve_line({"seven_day": {"used_percentage": 90, "resets_at": t0 + 32 * 3600}}, now=t0)
    if "RESET-EVE HOLD" not in ahead or "BEHIND PACE" in ahead:
        problems.append("reset-eve: 90% used at PACE ~81 should print the HOLD line, not a fill")
    # Observation 0350: the owner's target, the file's ceiling, the reading's age.
    t1 = 1_791_390_240.0  # 2026-10-07 16:24:00Z
    reset1 = t1 + (6 * 3600 + 36 * 60) + 3600  # the reset an hour after the target
    tgt = {"expires_at": "2026-10-07T18:24:00Z", "parallel_ceiling": 7, "target_pct": 98,
           "target_at": "2026-10-07T22:00:00Z"}
    win1 = {"written_at": t1 - 7200, "seven_day": {"used_percentage": 92, "resets_at": reset1}}
    line = reset_eve_line(win1, now=t1, budget=tgt)
    for want in ("target 98% by 2026-10-07 22:00Z", "needs 1.07 pt/h", "parallel_ceiling 7",
                 "read 120 min ago"):
        if want not in line:
            problems.append(f"reset-eve 0350: the target line lacks {want!r}: {line!r}")
    if "PACE" in line or "aim 100%" in line:
        problems.append(f"reset-eve 0350: a set target still printed PACE or the default aim: {line!r}")
    met = reset_eve_line({"seven_day": {"used_percentage": 98, "resets_at": reset1}}, now=t1, budget=tgt)
    if "RESET-EVE HOLD" not in met or "is met" not in met:
        problems.append(f"reset-eve 0350: a met target did not print HOLD: {met!r}")
    newer = {**tgt, "owner_reading": {"weekly_pct": 93, "read_at": "2026-10-07T16:20:00Z"}}
    if "93% used, read 4 min ago from the owner reading" not in reset_eve_line(win1, now=t1, budget=newer):
        problems.append("reset-eve 0350: a newer owner reading did not replace the lagging meter file")
    if "cap = 6 (no unexpired budget file)" not in eve_on:
        problems.append("reset-eve 0350: with no budget file the line does not say the default cap")
    if "lanes at ~0.22 pt/h" not in eve_on or "lanes at ~0.5 pt/h" not in reset_eve_line(
            {"seven_day": {"used_percentage": 69, "resets_at": t0 + 32 * 3600}}, now=t0,
            budget={"lane_pt_per_hour": 0.5}):
        problems.append("reset-eve 0349: the lane rate is not the default or the budget file's")
    if "default, not a measurement" not in eve_on:
        problems.append("reset-eve K8a: the built-in lane rate is not labelled a default")
    with tempfile.TemporaryDirectory() as td:
        bf = Path(td) / "b.json"
        bf.write_text(json.dumps({**tgt, "expires_at": "2026-10-07T16:00:00Z"}), encoding="utf-8")
        if read_budget(now=t1, path=bf) is not None:
            problems.append("reset-eve 0350: an expired budget file was read as current")
        bf.write_text(json.dumps(tgt), encoding="utf-8")
        if (read_budget(now=t1, path=bf) or {}).get("parallel_ceiling") != 7:
            problems.append("reset-eve 0350: an unexpired budget file was not read")
    for case, win in (("far", {"seven_day": {"used_percentage": 50, "resets_at": t0 + 100 * 3600}}),
                      ("past", {"seven_day": {"used_percentage": 50, "resets_at": t0 - 3600}}),
                      ("full", {"seven_day": {"used_percentage": 99, "resets_at": t0 + 3600}}),
                      ("absent", None), ("corrupt", {"seven_day": {"used_percentage": "x"}})):
        if reset_eve_line(win, now=t0):
            problems.append(f"reset-eve: the {case} case printed a fill line")

    # Pattern NUMBERS, never pattern text: this line gets pasted back into chat,
    # and echoing a trigger word here is exactly how observation 0079 happened.
    # The line is then held to its own rule before it is printed.
    success = (
        f"dispatch_gate selftest: OK ({len(patterns)} pattern(s) armed; positive samples matched "
        f"pattern #{patterns.index(hit) + 1 if hit in patterns else '?'} and "
        f"#{patterns.index(hit2) + 1 if hit2 in patterns else '?'} (the second is observation "
        f"0016's real prompt); the negative sample and a pasted terminal session matched nothing; "
        f"flag readable by the guard, session-less prompts write the sentinel; exits 0 on "
        f"{broken_input_cases} broken-input cases and still fires past an uncompilable pattern; "
        f"the usage-windows line reads a fresh file with its calibration state and says the plan "
        f"must ask on {len(windows_cases) - 2} stale/absent/corrupt files, fixture mode on argv "
        f"skips freshness)"
    )
    if patterns and first_match(success, patterns):
        problems.append("the selftest's own success line matches a trigger pattern, so pasting it "
                        "back would trip the gate (observation 0079); reword it")
    if problems:
        for p in problems:
            print(f"DISPATCH_GATE SELFTEST FAIL: {p}")
        return 2
    print(success)
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt") or ""
        session_id = data.get("session_id") or UNKNOWN_SESSION
        if not prompt:
            return 0
        patterns = load_patterns()
        hit = first_match(strip_pasted_terminal(prompt), patterns)
        try:
            eve = reset_eve_line(read_windows(windows_path()), budget=read_budget())
        except Exception:
            eve = ""
        if not hit and eve:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                     "additionalContext": eve}}))
            return 0
        if hit:
            write_flag(session_id)
            try:
                windows = windows_context()
            except Exception:
                windows = ("dispatchwright windows: unreadable -- the plan must ASK the owner for "
                           "percent used and reset time per window before fitting the table.")
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": ADDITIONAL_CONTEXT.format(pattern=hit) + " " + windows
                                         + (" " + eve if eve else ""),
                }
            }
            print(json.dumps(out))
        return 0
    except Exception:
        # Fail open, unconditionally -- a broken matcher must never block an
        # ordinary prompt. No stderr either: UserPromptSubmit has no user
        # reading this hook's own diagnostics.
        return 0


if __name__ == "__main__":
    sys.exit(main())
