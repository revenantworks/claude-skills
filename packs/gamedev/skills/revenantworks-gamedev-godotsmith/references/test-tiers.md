# Test tiers — build fast, test hard at the checkpoints

Loaded when a suite or a CI run is too slow to run on every change, when choosing which tests a
change runs, or when adding a short-run mode to a long test. The proof laws do not relax here:
the tiers decide **when** each proof runs, never **whether** it runs. Nothing lands without the
full gate green.

The figures below come from one simulation game's fix round (Godot 4, GUT, keep-neutral switch
rows, two CI platforms). The shapes are generic; the numbers are that project's.

## Contents

1. Measure where the time goes first
2. The three tiers
3. A short-run horizon for long trajectory tests
4. Selecting the tests a change runs
5. The budget covers the whole plan
6. One run per tree
7. A short-run mode is refused by every gate tool
8. Gate cost: rows that prove nothing of their own
9. Retiring a switch

---

## 1. Measure where the time goes first

Before cutting anything, build a duration table from the last full run: serial seconds per test
script, and per row for any script whose rows are long. Keep one table per CI platform.

- **The cheap lever is wherever the table points**, never where a feeling points. In the worked
  project one file's switch off-rows were 80% of an 11-hour serial suite; the other 166 scripts
  together were 14%. Trimming the fast scripts would have saved minutes.
- **Learn per-test seconds for every script**, not only for the ones a sharder splits. Without
  them a second pass can only estimate from the code.
- **A figure from a loaded rig is an estimate.** One script read 824 s on one day and 329 s on
  another. Label which figures are measured, which recorded, and which estimated.

## 2. The three tiers

The cause of a slow per-change check is usually a whole-stack proof running at every merge. A
proof about the whole stack belongs at a checkpoint. A build check only has to show that the
change is sound and that its own switch is neutral.

| Tier | When | What runs | Target |
|---|---|---|---|
| **T1 build** | each unit or change, before it is handed back | lint, import, guards, harnesses; the scripts the change edits plus the scripts that read a symbol it changed (budgeted, section 5); the base trajectory rows **to the short horizon**; the off-row of each switch the diff adds or edits, to the short horizon | ~15 min |
| **T2 join** | each merge of a wave, **on the merged head** | T1 over the merged diff; every script except the long trajectory file; the base rows to the full horizon; every row of each switch the wave added or edited; the re-pin proof; budget 0, nothing dropped; jobs = the rig's free cores | ~45 min |
| **T3 gate** | a playtest point, a milestone, a land | the full walk on every CI platform, every row to the full horizon; CI itself | unattended, while the person plays the last preview or overnight |

The loop: units build and pass T1 → the join runs T2 and cuts a preview → the person plays while
T3 runs → the notes and any T3 reds become the next round's rows → build fast again.

**What it costs, said out loud:** a late divergence of a switch the diff did not touch is found
at T3, not at the merge. Pins taken on named days (a mid-run fingerprint and an end fingerprint)
keep that cheap: a T3 red still names the switch and the day. Land rules do not change.

## 3. A short-run horizon for long trajectory tests

A long trajectory test (a seed run for 120 days, compared with pinned hashes) gains a checkpoint
pin partway through, and one switch (an environment variable or a flag) cuts the run there.

- **Unset means the full run.** CI and every gate leave it unset. Accept exactly three values —
  unset, the full horizon, the short one. Anything else fails every horizon row, never skips.
- **A pin past the cut reports "late", never "pass".** The run prints one line saying which
  asserts it left to the gate (`horizon 30: day-120 asserts left to the gate`).
- **Red first, three ways:** at the short horizon the engine stops at the checkpoint (assert the
  tick or day count); a wrong checkpoint pin still fails (the positive control); unset still
  reaches the end.
- **A bar decided before the checkpoint runs at the short horizon too.** A bar folded into a
  row's late block was skipped at T1 although its values were final by day 15.
- **Check the checkpoint is a live state.** A checkpoint pin taken after the run has frozen (a
  camp extinct by day 18) proves nothing; `ci-guards.md` section 4, pins over a dead state.

