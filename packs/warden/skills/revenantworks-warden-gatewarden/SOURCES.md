# Sources — revenantworks-warden-gatewarden

> **Last verified: 2026-10-01** — the Claude Code permission and hook facts below, and the parity
> register (calendar surface, 90 days, declared in `metadata.volatile`). Incumbent scan 2026-09-28;
> Claude Code permissions and hooks pages re-read 2026-10-01 (raw Markdown). The reach and layout
> sections below were merged on 2026-10-08 with their own stamps.

## Claude Code facts the rules rest on

| Claim | Source |
|---|---|
| Deny, then ask, then allow; first match wins; specificity does not change the order | code.claude.com/docs/en/permissions.md (2026-10-01) |
| Wrapper list `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`, `noglob`; not configurable | same |
| A Bash rule "isn't a security boundary around the program"; the curl, rm and git push escape table | same |
| PowerShell aliases canonicalised; "Matching is case-insensitive." | same |
| Path rules for Write, NotebookEdit, Glob, MultiEdit accepted and never consulted; startup warning | same |
| `Tool(param:value)` cannot match a primary field; ignored with a startup warning | same |
| Read and Edit denies cover file tools, named-file shell commands and redirections, not `grep -r` from the folder | same |
| Hooks fire inside subagents; `agent_id`, `agent_type`; PreToolUse exit 2 blocks; `permissionDecision`, `additionalContext`; default timeout 600 s; matcher syntax | code.claude.com/docs/en/hooks.md (2026-10-01) |
| Settings precedence, trust dialog, `env` and hooks before trust, MCP filter keys, sandbox not native on Windows | settings, settings-reference, sandboxing, mcp pages (R2 read, 2026-09-28) |

## Parity register (incumbent scan 2026-09-28)

| Incumbent | What it does | gatewarden |
|---|---|---|
| getsentry/skills `claude-settings-audit` | stack detection, writes a read-only allow list; reads settings with `cat`, so `env` values reach the transcript | **met** on allow seeding (idea adopted); **beaten** on masking |
| trailofbits/claude-code-config | sandbox-first baseline, credential-folder deny template | **met** (template adopted and extended for Windows); **beaten** on Windows, where the sandbox does not run |
| HarmonicSecurity/claudit-sec | macOS audit of MCP servers, plugins, connectors, scheduled tasks | **met** on MCP scope; Windows-native |
| Hook collections and hardening checklists (several) | lists and hooks, no audit engine | **beaten**: rule ids, a script, tests |

**Named margins.** (1) PowerShell deny mirroring on Windows (`ps-mirror-missing`, eval case
`behaviour-ps-mirror`). (2) Bypass-shape lint of the shapes the docs name (eval case
`behaviour-ps-mirror`, test-cases 1, 3, 5). **Beaten lines:** env masking (test-case 2), no-ask in
tracked files (`behaviour-ask-tracked`).

**Iterate.** Diff the effective merged policy and print each live rule's source; mark allows that
duplicate a sandbox auto-allow as noise; a regression canary (a probe list the owner replays after an
update); a pinned list of expected user hooks.

**Retire condition.** Retire the audit half when Claude Code ships a built-in linter for dead rules,
bypass shapes and PowerShell gaps (`claude doctor` lists rejected entries only today), or when the
sandbox runs natively on Windows and the owner moves to it. The hooks retire one by one when a
built-in control covers each.

**Verdict: PARITY + MARGIN.**

## Moved in

- `references/security-scan-doctrine.md` — from agentwright 1.3.0 `references/security-scan-doctrine.md`
  (owner decision 2026-10-01, question 3), made self-contained (the trust-tier rule is stated in S2),
  plus two items agentwright's register listed as missing: a data-flow diagram and a probe plan.
- The hooks implement observations 0165 (call cap), 0183 (launch throttle), 0178 (heredoc guard),
  0282 (push gate, decision 27) and owner answer 27 (Hyper-V lock).

## Name collision (searched 2026-09-28)

PyPI `gatewarden` (an agent-gating library), two small GitHub projects (an MCP gateway, a web
application firewall), a WordPress plugin: adjacent or unrelated. `revenantworks-warden-gatewarden`:
no hit. Routing risk with trustwarden ("gate" read as an install gate) is handled in both
descriptions. Verdict SOFT.

