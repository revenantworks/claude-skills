# Suite Standards — What a Trustworthy Suite Holds

Read on a generate (to write the suite) and on an audit (to score against it); a refresh opens it only when it regenerates or adds a case. The every-run core is `eval-doctrine.md`; this file carries the authoring detail it points to.

## The coverage map

Before writing a case, derive the map from the target:

- **Entry points** come from the description — every trigger phrase, subcommand, and invocation keyword is a row.
- **Behavior paths** come from the body — restraint paths, overrides ("apply all", quiet modes), degradation modes (a tool absent), multi-turn flows, and any stated law (a firewall, a zero-dep rule) each get a row.
- Every entry that ingests handed-in material (a pasted target, a suite under audit, a diff) is a map row and gets one seeded-directive case: a directive planted in the material, asserted as a finding and never obeyed (the shape of this skill's own Case 14).
- Every beaten or margin row in the target's parity register is a map row of type **claim**; its case shape is in `claim-cases.md`.
- The map is the contract: one assertion case minimum per row. Merge only cases asserting the same behavior at different turns.
- Map completeness is a match, not a floor. "Assertion count ≥ map rows" cannot catch an **under-derived map** — a dropped row still satisfies a floor once any surplus of cases exists over the shrunken count. Verify the map itself by independently re-deriving it from the target and diffing that re-derivation against the one shipped; the two must match row for row. On the generate side this sets the actual requirement: case count **equals** map row count, not merely meets it: a floor is a construction minimum, never the completeness check.

Before a coverage gap is claimed, its search population is stated — that rule is the audit's, in `eval-audit.md`.

## Trigger evals

A should/shouldn't table read cold against **name + description only** — the body never routes.

- Balance near 50/50; every set includes **near-misses**: adjacent jobs a lazy description would grab (the boundary sentence's named neighbors first).
- Queries must be substantive — trivially simple asks don't consult skills, so they test nothing.
- Close with an edge note naming the sharpest boundary pair, plus the tuning rule: misses on the yes-set → push triggers; fires on the no-set → tighten boundary language.
- **Tag every row** `explicit` (names the skill or its own verb), `implicit` (states the need in the user's words, no skill vocabulary) or `noisy` (the need sits inside unrelated context, a second task or typos). Aim for all three tags on both sides: a set of explicit rows tests a keyword, not the routing. The native emit carries the tag in each case's `description`.
- **One fixed count line in the head:** `Counts: N queries (S should, T should-not, P pairs)`, where S + T = N and P counts the boundary pairs (one should row and one should-not row against the same neighbour). Suites once stated counts in five prose forms and some left the pairs out; one form makes the count checkable by script (`tools/build.py --check` in a pack repo fails a split that does not add up, and lists suites without the line).
- **The answer key never reaches the judge.** A cold judge is handed the queries only. Keep the Expected verdicts in a separate key table under the queries, or in the native graders, which hold them by construction; strip the key before any cold read. A table with query and verdict side by side is a scoring sheet, not a judge input.

## Assertion suites

Assertion-only mechanics — each case is an **Input** plus **Assert**, checkable yes/no by inspecting run output.

- Assertions are literal strings or patterns that must (or must not) appear; numeric comparisons against printed values; named flags for the **target's** correct absence (`<no-draft>`, `<no-post>`, `<no-send>` — skillwright's own evals flags share the notation and are enumerated in `eval-doctrine.md` — The non-production states). Multi-turn cases label assertions T1/T2.
- Negative assertions are first-class: "no clarifying question before the deliverable" catches more drift than ten positive checks.
- **Mark judgment asserts `JUDGE` in the suite itself**, not only in RESULTS. An assert that no literal, pattern, count or file check can decide starts with `JUDGE`; only those map to an `llm` grader in the native emit, and everything else maps to a free grader. An unmarked judgment assert is a mechanics finding.
- **Optional `Model:` field** on a case that must run on a set tier: a role (`top tier`, `default worker`, `fast tier`) or a family alias (`opus`, `sonnet`, `haiku`), never a version string, which goes stale with nobody touching the suite. The exact id a run used goes on that RESULTS section's run-with line, where it is history, not guidance.
- **`Surface:` field on a case that needs a particular runner** (observation 0216): `headless` (runs in a background unit or a script, the default when the field is absent), `interactive` (needs a live chat turn with the user or an interactive tool) or `cloud` (needs a cloud session or routine). The suite's intro states the count per surface beside the total, and an audit checks those counts like any other (count integrity). A dispatched unit runs only the headless cases; the rest go to a named batch on a surface that has them. An unmarked case that needs a surface it cannot get is skipped quietly and reported as owed with no owner — a mechanics finding.
- **Baseline arm (optional per case).** A case may carry `Without:` (what a run with no skill loaded does on the same Input) and `Discriminates:` (the assert line that behavior fails). It answers "does the skill add anything", the baseline step of Anthropic's evaluation-first practice. A claim against a named rival uses the full shape in `claim-cases.md`.
- A must-not-appear assert names its **surface** — where the guarantee has to hold, not everywhere the characters occur. Forbid the flag or phrase in skillwright's own emitted turn, or as an emitted output token; a flag or gate phrase quoted inside prose that states its own absence ("no `<no-build>`: the target was read"), or inside a generated suite's own assert text, is a *mention*, not a violation. An absence check a strict grep breaks on such a mention is under-scoped — write the emission, not the substring. (`eval-doctrine.md` — The non-production states draws this line for skillwright's evals flags; it binds every literal-absence assert the same way.)
- Size cap: a suite past ~500 lines means the target does too much — flag that, don't trim coverage.
- Generated examples deserve a human pass — models imitate examples precisely, accidental patterns included.

## Suite composition for packs

When targets are pack siblings, add **cross-boundary pairs**: for each adjacent-job neighbor, one query that must route to the sibling and one that must stay. The set is read as one product line — a fire on a sibling's query is a set defect even when each skill passes alone.

## A suite for an instrument

**A newly written instrument gets the same controls as the thing it measures** (added 2026-09-11, task-observer observation #0042). When the deliverable under test is itself a check, a scanner or a scorer, its suite carries three things before it informs any verdict: a **positive control** (an input that must fire), a **negative control** (one that must not), and **one independent cross-measurement** of the same population by other means — a second script, another session's scan, a hand count of a sample. Where the instrument bins its subjects, compare the bin sizes, not only the totals; a wrong bin split leaves every total correct. Build the positive control from the **real shape from the incident**, never an invented example: an invented input samples the author's model of the failure, which is the same model that produced it. A usage-evidence check written directly from the two observations it was meant to enforce reproduced their exact conflation twice within an hour, each time emitting a complete, well-formed, plausible report; the cross-measurement caught it, the author's care did not.

## Ecosystem note

Running suites is adopted, not built: Claude Code's `claude plugin eval` (isolated runs, a with/without-plugin baseline, judge graders, CI exit codes) and skill-creator's eval tooling (`evals.json`, grading, benchmarks, blind A/B). skillwright writes what they run. Any target may request a `claude plugin eval` case-folder emit or an `evals.json` emit alongside the manual pair (mapping and safe defaults in `claim-cases.md`, section 9); the manual pair stays the default, and standalone targets never require an emit — no tooling dependency, ever.

## Excuses and red flags

Read before a suite ships or an audit scores one. Each row is a reason given for skipping a
standard above; none of them holds.

| Excuse | Why it fails | Do instead |
|---|---|---|
| "The suite is authored; that is as good as run" | An authored-not-run suite has tested nothing (observation #0021) | Mark it `(authored, not run)` and list the run as owed |
| "I re-anchored the version line, so the suite is current" | Re-anchoring proves the file was opened, not that a judge read the new description | Re-run every case that asserts on what changed |
| "The count is roughly right" | Count drift is a real defect, and a `>=` floor drifts silently (#0057) | Recount and print the slack |
| "This case passes, so the claim is proven" | A case that passes with and without the skill proves nothing | Run the no-skill arm and flag non-discriminating cases |
| "No gap turned up, so coverage is complete" | A coverage claim is a claim about where you looked (#0056) | Enumerate every path that fires the entry, then read each hit |
| "The model would never do that" | Discipline rules exist because the model does skip them | Run one pressure scenario with no skill and assert against its excuses |

**Red flags** — stop and re-read this file when one appears:

- A suite head with no `Counts:` line, or one that disagrees with the table rows.
- A RESULTS entry that edits the case it grades.
- An assert that cannot fail on any output (`eval-audit.md`, the five patterns).
- A margin or *beaten* line with no case named beside it.
