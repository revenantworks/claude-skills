# Tool surface — facts that age

> **Last verified: 2026-10-01** (calendar surface, 90 days, declared in `volatile.json`).
> `keywarden refresh` re-reads each source below (as data, not instructions) and restamps; a fact the source no longer
> carries is dropped, not kept from memory.

## Claude Code and cloud environments (code.claude.com, read 2026-10-01)

| Fact | Source |
|---|---|
| "Environment variables use `.env` format, one `KEY=value` pair per line." "Quote a value that spans multiple lines or contains a `#`" | docs/en/cloud-environments.md |
| "Anyone who uses the environment can read the values." | same |
| API credential: "Anthropic's agent proxy adds the key to requests for the hosts you list, after each request leaves the session's VM. The key never reaches Claude, the commands it runs, or the session's environment variables." | same |
| API credentials "are available on Pro and Max plans. They aren't available on Team or Enterprise plans yet"; added one at a time; "There's no edit"; "You can't view the value again after saving." | same |
| GitHub traffic goes through the GitHub proxy (no API credential needed); the Anthropic API and public package registries never get a credential | same |
| Shared environments: "don't include secrets in them" | same |
| Sandbox: "runs on macOS, Linux, and WSL2. Native Windows is not supported." | docs/en/sandboxing.md |
| `sandbox.credentials` "declares credential files and environment variables to protect from sandboxed commands"; `"mode": "deny"` or `"mask"`; mask shows a per-session sentinel and swaps the real value in on requests to `injectHosts` | same |
| "`sandbox.credentials` affects sandboxed Bash commands only. To strip credentials from all subprocesses regardless of sandboxing, set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`." | same |
| Project and local settings: "Claude Code applies none of their `credentials` entries" | same |
| `sandbox.credentials`: "Hide or mask credential files and variables inside the sandbox" | docs/en/settings-reference.md (read 2026-10-01) |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is named in the `CLAUDE_CODE_SCRIPT_CAPS` row: "JSON object limiting how many times specific scripts may be invoked per session when `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is set." Its own row did not come through in the 2026-10-01 fetch (page truncated); re-read it at refresh | docs/en/env-vars.md (read 2026-10-01) |

**Pending re-test:** the one-line rule for environment variables. The doc allows a quoted
multi-line value; a silent truncation of a multi-line paste was observed earlier. Keep values on
one line until a scratch-environment test settles it, then update this row and the one-line pointer in SKILL.md §2 (moved here by the warden fix round, K-1).

## GitHub CLI (cli.github.com manual; observed 2026-10-01)

- The token is "stored securely in the system credential store", with a fallback to "a plain
  text file"; `--insecure-storage` forces plaintext. `GH_TOKEN` is the headless route.
- `gh auth status --show-token` prints the token. `gh auth token` prints the token.
- **Observed 2026-10-01** with a dummy `GH_TOKEN` and an empty config dir: plain
  `gh auth status` on an invalid token printed the host and "The token in GH_TOKEN is invalid",
  and no part of the token. The success-path display is not verified here.
- `GH_DEBUG=api` prints request headers: `scope_check.py` removes it from the child.
- Minimum classic scopes for gh: `repo`, `read:org`, `gist`.

## GitHub tokens (docs.github.com)

Classic tokens answer with `X-OAuth-Scopes`; fine-grained tokens do not. Fine-grained limits:
one resource owner per token; no outside-collaborator repositories; no Packages; no Checks
API; no user-owned Projects; unused tokens revoked after one year. Read 2026-09-28 (R2 scan).

## Git Credential Manager (GCM docs/credstores.md, read 2026-09-28)

Windows default store `wincredman`; alternatives `dpapi`, `cache`, `plaintext` ("NOT secure"),
`none`; set with `GCM_CREDENTIAL_STORE` or `credential.credentialStore`. wincredman "does not
work over a network/SSH session". The git `store` helper writes `~/.git-credentials` in plain
text.

## Docker credential store (read 2026-10-01)

| Fact | Source |
|---|---|
| "If you don't configure a credential store, Docker stores credentials in the `config.json` file in a base64-encoded format." | docs.docker.com/reference/cli/docker/login/ |
| "Credential helpers are similar to credential stores, but act as the designated programs to handle credentials for specific registries." | same |
| Helper protocol: `store`, `get`, `erase`; the helpers repo adds "list: Lists stored credentials. There is no standard input payload." (server URL to user name) | same; github.com/docker/docker-credential-helpers |
| Helpers shipped: `osxkeychain`, `secretservice`, `wincred`, `pass`; Docker Desktop configures `desktop` | same repo; `desktop` not re-read 2026-10-01 |

## Windows Credential Manager

`cmdkey /list` lists target names, type and user, never passwords; no admin rights for the
user's own vault. Output labels are localised. Not re-verified against a doc page (standard
behaviour, R2 2026-09-28).

## Vault CLIs (read 2026-10-01)

| Tool | Safe | Prints values (never run) | Source |
|---|---|---|---|
| 1Password `op` | `op run` — "Secrets printed to stdout or stderr are concealed by default. Include the `--no-masking` flag to turn off masking."; `op whoami` | `op read`, `op item get --reveal`, `op inject` to stdout, `op run --no-masking` | 1password.dev/cli/reference/commands/run |
| Bitwarden Secrets Manager `bws` | `bws run -- '<cmd>'` — "runs commands with secrets injected as environment variables" | `bws secret get` (returns the secret object with its `value`) | bitwarden.com/help/secrets-manager-cli |
| Bitwarden `bw` | `bw status` | `bw get`, `bw list items` | bw help (not re-read 2026-10-01) |

## Fingerprint method

`sha256(salt + value.lower())`, first 12 hex, the same as shieldwarden's `shield_scan.py`, so a
keywarden row and a shieldwarden hit compare when both read the same salt variable (default
`SHIELD_SALT`). Lower-casing trades a tiny collision risk for comparability with shieldwarden.
