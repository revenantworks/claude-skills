# Identity surfaces — every place a name can leak, and how to check it

Read in `check` mode and when drafting a policy's surface list.

| Surface | What carries names | Check with |
|---|---|---|
| Tracked files | file text, file paths, fixture data, example config | `check --staged` before each commit; `check --range` for what is already committed |
| Commit metadata | author and committer name and address, trailers (`Co-authored-by`, `Signed-off-by`) | `identity --range <base>..HEAD` |
| Commit messages | free text, issue references | `check --range` (messages included) |
| Branch and tag names | a person's or client's name in a branch name | `check --branches` |
| PR and issue text | titles, bodies, review comments | save the draft to a file, `check --text` before posting |
| Rendered pages | published artifacts, docs sites, generated reports | `check --text` on the source before publishing |
| Settings and hooks | an `env` block setting `GIT_AUTHOR_EMAIL`, attribution text | read `.claude/settings*.json`; `check --text` on the file |
| Paths in output | a home folder named after a person | a `path:` class entry; the script also folds the running user's home to `~` |

## Order of checks before a push

1. `identity` on the repo: the address the next commit will use.
2. `identity --range <upstream>..HEAD`: every commit about to leave the machine.
3. `check --range <upstream>..HEAD --surface <repo's surface>`: messages and added lines.
4. For a public repo, `scan --history --identities` reads the same policy at scale.

## What a hit means

A `codename-required` hit is fixed in the text before it ships: replace the value with the
codename the finding names. A `banned-value` hit with no codename asks the user what the surface
should say. A hit already in pushed history is not fixed by a new commit; hand the range to
the rewrite steps (`plan` to `after`), gated on the user.

## Never on any surface

- Never echo a value to confirm a hit ("found <value> in line 4"). Report the rule, the class,
  the key label and the location.
- Never paste the values file, or a diff of it, into a report, an artifact or a chat that will be
  shared.
- Never send text to an outside service to look for names; all checks run locally.
