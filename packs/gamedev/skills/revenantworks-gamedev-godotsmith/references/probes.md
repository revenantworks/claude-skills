# Probes — a headless script written to answer one question

Loaded by **Entry — Check** and **Entry — Gate** when a figure has to be taken with a
probe (a throwaway headless script) rather than read off the suite, and by **Entry —
Review** when a probe's output is the evidence for a finding. A probe that answers the
wrong question looks exactly like one that answers the right one; these conventions make
the difference visible in its output.

## Contents

1. Say why, per entity
2. Count where the thing happens
3. Print what actually ran
4. Pin every input to a rate
5. Name, then cross-check

---

## 1. Say why, per entity

- **A reason line per building (or per actor).** When a probe reports that a thing did not
  happen, print one line per candidate saying why: `hut#3 idle: no builder in range`. A
  total ("2 of 5 built") hides which rule stopped the other three.
- **A per-tick task tally.** When the question is where the time or the people went, tally
  task kinds per tick and print the table. A day-end summary averages away the hour that
  matters.

## 2. Count where the thing happens

**Count at the producing call, never by differencing a store.** "Food made" measured as
store(end) − store(start) nets out everything eaten, spoiled and carried in between, and
reports a flow nobody can attribute. Increment a probe counter at the call that produces
the good, and a second at each call that consumes it.

## 3. Print what actually ran

**Print the effective flags from the patched class.** A probe that switches a rule off
(a monkey-patched constant, an overridden method, a test-only flag) prints the values the
class under test actually holds at run time, read from that class, in the probe's header.
A probe that set a flag on the wrong object runs the unchanged game and reports it as the
changed one.

## 4. Pin every input to a rate

A rate (heads per year, food per day, ms per tick) depends on every input the simulation
reads. **Pin each one, and name the pinned inputs in the probe header**: seed, start
recipe, day count, speed factor, any toggles. An input left to its default moves when a
later row changes the default, and the probe then answers a different question with the
same name.

## 5. Name, then cross-check

- **Index an enum by name, never by position.** `Kind.STOREHOUSE`, not `3`. A position
  moves when a member is added in the middle, and the probe silently reads a neighbour.
- **Cross-check one number another way.** Before trusting a probe's table, compute one of
  its figures by a second route (a head count from the roster and from births minus
  deaths, a store total from the ledger and from the store). Agreement is cheap evidence
  the probe reads what it says; disagreement is a probe bug found before anyone acts on it.
