# Changelog — revenantworks-gamedev-godotsmith

All notable changes to this skill. Format follows Keep a Changelog; versioning is semantic.

## [1.0.1] — 2026-09-22

Task-observer pass, 2026-09-20, from one Godot project's opening, keep-neutral and fog
builds. Observations 0085, 0086, 0087, 0090, 0092. The member was patch-bumped at install on
2026-09-22 (`release.py` bumps only the pack).

### Changed

- **Build proof now names what each tool cannot see (0092).** The headless import runs after
  **every** source change, not only when a file is added: it is the only tool that reports a
  parse or type-inference error — an untyped array literal defeating inference passes lint
  clean and is dropped silently by the suite. `project-hygiene.md` section 1, C1 and Entry —
  Check step 1.
- **"Green" means every step the workflow file runs, and the list is read from the file
  (0087).** A brief or checklist copied from memory drifts the moment CI grows a step; a
  lint step added a week earlier went unrun through three review rounds and two red pushes.
  New `ci-guards.md` section 5, which also records that a push is verified by the remote run
  and that a red step leaves every later step unverified rather than passing (0090). Entry —
  Guard and Entry — Check step 4 carry the short form.
- **A pinned literal read off a float-driven run is a per-platform fact (0090).** Pin it per
  platform keyed by `OS.get_name()`, each row measured on its own platform and a missing row
  failing loudly, or assert the property instead; integer-derived literals and hashes over
  committed bytes are exempt. `determinism-and-state.md` section 3.
- **Work added inside a per-entity per-step loop is the trigger to run the stress harness
  (0085).** A cost that scales with entity count is invisible at fixture size and is the
  whole frame at a realistic one; the trigger is structural, not a hunch, and the review
  reads the loop rather than the tests. `determinism-and-state.md` section 4, renamed, and
  Entry — Review.
- **The red-then-green checkpoint has one named exception (0086).** For a literal only the
  running mechanism can produce, build it, probe the literal under stated conditions, pin it,
  then prove the test can fail by perturbing it once — the positive control taken after the
  fact, with the commit body naming which tests took that path. `gdscript-invariants.md`
  section 3.
- **Per-commit isolation and the dummy renderer's textures (0092).** A multi-task unit proves
  each commit alone before the all-together run, because a later task's code masks an earlier
  task's defect; and under `--headless` a test reads the live `Image` a system holds, never
  `ImageTexture.get_image()` after an `update()`. `gut-traps.md` sections 3 and 4.

## [1.0.0] — 2026-09-12

Born. Second member of the gamedev pack.

### Added

- **Ten laws, body-resident.** Five about proving a build is green — the instrument claim,
  the coverage population, the exact-versus-floor asymmetry, honest red, and who may close a
  gate. Five about how the code gets written — parse is not run, signals up and calls down,
  compose rather than inherit, deterministic code owning its randomness and serialisation,
  and a structural claim being enforced or deleted.
- **Four entry points:** `check`, `guard`, `gate`, `review`.
- **Nine reference files** under progressive disclosure. Four cover proof (`gut-traps`,
  `ci-guards`, `gate-doctrine`, `gdscript-invariants`); four cover conventions
  (`structure-and-wiring`, `lifecycle-and-safety`, `determinism-and-state`,
  `project-hygiene`); one is the pack manifest.
- **Eval suites:** 20 trigger queries (10 should, 10 should not) and 21 assertion cases
  across five groups. Authored, not run — `evals/RESULTS.md` states that in its first line.

### Scope decision

Built narrow on purpose. The market scan found at least eight public Godot skill sets,
including one shipping 22 skills and another 99 plus 27 genre blueprints. All of them are
engine and API pattern material, which the Godot documentation carries better and which
stales at each version bump. The largest set's own documentation confirms it has no coverage
of testing conventions, CI guardrails, lint exclusions or build-and-gate workflow. That gap
is this skill; the engine half is deliberately left to the incumbents, which are named in
`SOURCES.md` rather than competed with.

### Method

Practices were extracted from all eight sets by five parallel readers, each briefed to take
durable conventions and reject API reference, with a sixth unit originating rules none of
them carried. 101 practices extracted, 96 durable, 82 not already covered. The originated
rules rest on the Godot 4.7 documentation and on one project's defect history.

### Corrections made during the build

Recorded because both were errors in this build's own inputs, and an uncorrected input error
propagates.

- The brief recorded `gamedev-skills/awesome-gamedev-agent-skills` as LGPL-3.0. It is
  Apache-2.0. The LGPL-3.0 source is `thedivergentai/GD-Agentic-Skills`, and nothing was
  copied from it.
- The brief recorded `vl4dt/godot-skills` as shipping 12 skills. It ships 22; ten were added
  after the figure this run inherited was written.

### Known thin spot

The `description` field measures 970 characters against a 1024 cap, leaving 54 of headroom.
That is enough to ship and not enough to edit casually. A future addition to the trigger
surface should tighten existing clauses rather than append, or the skill should split. Noted
here rather than discovered later.

[1.0.0]: https://github.com/revenantworks/claude-skills
