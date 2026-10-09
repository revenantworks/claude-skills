# revenantworks-scribe-lorescribe

A story-bible keeper for fiction projects that live beyond one manuscript. One bible feeds prose, game text, art briefs and audio briefs; several repos of one universe share it with version pins; and naming rules both generate names and test them. lorescribe checks new text against canon and proposes changes. The user writes canon.

It also writes **generation briefs** from canon: a story-draft card for a local model (lmstudiorunner), an entity-visual brief for an image workflow (comfyrunner, with pixelsmith for pixel art), and a timeline chart it draws itself as one offline HTML file. What comes back is checked against canon, and nothing generated becomes canon without the user's yes. Every runner is optional: without one, the brief comes back as text.

It also reads a finished **manuscript**: chapters in, a proposed bible out, every fact cited by chapter file and line with a quote a script has re-found in the text, and every place the book contradicts itself listed with both lines. Nothing is written to the bible until the user says yes. On Claude Code, chapter groups can run as parallel subagents. Story paths in games and interactive fiction are canon too: a fact can hold on one branch only, and checks run per path.

Part of the **scribe** pack (standard profile). One declared script, `scripts/manuscript.py` (Python 3 standard library, no network, read-only on chapters), serves manuscript mode; every other mode needs only the surface's own file tools. lmstudiorunner and comfyrunner (localops pack) and pixelsmith (gamedev pack) run its briefs when installed; none is required.

## What it does that others do not

| Margin | What it means | Eval case |
|---|---|---|
| Cross-medium canon | Entity files carry visual tags and a motif line, so an art or audio brief is checked against canon like a chapter is | `test-cases.md` T5 · native `brief-contra` |
| Canon both ways | Briefs go out to local text and image runners with the canon slice and a must-not list; drafts and image records come back through `check`, and new material is a `GEN-CANDIDATE`, never canon by itself | `test-cases.md` T15-T21 · native `brief-story-slice`, `draft-contra-flagged`, `absent-runner-text`, `timeline-chart` |
| Franchise canon across repos | A universe bible above several projects; each project pins a canon version; `PIN-DRIFT` reports what changed since | `test-cases.md` T6 · native `pin-drift` |
| Naming rules as generator and test | Phonology, forbidden clusters, sound folds, near-duplicate test, pronunciation key | `test-cases.md` T4, T7 · native `name-variant` |
| Read-only on handed-in lore | Proposes; never writes into a folder handed over read-only | `test-cases.md` T3 · native `readonly-folder` |
| Grounded manuscript provenance | Every extracted fact carries `<file>:<line>` and a quote the script re-finds; ungrounded rows are dropped | `test-cases.md` T22 · `scripts/test_manuscript.py` |
| Two-sided contradictions | `SELF-CONTRA` cites both lines; the user picks, the loser can stay as rumour or retired | `test-cases.md` T23 · native `ms-self-contra` |
| Incremental re-run | Only changed chapters are re-read; moved quotes re-anchor | `test-cases.md` T25 · `scripts/test_manuscript.py` |
| Branch-conditional canon | Facts per story path, checks per path, `BRANCH-LEAK` | `test-cases.md` T26 · native `branch-leak` |

Where another tool is stronger: promise, clock, route and prop-custody checks from chapter frontmatter. story-skills' deterministic engine does those; lorescribe reads its JSON report as evidence and can propose the per-chapter frontmatter that engine needs. Model recall at different chunk sizes is not yet measured (`references/manuscript-mode.md`).

## Package

```
revenantworks-scribe-lorescribe/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── entity-schema.md · canon-levels.md · check-codes.md
│   ├── names-method.md · franchise-canon.md · story-skills-interop.md
│   ├── generation-briefs.md · timeline-visual.md
│   ├── manuscript-mode.md
│   └── pack.md
├── scripts/
│   ├── manuscript.py        # chunk, ground, collate, rehash, cast, evidence, score
│   └── test_manuscript.py
└── evals/
    ├── trigger-evals.md · test-cases.md   # hand-run suites
    └── <case>/prompt.md + graders/        # claude plugin eval suite
```

## Install

Claude Code: add the marketplace and install the scribe pack (`/plugin marketplace add revenantworks/claude-skills`, then `/plugin install scribe@revenantworks`). claude.ai: upload the folder as a skill (Customize → Skills).

## Commands

| Say | Mode |
|---|---|
| `lorescribe bible` | build or extend entity files and the index |
| `lorescribe manuscript` | extract a proposed bible from chapters, with cited contradictions |
| `lorescribe check` | text or brief in, coded findings out |
| `lorescribe timeline` | dated events, entity state and story branches |
| `lorescribe names` | naming rules, generate, test, pronunciation key |
| `lorescribe brief` | a story-draft, entity-visual or timeline-visual brief from canon; a drawn timeline chart |
| `lorescribe audit` | score the bible itself without rewriting it |

## Staying current

`SOURCES.md` holds the parity register (90-day calendar surface). Re-run the incumbent scan when it ages out; the retire condition is stated there.

History: [CHANGELOG.md](CHANGELOG.md).

Tests for the script: `python -m unittest discover -s scripts -p "test_*.py"` from this folder.
