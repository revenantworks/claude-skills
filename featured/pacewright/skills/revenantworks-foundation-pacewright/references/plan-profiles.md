# Plan profiles — every plan-dependent number in one place

Last verified: 2026-09-28

Read when a figure in tokens, units or CI minutes is needed (SKILL.md — Load budget).
**Volatile** (calendar class, 60-day cadence): plans, their multipliers and CI pools change.
`pacewright refresh` re-verifies this file and nothing else.

The modes are written in percentages and port unchanged across plans. This file turns them into
absolute numbers. Two lines select the profile; the user edits them, in the local overlay
(`.dispatch/local.yaml`) or in chat:

```yaml
model_plan: max-20x   # max-20x | max-5x | pro
ci_plan: free         # free | pro | team
```

## Model plans

| Field | max-20x | max-5x | pro |
|---|---|---|---|
| Relative allowance | 20× | 5× | 1× |
| Tokens per weekly point | measured | measured × 0.25 of max-20x until 3 readings | measured × 0.05 of max-20x until 3 readings |
| Parallel units, ceiling | 5 | 3 | 1 |
| Largest unit before a split | 0.8 × the smaller room left (every plan) | same | same |
| Top-model switch | yes | yes | no |
| Turbo available | yes | yes, ceiling 3 | no |

- **Relative allowance** is the provider's own plan naming, used only as a scaling ratio.
- **Tokens per weekly point is in harness-reported tokens**, never cache-inclusive
  input-equivalent, which runs many times larger for the same point (`accounting.md` — every
  calibration constant names its unit).
- **Tokens per weekly point is never a shipped constant.** It is measured on the current plan
  (`window-fit.md` — Calibration). After a plan change it is scaled by the ratio above until three
  readings on the new plan re-measure it, and every conversion made on a scaled figure says
  "scaled, not measured".
- **The first week on a new plan runs the pace throttle.**

## CI plans

| Field | free | pro | team |
|---|---|---|---|
| Hosted minutes a month (private repos) | 2,000 | 3,000 | 3,000 per organisation |
| Hosted floor kept back | about 500 | about 500 | about 500 |
| Default runner | self-hosted | self-hosted | self-hosted |

- Public repositories on standard hosted runners do not draw on the monthly pool.
- A larger or non-Linux hosted runner draws minutes at a multiple; read the provider's billing
  page before counting one.
- The floor is policy, not a provider figure: it keeps hosted minutes for runs only hosted CI can
  prove.

## Shipped defaults

Any figure measured on the author's environment ships here labelled with its plan, sample count
and date, and is used only until the local calibration replaces it (`accounting.md` — first-run
calibration). None is shipped at 1.0.0: every token figure is marked `measured`, so a fresh
install asks or runs `unfitted` until its own readings exist.
