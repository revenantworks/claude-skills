#!/usr/bin/env python3
"""dispatch_ledger_guard.py — PreToolUse hook (matcher: Task|Agent|Workflow) for
revenantworks-foundation-dispatchwright.

Ledger header lines (2026-10-01, references/ledger-schema.md): a ledger whose
header says `records: public (off git)` -- or whose origin URL matches an entry
in CLAUDE_DISPATCH_PUBLIC_REMOTES -- gets no git-ignore warning (it warns the
other way when git would commit it). A ledger whose header says `ledger: v2`
has every row checked against the "Row validation (ledger v2)" list and a
malformed row blocks (exit 2); a ledger without that line is v1 and is never
blocked by that check.

Fixed 2026-08-18 — four fail-open defects, all reproduced on the live file
before the fix. The selftest below covers each one end to end; if you edit this
file, run `--selftest` and expect it to fail loudly rather than quietly pass.

  D1  NO SESSION ID WAS A TOTAL NO-OP. `flag_is_live` returned False whenever
      the payload carried no session id, so every Task/Agent/Workflow call
      without one sailed past the guard. Now a fresh flag with a session id the
      guard cannot correlate ENFORCES the ledger check instead of skipping it.
  D2  EXIT 1 ON ANY EXCEPTION. Claude Code blocks a PreToolUse call only on
      exit code 2; 1 is a non-blocking error. Only json.load was wrapped, so a
      throw anywhere later failed OPEN. The whole body is wrapped now and every
      path returns 0 or 2. Never 1.
  D3  A STALE LEDGER DISARMED THE GUARD FOREVER. find_ledger took the newest
      ledger by mtime with no age limit and no tie to the live run, so one old
      populated ledger in a directory passed every dispatch there for good. A
      ledger now has to sit inside the same staleness window that keeps the
      flag live, or name the current session outright.
  D4  JUNK CELLS COUNTED AS TIERED. `_populated` rejected only "", "-" and the
      em dash, so a row of TBD / ? / x satisfied "names its model, effort and
      surface". The three cells are now validated per field.

Pairs with dispatch_gate.py. That hook sets a mode-flag file
(`~/.claude/dispatch-mode.json`, session id + timestamp) when a prompt looks
like a fan-out. This hook reads it on every Task/Agent/Workflow call:

  - Flag absent, unreadable, stale, or owned by a DIFFERENT session -> exit 0.
    Dispatch mode is not active here; there is nothing to enforce.
  - Flag live for this session, or fresh but not correlatable -> the run ledger
    must exist, must be current, and must carry a properly tiered row. Anything
    else exits 2 with a short reason on stderr.

This is deliberately a coarse check, stated plainly rather than overclaimed: it
confirms *a* tiered row exists in the run's current ledger, not that the
SPECIFIC unit about to be dispatched has one -- correlating a Task call's own
tool_input against a specific ledger row would need a unit id the tool_input
has no standard place to carry. The coarse form still catches the failure mode
that matters most: a wave launched with a missing, stale, or untiered ledger.

Extended 2026-08-20 (skillwright pack audit, finding P1-2 / S-3): SKILL.md
section 6 states two wave-execution caps in prose -- max 6 concurrent units,
one writer per repo -- that nothing here enforced before this change; the
guard only ever proved a row existed, never that dispatching one more unit
would stay inside either cap. Both new checks (open_unit_count,
repo_collision) share the same coarse-by-necessity limitation as the check
above: they read the ledger AS IT STANDS and block when it already shows a
cap violated, rather than simulating what the specific about-to-run call would
do. Given the ledger row for a unit is written before its dispatch call fires
(SKILL.md section 5), the row for the call under the guard's own PreToolUse
hook is already in the ledger by the time these run, so "already violated"
correctly includes that unit.

Extended 2026-09-11 (task-observer observation #0022): open_unit_count()
counted ROWS, and a Workflow call is one row however many agents its own
script spawns -- three rows once hid 245 refuter agents from the 6-unit cap
and the usage-window check in the same run. A row whose `surface` cell states
an agent-count token -- written as the literal text `x<N>` somewhere in the
cell, e.g. `subagent (workflow) x245` (SKILL.md section 6's own worked form)
-- now counts as N units against the cap, not 1. `agent_multiplier()` parses
the token; a missing or malformed one (no digits, a non-positive count, `x`
with nothing after it) defaults to 1, the same as a row with no token at all,
so a normal single-agent row is never penalized and a broken token never
silently zeroes a row out of the count.

Extended 2026-09-17 (dispatchwright 1.3.0, pacewright's references/window-fit.md): the
usage windows. After every check above passes, the guard reads
`~/.claude/usage-windows.json` (written by usage_windows.py, the sibling
statusLine command -- the only place the harness publishes the subscription
windows) and `~/.dispatch/usage-calibration.json` (tokens-per-percent, measured
by Reconcile from verified waves). The rule, kept simple on purpose:

  - No windows file, or one older than 15 minutes -> say NOTHING (exit 0). The
    plan step already asked the owner; the guard has no better number.
  - `five_hour` or `seven_day` `used_percentage` at or above the stop band
    -> BLOCK (exit 2), naming the window and its reset time. The stop band is
    pacewright's unexpired budget file `stop_bands.stop` (50-95: it may
    tighten the band, never relax it), else the
    documented default of 95 (dispatchwright meters.md; K8a replaced a 97
    literal that covered the 5-hour window only). Exempt when every open
    row's `window` cell begins with `next` AND the call is the owner's
    explicit resume (any string in tool_input contains the word "resume"). A
    wave the plan already deferred to the next window, re-launched by the
    owner after that window rolled but before a fresh reading landed, is the
    one case a stop-band reading is stale by construction.
  - Otherwise sum `estimated_tokens` over the open rows; for each window with
    a calibration (samples >= 1) compute remaining = (100 - used) x
    tokens_per_percent x (1 - margin, default 15%); when remaining is below
    the sum, print ONE WARNING line with the numbers into additionalContext
    (exit 0). No calibration for a window means no comparison for it -- a
    number this hook cannot measure is a number it does not print.
  - On an allowed dispatch, when the ledger has a `pct_at_dispatch` column,
    fill each open row's empty cell with `5h=<pct> 7d=<pct>` -- the dispatch
    half of the calibration point Reconcile completes. Best-effort, never a
    reason to block, and skipped in fixture mode.

`--windows-file PATH`, `--calibration-file PATH` and `--ledger PATH` on argv
read fixtures instead of the live files (the windows file is then taken as
current, since a controls runner can hand a file but not a timestamp; the
ledger write is skipped). CLAUDE_USAGE_WINDOWS / CLAUDE_USAGE_CALIBRATION
override the live paths with the freshness check kept, for --selftest. Every
ledger written before 1.3.0 lacks the four optional columns and is read
exactly as before.

FAILS CLOSED whenever it is armed and cannot prove the dispatch is tiered --
that is the point of this hook. dispatch_gate.py is the opposite and must stay
that way: it runs on every prompt, and a gate that can block is how the
2026-08-18 incident locked the owner out of a whole session.

Run `python dispatch_ledger_guard.py --selftest` to exercise the flag logic,
the ledger currency rule, the cell validators, and the real exit codes of all
four defects against temp fixtures. Stdlib only.
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GATED_TOOLS = {"Task", "Agent", "Workflow"}

# Defensive cap beyond the session-id check: a live flag from the SAME session
# id is still ignored past this age, in case a session id were ever reused
# across an unexpectedly long gap. The session-id match is the primary test.
# The SAME window decides whether a ledger is current (D3) -- one mechanism,
# not two, so raising this raises both together.
STALE_SECONDS = 12 * 60 * 60
# A file written seconds ago can carry a timestamp slightly in the future when
# the clock steps or a network drive disagrees. Tolerate that much skew rather
# than reading a just-written ledger as bogus.
CLOCK_SKEW_SECONDS = 5 * 60

# Session ids the gate writes when the prompt payload had none. Treated as "no
# session id at all" on the flag side.
UNCORRELATABLE_SESSION_IDS = {"", "unknown-session", "unknown", "none", "null"}


def flag_path() -> Path:
    """The mode-flag file. CLAUDE_DISPATCH_FLAG exists so --selftest can run
    the real main() against a temp flag without touching the live one."""
    override = os.environ.get("CLAUDE_DISPATCH_FLAG")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "dispatch-mode.json"


def read_flag() -> dict | None:
    try:
        data = json.loads(flag_path().read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _fresh(ts: float | int | None, now: float | None = None) -> bool:
    """True if `ts` sits inside the staleness window. Shared by the flag check
    and the ledger currency check so the two can never drift apart."""
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return False
    now = time.time() if now is None else now
    age = now - ts
    return -CLOCK_SKEW_SECONDS <= age <= STALE_SECONDS


def flag_state(flag: dict | None, session_id: str) -> str:
    """One of: absent, stale, other-session, uncorrelated, live.

    D1 lives here. The old code returned False -- allow everything -- whenever
    the payload carried no session id, which made a session-less PreToolUse
    payload a free pass around the entire guard. A guard that cannot correlate
    must not conclude "not my session"; it can only conclude "I do not know".
    So a FRESH flag plus an uncorrelatable session id on either side returns
    "uncorrelated", and the caller enforces the ledger check exactly as it does
    for "live". Fail closed on the doubt.

    Blocking outright on "uncorrelated" would be worse, not better: it leaves
    the owner no remedy but deleting the flag by hand for the next 12 hours.
    Enforcing the ledger keeps the real invariant -- an untiered dispatch is
    impossible -- while a correctly tiered wave still runs.

    An absent or long-stale flag still returns early. Nothing was ever armed
    for anyone, and blocking there would lock out every Task call on a machine
    that simply never uses dispatch mode."""
    if not flag:
        return "absent"
    if not _fresh(flag.get("ts")):
        return "stale"
    flag_session = str(flag.get("session_id") or "").strip()
    payload_session = str(session_id or "").strip()
    if (
        flag_session.lower() in UNCORRELATABLE_SESSION_IDS
        or payload_session.lower() in UNCORRELATABLE_SESSION_IDS
    ):
        return "uncorrelated"
    if flag_session != payload_session:
        return "other-session"
    return "live"


def flag_is_live(flag: dict | None, session_id: str) -> bool:
    """Kept for callers that only want the yes/no. `flag_state` carries the
    reason, and main() uses that."""
    return flag_state(flag, session_id) == "live"


def ledger_names_session(path: Path, session_id: str) -> bool:
    """A ledger can tie itself to a session explicitly: the session id written
    anywhere in the ledger text, or in a sibling file named `session` in the
    run directory. Nothing writes those today -- the Markdown and CSV schemas
    in references/ledger-schema.md carry no session column -- so this is the
    forward path, not the primary test, and its absence is never a failure."""
    sid = str(session_id or "").strip()
    if not sid or sid.lower() in UNCORRELATABLE_SESSION_IDS:
        return False
    try:
        if sid in path.read_text(encoding="utf-8", errors="replace"):
            return True
    except Exception:
        pass
    marker = path.parent / "session"
    try:
        if marker.is_file() and sid in marker.read_text(encoding="utf-8", errors="replace"):
            return True
    except Exception:
        pass
    return False


def ledger_is_current(path: Path, session_id: str, now: float | None = None) -> bool:
    """D3. A ledger counts only if it belongs to the run that is live right
    now: it names the current session, or it was written inside the same
    staleness window that keeps the flag live. Without this a single populated
    ledger left in a directory passed every dispatch made there, forever."""
    if ledger_names_session(path, session_id):
        return True
    try:
        mtime = path.stat().st_mtime
    except Exception:
        return False
    return _fresh(mtime, now)


POINTER_FILE = ".dispatch/ledger-path"


def search_dirs(cwd: str) -> list[Path]:
    """The directories the lookup searches, in order (dispatchwright 1.4.0,
    observation 0172). The cwd, then each parent up to and including the first
    one holding `.git` (only when the cwd exists) -- so a session started in a subfolder of the repo still
    finds the repo's run dir. With no `.git` above, the cwd alone (the pre-1.4.0
    behaviour). Then any pinned roots named in CLAUDE_DISPATCH_ROOTS
    (os.pathsep-separated). Printed on a refusal so a miss is diagnosable."""
    start = Path(cwd or ".")
    walk = [start]
    try:
        if not start.is_dir():
            raise FileNotFoundError  # a cwd that does not exist searches itself only
        chain = [start] + list(start.resolve().parents)
        for i, d in enumerate(chain):
            if (d / ".git").exists():
                walk = [start] + chain[1:i + 1]
                break
    except Exception:
        walk = [start]
    pinned = [Path(p) for p in os.environ.get("CLAUDE_DISPATCH_ROOTS", "").split(os.pathsep) if p.strip()]
    return walk + pinned


def ledger_candidates(cwd: str) -> list[Path]:
    """Every ledger the conventions allow, newest first. The lookup order:
    CLAUDE_DISPATCH_LEDGER (names one file and wins outright), then a pointer
    file (`.dispatch/ledger-path`, one line naming the ledger) in a searched
    dir, then `.dispatch/runs/*/ledger.{md,csv}` in each searched dir."""
    env = _argv_path("--ledger") or os.environ.get("CLAUDE_DISPATCH_LEDGER")
    if env:
        p = Path(env)
        return [p] if p.is_file() else []
    found = []
    for root in search_dirs(cwd):
        ptr = root / POINTER_FILE
        try:
            if ptr.is_file():
                target = Path(ptr.read_text(encoding="utf-8").strip().splitlines()[0].strip())
                if not target.is_absolute():
                    target = root / target
                if target.is_file():
                    return [target]
        except Exception:
            pass
        found += list(root.glob(".dispatch/runs/*/ledger.md")) + list(root.glob(".dispatch/runs/*/ledger.csv"))
        if found:
            break
    candidates = [p for p in found if p.is_file()]

    def _mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except Exception:
            return 0.0

    candidates.sort(key=_mtime, reverse=True)
    return candidates


def find_ledger(cwd: str, session_id: str = "") -> Path | None:
    """The newest ledger that is still current for this run. A stale one is not
    a ledger for this purpose -- returning it and passing would be the D3 bug."""
    for p in ledger_candidates(cwd):
        if ledger_is_current(p, session_id):
            return p
    return None


# ---------------------------------------------------------------------------
# D4 -- what counts as a tiered cell.
#
# The rule, stated once so it does not need editing every time a model ships:
#
#   model    Must not be a known placeholder token, must contain a letter, and
#            must look like a NAME rather than a word: it carries a digit
#            (gpt-5, o3, Haiku 4.5) or joins two alphanumeric chunks with a
#            space, hyphen, dot, slash, underscore or colon (Claude Opus,
#            claude-opus-5). No list of model names appears anywhere here, so a
#            model released tomorrow passes on the day it ships while "TBD",
#            "?", "x", "auto" and "model" all fail.
#   effort   A genuinely closed vocabulary -- the harness defines it, not the
#            model vendors, so enumerating it is safe and it does not churn.
#            The cell passes if any of those words appears in it, which lets
#            "high", "effort: high" and "high (extended thinking)" through.
#   surface  Free text by design (subagent (background), main conversation, a
#            worktree name). No vocabulary is possible, so the bar is: not a
#            placeholder, at least four characters, and it contains a letter.
#            That rejects the junk a hurried row carries without pretending to
#            validate something this hook cannot see.
#
# The check is a floor, not a proof. It stops an untiered row, not a wrong one.
# ---------------------------------------------------------------------------
PLACEHOLDER_CELLS = {
    "", "-", "--", "---", "—", "–", "_", ".", "..", "...", "…",
    "?", "??", "???", "!", "n/a", "na", "n.a.", "nil", "null", "none", "nan",
    "tbd", "tba", "todo", "to do", "unknown", "unk", "unset", "undefined",
    "x", "xx", "xxx", "y", "yy", "z", "zz", "foo", "bar", "baz", "qux",
    "auto", "automatic", "default", "any", "same", "same as above", "ditto",
    "idem", "model", "effort", "surface", "tier", "fill", "fill in", "fillme",
    "fill me in", "placeholder", "pending", "wip", "tk", "tktk", "later",
    "see above", "as above", "n/k", "unspecified",
}

EFFORT_WORDS = {
    "none", "off", "zero", "minimal", "min", "low", "medium", "med", "moderate",
    "standard", "normal", "default-effort", "high", "higher", "xhigh", "veryhigh",
    "max", "maximum", "ultra", "think", "megathink", "ultrathink", "extended",
}


def _norm(cell: str) -> str:
    """Lowercase, collapse whitespace, drop surrounding punctuation."""
    s = " ".join(str(cell or "").split()).strip().lower()
    return s.strip("`*\"'()[[]{}<>.,;:!")


def _is_placeholder(cell: str) -> bool:
    return _norm(cell) in PLACEHOLDER_CELLS


def names_a_model(cell: str) -> bool:
    s = str(cell or "").strip()
    if _is_placeholder(s) or len(s) < 2:
        return False
    if not any(c.isalpha() for c in s):
        return False
    if any(c.isdigit() for c in s):
        return True
    return bool(re.search(r"[A-Za-z0-9][ \-._/:][A-Za-z0-9]", s))


def names_an_effort(cell: str) -> bool:
    s = _norm(cell)
    if not s or s in PLACEHOLDER_CELLS - EFFORT_WORDS:
        return False
    words = set(re.findall(r"[a-z]+", s))
    return bool(words & EFFORT_WORDS)


def names_a_surface(cell: str) -> bool:
    s = str(cell or "").strip()
    if _is_placeholder(s) or len(s) < 4:
        return False
    return any(c.isalpha() for c in s)


CELL_CHECKS = {
    "model": names_a_model,
    "effort": names_an_effort,
    "surface": names_a_surface,
}


def _populated(cells: dict[str, str]) -> bool:
    """True only if every one of model, effort and surface plausibly names a
    real value. The old version rejected "", "-" and the em dash and nothing
    else, so TBD / ? / x read as tiered (D4)."""
    for name, value in cells.items():
        check = CELL_CHECKS.get(name)
        if check is None:
            if not str(value or "").strip():
                return False
            continue
        if not check(value):
            return False
    return True


ROW_HEADER_NAMES = ("model", "effort", "surface")


def pipe_tables(text: str) -> list:
    """Every Markdown pipe table in the text as (first line number, [lines]).
    A table is a run of consecutive lines that start with `|`; any other line
    ends it."""
    tables, cur, start = [], [], 0
    for n, ln in enumerate(text.splitlines() + [""], 1):
        if ln.strip().startswith("|"):
            if not cur:
                start = n
            cur.append(ln)
        elif cur:
            tables.append((start, cur))
            cur = []
    return tables


def _header_has(line: str, names: tuple) -> bool:
    cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
    return all(any(name in cell for cell in cells) for name in names)


def row_table(text: str):
    """The unit-row table: the first pipe table whose header holds model,
    effort and surface (observation 0361). None when no table qualifies."""
    for start, lines in pipe_tables(text):
        if _header_has(lines[0], ROW_HEADER_NAMES):
            return start, lines
    return None


def row_table_note(path: Path) -> str:
    """One sentence naming the table the guard read, for a refusal message, so
    a refusal never blames the rows when it read the wrong table."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if path.suffix.lower() == ".csv":
        return " It read the CSV header row."
    tables = pipe_tables(text)
    picked = row_table(text)
    if picked is not None:
        return f" It read the table at line {picked[0]} (header: {picked[1][0].strip()})."
    if not tables:
        return " The file holds no pipe table."
    heads = "; ".join(f"line {s}: {t[0].strip()[:80]}" for s, t in tables[:4])
    return (f" None of its {len(tables)} pipe table(s) has a header naming model, effort and surface "
            f"({heads}).")


