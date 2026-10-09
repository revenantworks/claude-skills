# Ledger schema

The run ledger is the one artifact Reconcile (SKILL.md §8) trusts over any agent's word. One row
per dispatched unit, written at three points in its life — dispatch, commit, push — never
reconstructed from memory after the fact.

## Contents

- Where it lives — committed in a private repo, off git in a public one, `git check-ignore` at
  plan time, the lookup order
- Fields — every column, including `files_allowed`, `blocked_by`, `call_cap`, `actual`, `rework`,
  `meters` and the ledger v2 close fields; row validation
- Timestamps — one clock call, never a `~` time
- Header blocks — plan status, milestone health, rulings with their home, meters, recovery state,
  actuals
- Closing a row — every end state, including `landed locally` and `unverified`
- Worked example row
- Writing the ledger
- Resuming a run

## Where it lives

A run directory inside the repo being worked, not this skill's own folder and not a path outside
the repo: `<repo>/.dispatch/runs/<run-id>/ledger.md` (or `.csv` — either is fine, a run picks one
and states it in the plan). `<run-id>` is a short date-plus-slug the plan names once, e.g.
`2026-08-18-estate-sweep`.

**Committed in a private repo, off git in a public one** (observations #0032, #0203; owner ruling
2026-10-01). The plan states which case the run is in, as one ledger header line:
`records: private (committed)` or `records: public (off git)`.

- **Private repo:** the ledger, any `RESUME.md`, and any `OWNER-STEPS.md` beside it are committed
  to the run's own repo at every one of the three write points below — SKILL.md §5's durability
  contract applies to the run's own record, not only to the units it dispatches. Untracked state
  is one `git stash` (a session handover, a teleport, a worktree switch) away from vanishing, and a
  session that finds a clean tree reads that as "nothing to recover" rather than "something got
  stashed" — see Resuming a run, below.
- **Public repo:** run records stay untracked — the run directory is git-ignored, and the records
  live on disk or in a private companion repo that is committed at each write point instead. A run
  record carries owner decisions, account names and internal paths that a public history keeps
  forever. If any run file is ever staged in the public repo, leak-check the staged files first
  (names, paths, emails, credentials) and stop on a hit. Because untracked records can be stashed
  away, the `git stash list` check in Resuming a run applies with more force here.
- **Both:** records use repo-relative paths only, never a user-profile or drive path. If the run
  directory lives in a repo with no remote, say so in the header so a reader knows a local commit
  there is the only copy that exists anywhere.

**At plan time, run `git check-ignore -v <ledger path>`** (observation 0191). In a private repo,
a match is a stop: name the ignore rule it prints, because an ignored ledger is committed by
nothing but `git add -f`, so every write point below would record nothing. Narrow the rule
(ignore `.dispatch/**/cache/`, never the run directory) before the first row is written. In a
public repo, a match is the expected state; no match means the run directory would be committed,
so add the ignore rule before the first row.

**Lookup order** (observation 0172) — the ledger a session, a resume and the guard all read is the
first of:

1. `CLAUDE_DISPATCH_LEDGER` — names one file and wins outright; set it when a run's units span
   more than one repo and write to a shared location.
2. A pointer file, `.dispatch/ledger-path`, one line naming the ledger, in a searched directory.
3. `.dispatch/runs/*/ledger.{md,csv}` in the session's working directory, then in each parent up
   to the repo root — so a session started in a subfolder still finds the run.
4. Pinned roots named in `CLAUDE_DISPATCH_ROOTS` — for a session whose working directory sits
   outside the run's repo.

`dispatch_ledger_guard.py` (the PreToolUse hook, an optional rig install kept in the
`claude-skills` repo under `.claude/hooks/`) follows the same order, prints every directory it
searched when it refuses, and warns (never blocks) when the ledger is git-ignored or a closed row
carries anything but the bare word `done`.

## Fields

