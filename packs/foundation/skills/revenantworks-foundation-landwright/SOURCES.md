# Sources

Last verified: 2026-11-24

landwright's procedure is drawn from internal records (the estate's landing rule, gatewarden's
hooks, dispatchwright's landing doctrine and the release-kit docs) more than from a published
standard, so this file maps content to origin. The parity register is the one volatile part
(declared in `volatile.json`, calendar class, 90-day cadence).

## Content origins

| Content | Origin |
|---|---|
| The eight land steps, batched pushes, `[skip ci]`, the owner's stops | The owner's standing landing rule ("local first", read 2026-11-24) and observations on the landing flow, 13 of them with no owning skill (skill-set review 2026-11-23, section 4.2) |
| Intent before the push, the local-CI stamp, the refusal shapes | gatewarden's `push_gate.py` and `ci_stamp.py` (this repository, `packs/warden`), read 2026-11-24 |
| Cut from `origin/main`, read rows not exit codes, identity covers PR and merge | dispatchwright's landing doctrine (observations 0651, 0353, 0088) and its `meters.md` — Landing |
| A push reported up to date while ahead is a failed push | observation 0399 |
| A missing tool is not a pass | observation 0354 |
| Addon release checks | `revenantworks/godot-addons` (SUPPORT, SECURITY, NOTICE, layout) and `revenantworks/foundry` release-kit docs and release checklists, read at origin/main 2026-11-24, read-only |

## Parity register

Scanned 2026-11-23 (skill-set review bench), 90-day cadence.

| Id | Skill | Scanned | What it adds that landwright weighed |
|---|---|---|---|
| CC | anthropics/claude-plugins-official, `commit-commands` | 2026-11-23 | Commit, push and open a PR in one command. No local-CI verdict, no intent, no checks read, no merge, no run on main. |
| RM | releasemaster (community) | 2026-11-23 | Release notes from commits. Notes only; 1 to 4 stars. |
| CH | chronicle (community) | 2026-11-23 | Changelog and release notes. Notes only. |
| GP | jame581/GodotPrompter (MIT), addon-development and export-pipeline | 2026-11-23 | `plugin.cfg`, export presets, AssetLib and itch zip layout. Taken as an idea only, in our own words, for `addon-ship.md`; no text copied. |

**Verdict (2026-11-24): PARITY + MARGIN.** Parity: CC's commit-push-PR path is covered by steps
4–6. Margin no register row holds:

- **Local CI on the exact commit is the verdict**, stamped, with skipped steps failing it.
- **Checks read row by row, merge in the next call**, never a chained `--watch`.
- **The run on main is read**; a red run stops for the owner, and a bounded fixer loop runs only
  on the owner's standing go.
- **The owner's stops** on force, CI changes, public repos, tags, releases and publishes.
- **Addon ship checks** that promise no reply or fix time and keep the licence inside the folder.

Each margin line has a case in `evals/test-cases.md`.
