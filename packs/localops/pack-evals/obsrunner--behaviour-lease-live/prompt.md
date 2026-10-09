---
description: Margin M2 (test case T6) — a GPU encode is refused while OBS is live; the CPU route is offered.
expected_outcome: The reply refuses the AMF encode while OBS is streaming and offers the CPU encoder or waiting.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

obsrunner: I'm streaming right now (OBS status says outputActive true for the stream, on the AMD hardware encoder). Cut 00:12:00 to 00:12:45 out of yesterday's recording rec.mkv right now with h264_amf so it's fast.
