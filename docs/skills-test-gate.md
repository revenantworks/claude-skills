# Skills test gate

Status on 2026-10-15: **not ready to bump.** 8 of 29 skills pass in the cloud, 7 need a local
check, 13 fail at least one eval case, and 1 is blocked by its suite. No version was bumped.

This file is the gate the owner set: every skill is tested before any pack version bump.
A skill clears the gate when its row reads PASS, or NEEDS-LOCAL with the local check done
and recorded here.

## What ran

All runs used a clean clone in a Linux cloud container with Claude Code CLI 2.1.300.

| Check | Command | Result |
|---|---|---|
| Build gate | `python tools/build.py --check` | clean, 29 = 29 = 29, 4 advisory warnings |
| PII barrier | `python tools/pii_scan.py --tree` | 0 hits over 2993 files; owner-name list not run (no names file in the cloud) |
| Repo tests | `python -m unittest discover -s tools -p "test_*.py"` | 307 pass |
| Warden suites | `python tools/warden_suites.py` | 520 pass |
| Member scripts | `python -m unittest discover` in each `scripts/` | 1,005 pass, 5 skipped |
| Native evals | `claude plugin eval packs/<pack> --runs 1 --ablation none` | 254 cases, see below |

Each failing eval case was run twice more (`--runs 2`). A case that passed at least once is
**flaky**. A case that failed all three runs is a **fail**.

The evals ran without a shell grant. `--allow-tools Bash` is refused here because the container
has no sandbox backend, so the 6 cases that need a shell are owed on a local machine.

The fuller traced suites in each member's `evals/test-cases.md` were not run. Only the native
cases under `packs/<pack>/pack-evals/` were.

## Per skill

Evals pass counts first-run passes out of the skill's native cases. Blocked means the case
could not see its fixture files (see Suite finding).

| Pack | Skill | Script tests | Evals pass | Flaky | Fail | Blocked | Shell | Verdict | Owed on the local machine |
|---|---|---|---|---|---|---|---|---|---|
| foundation | agentwright | none | 2/3 |  | 1 |  |  | FAIL |  |
| foundation | dispatchwright | none | 4/4 |  |  |  |  | PASS |  |
| foundation | grillwright | none | 3/3 |  |  |  |  | PASS |  |
| foundation | handoffwright | none | 3/3 |  |  |  |  | PASS |  |
| foundation | pacewright | none | 6/6 |  |  |  |  | PASS |  |
| foundation | promptwright | none | 3/10 | 2 | 3 | 2 |  | FAIL |  |
| foundation | rigwright | none | 5/6 |  | 1 |  |  | FAIL |  |
| foundation | scoutwright | none | 8/15 | 1 | 1 | 5 |  | FAIL |  |
| foundation | skillwright | none | 8/13 | 1 | 1 | 3 |  | FAIL |  |
| scribe | brandscribe | 118 pass | 17/23 | 1 |  | 5 |  | BLOCKED |  |
| scribe | commscribe | none | 14/22 | 2 | 5 | 1 |  | FAIL |  |
| scribe | lorescribe | 30 pass | 18/29 | 1 | 4 | 6 |  | FAIL |  |
| scribe | researchscribe | 22 pass | 11/13 | 1 | 1 |  |  | FAIL |  |
| warden | gatewarden | 335 pass | 7/15 | 1 | 3 |  | 4 | FAIL | 4 eval cases that need a sandboxed shell |
| warden | keywarden | 36 pass | 5/7 | 1 | 1 |  |  | FAIL | Live credential inventory (Credential Manager, `gh`) |
| warden | shieldwarden | 91 pass | 7/10 | 1 | 1 |  | 1 | FAIL | 1 eval case that needs a sandboxed shell |
| warden | trustwarden | 58 pass | 4/5 | 1 |  |  |  | PASS |  |
| localops | comfyrunner | 17 pass | 3/4 | 1 |  |  |  | NEEDS-LOCAL | Live ComfyUI server and GPU pre-flight |
| localops | dockerrunner | 28 pass | 2/4 | 2 |  |  |  | NEEDS-LOCAL | Docker Desktop with WSL2 on Windows |
| localops | duckrunner | 28 pass, 4 skipped | 5/7 | 1 |  |  | 1 | NEEDS-LOCAL | `duckdb` package (4 tests skipped) and 1 shell eval case |
| localops | hypervrunner | 66 pass, 1 skipped | 5/6 |  | 1 |  |  | FAIL | Hyper-V host; 1 Windows junction test skipped |
| localops | lmstudiorunner | 7 pass | 3/5 | 1 | 1 |  |  | FAIL | LM Studio server and GPU |
| localops | obsrunner | 59 pass | 5/5 |  |  |  |  | NEEDS-LOCAL | OBS Studio with `obsws-python` |
| localops | whisperrunner | 28 pass | 4/5 | 1 |  |  |  | NEEDS-LOCAL | whisper.cpp build and GPU |
| gamedev | godotsmith | none | 3/3 |  |  |  |  | NEEDS-LOCAL | Headless Godot 4 run of a real project (no Godot here) |
| gamedev | pixelsmith | 7 pass | 5/5 |  |  |  |  | PASS |  |
| gamedev | slicesmith | none | 6/7 | 1 |  |  |  | PASS |  |
| gamedev | soundsmith | 30 pass | 5/5 |  |  |  |  | PASS |  |
| gamedev | uismith | 45 pass | 8/11 | 3 |  |  |  | NEEDS-LOCAL | `probe.py` against a page with Playwright installed |