def ledger_has_populated_row(path: Path) -> bool:
    """True if the ledger names at least one row whose model, effort and
    surface cells all plausibly name a real value. Supports the two forms
    ledger-schema.md allows: a Markdown pipe table, or a CSV with a header."""
    text = path.read_text(encoding="utf-8", errors="replace")
    needed = ("model", "effort", "surface")

    if path.suffix.lower() == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2:
            return False
        header = [h.strip().lower() for h in rows[0]]
        idx = {name: header.index(name) for name in needed if name in header}
        if len(idx) < len(needed):
            return False
        for row in rows[1:]:
            if len(row) <= max(idx.values()):
                continue
            if _populated({name: row[i] for name, i in idx.items()}):
                return True
        return False

    # Markdown pipe table: the first table whose header names model, effort
    # and surface (observation 0361). The header blocks ledger-schema.md puts
    # above the rows (meters, rulings, plan status) are tables too, so the
    # first pipe line of the file is not the row header.
    picked = row_table(text)
    if picked is None:
        return False
    _, lines = picked
    if len(lines) < 2:
        return False
    header_cells = [c.strip().lower() for c in lines[0].strip().strip("|").split("|")]
    idx: dict[str, int] = {}
    for name in needed:
        for i, cell in enumerate(header_cells):
            if name in cell:
                idx[name] = i
                break
    if len(idx) < len(needed):
        return False
    for ln in lines[1:]:
        stripped = ln.strip().strip("|")
        cells = [c.strip() for c in stripped.split("|")]
        # The `|---|---|` (or `|:---:|`) separator row: split FIRST, then check
        # each cell -- checking the raw string's character set was wrong, since
        # the inner "|" separators survive stripping only the outer pair and
        # poison a whole-string subset test (`{'-', '|'} <= {'-', ''}` is False
        # even for a genuine all-dash row).
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        if max(idx.values()) < len(cells) and _populated({name: cells[i] for name, i in idx.items()}):
            return True
    return False


# ---------------------------------------------------------------------------
# Wave-execution caps (SKILL.md section 6; audit finding P1-2, 2026-08-20).
# ---------------------------------------------------------------------------
MAX_CONCURRENT_UNITS = 6
CEILING_LIMIT = 12   # the highest cap a budget file may set (owner raised to 10 on reset eve, 2026-10-06)


def concurrent_cap() -> int:
    """6, or pacewright's unexpired budget-file parallel_ceiling when it is
    higher (never above CEILING_LIMIT). The owner sets that ceiling; a missing,
    expired or malformed file keeps 6. Never raises."""
    try:
        override = os.environ.get("DISPATCH_BUDGET_FILE")
        p = Path(override) if override else Path.home() / ".dispatch" / "budget-decision.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        exp = d.get("expires_at")
        if not isinstance(exp, str):
            return MAX_CONCURRENT_UNITS
        from datetime import datetime, timezone
        if datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            return MAX_CONCURRENT_UNITS
        c = d.get("parallel_ceiling")
        if isinstance(c, bool) or not isinstance(c, int):
            return MAX_CONCURRENT_UNITS
        return max(MAX_CONCURRENT_UNITS, min(c, CEILING_LIMIT))
    except Exception:
        return MAX_CONCURRENT_UNITS

# A row counts as "open" -- part of the concurrent-unit count -- from dispatch
# until it reaches a terminal status. `committed` is still open (the unit is
# still working toward a push); `pushed`, `verified`, `stalled`, `failed`, and
# `resumed` are all terminal here, since stalled/failed/resumed all mean the
# run has already noticed the unit is not quietly holding a wave slot.
OPEN_STATUSES = {"dispatched", "committed"}


def _table_rows(text: str, suffix: str, wanted: tuple) -> list:
    """Every row of a ledger as a dict keyed by the wanted column names, for
    whichever of them the header actually has. Parses the same two formats
    ledger_has_populated_row does (CSV, Markdown pipe table) but returns raw
    cell values for arbitrary columns -- the wave-cap checks need `repo`,
    `worktree`, and `status`, none of which that function reads."""
    rows = []
    if suffix == ".csv":
        parsed = list(csv.reader(io.StringIO(text)))
        if len(parsed) < 2:
            return rows
        header = [h.strip().lower() for h in parsed[0]]
        idx = {}
        for name in wanted:
            for i, cell in enumerate(header):
                if name in cell:
                    idx[name] = i
                    break
        for row in parsed[1:]:
            if not row or (idx and max(idx.values()) >= len(row)):
                continue
            rows.append({name: row[i].strip() for name, i in idx.items()})
        return rows

    # The unit-row table (observation 0361); a ledger with no such table falls
    # back to its first table, the pre-0361 reading.
    picked = row_table(text)
    if picked is None:
        tables = pipe_tables(text)
        if not tables:
            return rows
        picked = tables[0]
    lines = picked[1]
    if len(lines) < 2:
        return rows
    header_cells = [c.strip().lower() for c in lines[0].strip().strip("|").split("|")]
    idx = {}
    for name in wanted:
        for i, cell in enumerate(header_cells):
            if name in cell:
                idx[name] = i
                break
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        if not idx or max(idx.values()) >= len(cells):
            continue
        rows.append({name: cells[i] for name, i in idx.items()})
    return rows


AGENT_COUNT_RE = re.compile(r"(?<![A-Za-z0-9])[xX](\d+)\s*$")  # the token closes the cell (P1e review, 2026-09-11)


