# Slice and test — the cycle, the verify ladders, seams, the fix method

Read on every slice and every `fix`.

## Contents

- The cycle
- The verify ladder
- Plain lens — TypeScript, Python and any other repo
- Seams — test where the game really breaks
- Determinism before red
- Properties and mutants
- What tests cannot see
- Fix — prove it first

## The cycle

1. **Discover the commands.** Read the repo's own build and test commands, CI workflow first
   (runner discovery, under Plain lens). Never assume a default.
2. **Red.** Write one test for the slice's player-visible change. Name it as a sentence
   (`A_peer_that_never_shook_hands_cannot_command`). Run it. It must fail, and fail with the
   message you predicted. A test that passes first time, or fails for another reason, is fixed
   before any production code is written.
3. **Green.** Write the least code that passes. While iterating, run the **touched scripts**
   (the new test's file and every file whose subject the slice changed), confirmed narrowed by
   their own script count; the **whole** suite runs once at the done gate in
   `verify-and-exit.md`, never skipped (where the repo has a check queue, as the queued final
   check, its counts checked against the stated total). A suite that takes tens of minutes makes every red/green
   loop on the full run a wait, and a narrowing flag that silently runs everything costs the
   same (godotsmith `gut-traps.md`, section 4: GUT's `-gtest` needs `-gconfig=` too).
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
than expected reads exactly like one nobody predicted; godotsmith's L1 is the full rule, and
the done gate in `verify-and-exit.md` applies it to every slice.

Commands are Godot 4.x and version-bound; the repo's own scripts win where they exist.

## Plain lens — TypeScript, Python and any other repo

No `project.godot`: the same cycle and the same laws, with the repo's own commands in the
ladder. TypeScript and Python are the first-class cases; any other stack follows the same rule.

**Runner discovery — never guess a runner.** Before the first red, read the test command from
the repo, in this order: the CI workflow file (for example `.github/workflows/*.yml`), then the
repo's `CLAUDE.md`, then its README and task runner (`package.json` scripts, `pyproject.toml`,
`Makefile`, `tox.ini`, `noxfile.py`). The command CI runs is the command; when two sources
disagree, CI wins and the reply says so. Local verification runs **every step the CI file
runs**, read from that file now, never a remembered subset; a step that cannot run here is
listed NOT-RUN with its reason. When no source names a test command, ask; do not pick
`pytest`, `jest` or `vitest` because the stack usually uses it.

| Rung | TypeScript | Python | Passes when |
|---|---|---|---|
| 1 Install | the lockfile install CI runs | the environment sync CI runs | no error |
| 2 Build | the type check (`tsc --noEmit` or the repo's script) and the lint step CI runs | the type check and lint CI runs, if any | zero errors; warnings as errors where CI sets it |
| 3 Suite | the CI test step, whole suite | the CI test step, whole suite | counts equal the expected totals, failures 0 (`verify-and-exit.md`, the done gate) |
| 4 Entry smoke | one run of the entry point the slice changed: a CLI command, a script, an endpoint, a hook | same | the proof line prints |
| 5 Export | dropped; the package build only when the slice touches packaging | same | the built artifact holds the changed module |

Run the suite at least once in the configuration the code ships with: no environment variable
or flag that forces a stricter mode than a fresh install gets. A suite pinned to one mode never
tests the default a user actually runs.

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

The same method in either lens, in any repo. A fix built on a guess is not a fix.

1. **Reproduce.** Find the smallest steps that show the bug and run them. Record what was
   expected and what happened. If it will not reproduce, stop and report what was tried; never
   fix a bug nobody has seen. An evidence row from a recorded playtest (obsrunner `playtest`:
   video time, frames, play-log lines, seg/tick and the save) is the starting reproduction: load
   its save, step to its tick, and confirm the symptom before step 2.
2. **Failing test.** Write a test that reproduces it through the path the player or user hit.
   Run it and watch it fail with the bug's own symptom.
3. **List hypotheses.** Before touching code, write each candidate cause with the evidence for
   it and the one probe that would refute it. Most likely first.
4. **One at a time, bounded probe.** Test one hypothesis per probe: a log line, an assert, a
   breakpoint, one bisect step, a smaller input. State the probe's bound before running it (one
   command, or one edit and one run). Change one thing at a time. Probes live in a scratch copy
   or come out before the commit. A hypothesis fails when its probe refutes it, or when a fix
   built on it leaves the test red.
5. **Stop after the second failed hypothesis.** Do not probe further. Write up the evidence:
   the reproduction, the failing test, each hypothesis with its probe and result, what is now
   ruled out, and the next hypothesis with what testing it would need. Ask the user before a
   third. This holds when the user has already said keep going: write the evidence up first,
   then take the third probe only on a fresh yes given after the write-up.
6. **Fix** the confirmed cause with the least change. Run the whole suite through the done gate
   (where the repo has a check queue, queue it; the verdict's counts are checked against the stated
   total, and the row stays `checking` until then).
7. **Revert** the fix once and watch the test fail again; restore the fix.
8. **Commit** with the reproduction and the cause named in the body.