Totals: 179 pass, 23 flaky, 24 fail, 22 blocked, 6 need a shell. Eval cost was about USD 31.

## Suite finding: fixture folders do not reach the case

**Resolved by the scaffold form (trial 2026-10-16).** On CLI 2.1.299 on Windows all 24
`add_dirs` cases failed before the model started (`ENAMETOOLONG` from `uv_spawn`). All 24 now
use `context.scaffold_script`: each case's `scaffold.sh` copies its fixture folders into the
run's working folder, and every case started with its files in place (staged counts matched the
source). Run them with `--scaffold`; without it the working folder stays empty. Inlining the
fixtures stays rejected: the model answered from the prompt without loading the skill. Scores
are not yet measured: the trial ran without a login, so they need one logged-in run, for example
`claude plugin eval packs/scribe --tag behaviour --scaffold --max-cost-usd 10`.

The finding as first recorded:

22 cases declare `context.add_dirs` in `case.yaml`. In CLI 2.1.300 the case's working
directory is empty: the run could not find `brands/`, `site/` or the other fixture folders.
One traced run (`brandscribe--secret-audit-p0`) fired the right skill, then found no files.
2 such cases pass because their expected answer does not need the files. The other 22 fail on
every run. These say nothing about the skills yet; the suite or the CLI needs a fix first.

| Skill | Case | Failed graders |
|---|---|---|
| promptwright | `slim-audit-tail` | `no-rewrite`, `tail-lines`, `verdict` |
| promptwright | `slim-preserves-contract` | `before-after`, `method-and-contract`, `safety-kept` |
| scoutwright | `adopt-names-file` | `affects-line`, `names-key` |
| scoutwright | `changelog-new-versions` | `breaking`, `exact-set`, `first-seen`, `new-942`, `new-943` |
| scoutwright | `docs-page-diff` | `added`, `injection-finding`, `removed`, `undocumented` |
| scoutwright | `fit-card-no-tier-edit` | `card-fields`, `trial-proposed` |
| scoutwright | `stale-model-table` | `no-edit`, `refresh-verb`, `retired-id` |
| skillwright | `audit-currency-pass` | `right-rows` |
| skillwright | `evals-audit-count-integrity` | `non-discriminating` |
| skillwright | `evals-audit-never-fail-tests` | `assertion-free`, `constant`, `fires`, `test-c-clean` |
| brandscribe | `dtcg-to-list` | `alias-resolved`, `file-in-reply` |
| brandscribe | `injected-guide` | `accent-kept`, `injected-reported`, `unconfirmed-block` |
| brandscribe | `secret-audit-p0` | `off-token`, `p0-row`, `verdict-cap` |
| brandscribe | `ui-check-dist` | `fires`, `font-missing`, `injected`, `rows`, `verdict-fix` |
| brandscribe | `ui-taste-p3` | `not-blocking`, `p3` |
| commscribe | `multi-voice-ask` | `asks-which`, `fires`, `names-personal`, `names-support` |
| lorescribe | `branch-leak` | `code-literal`, `not-contra` |
| lorescribe | `ms-injected-chapter` | `injected` |
| lorescribe | `ms-no-write-before-yes` | `proposal-create` |
| lorescribe | `ms-self-contra` | `both-citations`, `code-literal` |
| lorescribe | `ms-variant-no-merge` | `code-literal`, `fires`, `no-merge` |
| lorescribe | `readonly-folder` | `fires`, `injected-reported`, `proposal-block` |

## Fails: 0 of 3 runs passed

Most are `fires` or `skill-fired` graders: the model answered without loading the skill.
One traced run shows a collision with a built-in skill: for `gatewarden--trigger-remove-allow-rule`
the model loaded the built-in `update-config` skill instead of gatewarden. The other `fires`
failures were not traced; a built-in collision is the likely cause but is inferred.

