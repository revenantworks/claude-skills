# RAM and the pack lease — how dockerrunner reads the shared state

**Read this file when:** `check` runs with `--need-ram-gb`, or `status` reports a lease.

## Contents

1. Why Docker needs to know about GPU jobs
2. What it reads — read-only
3. The RAM rule
4. Headroom is the user's number
5. What it never does

---

## 1. Why Docker needs to know about GPU jobs

Containers run inside the WSL2 VM, and the VM takes host RAM up to its cap. On a machine that
also runs local GPU jobs, those jobs use system RAM too: model files load through it, and
shared-GPU spill lands in it. The localops pack already keeps one lease file for the GPU. No
other Docker tool reads it. dockerrunner does, so a container job does not start while a render
or a model load is mid-flight on the same RAM.

## 2. What it reads — read-only

The pack's lease is defined in `gpu-seam.md`, the pack's shared resource seam, carried by the
localops GPU members (lmstudiorunner, comfyrunner, whisperrunner, obsrunner). dockerrunner does not
carry that file: it puts no work on the GPU. It reads the same two files, from the same place, and
writes neither:

- `gpu-lease.json` in the `localops` folder under the user's local state directory
  (`%LOCALAPPDATA%` on Windows, `$XDG_STATE_HOME` or `~/.local/state` elsewhere). Fields used:
  `holder`, `purpose`, `expires`, and `est_ram_bytes` when present. Held, stale and free are
  read the same way the pack's `gpu_preflight.py` reads them; an unreadable expiry is stale.
- `gpu-config.json` beside it, key `docker`: `ram_headroom_bytes` and `disk_headroom_bytes`,
  set by the user.

Every GPU holder writes `est_ram_bytes` beside `est_vram_bytes` (owner decision, 2026-10-01). A
holder that could not estimate it writes `null`; the rule below treats a missing or `null` figure
as unknown, never as zero.

## 3. The RAM rule

For a job needing `need` bytes:

- **WSL cap:** `need ≤ memory cap` (the `.wslconfig` value, or its 50% default). Fails →
  `reduce`: shrink the job, or propose a higher cap with `wslconfig_plan.py`.
- **Host:** `need + lease reservation + headroom ≤ RAM available now`. The reservation is the
  holder's `est_ram_bytes`. It is counted on top of the live reading because a holder may still
  be loading. That double-counts on purpose: an upper bound is the safe side for a crash gate.
- **Lease held, no `est_ram_bytes`:** interactive → `ask` (name the holder and its purpose);
  unattended → `refuse`.
- **Lease stale:** reported with its content. Interactive → `ask`; unattended → `refuse`. Never
  cleared by this skill.

## 4. Headroom is the user's number

When `docker.ram_headroom_bytes` or `docker.disk_headroom_bytes` is absent, the script proposes
10% of the total and labels it PROPOSED. Interactive runs state it and ask. Unattended runs refuse
until the user sets it. Every report names the value used and its source.

## 5. What it never does

It never writes, renews, takes over or deletes the lease. It never unloads a model or frees a GPU
(each GPU holder owns its own work). The pack decided against a separate RAM lease: one shared
lease with a RAM field covers it, so dockerrunner only reads. A heavy container the user wants GPU
jobs to wait for is named to the user, who holds the lease by hand (`holder: owner`).
