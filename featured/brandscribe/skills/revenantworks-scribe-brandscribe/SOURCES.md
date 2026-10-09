# Sources — brandscribe

Last verified: 2026-10-01

Where the guidance comes from, then the dated parity register. Re-check every 90 days, or sooner when the Design System type's release or contract changes.

## Platform facts

| Claim | Source | Checked |
|---|---|---|
| Design System type: `project/` file tree, index written last, list-shaped `tokens.json`, dropping values, upload records, caps, README as the entry point, revise = read live and change only what was asked | Artifact tool, Design System type instructions (release `1790882176-289c`, contract `0.2.47`) | 2026-10-01 |
| Slides and Design use the design system marked default without asking | Artifact tool, type listing text | 2026-10-01 |
| Design systems from codebases, Figma, uploads; Claude Code `/design-sync` is React-based | support.claude.com article 14604397; anthropics/claude-code issues #71523, #75729, #91063, #87797 (via R4, 2026-10-01) | 2026-10-01 |
| DESIGN.md: YAML front matter (`name` required; `colors`, `typography`, `rounded`, `spacing`, `components`), eight ordered sections, `{path}` refs, CLI `lint` / `diff` / `export` (Tailwind, DTCG), status alpha, Apache-2.0 | github.com/google-labs-code/design.md README (raw) and repository metadata (28k stars, pushed 2026-10-01) | 2026-10-01 |
| Vale substitution rule shape (`extends`, `message`, `level`, `ignorecase`, `swap`) | docs.vale.sh/checks/substitution | 2026-10-01 |
| WCAG 2.x relative luminance and contrast floors (4.5:1, 3:1 large text and non-text) | W3C WCAG 2.2 Understanding 1.4.3 and 1.4.11 (formula as published) | 2026-10-01 (formula unchanged since 2.0) |
| CIEDE2000 validation data | Sharma, Wu and Dalal (2005) test data | as published |
| `ui` floor: target size "at least 24 by 24 CSS pixels" with five exceptions (spacing, equivalent, inline, user agent control, essential) | W3C WCAG 2.2 Understanding 2.5.8 | 2026-10-01 |
| `ui` floor: visible keyboard focus; text resizable to 200%; non-text contrast 3:1 | W3C WCAG 2.2, success criteria 2.4.7, 1.4.4, 1.4.11 | 2026-10-01 |
| `ui` review areas grounded in general usability heuristics (visibility of status, error prevention and recovery, consistency, recognition over recall) | Nielsen Norman Group, "10 Usability Heuristics for User Interface Design" | as published |

## Adapted ideas (no code copied)

- Banned-tells classes and before/after pairs as voice teaching: the humanizer and stop-slop skill families and the scribe rebuild's copywriting lessons (run decision 30), restated in neutral terms.
- A brand registry file: cofoundy/brand-skills (MIT) `brands/registry.yaml` idea, here a Markdown roster.
- A voice file the user keeps rather than a dependency: jaimeschwarz/brandvoice (MIT) child-file idea.
- The `ui` mode, `references/ui-floor.md`, `references/ui-review.md` and `scripts/ui_check.py`: ideas harvested from the third-party impeccable skill (Apache-2.0, v4.3.1, read 2026-10-01). Ideas only, restated in our own words and shape; no text or code copied. Taken: check built output once at the end, not per edit; unmeasured instead of failed when the ground is unresolvable; the verify floor; theming browser-default surfaces; generic-UI patterns as questions; the brief wins over taste; scored areas with n/a and a severity tiebreak; judge before reading checker output; a bounded render pass with an evidence check; motion bands; truth in demo data. Dropped: per-edit hooks, a bundled binary, a live page-injection mode, persona and playbook commands. The checker's 31 rules are our own design (the source's detector rules are compiled and unreadable), plus two rig lessons: a missing webfont caught only on built output, and contrast false positives against an unpainted ground.
- The old brandwright skill (same repository, MIT): neutral core, data rule, definition resolution, provenance, rename history, P0 cap, gate mode, Design System three paths, upload fidelity, measurement doctrine sections 1-2.

## Parity register

Incumbents (read 2026-10-01): **B1** the native Design System type · **B2** Claude Design and `/design-sync` · **B4** Brand-System/brandsystem-mcp (MIT, 14 stars) · **B5** google-labs-code/design.md (Apache-2.0) · **B6** cofoundy/brand-skills (MIT, 38 stars).

| Line | vs B1/B2 | vs B4 | vs B6 | Reason | Eval case |
|---|---|---|---|---|---|
| Build a brand from a guide, page or PDF | met | out of scope (headless browser) | met | Ingest first through the surface's fetch and connectors | T2, T7 · `injected-guide` |
| Design System from React code | out of scope | out of scope | out of scope | design-sync owns it; pointer | N2 · `nearmiss-react-design-sync` |
| Brand-only Design System from a definition, any framework | **beaten** | beaten | beaten | design-sync is React-only with no headless path; the type's no-source fallback is a small default system | T3, T4 · `connect-four-lists`, `dtcg-to-list` |
| Voice inside the system | beaten | met | met | Content fundamentals carry the profile with example pairs and banned tells | T6, T16 · `first-run-pref` |
| Re-sync after a brand change, keeping page edits | met | beaten | beaten | Adds the four-list diff and a version stamp | T3, T13 |
| Drift audit across a repo | beaten | met | met | Stale-name hunt from History; P0 cap | T5, T9, T10, T11 · `secret-audit-p0` |
| Several brands with co-occurrence rules | beaten | out of scope | met | Roster, scope selection, one brand per output | T8, T9 |
| Neutral repo brand file (DESIGN.md) | out of scope | met | out of scope | Adopted as an export | T14 · `trigger-design-md` |
| Neutral UI floor on built output (`ui`) | out of scope | out of scope | out of scope | Claude builds pages unaided but skips a measured floor; the static checker plus a scored review with P3 questions is the margin over the harvested skill it replaces | Y15-Y19 · `ui-check-dist`, `ui-taste-p3` |
| Campaigns, strategy, drawn logos | out of scope | out of scope | met | Not this skill's job | N3, N6 · `nearmiss-draw-logo` |

**Named margins.**
1. **Definition to Design System, any framework**, re-synced per definition version with page edits kept (T3, T4, T13).
2. **Voice inside the system**: example pairs and banned tells in the brand book (T6, T16).
3. **Drift audit with a floor**: History-driven stale-name hunt and a P0 cap (T5, T9, T10).
4. **UI floor on built output**: 31 static rules where unresolvable means unmeasured, never failed, and taste stays a P3 question (T17-T19).

**Iterate.** Read a B4 `.brand/` folder as an ingest source when one is present; if DESIGN.md leaves alpha, follow its stable schema and drop the alpha caution; consider a DESIGN.md import path (DESIGN.md → definition) once its CLI's `diff` output is stable.

**Retire condition.** Retire the Design System path if the native type or Claude Design gains all three: build from a written definition with no code, a voice section with a method, and a definition-diff re-sync. Keep audit and voice then.

**Verdict: PARITY + MARGIN.** Biggest risk: the native platform moves fast; margin 1 is the most exposed. Watch the type's release line in `references/design-system.md`.
