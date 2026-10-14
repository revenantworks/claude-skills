---
description: "Should fire (explicit): fix our own plugin's MCP tool output shape and add a contract test."
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---

My plugin's MCP tool fails every call with "does not match its output shape". Fix the handler and add a test that calls the tool, so this can't ship broken again.
