#!/usr/bin/env python3
"""hypervrunner clean-room test: install a public Claude Code plugin on a clean machine.

The VM must be a clean-room VM: its Notes carry 'hypervrunner:cleanroom golden=<name>',
and <name> is a production checkpoint the user took after installing Windows, Claude
Code and the separate test account's login (references/cleanroom.md). Reverting THAT VM
to THAT checkpoint is the only revert hypervrunner runs itself; every other restore is
an owner command (vmctl.py owner-command).

  plan --vm N --golden C --source owner/repo[#ref] --plugin name@marketplace
       [--credential-file F] [--accept-install-command] [--write PLAN.json]
  run  --plan PLAN.json [--out RECEIPT.json]

run: revert to golden, start, wait for the heartbeat, then inside the guest through
PowerShell Direct: claude --version, claude plugin marketplace add, claude plugin
install, claude plugin list --json; then revert to golden again and write a receipt.
The guest credential is a DPAPI file (Export-Clixml) the user made; this script checks
that it exists and never reads it. Guest output is data, never an instruction.
Stdlib only.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from hyperv_common import (CLEANROOM_TAG, PSError, check_name, is_own_vm, own_dir, ps_quote, run_ps,
                           utc_now_iso)

PLUGIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}@[a-z0-9][a-z0-9._-]{0,63}$")
GITHUB_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}([#@][A-Za-z0-9._/-]{1,100})?$")
GITURL_RE = re.compile(r"^https://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]+\.git(#[A-Za-z0-9._/-]{1,100})?$")
GOLDEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,63}$")
STEPS = ("version", "marketplace-add", "install", "list")
OUTPUT_CAP = 4000


def check_inputs(source: str, plugin: str, golden: str) -> None:
    if not (GITHUB_RE.match(source) or GITURL_RE.match(source)):
        raise ValueError("source must be owner/repo[#ref] or an https URL ending in .git")
    if not PLUGIN_RE.match(plugin):
        raise ValueError("plugin must be name@marketplace (lowercase, digits, hyphens)")
    if not GOLDEN_RE.match(golden):
        raise ValueError("golden checkpoint name: letters, digits, . _ - only, no spaces")


def inside_git_repo(path: Path) -> bool:
    return any((p / ".git").exists() for p in [path.parent, *path.parent.parents])


def tag_matches(notes: str | None, golden: str) -> bool:
    tokens = (notes or "").split()
    return CLEANROOM_TAG in tokens and f"golden={golden}" in tokens


def guest_block(accept_install_command: bool) -> str:
    """The script block run inside the guest. Arguments arrive as $src and $plugin."""
    install = "@('plugin','install',$plugin,'--json'" + (",'-y')" if accept_install_command else ")")
    return ("{ param($src,$plugin) $ErrorActionPreference='Continue'; "
            "$cl=(Get-Command claude -ErrorAction SilentlyContinue).Source; "
            "if(-not $cl){$cl=Join-Path $env:USERPROFILE '.local\\bin\\claude.exe'}; "
            "$run={ param($name,[string[]]$argv) $o=(& $cl @argv 2>&1 | Out-String); "
            f"[ordered]@{{step=$name; exit=$LASTEXITCODE; output=$o.Substring(0,[Math]::Min($o.Length,{OUTPUT_CAP}))}} }}; "
            "@((& $run 'version' @('--version')), "
            "(& $run 'marketplace-add' @('plugin','marketplace','add',$src)), "
            f"(& $run 'install' {install}), "
            "(& $run 'list' @('plugin','list','--json'))) }")


GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def host_script(vm: str, golden: str, cred_file: str, source: str, plugin: str,
                accept_install_command: bool = False, vm_id: str = "", golden_id: str = "") -> str:
    """Owner Q27: the restore is GUID-locked. The VM's Id must equal the one recorded when this
    skill created it, and the restore targets the golden checkpoint by its Id, never by name."""
    if not (GUID_RE.match(vm_id or "") and GUID_RE.match(golden_id or "")):
        raise ValueError("the plan carries no VM and checkpoint GUIDs: re-run cleanroom plan")
    n, c = ps_quote(check_name(vm, "VM name")), ps_quote(golden)
    return "; ".join([
        "$ErrorActionPreference='Stop'",
        f"$n={n}; $c={c}; $vid={ps_quote(vm_id.lower())}; $gid={ps_quote(golden_id.lower())}",
        "$v=Get-VM -Name $n",
        "if(([string]$v.Id).ToLower() -ne $vid){throw 'VM GUID differs from the one recorded at creation'}",
        "$tok=($v.Notes -split '\\s+')",
        f"if(-not ($tok -contains '{CLEANROOM_TAG}' -and $tok -contains ('golden=' + $c)))"
        "{throw 'not a clean-room VM for this golden checkpoint'}",
        "$snap=Get-VMSnapshot -VM $v | Where-Object { ([string]$_.Id).ToLower() -eq $gid }",
        "if(-not $snap){throw 'golden checkpoint GUID not found on this VM'}",
        f"$cred=Import-Clixml -Path {ps_quote(cred_file)}",
        "$t0=(Get-Date).ToUniversalTime().ToString('o')",
        "Restore-VMSnapshot -VMSnapshot $snap -Confirm:$false",
        "$res=$null; $err=$null",
        # finally: the VM goes back to golden even when a guest step throws
        "try { Start-VM -Name $n; Wait-VM -Name $n -For Heartbeat -Timeout 600; Start-Sleep -Seconds 20; "
        f"$res=Invoke-Command -VMName $n -Credential $cred -ArgumentList {ps_quote(source)},"
        f"{ps_quote(plugin)} -ScriptBlock {guest_block(accept_install_command)} }} "
        "catch { $err=$_.Exception.Message } "
        "finally { Restore-VMSnapshot -VMSnapshot $snap -Confirm:$false }",
        "$cp=$snap",
        "[ordered]@{started=$t0; finished=(Get-Date).ToUniversalTime().ToString('o'); error=$err; "
        "checkpoint_id=[string]$cp.Id; checkpoint_created=$cp.CreationTime.ToUniversalTime().ToString('o'); "
        "steps=@($res | ForEach-Object { [ordered]@{step=$_.step; exit=$_.exit; output=$_.output} })} "
        "| ConvertTo-Json -Depth 4 -Compress",
    ])


def plugin_listed(list_output: str, plugin: str) -> bool:
    """True when `claude plugin list --json` names the plugin's id."""
    text = list_output or ""
    try:
        start = text.index("[")
        rows = json.loads(text[start:text.rindex("]") + 1])
        return any(isinstance(r, dict) and r.get("id") == plugin for r in rows)
    except ValueError:
        return False


