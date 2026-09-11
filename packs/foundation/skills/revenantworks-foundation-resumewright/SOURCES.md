# Sources

resumewright's shape is drawn from two internal records rather than a published standard, so
this file maps content to origin instead of to external documentation.

| Source | Applies to | Key guidance |
|---|---|---|
| `V:\Projects\.dispatch\runs\2026-09-10-estate-audit\RESUME.md` and `HANDOFF-PROMPT.md` (the owner's private estate-run directory; read on disk, never copied verbatim) | `references/handoff-template.md` (the file shape) | The section order (State now / Owner decisions / Next / Questions / Observations logged), the per-repo verified-sha form, and the resume-time `git stash list` / `git reflog` check are drawn from these two files' own shape. Only the shape moved into the template — no repo name, sha, decision, or path from either file is reproduced. |
| task-observer observation `0032-session-teleport-stashed-the-untracked-run-ledger.md` (`V:\Projects\github\MickMacPW\workshop\estate\observer\skill-observations\observation-log\`) | `SKILL.md` — Write step 3 (Commit), the Never section's first rule | The commit-in-the-same-call rule this whole skill exists to enforce: an untracked run directory was silently `git stash`-ed by a session handover, and a clean `git status` afterward read as "nothing to recover" rather than "something is stashed." |
| `V:\Projects\.dispatch\runs\2026-09-10-estate-audit\cache\h1-handoff-research.md` (this pack's own H1 research pass — candidate survey and spec, cited in full in `CHANGELOG.md`) | `SKILL.md` throughout; the dispatchwright and task-observer boundary paragraphs | The candidate survey (five existing session-handoff skills, none satisfying the commit requirement) and the spec section this member was built against — working name, pack placement, entry points, the commit rule, and the trigger-eval rows to write. |
| `revenantworks-foundation-dispatchwright/SKILL.md` §5 (Durability contract) and `references/ledger-schema.md` | `SKILL.md` — Gather step 1 (ledger-first reporting inside an active run); the dispatchwright boundary | The rule that a run's own ledger, not a second hand-kept list, is the source of truth for unit state — resumewright reads it rather than re-deriving it, the same discipline dispatchwright's own Reconcile applies to a unit's report. |

**Unsourced by design.** The exact file location rule (a run directory's `RESUME.md` when one
exists, the project root otherwise) and the no-remote-degrades-to-commit-only wording are
authored for this skill from the spec above, not drawn from a published standard — declared here
so the gap is visible rather than implied, matching this pack's own convention.
