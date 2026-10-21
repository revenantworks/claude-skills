# Systems and export

Loaded by **Entry — Review** when the change touches saving and loading, a play log, a state
machine, an event bus, C# signals or the export pipeline. These are conventions a project lives by and the
checks that hold them; the API for each lives in the Godot documentation, and this file
never restates it.

Sources for the borrowed practices are in `SOURCES.md`. Nothing here is copied text.

## Contents

1. Save and load — the file side
2. State machines — beyond sizing
3. An event bus, and when not to have one
4. C# signals
5. The export pipeline
6. A play log and engine errors

The canonical save form (sorted keys, fixed order, no incidental floats) is
`determinism-and-state.md` section 2; sizing a state machine is `structure-and-wiring.md`
section 7. Neither is repeated here.

---

## 1. Save and load — the file side

- **Write under `user://`, never `res://`.** The resource folder is read-only in an exported
  build, so a save that works in the editor fails only after export.
- **Never leave the only save half-written.** Write to a temporary file, then rename it over
  the old one, and keep the previous save as a backup. A crash or a full disk mid-write must
  cost one session at most, never the player's whole save.
- **Every save carries a format version.** Load migrates forward one version at a time, each
  step a small function with its own test that loads a saved fixture of the old format. An
  additive key with a default needs no version bump.
- **Load builds the new state aside, then swaps it in.** A load that fails halfway leaves the
  running game untouched and says why; it never leaves half the world loaded.
- **A save a player can share is untrusted input.** Never decode it with a format that can
  carry objects or scripts. Plain data in, validated field by field.
- **Prove it with a round trip:** save, load, save again, and compare the two files byte for
  byte. A difference is a serialisation bug or an unsaved field.

## 2. State machines — beyond sizing

- **Transitions live in one place.** A state may ask to change; the machine decides. A state
  that sets another state's flags directly is the second writer C2 forbids.
- **Enter and exit run every time.** Cleanup that lives only in one transition's path leaks
  the first time a new path reaches that state.
- **Save the state's identity, not its node.** The save holds a stable state id and the
  state's own data; load rebuilds the machine from those.
- **Test every legal transition and at least one illegal one**, and assert the illegal one is
  refused. A machine that accepts any transition is an enum with extra steps.

## 3. An event bus, and when not to have one

An autoload that only declares signals is a fair tool for events with many unrelated
listeners across the tree: a day ended, the game paused, a setting changed.

- **Not for a parent and its child.** That is C2: signal up, call down. A bus between
  neighbours hides who depends on whom.
- **Not for a request that needs an answer.** A bus broadcasts; a reply through it couples
  the asker to whichever listener happened to run first.
- **The bus holds no state and no logic.** Its file is a list of signals with typed
  parameters, and that list is the contract.
- **Listener order is not a contract.** Code that works only when one listener runs before
  another is a hidden dependency; make it explicit.
- **Every listener disconnects when it leaves the tree.** A bus outlives every scene, so a
  forgotten connection keeps a freed listener reachable. Test it: reload the scene twice and
  assert the connection count did not grow.

## 4. C# signals

- **Use the generated signal-name constants, never a string.** A string name survives a
  rename and fails at runtime; a constant fails at build time.
- **Disconnect what you connect.** A connection whose receiver is a lambda or a plain C#
  object is not cleaned up when the node goes; pair each connection with its removal on
  leaving the tree, and prefer a named method so the removal is possible.
- **Payloads must be engine-compatible types.** A plain C# class that the engine cannot
  marshal fails when the signal is emitted, not when it is declared; promote it to an engine
  object or a dictionary of plain values.
- **A signal crossing between GDScript and C# is connected by name.** It carries the
  rename hazard in `structure-and-wiring.md` section 6, so give it a test that asserts the
  connection resolves.
- **A C# build is not a run.** C1 applies twice: the .NET build, then the headless boot.

## 5. The export pipeline

- **Commit the export presets; never the credentials.** Signing passwords and keystore paths
  stay out of tracked files and come from the CI secret store or the engine's separate
  credentials file, which is ignored.
- **Pin the export templates to the editor version exactly.** A mismatch fails the export or,
  worse, ships a build the editor never tested. The pin lives with the engine pin
  (`project-hygiene.md`).
- **Export headless in CI, and test the export, not the editor.** Boot the exported build
  headless for a bounded number of frames and assert its proof line. An export that exits 0
  can still ship no code; slicesmith's export gate asserts what the package holds.
- **Non-resource files need an include filter.** JSON, CSV and text data load in the editor
  and vanish from the export unless the preset includes them. Guard it: list the data files
  the game loads and assert each is in the package.
- **A gate figure is taken on the build players run.** Debug and release builds differ in
  assertions and speed, so a performance figure names the export mode beside it
  (`perf-figures.md`).
- **One version number, one source.** The build stamps the version it reads from the project;
  a second hand-typed copy drifts.

## 6. A play log and engine errors

A play log lets a recorded playtest be joined to what the game did. The contract (fields, kinds,
segments, the mark key, how a recording is aligned) is obsrunner's `playtest` reference; this is
the Godot side.

- **One autoload, JSON Lines, one file per launch** under `user://`, written only off headless
  runs or behind an explicit flag, so the suite never writes one. Each line: `wall` (local ISO 8601
  with ms and offset), `mono_ms` (`Time.get_ticks_msec()`, monotonic; the system-time methods can
  be changed by the user), `session`, `seg` (+1 on every load, new game or restart), `tick`,
  `day`, `kind`, `detail`.
- **Views and IO only.** The logger reads state and never writes it: a test shows the state hash
  is unchanged with logging on, and the sim never calls the logger directly.
- **The mark key** writes a `mark` line and flashes a counter on screen, so the frame and the log
  both carry it.
- **Engine errors through a `Logger` (Godot 4.5+):** subclass `Logger` and register it with
  `OS.add_logger()` in an autoload's `_init()`. `_log_error` and `_log_message` are called from
  other threads, possibly at once: guard the writer with a `Mutex`. `push_error()` and
  `push_warning()` arrive at `_log_error`; `print()` cannot be used inside the logger; the
  engine's own start-up messages never arrive. Script backtraces are empty in a release export
  unless **Always Track Call Stacks** is set; set it in the playtest preset only.
- **Deduplicate on (file, line, code):** the first occurrence in full, then one `error_repeat`
  line per key per 10 s with `count`, `first_wall` and `last_wall`. A flood becomes a few lines,
  each placed in time.
- **`godot.log` rotates.** `user://logs/` keeps a few files and a later launch renames the
  current one, so a tool picks the engine log whose timestamps span the session, never the
  newest by name.
