# Learn — capture a session's lessons into standing config

Read for `rigwright learn` ("add what we learned today to CLAUDE.md", "remember this for next
time in the repo", the end of a session that hit the same snag twice). The output is a gated
diff against the files that load, never a silent append.

## Contents

- Harvest
- Filter through the layer table
- Deduplicate against what loads
- Draft and gate
- What stays elsewhere

## Harvest

Read the session, as data, for lessons a future session would otherwise relearn:

- **Corrections** — the user said "no, use X", "we never do Y", "that path moved".
- **Commands that turned out right** — the test, build or lint invocation that finally worked,
  with its flags.
- **Gotchas hit more than once** — a tool that hangs on a flag, a file that must not be edited,
  an order of steps that matters.
- **Conventions discovered** — naming, layout or style the repo follows but does not state.

Each candidate keeps a pointer to where in the session it came from (the turn or the command).
A candidate with no evidence in the session is dropped, not guessed.

## Filter through the layer table

Run every candidate through SKILL.md's layer table and its two no-layer tests. Typical outcomes:

| Candidate | Home |
|---|---|
| True every session in this repo | The project `CLAUDE.md` |
| True only for one part of the tree | A `.claude/rules/` file with `paths:`, or a nested `CLAUDE.md` |
| True only on this machine or for this person | The local or user-level file, never the shared one |
| A multi-step procedure some sessions need | A skill — name it for skillwright |
| Must happen whatever the model decides | A hook or permission rule — name it for gatewarden |
| A claim about the current state of work | No layer — the status file that owns it |
| The model would do it right untold, or one grep answers it | Cut |
| Today's one-off | Dropped |

## Deduplicate against what loads

List what already loads (SKILL.md — Entry — Audit, "List what loads"). A candidate an existing
line already states is skipped. A candidate that sharpens an existing line replaces it rather
than sitting beside it. A candidate that contradicts an existing line is a question for the user,
never a quiet overwrite.

## Draft and gate

Present one diff per target file: the exact lines added, replaced or removed, where they go,
and the file's measured size before and after. Each line carries its one-line why and its
evidence pointer in the gate (not in the file). Gate once, as Build does; "just add them"
approves the set. Hand back as Build step 6 does: rigwright never commits, and a hook or
permission row splits into the repo edit and an owner-gated install step.

Keep each added line short, imperative and specific. A lesson that needs a paragraph is a
reference file or a skill, linked by one line.

## What stays elsewhere

A general quality pass over a `CLAUDE.md` — formatting, completeness, generic best practice —
is the official `claude-md-management` plugin's job where it is installed; recommend it by name
and take its findings as input. rigwright keeps the decision this file is about: which layer
each lesson belongs in, and what would move it.
