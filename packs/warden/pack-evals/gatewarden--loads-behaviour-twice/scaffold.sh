#!/usr/bin/env bash
# Scaffold for behaviour-loads-twice: one open sync twin with an older body, one twin already off.
set -euo pipefail
C=scratch/claude
mkdir -p "$C/skills/deploy-helper" "$C/skills/notes-helper"
mkdir -p "$C/skills/synced/acct/deploy-helper" "$C/skills/synced/acct/notes-helper"
printf -- '---\nname: deploy-helper\ndescription: d\n---\ncanary-heron-4410 new\n' > "$C/skills/deploy-helper/SKILL.md"
printf -- '---\nname: deploy-helper\ndescription: d\n---\ncanary-heron-4410 old\n' > "$C/skills/synced/acct/deploy-helper/SKILL.md"
printf -- '---\nname: notes-helper\ndescription: d\n---\nsame\n' > "$C/skills/notes-helper/SKILL.md"
printf -- '---\nname: notes-helper\ndescription: d\n---\nsame\n' > "$C/skills/synced/acct/notes-helper/SKILL.md"
printf '{"skills": [{"name": "deploy-helper", "source": "plugin", "creatorType": "user"}, {"name": "notes-helper", "source": "plugin", "creatorType": "user"}]}\n' > "$C/skills/synced/acct/manifest.json"
printf '{"skillOverrides": {"anthropic-skills:notes-helper": "off"}}\n' > "$C/settings.json"
