# revenantworks-foundation-resumewright

Writes a committed session handoff — on request, before a pause, or ahead of a usage-limit or
compaction warning — and commits it in the same call, so the record survives whatever happens to
the working tree next. Built to close the gap task-observer observation #0032 found: a session's
own written state, left uncommitted, is one `git stash` away from silently disappearing.

What separates it from a chat summary or a plain saved file:

- **It commits in the same call.** Write and Commit are one step, never a file left in the
  working tree for "later." Where the repo has no remote, it says commit-only rather than
  attempting a push that cannot land anywhere.
- **Every claim traces to `git`, never to a report.** State now lists a repo's landed shas only
  once `git log --oneline origin/main -5` shows them — a unit's own "done" is not enough.
- **Resume checks the tree first.** `git stash list` and `git reflog -5` on the handoff's own
  repo, before the file is trusted — the exact check a handover skipped when #0032 happened.
- **It never duplicates a dispatchwright ledger.** Inside an active fan-out, unit state is read
  from the ledger already there; resumewright is for the session-level handoff outside that.

**Workflow:** Gather (git, the ledger if one exists, this session's own record) → Write (the
template shape) → Commit (same call, same repo) → Report the commit sha

## Package contents

```
revenantworks-foundation-resumewright/
├── SKILL.md                      # entry points — bare invocation, Write, Resume; the Never list
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   └── handoff-template.md       # the file shape, resume-time checks, where the file lives
└── evals/                        # in full folder-zips, excluded from .skill
    ├── trigger-evals.md          # 7 should-fire, 7 should-not, 2 injection probes
    ├── test-cases.md             # 10 assertion-suite cases
    └── RESULTS.md                # authored-not-run ledger — what running the suites still owes
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your
skills directory, or upload the archive in Claude settings. Trigger it by saying `resumewright`,
`write the handoff`, `pause here`, `holding position`, or `resumewright resume`. Self-contained:
no executable code ships. `git` is what turns State now into evidence rather than a guess and
what the commit step itself runs on; without it the handoff still writes, every claim it would
have verified is marked unverified instead of rounded up, and the commit step is reported as
skipped rather than attempted.

## Entry points

| Entry | What it does |
|---|---|
| **bare invocation** | States the job and the dispatchwright boundary, then asks whether to write now |
| **Write** (default) | Gather (verify against `git`, read an existing ledger) → Write the template shape → Commit in the same call → report the sha |
| **Resume** | `git stash list` + `git reflog -5` on the handoff's repo, then a direct read of the committed file |

## The two boundaries

- **dispatchwright's ledger owns an active fan-out's resume state.** resumewright covers the
  session-level handoff outside that — before a fan-out starts, between fan-outs, or a session
  that never dispatches at all. Both sides carry the boundary (dispatchwright 1.2.5 adds a §1
  bullet and a `resume`-entry pointer back).
- **task-observer's handoff-doc mode is the storage-less fallback.** resumewright's whole
  mechanism is a commit; where no filesystem or repo exists, that mode is the honest answer, not
  resumewright.

## The commit rule, in one line

Write and commit as one call, in the repo the file lives in, pushing to `origin` only where a
remote exists — never held for a later step, never gitignored, never left in the working tree.

## What did not land at 1.0.0

- **No automatic trigger.** A `PreCompact` hook or a usage-limit signal that fires resumewright
  on its own is a placement question resumewright deliberately leaves to rigwright, on request —
  it never writes live to a tracked `.claude/settings.json`, `CLAUDE.md`, or hooks directory to
  wire itself in.
- **No cold-listing judge yet.** `evals/RESULTS.md` records both suites as authored, not run.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
