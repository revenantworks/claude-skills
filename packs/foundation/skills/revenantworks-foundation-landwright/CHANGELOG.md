# Changelog — revenantworks-foundation-landwright

## [1.0.0] — 2026-11-24

First build (owner pick 2026-11-24: one landing-and-release member with an addon-shipping
section; the push step leaves handoffwright).

- Four modes: `land` (the eight steps, sync in to the run on main), `check` (stops before the
  push), `read` (the run on main for a PR, branch or commit), `ship` (Godot addon release checks).
- Local CI is the verdict, through gatewarden's `ci_stamp` when installed; a skipped step or a
  missing tool is not a pass.
- The push intent is its own call, with the exact commit count and head sha; the push goes to
  `origin` only and is read back from the remote.
- The land branch is cut from `origin/main`, never local main.
- Hosted checks are read row by row in one call and merged in the next; never chained, never a
  `--watch` exit code. Merge commit by default; a squash-only repo squashes.
- The land branch is cut before local CI, so local CI runs once, on the head that is pushed.
- A repo whose CI runs only on push to main shows no PR checks: the stamped local run is the
  pre-merge verdict, the report says "no PR checks configured", the run on main is the hosted one.
- The run on main is read; a red run is reported and stops for the owner. A fixer loop of at most
  three rounds runs only on the owner's standing go for that run.
- `[skip ci]` goes on the merge commit's message (`gh pr merge --body`) and is read back on main.
- The `gh` account switch, and the owner's stops (a red run, a merge conflict, force push, a CI or
  visibility change, a public repo before its branch push and its merge, any tag, release or
  publish). The merge reads back from `gh pr view`, never an exit code.
- A skill-pack release (`tools/release.py`) is skillwright's; the addon tag is made after a fetch.
- `references/addon-ship.md`: licence and NOTICE inside the addon folder, SUPPORT and SECURITY
  with no reply or fix times, `plugin.cfg` and asset-library metadata, the repo's own release kit,
  and the tag and draft release only on the owner's go.
