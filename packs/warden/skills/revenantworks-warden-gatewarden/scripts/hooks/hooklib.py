#!/usr/bin/env python3
"""hooklib.py: shared helpers for gatewarden's PreToolUse hooks. Stdlib only.

Contract every hook keeps (Claude Code hooks reference, read 2026-10-01):
  - the event arrives as JSON on stdin; tool calls inside subagents carry
    `agent_id` and `agent_type`;
  - exit 0 allows; JSON on stdout may add `additionalContext` (for Claude) and
    `systemMessage` (for the person watching);
  - exit 2 blocks the call, and stderr is the reason Claude reads.
A hook never exits 1: Claude Code treats 1 as a non-blocking error, so a crash
would fail open by accident. Each hook states its own fail mode instead.

Modes (owner 2026-10-08: enforcement starts light and is earned by evidence):
  - watch  — the call runs; the would-be block is logged, nobody is interrupted.
  - nudge  — the call runs; Claude reads the reason (additionalContext), you see nothing.
  - guard  — exit 2, as before.
A rule marked hard (irreversible or outward: a force or delete push, destroying a VM,
going live) is guard in every mode: no modes-file entry, snooze or GATEWARDEN_MODE changes
it. Every other rule starts in watch. warden_review.py reads the log and suggests promotions.

Time budget (verifier V-K8w F5): Claude Code reads a hook timeout or crash as allow, so a hard-rule
hook that runs long would fail open. Each hard-rule hook starts `start_budget()`: past BUDGET seconds
(GATEWARDEN_BUDGET, default 20, under the 30 s hook timeout) it stops and refuses when the command, or
a script it read, names what the hook guards, and allows otherwise. Subprocess timeouts shrink to fit.

Copy this file beside the hooks; they import it from their own folder.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SHELL_TOOLS = {"Bash", "PowerShell"}

# Claude Code reads hook output as UTF-8. On Windows Python writes the console code page (cp1252) by
# default, so an em dash printed as `â€”` and a glyph outside cp1252 crashed the write.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# ------------------------------------------------------------ notes (what the person and Claude read)
# One shape for every note and refusal: a header `<glyph> <hook> · <verdict>`, then indented lines:
# free text, aligned `label  value` rows, item lines (commits), and on a refusal one `fix:` line.
GLYPHS = {"cleared": "✓", "refused": "✗", "warning": "!", "nudge": "!", "weekly": "·"}
NOTE_LINES = 8
NOTE_WIDTH = 100
_IMPERATIVE = re.compile(r"^(?:Run|Write|Record|Tell|Print|Split|Use|Hand|Change|Commit|Follow|Give|Put|Pass|"
                         r"Finish|Stop|Read|Launch|Ask|Re-run|Remove|cd|Check)\b")


def clip(text: str, width: int = NOTE_WIDTH) -> str:
    """One line, at most `width` characters, cut at a word boundary with an ellipsis."""
    text = re.sub(r"\s*[\r\n]+\s*", " ", str(text)).strip()
    if len(text) <= width:
        return text
    cut = text[:width - 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > width // 2 else cut).rstrip(" ,;:") + "…"


def note(hook: str, verdict: str, why: str = "", rows=(), items=(), fix: str = "",
         limit: int = NOTE_LINES) -> str:
    """A short, aligned note: at most `limit` lines; items (commit lines) give way first."""
    import textwrap
    head = f"{GLYPHS.get(verdict, '!')} {hook} · {verdict}"
    rows = [(str(k), str(v)) for k, v in rows if str(v).strip()]
    pad = max((len(k) for k, _ in rows), default=0)
    row_lines = [f"  {k.ljust(pad)}  {clip(v, NOTE_WIDTH - pad - 4)}" for k, v in rows]
    fix_lines = [f"  fix: {' '.join(fix.split())}"] if fix else []  # never clipped: it is a command
    why_lines = [f"  {w}" for w in textwrap.wrap(" ".join(why.split()), NOTE_WIDTH - 2,
                                                 break_on_hyphens=False, break_long_words=False)]
    room = limit - 1 - len(row_lines) - len(fix_lines)
    why_lines = why_lines[:max(1, room)] if why_lines else []
    if why_lines and len(textwrap.wrap(" ".join(why.split()), NOTE_WIDTH - 2)) > len(why_lines):
        why_lines[-1] = "  " + clip(why_lines[-1].strip() + " …", NOTE_WIDTH - 2)
    room -= len(why_lines)
    items = [f"  {clip(i, NOTE_WIDTH - 2)}" for i in items]
    if len(items) > max(room, 0):
        keep = max(room - 1, 0)
        items = items[:keep] + [f"  … {len(items) - keep} more"] if room > 0 else []
    return "\n".join([head, *why_lines, *row_lines, *items, *fix_lines])


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;])\s+(?=[A-Z`(])", text.strip()) if s]


def as_note(text: str, verdict: str) -> str:
    """A plain `hook: reason. Fix.` text in the note shape. A text already in it passes unchanged."""
    text = (text or "").strip()
    if not text or text[:1] in GLYPHS.values():
        return text
    m = re.match(r"^([a-z][a-z -]{1,30}?): (.*)$", text, re.S)
    hook, body = (m.group(1), m.group(2)) if m else (hook_name().replace("_", " "), text)
    first, _, rest = body.partition("\n")
    items = [x for x in rest.split("\n") if x.strip()]
    fix = ""
    b = re.search(r"\bBlocked(?: to be safe)?[;.]\s*", first)
    if b:
        after, first = _sentences(first[b.end():]), first[:b.start()].strip()
        if after:
            fix, first = after[0], " ".join([first, *after[1:]]).strip()
    if not fix:
        parts = _sentences(first)
        for k in range(len(parts) - 1, 0, -1):
            if _IMPERATIVE.match(parts[k]):
                fix = parts.pop(k)
                break
        first = " ".join(parts)
    if fix and fix[:1].islower():
        fix = fix[0].upper() + fix[1:]
    return note(hook, verdict, why=first, items=items, fix=fix)


_EVENT: dict = {}


def read_event() -> tuple[dict | None, str]:
    """Return (event or None, raw stdin text). Never raises."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return None, ""
    try:
        ev = json.loads(raw)
        ev = ev if isinstance(ev, dict) else None
    except Exception:
        ev = None
    if ev:
        _EVENT.clear()
        _EVENT.update(ev)
    return ev, raw


