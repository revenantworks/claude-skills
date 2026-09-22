# Changelog — revenantworks-foundation-evalwright

## [1.1.4] — 2026-09-22

Doctrine only; the `description` is byte-identical, and no entry point, gate, or count moved.
Content applied from the task-observer review of 2026-09-20, citing observation #0061. It was
patch-bumped at install on 2026-09-22 (`release.py` bumps only the pack).

- **A clean control is a claim about the control, exactly as an empty result is (#0061).**
  `references/eval-doctrine.md`, Audit scoring, beside the empty-and-large-result rule: a control
  that comes back clean refutes nothing until someone answers whether it could have fired at all.
  Two cases by name — where a probe sits is part of what it tests, so a control appended at the
  end of an artefact exercises the end-of-input path and is not the same probe as the identical
  text mid-file; and where the instrument is importable, instrument it rather than write the next
  control. Measured: fourteen appended controls, every one structurally incapable of reproducing
  the defect and every clean result read as refutation, against one instrumented run that returned
  the root cause and its offsets.

## [1.1.3] — 2026-09-13

Doctrine only; the `description` is byte-identical, and no entry point, gate, or count moved.
Content applied from the task-observer weekly review of 2026-09-13 (autonomous mode), citing
observations #0056, #0057, #0060. Two bullets land in the SKILL body's Anti-patterns; the worked
detail sits in `references/eval-doctrine.md`.

- **A coverage claim states the population it searched (#0056).** `eval-doctrine.md`'s coverage
  map section now asks for every path that executes the code — the test directory, a CI job's own
  scripts, smoke and tooling harnesses, example projects — to be enumerated before a gap is
  reported, and makes a name hit a candidate rather than a confirmation until someone reads it and
  sees the right class exercised. Measured: three of four apparent gaps in one pass were covered
  by a headless script under `tools/` wired as a required CI step; an earlier delegated sweep
  produced 90 false positives on loose name matching alone.
- **A floor is not self-maintaining; an exact assertion is (#0057).** Same file, Count integrity:
  a `>=` guard prints its slack on success (`tests=411 floor=404 slack=7`) or bounds it with
  `<= floor + N`, and is re-derived from a baseline run before a suite changes. Measured: a floor
  of 404 against a real baseline of 408, so four tests could have vanished with the guard still
  green. dispatchwright's Reconcile carries the dispatch-time half of the same rule and is
  dispositioned to its own unit.
- **A large result is a claim about the instrument, exactly as an empty one is (#0060).** Same
  file, Audit scoring: group findings by the string actually matched, count the distinct set, and
  read it — 592 role-filtered findings collapsed to 133 distinct strings, every one documentation,
  an API example, or ordinary English. Two cautions ride with it: a completeness percentage is a
  ratio whose denominator the instrument chose, and a matcher that cannot tell describing a threat
  from performing one ranks the most careful writing worst. The rule's primary home, skillwright's
  third-party-adoption paragraph, is another unit's.
- Body re-measured against the foundation 2200-token row after the two Anti-patterns bullets
  (1.1.2 measured ≈1947; the two bullets add ≈130). Both eval files take a provenance re-anchor to
  1.1.3 — no case was added, retired, or had its assertion moved, so nothing is owed a re-run.

> Renamed from `revenant-foundation-evalwright` on 2026-08-07 (pack 2.0.0 — the `revenant` → `revenantworks` marketplace migration). Name-only change: directory, frontmatter `name:`, and every cross-reference moved; the version history below is continuous across the rename.

## [1.1.2] — 2026-09-11

Reference only; the `description` is byte-identical. Content applied from the task-observer
weekly review staged 2026-09-11, citing observations #0021, #0025, #0042.
`references/eval-doctrine.md` carries the content below. The content landed under unit L1b
while the 2026-08-17 freeze was still in force, so it shipped with no version bump and the
section stayed `[Unreleased]`; the owner lifted the freeze later the same day (2026-09-11,
`CLAUDE.md` and `packs/foundation/CLAUDE.md`), and this entry converts the section to a dated
release and bumps `frontmatter.metadata.version` `1.1.1` → `1.1.2` under unit P1d.

- **`references/eval-doctrine.md` states the provenance block's LAYOUT as an authoring rule
  (#0025).** One continuous paragraph, or newest re-anchor first, because a freshness gate reads
  a fixed head window; and a provenance-freshness failure has two candidate causes, not one.
- **Same file: a newly written instrument gets the same controls as the thing it measures
  (#0042).** Where the deliverable under test is a check, a scanner or a scorer, its suite
  carries a positive control, a negative control and one independent cross-measurement — with
  the positive control built from the real shape from the incident, never an invented example.
- **Same file: re-anchoring a suite is not running it (#0021, #0025).** "Authored, not run" is a
  finding — it is where a target's documented behaviour and its routing text drift undetected
  across version bumps.

## [1.1.1] — 2026-08-17

Frozen member; one real defect from the 2026-08-17 estate audit + security
scan closed, nothing else touched. Body, description, and `eval-doctrine.md`
are byte-identical to 1.1.0's, so the routing surface did not move.

- **S-1 · P1 (eval half) — no injection probe for any ingesting entry.**
  Turn shape rule 4 binds Generate, Audit, and Refresh — every entry reads
  handed-in material — but the suite carried no case that seeds a directive
  inside a target, a suite under audit, or a refresh diff and asserts it is
  reported, not obeyed. The 1.1.0 re-anchor line even named "any case
  asserting Generate's injection handling" as owed a re-run; none existed.
  `evals/test-cases.md` **Case 14** adds it as one law exercised at all
  three entries (T1 generate target, T2 audited suite, T3 refresh diff),
  **authored, not run**. Count 13 → 14; the intro count line and both eval
  provenance heads re-anchored to 1.1.1; the trigger suite is unchanged at
  20 (10/10) and no RESULTS.md row was added.
- Security scan 2026-08-17: (a) injection posture — the statement is
  file-level (Turn shape rule 4) and binds every entry, Generate citing it;
  (b) no fetch-and-follow, permission widening, secret echo, or guard bypass
  in SKILL.md or the doctrine; (c) no tools, scripts, MCPs, or siblings
  assumed — siblings named with the handoff direction stated, `pack.md`
  advisory; (d) hidden-text scan clean (2026-08-17, parent-run); (e) writes
  only the target's `evals/` pair, gated once, never auto-committed; (f) the
  injection probe now exists (this entry). Frontmatter carries only `name`,
  `description`, `license`, `metadata` — upload-safe. Scoreline after the
  fix: Rubric A 9.3 / standalone pass / C-1 pass · C-2 N/A; body ≈1947
  tokens against the 2200 row. Recorded, not changed (frozen): the standalone
  profile asks for stated degradation where file tools are absent and the
  body implies rather than states it (P2); dimension 11's stated-reason
  path is a pack-level call for every file-writing member.

## [1.1.0] — 2026-08-12

One 2026-08-12 estate-audit finding closed; the description is untouched, so
the routing surface did not move:

- **Injection rule promoted to file level (finding 10).** The
  data-never-instructions sentence was scoped to Entry — Generate's target
  while Entry — Audit reads an existing suite with no equivalent statement.
  It is now Turn shape rule 4, binding every entry, single-homed; the
  Generate entry cites it instead of restating it.

## [1.0.2] — 2026-08-01

A prose pass. Two SKILL.md rules that duplicated `eval-doctrine.md` in full —
the count-drift check and the provenance-line requirement — now name the
failure mode briefly and cross-reference the doctrine file instead of
restating it. A handful of dash-joined clauses in SKILL.md and
`eval-doctrine.md` were re-punctuated for clarity. No rule, gate, count, or
entry point moved, so no eval re-anchor is owed.

## [1.0.1] — 2026-08-01

Frozen-record marker added to the `evals/` files that cite predecessor-era
version numbers. Those designations predate the 2026-07-31 re-baseline, and
two of the tag names were later reused by unrelated releases, so a reader
could take a historical entry for a current one. The rows, verdicts, dates
and counts are untouched — only a header marker was added, so nothing about
what was executed or when has moved.

## [1.0.0] — 2026-07-31

Baseline release. The 1.0 feature set:

- Derives a coverage map from the target — a skill or SKILL.md, a prompt
  card, or an agent spec: entry points from the description, behavior paths
  (restraint, overrides, degradation, multi-turn) from the body.
- Generates two artifacts: the should/shouldn't trigger-eval table with
  near-misses, edge note, and tuning rule, and the assertion suite with
  negative assertions first-class.
- Count integrity: stated case counts must exactly match the actual case
  count and the re-derived coverage-map row count.
- Zero-runtime-dependency law: every generated suite runs cold by hand — no
  tooling, no harness — and the skill's own audits check that first.
- Audit scores 1–10 across five checks — coverage, boundary pairs, assertion
  mechanics, count integrity, self-containment — with a stated N/A rule when
  no trigger set is supplied; refresh is diff-scoped, regenerating only
  touched cases and re-verifying counts.
- Six-state restraint table with explicit flags; no volatile surfaces —
  refresh is event-driven by target change, so pack upkeep sweeps correctly
  skip it.
