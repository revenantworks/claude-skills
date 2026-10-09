# Trigger evals — 28 queries (14 should / 14 shouldn't)

Counts: 28 queries (14 should, 14 should-not, 5 pairs)

- Provenance: written for revenantworks-scribe-researchscribe 0.1.0, 2026-10-01 (pack-split build B14). **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.
- Method: read each query cold against name + description only; compare with the Expected column.
- State: cold run 2026-10-01 (run J1): blind list from `tools/blind_queries.py`, judged on the
  worker tier against all 30 pack descriptions: 24/24 agreed. Tiers checked: worker only; the fast
  and top tiers are unchecked. The native suite in the case folders is run by `claude plugin eval`
  in the pack's eval pass (A6); rows marked `native:` mirror a case folder.
- Re-read by hand 2026-10-01 after the description gained "defining a brand or its voice file is
  brandscribe's" (998 chars, A2 PK-1): 1-12 still fire; row 17 now routes out on that named
  clause instead of on absence; no row changed verdict.

| # | Query | Expected |
|---|---|---|
| 1 | which NAS should I buy for home backups under $600 — compare and pick one | SHOULD (verdict) · native: trigger-pick-nas |
| 2 | is the paid tier of this password manager worth it for a family of four | SHOULD (verdict, Decision) |
| 3 | go/no-go on moving our docs site to a static host | SHOULD (verdict) |
| 4 | deep research the current state of WebGPU support across browsers | SHOULD (research) · native: trigger-deep-research |
| 5 | research this: how do the big object-storage providers throttle requests | SHOULD (research) |
| 6 | here is a research summary from a colleague — grade it and turn it into a pick | SHOULD (report intake) · native: trigger-grade-report |
| 7 | write a reference guide for our backup process and verify each step against the docs | SHOULD (playbook) |
| 8 | fact-check this setup guide against current vendor docs and tell me what drifted | SHOULD (verify) |
| 9 | I have three overlapping how-to docs for the same tool — consolidate them | SHOULD (playbook consolidation) |
| 10 | read this Reddit thread and tell me what people say about the router | SHOULD (sources) · native: trigger-reddit-thread |
| 11 | researchscribe refresh | SHOULD (refresh) |
| 12 | research the real history of Roman roads for my novel, with sources | SHOULD (real-world research for fiction) |
| 13 | build a story bible for the factions in my game | SHOULD NOT (fiction canon — lorescribe) · native: nearmiss-story-bible |
| 14 | check chapter 9 for contradictions with my world's timeline | SHOULD NOT (canon check — lorescribe) |
| 15 | rewrite this email to my landlord to sound firmer | SHOULD NOT (message — commscribe) · native: nearmiss-rewrite-email |
| 16 | announce our decision to switch hosts to the team on Slack | SHOULD NOT (message — commscribe) |
| 17 | update our brand voice and palette | SHOULD NOT (brand — brandscribe) |
| 18 | which model tier should I run this summarisation prompt on | SHOULD NOT (run-target pick — promptwright) · native: nearmiss-prompt-model |
| 19 | is there a niche for a skill that writes changelogs | SHOULD NOT (skill parity verdict — skillwright) |
| 20 | document this Python module's API | SHOULD NOT (code docs) |
| 21 | what's 17 times 23 | SHOULD NOT (trivial) |
| 22 | summarize this PDF in five bullets | SHOULD NOT (summary, no verification or decision) |
| 23 | brainstorm names for my podcast | SHOULD NOT (ideation) |
| 24 | split this big migration into tiered agent units and launch them | SHOULD NOT (fan-out planning — dispatchwright) |
| 25 | check this auth setup doc against the framework's official docs for the version we run | SHOULD (verify official, K4 C1) |
| 26 | research our caching options and save the cited findings as a file in the repo | SHOULD (research, cited file, K4 C1) |
| 27 | check my CLAUDE.md against the official Claude Code docs and move rules where they belong | SHOULD NOT (config placement — rigwright) |
| 28 | write a handoff file into the repo with what we found this session | SHOULD NOT (session handoff — handoffwright) |

Edge notes:
- Sharpest pair **12 vs 13**: real-world facts for a story are researchscribe's; the story's own canon is lorescribe's. Misses here mean the description's lore line is too broad.
- **2 vs 18**: a standardize-on-one or worth-it decision with nothing to run is a verdict; a model for a prompt in hand is promptwright's.
- **4 vs 24**: "deep research" fans out inside this skill; a fan-out of build work is dispatchwright's.
- **25 vs 27** and **26 vs 28** (added 2026-10-08, K4 C1, authored, not run cold): a doc checked against
  official docs is a verify here unless the doc is Claude config (rigwright's); a cited research
  file is this skill's, a session-state file is handoffwright's.
- Tuning: misses on 1–12 → make the trigger verbs pushier; fires on 13–24 → tighten the boundary sentences.
