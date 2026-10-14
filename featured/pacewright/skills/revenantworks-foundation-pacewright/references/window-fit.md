# Window fit — calibration, the fit, and the window column of a plan table

Loaded by `pacewright fit`, and by any mode step that turns a percent into tokens (SKILL.md —
Load budget). This file is the contract behind the window column of a plan table: where the
window numbers come from, how a percent becomes a token allowance, how units are fitted, and what
a reconcile writes back so the next fit is better measured than this one. It is pacewright's.
A fan-out (dispatchwright) shows the table and stops for the user's go; the fit reaches it as
data, through the budget decision file (SKILL.md — The budget decision file), or through this
file's procedure run by hand. First written inside dispatchwright on the user's request that
nothing launches until a per-wave table has been shown and confirmed (history in CHANGELOG.md).

## Contents

- The windows
- Where the numbers come from — the data file, staleness, the ask
- Calibration — a percent is not a token count
- Estimates — every number names its basis
- The fit
- The table and the stop
- A unit added mid-run
- What Reconcile writes back
- The rig hooks (not package contents)

---

## The windows

Three kinds of window, all rolling, all in **percent used**, never tokens:

| Window | Key | What it is |
|---|---|---|
| 5-hour | `five_hour` | The rolling five-hour subscription window. Resets at `resets_at`. |
| 7-day | `seven_day` | The rolling weekly window. Resets at `resets_at`. |
| per-model | owner-named | Any per-model allowance the user tracks by hand — a frontier-tier weekly allowance, say. **Not in the harness data.** The user enters it; the skill never infers one. |

The harness publishes `five_hour` and `seven_day` only to a configured statusLine command, only
for claude.ai Pro/Max, only after the session's first API response, and drops a window once its
`resets_at` passes (verified against `code.claude.com/docs/en/statusline.md`, 2026-09-17). Hooks
receive no rate-limit field. The model has no surface of its own — no command, no file, no
environment variable, no endpoint. Everything below follows from that: the numbers reach a plan
through a file the statusline writes, or through the user.

## Where the numbers come from

**The data file.** The rig's statusline command (`usage_windows.py`, see the last section) writes
`~/.claude/usage-windows.json` on every refresh:

```json
{
  "written_at": 1758115200,
  "model": {"id": "<model id>", "display_name": "<model name>"},
  "context_used_percentage": 8,
  "five_hour": {"used_percentage": 23.5, "resets_at": 1758124800},
  "seven_day": {"used_percentage": 41.2, "resets_at": 1758556800},
  "spend_limit": null
}
```

`written_at` is Unix epoch seconds. A window the harness did not send is `null`. `spend_limit` is
present only behind a gateway and is reported, never fitted against.

**Staleness — 15 minutes.** The file is current when `written_at` is within the last 15 minutes.
Absent, unreadable, or older than that, and the plan **asks the user, one line**, and stops for
the answer:

> *Usage windows: I have no fresh reading. Percent used and reset time for the 5-hour and 7-day
> windows, and any per-model window you track?*

The skill never guesses a percent, never reuses a stale reading as if it were current, and never
reads a window off a screenshot or a memory of one. A plan with no window data and no answer
presents its table with the window column reading `unfitted` and does not launch.

**The rig hook shortcut.** When `dispatch_gate.py` is installed and the file is fresh, the gate's
`additionalContext` already carries one line with the windows and the calibration state, so the
plan turn fills the window column without asking. When the gate says the file is absent or stale,
the plan asks. The hook is a convenience, never a requirement: a rig without it runs the same
procedure by reading the file itself where it can, and by asking where it cannot.

## Calibration — a percent is not a token count

The capacity behind a percent is not published, so a percent becomes tokens only through
**measurement**. `~/.dispatch/usage-calibration.json`:

```json
{
  "updated": "2026-09-17",
  "windows": {
    "five_hour": {
      "tokens_per_percent": 41000,
      "samples": 3,
      "median_of_last": 10,
      "points": [
        {"run": "2026-09-10-estate-audit", "wave": 1, "tokens": 412000, "pct_delta": 9.8, "date": "2026-09-10"},
        {"run": "2026-09-13-weekly-review", "wave": 1, "tokens": 286000, "pct_delta": 7.1, "date": "2026-09-13"},
        {"run": "2026-09-17-window-fit", "wave": 1, "tokens": 501000, "pct_delta": 12.4, "date": "2026-09-17"}
      ]
    },
    "seven_day": {"tokens_per_percent": 238571, "samples": 1, "median_of_last": 10, "points": [
      {"run": "2026-09-17-window-fit", "wave": 1, "tokens": 501000, "pct_delta": 2.1, "date": "2026-09-17"}
    ]}
  },
  "wall": {
    "mechanical": {"seconds_per_ktoken": 0.9, "samples": 4},
    "structured": {"seconds_per_ktoken": 1.4, "samples": 2},
    "judgment":   {"seconds_per_ktoken": 2.2, "samples": 5}
  }
}
```

The numbers above are the file's **shape**, not this rig's figures; a real file holds only what
Reconcile has measured.

