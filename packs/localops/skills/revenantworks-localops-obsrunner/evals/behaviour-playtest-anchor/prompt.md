---
description: playtest (test case T22) — a Game Bar recording's start is its birth time; the MP4 creation_time tag is the end.
expected_outcome: The reply puts the start at 17:33:41 (the birth time or the file name), says the creation_time tag marks the end, and aligns by the wall clock.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

obsrunner: I recorded a playtest with Xbox Game Bar. The file is "Game 2026-10-21 17-33-41.mp4". Its file birth time is 17:33:41.07 local, its modified time is 17:54:49.6 local, ffprobe gives duration 1268.98 s, and the MP4 creation_time tag reads 17:54:49 local. My game wrote a play log with wall-clock times. What time did the recording start, so I can line the video up with the log?
