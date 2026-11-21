#!/usr/bin/env python3
"""outbound_text_guard.py: PreToolUse hook (matcher Bash|PowerShell|mcp__.*) that refuses text bound
for a GitHub page when it holds an entry of the private names list (observation 0561).

The pii_guard git hook reads commits only. A PR title, a PR body, an issue or a comment goes out
through `gh` or a GitHub MCP tool and never meets it, and GitHub keeps a body's edit history, so a
scrub after posting undoes nothing. One harness attribution template put the owner's display name
and login into a PR body that way. This hook checks the text before it is sent.

Checked:
  - a shell line with `gh pr|issue create|edit|comment|review`, `gh release create|edit` or
    `gh api` (any method): the whole line, heredoc bodies included, plus the file a
    `--body-file`/`--notes-file`/`-F` flag names when it exists;
  - a GitHub MCP tool that writes text or files (create_pull_request, update_pull_request,
    add_issue_comment, issue_write, update_issue_comment, add_reply_to_pull_request_comment,
    add_comment_to_pending_review, pull_request_review_write, create_or_update_file, push_files,
    create_repository): every string in its input. The two file tools commit on the host, so
    pii_guard never sees them either.

The names list is pii_guard's: `WARDEN_NAMES_FILE`, else `~/.warden/wordlist.txt`. An entry matches
case-insensitively as a whole word. The refusal never prints the entry it matched.

Fail mode: closed for a hit (rule `outbound_text_guard`, hard: the text is published the moment
the call runs). Open with a warning when the names list is missing, since nothing can be checked.
Open on an unreadable event or a crash: pii_guard and the release scan stay the later layers.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

RULE = "outbound_text_guard"
NAMES_VAR = "WARDEN_NAMES_FILE"
GH_TEXT = re.compile(r"(?i)(?:^|[\s;&|(`'\"])gh(?:\.exe)?\s+(?:(?:pr|issue)\s+(?:create|edit|comment|review)"
                     r"|release\s+(?:create|edit)|api)\b")
BODY_FILE = re.compile(r"(?:--body-file|--notes-file|-F)[=\s]+(['\"]?)([^\s'\"]+)\1")
MCP_WRITERS = ("create_pull_request", "update_pull_request", "add_issue_comment", "issue_write",
               "update_issue_comment", "add_reply_to_pull_request_comment", "add_comment_to_pending_review",
               "pull_request_review_write", "create_or_update_file", "push_files", "create_repository")
REASON = ("outbound text holds an entry of the private names list ({where}). PR and issue titles, "
          "bodies and comments are published, and GitHub keeps their edit history: remove the name "
          "(write \"the owner\"), drop any attribution line that names the owner or the account, and "
          "send again (observation 0561).")
MISSING = ("outbound_text_guard: names list not found ({var} or ~/.warden/wordlist.txt), so this "
           "PR or comment text was not checked for names.")


def load_names() -> list[re.Pattern] | None:
    path = os.environ.get(NAMES_VAR) or os.path.join(os.path.expanduser("~"), ".warden", "wordlist.txt")
    try:
        with open(path, encoding="utf-8") as f:
            entries = [s.strip() for s in f if s.strip() and not s.strip().startswith("#")]
    except OSError:
        return None
    return [re.compile(r"(?i)(?<![A-Za-z0-9])" + re.escape(e) + r"(?![A-Za-z0-9])") for e in entries]


def hits(text: str, names: list[re.Pattern]) -> bool:
    return any(p.search(text or "") for p in names)


def strings_of(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_of(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings_of(v)]
    return []


def shell_where(cmd: str, cwd: str, names: list[re.Pattern]) -> str:
    """Where a names-list hit sits in a gh line bound for GitHub, or '' when none."""
    if not GH_TEXT.search(cmd or ""):
        return ""
    if hits(cmd, names):
        return "in the command or its heredoc"
    for m in BODY_FILE.finditer(cmd):
        path = m.group(2)
        full = path if os.path.isabs(path) else os.path.join(cwd or ".", path)
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                if hits(f.read(), names):
                    return f"in the body file {os.path.basename(path)}"
        except OSError:
            continue
    return ""


def mcp_writer(tool: str) -> bool:
    low = tool.lower()
    return low.startswith("mcp__") and "github" in low and any(low.endswith("__" + w) for w in MCP_WRITERS)


def main() -> None:
    ev, _raw = hl.read_event()
    if ev is None:
        hl.allow()
        return
    tool = str(ev.get("tool_name") or "")
    ti = ev.get("tool_input") or {}
    shell = tool in hl.SHELL_TOOLS and bool(GH_TEXT.search(hl.command_of(ev)))
    mcp = mcp_writer(tool)
    if not (shell or mcp):
        hl.allow()
        return
    names = load_names()
    if names is None:
        hl.allow(context=MISSING.format(var=NAMES_VAR))
        return
    if shell:
        where = shell_where(hl.command_of(ev), str(ev.get("cwd") or ""), names)
    else:
        where = "in the tool input" if any(hits(s, names) for s in strings_of(ti)) else ""
    if where:
        hl.block(REASON.format(where=where), rule=RULE, hard=True)
    hl.allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
