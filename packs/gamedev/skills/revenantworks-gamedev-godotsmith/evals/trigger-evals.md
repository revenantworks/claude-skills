# Trigger Evals — 32 queries (16 should / 16 shouldn't)

Counts: 32 queries (16 should, 16 should-not, 10 pairs)

Read each cold against name + description only. Provenance: authored at
`revenantworks-gamedev-godotsmith` v1.0.0, 2026-09-12; history of earlier re-anchors is in
`CHANGELOG.md`. **Re-judged at v1.1.1, 2026-10-01 (pack split P1d)** after the description gained the
design-and-balance and asset-intake triggers: rows 1 to 23 keep their expected values;
row 24's note narrows; rows 25 to 30 are new. Hand-judged by the author model only; the run
record is `RESULTS.md`. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

The hard half is rows 13 to 24 and 28 to 30. godotsmith sits next to things it must not
absorb: general Godot engine and API work, eval-suite authoring, skill building, ordinary
test writing, game design authoring, and its two pack siblings. Every SHOULD NOT sits
deliberately close to one of those seams.

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
| 15 | "Author an eval suite for our new skill's triggers" | SHOULD NOT — near-miss: skillwright evals authors suites |
| 16 | "Score this assertion suite against a rubric" | SHOULD NOT — near-miss: skillwright evals' scoring job |
| 17 | "Build me a skill for Godot shader work" | SHOULD NOT — near-miss: skillwright |
| 18 | "Split this 40-file refactor across agents and reconcile it" | SHOULD NOT — near-miss: dispatchwright |
| 19 | "Write more tests for the ecology module" | SHOULD NOT — near-miss: authoring tests, not proving a run |
| 20 | "Our GitHub Actions runner is out of disk space" | SHOULD NOT — CI infrastructure, not a build's proof |
| 21 | "Migrate the project from Godot 4.3 to 4.7" | SHOULD NOT — near-miss: the upgrade cadence rule is here, the migration work is not |
| 22 | "Profile why the game drops frames in the city scene" | SHOULD NOT — near-miss: finding a cause, not ruling on a figure |
| 23 | "Design the pixel art so units read when zoomed out" | SHOULD NOT — near-miss: pixelsmith, same pack |
| 24 | "What's the best inventory system architecture for an RPG?" | SHOULD NOT — near-miss: design authoring, not proving a rule's claims |
| 25 | "Our emergency ration fires on every shortfall and a full granary still went extinct — how should this fallback trigger, and how do we measure it?" | SHOULD — design-and-balance, survival or grace |
| 26 | "godotsmith intake — wire these WAVs and Ogg loops into the project with the import settings from the audio rundown" | SHOULD — Entry — Intake, the rundown's keys written and guarded |
| 27 | "Does our project actually hold integer zoom and nearest filtering at every band? Check the settings, not the art" | SHOULD — render precondition read off the project |
| 28 | "Invent a tech tree with costs and unlock order for my strategy game" | SHOULD NOT — near-miss: design authoring; godotsmith proves a rule's claims, it does not write the design |
| 29 | "My Ogg music loop clicks at the seam in Godot" | SHOULD NOT — near-miss: soundsmith (the file and its loop offset) |
| 30 | "Is this level fun? Rate the pacing for me" | SHOULD NOT — a judgment gate the user closes; no skill certifies taste |
| 31 | "Review our save code: it writes straight over user://save.json and a crash mid-write wiped a player's save" | SHOULD — Entry — Review, `systems-and-export.md` section 1 (K4 C6, 2026-10-08) |
| 32 | "Build the save and load feature for the colony game, red test first, one slice at a time" | SHOULD NOT — near-miss: slicesmith wins (writing the feature); godotsmith reviews the save conventions after |

## Boundary notes for the judge

- **15, 16 versus 3.** skillwright (its evals entry) authors and scores the suite. godotsmith writes the CI
  assertions *around* a run and rules on whether its numbers can be believed. "Make a suite"
  routes away; "make this run's result trustworthy" routes here.
- **19 versus 4.** Writing tests is ordinary engineering. Asking which functions are
  genuinely uncovered is a claim about a search population, which is L2.
- **21 versus 12.** The rule *upgrade one minor version at a time* lives in
  `project-hygiene.md`, so an ask about upgrade **cadence** is a legitimate pull. Doing the
  migration is not.
- **22 versus 7.** Profiling to find a cause is engine work. Judging whether a measured
  figure clears a plan-stated bar, with conditions named, is a gate ruling.
- **23 versus 27** is the intra-pack art seam. Whether art reads is pixelsmith's; whether the
  project's settings hold the precondition the art assumes is a count against a bar, so
  godotsmith's.
- **29 versus 26** is the audio seam. A file property (a loop offset, a click) is
  soundsmith's; writing the rundown's import keys into the project is godotsmith's.
- **24 and 28 versus 25.** Since 2026-10-01 (owner footprint G2) godotsmith proves a design's
  or balance rule's claims — measured headline, the arms, the fallback shape. Writing the
  design itself (an architecture pick, a tech tree) stays out.
- **30** is L5: no machine closes a judgment gate.
- **32 versus 31** is the slicesmith seam: building the save feature is slicesmith's loop;
  reading a save path against the conventions is godotsmith's review.

## The rows most likely to fail

Recorded before the run so the result can falsify the prediction rather than confirm
whatever happens.

- **15 and 16** sit on the skillwright evals seam and share almost all their vocabulary with it.
- **19** is the sharpest: ordinary test writing overlaps this skill's nouns almost
  completely, and the distinction is about what the deliverable is, not what the subject is.
- **28** now sits beside the description's "simulation or balance rule" phrase; a pull means
  "proving" reads as "designing".
- **27** shares "integer zoom" and "nearest filtering" with pixelsmith's vocabulary; a miss
  means the cold listing routes every precondition question to the art skill.
