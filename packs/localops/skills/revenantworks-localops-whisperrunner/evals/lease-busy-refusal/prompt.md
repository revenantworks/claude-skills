---
description: Margin M2 (test case T3) — another runner's live lease blocks a GPU transcription in unattended mode.
expected_outcome: The reply refuses the GPU run as GPU busy and never interrupts or unloads the render.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Queue tonight's transcription of my interviews folder on the GPU, unattended, I'm going to bed. For reference, the localops GPU lease file currently reads:

```json
{"holder": "comfyrunner", "purpose": "video render, 121 frames", "started": "2026-10-01T21:40:00Z", "expires": "2026-10-01T22:30:00Z"}
```

It is 22:05 UTC now.
