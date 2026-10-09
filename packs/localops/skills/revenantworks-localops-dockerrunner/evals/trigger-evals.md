# Trigger evals — revenantworks-localops-dockerrunner

Counts: 25 queries (13 should, 12 should-not, 1 pairs)

Provenance: authored against SKILL.md v0.1.0 (2026-10-01), by the unit that wrote the
description. Judged from **name + description only**, as a cold router would. Not a cold judge —
the reader wrote the clauses — so a cold re-judge was owed. **Cold re-judge done 2026-10-01 (unit J1):** 24 rows, 0 misroutes; one collision with keywarden (J1 M9, C2: keywarden's suite routes "log in to Docker Hub" here while this description ceded "registry logins and secrets"). **FX4, 2026-10-01:** J1 edit E7 ("registry token storage is keywarden's") plus the trigger "to log in to a registry"; row #25 added. Re-judged by hand from name + description: rows 1-24 do not move (#18 "rotate my Docker Hub token" still routes to keywarden through "token storage"). **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Balance: 13 should-fire · 12 should-not (8 near-misses, 4 off-topic) — 25 in all. Unit: one query = one numbered row.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "docker desktop is stuck on starting" | Desktop will not start |
| 2 | "vmmem is using 12 GB of my RAM" | vmmem / WSL eats RAM |
| 3 | "my docker disk keeps growing even after I delete images" | Disk image keeps growing |
| 4 | "cap wsl at 8 GB" | WSL memory cap |
| 5 | "what's my .wslconfig actually set to" | Check the cap |
| 6 | "install ubuntu 24.04 in wsl" | Distro install steps |
| 7 | "list my wsl distros" | Distro inventory |
| 8 | "bring up the compose stack in this repo" | Compose up |
| 9 | "take the compose stack down" | Compose down |
| 10 | "clean up old docker images and stopped containers" | Prune |
| 11 | "run psql inside the db container" | Command inside a container |
| 12 | "dockerrunner status" | Named keyword |
| 25 | "log in to Docker Hub from Docker Desktop" | "to log in to a registry"; the login is one owner command here, token storage is keywarden's (J1 M9, E7) |

## Should not fire

| # | Request | Routes to | Kind |
|---|---|---|---|
| 13 | "run llama in docker model runner" | lmstudiorunner | near-miss (Model Runner) |
| 14 | "load a local model and summarise these files offline" | lmstudiorunner | near-miss |
| 15 | "make a sandbox VM to open this download" | hypervrunner | near-miss (sandbox) |
| 16 | "create a Hyper-V VM with 8 GB" | hypervrunner | near-miss |
| 17 | "add the GitHub MCP server from Docker's catalog" | Docker's MCP Toolkit (say so) | near-miss |
| 18 | "rotate my Docker Hub token" | keywarden | near-miss |
| 19 | "generate an image with ComfyUI" | comfyrunner | near-miss |
| 20 | "write a Dockerfile for my Flask app" | none — general coding | near-miss (Docker vocabulary, no Desktop operation) |
| 21 | "set up a weekly routine that prunes Docker" | agentwright (schedule), then this skill | off-topic for routing |
| 22 | "explain the difference between a VM and a container" | none — general knowledge | off-topic |
| 23 | "deploy this container to Kubernetes" | none | off-topic |
| 24 | "query these CSV files with SQL" | duckrunner | off-topic |

## Boundary notes

- **Sharpest pair: 13 vs 11.** "Docker" plus "run" fires both. The description routes Docker
  Model Runner by name to lmstudiorunner; 11 names a container and a command.
- **20 is the watched miss.** Authoring a Dockerfile is coding, not operating Desktop. If it
  fires here, tighten "runs Docker Desktop" before widening anything.
- **21** — the schedule is agentwright's; the prune it schedules still uses this skill's dry-list
  rule.
- **Tuning rule:** misses on 1–12 → make the trigger list pushier; fires on 13–20 → tighten the
  routing sentence for that sibling.
