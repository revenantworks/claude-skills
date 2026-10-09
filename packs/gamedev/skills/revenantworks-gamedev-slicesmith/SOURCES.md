# Sources — revenantworks-gamedev-slicesmith

Where this skill's guidance comes from, and how to re-check it.

Last verified: 2026-10-08 (the parity register; upkeep reads this stamp, 90-day cadence).

## Lessons from a game build

*Applies to: SKILL.md — The six laws, the excuses table; every reference.*

The laws were drawn from the user's own Godot 4 / C# game, built with Claude Code agents over
nine milestones (a private repository; its build plan, run log, milestone reviews, exit gates and
commit history were read on 2026-10-08). Each lesson below names the law or reference it became.
Lessons godotsmith already carries are routed there rather than restated.

| Lesson | Became |
|---|---|
| Every milestone names a proof obligation someone else can check | S1, spec template |
| Spike the load-bearing unknown before the milestone that needs it; run it for real; re-run when the access pattern changes | S2, Spikes |
| Slice thin, boring boundary first, renderer last | S3, plan order |
| 231 passing tests sat on unwired systems; a class created only by its own test | S3, cycle step 4 |
| The in-process transport hid a remote crash for nine milestones | S4, Seams |
| Exit code zero shipped an export with no code in it | S5, Export gate |
| Warnings as errors, zero-warning builds | Verify ladder rung 2 |
| Commit body states finding, cause and evidence | S6, The commit |
| Append-only run log; overstated claims withdrawn in writing | S6, The run log |
| Exit with the weaker true statement | S6, Exit step 7 |
| Adversarial review by a different model, four-part write-up | Exit step 3 |
| Deletion test before a point-of-no-return milestone | Exit step 4 |
| Name deferrals; track repeat deferrals | Exit step 5 |
| Name the enforcement layer for the riskiest change | Exit step 6 |
| Every subtask gets a tier and a write scope before dispatch | Hand-offs → dispatchwright |
| Tests that fail when the fix is deleted; names match asserts; red first | S4 (godotsmith `gdscript-invariants.md` §3 carries the detail) |
| Never credit an agent's completion claim | Evidence table (godotsmith `gate-doctrine.md` §5) |

## Anthropic guidance

| Claim | Source | Checked |
|---|---|---|
| Give Claude a way to verify its work; explore, plan, implement, commit; skip the plan when the diff fits one sentence | https://code.claude.com/docs/en/best-practices | 2026-10-08 |
| A reviewer in a fresh context; one writes tests, another the code | same page | 2026-10-08 |
| Description third person, what and when; body under 500 lines; feedback loops; evals with a baseline | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | 2026-10-08 |

## Parity register

*Volatile: declared in `volatile.json` (calendar, 90 days); `skillwright upkeep` re-checks it.*

Last verified: 2026-10-08. Ideas were taken as patterns; no code or text was copied.

| Incumbent | URL | Licence | Checked | Capability taken |
|---|---|---|---|---|
| addyosmani/agent-skills — spec-driven-development, planning-and-task-breakdown, incremental-implementation, test-driven-development, debugging-and-error-recovery | https://github.com/addyosmani/agent-skills | MIT | 2026-10-08 | Gated spec with assumptions and Always / Ask-first / Never; tasks with a verify command; checkpoints; never overwrite an unfinished plan; noticed-not-touching; discover the repo's commands; Prove-It for bugs; excuses tables |
| obra/superpowers — brainstorming, writing-plans, test-driven-development, verification-before-completion, finishing-a-development-branch | https://github.com/obra/superpowers | MIT | 2026-10-08 | Weight classes that only ratchet up; `Expected:` lines per step; delete code written before its test; revert the fix to prove the test; banned "should"/"seems"; three integration options and no force-push; deviations ledgered as rulings |
| mattpocock/skills — to-spec, to-tickets, tdd, implement | https://github.com/mattpocock/skills | MIT | 2026-10-08 | Test seams agreed beforehand; tracer-bullet slices sized to one context; one seam, one test per cycle |
| Trail of Bits skills — mutation-testing, property-based-testing, second-opinion | https://github.com/trailofbits/skills | CC-BY-SA-4.0 | 2026-10-08 | Ideas only, no text (share-alike licence): property tests and mutation tests as checks on a suite, and a review by a different model. Restated for a game sim in `slice-and-test.md` (Properties and mutants) and exit steps 2 and 3 (K4 C7) |
| BMad Game Dev Studio — gds-dev-story | https://github.com/bmad-code-org/bmad-module-game-dev-studio | MIT | 2026-10-08 | Halt after three consecutive failures; a Godot GUT knowledge file; a playtest-plan workflow |
| awesome-gamedev-agent-skills — godot-gdscript-headless-testing | https://github.com/gamedev-skills/awesome-gamedev-agent-skills | Apache-2.0 | 2026-10-08 | Import on a fresh checkout; a runner that exits nonzero; the exits-0-with-failures trap |

**Parity table**

| Line | Verdict | Reason | Case |
|---|---|---|---|
| Spec gate with assumptions and boundaries | met | addy, spec-kit, superpowers | C1 |
| Read-only plan with verify commands and expected lines | met | addy, superpowers | C2 |
| Red first; delete code written before its test | met | superpowers, addy | C3 |
| Prove-It fix with revert check | met | superpowers, addy | C5 |
| Halt after three failures | met | BMad GDS | C6 |
| Excuses table and red flags | met | addy, superpowers | C4 |
| Proof obligation per milestone, checked by someone else | **beaten** | No incumbent requires one | C1 |
| Player-reachable slices; a class only its test creates is not implemented | **beaten** | No incumbent tests reachability | C7 |
| Godot verify ladder with counts beside expected totals and a scene smoke-load | **beaten** | Engine pieces exist only as reference files, never as loop gates | C8 |
| Real-seam test and spikes run for real | **beaten** | No incumbent distinguishes a stand-in from the real seam | C9 |
| Export gate beyond exit code | **beaten** | None checks the exported output | C10 |
| Mutation sample and second-opinion review at exit | met | Trail of Bits (ideas) | C14 |
| Feel gate the agent may not close | **beaten** | None separates playtest from tests | C11 |

**Named margins.** (1) The proof obligation — C1. (2) The Godot verify ladder — C8. (3) The feel
gate — C11.

**Iterate.** Add gdUnit4 commands beside GUT when a project in RESULTS uses it. Measure how
often the three-failure halt fires before the user would have stopped. Add a scripted replay
recipe when a Godot replay tool stabilises.

**Retire condition.** Retire slicesmith when a maintained game-dev skill ships a coding loop
with an engine verify ladder, a proof obligation and a feel gate; recommend it and keep
godotsmith as its proof partner.
