#!/usr/bin/env python3
"""usage_windows.py — statusLine command for revenantworks-foundation-dispatchwright.

Wired in settings.json as the `statusLine.command`. Claude Code runs it on
every status refresh and hands it the statusline JSON on stdin — the ONLY
place the harness publishes the subscription usage windows (verified against
code.claude.com/docs/en/statusline.md, 2026-09-17): `rate_limits.five_hour`
and `rate_limits.seven_day`, each `{used_percentage, resets_at}` (percent 0-100,
Unix epoch seconds), present for claude.ai Pro/Max only, only after the
session's first API response, and dropped once a window's `resets_at` passes.
Hooks receive no rate-limit field and the model has no surface of its own, so
this script is the bridge: it writes what it was handed to a file the plan turn
and the two dispatch hooks can read.

Two jobs, in order:

  1. When the payload carries at least one rate-limit window, write
     `~/.claude/usage-windows.json` ATOMICALLY (temp file in the same directory,
     then os.replace) with the schema references/window-fit.md states:
       {"written_at": <epoch seconds>,
        "model": {"id": ..., "display_name": ...},
        "five_hour": {"used_percentage": ..., "resets_at": ...} | null,
        "seven_day": {...} | null,
        "spend_limit": {...} | null}
     A payload with NO window (before the first API response, or an API-key
     session) leaves the file alone: several sessions refresh the same file and
     a windowless refresh must not blank a good reading from another one.
  2. Print ONE compact line for the status bar:
       <model display name> | ctx <n>% | 5h <n>% (resets HH:MM) | 7d <n>% (resets Day HH:MM)
     Absent fields print nothing rather than a placeholder — a session before
     its first response shows only the model name. Reset times are local.

NEVER CRASHES, and that is the one property this script must keep: a
traceback here blanks the owner's status bar. Every step is wrapped; on any
fault it prints whatever it had assembled so far (or nothing) and exits 0.
The file write is best-effort — an unwritable home directory costs the file,
never the line.

Overrides, for tests and for a rig that keeps the file elsewhere:
  CLAUDE_USAGE_WINDOWS   path of the file to write (default ~/.claude/usage-windows.json)
  --out PATH             same, on argv; argv wins over the environment. A relative
                         PATH whose parent directory does not exist under the cwd
                         but does exist beside this script resolves there, so a
                         controls file can say `fixtures/window-fit/<name>` (the
                         same rule dispatch_gate.py's _argv_path applies) and the
                         controls never write the live file.

Run `python usage_windows.py --selftest` to check the real main() against the
documented statusline shape, a windowless payload, broken stdin, an unwritable
path, and the atomic write. Stdlib only.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_PATH = Path.home() / ".claude" / "usage-windows.json"
HOOKS_DIR = Path(__file__).resolve().parent
WINDOW_KEYS = ("five_hour", "seven_day", "spend_limit")


def out_path(argv: list[str] | None = None) -> Path:
    argv = sys.argv[1:] if argv is None else argv
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 < len(argv):
            p = Path(argv[i + 1])
            if not p.is_absolute() and not p.parent.is_dir() and (HOOKS_DIR / p).parent.is_dir():
                return HOOKS_DIR / p
            return p
    override = os.environ.get("CLAUDE_USAGE_WINDOWS")
    return Path(override) if override else DEFAULT_PATH


def _num(v):
    """A number or None. Booleans are not numbers here."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def _window(obj) -> dict | None:
    """{used_percentage, resets_at} with numeric fields, or None when the
    window is absent or carries no usable percent."""
    if not isinstance(obj, dict):
        return None
    pct = _num(obj.get("used_percentage"))
    if pct is None:
        return None
    return {"used_percentage": pct, "resets_at": _num(obj.get("resets_at"))}


def extract(data: dict) -> dict:
    """The file's content, from a statusline payload. Missing keys read as
    absent, never as an error."""
    model = data.get("model") if isinstance(data.get("model"), dict) else {}
    rate = data.get("rate_limits") if isinstance(data.get("rate_limits"), dict) else {}
    ctx = data.get("context_window") if isinstance(data.get("context_window"), dict) else {}
    return {
        "written_at": int(time.time()),
        "model": {
            "id": model.get("id") if isinstance(model.get("id"), str) else None,
            "display_name": model.get("display_name") if isinstance(model.get("display_name"), str) else None,
        },
        "context_used_percentage": _num(ctx.get("used_percentage")),
        "five_hour": _window(rate.get("five_hour")),
        "seven_day": _window(rate.get("seven_day")),
        "spend_limit": _window(rate.get("spend_limit")),
    }


