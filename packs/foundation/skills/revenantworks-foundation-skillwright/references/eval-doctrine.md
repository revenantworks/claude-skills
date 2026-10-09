# Eval Doctrine — the Core

The one home for eval doctrine (merged 2026-10-08 from skillwright's `eval-authoring.md` and the
retired evalwright's core). Read on every Entry — Evals run and at Build step 6, which always
ships evals. The four files it points to carry the detail.

## Contents

- What every suite holds
- The two artifacts every build ships
- The non-production states
- Where the rest lives

## What every suite holds

- **The map is the contract.** Case count equals map row count: a floor is a construction minimum, never the completeness check.
- **Assertion-only mechanics.** Each case is an **Input** plus **Assert**, decidable yes/no from run output; an assert only a judge can decide starts with `JUDGE`.
- **Count integrity.** Every number stated about a suite is counted, never taken from its intro.
- **Provenance.** Every suite opens with one line: target name · target version · derivation date. A version bump re-anchors it in the same commit, as one continuous paragraph.
- **Authored is not run.** A suite never run is a finding, never a footnote.
- **The zero-runtime-dependency law.** A generated suite is data, not calls: no step in it may require skillwright, a script or a harness to execute. A suite a human cannot run cold by reading it is a defect, and the first thing an eval audit checks.

## The two artifacts every build ships

**Trigger evals (`evals/trigger-evals.md`).** Twenty queries or more: should-fire and should-not rows, read cold against name + description only and compared to the key.

- The should-not set includes both off-topic asks and **near-misses**: adjacent jobs a lazy description would grab (the boundary sentence's targets).
- Close with edge notes naming the sharpest boundary pair and the tuning rule: misses on the yes-set → make triggers pushier; fires on the no-set → tighten the boundary language.
- Queries must be substantive — trivially simple asks don't consult skills at all, so they test nothing.

**Assertion suite (`evals/test-cases.md`).** Each case is an **Input** plus **Assert** — mechanical yes/no checks by inspecting the run output. No expected-behavior prose; failure conditions are negative assertions ("no clarifying question before the deliverable").

- **Coverage rule:** at least one case per entry point and per distinct behavior path (restraint paths, overrides, degradation modes). Merge only cases that assert the same behavior at different turns; keep everything else separate.
- **A case per claim:** every margin and every *beaten* line in the skill's parity register gets a case whose Input the incumbent's approach would fail (`claim-cases.md`; `rubrics.md` — A test per claim). A claim with no case does not ship.
- **Assertion types:** literal string or pattern that must (or must not) appear; numeric comparison against a printed value; a named flag for "correct absence" (e.g. `<no-build>`). Multi-turn cases label assertions T1/T2.
- **Size:** the suite stays under 500 lines; if it can't, the skill is probably doing too much — flag that instead of trimming coverage.
- **Sanity-check flag:** generated examples and assertions deserve a human pass — models imitate examples precisely, including accidental patterns.
- **Executed suites and the no-skill arm:** for a Claude Code or plugin build, also emit `claude plugin eval` case folders (trigger rows graded `tool_used: Skill`) and give every case a `Without:` line (`claim-cases.md` §3 and §9); a standalone chat build keeps the manual form. The member's `evals/` is the source: a pack-level `packs/<pack>/evals/` copy written by the build is generated, so edit the member case and rebuild, never the copy.
- **Variance and cases that prove nothing:** an executed case runs three times and RESULTS records the pass fraction (`3/3`); a case that passes with and without the skill is non-discriminating (`claim-cases.md` §5).
- **Pressure test for a discipline skill:** before writing a skill that enforces a rule the model is tempted to skip, run one pressure scenario with no skill loaded and record the model's exact excuses; each becomes a negative assert the built skill must block (`claim-cases.md` §7).

**When the assertion suite doesn't apply.** Purely subjective-output skills (art direction, voice) skip it with a stated reason in SOURCES or README; trigger evals still apply — routing is never subjective.

## The non-production states

Six states where an Entry — Evals run cannot or should not produce what it was reached for. With the complete `evals/` pair and the audit catalog, they are the whole set of ways an evals run ends. Each **state** has one shape; a flag is not a shape, and one flag can be carried by two states whose shapes differ (`<no-build>` is), so read the row, never the flag. The flag names the deliverable **asked for and withheld**; a state that withholds nothing carries none, and every flag states its reason on its own line. The gate and the handback attach only to output bound for the target's `evals/` folder; a state that ships an ask or an intro ends there. (The same notation appears *inside* generated suites, where it names the **target's** correct absence.)

| State | What still ships | Flag |
|---|---|---|
| **Bare `skillwright evals`** — no target, nothing requested | One line naming generate / audit / refresh, plus one line asking what to point it at | none |
| **Target absent or unreadable** — named but not supplied | Ask for it; never invent a suite, a map or trigger evals from a name | `<no-build>` |
| **The target isn't built yet** | Offer the Build entry, and the suite once the target exists. A user-stated gap list is readable: ship the suite keyed to the gaps, baseline arm required (`claim-cases.md`) | `<no-build>` — none when a gap list was supplied |
| **No routing surface** — no name + description (most prompt cards) | The assertion suite, keyed to the stated output contract; trigger evals skipped | `<no-triggers>` |
| **Subjective output** (art direction, pure voice) | Trigger evals; the assertion suite is skipped | `<no-suite>` |
| **A sound suite under audit** | The scoreline plus an empty or Optional-only catalog | none |

## Where the rest lives

| Rule | File |
|---|---|
| Coverage map, trigger evals, assertion mechanics, pack pairs, controls for an instrument, the ecosystem note | `suite-standards.md` |
| Audit scoring, discrimination, the N/A rule, search population, count integrity and floors, the never-fail lint, matcher counts and clean controls | `eval-audit.md` |
| Provenance and refresh, **Provenance discipline** (the `RESULTS.md` recording format, the one-paragraph history, re-anchoring is not running) | `eval-refresh.md` |
| Claim cases, the baseline arm, native case-folder emits (§9) | `claim-cases.md` |
