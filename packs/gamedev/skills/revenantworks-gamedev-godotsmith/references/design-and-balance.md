# Design and balance — proving a simulation rule before and after it ships

Loaded by **Entry — Review** when the change is a game-design or balance rule (a new
mechanic, a fallback, a tuning target, a converter between resources), and by **Entry —
Gate** when a balance figure is a gate item. The rules here judge whether a design's claims
about its own rule are measured. Whether the game is *fun* stays a judgment gate the user
closes (`gate-doctrine.md` section 1); this file never rules on taste.

The sections build on `gate-doctrine.md` sections 6 and 7 (populations, attribution) and
`gdscript-invariants.md` section 7 (prose claims that are measurements). They do not repeat
those rules; they add what a design and its balance rows need on top.

## Contents

1. Units first
2. A design's headline claim is measured
3. Fallback rules: survival or grace
4. Arms a balance comparison must carry
5. Converters and end states
6. Levers, noise and the player's own plays
7. Controls, flags and fix rounds
8. Sim build prep

---

## 1. Units first

When abstract simulation units meet real ones (real-world terrain, a measured day length, a
physical speed), **the conversion is the design's first section**, not a detail. State it
as one recipe constant with its arithmetic and its undo ("1 game unit = 100 m, so a
4-unit cell is 400 m and the 480 x 320 raster is a 192 x 128 km box"), then derive every
later figure (the box, the tile list, the counts) from that one line, so a reviewer can
re-derive all of them from it. A design that brings in real data and finds no scale in the
repo invents one here, in the open.

## 2. A design's headline claim is measured

- **A survival or impossibility claim about a rule the design invents is measured even in
  a read-only unit.** "A camp with grain in the store cannot starve" is one probe, named in
  the brief. In one run a fifty-line probe showed such a rule moved extinction from day 14
  to day 49, not to never. The claim carries its horizon ("never, while Y lasts"), and the
  horizon is one of the measured figures.
- **A conservation claim across a rule re-shape is a measurement.** Converting a rule from
  seasonal lumps to daily accrual and claiming "the yearly total is unchanged" is checked by
  a short simulation before the test is written; the test is written from the measurement,
  not from the claim. One such claim was 5% off at 30 head.
- **"Tune X to range R so that Y" is swept.** The review sweeps X across R and reports the
  Y column. A target and the consequence drawn from it may never hold together at any
  setting; only the sweep shows it.
- **A figure measured on a world a later note killed is struck.** When a decision overrules
  a geometry or a rule, every figure measured on it is struck, including those used as
  targets elsewhere.
- **Strong words are grepped across sibling designs.** At a design's close, grep every
  sibling for *guarantee*, *always*, *never*, *every* and *only*, and read each against the
  mechanism's own sentence. The words drift between designs written a day apart.

## 3. Fallback rules: survival or grace

A fallback (an emergency ration, a rescue spawn, a catch-up bonus) is one of two shapes,
and the shape picks the trigger:

| Shape | Fires | For |
|---|---|---|
| **Survival** | early and often, on any shortfall | keeping a working system alive through a dip |
| **Grace** | late and loud, after a sustained failure | giving a dying system a last chance the player can see |

The same mechanism measured in both shapes can be harmful in one and inert in the other:
fired on every shortfall, one ration rule ate a full store and caused an extinction a
staffed camp would never have had; fired after three unfed days it was inert on a healthy
camp and still gave a dying one 170 more days. A design that adds a fallback **states which
shape it is**, picks the trigger to match, measures both shapes in the population spread,
and names the harmful one as the undo.

A review of a fallback says all four in its reply, in these words: the rule's shape by name
(**survival** or **grace**); the shape the design wants, and the trigger that follows; the
measurement owed before any tuning (both shapes, across the seed population, not one run);
and the undo (the harmful shape, named). A smaller amount is never the fix on its own. Until
that measurement exists the reply calls the rule neither fine nor broken: the cause is a
hypothesis, and the reply says what each measured outcome would mean.

## 4. Arms a balance comparison must carry

- **An unavailable arm for anything that unlocks.** A rule keyed to a building, a tech or
  any other unlockable gets a measurement arm where that thing is not available. Two
  options that tie on every gate can split once the building is locked: in one run the arm
  dropped one option below the base with three hunger deaths while the other held. Required
  whenever the game has, or plans, an unlock system.
- **Rules on, rules off, adopted later.** When adopting a thing has a cost and its rules
  have an effect, judge the rules on-versus-off and report the adoption cost separately
  (`gate-doctrine.md` section 7).
- **The population, not the pins.** A balance row is measured across the population the
  player can reach, with a census before a run of rows (`gate-doctrine.md` section 6).

## 5. Converters and end states

When a contract splits one resource into parts with a converter between them (raw and
kept, ore and ingot), **name the end states — all raw, all converted, empty — and test every
consumer at each.** Tests of the mixed state miss the lockout: a consumer that reads only one
part silently gets nothing once the converter has taken everything, and the failure reads as
scarcity, not a lockout. A consumer that reads one part only states in its doc comment what
it does when that part is zero.

## 6. Levers, noise and the player's own plays

- **Evaluate levers in pairs.** Two fixes can each harm some cases alone and meet the bar
  only together. When a design proposes more than one lever, measure each alone and the
  pair, and report all three.
- **Say when a bar sits inside the noise.** If near-identical variants swing a figure
  across the bar (one case moved between 15 and 21 heads on a trivial change), the bar is
  inside the noise: report the spread with the verdict and widen the population before
  ruling (`gate-doctrine.md` section 3 on thin passes).
- **"Could a player survive this?" is measured on a player's plays.** Before calling a
  gap a legibility problem, measure what the player actually did (the plays available and
  the ones taken), not what an ideal agent would do.

## 7. Controls, flags and fix rounds

- **Run the control before promising it.** A design that predicts a control will not move
  greps the control's own recipe for every function the change touches, or runs it at
  design time and writes "expected to move, because ..." (`gate-doctrine.md` section 7).
- **Measure the flag flipped before the flag-off rows land.** Control rows that ship a
  feature behind an off flag are cheap only if the feature works when the flag is on. Run
  the flag-on case once before landing the flag-off rows; in one run three flag-off rows
  landed first and the flip then killed every camp, because the design had only measured a
  different rule.
- **A fix round proves the fix, not only the defect.** Run the naive fix and the chosen
  fix side by side, with a trace of each; the chosen form is defensible only against the
  naive one it replaced (an oscillation the naive fix causes, for instance).

## 8. Sim build prep

- **Read calendar constants at the base.** Phase bounds, day length and season length are
  read from the base the brief lands on, never copied as literals from a design written for
  a later flip.
- **Ask whether each new save key is re-derivable.** Before adding a key, check whether
  (seed, id, day) or another saved value already determines it. A table with a "cheap
  option" column cut four candidate keys to one in one run (`determinism-and-state.md`).
- **Route tick-pinned tests on a shared function through one helper.** A later gate added
  to a shared function then breaks one helper, not every earlier test that pinned a tick.
