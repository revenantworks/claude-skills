#!/usr/bin/env python3
"""scope_check.py - what a GitHub token may do, without printing it (stdlib only).

Runs `gh api -i <endpoint>` (default /user) with GH_DEBUG removed from the
child's environment, and prints ONLY the scope and expiry headers as JSON:
classic tokens answer with X-OAuth-Scopes; fine-grained tokens do not (they
answer per call with X-Accepted-GitHub-Permissions). The response body and
gh's raw error text are never printed; a failure reports a masked first line.

  --gh "<argv prefix>"   the gh command, words separated by | (default: gh)
  --hostname HOST        passed through to gh api for GitHub Enterprise
  --endpoint PATH        default /user

Exit 0 fine-grained or no broad scope, 1 a broad classic scope, 3 could not
read (gh missing, signed out, HTTP error), 4 crash (message withheld).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

import kw_common

BROAD = ("delete_repo", "delete:packages", "site_admin", "admin:")
HEADERS = {
    "x-oauth-scopes": "scopes",
    "x-accepted-oauth-scopes": "accepted_scopes",
    "x-accepted-github-permissions": "accepted_permissions",
    "github-authentication-token-expiration": "token_expiration",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gh", default="gh")
    ap.add_argument("--hostname")
    ap.add_argument("--endpoint", default="/user")
    ap.add_argument("--salt-env", default="SHIELD_SALT")
    args = ap.parse_args(argv)
    salt, _ = kw_common.get_salt(args.salt_env)
    prefix = [w for w in args.gh.split("|") if w]
    if len(prefix) == 1 and not shutil.which(prefix[0]):
        print(json.dumps({"tool": "scope_check", "status": "NOT-RUN", "reason": "gh not found"}))
        return kw_common.NOT_RUN
    cmd = prefix + ["api", "-i", args.endpoint]
    if args.hostname:
        cmd += ["--hostname", args.hostname]
    env = {k: v for k, v in os.environ.items() if k not in ("GH_DEBUG", "DEBUG")}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    known = [v for k, v in env.items() if v and kw_common.secret_named(k)]
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or ["(no message)"])[0]
        masked, _ = kw_common.mask_text(first, known, salt)
        print(json.dumps({"tool": "scope_check", "status": "FAILED", "exit": proc.returncode,
                          "message": masked[:200]}, indent=2))
        return kw_common.NOT_RUN
    doc = {"tool": "scope_check", "version": kw_common.VERSION, "status": "OK", "http_status": None,
           "scopes": None, "accepted_scopes": None, "accepted_permissions": None,
           "token_expiration": None}
    for line in proc.stdout.splitlines():
        if not line.strip():
            break  # end of headers: the body is never read
        if line.upper().startswith("HTTP/"):
            parts = line.split()
            doc["http_status"] = parts[1] if len(parts) > 1 else None
            continue
        name, _, value = line.partition(":")
        key = HEADERS.get(name.strip().lower())
        if key:
            value = value.strip()
            if key in ("scopes", "accepted_scopes"):
                doc[key] = [s.strip() for s in value.split(",") if s.strip()]
            else:
                doc[key] = value
    if doc["scopes"] is not None:
        doc["token_kind"] = "classic"
    elif doc["accepted_permissions"] is not None or doc["token_expiration"] is not None:
        doc["token_kind"] = "fine-grained"
    else:
        doc["token_kind"] = "unknown (no scope headers: fine-grained, app or OAuth token)"
    doc["broad_scopes"] = [s for s in (doc["scopes"] or []) if s.startswith(BROAD)]
    print(json.dumps(doc, indent=2))
    return kw_common.FINDINGS if doc["broad_scopes"] else kw_common.CLEAN


if __name__ == "__main__":
    sys.exit(kw_common.run_guarded(main))