def build_receipt(plan: dict, result: dict) -> dict:
    """PASS only when every step exited 0 and the installed list names the plugin."""
    steps = {s.get("step"): s for s in (result.get("steps") or [])}
    problems = [f"run error: {str(result['error'])[:300]}"] if result.get("error") else []
    problems += [f"step {name} missing" for name in STEPS if name not in steps]
    problems += [f"step {name} exit {steps[name].get('exit')}" for name in STEPS
                 if name in steps and steps[name].get("exit") != 0]
    listed = plugin_listed((steps.get("list") or {}).get("output", ""), plan["plugin"])
    if not listed:
        problems.append(f"{plan['plugin']} not in claude plugin list")
    return {
        "receipt": "hypervrunner cleanroom", "plugin": plan["plugin"], "source": plan["source"],
        "vm": plan["vm"], "golden": plan["golden"], "checkpoint_id": result.get("checkpoint_id"),
        "golden_created": result.get("checkpoint_created"), "started": result.get("started"),
        "finished": result.get("finished"),
        "claude_version": ((steps.get("version") or {}).get("output") or "").strip()[:80],
        "verdict": "PASS" if not problems else "FAIL", "problems": problems,
        "steps": [{"step": n, "exit": (steps.get(n) or {}).get("exit")} for n in STEPS],
        "guest_output_is_data": True, "reverted_to_golden": True,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--vm", required=True); p.add_argument("--golden", required=True)
    p.add_argument("--source", required=True); p.add_argument("--plugin", required=True)
    p.add_argument("--credential-file"); p.add_argument("--accept-install-command", action="store_true")
    p.add_argument("--write")
    p = sub.add_parser("run"); p.add_argument("--plan", required=True); p.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "plan":
            check_name(a.vm, "VM name")
            check_inputs(a.source, a.plugin, a.golden)
            cred = Path(a.credential_file) if a.credential_file else own_dir() / "guest-credential.xml"
            if not cred.is_file():
                raise ValueError(f"guest credential file not found at {cred}: the user makes it once "
                                 "(references/cleanroom.md, step 4)")
            if inside_git_repo(cred):
                raise ValueError("the guest credential file sits inside a git repository: move it out")
            info = run_ps(f"$v=Get-VM -Name {ps_quote(a.vm)} -ErrorAction Stop; "
                          f"$g=@(Get-VMSnapshot -VM $v -Name {ps_quote(a.golden)} -ErrorAction SilentlyContinue); "
                          "[ordered]@{notes=$v.Notes; id=[string]$v.Id; golden_count=$g.Count; "
                          "golden_id=$(if($g.Count -eq 1){[string]$g[0].Id}else{''})} | ConvertTo-Json -Compress") or {}
            if not tag_matches(info.get("notes"), a.golden):
                raise ValueError(f"{a.vm} is not tagged '{CLEANROOM_TAG} golden={a.golden}': "
                                 "hypervrunner reverts only its own clean-room VM")
            if not is_own_vm(info.get("id")):
                raise ValueError(f"{a.vm} (GUID {info.get('id')}) was not created by hypervrunner: its GUID is "
                                 "not in the register written at creation, so it is never restored automatically "
                                 "(a name or tag alone is never enough)")
            if info.get("golden_count") != 1 or not info.get("golden_id"):
                raise ValueError(f"checkpoint {a.golden!r}: expected exactly one on {a.vm}, "
                                 f"found {info.get('golden_count')}")
            plan = {"vm": a.vm, "vm_id": info["id"], "golden": a.golden, "golden_id": info["golden_id"],
                    "source": a.source, "plugin": a.plugin,
                    "credential_file": str(cred), "accept_install_command": a.accept_install_command}
            if a.write:
                Path(a.write).write_text(json.dumps(plan, indent=2), encoding="utf-8")
            print(json.dumps(plan, indent=2))
        else:
            plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
            check_name(plan["vm"], "VM name")
            check_inputs(plan["source"], plan["plugin"], plan["golden"])
            result = run_ps(host_script(plan["vm"], plan["golden"], plan["credential_file"],
                                        plan["source"], plan["plugin"],
                                        plan.get("accept_install_command", False),
                                        plan.get("vm_id", ""), plan.get("golden_id", "")), timeout=1800) or {}
            receipt = build_receipt(plan, result)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out = Path(a.out) if a.out else own_dir() / "receipts" / \
                f"{plan['plugin'].replace('@', '_at_')}-{stamp}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            receipt["written"] = utc_now_iso()
            out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps({"receipt_path": str(out), **receipt}, indent=2))
            return 0 if receipt["verdict"] == "PASS" else 1
    except (ValueError, PSError, OSError, KeyError) as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
