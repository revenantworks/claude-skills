# Install walkthrough — optional tools (owner-run)

keywarden installs nothing. Every tool below is optional: without it the matching store or
step reports NOT-RUN and the skill continues. Each step is the user's, with a check and a way
back. Run them in your own terminal; never paste a token into chat.

| Tool | Used for | Without it |
|---|---|---|
| Python 3 | all three scripts | the store list is walked by hand; every store is NOT-RUN |
| git | the `gcm` store | `gcm` NOT-RUN |
| gh | the `gh` store reads a file; `scope_check.py` calls `gh api` | `scope` falls back to the token settings page |
| 1Password `op` | injecting references at run time | references are proposed, not run |
| Bitwarden `bws` / `bw` | the same, for Bitwarden | same |

## gh (GitHub CLI)

1. Find the id first: `winget search "GitHub CLI"`, then `winget install --id <id it shows>`
   (ids were not re-verified for this release; the search is the check).
   Check: `gh --version` prints a version.
2. Sign in, in your own terminal: `gh auth login` (choose HTTPS; let gh store the token in the
   system credential store; do not pass `--insecure-storage`).
   Check: `gh auth status` lists the account. Do not add `--show-token`.
3. Way back: `gh auth logout`, then `winget uninstall --id <same id>`.

## 1Password CLI `op`

1. `winget search "1Password CLI"`, then `winget install --id <id it shows>`.
   Check: `op --version`.
2. Turn on the CLI integration in the 1Password desktop app's developer settings, so
   `op` signs in through the app and no password is typed into a shell.
   Check: `op whoami` prints the account, no secret.
3. Way back: turn the integration off; `winget uninstall --id <same id>`.

## Bitwarden Secrets Manager CLI `bws`

1. Download the release for Windows from Bitwarden's official release page, check its published
   checksum, and put `bws.exe` on PATH.
   Check: `bws --version`.
2. Create a machine-account access token in the Secrets Manager web app and set it as
   `BWS_ACCESS_TOKEN` in your user environment through Windows settings, not in a file in a repo.
   Check: `bws project list` returns projects (names, no values).
3. Way back: delete the access token in the web app, remove the variable, delete `bws.exe`.

## What the skill checks after each step

`cred_inventory.py --stores env,gh,gcm` re-runs: the new tool's credential should appear as a
keyring or reference row, never as plaintext.
