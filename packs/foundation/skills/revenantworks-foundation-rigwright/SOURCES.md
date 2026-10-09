# Sources

Where this skill's guidance comes from, and how to re-check it. Anything time-sensitive lives in `references/surface-notes.md` behind its own stamp — this file records provenance, not current values.

Last verified: 2026-09-26 (the parity register, the last section of this file; upkeep reads this stamp, 90-day cadence).

**Surface rows verified as of 2026-08-17** (`rigwright refresh`; the flat-structure row was carried, not re-verified — see `surface-notes.md`). The `AGENTS.md`, monorepo, symlinked-rules and subagent `effort` rows were re-verified 2026-09-28 against the raw `.md` pages.

## Claude Projects and profile preferences

| Claim | Source | Grade |
|---|---|---|
| Instructions apply to every chat; context not shared between chats unless in knowledge | Claude Help Center — "What are projects", "How can I create and manage projects" | published |
| RAG auto-scales knowledge capacity on paid plans | Claude Help Center — "What are projects" | published |
| Flat structure, no nesting, no cross-project access | Carried from 2026-07-30; not stated in the Help Center articles read 2026-08-17 — consistent secondary sources | **reported** (was published) |
| Organization instructions — Team/Enterprise, 3,000 chars, precede a member's own | Claude Help Center — "Set organization instructions" | published |
| Profile field labeled "Instructions for Claude", account-wide | Claude Help Center — "Understanding Claude's personalization features" | published |
| ~8,000-character instruction budget | Consistent secondary sources; no Anthropic figure | **reported** |
| ~1,500-character profile preference budget | Consistent secondary sources; no Anthropic figure | **reported** |

## CLAUDE.md and the memory hierarchy

| Claim | Source | Grade |
|---|---|---|
| Four-scope hierarchy; higher scopes load first | Claude Code docs — memory | published |
| `@path` imports, relative and absolute, nesting several hops | Claude Code docs — memory | published |
| `CLAUDE.local.md` supported as the gitignored personal file; a home-directory import is the worktree-safe form | Claude Code docs — memory (the 2026-07-30 row read it as deprecated) | published |
| `.claude/rules/` topic files; `paths:` frontmatter scopes a rule to matching files; `~/.claude/rules/` user-level | Claude Code docs — memory | published |
| Project instructions may live at `./.claude/CLAUDE.md`; imports max four hops; external imports in a project file prompt once | Claude Code docs — memory | published |
| Delivered as a user message after the system prompt, no strict-compliance guarantee | Claude Code docs — memory, troubleshooting | published |
| Imports load at launch and do not reduce context cost | Claude Code docs | published |
| `/init` generates a baseline; `/memory` inspects loaded files | Claude Code docs | published |
| Under-200-line target per CLAUDE.md | Claude Code docs — memory ("target under 200 lines") — moved from reported 2026-08-17 | published |
| `AGENTS.md` read natively when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` sits at or above the cwd (v2.1.277+); the "Remove an earlier AGENTS.md workaround" list. Replaces the 2026-08-17 row that said Claude Code does not read `AGENTS.md` | Claude Code docs — memory, sections "AGENTS.md" and "Remove an earlier AGENTS.md workaround" (raw `.md`, 2026-09-28) | published |
| `claudeMdExcludes`; symlinked rules treated as external imports, network paths not followed; Cowork skips out-of-cwd user imports; contradicting rules may be picked arbitrarily | Claude Code docs — memory (raw `.md`, 2026-09-28) | published |
| Subagent frontmatter `effort` overrides the session level | Claude Code docs — sub-agents, "Supported frontmatter fields" (raw `.md`, 2026-09-28) | published |
| The Agent tool call carries a model but no effort, so effort binds only through the definition | Task-observer observation #0179 | **reported** |

## Settings, permissions, and MCP configuration

| Claim | Source | Grade |
|---|---|---|
| Settings merge by scope with a managed layer above all | Claude Code docs — settings | published |
| Permission evaluation order, trust gating, `ask` semantics | moved to gatewarden 2026-10-01 (`rule-grammar.md`); rigwright keeps placement only | — |
| `$schema` line `https://json.schemastore.org/claude-code-settings.json` gives editor validation and can lag new keys | Claude Code docs — settings (read raw 2026-10-01) | published |
| `/doctor` (alias `/checkup`) and `/doctor prompt-audit`: trims, migrations, contradiction and stale-reference audit | Claude Code docs — commands (read 2026-10-01, pack-split research R5) | published |
| Output styles as an always-on home for reply shape | Claude Code docs — features-overview (read 2026-10-01, R5) | published |
| Skill frontmatter: `allowed-tools` is a per-turn grant, `disallowed-tools` exists, six keys accepted by claude.ai uploads | Claude Code docs — skills | published |
| `.claude/settings.local.json` auto-gitignored | Claude Code docs — settings | published |
| MCP servers in `.mcp.json` (project) / `~/.claude.json` (user), not in `settings.json` | Claude Code docs — MCP; settings | published |
| `.mcp.json` at the project root; `${VAR}` / `${VAR:-default}` expansion; project-server approval prompt | Claude Code docs — MCP (open item of 2026-07-30 closed 2026-08-17) | published |

## Auto-memory

| Claim | Source | Grade |
|---|---|---|
| Auto memory at `~/.claude/projects/<project>/memory/`; `MEMORY.md` first 200 lines / 25 KB loaded at start; `/memory` toggles, `autoMemoryEnabled`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Claude Code docs — memory | published |

