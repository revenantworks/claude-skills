# Proposal format — one command per change, the owner runs it

gatewarden's reach entries propose; the owner acts. A proposal is complete when the owner can run it without editing it, and safe when its first form previews.

## One item

```
P3 · could free · orphaned project transcripts
Evidence: ~/.claude/projects/<project> — source folder gone; 412 MB; newest file 41 days old
Run:      claude project purge "<source path>" --dry-run
Then:     claude project purge "<source path>"     (after reading the dry-run plan)
```

Fields: an ID, the group (**will free** · **could tighten** · **kept**), the finding, the evidence with its numbers, and the command. Paths in the report are redacted; the command uses the real path only when the owner runs it on their own machine, never in a shared or published copy.

## Commands by finding

| Finding | Command for the owner |
|---|---|
| Orphaned project transcripts or a `~/.claude.json` entry for a missing folder | `claude project purge "<path>" --dry-run`, then without `--dry-run` |
| Worktree with a broken git link | `git -C "<repo>" worktree prune --dry-run --verbose`, then without `--dry-run` |
| Live worktree no longer needed | `git -C "<repo>" worktree remove "<worktree>"` (refuses on uncommitted work: that refusal is the safety) |
| Orphaned scratchpad folder | PowerShell: `Remove-Item -LiteralPath "<folder>" -Recurse -Confirm` · Bash: `rm -rI -- "<folder>"` |
| Large folder the owner chose to clear | the same remove line, one folder per line, never a wildcard |
| Unused grant or reached-not-granted root | no command here: the evidence feeds `gatewarden harden`, which writes the rule change as a finished file |
| Live/tracked drift | one copy line, direction stated, after the owner says which side is right |
| A skill that loads twice (`loads.py`) | a synced twin: the complete `skillOverrides` block for user settings, which the owner pastes (where config lives is rigwright's); two plugins or a plugin plus a folder: `claude plugin uninstall <id>` for the copy the owner drops; two local copies: none here, the owner keeps one (skills are never proposed for removal) |
| Retention longer than wanted | a settings change goes through `harden` or rigwright places it; name `cleanupPeriodDays` |

## Never proposed

Settings files, CLAUDE.md files, skills, agents, commands, hooks, auto memory, `history.jsonl`, credentials, anything inside a repo's tracked tree, and any path the owner listed as kept. These go in the **kept** group so the owner sees they were considered.

## Rules

- Interactive or previewing forms first (`--dry-run`, `-Confirm`, `-I`).
- One target per line; no globs, no recursion over a parent the owner did not name.
- No elevation: a command that needs an administrator shell is named as such and left to the owner.
- gatewarden never runs any of these itself, including after the owner says yes; the owner runs them.
