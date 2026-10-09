# Trigger evals — revenantworks-warden-gatewarden

Counts: 59 queries (32 should, 27 should-not, 13 pairs)

Provenance: authored against SKILL.md v0.1.0 (2026-10-01), by the unit that wrote the
description. Judged from **name + description only**, as a cold router would. Not a cold judge —
the reader wrote the clauses — so a cold re-judge is owed. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Balance: 32 should-fire · 27 should-not (22 near-misses, 5 off-topic or no skill) — 59 in all. Row 27 added
2026-10-02 with `capreview`, judged the same way. Rows 25-26 added
in P1 (2026-10-01) with the go-live block; judged the same way. **Consolidation (2026-10-08, owner):**
filewarden's map, footprint, drift, loads and status entries merged in and the `layout` entry was
added; rows 28-59 are carried from filewarden's suite (origin marked) or new for `layout`, re-judged
by hand against the merged description, not yet cold-judged. filewarden's signposts rows went to
shieldwarden; its should-not rows naming gatewarden (remove an allow rule, a PreToolUse hook) are
this member's own job now, and row 40 carries one of them as a should-fire.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "audit my Claude Code permissions" | Named trigger |
| 2 | "why could Claude run git push when I denied it?" | Named trigger (why was this allowed) |
| 3 | "harden settings.json for this repo" | Named trigger (lock down) |
| 4 | "is this SessionStart hook safe?" | Named trigger |
| 5 | "lock down which MCP servers load in this project" | MCP server scope |
| 6 | "I denied rm in Bash, can Claude still delete files through PowerShell?" | PowerShell twin margin |
| 7 | "our routine stalled on a permission prompt, check the repo settings" | ask in a tracked file |
| 8 | "gate my git pushes so nothing goes out without CI passing" | Push gate hook |
| 9 | "cap how many tool calls each subagent can make" | Call cap hook |
| 10 | "security-scan what my scheduled agent is allowed to do" | scan (moved from agentwright) |
| 11 | "stop Claude from restoring or deleting my Hyper-V checkpoints" | Hyper-V lock hook |
| 12 | "gatewarden explain Bash git -C . push" | Named keyword |
| 25 | "make sure Claude can never start my stream or read my stream key" | OBS go-live block hook |
| 27 | "the call cap stopped my agent - was it looping or was the cap too low?" | capreview |
| 28 | "What's eating all the space on my second drive? I can't see where 200 GB went." | map (carried from filewarden row 1) |
| 29 | "Map where Claude has read and written on this machine over the last month." | footprint (filewarden row 2) |
| 30 | "Find orphaned worktrees and scratchpads Claude Code left behind." | footprint orphans (filewarden row 3) |
| 31 | "Which of my added directories has Claude never actually used?" | footprint, granted-never-reached (filewarden row 4) |
| 32 | "Make a treemap of my projects folder so I can see what's big." | map, local page (filewarden row 5) |
| 33 | "What's Claude's blast radius here — every folder it has touched?" | footprint (filewarden row 6) |
| 34 | "My ~/.claude folder is huge, help me clean it up." | map and footprint, proposals only (filewarden row 7) |
| 35 | "The hook installed in my user folder and the copy in my repo might have drifted — check them." | drift (filewarden row 8) |
| 36 | "Are all my repos where my drive layout rules say they should be?" | map with drive rules (filewarden row 9) |
| 37 | "gatewarden status" | Named subcommand (was "filewarden status", row 10) |
| 38 | "Some of my skills show up twice in /skills, once with an anthropic-skills: prefix. Which ones, and how do I stop it?" | loads (filewarden row 14) |
| 39 | "Is any skill loading twice on this machine, say from a plugin and my personal folder?" | loads (filewarden row 15) |
| 40 | "Remove this allow rule, nothing uses it any more." | harden on footprint evidence (filewarden should-not row 11, now this member's own job) |
| 41 | "gatewarden layout" | Named subcommand (new 2026-10-08) |
| 42 | "Show me every settings file, permission rule and hook I have, and where they overlap." | layout (new) |
| 43 | "Which of my gatewarden rules keep interrupting me the most, and where should each rule live?" | layout, event log and homes (new) |
| 44 | "Are dispatchwright's hooks wired twice, once in my user settings and again in this repo?" | layout, hook-twice (new) |
| 45 | "Should my git push deny rule live in my user settings or in the repo's settings.json?" | layout, a permission rule's home (new; rigwright keeps standing instructions) |

## Should not fire

| # | Request | Owner | Boundary |
|---|---|---|---|
| 13 | "should I install this MCP server from a forum post?" | trustwarden | install at all, not runtime scope |
| 14 | "vet this GitHub Action before I add it" | trustwarden | pre-install verdict |
| 15 | "rotate my GitHub token, I think it leaked" | keywarden | the credential itself |
| 16 | "where should I store my API keys on Windows?" | keywarden | secrets storage |
| 17 | "scan the repo history for leaked keys" | shieldwarden | content scan |
| 18 | "where should my settings files live in this repo?" | rigwright | layout and placement |
| 19 | "trim my CLAUDE.md, it's too long" | rigwright | standing config text |
| 20 | "design a weekly routine that triages my inbox, with a kill switch" | agentwright | designing the agent |
| 21 | "build a Hyper-V VM with a TPM for testing" | hypervrunner | running VMs |
| 22 | "how fast can I spend usage this week?" | pacewright | pacing, not enforcement |
| 23 | "write a Python function that parses JSON settings" | none | plain coding |
| 24 | "what's the weather in Lisbon" | none | off-topic |
| 26 | "switch my OBS scene to Gameplay and check dropped frames" | obsrunner | drives OBS; the block only guards go-live |
| 46 | "Scan this folder for keys before I zip it up." | shieldwarden | what is inside a file (filewarden row 12) |
| 47 | "Find the files on my drive named passwords or bank and tell me who can open them." | shieldwarden | signposts moved there (new 2026-10-08) |
| 48 | "Check the files in this folder for passwords written inside them." | shieldwarden | content scan (filewarden row 15) |
| 49 | "Where should my commit-message rule live — CLAUDE.md or a skill?" | rigwright | a standing instruction's home (filewarden row 4) |
| 50 | "Write the CLAUDE.md for this repo and decide which rules go in .claude/rules." | rigwright | standing config, not permission rules (new) |
| 51 | "Add a skillOverrides entry to my user settings that hides anthropic-skills:deploy-helper." | rigwright or the update-config skill | writing config; loads only finds the doubles (filewarden row 17) |
| 52 | "Delete node_modules in every project right now." | none | no skill runs a bulk delete (filewarden row 5) |
| 53 | "Write a Python script that walks a directory tree and sums file sizes." | none | plain coding (filewarden row 6) |
| 54 | "Should I install WizTree? Is it safe?" | trustwarden | install at all (filewarden row 7) |
| 55 | "Run a Postgres container and cap its disk at 20 GB." | dockerrunner | operate Docker (filewarden row 8) |
| 56 | "Compact the WSL disk, it's taking 80 GB." | dockerrunner | owns the disk; map only measures it (filewarden row 14) |
| 57 | "How many rows in state/queue.yml are done?" | duckrunner | a data query (filewarden row 9) |
| 58 | "Rewrite my git identity on the last 30 commits." | shieldwarden | identity and history rewrite (filewarden row 10) |
| 59 | "Is my gh token stored somewhere other people on this machine could read it?" | keywarden | credential storage (filewarden row 16) |

Boundary pairs: 2↔15 (denied command vs leaked token), 3↔18 (rule content vs file location),
6↔17 (PowerShell route vs content scan), 10↔20 (scan a built agent vs design one), 11↔21 (lock vs run),
5↔13 (scope of a loaded server vs installing one), 9↔22 (enforce a cap vs set a budget),
25↔26 (guard go-live vs drive OBS), 28↔56 (measure the disk vs compact it), 29↔46 (where Claude
wrote vs what is inside), 45↔49 (a permission rule's home vs a standing instruction's home),
38↔51 (find the doubles vs write the override), 28↔47 (a size map vs names that advertise secrets).