- **One point** = one verified wave: the ledger's summed actual tokens for the wave's rows,
  against the window's used-percentage delta between the wave's dispatch (`pct_at_dispatch`, the
  guard records it on the row) and its reconcile (`pct_at_reconcile`). A point is taken only when
  the delta is positive and the window's `resets_at` did not pass between the two readings — a
  reset in between makes the delta meaningless and the point is skipped, with the skip noted.
- **`tokens_per_percent`** is the running **median** of the last `median_of_last` points (default
  10). `samples` is the count of points ever taken; the date is the last write.
- **Until two points exist, the skill says so.** With zero, it asks the user for the allowance in
  tokens per window, and fits on that. With one, it fits on that one point and marks every row it
  produced *"one data point"*. A one-point window still writes `tokens_per_percent` — the median
  of one point is that point, `501000 / 2.1 = 238571` in the example above — and "one data point"
  is read off `samples: 1`, never off a `null`; `tokens_per_percent` is `null` only when there is
  no point at all, and both rig hooks read a `null` as *no calibration*. It never fills the gap
  with a figure reasoned into being from a model's context size, a plan's price, or a remembered
  number.
- **`wall`** holds the median seconds per thousand tokens per unit class, from verified rows'
  actual wall time. It feeds the table's est. wall column the same way: no sample, no number.
- **Fit every window, not the weekly one alone.** Work with many short calls can bind the 5-hour
  window long before the week: in one measured eval fan-out (about 720 eval runs) the 5-hour
  window moved 41% → 77% while the weekly moved 16% → 22%. A batch plan is fitted against both,
  read before each batch, and stops at 70% of the 5-hour window. That run's figures — about $0.11
  plan-equivalent per eval run (balanced tier, one run, with and without the skill) and about one
  weekly point per million flagship-tier tokens — are leads for the user's first estimate, never
  a calibration point: only Reconcile's own measurements enter this file.

## Estimates — every number names its basis

The table's `est. tokens` cell is the plan's own estimate (`estimated_tokens` in the ledger), and
it names where it came from:

- the median actual tokens of prior verified rows of the same class and surface — the ledger
  history a fan-out's reconcile already collects for its actual-vs-estimated report — stated as
  *"median of N rows"*;
- or the user's own figure, stated as *"owner"*.

A bare number with no basis is not an estimate and cannot be fitted. A unit with no basis is shown
with `est. tokens` reading `unestimated` and the plan asks for a figure before fitting it. A
Workflow or Task row that fans out to N agents estimates N × per-agent, and the N is the `x<N>`
token on the row's `surface` cell when dispatchwright is installed (its `references/ledger-schema.md`);
otherwise count the agents by hand and write N beside the row.

`est. wall` = est. tokens × the class's `seconds_per_ktoken` from the calibration file. With no
sample for that class the cell reads `—` and the confirmation line says wall is unmeasured.

## The fit

Inputs: the units in plan order, each with an estimate; each window's `used_percentage` and
`resets_at`; each window's `tokens_per_percent` (or the user's token allowance); the safety
margin, **default 15%**, stated in the table's caption.

1. **Remaining allowance per window** = (100 − used_percentage) × tokens_per_percent × (1 − margin).
   For an owner-entered per-model window the user's tokens-left figure stands in for the product.
