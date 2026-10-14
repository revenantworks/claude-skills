# Eval results — revenantworks-scribe-commscribe

## 2026-10-08 — K9 plugin-eval run (Windows, Claude Code 2.1.295)

harness: the Windows eval runner ignores context.add_dirs (Claude Code 2.1.295); needs a Linux runner; not a skill result.

Cases that read a fixture folder through `context.add_dirs`, so their scores on this runner are not skill results: `multi-voice-ask`.
