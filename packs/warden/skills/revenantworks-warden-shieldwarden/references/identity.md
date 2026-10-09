# Identity and naming — the steps of `policy`, `check` and `identity`

Read for `policy`, `check` and `identity`. Moved from identitywarden's SKILL.md body when the
identity and naming policy joined shieldwarden (2026-10-08); the steps are unchanged. The policy
format is `policy-format.md`, the git facts `git-identity.md`, the surface list
`identity-surfaces.md`.

**Workflow:** Locate → Lint → Check → Report → Propose (one command per fix)

Two things set this half apart: **the banned values live in an untracked file, outside the
policy**, so the policy can be committed without leaking what it bans; and **`identity --range`
checks every commit in a range**, author, committer and every trailer, where GitHub's push block
reads only the newest commit.

## 1. Locate

Find the policy: `identity-policy.json` (or the optional `.yaml`) in the repo root, which the
script finds when `--policy` is left out, or the path the user names. No policy → offer `policy`;
for a quick `identity` answer meanwhile, write the starter policy from `policy-format.md` to a
scratch folder and run against that.

The values file is private to this machine, outside every repo: `--values`, else
`WARDEN_IDENTITY_VALUES_FILE`, else `~/.warden/aliases.txt` (`%USERPROFILE%\.warden\` on Windows).
`check` cannot run without it, and Claude never reconstructs it from memory. **First need:** run
`python scripts/warden_private.py where identity-values`; if it is missing, recommend the default
path and hand the user one command, `python scripts/warden_private.py setup identity-values`,
which writes a template of comment lines only. The user fills it in their own editor; values never
pass through the chat. Another location: `setup identity-values --path <file>` prints the one
command that sets the variable (`private-files.md`).

## 2. Lint

`python scripts/identity_check.py lint --policy P --repo R`. Exit 0 → go on.
`values-file-missing` → the setup step above. `values-file-in-repo` or `values-file-legacy` (an old
file in a repo folder, or one named by the policy's `values_file` field) stops everything else: the
file is not used, and the finding's `fix` is the one command that moves it into the private folder
(`warden_private.py adopt`). If it was ever committed, the leak is in history: run the rewrite
steps (`plan` to `after`) on that range.

## 3. Check

| Request | Command |
|---|---|
| "which email will my next commit use" | `identity --policy P --repo R` |
| "is my address anywhere in this branch / before I push" | `identity --range <upstream>..HEAD`, then `check --range <upstream>..HEAD --surface S` |
| "sweep every repo under this folder" | `identity --root <folder>` (junctions are not followed) |
| a staged change | `check --staged --surface S` |
| a draft, PR text, a page to publish | save it to a file, `check --text FILE --surface S` |
| branch names | `check --branches --surface S` |
| score an existing setup, change nothing | `lint`, `identity --range` over the unpushed commits, `check --branches`, and a read of `.claude/settings*.json` for an `env` block or attribution text that overrides config |

Pass `--salt-env NAME` when two reports must be compared. Script exit codes: 0 no findings,
1 findings, 3 bad input, 4 internal error (type only). Without a shell, hand back these exact
commands, read nothing into context that the script would have read, and mark each check NOT-RUN.

## 4. Report

One table: rule, severity, where, field, commit, class, key label, and the codename to use. Count
findings per rule. State what was **not** checked (no values file, a range left out, a surface
with no policy entry). A clean result says which targets were clean, never "all clear" in general.

## 5. Propose — one command per fix

- **Identity:** a repo-local `git config --local` line per field (`git-identity.md`, "Fix
  commands"). The rule for a machine that commits for two or more accounts: every repo has a
  repo-local identity, the machine-wide default has no `user.email`, and `user.useConfigOnly` is
  on. Never edit global or system config: write the global change as one command the user runs.
- **A codename hit in unpushed text:** the edit that swaps in the codename, shown as a diff,
  applied on the user's yes.
- **A hit in a commit not yet pushed:** amend or reword, as one command, on the user's yes.
- **A hit already pushed:** the gated history rewrite (`plan` to `after`). Never a force-push.
- **The assistant's attribution trailer:** propose the `attribution` settings key
  (`git-identity.md`) in the settings file the user names, never hand-edited trailers.

## Writing a policy (`policy`)

First ask the format once: JSON by default, or YAML with its pros and cons from
`identity_check.py formats` (comments and hand-editing, against a PyYAML install the user runs).
Then write or update the policy (key labels, no values) as one plan → validate → write loop
(`policy-format.md`, "Writing a policy"), and hand over the setup command for the values file. The
owner types every value into that file in their own editor; Claude shows the policy, never the
values file, and writes on the user's yes. Then `lint` until it exits 0.

**Writes are gated.** The policy is written only in `policy`; text or commits change only as a
proposed fix, each after the user's yes. Never commit on its own, never push, never edit git
config outside the repo it was pointed at. **Local only:** no text goes to an outside service to
look for names; the one network call, `gh api user` for the noreply id, is the user's to run.
