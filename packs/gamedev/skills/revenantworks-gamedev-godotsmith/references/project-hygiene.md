# Project hygiene

Loaded by **Entry — Review**, fourth of four. The repository, the toolchain, and the things
that break when an agent edits a Godot project from outside the editor. Nothing here is
about gameplay; all of it is about whether tomorrow's run behaves like today's.

Sources for the borrowed practices are in `SOURCES.md`. Nothing here is copied text.

## Contents

1. Import before anything headless
2. What is committed and what is not
3. Resource identifiers
4. Naming collisions
5. Version pinning and upgrades
6. Cross-platform CI
7. Secrets and writable paths

---

## 1. Import before anything headless

**Run the headless import immediately after adding any new script or scene file, before any
headless typecheck, syntax check or test touches it.** Godot's headless tooling cannot see an
unimported file. It does not say "unimported" — it reports the symbol as not found, which
reads exactly like a typo or a missing class, and sends the reader hunting in the code.

In CI this is its own step before the first test run, not an assumption. An agent adding
files in one step and testing in the next will hit this every time otherwise.

## 2. What is committed and what is not

Three rules that are easy to get backwards:

- **Commit the import metadata and the resource identifier sidecars.** They are part of the
  project's identity; a checkout without them re-derives different ones.
- **Ignore the engine's generated cache directory.** It is machine-local, large, and churns.
- **End every unit of work with a pristine tree.** A Godot project generates files as a side
  effect of being opened, and a tree that is never clean means nobody can tell a generated
  file from an uncommitted change. Check the stash too: a handover or worktree switch can
  stash state silently, so a tree that reads suspiciously clean deserves a look at the stash
  list before you trust it.

## 3. Resource identifiers

**Never hand-author or hand-edit a resource's `uid://` value.** The engine owns them. A
fabricated one points at nothing and fails at load with an error that names the referencing
scene rather than the invented identifier.

**When moving, renaming or deleting a script or shader from outside the editor, move,
rename or delete its sidecar with it.** The editor does this for you; an agent working
through the filesystem does not, and the orphan is discovered at the next import.

**Treat scene and resource text files as data to read before editing and to diff after.**
Simple property and value edits by hand are fine. For anything structural — new node trees,
new signal wiring — generate the scene from a small script that builds the tree in code,
packs it and saves it. A generated scene is deterministic, reviewable as a diff, and cannot
corrupt the sections it does not touch. A hand-written nested edit can, silently.

## 4. Naming collisions

**Check a new global class name against the engine's own built-in type names before using
it.** A collision does not necessarily error. It shadows, and the failure appears somewhere
that looks unrelated to the name you chose.

The same check applies to autoload names, which live in the same global namespace as far as
most code is concerned.

## 5. Version pinning and upgrades

**Pin the exact engine version in a file every contributor and every agent reads.** Godot's
API surface moves between minor releases. An unstated version means a script can be correct
on one machine and silently wrong on another, and a CI pass proves only that it worked on
whatever the runner happened to install.

**Upgrade one minor version at a time, stabilising fully before the next hop.** Jumping
several releases at once collapses many independent breakages into one debugging session
where nothing isolates. This costs more calendar time and far less total time.

**Do not test engine internals.** An upgrade breaks those tests for reasons that have nothing
to do with your code, and the cost lands on whoever does the upgrade — which is precisely the
moment you most want a trustworthy suite.

## 6. Cross-platform CI

**Force LF line endings on shell scripts through a committed `.gitattributes`, from day one.**
A script checked out with CRLF fails on Linux with a carriage-return error that reads as a
broken test runner rather than a line-ending problem. It is the archetypal failure that gets
"fixed" by disabling the check.

**Detect or parameterise the platform-specific runner extension** rather than hardcoding one.

**Scripted edits read each file's own line ending before writing**, and **assert their match
count before writing**. Endings are a per-file property, not a per-repo one: five files in
one directory of a real project carried three different answers. A replace that finds nothing
returns the original bytes and exits zero, so without a count assertion the script reports
success and changes nothing.

## 7. Secrets and writable paths

**Never embed a secret in a shipped data or config asset.** Anything in a build's data files
is readable by anyone who has the build. There is no packing format that changes this.

**Draw a hard line between the read-only location the game is installed to and the writable
location runtime state goes.** Writing saves next to the executable works on the developer's
machine and fails on every platform with a real permissions model, at which point the failure
is a support ticket rather than a test failure.
