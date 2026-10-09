# Changelog — revenantworks-foundation-rigwright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): the subagent template's `model:` line names the `fable` alias (audit K7-1-23).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Decides which layer a standing rule belongs in, then builds the config Claude
reads before work, across claude.ai and Claude Code.

### What it does

- A layer table with eleven homes: four on claude.ai (profile preferences, Project instructions,
  knowledge files, project memory) and seven in Claude Code (`CLAUDE.md` or `AGENTS.md`, path-scoped
  `.claude/rules/`, nested `CLAUDE.md`, a skill, an output style, a hook or permission rule, auto
  memory), decided by how often a rule is true and whether the model can be trusted to follow it.
- Place: answers "where should this rule live?" from the table, with no build.
- Build: Project instructions and a knowledge-file plan, `CLAUDE.md`, the `.claude` layout,
  `.mcp.json`, subagents and hook entries, checked against each surface's limits.
- Audit: runs `/init`, `/doctor` and `/doctor prompt-audit` first where they exist, then scores
  placement, budget, enforceability, rot and coverage, and flags prose rules that belong in a hook.
- Slim: cuts what standing config costs with every rule kept — resolves what loads first, applies
  lossless rungs, gates any lossy cut, and states counts with their method and per-turn arithmetic.
- Refresh: re-verifies the dated surface notes; rows are marked published or reported, and reported
  figures are never treated as hard limits.

### Entry points

- `place` (default), `build`, `audit` (reports, never rewrites), `learn` (a session's lessons,
  each placed by the layer table and deduplicated against what loads, as one gated diff per
  file), `slim`, `refresh`.

### Safety rules

- Writes config files only on build, after the gate; without file tools it delivers pasteable
  blocks. Emits neutral. Ships no code.

### Integrations

- Anything unattended is agentwright's; permission rules, hook safety, a config map and an
  installed-item inventory gatewarden's; which identity drives which remote shieldwarden's
  (both re-pointed 2026-10-08, when the warden pack went from six members to four); a skill
  package skillwright's; a block's wording promptwright's. Runtime output cutting is left to
  external tools (caveman, rtk), named as optional.