def agent_multiplier(surface: str) -> int:
    """How many units a single ledger row is worth against the wave cap
    (observation #0022). A `surface` cell may carry an agent-count token --
    `x<N>` as the LAST thing in the cell, e.g. `subagent (workflow) x245` --
    naming how many agents the one Workflow/Task call behind this row actually
    spawned. Only a closing token counts: a note such as `retried x2 after
    timeout` in the middle of the cell is prose, not a count (a review of this
    change found the earlier any-position match inflated such rows). Anything that is not a positive integer --
    no token, `x` with no digits after it, `x0` -- defaults to 1, the same
    weight a row with no token at all carries: a missing or broken count must
    never make a row cheaper than a plain single-agent row, only a real
    number ever makes it more expensive."""
    matches = AGENT_COUNT_RE.findall(str(surface or ""))
    if not matches:
        return 1
    try:
        n = int(matches[-1])
    except ValueError:
        return 1
    return n if n > 0 else 1


def open_unit_count(path: Path) -> int:
    """Sum of agent weight across rows still open per OPEN_STATUSES, not a
    row count. A row with no status column, or a placeholder status, counts
    as open -- an unlabeled row is exactly the case a cap exists to catch,
    not a reason to exempt it. Each open row is worth `agent_multiplier()` of
    its `surface` cell (observation #0022) so a single Workflow row that fans
    out to N agents costs N against the cap, matching what SKILL.md section 6
    already says in prose."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    rows = _table_rows(text, path.suffix.lower(), ("status", "surface"))
    count = 0
    for row in rows:
        status = _norm(row.get("status", ""))
        if not status or status in PLACEHOLDER_CELLS or status in OPEN_STATUSES:
            count += agent_multiplier(row.get("surface", ""))
    return count


def repo_collision(path: Path) -> str | None:
    """The first repo with 2+ open rows that both write the main tree (no
    worktree/branch value) -- the one-writer-per-repo violation SKILL.md
    section 6 names. None if every repo with more than one open row has each
    writer isolated in its own worktree."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    rows = _table_rows(text, path.suffix.lower(), ("status", "repo", "worktree"))
    bare_writers: dict = {}
    for row in rows:
        status = _norm(row.get("status", ""))
        is_open = (not status) or (status in PLACEHOLDER_CELLS) or (status in OPEN_STATUSES)
        if not is_open:
            continue
        repo = _norm(row.get("repo", ""))
        worktree = _norm(row.get("worktree", ""))
        if not repo or repo in PLACEHOLDER_CELLS:
            continue
        if worktree and worktree not in PLACEHOLDER_CELLS:
            continue  # isolated in its own worktree -- not a collision
        bare_writers[repo] = bare_writers.get(repo, 0) + 1
    for repo, n in bare_writers.items():
        if n >= 2:
            return repo
    return None


# ---------------------------------------------------------------------------
# Usage windows (dispatchwright 1.3.0, pacewright's references/window-fit.md). The reader
# is duplicated in dispatch_gate.py on purpose: each hook installs alone into
# ~/.claude/hooks/ and imports nothing beside itself.
# ---------------------------------------------------------------------------
WINDOWS_STALE_SECONDS = 15 * 60
WINDOWS_CLOCK_SKEW_SECONDS = 5 * 60
DEFAULT_STOP_PCT = 95.0   # the documented stop band (dispatchwright meters.md); a default, not a measurement
STOP_PCT_RANGE = (50.0, 95.0)   # a budget file may tighten the band, never relax it (pacewright section 5)
SAFETY_MARGIN = 0.15
WINDOW_LABELS = (("five_hour", "5h"), ("seven_day", "7d"))
STOP_WINDOWS = (("five_hour", "5-hour"), ("seven_day", "7-day"))


def stop_band() -> tuple[float, str]:
    """(stop percent, source). pacewright's unexpired budget file's
    `stop_bands.stop` when it is a number in STOP_PCT_RANGE, else the
    documented 95% default. Never raises (K8a, audit K7-2-22: the guard held
    its own 97% literal on the 5-hour window only)."""
    try:
        override = os.environ.get("DISPATCH_BUDGET_FILE")
        p = Path(override) if override else Path.home() / ".dispatch" / "budget-decision.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        exp = d.get("expires_at")
        from datetime import datetime, timezone
        if datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            return DEFAULT_STOP_PCT, "default"
        v = (d.get("stop_bands") or {}).get("stop")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return DEFAULT_STOP_PCT, "default"
        if not STOP_PCT_RANGE[0] <= float(v) <= STOP_PCT_RANGE[1]:
            return DEFAULT_STOP_PCT, f"default (budget file stop {float(v):g} is outside 50-95, clamped)"
        return float(v), "budget file"
    except Exception:
        return DEFAULT_STOP_PCT, "default"


HOOKS_DIR = Path(__file__).resolve().parent


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
    object, or (unless fixture) older than WINDOWS_STALE_SECONDS. None means
    'say nothing' here, never 'block'."""
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


def _pct_of(windows: dict | None, key: str):
    w = (windows or {}).get(key)
    if not isinstance(w, dict):
        return None
    v = w.get("used_percentage")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def tokens_per_percent(cal: dict | None, key: str) -> float | None:
    """The measured tokens-per-percent for a window, or None when there is no
    measurement (no file, no entry, zero samples, or a non-number)."""
    wins = (cal or {}).get("windows")
    entry = wins.get(key) if isinstance(wins, dict) else None
    if not isinstance(entry, dict):
        return None
    tpp = entry.get("tokens_per_percent")
    samples = entry.get("samples")
    if isinstance(tpp, bool) or not isinstance(tpp, (int, float)) or tpp <= 0:
        return None
    if not isinstance(samples, int) or samples < 1:
        return None
    return float(tpp)


def safety_margin(cal: dict | None) -> float:
    m = (cal or {}).get("margin")
    if isinstance(m, bool) or not isinstance(m, (int, float)) or not (0 <= m < 1):
        return SAFETY_MARGIN
    return float(m)


_TOKENS_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?")


def parse_tokens(cell: str) -> int | None:
    """The leading number of an estimated_tokens cell: `60000`, `60,000`,
    `60k (median of 4 rows)`, `1.2M (owner)`. None when there is no number --
    the caller counts that as 0 and names the cell."""
    m = _TOKENS_RE.search(str(cell or ""))
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    if unit == "k":
        n *= 1_000
    elif unit == "m":
        n *= 1_000_000
    return int(n)


def _is_open(row: dict) -> bool:
    status = _norm(row.get("status", ""))
    return (not status) or (status in PLACEHOLDER_CELLS) or (status in OPEN_STATUSES)


def open_rows(path: Path) -> list:
    """Every open row as a dict of the cells the window step reads."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    rows = _table_rows(text, path.suffix.lower(), ("unit_id", "status", "surface", "estimated_tokens", "window"))
    return [r for r in rows if _is_open(r)]


def estimated_open_tokens(path: Path) -> tuple[int, list]:
    """(sum of estimated_tokens over open rows, taken exactly as written; the
    unit ids whose cell carried no number).

    No re-weighting by the surface cell's x<N> agent-count token happens
    here: the plan's estimate for a fan-out row is already N x per-agent
    (pacewright's references/window-fit.md, ledger-schema.md's estimated_tokens field),
    so multiplying again would double-count. The x<N> token weights the
    wave cap in open_unit_count(), not this sum."""
    total = 0
    unreadable = []
    for row in open_rows(path):
        n = parse_tokens(row.get("estimated_tokens", ""))
        if n is None:
            unreadable.append(row.get("unit_id") or "?")
            continue
        total += n
    return total, unreadable


def all_open_rows_next(path: Path) -> bool:
    rows = open_rows(path)
    if not rows:
        return False
    return all(_norm(r.get("window", "")).startswith("next") for r in rows)


def is_resume_call(data: dict) -> bool:
    """The owner's explicit resume, read off the call itself: any string
    value in tool_input carries the word 'resume'. Coarse by design."""
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return False
    for v in ti.values():
        if isinstance(v, str) and re.search(r"\bresum(e|ed|ing)\b", v, re.I):
            return True
    return False


def _local(ts, fmt: str) -> str:
    try:
        return time.strftime(fmt, time.localtime(float(ts)))
    except Exception:
        return ""


def record_pct_at_dispatch(path: Path, windows: dict) -> bool:
    """Fill each open row's EMPTY `pct_at_dispatch` cell with `5h=<pct> 7d=<pct>`.
    Markdown ledgers only; the file's own line ending is kept; only the
    target cell's bytes change. Returns True when something was written.
    Never raises -- a failed write is not a reason to block a dispatch."""
    try:
        if path.suffix.lower() != ".md":
            return False
        parts = []
        for key, label in WINDOW_LABELS:
            pct = _pct_of(windows, key)
            if pct is not None:
                parts.append(f"{label}={pct:g}")
        if not parts:
            return False
        value = " ".join(parts)
        raw = path.read_bytes()
        eol = b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") - raw.count(b"\r\n") else b"\n"
        lines = raw.split(eol)
        header_idx = None
        col = status_col = None
        for i, ln in enumerate(lines):
            s = ln.decode("utf-8", errors="replace")
            if s.strip().startswith("|"):
                cells = [c.strip().lower() for c in s.strip().strip("|").split("|")]
                if "pct_at_dispatch" in cells:
                    header_idx, col = i, cells.index("pct_at_dispatch")
                    status_col = next((j for j, c in enumerate(cells) if "status" in c), None)
                    break
        if header_idx is None:
            return False
        changed = False
        for i in range(header_idx + 1, len(lines)):
            s = lines[i].decode("utf-8", errors="replace")
            if not s.strip().startswith("|"):
                if s.strip():
                    break  # the table ended
                continue
            bars = [j for j, ch in enumerate(s) if ch == "|"]
            if len(bars) < col + 2:
                continue
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            status = cells[status_col] if status_col is not None and status_col < len(cells) else ""
            if not _is_open({"status": status}):
                continue
            cell = s[bars[col] + 1:bars[col + 1]]
            if cell.strip() and _norm(cell) not in PLACEHOLDER_CELLS:
                continue
            s = s[:bars[col] + 1] + f" {value} " + s[bars[col + 1]:]
            lines[i] = s.encode("utf-8")
            changed = True
        if changed:
            # Atomic: a crash mid-write must not truncate the live ledger (K7-2-24).
            tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            try:
                tmp_path.write_bytes(eol.join(lines))
                os.replace(tmp_path, path)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
        return changed
    except Exception:
        return False


def window_step(ledger: Path, data: dict, fixture_windows: Path | None = None,
                fixture_cal: Path | None = None) -> tuple[int, str | None, str | None]:
    """(exit code, stderr reason or None, additionalContext line or None) for
    the usage-window rule in the docstring. Runs only after the ledger checks
    have passed; exit 2 here is the stop-band block and nothing else."""
    fixture = fixture_windows is not None
    windows = read_windows(fixture_windows or windows_path(), fixture=fixture)
    if windows is None:
        return 0, None, None
    cal = read_calibration(fixture_cal or calibration_path())
    stop, stop_src = stop_band()
    for key, name in STOP_WINDOWS:
        used = _pct_of(windows, key)
        if used is None or used < stop:
            continue
        # Deferred wave, explicit resume: the stop-band reading is stale by construction.
        if all_open_rows_next(ledger) and is_resume_call(data):
            continue
        fmt = "%H:%M" if key == "five_hour" else "%a %H:%M"
        when = _local((windows.get(key) or {}).get("resets_at"), fmt) or "unknown"
        return 2, (
            f"dispatch_ledger_guard: the {name} usage window is {used:g}% used (>= "
            f"{stop:g}%, the {stop_src} stop band); it resets at {when} local. A unit launched now dies "
            "mid-write. Wait for the reset, or -- if this wave was already fitted to the next "
            "window (every open row's `window` cell says `next`) -- launch it as an explicit "
            "resume once the window has rolled. See pacewright's references/window-fit.md."
        ), None
    est, unreadable = estimated_open_tokens(ledger)
    margin = safety_margin(cal)
    warnings = []
    for key, label in WINDOW_LABELS:
        used = _pct_of(windows, key)
        tpp = tokens_per_percent(cal, key)
        if used is None or tpp is None:
            continue
        remaining = (100.0 - used) * tpp * (1.0 - margin)
        if remaining < est:
            when = _local((windows.get(key) or {}).get("resets_at"), "%H:%M" if key == "five_hour" else "%a %H:%M")
            warnings.append(
                f"{label} {used:g}% used, remaining allowance ~{int(remaining):,} tokens after a "
                f"{int(margin * 100)}% margin at {int(tpp):,} tokens/% -- below the {est:,} tokens "
                f"the open rows estimate" + (f"; resets {when}" if when else "")
            )
    context = None
    if warnings:
        context = (
            "dispatch_ledger_guard WARNING (usage windows): " + " · ".join(warnings) + ". "
            "Split the wave at a unit boundary so the remainder waits for the reset "
            "(pacewright's references/window-fit.md), or confirm with the owner before launching."
            + (f" Rows with no readable estimated_tokens counted as 0: {', '.join(unreadable)}." if unreadable else "")
        )
    if not fixture:
        record_pct_at_dispatch(ledger, windows)
    return 0, None, context


