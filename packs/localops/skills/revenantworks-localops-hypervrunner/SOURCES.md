# Sources — revenantworks-localops-hypervrunner

> **Last verified: 2026-10-01** — the primary sources and the parity register below
> (calendar surface, 90 days, declared in `volatile.json`). The incumbent scan is the
> pack-split research of 2026-09-28; the Microsoft and Claude Code pages were re-read on
> 2026-10-01 for this build.

## Primary — the tools this skill drives

- **Windows Sandbox CLI** — learn.microsoft.com, "Windows Sandbox command line" (page updated
  2025-01-24), read 2026-10-01: the CLI starts with Windows 11 24H2; `start --config` takes a
  formatted settings string; `exec` returns only an exit code ("no support for process I/O");
  `share --allow-write`, `connect`, `ip`, `stop`, `list`, `--raw` for JSON. Its own example
  writes `Networking` as `Disabled`.
- **Windows Sandbox configuration** — learn.microsoft.com, "Use and configure Windows Sandbox"
  (updated 2026-03-31), read 2026-10-01: supported values `Enable` / `Disable` / `Default` for
  vGPU, Networking, AudioInput, VideoInput, ProtectedClient, PrinterRedirection,
  ClipboardRedirection; `ReadOnly` defaults to false; writable mapped-folder changes persist after
  the sandbox is disposed; networking and clipboard are on by default; MemoryInMB minimum 2048.
- **Hyper-V cmdlets** — learn.microsoft.com raw pages for `Enable-VMTPM` and `Set-VMKeyProtector`
  (updated 2025-05-14), read 2026-10-01: syntax and the `-NewLocalKeyProtector` example. An
  exact-match read of both pages finds no statement on elevation, so the first-guardian row in
  `references/admin-split.md` stays **unverified** and the guardian goes into setup. `New-VM`,
  `Set-VMFirmware`, `Get-VMSecurity`, `Checkpoint-VM`, `Restore-VMSnapshot`, `New-VMSwitch`,
  `Invoke-Command -VMName` and `Copy-VMFile` as recorded by the research (2026-09-28).
- **Claude Code plugin commands** — code.claude.com/docs/en/plugins/cli-reference, read
  2026-10-01: `claude plugin marketplace add <source>` (owner/repo, git URL, path),
  `claude plugin install <plugin> --json`, the `Run this command now?` prompt for command-run
  installs, its refusal without a terminal, `-y`; `claude plugin list --json` with `id` per entry.
- **Claude Code plugin evals** — code.claude.com/docs/en/plugin-evals, read 2026-10-01: case
  folders (`prompt.md` + `graders/*.md`), `allowed_tools`, `max_turns`, grader types (`regex` with
  `match: not_contains` / `count:N` and `flags`, `tool_used` with `input_match`, `min`, `max`,
  `llm`), `arm: both` for a must-not-fire grader.

## Evidence for the admin split (secondary, research of 2026-09-28)

- containers/podman PR 26277 and PR 27650 (merged 2025-12-09): Hyper-V Administrators members run
  machine actions without full administrator rights; HKLM entries must exist first.
- podman-desktop issues 18963, 18965, 18966 (2026-08-26): tools that still demand elevation; the
  request for a one-time preparation step.
- hashicorp/packer issue 13512 (2025-11-02): a group member's checks failing in a stale or
  filtered session.

## Not used, and why

- A remembered Windows release for this machine: the audit reads the build live every time.
- PowerShell `-EncodedCommand` and temporary `.ps1` files for the read-only calls: scripts pass
  plain single-quoted PowerShell (no double quotes, a tested guard), so nothing is hidden and no
  execution-policy change is needed.

## Parity register

**Checked 2026-09-28** (pack-split research R1, section 2), reconfirmed by reading the build's
primary sources 2026-10-01.

