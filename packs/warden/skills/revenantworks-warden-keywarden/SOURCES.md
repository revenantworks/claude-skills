# Sources — revenantworks-warden-keywarden

> **Last verified: 2026-10-01** — the platform facts and the parity register (calendar surface,
> 90 days, declared in `volatile.json`). Incumbent scan 2026-09-28; Claude Code docs, the
> 1Password `op run` page and the Bitwarden Secrets Manager CLI page re-read 2026-10-01.

## Platform facts (read 2026-10-01, quoted in `references/tool-surface.md`)

| Claim | Source |
|---|---|
| Cloud environment variables: `.env` format, one pair per line, quoted multi-line allowed; anyone using the environment can read them | code.claude.com/docs/en/cloud-environments.md |
| API credentials: Pro and Max only; the key never reaches Claude, its commands or the environment; no edit; value not viewable after saving | same |
| Sandbox: macOS, Linux, WSL2; native Windows not supported; `sandbox.credentials` deny and mask; `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` for all subprocesses | code.claude.com/docs/en/sandboxing.md |
| GitHub credentials stay out of the cloud VM; the GitHub proxy attaches them | code.claude.com/docs/en/claude-code-on-the-web.md |
| `op run` conceals secrets in stdout and stderr by default; `--no-masking` turns it off | 1password.dev/cli/reference/commands/run |
| `bws run` injects secrets as environment variables; `bws secret get` returns the value | bitwarden.com/help/secrets-manager-cli |
| `gh auth status` on an invalid `GH_TOKEN` prints no part of the token | observed 2026-10-01 with a dummy token and an empty config dir |
| Docker keeps a login base64-encoded in `config.json` without a credential store; `credsStore`, `credHelpers`; a helper's `list` returns server URLs and user names, `get` the secret | docs.docker.com/reference/cli/docker/login/; github.com/docker/docker-credential-helpers |
| gh storage, `--show-token`, `GH_TOKEN`; GCM stores; fine-grained PAT limits; scope headers | R2 scan 2026-09-28 (cli.github.com, GCM docs/credstores.md, docs.github.com) |

## User complaints that set the margins

anthropics/claude-code issues #9637, #44868, #58043 (plaintext in settings `env`), #58173 (the
model's reflex "fires on output it has already produced, not on commands it is about to run"),
#59094, #59296, #66044 (built-in protection closed not planned), #97429; cloud secrets #32733,
#97934. nopeek's stated gap ("Claude can still `echo $API_SECRET`"). GitGuardian's count of
secrets in public MCP configs (cited in the chatforest.com review, 2026-08-16). Read 2026-09-28.

## Parity register

**Incumbents** (checked 2026-09-28): GitGuardian ggshield AI hook (runtime scanner, account
needed) · spences10/nopeek (redacting CLI + hooks) · kcmadden/claude-code-1password-skill (`op`
skill; macOS secret entry) · 1Password MCP / Environments · secret-management MCP servers
(Vault, Bitwarden, Infisical, Doppler, Azure Key Vault, CyberArk) · gitleaks and TruffleHog
(detection) · small hook projects (Auth-Guard, claude-code-secret-guard) · Claude Code's own
API credentials and sandbox masks.

| Capability | Best incumbent | keywarden | Eval case |
|---|---|---|---|
| Keep values out of the transcript at run time (redaction hook) | ggshield hook, nopeek | **out of scope** — a runtime hook is gatewarden policy; keywarden recommends one | — |
| Secret detection in files and history | gitleaks, TruffleHog | **out of scope** — shieldwarden's; its finding comes here for rotation | — |
| Store and inject from a vault | 1Password skill and MCP | **met**, driven not rebuilt (`op run`, `bws run`) | test-cases 8 |
| Credential location inventory with fingerprints | none found | **beaten** — margin 2 | test-cases 1, 15; native `trigger-inventory`, `behaviour-docker-store`; script tests |
| Least-privilege scope review | none found as a skill | **beaten** — headers only, never the token | test-cases 4; native `behaviour-scope-no-token` |
| Rotation runbook per credential class | 1Password skill (one line) | **beaten** — consumer map, owner issues and revokes, re-inventory | test-cases 5, 11 |
| Leak response | shieldwarden `after` (rotation first) | **met, shared** — keywarden the rotate half, shieldwarden the history half | test-cases 6; native `trigger-pasted-key` |
| Pre-flight on what a command prints when it fails | none found | **beaten** — margin 1 | test-cases 2, 3; native `behaviour-curl-preflight`; script tests |

**Named margins.** (1) Failure-path pre-flight, with a masking wrapper for unknown failure
paths. (2) Fingerprint-only inventory across Windows stores, the two plaintext hot spots
(settings `env`, `.mcp.json`) included.

**Iterate proposals.** (a) Liveness without printing (live, dead or unknown plus the
fingerprint), the TruffleHog way. (b) A references-only `.env.tpl` for any vault, not only
1Password — shipped as a rule in 0.1.0. (c) A consumer map — shipped in 0.1.0 (`seen_at`).
(d) A Docker credential-helper row: shipped 2026-10-01 as the `docker` store (owner standing
rule; `config.json` plus the helper's `list`, server names only).

**Retire condition.** GitGuardian, 1Password or Claude Code itself ships a Windows-aware
credential inventory with fingerprints plus a pre-run failure-path check (for example, if
issue #66044 or #59296 is revived and shipped).

**Verdict: PARITY + MARGIN.** Built.

## Name collision (searched 2026-09-28)

npm `keywarden` (an unrelated CLI), PyPI `keywarden` (a licence client), crates.io `keywarden`
(a passkey server API), GitHub `DINAKAR-S/keywarden` (a vault MCP server: a tool keywarden could
inventory, not a rival skill). The exact skill name has no hit. Verdict SOFT; name kept.

## Departures from the research spec

- Fingerprint: the spec sketched HMAC-SHA256, 8 hex. Built as shieldwarden's method
  (`sha256(salt + value.lower())`, 12 hex) so the two skills' fingerprints compare, which the
  spec also required. The comparison requirement won.
- Added `preflight.py` (check and masked run) to carry margin 1 in code, and a `preflight`
  entry; the spec named the rule but no script.
- Added gh account switching to `scope`, because the identity member's description (merged into shieldwarden 2026-10-08) routed "tokens and
  gh account sign-in" here.
