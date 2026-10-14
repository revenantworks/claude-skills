#!/usr/bin/env python3
"""settings_layout.py: one read-only map of every settings level, permission rule and hook. Stdlib only.

gatewarden's `layout` entry. Run, never read into context. It reads and never writes: no
settings file, no hook folder, no modes file, no state folder is created or changed.

    python settings_layout.py [--project DIR] [--home DIR] [--settings F ...]
                              [--events FILE] [--since DAYS] [--json OUT]

What it reads (references/layout.md):
  settings   managed, local, project and user files (or the --settings list): permission rules,
             additionalDirectories, defaultMode, enabledPlugins and every hook entry
  plugins    every hooks/hooks.json under <home>/.claude/plugins/; one with a "modules" list is
             a Revenantworks mod (mods/ in the skills repo), shown by name with the switch file
  events     gatewarden's event log (GATEWARDEN_EVENTS, else <state>/events.jsonl and its .1
             rotation; <state> is GATEWARDEN_STATE, else <home>/.claude/gatewarden) and the
             modes file beside it, for which rules interrupt most

What it prints: the levels; every rule and hook with where it lives; overlaps (a rule in two
files, a rule allowed and denied, an allow a deny shadows, a hook wired twice); the rules the
event log shows interrupting most; and one proposed home per rule and hook, with the reason.
Hooks are named by their script file only, never by the full command line, and no `env` value
is read. Exit codes: 0 map written, 2 input error, 3 NOT-RUN (no settings file and no event
log), 4 crashed (exception type only).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "hooks"))
import perm_common as pc  # noqa: E402
from warden_fs import redact, write_json  # noqa: E402

DAY = 86400.0
GATEWARDEN_HOOKS = {"push_gate", "ci_stamp", "hyperv_lock", "call_cap", "launch_throttle", "heredoc_guard",
                    "golive_block", "warden_digest", "warden_review"}
DISPATCH_HOOKS = {"dispatch_gate", "dispatch_ledger_guard"}
HARD = {"push_gate.irreversible", "push_gate.unreadable", "golive_block", "hyperv_lock"}
CRED = re.compile(r"(?i)(\.ssh|\.aws|\.gnupg|\.npmrc|\.netrc|\.env\b|credentials|\.docker/config|secrets?)")
SCRIPT = re.compile(r"""([^\s"'\\/]+\.(?:py|sh|ps1|js|mjs|ts|cmd|bat))\b""", re.I)
SCOPE_ORDER = ("managed", "local", "project", "user", "given")
_HOME: list[str] = []  # the --home folder, shown as ~ like the real one


def show(path: str) -> str:
    """A path for output: the read home (real or --home) reads ~, then warden_fs redaction."""
    p = os.path.abspath(path) if os.path.isabs(path) else path
    for h in _HOME:
        if p == h or p.startswith(h + os.sep):
            p = "~" + p[len(h):]
            break
    return redact(p)


def discover(project: str, home: str) -> list[tuple[str, str]]:
    """(scope, path) for every settings file that exists, managed first; home is overridable."""
    pf = os.environ.get("ProgramFiles")
    cands = [
        ("managed", os.path.join(pf, "ClaudeCode", "managed-settings.json") if pf else ""),
        ("managed", "/Library/Application Support/ClaudeCode/managed-settings.json"),
        ("managed", "/etc/claude-code/managed-settings.json"),
        ("local", os.path.join(project, ".claude", "settings.local.json")),
        ("project", os.path.join(project, ".claude", "settings.json")),
        ("user", os.path.join(home, ".claude", "settings.json")),
    ]
    return [(s, p) for s, p in cands if p and os.path.isfile(p)]


def hook_label(command: str) -> str:
    """The hook's script file name, or its first word; never the whole command line."""
    m = SCRIPT.findall(command or "")
    if m:
        return m[-1]
    first = (command or "").strip().split()
    return os.path.basename(first[0]) if first else "?"


def family(label: str) -> str:
    stem = os.path.splitext(label)[0]
    if stem in GATEWARDEN_HOOKS:
        return "gatewarden"
    if stem in DISPATCH_HOOKS:
        return "dispatchwright"
    return "other"


def read_settings(pairs: list[tuple[str, str]]) -> tuple[list[dict], list[dict], list[dict]]:
    """files, rules, hooks. Rule and hook rows carry their file's scope and redacted path."""
    files, rules, hooks = [], [], []
    for scope, path in pairs:
        info = pc.load(path)
        data = info["data"] or {}
        where = show(path)
        tracked = pc.is_tracked(path)
        files.append({"scope": scope, "path": where, "tracked": tracked, "error": info["error"],
                      "defaultMode": (data.get("permissions") or {}).get("defaultMode"),
                      "enabledPlugins": sorted(k for k, v in (data.get("enabledPlugins") or {}).items() if v)})
        if not info["data"]:
            continue
        perms = data.get("permissions") or {}
        for kind, items in pc.rules_of(data).items():
            for r in items:
                rules.append({"kind": kind, "rule": r, "scope": scope, "file": where, "tracked": tracked})
        for d in perms.get("additionalDirectories") or []:
            if isinstance(d, str):
                rules.append({"kind": "directory", "rule": show(d), "scope": scope, "file": where,
                              "tracked": tracked})
        for event, groups in (data.get("hooks") or {}).items():
            for g in groups if isinstance(groups, list) else []:
                for h in (g or {}).get("hooks") or []:
                    label = hook_label(str(h.get("command") or h.get("url") or ""))
                    hooks.append({"event": event, "matcher": str((g or {}).get("matcher", "")), "hook": label,
                                  "family": family(label), "scope": scope, "file": where, "tracked": tracked})
    return files, rules, hooks


def read_plugins(home: str) -> list[dict]:
    """Every installed plugin hooks file; a "modules" list marks a Revenantworks-style mod."""
    root = os.path.join(home, ".claude", "plugins")
    out = []
    if not os.path.isdir(root):
        return out
    base_depth = root.rstrip(os.sep).count(os.sep)
    for dp, dns, fns in os.walk(root):
        if dp.count(os.sep) - base_depth > 7:
            dns[:] = []
            continue
        dns[:] = [d for d in dns if d not in ("node_modules", ".git")]
        if os.path.basename(dp) == "hooks" and "hooks.json" in fns:
            plugin_dir = os.path.dirname(dp)
            name = os.path.basename(plugin_dir)
            try:
                with open(os.path.join(plugin_dir, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
                    name = json.load(fh).get("name") or name
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(dp, "hooks.json"), encoding="utf-8") as fh:
                    hj = json.load(fh)
            except (OSError, ValueError):
                out.append({"plugin": name, "mod": False, "events": [], "error": "unreadable hooks.json"})
                continue
            events = sorted((hj.get("hooks") or {}).keys()) if isinstance(hj, dict) else []
            out.append({"plugin": name, "mod": bool(isinstance(hj, dict) and hj.get("modules")),
                        "events": events, "path": show(plugin_dir)})
    return sorted(out, key=lambda p: p["plugin"])


def state_dir(home: str) -> str:
    return os.environ.get("GATEWARDEN_STATE") or os.path.join(home, ".claude", "gatewarden")


def read_events(path: str, since_days: float) -> tuple[list[dict], bool]:
    since = time.time() - since_days * DAY
    rows, found = [], False
    for p in (path + ".1", path):
        try:
            with open(p, encoding="utf-8") as fh:
                found = True
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and float(r.get("at", 0) or 0) >= since:
                        rows.append(r)
        except OSError:
            pass
    return rows, found


def mode_of(rule: str, cfg: dict) -> str:
    """The modes file's entry for the rule or its hook, else guard for a hard rule, else the default."""
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    for key in (rule, rule.split(".", 1)[0]):
        if rules.get(key) in ("watch", "nudge", "guard"):
            return rules[key]
    if rule in HARD:
        return "guard"
    return cfg.get("default") if cfg.get("default") in ("watch", "nudge", "guard") else "watch"


def interruptions(rows: list[dict], cfg: dict) -> list[dict]:
    by = defaultdict(list)
    for r in rows:
        by[str(r.get("rule") or "?")].append(r)
    out = []
    for rule, rs in by.items():
        c = Counter(str(r.get("outcome") or "") for r in rs)
        out.append({"rule": rule, "events": len(rs), "blocked": c["blocked"], "nudged": c["nudged"],
                    "logged": c["logged"], "sessions": len({r.get("session") for r in rs}),
                    "mode": mode_of(rule, cfg)})
    # Interrupting first: a refusal stops the owner, a nudge stops Claude; a watch line stops nobody.
    return sorted(out, key=lambda x: (-(x["blocked"] * 2 + x["nudged"]), -x["events"], x["rule"]))


def overlaps(rules: list[dict], hooks: list[dict], plugins: list[dict]) -> list[dict]:
    out = []
    seen = defaultdict(list)
    for r in rules:
        seen[(r["kind"], r["rule"])].append(r)
    for (kind, rule), rs in sorted(seen.items()):
        if len({x["file"] for x in rs}) > 1:
            out.append({"kind": "duplicate", "rule": rule, "rule_kind": kind,
                        "where": sorted({f"{x['scope']}:{x['file']}" for x in rs}),
                        "note": "the same rule in more than one file; one copy is enough"})
    denies = [r for r in rules if r["kind"] == "deny"]
    for r in rules:
        if r["kind"] not in ("allow", "ask"):
            continue
        tool, spec = pc.parse_rule(r["rule"])
        sample = pc.sample_of(spec) if spec else ""
        for d in denies:
            dt, dspec = pc.parse_rule(d["rule"])
            if not pc.tool_family_match(dt, tool):
                continue
            same = d["rule"] == r["rule"]
            if same or (spec is not None and pc.spec_matches(tool, dspec, sample)) or dspec is None:
                out.append({"kind": "conflict" if same else "shadowed", "rule": r["rule"], "rule_kind": r["kind"],
                            "where": [f"{r['scope']}:{r['file']}", f"{d['scope']}:{d['file']}"],
                            "note": f"deny {d['rule']} is checked first, so this {r['kind']} rule never decides"})
                break
    wired = defaultdict(list)
    for h in hooks:
        wired[(h["event"], h["hook"])].append(h)
    for (event, hook), hs in sorted(wired.items()):
        if len(hs) > 1:
            out.append({"kind": "hook-twice", "rule": hook, "rule_kind": event,
                        "where": sorted({f"{x['scope']}:{x['file']}" for x in hs}),
                        "note": "wired more than once, so it fires more than once on the same call"})
    mods = sorted(p["plugin"] for p in plugins if p.get("mod"))
    for h in hooks:
        if h["family"] == "gatewarden" and mods:
            out.append({"kind": "mod-beside-hook", "rule": h["hook"], "rule_kind": h["event"],
                        "where": [f"{h['scope']}:{h['file']}"] + mods,
                        "note": "a mod may stand in for this hook (RW_MOD_<ID>=1, references/hooks.md); "
                                "check one of them is switched off for this call"})
            break
    return out


def propose(rules: list[dict], hooks: list[dict]) -> list[dict]:
    """One proposed home per rule and per hook, with the reason. A proposal only; nothing moves."""
    out = []
    grouped = defaultdict(list)
    for r in rules:
        grouped[(r["kind"], r["rule"])].append(r)
    for (kind, rule), rs in sorted(grouped.items()):
        now = sorted({x["scope"] for x in rs}, key=SCOPE_ORDER.index)
        tracked = any(x["tracked"] for x in rs)
        home, why = now[0], "where it is: nothing here suggests a better level"
        if "managed" in now:
            home, why = "managed", "an administrator's rule; it stays managed and wins over every other level"
        elif kind == "ask" and (tracked or "project" in now):
            home, why = "local", ("an ask rule in a tracked or shared file stalls an unattended run; keep it in the "
                                  "untracked settings.local.json, or make it a deny (rule ask-in-tracked)")
        elif kind == "directory":
            home, why = ("local", "an added directory is a machine path; keep it out of the shared project file") \
                if "project" in now else (now[0], "a machine path, kept where it is")
        elif re.search(r"\(\./|\(\*\*/|\([^)~/]*\.\w+\)", rule):
            home, why = "project", "the rule names a repo-relative path, so it travels with the repo"
        elif kind == "deny" and CRED.search(rule):
            home, why = "user", "a credential-path deny guards every project, so it belongs in user settings"
        elif re.search(r"\((?:~|/|[A-Za-z]:)", rule):
            home, why = "user", "the rule names a home or absolute path, so it belongs to this machine's user settings"
        if len(now) > 1 and home in now and "managed" not in now:
            why += f"; drop the copies in {', '.join(s for s in now if s != home)}"
        out.append({"what": f"{kind} {rule}", "now": now, "home": home, "why": why})
    wired = defaultdict(list)
    for h in hooks:
        wired[(h["event"], h["hook"])].append(h)
    for (event, hook), hs in sorted(wired.items()):
        now = sorted({x["scope"] for x in hs}, key=SCOPE_ORDER.index)
        fam = hs[0]["family"]
        if "managed" in now:
            home, why = "managed", "an administrator's hook; it stays managed"
        elif fam in ("gatewarden", "dispatchwright"):
            home, why = "user", (f"a {fam} hook is installed once in ~/.claude/hooks/ and wired in user settings; "
                                 "a second wiring in a project double-fires")
        else:
            home, why = now[0], "a repo's own hook stays with the repo; a personal one belongs in user settings"
        if len(now) > 1:
            why += f"; drop the copies in {', '.join(s for s in now if s != home)}"
        out.append({"what": f"hook {event} {hook}", "now": now, "home": home, "why": why})
    return out


def print_text(m: dict) -> None:
    print(f"settings levels ({len(m['files'])}):")
    for f in m["files"]:
        extra = f"  ERROR {f['error']}" if f["error"] else ""
        print(f"  {f['scope']:8} {f['path']}  tracked={'yes' if f['tracked'] else 'no'}"
              f"  defaultMode={f['defaultMode'] or '-'}  plugins={len(f['enabledPlugins'])}{extra}")
    print(f"rules ({len(m['rules'])}):")
    for r in m["rules"]:
        print(f"  {r['kind']:9} {r['rule']}  [{r['scope']}]")
    print(f"hooks ({len(m['hooks'])}):")
    for h in m["hooks"]:
        print(f"  {h['event']:16} [{h['matcher'] or '*'}] {h['hook']}  {h['family']}  [{h['scope']}]")
    if m["plugins"]:
        print(f"plugin hooks ({len(m['plugins'])}):")
        for p in m["plugins"]:
            print(f"  {p['plugin']}  {'mod' if p.get('mod') else 'plugin'}  events={','.join(p.get('events') or []) or '-'}")
    print(f"overlaps ({len(m['overlaps'])}):")
    for o in m["overlaps"]:
        print(f"  {o['kind']:15} {o['rule_kind']} {o['rule']}  in {' + '.join(o['where'])}  - {o['note']}")
    ev = m["events"]
    print(f"interruptions, last {ev['since_days']:g} days ({ev['log'] or 'no event log'}):")
    for i in ev["rules"][:15]:
        print(f"  {i['rule']:26} mode={i['mode']:5} blocked={i['blocked']} nudged={i['nudged']} "
              f"logged={i['logged']} sessions={i['sessions']}")
    print(f"proposed homes ({len(m['homes'])}):")
    for h in m["homes"]:
        print(f"  {h['what']}  now={'+'.join(h['now'])} -> {h['home']}  - {h['why']}")
    print("A map and proposals only: nothing was written. Moving a rule is the owner's edit "
          "(or gatewarden harden's finished file); where a non-permission rule lives is rigwright's.")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="settings_layout.py", description="gatewarden layout: read-only settings map")
    ap.add_argument("--project", default=None)
    ap.add_argument("--home", default=None, help="home folder to read (default: the real one)")
    ap.add_argument("--settings", nargs="*", default=None, help="read these files instead of discovering")
    ap.add_argument("--events", default=None, help="event log path (default: gatewarden's)")
    ap.add_argument("--since", type=float, default=28.0, help="days of events to read (default 28)")
    ap.add_argument("--json", dest="out", default=None, help="write JSON here ('-' for stdout)")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    home = os.path.abspath(a.home or os.path.expanduser("~"))
    project = os.path.abspath(a.project or os.getcwd())
    _HOME[:] = [home]
    if a.settings is not None:
        missing = [p for p in a.settings if not os.path.isfile(p)]
        if missing:
            print(f"error: {len(missing)} settings file(s) not found", file=sys.stderr)
            return 2
        pairs = [("given", p) for p in a.settings]
    else:
        pairs = discover(project, home)
    files, rules, hooks = read_settings(pairs)
    plugins = read_plugins(home)
    sdir = state_dir(home)
    log = a.events or os.environ.get("GATEWARDEN_EVENTS") or os.path.join(sdir, "events.jsonl")
    rows, found = read_events(log, a.since)
    try:
        with open(os.environ.get("GATEWARDEN_MODES") or os.path.join(sdir, "modes.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        cfg = cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        cfg = {}
    if not files and not found:
        print("layout: NOT-RUN: no settings file at any level and no gatewarden event log", file=sys.stderr)
        return 3
    switch = os.path.join(home, ".claude", "revenantworks", "switches.json")
    m = {"tool": "gatewarden.settings_layout", "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "files": files, "rules": rules, "hooks": hooks, "plugins": plugins,
         "mods_switch_file": show(switch) if os.path.isfile(switch) else None,
         "overlaps": overlaps(rules, hooks, plugins),
         "events": {"log": show(log) if found else None, "since_days": a.since,
                    "rules": interruptions(rows, cfg)},
         "homes": propose(rules, hooks)}
    if a.out:
        write_json(m, a.out)
    if a.out != "-":
        print_text(m)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never echo file content in a crash
        print(f"layout: crashed ({type(exc).__name__})", file=sys.stderr)
        sys.exit(4)
