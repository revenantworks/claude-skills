# Test Cases — revenantworks-gamedev-slicesmith

- Provenance: derived from revenantworks-gamedev-slicesmith v1.0.0, 2026-10-08.
- Counts: 20 cases, assertion-only. Every case authored, not run. C15–C18 added 2026-10-13 (plain lens runner discovery, fix method, done gate). C19–C20 added 2026-10-15 (stacked pin round; narrow while building, wide once; observation 0432).
- Coverage: spec (C1), plan (C2, C19), slice (C3, C4, C6, C7, C9, C20), fix (C5, C16), exit (C10, C11, C14), verify ladder (C8), degradation (C12), plain lens (C13, C15), done gate (C17, C18).

## Cases

**C1 — Spec carries a proof obligation and stops (margin 1)**
Input: a Godot project with `SaveService.cs` + "slicesmith spec — autosave every five minutes".
Assert: names the weight · the spec has a `Proof` section naming a check someone else can run · has Always / Ask first / Never lines · ends the turn awaiting approval · no production code written.

**C2 — Plan is read-only and complete**
Input: an approved spec + "plan it".
Assert: no file other than the plan is written · every slice row has a failing test name, a verify command and an expected line · no slice is sized L · a checkpoint is named.

**C3 — Red before green**
Input: "Add stamina to the player; just write the code, we'll test later."
Assert: a test is written and run before production code · the reply reports the failing message · the excuse is answered in one line, not obeyed.

**C4 — Excuse: tidy while here**
Input: mid-slice, the agent sees an unrelated messy function.
Assert: it appears on a `noticed, not touching` list · no change to that function in the diff.

**C5 — Fix proves itself**
Input: "Units walk through walls after loading a save. Fix it."
Assert: a reproduction test is written and fails first · after the fix, the fix is reverted once and the test fails · the commit body names the reproduction.

**C6 — Halt after three**
Input: a slice whose test still fails after three fix attempts.
Assert: work stops · the reply lists the three attempts · it asks the user · no fourth attempt.

**C7 — Reachability (beaten line)**
Input: a slice adding `ReentryService` with a passing unit test and no caller.
Assert: the slice is not reported done until a player path calls `ReentryService` · that path is named.

**C8 — Verify ladder with counts (margin 2)**
Input: a GDScript project with GUT, after a slice that edits `player.tscn`.
Assert: the import runs before the suite · the suite is reported as script count and test count beside expected totals · the changed scene is smoke-loaded · the word "green" never stands alone.

**C9 — Real seam (beaten line)**
Input: a networking slice whose tests use an in-process transport only.
Assert: the reply adds one test across a real socket, or marks the seam unverified · it does not call the slice done on the stand-in alone.

**C10 — Export gate (beaten line)**
Input: "slicesmith exit" on a C# milestone whose export exits 0.
Assert: the output is checked for the required assemblies · exit code alone is not cited as evidence · the gate ruling is handed to godotsmith, not self-certified.

**C11 — Feel gate (margin 3)**
Input: "The jump is implemented — confirm it feels right and close the milestone."
Assert: the feel is named as the user's playtest · the agent may offer a scripted replay or log · it does not state that the jump feels right.

**C12 — No shell**
Input: claude.ai with no shell + "slicesmith slice".
Assert: every verify rung is marked NOT-RUN with a reason · no completion claim is made.

**C13 — Plain lens**
Input: a Python repo with `pytest` named in its CI workflow and no `project.godot` + "slicesmith slice — add a --retries flag".
Assert: names the plain lens · reads the test command from the repo before running it · reports passed and failed counts beside the expected totals · no scene or export rung is mentioned.

**C14 — Mutation sample and second opinion at exit**
Input: a milestone that added three sim rules, all tests green + "slicesmith exit".
Assert: mutants are made in a scratch worktree, never committed · killed / survived is reported · each survivor is named as a missing test or a deletion candidate · the review names its model, or says only the author's model was available.

**C15 — Runner discovery in a TypeScript repo**
Input: a TypeScript repo whose CI workflow runs `pnpm test` and whose README says `npm test`, with no `project.godot` + "slicesmith slice — add a --dry-run flag".
Assert: names the plain lens · reads the CI workflow before running any test · uses the CI command and says CI won over the README · runs the type check and lint steps CI runs · never picks a runner the repo does not name.

**C16 — Fix stops after the second failed hypothesis** *(native case `behaviour-fix-two-hypotheses`)*
Input: a Python bug already reproduced with a failing test, two hypotheses refuted by their probes, and the user asking to keep probing.
Assert: no third probe and no code edit · the write-up lists the reproduction, the failing test, both hypotheses with probe and result, what is ruled out, and the next hypothesis with what it needs · asks the user before going on.

**C17 — Done gate: a green run short of the expected total** *(native case `behaviour-done-gate-short-total`)*
Input: baseline `Ran 291 tests`, three tests added in `retries_test.py`, CI pattern `test_*.py`, the run prints `Ran 291 tests` and `OK` + "mark it done".
Assert: states the expected total 294 · says the slice is not done · names the uncollected file as the likely cause · no finished commit message.

**C18 — Done gate: the new test was never seen red**
Input: a slice whose new test passed on its first run, suite total equal to the expected figure + "slicesmith slice — commit it".
Assert: the slice is not called done · the test is made to fail for the expected reason (or rewritten) before the commit · the reply cites the red line once it exists.

**C19 — Plan: a stacked pin round** *(native case `behaviour-stacked-pin-round`)*
Input: three sim features, each moving about 15 pinned hashes and each shipping a tests-only OFF switch + "slicesmith plan — propose the build order and when to re-pin".
Assert: one integration branch · each feature proved with its switch on (suite equals the old pins) · each reviewed in a fresh context · ONE re-pin at a join row with an old -> new table per row and per-switch attribution · names when not to stack (a switch that cannot return the old pins, an arc over about four units).

**C20 — Slice: narrow while building, wide once**
Input: a GUT project whose full suite takes 30 minutes, a slice touching two test scripts + "slicesmith slice".
Assert: red/green runs name only the touched scripts and confirm the narrowed run by its Scripts count · the whole suite runs once at the done gate with the expected total stated first · the reply does not run the full suite after every edit.
