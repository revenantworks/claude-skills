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
| `model` | Copied verbatim from promptwright's target table — never chosen here. |
| `effort` | Copied verbatim from the same table. |
| `surface` | `inline` \| `subagent (background)` \| `subagent (foreground)` \| `remote worktree`. |
| `repo` | The repo this unit writes, or `—` for a read-only unit. |
| `worktree` / `branch` | The path and branch a writer unit runs in, per §6's one-writer-per-repo rule. `—` for a unit that shares the main tree. |
| `expected_artifacts` | What the unit should produce — a file, a commit, a report — stated before dispatch, not inferred after. |
| `estimated_tokens` | The plan's own estimate, for §8's actual-vs-estimated report. |
| `dispatch_ts` | Timestamp the row was written, before the unit launched. |
| `commit_sha` | The commit the unit made, once it reports one. |
| `commit_ts` | Timestamp the commit line was added to the row. |
| `push_ts` | Timestamp the row was updated after a confirmed push. |
| `remote_sha` | What `git rev-parse origin/main` (or the unit's branch) actually shows — the field Reconcile checks, not `commit_sha`. |
| `status` | `dispatched` \| `committed` \| `pushed` \| `verified` \| `stalled` \| `failed` \| `resumed`. Only `verified` means `commit_sha == remote_sha` was checked and matched. |

## Worked example row

```
| unit_id | task                          | class      | model            | effort | surface            | repo    | worktree/branch      | expected_artifacts       | estimated_tokens | dispatch_ts         | commit_sha | commit_ts | push_ts | remote_sha | status   |
|---------|-------------------------------|------------|------------------|--------|---------------------|---------|-----------------------|--------------------------|-------------------|----------------------|------------|-----------|---------|------------|----------|
| U3      | rewrite README paths after move | mechanical | Claude Haiku 4.5 | none   | subagent (background) | workshop | wt-u3 / dispatch-u3   | README.md diff, 1 commit | 4000              | 2026-08-18T14:02:11Z | a1b2c3d    | 14:06Z    | 14:06Z  | a1b2c3d    | verified |
```

`status` reaches `verified` only after Reconcile confirms `remote_sha` independently — a row a
unit's own report marks "done" stays at `pushed` until that check runs.

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