TIERED_LEDGER = (
    "| unit_id | task | class | model | effort | surface |\n"
    "|---------|------|-------|-------|--------|---------|\n"
    "| U1 | thing | judgment | Claude Opus 5 | high | subagent (background) |\n"
)


def _run_guard_full(payload, flag: dict | None, tmp: Path, env_extra: dict | None = None,
                    argv: list | None = None) -> tuple[int, str, str]:
    """Run this file as the real hook, in a subprocess, against a temp flag.
    The selftest asserts on EXIT CODES, not on internal returns -- D2 was
    exactly the kind of bug an internals-only test cannot see. Returns
    (exit code, stdout, stderr)."""
    flag_file = tmp / "flag.json"
    if flag is None:
        if flag_file.exists():
            flag_file.unlink()
    else:
        flag_file.write_text(json.dumps(flag), encoding="utf-8")
    env = dict(os.environ)
    env["CLAUDE_DISPATCH_FLAG"] = str(flag_file)
    env.pop("CLAUDE_DISPATCH_LEDGER", None)
    # Isolate every case from the live windows and calibration files: a fresh
    # reading on the rig must not change what the pre-1.3.0 cases see.
    env["CLAUDE_USAGE_WINDOWS"] = str(tmp / "no-usage-windows.json")
    env["CLAUDE_USAGE_CALIBRATION"] = str(tmp / "no-usage-calibration.json")
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + list(argv or []),
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_guard(payload, flag: dict | None, tmp: Path, env_extra: dict | None = None) -> int:
    return _run_guard_full(payload, flag, tmp, env_extra)[0]


