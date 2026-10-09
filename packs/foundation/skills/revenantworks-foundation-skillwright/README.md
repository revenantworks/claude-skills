# revenantworks-foundation-skillwright

Builds, audits, and ports Agent Skills — from a one-line intent to a packaged, install-ready skill or multi-skill pack. What separates it from skill scaffolders and creators:

- Every build starts with fresh best-practices research and a **parity verdict**: the skill is built best of breed — matching or beating the two or three strongest incumbents (skills, plugins, MCP servers, prompt libraries, dedicated tools) line by line, adding at least one named margin none of them has, and proposing a better way for each line. Every "better than" claim ships with an eval case the incumbent's approach would fail, and the dated scan lives in the skill's own `SOURCES.md` as a parity register that ages on a 90-day cadence.
- It constructs to a declared **policy profile** rather than one-size rules (standalone by default: self-contained, lean, self-updating — but packs may allow tools, scripts, and sibling skills, all declared).
- It ships every skill **born testable** — trigger evals and an assertion suite in the box — and writes, audits and refreshes suites for skills, prompt cards and agent specs that already exist (`skillwright evals`, folded in from the retired evalwright 2026-10-08).
- It slims a skill package without changing what it does, under a waste taxonomy and a lossless/lossy ladder (`skillwright slim`, from the retired tokenwright), and diagnoses a skill that did not fire or cost too much (`skillwright diagnose`).

It builds **spec-clean neutral**: no brand or voice is applied. It runs zero scripts of its own, so it behaves identically on claude.ai, Claude Code, and the API.

**Build workflow:** Intent → Pack & profile → Research → Parity verdict → Design catalog *(one gate)* → Build → Self-audit → Package

Interaction contract: one complete catalog, one approval gate, no drip-feed iteration.

## Package contents

