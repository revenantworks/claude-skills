#!/usr/bin/env python3
"""gatewarden loads: skills that reach a Claude Code session from more than one source.

Run, never read into context. Stdlib only. Read-only: it never edits a settings file.

    loads.py [--home DIR] [--project DIR ...] [--retired NAME ...] [--json OUT]

Sources (each optional; a missing one is listed under `not_checked`):
  user          <home>/skills/<dir>/SKILL.md          (a junction is resolved once)
  project       <project>/.claude/skills/<dir>/SKILL.md
  synced        <home>/skills/synced/<account>/manifest.json and its skill folders
                (shown in Claude Code as anthropic-skills:<name>)
  plugin        <home>/plugins/installed_plugins.json, each install's skills/ folder
  synced-plugin <home>/plugins/synced/<account>/<plugin>/skills/
  overrides     skillOverrides in <home>/settings.json and each project's
                .claude/settings.json and .claude/settings.local.json

Kinds: 1 claude.ai sync twin (synced plus another copy) · 2 synced, no local copy
(a user-created synced skill nothing else carries) · 3 plugin plus local, or two plugins ·
4 user plus project scope, or two folders with one SKILL.md name · 5 stale twin (bodies
differ by hash). A twin already set to "off" in skillOverrides reads `handled`.

Output: names, redacted paths and SKILL.md hashes only; no file content is printed. The
fix is a proposal: a complete skillOverrides block or one command. Applying a settings
block is the owner's (rigwright places config); gatewarden never writes it.
Exit codes: 0 nothing open, 1 a finding or a stale twin, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import header, norm, redact, write_json  # noqa: E402

SYNC_NS = "anthropic-skills"
BUILTIN_SOURCES = {"anthropic", "anthropic-example"}
SKIP_DIRS = {"synced", ".trash"}


def body_hash(skill_md: Path) -> str | None:
    try:
        data = skill_md.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:12]


def fm_name(skill_md: Path) -> str | None:
    """The `name:` field of the SKILL.md frontmatter, or None. Reads the frontmatter only."""
    try:
        with skill_md.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
            if first != "---":
                return None
            for _ in range(80):
                line = f.readline()
                if not line or line.strip() == "---":
                    return None
                if line.startswith("name:"):
                    v = line.split(":", 1)[1].strip().strip("'\"")
                    return v or None
    except OSError:
        return None
    return None


def real(p: Path) -> str:
    try:
        r = norm(os.path.realpath(p))
    except OSError:
        r = norm(str(p))
    return r.casefold() if os.name == "nt" else r


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def folder_skills(folder: Path, kind: str, ns: str | None = None, extra: dict | None = None) -> list[dict]:
    out = []
    for e in sorted(folder.iterdir(), key=lambda x: x.name.casefold()):
        if e.name in SKIP_DIRS or e.name.startswith("."):
            continue
        md = e / "SKILL.md"
        if not e.is_dir() or not md.is_file():
            continue
        name = fm_name(md) or e.name
        label = f"{ns}:{name}" if ns else name
        row = {"name": name, "type": kind, "label": label, "path": redact(str(e)),
               "real": real(e), "hash": body_hash(md), "loads": True}
        if extra:
            row.update(extra)
        out.append(row)
    return out


def user_sources(home: Path, notes: list) -> list[dict]:
    d = home / "skills"
    if not d.is_dir():
        notes.append("user skills folder")
        return []
    return folder_skills(d, "user")


def project_sources(projects: list[Path], notes: list) -> list[dict]:
    out = []
    for p in projects:
        d = p / ".claude" / "skills"
        if not d.is_dir():
            notes.append(f"project skills folder ({redact(str(p))})")
            continue
        out += folder_skills(d, "project")
    return out


def synced_sources(home: Path, settings: dict, notes: list) -> list[dict]:
    root = home / "skills" / "synced"
    manifests = sorted(root.glob("*/manifest.json")) if root.is_dir() else []
    if not manifests:
        notes.append("synced skills manifest")
        return []
    on = settings.get("syncClaudeAiSkills") is not False
    out = []
    for m in manifests:
        data = read_json(m)
        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            notes.append(f"synced manifest unreadable ({redact(str(m))})")
            continue
        for s in data["skills"]:
            if not isinstance(s, dict) or not s.get("name"):
                continue
            name = str(s["name"])
            folder = m.parent / name
            builtin = s.get("source") in BUILTIN_SOURCES or s.get("creatorType") not in (None, "user")
            out.append({"name": name, "type": "synced", "label": f"{SYNC_NS}:{name}",
                        "path": redact(str(folder)), "real": real(folder),
                        "hash": body_hash(folder / "SKILL.md"), "loads": on, "builtin": builtin})
    return out


def plugin_sources(home: Path, settings: dict, notes: list) -> list[dict]:
    out = []
    reg = home / "plugins" / "installed_plugins.json"
    data = read_json(reg) if reg.is_file() else None
    if not isinstance(data, dict):
        notes.append("installed plugins list")
    else:
        enabled = settings.get("enabledPlugins") if isinstance(settings.get("enabledPlugins"), dict) else {}
        plugins = data.get("plugins") if isinstance(data.get("plugins"), dict) else {}
        for pid, installs in sorted(plugins.items()):
            if not isinstance(installs, list):
                continue
            pname, _, market = pid.partition("@")
            for inst in installs:
                if not isinstance(inst, dict):
                    continue
                path = Path(str(inst.get("installPath") or ""))
                if not str(inst.get("installPath") or "") or not path.is_dir():
                    path = home / "plugins" / "cache" / market / pname / str(inst.get("version", ""))
                meta = read_json(path / ".claude-plugin" / "plugin.json") or {}
                ns = meta.get("name") if isinstance(meta, dict) and meta.get("name") else pname
                skills = path / "skills"
                if not skills.is_dir():
                    continue
                out += folder_skills(skills, "plugin", ns, {"plugin": pid,
                                     "loads": enabled.get(pid) is not False,
                                     "scope": inst.get("scope", "user")})
    root = home / "plugins" / "synced"
    on = settings.get("syncClaudeAiPlugins") is not False
    for acct in sorted(root.iterdir()) if root.is_dir() else []:
        if not acct.is_dir() or acct.name.startswith("."):
            continue
        for plug in sorted(acct.iterdir()):
            if not plug.is_dir() or plug.name.startswith(".") or not (plug / "skills").is_dir():
                continue
            meta = read_json(plug / ".claude-plugin" / "plugin.json") or {}
            ns = meta.get("name") if isinstance(meta, dict) and meta.get("name") else plug.name.split("~")[0]
            out += folder_skills(plug / "skills", "synced-plugin", ns, {"plugin": ns, "loads": on})
    return out


def overrides(home: Path, projects: list[Path]) -> tuple[dict, dict, dict]:
    """(user settings, user skillOverrides, {key: [files where it is off]})."""
    user = read_json(home / "settings.json")
    user = user if isinstance(user, dict) else {}
    off: dict[str, list[str]] = {}
    files = [(home / "settings.json", user)]
    for p in projects:
        for fn in ("settings.json", "settings.local.json"):
            f = p / ".claude" / fn
            d = read_json(f) if f.is_file() else None
            if isinstance(d, dict):
                files.append((f, d))
    for f, d in files:
        so = d.get("skillOverrides")
        if isinstance(so, dict):
            for k, v in so.items():
                if v == "off":
                    off.setdefault(str(k), []).append(redact(str(f)))
    uo = user.get("skillOverrides") if isinstance(user.get("skillOverrides"), dict) else {}
    return user, dict(uo), off


def classify(name: str, srcs: list[dict], off: dict, retired: set[str]) -> dict:
    live = [s for s in srcs if s["loads"]]
    syn = [s for s in live if s["type"] == "synced"]
    local = [s for s in live if s["type"] in ("user", "project")]
    plug = [s for s in live if s["type"] in ("plugin", "synced-plugin")]
    kinds = []
    if syn and (local or plug):
        kinds.append(1)
    if syn and not local and not plug and not any(s.get("builtin") for s in syn):
        kinds.append(2)
    if plug and (local or len(plug) >= 2):
        kinds.append(3)
    if len(local) >= 2:
        kinds.append(4)
    hashes = {s["hash"] for s in live if s["hash"]}
    if len(live) >= 2 and len(hashes) > 1:
        kinds.append(5)
    key = f"{SYNC_NS}:{name}"
    handled_by = off.get(key, [])
    twin_off = bool(handled_by)
    fixes, add_off = [], False
    status = "handled"
    if 1 in kinds and not twin_off:
        fixes.append(f'skillOverrides "{key}": "off" in user settings (block below)')
        add_off = True
    if 3 in kinds:
        ids = sorted({s.get("plugin") for s in plug if s.get("plugin")})
        fixes.append("uninstall one copy: " + " | ".join(f"claude plugin uninstall {i}" for i in ids)
                     + (" (or drop the local copy; owner's choice)" if local else ""))
    if 4 in kinds:
        fixes.append("personal scope wins over project: keep one copy (owner's call; "
                     "gatewarden never proposes removing a skill)")
    open_load = (1 in kinds and not twin_off) or 3 in kinds or 4 in kinds
    if open_load:
        status = "finding"
    elif 2 in kinds:
        if twin_off:
            status = "handled"
        elif name in retired:
            status = "finding"
            add_off = True
            fixes.append(f'skillOverrides "{key}": "off" in user settings (block below); '
                         "delete it on claude.ai by hand (Customize > Skills)")
        else:
            status = "review"
            fixes.append("synced, no local copy: keep it if it is a claude.ai-only skill; "
                         "pass --retired NAME if it is retired")
    if 5 in kinds:
        if any(s["type"] == "synced" for s in srcs):
            fixes.append("re-upload the current skill zip on claude.ai by hand (Customize > Skills); "
                         "never switch it off there, that removes it from Cowork too")
        else:
            fixes.append("copies differ: drift.py --pair LIVE TRACKED names the files")
        if status == "handled":
            status = "stale"
    if not kinds:
        status = "single"
    return {"skill": name, "kinds": kinds, "status": status,
            "sources": [{k: s[k] for k in ("type", "label", "path", "hash", "loads") if k in s}
                        | ({"plugin": s["plugin"]} if s.get("plugin") else {}) for s in srcs],
            "bodies": "n/a" if len([s for s in srcs if s["hash"]]) < 2
            else ("same" if len({s["hash"] for s in srcs if s["hash"]}) == 1 else "differ"),
            "handled": twin_off, "handled_by": handled_by, "fix": fixes, "_add_off": add_off}


def table(rows: list[dict]) -> str:
    lines = ["| skill | kinds | sources | bodies | handled | fix |", "|---|---|---|---|---|---|"]
    for r in rows:
        srcs = ", ".join(s["label"] + ("" if s["loads"] else " (off)") for s in r["sources"])
        lines.append(f"| {r['skill']} | {','.join(map(str, r['kinds']))} | {srcs} | {r['bodies']} | "
                     f"{'yes' if r['handled'] else 'no'} | {'; '.join(r['fix']) or '-'} |")
    return "\n".join(lines)


ORDER = {"finding": 0, "stale": 1, "review": 2, "handled": 3}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--home", default=os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude",
                    help="Claude Code config folder (default ~/.claude)")
    ap.add_argument("--project", action="append", default=[],
                    help="a project folder whose .claude/skills is checked (default: the current folder)")
    ap.add_argument("--retired", action="append", default=[], help="a synced skill name the owner retired")
    ap.add_argument("--json", dest="out", help="write JSON here ('-' for stdout); default prints the table")
    a = ap.parse_args(argv)
    home = Path(os.path.expanduser(a.home))
    if not home.is_dir():
        print("error: Claude config folder not found", file=sys.stderr)
        return 2
    projects = [Path(os.path.expanduser(p)) for p in (a.project or [os.getcwd()])]
    notes: list[str] = []
    user_settings, user_over, off = overrides(home, projects)
    srcs = user_sources(home, notes) + project_sources(projects, notes)
    srcs += synced_sources(home, user_settings, notes) + plugin_sources(home, user_settings, notes)
    seen, uniq = set(), []
    for s in srcs:                       # a junction or a project equal to home counts once
        kind = "local" if s["type"] in ("user", "project") else s["type"]
        key = (kind, s["real"], s["name"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    by: dict[str, list[dict]] = {}
    for s in uniq:
        by.setdefault(s["name"], []).append(s)
    rows = [classify(n, ss, off, set(a.retired)) for n, ss in sorted(by.items())]
    rows = [r for r in rows if r["status"] != "single"]
    rows.sort(key=lambda r: (ORDER[r["status"]], r["skill"]))
    new = {f"{SYNC_NS}:{r['skill']}": "off" for r in rows if r.pop("_add_off")}
    block = None
    if new:
        merged = dict(user_over)
        merged.update(new)
        block = {"skillOverrides": dict(sorted(merged.items()))}
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ORDER}
    out = header("loads")
    out.update({"counts": counts, "skills_seen": len(by), "rows": rows, "not_checked": notes,
                "settings_block": block,
                "settings_note": ("gatewarden never writes settings: the owner puts this complete "
                                  "skillOverrides block in user settings (~/.claude/settings.json); "
                                  "where config lives is rigwright's, permission rules are gatewarden's. "
                                  "Re-run after each claude.ai upload.") if block else None})
    if a.out:
        write_json(out, a.out)
    else:
        print(f"skills seen: {len(by)}; " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
        if rows:
            print(table(rows))
        if notes:
            print("not checked: " + "; ".join(notes))
        if block:
            print("\nProposed user settings block (complete skillOverrides, existing entries kept):")
            print(json.dumps(block, indent=2))
            print(out["settings_note"])
    return 1 if counts["finding"] or counts["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
