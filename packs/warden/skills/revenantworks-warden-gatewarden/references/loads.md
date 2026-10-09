# Loads — skills that load twice

One skill name can reach a Claude Code session from several sources. Each copy pays its listing cost, and each can answer with a different body. `scripts/loads.py` reads every source once and reports one row per name. Verified against Claude Code's skills docs and a live rig, 2026-10-02.

## Sources it reads

Each is optional; a missing one is listed under `not_checked`, never guessed.

| Source | Where |
|---|---|
| User scope | `~/.claude/skills/<dir>/SKILL.md` (a junction is resolved once, so a linked skill counts once) |
| Project scope | `<project>/.claude/skills/<dir>/SKILL.md` for each `--project` (default: the current folder) |
| claude.ai sync | `~/.claude/skills/synced/<account>/manifest.json` and its skill folders; shown in Claude Code as `anthropic-skills:<name>` |
| Installed plugins | `~/.claude/plugins/installed_plugins.json`, each install's `skills/` folder; `enabledPlugins: false` reads as not loading |
| Synced plugins | `~/.claude/plugins/synced/<account>/<plugin>/skills/` |
| Overrides | `skillOverrides` in user settings and each project's `.claude/settings.json` and `.claude/settings.local.json`; `syncClaudeAiSkills` / `syncClaudeAiPlugins: false` read as not loading |

The skill name is the SKILL.md `name:` field, else the folder name. Anthropic's built-in synced skills (pdf, docx and the like) appear only when a local copy shares their name.

## Kinds and fixes

| Kind | What it is | The fix it proposes |
|---|---|---|
| 1 | claude.ai sync twin: an uploaded skill syncs in as `anthropic-skills:<name>` beside the local copy | `"skillOverrides": {"anthropic-skills:<name>": "off"}` in user settings: the key with the prefix hides only the synced copy. Never switch the skill off on claude.ai: that also removes it from Cowork. Re-run after each upload. |
| 2 | Synced, no local copy: a user-created synced skill nothing local carries | Listed as `review` for the owner to judge (a claude.ai-only companion is fine). A name passed with `--retired` gets the same override, plus "delete it on claude.ai by hand". |
| 3 | Plugin plus a local folder, or two plugins carrying one skill (a featured plugin plus its pack) | `skillOverrides` does not reach plugin skills: `claude plugin uninstall <id>` for one copy, the owner's choice. Two unrelated plugins can share a generic name; the bodies column tells. |
| 4 | User scope plus project scope, or two folders whose SKILL.md `name:` is the same | Personal wins over project. Keep one copy; which one is the owner's call (skills are never proposed for removal). |
| 5 | Stale twin: the copies' SKILL.md hashes differ, so one surface runs an older version | A synced twin: re-upload the current zip on claude.ai by hand (Cowork and routines still run the old body even when the twin is off here). Two local copies: `drift.py --pair` names the files. |

## Status per row

- **finding** — a double load still open (kind 1 not off, kind 3, kind 4, or a kind 2 named retired).
- **stale** — the twin is off here, but its body differs (kind 5): Cowork and routines run the old one.
- **review** — kind 2, synced only, for the owner to judge.
- **handled** — the twin is already `"off"` in `skillOverrides`, bodies the same.

Exit 1 on any finding or stale row.

## The settings block

When any row needs an override, the output carries one complete `skillOverrides` block: the user's existing entries kept, the new `"off"` entries added, sorted. gatewarden never writes it. The owner pastes it into user settings (`~/.claude/settings.json`); where config lives is rigwright's, permission rules are gatewarden's. Do not set it through the `/skills` menu: that path saves to the project's `.claude/settings.local.json`, so the fix covers one project only.

## Without a shell

Ask for the `/skills` list (or a screenshot), then compare by name: an `anthropic-skills:<name>` entry beside a bare `<name>` is kind 1; a `plugin:<name>` beside a bare `<name>` is kind 3. Bodies cannot be compared this way: say so, and mark kind 5 NOT-RUN.
