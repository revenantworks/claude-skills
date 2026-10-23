# Modes — one shared base, one throttle per mode

Loaded when a mode other than normal is on or about to start (SKILL.md — Load budget). SKILL.md
§3 carries PACE, the normal throttle, the unit-fit rule and the live gate; this file carries the
rest of each mode. Every figure here is a percentage or a ratio. A figure in tokens, units or CI
minutes comes from `plan-profiles.md`, never from this file.

## Contents

- The shared base
- Precedence
- Auto-mode switches
- The spend target (any mode)
- Pace
- Turbo
- Overnight
- Work day
- Owner-away
- Reset-eve
- Switches (reset-eve and turbo)
- Modes not yet defined
- Testing a mode

---

## The shared base

Every mode keeps all of these. A mode differs only in its throttle, so no mode loses a rule that
saves the meter (observation 0180):

1. **One tier table** — the fan-out's own (dispatchwright's `tier-routing.md`). A mode never
   carries its own tier choices. Without dispatchwright, the mode names no tier: pick each unit's
   tier with promptwright `model`, or by hand (the lowest tier that passes, effort raised before
   the tier).
2. **No rework.** A branch lands in the session that built it. Units write progress to disk. The
   controller stays idle while units run, so a human message never lands mid-turn and kills them.
3. **A small controller.** Read ledgers in slices; do lands and CI reads inline, not as extra
   units. **Auto-compact replaces the controller handover** (owner 2026-09-28, observation
   0210): no manual new session at a context line. Keep the ledger, the handover block and the
   pace log current at every event. After a compaction, re-read the handover block and the
   ledger before acting, and never re-launch a unit that is still running: background units
   and session crons survive a compaction. A new session is only for a crash, a restart or an
   owner request, and it starts with `dispatchwright resume` (without dispatchwright: the run's own
   resume file, after `git stash list` and `git reflog`).
   **Compact on purpose at a quiet point; auto-compact is the backstop** (owner 2026-10-01).
   Every controller turn re-reads the whole context, so a large context costs usage on every
   turn, not only at the limit. When no unit is running and a wave has just landed, write the
   ledger checkpoint and the open owner questions to disk, then run `/compact` (or ask the user
   to). Do not wait for auto-compact on a large window: it fires late, and can land in the
   middle of a land step. Never compact while a land or integrate is half done. A fresh session
   (with a handoffwright handoff) is for the end of a work block or a switch of repo or
   project, not for a context line.
4. **A design lead cap.** No new design while more than about one wave of designed builds waits.
5. **Skip the re-check round** when a review's findings are minor-only.
6. **Small briefs and short returns.**
7. **Measure on the harness count.** Rows landed per meter point, with a rework column. A unit's
   own token report is not evidence: one reported 145k where the harness counted 205k.
8. **Real work only** (owner rule 2026-10-06, observation 0347). In every fill or catch-up mode an
   eligible lane is a planned row whose blockers are clear. Spend pressure never creates a row:
   no extra review of code a later planned pass covers, no brief written early only because a
   lane is idle. When nothing real is unblocked, the check says "the gap stands until <row>
   lands" and launches nothing. Filler spends the allowance and still reports a success.

The costs that turbo showed were not parallelism (observation 0176): they were relaunches,
rebases, controller context and design built far ahead of the builds that need it. The base rules
above are the fix; a throttle alone does not remove them.

## Precedence

Hard stops (95% weekly, the stop band, identity and green-gate rules) > overnight, work-day and
owner-away conduct rules > reset-eve > pace > turbo > normal. A higher line always wins; a mode never lifts a
hard stop, with the one exception named under reset-eve's final 3 hours.

## Auto-mode switches

Three modes can start by themselves: **pace** (by the gap), **overnight** (by the clock) and
**reset-eve** (by the projected close). Each can be switched off (owner, 2026-10-23) in
`~/.dispatch/spend-modes.json`:

