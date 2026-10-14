# RAM pre-flight before a VM or sandbox starts

**Read this file when:** any step is about to start a VM or a sandbox, or plan a VM's memory.

## Why

A VM's startup memory is taken from physical RAM the moment it starts, and it adds to the
commit charge. On a machine that also runs local models or renders, the same RAM and the same
commit limit are shared: a GPU job that spills into shared memory lands in system memory too.
Every other local runner sees only its own memory; this check sees the machine.

## The rule

`request + headroom ≤ free physical memory` **and** `request + headroom ≤ free commit`.

- **request**: the VM's `MemoryStartup`, or the sandbox's `MemoryInMB` (4096 by default).
- **free physical, free commit, total**: `Win32_OperatingSystem` `FreePhysicalMemory`,
  `FreeVirtualMemory`, `TotalVisibleMemorySize`, read live (or from a saved audit).
- **headroom**: the user's number, `ram_headroom_bytes` in `config.json` in the per-user state
  folder (`%LOCALAPPDATA%\localops\hypervrunner\`). Absent: 10% of total is **PROPOSED** and
  labelled. Interactive states the proposal and asks; unattended refuses until the user sets it.

## The GPU lease, read only

The localops pack keeps one GPU lease (`gpu-lease.json` in `%LOCALAPPDATA%\localops\`, fields
`holder`, `purpose`, `started`, `expires`, `est_vram_bytes`, `est_ram_bytes`, `device`,
`instance_ids`; the pack's shared `gpu-seam.md`, carried by the GPU runners, is its home).
hypervrunner never writes or takes it: a VM does not hold the GPU. It reads it because a live
lease means a model or a render is using memory right now, and its `est_ram_bytes` says how
much RAM that holder expects to take. Name that figure when asking; `null` reads as unknown.

| Lease | Interactive | Unattended |
|---|---|---|
| none | no effect | no effect |
| live, any holder | `ask`: name the holder and purpose | `refuse` |
| stale (expired or unreadable) | `ask`: the user decides | `refuse` |

## Verdicts

`go`, `ask`, `reduce`, `unmeasured`, `refuse`; the worst wins. `reduce`: offer less startup
memory (or a smaller sandbox), or wait for the other job. `unmeasured`: interactive says which
reading is missing and asks; unattended refuses. Every report names the request, the headroom
and its source, and the readings.

## The pack decision

The pack keeps one shared lease with a RAM field, not a second RAM lease (2026-10-01). Every GPU
holder writes `est_ram_bytes`; hypervrunner reads it as above and writes nothing.
