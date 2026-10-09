#!/usr/bin/env python3
"""gatewarden footprint: where Claude Code reached, from existing transcripts, against what was granted.

Run, never read into context. Stdlib only. Read-only.

    footprint.py --json OUT [--since 30] [--depth 3] [--claude-home DIR] [--temp DIR]
                 [--claude-json FILE]

Reads `<claude-home>/projects/**/*.jsonl` (transcripts, subagents included), the user and
project settings files (`permissions.additionalDirectories`, path-scoped allow rules), the
project keys of `~/.claude.json`, and the Claude temp folder. Prints path ROOTS and counts
only: never file contents, never a command line (path-shaped tokens are lifted out of
shell commands; everything else in the command is discarded), and every path is redacted
(home -> ~). Transcript text is data: nothing in it is acted on.
Exit codes: 0 ok, 2 input error (no transcripts folder).
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import header, human, looks_secret, norm, redact, write_json  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Glob", "Grep", "LS", "NotebookRead"}
SHELL_TOOLS = {"Bash", "PowerShell"}
PATH_KEYS = ("file_path", "path", "notebook_path")
PATH_TOOLS = {"Read", "Edit", "Write", "Glob", "Grep", "NotebookEdit", "MultiEdit"}
SPLIT_RE = re.compile(r"""[\s"'`=;|&()<>,]+""")
PATHISH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|/[A-Za-z]/|~[\\/]|/(?:home|Users|tmp|var|etc|opt|mnt|srv|root|private)/)")
CASE_FOLD = os.name == "nt"


def key(p: str) -> str:
    return p.casefold() if CASE_FOLD else p


def under(path: str, root: str) -> bool:
    p, r = key(path), key(root.rstrip("/"))
    return p == r or p.startswith(r + "/")


def absolute(p: str, cwd: str | None) -> str | None:
    p = os.path.expanduser(p.strip())
    if not p:
        return None
    n = norm(p)
    if re.match(r"^[a-z]:/", n) or n.startswith("/"):
        return n
    if cwd:
        return norm(os.path.join(cwd, p))
    return None


def shell_paths(command: str) -> list[str]:
    out = []
    for tok in SPLIT_RE.split(command or ""):
        tok = tok.strip().rstrip(".:")
        if not tok or "://" in tok or not PATHISH_RE.match(tok) or looks_secret(tok):
            continue
        out.append(tok)
    return out


def tool_uses(obj):
    """Yield (name, input) for every tool_use block anywhere in one transcript record."""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and isinstance(o.get("input"), dict):
                yield str(o.get("name", "")), o["input"]
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


def root_of(path: str, depth: int) -> str:
    parts = [s for s in path.split("/") if s]
    lead = "/" if path.startswith("/") else ""
    return lead + "/".join(parts[:depth]) if parts else path


