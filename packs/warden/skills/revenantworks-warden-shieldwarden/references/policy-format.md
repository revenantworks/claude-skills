# Policy format — the tracked policy and the private values file

Read in `policy` mode, and in `check` when a policy fails `lint`. Two files, split on purpose:
the **policy** says what is banned where and may be tracked; the **values file** holds the
banned values themselves and lives only on this machine, outside every repo
(`references/private-files.md`). The script reads both and prints neither value.

## Contents

- The policy file (`identity-policy.json`)
- The values file (`aliases.txt`)
- Rules the script emits
- A starter policy (placeholders only)
- Writing a policy with the user

## The policy file (`identity-policy.json`)

**JSON by default**, so the checker stays stdlib-only. **YAML is an optional path** (owner Q26):
`identity-policy.yaml` (or `.yml`) holds the same keys and loads only when PyYAML is installed;
without it the script exits 3 and names the JSON form. The skill never installs PyYAML; the user
may (`pip install pyyaml`). The script finds the policy in the repo root when `--policy` is left
out, and refuses two policy files side by side.

**Offer the choice once, when a policy is first written.** Run
`python scripts/identity_check.py formats --repo R` (prints the default, whether PyYAML is present,
the trade-offs and any policy already there) and ask one question, JSON first:

- **JSON (default)** — nothing to install; strict syntax, no comments.
- **YAML** — comments beside each rule and easier hand-editing; costs a PyYAML install the user
  runs (stated when `formats` says it is absent), one more dependency to keep current, and
  indentation mistakes are easy by hand.

Record the answer in the policy-writing plan. Switching later is a re-write of the same keys,
never both files at once.

