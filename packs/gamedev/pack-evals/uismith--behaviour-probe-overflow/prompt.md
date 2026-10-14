---
description: Behaviour - reading a probe report, the measured break leads, with its exact change (test case 4).
tags: [behaviour, margin]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---
uismith probe ran on report.html. Its dark-theme table reads:

| Width | Page / viewport | Past right | Off left | Clipped | Truncated | Status |
|---|---|---|---|---|---|---|
| 320 | 412 / 320 | table.data (92 px) | - | td.name (60 px) | - | FINDING |
| 375 | 412 / 375 | table.data (37 px) | - | - | - | FINDING |
| 768 | 768 / 768 | - | - | - | span.title (40 px) | PASS |

The light theme passed at every width. Is the page fine to ship, and what do I change?
