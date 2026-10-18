# Trigger Evals — revenantworks-gamedev-slicesmith

- Provenance: derived from revenantworks-gamedev-slicesmith v1.0.0, 2026-10-08.
- Counts: 32 queries (17 should, 15 should-not, 8 pairs), judged cold against name + description only. Rows 27–31 added 2026-10-13 (plain lens, fix method, done gate). Row 32 added 2026-10-17 (the test-later trigger, moved here from the behaviour case `behaviour-red-first`, which now names the skill).
- Owed: every row authored, not run.

## Should fire

| # | Query | Why |
|---|---|---|
| 1 | "slicesmith" | Quoted invocation keyword |
| 2 | "Implement autosave in my Godot game." | Build a feature in a game |
| 3 | "Add a stamina mechanic to the player controller — write the test first." | Mechanic plus test-first |
| 4 | "Turn GRILL-autosave.md into slices and start on the first one." | A grill record into slices |
| 5 | "Plan milestone 4 for the multiplayer lobby." | Plan a milestone |
| 6 | "What's the next slice?" | The loop's own phrase |
| 7 | "Units sometimes walk through walls after loading a save. Fix it." | Game bug fix |
| 8 | "Write the spec for the fog-of-war system before we code it." | Spec entry |
| 9 | "Is milestone 3 ready to exit?" | Exit entry |
| 10 | "slicesmith fix — the inventory duplicates items on drop" | Named subcommand |
| 11 | "Build the turn timer in C# for my Godot project, one small step at a time." | Incremental build, C# Godot |
| 23 | "Add a retry flag to my Python CLI, test-first, one slice at a time." | Plain lens: test-first and slices asked for by name |
| 25 | "Every colony-sim test passes; mutate the new rules and see what survives before milestone 5 exits." | Exit: mutation sample (K4 C7) |
| 27 | "My Python export tool drops the last row. Fix it reproduce-first: a failing test, then one hypothesis at a time." | Plain lens: reproduce-first fix asked for |
| 28 | "Add a --dry-run flag to my TypeScript CLI, test-first, in thin slices." | Plain lens: TypeScript, test-first and slices asked for |
| 29 | "The suite is green and I added two tests. Is this slice done?" | Done gate phrase |
| 32 | "Add a stamina stat to the player in my Godot game. Just write the code; we can test later." | A game stat, even when told to test later (missed 2 of 3 native runs, 2026-10-16 and 10-17) |

## Should not fire

| # | Query | Route | Why |
|---|---|---|---|
| 12 | "GUT says green but did every test file actually parse?" | godotsmith | Whether a run can be believed |
| 13 | "Rule on whether the M4 gate can close." | godotsmith | Gate ruling |
| 14 | "This hut vanishes against the grass when zoomed out." | pixelsmith | Art reads |
| 15 | "What LUFS should my SFX hit?" | soundsmith | Audio level |
| 16 | "Grill me on the autosave feature before we build it." | grillwright | Interview first, named |
| 17 | "Split this milestone across six agents and run them in parallel." | dispatchwright | Fan-out |
| 18 | "Review this scene for signal direction and node ownership." | godotsmith | Convention review |
| 19 | "Write a prompt for an NPC dialogue generator." | promptwright | A prompt |
| 20 | "Implement OAuth login in my Express API — no tests, just ship it." | none | Not a game, and asks for neither test-first nor slices |
| 21 | "Design a fun crafting mechanic for my game." | none | Designing the mechanic is the user's |
| 22 | "Write the handoff so I can pick this up tomorrow." | handoffwright | A pause |
| 24 | "Review this Python PR for bugs." | code review | Review, not the build loop |
| 26 | "CI printed a mutation score of 81% — can the M5 gate rest on that figure?" | godotsmith | Ruling on a gate figure, not running the loop |
| 30 | "Map this unfamiliar TypeScript repo: entry points, main flows, where I'd change the retry logic." | researchscribe | A repo map, no code written |
| 31 | "My Python export tool drops the last row — just patch it, no tests." | none | Not a game, and asks for neither test-first nor a reproduce-first fix |

## Edge notes

Sharpest pairs: #2 vs #16 (build versus a named interview first); #9 vs #13 (bringing exit
evidence versus ruling the gate); #11 vs #17 (one loop versus a fan-out); #3 vs #12 (writing
the test versus believing the run); #25 vs #26 (running the mutation sample versus ruling on
its figure); #27 vs #31 (a reproduce-first fix asked for versus a bare patch); #28 vs #30
(building in a repo test-first versus mapping it). Misses on the yes-set: make the triggers pushier. Fires on
the no-set: tighten the boundary sentence.
