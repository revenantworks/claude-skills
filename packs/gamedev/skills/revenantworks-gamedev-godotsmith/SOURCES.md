# Sources — revenantworks-gamedev-godotsmith

Every source below was fetched and read on **2026-09-12**, and its state verified live
against the GitHub API rather than taken from a README. Where a fact here ages — a star
count, a last-commit date — it is stamped with that date and should be re-checked rather
than trusted.

**No text is copied from any source.** Practices are restated in this skill's own words.
A practice is a fact about how to work; the expression of it here is original. Attribution
is given so a reader can go to the original and read the fuller treatment.

## Licence note

One source, `thedivergentai/GD-Agentic-Skills`, is **LGPL-3.0** while this skill is MIT.
Nothing was copied from it. Two of its ideas informed the writing — the three-pass split of
code review into judgment, deterministic rule enforcement and mechanical build execution,
and the one-way parent-child state flow rule — and both are stated here in original prose.
Its persona layer (named characters, first-person quotes, a certification ceremony) was
examined and deliberately not taken: it is presentation, not practice.

A second source's licence was **mis-recorded in this run's own brief**.
`gamedev-skills/awesome-gamedev-agent-skills` is Apache-2.0, not LGPL-3.0. Corrected here
because the brief's error is exactly the kind of fact that propagates if nobody writes down
that it was wrong.

## The sets read

| Source | Licence | State at 2026-09-12 | What was taken |
|---|---|---|---|
| [vl4dt/godot-skills](https://github.com/vl4dt/godot-skills) | MIT | 22 skills live, not the 12 this run's brief named; single contributor, 19 commits, last 2026-08-25 | The runtime-versus-static verification layering, autoload state leaking between tests, the cross-platform line-ending rule, lambda signal connections not auto-disconnecting. Its `godot-headless-workflow` is the closest public work to this skill's core, and the boundary is named in `pack.md` |
| [thedivergentai/GD-Agentic-Skills](https://github.com/thedivergentai/gd-agentic-skills) | LGPL-3.0 | 99 skills, 27 genre blueprints, last pushed 2026-09-09 | One-way parent-child state flow; one-minor-step version upgrades; strict progressive disclosure for a large rule library; the review-pass separation. **Confirmed the gap this skill exists for**: its own documentation states it carries no testing conventions, CI guardrails, lint exclusions or build-and-gate workflow |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | Apache-2.0 | 73 skills across ten engines, Godot subset of 15 plus a router | Composition over deep inheritance; single authoritative writer per piece of state; deferred destruction with guards; reference by stable identity rather than tree position; secrets never in shipped data assets; the read-only-versus-writable path split. Its cross-engine agreement on a practice was treated as evidence that the practice is about the problem rather than about Godot |
| [fenixnix/Godot-Skills](https://github.com/fenixnix/Godot-Skills) | MIT | 7 stars, 12 skill files, single push 2026-03-15, no commits since | Little. Largely a restatement of the official Godot documentation, and at least one file ships with no YAML frontmatter, so it cannot trigger. Recorded for completeness |
| [Randroids-Dojo/Godot-Claude-Skills](https://github.com/Randroids-Dojo/Godot-Claude-Skills) | see repo | read 2026-09-12 | Engine-driving test session discipline: follow a scene start with an explicit synchronisation point before asserting |
| [jame581/GodotPrompter](https://github.com/jame581/GodotPrompter) | see repo | read 2026-09-12 | The richest of the four smaller sets. Worker-thread rules and the thread-pool deadlock; validity checks after an await; calling the base implementation first in an engine virtual; dependency wiring by scope and lifetime; state machines sized to the problem; parallel state machines; the re-import-before-typecheck rule |
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
