# revenantworks-gamedev-pixelsmith

Art direction for pixel art that one camera must read at several zoom scales — people at near, formations and clusters at mid, territories at far — with every asset drawn once. What separates it from sprite generators and single-scale pixel-art guides: it does not draw, and it does not stop at one scale. It writes the per-band rules (value ladder, silhouette vocabulary, icon vocabulary), computes terrain-versus-unit contrast as a number, runs a repeatable one-scene look test with a scorecard, and briefs an artist or a generator toward that pass line. The first member of the `gamedev` pack.

**Workflow:** Band model → Rules per band → Look test → Findings → Brief or audit

## Package contents

```
revenantworks-gamedev-pixelsmith/
├── SKILL.md                  # band model, five laws, four entries, restraint, turn shape
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── band-rules.md         # value ladder; near/mid/far rules and "reads" checklists
│   ├── look-test.md          # procedure, image and text paths, scorecard, pass line
│   ├── contrast.md           # the value-gap method, fix ladder, and the case log (Case 1: the hut)
│   ├── briefing.md           # artist brief and generator prompt templates
│   └── pack.md               # gamedev-pack advisory manifest (generated from the registry)
└── evals/                    # in full folder-zips, excluded from .skill
    ├── trigger-evals.md      # 20 should/shouldn't queries
    └── test-cases.md         # 12 assertion cases
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your skills directory, install the `gamedev` pack from the marketplace, or upload the archive in Claude settings. Profile `standard`: image viewing is optional and declared; with no image tool the look test runs its text-described path in full.

## Entry points

| Entry | Say | Delivers |
|---|---|---|
| Direct | "rules for art that reads at every zoom", "my huts vanish against forest" | Band model, rules per band, contrast table, the test to run next |
| Test | `pixelsmith test`, "run the look test on this scene" | A scorecard per band with pass/fail per line and findings ordered by cheapest fix |
| Brief | `pixelsmith brief`, "brief the pixel artist", "prompt for the sprite generator" | An artist brief or a one-asset generator prompt, filled from the rule set |
| Audit | `pixelsmith audit`, "score my art bible" | A 1–10 score per law and a findings catalog, no redraw |

## Commands and switches

| Invocation | Effect |
|---|---|
| `pixelsmith` | Bare invocation — states the four entries and asks what to direct |
| `pixelsmith test` | Look test on one scene; image path when the surface can show images, text path otherwise |
| `pixelsmith brief` | Artist brief or generator prompt from the rule set |
| `pixelsmith audit` | Score existing art or an art bible against the laws without rewriting |
| "apply all" / "just write it" | Skips the one gate |

## Boundaries

Drawing or generating the sprite is an art tool's job. Engine rendering, crossfade, aggregation, and LOD code belong to the game's engineering. A brand palette is defined and applied by `revenantworks-foundation-brandwright`; pixelsmith takes it as an input and never requires the sibling.

## Staying current

No volatile file: the laws and the method are durable craft. `references/contrast.md` grows a case-log row when a recorded failure and its confirmed fix are added; rows are never edited. The eval suite re-anchors with every version bump.

## Evals

`evals/trigger-evals.md` (20 queries, 10 should / 10 shouldn't, four near-misses) and `evals/test-cases.md` (12 assertion cases). Art quality is subjective and is not asserted; routing, procedure, count, and the contrast arithmetic are.

History in [CHANGELOG.md](CHANGELOG.md).