def command_of(ev: dict) -> str:
    ti = ev.get("tool_input") or {}
    cmd = ti.get("command") if isinstance(ti, dict) else None
    return cmd if isinstance(cmd, str) else ""


def stood_down(feature: str) -> bool:
    """True when a Revenantworks mod stands in for this hook (RW_MOD_<ID>=1)."""
    return os.environ.get(f"RW_MOD_{feature}") == "1"


MODES = ("watch", "nudge", "guard")
EVENTS_MAX_BYTES = 1_000_000
_SECRETISH = re.compile(r"(?i)(ghp_|gho_|github_pat_|sk-|xox[abp]-|AKIA)[A-Za-z0-9_\-]{6,}|[A-Za-z0-9+/_\-]{32,}|https?://[^\s@]+@")


def hook_name() -> str:
    return os.path.splitext(os.path.basename(sys.argv[0] or "hook"))[0]


def modes_path() -> str:
    return os.environ.get("GATEWARDEN_MODES") or os.path.join(state_dir(), "modes.json")


def events_path() -> str:
    return os.environ.get("GATEWARDEN_EVENTS") or os.path.join(state_dir(), "events.jsonl")


def load_modes() -> dict:
    try:
        cfg = load_json(modes_path())
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def entry_mode(value, now: float) -> str | None:
    """A modes-file rule entry: "watch" (no expiry), or {"mode": m, "until": epoch} (ignored once past)."""
    if isinstance(value, str):
        return value if value in MODES else None
    if isinstance(value, dict) and value.get("mode") in MODES:
        try:
            until = float(value.get("until", 0))
        except (TypeError, ValueError):
            return None
        # A non-finite date (Infinity, NaN in a hand-edited file) never counts as live (V-K8w F12).
        return value["mode"] if math.isfinite(until) and until > now else None
    return None


def mode_for(rule: str, hard: bool = False) -> str:
    """Hard (guard, always), then the per-rule entry, then the per-hook entry, then a live snooze
    (watch), then GATEWARDEN_MODE, then the file's default, then watch.

    A hard rule reads no entry at all (owner 2026-10-08: a force or delete push, a Hyper-V destroy and
    an OBS go-live refuse in every mode). The modes file sits where tools Claude runs can write it, so
    an entry that could relax a hard rule would be a switch Claude could flip (warden audit K7-4-02)."""
    if hard:
        return "guard"
    cfg = load_modes()
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    hook = rule.split(".", 1)[0]
    now = time.time()
    for key in (rule, hook):
        m = entry_mode(rules.get(key), now)
        if m:
            return m
    snooze = cfg.get("snooze") if isinstance(cfg.get("snooze"), dict) else {}
    for key in (rule, hook):
        try:
            until = float(snooze.get(key, 0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(until) and until > now:
            return "watch"
    env = os.environ.get("GATEWARDEN_MODE", "")
    if env in MODES:
        return env
    return cfg.get("default") if cfg.get("default") in MODES else "watch"


_TOKEN = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|gho_|ghs_|ghu_|ghr_|github_pat_|glpat-|sk-|xox[abprs]-|AKIA)"
                    r"[A-Za-z0-9_\-]{6,}|(?<=://)[^\s/@]+(?=@)")


def mask(text: str) -> str:
    """Every line kept, token-shaped values and URL credentials masked: for echoed logs, where
    scrub()'s 32-character rule would hide commit ids and test names."""
    return _TOKEN.sub("[redacted]", text or "")


def scrub(text: str) -> str:
    """One line, no secret-shaped values, nothing after a quoted command."""
    lines = (text or "").strip().split("\n")
    line = lines[0]
    if line[:1] in GLYPHS.values() and len(lines) > 1:  # a note: the header and its first detail line
        line = f"{line[2:]}: {lines[1].strip()}"
    line = re.split(r",? read from:", line, maxsplit=1)[0]
    return _SECRETISH.sub("[redacted]", line)[:160]


def log_event(rule: str, mode: str, outcome: str, reason: str, hard: bool) -> None:
    """Append one line to the event log. Never the command text: a fingerprint only."""
    import hashlib
    import time
    try:
        path = events_path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > EVENTS_MAX_BYTES:
            os.replace(path, path + ".1")
        cmd = command_of(_EVENT) if _EVENT else ""
        row = {
            "at": time.time(), "hook": rule.split(".", 1)[0], "rule": rule, "mode": mode,
            "outcome": outcome, "hard": hard, "tool": str(_EVENT.get("tool_name") or ""),
            "where": os.path.basename(str(_EVENT.get("cwd") or "").rstrip("/\\")),
            "fingerprint": hashlib.sha256(cmd.encode("utf-8", "replace")).hexdigest()[:12] if cmd else "",
            "session": str(_EVENT.get("session_id") or "")[:12], "reason": scrub(reason),
        }
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass  # The log is evidence, never a reason to fail the call.


