# Trigger Evals — revenantworks-foundation-rigwright

- Provenance: derived from revenantworks-foundation-rigwright v1.0.0; last re-anchored to v1.0.0, 2026-10-01; 2026-10-04 changes carry no version bump (private-test-phase rule). Full re-anchor history moved to evals/RESULTS.md.
- Counts: 39 queries (22 should, 17 should-not, 8 pairs), judged cold against name + description only (method notes moved to evals/RESULTS.md).
- Owed: rows 21-31 not yet judged cold; the 20/20 cold results in RESULTS.md cover rows 1-20 only. Rows 19-31 were re-read by hand against the 2026-10-01 slim description (gatewarden, filewarden and the retired names); the cold re-judge is still owed. 2026-10-08 (no version bump, owner-approved consolidation): tokenwright retired and this skill gained `slim`; rows 18 and 24 flip to should, rows 32-37 added. Authored, not run. Same day (warden 6 → 4): rows 30-31 and the #31 note re-pointed from the retired filewarden to gatewarden.

## Should fire

| # | Query | Why |
|---|---|---|
| 1 | "Set up a Claude Project for my client research work" | Named surface, build intent |
| 2 | "Write me a CLAUDE.md for this repo" | Named artifact |
| 3 | "My project instructions are a mess — can you tighten them?" | Fix intent on a named surface |
| 4 | "Should this rule go in my CLAUDE.md or a skill?" | The placement question, verbatim |
| 5 | "What belongs in profile preferences vs project instructions?" | Placement across two named layers |
| 6 | "My CLAUDE.md is 400 lines and Claude ignores half of it" | Bloat symptom on a named artifact |
| 7 | "Score my repo's Claude config" | The audit entry |
| 8 | "rigwright audit" | Quoted invocation keyword |
| 9 | "I need a .mcp.json for this project's servers" | Named artifact in scope |
| 10 | "Plan the knowledge files for a Project about our pricing policy" | Knowledge-file plan, named |
| 21 | "Write the hook that enforces this rule in my repo" | Hook named in the description; the hook-write probe owed since 1.0.2 |
| 22 | "Should this be a path-scoped rule instead of a CLAUDE.md line?" | Placement question on a repo config layer |
| 23 | "We already have an AGENTS.md — do we need a CLAUDE.md too?" | Placement across two instruction files; the description names both since 2026-10-01 |
| 25 | "rigwright place: our commit-message rule" | Named mode |
| 26 | "This CLAUDE.md says wave 3 is paused — is that fine?" | Stale-status audit, named in the description |
| 27 | "Audit my setup for bloat" | Audit trigger, verbatim |
| 18 | "Trim the token cost of my CLAUDE.md" | Slim entry since 2026-10-08 (was a should-not to the retired tokenwright); pair-mate of #36 |
| 24 | "Slim my CLAUDE.md — the layout is already right, I just want it cheaper" | Slim, cost motive with layout settled; pair-mate of #6 (placement) inside one skill now |
| 32 | "Why does my CLAUDE.md cost so many tokens every session?" | Slim, cost question on standing config |
| 33 | "Set token budgets for the seven instruction files in this project." | Slim over a set of standing config; pair-mate of #35 |
| 34 | "ugh the bill jumped this month, and the team keeps adding rules to our CLAUDE.md... why does this instruction file cost so many tokens per turn, and what could come out without changing behavior? layout is fine, it's just the cost" | Noisy: slim asked inside billing talk |
| 38 | "Before we close, add what we learned today about the flaky test runner to CLAUDE.md." | Learn: session lessons into standing config; pair-mate of #39 |

## Should not fire

| # | Query | Routes to | Why it's a near-miss |
|---|---|---|---|
| 11 | "Build me a skill that formats changelogs" | skillwright | Config-shaped verb, skill object |
| 12 | "Audit this SKILL.md against best practices" | skillwright | Shares the `audit` verb |
| 13 | "Make this a weekly Cowork task" | agentwright | Setup-shaped, but unattended |
| 14 | "Set up a routine that reviews PRs on merge" | agentwright | "Set up" is rigwright's verb; the object runs unattended |
| 15 | "Edit the SKILL.md for my desktop scheduled task" | agentwright | **Sharpest pair.** Filename says skill, object is a scheduled task |
| 16 | "What guardrails should my scheduled agent have?" | agentwright | Runtime authority |
| 17 | "Rewrite this system prompt so it stops rambling" | promptwright | Instruction text with no layer question |
| 19 | "Apply our brand palette to the project README" | brandscribe | Identity, not configuration |
| 20 | "Draft the announcement telling the team about the new Project" | commscribe | Message to a channel |
| 28 | "Lock down my settings.json so Claude can never read ~/.ssh" | gatewarden | Permission content, not placement |
| 29 | "Is the hook in my repo safe to install?" | gatewarden | Hook safety review |
| 30 | "Map what Claude can write on this machine" | gatewarden | Reach map, not config placement |
| 31 | "Is my live ~/.claude/settings.json in sync with the repo copy?" | gatewarden | Live/tracked map; rigwright only names the pair |
| 35 | "Slim this system prompt — it's 6k tokens and I need it under 3k." | promptwright | A prompt's slim is promptwright's; same verb, different object |
| 36 | "Get this SKILL.md under 300 lines without changing what it does." | skillwright | A skill package's slim is skillwright's |
| 37 | "My session keeps compacting mid-task — manage my live context." | none (runtime) | A live session, not an artifact; runtime tools, never a slim |
| 39 | "Turn the release steps we worked out today into a reusable skill." | skillwright | A procedure some sessions need is a skill package, not a CLAUDE.md line; pair-mate of #38 |

## Edge notes

**Sharpest boundary pair: #15 against #2.** Both name a `SKILL.md`. The deciding property is the *object*, never the filename: a desktop scheduled task is stored on disk as a `SKILL.md` and is still agentwright's, because a filename describes the format and not the thing. rigwright's description carries this by claiming attended standing configuration and routing "anything that runs unattended" away by name; agentwright's claims scheduled tasks positively. If #15 fires rigwright, the fix is on rigwright's boundary sentence, not on agentwright's.

**Second-sharpest: #18 against #35 and #36.** Since 2026-10-08 the slim verb is split by object, not by motive: standing config is rigwright's slim, a prompt promptwright's, a skill package skillwright's. #18 and #6 now both route here; the motive picks the mode inside rigwright (cost → `slim`, placement or effectiveness → `audit` or `build`).

**#13 and #14 test the same seam from the setup side.** rigwright owns the verbs *set up*, *configure*, *scaffold*; agentwright owns the objects those verbs are applied to when nobody is watching the result. The verb cannot decide it, which is why both descriptions carry the object test.

**Permission and drift seams (2026-10-01): #21 against #28-29.** Writing a hook entry that enforces a repo convention is placement plus emit (rigwright); what a permission rule says and whether a hook is safe is gatewarden's. #31 against #18: a diverged live/tracked pair is gatewarden's map; rigwright names a pair it meets and scores it under rot.

**Tuning rule.** Misses on the should-set → the description's triggers need to be pushier, most likely by naming a surface the query used. Fires on the should-not set → tighten the boundary sentence, and check whether the sibling's description makes its own positive claim; a boundary held from one side only is the failure mode this pack has already hit twice.
