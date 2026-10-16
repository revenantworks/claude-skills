# Changelog — gdscript-lsp

## [1.0.0] — 2026-10-16

2026-10-16 (Godot tooling trial, ask AI): first build. An opt-in plugin beside the gamedev pack,
in the pyright-lsp shape (`.lsp.json` maps `.gd` to one server). `scripts/gdscript_lsp_bridge.py`
relays Claude Code's stdio LSP client to Godot's TCP language server (port 6005), loopback only,
with an opt-in headless editor (`GODOT_LSP_SPAWN=1`) that it stops on exit.
`scripts/gdformat_check.py` is a check-only PostToolUse hook for `.gd` files
(gdscript-formatter, then gdformat): exit 2 with the formatter's output when a file needs
formatting, NOT-RUN when no formatter is present; it never edits a file and installs nothing.
Tests in `scripts/test_*.py`.