| Incumbent | Link | Checked | What it is |
|---|---|---|---|
| hyperv-mcp | github.com/adamdriscoll/hyperv-mcp | 2026-09-28 | PowerShell module exposed as MCP: VM list, power, checkpoints, PowerShell Direct, file copy; prefers the group; its elevated path uses `Start-Process -Verb RunAs` with `-ExecutionPolicy Bypass`; safety section classes restore, removal, turn-off and reset as destructive |
| domain-expert hyper-v skill | github.com/chrishuffman5/domain-expert (plugins/os/skills/hyper-v) | 2026-09-28 | Windows Server Hyper-V knowledge skill: architecture, Replica, GPU-P, vTPM, shielded VMs, diagnostics; no client sandbox or clean-room job |
| small Hyper-V MCP servers | github.com/Tzion0/hyper-v-mcp, simurg79/hyper-v-mcp, RestrictedWTF/hyper-v-mcp-rs | 2026-09-28 | Lifecycle wrappers; no Gen2 profile, no sandbox |
| official sources | anthropics/skills, claude-plugins-official | 2026-09-28 | exact-match scan for hyper-v, hyperv, sandbox VM: none |
| virtualization-mcp | github.com/sandraschi/virtualization-mcp | 2026-10-01 | VirtualBox, Hyper-V and Windows Sandbox MCP server; sandbox network configurable, on in its examples |
| hypervm-mcp | github.com/heavycaffeiner/hypervm-mcp | 2026-10-01 | No-UAC Hyper-V MCP through a LocalSystem service; standing privilege, the opposite of the admin split |

| Capability | Verdict | Reason | Eval case |
|---|---|---|---|
| VM lifecycle, checkpoints, power | met | Same cmdlets | test-cases TC4, TC5 |
| Guest code through PowerShell Direct | met | Same mechanism; output is data | test-cases TC6, TC13 |
| Server features (Replica, live migration, clustering) | out of scope | domain-expert covers it; this is a client-machine runner | trigger-evals no-4 |
| Gen2 security profile built and proved | **beaten — margin 1** | No incumbent proves secure boot, template and TPM after building; verify exits 1 on any miss | test-cases TC2, TC4 (no native case: it needs a Hyper-V host) |
| Admin split: group by default, one elevated setup handover | beaten | hyperv-mcp self-elevates with Bypass; this audit tells a stale token from a missing membership and never elevates | test-cases TC1, TC8; native `behaviour-token-stale` |
| Clean-room plugin install test from a golden checkpoint | **beaten — margin 2** | No incumbent has the job; PASS needs the plugin in `claude plugin list`, and the revert runs in a `finally` | test-cases TC6, TC7 |
| Untrusted download in a locked-down sandbox | beaten | sandraschi/virtualization-mcp pairs Hyper-V with Windows Sandbox (re-scan 2026-10-01) but leaves networking on by default and proves nothing after start; here the config is validated, one writable folder, network proven off after start | test-cases TC3, TC10; native `behaviour-sandbox-config` |
| RAM pre-flight with other local jobs | beaten | Incumbents see only their own memory; this reads free physical, free commit and the pack's GPU lease | test-cases TC9 |
| Destructive steps | met (adopted) | hyperv-mcp classes them destructive with human approval; here they are owner commands outright | test-cases TC5 |

**Margins:** (1) the verified Gen2 security profile; (2) the clean-room plugin install test from a
golden checkpoint, with a receipt.

**Iterate proposals.**
1. Lifecycle: a `golden` sub-step that records the image's build and patch level beside the
   checkpoint (the audit warns on age today, not on patch level).
2. PowerShell Direct: copy a local marketplace into the guest with `Copy-VMFile` so a plugin can be
   tested before it is pushed.
3. Gen2 profile: add `Get-VMKeyProtector` and the guardian's certificate expiry to verify.
4. Admin split: move the unverified rows (first guardian, Internal and External switch) to
   verified with one recorded live test each.
5. Sandbox: run a check inside the sandbox at logon that writes `ipconfig` into the output folder,
   a second proof of networking off that does not depend on `wsb ip`.
6. RAM: write a RAM lease once the pack's shared resource lease gains `est_ram_bytes`.

**Retire condition.** Retire the sandbox half if Windows Sandbox gains `exec` output and a
Claude-facing wrapper from Microsoft. Retire the whole skill if a maintained Hyper-V MCP server
adds a verified Gen2 security profile, a mode that never self-elevates, and a checkpoint-revert
test runner.

**Verdict: PARITY + MARGIN.**

## Adopted ideas (no text or code copied)

- Prefer the group over elevation; class restore, removal, turn-off and reset as destructive;
  expose only named commands (hyperv-mcp README: Requirements, Safety, command allowlist).
  Ideas only, cited here; no text or code taken, so its licence does not bind this skill.
- Identify the Windows version first; validate with live readings rather than guesses
  (domain-expert hyper-v skill). Ideas only.