```
revenantworks-foundation-skillwright/
├── SKILL.md                      # entry point — workflow, entry points, load budget, turn shape
├── README.md                     # this file
├── LICENSE                       # Apache-2.0
├── CHANGELOG.md                  # version history
├── SOURCES.md                    # where the guidance comes from
├── references/                   # runtime — loaded per the SKILL.md load budget
│   ├── rubrics.md                # Rubric A baseline (calendar-volatile, refresh target) + security S-1..S-4 + generator G-1..G-3 + naming-class coverage + policy profiles
│   ├── build-templates.md        # skeletons, naming render, suites & composition, gold standard
│   ├── pack-registry.md          # structural registry (event-driven) — roster, naming template, profiles; build.py derives manifests here
│   ├── description-crafting.md   # trigger writing, boundary sentences, discoverability test
│   ├── pack-design.md            # whole-pack design: capability map, roster catalog, session staging
│   ├── pack-integration.md       # integrate doctrine: registry → roster → manifests → release
│   ├── release-doctrine.md       # release-only: version arithmetic, eval ledger, parity, assets, register
│   ├── upkeep-doctrine.md        # upkeep sweep: cadence math, refresh-verb map, degradation by environment
│   ├── eval-doctrine.md          # the one home for eval doctrine: core rules, the two artifacts, non-production states
│   ├── suite-standards.md        # coverage map, trigger evals, assertion mechanics, pack pairs
│   ├── claim-cases.md            # claim cases, the baseline arm, native case-folder emits
│   ├── eval-audit.md             # scoring a suite, count integrity, the never-fail lint
│   ├── eval-refresh.md           # provenance, diff-scoped refresh, recording runs
│   ├── slim-doctrine.md          # waste taxonomy, lossless/lossy ladder, preservation contract, measuring
│   ├── diagnose.md               # did-not-fire and cost diagnosis: evidence rule, cause → owning fix
│   ├── scanner-stage.md          # the optional, vetted scanner as stage 1 of the security pass
│   ├── mods.md                   # what the optional mods write for this skill
│   └── pack.md                   # foundation-pack advisory manifest (stamped)
└── evals/                        # maintenance / QA assets — in full folder-zips, excluded from .skill
    ├── test-cases.md             # assertion-only regression suite
    ├── trigger-evals.md          # should/shouldn't-trigger queries
    └── RESULTS.md                # execution ledger — baselines per release
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your platform's skills directory, or upload the archive in Claude settings. Trigger it by asking to build, audit, score, or package a skill, or by saying `skillwright` (subcommands: `skillwright evals`, `skillwright slim`, `skillwright diagnose`, `skillwright refresh`, `skillwright integrate`, `skillwright pack`, `skillwright port`, `skillwright upkeep`).

## Entry points

| Entry | What it does |
|---|---|
| **build** | Intent → research → parity verdict (parity table, named margin, iterate proposals, retire condition) → one design catalog + gate → package → self-audit → handback |
| **audit** | Point at any existing skill: dual scoring (best practices + its declared profile), a parity re-check against a fresh incumbent scan (recommending the incumbent and retiring the skill when it has been overtaken), one fix catalog + gate, one consolidated rewrite. Carries the **security pass** — four build-time classes of the skill package itself (injection surface in its instructions, secrets in the artifact, undeclared or ungated capability, unsafe defaults in what it generates), reported as class-tagged rows in the same catalog; what an agent may do at runtime is gatewarden's scan. Carries the **prose pass** — a register-only rewrite of a skill's or pack's own files (SKILL.md, README, CLAUDE.md, reference docs, spec files) with every statement frozen and diffed; text written to an audience through a channel, and docs prose outside a skill package, stay commscribe's. Carries the **currency pass** — models, features and layout scored against the live docs, with any model version outside the skill's one dated reference file filed as a row |
| **evals** | Generate, audit or refresh the trigger evals and assertion suite of a skill, prompt card or agent spec; the suite runs cold with no tooling. Prompt tuning cases stay in promptwright's `optimize` |
| **slim** | Cut what a SKILL.md, its references or a pack costs with behavior held constant: lossless rungs apply, lossy cuts gate, every count names its method; `slim audit` scores only, `slim budget` plans a set. Prompts are promptwright's `slim`, standing config rigwright's; runtime output cutting is served by external tools (caveman, rtk), optional |
| **diagnose** | Why a skill did not fire or a run cost too much: one cause with its citation and the owning fix, nothing applied |
| **refresh** | Re-verifies the best-practices baseline against canonical sources; regenerates only the stamped section |
| **upkeep** | Pack-wide staleness sweep: reads every member's `volatile.json`, reports each calendar surface's status vs cadence (report-only default), runs the mapped refresh verb per overdue surface on approval — degrading by environment |
| **port** | Point at an existing skill set + a target: identity-scrubbed, renamed, re-verified copy with a PORT-REPORT — source never modified |
| **integrate** | Propagate a new or changed member across its pack: registry row, capstone roster line, `pack.md` restamp ×N, packages rebuilt per policy, repo-sync bundle + upload checklist. Offered as "keep going" after every pack build |
| **pack** | Design and build a whole pack from a domain or role: capability map tiered by value, every incumbent-owned job built to parity-plus-margin and runtime infrastructure driven as a tool → one roster gate (trigger-partition table, session plan) → staged builds → set discoverability test → integrate → optional plugin/marketplace prep |

Brand and voice are out of scope: skillwright builds neutral and hands branding to no other skill.

## Commands & switches

Named invocations — everything else routes on natural requests ("build me a skill that…", "audit this SKILL.md"):

| Invocation | What it does |
|---|---|
| `skillwright` | Bare invocation — capability line, then asks what to build or check |
| `skillwright evals [generate\|audit\|refresh]` | Write, score or refresh a suite for an existing skill, prompt card or agent spec |
| `skillwright slim [audit\|budget]` | Slim a skill package, score its waste, or plan a set's budgets |
| `skillwright diagnose` | Find why a skill did not fire, or what made a run cost too much |
| `skillwright refresh` | Re-verify the best-practices baseline in `references/rubrics.md`; patch bump + repackage. Run at the 60-day stamp or when the skill format changes |
| `skillwright upkeep` | Sweep the whole pack for stale calendar surfaces (reads each member's `volatile.json`); report due/overdue, refresh the approved ones per their owning skill's verb, degrade by environment |
| `skillwright port` | Re-issue a skill set for a new owner or purpose — sanitize sweep + rename + stale-ref refresh + PORT-REPORT; the source set is never modified |
| `skillwright integrate [member]` | One-operation pack propagation with all-or-notes integrity and a count check; blast radius per the pack's `restamp: eager \| lazy` policy (default lazy) |
| `skillwright pack [domain]` | Whole-pack design and build: one roster gate, a persisted `<pack>-spec.md` baton, staged multi-session builds above 3 members, plugin prep on request |

| In-request switch | Effect |
|---|---|
| "just build it" / "apply all" | Skips the single approval gate (design catalog or audit findings) |
| "keep going" (at a pack build's continuation offer) | Runs integrate with approval carried over — no second gate |
| A profile name ("standard profile", "standalone") | Overrides the pack's declared profile for that build |
| "pack \<name\>" (+ profile for a new pack) | Targets or registers a pack at build time; members ship a stamped `references/pack.md` |
| "plugin target" / "ship as a plugin" (packs) | Additionally packages the pack as a Claude Code plugin repo (plugin.json + `skills/`, optional `.mcp.json`), marketplace-registerable — `.skill` stays the default |

## Staying current

Two volatile surfaces, declared in `volatile.json`. `references/rubrics.md` is **calendar** (60-day) — **"skillwright refresh"** re-verifies the best-practices baseline against its canonical sources, patch-bumps, and repackages. `references/pack-registry.md` is **event-driven** — restamped only when pack membership or structure changes (via `skillwright integrate`), never on a clock. Everything else is durable doctrine.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
