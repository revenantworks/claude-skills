# Credential stores on a Windows dev machine

What `inventory` looks at, how it reads each store without a value, and what counts as a
plaintext risk. Store names match `scripts/cred_inventory.py --stores`. Facts that age live in
`tool-surface.md`.

| Store | Where | How it is read | Value readable here? | Plaintext risk when |
|---|---|---|---|---|
| `files` | `.env`, `.env.*` under each `--root` | key=value lines; keys with a secret-like name or a token-shaped value | yes, fingerprinted | a literal value (not `op://…`, `${VAR}`, `$VAR`, `%VAR%`, `<placeholder>`) |
| `files` | `.claude/settings.json`, `.claude/settings.local.json` (project and `~/.claude`) | the `env` block | yes, fingerprinted | any literal secret — every process Claude Code starts inherits it |
| `files` | `.mcp.json` (project), `~/.claude.json` (user and per-project MCP servers) | each server's `env` and `headers` | yes, fingerprinted | a literal key or `Authorization` header |
| `env` | the current process environment | secret-named variables | yes, fingerprinted | always reported; a value set machine-wide reaches every child process |
| `wincred` | Windows Credential Manager (the user's own vault) | `cmdkey /list`: target names, type, whether a user is set | **no** (names only) | never, by itself; it is the safe store |
| `gcm` | Git Credential Manager settings | `git config --global credential.helper` and `credential.credentialStore`, `GCM_CREDENTIAL_STORE` | n/a | helper `store`, or credential store `plaintext` |
| `gcm` | `~/.git-credentials` | `scheme://user:secret@host` lines; host kept, user dropped | yes, fingerprinted | always (it is a plaintext file) |
| `gh` | gh's `hosts.yml` (`GH_CONFIG_DIR`, else `%APPDATA%\GitHub CLI`, else `~/.config/gh`) | `oauth_token:` lines per host | yes when present | a token in the file (gh fell back to plaintext, or `--insecure-storage`) |
| `docker` | Docker's `config.json` (`DOCKER_CONFIG`, else `~/.docker`) | `credsStore`, `credHelpers` per registry, `auths` entries (`auth`, `identitytoken`, `registrytoken`, `password`) | inline `auths` values, fingerprinted | an inline value in `auths` (no store configured: Docker keeps the login base64-encoded in the file) |
| `docker` | the helper's `list` (`--docker-list`, or a saved `--docker-list-file`) | server URL to user name; the user name is dropped | **no** (server names only) | never, by itself |

## Not on disk — list by name from the user's screens

- **Cloud environments** (claude.ai/code environment editor): variables are readable by anyone
  who uses the environment. On Pro and Max, an **API credential** keeps the key out of the
  session entirely; prefer it for any key whose host it can match. Not for GitHub (the GitHub
  proxy handles it) or the hosts that never get a credential (`tool-surface.md`).
- **Routine credentials**: designed by agentwright; keywarden lists them for the consumer map.
- **Docker logins**: the `docker` store above. A login (`docker login`) and Docker itself are
  dockerrunner's; listing, storing and rotating the registry token is keywarden's.

## Rules for the run

- Links and junctions are not followed; `.git`, `node_modules`, virtual environments and build
  folders are skipped; depth 6 by default.
- An unparseable JSON file is listed under `not_read` with the reason only. The parser's message
  is never shown (it can quote the document).
- `cmdkey` output is localised. The parser reads the English labels (`Target`, `Type`, `User`);
  on another display language it reports "no Target lines" instead of a false clean. A saved
  listing can be read with `--cmdkey-file` (target names only; the file holds no values).
- `wincred` "does not work over a network/SSH session" (GCM docs); in a remote shell, report it
  NOT-RUN rather than empty.
- The first live run on a new machine is the user's to start: it shows target names, which can
  name accounts. Ask before running `wincred`; report counts if the user prefers.
- `docker` reads `config.json` only. A helper is run only with `--docker-list` (ask first, as
  for `wincred`), and only as `docker-credential-<name> list`, which returns server URLs and
  user names. Its `get` returns the secret and is never run. A Docker Desktop install usually
  names `desktop`, which keeps the logins in Credential Manager, so they also show under `wincred`.
