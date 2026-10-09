# Sources — revenantworks-foundation-pacewright

Last verified: 2026-09-28 (the parity register below; upkeep reads this stamp, 90-day cadence).

## Parity register (dated 2026-09-28; 90-day cadence)

The incumbents that do part of this skill's job, and where it stands against each. The pages were
fetched on 2026-09-26 for the dispatchwright audit that proposed this split; this register was
compiled from that audit on 2026-09-28 without a second fetch. Re-check them before claiming a
capability no incumbent has.

| Incumbent | Licence / state 2026-09-26 | Covers | Verdict |
|---|---|---|---|
| **B** [pmcbride/claude-cost-control](https://github.com/pmcbride/claude-cost-control) | Public repo; hooks with a self-test | PreToolUse hooks on agent launch escalate at 70/80/90/94% of the 5-hour window, blocking new spawns at 80%; reads the native rate-limit fields; fails open on stale state | The live-gate incumbent. Its bands informed the slow and stop bands (§3). It has no plan-time fit, no weekly pacing, no modes and no reconcile of readings against spend |
| [boyand/cc-budget](https://github.com/boyand/cc-budget) | MIT | A pacing marker for the 5-hour, 7-day and per-model windows; warns only, never blocks | Idea source for the PACE line against the weekly window. No fit, no throttle, no leak check |
| [leaflessbranch/cc-pacekeeper](https://github.com/leaflessbranch/cc-pacekeeper) | v0.9.0, read 2026-10-01 | Live meters handed to Claude by hooks; a budget contract per subagent; a dispatch advisory; checkpoint plus wake cron at 85% of the block; cross-session awareness; weekly model-family nudge | The nearest rival (found 2026-10-01). No plan-time fit, no modes, no reconcile of readings against spend, no model admission |
| [Gui-Gou/claude-statusline-burnrate](https://github.com/Gui-Gou/claude-statusline-burnrate) | read 2026-10-01 | Statusline weekly-limit math: today's share and sustainable burn | A display; idea source for a burn-rate line |
| [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams) | First-party, experimental | Per-teammate model; teammates inherit the lead's effort | Context only: a runtime with no usage pacing of its own. A fan-out on it still reads the budget decision file |
| The official `session-report` plugin and the community `receipts` tool (URLs not re-fetched) | Not read 2026-10-08; idea only | A spend report per session from the harness's local transcripts | Idea source for `spend` (accounting.md — Spend by skill, subagent and prompt), restated in our own words: attribution by skill, subagent and starting prompt, counts only, cache reads apart. Neither is installed or required |
| [Claude Code statusline](https://code.claude.com/docs/en/statusline.md) | First-party docs | The statusline command receives the session's rate-limit windows | The only source of the meter file (`~/.claude/usage-windows.json`); where it is installed is rigwright's placement |

**Margin held on 2026-10-01** (re-scanned live by unit PR): a plan-time fit into the 5-hour and
weekly windows with measured percent-to-token calibration before anything launches; spend modes
that share one base and differ only in their throttle; a reconcile of each meter reading against
known spend, with a brake on unexplained points; model admission by a measured baseline; and
every plan number held as data in one profile.

**Owed:** none of these margins has a passing run yet (evals/RESULTS.md). A margin claim becomes
evidence only when its case is run.

Injection check, 2026-09-28: no fetched page addressed an agent reader. None of their text is
copied here; practices are restated in this skill's own words.

## Internal sources

The doctrine comes from the task-observer log of one owner's long multi-agent runs. The
observation ids are provenance, not names.

| Observations | Applies to |
|---|---|
| #0156 | §3 live gate |
| #0171, #0175, #0176, #0180 | §3 and `references/modes.md` — the shared base, pace, turbo, overnight, reset-eve |
| #0184 | `references/accounting.md` — model baselines |
| #0185 | `references/accounting.md` — CI minutes |
| #0186 | §4 and `references/accounting.md` — the UBA |
| #0187 | §6 and `references/accounting.md` — the overlay, first-run calibration, the dashboard |
| #0188 | `references/accounting.md` — portfolio shares |
| #0189 | §1 and §5 — the split and the data-file seam |

`references/window-fit.md` was first written inside dispatchwright at 1.3.0 (2026-09-17) and moved
here at 1.0.0; its history is in dispatchwright's CHANGELOG.

**Unsourced by design.** The mode thresholds (PACE + 3, + 10, + 15), the 0.8 unit-fit factor,
the 15-minute freshness line and the UBA trigger levels are policy authored from those runs, not
drawn from a published standard. The plan-profile figures are the provider's and are re-verified
by `pacewright refresh`.
