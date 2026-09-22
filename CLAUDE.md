# CLAUDE.md — claude-skills

The canonical home of every Revenantworks Agent Skill (repository
`revenantworks/claude-skills`, renamed from `citadel` 2026-08-17). Two packs live under
`packs/`: **foundation** (ten `-wright` members, standalone profile) and **gamedev**
(since 2026-08-29; `-smith` motif, standard profile; first member pixelsmith). The
foundation pack has its own router `CLAUDE.md` that loads when you work under it. This root file exists because the repo's top level,
`tools/`, and `audit/` previously loaded no standing context at all (audit
finding `citadel-no-root-claude-md`, 2026-08-15).

## Layout

- `packs/<pack>/skills/<member>/` — SKILL.md + references + evals; the pack's
  `.claude-plugin/plugin.json` carries the pack version, which must equal its
  entry in `.claude-plugin/marketplace.json` (the build check enforces it)
- `tools/` — `build.py`, `release.py` (the whole close-of-pass loop), and the
  tests; `audit/` — COLLISION.md and audit records
- `RUNBOOK.md` · `NEXT.md` · `CHANGELOG.md` — operations, backlog, history

## Commands

```bash
python tools/build.py --check      # read-only gate: versions, counts, seams
python tools/build.py --parity     # read-only: installed-copy parity
python -m unittest discover -s tools -p "test_*.py"
python tools/build.py              # REAL build — regenerates references/pack.md manifests
python tools/release.py <pack>=X.Y.Z -m "..."   # bump, build, check, tests, commit, tag, push, brand copies
```

(`python` on the rig, `python3` on Linux clones. A bare `build.py` and
`--footprint` can WRITE manifest drift — the read-only pair above is what
report-only passes are allowed to run.)

## Hard rules

- **This repo is public and ships neutral.** No brand styling content here —
  the definition lives in the private brand repo and overlays at package time.
  No personal, employer, or client name, ever.
- **A member change ships to the public via a PACK version bump** — the pack
  version is the plugin cache key, so a member-only bump never ships there.
- **The rig loads by junction, not by plugin** (2026-08-17). The rig junctions
  every foundation member from `~/.claude/skills/<member>` into this working
  tree. Edit here — it is live next session. `claude plugin update` is not
  part of the rig loop; the pack is uninstalled here. claude.ai copies still
  move by delete-and-re-upload; `release.py` prints which zips changed.
- **Freeze lifted (2026-09-11):** tokenwright, commwright, evalwright were
  frozen 2026-08-17; owner decision 2026-09-11 lifts it. All three are
  ordinary members again — bumps follow the two-clock rule like any other
  member (member clock vs. pack clock; see
  `packs/foundation/skills/revenantworks-foundation-skillwright/references/release-doctrine.md`).
- **No `ask` rules** in any tracked `.claude/settings.json`; a committed `ask`
  freezes an unattended run. Hook wired here: the post-commit pack-bump nudge
  (PostToolUse on `git commit`).
- **`.claude/hooks/` also stores what it does not arm.** Since 2026-08-21 it
  version-controls dispatchwright's two forcing hooks — `dispatch_gate.py`,
  `dispatch_ledger_guard.py` and their `dispatch_patterns.txt` — which are
  deliberately **not** wired in this repo's `settings.json`. A rig installs
  them into `~/.claude/hooks/`, and that installed copy is the one that fires.
  Wiring them here as well would double-fire against an already-armed rig.
