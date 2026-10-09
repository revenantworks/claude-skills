# Sources — revenantworks-gamedev-godotsmith

Last verified: 2026-09-26 (the parity register below; upkeep reads this stamp, 90-day cadence).

## Parity register (dated 2026-09-26; 90-day cadence)

The incumbents that do part of this skill's job, and where it stands against each. Every
state figure below is from the GitHub API on 2026-09-26 and ages; re-check it before
claiming a capability no incumbent has.

| Incumbent | Licence / state 2026-09-26 | Covers | Verdict |
|---|---|---|---|
| **H** [haxqer/godot-skill](https://github.com/haxqer/godot-skill) | MIT · 159 stars · pushed 2026-09-23 | Bundled runners for GUT, GdUnit4 and a mini runner, with structured JSON back; counts test scripts because a runner exits 0 when it finds nothing; attributes `SCRIPT ERROR:` lines to a test; a `risky` status for no-assertion tests; a result-sum identity; headless input injection and screenshots | **Adopted as a tool to drive** (Entry — Check step 3, `compatibility`). Its JSON is a summary line, so L1 still applies to it. Its per-runner exit codes informed the `gut-traps.md` marker table |
| **Q** [Qb-Lab/godot-agent-skills](https://github.com/Qb-Lab/godot-agent-skills) (`godot-verify`) | MIT · 0 stars · pushed 2026-09-17 | A verify-before-done stop hook; five verification levels (import, load, parse, test runner, scene runner); the five-pattern error set; the note that Godot can print an error and still exit 0. Its own README says it is not yet eval-tested | Idea source. The five-pattern set and the exit-0 note are in `ci-guards.md` §1(a) with an allow-list. A grep alone does not catch a drop that printed no marker, so the exact script count stays (L1, L3) |
| **G** [thedivergentai/GD-Agentic-Skills](https://github.com/thedivergentai/gd-agentic-skills) | LGPL-3.0 · 758 stars · pushed 2026-09-09 | The breadth leader on engine and convention material | Unchanged from 2026-09-12: no testing, CI-guard or gate doctrine. The first named set for engine reference after the Godot docs (README) |
| [mjasnikovs/godot-gdUnit4](https://github.com/mjasnikovs/godot-gdUnit4) | MIT · 0 stars · pushed 2026-09-26 | Reference GdUnit4 suites with ten named traps; trap 7 is exit 101 (orphans, warnings only) read as a pass | Idea source for `gut-traps.md` D8 and the GdUnit4 row of the marker table |
| [Coding-Solo/godot-mcp](https://github.com/Coding-Solo/godot-mcp) | MIT · 5,843 stars · pushed 2026-04-16 | Launch the editor, run the project, capture debug output, uid management. No test runner | **Adopted as a tool to drive** where present, never rebuilt. Its captured output is still read against the marker set |

**Margin held on 2026-09-26** (no incumbent has it): the three-number reconciliation and the
exact script count as the marker-free witness; the exact-versus-floor asymmetry with printed
slack; the signature-asserting tolerated red; the four gate verdicts with UNMEASURED; gate
figures re-derived from raw counts with their conditions; populations and attribution for
a gate figure; the five build conventions.

**Engine reference is routed, not adopted.** No Godot skill set is bundled here.
The default is the Godot documentation, then **G**.

Injection check, 2026-09-26: of the fetched pages only Q's README addresses an agent reader,
with a benign read-before-installing warning. Recorded, not acted on.

## Build-time scan (2026-09-12)

Every source below was fetched and read on **2026-09-12**, and its state verified live
against the GitHub API rather than taken from a README. Where a fact here ages — a star
count, a last-commit date — it is stamped with that date and should be re-checked rather
than trusted.

**No text is copied from any source.** Practices are restated in this skill's own words.
A practice is a fact about how to work; the expression of it here is original. Attribution
is given so a reader can go to the original and read the fuller treatment.

### Licence note

One source, `thedivergentai/GD-Agentic-Skills`, is **LGPL-3.0** while this skill is Apache-2.0.
Nothing was copied from it. Two of its ideas informed the writing — the three-pass split of
code review into judgment, deterministic rule enforcement and mechanical build execution,
and the one-way parent-child state flow rule — and both are stated here in original prose.
Its persona layer (named characters, first-person quotes, a certification ceremony) was
examined and deliberately not taken: it is presentation, not practice.

A second source's licence was **mis-recorded in this run's own brief**.
`gamedev-skills/awesome-gamedev-agent-skills` is Apache-2.0, not LGPL-3.0. Corrected here
because the brief's error is exactly the kind of fact that propagates if nobody writes down
that it was wrong.

### The sets read

| Source | Licence | State at 2026-09-12 | What was taken |
|---|---|---|---|
| [vl4dt/godot-skills](https://github.com/vl4dt/godot-skills) | MIT | 22 skills live, not the 12 this run's brief named; single contributor, 19 commits, last 2026-08-25 | The runtime-versus-static verification layering, autoload state leaking between tests, the cross-platform line-ending rule, lambda signal connections not auto-disconnecting. Its `godot-headless-workflow` is the closest public work to this skill's core, and the boundary is named in `pack.md` |
| [thedivergentai/GD-Agentic-Skills](https://github.com/thedivergentai/gd-agentic-skills) | LGPL-3.0 | 99 skills, 27 genre blueprints, last pushed 2026-09-09 | One-way parent-child state flow; one-minor-step version upgrades; strict progressive disclosure for a large rule library; the review-pass separation. **Confirmed the gap this skill exists for**: its own documentation states it carries no testing conventions, CI guardrails, lint exclusions or build-and-gate workflow |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | Apache-2.0 | 73 skills across ten engines, Godot subset of 15 plus a router | Composition over deep inheritance; single authoritative writer per piece of state; deferred destruction with guards; reference by stable identity rather than tree position; secrets never in shipped data assets; the read-only-versus-writable path split. Its cross-engine agreement on a practice was treated as evidence that the practice is about the problem rather than about Godot |
| [fenixnix/Godot-Skills](https://github.com/fenixnix/Godot-Skills) | MIT | 7 stars, 12 skill files, single push 2026-03-15, no commits since | Little. Largely a restatement of the official Godot documentation, and at least one file ships with no YAML frontmatter, so it cannot trigger. Recorded for completeness |
| [Randroids-Dojo/Godot-Claude-Skills](https://github.com/Randroids-Dojo/Godot-Claude-Skills) | see repo | read 2026-09-12 | Engine-driving test session discipline: follow a scene start with an explicit synchronisation point before asserting |
| [jame581/GodotPrompter](https://github.com/jame581/GodotPrompter) | MIT | read 2026-09-12; topic list re-read 2026-10-08 | The richest of the four smaller sets. Worker-thread rules and the thread-pool deadlock; validity checks after an await; calling the base implementation first in an engine virtual; dependency wiring by scope and lifetime; state machines sized to the problem; parallel state machines; the re-import-before-typecheck rule. **2026-10-08 (K4 C6):** its topic coverage — save and load, state machines, an event bus, C# signals, the export pipeline — set the topic list for `systems-and-export.md`; the conventions there are written in this skill's own words, as checks, and its API material is left to the Godot docs |
| [fernforestgames/agent-skill-godot](https://github.com/fernforestgames/agent-skill-godot) | MIT | read 2026-09-12 | Deferred node freeing, and never mutating a children collection while iterating it |
| [alexmeckes/godot-claude-skills](https://github.com/alexmeckes/godot-claude-skills) | see repo | audited 2026-09-12, **rejected** | Nothing. Four of its five skills ship with no frontmatter and cannot trigger; content targets 3D and platformers; it funnels to a companion server that runs arbitrary script in-editor. Recorded so the rejection is not re-litigated |

## Originated, not borrowed

The following rest on the engine's own documentation and on one project's defect history
rather than on any published skill. They were checked against the Godot 4.7 docs to confirm
they are not already standard advice.

- **Parse is not run**, and the headless harness owed by any change to a scene file, an
  `@onready`, an exported node reference or a signal wiring.
- **A structural claim is enforced or it is decoration** (C5). A claim in a class doc is
  true the day it is written and unchecked forever after.
- **Banning global randomness with a CI check**, and the canonical save form the state hash
  is taken over.
- **Every clamped or adjustable parameter gets a test that drives it to each limit** and
  asserts the system still works there. This one came from a real defect: a clamp floored at
  a value nobody checked against the geometry it bounded, which blanked the screen ten key
  presses from the default.
- **The exact-versus-floor asymmetry** (L3), from a CI test floor found sitting four behind
  the real count after four separate commits each added a test without touching it.
- **The coverage population** (L2), from a sweep where three of four apparent gaps were
  covered by one required headless script outside the test directory.

## Anthropic's skill guidance

- [Agent Skills best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) — the description field as the routing surface, the body-size guidance, progressive disclosure into references, and the rule that untrusted content is treated as data rather than instructions. Read 2026-09-12.

## Injection check

Every fetched skill file was scanned for text addressing the reading agent rather than
teaching Godot. **None was found** in any of the eight sets. Recorded because an empty
result is a claim about the instrument: the scan covered every markdown file in each set,
and the only agent-directed lines found were ordinary install and progressive-disclosure
documentation.
