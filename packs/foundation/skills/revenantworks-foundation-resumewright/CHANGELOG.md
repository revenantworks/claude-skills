# Changelog — revenantworks-foundation-resumewright

## [1.0.3] — 2026-09-14

**Same routing miss as promptwright 1.5.9, the other half** (observation #0071). Asked for "a
prompt to hand off to do the work later," the acting session correctly did not invoke
resumewright — but only because its scope was checked *after* the owner asked a second time, not
because the request was routed there and declined. A session-state handoff and a forward task
brief look alike from the outside (both are "a document for a later reader") and this skill's
description named nothing to tell them apart.

- `description` gains "hand off"/"handoff" as explicit trigger phrasing (closer to how the owner
  actually asked) plus an explicit exclusion: a request to hand off work that has not started yet
  is a task brief, not a resume, and routes to promptwright's Entry — Model for the tier pick, or
  plain writing / dispatchwright's unit-brief template for the content.
- The `Write` entry point gains the same distinction in the body, so the boundary is stated where
  the decision is actually made, not only in the frontmatter.
- `evals/trigger-evals.md` gains **#15** (should-not: a forward task brief for new work — nothing
  for this skill to verify against git yet). 16 → **17**, 7/7 → **7/8**. The `description` moved,
  so a full cold re-judge is owed and not yet performed — recorded rather than skipped.

## [1.0.2] — 2026-09-13

Weekly skill review (autonomous mode), observation #0045.

- The handoff's State block gains a line per non-git change with its reversal: a setting, plugin,
  routine, remote or junction the session changed, undone by an exact command or restored from a
  file holding the prior value, written by the session that made the change. A landed sha reverses
  itself; nothing else in the handoff did, so a resume could not undo what a paused session had done.
  Mirrors the `reversal` field dispatchwright's ledger row gains in the same review.
- One line under What resumewright never does states the rule.

## [1.0.1] — 2026-09-11

**Local-path leak fixed on first tag** (`tools/test_release_paths.py`'s
`test_no_absolute_local_path_in_tracked_files`, widened 2026-09-10 per task-observer observation
#0013 — the CHANGELOG-only exemption does not travel to other file classes; this is exactly the
next class it was warning about). `SOURCES.md` named three private files by their absolute
drive-letter path (the owner's own estate-run directory, the observation-log path) — this repo
is public and no such path belongs in a tracked file. The three rows are unchanged in what they
say; each now names its source generically ("a private estate-run directory's own RESUME.md,"
"owner-private observation log") instead of by path. The test was written *before* this member's
first commit and passed, because `git grep` (the check's own mechanism) only scans tracked
content — a brand-new, not-yet-`git add`-ed file is invisible to it until the moment it lands.
Caught and fixed in the very next commit against origin, before any other change rode on top of
it. `description` and every behavior rule are byte-identical; no eval re-anchor beyond the
provenance-line restatement below.

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
