# Eval Doctrine — What a Trustworthy Suite Looks Like

Load this file on every run. It governs what evalwright generates and what its audits score against. The doctrine extends the pack's `eval-authoring.md` baseline (skillwright); where the two differ, this file governs evalwright runs.

## The coverage map

Before writing a case, derive the map from the target:

- **Entry points** come from the description — every trigger phrase, subcommand, and invocation keyword is a row.
- **Behavior paths** come from the body — restraint paths, overrides ("apply all", quiet modes), degradation modes (a tool absent), multi-turn flows, and any stated law (a firewall, a zero-dep rule) each get a row.
- The map is the contract: one assertion case minimum per row. Merge only cases asserting the same behavior at different turns.
- Map completeness is a match, not a floor. "Assertion count ≥ map rows" cannot catch an **under-derived map** — a dropped row still satisfies a floor once any surplus of cases exists over the shrunken count. Verify the map itself by independently re-deriving it from the target and diffing that re-derivation against the one shipped; the two must match row for row. On the generate side this sets the actual requirement: case count **equals** map row count, not merely meets it: a floor is a construction minimum, never the completeness check.

**State the search population before you claim a gap** (added 2026-09-13, task-observer observation #0056). A coverage finding is a claim about a search, and it is exactly as good as the population that search ran over. Before scoring coverage or reporting an uncovered path, enumerate every place the behaviour is actually driven — the test directory, any CI job's own scripts, smoke or tooling harnesses, example projects — and search all of them; scoping to the directory named `tests` encodes the assumption that testing happens only there, which one line of CI config can falsify. Measured: three of four apparent gaps in one pass were covered by a headless script under `tools/` wired as a required CI step. The matching half binds as hard: **a name hit is a candidate, not a confirmation** until someone reads it and sees the right class exercised — a bare identifier matches the same name on unrelated classes (`_process` hit seven times on a different class in that pass; an earlier delegated sweep produced 90 false positives almost entirely this way). State the population beside the finding, so a later reader can tell a real gap from a narrow search.


## Trigger evals

A should/shouldn't table read cold against **name + description only** — the body never routes.

- Balance near 50/50; every set includes **near-misses**: adjacent jobs a lazy description would grab (the boundary sentence's named neighbors first).
- Queries must be substantive — trivially simple asks don't consult skills, so they test nothing.
- Close with an edge note naming the sharpest boundary pair, plus the tuning rule: misses on the yes-set → push triggers; fires on the no-set → tighten boundary language.

## Assertion suites

Assertion-only mechanics — each case is an **Input** plus **Assert**, checkable yes/no by inspecting run output.

- Assertions are literal strings or patterns that must (or must not) appear; numeric comparisons against printed values; named flags for the **target's** correct absence (`<no-draft>`, `<no-post>`, `<no-send>` — evalwright's own output flags share the notation and are enumerated in the SKILL body's non-production states). Multi-turn cases label assertions T1/T2.
- Negative assertions are first-class: "no clarifying question before the deliverable" catches more drift than ten positive checks.
- A must-not-appear assert names its **surface** — where the guarantee has to hold, not everywhere the characters occur. Forbid the flag or phrase in evalwright's own emitted turn, or as an emitted output token; a flag or gate phrase quoted inside prose that states its own absence ("no `<no-build>`: the target was read"), or inside a generated suite's own assert text, is a *mention*, not a violation. An absence check a strict grep breaks on such a mention is under-scoped — write the emission, not the substring. (SKILL Restraint draws this line for evalwright's flags; it binds every literal-absence assert the same way.)
- Size cap: a suite past ~500 lines means the target does too much — flag that, don't trim coverage.
- Generated examples deserve a human pass — models imitate examples precisely, accidental patterns included.

## Count integrity

An intro that says 18 over 22 cases is a real defect (this pack shipped one; the check exists because of it). Audits verify by counting, never by trusting the intro. The rule binds **every** number an audit states about its target, not only the intro/Contents/case-count triple — a scoreline or catalog clause such as "`<no-deploy>` appears 8 times" is itself a countable claim about the target and is grepped before it is printed. A number inside a finding's own justification that was never counted is the same defect, at a smaller scale, as an uncounted intro.

**A floor is not self-maintaining; an exact assertion is** (added 2026-09-13, task-observer observation #0057). Where a suite, or the CI step that guards it, asserts a count, an exact assert stays true by construction — the number changes, the guard goes red, someone updates it — while a `>=` floor falls further behind on every addition and never says so, because what it prints on success is "pass", not "pass, with 4 to spare". Measured: a floor of 404 against a real baseline of 408, so four tests could have been deleted, commented out, or silently dropped with the guard still green — the exact failure the exact assert three lines above it was added to catch. The coverage map section calls a floor a construction minimum for the same reason; this is what to do where a floor is nonetheless the right shape, because the number legitimately moves on almost every commit and an exact assert there trains everyone to edit the number without reading it. Give the floor one of the two things it lacks: **print the slack** on success (`tests=411 floor=404 slack=7`), or **bound it** — assert `>= floor` and `<= floor + N` for a small N, so it cannot drift more than N behind before the guard itself demands the update. And before changing a suite, **run it unchanged and record the numbers**: the expectation a guard is rewritten against comes from a baseline run, never from the last time someone wrote a number down. dispatchwright's Reconcile carries the dispatch-time half of the same rule.


## Provenance and refresh

- Every suite opens with one line: target name · target version · derivation date.
- A refresh diffs the target against that line: regenerate touched cases, add rows for new entry points, retire dead rows by name, re-run count integrity, update the provenance line.
- **"Touches" is not limited to the changed entry's own row.** A rename or behavior change also touches any case filed under a *different* entry whose Input or Assert merely **references** the changed name, flag, or vocabulary — not only the case that is that entry. Verbatim is reserved for cases with no reference, direct or incidental, to what changed; a case that survives a rename still quoting the old vocabulary because its row belongs to some other entry is a stale suite the "leave untouched cases verbatim" rule was never meant to protect.

## Suite composition for packs

When targets are pack siblings, add **cross-boundary pairs**: for each adjacent-job neighbor, one query that must route to the sibling and one that must stay. The set is read as one product line — a fire on a sibling's query is a set defect even when each skill passes alone.

## Audit scoring

The five checks, their anchors, and the P0 line live in the SKILL body's Audit entry and bind whether or not this file is open. Overall = average of the checks scored — five, or **four when boundary pairs is N/A** — one decimal. Scoring self-containment means running the suite the way its reader would: a human with the file, no tooling, no evalwright — if any case stalls waiting for something to be installed, that is the finding.

**A large result is a claim about the instrument, exactly as an empty one is** (added 2026-09-13, task-observer observation #0060). Where a count comes from a matcher — a grep sweep, a scanner, a tally of hits across a population — it is a count of *matches*, not of problems, and filtering by *where* a hit sits never settles *what* was matched. Before such a count is reported or scored: **group the surviving findings by the string actually matched, count the distinct set, and read it.** The distinct set is usually one to two orders of magnitude smaller and therefore readable — 690 findings filtered by file role left 592, which collapsed to 133 distinct strings, and reading all 133 showed every one to be documentation, an API example, or ordinary English; validated findings, zero. Two cautions ride with it: a coverage or completeness percentage is a ratio whose denominator is whatever the instrument chose to count, so re-derive it against the scoped population rather than quoting it; and where a matcher cannot tell describing a threat from performing one, the most careful writing scores worst, so a ranking that tracks documentation quality is reporting on its own instrument. This is the population rule in **The coverage map** read from the other end: an empty result and a huge one are the same claim about the same search.


**Boundary pairs N/A rule.** Boundary pairs scores the trigger-eval set; it needs that set as its artifact. Entry — Audit accepts "an existing suite" singular, and an assertion suite alone is a legitimate audit input (Cases 5 and 6 are exactly this). When no trigger-eval half was supplied, boundary pairs is not a check that came back low: it is a check with nothing to score, and scoring it 1 against an artifact the submitter was never asked for drags the overall average down by a full check for a gap that isn't the suite's. Mark it **N/A** on the scoreline with the reason ("no trigger-eval set supplied"), average the remaining four, and let the catalog note that a full score requires the pair if the auditor wants one.

## Provenance discipline

When the target's version bumps, the suite's provenance line updates **in the same commit**: keep the derivation history, append "re-anchored to vX.Y.Z, YYYY-MM-DD". A suite whose head names an older target version with no dated re-anchor is a finding — the exact staleness class this skill audits others for, and the pack's build gate warns on it. Recording a run: a dated `evals/RESULTS.md` section (date · target version · runner · per-row verdicts · pass rate; irreducible-judgment rows tagged `JUDGE`) — a protocol, never an executor.

**Write the provenance history as ONE continuous paragraph** — no hard newlines between versions, or newest re-anchor first (added 2026-09-11, task-observer observation #0025). A freshness gate typically reads a fixed head window (N lines) of each eval file. A history kept as one paragraph is still "line 3" however long it grows; a history authored with one physical line per bump works by coincidence until the newest note's own line number crosses the window, and then the build fails with a message about a missing version on a file that plainly names it. Two consequences: the layout is an authoring rule, not a style preference; and a provenance-freshness failure has **two** candidate causes — the version is genuinely missing, or the line sits past the window — so check the line number before re-anchoring something already anchored. The general form: a validator with a fixed read-window encodes an assumption about layout, not only content, and that assumption stays invisible until a file written in a different but equally valid convention crosses it.

**A newly written instrument gets the same controls as the thing it measures** (added 2026-09-11, task-observer observation #0042). When the deliverable under test is itself a check, a scanner or a scorer, its suite carries three things before it informs any verdict: a **positive control** (an input that must fire), a **negative control** (one that must not), and **one independent cross-measurement** of the same population by other means — a second script, another session's scan, a hand count of a sample. Where the instrument bins its subjects, compare the bin sizes, not only the totals; a wrong bin split leaves every total correct. Build the positive control from the **real shape from the incident**, never an invented example: an invented input samples the author's model of the failure, which is the same model that produced it. A usage-evidence check written directly from the two observations it was meant to enforce reproduced their exact conflation twice within an hour, each time emitting a complete, well-formed, plausible report; the cross-measurement caught it, the author's care did not.

**Re-anchoring a suite is not running it.** Updating the version line proves the file was opened. A suite left "authored, not run" has tested nothing, and it is exactly where a drift between a target's documented behaviour and its routing text survives version bumps undetected — one skill's description omitted a write-op verb its body documented, through two bumps, because no cold judge had ever read the two against each other (#0021). Carry "authored, not run" as a finding, never a footnote.

## Ecosystem note

skill-creator's eval tooling (evals.json, subagent runs, grading, benchmarks, blind A/B — per the Claude Code skills docs) is the adopted automation lane. A standard-profile target may request an `evals.json` emit alongside the manual pair; standalone targets stay manual by design — no tooling dependency, ever.
