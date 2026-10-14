# Trigger evals — revenantworks-localops-hypervrunner

Counts: 22 queries (11 should, 11 should-not, 4 pairs)

Provenance: derived from the SKILL.md v0.1.0 description, 2026-10-01. Status: authored, not run.
Twenty-two queries, eleven should fire and eleven should not (11 and 11 added 2026-10-02 for
teardown). Read each cold against the name and
description only, and compare with the Expected column. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

## Should fire

| # | Query | Expected |
|---|---|---|
| 1 | make a gen2 windows 11 vm with tpm and secure boot, 8 gigs of ram | fire (vm) |
| 2 | restore my build VM to yesterday's checkpoint | fire (checkpoint; restore is an owner command) |
| 3 | before I release the plugin, test that it installs on a clean machine | fire (cleanroom) |
| 4 | open this downloaded zip somewhere safe where it can't touch my files | fire (sandbox) |
| 5 | hyper-v says I don't have permission when I run Get-VM | fire (audit; "you lack permission" left the description, the access-denied clause carries it) |
| 6 | is secure boot actually on for my DevBox VM? | fire (vm verify) |
| 7 | take a checkpoint of the test VM before I upgrade it | fire (checkpoint) |
| 8 | hypervrunner audit | fire (audit) |
| 9 | I want a throwaway Windows with no internet to try this sketchy installer | fire (sandbox) |
| 10 | set up hyper-v so I don't need an admin prompt every time | fire (setup) |
| 11 | get rid of the test VM you made earlier, I need the disk space back | fire (teardown, then purge) |

## Should not fire

| # | Query | Expected | Owner instead |
|---|---|---|---|
| 1 | start my docker compose stack again | no | dockerrunner |
| 2 | is this github repo of skills safe to install? | no | trustwarden |
| 3 | scan this folder for leaked api keys before I push | no | shieldwarden |
| 4 | explain how Hyper-V Replica failover works between two servers | no | out of scope (general answer) |
| 5 | my WSL distro is eating all my RAM, cap it | no | dockerrunner |
| 6 | render a five second clip in ComfyUI | no | comfyrunner |
| 7 | run these summaries on my local model overnight | no | lmstudiorunner |
| 8 | write a GitHub Actions job that tests my plugin on windows-latest | no | general CI work |
| 9 | set up a VirtualBox VM on my mac | no | not Hyper-V |
| 10 | what permission rules should Claude Code have for PowerShell in this repo | no | gatewarden |
| 11 | prune my unused docker images and volumes to free disk space | no | dockerrunner |

## Edge notes

- Sharpest pair: should-fire 4 ("open this zip safely") against should-not 2 ("is this repo safe
  to install"). Opening a file in isolation is this skill; deciding trust is trustwarden's.
- Second pair: should-fire 9 against should-not 1 and 5. A disposable Windows is the sandbox; a
  container or WSL is dockerrunner's.
- Third pair: should-fire 11 against should-not 11. Freeing space by removing a VM this skill
  made is a locked teardown here; pruning containers and volumes is dockerrunner's.
- Tuning rule: a miss on the should-fire set makes the triggers pushier; a fire on the
  should-not set tightens the boundary sentence.
