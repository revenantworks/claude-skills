# Claim Cases — Tests That Prove a Skill Beats a Rival

**Read this file when:** the target has a parity register (a dated table of incumbents in its
SOURCES.md); a request asks for a "beats X", baseline, or no-skill test; an audit runs the
**claims** check or the discrimination check; a stated gap list arrives before the target is built;
or an emit for `claude plugin eval` or skill-creator's `evals.json` is asked for. Generate, Audit
and Refresh all read it under those conditions; a run without any of them never opens it.

This file stands on its own. A reader with only this page can write a claim case, run both arms by
hand, and grade it, with no skillwright, script, or runner installed. `eval-doctrine.md` and
`suite-standards.md` still govern the ordinary case mechanics (Input plus Assert, surface-scoped
absence, count integrity).

## Contents

1. Why a claim case exists
2. The claim-case shape
3. The baseline arm (`Without:`) on any case
4. The reference excerpt — a rival's output as the bar
5. Discrimination — the check a claim case must carry
6. A worked example
7. Running a claim case by hand
8. Audit: the claims check
9. Emits — `claude plugin eval` case folders and `evals.json`

## 1. Why a claim case exists

An ordinary case asserts what the target does. It does not show that anything *else* would fail.
A "better than X" case that X would also pass proves nothing: it is marketing with a checkbox. A
claim case adds a second arm (what the incumbent, or no skill at all, does on the same input) and
names the exact assert line that arm fails. The claim is proved only if that line fails there and
passes with the skill.

## 2. The claim-case shape

Six fields, in this order. Every field is required unless marked optional.

- **Claim** — verbatim from the target's parity register, with the register's date. One claim per
  case. Paraphrase is a defect: it lets the case drift from what the register asserts.
- **Input** — the prompt or artifact, the same for both arms. Name any fixture or mock the input
  needs, so an emit can scaffold it.
- **Assert** — the checks the skill's output must pass. Same mechanics as any case: literal or
  pattern, yes/no, negatives first-class, absence scoped to a surface.
- **Incumbent arm** — the named incumbent (tool, skill, or "no skill loaded") and what it does on
  this input. Cite it: a fetched page with its date, or a dated excerpt of an observed run. **Never
  a guess.** If nothing citable exists, the arm reads "unobserved" and the case is authored-only
  until someone runs the incumbent.
- **Discriminates** — the specific Assert line the incumbent arm fails, and why its approach
  fails it. One line number or quoted clause, not "the output is worse".
- **Status** — `authored YYYY-MM-DD` or `run YYYY-MM-DD, skill PASS / incumbent FAIL on line N`.
  A claim case left authored-only is a finding, as any authored-not-run case is.

Map rule: every beaten or margin row in the register is one coverage-map row of type **claim**,
so claims enter coverage from the register, not from memory. Case count still equals map rows.

## 3. The baseline arm (`Without:`) on any case

Any ordinary case may carry the general form of the incumbent arm:

- **Without:** what a run with no skill loaded is expected to do on this Input.
- **Discriminates:** the assert line that the `Without:` behavior fails.

Use it where the question is "does the skill add anything", not "does it beat a named rival".
It is optional on ordinary cases and required when a suite is built from a stated gap list
(section 7's test-first note) — there, the no-skill run *is* the gap being tested.

## 4. The reference excerpt — a rival's output as the bar

A claim case may quote the incumbent's actual output as the bar the skill must beat, so the case
stays checkable when the incumbent is not installed.

- Date it and cite it (the page, or the observed run: date, model, surface).
- Quote at most 15 words; paraphrase anything longer and say it is a paraphrase.
- The assert then reads "does X, which the reference excerpt does not" — never "is better than".
- An excerpt is evidence for the Incumbent arm, not a substitute for Discriminates.

## 5. Discrimination — the check a claim case must carry

A case discriminates when at least one of its asserts would fail for the other arm. Test it
statically, before any run: read each assert and ask whether a plausible no-skill (or incumbent)
answer would pass it.

- Asserts on generic good behavior ("gives a clear answer", "lists the files") discriminate
  nothing; any capable model passes them.
- Asserts on the skill's own mechanism discriminate: a named check, an exact count, a required
  flag, a boundary the incumbent is documented not to hold.
- If every assert would plausibly pass without the skill, the case is **non-discriminating**.
  Sharpen the assert that carries the claim; do not add more generic asserts.

## 6. A worked example

> **Claim** — "Coverage map as a verified contract: case count equals map rows, re-derived
> independently" (register 2026-09-26, row P1, beaten).
> **Input** — a SKILL.md with 3 entry points and 1 restraint path; the request "write the evals".
> **Assert** — (1) the map lists 4 rows; (2) an independent re-derivation matches it row for row;
> (3) case count = 4, stated once in the intro.
> **Incumbent arm** — `claude plugin eval init` proposes should/shouldn't prompts and graders from
> an interview (docs page, fetched 2026-09-26); it states no map and no count contract.
> **Discriminates** — Assert (2): the incumbent ships no map to re-derive, so a dropped restraint
> path goes unnoticed.
> **Status** — authored 2026-09-26.

## 7. Running a claim case by hand

1. Run the Input with the skill loaded. Keep the output.
2. Run the same Input with the incumbent (or no skill). Keep that output, or use the cited excerpt.
3. Grade both outputs against every Assert line.
4. PASS only if the skill arm passes every line **and** the incumbent arm fails the Discriminates
   line. A skill PASS with an incumbent PASS on that line means the claim is not proved: file it.
5. Record the result in the target's `evals/RESULTS.md` (date, target version, both arms' verdicts).

