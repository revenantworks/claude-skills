# Sources — revenantworks-localops-dockerrunner

> **Last verified: 2026-10-01** — the primary sources and the parity register below
> (calendar surface, 90 days, declared in `volatile.json`). Research scan 2026-09-28;
> key facts re-read 2026-10-01.

## Primary — the programs this skill drives

| Claim | Source | Checked |
|---|---|---|
| `.wslconfig` location, `[wsl2]` and `[experimental]` keys and defaults (memory 50%, swap 25% rounded up, defaultVhdSize 1 TB, autoMemoryReclaim dropCache, sparseVhd false); restart after `wsl --shutdown`; WSL Settings app recommended | learn.microsoft.com/windows/wsl/wsl-config (page updated 2026-09-16, read 2026-09-28); its source `MicrosoftDocs/WSL` `WSL/wsl-config.md`, raw, re-read 2026-10-01 | 2026-10-01 |
| `wsl --list --verbose`, `--install -d`, `--shutdown`, `--manage <distro> --set-sparse` | Microsoft WSL docs (basic commands, disk management), read 2026-09-28 | 2026-09-28 |
| Docker Desktop 4.93.0 (2026-09-28) and 4.92.0 (2026-09-21); WSL integration fixes | docs.docker.com/desktop/release-notes | 2026-09-28 |
| Docker's data disk at `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`, older `...\wsl\data\ext4.vhdx`; dynamic VHDX does not shrink | secondary write-ups found by search 2026-10-01 (dev.to, makeuseof, linuxvox), confirmed by a read-only probe on a Windows 11 machine with Desktop 4.93.0 on 2026-10-01 | 2026-10-01 |
| `docker mcp` CLI: profiles, gateway run, catalog; `docker mcp feature enable profiles` outside Desktop | github.com/docker/mcp-gateway README, raw, re-read 2026-10-01 (v0.44.1 per the API, 2026-09-28) | 2026-10-01 |
| The docker CLI needs no admin once Desktop runs (`docker-users`); install/update needs admin | docs.docker.com install on Windows, read 2026-09-28 | 2026-09-28 |
| Optimize-VHD needs admin and the Hyper-V module | learn.microsoft.com Hyper-V cmdlets, read 2026-09-28. Whether Hyper-V Administrators alone suffices: **unverified** | 2026-09-28 |

**Unverified, carried as such:** whether `--set-sparse` applies to Docker Desktop's separate data
disk; whether a distro install needs admin once WSL is on; the Docker MCP Toolkit docs summary
calling the Gateway "invite-only" (contradicted by the public repo and release).

## User complaints that set the margins

- microsoft/WSL issue 4166 — WSL2 holds RAM and does not return it (open, about 459 comments).
- microsoft/WSL issue 4699 — the VHDX grows and never shrinks (open since 2019, about 379 comments).
- docker/mcp-gateway issue 317 — secrets from the environment (keywarden's, not this skill's).
- ckreiling/mcp-server-docker issue 22 — run a command inside a running container (parity).

## Parity register

**Incumbents** (read 2026-09-28): ckreiling/mcp-server-docker (Python MCP server, 746 stars,
pushed 2026-08-07); docker/mcp-gateway's `docker` catalog server (runs the docker CLI with
`docker.sock` mounted); WSL setup skills (timsonner `wsl-containers`, hocndh-1784 `wsl-setup`);
WSL MCP servers (aniongithub/wsl-mcp, 20000419/fauxnix). Anthropic's skills repo and the
official plugin marketplace carry no Docker or WSL operations skill (exact-match scan).
Re-scanned 2026-10-01 (unit PR): WSL VHDX cleanup skills (mcpmarket "WSL Disk Cleanup", FrancoEscob/deep-disk-cleanup). mcp-server-docker is GPL-3.0.

| Capability | Verdict | Reason | Eval case |
|---|---|---|---|
| Container, image, volume, network listing and control | met | Plain docker CLI; the incumbents wrap the same CLI | — |
| Compose up and down | met | `docker compose`, plan shown first (adopted from mcp-server-docker's plan + apply) | test-cases 6, 7 |
| Natural-language compose authoring | out of scope | mcp-server-docker does it; this skill drives a program, it does not design stacks | — |
| Engine-up pre-flight (Desktop running, WSL2 backend, context) | beaten | No incumbent checks backend or context before acting | test-cases 9 |
| RAM pre-flight against `.wslconfig` and the pack lease | beaten — **margin 1** | No incumbent reads `.wslconfig` or knows other local GPU and RAM users | test-cases 1, 2; native `wslconfig-default` |
| Disk pre-flight: `docker system df` plus the host VHDX size | beaten — **margin 2** (narrowed 2026-10-01) | WSL 4699: the VHDX never shrinks by itself. A "WSL Disk Cleanup" skill (mcpmarket, source unverified) compacts the VHDX by stopping Docker Desktop; none measures it as a pre-flight or leaves the stop to the user | test-cases 8 |
| WSL distro inventory and install | met | `wsl --list --verbose`; install handed to the user (installs are manual) | test-cases 12 |
| Prune with a dry list first | beaten | Incumbents prune on request; this lists, and the user runs one command by ID | test-cases 3, 4; native `prune-volumes` |
| MCP server hosting | out of scope | Docker's MCP Toolkit owns it; routed, never driven | trigger-evals 17 |
| Docker Model Runner | out of scope | lmstudiorunner owns local LLMs | trigger-evals 13; native `nearmiss-model-runner` |
| Docker Sandboxes | out of scope | hypervrunner (isolation) | trigger-evals 15 |

**Iterate proposals.** (1) Write a RAM lease of its own once the pack's shared-resource file
adds `est_ram_bytes` and a non-GPU holder, so GPU jobs wait for a heavy container. (2) Read
Docker Desktop's custom disk-image location from its settings file instead of asking for
`--vhdx`. (3) A `check` input from compose `mem_limit` values, summed per stack. (4) Verify
`--set-sparse` on Docker's data disk and promote it to the default reclaim route if it works.

**Retire condition.** Retire when Docker Desktop ships its own agent-facing pre-flight (engine,
WSL memory, VHDX size) through `docker mcp` or a Docker-published skill, or when WSL returns disk
space by default (microsoft/WSL 4699 closed as fixed) and caps memory sensibly by default.

**Verdict: PARITY + MARGIN.** Margins: a WSL-aware RAM pre-flight tied to the pack lease, and
host-side disk truth.

## Adopted patterns

- Read tools first, least privilege (docker/mcp-gateway README).
- Logs and stats as read-only views separate from actions (mcp-server-docker README, resources).
- Plan before apply for compose (mcp-server-docker "plan + apply").
- `.wslconfig` changes only with `wsl --shutdown` and a wait, WSL Settings app for manual edits
  (Microsoft WSL settings doc).

Nothing was copied verbatim; no third-party code is included.
