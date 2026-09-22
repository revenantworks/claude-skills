# Trigger Evals — 24 queries (12 should / 12 shouldn't)

Read each cold against name + description only. Provenance: authored at **Re-anchored to v1.0.1, 2026-09-22:** provenance only, nothing executed here: the 2026-09-20 task-observer batch was installed (doctrine and references only). The `description` is byte-identical, so no query, expected value, or count moved.
`revenantworks-gamedev-godotsmith` v1.0.0, 2026-09-12. Authored, not run — see `RESULTS.md`.

The hard half is rows 13 to 24. godotsmith sits next to four things it must not absorb:
general Godot engine and API work, eval-suite authoring, skill building, and ordinary test
writing. Every SHOULD NOT below sits deliberately close to one of those seams.

| # | Query | Expected |
|---|---|---|
| 1 | "The GUT run says all tests passed but I think a test file is being skipped" | SHOULD — the silent-drop trap, L1 |
| 2 | "Our CI asserts at least 404 tests and we're at 411 — is that guard still doing anything?" | SHOULD — floor decay, L3 |
| 3 | "Write the CI step that checks the Godot test run properly" | SHOULD — guard entry |
| 4 | "Which of these functions are actually untested?" | SHOULD — coverage population, L2 |
| 5 | "Can we close the M2b gate? Every check is green" | SHOULD — gate entry, machine versus judgment |
| 6 | "check_camp_year fails — should we just delete it or lower MIN_HEADS?" | SHOULD — honest red, L4 |
| 7 | "The frame rate says 4.24 ms — is that a pass against our budget?" | SHOULD — re-derive the figure |
| 8 | "This clamp is a bare 0.4 and nothing checks it against the band spacing" | SHOULD — magic constant invariant |
| 9 | "godotsmith check" | SHOULD — bare entry |
| 10 | "The class doc says every departure goes through _depart but one branch doesn't" | SHOULD — C5, enforced or decoration |
| 11 | "Review this node — it crashes sometimes when the scene reloads" | SHOULD — review entry, await validity and signal lifetime |
| 12 | "Our seed stopped reproducing and nothing obvious changed" | SHOULD — C4, determinism and global randomness |
| 13 | "Write a CharacterBody2D controller with coyote time" | SHOULD NOT — engine pattern, a general Godot skill's |
| 14 | "How do I set up AnimationTree blend spaces in Godot 4.7?" | SHOULD NOT — API reference |
| 15 | "Author an eval suite for our new skill's triggers" | SHOULD NOT — near-miss: evalwright authors suites |
| 16 | "Score this assertion suite against a rubric" | SHOULD NOT — near-miss: evalwright's scoring job |
| 17 | "Build me a skill for Godot shader work" | SHOULD NOT — near-miss: skillwright |
| 18 | "Split this 40-file refactor across agents and reconcile it" | SHOULD NOT — near-miss: dispatchwright |
| 19 | "Write more tests for the ecology module" | SHOULD NOT — near-miss: authoring tests, not proving a run |
| 20 | "Our GitHub Actions runner is out of disk space" | SHOULD NOT — CI infrastructure, not a build's proof |
| 21 | "Migrate the project from Godot 4.3 to 4.7" | SHOULD NOT — near-miss: the upgrade cadence rule is here, the migration work is not |
| 22 | "Profile why the game drops frames in the city scene" | SHOULD NOT — near-miss: finding a cause, not ruling on a figure |
| 23 | "Design the pixel art so units read when zoomed out" | SHOULD NOT — near-miss: pixelsmith, same pack |
| 24 | "What's the best inventory system architecture for an RPG?" | SHOULD NOT — near-miss: game design, not project convention |

## Boundary notes for the judge

- **15, 16 versus 3.** evalwright authors and scores the suite. godotsmith writes the CI
  assertions *around* a run and rules on whether its numbers can be believed. "Make a suite"
  routes away; "make this run's result trustworthy" routes here.
- **19 versus 4.** Writing tests is ordinary engineering. Asking which functions are
  genuinely uncovered is a claim about a search population, which is L2.
- **21 versus 12.** The rule *upgrade one minor version at a time* lives in
  `project-hygiene.md`, so an ask about upgrade **cadence** is a legitimate pull. Doing the
  migration is not.
- **22 versus 7.** Profiling to find a cause is engine work. Judging whether a measured
  figure clears a plan-stated bar, with conditions named, is a gate ruling.
- **23** is the intra-pack seam. Both members serve the same game; pixelsmith owns how art
  reads, godotsmith owns whether the build is provable.
- **24** is the widest near-miss. The conventions here are about structure that makes a
  project provable, not about which design plays better.

## The four rows most likely to fail

Recorded before the run so the result can falsify the prediction rather than confirm
whatever happens.

- **15 and 16** sit on the evalwright seam and share almost all their vocabulary with it.
  A pull means the description is claiming suite authoring.
- **19** is the sharpest: ordinary test writing overlaps this skill's nouns almost
  completely, and the distinction is about what the deliverable is, not what the subject is.
- **24** tests whether "conventions" in the description reads as project structure or as
  game design. A pull means that word is doing too much work.