## Skill-format conformance

Built against the Agent Skills format as documented at platform.claude.com (agents-and-tools/agent-skills, overview and best practices) and the open standard at agentskills.io, re-verified 2026-07-30: frontmatter `name` and `description`, ≤500-line body guidance, progressive disclosure, one-level reference links.

## Parity register (dated 2026-09-26; 90-day cadence)

The incumbents that do this skill's job, what each covers, and the capability rows (the 2026-09-26 parity table, rows 1–16) each one bears on. Re-check before claiming a capability no incumbent has. The 2026-07-30 niche scan (agentskills.io, skills.sh, anthropics/skills, anthropics/claude-plugins-community, VoltAgent/awesome-agent-skills, lobehub, claudeskills.info) is superseded by this register.

| Incumbent | Licence / origin | Covers | Rows |
|---|---|---|---|
| **I1** `claude-md-improver` + `/revise-claude-md` (plugin `claude-md-management`) | Anthropic official plugin | Discovers every `CLAUDE.md`, scores six criteria on 100 points, reports before editing, applies additive diffs after approval; `/revise-claude-md` harvests session learnings into `CLAUDE.md` | 1, 2, 3, 7, 13 (partial) |
| **I2** `ai-sdlc:claude-md-audit` (mll-lab/claude-plugin-marketplace, PR #18, merged 2026-09-23) | MIT — **idea source only**, no text copied | Subtractive audit with three per-claim tests (counterfactual, enforcement, derivability); a derivability cut names its grep; enforcement moves carry working config; runs the claimed commands; RED/GREEN against a fixture repo | 3, 4, 5, 6, 15. The *would it happen anyway* and *can one grep answer it* placement tests and the run-the-commands `rot` rule take the idea from I2 |
| **I3** `claude-automation-recommender` (plugin `claude-code-setup`) | Anthropic official plugin | Read-only; maps codebase signals to recommended MCP servers, skills, hooks, subagents, plugins; emits no config | 1 (partial), 5, 11, 12, 16 |
| `hookify` | Anthropic official plugin | Writes hook rules from a described behaviour or recent corrections | 11 |
| `/init` | First-party Claude Code command | Generates a baseline `CLAUDE.md` from the repo; suggests improvements to an existing one | 2 |

**Re-scored 2026-10-01 (pack-split research R5; owner Q21 kept rigwright, slimmed).** Built-ins now cover the Claude Code half: `/init` builds a repo `CLAUDE.md`, `/doctor` trims and migrates always-loaded guidance into skills and nested files, `/doctor prompt-audit` finds stale references and contradictions, startup warnings check size. Verdict: **GAPS** on the Claude Code build and audit (rigwright runs the natives first and does not redo them); **PARITY + MARGIN** on cross-surface placement.

**Margin held on 2026-10-01** (no incumbent has it): one placement answer across claude.ai and Claude Code (profile preferences, Project instructions, knowledge files and project memory beside the seven Claude Code homes); Project instruction and knowledge-plan emission against published and reported caps; restated status detected as rot and fixed by a pointer; an enforceability backtest of prose rules against session history; a score-only P0/P1/P2 catalog with an owner-install boundary per row; the attended-versus-unattended seam; `[published]`/`[reported]` grading with a scoped Refresh. **Moved out 2026-10-01:** rig inventory and live/tracked pair mapping (filewarden), permission rules, trust and hook safety (gatewarden), multi-identity routing (identitywarden). Re-pointed 2026-10-08 (warden 6 → 4): the inventory and pair mapping are gatewarden's, identity routing shieldwarden's. Out of scope by choice: recommending which MCP servers or plugins to adopt (row 16) is a verdict job, researchscribe's. Re-scanned live 2026-10-01 (unit PR): I1–I3 unchanged; no cross-surface placement tool found.

**Retire condition** (R5): if a native-eval baseline (`evals/` case folders, with and without the skill) shows no measured gain on the placement and Projects cases, or if Anthropic ships a tool that decides placement across claude.ai and Claude Code, rigwright retires and its placement table moves to a skillwright reference. Re-check at each 90-day stamp.

**Adopted 2026-10-08** (owner-approved estate review; idea only, our own words): I1's `/revise-claude-md` session-learnings harvest became Entry — Learn (`references/learn.md`). What rigwright adds: every lesson runs through the layer table (path rule, local file, skill, hook, status file or cut) before it reaches `CLAUDE.md`, duplicates against what already loads are dropped, and contradictions go to the user. The generic CLAUDE.md quality pass stays I1's, recommended by name.

## Re-checking

`rigwright refresh` re-verifies `references/surface-notes.md` against these sources and restamps that file only. Nothing else here is time-sensitive. Where a **reported** figure becomes published, move the row and note the move — never silently promote it.

## Slim (added 2026-10-08)

*Applies to: Entry — Slim and `references/slim.md`.* The ladder, preservation contract, measuring rules and cache-floor rule were moved here, condensed, from the retired tokenwright when each owner took the slim of its own artifacts; the pack's full doctrine and its sources (Anthropic's context-engineering guidance, the token-counting and prompt-caching docs, the description-cap sources) now sit in skillwright's `SOURCES.md` — Slim entry, which this file does not restate. Runtime tools named as optional, never required: JuliusBrussee/caveman (https://github.com/JuliusBrussee/caveman, output compression) and rtk-ai/rtk (https://github.com/rtk-ai/rtk, Apache-2.0, command-output compression), both read 2026-10-08.