def _nudged_before(rule: str) -> bool:
    """One nudge per rule, command and session: a repeated warning stops being read."""
    import hashlib
    cmd = command_of(_EVENT) if _EVENT else ""
    fp = hashlib.sha256(cmd.encode("utf-8", "replace")).hexdigest()[:12] if cmd else ""
    sess = str(_EVENT.get("session_id") or "")[:12]
    try:
        with open(events_path(), encoding="utf-8") as fh:
            tail = fh.readlines()[-500:]
    except OSError:
        return False
    for line in tail:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("outcome") == "nudged" and r.get("rule") == rule and r.get("session") == sess \
                and r.get("fingerprint") == fp:
            return True
    return False


def block(reason: str, rule: str = "", hard: bool = False) -> None:
    """Refuse, nudge or log, by the rule's mode. `hard` marks an irreversible or outward act."""
    rule = rule or hook_name()
    mode = mode_for(rule, hard)
    if mode == "guard":
        log_event(rule, mode, "blocked", reason, hard)
        sys.stderr.write(as_note(reason, "refused") + "\n")
        sys.stderr.flush()
        sys.exit(2)
    if mode == "nudge" and not _nudged_before(rule):
        log_event(rule, mode, "nudged", reason, hard)
        text = as_note(reason, "refused").split("\n")
        head = text[0].rsplit(" · ", 1)[0] + " · nudge"
        allow(context="\n".join([GLYPHS["nudge"] + head[1:], *text[1:NOTE_LINES - 1],
                                 f"  (nudge mode: {rule} let this call run. Follow the rule from here "
                                 "unless the owner says otherwise.)"]))
    log_event(rule, mode, "logged", reason, hard)
    sys.exit(0)


def allow(context: str = "", message: str = "") -> None:
    out: dict = {}
    if context:
        out["hookSpecificOutput"] = {"hookEventName": "PreToolUse",
                                     "additionalContext": as_note(context, "warning")}
    if message:
        out["systemMessage"] = as_note(message, "warning")
    if out:
        sys.stdout.write(json.dumps(out) + "\n")
    sys.exit(0)


def segments(command: str) -> list[str]:
    """Split a shell line on ; && || | and newlines. Quotes are respected
    roughly (a separator inside quotes does not split).

    Comments are dropped first: a `#` that starts a word (line start or after
    whitespace or a separator) runs to the end of the line in sh, bash and
    PowerShell alike and never executes. PowerShell's `<# … #>` block is NOT
    stripped: in bash `<#` is a redirect plus a line comment, so treating the
    block as dead text would hide the bash lines after it. Before 2026-10-04 one apostrophe in a comment
    ("this machine's") opened a quote that swallowed the lines after it, so a
    plain `git push origin HEAD:main` was read inside a merged segment and
    refused as a delete push (observation 0327)."""
    return [s for s, _ in split_ops(command)]


def split_ops(command: str) -> list[tuple[str, str]]:
    """segments() with the separator after each one (`;`, `|`, `||`, `&&`, a newline, or "")."""
    command = strip_comments(command)
    out, cur, quote = [], [], None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch in ";|\n" or command.startswith("&&", i):
            sep = command[i:i + 2] if command.startswith(("&&", "||"), i) else ch
            out.append(("".join(cur), sep))
            cur = []
            i += len(sep) - 1
        else:
            cur.append(ch)
        i += 1
    out.append(("".join(cur), ""))
    return [(s.strip(), sep) for s, sep in out if s.strip()]


# A line continuation joins two lines into one command (V-K8w F1): `git push \<newline> --force` in
# sh and bash, `` git push `<newline> --force `` in PowerShell. Joined once, before any split or match.
# An even run of backslashes (or backticks) before the newline is an escaped character, not a join.
CONT_SH = re.compile(r"(?<!\\)((?:\\\\)*)\\\r?\n")
CONT_PS = re.compile(r"(?<!`)((?:``)*)`\r?\n")


def is_powershell() -> bool:
    return _EVENT.get("tool_name") == "PowerShell"


def join_lines(text: str, ps: bool | None = None) -> str:
    """The text with line continuations joined: backslash-newline always (sh semantics, and a harmless
    join elsewhere), backtick-newline when the text is PowerShell (in bash a backtick opens a
    substitution, so it is left alone there)."""
    text = CONT_SH.sub(r"\1", text)
    if is_powershell() if ps is None else ps:
        text = CONT_PS.sub(r"\1", text)
    return text


# ------------------------------------------------------------ time budget (V-K8w F5)
BUDGET = 20.0
_CLOCK: dict = {}


