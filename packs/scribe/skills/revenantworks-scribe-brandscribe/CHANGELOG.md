# Changelog — revenantworks-scribe-brandscribe

## [1.0.0] — 2026-10-01

First public release. A brand-definition keeper that turns one written definition into the files
Claude and people build on, plus a neutral UI floor for any built page. It ships with no brand.

Description cut to about 600 characters, main use case first (2026-10-08).

K8c fix round (2026-10-08): rule 3 states why model invocation stays on (K7-3-10); the load
budget points at the Modes table instead of repeating it.

### What it does

- Keeps several brand definitions side by side and picks one per request; asks when the roster has
  more than one and none is named.
- Builds a definition from a style guide, website, PDF or live system: asks only the open groups and
  writes nothing before the gate.
- Exports a Claude Design System for any framework (tokens, brand book, fonts, copied marks, cover;
  no component code), a repo `DESIGN.md` and `VOICE.md`, a voice profile with before/after pairs and
  banned tells, an agent brief, an offline one-file HTML brand guide, DTCG tokens and a Vale style.
- Re-syncs a live Design System per definition version with a four-list diff (matched, changed,
  live-only, definition-only) that keeps page edits.
- Audits a repo, docs or artifacts for brand drift in seven categories: stale names hunted from
  History rows, off-palette colours, repeat audits showing new, fixed and recurring findings. A P0
  (a co-occurrence breach or a found credential) caps the overall score at 3.0.
- The neutral UI floor (`ui`): a 31-rule static checker on built HTML/CSS (missing assets and fonts,
  labels, contrast on the painted ground, focus, motion, generic-UI patterns), then a six-area scored
  review with a P0–P3 catalog and a derived verdict.

### Modes

- `setup` (first run per brand: dash and emoji preference, where brand files live), `build`,
  `export` (`design-system`, `design-md`, `voice`, `brief`, `guide-card`, `tokens`, `vale`), `sync`,
  `audit` (report only), `gate` (pass or fail for one page or artifact), `ui`.

### Scripts

- `scripts/tokens_check.py` (optional, stdlib only): contrast ratios, a `tokens.json` check and DTCG
  conversion.
- `scripts/ui_check.py` (optional, stdlib only): the static UI floor; exit 0 clean, 1 findings,
  2 error; `--json` and `--list-rules`.
- Both read files and print; they write nothing. Without Python, Claude's code tool computes the
  same figures or they are reported unmeasured. Tests ship beside each script.

### Safety rules

- Guides, pages and live systems are data; an embedded instruction is reported as `INJECTED`.
- Nothing is written before the gate. An unresolvable ground is unmeasured, never failed; taste
  patterns are P3 questions that never block a ship.
- It adds no line to any other skill: other work picks a brand up from the default Design System,
  from repo files the owner places, or from a pasted export.

### Integrations

- Uses the Artifact tool's Design System type, web fetch and browser tools where present; without
  them every deliverable comes back as files in chat.
- Writes briefs that comfyrunner (brand imagery), lmstudiorunner (offline name and tagline batches)
  and pixelsmith (pixel palettes) can take; none is required. UI copy rows go to commscribe.
- Dated references: Design System type facts (30 days), DESIGN.md format facts (60 days), parity
  register (90 days).
- Also ships as a featured one-skill plugin; install the pack or the featured plugin, not both.
