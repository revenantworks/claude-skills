---
description: Beaten line "audit against this GPU" and margin M3 (test case T1) — AV1 on an RX 6000 card fails with its fix.
expected_outcome: The audit marks the stream encoder FAIL because this GPU has no AV1 hardware encoder, and names HEVC or H.264 AMF as the fix.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Audit my OBS streaming setup. My graphics card reads as "AMD Radeon RX 6700 XT". From my profile's basic.ini:

```ini
[Output]
Mode=Advanced

[AdvOut]
Encoder=av1_texture_amf
RecEncoder=h265_texture_amf
RecFormat2=mkv
```

and streamEncoder.json is `{"rate_control": "CBR", "keyint_sec": 2, "bitrate": 8000}`.