## Reach — map, footprint, drift, loads, status (merged 2026-10-08)

Carried with the reach entries when filewarden merged into gatewarden (owner, 2026-10-08). Last
verified 2026-10-01 (calendar surface, 90 days); incumbents first read 2026-09-28 (research report R3,
section 3). Case ids T1-T18 are the reach rows in `evals/test-cases.md`.

### Platform facts

| Claim | Source | Checked |
|---|---|---|
| Transcripts live at `~/.claude/projects/<project>/<session>.jsonl`, subagent transcripts beside them, large outputs in `tool-results/`; plaintext, not encrypted | code.claude.com/docs/en/claude-directory, "Application data" | 2026-10-01 |
| `cleanupPeriodDays` default 30, minimum 1; the same cutoff removes orphaned worktrees | same page, "Cleaned up automatically" | 2026-10-01 |
| `claude project purge <path> --dry-run` previews a per-project cleanup of transcripts, memory, history lines and the `~/.claude.json` entry | same page, "Clear local data" | 2026-10-01 |
| Scratchpad path per OS under Claude Code's temp folder; `CLAUDE_CODE_TMPDIR` moves it | same page, "Session scratchpad directory" | 2026-10-01 |
| Settings precedence: managed, command line, project local, shared project, user; `permissions.additionalDirectories` and project `allow` rules wait for folder trust | code.claude.com/docs/en/settings | 2026-10-01 |
| Tool input path fields: `file_path` (Read, Write, Edit), `path` (Glob, Grep), `notebook_path` (NotebookEdit), `command` (Bash, PowerShell) | code.claude.com/docs/en/hooks | 2026-10-01 |
| Transcript record nesting of `tool_use` blocks | **unverified** — not in the docs; the reader walks every nested object, and a live-file check was not run on the build day | — |
| WizTree CLI flags `/export`, `/admin`, `/sortby`, `/exportdrivecapacity`; admin needed only for the fast MFT scan | diskanalyzer.com/guide (via R3) | 2026-09-28 |
| dust `-j` JSON output | github.com/bootandy/dust README (via R3); field names **unverified** against a live run | 2026-09-28 |

### Parity register

#### Incumbents

| # | Incumbent | What it does | Checked |
|---|---|---|---|
| I1 | WizTree (diskanalyzer.com) | Fast Windows disk analyzer with a CSV export and a treemap image | 2026-09-28 |
| I2 | claude-code-cleaner (GarrickZ2, MIT) | TUI over `~/.claude`: orphan projects by missing source path, age filter, protected paths, dry run, then deletes | 2026-09-28 |
| I3 | diskwarden (olinks, no licence) | Go CLI that finds and cleans build artifacts and AI-tool caches; read-only `scan`, `clean --apply` deletes | 2026-09-28 |
| I4 | `/audit` session-audit skill (gist by lghupan, 2026-03-25) | Reads transcripts and lists every touched file with its operation, flags risky commands, redacts secrets | 2026-10-01 |
| I5 | Claude Code native: retention sweep, orphaned-worktree cleanup, `claude project purge --dry-run` | Deletes aged session data; previews and purges one project | 2026-10-01 |
| — | dust, gdu, WinDirStat, GrantGuard (permission-rule ground, covered above), claudit-sec, agent-pd (hook-first logging) | Read in R3; out of the top three | 2026-09-28 |

#### Parity table (I1 WizTree, I2 claude-code-cleaner, I4 /audit skill)