def start_budget(rule: str, reason: str, hit) -> None:
    """Fail closed on time. `hit()` says whether the command or a file read so far names what this hook
    guards; past the budget the hook refuses (exit 2) when it does and allows when it does not. A timer
    thread is the backstop for code that never reaches check_budget()."""
    import threading
    try:
        secs = float(os.environ.get("GATEWARDEN_BUDGET") or BUDGET)
    except ValueError:
        secs = BUDGET
    if not math.isfinite(secs) or secs <= 0:
        secs = BUDGET
    _CLOCK.update(deadline=time.monotonic() + secs, secs=secs, rule=rule, reason=reason, hit=hit)
    t = threading.Timer(secs + 0.5, _over_budget)
    t.daemon = True
    t.start()


def remaining() -> float:
    return _CLOCK["deadline"] - time.monotonic() if _CLOCK else 1e9


def check_budget() -> None:
    if _CLOCK and time.monotonic() > _CLOCK["deadline"]:
        _over_budget()


def _over_budget() -> None:
    try:
        hit = bool(_CLOCK["hit"]())
    except Exception:
        hit = True
    if hit:
        try:
            log_event(_CLOCK["rule"], "guard", "blocked", "time budget", True)
            sys.stderr.write(as_note(f"{_CLOCK['reason'].rstrip()} The check ran past its {_CLOCK['secs']:g} s "
                                     "time budget on a command that names what this hook guards. Blocked to be "
                                     "safe; split the command.", "refused") + "\n")
            sys.stderr.flush()
        finally:
            os._exit(2)
    os._exit(0)


def strip_comments(text: str, ps: bool | None = None) -> str:
    """Remove `#` line comments outside quotes; newlines are kept so a caller's
    line numbers still hold. In PowerShell a `<# … #>` block goes first: its `#>` would otherwise
    start a line comment that hides the command after the block (`<# x #> git push -f`, V-K8w)."""
    if is_powershell() if ps is None else ps:
        text = re.sub(r"<#.*?#>", lambda m: " " + "\n" * m.group(0).count("\n"), text, flags=re.S)
    out, i, quote, n = [], 0, None, len(text)
    while i < n:
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "#" and (i == 0 or text[i - 1] in " \t\n;|&("):
            end = text.find("\n", i)
            i = n if end < 0 else end
            continue
        if ch in "'\"":
            quote = ch
        out.append(ch)
        i += 1
    return "".join(out)


def budget_timeout(timeout: float) -> float:
    """A subprocess timeout that ends before the hook's time budget does."""
    return max(0.5, min(timeout, remaining() - 1.0))


def run_git(cwd: str, *args: str, timeout: int = 15) -> str:
    check_budget()
    # git writes UTF-8 (commit subjects with an em dash); the locale decode read it as cp1252 mojibake.
    p = subprocess.run(["git", *args], cwd=cwd or None, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=budget_timeout(timeout), creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "").strip() or f"git {' '.join(args)} failed")
    return p.stdout.strip()


def state_dir() -> str:
    d = os.environ.get("GATEWARDEN_STATE") or os.path.join(os.path.expanduser("~"), ".claude", "gatewarden")
    os.makedirs(d, exist_ok=True)
    return d


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json_atomic(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def unquote(token: str) -> str:
    return re.sub(r"^(['\"])(.*)\1$", r"\2", token)


# ------------------------------------------------------------ command normalisation
# A text-matching hook is only as strong as the text it matches. Before a hook matches,
# `expand()` unwraps every shape that hides a command from a plain reading (warden audit
# A3, 2026-10-01): quote, escape and caret splices; `"a" + "b"` concatenation; ${IFS};
# `sh|bash|zsh -c`, `pwsh|powershell -Command`, `cmd /c`, `eval`, `iex`; `$(…)`,
# backticks, `<(…)`; `-EncodedCommand` (base64 of UTF-16LE); a script file a shell or an
# interpreter runs; a script piped into a shell. What it cannot read raises Unparseable
# (hard: every hook blocks) or lands in `opaque` (each hook blocks when its own hint words
# appear on the line). A script file on disk that it cannot read (over MAX_FILE, no access)
# lands in `unread` (a shell runs it) or `unread_code` (an interpreter runs it): push_gate refuses
# the first, hyperv_lock and golive_block refuse both (V-K8w FP2). A script over BIG is not parsed
# word by word: it lands in `big` and each hook scans it with its own regexes (V-K8w F8). A script a
# shell runs that is not on disk yet lands in `pending`: it is written on this same line.

class Unparseable(Exception):
    def __init__(self, why: str, hard: bool = True):
        super().__init__(why)
        self.hard = hard


MAX_DEPTH = 4
MAX_FILE = 8_000_000
BIG = 256_000
FILES_READ: list[str] = []  # every script text read this run, for the time-budget verdict
IFS = re.compile(r"\$\{IFS[^}]*\}|\$IFS(?!\w)")
CONCAT = re.compile(r"""(['"])\s*\+\s*(['"])""")
SPLICE = re.compile(r"""(?<=[\w.$-])(?:''|"")(?=[\w.-])|[`^](?=[\w.-])|(?<=[A-Za-z])\\(?=[A-Za-z])"""
                    r"""|\$@|\$\*|\$\{\}|\$\(\s*\)|\$''|\$\"\"""")
VAR = re.compile(r"\$\{[^}]*\}|\$[A-Za-z_][\w:]*|%[A-Za-z_]\w*%")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "ash", "busybox", "wsl", "pwsh", "powershell", "cmd"}
PS = {"pwsh", "powershell"}
EXECUTORS = SHELLS | {"eval", "iex", "invoke-expression", "invoke-command", "icm", "source", "foreach",
                      "xargs", "su", "sudo", "doas", "ssh", "start-process", "saps", "start", "runas",
                      "watch", "timeout", "nohup", "env", "exec", "command", "time", "script", "--exec",
                      "-x", "alias", "set-alias", "sal", "new-alias", "nal", "doskey", "flock", "runuser",
                      "setsid", "tmux", "screen", "parallel", "npx", "nodemon", "watchexec", "entr",
                      "chroot", "unshare", "nice", "ionice", "stdbuf"}
