# revenantworks-gamedev-pixelsmith

Art direction for pixel art that one camera must read at several zoom scales — people at near, formations and clusters at mid, territories at far — with every asset drawn once. What separates it from sprite generators and single-scale pixel-art guides: it does not draw, and it does not stop at one scale. It writes the per-band rules (value ladder, silhouette vocabulary, icon vocabulary), computes terrain-versus-unit contrast as a number, runs a repeatable one-scene look test with a scorecard, and briefs an artist or a generator toward that pass line. The first member of the `gamedev` pack.

**Workflow:** Band model → Rules per band → Look test → Findings → Brief or audit

## Package contents

```
revenantworks-gamedev-pixelsmith/
├── SKILL.md                  # band model, five laws, five entries, restraint, turn shape
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── band-rules.md         # value ladder; near/mid/far rules and "reads" checklists
│   ├── look-test.md          # procedure, image and text paths, scorecard, pass line
│   ├── contrast.md           # the value-gap method, fix ladder, and the case log (Case 1: the hut)
│   ├── briefing.md           # artist brief and generator prompt templates
│   ├── pixel-3d.md           # the `3d` mode: render precondition, billboards, seam test, 3D scorecard
│   └── pack.md               # gamedev-pack advisory manifest (generated from the registry)
├── scripts/
│   ├── pixel_post.py         # run, not read: the diffusion post-process (stdlib only)
│   └── test_pixel_post.py    # the script's tests
└── evals/                    # in full folder-zips, excluded from .skill
    ├── trigger-evals.md      # 26 should/shouldn't queries
    ├── test-cases.md         # 17 assertion cases
    ├── RESULTS.md            # run records
    └── <case>/               # 5 native `claude plugin eval` cases (prompt.md + graders/)
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
| 3D | `pixelsmith 3d`, "my billboard sprites blur in the 3D view" | Pixelated-3D rules (render precondition, billboards, eight directions, light steps), the seam test, and D1–D6 scorecard lines marked PROVISIONAL |

## Commands and switches

| Invocation | Effect |
|---|---|
| `pixelsmith` | Bare invocation — states the five entries and asks what to direct |
| `pixelsmith test` | Look test on one scene; image path when the surface can show images, text path otherwise |
| `pixelsmith brief` | Artist brief or generator prompt from the rule set |
| `pixelsmith audit` | Score existing art or an art bible against the laws without rewriting |
| `pixelsmith 3d` | Rules and scorecard for a band that renders in 3D or 2.5D, pixelated 3D only |
| `python scripts/pixel_post.py <candidate.png> --spec <spec.txt> --factor <n> --out <out.png>` | Runs the diffusion post-process (steps 2-4 and 6 of the contract in `briefing.md`) on one candidate and prints one JSON record |
| `python scripts/pixel_post.py --selftest` | The script checks itself |
| "apply all" / "just write it" | Skips the one gate |

## Boundaries

Drawing or generating the sprite is an art tool's job; on a local diffusion model, `revenantworks-localops-comfyrunner` renders the diffusion brief; the post-process contract is pixelsmith's and runs through `scripts/pixel_post.py`, then the candidates go to the look test. Engine rendering, crossfade, aggregation, and LOD code belong to the game's engineering. A brand palette is defined by `revenantworks-scribe-brandscribe`; pixelsmith takes it as an input and never requires the sibling. In a 3D band, renderer and viewport setup and every count against a bar are `revenantworks-gamedev-godotsmith`'s; pixelsmith states the art rule. General 3D art direction (PBR, modelling, topology, rigging) and image-to-3D generation are out of scope.

## Staying current

One volatile file: `SOURCES.md` (parity registers, 90 days); the laws and the method are durable craft. `references/contrast.md` grows a case-log row when a recorded failure and its confirmed fix are added; rows are never edited. The eval suite re-anchors with every version bump.

## Evals

`evals/trigger-evals.md` (26 queries, 12 should / 14 shouldn't), `evals/test-cases.md` (17 assertion cases), and five native `claude plugin eval` cases in `evals/<case>/`. Run records in `evals/RESULTS.md`. The script's own tests: `python -m unittest discover -s scripts -p "test_*.py"`. Art quality is subjective and is not asserted; routing, procedure, count, and the contrast arithmetic are.

History in [CHANGELOG.md](CHANGELOG.md).