| Field | What it holds |
|---|---|
| `unit_id` | Short, stable — `U1`, `U2`, … The number a unit's own brief and its ledger row share. |
| `task` | One line: what the unit does. |
| `class` | `mechanical` \| `structured` \| `judgment` — the three work classes one large rebuild's lesson names, and the input to Tier (§4). |
| `model` | Read from this skill's own `references/tier-routing.md` — never invented, never rounded up "to be safe" (self-contained since 1.2.9, observation #0073). |
| `effort` | From the same file, **written as it will bind** (observation 0179): the value in the agent definition the unit launches by, or `inherited (<session effort>)` where the surface has no definitions. Never the intended value alone. |
| `surface` | `inline` \| `subagent (background)` \| `subagent (foreground)` \| `teammate` \| `remote worktree`, plus `· def: <agent definition>` when the unit launches by `subagent_type` (tier-routing.md, How effort actually binds). **`teammate`** (an agent-teams teammate) is for read-only research and review waves only: an in-process teammate cannot be resumed, inherits the lead's effort, cannot nest, and the feature is experimental. **A row for a Workflow or Task call that itself fans out to more than one agent states the count as an `x<N>` token in this cell** — `subagent (workflow) x245`, not three rows for 245 agents (observation #0022). `dispatch_ledger_guard.py`'s `open_unit_count()` parses the token and counts the row as N units against the 6-unit wave cap; a missing or malformed token (no digits, `x0`, `xN`) defaults to 1. Two tokens in one cell: the last one wins. **Where a step in this unit's route needs a credential the unit may not switch to, the split is recorded here too** — `subagent (background) · PR and release: controller` (observation #0088). |
| `repo` | The repo this unit writes, or `—` for a read-only unit. |
| `worktree` / `branch` | The path and branch a writer unit runs in, per §6's one-writer-per-repo rule. `—` for a unit that shares the main tree. |
| `files_allowed` | The paths or globs this writer may change (observation 0183). The brief states the same list; Reconcile runs `git diff --name-status <base>..<sha>`, and a path outside the list makes the row `unverified`. Two writers in one repo need disjoint lists (SKILL.md §6). `—` for a read-only unit. |
| `blocked_by` | The unit ids this row waits on, or `—`. A row launches only when every row it names is closed; the wave table orders by these edges. |
| `call_cap` | The tool-call ceiling the brief gives the unit (observation 0165), **counted by the harness**, never by the unit (observation 0280): the unit stops near 0.85 of it to leave room to commit and report, and §7's 2x-budget stop reads the harness's count as the only evidence. Part of the cap is reserved for verification (unit-brief-template.md, Budget). There is no per-unit token stop; a size gate names the tool that measures it. Where gatewarden's call-cap hook is installed, the controller may write the launched agent's cap into that hook's caps file so the hook refuses calls past it; the hook is gatewarden's, the cap is this row's. |
| `expected_artifacts` | What the unit should produce — a file, a commit, a report — stated before dispatch, not inferred after. |
| `estimated_tokens` | The plan's own estimate, with its basis beside it — `60000 (median of 4 rows)` or `400000 (owner)`. **A row for a Workflow or Task call that fans out to N agents holds N × the per-agent figure** — the N being the `x<N>` token on its `surface` cell — so the guard can take the column as written. The guard sums this column over the open rows exactly as written; a cell it cannot read as a number counts as 0 and is named in its warning. |
| `actual` | `<tokens> / <calls> / <min>`, copied from the harness's completion notice (observation 0144). A figure the unit reports about itself is written with `(self-reported, unverified)` and never feeds a calibration. |
| `rework` | `0` or the number of fix rounds the row needed, with the finding ids — the input to the actuals block and to measured-cost tiering (tier-routing.md). |
| `meters` | What this unit spent per meter besides Claude tokens, from readings taken at dispatch and at close (`references/meters.md`): `ci_min=4 api=120`, or `—` when it spent none. Free local tools write `local`. |
| `harness_tokens` | The harness's token figure for the unit, the number only. **Mandatory at close** for every row that ran an agent (observation 0271). |
| `done_ts` | Timestamp the row closed (Timestamps, below). **Mandatory at close.** |
| `ci_green` *(writer rows)* | `yes` \| `no` \| `n/a` — the remote CI result on `remote_sha`, read by full sha. |
| `bar_met` *(rows with a gate)* | `yes` \| `no` \| `advisory` — the gate's bar as re-derived at Reconcile; `advisory` when the bar is below measured rig noise. |
| `round_reason` *(fix rounds)* | `finding` \| `gate` \| `ci` \| `owner` \| `brief-defect` — why this row exists, when it is a fix round. |
| `trial_arm` *(trial rows)* | The arm a model or rule trial assigned this row (`on`, `off`, `later`, or a model alias), else `—`. |
| `est_wall` *(optional)* | The plan's wall-time estimate, or `—` when no sample exists. |
| `window` *(optional)* | Where the fit placed the unit: `this 5-hour window`, `this week`, `next 5-hour window at HH:MM`, `next week`, `too large`, `unfitted`, or `unfitted (owner go)` (SKILL.md §6). Written from the budget decision file where a pacing skill wrote one; otherwise from dispatchwright's own simple fit. |
| `pct_at_dispatch` / `pct_at_reconcile` *(optional)* | The windows' used-percentages at launch and at Reconcile, `5h=23.5 7d=41.2`, taken from the same clock call as the row's timestamp. Never back-filled from memory. A pacing skill reads the pair as one calibration point. |
| `shared_artifacts` *(optional, parallel-writer waves)* | Content this unit's file shares with another writer's — a table, a string set, a constant — and how it was settled: `central` (fixed before dispatch; quote it verbatim), `owner: <unit_id>`, or `—`. Enumerated by grepping the whole document set before the split (observation #0082). The re-check diffs exactly these cells. |
| `script_archive` *(optional, workflow rows)* | Path of the wave script as archived beside the ledger — the record, never a launch handle. |
| `script_launch_handle` *(optional, workflow rows)* | The path the harness returned when it persisted its own copy of the script, with the session it was issued in. Valid for that session only (observation #0081). |
| `dispatch_ts` | Timestamp the row was written, before the unit launched (Timestamps, below). |
| `commit_sha` | The commit the unit made, once it reports one. |
| `commit_ts` | Timestamp the commit line was added to the row. |
| `push_ts` | Timestamp the row was updated after a confirmed push. |
| `remote_sha` | What `git rev-parse origin/main` (or the unit's branch) actually shows — the field Reconcile checks, not `commit_sha`. |
| `reversal` | How this unit's change is undone: the exact command, or the path of the file holding the prior state — written with `commit_sha` by the unit that made the change (observation #0045). A row whose only surface is a git commit may read `—`; every other surface carries its own. Reconcile treats an empty `reversal` on a landed non-git row as unverified. |
| `status` | `dispatched` \| `committed` \| `landed locally` \| `pushed` \| `verified` \| `done` \| `unverified` \| `stalled` \| `failed` \| `resumed`. Only `verified` means `commit_sha == remote_sha` was checked and matched; `done` is the closing state for a unit that produces no commit. |

The optional columns are optional: `dispatch_ledger_guard.py` tolerates a ledger without them —
every ledger written before they existed — and a plan that omits them loses only their record.

**Row validation (ledger v2, observation 0271).** Every cell with a value list above (`class`,
`status`, `ci_green`, `bar_met`, `round_reason`) holds exactly one listed value; `actual`,
`harness_tokens` and `estimated_tokens` lead with a number; every timestamp matches the
Timestamps format; a closed row has `harness_tokens` and `done_ts`. A row that fails any check is
malformed: the controller fixes it before the next launch and never reads it as calibration.
This skill ships no code, so the check runs by hand or in a rig hook that implements this list
and fails on a malformed row — free text in a valued cell is the failure it exists to catch.
A v2 ledger says so in one header line, `ledger: v2`; a rig hook checks every row against this list only when that line is present, so a ledger written before v2 is never failed on it.

## Timestamps

`dispatch_ts`, `commit_ts`, `push_ts`, `done_ts` and every calibration reading come from **one clock call**
per write — `date -u +"%Y-%m-%d %H:%MZ"` or its equivalent — and the readings written beside it are
taken in the same step (observation 0174). A time written with `~`, or recalled rather than read,
is refused: it is exactly the guess the ledger exists to replace. **The controller never types a
time** (observation 0343): not a planned launch time ("dispatched 15:40Z" written at 15:29Z), not a
placeholder ("pushed 17:2xZ"). The stamp comes from the same command that launches, commits or
pushes — `git push origin main && date -u +"%Y-%m-%d %H:%MZ"` — or from a writer that reads the
clock itself, such as the rig's `dispatch_budget_write.py` for the budget file.

## Header blocks

A ledger opens with short blocks above the rows. Each is optional until the run needs it. The
blocks may be tables: the guard reads the first pipe table whose header holds `model`, `effort`
and `surface` as the unit rows, and a refusal names the table it read (observation 0361). So no
header block carries all three of those words in its header.

- **Plan status** (observations 0101, 0113, 0117, 0147, 0158) — one table, `item | built | next | blocked-by`, for the
  plan the run serves. Confirm each dependency exists at HEAD by symbol (a grep for the function
  or constant), never by a sentence in a plan file. A landing out of order records which items it
  subsumes. **Drift alarm:** after N off-plan units (the plan names N; 3 by default) the
  controller stops and asks whether the plan or the run is wrong.
- **Milestone health** — one line per milestone the run serves: `milestone | red/green | the
  machine-verifiable check that decides it` (a test target, a CI job, a grep with an expected
  count). A phase closes only when its line reads green from that check, never from a summary.
- **Rulings** — one row per owner ruling: the ruling verbatim, the sections of the plan it
  inverts, its **home** — the brief and section that will carry it — and its state. A ruling with
  no named home is an open item (observation 0276). A ruling row stays open until the landing that
  carries it out is verified; it is never closed by the ruling itself. A trial ruling carries a tally line
  under it — `arm | unit | result`, one entry per closed trial row — updated at each close, so
  the arm the next row is due is read, not reconstructed (observation 0280).
  **An answer is a ruling too** (observation 0337): when a fix unit closes with open owner
  questions, each becomes a ruling row naming the brief lines it changes. The user's answer
  opens an apply step (edit those lines, commit the brief), and the row closes only when the brief
  says it; a line in a decision log is not the apply. **A wave boundary or trigger a decision
  names** ("after T05n", "end of wave 2") is derived from the brief order and checked: the named
  row must be in the wave the trigger expects, or the trigger never fires.
- **Meters** — the reading per meter at plan time and at each land, with the wave's spend and the
  room left (`references/meters.md`).
- **Recovery state** — when entered, why, which fixer runs, when exited (SKILL.md §6).
- **Actuals** — one line per closed writer row: `unit | class | est | actual | ratio | rework |
  meters`.
  It is the run's own measured cost per class; a pacing skill may read it, and tier-routing's
  measured-cost rule reads it.

## Closing a row

Every way a unit can end needs a defined end state, **including the ways that produce no commit**
(observation #0023). A lifecycle whose only exit is a matched sha leaves read-only units and
failures parked at `dispatched` forever: twenty-five open rows once blocked a launch against a
six-unit cap, sixteen of them units that had finished hours earlier.

| How the unit ended | Closing status | Written when |
|---|---|---|
| Writer unit, sha matched on origin | `verified` | Reconcile confirms `remote_sha` |
| Writer unit, committed locally, push batched by the controller | `landed locally` | the controller confirms the local sha; becomes `verified` after the batch push |
| Read-only unit (no repo, no commit) | `done` | its report is received |
| Unit that found nothing to change | `done`, with "no change needed" and the reason in a note | its report is received |
| Unit whose work was absorbed by another | `done`, naming the absorbing unit in a note | the merge decision is made |
| Row whose claim could not be confirmed | `unverified`, with what failed | Reconcile, or a resume (below) |
| Unit that failed | `failed`, with the reason in the cell | the failure is known |

**The `status` cell of a closed row holds the bare word** (`done`, `verified`, …); the reason
goes in a note column or after the table. The guard warns on a cell such as `done (no change)`.

**The dispatcher closes the row when the unit returns, not at Reconcile.** Reconcile still
verifies every writer row independently.

**The wave cap counts only rows in `dispatched` or `committed`.** That is the rule that makes
"what must I close before the next wave" answerable off the ledger instead of by memory.

## Worked example row

```
| unit_id | task                            | class      | model     | effort | surface                                | repo     | worktree/branch     | files_allowed | call_cap | expected_artifacts       | estimated_tokens | actual            | rework | dispatch_ts       | commit_sha | remote_sha | status   |
|---------|---------------------------------|------------|-----------|--------|----------------------------------------|----------|---------------------|---------------|----------|--------------------------|------------------|-------------------|--------|-------------------|------------|------------|----------|
| U3      | rewrite README paths after move | mechanical | claude-haiku-5-5 | low  | subagent (background) · def: haiku-low | workshop | wt-u3 / dispatch-u3 | README.md     | 30       | README.md diff, 1 commit | 4000 (owner)     | 5200 / 11 / 3     | 0      | 2026-08-18 14:02Z | a1b2c3d    | a1b2c3d    | verified |
```

The example omits `reversal`, `commit_ts` and `push_ts` for width; this unit's surface is a git
commit, so `reversal` would read `—`. The `model` cell holds a full model id or name with its
version (observation 0361): the guard refuses a bare family word such as `opus` or `haiku`.

## Writing the ledger

Every unit's brief (`references/unit-brief-template.md`) includes the exact row it must keep
current — the unit updates its own row at commit and at push, and the dispatcher (or the next
resumed session) writes the `dispatch` row before launch. No unit is launched without one. In a
private repo each of those writes is followed by a commit of the ledger file itself — staged by
path, `git add -- <ledger> RESUME.md OWNER-STEPS.md` — per "Where it lives" above; a row updated
in the working tree but never committed is exactly as recoverable as a row never written. In a
public repo the same commit goes to the private companion repo where one exists; otherwise the
record is disk-only and the header says so. Run-record commits carry `[skip ci]` where the
workflow's `paths-ignore` does not already cover them (`references/meters.md`).

**Never edit tracked run records while that repo's local CI runs** (observation 0364). A local
CI script that ends by resetting the tree (`git checkout -- .`, as hosted CI does) discards every
tracked edit made during the run, silently. Commit the records before the CI run starts, buffer
ledger writes until it ends, or keep the run directory in a repo whose CI is not running.

## Resuming a run

Before reading the ledger as ground truth, confirm it is still there in the shape it was left.
When the ledger path is missing, or the tree reads unexpectedly clean where the plan says a run
was mid-flight, run `git stash list` and `git reflog -5` on the run's own repo before concluding
the run has no state — a handover, a teleport, or a worktree switch can stash the whole run
directory silently (observation #0032). One `git stash pop` on the right stash restores it.

**On resume, re-check every closed writer row** (observation 0183): a row reading `done`,
`pushed` or `verified` whose sha is not on origin (or, for `landed locally`, not in the local
branch) is rewritten to `unverified` before anything new launches. A row is only as true as the
last check of it.

**Check every cited base by ancestry, never by existence** (observation 0338). On resume and at
every join check, each base a brief cites passes `git merge-base --is-ancestor <id> origin/main`.
`git cat-file -e` is the wrong test: after a history rewrite the old objects stay in the local
clone (reflog, packs), so a stale base still "exists". After a recorded rewrite, re-point every
run brief from the commit map, parked briefs included, or mark each parked brief stale in one line.

**A workflow wave is relaunched from the archive, inline** (observation #0081). A harness that
accepts a script path only for a script it persisted in the current session refuses the run
directory's copy. So a handoff line reading *"re-dispatch via `Workflow({scriptPath: <run
dir>/…})`"* is exact only for the session that wrote it. Paste `script_archive` inline, then write
the new `script_launch_handle` onto the row. The quieter danger: a session that edits the run-dir
copy and relaunches by a still-valid harness path runs the stale script.

Optional mods write beside the ledger (an `actuals.jsonl` sidecar, never the ledger itself) and never stand in for the forcing hooks: `references/mods.md`, only when their data is present.
