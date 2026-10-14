# Verdict measurement — judging a measured system

**Read this file when** a verdict compares options whose evidence is a measurement this run or
the user produced: a simulation's runs, a detector's alerts, a benchmark sweep, a before and
after on a tuning lever. Verdict mode only, read beside `verdict-mode.md` before its §2. A
verdict on products, plans or vendors never opens it.

Scope: verdicts **between options**. Whether one project's own measured figure may close that
project's own gate is the project's gate doctrine, not a verdict (in a Godot project, the
godotsmith skill's when installed). Timing and frame-rate method belongs there too.

## Rules

- **A detector is judged on two numbers, never one.** Hit lead time (how early it fires before
  the event) **and** its false-positive rate on the runs where the event never came (the
  surviving runs). A lead time with no false-positive rate is a detector that could be firing
  on everything.
- **Attribute an effect before crediting it.** Where a with/without comparison spreads, report
  the population, the stores or stock, and the demand **per period** for both arms, and say
  whether the effect acted directly or through the population (more agents doing the same
  thing). An effect that only moved the population is not the lever's effect.
- **Test levers in pairs.** Two candidate fixes are compared in the same runs, same seeds, same
  length, never each against its own baseline from a different day.
- **Say when a bar sits inside the noise.** Where the difference between two options is smaller
  than the spread between repeat runs of either, the measurement cannot separate them; the
  pick rests on the other criteria, and the confidence line says so.
- **Tabulate flow by source before choosing a fix.** Where the problem is a quantity that
  builds up or drains (resources, queue length, memory), tabulate where it comes from and where
  it goes, per source, before comparing fixes. A fix chosen before the flow table targets the
  loudest source, not the largest.

Every figure these rules produce is a derived figure: `verification.md` §6 governs how it ships.
