# Handoff template

The section shape every Write pass fills in, per SKILL.md step 2. Placeholder content only —
this file is never a record of any real session, repo, or decision; copy the shape, never the
example text. Sections with nothing real to put in them are written as empty or dropped, not
padded (SKILL.md — Behavior notes, Never pad).

## File shape

```markdown
# RESUME — <session or run name> (<one-line status>)

Written <date/time>, <why now — on request, before a pause, a usage-limit or compaction
warning>. Start the next session from <path>. <If a dispatchwright run is active: "Load
dispatchwright, then run its `resume` entry.">

## Incident notes (only if something threatened the record this session — otherwise omit)

<What happened, what was lost or nearly lost, how it was recovered, and the one-line rule that
prevents a repeat — e.g. "run `git stash list` before trusting a clean tree.">

## State now (verified against origin, not against a report)

- <repo>: <N> commits, <what shipped>, verified via `git log --oneline origin/main -5` at
  <sha>. Repeat one line per repo touched this session.
- <non-git change>: <the setting, plugin, routine, remote or junction changed> — undone by
  `<exact command>` or restored from `<path of the file holding the prior state>`. One line per
  change. A landed sha reverses itself; nothing else here does, and an undo reconstructed later
  recovers only what someone happened to mention (task-observer observation #0045).

## Owner decisions recorded (do not re-ask)

<Every standing decision made this session, in enough detail that the next session does not
re-ask the question. One list, not scattered through the state section.>

## Next (in order; reference a ledger row where one exists)

1. <Next step, ordered, with enough context to start cold.>
2. ...

## Questions for the owner (only if any are genuinely open)

1. <A decision only the owner can make, with the options named.>

## Observations logged this session (only if task-observer is active)

<ids and short titles>
```

## Resume-time checks (before trusting the file above)

1. `git stash list` and `git reflog -5` on the repo the handoff file lives in — a handover or a
   worktree switch can stash the whole run or session state silently, and a clean `git status`
   after that reads as "nothing to recover" rather than "something is stashed."
2. Read the committed handoff file directly once the tree is confirmed — no re-deriving what it
   already states.
3. `git log --oneline origin/main -5` per repo named in State now, to confirm nothing has moved
   since the handoff was written — a stale handoff is read as a starting point, not as current
   truth without a re-check.

## Where the file lives

- Inside an existing run directory (a dispatchwright fan-out already in progress):
  `.dispatch/runs/<run-id>/RESUME.md`, beside that run's own `ledger.md` — resumewright reports
  what the ledger already tracks, it never keeps a second copy of unit state.
- An ordinary session with no run directory: the project root, `RESUME.md` — the filename
  already established by this shape, never a second name for the same job.
- A repo with no remote: state that plainly in the file's own header (State now, or the opening
  line) so a reader knows a local commit there is the only copy that exists anywhere.
