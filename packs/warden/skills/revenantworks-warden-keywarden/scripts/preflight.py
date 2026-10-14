#!/usr/bin/env python3
"""preflight.py - what a credential command prints when it fails (stdlib only).

  check --command "<cmd>"   static check of a command line against the shapes in
                            references/dangerous-shapes.md. JSON out; the command
                            itself is never echoed. Exit 0 SAFE, 1 findings.
  run -- <program> [args]   run a command with stdout and stderr captured, then print
                            them with every secret-named environment value, its
                            base64 forms, token shapes, credential header values and
                            URL passwords replaced by <masked:class:fingerprint>.
                            Exit: the program's own code; 3 if it could not start;
                            4 crash (message withheld).

`run` does not use a shell: pass the program and its arguments as separate words.
Add --mask-env NAME for a variable whose name does not look secret.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

import kw_common

SECRET_FILE = r"(\.env(\.[\w.-]+)?|\.git-credentials|hosts\.ya?ml|credentials(\.json)?|\.netrc|_netrc|\.npmrc|\.pypirc|id_rsa|id_ed25519|[\w.-]+\.pem|[\w.-]+\.pfx|[\w.-]+\.key)"

RULES = [
    ("git-credential-fill",
     re.compile(r"\bgit\s+credential(-manager)?\s+(fill|get)\b|\bgit-credential-\w+\s+get\b", re.I),
     "prints the stored password or token on success",
     "Test access without reading the credential: git ls-remote <url> > NUL; echo exit $?"),
    ("gh-auth-token", re.compile(r"\bgh\s+auth\s+token\b", re.I),
     "prints the token on success",
     "gh auth status (no --show-token), or python scripts/scope_check.py"),
    ("gh-show-token", re.compile(r"\bgh\s+auth\s+status\b.*(--show-token|\s-t\b)", re.I),
     "prints the token in full",
     "gh auth status, without --show-token"),
    ("curl-verbose-auth",
     re.compile(r"\bcurl(\.exe)?\b(?=.*(\s-v\b|--verbose|--trace|\s-\w*v\w*\s))(?=.*(authorization|-u\s|--user\b|x-api-key|private-token|token\s))", re.I),
     "verbose and trace modes print request headers, the credential header included, on success and on failure",
     "curl -sS -o NUL -w \"%{http_code}\\n\" -H @<header-file> <url> (header file outside the repo), "
     "or wrap it: python scripts/preflight.py run -- curl ..."),
    ("http-client-debug", re.compile(r"(GH_DEBUG=api|GIT_CURL_VERBOSE=1|GIT_TRACE_CURL|HTTPIE.*--verbose|\bhttp\s+-v\b|Invoke-WebRequest.*-Verbose)", re.I),
     "debug tracing prints request headers, the credential included",
     "drop the debug switch; print only the status code"),
    ("echo-secret-var",
     re.compile(r"(\b(echo|printf|print|Write-(Output|Host)|printenv)\b[^|;&]*(\$\{?|\$env:|%)[A-Za-z_]*(TOKEN|SECRET|KEY|PASS|PWD|CREDENTIAL|AUTH)[A-Za-z_]*)", re.I),
     "prints the value",
     "print whether it is set, never the value: python -c \"import os;print(bool(os.environ.get('NAME')))\""),
    ("env-dump",
     re.compile(r"(^|[;&|]\s*)(printenv|env|set|export\s+-p|Get-ChildItem\s+env:|gci\s+env:|dir\s+env:|ls\s+env:)\s*($|[;&|])", re.I),
     "dumps every variable, secrets included",
     "list names only: python -c \"import os;print(sorted(os.environ))\""),
    ("read-secret-file",
     re.compile(r"\b(cat|type|more|less|head|tail|Get-Content|gc|bat|nl|strings|xxd)\b[^|;&]*" + SECRET_FILE + r"(\s|$|['\"])", re.I),
     "prints the file, values included",
     "python scripts/cred_inventory.py --root <folder> --stores files (fingerprints only)"),
    ("vault-read-prints",
     re.compile(r"\bop\s+(read\b|item\s+get\b.*--reveal|inject\b(?!.*\s-o\s))|\bbw\s+(get\b|list\s+items\b)|\bbws\s+secret\s+get\b|\bop\s+run\b.*--no-masking", re.I),
     "prints the stored value from the vault",
     "inject without printing: op run --env-file .env.tpl -- <cmd> (bws run -- <cmd> for Secrets Manager)"),
    ("ps-convertfrom-secure",
     re.compile(r"ConvertFrom-SecureString.*-AsPlainText|GetNetworkCredential\(\)\.Password|Get-StoredCredential", re.I),
     "turns a protected value into plain text in the output",
     "keep it a SecureString; pass the credential object, never its .Password"),
]
SCRIPT_RUN = re.compile(r"\b(python3?|py|node|deno|ruby|pwsh|powershell|bash|sh|npx|uv\s+run)\b", re.I)
SECRET_REF = re.compile(r"(\$\{?|\$env:|%)([A-Za-z_][A-Za-z0-9_]*)", re.I)


def check(command: str, salt: str) -> dict:
    findings = []
    for rule, rx, why, rewrite in RULES:
        if rx.search(command):
            findings.append({"rule": rule, "why": why, "safe_rewrite": rewrite})
    refs = [m.group(2) for m in SECRET_REF.finditer(command) if kw_common.secret_named(m.group(2))]
    if refs and SCRIPT_RUN.search(command) and not any(f["rule"] in ("curl-verbose-auth",) for f in findings):
        findings.append({
            "rule": "unknown-failure-path",
            "why": "a script that takes a credential can print it on failure (an HTTP error body, a "
                   "traceback that reprs the request, a debug log); its failure output is unknown",
            "safe_rewrite": "python scripts/preflight.py run -- <the same command, as separate words>"})
    literals = []
    for m in kw_common.SHAPE_RE.finditer(command):
        v = m.group(0)
        literals.append({"prefix_class": kw_common.prefix_class(v), "length": len(v),
                         "fingerprint": kw_common.fingerprint(v, salt)})
    if literals:
        findings.append({
            "rule": "literal-secret",
            "why": "a credential typed into a command line is already in the transcript and the shell history",
            "safe_rewrite": "treat it as leaked: keywarden leak (rotate first); reference it from a store next time"})
    return {"tool": "preflight", "version": kw_common.VERSION,
            "verdict": "SAFE" if not findings else "REWRITE",
            "findings": findings, "literal_secrets": literals,
            "note": "the command line is not echoed"}


def known_values(extra_names: list[str]) -> list[str]:
    vals = []
    for k, v in os.environ.items():
        if v and (kw_common.secret_named(k) or k in extra_names) and k != "SHIELD_SALT":
            vals.append(v)
            vals.append(kw_common.strip_scheme(v))
    return vals


def run(cmd: list[str], extra_names: list[str], salt: str) -> int:
    if not cmd:
        sys.stderr.write("nothing to run\n")
        return kw_common.NOT_RUN
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=600)
    except FileNotFoundError:
        sys.stderr.write("NOT-RUN: program not found (first word of the command)\n")
        return kw_common.NOT_RUN
    except (OSError, subprocess.SubprocessError) as e:
        sys.stderr.write(f"NOT-RUN: could not start ({type(e).__name__})\n")
        return kw_common.NOT_RUN
    known = known_values(extra_names)
    total = 0
    for data, stream in ((proc.stdout, sys.stdout), (proc.stderr, sys.stderr)):
        text = data.decode("utf-8", errors="replace")
        masked, n = kw_common.mask_text(text, known, salt)
        total += n
        stream.write(masked)
        stream.flush()
    sys.stderr.write(f"\n[preflight] exit {proc.returncode}; masked {total} occurrence(s)\n")
    return proc.returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("check")
    c.add_argument("--command", help="the command line; read from stdin when absent")
    r = sub.add_parser("run")
    r.add_argument("--mask-env", action="append", default=[])
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    for p in (c, r):
        p.add_argument("--salt-env", default="SHIELD_SALT")
    args = ap.parse_args(argv)
    salt, _ = kw_common.get_salt(args.salt_env)
    if args.mode == "check":
        command = args.command if args.command is not None else sys.stdin.read()
        doc = check(command, salt)
        print(json.dumps(doc, indent=2))
        return kw_common.CLEAN if doc["verdict"] == "SAFE" else kw_common.FINDINGS
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if len(cmd) == 1 and " " in cmd[0]:
        cmd = shlex.split(cmd[0], posix=os.name != "nt")
    return run(cmd, args.mask_env, salt)


if __name__ == "__main__":
    sys.exit(kw_common.run_guarded(main))
