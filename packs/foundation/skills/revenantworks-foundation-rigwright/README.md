# revenantworks-foundation-rigwright

rigwright decides *which layer a rule belongs in* before anything is written, across claude.ai and
Claude Code. `/init` will write you a CLAUDE.md and `/doctor` will trim one. Neither will tell you
that a rule belongs in your claude.ai profile rather than a Project, that four of your rules are
unenforceable as prose and belong in a hook, or that a status line in your CLAUDE.md should be a
pointer. rigwright runs those natives first and covers what they do not.

The rig is what a session opens with, every time. rigwright places each rule, builds the files,
and scores a setup that has silted up.

## Package

```
revenantworks-foundation-rigwright/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── surface-notes.md        # volatile, 60-day — per-surface fields, caps, load semantics, refresh procedure
│   ├── artifact-templates.md   # emit shapes (Project, CLAUDE.md, .claude, hook entry, subagent, CI) + validation
│   ├── audit-evidence.md       # audit-only: usage evidence, controls, fixtures, rule backtest
│   ├── slim.md                 # slim-only: load graph, ladder, preservation contract, per-turn arithmetic
│   └── pack.md                 # sibling boundaries, read on boundary doubt only
└── evals/
    ├── trigger-evals.md        # 37 routing queries (1–20 judged cold 20/20 before 2026-10-08; the rest owed)
    ├── test-cases.md           # 39 assertion cases
    ├── RESULTS.md              # executed runs, newest last
    └── <case>/                 # 6 native `claude plugin eval` cases (prompt.md + graders/)
```

## Install

**claude.ai** — Settings → Capabilities → Skills, upload the zip.
**Claude Code** — the foundation plugin carries it; or drop the folder in `~/.claude/skills/`.

## Modes

| Invocation | Does |
|---|---|
| `rigwright place` *(default; any bare placement question)* | "Where should this rule live?" — answered from the layer table, no build |
| `rigwright build` | Builds the config from intent — Project instructions, knowledge-file plan, CLAUDE.md, `.claude` layout, `.mcp.json` |
| `rigwright audit` | Runs `/doctor` and `/doctor prompt-audit` first, then scores placement, budget, enforceability, rot, coverage. Reports, never rewrites |
| `rigwright slim` | Cuts what standing config costs with every rule kept: resolves what loads, applies lossless rungs, gates any lossy cut, states the per-turn arithmetic. Runtime output cutting is left to external tools (caveman, rtk), optional |
| `rigwright refresh` | Re-verifies `surface-notes.md` against current docs, restamps that file only |

## The layer table

Eleven homes — four on claude.ai (profile preferences, Project instructions, knowledge files, project memory) and seven in Claude Code (`CLAUDE.md` or `AGENTS.md`, path-scoped `.claude/rules/`, nested `CLAUDE.md`, a skill, an output style, a hook or permission rule, auto memory) — and one question deciding between them: how often is it true, and can the model be trusted to follow it? The table lives in `SKILL.md` and loads with the body.

## Boundaries

Attended config is rigwright's. Anything firing on a schedule or an event with no human reading the result is **agentwright's**, whole. Permission rule content, hook safety, a live/tracked config map and an inventory of installed skills and hooks are **gatewarden's**; which identity may drive which remote is **shieldwarden's** (both in the warden pack). A genuine Agent Skill package is **skillwright's**. Instruction wording, once its home is settled, is **promptwright's**. Trimming standing config for cost, every rule kept, is rigwright's own `slim` mode; a prompt's slim is **promptwright's** and a skill package's **skillwright's**. rigwright emits spec-clean neutral.

## Staying current

`surface-notes.md` carries a 60-day stamp; `SOURCES.md` carries the dated parity register and the retire condition on a 90-day stamp. `rigwright refresh` re-verifies the first; `skillwright upkeep` sweeps both via the `volatile.json` block. Rows are marked `[published]` or `[reported]` — reported figures are guidance and are never validated against as hard limits.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
