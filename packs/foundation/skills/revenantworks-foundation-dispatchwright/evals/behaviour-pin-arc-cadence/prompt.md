---
description: Behaviour - land cadence is per arc for pin-moving lanes, one join row re-pins once, and view lanes that move no pins land freely (observation 0432).
tags: [behaviour, plan, lands]
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---
dispatchwright plan. Game repo, one writer per worktree. Units: N1, N2, N3 are three sim changes, each moving the determinism hash pins and each shipping an OFF switch that returns the old pins; V1 is a HUD layout fix that touches no sim file and moves no pin. Today each unit lands alone with its own re-pin, review, CI run and remote update. Propose the table and the land cadence. Do not launch anything.
