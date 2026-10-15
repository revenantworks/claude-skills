---
description: Behaviour - a stacked re-pin needs complete controls and a per-control table; a control that leaves rows moved is a finding, not a table to fill from failure lines (determinism-and-state section 3a, test case G10).
tags: [behaviour, determinism, pins]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
We built three sim changes on one branch. Each has a tests-only `_OFF` switch meant to return the old behaviour. At the join, I turned all three switches on and ran our keep-neutral test: 5 of the 9 pinned hashes match main, 4 still differ. My plan is to copy the 9 new hashes from the failure lines into the test, commit "re-pin", and move on, since the switches are all there. Is that sound?
