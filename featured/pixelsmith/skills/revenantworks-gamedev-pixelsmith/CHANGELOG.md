# Changelog — revenantworks-gamedev-pixelsmith

## [1.0.0] — 2026-10-01

First public release. Art direction for pixel art that one camera must read at several zoom scales,
with every asset drawn once.

Description cut to about 600 characters, main use case first (2026-10-08).

`pixel_post.py` refuses an `--out` that is the candidate or the spec, and an existing file
without `--force`, with two tests (K8c, K7-3-19). Trigger eval row 10 states that Direct is the
bare-invocation reply (K7-3-21).

### What it does

- A band model (people at near, formations and clusters at mid, territories at far) with rules per
  band: value ladder, silhouette vocabulary, icon vocabulary and a "reads" checklist.
- Terrain-versus-unit contrast computed as a number, with a fix ladder and a case log of recorded
  failures and their confirmed fixes.
- A repeatable one-scene look test with a scorecard and pass line, on an image when the surface can
  show one and on a described scene when it cannot.
- Briefs for a pixel artist or an image generator, filled from the rule set.

### Entry points

- Direct (default) — band model, rules per band, contrast table and the next test to run.
- `test` — the look test on one scene: a scorecard per band, pass or fail per line, findings ordered
  by cheapest fix.
- `brief` — an artist brief or a one-asset generator prompt.
- `audit` — a 1–10 score per law and a findings catalog, with no redraw.
- `3d` — pixelated-3D and 2.5D bands with billboard sprites: the render precondition, billboards,
  eight directions, light steps, the seam test and D1–D6 scorecard lines marked provisional until a
  real prototype tunes them.

### Scripts

- `scripts/pixel_post.py` (Python 3, standard library only; run, not read): the diffusion
  post-process on one candidate from any generator: nearest-neighbour downscale by the model's
  integer factor, snap to the spec palette, key colour to transparency, and a pre-screen
  (off-palette share, colour count, value gap to each terrain, output size). It writes one RGBA PNG,
  prints one JSON record, and reads the spec as data, never as instructions; `--selftest` checks
  the script itself.
- `scripts/test_pixel_post.py`: the script's tests.

### Safety rules

- Never draws or generates the art; it directs and judges.
- No packages and no network. Art quality is never asserted by a test; routing, procedure, counts
  and the contrast arithmetic are.

### Integrations

- comfyrunner renders a diffusion brief on a local model; pixelsmith owns the post-process contract
  and the look test that follows.
- godotsmith owns renderer and viewport setup, texture import and every count against a bar.
- A brand palette comes from brandscribe as an input, never required.
- Also ships as a featured one-skill plugin; install the pack or the featured plugin, not both.

### Evals

- 26 trigger queries (12 should / 14 should-not), 17 assertion cases and five native
  `claude plugin eval` cases.