def has_window(record: dict) -> bool:
    return any(record.get(k) for k in WINDOW_KEYS)


def write_atomic(path: Path, record: dict) -> bool:
    """Temp file beside the target, then os.replace — a reader never sees a
    half-written file. Returns False (and writes nothing) on any fault."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".usage-windows-", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(record, fh)
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
        return True
    except Exception:
        return False


def _pct(v) -> str:
    return f"{v:.0f}%" if float(v).is_integer() else f"{v:.1f}%"


def _local(ts, fmt: str) -> str:
    try:
        return time.strftime(fmt, time.localtime(float(ts)))
    except Exception:
        return ""


def status_line(record: dict) -> str:
    """One line; every segment optional; nothing is a placeholder."""
    parts = []
    name = (record.get("model") or {}).get("display_name")
    if name:
        parts.append(str(name))
    ctx = record.get("context_used_percentage")
    if ctx is not None:
        parts.append(f"ctx {_pct(ctx)}")
    five = record.get("five_hour")
    if five:
        seg = f"5h {_pct(five['used_percentage'])}"
        when = _local(five.get("resets_at"), "%H:%M") if five.get("resets_at") is not None else ""
        if when:
            seg += f" (resets {when})"
        parts.append(seg)
    week = record.get("seven_day")
    if week:
        seg = f"7d {_pct(week['used_percentage'])}"
        when = _local(week.get("resets_at"), "%a %H:%M") if week.get("resets_at") is not None else ""
        if when:
            seg += f" (resets {when})"
        parts.append(seg)
    spend = record.get("spend_limit")
    if spend:
        parts.append(f"spend {_pct(spend['used_percentage'])}")
    return " | ".join(parts)


# The documented statusline payload (code.claude.com/docs/en/statusline.md,
# read 2026-09-17), trimmed to the keys this script reads plus the ones around
# them. This is the positive control's shape; the values are the docs' own.
DOCUMENTED_PAYLOAD = {
    "cwd": "/current/working/directory",
    "session_id": "abc123...",
    "model": {"id": "claude-opus-5", "display_name": "Opus"},
    "workspace": {"current_dir": "/current/working/directory", "project_dir": "/original/project/directory"},
    "version": "2.1.90",
    "cost": {"total_cost_usd": 0.01234, "total_duration_ms": 45000},
    "context_window": {
        "total_input_tokens": 15500, "total_output_tokens": 1200, "context_window_size": 200000,
        "used_percentage": 8, "remaining_percentage": 92,
    },
    "rate_limits": {
        "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
        "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
        "spend_limit": {"used_percentage": 62.8, "resets_at": 1740787200},
    },
}


def _run(payload, out: Path, env_extra: dict | None = None) -> tuple[int, str]:
    """The real script in a subprocess: exit code and stdout are the contract."""
    env = dict(os.environ)
    env.pop("CLAUDE_USAGE_WINDOWS", None)
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--out", str(out)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout


def selftest() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        out = tmp / "usage-windows.json"

        # --- the documented shape writes the file and prints the line ---------
        code, line = _run(DOCUMENTED_PAYLOAD, out)
        if code != 0:
            problems.append(f"the documented payload exited {code}; must be 0")
        if not out.exists():
            problems.append("the documented payload wrote no file")
        else:
            rec = json.loads(out.read_text(encoding="utf-8"))
            for key in ("written_at", "model", "five_hour", "seven_day", "spend_limit"):
                if key not in rec:
                    problems.append(f"the file lacks {key!r}")
            if abs(time.time() - rec.get("written_at", 0)) > 60:
                problems.append("written_at is not now")
            if rec.get("five_hour", {}).get("used_percentage") != 23.5 or rec.get("five_hour", {}).get("resets_at") != 1738425600:
                problems.append(f"five_hour not carried through: {rec.get('five_hour')!r}")
            if rec.get("seven_day", {}).get("used_percentage") != 41.2:
                problems.append(f"seven_day not carried through: {rec.get('seven_day')!r}")
            if rec.get("model", {}).get("display_name") != "Opus" or rec.get("model", {}).get("id") != "claude-opus-5":
                problems.append(f"model not carried through: {rec.get('model')!r}")
        for want in ("Opus", "ctx 8%", "5h 23.5%", "7d 41.2%", "resets "):
            if want not in line:
                problems.append(f"the status line lacks {want!r}: {line!r}")
        if "\n" in line.strip():
            problems.append("the status line is more than one line")
        leftovers = [p.name for p in tmp.iterdir() if p.name.startswith(".usage-windows-")]
        if leftovers:
            problems.append(f"temp files left behind by the atomic write: {leftovers}")

        # --- a windowless payload leaves the file alone and prints the model only ---
        before = out.read_bytes() if out.exists() else b""
        windowless = {"model": {"id": "claude-sonnet-5", "display_name": "Sonnet"},
                      "context_window": {"used_percentage": None}}
        code, line = _run(windowless, out)
        if code != 0:
            problems.append(f"a windowless payload exited {code}; must be 0")
        if out.read_bytes() != before:
            problems.append("a windowless refresh overwrote a good reading; it must leave the file alone")
        if line.strip() != "Sonnet":
            problems.append(f"a windowless payload should print only the model name, got {line!r}")

        # --- absent fields print nothing, never a placeholder -----------------
        bare = {"rate_limits": {"five_hour": {"used_percentage": 50}}}
        code, line = _run(bare, tmp / "bare.json")
        if code != 0:
            problems.append(f"a payload with only one window exited {code}")
        if line.strip() != "5h 50%":
            problems.append(f"expected exactly '5h 50%' for a bare five_hour, got {line!r}")
        for bad in ("None", "null", "?", "n/a", "--"):
            if bad in line:
                problems.append(f"placeholder {bad!r} printed for an absent field: {line!r}")

        # --- never crashes ---------------------------------------------------
        blocker = tmp / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        cases = [
            ("unparseable stdin", "{not json", tmp / "x.json", {}),
            ("empty stdin", "", tmp / "x.json", {}),
            ("stdin that is not an object", "[1, 2]", tmp / "x.json", {}),
            ("rate_limits that is not an object", {"model": {"display_name": "Opus"}, "rate_limits": "nope"}, tmp / "x.json", {}),
            ("a window with junk fields", {"rate_limits": {"five_hour": {"used_percentage": "lots", "resets_at": "soon"}}}, tmp / "x.json", {}),
            ("an unwritable output path", DOCUMENTED_PAYLOAD, blocker / "usage-windows.json", {}),
        ]
        for label, payload, path, extra in cases:
            try:
                code, line = _run(payload, path, extra)
            except Exception as e:
                problems.append(f"the selftest could not run the {label} case: {e}")
                continue
            if code != 0:
                problems.append(f"{label}: exited {code}; this script must never fail the status bar")
        # The unwritable path still prints the line: the write is best-effort.
        code, line = _run(DOCUMENTED_PAYLOAD, blocker / "usage-windows.json")
        if "5h 23.5%" not in line:
            problems.append(f"an unwritable path cost the status line, not only the file: {line!r}")

        # --- the environment override is honoured when argv gives no --out -----
        env_out = tmp / "env.json"
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=json.dumps(DOCUMENTED_PAYLOAD), capture_output=True, text=True,
            env={**os.environ, "CLAUDE_USAGE_WINDOWS": str(env_out)},
        )
        if proc.returncode != 0 or not env_out.exists():
            problems.append("CLAUDE_USAGE_WINDOWS was not honoured")

        # --- a relative --out resolves beside the hook when its parent lives only there ---
        rel = Path("fixtures") / "window-fit" / ".selftest-usage-windows.json"
        beside = HOOKS_DIR / rel
        if (HOOKS_DIR / "fixtures" / "window-fit").is_dir():
            try:
                if beside.exists():
                    beside.unlink()
                proc = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--out", str(rel)],
                    input=json.dumps(DOCUMENTED_PAYLOAD), capture_output=True, text=True,
                    cwd=td, env={k: v for k, v in os.environ.items() if k != "CLAUDE_USAGE_WINDOWS"},
                )
                if proc.returncode != 0 or not beside.exists():
                    problems.append("a relative --out with no such parent under the cwd did not resolve beside the hook")
                if (Path(td) / rel).exists():
                    problems.append("a relative --out was written under the cwd instead of beside the hook")
            finally:
                if beside.exists():
                    beside.unlink()

    if problems:
        for p in problems:
            print(f"USAGE_WINDOWS SELFTEST FAIL: {p}")
        return 2
    print(
        "usage_windows selftest: OK (the documented statusline shape writes the file atomically "
        "and prints model | ctx | 5h | 7d; a windowless refresh leaves the file alone; absent "
        "fields print nothing; exits 0 on 6 broken-input cases; env override honoured; a "
        "relative --out resolves beside the hook)"
    )
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    line = ""
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return 0
        record = extract(data)
        line = status_line(record)
        if has_window(record):
            write_atomic(out_path(), record)
    except Exception:
        pass
    finally:
        try:
            if line:
                print(line)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
