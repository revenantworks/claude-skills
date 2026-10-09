# Slice and test — the cycle, the Godot verify ladder, seams

Read on every slice and every `fix`.

## Contents

- The cycle
- The verify ladder
- Seams — test where the game really breaks
- Determinism before red
- Properties and mutants
- What tests cannot see
- Fix — prove it first

## The cycle

1. **Discover the commands.** Read the repo's own build and test commands (README, CI workflow,
   project files). Never assume a default.
2. **Red.** Write one test for the slice's player-visible change. Name it as a sentence
   (`A_peer_that_never_shook_hands_cannot_command`). Run it. It must fail, and fail with the
   message you predicted. A test that passes first time, or fails for another reason, is fixed
   before any production code is written.
3. **Green.** Write the least code that passes. Run the **whole** suite, not the one file.
4. **Wire.** Reach the new code from a path the player uses — an input, a scene, a menu. A
   class created only by its own test is not implemented (S3).
5. **Refactor** only while green, then run the suite again.
6. **Verify** with the ladder below.
7. **Commit** per `verify-and-exit.md`.

Code written before step 2 is deleted, not adapted. More than about 100 lines without a test
run is a red flag: stop and run.

## The verify ladder

Each rung prints a line the slice's plan row names. A rung that cannot run is reported
NOT-RUN with the reason; it is never skipped silently.

| Rung | GDScript + GUT | C# + xUnit | Passes when |
|---|---|---|---|
| 1 Import | `godot --headless --import` | same, when scenes or assets changed | no `ERROR` or `SCRIPT ERROR` line |
| 2 Build | parse check via the import | `dotnet build -warnaserror` | zero errors, zero warnings |
| 3 Suite | `godot --headless -s addons/gut/gut_cmdln.gd -gexit` | `dotnet test --no-build` | script and test counts equal the expected totals, failures 0 |
| 4 Scene smoke | a headless script that loads each changed `.tscn` and checks its nodes and signals resolve | the same, run from `Main` with a proof flag | the proof line prints, e.g. `[M4] OK` |
| 5 Export | at `exit`, or when the slice touches export settings | same | see `verify-and-exit.md` |

State rung 3 as three numbers beside the expected totals, never as "green". A total merely lower
than expected reads exactly like one nobody predicted; godotsmith's L1 is the full rule.

Commands are Godot 4.x and version-bound; the repo's own scripts win where they exist.

**Plain lens** (no `project.godot`): rung 1 is the repo's install or dependency sync, rung 2 its
build, type check and lint with warnings as errors where the stack allows, rung 3 its full test
command with counts beside the expected totals (for example `pytest -q` reports passed, failed
and skipped), rung 4 one end-to-end run of the entry point the slice changed (a CLI command, a
script, an endpoint), and rung 5 is dropped. Read every command from the repo's README, CI
workflow or task runner first; never assume a default.

## Seams — test where the game really breaks

- Agree the seams with the user in the spec before writing tests.
- A stand-in (in-process transport, mocked file system, fake clock) cannot produce the failures
  of the real thing. Once per slice that touches a boundary, test across the real one: raw bytes
  on a real socket, a real file held open, a real scene loaded.
- Assert on intermediate states, not only end states both paths reach anyway.
- Every test must fail when the fix or guard is deleted, and its name must match what it
  asserts. A test asserting `0 == 0`, or named for a check it never makes, is a defect.

## Determinism before red

A test on a deterministic path is only meaningful when the path is deterministic:

- Seed every random generator the state carries; no global RNG on that path.
- Step frames or ticks directly; never wait on wall-clock timers in a test.
- Fixed physics step; sorted keys in anything hashed or saved.
- A replay or golden-state test pins the hash of a known run.

Otherwise a red cannot be told from noise.

## Properties and mutants

An example test checks the case someone thought of. A simulation needs two more kinds.

**Property tests** state a rule that must hold for every input, then feed it many generated
inputs from a seeded generator. Good properties for a sim: conservation (what goes in equals
what is used, stored and lost), bounds (no stock below zero, no population over capacity),
determinism (same seed and inputs give the same state hash), round trip (save then load
changes nothing), and any ordering the design states. On a failure, shrink to the smallest
input that still fails and pin it as an ordinary example test; print the seed so the failure
replays. With no property library (GDScript), a seeded loop of a few hundred generated cases
with the seed in the failure message is the property test. Use a library only if the repo
already depends on one; adding one is Ask-first.

**Mutation tests** check the tests. Change one rule in the code (flip a comparison, move a
boundary by one, drop a line, swap a constant) and run the suite. If it still passes, the
mutant survived: nothing tested that rule. Each survivor is a missing test (write it, red
first) or a rule nothing depends on (a named deletion candidate). Where no tool exists, mutate
by hand, about ten mutants across the rules the milestone added; where the repo's language has
a mutation tool, it may run on the touched files only. Mutate in a scratch worktree, never in
the slice's commit, and record killed / survived beside the exit evidence. The score is
evidence, never a bar to tune.

## What tests cannot see

- `.tscn`, `.tres` and `.import` changes, node paths, exported variables and signal
  connections: covered by rung 4, never by a unit test alone. Do not hand-edit a `.tscn`
  without loading it afterwards.
- Feel, timing and readability: the user's playtest. slicesmith may script an input replay and
  capture the log or a screenshot as evidence for the user; it never claims the feel itself.
- Export-only failures — excluded resources, missing assemblies, a solution format the
  exporter ignores: rung 5.

## Fix — prove it first

1. Write a test that reproduces the bug through the path the player hit. Watch it fail.
2. Find the root cause. After three failed fixes, stop and report what was tried.
3. Fix it. Run the whole suite.
4. Revert the fix once and watch the test fail again; restore the fix.
5. Commit with the reproduction named in the body.
