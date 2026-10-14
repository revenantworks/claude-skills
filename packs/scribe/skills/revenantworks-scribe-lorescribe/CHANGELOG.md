# Changelog — revenantworks-scribe-lorescribe

## [1.0.0] — 2026-10-01

First public release. A story-bible keeper for fiction projects that live beyond one manuscript. It
checks new text against canon and proposes changes; the owner writes canon. It never drafts prose.

Description cut to about 600 characters, main use case first (2026-10-08).

`manuscript.py chunk` refuses an `--out` inside the chapters folder or on the manuscript file, not
only the folder itself, with two tests (K8c, K7-3-18).

### What it does

- One bible (characters, places, factions, canon levels) feeds prose, game text, art briefs and
  audio briefs. Entity files carry visual tags and a motif line, so an art or audio brief is checked
  against canon like a chapter is.
- Checks a chapter, scene, in-game strings, a brief, or generated drafts and images for
  contradictions, dead characters acting, name variants and timeline paradoxes, with coded findings.
- A world timeline with dated events, entity state and story branches, drawn as one offline
  HTML/SVG chart.
- Branch-conditional canon: a fact can hold on one story path only; checks run per path and report
  `BRANCH-LEAK`.
- Franchise canon across repos: a universe bible above several projects, each pinned to a canon
  version; `PIN-DRIFT` reports what changed since.
- Naming rules that both generate and test names: phonology, forbidden clusters, sound folds, a
  near-duplicate test and a pronunciation key.
- Generation briefs from canon: a story-draft card for a local model, an entity-visual brief for an
  image workflow, a timeline-visual brief. New material comes back through `check` as a
  `GEN-CANDIDATE`, never canon by itself.
- Manuscript mode: chapters in, a proposed bible out. Every fact is cited by chapter file and line
  with a quote the script re-finds in the text; ungrounded rows are dropped. `SELF-CONTRA` lists
  both lines of each place the book contradicts itself, and the owner picks. Re-runs read only
  changed chapters and re-anchor moved quotes. On Claude Code, chapter groups can run as parallel
  subagents.
- A score-only audit of the bible itself.

### Modes

- `bible`, `manuscript`, `check`, `timeline`, `names`, `brief`, `audit`.
- A story-draft brief carries a scene shape and canon-checked beats; the return check reports
  beats hit, missed or reordered.

### Scripts

- `scripts/manuscript.py` (Python 3 standard library, no network, read-only on chapters, writes only
  its ledger folder): chunk, ground, collate, rehash, cast, evidence and score. Without Python the
  manuscript loop runs by hand.
- `scripts/test_manuscript.py`: the script's tests.

### Safety rules

- Proposes; never writes into a folder handed over read-only, and nothing reaches the bible without
  the owner's yes. Writes follow a plan → validate → execute loop.
- Brand words are not canon.

### Integrations

- lmstudiorunner and comfyrunner run its briefs, with pixelsmith for pixel art; none is required, and
  without one the brief comes back as text.
- Reads the JSON report of story-skills' deterministic engine as evidence for promise, clock, route
  and prop-custody checks, and can propose the per-chapter frontmatter that engine needs.
- Boundaries: real-world research is researchscribe's, line edits commscribe's, charts of real data
  dataviz's, audio soundsmith's.