def selftest() -> int:
    """Covers the four fixed defects at the exit-code level, plus the flag and
    parsing logic. Every case names the defect it guards, so a future edit that
    reopens one fails here by name."""
    problems = []
    now = time.time()

    # --- flag logic, including D1 ---------------------------------------
    live = {"session_id": "abc", "ts": now}
    if flag_state(live, "abc") != "live":
        problems.append("a fresh flag with a matching session id should read live")
    if flag_state(live, "different-session") != "other-session":
        problems.append("a flag from a different session id should not enforce")
    if flag_state({"session_id": "abc", "ts": now - STALE_SECONDS - 3600}, "abc") != "stale":
        problems.append("a flag older than STALE_SECONDS should read stale")
    if flag_state(None, "abc") != "absent":
        problems.append("a missing flag should never enforce")
    # D1: the payload carries no session id.
    if flag_state(live, "") != "uncorrelated":
        problems.append("D1: a fresh flag plus an empty payload session id must enforce, not skip")
    if flag_state({"session_id": "unknown-session", "ts": now}, "abc") != "uncorrelated":
        problems.append("D1: a fresh flag whose own session id is the unknown sentinel must enforce")
    if flag_state({"session_id": "abc", "ts": now - STALE_SECONDS - 3600}, "") != "stale":
        problems.append("D1: a stale flag must still be stale even with no payload session id")

    # --- cell validators, D4 --------------------------------------------
    for good in ("Claude Opus 5", "Claude Haiku 4.5", "claude-sonnet-5", "gpt-5", "o3", "Claude Opus"):
        if not names_a_model(good):
            problems.append(f"D4: a real model name was rejected: {good!r}")
    for junk in ("", "-", "—", "TBD", "?", "x", "auto", "model", "n/a", "  "):
        if names_a_model(junk):
            problems.append(f"D4: a placeholder passed as a model name: {junk!r}")
    for good in ("none", "low", "medium", "high", "max", "effort: high", "high (extended thinking)"):
        if not names_an_effort(good):
            problems.append(f"D4: a real effort was rejected: {good!r}")
    for junk in ("", "-", "?", "x", "TBD", "42", "???"):
        if names_an_effort(junk):
            problems.append(f"D4: a placeholder passed as an effort: {junk!r}")
    for good in ("subagent (background)", "main conversation", "worktree wt-1", "cloud routine"):
        if not names_a_surface(good):
            problems.append(f"D4: a real surface was rejected: {good!r}")
    for junk in ("", "-", "?", "x", "TBD", "n/a", "  "):
        if names_a_surface(junk):
            problems.append(f"D4: a placeholder passed as a surface: {junk!r}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # --- ledger parsing ---------------------------------------------
        empty_md = tmp / "empty.md"
        empty_md.write_text(
            "| unit_id | task | class | model | effort | surface |\n"
            "|---|---|---|---|---|---|\n"
            "| U1 | thing | mechanical |  |  |  |\n",
            encoding="utf-8",
        )
        if ledger_has_populated_row(empty_md):
            problems.append("an all-blank ledger row was read as populated")

        junk_md = tmp / "junk.md"
        junk_md.write_text(
            "| unit_id | task | class | model | effort | surface |\n"
            "|---|---|---|---|---|---|\n"
            "| U1 | thing | mechanical | TBD | ? | x |\n",
            encoding="utf-8",
        )
        if ledger_has_populated_row(junk_md):
            problems.append("D4: a row of TBD / ? / x was read as tiered")

        filled_md = tmp / "filled.md"
        filled_md.write_text(TIERED_LEDGER, encoding="utf-8")
        if not ledger_has_populated_row(filled_md):
            problems.append("a fully-populated ledger row was not recognized")

        filled_csv = tmp / "filled.csv"
        filled_csv.write_text(
            "unit_id,task,class,model,effort,surface\n"
            "U1,thing,mechanical,Claude Haiku 4.5,none,subagent (background)\n",
            encoding="utf-8",
        )
        if not ledger_has_populated_row(filled_csv):
            problems.append("a fully-populated CSV ledger row was not recognized")

        junk_csv = tmp / "junk.csv"
        junk_csv.write_text(
            "unit_id,task,class,model,effort,surface\nU1,thing,mechanical,TBD,?,x\n",
            encoding="utf-8",
        )
        if ledger_has_populated_row(junk_csv):
            problems.append("D4: a CSV row of TBD / ? / x was read as tiered")

        # --- ledger currency, D3 -----------------------------------------
        fresh_dir = tmp / "fresh" / ".dispatch" / "runs" / "r1"
        fresh_dir.mkdir(parents=True)
        fresh_ledger = fresh_dir / "ledger.md"
        fresh_ledger.write_text(TIERED_LEDGER, encoding="utf-8")
        if not ledger_is_current(fresh_ledger, "abc"):
            problems.append("a ledger written just now should read as current")
        if find_ledger(str(tmp / "fresh"), "abc") is None:
            problems.append("find_ledger did not locate a fresh ledger under .dispatch/runs/*/")

        old_dir = tmp / "old" / ".dispatch" / "runs" / "2020-01-01-ancient"
        old_dir.mkdir(parents=True)
        old_ledger = old_dir / "ledger.md"
        old_ledger.write_text(TIERED_LEDGER, encoding="utf-8")
        ancient = now - STALE_SECONDS - 3600
        os.utime(old_ledger, (ancient, ancient))
        if ledger_is_current(old_ledger, "abc"):
            problems.append("D3: a ledger older than the flag's window read as current")
        if find_ledger(str(tmp / "old"), "abc") is not None:
            problems.append("D3: find_ledger returned a stale ledger, which is the permanent-disarm bug")

        marked_dir = tmp / "marked" / ".dispatch" / "runs" / "r1"
        marked_dir.mkdir(parents=True)
        marked = marked_dir / "ledger.md"
        marked.write_text(TIERED_LEDGER + "\nsession: sess-xyz\n", encoding="utf-8")
        os.utime(marked, (ancient, ancient))
        if not ledger_is_current(marked, "sess-xyz"):
            problems.append("a ledger naming the current session should stay current despite its mtime")
        if ledger_is_current(marked, "some-other-session"):
            problems.append("D3: an old ledger naming a DIFFERENT session read as current")

        missing = find_ledger(str(tmp / "nothing-here"), "abc")
        if missing is not None:
            problems.append("find_ledger found a ledger in a directory with no .dispatch/runs/ tree")

        # --- wave-cap enforcement, 2026-08-20 audit P1-2 ---------------------
        def _row(unit_id, repo="—", worktree="—", status="dispatched"):
            return (
                f"| {unit_id} | thing | mechanical | Claude Opus 5 | high | "
                f"subagent (background) | {repo} | {worktree} | x | 1 | t | | | | | {status} |"
            )

        header = (
            "| unit_id | task | class | model | effort | surface | repo | worktree | "
            "expected_artifacts | estimated_tokens | dispatch_ts | commit_sha | commit_ts | "
            "push_ts | remote_sha | status |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        )

        under_cap = tmp / "under_cap.md"
        under_cap.write_text(header + "\n".join(_row(f"U{i}") for i in range(1, 4)), encoding="utf-8")
        if open_unit_count(under_cap) != 3:
            problems.append("open_unit_count miscounted 3 dispatched rows")

        over_cap = tmp / "over_cap.md"
        over_cap.write_text(header + "\n".join(_row(f"U{i}") for i in range(1, 8)), encoding="utf-8")
        if open_unit_count(over_cap) != 7:
            problems.append("open_unit_count miscounted 7 dispatched rows")

        # The cap from pacewright's budget file (2026-10-06). Every later check in
        # this selftest (and its subprocesses) sees no budget file, so 6 holds.
        from datetime import datetime, timedelta, timezone
        bud = tmp / "budget.json"
        fut = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        os.environ["DISPATCH_BUDGET_FILE"] = str(bud)
        for ceiling, exp, want in ((10, fut, 10), (20, fut, CEILING_LIMIT), (3, fut, 6),
                                   (10, past, 6), ("10", fut, 6)):
            bud.write_text(json.dumps({"expires_at": exp, "parallel_ceiling": ceiling}), encoding="utf-8")
            if concurrent_cap() != want:
                problems.append(f"concurrent_cap: ceiling {ceiling!r} expiring {exp} gave "
                                f"{concurrent_cap()}, want {want}")
        bud.write_text("{not json", encoding="utf-8")
        if concurrent_cap() != 6:
            problems.append("concurrent_cap: a malformed budget file did not keep 6")
        os.environ["DISPATCH_BUDGET_FILE"] = str(tmp / "no-budget.json")

        mixed_terminal = tmp / "mixed_terminal.md"
        rows = [_row(f"U{i}") for i in range(1, 6)] + [
            _row("U6", status="pushed"), _row("U7", status="verified"),
        ]
        mixed_terminal.write_text(header + "\n".join(rows), encoding="utf-8")
        if open_unit_count(mixed_terminal) != 5:
            problems.append("open_unit_count counted a pushed/verified row as still open")

        no_collision = tmp / "no_collision.md"
        no_collision.write_text(
            header + "\n".join(
                [_row("U1", repo="workshop", worktree="wt-u1"), _row("U2", repo="workshop", worktree="wt-u2")]
            ),
            encoding="utf-8",
        )
        if repo_collision(no_collision) is not None:
            problems.append("repo_collision flagged two writers that each have their own worktree")

        yes_collision = tmp / "yes_collision.md"
        yes_collision.write_text(
            header + "\n".join(
                [_row("U1", repo="workshop", worktree="—"), _row("U2", repo="workshop", worktree="—")]
            ),
            encoding="utf-8",
        )
        if repo_collision(yes_collision) != "workshop":
            problems.append("repo_collision missed two bare-tree writers on the same repo")

        different_repos = tmp / "different_repos.md"
        different_repos.write_text(
            header + "\n".join(
                [_row("U1", repo="workshop", worktree="—"), _row("U2", repo="citadel", worktree="—")]
            ),
            encoding="utf-8",
        )
        if repo_collision(different_repos) is not None:
            problems.append("repo_collision flagged two bare-tree writers on DIFFERENT repos")

        # --- agent-count token in the surface cell, observation #0022 -------
        for good, want in (
            ("subagent (workflow) x245", 245),
            ("subagent (workflow) x1", 1),
            ("subagent (background) X12", 12),
            ("subagent (workflow) x245 ", 245),
        ):
            if agent_multiplier(good) != want:
                problems.append(f"0022: agent_multiplier({good!r}) should be {want}, "
                                 f"got {agent_multiplier(good)}")
        for plain in ("subagent (background)", "main conversation", "worktree wt-1", "cloud routine"):
            if agent_multiplier(plain) != 1:
                problems.append(f"0022: a surface cell with no token should default to 1: {plain!r}")
        for malformed in ("subagent (workflow) x", "subagent (workflow) x0", "subagent (workflow) xN",
                           "subagent (workflow) x-5", "boxed245", "",
                           "x9 subagent (workflow)", "subagent (background) - retried x2 after timeout"):
            if agent_multiplier(malformed) != 1:
                problems.append(f"0022: a malformed/absent token should default to 1, not zero out "
                                 f"the row: {malformed!r} -> {agent_multiplier(malformed)}")
        if agent_multiplier("subagent (workflow) x3 then x245") != 245:
            problems.append("0022: two tokens in one cell should take the LAST one")

        workflow_row = (
            "| unit_id | task | class | model | effort | surface | repo | worktree | "
            "expected_artifacts | estimated_tokens | dispatch_ts | commit_sha | commit_ts | "
            "push_ts | remote_sha | status |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| V-A | verify findings | judgment | Claude Opus 5 | high | "
            "subagent (workflow) x245 | — | — | x | 1 | t | | | | | dispatched |"
        )
        one_workflow_row = tmp / "one_workflow_row.md"
        one_workflow_row.write_text(workflow_row, encoding="utf-8")
        if open_unit_count(one_workflow_row) != 245:
            problems.append(f"0022: a single ledger row of 'x245' agents should count as 245 open "
                             f"units, got {open_unit_count(one_workflow_row)} -- the exact failure "
                             f"mode that hid 245 refuters from the wave cap")

        # --- real exit codes ---------------------------------------------
        fresh_flag = {"session_id": "abc", "ts": now}
        no_ledger_dir = tmp / "bare"
        no_ledger_dir.mkdir()

        cases = [
            # (label, payload, flag, expected exit)
            ("a non-gated tool is never touched",
             {"tool_name": "Read", "session_id": "abc", "cwd": str(no_ledger_dir)}, fresh_flag, 0),
            ("no flag on disk means nothing is armed",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(no_ledger_dir)}, None, 0),
            ("a stale flag means nothing is armed",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(no_ledger_dir)},
             {"session_id": "abc", "ts": now - STALE_SECONDS - 3600}, 0),
            ("another session's flag is not ours",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(no_ledger_dir)},
             {"session_id": "zzz", "ts": now}, 0),
            ("armed and no ledger blocks",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(no_ledger_dir)}, fresh_flag, 2),
            ("armed with a tiered fresh ledger allows",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "fresh")}, fresh_flag, 0),
            # D1
            ("D1: no session id in the payload must still enforce",
             {"tool_name": "Task", "tool_input": {"prompt": "x"}, "cwd": str(no_ledger_dir)}, fresh_flag, 2),
            ("D1: no session id, but a tiered fresh ledger, still allows",
             {"tool_name": "Task", "tool_input": {"prompt": "x"}, "cwd": str(tmp / "fresh")}, fresh_flag, 0),
            # D2
            ("D2: an unreadable ledger blocks with 2, never 1",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "trap")}, fresh_flag, 2),
            ("D2: unparseable stdin blocks with 2, never 1",
             "{not json at all", fresh_flag, 2),
            ("D2: empty stdin blocks with 2, never 1", "", fresh_flag, 2),
            # D3
            ("D3: a stale populated ledger no longer passes",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "old")}, fresh_flag, 2),
            # D4
            ("D4: a ledger of junk cells no longer passes",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "junkrun")}, fresh_flag, 2),
            # Wave-cap enforcement, audit P1-2
            ("P1-2: a ledger with 7 open units blocks over the 6-unit cap",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "overcaprun")}, fresh_flag, 2),
            ("P1-2: a ledger with 6 open units stays inside the cap and allows",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "atcaprun")}, fresh_flag, 0),
            ("P1-2: two bare-tree writers on the same repo block",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "collisionrun")}, fresh_flag, 2),
            ("P1-2: two writers on the same repo each in their own worktree allow",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "isolatedrun")}, fresh_flag, 0),
            # observation #0022 -- agent-count token
            ("0022: one 'x245' Workflow row blocks over the cap by itself",
             {"tool_name": "Task", "session_id": "abc", "cwd": str(tmp / "agentcountrun")}, fresh_flag, 2),
        ]

        # D2 fixture: ledger.md is a directory, so read_text throws.
        (tmp / "trap" / ".dispatch" / "runs" / "r1" / "ledger.md").mkdir(parents=True)
        # D4 fixture: a fresh ledger whose only row is junk.
        junk_run = tmp / "junkrun" / ".dispatch" / "runs" / "r1"
        junk_run.mkdir(parents=True)
        (junk_run / "ledger.md").write_text(junk_md.read_text(encoding="utf-8"), encoding="utf-8")

        # Wave-cap fixtures, audit P1-2.
        overcap_run = tmp / "overcaprun" / ".dispatch" / "runs" / "r1"
        overcap_run.mkdir(parents=True)
        (overcap_run / "ledger.md").write_text(over_cap.read_text(encoding="utf-8"), encoding="utf-8")

        atcap_run = tmp / "atcaprun" / ".dispatch" / "runs" / "r1"
        atcap_run.mkdir(parents=True)
        atcap_rows = header + "\n".join(_row(f"U{i}") for i in range(1, 7))
        (atcap_run / "ledger.md").write_text(atcap_rows, encoding="utf-8")

        collision_run = tmp / "collisionrun" / ".dispatch" / "runs" / "r1"
        collision_run.mkdir(parents=True)
        (collision_run / "ledger.md").write_text(yes_collision.read_text(encoding="utf-8"), encoding="utf-8")

        isolated_run = tmp / "isolatedrun" / ".dispatch" / "runs" / "r1"
        isolated_run.mkdir(parents=True)
        (isolated_run / "ledger.md").write_text(no_collision.read_text(encoding="utf-8"), encoding="utf-8")

        # observation #0022 fixture.
        agentcount_run = tmp / "agentcountrun" / ".dispatch" / "runs" / "r1"
        agentcount_run.mkdir(parents=True)
        (agentcount_run / "ledger.md").write_text(workflow_row, encoding="utf-8")

        for label, payload, flag, expected in cases:
            code = _run_guard(payload, flag, tmp)
            if code != expected:
                problems.append(f"{label}: expected exit {expected}, got {code}")
            if code not in (0, 2):
                problems.append(f"{label}: exit {code} is neither allow (0) nor block (2)")

        # --- usage windows, dispatchwright 1.3.0 -----------------------------
        # Windows files in the shape usage_windows.py writes from the documented
        # statusline payload; only written_at is minted here, as the flag's ts is.
        def _windows_file(name, written_at, five=23.5, seven=41.2):
            p = tmp / name
            p.write_text(json.dumps({
                "written_at": written_at,
                "model": {"id": "claude-opus-5", "display_name": "Opus"},
                "five_hour": {"used_percentage": five, "resets_at": 1738425600},
                "seven_day": {"used_percentage": seven, "resets_at": 1738857600},
                "spend_limit": None,
            }), encoding="utf-8")
            return str(p)

        w_fresh = _windows_file("w-fresh.json", now)
        w_block = _windows_file("w-block.json", now, five=97.5)
        w_block_stale = _windows_file("w-block-stale.json", now - WINDOWS_STALE_SECONDS - 60, five=97.5)
        # Under the 95% stop band, so the 7d WARNING path is reached (K8a: at 98% the weekly stop blocks).
        w_week = _windows_file("w-week.json", now, seven=94.5)
        w_five_stop = _windows_file("w-five-stop.json", now, five=95.5)
        w_week_stop = _windows_file("w-week-stop.json", now, seven=96.0)
        w_five_92 = _windows_file("w-five-92.json", now, five=92.0)
        bud_stop90 = tmp / "budget-stop90.json"
        bud_stop90.write_text(json.dumps({"expires_at": "2099-01-01T00:00:00Z",
                                          "stop_bands": {"slow": 80, "stop": 90}}), encoding="utf-8")
        bud_stop99 = tmp / "budget-stop99.json"
        bud_stop99.write_text(json.dumps({"expires_at": "2099-01-01T00:00:00Z",
                                          "stop_bands": {"slow": 80, "stop": 99}}), encoding="utf-8")
        bud_stop_bad = tmp / "budget-stop-bad.json"
        bud_stop_bad.write_text(json.dumps({"expires_at": "2099-01-01T00:00:00Z",
                                            "stop_bands": {"stop": "high"}}), encoding="utf-8")
        cal_ok = tmp / "cal-ok.json"
        cal_ok.write_text(json.dumps({"windows": {
            "five_hour": {"tokens_per_percent": 41000, "samples": 3},
            "seven_day": {"tokens_per_percent": 50000, "samples": 2},
        }}), encoding="utf-8")
        cal_tiny = tmp / "cal-tiny.json"
        cal_tiny.write_text(json.dumps({"windows": {
            "five_hour": {"tokens_per_percent": 10, "samples": 1},
        }}), encoding="utf-8")
        cal_none = tmp / "cal-none.json"
        cal_none.write_text(json.dumps({"windows": {"five_hour": {"tokens_per_percent": None, "samples": 0}}}),
                            encoding="utf-8")

        header13 = (
            "| unit_id | task | class | model | effort | surface | repo | worktree | "
            "expected_artifacts | estimated_tokens | est_wall | window | pct_at_dispatch | "
            "pct_at_reconcile | dispatch_ts | commit_sha | commit_ts | push_ts | remote_sha | status |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        )

        def _row13(unit_id, est="400000 (owner)", window="this 5-hour window", pct="", status="dispatched"):
            return (
                f"| {unit_id} | thing | judgment | Claude Opus 5 | high | subagent (background) | — | — | x | "
                f"{est} | 9 min | {window} | {pct} | | t | | | | | {status} |"
            )

        def _run13(name, rows, header=header13):
            d = tmp / name / ".dispatch" / "runs" / "r1"
            d.mkdir(parents=True)
            (d / "ledger.md").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
            return d / "ledger.md"

        led_plain = _run13("w-plain", [_row13("U1"), _row13("U2", est="60k (median of 4 rows)")])
        led_next = _run13("w-next", [_row13("U3", window="next 5-hour window at 11:00"),
                                     _row13("U4", window="next 5-hour window at 11:00")])
        led_mixed = _run13("w-mixed", [_row13("U3", window="next 5-hour window at 11:00"),
                                       _row13("U4", window="this 5-hour window")])
        led_record = _run13("w-record", [_row13("U1"), _row13("U2", pct="5h=1 7d=2"),
                                         _row13("U9", status="verified")])
        led_bad_cell = _run13("w-badcell", [_row13("U1", est="a lot"), _row13("U2", est="500000 (owner)")])
        resume_call = {"tool_name": "Task", "session_id": "abc",
                       "tool_input": {"description": "dispatchwright resume U3", "prompt": "resume U3 from its ledger row"}}
        plain_call = {"tool_name": "Task", "session_id": "abc",
                      "tool_input": {"description": "verify findings", "prompt": "check the findings"}}

        # (label, payload, env, expected exit, must-contain in stdout+stderr, must-not-contain)
        window_cases = [
            ("1.3.0: no windows file says nothing and allows",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {}, 0, (), ("WARNING", "5-hour usage window")),
            ("1.3.0: a stale windows file at 97.5% neither blocks nor warns",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {"CLAUDE_USAGE_WINDOWS": w_block_stale}, 0, (),
             ("WARNING", "5-hour usage window")),
            ("1.3.0: a fresh windows file at 97.5% blocks and names the reset time",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {"CLAUDE_USAGE_WINDOWS": w_block}, 2,
             ("97.5% used", "resets at"), ()),
            ("1.3.0: 97.5%, every open row deferred to next, and an explicit resume allows",
             {**resume_call, "cwd": str(tmp / "w-next")}, {"CLAUDE_USAGE_WINDOWS": w_block}, 0, (),
             ("5-hour usage window",)),
            ("1.3.0: 97.5% with next rows but no resume word still blocks",
             {**plain_call, "cwd": str(tmp / "w-next")}, {"CLAUDE_USAGE_WINDOWS": w_block}, 2,
             ("97.5% used",), ()),
            ("1.3.0: 97.5% on a resume where one open row is not deferred still blocks",
             {**resume_call, "cwd": str(tmp / "w-mixed")}, {"CLAUDE_USAGE_WINDOWS": w_block}, 2,
             ("97.5% used",), ()),
            ("1.3.0: ample allowance allows with no warning",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_fresh, "CLAUDE_USAGE_CALIBRATION": str(cal_ok)}, 0, (), ("WARNING",)),
            ("1.3.0: a tiny 5h calibration warns with the numbers and still allows",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_fresh, "CLAUDE_USAGE_CALIBRATION": str(cal_tiny)}, 0,
             ("WARNING", "additionalContext", "5h 23.5% used", "460,000 tokens"), ()),
            ("1.3.0: a nearly spent 7d window warns on the 7d calibration",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_week, "CLAUDE_USAGE_CALIBRATION": str(cal_ok)}, 0,
             ("WARNING", "7d 94.5% used"), ("5h 23.5% used",)),
            ("1.3.0: no calibration means no comparison, no warning",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_fresh, "CLAUDE_USAGE_CALIBRATION": str(cal_none)}, 0, (), ("WARNING",)),
            ("1.3.0: an unreadable estimated_tokens cell counts as 0 and is named in the warning",
             {**plain_call, "cwd": str(tmp / "w-badcell")},
             {"CLAUDE_USAGE_WINDOWS": w_week, "CLAUDE_USAGE_CALIBRATION": str(cal_ok)}, 0,
             ("WARNING", "counted as 0: U1"), ()),
            ("1.3.0: a pre-1.3.0 ledger without the new columns is read exactly as before",
             {**plain_call, "cwd": str(tmp / "fresh")}, {"CLAUDE_USAGE_WINDOWS": w_fresh,
                                                          "CLAUDE_USAGE_CALIBRATION": str(cal_ok)}, 0, (), ("WARNING",)),
            ("1.3.0: a pre-1.3.0 ledger still blocks at 97.5%",
             {**plain_call, "cwd": str(tmp / "fresh")}, {"CLAUDE_USAGE_WINDOWS": w_block}, 2, ("97.5% used",), ()),
            # K8a (audit K7-2-22): the stop band is the documented 95% default on BOTH
            # windows, and pacewright's budget file `stop_bands.stop` replaces it.
            ("K8a: the 5-hour window at 95.5% blocks at the default 95% stop band",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {"CLAUDE_USAGE_WINDOWS": w_five_stop}, 2,
             ("95.5% used", ">= 95%"), ()),
            ("K8a: the 7-day window at 96% blocks at the default 95% stop band",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {"CLAUDE_USAGE_WINDOWS": w_week_stop}, 2,
             ("7-day usage window is 96% used",), ()),
            ("K8a: 92% passes the default stop band",
             {**plain_call, "cwd": str(tmp / "w-plain")}, {"CLAUDE_USAGE_WINDOWS": w_five_92}, 0, (),
             ("usage window is",)),
            ("K8a: a budget file stop band of 90 blocks at 92%",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_five_92, "DISPATCH_BUDGET_FILE": str(bud_stop90)}, 2,
             ("92% used", ">= 90%", "budget file"), ()),
            ("K8a: a budget file stop band of 99 cannot relax the 95% line and says it clamped",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_block, "DISPATCH_BUDGET_FILE": str(bud_stop99)}, 2,
             ("97.5% used", ">= 95%", "clamped"), ()),
            ("K8a: a malformed budget stop band keeps the 95% default",
             {**plain_call, "cwd": str(tmp / "w-plain")},
             {"CLAUDE_USAGE_WINDOWS": w_five_stop, "DISPATCH_BUDGET_FILE": str(bud_stop_bad)}, 2,
             (">= 95%",), ()),
            ("K8a: a weekly stop on a resume of rows deferred to next still allows",
             {**resume_call, "cwd": str(tmp / "w-next")}, {"CLAUDE_USAGE_WINDOWS": w_week_stop}, 0, (),
             ("usage window is",)),
        ]
        for label, payload, extra, expected, wants, must_nots in window_cases:
            code, out, err = _run_guard_full(payload, fresh_flag, tmp, extra)
            combined = out + err
            if code != expected:
                problems.append(f"{label}: expected exit {expected}, got {code} ({combined.strip()[:200]!r})")
            if code not in (0, 2):
                problems.append(f"{label}: exit {code} is neither allow (0) nor block (2)")
            for want in wants:
                if want not in combined:
                    problems.append(f"{label}: output lacks {want!r}: {combined.strip()[:300]!r}")
            for must_not in must_nots:
                if must_not in combined:
                    problems.append(f"{label}: output wrongly carries {must_not!r}")

        # The dispatch half of the calibration point: an allowed dispatch fills
        # every open row's EMPTY pct_at_dispatch cell, leaves a filled one and a
        # closed row alone, and changes no other byte.
        before = led_record.read_text(encoding="utf-8")
        code, out, err = _run_guard_full({**plain_call, "cwd": str(tmp / "w-record")}, fresh_flag, tmp,
                                         {"CLAUDE_USAGE_WINDOWS": w_fresh})
        after = led_record.read_text(encoding="utf-8")
        if code != 0:
            problems.append(f"1.3.0: the pct_at_dispatch write case exited {code}")
        rows_after = after.splitlines()
        u1 = next((r for r in rows_after if r.startswith("| U1 ")), "")
        u2 = next((r for r in rows_after if r.startswith("| U2 ")), "")
        u9 = next((r for r in rows_after if r.startswith("| U9 ")), "")
        if "| 5h=23.5 7d=41.2 |" not in u1:
            problems.append(f"1.3.0: an empty pct_at_dispatch cell on an open row was not filled: {u1!r}")
        if "| 5h=1 7d=2 |" not in u2:
            problems.append(f"1.3.0: a filled pct_at_dispatch cell was overwritten: {u2!r}")
        if "5h=23.5" in u9:
            problems.append(f"1.3.0: a closed row's pct_at_dispatch cell was filled: {u9!r}")
        if before.replace("|  | | t |", "| 5h=23.5 7d=41.2 | | t |", 1) != after:
            problems.append("1.3.0: the pct_at_dispatch write changed bytes outside the one target cell")
        # A second run is idempotent.
        _run_guard_full({**plain_call, "cwd": str(tmp / "w-record")}, fresh_flag, tmp, {"CLAUDE_USAGE_WINDOWS": w_fresh})
        if led_record.read_text(encoding="utf-8") != after:
            problems.append("1.3.0: a second allowed dispatch rewrote pct_at_dispatch cells")
        # Fixture mode: the ledger and the windows file come from argv, the
        # windows file is taken as current, and the ledger is never written.
        fixture_led = tmp / "fixture-ledger.md"
        fixture_led.write_text(header13 + _row13("U1") + "\n", encoding="utf-8")
        (tmp / "session").write_text("abc", encoding="utf-8")
        fx_before = fixture_led.read_bytes()
        code, out, err = _run_guard_full(
            {**plain_call, "cwd": str(tmp / "bare")}, fresh_flag, tmp, {},
            ["--ledger", str(fixture_led), "--windows-file", w_block_stale],
        )
        if code != 2 or "97.5% used" not in (out + err):
            problems.append(f"1.3.0: fixture mode did not read the argv windows file as current (exit {code})")
        code, out, err = _run_guard_full(
            {**plain_call, "cwd": str(tmp / "bare")}, fresh_flag, tmp, {},
            ["--ledger", str(fixture_led), "--windows-file", w_fresh, "--calibration-file", str(cal_ok)],
        )
        if code != 0 or fixture_led.read_bytes() != fx_before:
            problems.append("1.3.0: fixture mode wrote the ledger or blocked an allowed dispatch")

        # parse_tokens and the resume detector, pinned.
        for cell, want in (("400000", 400000), ("60,000", 60000), ("60k (median of 4 rows)", 60000),
                           ("1.2M (owner)", 1200000), ("~86k", 86000), ("a lot", None), ("", None)):
            if parse_tokens(cell) != want:
                problems.append(f"1.3.0: parse_tokens({cell!r}) should be {want!r}, got {parse_tokens(cell)!r}")
        if not is_resume_call(resume_call) or is_resume_call(plain_call):
            problems.append("1.3.0: is_resume_call does not separate a resume from a plain call")
        if any(is_resume_call({"tool_input": {"prompt": p}}) for p in ("check the handoffwright handoff", "update the resumewriter notes")):
            problems.append("1.3.0: is_resume_call matched a skill name or a compound word as a resume")

    # --- 1.4.0: lookup order, pointer file, status lint (observation 0172) ---
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sub = root / "a" / "b"
        sub.mkdir(parents=True)
        (root / ".git").mkdir()
        run = root / ".dispatch" / "runs" / "r1"
        run.mkdir(parents=True)
        led = run / "ledger.md"
        led.write_text("| unit_id | model | effort | surface | status |\n|---|---|---|---|---|\n"
                       "| U1 | Claude Opus 5.5 | medium | subagent (background) | done (read-only) |\n"
                       "| U2 | Claude Opus 5.5 | medium | subagent (background) | done |\n", encoding="utf-8")
        if led not in ledger_candidates(str(sub)):
            problems.append("1.4.0: the parent walk did not find the repo-root run dir from a subfolder")
        if status_lint(led) != ["U1"]:
            problems.append(f"1.4.0: status_lint should flag only U1, got {status_lint(led)}")
        other = root / "elsewhere.md"
        other.write_text(led.read_text(encoding="utf-8"), encoding="utf-8")
        (sub / ".dispatch").mkdir()
        (sub / POINTER_FILE).write_text(str(other) + "\n", encoding="utf-8")
        if ledger_candidates(str(sub)) != [other]:
            problems.append("1.4.0: a .dispatch/ledger-path pointer did not win over the parent walk")
    with tempfile.TemporaryDirectory() as td:
        if search_dirs(td)[:1] != [Path(td)]:
            problems.append("1.4.0: search_dirs must start at the cwd")

    hk_cases = _selftest_records_and_v2(problems)

    if problems:
        for p in problems:
            print(f"DISPATCH_LEDGER_GUARD SELFTEST FAIL: {p}")
        return 2
    print(
        "dispatch_ledger_guard selftest: OK (flag states incl. uncorrelated, "
        "ledger currency, cell validators, agent-count token parsing, and 18 real "
        "exit-code cases covering all four 2026-08-18 defects, the 2026-08-20 "
        "wave-cap enforcement, and the 2026-09-11 observation #0022 fix; plus "
        f"{len(window_cases)} usage-window cases (2026-09-17, dispatchwright 1.3.0): "
        "silent on an absent or stale file, the stop-band block (95% default or the budget file, both windows) with its resume exemption, "
        "the calibration warning with its numbers, a pre-1.3.0 ledger unchanged, "
        "the pct_at_dispatch cell write, and argv fixture mode; plus the 1.4.0 lookup-order, "
        f"pointer-file and status-lint cases; plus {hk_cases} records-header and ledger-v2 "
        "row-validation cases)"
    )
    return 0


