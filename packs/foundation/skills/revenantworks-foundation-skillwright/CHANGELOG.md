# Changelog — revenantworks-foundation-skillwright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): pack-registry drops the pointer to a history file that never shipped (git history holds it); SOURCES points at the live prompt-caching page instead of copying per-model rates and floors (audit K7-1-07, -08).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Builds, audits, ports and integrates Agent Skills, from a one-line intent to a
packaged, install-ready skill or multi-skill pack.

### What it does

- Build: fresh best-practices research and a parity verdict against the two or three strongest
  incumbents, with at least one named margin, an eval case for every "better than" claim, and a
  dated parity register in the skill's own `SOURCES.md`; then one design catalog, one gate, the
  package and a self-audit.
- Builds to a declared policy profile (standalone by default; packs may allow declared tools,
  scripts and sibling skills).
- Every skill is born testable, with trigger evals and an assertion suite in the box.
- Audit: dual scoring (best practices and the declared profile), a parity re-check that can
  recommend retiring the skill, a security pass (injection surface, secrets, undeclared or ungated
  capability, unsafe defaults), a prose pass on the package's own files with every statement frozen
  and diffed, and a currency pass against the live docs.
- Security pass stage 1: an optional third-party skill scanner, vetted with trustwarden first and
  never required; its hits are evidence and skillwright's own audit stays the verdict
  (`references/scanner-stage.md`).
- Pack: whole-pack design from a domain or role, with a capability map, one roster gate and staged
  builds.
- Integrate: propagates a new or changed member across its pack (registry row, capstone roster,
  manifests, packages, upload checklist).
- Port: an identity-scrubbed, renamed, re-verified copy for a new owner, with a port report; the
  source is never modified.
- Upkeep: a pack-wide staleness sweep of every member's dated surfaces, report-only by default.
- Refresh: re-verifies the best-practices baseline (60-day stamp).
- Evals: writes, audits and refreshes the trigger evals and assertion suite of a skill, prompt card
  or agent spec — a coverage map as the contract, count integrity, claim cases, native
  `claude plugin eval` case folders, and suites that run cold with no tooling.
- Slim: cuts what a skill package costs with behavior held constant — a waste taxonomy, a
  lossless/lossy ladder where lossy cuts always gate, a preservation contract, an equivalence
  probe, measured before/after counts, a score-only audit and a set budget sheet.
- Diagnose: why a skill did not fire or a run cost too much, as one cited cause and the owning fix.
- An excuses and red-flags table read at Build step 7, before the scoreline, naming the reasons a
  build skips research, evals, guards or the self-audit.

### Entry points

- `build`, `audit`, `evals`, `slim`, `diagnose`, `refresh`, `upkeep`, `port`, `integrate [member]`,
  `pack [domain]`. "just build
  it" or "apply all" skips the single gate.

### References

- Rubrics (the dated baseline, security S-1..S-4, generator G-1..G-3, policy profiles), build
  templates, description crafting, eval doctrine (core, suite standards, claim cases, eval audit,
  eval refresh), slim doctrine, diagnose, pack design, pack integration, the pack registry,
  release doctrine and upkeep doctrine.

### Safety rules

- Builds spec-clean neutral: no brand or voice is applied.
- Writes only the package it builds, ports or fixes, on approval. Ships no code; packaging may use an
  optional shell and stdlib Python, which skip cleanly when absent.

### Integrations

- Prompts, their slim and their tuning cases are promptwright's; standing config and its slim
  rigwright's; docs prose outside a skill package commscribe's; applying a brand brandscribe's;
  runtime permissions gatewarden's. Runtime and output token cutting is left to external tools
  (caveman, rtk), named as optional. A skill scanner such as getsentry skill-scanner runs first in
  an audit's security pass when installed.
