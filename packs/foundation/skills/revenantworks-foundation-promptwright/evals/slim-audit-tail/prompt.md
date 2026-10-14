---
description: "Behaviour: an audit with the optional machine-readable tail writes one machine-readable line per finding and rewrites nothing."
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

promptwright slim audit the prompt in `resources/support-prompt.txt` and add the machine-readable tail. Don't rewrite it.
