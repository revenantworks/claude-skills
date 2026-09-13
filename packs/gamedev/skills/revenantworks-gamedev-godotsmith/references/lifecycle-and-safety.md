# Lifecycle and safety

Loaded by **Entry — Review**, second of four. Node lifetime, signal lifetime, and the
threading rules. Most entries here describe a crash or a leak that only appears under
teardown, reload, or load, which is why they survive code review so easily.

Sources for the borrowed practices are in `SOURCES.md`. Nothing here is copied text.

## Contents

1. Freeing nodes
2. Surviving an await
3. Signal lifetime
4. Overriding engine virtuals
5. Worker threads and the scene tree
6. Test-time lifetime

---

## 1. Freeing nodes

**Use the deferred free, never the immediate one, during normal play.** An immediate free
destroys the node inside the current frame, while the engine may still be iterating over it.
The deferred path waits for the end of the frame, which is the whole reason it exists.

**Never mutate a children collection while iterating it.** Take a copy first, or collect the
targets and free them after the loop. Removing from the collection you are walking skips
elements, and the skip is silent.

**Guard every deferred destruction.** Between requesting the free and the frame ending,
other code can still reach the node. Anything holding a reference must check validity before
using it, and a system that caches node references needs an explicit invalidation path.

## 2. Surviving an await

This is the single highest-yield check in this file for agent-written Godot code.

**After any `await` — a timer, a signal, an animation finishing — the node you were running
on may be gone.** The await yields, the scene changes or the parent frees, and execution
resumes inside an object that no longer exists. The crash is at the first property access
after the await, which is nowhere near the cause.

Check validity of `self` after every await that can span a frame, and return if it has gone.
The check costs nothing; skipping it produces a crash that reproduces only under scene
transitions.

**Follow a simulated input with an explicit synchronisation point.** In an async test that
drives the engine loop, an input queued and then immediately asserted has not been processed
yet. Await the engine's own processing point before asserting, or the test reads the state
from before the input.

## 3. Signal lifetime

**A method-reference connection auto-disconnects when its owning node is freed. A lambda or
closure connection does not.** This asymmetry is invisible at the call site — both look like
"connecting a signal" — so a reviewer checking that a connection happens in the right place
will pass code that crashes on teardown.

A closure connection must be disconnected explicitly when the node exits the tree, or made
one-shot. Otherwise the callback holds a live reference into a freed node and fires on the
next emission.

**In C#, always disconnect in the exit-tree hook.** GDScript's connections are reference-
counted in a way C# events are not, so the language you are in changes the rule.

## 4. Overriding engine virtuals

**Call the base implementation first when overriding an engine virtual** — ready, process,
physics process, input. The engine does real setup in those, and an override that silently
replaces it produces a node that is subtly not initialised, with no error anywhere.

## 5. Worker threads and the scene tree

Three hard rules, and the first is absolute:

1. **Never touch a live scene-tree node from a worker thread.** Not a read, not a write.
   Snapshot the data you need before spawning the thread, do pure computation on the copy,
   and marshal the result back to the main thread with a deferred call.
2. **Never read or write a resource concurrently, and never await a signal from a worker
   thread.** Both are main-thread constructs.
3. **Never wait on a thread-pool task from inside another running pool task.** That is a
   deadlock, and it reports as a busy error rather than as a hang, which sends people
   looking in the wrong place.

Two sizing rules that save more time than they cost:

- **Do not thread cheap work.** The handoff costs more than the computation.
- **Do not create and join a thread per frame.** Pre-create long-lived workers and feed them.

## 6. Test-time lifetime

**Free every test-instantiated node through the framework's own auto-free helper.** A test
that instantiates a node and forgets it leaks into the next test in the same run, which
turns into an order-dependent failure somebody will later call flaky.

**When tests pass individually but fail as a suite, suspect shared global state before you
suspect ordering.** Godot's autoload pattern makes a singleton reachable from any script, so
a suite that never resets one produces failures that move when you reorder the tests. Reset
explicitly in a per-test setup hook. Calling it flaky and re-running is how a real regression
gets hidden.

**A red test must fail for the right reason before you trust it.** Verify the failure
message says what you expect. A test that fails because the symbol does not exist yet is not
the same test as one that fails because the behaviour is wrong, and only the second proves
anything once it goes green.

**Do not test engine internals, private implementation state, or pixel-perfect rendering
output.** Those assertions fail on engine upgrades for reasons that have nothing to do with
your code, and the cost lands on whoever does the upgrade. Rendering comparisons in
particular do not belong in a headless run at all: there is no real framebuffer, so a pass
there is evidence of nothing.
