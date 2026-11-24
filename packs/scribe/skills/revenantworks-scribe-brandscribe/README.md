# revenantworks-scribe-brandscribe

A brand-definition keeper that turns one written definition into the files Claude and people build on: a Claude Design System for any framework (tokens, brand book, fonts, copied marks, cover, no component code), a `DESIGN.md` and `VOICE.md` for a repo, a voice profile with example pairs, an agent brief and a one-file brand guide. It keeps several brands side by side and picks one per request. It audits drift with a score floor that a leak cannot average away. A UI critique of a built page is uismith's (gamedev pack). It ships with no brand.

Part of the **scribe** pack (standard profile). It adds no line to any other skill: other work picks the brand up from the default Design System, from repo files the user places, or from an export the user pastes.

## What it does that others do not

| Margin | What it means | Eval case |
|---|---|---|
| Definition to Design System, any framework | A brand-only system from a written definition, then re-synced per definition version with a four-list diff (matched, changed, live-only, definition-only) that keeps page edits | `test-cases.md` T3, T4, T13 · native `connect-four-lists`, `dtcg-to-list` |
| Voice inside the system | The brand book's content fundamentals carry the voice profile with before/after pairs and banned tells, so decks and agents that read the system get the voice | `test-cases.md` T6, T16 · native `first-run-pref` |
| Drift audit with a floor | Stale names hunted from History rows; a P0 (a co-occurrence breach or a found credential) caps the overall at 3.0; repeat audits show new, fixed and recurring | `test-cases.md` T5, T9, T10, T11 · native `secret-audit-p0` |
| Safe with handed-in material | Guides, pages and live systems are data; an embedded instruction is reported as `INJECTED`; nothing is written before the gate | `test-cases.md` T1, T2 · native `no-definition-apply`, `injected-guide` |

## Package

```
revenantworks-scribe-brandscribe/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── definition-schema.md · voice-profile.md
│   ├── design-system.md · repo-files.md
│   ├── audit.md · measurement.md
│   └── pack.md
├── scripts/
│   ├── tokens_check.py          # optional, stdlib only
│   └── test_tokens_check.py
└── evals/
    ├── trigger-evals.md · test-cases.md   # hand-run suites
    └── <case>/prompt.md + graders/        # claude plugin eval suite
```

## Install

Claude Code: add the marketplace and install the scribe pack (`/plugin marketplace add revenantworks/claude-skills`, then `/plugin install scribe@revenantworks`). claude.ai: upload the folder as a skill (Customize → Skills).

## Commands

| Say | Does |
|---|---|
| `brandscribe setup` | First-run questions per brand: dash and emoji preference (default: avoid both), where brand files live |
| `brandscribe build` | Ingest a guide, page, PDF or live system, ask only the open groups, write the definition at the gate |
| `brandscribe export design-system` | Build a Claude Design System from the selected brand |
| `brandscribe export design-md` / `voice` / `brief` / `guide-card` / `tokens` / `vale` | DESIGN.md, voice profile or VOICE.md, agent brief, offline HTML guide, DTCG tokens, Vale style |
| `brandscribe sync` | Connect a live system to a definition, or re-sync after a version bump |
| `brandscribe audit` | Seven-category drift report, report only |
| `brandscribe gate` | Pass or fail for one page or artifact |

Name the brand in the request ("for example-brand") when the roster has more than one.

## Script

The script is optional and uses the Python standard library only. They read files and print; they write nothing.

```
python scripts/tokens_check.py contrast "#1a1a1a" "#ffffff"
python scripts/tokens_check.py check project/tokens.json
python scripts/tokens_check.py convert tokens.dtcg.json > tokens.json
python -m unittest discover -s scripts -p "test_*.py"
```

Without Python, Claude computes the same figures with its code tool, or marks them "unmeasured on this surface".

## Optional local tools

comfyrunner (brand imagery from a brief), lmstudiorunner (offline name and tagline batches) and pixelsmith (pixel palettes from brand colours) take briefs brandscribe writes. None is required; without them the brief comes back as text.

## Staying current

`references/design-system.md` holds a dated block for the Design System type (30-day cadence); the live type's own instructions always win. `references/repo-files.md` holds the DESIGN.md format facts (60 days; the format is alpha). `SOURCES.md` is the parity register (90 days).

See CHANGELOG.md for history.
