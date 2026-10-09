---
description: Should trigger - a repo and history scan for leaked keys before publishing. Flipped from identitywarden's near-miss in the 2026-10-08 consolidation; it is shieldwarden's own job.
tags: [trigger, should-fire]
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---
Scan this repository and its history for leaked API keys, tokens and passwords before I make it public.