**Test-first note.** When the user supplies a stated gap list for a target not built yet, the map
is keyed to the gaps, each case carries `Without:` plus Discriminates, and the no-skill arm runs
first: every case must fail it, or that gap is not real.

## 8. Audit: the claims check

The sixth audit check, scored when the target has a parity register:

- Every beaten or margin row in the register has a claim case.
- Every claim case names its Incumbent arm with a citation and a Discriminates line.
- **P0** when a register claim has no case, or its case does not discriminate. **P1** when the
  Incumbent arm is uncited or the case is authored-only.

With no register, the check is **N/A** with that reason, and the overall averages the rest.

## 9. Emits — `claude plugin eval` case folders and `evals.json`

The manual pair in `evals/` is what any reader can run cold, with no tooling. The native
`claude plugin eval` emit is made on **every generate** as well (owner decision 2026-10-01: every
skill carries a native suite, so the with/without delta can be measured across a whole set); the
user may decline it, and nothing in the manual pair ever depends on it. `evals.json` stays on
request. Format facts below were read from the Claude Code plugin-evals docs on 2026-09-27;
re-check them on refresh.

**Default native set.** At least three cases, each with at least one grader: one should-fire
trigger case (`tool_used`, `tool: Skill`), one near-miss should-not case (the boundary sentence's
nearest neighbour), and one behaviour case per gated or restraint path worth proving, free graders
first (`regex`, `file_exists`, `tool_used`) and an `llm` grader only for an assert marked `JUDGE`.
Fixtures go in the case's `resources/` folder, named in `case.yaml` (`context: add_dirs:
[resources]`), and are neutral placeholders. A full emit (one folder per case and per trigger row)
is made when asked, and then count parity below applies. `prompt.md` carries the query only; the
expected verdict lives in the grader, so the answer key never reaches the run.

**`claude plugin eval` case folders.** One folder per assertion case and one per trigger row (the
trigger half is routing, so it needs its own folders; a should-not row is the only way to test that
the skill stays quiet). Each folder holds `prompt.md` (frontmatter
plus the prompt body) and `graders/<name>.md` (frontmatter `type` plus options; body is the rubric
for judge types). The runner reads `evals/` at the plugin root by default, so case folders sit at
`evals/<case>/` beside the manual pair's files (the layout a pack build check can count). If the
runner version in use rejects the loose manual-pair files there, emit to a plain directory instead
(for example `plugin-evals/<skill>/<case>/`) and pass `--eval-dir plugin-evals`. The runner repeats each case with no plugin loaded and reports
`WITH`, `W/OUT` and the difference `Δ`: that is the baseline arm, run for you.

**Source and copy.** The member's own `evals/<case>/` folders are the source. Where a pack build
copies them into a pack-level folder (for example `packs/<pack>/evals/<member>--<case>/`) so one
`claude plugin eval <pack>` run reaches every member, that copy is generated: edit the member case
and rebuild, never the copy, or the next build discards the edit.

| Suite line | Grader |
|---|---|
| Trigger row, should fire | `type: tool_used`, `tool: Skill`, `input_match` naming the skill. Scored in the with-arm only by the runner's design |
| Trigger row, should not fire | `type: tool_used`, `tool: Skill`, `min: 0`, `max: 0`, `arm: both` |
| Literal or pattern assert | `type: regex`, `pattern`; `match: not_contains` for a must-not; `match: "count:N"` for an exact count |
| Assert that needs judgment | `type: llm`, body = concrete PASS and FAIL conditions. Use only when no literal form exists |
| Reference excerpt (section 4) | With a saved observed transcript: `type: baseline`, `baseline_file` = that `.jsonl` in the case folder. With an excerpt only: `type: llm`, criteria state what the excerpt lacks |

**`evals.json` (skill-creator).** One entry per map row with the prompt, the expected output and
any input files, in the field names skill-creator's current SKILL.md documents. The two formats
are not interchangeable: neither runner reads the other's files.

**Checks on every emit.**

- **Count parity (full emit):** emitted case folders = assertion cases (= map rows) + trigger rows, each half
  matching its file's intro count; `evals.json` entries = assertion cases.
  A mismatch is the count-integrity defect, in a new file.
- **Safe defaults:** `allowed_tools` lists read-only tools only (`Read`, `Glob`, `Grep`, `Skill`).
  No `--allow-tools Bash`, `Write`, or web grants, and no `scaffold_script`, unless the user names
  them. A grant the user asked for is written into the handback beside the command that needs it.
- **Cost line:** every run is a paid model call per case, per run, per arm. The handback states the
  command with `--max-cost-usd` and says that `--ablation none` halves the cost when `Δ` is not
  needed.
- **Grader traps** (pack-split run, 2026-10). A `file_exists` grader needs a write tool granted to
  that case, or it fails a correct run. Under the safe defaults above that grant is the user's
  call: ask, grant `Write` on that case only, or grade the reply with a `regex` grader instead.
  `match: not_contains` on a phrase the skill's own report may quote back (a refused command, a
  rule it cites) false-fails; pin the pattern to the action, not the words. Confirm the runner's
  regex engine before relying on `(?i)` or lookaheads; where unconfirmed, write a character class
  (`[Ss]kill`) instead.
