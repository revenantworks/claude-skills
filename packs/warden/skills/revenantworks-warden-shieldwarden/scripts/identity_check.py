#!/usr/bin/env python3
"""identity_check.py: shieldwarden's identity and naming-policy checker (stdlib only).

Run it; never read it into context. It prints rule names, locations, commit ids and salted
fingerprints. It never prints a banned value, an email address or the values file's contents:
every output string passes a redaction step, and a crash prints only the exception type.

The values file is private to this machine: --values, else WARDEN_IDENTITY_VALUES_FILE, else
~/.warden/aliases.txt (warden_private.py). One inside a git work tree, or an old one named
by the policy's values_file field, is never used; lint reports it with the one move command.

Modes
  lint      --policy P [--values V] [--repo DIR]
            Validate the policy and the values file; report a missing values file (with the
            setup command) or one outside the private folder (with the move command).
  check     --policy P --values V --surface S (--text FILE | --stdin | --staged | --range R)
            [--branches] [--repo DIR]
            Test text, a staged diff or a commit range (metadata, messages, added lines)
            against the policy for one surface.
  identity  --policy P [--values V] [--repo DIR] [--range R] [--root DIR [--depth N]]
            The effective git identity of a folder and the config source that decides it;
            with --range, author, committer and every trailer on every commit in the range;
            with --root, the folder check for every repo under a root.

Common: --salt-env NAME adds an HMAC-SHA256 fingerprint (`fp`) per value hit, keyed by the
environment variable NAME. Without it, hits carry the class and key label only.

Exit codes: 0 no findings · 1 findings · 3 bad input (policy, values file, repo, range)
· 4 internal error (type name only, never the message).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warden_private  # noqa: E402  (pack-shared: the private-file convention, references/private-files.md)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):[ \t]*(.+)$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
KEY_RE = re.compile(r"^[a-z][a-z0-9-]*:[A-Za-z0-9][A-Za-z0-9_.-]*$")
MIN_VALUE_LEN = 3
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: no console pops up


class InputError(Exception):
    """Bad input. The message is authored here and never carries a value."""


# ---------------------------------------------------------------- loading

POLICY_NAMES = ("identity-policy.json", "identity-policy.yaml", "identity-policy.yml")
YAML_TRADE_OFFS = {
    "pros": ["comments beside each rule", "easier hand-editing: no quotes or trailing commas"],
    "cons": ["needs PyYAML, which the user installs (pip install pyyaml); this skill never installs it",
             "one more dependency to keep current; without it the check exits 3 and names the JSON form",
             "indentation mistakes are easy when hand-editing"],
}


def pyyaml_available() -> bool:
    try:
        import yaml  # noqa: F401  optional, declared: never installed by this skill
    except ImportError:
        return False
    return True


def found_policies(repo: str) -> list[str]:
    root = Path(repo)
    return [n for n in POLICY_NAMES if (root / n).is_file()]


def find_policy(repo: str) -> str:
    found = found_policies(repo)
    if not found:
        raise InputError("no policy given and no identity-policy.json in the repo root")
    if len(found) > 1:
        raise InputError("two policy files in the repo root (" + ", ".join(found) + "); keep one")
    return str(Path(repo) / found[0])


def mode_formats(repo: str) -> tuple[dict, int]:
    found = found_policies(repo)
    conflict = len(found) > 1
    out = {"mode": "formats", "default": "json", "json": {"available": True, "needs": "nothing (stdlib)"},
           "yaml": {"available": pyyaml_available(), **YAML_TRADE_OFFS}, "found": found, "conflict": conflict}
    return out, (1 if conflict else 0)


def load_policy(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise InputError("policy file not found")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yml", ".yaml"):
        try:
            import yaml  # optional, declared: used only when already installed
        except ImportError:
            raise InputError("a YAML policy needs PyYAML; use the JSON form (references/policy-format.md)")
        try:
            pol = yaml.safe_load(text)
        except Exception:
            raise InputError("policy is not valid YAML")
    else:
        try:
            pol = json.loads(text)
        except json.JSONDecodeError:
            raise InputError("policy is not valid JSON")
    if not isinstance(pol, dict) or pol.get("version") != 1:
        raise InputError("policy must be an object with version 1")
    if not isinstance(pol.get("surfaces"), dict) or not pol["surfaces"]:
        raise InputError("policy needs a non-empty surfaces map")
    pol["_dir"] = str(p.resolve().parent)
    return pol


def values_status(pol: dict, flag: str | None) -> tuple[Path | None, dict | None]:
    """Resolve the values file: --values > WARDEN_IDENTITY_VALUES_FILE > ~/.warden/aliases.txt.

    Returns (path, None) when usable, else (None, finding). A file inside a git work tree, or an
    old file named by the policy's values_file field, is reported with the one command that moves
    it into the private folder, and is never used (references/private-files.md).
    """
    res = warden_private.resolve("identity-values", flag)
    if res.ok:
        return res.path, None
    if res.path is not None and warden_private.git_work_tree(res.path) is None:
        raise InputError(f"values file not found ({res.source})")
    old = res.path
    if old is None and pol.get("values_file"):
        cand = Path(pol["_dir"]) / pol["values_file"]
        old = cand if cand.is_file() else None
    if old is None:
        return None, {"rule": "values-file-missing", "severity": "error", "where": "values", "field": "location",
                      "setup": warden_private.setup_command("identity-values")}
    rule = "values-file-in-repo" if warden_private.git_work_tree(old) is not None else "values-file-legacy"
    return None, {"rule": rule, "severity": "error", "where": "values", "field": "location",
                  "fix": f'python scripts/warden_private.py adopt identity-values "{old.resolve()}"'}


def load_values(path: Path | None) -> dict[str, str]:
    """`class:label = value` per line, `#` comments. Returns {key: value}."""
    if path is None:
        return {}
    if not path.is_file():
        raise InputError("values file not found")
    out: dict[str, str] = {}
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise InputError(f"values file line {n}: expected 'class:label = value'")
        key, val = (s.strip() for s in line.split("=", 1))
        if not KEY_RE.match(key):
            raise InputError(f"values file line {n}: key is not class:label")
        if not val:
            raise InputError(f"values file line {n}: empty value")
        out[key] = val
    return out


# ---------------------------------------------------------------- matching

class Matcher:
    def __init__(self, pol: dict, values: dict[str, str], salt: bytes | None):
        self.pol = pol
        self.values = values
        self.salt = salt
        self.codenames = pol.get("codenames", {}) or {}
        self.allowed = [re.compile(p, re.I) for p in pol.get("allowed_emails", [])]
        self.allowed_trailer = self.allowed + [re.compile(p, re.I) for p in pol.get("allowed_trailer_emails", [])]
        self.exclude = pol.get("exclude", []) or []
        self.pats = []
        for key, val in values.items():
            if len(val) < MIN_VALUE_LEN:
                continue
            pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(val) + r"(?![A-Za-z0-9])", re.I)
            self.pats.append((key, val, pat))
        # longest first, so the redactor replaces a full name before a part of it
        self.redact_pats = sorted(self.pats, key=lambda t: -len(t[1]))

    def fp(self, value: str) -> str | None:
        if not self.salt:
            return None
        return hmac.new(self.salt, value.lower().encode("utf-8"), hashlib.sha256).hexdigest()[:12]

    def email_ok(self, addr: str, trailer: bool = False) -> bool:
        pats = self.allowed_trailer if trailer else self.allowed
        return any(p.search(addr) for p in pats)

    def value_hits(self, text: str, banned: list[str]):
        """Yield (rule, key, class, value) for each policy value found in text."""
        for key, val, pat in self.pats:
            if not pat.search(text):
                continue
            cls = key.split(":", 1)[0]
            if key in self.codenames:
                yield "codename-required", key, cls, val
            elif cls in banned:
                yield "banned-value", key, cls, val

    def excluded(self, rule: str, where: str) -> bool:
        return any(fnmatch.fnmatch(where, e.get("where", "*")) and e.get("rule", rule) == rule
                   for e in self.exclude)


def finding(m: Matcher, rule: str, where: str, field: str, commit: str = "", key: str = "",
            value: str = "", severity: str = "error", **extra) -> dict | None:
    if m.excluded(rule, where):
        return None
    row = {"rule": rule, "severity": severity, "where": where, "field": field}
    if commit:
        row["commit"] = commit
    if key:
        row["class"] = key.split(":", 1)[0]
        row["key"] = key
        if key in m.codenames:
            row["use"] = m.codenames[key]
        fp = m.fp(value)
        if fp:
            row["fp"] = fp
    row.update(extra)
    return row


def scan_text(m: Matcher, surface: dict, text: str, where: str, field: str, commit: str = "") -> list[dict]:
    rows = []
    banned = surface.get("banned", [])
    for rule, key, _cls, val in m.value_hits(text, banned):
        rows.append(finding(m, rule, where, field, commit, key, val))
    if surface.get("email_any"):
        for addr in EMAIL_RE.findall(text):
            if not m.email_ok(addr) and not any(p.search(addr) for _, _, p in m.pats):
                rows.append(finding(m, "email-not-allowed", where, field, commit))
    return [r for r in rows if r]


# ---------------------------------------------------------------- git

def git(repo: str, *args: str, check: bool = True) -> str:
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    except FileNotFoundError:
        raise InputError("git not found on PATH")
    if check and r.returncode != 0:
        raise InputError(f"git {args[0]} failed (exit {r.returncode})")  # stderr never echoed
    return r.stdout if r.returncode == 0 else ""


def short(sha: str) -> str:
    return sha[:12]


def parse_diff(diff: str):
    """Yield (path, line_no, added_text) for each added line of a unified=0 diff."""
    path, line = "", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            mm = HUNK_RE.match(raw)
            line = int(mm.group(1)) if mm else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            yield path, line, raw[1:]
            line += 1


def commits(repo: str, rng: str) -> list[dict]:
    out = git(repo, "log", "--no-color", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e", rng)
    rows = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        parts = rec.split("\x1f")
        if len(parts) < 6:
            continue
        sha, an, ae, cn, ce, body = parts[:6]
        rows.append({"sha": sha, "an": an, "ae": ae, "cn": cn, "ce": ce, "body": body})
    return rows


def metadata_rows(m: Matcher, pol: dict, c: dict, check_message: bool) -> list[dict]:
    surface = pol["surfaces"].get("commit-metadata", {"banned": [], "email_any": True})
    sid, rows = short(c["sha"]), []
    for who, name, addr in (("author", c["an"], c["ae"]), ("committer", c["cn"], c["ce"])):
        if not m.email_ok(addr):
            rows.append(finding(m, f"non-noreply-{who}", sid, f"{who}-email", sid))
        rows += scan_text(m, {"banned": surface.get("banned", [])}, name, sid, f"{who}-name", sid)
    for ln in c["body"].splitlines():
        t = TRAILER_RE.match(ln.strip())
        if t and EMAIL_RE.search(t.group(2)):
            for addr in EMAIL_RE.findall(t.group(2)):
                if not m.email_ok(addr, trailer=True):
                    rows.append(finding(m, "trailer-email-not-allowed", sid, f"trailer:{t.group(1).lower()}", sid))
            rows += scan_text(m, {"banned": surface.get("banned", [])}, t.group(2), sid,
                              f"trailer:{t.group(1).lower()}", sid)
    if check_message:
        body = "\n".join(ln for ln in c["body"].splitlines()
                         if not (TRAILER_RE.match(ln.strip()) and EMAIL_RE.search(ln)))
        rows += scan_text(m, surface, body, sid, "message", sid)
    return [r for r in rows if r]


# ---------------------------------------------------------------- modes

def mode_lint(pol: dict, vpath: Path | None, status: dict | None) -> list[dict]:
    rows: list[dict] = []
    if vpath is None:
        return [status] if status else []
    values = load_values(vpath)
    listed = set(pol.get("values_keys", []) or [])
    for k in sorted(listed - set(values)):
        rows.append({"rule": "values-key-missing", "severity": "error", "where": "values", "field": "key", "key": k})
    for k in sorted(set(values) - listed):
        rows.append({"rule": "values-key-unlisted", "severity": "warn", "where": "values", "field": "key", "key": k})
    for k, v in values.items():
        if len(v) < MIN_VALUE_LEN:
            rows.append({"rule": "value-too-short", "severity": "warn", "where": "values", "field": "value", "key": k})
        if v.lower() in k.lower():
            rows.append({"rule": "label-contains-value", "severity": "error", "where": "values", "field": "key",
                         "key": "<redacted>"})
    for k in pol.get("codenames", {}) or {}:
        if k not in listed:
            rows.append({"rule": "codename-key-unknown", "severity": "error", "where": "policy",
                         "field": "codenames", "key": k})
    classes = set(pol.get("classes", []) or [])
    for name, s in pol["surfaces"].items():
        for c in s.get("banned", []):
            if classes and c not in classes:
                rows.append({"rule": "surface-class-unknown", "severity": "error", "where": f"surfaces.{name}",
                             "field": "banned", "class": c})
    return rows


def mode_check(m: Matcher, pol: dict, args) -> list[dict]:
    if args.surface not in pol["surfaces"]:
        raise InputError("surface not in policy")
    surface = pol["surfaces"][args.surface]
    rows: list[dict] = []
    if args.text:
        p = Path(args.text)
        if not p.is_file():
            raise InputError("text file not found")
        for n, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            rows += scan_text(m, surface, ln, f"{p.name}:{n}", "text")
    if args.stdin:
        for n, ln in enumerate(sys.stdin.read().splitlines(), 1):
            rows += scan_text(m, surface, ln, f"stdin:{n}", "text")
    if args.staged:
        for path, n, text in parse_diff(git(args.repo, "diff", "--cached", "--no-color", "--unified=0")):
            rows += scan_text(m, surface, text, f"{path}:{n}", "staged")
            rows += scan_text(m, surface, path, path, "path") if n == 1 else []
    if args.range:
        for c in commits(args.repo, args.range):
            rows += metadata_rows(m, pol, c, check_message=True)
            diff = git(args.repo, "show", "--no-color", "--unified=0", "--format=", c["sha"])
            for path, n, text in parse_diff(diff):
                rows += scan_text(m, surface, text, f"{path}:{n}", "added", short(c["sha"]))
    if args.branches:
        refs = git(args.repo, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
        for ref in refs.splitlines():
            rows += scan_text(m, {"banned": surface.get("banned", [])}, ref, "branch", "branch-name")
    if not (args.text or args.stdin or args.staged or args.range or args.branches):
        raise InputError("check needs --text, --stdin, --staged, --range or --branches")
    return rows


def folder_identity(m: Matcher, repo: str, label: str) -> list[dict]:
    if git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
        raise InputError("not a git work tree")
    rows: list[dict] = []
    eff = git(repo, "config", "--show-scope", "--show-origin", "--get", "user.email", check=False).strip()
    glob_origin = git(repo, "config", "--global", "--no-includes", "--show-origin", "--get", "user.email",
                      check=False).strip()
    uco = git(repo, "config", "--type=bool", "--get", "user.useConfigOnly", check=False).strip() == "true"
    includes = []
    for ln in git(repo, "config", "--show-origin", "--get-regexp", r"^includeif\.", check=False).splitlines():
        key = ln.split("\t", 1)[-1].split(" ", 1)[0]
        includes.append(re.sub(r"^includeif\.|\.path$", "", key, flags=re.I))
    if not eff:
        rows.append(finding(m, "no-identity", label, "user.email",
                            severity="warn" if uco else "error", use_config_only=uco))
        return [r for r in rows if r]
    scope, origin, value = (eff.split("\t") + ["", "", ""])[:3]
    source = "local" if scope in ("local", "worktree", "command") else (
        "global-default" if glob_origin and glob_origin.split("\t")[0] == origin else f"{scope}-include")
    info = {"scope": scope, "source": source, "origin": origin.replace("file:", "", 1),
            "use_config_only": uco, "include_conditions": includes}
    if source == "global-default":
        rows.append(finding(m, "no-local-identity", label, "user.email", severity="error",
                            fix='git -C <repo> config --local user.email "<noreply-address>"',
                            **info))
    if not m.email_ok(value):
        rows.append(finding(m, "identity-email-not-allowed", label, "user.email", **info))
    if not uco:
        rows.append(finding(m, "use-config-only-off", label, "user.useConfigOnly", severity="warn",
                            fix="git -C <repo> config --local user.useConfigOnly true"))
    if not rows:
        rows.append(finding(m, "identity-ok", label, "user.email", severity="info", **info))
    return [r for r in rows if r]


def find_repos(root: Path, depth: int) -> list[Path]:
    found: list[Path] = []
    root = root.resolve()
    for dirpath, dirnames, _files in os.walk(root, followlinks=False):
        here = Path(dirpath)
        rel_depth = len(here.relative_to(root).parts)
        if (here / ".git").exists():
            found.append(here)
            dirnames[:] = []
            continue
        is_junction = getattr(os.path, "isjunction", lambda _p: False)
        dirnames[:] = [d for d in dirnames if rel_depth < depth and not d.startswith(".")
                       and not is_junction(os.path.join(dirpath, d))]
    return sorted(found)


def mode_identity(m: Matcher, pol: dict, args) -> list[dict]:
    rows: list[dict] = []
    if args.root:
        root = Path(args.root)
        if not root.is_dir():
            raise InputError("root is not a folder")
        for repo in find_repos(root, args.depth):
            rows += folder_identity(m, str(repo), repo.relative_to(root.resolve()).as_posix() or ".")
        return rows
    rows += folder_identity(m, args.repo, ".")
    if args.range:
        for c in commits(args.repo, args.range):
            rows += metadata_rows(m, pol, c, check_message=False)
    return rows


# ---------------------------------------------------------------- output

def redact(text: str, m: Matcher | None) -> str:
    if m:
        for _k, _v, pat in m.redact_pats:
            text = pat.sub("<redacted>", text)
    text = EMAIL_RE.sub("<email>", text)
    home = str(Path.home())
    for h in {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}:
        if h and len(h) > 3:
            text = text.replace(h, "~")
    return text


def emit(obj: dict, m: Matcher | None) -> None:
    sys.stdout.write(redact(json.dumps(obj, indent=1, ensure_ascii=False), m) + "\n")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="identity_check.py", description="shieldwarden identity and naming-policy check")
    sub = ap.add_subparsers(dest="mode", required=True)
    fp = sub.add_parser("formats")
    fp.add_argument("--repo", default=".")
    for name in ("lint", "check", "identity"):
        sp = sub.add_parser(name)
        sp.add_argument("--policy", help="default: identity-policy.json (or .yaml) in the repo root")
        sp.add_argument("--values", help="default: $WARDEN_IDENTITY_VALUES_FILE, else ~/.warden/aliases.txt")
        sp.add_argument("--repo", default=".")
        sp.add_argument("--salt-env")
        if name == "check":
            sp.add_argument("--surface", required=True)
            sp.add_argument("--text")
            sp.add_argument("--stdin", action="store_true")
            sp.add_argument("--staged", action="store_true")
            sp.add_argument("--range")
            sp.add_argument("--branches", action="store_true")
        if name == "identity":
            sp.add_argument("--range")
            sp.add_argument("--root")
            sp.add_argument("--depth", type=int, default=3)
    return ap


def main(argv: list[str] | None = None) -> int:
    m: Matcher | None = None
    try:
        args = build_parser().parse_args(argv)
        if args.mode == "formats":
            out, code = mode_formats(args.repo)
            emit(out, None)
            return code
        pol = load_policy(args.policy or find_policy(args.repo))
        vpath, status = values_status(pol, args.values)
        if args.mode == "lint":
            rows = mode_lint(pol, vpath, status)
            values = load_values(vpath) if vpath else {}
            m = Matcher(pol, values, None)
        else:
            if args.mode == "check" and vpath is None:
                if status and status["rule"] == "values-file-missing":
                    raise InputError("NOT-RUN: no values file; run setup: " + status["setup"])
                raise InputError("NOT-RUN: the values file is not in the private folder and is not used; "
                                 "lint prints the one command that moves it")
            values = load_values(vpath) if vpath else {}
            salt = os.environ.get(args.salt_env, "").encode("utf-8") if args.salt_env else None
            m = Matcher(pol, values, salt or None)
            rows = mode_check(m, pol, args) if args.mode == "check" else mode_identity(m, pol, args)
        bad = [r for r in rows if r.get("severity") in ("error", "warn")]
        emit({"mode": args.mode, "findings": rows,
              "summary": {"findings": len(bad), "errors": sum(r["severity"] == "error" for r in bad)}}, m)
        return 1 if bad else 0
    except InputError as e:
        emit({"error": "input", "detail": str(e)}, m)
        return 3
    except SystemExit as e:  # argparse usage errors
        return 3 if e.code not in (0, None) else 0
    except Exception as e:  # never the message: it may carry a value
        sys.stdout.write(json.dumps({"error": "internal", "type": type(e).__name__}) + "\n")
        return 4


if __name__ == "__main__":
    sys.exit(main())
