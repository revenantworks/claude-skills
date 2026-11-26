# Changelog — revenantworks-foundation-handoffwright

## [Unreleased]

- `handoff-template.md` Starter prompt: a prompt that sits in a file, for a terminal session, is handed over as one command, `claude "Read <absolute prompt path> and follow it exactly."`, with "press Enter if the session opens without submitting it"; clipboard handover only for web pastes (observation 0731). Reference only; body unchanged.

## [1.1.0] — 2026-11-24

- Description neighbour list cut to the nearest siblings for the listing budget (SK1a trim list, run 2026-11-23-weekly-loop); no behaviour change.
- Body back under its 3200-token budget (3263 to 3187 by `build.py --footprint`): the starter
  prompt's locator detail (sha, branch and worktree read from git in the commit call, #0684)
  moved from Write step 4 to `handoff-template.md` → Starter prompt, which step 4 already reads.
  No behaviour change.
- Review RV-SK2c: the no-filesystem cue (task-observer's handoff-doc mode) is kept; trigger row #14 routes on it.

- Never pushes (owner pick 2026-11-24): the Write step commits locally and names the push as the
  landing step's job, at a compaction or usage-limit warning too; compatibility, the report line,
  the rules list and `handoff-template.md` say so. Test Case 6 now asserts commit only, no push.
  The landing step is named: `revenantworks-foundation-landwright` when installed (compatibility,
  Write step 3 and the rules list), else the repo's own landing step (run 2026-11-23-weekly-loop
  SK3).

- 2026-11-20 observer review (observation 0620): `handoff-template.md` Next: a step is listed as
  owed only after its log or output was read.

- Write step 4: the starter prompt's sha, branch and worktree path are read from git in the
  repo the file lives in, in the same call as the commit, never copied from the brief's subject
  (#0684).

## [1.0.0] — 2026-10-01

2026-10-16 (full observation review, U21): the Excuses table gains the branch-from-local-main row: a hand-over command that creates a branch for a push fetches, checks shared history and branches from `origin/main` (observation 0442, carrier for 0441).

2026-10-08 (K8 fix round): compatibility declares the optional background-agent tool `now` uses; the bare reply names `now`; "no launch before the commit lands"; the trigger-eval prose count reads 10 / 9; SOURCES cite private runs neutrally (audit K7-2-13, -18, -19, -20, -21).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Owns every handoff and ends each with a paste-ready starter prompt for the
next chat.

### What it does

- Two shapes: a resume (this session's state, verified against git) and a forward task brief (what a
  later session or agent should do next: dependencies landed or not, each step with a "done when"
  check and an undo for risky ones, portable commands, and a `Model:` line from promptwright).
  A starter prompt for a local session names the machine's existing clone, checked with
  `rev-parse --show-toplevel`, never a fresh clone (observation 0358; 2026-10-08, test phase).
- Write and commit are one step: it stages the handoff and the paths it names, never `git add -A`,
  and pushes to origin only where a remote exists and the repo's policy allows; otherwise it reports
  the push deferred or commit-only.
- Every claim traces to git: landed shas are listed only once `git log origin/main` shows them.
- Resume checks the tree first: `git stash list`, `git reflog -5` and an ancestry check, then a
  four-line staleness report, and waits for a go before any write.
- An excuses and red-flags table in the handoff template, read before the commit.

### Entry points

- Bare invocation (states the job and both shapes), Write (default), Now (the committed handoff
  goes straight to a fresh background agent; this session then stops writing that repo), Resume.

### Safety rules

- Never duplicates a dispatchwright ledger; inside an active fan-out, unit state is read from it.
- Never forces with `-f`; a gitignored location stays local and the report quotes the ignore rule.
- Without git the handoff still writes, unverified claims are marked, and the commit is reported
  skipped. Ships no code.

### Integrations

- A forward brief's tier line comes from promptwright (absent: "unassigned — tier with
  promptwright"). An automatic handoff trigger is rigwright's placement question; task-observer's
  handoff-doc mode covers a chat with no filesystem.
