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

Run `python dispatch_gate.py --selftest` to check the patterns file compiles,
that the samples discriminate, that the flag it writes is one the guard can
read, and that the hook still exits 0 on every broken input it can be handed.
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
        'PS C:\\Users\\owner> Copy-Item "V:\\Projects\\github\\revenantworks\\claude-skills\\.claude'
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

    # Pattern NUMBERS, never pattern text: this line gets pasted back into chat,
    # and echoing a trigger word here is exactly how observation 0079 happened.
    # The line is then held to its own rule before it is printed.
    success = (
        f"dispatch_gate selftest: OK ({len(patterns)} pattern(s) armed; positive samples matched "
        f"pattern #{patterns.index(hit) + 1 if hit in patterns else '?'} and "
        f"#{patterns.index(hit2) + 1 if hit2 in patterns else '?'} (the second is observation "
        f"0016's real prompt); the negative sample and a pasted terminal session matched nothing; "
        f"flag readable by the guard, session-less prompts write the sentinel; exits 0 on "
        f"{broken_input_cases} broken-input cases and still fires past an uncompilable pattern)"
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
        if hit:
            write_flag(session_id)
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": ADDITIONAL_CONTEXT.format(pattern=hit),
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
