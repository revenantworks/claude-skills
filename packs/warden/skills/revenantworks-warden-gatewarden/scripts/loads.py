#!/usr/bin/env python3
"""gatewarden loads: skills that load twice, sit on the wrong surface, and what the listing costs.

Run, never read into context. Stdlib only. Read-only: it never edits a settings file.

    loads.py [--home DIR] [--project DIR ...] [--retired NAME ...] [--json OUT]

Sources (each optional; a missing one is listed under `not_checked`):
  user          <home>/skills/<dir>/SKILL.md          (a junction is resolved once)
  project       <project>/.claude/skills/<dir>/SKILL.md
  synced        <home>/skills/synced/<account>/manifest.json and its skill folders
                (shown in Claude Code as anthropic-skills:<name>)
  plugin        <home>/plugins/installed_plugins.json, each install's skills/ folder; a plugin
                from a local-path marketplace is read in place from that folder, not its cache
  synced-plugin <home>/plugins/synced/<account>/<plugin>/skills/
  overrides     skillOverrides in <home>/settings.json and each project's
                .claude/settings.json and .claude/settings.local.json

Kinds: 1 claude.ai sync twin (synced plus another copy) · 2 synced, no local copy
(a user-created synced skill nothing else carries) · 3 plugin plus local, or two plugins ·
4 user plus project scope, or two folders with one SKILL.md name · 5 stale twin (bodies
differ by hash) · 6 one plugin both installed and synced (the install wins, not a double
load) · 7 a machine-driving skill on claude.ai (a review row, the owner's choice). A twin
already set to "off" in skillOverrides reads `handled`.

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
MACHINE_PACKS = ("warden", "localops")   # drive the user's own machine: mostly NOT-RUN in chat
DESC_CAP = 1536                          # description + when_to_use, per skill, in the listing
BUDGET_DEFAULT = 0.01                    # the listing's share of the context window
WINDOWS = {"200k": 200_000, "1m": 1_000_000}


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


def fm_listing(skill_md: Path) -> dict:
    """What the skill puts in the listing: description + when_to_use characters, and manual-only."""
    fields: dict[str, list[str]] = {}
    manual = False
    try:
        with skill_md.open("r", encoding="utf-8", errors="replace") as f:
            if f.readline().strip() != "---":
                return {"chars": 0, "manual": False}
            current = None
            for _ in range(80):
                line = f.readline()
                if not line or line.strip() == "---":
                    break
                if line[:1] in " \t":
                    if current:
                        fields[current].append(line.strip())
                    continue
                key, _sep, value = line.partition(":")
                value = value.strip().strip("'\"")
                current = key if key in ("description", "when_to_use") else None
                if current:
                    fields[current] = [] if value in (">", "|", ">-", "|-") else [value]
                elif key == "disable-model-invocation":
                    manual = value.lower() == "true"
    except OSError:
        return {"chars": 0, "manual": False}
    return {"chars": sum(len(" ".join(v)) for v in fields.values()), "manual": manual}


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
               "real": real(e), "hash": body_hash(md), "loads": True, **fm_listing(md)}
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
                        "hash": body_hash(folder / "SKILL.md"), "loads": on, "builtin": builtin,
                        **fm_listing(folder / "SKILL.md")})
    return out


def synced_plugin_folders(acct: Path) -> set[str] | None:
    """The folders the synced manifest calls current (<name>~g<generation>), or None with no manifest."""
    data = read_json(acct / "manifest.json")
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), list):
        return None
    out = set()
    for p in data["plugins"]:
        if isinstance(p, dict) and p.get("name"):
            out.add(f"{p['name']}~g{p['generation']}" if p.get("generation") else str(p["name"]))
    return out


def in_place_path(home: Path, market: str, pname: str) -> Path | None:
    """A relative-path plugin of a local-directory marketplace loads from there, not its cache."""
    known = read_json(home / "plugins" / "known_marketplaces.json")
    entry = known.get(market) if isinstance(known, dict) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("source"), dict):
        return None
    if entry["source"].get("source") != "directory" or not entry.get("installLocation"):
        return None
    root = Path(str(entry["installLocation"]))
    catalog = read_json(root / ".claude-plugin" / "marketplace.json")
    plugins = catalog.get("plugins") if isinstance(catalog, dict) else None
    for p in plugins if isinstance(plugins, list) else []:
        if isinstance(p, dict) and p.get("name") == pname and str(p.get("source", "")).startswith("./"):
            return root / str(p["source"])
    return None


def plugin_sources(home: Path, settings: dict, notes: list) -> list[dict]:
    out = []
    enabled = settings.get("enabledPlugins") if isinstance(settings.get("enabledPlugins"), dict) else {}
    reg = home / "plugins" / "installed_plugins.json"
    data = read_json(reg) if reg.is_file() else None
    if not isinstance(data, dict):
        notes.append("installed plugins list")
    else:
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
                path = in_place_path(home, market, pname) or path
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
        current = synced_plugin_folders(acct)
        for plug in sorted(acct.iterdir()):
            if not plug.is_dir() or plug.name.startswith(".") or not (plug / "skills").is_dir():
                continue
            if current is not None and plug.name not in current:
                notes.append(f"old synced plugin folder, not read ({plug.name})")
                continue
            meta = read_json(plug / ".claude-plugin" / "plugin.json") or {}
            ns = meta.get("name") if isinstance(meta, dict) and meta.get("name") else plug.name.split("~")[0]
            out += folder_skills(plug / "skills", "synced-plugin", ns, {"plugin": ns,
                                 "loads": on and enabled.get(f"{plug.name.split('~')[0]}@synced") is not False})
    return out


def overrides(home: Path, projects: list[Path]) -> tuple[dict, dict, dict, dict]:
    """(user settings, user skillOverrides, {key: [files where it is off]}, {key: winning value})."""
    user = read_json(home / "settings.json")
    user = user if isinstance(user, dict) else {}
    off: dict[str, list[str]] = {}
    visibility: dict[str, str] = {}
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
                visibility[str(k)] = str(v)                # user, then project, then local: last wins
                if v == "off":
                    off.setdefault(str(k), []).append(redact(str(f)))
    uo = user.get("skillOverrides") if isinstance(user.get("skillOverrides"), dict) else {}
    return user, dict(uo), off, visibility


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
    # One plugin both installed and synced keeps one label: the session lists it once.
    same_plugin = (len(plug) >= 2 and len({s["label"] for s in plug}) == 1
                   and {s["type"] for s in plug} == {"plugin", "synced-plugin"})
    if plug and (local or (len(plug) >= 2 and not same_plugin)):
        kinds.append(3)
    if len(local) >= 2:
        kinds.append(4)
    hashes = {s["hash"] for s in live if s["hash"]}
    if len(live) >= 2 and len(hashes) > 1:
        kinds.append(5)
    if same_plugin:
        kinds.append(6)
    machine = (any(f"-{p}-" in name for p in MACHINE_PACKS)
               and any(s["type"] in ("synced", "synced-plugin") for s in srcs))
    if machine:
        kinds.append(7)
    key = f"{SYNC_NS}:{name}"
    handled_by = off.get(key, [])
    twin_off = bool(handled_by)
    fixes, add_off = [], False
    status = "handled"
    if 1 in kinds and not twin_off:
        fixes.append(f'skillOverrides "{key}": "off" in user settings (block below)')
        add_off = True
    if 3 in kinds:
        ids = sorted({s["plugin"] for s in plug if s.get("plugin") and s["type"] == "plugin"})
        synced_ids = sorted({s["plugin"] for s in plug if s.get("plugin") and s["type"] == "synced-plugin"})
        ways = [f"claude plugin uninstall {i}" for i in ids] + [f"remove {i} on claude.ai" for i in synced_ids]
        fixes.append("uninstall one copy: " + " | ".join(ways)
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
        if same_plugin:
            fixes.append("the synced plugin differs from this install: update it on claude.ai (chat and Cowork "
                         "run that copy, and the desktop Code tab can); keep the install, it is not the problem")
        elif any(s["type"] == "synced" for s in srcs):
            fixes.append("re-upload the current skill zip on claude.ai by hand (Customize > Skills); "
                         "never switch it off there, that removes it from Cowork too")
        else:
            fixes.append("copies differ: drift.py --pair LIVE TRACKED names the files")
        if status == "handled":
            status = "stale"
    if machine:
        fixes.append("drives this machine: in claude.ai chat mostly NOT-RUN while still costing its description; "
                     "switch it off there only if no chat or Cowork task uses it (that removes it from both)")
        if status == "handled":
            status = "review"
    if not kinds:
        status = "single"
    return {"skill": name, "kinds": kinds, "status": status,
            "sources": [{k: s[k] for k in ("type", "label", "path", "hash", "loads") if k in s}
                        | ({"plugin": s["plugin"]} if s.get("plugin") else {}) for s in srcs],
            "bodies": "n/a" if len([s for s in srcs if s["hash"]]) < 2
            else ("same" if len({s["hash"] for s in srcs if s["hash"]}) == 1 else "differ"),
            "handled": twin_off, "handled_by": handled_by, "fix": fixes, "_add_off": add_off}


def listing_cost(srcs: list[dict], visibility: dict, fraction: float) -> dict:
    """The listing before its budget: (description + name characters) / 3, which fits /skill-doctor."""
    seen: set[str] = set()
    by: dict[str, dict] = {}
    over_cap = set()
    for s in srcs:
        state = visibility.get(s["label"], "on")
        if not s["loads"] or s.get("manual") or state in ("off", "user-invocable-only") or s["label"] in seen:
            continue
        seen.add(s["label"])
        chars = 0 if state == "name-only" else s.get("chars", 0)
        if chars > DESC_CAP:
            over_cap.add(s["name"])
        row = by.setdefault(s["type"], {"copies": 0, "tokens_est": 0})
        row["copies"] += 1
        row["tokens_est"] += (min(chars, DESC_CAP) + len(s["name"])) // 3
    tokens = sum(r["tokens_est"] for r in by.values())
    budget = {k: round(w * fraction) for k, w in WINDOWS.items()}
    return {"copies": sum(r["copies"] for r in by.values()), "tokens_est": tokens, "by_source": by,
            "over_cap": sorted(over_cap), "budget_fraction": fraction, "budget_tokens": budget,
            "over_budget": [k for k, v in budget.items() if tokens > v]}


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
    user_settings, user_over, off, visibility = overrides(home, projects)
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
    fraction = user_settings.get("skillListingBudgetFraction")
    fraction = fraction if isinstance(fraction, (int, float)) and fraction > 0 else BUDGET_DEFAULT
    listing = listing_cost(uniq, visibility, fraction)
    out.update({"counts": counts, "skills_seen": len(by), "listing": listing, "rows": rows, "not_checked": notes,
                "settings_block": block,
                "settings_note": ("gatewarden never writes settings: the owner puts this complete "
                                  "skillOverrides block in user settings (~/.claude/settings.json); "
                                  "where config lives is rigwright's, permission rules are gatewarden's. "
                                  "Re-run after each claude.ai upload.") if block else None})
    if a.out:
        write_json(out, a.out)
    else:
        print(f"skills seen: {len(by)}; " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
        print(f"listing: {listing['copies']} skills, about {listing['tokens_est']} tokens before the budget "
              "(estimate; /skill-doctor and /doctor give the live figures)")
        print(f"budget: {fraction:.1%} of the context window, about {listing['budget_tokens']['200k']} tokens at 200k, "
              f"{listing['budget_tokens']['1m']} at 1M"
              + (f"; OVER at {', '.join(listing['over_budget'])}: the least-used skills lose their descriptions"
                 if listing["over_budget"] else ""))
        if listing["over_cap"]:
            print(f"cut at {DESC_CAP} characters in the listing: " + ", ".join(listing["over_cap"]))
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
