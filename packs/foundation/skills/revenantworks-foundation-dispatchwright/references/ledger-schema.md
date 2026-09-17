# Ledger schema

The run ledger is the one artifact Reconcile (SKILL.md §8) trusts over any agent's word. One row
per dispatched unit, written at three points in its life — dispatch, commit, push — never
reconstructed from memory after the fact.

## Where it lives

A run directory inside the repo being worked, not this skill's own folder and not a path outside
the repo: `<repo>/.dispatch/runs/<run-id>/ledger.md` (or `.csv` — either is fine, a run picks one
and states it in the plan). `<run-id>` is a short date-plus-slug the plan names once, e.g.
`2026-08-18-estate-sweep`.

**Committed, not gitignored (reversed 2026-09-10, task-observer observation #0032).** The ledger,
any `RESUME.md`, and any `OWNER-STEPS.md` beside it are committed to the run's own repo at every
one of the three write points below — SKILL.md §5's durability contract applies to the run's own
record, not only to the units it dispatches. Untracked state is one `git stash` (a session
handover, a teleport, a worktree switch) away from vanishing, and a session that finds a clean
tree reads that as "nothing to recover" rather than "something got stashed" — see Resuming a run,
below. If the run directory lives in a repo with no remote, say so in the ledger's own header so
a reader knows a local commit there is the only copy that exists anywhere.

An override path may be set via `CLAUDE_DISPATCH_LEDGER` when a run's units span more than one
repo and need to write to a shared location; `dispatch_ledger_guard.py` (the PreToolUse hook, an
optional rig install kept in the `claude-skills` repo under `.claude/hooks/`) reads the same
override, so the two must agree.

## Fields

| Field | What it holds |
|---|---|
| `unit_id` | Short, stable — `U1`, `U2`, … The number a unit's own brief and its ledger row share. |
| `task` | One line: what the unit does. |
| `class` | `mechanical` \| `structured` \| `judgment` — the same three classes the 2026-08-17 rebuild's lesson names, and the input to Tier (§4). |
| `model` | Read from this skill's own `references/tier-routing.md` — never invented, never rounded up "to be safe" (self-contained since 1.2.9, observation #0073). |
| `effort` | From the same file: the effort ladder and its role-based overrides. |
| `surface` | `inline` \| `subagent (background)` \| `subagent (foreground)` \| `remote worktree`. **A row for a Workflow or Task call that itself fans out to more than one agent states the count as an `x<N>` token in this cell** — `subagent (workflow) x245`, not three rows for 245 agents (task-observer observation #0022: three rows once hid 245 refuter agents from the wave cap and the usage-window check). `dispatch_ledger_guard.py`'s `open_unit_count()` parses the token and counts the row as N units against the 6-unit wave cap, not 1; a missing or malformed token (no digits, `x0`, `xN`) defaults to 1, the same weight a row with no token carries. Two tokens in one cell: the last one wins. |
| `repo` | The repo this unit writes, or `—` for a read-only unit. |
| `worktree` / `branch` | The path and branch a writer unit runs in, per §6's one-writer-per-repo rule. `—` for a unit that shares the main tree. |
| `expected_artifacts` | What the unit should produce — a file, a commit, a report — stated before dispatch, not inferred after. |
| `estimated_tokens` | The plan's own estimate, for §8's actual-vs-estimated report, with its basis beside it — `60000 (median of 4 rows)` or `400000 (owner)` (`references/window-fit.md`). **A row for a Workflow or Task call that fans out to N agents holds N × the per-agent figure** — the N being the `x<N>` token on its `surface` cell — so the guard can take the column as written. `dispatch_ledger_guard.py` sums this column over the open rows exactly as written (no re-weighting by the surface cell) to compare against the windows' remaining allowance; a cell it cannot read as a number counts as 0 and is named in its warning. A per-agent figure written here under-counts the wave by the fan-out factor (observation #0022). |
| `est_wall` *(optional, 1.3.0)* | The plan's wall-time estimate for the table — est. tokens × the class's measured seconds per thousand tokens from the calibration file, or `—` when no sample exists. |
| `window` *(optional, 1.3.0)* | Which window the fit placed the unit in, in the table's own words: `this 5-hour window`, `this week`, `next 5-hour window at HH:MM`, `next week`, an owner-named per-model window, `too large`, or `unfitted`. A cell beginning `next` is what lets the guard's ≥97% block stand aside on the owner's explicit resume. |
| `pct_at_dispatch` *(optional, 1.3.0)* | The windows' used-percentages when the unit launched, `5h=23.5 7d=41.2`. Written by the guard when the windows file is fresh, else by the dispatcher from the reading the plan used, else left empty — never back-filled from memory. |
| `pct_at_reconcile` *(optional, 1.3.0)* | The same reading at Reconcile, same form. The pair is one calibration point per wave (`references/window-fit.md`); a wave missing either half yields none. |
| `dispatch_ts` | Timestamp the row was written, before the unit launched. |
| `commit_sha` | The commit the unit made, once it reports one. |
| `commit_ts` | Timestamp the commit line was added to the row. |
| `push_ts` | Timestamp the row was updated after a confirmed push. |
| `remote_sha` | What `git rev-parse origin/main` (or the unit's branch) actually shows — the field Reconcile checks, not `commit_sha`. |
| `reversal` | How this unit's change is undone: the exact command, or the path of the file holding the prior state — written at the same time as `commit_sha`, by the unit that made the change, never by a later reader (task-observer observation #0045). A git commit reverses itself, so a row whose only surface is a commit may read `—`; every other surface — a setting, a plugin, a routine, a remote, a junction, a moved folder, a repo description — carries its own. Reconcile (SKILL.md §8) treats an empty `reversal` on a landed non-git row as unverified. The counter-example the rule comes from: twenty-one branch deletions were the one destructive action whose undo was written as it happened (`cache/branch-deletions.json`, one tip sha per branch), and theirs is the only rollback line that is exact. |
| `status` | `dispatched` \| `committed` \| `pushed` \| `verified` \| `done` \| `stalled` \| `failed` \| `resumed`. Only `verified` means `commit_sha == remote_sha` was checked and matched; `done` is the closing state for a unit that produces no commit (see Closing a row). |

The four 1.3.0 columns are optional: `dispatch_ledger_guard.py` tolerates a ledger without them —
every ledger written before 1.3.0 — and a plan that omits them loses only the fit's record, not
the guard's other checks.

## Closing a row

Every way a unit can end needs a defined end state, **including the ways that produce no commit**
(task-observer observation #0023). A lifecycle whose only exit is a matched sha leaves read-only
units and failures parked at `dispatched` forever: twenty-five open rows once blocked a launch
against a six-unit cap, sixteen of them units that had finished hours earlier, and closing them
took a regex edit this doctrine nowhere described.

| How the unit ended | Closing status | Written when |
|---|---|---|
| Writer unit, sha matched on origin | `verified` | Reconcile confirms `remote_sha` |
| Read-only unit (no repo, no commit) | `done` | its report is received |
| Unit that found nothing to change | `done`, with "no change needed" and the reason | its report is received |
| Unit whose work was absorbed by another | `done`, naming the absorbing unit | the merge decision is made |
| Unit that failed | `failed`, with the reason in the cell | the failure is known |

**The dispatcher closes the row when the unit returns, not at Reconcile.** Reconcile still
verifies every writer row independently — closing a read-only row early does not shorten the
audit, it only stops a finished unit from counting as running.

**The wave cap counts only rows in `dispatched` or `committed`.** That is the rule that makes
"what must I close before the next wave" answerable off the ledger instead of by memory.

## Worked example row

```
| unit_id | task                          | class      | model            | effort | surface            | repo    | worktree/branch      | expected_artifacts       | estimated_tokens | dispatch_ts         | commit_sha | commit_ts | push_ts | remote_sha | status   |
|---------|-------------------------------|------------|------------------|--------|---------------------|---------|-----------------------|--------------------------|-------------------|----------------------|------------|-----------|---------|------------|----------|
| U3      | rewrite README paths after move | mechanical | Claude Haiku 4.5 | none   | subagent (background) | workshop | wt-u3 / dispatch-u3   | README.md diff, 1 commit | 4000              | 2026-08-18T14:02:11Z | a1b2c3d    | 14:06Z    | 14:06Z  | a1b2c3d    | verified |
```

`status` reaches `verified` only after Reconcile confirms `remote_sha` independently — a row a
unit's own report marks "done" stays at `pushed` until that check runs. The example omits the
`reversal` column for width; this unit's surface is a git commit, so that cell would read `—`.

## Writing the ledger

Every unit's brief (`references/unit-brief-template.md`) includes the exact row it must keep
current — the unit updates its own row at commit and at push, and the dispatcher (or the next
resumed session) writes the `dispatch` row before launch. No unit is launched without one. Each
of those three writes is followed by a commit of the ledger file itself (`git add` the ledger
path, `RESUME.md`, `OWNER-STEPS.md` — `git commit`), per "Where it lives" above; a row updated in
the working tree but never committed is exactly as recoverable as a row never written.

## Resuming a run

Before reading the ledger as ground truth, confirm it is still there in the shape it was left.
When the ledger path is missing, or the tree reads unexpectedly clean where the plan says a run
was mid-flight, run `git stash list` and `git reflog -5` on the run's own repo before concluding
the run has no state — a handover, a teleport, or a worktree switch can stash the whole
untracked-or-uncommitted run directory silently, and a clean `git status` after that reads as
"nothing to recover" rather than "something is stashed" (task-observer observation #0032). One
`git stash pop` on the right stash restores it; nothing about a plain read of the working tree
tells a resuming session to look there.