def _selftest_records_and_v2(problems: list) -> int:
    """The `records: public (off git)` header (owner Q13, observation 0203) and
    the ledger v2 row validation (observation 0271). Appends to `problems` and
    returns the number of cases run."""
    cases = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal cases
        cases += 1
        if not cond:
            problems.append(msg)

    def _git(cwd: Path, *args: str) -> bool:
        try:
            return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, timeout=20).returncode == 0
        except Exception:
            return False

    v2_head = (
        "| unit_id | task | class | model | effort | surface | estimated_tokens | actual | harness_tokens "
        "| ci_green | bar_met | round_reason | dispatch_ts | commit_ts | push_ts | done_ts | status |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )

    def _v2row(uid="U1", cls="mechanical", est="4000 (owner)", actual="5200 / 11 / 3", harness="5200",
               ci="yes", bar="—", rr="—", dts="2026-10-01 14:02Z", cts="", pts="", done="2026-10-01 14:30Z",
               status="done"):
        return (f"| {uid} | thing | {cls} | Claude Opus 5.5 | medium | subagent (background) | {est} | {actual} "
                f"| {harness} | {ci} | {bar} | {rr} | {dts} | {cts} | {pts} | {done} | {status} |")

    def _ledger(dirpath: Path, header_lines: str, rows: list, pre_table: str = "") -> Path:
        run = dirpath / ".dispatch" / "runs" / "r1"
        run.mkdir(parents=True, exist_ok=True)
        p = run / "ledger.md"
        p.write_text("# Ledger\n\n" + header_lines + "\n" + pre_table + v2_head + "\n".join(rows) + "\n",
                     encoding="utf-8")
        return p

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # --- records header detection ---
        for i, line in enumerate(("records: public (off git)", "`records: public (off git)`",
                                  "- **records:** public (off git)", "Records: Public (off git)")):
            p = _ledger(tmp / f"pub{i}", line, [_v2row()])
            check(ledger_records_public(p), f"HK: the header line {line!r} was not read as public")
        for i, line in enumerate(("records: private (committed)", "", "the records: public (off git) rule is "
                                  "for other repos | not this one")):
            p = _ledger(tmp / f"priv{i}", line, [_v2row()])
            check(not ledger_records_public(p), f"HK: {line!r} was read as a public-records header")
        # A table cell saying it is not a header.
        p = _ledger(tmp / "cell", "", [_v2row(uid="U1")], pre_table="| note | records: public (off git) |\n|---|---|\n\n")
        check(not ledger_records_public(p), "HK: a table cell was read as the records header")

        # --- the git-ignore warning, in a real repo ---
        repo = tmp / "repo"
        repo.mkdir()
        if _git(repo, "init", "-q"):
            (repo / ".gitignore").write_text(".dispatch/\n", encoding="utf-8")
            pub = _ledger(repo, "records: public (off git)\nledger: v2", [_v2row()])
            check(ledger_is_ignored(pub), "HK: the test repo does not ignore .dispatch/ (setup)")
            notes = " ".join(ledger_warnings(pub))
            check("git ignores" not in notes,
                  f"HK: a public-records ledger that git ignores still warned: {notes[:200]!r}")
            pub.write_text(pub.read_text(encoding="utf-8").replace("records: public (off git)",
                                                                   "records: private (committed)"),
                           encoding="utf-8")
            notes = " ".join(ledger_warnings(pub))
            check("git ignores" in notes, "HK: a private-records ledger that git ignores lost its warning")
            pub.write_text(pub.read_text(encoding="utf-8").replace("records: private (committed)", ""),
                           encoding="utf-8")
            notes = " ".join(ledger_warnings(pub))
            check("git ignores" in notes, "HK: a ledger with no records header that git ignores lost its warning")
            # A public-records ledger that git would commit: the reverse warning.
            (repo / ".gitignore").write_text("", encoding="utf-8")
            pub.write_text("records: public (off git)\n" + pub.read_text(encoding="utf-8"), encoding="utf-8")
            notes = " ".join(ledger_warnings(pub))
            check("would commit" in notes,
                  f"HK: a public-records ledger git does not ignore did not warn: {notes[:200]!r}")
            # The remote route: CLAUDE_DISPATCH_PUBLIC_REMOTES names the origin.
            (repo / ".gitignore").write_text(".dispatch/\n", encoding="utf-8")
            pub.write_text(pub.read_text(encoding="utf-8").replace("records: public (off git)", ""),
                           encoding="utf-8")
            _git(repo, "remote", "add", "origin", "https://example.invalid/acme/open-repo.git")
            old = os.environ.get("CLAUDE_DISPATCH_PUBLIC_REMOTES")
            try:
                os.environ["CLAUDE_DISPATCH_PUBLIC_REMOTES"] = "other/thing" + os.pathsep + "acme/open-repo"
                check(ledger_records_public(pub), "HK: a remote named in CLAUDE_DISPATCH_PUBLIC_REMOTES was not public")
                check("git ignores" not in " ".join(ledger_warnings(pub)),
                      "HK: an ignored ledger in a listed public remote still warned")
                os.environ["CLAUDE_DISPATCH_PUBLIC_REMOTES"] = "other/thing"
                check(not ledger_records_public(pub), "HK: an unlisted remote was read as public")
            finally:
                if old is None:
                    os.environ.pop("CLAUDE_DISPATCH_PUBLIC_REMOTES", None)
                else:
                    os.environ["CLAUDE_DISPATCH_PUBLIC_REMOTES"] = old
        else:
            problems.append("HK: git init failed; the ignore-warning cases could not run")

        # --- ledger version detection ---
        for i, line in enumerate(("ledger: v2", "`ledger: v2`", "- **ledger:** v2", "Ledger schema: v2")):
            p = _ledger(tmp / f"ver{i}", line, [_v2row()])
            check(ledger_version(p) == 2, f"HK: {line!r} was not read as a v2 header")
        for i, line in enumerate(("", "ledger v2 close fields are described elsewhere", "ledger: v1")):
            p = _ledger(tmp / f"v1-{i}", line, [_v2row()])
            check(ledger_version(p) == 1, f"HK: {line!r} was read as a v2 header")

        # --- v2 row validation, unit level ---
        good = _ledger(tmp / "good", "ledger: v2", [
            _v2row(),
            _v2row(uid="U2", cls="judgment", actual="", harness="", ci="—", done="", status="dispatched"),
            _v2row(uid="U3", cls="structured", ci="n/a", bar="advisory", rr="brief-defect", status="landed locally",
                   cts="2026-10-01 14:10Z", actual="9000 / 20 / 6 (self-reported, unverified)"),
            _v2row(uid="U4", status="verified", bar="yes", rr="finding", pts="2026-10-01 14:20Z"),
        ], pre_table="| unit | class | est | actual | ratio |\n|---|---|---|---|---|\n| U9 | free text | x | y | z |\n\n")
        check(v2_row_problems(good) == [], f"HK: a well-formed v2 ledger reported {v2_row_problems(good)}")
        # The end-to-end copy carries no header-block table: the v1 parsers read
        # the FIRST pipe table as the row header (a known, separate limit).
        _ledger(tmp / "good2", "ledger: v2", [_v2row(), _v2row(uid="U2", actual="", harness="", done="",
                                                               status="dispatched")])
        bad_rows = {
            "class": _v2row(cls="mechanical-ish"),
            "status": _v2row(status="done (no change)"),
            "estimated_tokens": _v2row(est="about 60k"),
            "actual": _v2row(actual="unknown"),
            "harness_tokens": _v2row(harness="~90k"),
            "dispatch_ts": _v2row(dts="~14:02"),
            "done_ts": _v2row(done="2026-10-01"),
            "ci_green": _v2row(ci="green"),
            "bar_met": _v2row(bar="maybe"),
            "round_reason": _v2row(rr="because"),
            "harness_tokens missing": _v2row(harness=""),
            "done_ts missing": _v2row(done="—"),
            "cells": "| U1 | thing | mechanical | Claude Opus 5.5 | medium |",
        }
        for i, (what, row) in enumerate(bad_rows.items()):
            p = _ledger(tmp / f"bad{i}", "ledger: v2", [row])
            got = v2_row_problems(p)
            check(bool(got) and all(g.startswith("U1") for g in got),
                  f"HK: a v2 row with a bad {what} was not reported malformed: {got}")
            key = what.split()[0]
            check(any(key in g for g in got), f"HK: the {what} problem does not name {key!r}: {got}")
        # A v2 ledger missing the close columns: a closed row cannot carry them.
        p = tmp / "nocols" / "ledger.md"
        p.parent.mkdir(parents=True)
        p.write_text("ledger: v2\n\n| unit_id | class | model | effort | surface | estimated_tokens | status |\n"
                     "|---|---|---|---|---|---|---|\n"
                     "| U1 | mechanical | Claude Opus 5.5 | medium | subagent (background) | 4000 | done |\n",
                     encoding="utf-8")
        got = v2_row_problems(p)
        check(any("harness_tokens" in g for g in got) and any("done_ts" in g for g in got),
              f"HK: a closed v2 row with no close columns was not malformed: {got}")
        # v1: the same bad rows are never validated.
        p = _ledger(tmp / "v1bad", "", [_v2row(cls="free text", status="done (no change)", harness="")])
        check(v2_row_problems(p) == [], "HK: a v1 ledger was validated as v2")
        # A CSV v2 ledger with a `# ledger: v2` comment header.
        p = tmp / "csv" / "ledger.csv"
        p.parent.mkdir(parents=True)
        p.write_text("# ledger: v2\nunit_id,class,model,effort,surface,estimated_tokens,harness_tokens,done_ts,status\n"
                     "U1,mechanical,Claude Opus 5.5,medium,subagent (background),4000,5200,2026-10-01 14:30Z,done\n"
                     "U2,vibes,Claude Opus 5.5,medium,subagent (background),4000,,,dispatched\n", encoding="utf-8")
        check(ledger_version(p) == 2, "HK: a CSV `# ledger: v2` comment was not read as v2")
        got = v2_row_problems(p)
        check(len(got) == 1 and got[0].startswith("U2") and "class" in got[0],
              f"HK: the CSV v2 check should flag only U2's class, got {got}")

        # --- end to end, exit codes ---
        flag = {"session_id": "abc", "ts": time.time()}
        call = {"tool_name": "Task", "session_id": "abc",
                "tool_input": {"description": "verify findings", "prompt": "check the findings"}}
        e2e = [
            ("HK: a well-formed v2 ledger allows", "good2", 0, (), ("malformed",)),
            ("HK: a malformed v2 row blocks and names the row", "bad0", 2, ("malformed", "U1", "class"), ()),
            ("HK: a v1 ledger with free text in valued cells is never blocked", "v1bad", 0, (), ("malformed",)),
        ]
        for label, sub, expected, wants, must_nots in e2e:
            code, out, err = _run_guard_full({**call, "cwd": str(tmp / sub)}, flag, tmp)
            combined = out + err
            check(code == expected, f"{label}: expected exit {expected}, got {code} ({combined.strip()[:300]!r})")
            for want in wants:
                check(want in combined, f"{label}: output lacks {want!r}: {combined.strip()[:300]!r}")
            for must_not in must_nots:
                check(must_not not in combined, f"{label}: output wrongly carries {must_not!r}")

        # --- observation 0361: header blocks (tables) above the rows ---
        meters = "| meter | reading | read at |\n|---|---|---|\n| 7d | 41% | 2026-10-01 14:00Z |\n\n"
        rulings = "| ruling | date |\n|---|---|\n| one writer per repo | 2026-10-01 |\n\n"
        mp = _ledger(tmp / "meters", "", [_v2row(uid="M1", status="dispatched")], pre_table=meters + rulings)
        check(ledger_has_populated_row(mp), "0361: a meters table above the rows hid the populated row")
        check(open_unit_count(mp) == 1,
              f"0361: open_unit_count read the wrong table (got {open_unit_count(mp)}, want 1)")
        picked = row_table(mp.read_text(encoding="utf-8"))
        check(picked is not None and "unit_id" in picked[1][0], "0361: row_table did not pick the unit-row table")
        check("line" in row_table_note(mp) and "unit_id" in row_table_note(mp),
              f"0361: the note does not name the table read: {row_table_note(mp)!r}")
        tbd = _ledger(tmp / "meterstbd", "", [_v2row(uid="T1").replace("Claude Opus 5.5", "TBD")], pre_table=meters)
        check(not ledger_has_populated_row(tbd), "0361: a TBD model cell read as tiered under a meters table")
        only = tmp / "onlymeters" / ".dispatch" / "runs" / "r1"
        only.mkdir(parents=True, exist_ok=True)
        (only / "ledger.md").write_text("# Ledger\n\n" + meters, encoding="utf-8")
        note = row_table_note(only / "ledger.md")
        check("None of its 1 pipe table" in note, f"0361: a rowless ledger's note is wrong: {note!r}")
        e2e = [
            ("0361: a schema ledger with a meters table first allows", "meters", 0, (), ("carries no row",)),
            ("0361: refusal names the table it read", "meterstbd", 2, ("carries no row", "It read the table at line"), ()),
            ("0361: refusal says no table has the row header", "onlymeters", 2, ("None of its 1 pipe table",), ()),
        ]
        for label, sub, expected, wants, must_nots in e2e:
            code, out, err = _run_guard_full({**call, "cwd": str(tmp / sub)}, flag, tmp)
            combined = out + err
            check(code == expected, f"{label}: expected exit {expected}, got {code} ({combined.strip()[:300]!r})")
            for want in wants:
                check(want in combined, f"{label}: output lacks {want!r}: {combined.strip()[:300]!r}")
            for must_not in must_nots:
                check(must_not not in combined, f"{label}: output wrongly carries {must_not!r}")
    return cases


def ledger_is_ignored(path: Path) -> bool:
    """True when git would ignore the ledger (dispatchwright 1.4.0, observation
    0191): an ignored ledger is committed by nothing but `git add -f`, so the
    three-point durability rule silently records nothing. Any failure -- no git,
    not a repo -- reads as not ignored; this is a warning, never a block."""
    try:
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", str(path.name)], cwd=str(path.parent),
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def status_lint(path: Path) -> list:
    """Unit ids whose status cell starts with `done` but is not exactly `done`
    (observation 0172): `done (read-only)` or `done, absorbed` reads as open to
    a strict parser and as closed to a human. The reason goes in another cell."""
    bad = []
    try:
        text = path.read_text(encoding="utf-8")
        for row in _table_rows(text, path.suffix.lower(), ("unit_id", "status")):
            s = _norm(row.get("status", ""))
            if s.startswith("done") and s != "done":
                bad.append(row.get("unit_id") or "?")
    except Exception:
        pass
    return bad


# ---------------------------------------------------------------------------
# Ledger header lines (references/ledger-schema.md): `records: public (off git)`
# (owner Q13, observation 0203) and `ledger: v2` (observation 0271). A header
# line is any line outside a pipe table; backticks and bold markers are
# ignored, as are a leading list bullet and a leading `#` (a CSV ledger carries
# its header lines as `#` comments).
# ---------------------------------------------------------------------------
RECORDS_PUBLIC_RE = re.compile(r"^(?:#+\s*)?(?:[-+]\s+)?records\s*:\s*public\s*\(\s*off\s+git\s*\)", re.I)
LEDGER_V2_RE = re.compile(r"^(?:#+\s*)?(?:[-+]\s+)?ledger(?:\s+schema)?\s*:\s*v2\b", re.I)


def _header_lines(path: Path) -> list:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    out = []
    csv_form = path.suffix.lower() == ".csv"
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|") or (csv_form and not s.startswith("#")):
            continue
        out.append(s.replace("`", "").replace("*", "").strip())
    return out


def _git_out(cwd: Path, *args: str) -> tuple:
    """(returncode, stdout) of a git call; (-1, "") on any failure."""
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=10)
        return r.returncode, (r.stdout or "").strip()
    except Exception:
        return -1, ""


