# Changelog — revenantworks-scribe-commscribe

## [1.0.0] — 2026-10-01

First public release. Writes and cleans up messages and docs for their channel and reader, in a
plain human voice with no AI tells, and never moves a fact while doing it. It never sends.

Description cut to about 600 characters, main use case first (2026-10-08).

K8c fix round (2026-10-08): rule 6 states that model invocation stays on (K7-3-11); the
description lists `retell` (K7-3-16); SOURCES.md source ids renumbered C<n> to S<n> (K7-3-17).

### What it does

- Channels: email, texts, Slack or Teams, release notes, social, Discord, YouTube titles, status
  updates, READMEs, memos, long docs in Claude Docs, and UI microcopy (buttons, errors, empty and
  loading states, confirms).
- Humanized default (rules H1–H9): drafts without AI tells; dash removal is a recast, never a comma
  splice.
- Facts never move: every repair is checked claim by claim against seven named fact moves (an
  invented actor, a dropped manner word, a reattached modifier, a promoted noun, merged events, an
  act turned into a state, a deleted agent); any hit rejects the repair.
- Channel contracts with precedence: each channel has a ceiling and required structure; frozen facts
  outrank the ceiling, and the ceiling outranks style rules.
- Named voices side by side, picked per request and never assumed. A voice learns from 3 to 5
  samples or from the diff between a draft and the writer's final edit.
- A score-only audit with a ship-or-revise gate, and pre-publish hygiene.
- A first-run question so the writer knows the no-dash, no-emoji defaults and can switch them.

### Modes

- `draft`, `reshape`, `humanize`, `audit`, `retell`, `formats`, `cadence`, `voice` (`learn`, `diff`), `docs`.
  `retell` gives an explanation that did not land a shorter second try from a new angle.
  A bare `commscribe` answers in three sentences and asks what to write.

### Safety rules

- Never sends. Writes a voice or defaults file only after the writer approves it.
- Claude Docs is a channel: outline first, one update per section, through the connector only.
- A brand's own voice guide is read, never edited. Ships no voice.
- No scripts, no packages, no network of its own; with no file tools everything comes back in chat.

### Integrations

- lmstudiorunner runs offline drafts or bulk rewrites from a commscribe brief, and every item that
  comes back is fact-checked; whisperrunner turns a voice note into a transcript that becomes the
  frozen source. Neither is required.
- Boundaries: a skill package's own files are skillwright's; a brand and its voice guide,
  brandscribe's; a researched write-up with graded sources, researchscribe's; fiction canon,
  lorescribe's.
