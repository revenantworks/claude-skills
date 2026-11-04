# Loads — skills that load twice, sit on the wrong surface, and cost a listing

One skill name can reach a Claude Code session from several sources. Each copy pays its listing cost, and each can answer with a different body. `scripts/loads.py` reads every source once and reports one row per name. Verified against Claude Code's docs and a live rig, 2026-11-04.

## Sources it reads

Each is optional; a missing one is listed under `not_checked`, never guessed.

| Source | Where |
|---|---|
| User scope | `~/.claude/skills/<dir>/SKILL.md` (a junction is resolved once, so a linked skill counts once) |
| Project scope | `<project>/.claude/skills/<dir>/SKILL.md` for each `--project` (default: the current folder) |
| claude.ai sync | `~/.claude/skills/synced/<account>/manifest.json` and its skill folders; shown in Claude Code as `anthropic-skills:<name>` |
| Installed plugins | `~/.claude/plugins/installed_plugins.json`, each install's `skills/` folder; `enabledPlugins: false` reads as not loading. A relative-path plugin in a local-directory marketplace loads in place, so its folder is read, not the old cache `installPath` names |
| Synced plugins | `~/.claude/plugins/synced/<account>/<plugin>/skills/`; with a `manifest.json` only its current folder (`<name>~g<generation>`) is read, and an older folder is listed under `not_checked`; `"<name>@synced": false` in `enabledPlugins` reads as not loading |
| Overrides | `skillOverrides` in user settings and each project's `.claude/settings.json` and `.claude/settings.local.json`; `syncClaudeAiSkills` / `syncClaudeAiPlugins: false` read as not loading |

The skill name is the SKILL.md `name:` field, else the folder name. Anthropic's built-in synced skills (pdf, docx and the like) appear only when a local copy shares their name.

## Kinds and fixes

| Kind | What it is | The fix it proposes |
|---|---|---|
| 1 | claude.ai sync twin: an uploaded skill syncs in as `anthropic-skills:<name>` beside the local copy | `"skillOverrides": {"anthropic-skills:<name>": "off"}` in user settings: the key with the prefix hides only the synced copy. Never switch the skill off on claude.ai: that also removes it from Cowork. Re-run after each upload. |
| 2 | Synced, no local copy: a user-created synced skill nothing local carries | Listed as `review` for the owner to judge (a claude.ai-only companion is fine). A name passed with `--retired` gets the same override, plus "delete it on claude.ai by hand". |
| 3 | Plugin plus a local folder, or two plugins carrying one skill (a featured plugin plus its pack) | `skillOverrides` does not reach plugin skills: `claude plugin uninstall <id>` for one copy, the owner's choice. Two unrelated plugins can share a generic name; the bodies column tells. |
| 4 | User scope plus project scope, or two folders whose SKILL.md `name:` is the same | Personal wins over project. Keep one copy; which one is the owner's call (skills are never proposed for removal). |
| 5 | Stale twin: the copies' SKILL.md hashes differ, so one surface runs an older version | A synced twin: re-upload the current zip on claude.ai by hand (Cowork and routines still run the old body even when the twin is off here). A synced plugin (kind 6): update it on claude.ai. Two local copies: `drift.py --pair` names the files. |
| 6 | One plugin both installed and synced from claude.ai under one manifest name | Not a double load: Claude Code loads the other copy and reports the synced one as not loaded. Never an uninstall, which removes the working install. Alone it reads `handled`; with kind 5 it reads `stale`. To silence it here: `claude plugin disable <name>@synced`. |
| 7 | A skill from a machine-driving pack (`warden`, `localops`) on claude.ai, as a skill or a synced plugin | The owner's choice, so it never fails the run. In chat it mostly reports NOT-RUN while still costing its description; Cowork loads more of a plugin (hooks, agents, local MCP on your computer), so check there first. Switch it off in Customize only if neither uses it. |

## Status per row

- **finding** — a double load still open (kind 1 not off, kind 3, kind 4, or a kind 2 named retired).
- **stale** — the twin is off here, but its body differs (kind 5): Cowork and routines run the old one.
- **review** — kind 2 synced only, or kind 7 on the wrong surface, for the owner to judge.
- **handled** — the twin is already `"off"` in `skillOverrides`, bodies the same.

Exit 1 on any finding or stale row.

## Listing cost

Every run prints the listing's size before its budget: skill count and estimated tokens, per source in `--json`. The estimate is (description + `when_to_use` + name characters) / 3, which came within about 10 tokens of `/skill-doctor` on the skills checked (2026-11-04). One label counts once; an `"off"`, `"user-invocable-only"` or `disable-model-invocation: true` skill counts zero; `"name-only"` counts its name. Bundled skills, MCP tools and instruction files are not in it.

**The budget.** The listing gets 1% of the context window (`skillListingBudgetFraction`). Every name stays, but past the budget Claude Code drops descriptions, least-used skills first, and a skill with no description rarely triggers by itself. So the cost is capped and the damage is lost triggers: a rarely used skill can go quiet because of skills you never use. One entry is also cut at 1,536 characters (`skillListingMaxDescChars`).

**The live figures** are native: `/skill-doctor` gives each skill's listing cost, uses and last use (`< 20` means name only, its description was dropped); `/doctor` estimates the listing and its biggest contributors; `/plugin` marks plugins not used recently. From Git Bash, `claude -p "/skill-doctor"` fails because the shell rewrites the path; run it from PowerShell.

**Making room, in this order:**
1. Switch off what is never used. Plugin skills go by whole plugin (`/plugin`, or `claude plugin disable <name>@<origin>`; `skillOverrides` does not reach them). Others: `/skills` or `skillOverrides`. On claude.ai, switching one off also removes it from Cowork, so it is the owner's decision about use, and never the fix for a double load.
2. `"name-only"` for a skill you only call by name: it stays in the `/` menu with no description. `disable-model-invocation: true` does more where you own the SKILL.md.
3. Shorten descriptions, with the key use case first.
4. Raise `skillListingBudgetFraction` (`0.02` = 2%), which spends more context on every turn.

## The settings block

When any row needs an override, the output carries one complete `skillOverrides` block: the user's existing entries kept, the new `"off"` entries added, sorted. gatewarden never writes it. The owner pastes it into user settings (`~/.claude/settings.json`); where config lives is rigwright's, permission rules are gatewarden's. Do not set it through the `/skills` menu: that path saves to the project's `.claude/settings.local.json`, so the fix covers one project only.

## Without a shell

Ask for the `/skills` list (or a screenshot), then compare by name: an `anthropic-skills:<name>` entry beside a bare `<name>` is kind 1; a `plugin:<name>` beside a bare `<name>` is kind 3. Bodies cannot be compared this way: say so, and mark kind 5 NOT-RUN.

## Proving which copy ran

A host's report of where code loads from is a claim. `claude plugin list` said a mod was read from
the checkout, and `plugin update` said nothing to update, while a desktop-app session ran the plugin
cache's older copy (observation 0420). Prove which copy ran from the running code's own output (a
string or a version only one copy contains), and compare the cache under the plugin's `installPath`
even when the CLI reports a folder load.

A skill load prints its base directory, which is the direct proof. On 2026-11-04 a desktop Code tab
session ran a claude.ai plugin from the app's own data folder (`Claude-Data/.../rpm/...`), with
`claude plugin list` showing the local install enabled. So in that session the account's copy ran, and
edits in a local checkout did not reach it until they synced. The docs' order (install beats synced)
was not what this desktop session did; one observation, so re-check on the machine in question. The
same session listed two synced skills that a terminal run hid with `"anthropic-skills:<name>": "off"`.