STDIN_EVAL = {"iex", "invoke-expression"}
INTERPRETERS = {"python", "python3", "py", "pythonw", "node", "perl", "ruby", "php"}
CODE_FLAGS = {"-c", "-e", "--eval", "-r"}
READERS = {"cat", "type", "gc", "get-content", "more", "less", "head", "tail"}
RUNS = PS | SHELLS | STDIN_EVAL | INTERPRETERS | {"source", "."}  # the programs expand() reads further
SHELL_FILE = re.compile(r"(?i)\.(sh|bash|zsh|ps1|psm1|bat|cmd)$")
OPAQUE = re.compile(r"(?i)\[scriptblock\]::create|&\s*\$|&\s*\(|\.invoke\(|\binvoke-command\b"
                    r"|(?:^|[\s;|&])(?:eval|iex|invoke-expression)\s+[\"']?\$")
CD_SEG = re.compile(r"""(?i)^\s*(?:cd|chdir|pushd|set-location|sl)\s+(?:-path\s+)?(?:"([^"]+)"|'([^']+)'|(\S+))\s*$""")


def despliced(text: str) -> str:
    """The text with splices removed, for matching only (it may damage paths)."""
    t = IFS.sub(" ", text)
    t = CONCAT.sub("", t)
    t = SPLICE.sub("", t)
    return re.sub(r"""['"`]""", "", t)


def word(tok: str) -> str:
    """A token as the program or subcommand name it runs as; NUL when built at run time."""
    t = despliced(tok)
    if VAR.search(t) or re.search(r"\$\(|`[^`]*`", tok):
        return "\x00"
    return t.strip("{}()[];,&@ \t").lower()


def prog(tok: str) -> str:
    """The program a token names: last path part, quotes and splices removed, no .exe."""
    t = unquote(tok.strip("{}()&@ \t"))
    w = word(re.split(r"[\\/]", t)[-1])
    return w[:-4] if w.endswith(".exe") else w


def tokens(segment: str) -> list[str]:
    """Shell words, with `"a" + "b"` concatenation and ${IFS} word splits applied first."""
    segment = CONCAT.sub("", IFS.sub(" ", segment))
    try:
        import shlex
        return shlex.split(segment, posix=False)
    except ValueError:
        return segment.split()


def resolve(path: str, cwd: str) -> str:
    path = os.path.expanduser(unquote(path.strip()))
    m = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    if os.name == "nt" and m:  # Git Bash style: a one-letter root folder becomes that drive
        path = m.group(1).upper() + ":" + (m.group(2) or "/")
    full = os.path.normpath(os.path.join(cwd or os.getcwd(), path))
    if os.name != "nt" and "\\" in path and not os.path.exists(full):
        # PowerShell on Linux and macOS reads a backslash as a separator (.\push.ps1).
        alt = os.path.normpath(os.path.join(cwd or os.getcwd(), path.replace("\\", "/")))
        if os.path.exists(alt):
            return alt
    return full


def cd_target(segment: str) -> str | None:
    m = CD_SEG.match(segment)
    return (m.group(1) or m.group(2) or m.group(3)) if m else None


def read_small(path: str) -> str | None:
    return read_script(path)[0]


def read_script(path: str) -> tuple[str | None, str]:
    """(text, why it was not read). No file there gives (None, ""): a later write is checked when
    it is written. A file over MAX_FILE or one that cannot be opened gives (None, why): the caller
    records it in Expanded.unread, and every hard-rule hook refuses (warden audit K7-4-03)."""
    try:
        if not os.path.isfile(path):
            return None, ""
        if os.path.getsize(path) > MAX_FILE:
            return None, f"a script over {MAX_FILE // 1_000_000} MB ({os.path.basename(path)})"
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        FILES_READ.append(text)
        return text, ""
    except OSError:
        return None, f"a script the hook cannot open ({os.path.basename(path)})"


def substitutions(text: str) -> list[str]:
    """Inner text of $(…), <(…), >(…), @(…) and `…` pairs."""
    out, i = [], 0
    while i < len(text):
        if text[i] in "$<>@" and text.startswith("(", i + 1):
            depth, j = 0, i + 1
            while j < len(text):
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                if depth == 0:
                    break
                j += 1
            if depth:
                raise Unparseable("an unclosed $( substitution", hard=False)
            out.append(text[i + 2:j])
            i = j
        i += 1
    ticks = [m.start() for m in re.finditer(r"(?<!\\)`", text)]
    for a, b in zip(ticks[0::2], ticks[1::2]):
        inner = text[a + 1:b]
        if inner.strip() and len(inner.strip()) > 1:
            out.append(inner)
    return out


def decode_ps(b64: str) -> str:
    import base64
    import binascii
    try:
        raw = base64.b64decode(unquote(b64) + "=" * (-len(unquote(b64)) % 4), validate=True)
        return raw.decode("utf-16-le")
    except (binascii.Error, ValueError):
        raise Unparseable("an -EncodedCommand that does not decode")


