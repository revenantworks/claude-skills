---
description: Trigger row Y1 — a local transcription to srt must load whisperrunner.
expected_outcome: The whisperrunner skill is invoked.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a recording of yesterday's team meeting saved as meeting.m4a in my Downloads folder. Please transcribe it into srt subtitles with timestamps, on this machine only. Nothing should go to a cloud service.