Measured in the worked project: eight rows went from 1,398 s to 271 s (5.2x). The state at the
cut was byte-equal to the full run's state on that day.

## 4. Selecting the tests a change runs

**Selection by file name misses tests that read a changed symbol.** Three instances in three
waves, each green in every unit's own check and red only on the merged head:

- a radius constant doubled; another feature's test had copied the old value into a literal;
- a notice gained a queue; another feature's test read the notice field right after a save;
- the tick length changed; a test of an old screen counted ticks at the old rate.

So T1 selects by symbol as well as by file:

- for each `func`, `const`, `var`, `static var` or `signal` whose definition or body a hunk
  touches, and each of the file's own members a touched function writes (an assignment, or a
  mutating call such as `push_back` or `set_text`), add every test script that reads it: `.name`,
  `name(`, a quoted name as the first argument of `call`, `get`, `has_method` or `connect`, and a
  signal's quoted name anywhere (an emit-count assert);
- a symbol named by a large share of the scripts (about a fifth) is a hub: it maps nothing on its
  own name, maps by its `Class.name` form where that is specific, and is noted as left to T2;
- over-selection is the safe direction; a misjoin that selects too much costs time, never proof.

**A test that copies a constant's value instead of reading it is a hidden dependency.** Read the
constant. A lint row can flag numeric literals in tests that equal a changed constant's old value.

**Run one check on the merged head before calling a wave green.** "Green alone" was true for each
unit and still hid every one of the three reds. The merged-head check is what caught them; T2 is
that check.

State what selection cannot see: a guard on a switch edited outside its declaring file, the
transitive callers of a hub class, static leaks between rows that share a process. Each is a T2 or
T3 item, and the plan prints it.

## 5. The budget covers the whole plan

- **One budget over the whole plan's estimate**, never over one step. A budget on one step left
  an edit to a hub file selecting nearly every off-row: 4.9 hours planned for a 15-minute tier.
- **Never dropped:** lint, import, guards, harnesses, the base rows, the edited switches' rows,
  and the scripts the change itself edits. Over the budget they run anyway, with a note naming
  them.
- **Fill the droppable classes strictly by priority** (named scripts, then symbol readers most
  specific first, then the rest, cheapest first inside a class). The first job that does not fit
  is dropped with every job after it, so a lower class never takes an edited script's room.
- **Every dropped job is printed** as "left to T2/T3" with its estimate, and the verdict line
  carries the count: `FAST TIER (build) GREEN; 12 jobs left to T2/T3 (est 2,300 s serial)`. A gap
  named only in the plan print is a gap nobody quotes.
- **The join's budget is 0.** Everything runs.
- **Price a step through the runner's lane limits**, not total seconds divided by jobs: a lane
  capped at two long jobs per worktree makes ten 600-s jobs take 3,000 s on four slots, not 1,500.
- **A step with no jobs where jobs are expected is NOT RUN**, never green. Five renamed base rows
  must not make the trajectory step read "nothing to run".
- **Count literals move at the join.** T1 may be lenient on exact literals (the join syncs them),
  but stays red below the floor. A unit that cuts tests on purpose stays red on that one guard
  until the join lowers the floor; its brief states that expected red.

## 6. One run per tree

A tool that only reads the tree can still write per-tree state: logs, job files, caches. Two
copies on one worktree in the worked project deleted each other's finished job logs, then crashed
on a locked file.

- **The barrier belongs in the tool**, not in the caller's memory: a lock file in the git dir
  holding the pid and start time; a second run exits with "held by pid N since T"; a dead or
  reused pid's lock is taken over inside an OS-level lock, and the lock file is written whole
  (temp file, then link or rename) so no reader sees half of it.
- **Per-run file names** (`job-<pid>-<k>`), and a run removes only a dead run's files, never a
  live one's.
- **Map every OS error in the lock path to "held"**, not a traceback: on Windows a remove during
  another process's read raises a sharing violation, and a traceback reads as RED, not NOT RUN.