def is_encoded_flag(tok: str) -> bool:
    n = tok.lstrip("-/").lower()
    return tok[:1] in "-/" and bool(n) and (n == "ec" or (n[0] == "e" and "encodedcommand".startswith(n)))


class Expanded:
    def __init__(self):
        self.shells: list[tuple[str, str]] = []   # (shell text, cwd it runs in)
        self.code: list[tuple[str, str]] = []     # (code body, file path or "")
        self.opaque: list[str] = []               # shapes whose content could not be read
        self.unread: list[str] = []               # script files a shell runs that the hook could not
                                                  # read (too large, no access): hard rules refuse
        self.unread_code: list[str] = []          # the same for a file an interpreter runs
        self.big: list[str] = []                  # shell scripts over BIG: regex-scanned, not parsed
        self.pending: list[str] = []              # scripts a shell runs that are not on disk yet
        self.written: dict[str, bool] = {}        # files this line writes -> True when their new
                                                  # content is not plain on the line (copy, download)
        self.files = True                         # False: never read a file (heredoc_guard)
        self.read: set[str] = set()               # files already expanded: a script that names itself
                                                  # (a usage comment) is read once, not to MAX_DEPTH


QUOTED_VALUE = re.compile(r"""^[\w.:-]+=(['"])(.*)\1$""", re.S)

# V-K8w2 B8: inline interpreter code (`python -c`, `node -e`, `pwsh -c`) that names both a decode call
# and a run call hands a program text the hook never sees. Plain substrings of the call names, matched
# without case; nothing is decoded or evaluated.
DECODE_CALLS = ("b64decode", "base64.decode", "frombase64string")
RUN_CALLS = ("os.system", "subprocess", "exec(", "eval(", "execsync", "child_process", "invoke-expression",
             "iex")
DECODE_AND_RUN = "inline code that decodes text and runs it"


def decodes_and_runs(code: str) -> bool:
    """True when inline code names a decode call and a run call (B8)."""
    low = code.lower()
    decodes = any(n in low for n in DECODE_CALLS) or ("buffer.from" in low and "base64" in low)
    return decodes and any(n in low for n in RUN_CALLS)


def _inline_code(code: str, out: "Expanded") -> None:
    """Fail closed on B8 inline code: unread_code for the hooks that read code, unread for push_gate."""
    if decodes_and_runs(code):
        out.unread_code.append(DECODE_AND_RUN)
        out.unread.append(DECODE_AND_RUN)


# V-K8w2 B2: a PowerShell segment whose command word is `iex`, `Invoke-Expression`, `&` or `.` runs a string
# the hook never sees when its argument text, or the value set on the same line for the variable it names,
# builds that string. Plain substrings, matched without case; nothing is evaluated.
STRING_BUILDERS = ("frombase64string", "-join", "-f ", "[char]")
STRING_RUN_WORD = re.compile(r"(?i)^\s*(?:iex|invoke-expression|&|\.)(?=[\s(\"'$]|$)")
BUILT_STRING = "a PowerShell run of a string built from encoded or joined parts"


def _built_string_run(seg: str, segs: list[str], out: "Expanded") -> None:
    """Fail closed on B2: unread_code for the hooks that read code, unread for push_gate."""
    m = STRING_RUN_WORD.match(seg)
    if not m:
        return
    arg = seg[m.end():]
    texts = [arg]
    for name in re.findall(r"\$([A-Za-z_][\w:]*)", arg):
        assign = re.compile(r"(?i)^\s*\$" + re.escape(name) + r"\s*=(?!=)(.*)$", re.S)
        texts += [a.group(1) for a in (assign.match(s) for s in segs) if a]
    if any(b in t.lower() for t in texts for b in STRING_BUILDERS):
        out.unread_code.append(BUILT_STRING)
        out.unread.append(BUILT_STRING)


# V-K8w2 B1: a `$(…)` or backtick substitution that is the program text of an executor (`eval`, `sh -c`,
# `bash -c`, or the segment's command word) runs a text the hook never sees when the substitution names a
# decoder or a fetcher. Plain substrings, matched without case; nothing is evaluated. Each nesting level
# expand() walks is checked on its own text.
SUB_DECODERS = ("base64 -d", "base64 --decode", "xxd -r", "certutil -decode")
SUB_FETCHERS = ("curl", "wget", "iwr", "invoke-webrequest", "irm")
SUB_RUNNER = re.compile(r"(?is)^(?:eval\b.*|(?:\S*/)?(?:sh|bash)\s+(?:-\w+\s+)*-\w*c\w*\b.*)$")
RUN_SUBSTITUTION = "a substitution that decodes or fetches the text a shell runs"


def _run_substitution(command: str, inner: str, ps: bool, out: "Expanded") -> None:
    """Fail closed on B1: unread for push_gate, unread_code for the hooks that read code."""
    low = inner.lower()
    if not (any(n in low for n in SUB_DECODERS + SUB_FETCHERS) or ("openssl" in low and " -d" in low)):
        return
    forms = ["$(" + inner + ")"] + ([] if ps else ["`" + inner + "`"])
    for form in forms:
        for m in re.finditer(re.escape(form), command):
            seg = re.split(r"[;&|\n]", command[:m.start()])[-1]
            seg = re.sub(r"""['"]""", "", seg).strip()
            # In PowerShell a `$(…)` command word prints its value; only the executors run it there.
            if (not seg and not ps) or SUB_RUNNER.match(seg):
                if RUN_SUBSTITUTION not in out.unread:
                    out.unread.append(RUN_SUBSTITUTION)
                    out.unread_code.append(RUN_SUBSTITUTION)
                return