| Key | Required | Meaning |
|---|---|---|
| `version` | yes | `1` |
| `values_keys` | yes | Every key the values file must hold (`class:label`). Lint flags a key missing from the file, and a file key not listed here. This list is how the tracked policy references the values without containing them |
| `classes` | no | The classes in use: `real-name`, `employer`, `client`, `email`, `handle`, `path`, or the user's own. Lint flags a surface naming a class not listed |
| `codenames` | no | `{ "class:label": "codename" }`. A value with a codename raises `codename-required` with `use` set to the codename, on every surface |
| `surfaces` | yes | `{ name: { "banned": [classes], "email_any": bool } }`. `email_any: true` flags any address not allowed, even one not in the values file |
| `allowed_emails` | no | Regexes for addresses allowed anywhere: the account's noreply form, `example.com` placeholders |
| `allowed_trailer_emails` | no | Extra regexes allowed only inside commit trailers (for example the assistant's own trailer address, if the user keeps it) |
| `exclude` | no | `[{ "where": glob, "rule": name }]` known-safe hits; `where` matches the finding's `where` field (`docs/example.md:*`) |
| `values_file` | legacy | The earlier in-repo location. Never read for values: when the file it names exists, lint reports it with the one move command. Delete the field after the move |

Surface names are the user's; `commit-metadata` is the one `identity --range` uses. The usual set
is in `identity-surfaces.md`.

## The values file (`aliases.txt`)

Found in this order: `--values`, the `WARDEN_IDENTITY_VALUES_FILE` variable, then
`~/.warden/aliases.txt` (`%USERPROFILE%\.warden\` on Windows). One entry per line,
`class:label = value`; `#` starts a comment. The label is a neutral handle the user picks
(`client-1`, `owner`, `personal`), because labels **are** printed. Lint fails a label that contains
its own value. Values shorter than 3 characters are skipped and flagged (`value-too-short`): they
would match everywhere.

Rules for this file, in the order they matter:

1. It sits outside every repo. The script refuses one inside a git work tree, whichever way it was
   named: lint reports `values-file-in-repo` with a `fix` command, and `check` exits 3.
2. Claude never writes a value into it. The user creates it with
   `python scripts/warden_private.py setup identity-values` (comment lines only) and types each
   value in their own editor; a value never passes through the chat.
3. It stays out of every published place: no artifact, no report, no cloud routine's repo.
4. A machine without the file can still lint the policy's shape (`values-file-missing`, with the
   setup command); `check` refuses to run (exit 3, NOT-RUN).

## Rules the script emits

| Rule | Mode | Meaning |
|---|---|---|
| `banned-value` | check, identity | A values-file entry of a class the surface bans |
| `codename-required` | check, identity | A value with a codename; `use` names the codename |
| `email-not-allowed` | check | An address not on the allowed list, on a surface with `email_any` |
| `non-noreply-author` / `non-noreply-committer` | identity, check | A commit address not on the allowed list |
| `trailer-email-not-allowed` | identity, check | A trailer address on neither allowed list |
| `no-identity` | identity | No `user.email` anywhere; with `useConfigOnly` on, git refuses to commit, which is correct |
| `no-local-identity` | identity | The address comes from the machine-wide default, not a choice for this repo; `fix` is one command |
| `identity-email-not-allowed` | identity | The effective address is not allowed |
| `use-config-only-off` | identity | Warn: a repo with no identity would fall back silently |
| `identity-ok` | identity | Info: local or include-chosen, allowed address |
| `values-file-missing` | lint | No values file anywhere; `setup` is the one command that creates the template |
| `values-file-in-repo` / `values-file-legacy` | lint | A values file inside a git work tree, or one named by the legacy `values_file` field: not used; `fix` is the one `warden_private.py adopt` command that moves it |
| `values-key-*`, `label-contains-value`, `codename-key-unknown`, `surface-class-unknown` | lint | Policy and values-file hygiene |

Each finding carries `rule`, `severity`, `where`, `field`, and where relevant `commit` (12 hex),
`class`, `key`, `use`, `fp`, `fix`, `setup`. `fp` is an HMAC-SHA256 over the value, keyed by the
environment variable `--salt-env` names: equal values give equal fingerprints within one salt, so
two reports can be compared without either holding the value.

## A starter policy (placeholders only)

```json
{
  "version": 1,
  "values_keys": ["real-name:owner", "employer:employer-1", "client:client-1", "email:personal"],
  "classes": ["real-name", "employer", "client", "email", "path"],
  "codenames": {"real-name:owner": "the user", "client:client-1": "the client"},
  "surfaces": {
    "public-repo":     {"banned": ["real-name", "employer", "client", "email", "path"], "email_any": true},
    "personal-repo":   {"banned": ["employer", "client", "email", "path"], "email_any": true},
    "commit-metadata": {"banned": ["real-name", "employer", "client", "email"], "email_any": true},
    "pr-text":         {"banned": ["real-name", "employer", "client", "email", "path"], "email_any": true},
    "rendered-page":   {"banned": ["real-name", "employer", "client", "email", "path"], "email_any": true}
  },
  "allowed_emails": ["^(\\d+\\+)?[A-Za-z0-9-]+@users\\.noreply\\.github\\.com$", "@example\\.(com|org|net)$"],
  "allowed_trailer_emails": [],
  "exclude": []
}
```

And in the private folder, filled by the user (the setup template holds comment lines only):

```
# ~/.warden/aliases.txt — outside every repo, never pasted into a report
real-name:owner = <the user's real name>
employer:employer-1 = <employer name>
client:client-1 = <client name>
email:personal = <personal address>
```

The `path` class catches a home folder named after a person: add a `path:home = <user folder name>`
line when the user's user folder carries their name.

## Writing a policy with the user

Plan → validate → write. (1) List surfaces with the user: which repos are public, which personal,
which pages get published. (2) List classes, key labels and codenames; no value is asked for.
(3) Draft the policy, show it, and write it on the user's yes. (4) Hand over
`python scripts/warden_private.py setup identity-values` when `where` reports no values file; the
owner adds one `class:label = value` line per key in their own editor. (5) Run `lint`; fix and
re-run until it exits 0. (6) Run `check --staged` once to prove the hook path works before relying
on it.
