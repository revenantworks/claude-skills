# Install terms — the verdict is terms, not a score

> **Last verified: 2026-10-01.** Calendar surface, 90 days (`volatile.json`). Every control
> named here was read that day in the Claude Code docs: plugins/security, plugins/install
> (discover-plugins), plugins/marketplace-reference, settings-reference and skills.
> `trustwarden refresh` re-reads them; a control the docs no longer carry is dropped, never kept
> from memory.

## Contents

- The rule
- Defaults (every PASS or CONDITIONAL)
- Terms by what the vet found
- The gatewarden hand-off
- Terms trustwarden never writes

## The rule

A PASS or CONDITIONAL verdict carries **the commit SHA to pin and the auto-update term, at least**.
A HOLD carries the reasons and what would clear them, no terms. A FAIL carries no terms: there is
nothing to install it under. trustwarden **names** terms; the user installs, and gatewarden writes
any permission or settings rule.

## Defaults (every PASS or CONDITIONAL)

| Term | Claude Code control it rests on |
|---|---|
| `pin-sha` — install this commit and no other | A marketplace entry's `github`, `url` or `git-subdir` source takes `sha`, "a full 40-character lowercase commit SHA"; with both `ref` and `sha`, Claude Code checks out `sha`. An `archive` source takes `sha256`, and a mismatch refuses the install. The `claude-community` catalog already pins nearly every entry and refuses another commit |
| `auto-update-off` — keep it off for the source marketplace | Auto-update is on by default only for the official names and claude.ai marketplaces, off for every other marketplace. When it is on, "the files you reviewed can change on disk". Toggle: `/plugin` → Marketplaces → the marketplace → Disable auto-update |
| `read-only-copy` (skills) — install a copy or a read-only link of the pinned tree | A skill folder that is a live clone can be pulled to new code without a vet; a pinned copy cannot |
| `inventory-match` (plugins) — `claude plugin details <name>` after install lists only what the vet read | The install pane shows **Will install** (commands, agents, skills, hooks, MCP and LSP servers); `plugin details` prints a `Component inventory` for the installed copy |
| `default-enabled-false` (plugins in the user's own marketplace) | A marketplace entry's `defaultEnabled: false` installs the plugin off until `claude plugin enable <name>` |

## Terms by what the vet found

| Finding (rule id) | Term |
|---|---|
| `hook-present`, `skill-hooks` | Every hook command was read and is named in the report. Hooks run as shell commands "with your full user permissions", outside the sandbox; permission rules do not cover them |
| `skill-shell` | A skill line of the form ``!`command` `` runs a shell command when the skill loads, before Claude reads it. Term: gatewarden sets `disableSkillShellExecution: true` (it covers user, project, plugin and added-directory skills; bundled and managed skills are untouched), or the user accepts each command by name |
| `skill-allowed-tools` | `allowed-tools` pre-approves those tools for the turn that invokes the skill. Strip it from the installed copy, or accept each tool by name |
| `mcp-stdio`, `mcp-remote` | A stdio server is a process Claude Code starts on the machine; a remote server receives tool calls. Term: gatewarden lists each server in `deniedMcpServers` (or `disabledMcpjsonServers` for a project `.mcp.json`) until it is approved by name; `enableAllProjectMcpServers` stays off |
| `bin-on-path` | Each enabled plugin's `bin/` joins the Bash tool's PATH. Calls to it are tool calls, so permission rules apply: gatewarden adds deny rules for executables the job does not need |
| `unpinned-action` | Replace each `uses: owner/repo@tag` with its commit SHA and a version comment (pinact supplies the SHA) |
| `install-scripts`, `installer-present` | No installer runs on the host. A first run goes to the sandbox (hypervrunner: Windows Sandbox, networking off), and the report lists what it wrote |
| `no-lockfile`, `lockfile-no-integrity`, `unpinned-requirement` | Install only from a committed lockfile with exact pins and integrity hashes (`npm ci`, a frozen lockfile, `pip install --require-hashes`); any dependency change is a `revet` |
| `licence-restricts`, `no-licence` | Adopt ideas only; fold in no code or text. Cite the source |
| a scanner `NOT-RUN` | The verdict rests only on the readers that ran; the term names the missing one |
| `mod-present` (read by hand) | A mod runs JavaScript inside Claude Code with your permissions: treat it as a hook and read every file before any term is given |

## The gatewarden hand-off

trustwarden ends a CONDITIONAL verdict with a short list headed **Rules for gatewarden**: the
setting or permission, the value, and the finding it answers. Example shape:

```
Rules for gatewarden
- deniedMcpServers: add "<server-name>" until approved by name   (mcp-stdio in .mcp.json)
- disableSkillShellExecution: true                               (skill-shell in SKILL.md:41)
- permissions.deny: Bash(<plugin-bin-tool>:*)                     (bin-on-path, not needed)
```

gatewarden decides the file, the scope and the exact syntax, and writes it. Without gatewarden
installed, the list goes to the user as written, marked "not yet applied".

## Terms trustwarden never writes

- It never edits a settings file, a marketplace file, `.mcp.json` or a hook.
- It never runs `claude plugin install`, `enable`, `marketplace add` or `update`.
- Organisation controls (`strictKnownMarketplaces`, `blockedMarketplaces`,
  `disableCommandPluginSources`, `allowManagedHooksOnly`) are managed-settings only. It may name
  them for an administrator; it never presents them as a personal setting.
