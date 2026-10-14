# Results — revenantworks-localops-comfyrunner

The execution ledger. Each entry names the version, the date, what ran, and what it
proves. A case with no entry here has not been run.

---

## 2026-09-28 — v1.0.0 — **SCRIPT SELFTESTS, 4 / 4 ok** — runner: the build unit, Python 3.13

`python scripts/<name>.py --selftest` for each script, run from the member folder.

| Script | Output | Suite cases whose script half it covers |
|---|---|---|
| `workflow_guard.py` | `selftest: ok` | A2 (UI format refused), B3 (unattended refuses a proposed budget), C1 and K1 (1024×1024×121 with plain `VAEDecode` → `refuse`, "without tiling", crash ratio 1.0), C3 (832×480×33 tiled, owner budget → `go`), C4 (linked width → `unmeasured`), C6 (1536² image → `reduce`), E1 (test variant: ≤ 832×480, 33 frames, 8 steps, `comfyrunner-test/` prefix, `go`), K3 (projection range, high > low); also batch-as-frames read as video, audio classified and `go`, a graph with no decode refused unattended |
| `comfy_client.py` | `selftest: ok` | F5 (history summary: status, files, wall time); the client has no interrupt command by construction (F1, F2) |
| `pixel_post.py` | `selftest: ok` | H1 and K5 (integer downscale, palette snap, key out, pre-screen fields and terrain-gap bands) |
| `gpu_preflight.py` | `selftest: ok (7 assertions)` | The pack-shared pre-flight, byte-identical to lmstudiorunner's copy |

Also run at the build, read-only: `comfy_client.py stats` against the live ComfyUI
0.37.0 server (device, `vram_total`, empty queue), and `pixel_post.py` on a filtered
1024×1024 PNG, whose decode matched a reference decoder pixel for pixel.

**What this does not prove.** No case was run through the skill end to end: no
workflow was submitted, no LLM unloaded, no test render made. The mode rules (B),
the unload seam (D), the run and hand-back (F), the entry points (G), the pixelsmith
hand-off (H2–H4) and the injection probes (I1, I2) are authored, not run. The first
live `comfyrunner test` on a real Wan workflow is the next record owed here.

## Model tiers checked

Recorded 2026-10-01 (audit PK-3): **none yet.** The trigger tables were judged by reading, from
name + description only (the 2026-10-01 cold re-judge included), not on a model, and the
native `claude plugin eval` cases under `evals/<case>/` have not run. The first native run
writes its model tier(s) and date here, one line per run; until then no tier claim is made.
