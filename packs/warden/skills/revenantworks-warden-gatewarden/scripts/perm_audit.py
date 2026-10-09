#!/usr/bin/env python3
"""perm_audit.py: audit and harden Claude Code permission settings. Stdlib only.

  python perm_audit.py audit  [--settings F ...] [--project DIR] [--platform windows|other]
                              [--no-ask-rule] [--json]
  python perm_audit.py harden --settings F [--platform ...] [--no-ask-rule]
                              [--credential-denies] [--add-hooks DIR [--hooks a,b]] [--hook-denies]
                              [--out-dir DIR]

--add-hooks also writes the hooks-folder denies (HOOK_DENIES); --hook-denies writes them alone.

audit reads every settings level it finds (or the files named), plus the hooks
inside them, and prints findings by rule id with file, line and JSON pointer.
Env values are never printed: each is shown as a sha256 fingerprint.
Exit: 0 clean, 1 findings, 3 NOT-RUN (no settings file found), 4 crash.

harden writes `<name>.hardened.json` beside the original (or in --out-dir), never
the live file, validates it as JSON, and prints one copy command.

Rule ids and their reasons: references/bypass-shapes.md and rule-grammar.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perm_common as pc  # noqa: E402

VERSION = "0.1.0"
NET = re.compile(r"(?i)\b(curl|wget|invoke-webrequest|iwr|invoke-restmethod|irm|nc|ncat|ssh|scp)\b|https?://")
FETCH_EXEC = re.compile(r"(?i)\|\s*(sh|bash|zsh|pwsh|powershell)\b|\biex\b|invoke-expression|\bnpx\b|\buvx\b|pip install")
ENV_READ = re.compile(r"(?i)\bprintenv\b|\$env:|os\.environ|/proc/self/environ|\benv\s*\|")
DEAD_TOOLS = {"Write": "Edit", "MultiEdit": "Edit", "NotebookEdit": "Edit", "Glob": "Read"}
CRED_DENIES = ["Read(~/.ssh/**)", "Edit(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.npmrc)",
               "Read(~/.git-credentials)", "Read(~/.config/gh/**)", "Read(~/AppData/Roaming/GitHub CLI/**)",
               "Read(./.env)", "Read(./.env.*)", "Read(**/.env)"]
# Owner HV2: the hooks protect nothing if Claude can rewrite them. Edit deny rules cover the Write
# and Edit tools and the targets of Bash redirections (permissions.md, read 2026-10-01); they do not
# bind a script that opens files itself, which is why the hooks also check what a command runs.
# The state folder ~/.claude/gatewarden/ is not denied: a controller writes call-caps.json there.
# modes.json in it needs its own owner-installed deny (references/hooks.md, "Protect the modes file").
HOOK_DENIES = ["Edit(~/.claude/hooks/**)"]
HOOK_SET = [("Bash|PowerShell", "push_gate.py"), ("Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit", "hyperv_lock.py"),
            ("Bash|PowerShell", "heredoc_guard.py"), ("*", "call_cap.py"), ("Agent|Task|Workflow", "launch_throttle.py"),
            ("Bash|PowerShell|Read|Write|Edit|MultiEdit|mcp__.*", "golive_block.py")]


def platform_of(arg: str | None) -> str:
    if arg:
        return arg
    return "windows" if sys.platform == "win32" else "other"


def gather(args) -> list[dict]:
    if args.settings:
        pairs = [("given", p) for p in args.settings if os.path.isfile(p)]
    else:
        pairs = pc.discover(args.project or os.getcwd())
    files = []
    for scope, path in pairs:
        info = pc.load(path)
        info["scope"] = scope
        info["tracked"] = pc.is_tracked(path)
        info["rules"] = pc.rules_of(info["data"]) if info["data"] else {"deny": [], "ask": [], "allow": []}
        files.append(info)
    return files


def finding(f, rule_id, sev, pointer, rule_text, reason, needle=None):
    return {"rule_id": rule_id, "severity": sev, "file": f["path"], "line": pc.line_of(f["raw"], needle or rule_text),
            "pointer": pointer, "rule_text": rule_text, "reason": reason}


def audit(files: list[dict], platform: str, ask_rule: bool) -> tuple[list, list, list]:
    out, hooks, env = [], [], []
    all_deny = [(f, i, r) for f in files for i, r in enumerate(f["rules"]["deny"])]
    sandbox = any(((f["data"] or {}).get("sandbox") or {}).get("enabled") is True for f in files)
    ps_denies = {(pc.parse_rule(r)[1] or "").lower() for _, _, r in all_deny if pc.parse_rule(r)[0] == "PowerShell"}
    for f in files:
        if f["error"]:
            out.append({"rule_id": "unparseable", "severity": "high", "file": f["path"], "line": 0, "pointer": "",
                        "rule_text": "", "reason": f"{f['error']}; no rule in this file is in force as written"})
            continue
        d = f["data"]
        for key, val in (d.get("env") or {}).items():
            env.append({"file": f["path"], "key": key, "fingerprint": pc.fingerprint(val)})
        for kind in ("deny", "ask", "allow"):
            for i, r in enumerate(f["rules"][kind]):
                tool, spec = pc.parse_rule(r)
                ptr = f"/permissions/{kind}/{i}"
                if tool in DEAD_TOOLS and spec:
                    out.append(finding(f, "dead-tool-rule", "medium", ptr, r,
                                       f"path rules for {tool} are accepted but never consulted; "
                                       f"write it as {DEAD_TOOLS[tool]}({spec})"))
                field = pc.PRIMARY_FIELD.get(tool)
                if field and spec and spec.startswith(field + ":"):
                    out.append(finding(f, "param-primary-ignored", "high", ptr, r,
                                       f"Tool(param:value) cannot match the primary field `{field}`; Claude Code "
                                       "ignores this rule with a startup warning. Write the plain form instead"))
                if kind == "deny" and tool == "Bash":
                    if platform == "windows" and (spec or "").lower() not in ps_denies:
                        out.append(finding(f, "ps-mirror-missing", "high", ptr, r,
                                           "no PowerShell twin: on Windows Claude can run the same command "
                                           f"through the PowerShell tool; add PowerShell({spec or ''})" if spec else
                                           "no PowerShell twin: add a bare PowerShell deny"))
                    if spec and spec.strip() not in ("*", ""):
                        first = spec.split()[0]
                        sub = " ".join(spec.split()[1:])
                        extra = f", `git -C . {sub}`, `git -c k=v {sub}`" if first == "git" else ""
                        out.append(finding(f, "abs-path-escape", "medium", ptr, r,
                                           f"a Bash rule is not a security boundary: an absolute path (/usr/bin/{first}), "
                                           f"`sh -c \"...\"`{extra} or a script file runs the same thing unmatched; "
                                           "pair it with a PreToolUse hook or the sandbox"))
                if kind == "deny" and tool == "Read" and not sandbox:
                    out.append(finding(f, "read-deny-shell-gap", "medium", ptr, r,
                                       "without the sandbox a Read deny covers the file tools and named-file shell "
                                       "commands (cat, head, sed, redirections) but not `grep -r` from the folder or "
                                       "a script that opens the file itself"))
                if kind == "allow" and tool in pc.SHELL_FAMILY and (spec is None or spec.strip() in ("", "*")):
                    out.append(finding(f, "blanket-allow", "high", ptr, r, "the whole shell tool is allowed"))
                if kind == "allow" and spec:
                    for df, _, dr in all_deny:
                        dt, ds = pc.parse_rule(dr)
                        if pc.tool_family_match(dt, tool) and pc.spec_matches(tool, ds, pc.sample_of(spec)):
                            out.append(finding(f, "allow-under-deny", "low", ptr, r,
                                               f"never takes effect: deny {dr} in {os.path.basename(df['path'])} "
                                               "is checked first and an allow cannot carve out of it"))
                            break
                if kind == "ask" and f["tracked"] and ask_rule:
                    out.append(finding(f, "ask-in-tracked", "high", ptr, r,
                                       "an ask rule in a tracked settings file stalls or denies an unattended run "
                                       "(routine, scheduled task, claude -p): nobody answers. Use allow or deny "
                                       "(named rule, default on; --no-ask-rule turns it off)"))
        perms = d.get("permissions") or {}
        if perms.get("defaultMode") == "bypassPermissions" and not sandbox:
            out.append(finding(f, "bypass-no-sandbox", "high", "/permissions/defaultMode", "bypassPermissions",
                               "bypass mode with no sandbox: every tool call runs unasked on the host"))
        if "mcpServers" in d:
            out.append(finding(f, "mcpservers-in-settings", "medium", "/mcpServers", "mcpServers",
                               "MCP servers belong in .mcp.json or ~/.claude.json; this key is a schema error"))
        if d.get("enableAllProjectMcpServers") is True and f["tracked"]:
            out.append(finding(f, "mcp-enable-all-tracked", "high", "/enableAllProjectMcpServers",
                               "enableAllProjectMcpServers",
                               "a tracked file approves every server any future .mcp.json adds; list them by name"))
        for event, groups in (d.get("hooks") or {}).items():
            for gi, g in enumerate(groups or []):
                for hi, h in enumerate((g or {}).get("hooks") or []):
                    cmd = str(h.get("command") or h.get("url") or "")
                    ptr = f"/hooks/{event}/{gi}/hooks/{hi}"
                    hooks.append({"file": f["path"], "event": event, "matcher": g.get("matcher", ""),
                                  "type": h.get("type"), "command": cmd})
                    for rid, rx, sev, why in (
                            ("hook-network", NET, "high", "the hook reaches the network; hooks run with your user "
                             "rights outside any sandbox and can send data out"),
                            ("hook-fetch-exec", FETCH_EXEC, "high", "the hook fetches or runs code it did not ship"),
                            ("hook-env-read", ENV_READ, "medium", "the hook reads environment variables, where "
                             "tokens often live")):
                        if rx.search(cmd):
                            out.append(finding(f, rid, sev, ptr, cmd, why))
    return out, hooks, env


def print_text(files, findings, hooks, env):
    for f in files:
        print(f"file  {f['path']}  scope={f['scope']} tracked={'yes' if f['tracked'] else 'no'}"
              f"  deny={len(f['rules']['deny'])} ask={len(f['rules']['ask'])} allow={len(f['rules']['allow'])}")
    for e in env:
        print(f"env   {e['key']}  {e['fingerprint']}  ({os.path.basename(e['file'])})")
    for h in hooks:
        print(f"hook  {h['event']} [{h['matcher']}]  {h['command']}  ({os.path.basename(h['file'])})")
    for x in findings:
        print(f"{x['severity'].upper():6} {x['rule_id']:24} {os.path.basename(x['file'])}:{x['line']}  "
              f"{x['rule_text']}  - {x['reason']}")
    print(f"{len(findings)} finding(s) across {len(files)} file(s). This models the documented rules; "
          "it is not the harness.")


def hook_deny_rules(hooks_dir: str | None) -> list[str]:
    """The hooks-folder denies, plus one for a hooks folder outside ~/.claude/hooks."""
    rules = list(HOOK_DENIES)
    if hooks_dir:
        d = hooks_dir.replace("\\", "/").rstrip("/")
        home = os.path.expanduser("~").replace("\\", "/").rstrip("/")
        if d.lower().startswith(home.lower() + "/"):
            d = "~" + d[len(home):]
        if d.startswith("~/"):
            rule = f"Edit({d}/**)"
        elif re.match(r"^[A-Za-z]:/", d):  # a Windows drive path matches in POSIX form: //<letter>/rest
            rule = f"Edit(//{d[0].lower()}/{d[3:]}/**)"
        elif d.startswith("/"):
            rule = f"Edit(//{d.lstrip('/')}/**)"
        else:
            rule = f"Edit(./{d.removeprefix('./')}/**)"
        if not rule.startswith("Edit(~/.claude/hooks/"):
            rules.append(rule)
    return rules


def harden(args, platform) -> int:
    path = args.settings[0]
    info = pc.load(path)
    if info["error"]:
        print(f"harden: {os.path.basename(path)} is {info['error']}; fix it first", file=sys.stderr)
        return 4
    data = info["data"]
    perms = data.setdefault("permissions", {})
    notes = []
    deny = perms.setdefault("deny", [])
    if platform == "windows":
        have = {(pc.parse_rule(r)[1] or "").lower() for r in deny if pc.parse_rule(r)[0] == "PowerShell"}
        for r in list(deny):
            tool, spec = pc.parse_rule(r)
            if tool == "Bash" and (spec or "").lower() not in have:
                twin = f"PowerShell({spec})" if spec else "PowerShell"
                deny.append(twin)
                have.add((spec or "").lower())
                notes.append(f"added {twin}")
    if perms.get("ask") and pc.is_tracked(path) and not args.no_ask_rule:
        for r in perms.pop("ask"):
            if r not in deny:
                deny.append(r)
            notes.append(f"ask -> deny: {r}")
    if args.credential_denies:
        for r in CRED_DENIES:
            if r not in deny:
                deny.append(r)
                notes.append(f"added {r}")
    if args.add_hooks or args.hook_denies:
        for r in hook_deny_rules(args.add_hooks):
            if r not in deny:
                deny.append(r)
                notes.append(f"added {r}")
    if args.add_hooks:
        hooks = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
        existing = json.dumps(hooks)
        wanted = {h.strip().removesuffix(".py") for h in args.hooks.split(",")} if args.hooks else None
        for matcher, script in HOOK_SET:
            cmd = f'python "{args.add_hooks.rstrip("/")}/{script}"'
            if script in existing or (wanted is not None and script[:-3] not in wanted):
                continue
            hooks.append({"matcher": matcher, "hooks": [{"type": "command", "command": cmd, "timeout": 30}]})
            notes.append(f"hook {script} on {matcher}")
        # call_cap also logs each subagent's end (SubagentStop) into its local event log.
        if wanted is None or "call_cap" in wanted:
            stop = data["hooks"].setdefault("SubagentStop", [])
            if "call_cap.py" not in json.dumps(stop):
                cmd = f'python "{args.add_hooks.rstrip("/")}/call_cap.py"'
                stop.append({"hooks": [{"type": "command", "command": cmd, "timeout": 30}]})
                notes.append("hook call_cap.py on SubagentStop")
        # The weekly digest: one line at session start, once a week, never a prompt.
        start = data["hooks"].setdefault("SessionStart", [])
        if "warden_digest.py" not in json.dumps(start):
            cmd = f'python "{args.add_hooks.rstrip("/")}/warden_digest.py"'
            start.append({"hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
            notes.append("hook warden_digest.py on SessionStart")
    if not deny:
        perms.pop("deny")
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    json.loads(text)
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(path)
    out = os.path.join(out_dir, (base[:-5] if base.endswith(".json") else base) + ".hardened.json")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", info["eol"]))
    for n in notes or ["no change needed"]:
        print(f"- {n}")
    print("JSON parse: ok. Schema check: not run (no network fetch; validate with your editor's schema).")
    if platform == "windows":
        print(f'Copy-Item -LiteralPath "{out}" -Destination "{os.path.abspath(path)}"')
    else:
        print(f'cp "{out}" "{os.path.abspath(path)}"')
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="perm_audit.py")
    ap.add_argument("mode", choices=["audit", "harden"])
    ap.add_argument("--settings", action="append")
    ap.add_argument("--project")
    ap.add_argument("--platform", choices=["windows", "other"])
    ap.add_argument("--no-ask-rule", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--credential-denies", action="store_true")
    ap.add_argument("--add-hooks")
    ap.add_argument("--hook-denies", action="store_true",
                    help="add the hooks-folder deny rules without adding hooks (--add-hooks adds them too)")
    ap.add_argument("--hooks", help="comma list: push_gate,hyperv_lock,heredoc_guard,call_cap,launch_throttle,golive_block (warden_digest is always added)")
    ap.add_argument("--out-dir")
    args = ap.parse_args(argv)
    platform = platform_of(args.platform)
    if args.mode == "harden":
        if not args.settings or not os.path.isfile(args.settings[0]):
            print("harden: name one existing --settings file", file=sys.stderr)
            return 3
        return harden(args, platform)
    files = gather(args)
    if not files:
        print("NOT-RUN: no settings file found", file=sys.stderr)
        return 3
    findings, hooks, env = audit(files, platform, not args.no_ask_rule)
    if args.json:
        print(json.dumps({"tool": "perm_audit", "version": VERSION, "platform": platform,
                          "files": [{"path": f["path"], "scope": f["scope"], "tracked": f["tracked"],
                                     "error": f["error"]} for f in files],
                          "findings": findings, "hooks": hooks, "env": env}, indent=2))
    else:
        print_text(files, findings, hooks, env)
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        print(f"perm_audit crashed: {type(exc).__name__}", file=sys.stderr)
        sys.exit(4)
