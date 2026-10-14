# Changelog — revenantworks-localops-dockerrunner

## [1.0.0] — 2026-10-01

First public release. Runs Docker Desktop on Windows and the WSL2 virtual machine under it, and
checks RAM and disk before any container work starts.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Reads before it acts: the WSL memory cap in `.wslconfig`, the localops pack lease (who is running a
  GPU job right now), `vmmem`, the VHDX size on the host and `docker system df`.
- Check: pass or fail for a job's RAM and disk needs against the WSL cap, the lease and the host.
- The WSL memory cap: proposes about a third of installed RAM from the real figure, so local GPU
  jobs keep room, and writes `.wslconfig.proposed` beside the file with one copy line that backs up
  the original.
- Compose `up` shows the resolved plan and its risky lines before starting on a yes; `down` never
  deletes volumes or images.
- Prune: a dry list and one command that removes exactly the listed IDs, plus reclaim advice for the
  VHDX, which a prune alone never shrinks.
- Runs a command inside a container, logs in to a registry, lists WSL distros and gives the steps to
  install one.
- Two modes: interactive, and unattended (every value the owner's, every reading measured, only a
  named compose file runs and only pinned image tags are pulled).

### Entry points

- `audit` (changes nothing), `check`, `up <file>`, `down <file>`, `prune`, `status` (disk growth
  since the last recorded audit), `refresh` (re-verifies the WSL and command references).

### Scripts

- `scripts/docker_preflight.py` (read-only: audit, check, status, prune list) and
  `scripts/wslconfig_plan.py` (a proposal beside the file, never in place), Python 3 stdlib, with
  tests.

### Safety rules

- Installs nothing; a missing Docker Desktop, WSL or distro gets an owner walkthrough with a check
  per step and a way back.
- Every destructive step (a prune, a volume removal, `wsl --shutdown`, a disk compaction) goes to the
  owner as one command. Volumes are removed only when named and unused.
- Never edits `.wslconfig` in place and never elevates itself; admin steps say so and stop.
- Reads the lease and `gpu-config.json`, never writes them. No packages, no cloud network.

### Integrations

- Routes away from Docker's MCP Toolkit and Docker Model Runner. Local LLMs are lmstudiorunner's,
  image generation comfyrunner's, VMs and sandboxes hypervrunner's, registry token storage
  keywarden's.
