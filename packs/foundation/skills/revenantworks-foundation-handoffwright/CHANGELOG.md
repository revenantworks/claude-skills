# Changelog — revenantworks-foundation-handoffwright

## [1.0.0] — 2026-10-01

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