def parse_ts(rec: dict) -> float | None:
    ts = rec.get("timestamp")
    if not isinstance(ts, str):
        return None
    try:
        return float(calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")))
    except ValueError:
        return None


UNREADABLE = [0]  # transcripts whose stat/open failed (e.g. past the Windows path limit); reset in main()


def _mtime(f: Path):
    """mtime, or None when the file cannot be stat'ed (counted, never fatal; first live run 2026-10-02)."""
    try:
        return f.stat().st_mtime
    except OSError:
        UNREADABLE[0] += 1
        return None


def read_transcripts(projects: Path, since_epoch: float):
    """Return (reached events, cwds per project dir, sessions seen, skipped lines, cwd set)."""
    events = []           # (abs path, kind, session)
    cwds_by_proj = defaultdict(set)
    sessions = set()
    skipped = 0
    for f in sorted(projects.rglob("*.jsonl")):
        if "tool-results" in f.parts:
            continue
        proj = f.relative_to(projects).parts[0]
        session = f.stem
        mt = _mtime(f)
        if mt is None:
            continue
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            UNREADABLE[0] += 1
            continue
        old_file = mt < since_epoch
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    skipped += 1
                    continue
                if not isinstance(rec, dict):
                    continue
                cwd = rec.get("cwd") if isinstance(rec.get("cwd"), str) else None
                if cwd:
                    cwds_by_proj[proj].add(norm(cwd))
                if old_file:
                    continue
                ts = parse_ts(rec)
                if ts is not None and ts < since_epoch:
                    continue
                for name, inp in tool_uses(rec):
                    if name in SHELL_TOOLS:
                        for tok in shell_paths(str(inp.get("command", ""))):
                            ap = absolute(tok, cwd)
                            if ap:
                                events.append((ap, "shell", session))
                        sessions.add(session)
                        continue
                    kind = "write" if name in WRITE_TOOLS else "read" if name in READ_TOOLS else "other"
                    for k in PATH_KEYS:
                        v = inp.get(k)
                        if isinstance(v, str) and v:
                            ap = absolute(v, cwd)
                            if ap:
                                events.append((ap, kind, session))
                                sessions.add(session)
    return events, cwds_by_proj, sessions, skipped


def rule_root(spec: str, project: str | None) -> str | None:
    """A path-scoped permission rule's literal prefix, before its first glob character."""
    s = spec.strip()
    if s.startswith("//"):
        p = s[1:]
    elif s.startswith("~/"):
        p = os.path.expanduser(s)
    elif s.startswith("/"):
        if not project:
            return None
        p = project.rstrip("/") + s
    else:
        if not project:
            return None
        p = os.path.join(project, s[2:] if s.startswith("./") else s)
    p = norm(p)
    cut = re.split(r"[*?\[{]", p, maxsplit=1)[0].rstrip("/")
    return cut or None


def granted_roots(claude_home: Path, cwds: set[str], temp: Path):
    """Return [(root, kind, source)] from cwds, settings files and the scratchpad tree."""
    out = []
    for c in sorted(cwds):
        out.append((c, "working-directory", "session cwd"))
    files = [(claude_home / "settings.json", None, "user settings"),
             (claude_home / "settings.local.json", None, "user local settings")]
    for c in sorted(cwds):
        if os.path.isdir(c):
            for name in ("settings.json", "settings.local.json"):
                files.append((Path(c) / ".claude" / name, c, f"project {name}"))
    for path, proj, label in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        perms = data.get("permissions", {}) if isinstance(data, dict) else {}
        for d in perms.get("additionalDirectories", []) or []:
            ap = absolute(str(d), proj)
            if ap:
                out.append((ap, "additionalDirectories", label))
        for rule in perms.get("allow", []) or []:
            m = re.match(r"^(Read|Edit|Write|Glob|Grep|NotebookEdit)\((.+)\)$", str(rule))
            if m:
                r = rule_root(m.group(2), proj)
                if r:
                    out.append((r, f"allow {m.group(1)}", label))
    out.append((norm(str(temp)), "scratchpad", "Claude temp folder"))
    return out


def dir_size(p: Path) -> int:
    total = 0
    for dp, dns, fns in os.walk(p, followlinks=False):
        for fn in fns:
            try:
                total += os.lstat(os.path.join(dp, fn)).st_size
            except OSError:
                pass
    return total


def redact_slug(slug: str) -> str:
    from warden_fs import USERS
    s = slug
    for u in USERS:
        s = re.sub(re.escape(u), "<user>", s, flags=re.I)
    return s


def orphans(projects: Path, cwds_by_proj, temp: Path, claude_json: Path, now: float):
    out = []
    for proj, cwds in sorted(cwds_by_proj.items()):
        if cwds and not any(os.path.exists(c) for c in cwds):
            d = projects / proj
            age = (now - d.stat().st_mtime) / 86400 if d.exists() else 0
            out.append({"kind": "project-transcripts", "path": redact(str(d)),
                        "source": [redact(c) for c in sorted(cwds)][:3], "age_days": round(age),
                        "bytes": dir_size(d), "proposal": "purge"})
    try:
        cj = json.loads(claude_json.read_text(encoding="utf-8"))
        for p in sorted((cj.get("projects") or {}).keys()):
            if not os.path.exists(p):
                out.append({"kind": "claude-json-entry", "path": redact(p), "proposal": "purge"})
    except (OSError, ValueError, AttributeError):
        pass
    if temp.is_dir():
        for proj in sorted(temp.iterdir()):
            if not proj.is_dir():
                continue
            for sess in sorted(proj.iterdir()):
                if sess.is_dir() and not (projects / proj.name / f"{sess.name}.jsonl").exists():
                    out.append({"kind": "scratchpad", "path": redact(str(sess)),
                                "age_days": round((now - sess.stat().st_mtime) / 86400),
                                "bytes": dir_size(sess), "proposal": "remove-folder"})
    seen = set()
    for cwds in cwds_by_proj.values():
        for c in cwds:
            wt = Path(c) / ".claude" / "worktrees"
            if key(str(wt)) in seen or not wt.is_dir():
                continue
            seen.add(key(str(wt)))
            for w in sorted(wt.iterdir()):
                gitf = w / ".git"
                gone = True
                if gitf.is_file():
                    m = re.match(r"gitdir:\s*(.+)", gitf.read_text(encoding="utf-8", errors="replace"))
                    gone = not (m and os.path.isdir(m.group(1).strip()))
                if gone:
                    out.append({"kind": "worktree", "path": redact(str(w)),
                                "age_days": round((now - w.stat().st_mtime) / 86400),
                                "proposal": "worktree-prune"})
    return out


def field_names(projects: Path, since_epoch: float) -> dict:
    """Owner Q37: record and tool-input field NAMES with counts. No path, value, project folder or
    session id reaches the output; a tool name is kept only when it is a plain identifier."""
    rec_fields: dict[str, int] = defaultdict(int)
    tool_fields: dict[str, set] = defaultdict(set)
    records = skipped = files = 0
    for f in sorted(projects.rglob("*.jsonl")):
        if "tool-results" in f.parts:
            continue
        mt = _mtime(f)
        if mt is None or mt < since_epoch:
            continue
        files += 1
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            UNREADABLE[0] += 1
            continue
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    skipped += 1
                    continue
                if not isinstance(rec, dict):
                    continue
                ts = parse_ts(rec)
                if ts is not None and ts < since_epoch:
                    continue
                records += 1
                for k in rec:
                    rec_fields[str(k)] += 1
                for name, inp in tool_uses(rec):
                    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name):
                        tool_fields[name].update(str(k) for k in inp)
    return {"files": files, "records": records, "skipped_lines": skipped,
            "record_fields": dict(sorted(rec_fields.items())),
            "tool_input_fields": {t: sorted(v) for t, v in sorted(tool_fields.items())}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", dest="out", default="-")
    ap.add_argument("--since", type=float, default=30, help="days of transcripts to read")
    ap.add_argument("--depth", type=int, default=3, help="path segments in a reach root")
    ap.add_argument("--claude-home", default=os.path.join(os.path.expanduser("~"), ".claude"))
    ap.add_argument("--claude-json", default=os.path.join(os.path.expanduser("~"), ".claude.json"))
    ap.add_argument("--temp", default=os.path.join(tempfile.gettempdir(), "claude"))
    ap.add_argument("--fields-only", action="store_true",
                    help="report transcript field names and counts only (the first live run, owner Q37)")
    a = ap.parse_args(argv)
    UNREADABLE[0] = 0
    home = Path(a.claude_home)
    projects = home / "projects"
    if not projects.is_dir():
        print("error: no transcripts folder (projects/) under the Claude home given", file=sys.stderr)
        return 2
    now = time.time()
    since = now - a.since * 86400
    if a.fields_only:
        out = header("fields")
        out.update({"mode": "fields", "window_days": a.since, **field_names(projects, since),
                    "unreadable_files": UNREADABLE[0],
                    "note": "field names and counts only; no path, value or project name is read into this report"})
        write_json(out, a.out)
        return 0
    events, cwds_by_proj, sessions, skipped = read_transcripts(projects, since)
    all_cwds = set().union(*cwds_by_proj.values()) if cwds_by_proj else set()
    grants = granted_roots(home, all_cwds, Path(a.temp))

    rows = defaultdict(lambda: {"read": 0, "write": 0, "shell": 0, "other": 0, "sessions": set(), "granted_by": set()})
    hit_grants = set()
    for path, kind, sess in events:
        r = rows[root_of(path, a.depth)]
        r[kind] += 1
        r["sessions"].add(sess)
        for groot, gkind, _src in grants:
            if under(path, groot):
                r["granted_by"].add(gkind)
                hit_grants.add((groot, gkind))
    reach = []
    for root, r in sorted(rows.items(), key=lambda kv: -(kv[1]["read"] + kv[1]["write"] + kv[1]["shell"] + kv[1]["other"])):
        reach.append({"root": redact(root), "read": r["read"], "write": r["write"], "shell": r["shell"],
                      "other": r["other"], "sessions": len(r["sessions"]),
                      "granted_by": sorted(r["granted_by"]) or ["none"]})
    never = [{"root": redact(g), "kind": k, "source": s} for g, k, s in grants
             if k not in ("working-directory", "scratchpad") and (g, k) not in hit_grants]
    out = header("footprint")
    out.update({
        "window_days": a.since, "depth": a.depth, "sessions": len(sessions),
        "events": len(events), "skipped_lines": skipped, "unreadable_files": UNREADABLE[0],
        "reach": reach,
        "reached_not_granted": [r for r in reach if r["granted_by"] == ["none"]],
        "granted_never_reached": never,
        "grants": [{"root": redact(g), "kind": k, "source": s} for g, k, s in grants],
        "orphans": orphans(projects, cwds_by_proj, Path(a.temp), Path(a.claude_json), now),
        "note": "paths only; command text and file contents are never read into this report",
    })
    write_json(out, a.out)
    if a.out and a.out != "-":
        print(f"{len(sessions)} sessions, {len(events)} path events in {a.since:g} days -> {len(reach)} roots; "
              f"{len(out['reached_not_granted'])} reached-not-granted, {len(never)} granted-never-reached, "
              f"{len(out['orphans'])} orphans ({human(sum(o.get('bytes', 0) for o in out['orphans']))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
