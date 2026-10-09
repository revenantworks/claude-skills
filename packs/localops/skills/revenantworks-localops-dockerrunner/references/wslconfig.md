# .wslconfig — keys, defaults, and the change rule

> **Last verified: 2026-10-01** against Microsoft's "Advanced settings configuration in WSL"
> (learn.microsoft.com/windows/wsl/wsl-config; its source file in MicrosoftDocs/WSL re-read
> 2026-10-01). Calendar surface, 90 days. Refresh: `dockerrunner refresh`.

**Read this file when:** `audit` reports a WSL value, the user asks to cap WSL memory, or a
`check` fails on the WSL cap.

## Contents

1. Where the file lives and what reads it
2. The keys this skill reads
3. The default cap rule
4. Changing it — never in place
5. vmmem — reading what WSL really holds

---

## 1. Where the file lives and what reads it

`%UserProfile%\.wslconfig` — one file per Windows user. It sets the one WSL2 virtual machine
that every distro shares, Docker Desktop's `docker-desktop` distro included. So a cap here caps
every container. Per-distro settings live in `/etc/wsl.conf` inside the distro; this skill does
not edit that file.

Microsoft recommends the **WSL Settings** app (Start menu) for manual edits. The skill's own
route is `scripts/wslconfig_plan.py` (section 4), which writes a proposal and never edits the
live file.

## 2. The keys this skill reads

| Section | Key | Default (Microsoft) | Why it matters here |
|---|---|---|---|
| `[wsl2]` | `memory` | 50% of Windows RAM | The cap on the whole VM. Containers can never use more |
| `[wsl2]` | `swap` | 25% of Windows RAM, rounded up to the nearest GB | Disk-backed overflow; slow but avoids an out-of-memory kill |
| `[wsl2]` | `processors` | All logical processors | Read and reported, never proposed |
| `[wsl2]` | `defaultVhdSize` | 1 TB (1099511627776) | The VHDX ceiling, used by `check --need-disk-gb` |
| `[wsl2]` | `networkingMode` | `nat` (also `mirrored`; `bridged` is deprecated) | Reported only |
| `[experimental]` | `autoMemoryReclaim` | `dropCache` (also `gradual`, `disabled`) | `disabled` keeps cached RAM inside the VM; vmmem stays large |
| `[experimental]` | `sparseVhd` | `false` | With `true`, new VHDX files are created sparse and can give space back |

Sizes are written as `8GB`, `512MB`. The script reads them in binary units (1 GB = 1024³ bytes);
the difference from decimal units is under 7%, inside the headroom.

**Unknown keys** stay exactly as written. The script never deletes a key it was not asked to
change, and its read-back fails the plan if one changed.

## 3. The default cap rule

The user's rule: **cap WSL memory at about a third of installed RAM**, so local GPU jobs (LM
Studio, ComfyUI) keep room in system memory. The audit reads the real installed figure first and
proposes `floor(RAM ÷ 3)` GB, labelled PROPOSED until the user confirms it.

- On 32 GB: default 16 GB, proposed 10 GB.
- On 64 GB: default 32 GB, proposed 21 GB.

A job that needs more than the cap is a `check` result of `reduce`. Raise the cap for that job
(a new proposal), or shrink the job. Never lift the cap silently.

## 4. Changing it — never in place

1. `python scripts/wslconfig_plan.py --memory-gb N` (add `--swap-gb`, `--auto-memory-reclaim`,
   `--sparse-vhd` as needed). It writes `.wslconfig.proposed` beside the original, keeps every
   other line and the file's line ending, and re-parses its own output. A failed read-back writes
   nothing.
2. Show the user the `diff` it prints and the `warning`.
3. Hand over its `owner_command`: one PowerShell line that backs up the original
   (`.wslconfig.bak-<date>`), copies the proposal in, and runs `wsl --shutdown`.
4. **`wsl --shutdown` stops every distro and Docker Desktop's engine.** Running containers stop.
   Changes apply only after the subsystem has stopped: wait until `wsl --list --running` shows
   none, then start Docker Desktop.
5. Re-run `audit` and confirm the new value reads `source: file`.

Unattended runs never hand over or run step 3; they record the proposal for the user.

## 5. vmmem — reading what WSL really holds

The VM shows on Windows as the `vmmemWSL` process (older builds: `vmmem`). The audit reads its
memory with `tasklist` and reports it beside the cap. A large figure with few containers running
is cache the VM has not returned (microsoft/WSL issue 4166). The fixes, in order: confirm
`autoMemoryReclaim` is not `disabled`; set a cap; as a last step, `wsl --shutdown` (the user's
command — it stops every container).
