# Structure and wiring

Loaded by **Entry — Review**, first of four. How a Godot project is shaped and how its
parts reach each other. These are the findings with the largest blast radius, because
structure is the thing a project cannot cheaply change later.

Sources for the borrowed practices are in `SOURCES.md`. Nothing here is copied text.

## Contents

1. Composition over inheritance
2. Single responsibility, and the two-word test
3. Signal direction
4. One authoritative writer
5. Wiring dependencies
6. Signals as an interface
7. State machines, sized to the problem

---

## 1. Composition over inheritance

The scene tree is the substrate, and a deep class hierarchy is expensive to refactor inside
it: moving one behaviour means touching every descendant. Build from small, single-purpose
child scenes that can be attached where needed.

**Cap inheritance depth at three.** Past that, the cost of understanding what a node
actually does exceeds the cost of composing it. When a subset of entities needs a subset of
behaviours, that is composition's case, not inheritance's — a hierarchy forces every mix
into a new subclass and the combinations multiply.

This is the one practice every public Godot skill set agrees on, and it holds across
engines, which is evidence it is about the problem rather than about Godot.

## 2. Single responsibility, and the two-word test

**If a scene cannot be named in two words or fewer, it is doing too much.** "PlayerHitbox"
passes. "PlayerMovementAndInventoryAndUI" is three scenes wearing one name.

A corollary worth enforcing: **any independently reusable unit should run and be testable in
complete isolation** from the rest of the game. A scene that only works when booted inside
the full game is not a component, it is a fragment, and it cannot be covered by anything
cheaper than an end-to-end run.

## 3. Signal direction

The rule, in one line: **signals up, calls down, siblings through a shared owner.**

- **Up.** A child emits an event describing what already happened, in the past tense —
  `died`, `item_picked_up`, `health_changed`. The child stays ignorant of who is listening.
- **Down.** A parent calls its children directly. It owns them, so it may command them.
- **Sideways.** Two nodes that are not parent and child do not reach across the tree for one
  another. They talk through the owner they share.

**An event bus is a last resort, not a default.** Reach for a global signal hub only when
the alternative is a hard-coded path to a distant node. A bus makes every connection
invisible at the call site, which is exactly the property that makes a large project hard to
reason about.

Two anti-patterns worth naming because they look like good design:

- **A handler that re-emits the signal it just received.** That is a loop waiting for a
  second listener.
- **A chain of handlers whose only job is to forward.** Each hop is a place the payload can
  be dropped and nobody will see where.

## 4. One authoritative writer

Give every piece of runtime state exactly one owner that may write it. A second system that
wants it changed asks the owner rather than writing it too.

The failure this prevents is the one that looks like a physics bug: a state machine sets a
velocity, a separate movement script also sets it, and which one wins depends on node order
in the tree. Nothing in the code says the two are in conflict.

**Keep ephemeral and persistent state structurally separate.** Per-session state and
state that must survive a save belong in different owners, not in one bag with a convention
about which keys are which. The convention is what breaks.

## 5. Wiring dependencies

Choose by scope and lifetime, never by habit:

| Pattern | Use when | Do not use when |
|---|---|---|
| Autoload singleton | the service is genuinely global and lives for the whole run | it is merely convenient to reach |
| Exported reference or parent injection | the collaborator is owned by the editor or the parent scene | the collaborator is global |
| Service locator | the implementation must be swappable at runtime | you just want a shortcut |

**Resolve references in a defined initialisation step**, not opportunistically at first use.
A dependency resolved lazily fails at whatever moment it is first needed, which is rarely
where the bug is.

**Break a circular initialisation between two systems with a signal**, not by having each
look the other up. A mutual lookup means whichever loads second wins, and load order is not
something the code states.

## 6. Signals as an interface

**Type every signal parameter.** An untyped payload is a contract nobody can check.

**Once a payload needs more than two or three primitives, promote it to a typed object.** A
signal with six loose arguments is a struct that has not been declared, and every listener
re-derives the meaning of argument four.

**Check before subscribing.** Re-subscribing on a scene reload silently doubles every
callback; the symptom is a handler running twice with no sign of a second connection.

**A dynamic dispatch by name is a refactor hazard.** Where a mechanism resolves its target by
string, a rename breaks it silently and no tool can find the call site. If it must exist,
give it a test that asserts the target resolves.

## 7. State machines, sized to the problem

Match the weight to the actual complexity. Fewer than about five states with no per-state
data is an enum and a `match`; a full state-object hierarchy for that is ceremony.

**Parallel state machines beat one combinatorial machine.** Movement, combat and animation
each get their own, running side by side. One machine covering all three needs a state for
every combination, and the count grows multiplicatively.
