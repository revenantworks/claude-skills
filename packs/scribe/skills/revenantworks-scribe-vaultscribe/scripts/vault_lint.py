"""vaultscribe structure, trust and privacy check for an LLM wiki vault. Python 3 stdlib only;
no network. Read-only: it writes nothing anywhere.

Usage
  python vault_lint.py [VAULT] [--today YYYY-MM-DD] [--no-git] [--review N]

VAULT is the vault root (default: the current folder): it holds raw/ (sources) and wiki/ (pages,
with index.md, log.md and privacy-signals.md at wiki/ root). Setup copies this file into the
vault's tools/ folder, so `python tools/vault_lint.py` run from the vault root lints it.

It checks structure, never truth. Output, one line each:
  PROBLEM <CODE>: <detail>   a defect; any PROBLEM line makes the exit code 1
  NEW: <raw path>            a non-empty raw file no page cites yet (what `ingest new` reads)
  REVIEW: <page> (...)       the oldest pages by `updated:`, for a read against their sources
  ADVICE: <text>             a threshold crossed (privacy signals, page count)
  NOT-RUN: <check> (<why>)   a check that could not run (git absent); never a pass
Codes: DUP-NAME BROKEN-LINK NO-SOURCES BAD-SOURCE NOT-INDEXED INDEX-MISSING ORPHAN
REMOTE-EMBED HTML-IMG IFRAME SCRIPT HTML-COMMENT RAW-CHANGED OVERSIZE EMAIL USER-PATH SECRET.
A privacy or secret hit names the file and line only: the value is never printed.

Exit codes: 0 clean, 1 problems found, 2 usage error (no wiki/ folder or a bad argument).
Reference: references/lint-review.md.
"""
import argparse
import datetime
import pathlib
import re
import subprocess
import sys

SPECIAL = {"index", "log", "privacy-signals"}
SNAPSHOTS = "raw/snapshots/"   # dated copies written by vault_snapshot.py
NOTES = "raw/notes/"           # the user's own notes: the user may edit them
OK_FILE = "raw-removed-ok.txt"  # raw paths the user changed or removed on purpose
SIGNAL_DAYS, SIGNAL_LIMIT, PAGE_ADVICE, SIZE_LIMIT = 30, 3, 200, 10_000_000

