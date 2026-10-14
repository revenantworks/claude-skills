# Trigger Evals — 36 queries (18 should / 18 shouldn't)

- Provenance: derived from revenantworks-foundation-agentwright v1.0.0; last re-anchored to v1.0.0, 2026-10-01; 2026-10-04 changes carry no version bump (private-test-phase rule). Full re-anchor history moved to evals/RESULTS.md.
- Counts: 36 queries (18 should, 18 should-not, 4 pairs), judged cold against name + description only (method notes moved to evals/RESULTS.md).
- Owed: rows 15, 16, 24-26, 29 and 32 were re-judged by hand against the 2026-10-01 description (security scan moved to gatewarden, vendor targets cut, retired names re-pointed); the cold re-judge of every row is still owed, not claimed.

| # | Query | Expected |
|---|---|---|
| 1 | design a morning agent that scans my watchlist and emails me signals | SHOULD |
| 2 | agentwright audit — here's my Entry Scan prompt | SHOULD |
| 3 | what guardrails should my auto-reply bot have | SHOULD |
| 4 | add a kill switch to this scheduled task | SHOULD |
| 5 | my agent reads incoming emails — how do I keep injections from doing damage | SHOULD |
| 6 | spec the retry and failure behavior for the nightly sync agent | SHOULD |
| 7 | what should the agent output when it finds nothing | SHOULD |
| 8 | review this automation before I let it touch my accounts | SHOULD |
| 9 | how should agent A hand results to agent B safely | SHOULD |
| 10 | harden this cron bot so it can't overspend | SHOULD |
| 11 | write the system prompt for my trading agent | SHOULD NOT (prompt text — promptwright) |
| 12 | which stocks should the agent buy | SHOULD NOT (domain strategy — owner pack) |
| 13 | pen-test this codebase for injection vulns | SHOULD NOT (code-level — security harness) |
| 14 | build me a skill that audits agents | SHOULD NOT (skill build — skillwright) |
| 15 | draft the announcement that the agent is live | SHOULD NOT (message — commscribe) |
| 16 | compare LangGraph vs CrewAI and pick one | SHOULD NOT (verdict — researchscribe) |
| 17 | why did my script throw a KeyError | SHOULD NOT (debugging, not agent design) |
| 18 | set up the actual cron job on my server | SHOULD NOT (execution — surface/infra) |
| 19 | design an agent that mass-DMs people who criticize me | SHOULD (it is an agent-design ask and routes here; the harassment restraint is applied *after* routing and is asserted in `test-cases.md` Case 11 — restraint: harassment, not by a cold routing listing) |
| 20 | what's a good schedule for posting videos | SHOULD NOT (content strategy) |
| 21 | does this agent spec have regression coverage? write the missing test cases | SHOULD NOT (suite authoring — skillwright evals) |
| 22 | harden the ops spec for my inbox agent — caps, retries, kill switch | SHOULD |
| 23 | agentwright refresh | SHOULD (platform-notes baseline maintenance — no spec run) |
| 24 | my inbox agent has delete and send granted but only ever reads — check what it's actually allowed to do | SHOULD NOT (runtime tool-grant scope — gatewarden scan) |
| 25 | is my scheduled agent leaking credentials? the API key is pasted into its instructions and its errors dump the whole payload | SHOULD NOT (runtime credentials exposure — gatewarden scan) |
| 26 | security-scan this agent — here's its tool list and its retry policy | SHOULD NOT (runtime scan — gatewarden scan) |
| 27 | audit how this skill package is built — is its SKILL.md structured to best practice | SHOULD NOT (the skill artifact, not an agent's runtime permissions — skillwright) |
| 28 | scan my repo for hardcoded secrets and vulnerable dependencies | SHOULD NOT (code-level — security harness; the new security clause claims an agent's grants, not a codebase) |
| 29 | is my agent spec missing any sections — does it cover cadence, output contract, zero-signal | SHOULD (Entry — Audit; spec completeness is agentwright's, the grant scan is gatewarden's) |
| 30 | make this spec a weekly Cowork task | SHOULD (Entry — Emit) |
| 31 | agentwright emit — render this to a Claude Code routine | SHOULD (named subcommand) |
| 32 | render this spec as a GitHub Actions scheduled workflow instead | SHOULD (Entry — Emit, CI target) |
| 33 | write the custom instructions for my Claude Project | SHOULD NOT (standing config a human reads in session — rigwright) |
| 34 | my CLAUDE.md is too long, what should come out | SHOULD NOT (attended repo config — rigwright) |
| 35 | should my wait-for-CI checker be a cron routine, a self-paced wake or /loop — and how do I stop it running forever | SHOULD (loop pacing, area 1; pair-mate of 36) |
| 36 | write the full system prompt text my overnight coding agent will run on | SHOULD NOT (the prompt text itself — promptwright; the objective's done check and budget would stay here) |

Edge note: sharpest pair is 1 vs 11 — the system around the prompt is agentwright; the prompt itself is promptwright. 21 vs 8 splits suite authoring (skillwright evals) from spec review (here) — "write the test cases" leaves; "review the automation" stays. Misses on the yes-set → push "agent/bot/scheduled/automation" nouns; fires on 11 → strengthen the prompt-text boundary sentence. #23 is maintenance, not design — it regenerates the stamped platform baseline and produces no spec. Since 2026-10-01 rows 24-26 are near-misses: what a built agent may do at runtime is gatewarden's `scan`, and agentwright's description names that boundary. 29 is the pair that stays: whether a *spec* covers its areas is agentwright's Audit. 27 (skill package, skillwright) and 28 (codebase, security harness) guard the other sides. Fires on 24-26 → the gatewarden boundary clause is too weak; fires on 27 or 28 → agentwright is over-claiming security.

**Emit-seam edge note (new at 1.3.0).** Sharpest new pair is **30 vs 33**. Both are setup-shaped requests naming a Claude surface; the deciding property is who reads the output. A Cowork task fires with nobody watching, so it is agentwright's whole — cadence, guardrails, zero-signal line and all. Claude Project instructions are read by a human in the session, so they are rigwright's. The word "set up" appears in both descriptions and decides nothing. Fires on 33 or 34 → the rigwright boundary sentence is under-claiming and needs the named objects, not the category.
