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
6. Editor-side claims with no window
7. A real render with no window

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
- **A bot that plays the game is part of the instrument** (observation 0617). Before a census
  bot's figure names a game fault or reaches the user, check one world's raw log against its
  table: a death in the log appears in the death column, a job count equals the people holding
  that job. In one build a job share counted babies, a column read the row's want instead of
  its holder, and a death column read 0 over 43 logged kills; two "game faults" and a design
  call rested on it. Report the bot as the suspect first.

## 6. Editor-side claims with no window

(Observation 0599.) A bug in a native editor panel needs neither a visible editor nor a real
mouse. A temporary `EditorPlugin` in a temp copy of the project, run with `--headless --editor`,
opens the resource with `EditorInterface.edit_resource`, finds private native classes by
`get_class()` and the input target by `get_signal_connection_list("gui_input")`, emits
`gui_input` with mouse events, and reads the inspector back
(`EditorInspector.get_edited_object()`, the `EditorProperty` count). Point the editor's settings
folder (APPDATA on Windows) at the temp folder, so the user's editor settings and project list
stay untouched. Limits: the dummy renderer draws nothing, emitted input skips real hit testing,
and a run on a build without the bug is a control, never a reproduction. Where the build can
show only the good state, a self-test flag forces the bad one, to prove the detector can report
it.

## 7. A real render with no window

(Observation 0608.) For visual work a headless run cannot judge (fog colour, stair-stepped far
edges), start Godot on a separate Windows desktop (`CreateDesktop`, then `STARTUPINFO.lpDesktop`
naming it): it renders real frames and opens no window on the user's screen. It does not prove
input focus or the player's real resolution. Observed on one Windows build machine.
