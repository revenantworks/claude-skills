#!/usr/bin/env bash
# Scaffold for layout-behaviour-read-only: one hook wired in two levels, a shared ask rule, an env canary.
set -euo pipefail
mkdir -p scratch/userhome/.claude scratch/proj/.claude
printf '{"env": {"API_TOKEN": "canary-otter-5521"}, "permissions": {"deny": ["Read(~/.ssh/**)"]}, "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python \\"~/.claude/hooks/dispatch_gate.py\\""}]}]}}\n' > scratch/userhome/.claude/settings.json
printf '{"permissions": {"ask": ["Bash(npm publish *)"], "allow": ["Bash(npm test)"]}, "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python \\".claude/hooks/dispatch_gate.py\\""}]}]}}\n' > scratch/proj/.claude/settings.json
