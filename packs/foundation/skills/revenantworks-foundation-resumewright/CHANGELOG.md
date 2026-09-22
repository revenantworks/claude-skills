# Changelog — revenantworks-foundation-resumewright

## [1.1.2] — 2026-09-22

**Two handoff files that both read as current, and an "exact" command only the writing session
could run** (task-observer observations #0080, #0081).

- Write step 2, Location (#0080): a new handoff written beside an older one under another name
  stamps that older file's own header, in the same commit, with a dated line naming its successor
  — a handoff is superseded only when the older file says so. With it, the content rule: a status
  claim that can change lives in exactly one file, every other surface pointing there rather than
  restating it.
- "What resumewright never does" gains a bullet: never leaves an older handoff readable as
  current (#0080).
- Write step 2, the executor-command line (#0081): extends the #0076 rule — a command is *exact*
  only if a fresh session can run it as written, so a harness-issued handle scoped to this session
  (a persisted workflow `scriptPath`, a run id, a session-directory path) is named as the archive
  copy to paste inline plus how to obtain a new handle, never as the path that resolved here.
- `references/handoff-template.md`: Where the file lives gains the supersede stamp and its
  one-line form (#0080); Resume-time checks gain a fourth step for a repo holding more than one
  handoff-shaped file (#0080); Starter-prompt rules gain "never hand over a handle this session
  was issued" (#0081).

The member was patch-bumped at install on 2026-09-22 (`release.py` bumps only the pack).

## [1.1.1] — 2026-09-14

**The first blind re-judge of 1.1.0's description found a regression that 1.1.0 caused; this
patch fixes it.** One fresh judge, holding the listing of all 14 members plus the 15 routing
queries with the key withheld, scored 1.1.0 at **13 / 15**:

- #14 ("There's no filesystem here — just tell me what to paste into the next chat.") came back
  SHOULD. 1.1.0's "With no filesystem, task-observer's handoff-doc mode is the fallback" read as
  this skill covering the case; 1.0.0's wording had passed it.
- #12 ("Set up a hook that writes a handoff automatically before every compaction.") came back
  AMBIGUOUS against rigwright, because no description said who places that hook.

Changes:

- `description`: its closing sentences become one exclusion — resuming an active dispatchwright
  fan-out, setting up a hook that writes handoffs automatically (rigwright's), and a chat with no
  filesystem to commit into (task-observer's handoff-doc mode). 994 → 955 characters, no `: `. A
  second, different fresh judge scored it **15 / 15** (`evals/RESULTS.md`), which discharges the
  re-judge owed since 1.0.3.
- Write step 2, task-brief shape (observation #0076): a command the brief hands its executor points
  at the repo's own command block or gives every surface's form, never only the form that worked
  where the brief was written.
- Eval provenance re-anchored; no case moved.

## [1.1.0] — 2026-09-14

**Owner request: a handoff ends with a paste-ready starter prompt, not a bare sha.** A committed
handoff still left the owner composing the next session's opening message by hand, and the part
most often retyped wrong was the file path — the one thing that makes the rest reachable. The
change was first drafted against 1.0.1 in a synced copy with no git, and kept durable in another
repo until it could land here; it is merged onto 1.0.4, not pasted over it.

- Workflow line and Write step 4: Report now ends by emitting the starter prompt in a fenced
  block — the repo, the handoff file by path, the verified sha and branch, read-this-first, and
  only what the file cannot carry. Step 4 keeps 1.0.4's untracked-location line; for that case the
  prompt names the path and says *uncommitted* instead of a sha.
- "What resumewright never does" gains a first bullet: never ends a Write at the commit sha.
- `references/handoff-template.md` gains a **Starter prompt** section (the block and five rules),
  immediately before Resume-time checks. It is emitted in chat, never written into the file.
- **`description` repaired.** 1.0.4 shipped it at 1321 characters, over the 1024 house ceiling,
  with an unquoted `Entry: Model` that made the whole frontmatter fail YAML parse; `build.py
  --check` failed on both. Rewritten to 994 characters with no `: ` in the value. Every trigger
  phrase is kept verbatim; it now names the starter prompt, and it drops the claim that
  dispatchwright's tiering is promptwright's, untrue since dispatchwright 1.2.9 (#0073).
- `evals/test-cases.md` re-anchored to v1.1.0 (1.0.3 and 1.0.4 never re-anchored it) and gains
  **Case 11** for the starter prompt — 10 → 11 cases, authored, not run.
  `evals/trigger-evals.md` re-anchored; the description moved again, so the cold re-judge owed
  since 1.0.3 is still owed, now against the 1.1.0 text.

## [1.0.4] — 2026-09-14

**Owner ruling on 1.0.3's split, same day** (observation #0072, direct follow-up to #0071).
1.0.3 gave the forward-task-brief half of a handoff request to promptwright and had this skill
explicitly decline it. The owner ruled that shape wrong: one request should mean one skill,
not two skills' descriptions negotiating who owns which half. resumewright now owns every
handoff — backward session state and forward task briefs alike.

- `description` widens from "session state only" to "every handoff" — a forward brief calls
  promptwright's Entry — Model internally for its tier/model line rather than excluding the case.
- The `Write` entry point states the two shapes explicitly (resume vs. task brief) instead of
  declining one of them; step 1 (Gather) runs for both, since a task brief needs the starting
  point too; step 2 (Write) branches by shape, the task-brief shape ending in a `Model:` line from
  promptwright.
- "What resumewright never does" gains an exception: a location gitignored **on purpose** (a
  local-tooling directory with live git worktrees, the exact shape that already forced one prior
  fix in this estate) does not get force-added — the write stands as local state and the report
  says so, rather than fighting a deliberate rule with `-f`.
- `evals/trigger-evals.md`: #15 flips should-not → should, renumbered **#8** in the should-fire
  table. 17 stays 17, split moves 7/8 → **8/7**. Cold re-judge still owed, now against the 1.0.4
  text.

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