```json
{"schema": 1, "written_at": "2026-10-23T05:00:00Z", "auto": {"pace": true, "overnight": false, "reset-eve": true}}
```

- **The user is the one writer**: by hand, or through vigil's spend-mode switch (`/rw-vigil spend
  auto <mode> on|off`, or the button on its Spend mode tile). pacewright reads it at every check
  and never writes it.
- **A mode switched off is entered only on the user's word**, the way turbo is. The check that
  would have entered it says so in one line ("overnight is switched off; staying in normal") and
  runs the next mode down the precedence line.
- **A missing file, an unreadable file or a mode the file leaves out means on**: the shipped
  behaviour. The switch never lifts a hard stop or a conduct rule the user asked for by word.
- A mode already running when it is switched off ends at the next check.

## The spend target (any mode)

With `target_pct` by `target_at` in the budget file (the user's goal, observation 0350), every
2-hour check in every mode prints two figures: the **needed rate** = (target - reading) / hours
left to `target_at`, and the **lane count that meets it** = the needed rate / the mix's measured
points per lane-hour (`accounting.md`, Lane rates). Under the line, add lanes in reset-eve's
order — verifiable units first, then reviews, then briefs for queued rows — within the rig gate
(Turbo). **The rig gate always wins over the target**: a closed gate holds the lane, and the
check says which bound held it. **Never padding work** (base rule 8, the pace-lanes rule): when
no real row is unblocked, the check prints "the gap stands until <row> lands" and adds nothing.
A lane with no measured rate is named, not guessed.

## Pace

**On** when the gap is above PACE + 3, or on the user's word. **Off** when the gap is back within
3 of PACE for two checks in a row.

- **Burn budget:** %/h = 0.565 − gap ÷ hours to the weekly reset. (0.565 %/h is 95% spread over a
  168-hour week.) A negative result means no new spend until the next check.
- **Running budget, not stop-start.** Launch when the harness tokens spent since the last owner
  reading are under budget %/h × hours since that reading. A rule of "launch only if the gap shrank
  since the last check" fails every check while a unit runs, because a running unit grows the gap,
  and leaves budget unused.
- **One builder**, plus an optional small read-only unit.
- **A log line per check:** time, reading, PACE, gap, budget, spent since, launched or held, why.
- **Halt a launch** when the gap did not shrink by at least half of what the plan said since the
  last check, read across checks, not one.

## Turbo

**On only on the user's word**, for a stated period inside one waking work block. A plan, a ledger
line or a routine never turns it on, and it never runs into Overnight (the budget file cannot
expire past the next 22:00 user-local), unless the user explicitly orders turbo for the night
(Overnight, below).

**What turbo lifts: the spend throttle, nothing physical** (owner ruling 2026-10-20, observation
0470; it reverses the 2026-10-16 "no cap" ruling). The gap table (SKILL.md §3) is off and the
week's allowance may run to the stop bands. Turbo does not lift the base cap of 6 writer units,
and it never lifts a machine limit. What bounds turbo is the rig, the check queue and the land,
read fresh before every launch. A second breach of the same machine limit (0446, then 2026-10-19)
made this a gate in code, not a sentence.

**Entry, one question once:** "Rig-aware turbo (pick), or a lower number?" The answer goes into the
budget file through the writer: `--mode turbo --ttl 2h` (rig-aware; entering turbo this way drops
a number kept from an earlier file) or `--parallel <n>` with n <= 6, which the ledger guard then
holds as written. There is no "no cap" answer: the writer refuses `--parallel none` and a turbo
number above 6. An unattended start takes the
pick. A later answer from the user replaces it; it is not asked again at each check.

**Every launch passes four launch gates:**
1. **Real work only**: a planned row on the path to a landed row — builds of designed rows first,
   then their checks, then designs under the lead cap (base rule 8; spend pressure never creates
   a row).
2. Its file set does not overlap a running writer's (one writer per repo or worktree).
3. It can land in this session, measured: unlanded WIP under its limit (the rig gate, below).
4. Its tier comes from the shared table.

**The rig gate.** Every heavy launch in turbo passes `rig_gate` (dispatchwright
`scripts/rig_gate.py`, called by the ledger guard inside a 6-second budget; register the guard with
a hook timeout of 10 s or more, since a killed hook does not block). It reads, in one call: the
slot registry, every headless engine and suite process on the machine, the check queue, the land
flag and land verdict, the base's status and the run's verified unlanded branches. A run-tool
signal it cannot read is reported "not measured", never a crash. A process listing that fails,
exits non-zero, times out or comes back empty is "not measured" too, never a measured 0, and a
heavy launch with neither the listing nor the CPU sample measured is refused. **Without
dispatchwright's rig gate or its ledger guard** (pacewright alone), apply the bounds table below by
hand before each heavy launch and state "rig gate: by hand" in the check line. It refuses a launch,
naming the bound, when any of these fails:

| bound | value (default; key in `~/.dispatch/rig-gate.json`) | counts |
|---|---|---|
| writer units | <= 6 open writer rows (base cap; in the ledger guard, every mode) | a row is open until its check verdict exists (`checking` counts) |
| all units | <= 12, writers included (the ledger guard, in a turbo file the writer stamped) | read-only design, briefs, docs, research, reviews that run no local suite |
| busy engines | busy <= B - 2 for a heavy launch, B = the rig budget (`rig_budget`, default physical cores + 2: 10 on 8 cores / 16 threads) | every headless engine or suite process on the machine, counted as the process that is the engine (a slot waiter, a shell or a `timeout` wrapper is none; a waiting slot never counts; the slot registry's running count is a floor), leaf engines only: an engine with an engine below it (ci_local over its Godot shards) counts none itself, the engines under it one each, and a headless Godot always counts, so a 6-shard walk is 6, + 2 while the self-hosted runner has a job, + the container shards no host process shows (`extra_busy_file`) |
| CPU | under 85% for a heavy launch (`cpu_max_pct`), over a 3-second sample | machine-wide |
| check-queue wait | expected queue wait <= H = 45 min (`queue_horizon_min`) for a writer whose work ends in a check | (expected seconds of queued checks + half of each running one, a running check counted once) / check lanes |
| land state | no writer launch while a land walk runs, or while the land, a branch CI run or main is red | the land flag, the land verdict, the nightly status file; a row noting `fixer-of: <land>` is that red's fixer and passes the red bound (a land walk still holds it) |
| unlanded WIP | < 6 verified branches not on origin/main (`wip_limit`) for a build | verified = the branch tip carries a GREEN, current queue verdict, or the branch is named in `wip.verified_file`; any branch name; a running unit's branch, an abandoned or a red one is not counted. At the limit the next launch is a join or a land (a row noting `kind: join` or `kind: land`), never a build |
| top tier | closed unless the stamped file says `top_tier_open: true` with the user's quoted word and the row's notes say `owner-called` | `fable-*` agent types, in every mode |

A heavy launch is a unit that will run a local suite, build, render, measure or engine run (a
ledger `lane` cell says `heavy` or `light`; without it a writer row is heavy). A light launch passes
only the writer, all-units and top-tier bounds. An escalation is a launch and passes the gate. A
unit stalled behind a closed gate is not a failure: it frees its slot and requeues; only a
verifiable failed check escalates (dispatchwright §7). A check that timed out on a loaded rig is
`TIMEOUT`: it requeues and never counts toward the escalation rule. In turbo every ledger row
carries a numeric token estimate, so the 2x-estimate stop has a number to compare.

**The older machine limits still hold; the stricter wins.** The derived heavy-lane cap — floor(logical
threads ÷ threads per heavy lane), at least 1, threads per heavy lane from one measured heavy run
(overlay key `turbo.heavy_lane_threads`, `accounting.md`; until measured, one heavy lane per 5
logical threads: 3 on 16 threads) — and the machine-wide suite ceiling: a suite starts below 2
running, or under the cap (default 4, `~/.dispatch/suite-cap.json`) while the CPU is under its
target (default 75%). A wrapper and the suite it starts share one slot; separate suites each
count. Every background suite starts at below-normal priority with no window, through
dispatchwright's `scripts/suite_slot.py` where installed, and logs to `~/.dispatch/suite-perf.jsonl`.

**Stop launching** (light lanes may continue unless the line says otherwise) when any of these holds:
busy engines over B - 2; queue wait over H; a land walk running; a land, branch CI or main red (only its
fixer and light lanes); WIP at the limit; the 5-hour window at 85% or more, or any stop band (the
slow and stop bands default to 80% and 95%, both windows, and the 95% weekly stop: all launches);
the clock past the file's expiry or inside Overnight without the user's night order (all
launches); an owner stop (all launches). Never message running units with a new cap or flag. The
slot runner and the queue own the CPU; read them first (observation 0462).

**Checks** every 2 hours and at every land, one log line: rows landed since the last check, busy
engines / B, queue wait / H, WIP, land state, the 5-hour and weekly readings, and with a spend
target the needed rate and its lane count (The spend target, above). **Renewal is a check**: the
writer renews turbo only with `--landed <n>` and a reading under 15 minutes old, at a TTL of 2 h at
most. **Drops to normal** after two checks in a row with 0 rows landed (the writer does it), with
queue wait over 2 x H, or below the baseline rate (rows landed per meter point; the first measured
figure was 0.21, from one turbo day — a local overlay replaces it with the environment's own).
**Ends** at PACE + 15, at the end of the stated period, at the Overnight start (unless the user
ordered a turbo night), or on the user's word.

**Lands go first and in batches.** The land walk takes the reserved long slot, ahead of any row's
suite, and is never queued behind row suites. Finished, reviewed rows wait and merge in batches,
so one land run (and one CI run) covers several rows; lands stay serial. While a branch CI run is
in flight on the rig's own runner, check lanes drop to 4 and no writer whose check would join the
queue launches.

## Overnight

**On by clock**, 22:00–09:00 in the user's time zone. An owner message at night is answered and
does not end the mode.

**Entry is a gate, not a label** (observation 0340). An unattended mode is only as good as its
least-allowed command. Before the user leaves:

- Every command form the queued units will run is on the allow list. The briefs carry fixed
  command strings, and the controller lists them for the user to check. A command form held by
  an `ask` rule stops the whole session on a prompt nobody answers; one unit sat about 9 hours on
  a single in-place `sed` edit that way.
- Liveness is watched from something that prompt cannot block: a scheduled cloud check, or a
  monitor on each unit's journal or worktree modification time that reports a unit silent for one
  interval. A session cron that needs an idle prompt logged nothing for that whole night.

- The throttle is picked from the gap, **never turbo** — unless the user explicitly orders turbo
  for the night (the writer records their words: `--night-order "<quote>"`). Turbo then runs
  under the rig gate and its 2-hour checks, the renewals are the controller's, and Overnight's
  conduct holds: no questions, defaults taken, a morning file, a morning report.
- **No questions, and never a blocking question tool** (observation 0348). Launch every
  launchable row first; each question then goes to a morning file with a recommended answer, and
  only the rows that depend on it wait. A reversible fork takes the default; an irreversible one
  parks that row. One interactive question asked at night stalled a whole chain about 5 hours.
  "Ask interactively when the user has time" applies only while the user is present.
- The controller acts only on events, in the fewest calls. Auto-compact carries it through the
  night (base rule 3); no new session until morning.
- **Morning report:** rows landed, spend, gap, the questions and their recommended answers.

## Work day

The user is around but busy. Between check-ins the run behaves as Overnight; at set times the
controller checks in with the user. **On** at the user's word ("work day", "check in with me at
lunch and 5"), never by clock alone.

- **Between check-ins, Overnight's conduct holds.** The same entry gate (every queued command form
  on the allow list; liveness watched from outside the session), because the gaps between
  check-ins are hours long. **No blocking question tool** (observation 0348): launch every
  launchable row first; each question goes to the day's **check-in file** with a recommended
  answer, stamped from the clock in the writing command (observation 0343), and only the rows that
  depend on it wait. A reversible fork takes the recommended default and records it there; an
  irreversible one parks that row until the next check-in. Work never pauses for a question.
- **The throttle** comes from the gap. Turbo only on the user's word, as in every mode.
- **Check-ins** at the user's local times, default **12:00 and 17:00**. Launch every launchable
  row first, then present, in order:
  1. The queued questions, one at a time with the question tool, the recommended answer first.
  2. Owner tasks: steps only the user can do, one runnable command each.
  3. Status in three lines: landed, running, spend against PACE.

  Running units keep running through the check-in; nothing pauses for it. An unanswered question
  rolls to the next check-in; after the day's last check-in it rolls to the morning file.
- **Waking at a check-in:** a session cron at each check-in time, the controller's first event
  after that time, whichever comes first, and a push notification where the surface has one.
  **Its limit:** a session cron fires only at an idle prompt (observation 0340), so a check-in can
  arrive late; the next event then runs it.
- **A user message mid-day** is answered and does not end the mode. "Ask me now" runs a check-in
  at once.
- **Ends** on the user's word, at the optional end time, or by handing over to Overnight at its
  start; open questions then move to the morning file.

**Config** lives in the local overlay, `.dispatch/local.yaml` (`accounting.md`), as owner keys.
The default needs no entry; to change it, edit the values:

```yaml
entries:
  - key: workday.checkins
    value: ["12:00", "17:00"]   # user-local HH:MM; the default
    source: owner
  - key: workday.end            # optional; absent = until Overnight starts
    value: "18:00"
    source: owner