## 7. A short-run mode is refused by every gate tool

A switch that makes a check cheaper by checking less is safe only where it is asked for. In the
worked project the build tool set the horizon variable for its own jobs and cleared it from its
parent shell. The re-pin tool, the nightly gate, the bisect tool and the local CI walk all built
their children's environment from the inherited one and had never heard of it. A shell left with
it set would have run a re-pin or a nightly to day 30, compared nothing at day 120, and reported
green.

- **Every tool that gives a gate verdict refuses the variable when it is set**: it exits before
  any run, names the variable, and says to unset it. Its verdict line names the mode it ran in.
- **Find every launcher**: grep the tools for an environment copied into a child process (in
  Python, `os.environ` near the engine's launch line), and give each one a line in the change:
  sets it, clears it, or refuses it.
- **Test each refusal three ways:** set, it exits before any run (the stubbed runner is never
  called); unset and the full value, it takes its normal path (the positive control); the variable
  never reaches a child's environment.
- **Every documented entry point counts.** A review found the old local CI walk, still printed as
  the land command in the run's resume notes, unguarded. Guard it or retire it and fix the doc.

## 8. Gate cost: rows that prove nothing of their own

Ask of each long row: **what does it assert that no other row asserts, on what setup?** In a
deterministic run with statics reset between rows, two rows with the same switch set, the same
seeds (or a subset) and the same pin table are one row run twice.

- **A rewire onto a shared fixture can make rows duplicates.** At each join of the worked
  project, older per-switch off-rows were re-pointed at the new stack helper and its table and
  kept. 56 of 95 rows became exact subsets of a stack row: 45% of the serial suite. Each rewire was
  a correct local edit. The join that makes a row's setup equal another row's deletes the row in
  the same commit and names the row that now covers it.
- **Guard it, structurally:** a check over the test file fails when two rows call the same setup
  helpers with no extra switch or seed and read the same table.
- **The merge classes:**
  - *merge* into an existing row with the same setup (delete the subset row);
  - *merge into one stacked row* several dedicated switches whose off arm no recipe reaches.
    Measure first; a key that moves gives that switch its own row back, with its old asserts.
    Red first against the wrong table;
  - *one seed* where the switch writes state nothing in the run reads. Prove it: the switch's
    table differs from its neighbour's only in the hash keys;
  - *fold* two tests that assert the same bars on the same result into one;
  - *split* one long test per case, so the sharder packs it: no serial saving, a shorter critical
    path (824 s became about 275 s).
- **Say what a merge loses:** the switch's own name in a failure line. Diagnosis then takes a
  bisect tool or one throwaway per-switch run. It loses no computation and no assert.
- **Point readers at the original** when two pin tables are byte copies; delete the copy.
- **Rank rows by serial seconds per unique assert** at each milestone, so the pile cannot grow
  silently between audits.

Worked result: no assert, bar or positive control lost; the two-platform walk sharing eight slots
went from about 141 to about 52 minutes.

## 9. Retiring a switch

A switch's off arm, its pin table and its off-row can go once the feature is accepted. Accepted is
a recorded ruling, never "played in a build".

- **Retire by stack boundary.** A switch inside a stack can only go with every pin table older
  than its join: retiring one makes those tables impossible to reproduce.
- **Before the retirement lands, list two things:**
  1. every **other** switch whose rows the retirement drops (rows whose tables were measured with
     the retired switch off). Each gets a new row, re-pinned with the retired feature on, or its
     own retirement ruling;
  2. every hook, stack helper, test arm and literal keyed on the retired switch, the manual
     controls no CI step runs included. Re-measure each or retire it, and fix the procedure that
     tells someone to run it.
- **A switch with no row fails the build.** A registry check that only prints "no row" is a note,
  and three shipped switches lost their only rows behind one. Make it fail (C5).
- In the worked project the retirement unit's proof was green — the base rows, the next stack row,
  a grep for the retired names — and still left three switches unproven and four manual controls
  reading tables nobody could reproduce. Proving what remains is green does not show that what was
  removed was covered elsewhere.
