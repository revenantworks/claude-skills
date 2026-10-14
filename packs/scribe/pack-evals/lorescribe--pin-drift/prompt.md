---
description: "Margin 2 (T6): a project pinned to universe canon 1.3 uses a fact retired in 1.4; expect PIN-DRIFT."
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

My universe has a shared bible in its own repo, and each game repo pins the canon version it was built against.

Game repo `bible.md`: `universe: shared-universe-bible`, `pin: "1.3"`.

Universe `CANON-LOG.md`:

| version | date | id | change |
|---|---|---|---|
| 1.3 | 2026-03-02 | glass-monks | level soft -> hard |
| 1.4 | 2026-06-18 | weir-bridge | retired: the bridge was never built |

New quest text for the game: "Meet the courier on the Weir Bridge at midnight and cross to the glass monks' gate."

Check the quest text against canon.
