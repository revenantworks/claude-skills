# Sources — revenantworks-warden-trustwarden

> **Last verified: 2026-10-01** — the Claude Code controls and tool flags below, and the parity
> register (calendar surface, 90 days, declared in `volatile.json`). Incumbent scan
> 2026-09-28; Claude Code docs and tool READMEs re-read 2026-10-01.

## Claude Code controls the terms rest on (read 2026-10-01, raw Markdown)

| Claim | Source |
|---|---|
| "A Claude Code plugin you install can execute arbitrary code on your machine with your user privileges." Hooks and MCP servers run outside the sandbox; `bin/` joins the Bash tool's PATH; mods run JavaScript inside Claude Code; auto-update can change reviewed files on disk; `defaultEnabled: false` | code.claude.com/docs/en/plugins/security.md |
| Review order: marketplace source (`claude plugin marketplace list`), the details pane, then `hooks/hooks.json`, `.mcp.json`, every file in `bin/`; `claude --plugin-dir <dir> plugin details <name>` prints a `Component inventory` without starting a session | same page |
| Official and community marketplace names accepted only from `github.com/anthropics/`; `claude-community` pins nearly every entry to a commit SHA; `archive` `sha256` mismatch refuses the install | same page |
| Auto-update on by default for official names (except two) and claude.ai marketplaces, off for every other marketplace; toggled per marketplace in `/plugin` → Marketplaces | code.claude.com/docs/en/discover-plugins.md |
| Plugin source types and pins: `github`, `url`, `git-subdir` take `ref` and `sha` (40-char lowercase; `sha` wins); `archive` takes `sha256`; `npm` never runs install scripts; a `command` source runs a command at install and once per session | code.claude.com/docs/en/plugins/marketplace-reference.md |
| `deniedMcpServers`, `allowedMcpServers`, `enableAllProjectMcpServers`, `enabledMcpjsonServers`, `disabledMcpjsonServers`, `enabledPlugins` (any file); `strictKnownMarketplaces`, `blockedMarketplaces`, `disableCommandPluginSources`, `allowManagedHooksOnly` (managed only) | code.claude.com/docs/en/settings-reference.md (summarised fetch; key names and scopes quoted). Re-read 2026-10-01 by the warden fix round: `deniedMcpServers` "Block specific MCP servers by URL, command, or name"; `disableSkillShellExecution` "Stop skills and custom commands from running inline shell"; `permissions.disableBypassPermissionsMode` "Prevent anyone from entering bypassPermissions mode" |
| Skill `allowed-tools`: "Tools Claude can use without asking permission during the turn that invokes this skill." Skill `hooks` register on invoke and run for the session. ``!`<command>` `` "runs shell commands before the skill content is sent to Claude"; `"disableSkillShellExecution": true` replaces each with a placeholder (bundled and managed skills unaffected) | code.claude.com/docs/en/skills.md |

## Tools driven (read 2026-10-01)

| Tool | Facts used | Source |
|---|---|---|
| skillspector | `scan [TARGET]`, `--format terminal\|json\|markdown\|sarif`, `--output`, `--no-llm`; exit 0/1/2; `MAX_FILE_BYTES` 1 MB per file; install via `uv tool install git+…` | raw README, github.com/NVIDIA/skillspector |
| zizmor | `--offline` / `ZIZMOR_OFFLINE`; collects workflows, actions, Dependabot, pre-commit; `--format plain\|json\|sarif\|github`; exit 0, 1, 2, 3, 11–14 | docs.zizmor.sh/usage |
| pinact | `pinact run --check` exits non-zero on unpinned actions; `--fix=false`; `--no-api` offline; token optional against rate limits; install via go, Homebrew, aqua, winget, scoop, release binaries | raw README, github.com/suzuki-shunsuke/pinact |
| OpenSSF Scorecard | Docker image `ghcr.io/ossf/scorecard`, `GITHUB_AUTH_TOKEN`, `--format=json`, `--checks=`, `--repo=` | raw README, github.com/ossf/scorecard |
| cisco skill-scanner, snyk agent-scan | package names, key needs, agent-scan starting stdio servers and sending data to Snyk | R2 scan 2026-09-28 (READMEs read raw that day); not re-read 2026-10-01 |

## User complaints that set the margins

skillspector #363 (oversized files skipped), #268 (verdict-bypass attempts in scanned content),
#72 (pre-commit use); cisco skill-scanner #220 (unrelated files skipped), #229 (signatures read only
`SKILL.md`); snyk agent-scan #421 and #462 (`.pyc` bypass), #482 (pinning covers descriptions only),
#412, #392, #472 (false positives on docs and redaction markers). Read 2026-09-28.

## Parity register

