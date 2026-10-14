# Security Policy

## Supported versions

Only the latest release gets security fixes.

## What to report

The skills in this repository are instructions and scripts that run on your machine.
Report problems such as:

- A script that reads, prints, or sends secrets, files, or personal data it should not.
- A skill or hook that runs a command with more reach than it states.
- Text in a skill that can steer Claude to act against the user (prompt injection).
- A workflow or tool that leaks a token or lets a stranger run code in CI.
- Personal data (names, paths, emails, keys) in the repository or its history.

## How to report

Do not open a public issue. Use the private form:
<https://github.com/revenantworks/claude-skills/security/advisories/new>.

Include what you found, where it is (file and line), and steps to reproduce it. Use
placeholders instead of real secrets or other people's data.

## What to expect

We aim to reply within 7 days and to share a fix or a plan within 30 days. These are goals,
not guarantees. We credit reporters in the release notes unless they ask us not to.
