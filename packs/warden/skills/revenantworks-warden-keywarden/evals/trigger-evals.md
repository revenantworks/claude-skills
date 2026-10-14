# Trigger evals — revenantworks-warden-keywarden

Counts: 26 queries (13 should, 13 should-not, 3 pairs)

Provenance: authored against SKILL.md v0.1.0 (2026-10-01), by the unit that wrote the
description. Judged from **name + description only**, as a cold router would. Not a cold judge —
the reader wrote the clauses — so a cold re-judge is owed. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Balance: 13 should-fire · 13 should-not (11 near-misses, 2 off-topic) — 26 in all. Rows 25-26
(KW, 2026-10-01) are the `docker` store pair against dockerrunner; judged by hand, not cold.

FX3 (2026-10-01): the description now says "a vault's MCP server is vetted by trustwarden first" (warden audit W-1, the keywarden ↔ trustwarden seam's description signal). Rows 12 and 19 re-judged by hand: 12 (which token an installed MCP server uses) still fires; 19 (is the Bitwarden MCP server safe to install) now has a named route to trustwarden. Row 22 stays dockerrunner (J1 C2, owner 2026-10-01: dockerrunner keeps the registry login, keywarden stores and rotates the token; E7 lands in dockerrunner's description). J1 cold re-judge: 24 rows, 1 misroute (M9, row 22), resolved by E7.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "where are all my API keys and tokens stored on this PC?" | inventory |
| 2 | "is my gh token too broad? what should it be cut to?" | scope |
| 3 | "I pasted my API key into the chat by mistake, what now?" | leak |
| 4 | "rotate the key the Sunday routine uses and update everything that reads it" | rotate |
| 5 | "check this curl before I run it with my token" | preflight |
| 6 | "my verify script printed something on a 401 — could that have leaked the key?" | preflight, failure path |
| 7 | "are there plaintext secrets in my Claude settings or .mcp.json?" | inventory, named stores |
| 8 | "switch gh to my other GitHub account" | scope, account |
| 9 | "I committed a .env with a live key an hour ago" | leak (rotate half) |
| 10 | "keywarden inventory" | named keyword |
| 11 | "set this project up so the key comes from 1Password instead of a .env file" | references, op run |
| 12 | "which of my tokens does the MCP server for the tracker use, and where else is it?" | consumer map |
| 25 | "which registry logins does Docker keep on this PC, and is any stored in plaintext?" | inventory, `docker` store |

## Should not fire

| # | Request | Routes to | Kind |
|---|---|---|---|
| 13 | "scan this repo and its history for leaked secrets before I publish" | shieldwarden | near-miss (detection) |
| 14 | "plan a history rewrite to remove the key I committed" | shieldwarden | near-miss (rewrite) |
| 15 | "add a deny rule so Claude never reads .env files" | gatewarden | near-miss (policy) |
| 16 | "install a hook that redacts tokens from tool output" | gatewarden | near-miss (hook) |
| 17 | "design the credentials for my new nightly routine" | agentwright | near-miss (routine design) |
| 18 | "which email will my next commit use in this repo?" | shieldwarden | near-miss (identity; re-pointed 2026-10-08 when the naming policy merged into shieldwarden) |
| 19 | "is the Bitwarden MCP server safe to install?" | trustwarden | near-miss (pre-install vet) |
| 20 | "is my installed hook the same as the repo copy?" | gatewarden | near-miss (drift; re-pointed 2026-10-08 when drift moved to gatewarden) |
| 21 | "where should the rule about secrets live, CLAUDE.md or a hook?" | rigwright | near-miss (placement) |
| 22 | "log in to Docker Hub from Docker Desktop" | dockerrunner | near-miss (operate Docker) |
| 26 | "docker pull says the credential helper is not found; fix Docker" | dockerrunner | near-miss (operate Docker) |
| 23 | "write a password-strength checker function in Python" | none | off-topic |
| 24 | "explain how OAuth refresh tokens work" | none | off-topic (concept, no credential of theirs) |

## Edge notes

Sharpest pair: **3 vs 13** — a leak is rotation first (keywarden), and finding where else it
went is shieldwarden's; a leak request fires keywarden, which hands the history half over by
name. Second: **8 vs 18** — which account *authenticates* is keywarden; which identity a commit
is *authored as* is shieldwarden's `identity`. Tuning: misses on the yes-set → push the store names and
"before running a command with a token" harder; fires on the no-set → tighten the boundary
sentence.