def expand(command: str, cwd: str = "", depth: int = 0, out: Expanded | None = None,
           ps: bool | None = None, files: bool = True) -> Expanded:
    """Every shell text and code body the command runs, as far as text can show it. `ps` says the
    text is PowerShell (None: the event's tool); `files=False` reads no file from disk."""
    if out is None:
        out = Expanded()
        out.files = files
    if depth > MAX_DEPTH:
        raise Unparseable(f"commands nested more than {MAX_DEPTH} levels deep")
    check_budget()
    ps = is_powershell() if ps is None else ps
    command = join_lines(command, ps)
    out.shells.append((command, cwd))
    if OPAQUE.search(command):
        out.opaque.append("a command built or invoked at run time")
    for inner in substitutions(command):
        _run_substitution(command, inner, ps, out)
        expand(inner, cwd, depth + 1, out, ps)
    ops = split_ops(command)
    segs = [s for s, _ in ops]
    toks_all = [tokens(s) for s in segs]
    if any(prog(t) in EXECUTORS or t.lower() in EXECUTORS for toks in toks_all for t in toks):
        inner_ps = ps or any(prog(t) in PS or prog(t) in STDIN_EVAL for toks in toks_all for t in toks)
        for toks in toks_all:
            for t in toks:
                m = QUOTED_VALUE.match(t)  # alias gp='…', a NAME='…' handed on to a runner
                if m:
                    expand(m.group(2), cwd, depth + 1, out, inner_ps)
                if len(t) > 2 and t[0] == t[-1] and t[0] in "'\"":
                    inner = t[1:-1]
                    if inner.strip().startswith("$") and not inner.strip().startswith("$("):
                        out.opaque.append("a shell handed a variable to run")
                    expand(inner, cwd, depth + 1, out, inner_ps)
    cur, piped_files, prev_sep, prev_vis = cwd, [], "", False
    for (seg, sep), toks in zip(ops, toks_all):
        target = cd_target(seg)
        if target:
            cur = resolve(target, cur)
            prev_sep, prev_vis = sep, False
            continue
        if ps:
            _built_string_run(seg, segs, out)
        progs = [prog(t) for t in toks]
        vis = _visible(seg, toks, progs)
        if out.files:
            for path, hidden in _writes(seg, toks, progs, prev_sep == "|" and prev_vis, vis):
                key = os.path.normcase(os.path.abspath(resolve(path, cur)))
                out.written[key] = out.written.get(key, False) or hidden
        stdin_runner = False
        for i, p in enumerate(progs):
            if p not in RUNS:
                continue  # no O(n) copy per word on a long line (V-K8w F5)
            rest = toks[i + 1:]
            if p in PS:
                for k, t in enumerate(rest):
                    if is_encoded_flag(t):
                        if k + 1 >= len(rest):
                            raise Unparseable("an -EncodedCommand with no value")
                        expand(decode_ps(rest[k + 1]), cur, depth + 1, out, True)
                    elif t.lower() in ("-file", "-f") and k + 1 < len(rest):
                        _run_file(rest[k + 1], cur, depth, out, shell=True)
                    elif t.lower() in ("-c", "-command") and (k + 1 >= len(rest) or rest[k + 1] == "-"):
                        stdin_runner = True
                    elif t.lower() in ("-c", "-command"):
                        _inline_code(unquote(rest[k + 1]), out)
                    elif t in ("-",):
                        stdin_runner = True
                if i == 0 and not rest:
                    stdin_runner = True
            elif p in SHELLS and p != "cmd":
                opts = [t for t in rest if t.startswith("-")]
                # A redirection (`<<'EOF'`, `2>&1`) is not the script a shell runs.
                args = [t for t in rest if not t.startswith("-") and not re.match(r"^\d*[<>]", t)]
                if any("c" in o.lstrip("-") and not o.startswith("--") for o in opts) or p == "wsl":
                    pass  # the command string is unwrapped as a quoted token above
                elif args:
                    _run_file(args[0], cur, depth, out, shell=True)
                elif i == 0:
                    stdin_runner = True
            elif p == "cmd":
                after = [t for t in rest if t.lower() not in ("/c", "/k", "/q", "/d", "/s")]
                if after and SHELL_FILE.search(unquote(after[0])):
                    _run_file(after[0], cur, depth, out, shell=True)
            elif p in ("source", ".") and i == 0 and rest:
                _run_file(rest[0], cur, depth, out, shell=True)
            elif p in STDIN_EVAL and not rest:
                stdin_runner = True
            elif p in INTERPRETERS:
                flag = next((k for k, t in enumerate(rest) if t in CODE_FLAGS), None)
                if flag is not None and flag + 1 < len(rest):
                    out.code.append((unquote(rest[flag + 1]), ""))
                    _inline_code(unquote(rest[flag + 1]), out)
                else:
                    args = [t for t in rest if not t.startswith("-")]
                    module = any(t == "-m" for t in rest[:rest.index(args[0])]) if args else "-m" in rest
                    if module:
                        pass
                    elif args:
                        _run_file(args[0], cur, depth, out, shell=False)
                    elif i == 0 or rest == ["-"]:
                        stdin_runner = True
                break
        if toks:
            first = toks[1] if toks[0] == "&" and len(toks) > 1 else toks[0].lstrip("&")
            if SHELL_FILE.search(unquote(first.strip())):
                _run_file(first, cur, depth, out, shell=True)
        if progs and progs[0] in READERS:
            piped_files += [resolve(t, cur) for t in toks[1:] if not t.startswith("-")]
        elif stdin_runner:
            code_runner = bool(progs) and progs[0] in INTERPRETERS
            if any(out.written.get(os.path.normcase(os.path.abspath(f))) for f in piped_files):
                piped_files = []  # copied or generated on this line: what is on disk now is not what runs
                prev_vis = False
            read = [read_script(f) for f in piped_files] if out.files else []
            (out.unread_code if code_runner else out.unread).extend(why for _, why in read if why)
            texts = [t for t, _ in read]
            if piped_files and out.files and all(t is not None for t in texts):
                for f, t in zip(piped_files, texts):
                    if code_runner:
                        out.code.append((t, f))
                    elif len(t) > BIG:
                        out.big.append(t)
                    else:
                        expand(t, cur, depth + 1, out, ps or bool(re.search(r"(?i)\.ps[md]?1$", f)))
            elif not piped_files and (prev_sep != "|" or prev_vis):
                pass  # nothing piped in (a heredoc body is read on this line), or a plain echoed literal
            else:
                # `… | base64 -d | bash`, `curl … | sh`, `$s | iex`: the script never shows. Unread, so
                # every hard-rule hook refuses whatever the line says (K8w2, beyond the verifier's list).
                (out.unread_code if code_runner else out.unread).append(
                    "a script piped into a shell from a source the hook cannot read")
            piped_files = []
        prev_sep, prev_vis = sep, vis
    return out