def ledger_records_public(path: Path) -> bool:
    """True when the run's records are meant to stay off git: the ledger header
    says `records: public (off git)`, or the ledger's repo has an origin URL
    containing one of the entries in CLAUDE_DISPATCH_PUBLIC_REMOTES
    (os.pathsep-separated, case-insensitive substrings) -- the controller's way
    to mark a repo public once instead of in every ledger."""
    if any(RECORDS_PUBLIC_RE.search(ln) for ln in _header_lines(path)):
        return True
    marks = [m.strip().lower() for m in os.environ.get("CLAUDE_DISPATCH_PUBLIC_REMOTES", "").split(os.pathsep)
             if m.strip()]
    if not marks:
        return False
    code, url = _git_out(path.parent, "config", "--get", "remote.origin.url")
    return code == 0 and any(m in url.lower() for m in marks)


def ledger_in_work_tree(path: Path) -> bool:
    code, out = _git_out(path.parent, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out == "true"


def ledger_version(path: Path) -> int:
    """2 when a header line says `ledger: v2`, else 1. A ledger without that
    line is validated as v1 -- the checks it always had -- and is never blocked
    by the v2 row validation."""
    return 2 if any(LEDGER_V2_RE.search(ln) for ln in _header_lines(path)) else 1


# Row validation (ledger v2), references/ledger-schema.md.
V2_VALUED = {
    "class": {"mechanical", "structured", "judgment"},
    "status": {"dispatched", "committed", "landed locally", "pushed", "verified", "done", "unverified",
               "stalled", "failed", "resumed"},
    "ci_green": {"yes", "no", "n/a"},
    "bar_met": {"yes", "no", "advisory"},
    "round_reason": {"finding", "gate", "ci", "owner", "brief-defect"},
}
V2_REQUIRED_VALUED = {"class", "status"}
V2_NUMBER_LED = ("estimated_tokens", "actual", "harness_tokens")
V2_REQUIRED_NUMBER = {"estimated_tokens"}
V2_TIMESTAMPS = ("dispatch_ts", "commit_ts", "push_ts", "done_ts")
V2_CLOSED = {"done", "verified", "landed locally", "pushed", "unverified", "failed"}
V2_EMPTY = {"", "-", "—", "–"}
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z$")


def _col_name(cell: str) -> str:
    m = re.match(r"[a-z0-9_/]+", cell.replace("`", "").replace("*", "").strip().lower())
    return m.group(0) if m else ""


def _row_tables(path: Path) -> list:
    """Every (header, rows) table whose header has a `unit_id` column -- the
    row tables, not the header blocks (plan status, rulings, actuals) above
    them. Rows are raw cell lists."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".csv":
        body = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("#"))
        parsed = [r for r in csv.reader(io.StringIO(body)) if r]
        if not parsed:
            return []
        header = [_col_name(h) for h in parsed[0]]
        return [(header, [[c.strip() for c in r] for r in parsed[1:]])] if "unit_id" in header else []
    tables, cur = [], []
    for ln in text.splitlines() + [""]:
        if ln.strip().startswith("|"):
            cur.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif cur:
            tables.append(cur)
            cur = []
    out = []
    for t in tables:
        header = [_col_name(c) for c in t[0]]
        if "unit_id" not in header:
            continue
        rows = [r for r in t[1:] if not all(set(c) <= {"-", ":"} for c in r)]
        out.append((header, rows))
    return out


def v2_row_problems(path: Path) -> list:
    """One line per failed check, each led by the row's unit id, for a v2
    ledger; [] for a v1 ledger. The checks are the "Row validation (ledger v2)"
    list: a valued cell holds exactly one listed value; actual, harness_tokens
    and estimated_tokens lead with a number; every timestamp matches
    `YYYY-MM-DD HH:MMZ`; a closed row has harness_tokens and done_ts."""
    if ledger_version(path) != 2:
        return []
    problems = []
    for header, rows in _row_tables(path):
        for n, raw in enumerate(rows, 1):
            uid = raw[header.index("unit_id")] if len(raw) > header.index("unit_id") else ""
            uid = uid.replace("`", "").strip() or f"row {n}"
            if len(raw) != len(header):
                problems.append(f"{uid}: {len(raw)} cells, the header has {len(header)}")
                continue
            row = {h: c.replace("`", "").strip() for h, c in zip(header, raw) if h}
            for col, allowed in V2_VALUED.items():
                if col not in row:
                    continue
                v = row[col]
                if v in V2_EMPTY:
                    if col in V2_REQUIRED_VALUED:
                        problems.append(f"{uid}: {col} is empty")
                elif v.lower() not in allowed:
                    problems.append(f"{uid}: {col} {v!r} is not one of {', '.join(sorted(allowed))}")
            for col in V2_NUMBER_LED:
                if col not in row:
                    continue
                v = row[col]
                if v in V2_EMPTY:
                    if col in V2_REQUIRED_NUMBER:
                        problems.append(f"{uid}: {col} is empty")
                elif not v[:1].isdigit():
                    problems.append(f"{uid}: {col} {v!r} does not lead with a number")
            for col in V2_TIMESTAMPS:
                v = row.get(col, "")
                if v not in V2_EMPTY and not TIMESTAMP_RE.match(v):
                    problems.append(f"{uid}: {col} {v!r} is not `YYYY-MM-DD HH:MMZ` from one clock call")
            if row.get("status", "").lower() in V2_CLOSED:
                for col in ("harness_tokens", "done_ts"):
                    if row.get(col, "") in V2_EMPTY:
                        problems.append(f"{uid}: closed row has no {col}")
    return problems


def ledger_warnings(path: Path) -> list:
    notes = []
    public = ledger_records_public(path)
    if ledger_is_ignored(path):
        if not public:
            notes.append(f"dispatch_ledger_guard WARNING: git ignores {path}; a plain `git add` commits "
                         "nothing, so the ledger is not durable. Name the ignore rule (`git check-ignore -v`) "
                         "and narrow it, or, in a public repo, write the header line `records: public (off git)` "
                         "(references/ledger-schema.md, Where it lives).")
    elif public and ledger_in_work_tree(path):
        notes.append(f"dispatch_ledger_guard WARNING: {path} keeps its records off git (public repo), but git "
                     "would commit it; add an ignore rule for the run directory before the next row "
                     "(references/ledger-schema.md, Where it lives).")
    bad = status_lint(path)
    if bad:
        notes.append("dispatch_ledger_guard WARNING: status cells start with `done` but are not exactly "
                     f"`done` for {', '.join(bad)}; write the bare word and put the reason in another cell.")
    return notes


def _guard(data: dict) -> int:
    tool_name = data.get("tool_name", "")
    if tool_name not in GATED_TOOLS:
        return 0

    session_id = str(data.get("session_id") or "")
    state = flag_state(read_flag(), session_id)
    if state in ("absent", "stale", "other-session"):
        return 0  # dispatch mode is not active for this session

    cwd = data.get("cwd") or os.getcwd()
    ledger = find_ledger(cwd, session_id)
    if ledger is None:
        stale_seen = [str(p) for p in ledger_candidates(cwd)]
        extra = (
            f" Ledgers were found but none is current for this run: {', '.join(stale_seen)}."
            f" A ledger counts only if it names this session or was written in the last"
            f" {STALE_SECONDS // 3600}h."
            if stale_seen else ""
        )
        searched = ", ".join(str(d) for d in search_dirs(cwd))
        print(
            "dispatch_ledger_guard: dispatch mode is active for this session but no current run "
            "ledger was found (checked CLAUDE_DISPATCH_LEDGER, then a .dispatch/ledger-path pointer "
            f"and .dispatch/runs/*/ledger.{{md,csv}} in: {searched})." + extra + " Write the ledger row -- model, effort, surface, from "
            "dispatchwright's own tier table (references/tier-routing.md) -- before this dispatch. "
            "See references/ledger-schema.md.",
            file=sys.stderr,
        )
        return 2

    if not ledger_has_populated_row(ledger):
        print(
            f"dispatch_ledger_guard: {ledger} carries no row that names a model, an effort, and a "
            "surface. Placeholders such as TBD, ?, x or a dash do not count. Tier the unit from "
            "dispatchwright's own tier table first and write the real row before dispatching it."
            + row_table_note(ledger),
            file=sys.stderr,
        )
        return 2

    # Ledger v2 (observation 0271): a malformed row fails closed. A ledger with
    # no `ledger: v2` header line is v1 and skips this check entirely.
    malformed = v2_row_problems(ledger)
    if malformed:
        shown = "; ".join(malformed[:8]) + (f"; and {len(malformed) - 8} more" if len(malformed) > 8 else "")
        print(
            f"dispatch_ledger_guard: {ledger} is a v2 ledger (header `ledger: v2`) with malformed rows: "
            f"{shown}. Fix each row before the next launch; a malformed row is never read as calibration "
            "(references/ledger-schema.md, Row validation).",
            file=sys.stderr,
        )
        return 2

    open_count = open_unit_count(ledger)
    cap = concurrent_cap()
    if open_count > cap:
        print(
            f"dispatch_ledger_guard: {ledger} already shows {open_count} open units (dispatched or "
            f"committed, not yet pushed) -- over the {cap}-unit wave cap in "
            "SKILL.md section 6. Let some units reach pushed/verified before dispatching another, "
            "or split the remainder into a second wave.",
            file=sys.stderr,
        )
        return 2

    collision = repo_collision(ledger)
    if collision:
        print(
            f"dispatch_ledger_guard: {ledger} shows two or more open units writing '{collision}' "
            "with no worktree assigned to either -- the one-writer-per-repo rule in SKILL.md "
            "section 6. Give each writer its own worktree, or sequence them instead of running "
            "both at once.",
            file=sys.stderr,
        )
        return 2

    # Usage windows (1.3.0): silent without a fresh reading; the stop-band block;
    # the calibration warning; the pct_at_dispatch cell.
    code, reason, context = window_step(
        ledger, data, _argv_path("--windows-file"), _argv_path("--calibration-file")
    )
    if code == 2:
        print(reason, file=sys.stderr)
        return 2
    notes = ledger_warnings(ledger)
    if notes:
        context = (context + " " if context else "") + " ".join(notes)
    if context:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "additionalContext": context}}))
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    # D2. Every path below returns 0 or 2. Claude Code blocks a PreToolUse call
    # ONLY on exit code 2 -- a bare traceback exits 1, which it reads as a
    # non-blocking error and runs the tool anyway. So the whole body is wrapped,
    # and an unexpected fault blocks rather than waving the dispatch through on
    # exactly the path this hook exists to protect.
    try:
        try:
            data = json.load(sys.stdin)
        except Exception as e:
            raise RuntimeError(f"the PreToolUse payload on stdin could not be parsed ({e})") from e
        if not isinstance(data, dict):
            raise RuntimeError("the PreToolUse payload on stdin was not a JSON object")
        return _guard(data)
    except Exception as e:
        print(
            f"dispatch_ledger_guard: blocking because the guard itself failed -- {type(e).__name__}: {e}. "
            "It cannot prove this dispatch is tiered, so it fails closed. Fix the fault, or disarm the "
            "guard by deleting the flag file (~/.claude/dispatch-mode.json); removing the PreToolUse "
            "block from ~/.claude/settings.json turns it off for good.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
