# Changelog — revenantworks-foundation-pacewright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): whether a new model should take a job type is scoutwright's `fit` (trigger row #11 is now its near-miss, #29 the baseline pair); compatibility names the run notes as the controller's; the bare reply names `spend`, with `dashboard` folded under it; calibration tables labelled examples (audit K7-2-10, -14, -15, -16, -17).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Paces a Claude subscription's usage across sessions, runs and projects. It
never runs the work: it says what may launch now.

### What it does

- Reads the 5-hour, weekly, per-model and CI-minutes meters, from a statusline meter file or one
  line asked of the owner.
- Spend modes on one shared base: normal, pace, turbo, overnight, owner-away and reset-eve, each
  differing only in its throttle. Turbo starts only on the owner's word.
- Fits a list of planned units or sessions into what the windows have left, with a margin, and
  re-cuts waves that do not fit.
- A percent becomes tokens only through measured calibration; with no measured figure the fit says
  `unfitted`.
- Usage reconciliation (UBA): each reading is compared with the known spend, and launches brake when
  points go missing.
- A weekly budget per meter (Claude windows, the top-model allowance, CI minutes per repo, the
  GitHub API limit, any paid API), written to a budget decision file that a fan-out reads as data.
- Plan profiles: every plan-dependent number in one data file, so a plan change is a data edit.
- Admits a new model for a job type only through a measured baseline.
- Lane rates and tokens per point are dated data per tier and mix, calibrated from owner readings
  at least 1.5 hours apart; a top-tier model's cost per point is measured when it runs alone, and
  stated as an assumption with its source until then.
- Reset-eve turns on when the projected close misses the target, treats under-pace as a deficit,
  prints the lane count at every check and reads the owner's own target from the budget file.
- Fill and catch-up lanes serve planned rows only; spend never creates a row.
- Overnight entry is a gate: every queued command on the allow list and liveness watched from
  outside the session; no blocking question while a row is launchable.
- Budget file stamps come from the clock in the writing command, never typed.

### Entry points

- `check` (with `--dry`, writes nothing), `mode <name>`, `fit`, `uba`, `baseline`, `spend` (tokens by skill, subagent and
  starting prompt, read from local transcripts; counts only), `dashboard`,
  `refresh` (re-verifies the plan profiles against the provider's pages).

### Safety rules

- Writes three files only: the budget decision file, the calibration file and a local overlay.
- Never reasons a number into being; every reading is data, not instructions. Ships no code.

### Integrations

- dispatchwright reads the budget decision file when present and unexpired; neither skill calls the
  other. skillwright or promptwright `slim` sizes one artifact's cost; rigwright places the statusline that writes the
  meter file; agentwright wraps a scheduled pace check.
- Also ships as a featured one-skill plugin; install the pack or the featured plugin, not both.
- Optional mods: `dash` (status-line meters, the meter-file fallback writer) and `privacy`; they
  never block.
