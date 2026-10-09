# Changelog

## 9.4.3

- Removed the `--legacy-output` flag; use `--output-format` instead
- Added a `SessionPause` hook event
- Fixed a crash when a changelog line held a date like 2026-09-30

## [9.4.2]

- Improved plugin install speed
- Security: settings files are no longer readable by subagents without a grant

## 9.4.1

- Added `/rename` for sessions

## 9.4.0

- Fixed worktree cleanup on exit