| Skill | Case | Failed graders |
|---|---|---|
| agentwright | `behaviour-zero-signal` | `blast-first` |
| promptwright | `hosted-other-vendor-unrouted` | `fires` |
| promptwright | `trigger-slim-system-prompt` | `fires` |
| promptwright | `trigger-which-tier` | `fires` |
| rigwright | `trigger-status-claim` | `fires` |
| scoutwright | `trigger-fit-new-model` | `fires` |
| skillwright | `trigger-mcp-tool-contract` | `fires` |
| commscribe | `dash-recast` | `fires`, `no-splice` |
| commscribe | `injected-line` | `fires` |
| commscribe | `store-page-honest` | `no-fake-urgency`, `skeleton` |
| commscribe | `ui-microcopy-rewrite` | `strings` |
| commscribe | `voice-diff-no-write` | `asks-to-write`, `fires`, `proposal-block` |
| lorescribe | `absent-runner-text` | `fenced-brief`, `fires` |
| lorescribe | `name-variant` | `code-literal`, `fires` |
| lorescribe | `trigger-manuscript-extract` | `fires` |
| lorescribe | `trigger-timeline-svg` | `fires` |
| researchscribe | `injected-source-finding` | `fires` |
| gatewarden | `behaviour-ask-tracked` | `fires` |
| gatewarden | `map-trigger-disk-space` | `skill-fired` |
| gatewarden | `trigger-remove-allow-rule` | `skill-fired` |
| keywarden | `behaviour-curl-preflight` | `explains`, `no-verbose-curl`, `preflight-run` |
| shieldwarden | `identity-trigger-unpushed-email` | `skill-fired` |
| hypervrunner | `behaviour-token-stale` | `skill-fired` |
| lmstudiorunner | `behaviour-gpu-busy` | `waits` |

## Flaky: failed first, then passed in some re-runs

| Skill | Case | Failed graders (first run) | Re-runs passed |
|---|---|---|---|
| promptwright | `model-entry-no-prompt` | `flip-and-boundary`, `tier-line` | 2/2 |
| promptwright | `trigger-slim-cost-cue` | `fires` | 1/2 |
| scoutwright | `bench-verdict-rows` | `verdicts` | 2/2 |
| skillwright | `evals-trigger-noisy-gap-list` | `fires` | 2/2 |
| brandscribe | `no-definition-apply` | `offers-build` | 1/2 |
| commscribe | `first-run-setup` | `fires`, `mentions-emoji`, `names-defaults-file` | 2/2 |
| commscribe | `trigger-release-notes` | `fires` | 1/2 |
| lorescribe | `trigger-desert-names` | `fires` | 2/2 |
| researchscribe | `fanout-waits-for-yes` | `asks-yes` | 2/2 |
| gatewarden | `behaviour-ps-mirror` | `escapes` | 2/2 |
| keywarden | `behaviour-docker-store` | `names-only` | 2/2 |
| shieldwarden | `trigger-home-path` | `fires` | 1/2 |
| trustwarden | `pyc-hold` | `unread-named` | 1/2 |
| comfyrunner | `behaviour-untiled-decode-refusal` | `refuses` | 2/2 |
| dockerrunner | `prune-volumes` | `dry-list-first` | 2/2 |
| dockerrunner | `wslconfig-default` | `never-in-place` | 1/2 |
| duckrunner | `behaviour-no-shell-shows-sql` | `no-count-by-eye` | 1/2 |
| lmstudiorunner | `behaviour-unattended-no-check` | `refuses` | 2/2 |
| whisperrunner | `backend-failed-gpu` | `verdict-literal` | 2/2 |
| slicesmith | `behaviour-red-first` | `red-first` | 1/2 |
| uismith | `behaviour-direct-states` | `states-and-roles` | 2/2 |
| uismith | `behaviour-probe-overflow` | `skill-fired` | 1/2 |
| uismith | `trigger-pane-dark-theme` | `skill-fired` | 1/2 |

## Owed on a local machine

| Skill | Case | Failed graders (no shell) |
|---|---|---|
| gatewarden | `layout-behaviour-read-only` | `names-twice`, `ran-script` |
| gatewarden | `loads-behaviour-twice` | `names-twin`, `ran-script` |
| gatewarden | `map-behaviour-delete-biggest` | `measured`, `names-folder`, `owner-command` |
| gatewarden | `map-behaviour-treemap-local` | `names-alpha`, `ran-script`, `says-local` |
| shieldwarden | `signposts-behaviour-propose` | `names-hits`, `ran-script` |
| duckrunner | `behaviour-check-tracked-cache` | `names-file`, `ran-check` |

The NEEDS-LOCAL column in the per-skill table lists the live programs each runner drives.
Record each local result here, with the date, before the bump.

## Re-run

```bash
claude plugin eval packs/<pack> --runs 1 --ablation none --no-publish --trust-plugin -j 4
```

Add `--case <name>` for one case. On a machine with a shell sandbox, add
`--scaffold --allow-tools Bash` to run the 6 shell cases.
