# revenantworks-foundation-handoffwright

Owns every handoff. It writes either this session's own state, verified against `git`, or a
forward task brief for a later session or agent. It commits the file in the same call, so the
record survives whatever happens to the working tree next. Then it emits a paste-ready starter
prompt for the next chat. Built to close the gap task-observer observation #0032 found: a
session's own written state, left uncommitted, is one `git stash` away from silently
disappearing.

What separates it from a chat summary or a plain saved file:

- **It commits in the same call.** Write and Commit are one step, never a file left in the
  working tree for "later." It stages the handoff and the paths it names, never `git add -A`.
  Where the repo has no remote, it says commit-only. Where the repo's CLAUDE.md sets a batched or
  local-first push policy, it reports the push as deferred.
- **Every claim traces to `git`, never to a report.** State now lists a repo's landed shas only
  once `git log --oneline origin/main -5` shows them. A unit's own "done" is not enough.
- **Two shapes, one skill.** A resume states what already happened. A forward brief states what
  should happen next: dependencies landed or not, each step with a "done when" check and an undo
  for risky ones, portable commands, no session-scoped handle, and a `Model:` line from
  promptwright.
- **Resume checks the tree first.** `git stash list`, `git reflog -5` and an ancestry check on
  the handoff sha, then a four-line staleness report (age, commits since, ancestry, uncommitted
  files). It proposes the first Next step and waits for a go before any write.
- **It never duplicates a dispatchwright ledger.** Inside an active fan-out, unit state is read
  from the ledger already there.

**Workflow:** Gather (git, the ledger if one exists, this session's own record) → Write (the
template shape) → Commit (same call, same repo) → Report the sha **and emit the paste-ready
starter prompt** for the next chat

## Package contents

```
revenantworks-foundation-handoffwright/
├── SKILL.md                      # entry points — bare invocation, Write, Resume; the Never list
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md (sources + dated parity register)
├── references/
│   └── handoff-template.md       # both shapes, size note, starter prompt, resume checks, location
└── evals/                        # in full folder-zips, excluded from .skill
    ├── trigger-evals.md          # 17 queries: 8 should-fire, 7 should-not, 2 injection probes
    ├── test-cases.md             # 16 assertion-suite cases
    ├── RESULTS.md                # blind trigger judges and the traced assertion run
    └── <case>/                   # 3 native `claude plugin eval` cases (prompt.md + graders/)
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your
skills directory, or upload the archive in Claude settings. Trigger it by saying `handoffwright`,
`write the handoff`, `hand off`, `give me a prompt to hand off`, `pause here`, `holding
position`, or `handoffwright resume`. Self-contained: no executable code ships. `git` turns State
now into evidence and runs the commit; without it the handoff still writes, every claim it would
have verified is marked unverified, and the commit is reported as skipped. promptwright and
dispatchwright are optional siblings: without promptwright a brief's Model line reads
"unassigned — tier with promptwright"; without dispatchwright there is no ledger to read.

## Entry points

| Entry | What it does |
|---|---|
| **bare invocation** | States the job, both shapes and the dispatchwright boundary, then asks whether to write now |
| **Write** (default) | Gather (verify against `git`, read an existing ledger) → Write the resume or brief shape → Commit in the same call → report the sha and emit the starter prompt |
| **Resume** | Stash, reflog and ancestry checks, a direct read of the committed file, the four-line staleness report, then wait for a go |

## The boundaries

- **dispatchwright's ledger owns an active fan-out's resume state.** handoffwright covers the
  handoff outside that: before a fan-out starts, between fan-outs, or a session that never
  dispatches at all.
- **rigwright places any automatic trigger.** A `PreCompact` hook or usage-limit signal that
  fires handoffwright on its own is rigwright's placement question, on request.
- **task-observer's handoff-doc mode is the storage-less fallback.** Where no filesystem or repo
  exists, that mode is the honest answer.

## The commit rule, in one line

Write and commit as one call, in the repo the file lives in, staging only named paths, pushing
to `origin` only where a remote exists and the repo's policy allows. The one exception is a
gitignored location: the file stays local, and the report quotes the ignore rule without calling
it deliberate. Nothing is forced with `-f`.

## Eval status

- Trigger suite: blind cold judges scored 14/14, then 15/15 on a later pre-release build.
- Assertion suite: traced once on a pre-release build (Opus tier, not blind), 15/16; Case 1 has an owed
  wording decision. Haiku and Sonnet tier runs are owed. Details in `evals/RESULTS.md`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