LINK = re.compile(r"(?<!!)\[\[([^\]|#\\]+)")
CODE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]*`", re.S)
EMAIL = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@(?![A-Z0-9-]*\.?noreply\.)(?!users\.noreply\.github\.com\b)"
    r"[A-Z0-9-]+(?:\.[A-Z0-9-]+)*\.[A-Z]{2,}\b")
PLACEHOLDER = r"(?!(?:owner|user|username|you|your-name|name|public|default|shared|runner)\b|<|\$|%|\{)"
USER_PATH = re.compile(r"(?i)(?:[\\/]Users[\\/]+|(?<![\w.])/home/)" + PLACEHOLDER + r"[A-Za-z0-9_.-]+")
SECRET = re.compile(
    r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{36}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY")
ACTIVE = [
    ("REMOTE-EMBED", re.compile(r"(?i)!\[[^\]]*\]\(\s*<?(?:https?:)?//")),
    ("HTML-IMG", re.compile(r"(?i)<img\b")),
    ("IFRAME", re.compile(r"(?i)<iframe\b")),
    ("SCRIPT", re.compile(r"(?i)<script\b")),
    ("HTML-COMMENT", re.compile(r"<!--")),
]


def read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def norm(name):
    return name.strip().removesuffix(".md").split("/")[-1].casefold()


def links(text):
    return {norm(found) for found in LINK.findall(CODE.sub("", text))}


def front_matter(text):
    match = re.match(r"﻿?---\r?\n(.*?)\r?\n---\s*(?:\n|$)", text, re.S)
    return match.group(1).splitlines() if match else []


def sources_of(lines):
    found, active = [], False
    for line in lines:
        item = re.match(r"\s*-\s+(.+?)\s*$", line)
        if re.match(r"sources:\s*$", line):
            active = True
        elif active and item:
            found.append(item.group(1).strip("\"'"))
        else:
            active = False
    return found


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def git_lines(root, *args):
    """git output lines, or None when git is absent or this is not a work tree."""
    no_window = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    try:
        done = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=root, stdin=subprocess.DEVNULL,
                              capture_output=True, encoding="utf-8", errors="replace", **no_window)
    except OSError:
        return None
    return done.stdout.splitlines() if done.returncode == 0 else None


def lint(root, today=None, use_git=True, review=5):
    """Return (output lines, problem count). Reads only; never writes."""
    root = pathlib.Path(root)
    wiki, raw = root / "wiki", root / "raw"
    today = today or datetime.date.today()
    problems, info = [], []

    files = sorted(p for p in wiki.rglob("*.md") if p.parent != wiki or p.stem not in SPECIAL)
    pages = {}
    for path in files:
        if norm(path.stem) in pages:
            problems.append(f"DUP-NAME: {path.relative_to(root).as_posix()} shares a name with "
                            f"{pages[norm(path.stem)].relative_to(root).as_posix()}")
        else:
            pages[norm(path.stem)] = path
    inbound = {name: 0 for name in pages}
    index = wiki / "index.md"
    indexed = links(read(index)) if index.is_file() else set()
    dated, cited = [], set()

    for name, path in pages.items():
        text = read(path)
        label = path.relative_to(root).as_posix()
        for target in sorted(links(text)):
            if target in inbound:
                if target != name:
                    inbound[target] += 1
            elif target not in SPECIAL:
                problems.append(f"BROKEN-LINK: {label} links [[{target}]], which is no page")
        front = front_matter(text)
        sources = sources_of(front)
        cited.update(sources)
        if not sources and path.parent != wiki:  # a hub at wiki/ root links pages; it makes no claim
            problems.append(f"NO-SOURCES: {label} has no sources in its front matter")
        for source in sources:
            if not source.startswith("raw/") or ".." in source.split("/") or not (root / source).is_file():
                problems.append(f"BAD-SOURCE: {label} cites {source}, which is not a file under raw/")
        if name not in indexed:
            problems.append(f"NOT-INDEXED: {label} is not linked from wiki/index.md")
        visible = CODE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        for code, pattern in ACTIVE:
            for hit in pattern.finditer(visible):
                problems.append(f"{code}: {label}:{line_of(visible, hit.start())}")
        updated = next((ln.split(":", 1)[1].strip() for ln in front if ln.startswith("updated:")), "")
        dated.append((updated or "0000-no-date", name))

    for gone in sorted(indexed - set(pages) - SPECIAL):
        problems.append(f"INDEX-MISSING: wiki/index.md links [[{gone}]], which is no page")
    if len(pages) > 1:
        for name, count in sorted(inbound.items()):
            if count == 0:
                problems.append(f"ORPHAN: {pages[name].relative_to(root).as_posix()} has no page linking to it")

    raw_files = sorted(p for p in raw.rglob("*") if p.is_file()) if raw.is_dir() else []
    waiting = [rel for p in raw_files
               if p.name != ".gitkeep" and p.stat().st_size > 0
               and not (rel := p.relative_to(root).as_posix()).startswith(SNAPSHOTS)
               and rel not in cited]

    if use_git:
        logged = git_lines(root, "log", "--relative", "--no-renames", "--diff-filter=MD", "--name-only",
                           "--format=", "--", "raw")
        working = git_lines(root, "diff", "--relative", "--name-only", "--no-renames", "--diff-filter=MD",
                            "HEAD", "--", "raw")
        if logged is None:
            info.append("NOT-RUN: raw change check (git absent, not a work tree, or no commit yet)")
        else:
            ok_path = root / OK_FILE
            ok = set(read(ok_path).splitlines()) if ok_path.is_file() else set()
            for path in sorted(set(logged + (working or []))):
                if path and path not in ok and not path.endswith(".gitkeep") and not path.startswith(NOTES):
                    problems.append(f"RAW-CHANGED: {path} was changed or removed; if the user meant it, "
                                    f"they add the path to {OK_FILE}")
    else:
        info.append("NOT-RUN: raw change check (--no-git)")

    for path in sorted(wiki.rglob("*.md")) + raw_files:
        label = path.relative_to(root).as_posix()
        if path.stat().st_size > SIZE_LIMIT:
            problems.append(f"OVERSIZE: {label} is over 10 MB")
            continue
        text = read(path)
        for code, pattern in (("EMAIL", EMAIL), ("USER-PATH", USER_PATH), ("SECRET", SECRET)):
            hit = pattern.search(text)
            if hit:
                tail = "; rotate it first, then remove it" if code == "SECRET" else ""
                problems.append(f"{code}: {label}:{line_of(text, hit.start())} (value not shown{tail})")

    signals = 0
    log = wiki / "privacy-signals.md"
    cutoff = today - datetime.timedelta(days=SIGNAL_DAYS)
    for line in (read(log).splitlines() if log.is_file() else []):
        try:
            if datetime.date.fromisoformat(line.strip()[:10]) >= cutoff:
                signals += 1
        except ValueError:
            continue

    out = [f"pages: {len(pages)}", f"privacy signals, last {SIGNAL_DAYS} days: {signals}",
           f"raw files waiting to be ingested: {len(waiting)}"]
    out += [f"NEW: {path}" for path in waiting]
    if signals >= SIGNAL_LIMIT:
        out.append(f"ADVICE: {signals} privacy signals in {SIGNAL_DAYS} days (limit {SIGNAL_LIMIT}). Move "
                   "personal material to a git-ignored private/ folder; moving never erases git history.")
    if len(pages) >= PAGE_ADVICE:
        out.append(f"ADVICE: {len(pages)} pages. Split wiki/index.md by group.")
    out += [f"REVIEW: {name} (updated {updated.replace('0000-no-date', 'never')})"
            for updated, name in sorted(dated)[:review]]
    out += info
    out += [f"PROBLEM {p}" for p in problems]
    out.append(f"problems: {len(problems)}")
    return out, len(problems)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint an LLM wiki vault (read-only).")
    ap.add_argument("vault", nargs="?", default=".")
    ap.add_argument("--today", help="YYYY-MM-DD; the day the privacy-signal window ends (default today)")
    ap.add_argument("--no-git", action="store_true", help="skip the raw change check (reported NOT-RUN)")
    ap.add_argument("--review", type=int, default=5, help="how many oldest pages to list for review")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.vault)
    if not (root / "wiki").is_dir():
        print(f"usage error: {root} has no wiki/ folder; run setup first or pass the vault root")
        return 2
    try:
        today = datetime.date.fromisoformat(a.today) if a.today else None
    except ValueError:
        print(f"usage error: --today {a.today!r} is not YYYY-MM-DD")
        return 2
    out, count = lint(root, today=today, use_git=not a.no_git, review=a.review)
    print("\n".join(out))
    return 1 if count else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