```

Times said in the session ("check in at 11:30 and 16:00") are an owner ruling for that day and
beat the overlay. A value not in `HH:MM` is ignored and reported, and the default stands.

## Owner-away

Overnight for several days. **On** at "away until X", or after 12 waking hours with no owner
message.

- A **daily digest** in place of the morning report.
- **No design rounds.** No top-tier unit except an escalation.
- Maintenance only when no decision-free row is left.
- **Its limit:** it lasts only as long as the controller session. A true multi-day controller is
  fresh scheduled sessions that read the ledger, act and exit — agentwright's wrapper.

## Reset-eve

Spend the allowance that a weekly reset would otherwise throw away, on high-value queued work.
**A spend target is a rate problem, not a deadline problem** (observation 0345). Reset-eve is on
from the first reading where the **projected close** misses the target: weekly % + measured burn
per hour × hours to the reset < target. It is not defined by hours to the reset: one controller
treated "the final 3-4 hours" as not yet applying at 32 hours out, while the arithmetic already
showed a shortfall, and ran light twice. Without a measured burn, it is on from 36 hours before
the reset when all-models is under 85%.

- **Target** 93% by default, or the user's `target_pct` by `target_at` in the budget file
  (observation 0350); the need is then (target − reading) ÷ hours to `target_at`, and PACE is not
  the yardstick. Dispatch stops at 95%; **never credits**.
- **Under pace is a deficit, never "fine".** Every reset-eve check prints the needed rate and the
  lane count that meets it (lanes = needed points per hour ÷ the mix's measured rate per lane,
  `accounting.md`, Lane rates). A check that reads "pace is fine" while points under pace is the
  failure this mode exists to catch.
- **The budget file's parallel ceiling defaults to the wave cap on reset eve**, never a
  conservative 3; a lower ceiling names its reason (a writer limit, the 5-hour window binding).
- **Order:** verifiable units first, then reviews, then designs under the lead cap.
- **The top model only in the last 12 hours.** The cheaper tier goes first; the top model gets
  only the room the cheaper lanes cannot spend before the reset (room left − lane capacity × hours
  left). A top-model unit must be expected to finish at least 1 hour before the reset. Fill spare
  allowance with the tier that does the most work per point; the expensive tier takes the leftover
  that would otherwise be lost.
- **The final 3 hours aim at 100%.** The unit-fit factor becomes 1.0 and the 95% stop is lifted
  for this stage only. Cheap-to-lose work goes first (verifiers, reviews, research, small builds).
  About 1% is kept back for the controller to reconcile. Anything unlanded lands after the reset.
- **The reset is exact to the minute, and the last check is one minute before it** (owner rule
  2026-10-01, observation 0281; a reading at the reset minute showed every weekly meter at 0%).
  The last usage check and the last launch decision fall at reset − 1 minute, not 20 to 40
  minutes earlier. A cut-tolerant unit that saves as it goes may run to the reset; only a unit
  that must land a commit keeps a finish margin. In the final hour, pace checks run every 10 to
  15 minutes.

**Capacity against room** (observations 0253, 0279). A target the lanes cannot reach is a gap
found too late. At every reset-eve checkpoint — window entry, the top model's window opening,
the final window opening, and every check inside the final window — compute:

- **Room** = target − weekly %, in points, and the hours left to the last launch.
- **Capacity** = the lanes' measured points per hour: writers (one per repo) × each unit's burn
  rate, plus the read-only lanes. Burn rates come from the pace log or the calibration, in
  harness tokens; a lane with no measured rate is named, not guessed.
- **If capacity < room**, say so at that checkpoint, not hours later, and plan the extra lanes
  before the window opens: parallel non-writer work that still advances the end goal (brief and
  design checks for rows ahead, verifiers, research, another project's queue). Never filler.
- **In the final window, size the lane count to the room:** lanes needed = room points ÷ hours
  left ÷ the mix's measured points per lane-hour (`accounting.md`, Lane rates; never one
  constant: an Opus build lane and a Fable lane differ several times over). Launch that many cut-tolerant lanes at
  once, re-compute at each check, and add lanes whenever the projected close is under the aim. One
  measured eve closed at 98% against 100% while launching one to four lanes of about 0.1 point
  each into about 2 points of room.
- **A pace-log row whose gap is negative carries the launch count that closes it**, or says why
  it cannot (no unit cut-tolerant, a lane rate unmeasured, the 5-hour window binding).

Facts behind it (observation 0180, from the provider's documentation): nothing rolls over; the
top model's usage counts toward the all-models meter too; at a weekly limit, background and
headless runs stop with no model fallback; credits are opt-in.

## Switches (reset-eve and turbo)

- `weekly` — spend toward the target.
- `top` — top-model work, one unit at a time; closes at all-models 90%; needs a top-model reading
  under 2 hours old (it comes only from `/usage` or the user — the statusline has no per-model
  field), and opens only on the user's quoted word (`--top-open --owner-word "<quote>"`; the
  ledger guard refuses a `fable-*` launch without it and an `owner-called` row).
- `5h` — keep each 5-hour window busy within the unit-fit rule; stop at 90%.

## Modes not yet defined

Named so they are not re-invented ad hoc (observation 0180): **recovery** (a red base or the CI
runner down: one fixer, nothing else lands — a fan-out's rule, applied by dispatchwright),
**playtest** (main frozen, branches only), **deadline sprint** (turbo with a dated target),
**maintenance** (checks only). Each needs a pass line before it is used.

## Testing a mode

Every mode is judged on one scoreboard (`accounting.md`): rows per point, gap against plan,
rework share, first-pass rate, controller calls per event, idle hours. The pass line is fixed
before the test, and a verdict needs three or more meter readings.
