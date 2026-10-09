# Trigger Evals — description tuning

- Provenance: derived from revenantworks-foundation-skillwright v1.0.0; last re-anchored to v1.0.0, 2026-10-01; 2026-10-04 changes carry no version bump (private-test-phase rule). Full re-anchor history moved to evals/RESULTS.md. P1 apply 2026-10-01 (no version bump, owner decision 46): description narrowed to skill-package prose (docs prose → commscribe), gains "beats its incumbents" and the currency audit, and drops the brandwright clause; trigger rows 8, 35, 37 retargeted (brandscribe, commscribe), no expected verdict moved; Cases 14, 16, 37 retargeted; Cases 52-54 added (currency pass, evidence rules, CI template). Authored, not run; the cold re-judge is owed (J1). 2026-10-08 (no version bump, owner-approved foundation consolidation): evalwright folded in as the evals entry and tokenwright retired into slim entries; the description gains evals, slim and diagnose. Row 25 flips to should (evals on an existing skill is now this skill's); rows 26, 27, 36 retargeted; rows 45-60 carry evalwright's trigger rows, rows 61-67 the slim seam (tokenwright's skill rows here, its prompt and config rows to promptwright and rigwright), rows 68-72 the diagnose entry. Authored, not run. 2026-10-08 (no version bump): rows 73-74 add the optional scanner stage and its trustwarden pair; description unchanged; authored, not run.
- Counts: 74 queries (43 should, 31 should-not, 20 pairs), judged cold against name + description only (method notes moved to evals/RESULTS.md).
- Owed: #44 is authored, not executed; the re-run owed since v1.2.0 is neither discharged nor enlarged.

| # | Query | Should trigger? | Why |
|---|---|---|---|
| 1 | "Build me a skill that summarizes legal contracts into risk memos." | ✅ yes | Build-from-scratch, the core case |
| 2 | "Turn the workflow we just did into a skill." | ✅ yes | Extract-from-conversation build |
| 3 | "skillwright" | ✅ yes | Bare invocation |
| 4 | "Audit my skill against current best practices." | ✅ yes | Audit-existing |
| 5 | "Does this SKILL.md meet the spec? Score it." | ✅ yes | Audit + scoring |
| 6 | "Is there actually a niche for a skill that does invoice triage?" | ✅ yes | Parity verdict — the incumbent scan, parity table and margin answer the niche question |
| 7 | "skillwright upkeep" | ✅ yes | Pack-wide staleness sweep |
| 8 | "Apply my company's branding to the skills we generate." | ❌ no | Brand application — brandscribe's, not a build or port |
| 9 | "Package this skill folder so I can install it." | ✅ yes | Release packaging |
| 10 | "skillwright refresh" | ✅ yes | Baseline maintenance |
| 11 | "Write me a prompt that summarizes legal contracts." | ❌ no | Prompt, not skill — promptwright's job |
| 12 | "Improve this system prompt for my support agent." | ❌ no | Prompt improvement — promptwright |
| 13 | "What are Claude skills and how do they work?" | ❌ no | Explanation, no artifact to build |
| 14 | "Install the PDF skill for me." | ❌ no | Installation, not authoring |
| 15 | "Build me a web app that tracks invoices." | ❌ no | Software build, not a skill package |
| 16 | "Summarize this document." | ❌ no | Wants the task done, not a skill built |
| 17 | "Design a logo and brand palette for my company." | ❌ no | Brand creation, not brand-to-skill configuration |
| 18 | "Write a README for my Python library." | ❌ no | Docs for code, not a skill package |
| 19 | "Which model should I run this prompt on?" | ❌ no | Model routing — promptwright |
| 20 | "Make me a project plan for Q3." | ❌ no | Planning task, unrelated |
| 21 | "Port this skill pack so I can use it at my job — branding out, new names." | ✅ yes | Port — rebrand for a new owner |
| 22 | "Strip the branding and any personal references out of these skills." | ✅ yes | Port — sanitize sweep |
| 23 | "Make this skill set neutral and rename everything for a client handoff." | ✅ yes | Port — neutral re-issue |
| 24 | "Port this python app to linux." | ❌ no | Software porting — no skill set involved |
| 25 | "Write the trigger evals and test cases for my existing skill — don't touch the skill itself." | ✅ yes | Suite authoring for an existing target — the evals entry |
| 26 | "Build me a skill that triages invoices, and make sure it ships with a full eval suite." | ✅ yes | The build owns the package; the suite ships with it under `eval-doctrine.md` |
| 27 | "skillwright integrate pacewright" | ✅ yes | Direct integrate invocation |
| 28 | "Add the new member to the pack and update the rest of the skills with the integration." | ✅ yes | Pack propagation in natural language — roster restamp + registry + release set |
| 29 | "Integrate my app with the Stripe API." | ❌ no | Software integration, not pack propagation — no skill, pack, or roster in sight |
| 30 | "keep going" | ❌ no | Bare continuation outside a pack build's offer — ordinary conversation; only the continuation context routes it |
| 31 | "Build me a pack of skills for a customer-support engineer at a software company." | ✅ yes | Whole-pack design-and-build from a role — the Entry — Pack core case |
| 32 | "skillwright pack — research what a technical writer needs and build the roster." | ✅ yes | Direct pack invocation with domain research |
| 33 | "What skills are in the foundation pack?" | ❌ no | Roster lookup, not a design or build — the manifest answers it |
| 34 | "Build me a starter pack of prompts for cold sales emails." | ❌ no | A pack of prompts, not skills — promptwright's job; "pack" alone doesn't route here |
| 35 | "Humanize the README in my skill pack — it reads like a bot wrote it." | ✅ yes | Prose pass on a pack's own file; the object is named in the description and commscribe covers docs prose outside a skill package, and a pack README is inside one |
| 36 | "The prose in my pack's CLAUDE.md is unreadable — rewrite it, same rules." | ✅ yes | Prose pass on a pack's own file; rigwright also names CLAUDE.md, for placement and for a standing-config slim, and nothing here asks for either |
| 37 | "Humanize the release announcement for this skill before I post it." | ❌ no | A message bound for a channel is commscribe's even when a skill is its subject — the prose clause claims files, not audiences |
| 38 | "Audit this skill for security problems before I publish it — secrets, injection, anything unsafe." | ✅ yes | Security pass on a skill package; the description's security clause names all three cues |
| 39 | "Does my SKILL.md tell the model to just do whatever the files it loads say?" | ✅ yes | S-1 injection surface in a skill's own instructions — the artifact is a SKILL.md, named in the trigger list |
| 40 | "Check the template my skill generates — I think it writes world-readable config and pins nothing." | ✅ yes | S-4 unsafe defaults in generated output; the object is what a skill package bakes in, not a running system |
| 41 | "Review my nightly agent's tool permissions." | ❌ no | Runtime permission on an agent — gatewarden's scan, by the boundary sentence; no skill package is in play |
| 42 | "My scheduled agent reads customer email — how do I stop an injection from making it send things?" | ❌ no | Injection at runtime with a blast radius — agentwright's isolation and trust-tier job; skillwright's injection claim is scoped to a skill's own instructions |
| 43 | "Pen-test our API for injection vulnerabilities." | ❌ no | Code-level threat coverage — a security harness's job, neither wright's; "injection" alone does not route here |
| 44 | "A plugin just shipped everything my PDF skill does — is my skill still worth keeping, or should I retire it?" | ✅ yes | Audit's parity re-check and retire condition on an existing skill; the object is a skill package against its incumbents, not a general product comparison (researchscribe) |
| 45 | "write trigger evals for my new skill" | ✅ yes | Evals, generate |
| 46 | "build an assertion suite for this SKILL.md" | ✅ yes | Evals, generate; pair-mate of #56 |
| 47 | "skillwright evals audit this suite" | ✅ yes | Evals, audit by keyword |
| 48 | "generate test cases for this prompt card" | ✅ yes | Evals on a prompt card — no routing surface, assertion suite only |
| 49 | "the intro says 18 cases but I count 22 — check my suite" | ✅ yes | Evals audit, count integrity (implicit) |
| 50 | "skillwright evals refresh — I just shipped v1.2 of the skill" | ✅ yes | Evals refresh by keyword |
| 51 | "does this agent spec have regression coverage?" | ✅ yes | Evals on an agent spec |
| 52 | "are my should/shouldn't queries balanced?" | ✅ yes | Evals audit, boundary pairs |
| 53 | "I haven't built the skill yet — here are three tasks Claude gets wrong without it; write the evals first" | ✅ yes | Test-first gap list |
| 54 | "write a test case that proves my skill beats promptfoo on routing" | ✅ yes | Claim case |
| 55 | "ok the skill's finally done, pushed it, CI is green — oh before I forget can u do the should/shouldnt evls for it" | ✅ yes | Noisy: evals asked inside status talk; pair-mate of #58 |
| 56 | "write unit tests for this Python function" | ❌ no | Code unit tests — engineering tooling |
| 57 | "run my plugin's eval suite and show me the with/without delta" | ❌ no | Running a suite is `claude plugin eval`'s; skillwright writes what it runs |
| 58 | "my CI is flaky again and the parse_date test keeps timing out — add a few more unit tests for that function while you look" | ❌ no | Noisy: code unit tests buried in CI talk |
| 59 | "benchmark the top tier against the default worker on my workload" | ❌ no | A model benchmark — promptwright model or a harness, not a suite for a skill |
| 60 | "optimize my support prompt against these eight test cases" | ❌ no | Prompt tuning cases stay in promptwright's optimize; pair-mate of #48 |
| 61 | "Get this SKILL.md under 300 lines without changing what it does." | ✅ yes | Slim on a skill package |
| 62 | "skillwright slim — my skill's references cost too much every run" | ✅ yes | Slim by keyword |
| 63 | "Score my pack's skill descriptions for token waste without rewriting anything." | ✅ yes | Slim audit, score-only |
| 64 | "Set token budgets for the members of my skill pack." | ✅ yes | Slim budget over a set of skills |
| 65 | "Slim this system prompt — it's 6k tokens and I need it under 3k." | ❌ no | A prompt's slim is promptwright's |
| 66 | "My CLAUDE.md costs too much per session — slim it, but keep every rule exactly as it is." | ❌ no | Standing config's slim is rigwright's |
| 67 | "Make Claude's replies terser at runtime so the session spends fewer output tokens." | ❌ no | Runtime output cutting — external tools (caveman, rtk), not an artifact slim |
| 68 | "skillwright diagnose — my changelog skill never fires when I ask for release notes" | ✅ yes | Diagnose by keyword |
| 69 | "Why didn't my PDF skill trigger in yesterday's session? Here's the transcript path." | ✅ yes | Diagnose, did not fire; pair-mate of #71 |
| 70 | "That run with my research skill burned 200k tokens — find out why." | ✅ yes | Diagnose, cost |
| 71 | "Why did my scheduled agent fail last night?" | ❌ no | An unattended agent's failure is agentwright's |
| 72 | "Debug why my Python test keeps failing." | ❌ no | Code debugging, no skill in play |
| 73 | "Audit this skill — and if I have a skill scanner installed, run it first." | ✅ yes | An audit with the scanner as stage 1 of the security pass (`scanner-stage.md`). The pair with #74 |
| 74 | "Is this skill-scanner tool safe to install before I let it read my skills?" | ❌ no | Vetting third-party code before install is trustwarden's; skillwright runs a scanner only after that vet. The pair with #73 |

**Security-pass edge notes (v1.4.0).** #38–#40 vs #41–#42 is the whole risk of the added clause, and the word doing the damage is **injection**: it now appears in skillwright's description *and* in agentwright's, so the object decides and nothing else. A **skill package** — its SKILL.md, its reference files, the template it generates — is skillwright's; a **running agent** — its permissions, its cadence, what an injected instruction could make it do — is agentwright's, which claims untrusted content flowing through an agent by name. #42 is the sharpest pair-mate to #38 (same noun, opposite object) and must be judged first on the re-run, #41 second. #43 sits outside both descriptions on purpose: agentwright already defers code-level threat coverage to a security harness, and skillwright names no code object at all — a row that fires either wright is a breadth defect in whichever fired.

**Prose-pass edge notes (v1.3.0).** #35/#36 vs #18 is the whole risk of the added clause: a README *belonging to a skill or pack* routes here, a README for a Python library does not, and the only thing separating them is the ownership qualifier "a skill's or pack's own files" — #18 is now the closest no-row in the suite alongside #8 and must be judged first on the re-run. #37 is the seam's message side and the line the clause must not cross: same verb, same subject, different object class. #36 vs rigwright is the CLAUDE.md contention: rigwright names that file for placement and slim, and a prose rewrite of a pack's own CLAUDE.md is neither.

**Edge notes.** #31 vs #34 is the pack boundary — a pack of *skills* routes here; a pack of *prompts* is promptwright's even with identical phrasing. #33 marks lookup vs build. #28 vs #29 is the integrate boundary — pack/roster/member vocabulary routes here; "integrate" against an app or API does not. #30 only fires when a pack build just offered the continuation.

**Original edge notes.** #1 vs #11 is the sharpest boundary — "build a skill that does X" wants a package; "write a prompt that does X" wants promptwright. #8 and #17 both mark the brandscribe boundary — applying a brand and inventing one alike route there; skillwright builds neutral. #24 is the port near-miss — "port" alone is ambiguous; the description anchors it to skill sets. #26 and #25 both route here since 2026-10-08 — a suite ships with a build, and a suite for an existing skill is the evals entry. If real usage misses the yes-set, push the trigger verbs harder; if it fires on the no-set, tighten the boundary sentences.

**Evals, slim and diagnose edge notes (2026-10-08).** #46 vs #56 is the evals line — tests for a skill route here, tests for a function never do. #47 vs #57 — writing or scoring a suite is here, running it is the runner's. #48 vs #60 — a prompt card's assertion suite is here; tuning a prompt against cases is promptwright's optimize. #61 vs #65 vs #66 is the slim split by owner: a skill package here, a prompt promptwright's, standing config rigwright's — the object decides, never the verb. #67 is runtime and stays out. #69 vs #71 — a skill that did not fire is diagnose; an unattended agent that failed is agentwright's. #73 vs #74 — running an installed scanner inside an audit is here; vetting the scanner itself before install is trustwarden's.
