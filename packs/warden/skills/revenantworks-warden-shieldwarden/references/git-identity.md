# Git identity — which address a commit gets, and how to pin it

> **Last verified: 2026-10-01** (calendar surface, declared in `volatile.json`). `shieldwarden refresh`
> re-verifies it.

Read in `identity` mode and whenever a fix is proposed. Git facts read from the git-config
documentation (git/git master, `Documentation/config.adoc`) on 2026-10-01; GitHub facts from
docs.github.com the same day. Re-verify on `shieldwarden refresh`.

## Contents

- How git picks `user.email`
- The rule for two accounts on one machine
- `includeIf` conditions, and where they miss
- `user.useConfigOnly`
- The noreply address
- What GitHub's push block does not cover
- The assistant's own attribution
- Fix commands (repo-local, one each)

## How git picks `user.email`

Last one wins across system, global, local, then worktree config; an `include` or `includeIf`
file counts as part of the file that includes it. `git config --show-scope --show-origin --get
user.email` names both the scope and the file that won. The script calls a global value from the
global file itself the **global default** (`no-local-identity`), and a global-scope value from
another file an **include** (`global-include`, set by an `includeIf` block). Environment variables
(`GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_EMAIL`) and `-c user.email=` override all of it for one
command, and a Claude Code `env` block in settings sets them for every command Claude runs: check
`.claude/settings*.json` when a commit's address differs from what config says.

## The rule for two accounts on one machine

When one machine commits for more than one account (a personal and a work or brand account),
every repo carries a **repo-local identity**, set when the repo is cloned or created, and the
machine-wide default carries **no** `user.email`. With `user.useConfigOnly=true` set globally, a
repo with no local identity then refuses to commit instead of quietly using the wrong account.
`identity --root <folder>` sweeps every repo under a folder against this rule. An `includeIf`
per account folder is the alternative, with the misses below.

## `includeIf` conditions, and where they miss

| Condition | Matches on | Watch for |
|---|---|---|
| `gitdir:<glob>` | where the `.git` directory is | case-sensitive; on Windows use `gitdir/i` |
| `gitdir/i:<glob>` | the same, case-insensitive | the right one on a case-insensitive file system |
| `worktree:<glob>` | the current worktree's working directory | a newer keyword; check the installed git has it (`git config --help`) |
| `onbranch:<glob>` | the checked-out branch | — |
| `hasconfig:remote.*.url:<glob>` | any remote URL | keys on the remote, so it survives a moved or linked folder |

The docs state that symlinks inside `$GIT_DIR` are not resolved before matching, while outside it
both the symlink and the real path are tried. A linked worktree's `.git` is a file pointing into
the main repo's `.git/worktrees/`, so a `gitdir` glob written for the clone's folder can miss a
worktree created elsewhere, and a junction or symlink to an account folder can match the wrong
glob. When an include-set identity looks wrong, prefer `hasconfig:remote.*.url` or a repo-local
line.

## `user.useConfigOnly`

With it on, git does not guess an address from the user and host name; a repo with no configured
address cannot commit. It does **not** stop a global `user.email` from applying, which is why the
two-account rule also removes the global address.

## The noreply address

GitHub's private address is `ID+USERNAME@users.noreply.github.com` for accounts created after
2017-07-18, and `USERNAME@users.noreply.github.com` for older accounts with privacy on. The ID is
the account's numeric id (`gh api user --jq .id`, an optional network call the user runs). This is
the default allowed address in the starter policy.

## What GitHub's push block does not cover

The "block command line pushes that expose my email" setting checks only the most recent commit
of a push (docs: "When you push to GitHub, we'll check the most recent commit."). A personal
address in an earlier commit of the same push goes through. `identity --range <base>..HEAD`
checks every commit, author, committer and trailer. Merges made in the web interface carry the
account's own address unless its email privacy is on.

## The assistant's own attribution

Claude Code adds a `Co-authored-by` trailer to commits and a line to PR descriptions by default.
The `attribution` settings key controls both. The settings reference
(code.claude.com/docs/en/settings-reference, read 2026-10-01) lists `attribution.commit`: "Change or
hide the trailer Claude Code adds to commits"; `attribution.pr`: "Change or hide the attribution
line in pull request descriptions"; and `attribution.sessionUrl`: "Omit the claude.ai session link
from cloud and Remote Control commits". Read the key's own entry on that page for the value shape
before proposing it (a replacement string, or the value that hides the line). Propose that key,
in the settings file the user names, rather than editing trailers by hand. Separately, an open
Claude Code issue (#96146, filed 2026-09-22) reports a built-in hook prescribing the assistant's
own address as commit author; `non-noreply-author` catches the result if the policy does not
allow that address.

## Fix commands (repo-local, one each)

Never edit global or system config; hand the user one command per change:

```
git -C <repo> config --local user.email "<noreply-address>"
git -C <repo> config --local user.name "<display name>"
git -C <repo> config --local user.useConfigOnly true
```

A global change (removing the default address, adding `useConfigOnly`, an `includeIf` block) is
written out in full as the one command the user runs; Claude does not run it. A history rewrite
for a bad address already pushed is shieldwarden's gated rewrite.