2. **Walk the units in plan order, accumulating.** For each unit, add its estimate to the running
   total for every window and test each total against that window's remaining allowance. The unit
   is marked with the **first window it fits**, in this order: `this 5-hour window` (fits the
   5-hour remainder and the week's) · `next 5-hour window at HH:MM` (over the 5-hour remainder,
   inside the week's; local time from `five_hour.resets_at`; the 5-hour running total restarts at
   a full window less margin, 100 × tokens_per_percent × (1 − margin)) · `next week` (over the
   week's remainder; from `seven_day.resets_at`; the weekly total restarts likewise). `this week`
   appears only in a plan that has a 7-day reading and no 5-hour one (an owner who tracks the
   week alone): it means the unit fits the week's remainder. A per-model window the user named
   is tested alongside the harness windows and its name appears in the cell when it is the
   binding one.
3. **A wave splits only at unit boundaries.** The first unit that no longer fits the current window
   starts the next wave; nothing inside a unit is cut to make it fit. When a later unit fits the
   current window but an earlier one did not, plan order still wins — the wave does not reorder
   itself around the numbers.
4. **A single unit larger than a whole window** — its estimate exceeds 100 × tokens_per_percent ×
   (1 − margin) for any window it must pass through — is a **decomposition defect** (the unit is
   re-cut, in a fan-out by dispatchwright's Decompose), not a scheduling problem. The table shows it with `too large` in the window column and the plan
   stops there, before any confirmation line, to re-cut the unit.
5. The result goes into every row's `window` cell (dispatchwright's ledger schema), in the exact
   wording above, so the guard and a resuming session read the same word the table showed.
6. **CI minutes are fitted too** (observations 0169, 0185). A unit whose proof needs hosted CI
   carries an estimate in minutes; sum them in plan order against the month's hosted minutes left
   less the hosted floor (`references/accounting.md` — CI minutes). A unit past that line reads
   `waits for CI minutes` in the window cell, and the budget decision file's `hosted_ci_allowed`
   is `false`. A local or self-hosted run spends none, so it is the default proof; batched pushes
   (one per wave, not one per piece) are what keep the hosted total small.

Nothing here rounds a unit up "to be safe": the margin is the only conservatism, and it is stated.

## The table and the stop

A fan-out's plan (`dispatchwright plan`) ends by presenting **one table** and **one confirmation
line**, then stops. `pacewright fit` on a list of planned units or sessions, with no fan-out in
play, shows the same table and stops the same way:

```text
Wave plan — run 2026-09-17-example · margin 15% · 5h 23.5% used (resets 14:00) · 7d 41.2% used (resets Tue 09:00) · calibration: 5h 3 samples, 7d one data point
| unit | class      | model         | effort | est. tokens          | est. wall | window                         |
|------|------------|---------------|--------|----------------------|-----------|--------------------------------|
| U1   | mechanical | <fast tier>   | low    | 60k (median of 4 rows) | 1 min   | this 5-hour window             |
| U2   | structured | <default worker> | medium | 400k (median of 2 rows) | 9 min | this 5-hour window             |
| U3   | judgment   | <top tier>    | high   | 900k (owner)           | 33 min  | next 5-hour window at 14:00    |
| U4   | judgment   | <top tier>    | high   | 700k (owner)           | 26 min  | next 5-hour window at 14:00    |
Runs now: U1–U2 (~460k, ~10 min). Waits for the next 5-hour window at 14:00: U3–U4 (~1.6M). Go?
```

Columns, in order, always: **unit | class | model | effort | est. tokens | est. wall | window**.
The caption names the run, the margin, each window's reading, and the calibration state — so the
owner sees on one line whether the fit rests on measurement or on a single point. The confirmation
line says what runs now and what waits, and ends in a question. **Nothing launches until the user
says go.** A declined or partial plan is handed back as the ledger file with the window column
filled, nothing launched.

`dispatchwright dispatch` on a plan the user has approved runs it without a second ask. When
the approved plan's later waves are marked for a next window, dispatch launches the current wave,
then waits for that window's reset and re-reads the data file (or asks) before launching the
next — never launches against the old reading.

## A unit added mid-run

A unit added while a run is live gets a row through the same table and is fitted
against the **current** reading, not the one the plan was fitted to. It is announced in one line
— unit, model, effort, estimate, the window it landed in. It asks again **only** when its estimate
pushes the running total past the window the approved plan was fitted to; a unit that still fits
is announced and dispatched.

## What Reconcile writes back

A reconcile — dispatchwright's in a fan-out, `pacewright check` otherwise — closes the loop per
row and per wave. pacewright owns the calibration file; a fan-out's reconcile appends to it under
the rules below:

- on the row: the actual tokens the unit spent (from its own report, restated against the
  harness's own per-agent count where the surface prints one), the actual wall time, and
  `pct_at_reconcile` — the window's used-percentage at the time of the reconcile read;
- per wave: one calibration point per window (the rules above), appended to
  `~/.dispatch/usage-calibration.json`, the median recomputed, `samples` and `updated` rewritten;
  and one `wall` point per class for every verified row that recorded its wall time;
- in the report: the fit's estimated tokens beside the actual, per window, in the
  actual-vs-estimated table a fan-out's reconcile already produces per tier.

A wave whose `pct_at_dispatch` is missing (the guard was not installed, or the file was absent
at dispatch) produces no calibration point; the report says so, and the next plan's calibration
state shows the sample count that results.

## The rig hooks (not package contents)

Kept in the `claude-skills` repo under `.claude/hooks/` and installed from there, beside
dispatchwright's two forcing hooks. Where the statusline and hooks are placed is rigwright's.
A surface without them runs the procedure above by hand.

- **`usage_windows.py`** — the statusLine command. Reads the statusline JSON on stdin, writes
  `~/.claude/usage-windows.json` atomically (temp file, then replace) whenever the payload carries
  at least one rate-limit window, and prints one compact line: model · context used % · 5h used %
  (resets HH:MM) · 7d used % (resets Day HH:MM). Absent fields print nothing. It never crashes on a
  missing key — a crash blanks the user's status bar.
- **`dispatch_gate.py`** — when the file is fresh, its `additionalContext` gains one line with the
  windows and the calibration state; when absent or stale, the line says the plan must ask.
- **`dispatch_ledger_guard.py`** — on a Task/Agent/Workflow call, sums `estimated_tokens` over the
  open rows, converts each window's remaining percent through the calibration, and **warns** (one
  line into `additionalContext`, exit 0) when the allowance minus margin is below the sum; **fails
  closed** (exit 2, naming the reset time) when `five_hour.used_percentage` is 97 or more, unless
  every open row's `window` cell begins with `next` and the call is the user's explicit resume.
  With no fresh file it says nothing, because the plan step already asked. It records
  `pct_at_dispatch` on the row where it can.
