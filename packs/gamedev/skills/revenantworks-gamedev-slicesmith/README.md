# revenantworks-gamedev-slicesmith

slicesmith runs the loop that writes game code in a Godot 4 project: spec, plan, thin vertical
slices, a failing test first, verify, commit. General coding-loop skills stop at "the tests
pass". slicesmith adds what a game needs on top: a proof obligation per milestone, real spikes
before the architecture leans on them, slices a player can reach, a Godot verify ladder
(import, zero-warning build, counted suite, scene smoke-load, export check), and a feel gate
only the user may close.

## Package

```
revenantworks-gamedev-slicesmith/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE · NOTICE
├── references/
│   ├── spec-and-plan.md     # spec and plan: weight classes, templates, spikes, slice sizing
│   ├── slice-and-test.md    # every slice and fix: the cycle, verify ladder, seams, determinism
│   ├── verify-and-exit.md   # commit and exit: evidence, commit body, run log, review, export gate
│   └── pack.md              # sibling boundaries, read on boundary doubt only
└── evals/
    ├── trigger-evals.md · test-cases.md · RESULTS.md
    └── <case>/              # native `claude plugin eval` cases (prompt.md + graders/)
```

## Install

**Claude Code** — `/plugin install gamedev@revenantworks`, or drop the folder in `~/.claude/skills/`.
**claude.ai** — Settings → Capabilities → Skills, upload the zip. With no shell it plans and
writes slices, and marks every verify step NOT-RUN.

## Commands

| Invocation | Does |
|---|---|
| `slicesmith spec` | Reads the code, writes the spec with its proof obligation, then stops for approval |
| `slicesmith plan` | Read-only: spikes first, then slices with failing test, verify command and expected line |
| `slicesmith slice` | The next unblocked slice: red, green, wire, verify, commit |
| `slicesmith fix` | A bug: reproduce with a failing test, fix, revert once to prove the test, commit |
| `slicesmith exit` | Closes a milestone: re-derived figures, fresh-context review, deletion test, deferrals, export gate |

## What sets it apart

- **Six laws** carried in the body, learned from building a real game: name the proof first;
  spike for real; slices a player can reach; red first across the real seam; evidence, never a
  claim; one slice, one honest commit.
- **A Godot verify ladder** that states counts beside expected totals, never "green".
- **Things tests cannot see** — scenes, resources, feel, export-only failures — each has a rung
  or an owner.
- **An excuses table** with game-specific rows ("it compiles, so the jump works").

## Boundaries

Whether a run can be believed, CI guards and the gate ruling are **godotsmith's**; art
**pixelsmith's**; audio **soundsmith's**. A requirements interview is **grillwright's** and a
multi-agent fan-out **dispatchwright's** (foundation pack).

## Staying current

`SOURCES.md` carries the dated parity register on a 90-day stamp; `skillwright upkeep` sweeps it.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
