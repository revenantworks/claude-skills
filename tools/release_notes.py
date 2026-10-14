#!/usr/bin/env python3
"""claude-skills — release notes: draft a pack's CHANGELOG entry from its commits, and lint it.

Used by release.py (steps 1 and 2); stdlib only. Ideas taken from the release-notes-drafter
routine template, fitted to this repo's rule that the CHANGELOG moves only at release:

  draft(pack, since)   the commits that touched packs/<pack>/ since the previous tag (or, with
                       no tag yet, since the repo's first commit), internal ones
                       dropped (scope tools, ci, docs, test...), sorted under New / Improved /
                       Fixed / Breaking by the summary's first verb. It is a draft: release.py
                       heads it with a "(fill in)" line, so the changelog gate still stops the
                       run until a person has read and edited it.
  lint(section)        errors: a Breaking item with no "Migrate:" line. Warnings: a file path,
                       a function name, a commit hash, an internal code (B5, M14e, V-K8w2), or
                       an item over four sentences — the CHANGELOG is public and written for
                       users, not contributors.

    python tools/release_notes.py draft <pack> [--since <tag-or-date>]   # print a draft
    python tools/release_notes.py lint <pack>-vX.Y.Z                     # lint one CHANGELOG section
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADINGS = ("New", "Improved", "Fixed", "Breaking")
INTERNAL_SCOPES = {"tools", "ci", "docs", "doc", "test", "tests", "build", "chore", "release", "refactor"}
NEW_VERBS = {"add", "adds", "introduce", "introduces", "new", "create", "creates", "ship", "ships", "support"}
FIX_VERBS = {"fix", "fixes", "correct", "corrects", "repair", "repairs", "restore", "restores", "stop", "stops"}
FILL = "(fill in)"
REVIEW_LINE = f"- {FILL} review the draft below in plain user words, then delete this line"

_PATH = re.compile(r"(?<![\w/@])(?:[\w.-]+/)+[\w.-]+|\b[\w-]+\.(?:py|md|json|ts|js|ya?ml|ps1|sh|toml|txt)\b")
_FUNC = re.compile(r"\b[A-Za-z_]\w*\(\)")
_SHA = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
_CODE = re.compile(r"\b(?:[A-Z]\d{1,2}[a-z]?|[A-Z]-[A-Z]\w*\d\w*|M\d+[a-z]?\d*)\b")  # B5, M14e, V-K8w2
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*(\"])")


def _git(*args: str, root: Path = ROOT) -> str:
    r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def commits(pack: str, since: str | None, root: Path = ROOT) -> list[tuple[str, str]]:
    """[(subject, body)] for non-merge commits touching packs/<pack>/, oldest first.
    since: a tag (range since..HEAD), an ISO date (--since), or None (all)."""
    fmt = "--format=%s%x1f%b%x1e"
    if since and re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        # after the heading's whole day: the dated release's own commits are already in it
        out = _git("log", "--no-merges", "--reverse", fmt, f"--since={since} 23:59:59", "--", f"packs/{pack}",
                   root=root)
    elif since:
        out = _git("log", "--no-merges", "--reverse", fmt, f"{since}..HEAD", "--", f"packs/{pack}", root=root)
    else:
        out = _git("log", "--no-merges", "--reverse", fmt, "--", f"packs/{pack}", root=root)
    rows = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if rec:
            subj, _, body = rec.partition("\x1f")
            rows.append((subj.strip(), body.strip()))
    return rows


def classify(subject: str, body: str) -> tuple[str | None, str, str]:
    """(heading or None for internal, scope, summary)."""
    scope, sep, summary = subject.partition(": ")
    if not sep or not re.fullmatch(r"[a-z0-9][\w./-]*", scope.strip()):  # a scope is one lower-case token
        scope, summary = "", subject
    scope = scope.strip()
    summary = summary.strip().rstrip(".")
    first = summary.split(" ", 1)[0].lower() if summary else ""
    if scope.lower() in INTERNAL_SCOPES or first in {"refactor", "test", "tests"}:
        return None, scope, summary
    if "BREAKING" in subject or "BREAKING" in body or "breaking change" in (subject + " " + body).lower():
        return "Breaking", scope, summary
    if first in FIX_VERBS or re.search(r"\b(bug|regression)\b", summary, re.I):
        return "Fixed", scope, summary
    if first in NEW_VERBS:
        return "New", scope, summary
    return "Improved", scope, summary


def draft(pack: str, since: str | None, root: Path = ROOT) -> str:
    """The drafted section body (headings + bullets), or "" when no user-facing commit."""
    groups: dict[str, list[str]] = {h: [] for h in HEADINGS}
    for subj, body in commits(pack, since, root):
        head, scope, summary = classify(subj, body)
        if head is None or not summary:
            continue
        text = summary[0].upper() + summary[1:] + "."
        line = f"- **{scope}**: {text}" if scope else f"- {text}"
        if head == "Breaking":
            line += "\n  Migrate: (fill in) what a user must do."
        if line not in groups[head]:
            groups[head].append(line)
    parts = []
    for h in HEADINGS:
        if groups[h]:
            parts.append(f"### {h}\n\n" + "\n".join(groups[h]))
    return "\n\n".join(parts)


def default_since(root: Path = ROOT) -> str | None:
    """With no previous tag: the repo's first commit (the 1.0.0 export), else the date on the
    newest dated CHANGELOG heading. The first commit wins because a re-exported history carries
    the export's date, not the release's."""
    first = _git("rev-list", "--max-parents=0", "HEAD", root=root).split()
    if first:
        return first[-1]
    clog = root / "CHANGELOG.md"
    if not clog.exists():
        return None
    m = re.search(r"^## \[[^\]]+\] - (\d{4}-\d{2}-\d{2})", clog.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def section(clog_text: str, tag: str) -> str | None:
    head = f"## [{tag}]"
    i = clog_text.find(head)
    if i < 0:
        return None
    return clog_text[i:].split("\n## ", 1)[0]


def fill_scaffold(text: str, tag: str, body: str) -> str:
    """Replace a bare "- (fill in)" scaffold under ## [tag] with the review line and the draft.
    A section a person has written is never touched; no draft leaves the scaffold as it is."""
    sec = section(text, tag)
    if not body or sec is None or sec.split("\n", 1)[1:2] != [f"\n- {FILL}\n"]:
        return text
    first = sec.split("\n", 1)[0]
    return text.replace(sec, f"{first}\n\n{REVIEW_LINE}\n\n{body}\n", 1)


def _items(sec: str) -> list[tuple[str, str]]:
    """[(heading, item text)] for each top-level bullet, continuation lines joined."""
    items, head, cur = [], "", None
    for ln in sec.split("\n")[1:]:
        if ln.startswith("### "):
            head, cur = ln[4:].strip(), None
        elif ln.startswith("- "):
            cur = [head, ln[2:].strip()]
            items.append(cur)
        elif cur is not None and ln.startswith("  ") and ln.strip():
            cur[1] += " " + ln.strip()
        elif not ln.strip():
            cur = None
    return [(h, t) for h, t in items]


def lint(sec: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one CHANGELOG section."""
    errors, warnings = [], []
    for head, text in _items(sec):
        if FILL in text:
            continue
        short = text[:60] + ("…" if len(text) > 60 else "")
        if head.lower() == "breaking" and not re.search(r"\bmigrate:", text, re.I):
            errors.append(f"Breaking item has no 'Migrate:' line: {short}")
        plain = re.sub(r"`[^`]*`", lambda m: m.group(0).strip("`"), text)
        for what, rx in (("a file path", _PATH), ("a function name", _FUNC), ("a commit hash", _SHA),
                         ("an internal code", _CODE)):
            hit = rx.search(plain)
            if hit:
                warnings.append(f"{what} ({hit.group(0)}) in: {short}")
        n = len([s for s in _SENT.split(text) if s.strip()])
        if n > 4:
            warnings.append(f"{n} sentences (keep to 4) in: {short}")
    return errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "draft":
        since = argv[argv.index("--since") + 1] if "--since" in argv else default_since()
        print(draft(argv[1], since) or "(no user-facing commits)")
        return 0
    if len(argv) == 2 and argv[0] == "lint":
        sec = section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), argv[1])
        if sec is None:
            print(f"✗ CHANGELOG.md has no heading ## [{argv[1]}]"); return 1
        errors, warnings = lint(sec)
        for w in warnings:
            print(f"  ! {w}")
        for e in errors:
            print(f"  ✗ {e}")
        return 1 if errors else 0
    print(__doc__)
    return 0 if argv[:1] in ([], ["-h"], ["--help"]) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