ECHOERS = {"echo", "printf", "write-output", "write-host", "write"}
COPIERS = {"cp", "mv", "install", "ln", "copy", "move", "copy-item", "cpi", "move-item", "mi", "scp", "rsync",
           "xcopy", "robocopy", "rename-item", "ren"}
FILE_WRITERS = {"set-content", "sc", "add-content", "ac", "out-file", "new-item", "ni", "curl", "wget",
                "invoke-webrequest", "iwr", "invoke-restmethod", "irm"}
OUT_FLAGS = {"-o", "--output", "--output-document", "-outfile", "-path", "-filepath", "-literalpath"}
REDIR_TARGET = re.compile(r"(?<![<>&\d-])\d*>>?\|?\s*([^\s;|&<>()]+)")


def _visible(seg: str, toks: list[str], progs: list[str]) -> bool:
    """True when what the segment prints is plain on this line: a heredoc or here-string, or echo, printf
    or a PowerShell string literal with no variable, substitution or escape sequence in it."""
    if "<<" in seg:
        return True
    if not toks or not (progs[0] in ECHOERS or toks[0][:1] in "'\""):
        return False
    return "\\" not in seg and "`" not in seg and not re.search(r"\$[\w({'\"]", re.sub(r"'[^']*'", "", seg))


def _writes(seg: str, toks: list[str], progs: list[str], fed_visibly: bool, vis: bool) -> list[tuple[str, bool]]:
    """(path, hidden) for each file the segment writes; hidden when its new content is not plain on the
    line (a copy, a download, a program's output), so the file on disk now is not what will run."""
    found = []
    for m in REDIR_TARGET.finditer(re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", " ", seg)):
        t = m.group(1)
        if not (t.startswith("&") or t.lower() in ("/dev/null", "$null", "nul")):
            found.append((t, not vis))
    if not progs:
        return found
    p, args = progs[0], [unquote(t) for t in toks[1:] if not t.startswith("-")]
    if p == "tee":
        found += [(a, not fed_visibly) for a in args]
    elif p in COPIERS and args:
        found.append((args[-1], True))
    elif p in FILE_WRITERS:
        for k, t in enumerate(toks[1:], 1):
            name, _, val = t.partition("=")
            if name.lower() in OUT_FLAGS and (val or k + 1 < len(toks)):
                found.append((unquote(val or toks[k + 1]), True))
        if p in ("set-content", "sc", "add-content", "ac", "out-file") and args:
            found.append((args[0], True))
    return found


def _run_file(path_tok: str, cwd: str, depth: int, out: Expanded, shell: bool) -> None:
    if not out.files:
        return
    path = resolve(path_tok, cwd)
    key = os.path.normcase(os.path.abspath(path))
    if key in out.read:
        return  # already expanded in this command: its content was checked the first time
    out.read.add(key)
    hidden = out.written.get(key)
    if hidden is not None:  # this line writes the file before it runs it: the disk copy is stale
        if hidden:
            (out.unread if shell else out.unread_code).append(
                f"a script this line writes from content the hook cannot see ({os.path.basename(path)})")
        elif shell:
            out.pending.append(path)  # its new content is plain on this line and read there
        return
    text, why = read_script(path)
    if why:
        # On disk but unread: fail closed for hard rules (K7-4-03), by who runs it (V-K8w FP2).
        (out.unread if shell else out.unread_code).append(why)
        return
    if text is None:
        if shell:
            out.pending.append(path)  # written on this line, or never: the hook cannot read it now
        return
    if not shell:
        out.code.append((text, path))
    elif len(text) > BIG:
        out.big.append(text)
    else:
        expand(text, cwd, depth + 1, out, bool(re.search(r"(?i)\.ps[md]?1$", path)))
