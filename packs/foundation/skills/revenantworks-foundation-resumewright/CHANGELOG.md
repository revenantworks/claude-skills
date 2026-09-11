# Changelog — revenantworks-foundation-resumewright

## [1.0.0] — 2026-09-11

Baseline release. Built from the estate audit's H1/H2 research pass (cache/h1-handoff-research.md):
five candidate skills were surveyed (tenequm's pre-compact, baton, cross-session-handle,
Claude-Skill-Session-Handoff, the anthropics/skills catalog) and none satisfied the commit
requirement observation #0032 exists to close — every real candidate either states "never commit"
outright, gitignores its own output by design, or leaves an uncommitted file with no durability
guarantee at all. None reproduces the `RESUME.md`/`HANDOFF-PROMPT.md` shape either: multi-repo
landed-sha state verified against origin, an ordered remainder referencing a dispatchwright
ledger where one exists, and an owner-decisions block distinct from a next step.

The 1.0 feature set:

- **Write:** Gather (verify every landed sha against `git log --oneline origin/main -5`, never
  against a report) → Write the handoff per `references/handoff-template.md`'s shape → Commit in
  the same call, in the repo the file lives in, pushing to `origin` only where the repo has a
  remote → report the commit sha.
- **Resume:** `git stash list` and `git reflog -5` on the handoff's repo before trusting a clean
  tree, then a direct read of the committed file — matching `dispatchwright resume`'s own first
  action, for the same reason (observation #0032: a handover can stash a whole run or session
  state silently).
- **The dispatchwright boundary:** inside an active fan-out, its own ledger already covers unit
  and resume state; resumewright is for the session-level handoff outside that — before a
  fan-out starts, between fan-outs, or in a session that never dispatches at all. Declared on
  both sides — resumewright's own description and a new §1 bullet plus a resume-entry pointer in
  dispatchwright 1.2.5.
- **The task-observer boundary:** its handoff-doc mode is the fallback for a storage-less
  environment; resumewright's whole mechanism is a commit that mode cannot make, so where a repo
  exists resumewright is the one that runs.
- Never invents a landed sha, a decision, or a completed step; never writes or infers a secret;
  never installs its own trigger (a hook or CLAUDE.md rule wiring it to `PreCompact` or a
  usage-limit signal is rigwright's placement call, on request); never pushes to a remote other
  than `origin`, and never at all where the repo has none.
- 16 trigger evals (7 should / 7 shouldn't / 2 injection probes), 10 assertion-suite cases
  (including the two injection probes restated as mechanical checks) — both authored, not run,
  per the pack's standing first-release convention.
