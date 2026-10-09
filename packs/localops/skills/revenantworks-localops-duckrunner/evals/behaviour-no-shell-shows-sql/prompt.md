---
description: Behaviour, margin 2 and the no-shell rule. With no shell the skill shows the SQL, marks the answer NOT-RUN and gives no count by eye. Without the skill, a model counts the pasted items.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Use duckrunner. My repo has state/queue.yml with exactly this content:

```yaml
- id: 1
  title: write tests
  done: true
- id: 2
  title: ship the release
  done: false
- id: 3
  title: review the docs
  done: true
```

How many items are done? Show me the query.