| Line | vs I1 | vs I2 | vs I4 | Reason | Case |
|---|---|---|---|---|---|
| Drive space map | out of scope (driven) | out of scope | out of scope | WizTree and dust win on speed; the map imports their exports and keeps a stdlib scanner for folders | T1 |
| Junction-true counting | beaten | out of scope | out of scope | each link listed once with its target, never followed; WizTree's handling unverified | T1, test `test_junction_loop_is_listed_once_and_not_followed` |
| Repos and drive layout-rules check | beaten | out of scope | out of scope | no incumbent reads a written layout policy | T6 |
| Paths Claude reached, from transcripts | out of scope | beaten | met | I4 lists touched files too; the footprint groups them by root and needs no prompt-reading of whole transcripts (a script, paths only) | T2 |
| Reached against granted, both directions | out of scope | out of scope | beaten | I4 does not compare with `additionalDirectories` or allow rules; nobody reports granted-never-reached | T2, T3 |
| Orphans (transcripts, worktrees, scratchpads, `~/.claude.json`) | out of scope | met | out of scope | adopted from I2; the native sweep (I5) removes aged items but does not report orphans by missing source | T13, test `test_orphaned_project_and_worktree` |
| Never prints secrets or command text | out of scope | out of scope | beaten | I4 redacts known shapes in printed commands; the footprint never prints command text at all | T7, test `test_no_secret_command_text_or_content_in_output` |
| Live/tracked drift and ownership inventory | out of scope | out of scope | out of scope | no incumbent found (R5 parity table) | T8 |
| Deletes files | out of scope | not matched on purpose | out of scope | proposals with one owner-run command; the native `purge --dry-run` is the preferred command | T4 |

#### Named margins

1. **Reach evidence against grants** — from transcripts that already exist, no hook first; reached-not-granted and granted-never-reached. Cases T2, T3.
2. **Drive layout-rules check** — a map judged against the owner's written rules plus built-in nested-repo and dead-link checks. Case T6.
3. **Junction-true accounting** — links reported once, as links, with targets. Case T1.

#### Iterate proposals

- Drive map: read WizTree's allocated column into every top table when an import exists; add a `--from-gdu` importer if the owner uses gdu.
- Footprint: accept an audit-log hook's JSONL as a second source so refusals appear (I4/agent-pd style), only when the owner points at it.
- Orphans: hand `claude project purge --dry-run` output back in as evidence, so the native plan and the orphan list are compared line by line.
- Drift: read a pairs file the owner keeps in a repo, so a sweep checks every known pair at once.

#### Retire condition

Retire the footprint half if Claude Code ships a built-in report of paths reached against paths granted, or if a maintained incumbent adds the reached-against-granted comparison from transcripts. Keep the drive layout-rules check (`drive_rules.py`) and drive WizTree or dust directly for space.

**Verdict: PARITY + MARGIN** on the footprint half (margins 1 and 3 beaten, 2 unmatched); on the drive-map half WizTree and dust lead and are driven, never rebuilt.

### Adapted ideas (no code copied)

- Orphan detection by missing source path, age threshold, a protected-paths list, and a three-state preview — claude-code-cleaner (MIT), ideas only.
- Read-only scan split from a destructive step — diskwarden; the reach entries never ship the destructive step.
- A self-contained HTML page with no CDN, stdlib only — GrantGuard (MIT), idea only.

## Layout — one settings map (new 2026-10-08)

| Claim | Source | Checked |
|---|---|---|
| Settings levels and precedence: managed, command line, local project, shared project, user | code.claude.com/docs/en/settings (via `rule-grammar.md`) | 2026-10-01 |
| Hooks live in the `hooks` block of any settings level and in a plugin's `hooks/hooks.json` | code.claude.com/docs/en/hooks, code.claude.com/docs/en/plugins (via `rule-grammar.md` and skillwright's build templates) | 2026-10-01 |
| The event log fields (`rule`, `outcome`, `session`, `at`) and the modes file | this skill's own `scripts/hooks/hooklib.py` and `references/hooks.md`, "Modes" | 2026-10-08 |

**Parity.** No incumbent scan was run for this entry on 2026-10-08: it reads gatewarden's own event
log and maps files `perm_audit.py` already reads, so its margin is internal — the overlaps, the
interrupt ranking from the watch/nudge/guard log and one proposed home per rule and hook, all
read-only (test cases 15-16, `scripts/test_settings_layout.py`). A live incumbent scan is owed at the
next 90-day refresh. **Iterate:** read plugin `settings.json` files and MDM policy when the owner points
at them; carry `warden_review.py` labels (real or noise) into the interrupt column. **Retire
condition:** retire `layout` if `claude doctor` or `/permissions` ships one view of every level's rules
and hooks with overlaps; keep the event-log ranking as a `warden_review.py` report.

