# Anti-patterns

Thirteen ways a fan-out loses work or wastes it, each with the one-line reason it matters and,
where one large rebuild produced a real instance, that instance. SKILL.md §9 points
here; this file is the lookup, not a standing load.

1. **Dispatch without a ledger row.** A unit launched before its row exists has no record to
   reconcile against — if it dies silently, nothing shows it was ever running.

2. **Separate commit and push.** A commit with no matching push is invisible on the remote; the
   rebuild lost one agent's work this exact way — it died on a usage limit at the
   words "Final verification and push," committed but unpushed, and looked lost until the next
   session checked the tree by hand.

3. **Treating a report as proof.** An agent's own account of what it did is not evidence of what
   landed. The same rebuild's adversarial verification against the filesystem, git, and the live
   routine API found 3 refuted and 5 partial claims out of 98 self-reported ones — including a
   disaster-recovery document still pointing at a repo path that no longer existed.

4. **Restarting instead of resuming.** Re-running a unit from scratch after a stall throws away
   whatever it already pushed and risks redoing (or conflicting with) real, landed work — the
   whole reason Resume's first action is reading origin before anything else.

5. **One agent marking another complete.** A dispatcher or sibling unit that certifies another
   unit's work without checking origin is trusting a report by proxy — the same failure as #3,
   one layer removed.

6. **Concurrent writers without a worktree.** Two units writing one repo in the same window
   collide. That rebuild hit this directly: two agents both wrote to one
   repo in the same window, one had to rebase, and a third agent's own sub-agents died mid-run and
   it silently redid their work by hand rather than surfacing the collision.

7. **A whole wave inside one minute.** Launching every unit in a wave at once removes the stagger
   that keeps two units from racing for the same file before either has committed anything.

8. **Two units fetching the same large document.** Every unit that independently fetches a big
   spec or listing pays its cost twice and doubles the chance of blowing a context window — the
   rebuild's own listing call returned up to 393 KB per page and overflowed the token limit on
   nearly every repo, more than once, because nothing cached the result for reuse.

9. **Escalating on a hunch.** A tier jump with no failed check, failed test, contract violation,
   or verifier's refutation behind it is a guess wearing the shape of a decision — the rebuild's
   root cause for running everything at one tier was exactly this: nothing forced a unit to earn
   its tier with a signal.

10. **A planning turn run at high effort.** High reasoning effort on a planning or orchestrator
    subtask reliably over-thinks and scope-creeps the plan itself, past what was actually asked —
    `references/tier-routing.md`'s own role-based override exists because of this failure mode.

11. **Fanning out work that shares context.** Splitting iterative work — where each step needs
    what the last one built — into separate units throws that shared context away between them;
    it belongs in the main conversation (SKILL.md §2), not a wave.

12. **No stop condition.** A unit with no stated definition of "done" cannot be checked against
    one; it either runs past what was needed or gets marked complete by guesswork.

13. **Launching top-tier work on a nearly spent window.** Starting a frontier-tier wave against a
    rolling usage window that is nearly exhausted is how a unit dies mid-write with nothing
    pushed yet. That rebuild's own run — about 20 background agents and 4 workflows, all
    at the top tier and high effort, across 9 repos — cost five separate usage-limit stops and two
    agents that died mid-write. Pacing a run over the week is pacewright's; every run still reads its meters
    (SKILL.md §6), and `references/meters.md` has the fallback fit and live gate.

## Excuses and red flags

Read before every §8 Reconcile report. Each row is a reason given for rounding a unit up to
done; none of them holds.

| Excuse | Why it fails | Do instead |
|---|---|---|
| "The agent said it pushed" | Completion is an origin sha match, never an agent's word | Run `git rev-parse origin/<branch>` per row |
| "Tests are green locally" | Local runs prove one machine only (#0087, #0090) | Wait for CI green on the commit |
| "The total looks about right" | A short total hides skipped files (#0057) | Check it against the brief's expected total |
| "That extra path is harmless" | A path outside `files_allowed` is scope drift (0183) | Mark the row `unverified` and report it |
| "The window will last one more wave" | Units die mid-write on a spent window (#13 above) | Read the meters before the wave launches |
| "Effort was set in the ledger" | The ledger states intent, not what resolved (0179) | Read effort from the definition or harness record |

**Red flags** — a report holding one is not ready:

- A row marked done with no origin sha beside it.
- A gate figure copied from a summary line.
- A worktree or branch the report does not mention.
- Spend figures with no source, not marked unverified.
