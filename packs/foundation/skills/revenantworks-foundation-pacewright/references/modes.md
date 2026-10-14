# Modes — one shared base, one throttle per mode

Loaded when a mode other than normal is on or about to start (SKILL.md — Load budget). SKILL.md
§3 carries PACE, the normal throttle, the unit-fit rule and the live gate; this file carries the
rest of each mode. Every figure here is a percentage or a ratio. A figure in tokens, units or CI
minutes comes from `plan-profiles.md`, never from this file.

## Contents

- The shared base
- Precedence
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

**On only on the user's word**, for a stated period. A plan, a ledger line or a routine never
turns it on.

- Up to **5 units**, each passing four **launch gates**:
  1. It is on the path to a landed row — builds of designed rows first, then their checks, then
     designs under the lead cap.
  2. Its file set does not overlap a running writer's.
  3. It can land in this session.
  4. Its tier comes from the shared table.
- **No launch** while the 5-hour window is at 85% or more.
- **Ends** at PACE + 15, at the end of the stated period, or on the user's word.
- **Drops to normal** after two checks in a row below the baseline rate (rows landed per meter
  point; the first measured figure was 0.21, from one turbo day — a local overlay replaces it with
  the environment's own).

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

- The throttle is picked from the gap, **never turbo**.
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
  field).
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