**Incumbents** (checked 2026-09-28): NVIDIA/skillspector (skill scanner, about 18.5k stars, pushed
2026-09-28) · cisco-ai-defense/skill-scanner (2.6k, pushed 2026-09-26) · snyk/agent-scan (3.1k,
pushed 2026-09-28) · cisco-ai-defense/mcp-scanner (1.1k; README not read) · ossf/scorecard v5.5.0 ·
zizmorcore/zizmor v1.30.1 · suzuki-shunsuke/pinact v5.0.0 and stacklok/frizbee · SocketDev/socket-cli
(account needed; unverified) · skill-vetter checklist skills (UseAI-pro/openclaw-skills-security
`skill-vetter`, mcpmarket "Skill Vetter" and "Security Skill Vetter", a `vet-skill` gist) · the Claude
Code plugin security page · Claude Enterprise automated skill scanning (org-side; unverified for a
solo account).

| Capability | skillspector | agent-scan | vetter skills | trustwarden | Eval case |
|---|---|---|---|---|---|
| Static scan of skill files | yes | yes | checklist | **met** by driving skillspector | — |
| MCP server scan | via its MCP mode | yes, but starts the servers | checklist | **beaten on safety**: reads `.mcp.json` and source statically, never starts a server | test-cases 7 |
| GitHub Actions vetting | no | no | no | **met** by driving zizmor and pinact | test-cases 4 |
| Provenance and maintainer signals | partial | no | prose | **met** by `gh api` facts and Scorecard | — |
| Coverage report (what no scanner read) | no | no | no | **beaten**: margin 1 | test-cases 1, native `pyc-hold` |
| Verdict as install terms tied to Claude Code controls | no | no | partial | **beaten**: margin 2 | test-cases 3, 6 |
| Re-vet on update (diff since the pinned SHA) | no | descriptions only | no | **beaten**: `revet` diffs the whole tree and both tree hashes | test-cases 8 |
| Load-time and installer writes (skill `!` shell, hooks, `CLAUDE.md` blocks, git hooks) | partial | no | partial | **beaten**: rules `skill-shell`, `installer-writes-config` | test-cases 5, 9 |
| Runs offline, no account | yes | no | yes | **met** | — |

**Named margins.**
1. **Coverage ledger.** Every file gets a row with its readers; bytecode, archives, binaries and
   files over 1 MB are UNREAD; an UNREAD executable kind makes PASS impossible. Case: test-cases 1
   and native `pyc-hold` (a skill with a `.pyc` and a 2 MB companion that "passed the scanner" must
   come back HOLD with both files UNREAD).
2. **Install terms tied to Claude Code's own controls.** Every PASS or CONDITIONAL names the SHA,
   auto-update off, and per-finding terms (`deniedMcpServers`, `disableSkillShellExecution`,
   `defaultEnabled: false`, deny rules for `bin/`). Cases: test-cases 3 and 6; script test
   `test_every_pass_or_conditional_carries_sha_and_autoupdate`.

**Iterate proposals.**
- Static scan: run cisco skill-scanner's static analyzers as the default second reader when
  installed, so two scanners can agree without the network.
- MCP scan: parse server source for the tool descriptions it would register, so tool poisoning is
  read without starting the server.
- Actions: feed pinact's resolved SHAs straight into the `pin-action` terms when a token is present.
- Provenance: record a maintainer-signal snapshot beside the pin so `revet` can show what changed in
  the maintainers as well as the code.
- Coverage: read oversized text files in chunks with the red-flag rules, so "oversized" stops
  meaning "unread by everyone" for text.
- Terms: emit gatewarden's rule list as a machine-readable block gatewarden can take as input.
- Re-vet: hash the tree of an installed plugin's cache copy and compare it with the pinned tree.

**Retire condition.** Retire when one scanner covers skills, plugins, MCP servers and Actions with a
coverage report and install terms, or when Claude Code ships an install-time vet that pins, scans and
reports skipped files itself.

**Verdict: PARITY + MARGIN**, as an orchestrator. Name collision SOFT (trustwarden.ai, an identity
product for agents; trustwarden.ca, a security firm; an empty GitHub repository; none on npm, PyPI or
crates.io; searched 2026-09-28).

## Adapted ideas (no text or code copied)

The review order (marketplace source, details pane, hooks, `.mcp.json`, `bin/`) follows the Claude
Code plugin security page. SHA pinning with a version comment follows pinact's convention.
Per-server consent before contact and link-local refusal follow snyk agent-scan's design. Reading a
scanner's report by file role and matched string is this pack's own doctrine (skillwright rubrics).
Added 2026-10-08 (K4 C4, ideas from a review of popular public skills, written in our own words):
Sentry's skill-scanner (`getsentry/skills`, Apache-2.0; its SKILL.md read 2026-10-08 for what it
checks and runs) as an optional, vetted second reader; lockfile supply-chain checks, credited to
Trail of Bits' supply-chain skills; the copied-name check, from the review's finding that five
look-alike "superpowers" packs showed 210k to 695k installs. Nothing was installed.
Licences: the docs are Anthropic's published documentation; the tools are each under their own
licence and are run, never vendored.
