#!/usr/bin/env python3
"""shieldwarden signposts: files and folders whose NAMES advertise sensitive data, and who can open them.

Run, never read into context. Stdlib only. Read-only: it never opens a file's contents, and it never
renames, moves or re-permits anything. Every suggestion is a command for the user to run.

    signposts.py PATH [PATH ...] --json OUT [--depth 8] [--max-entries 200000] [--max-seconds 300]
                 [--words FILE] [--access auto|windows|posix|none] [--shell ps|sh] [--max-access 500]
    signposts.py --template          (print an empty private-list template to stdout)

Names only: each file and folder name is split into words (case-insensitive, camelCase and
separators split) and matched whole-word against the shipped list plus the user's private list.
Metadata only: owner and access list (Windows: icacls, plus `net share`; POSIX: mode bits).
Private list resolution: --words FILE > $WARDEN_SIGNPOST_WORDS > ~/.warden/glossary.txt if it
exists > the shipped list alone. A private list inside a git work tree is refused. Its entries are
never printed: a hit on one reads "private list #N". A line "accept: <path>" marks a known-false
path (and everything under it) as accepted.
Never follows a junction or symlink (each is listed once under not_scanned); skips git internals and
package caches; caps depth, entry count and time, and lists what it did not scan.
Exit codes: 0 no hits, 1 hits or a partial scan, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import USERS, header, link_kind, norm, redact, write_json  # noqa: E402

ENV_WORDS = "WARDEN_SIGNPOST_WORDS"
DEFAULT_WORDS_FILE = Path.home() / ".warden" / "glossary.txt"

# The shipped list. "strong" names a credential, key or identity document; "general" a sensitive area.
STRONG = ["secret", "secrets", "top secret", "password", "passwords", "passwd", "credential",
          "credentials", "creds", "keys", "private key", "id rsa", "wallet", "seed", "recovery", "2fa",
          "mfa", "backup codes", "ssn", "passport"]
GENERAL = ["private", "confidential", "classified", "sensitive", "restricted", "login", "logins", "tax",
           "bank", "finance"]

# Folders never descended: version-control internals and package or build caches.
SKIP_DIRS = {".git": "git internals", ".hg": "vcs internals", ".svn": "vcs internals",
             "node_modules": "package cache", "__pycache__": "package cache", ".venv": "package cache",
             "venv": "package cache", "site-packages": "package cache", ".tox": "package cache",
             ".mypy_cache": "package cache", ".pytest_cache": "package cache", ".gradle": "package cache",
             ".m2": "package cache", ".npm": "package cache", ".yarn": "package cache",
             ".pnpm-store": "package cache", ".nuget": "package cache", ".cache": "package cache",
             "$recycle.bin": "system folder", "system volume information": "system folder"}
SKIP_SUFFIXES = {("cargo", "registry"): "package cache", ("go", "pkg", "mod"): "package cache"}

# Names a program reads by that exact name: renaming or moving them breaks the program.
FUNCTIONAL = {"id_rsa", "id_rsa.pub", "id_ed25519", "id_ecdsa", "id_dsa", "credentials",
              "credentials.json", ".git-credentials", ".netrc", "_netrc", "wallet.dat", "keys",
              "private-keys-v1.d", "secrets.json", "secrets.yaml", "secrets.yml"}
APP_SEGMENTS = {"appdata", "library", "programdata", "program files", "program files (x86)", "windows"}

# Windows accounts that make a grant broad (names as icacls prints them, and their SIDs).
BROAD = {"everyone": "Everyone", "*s-1-1-0": "Everyone",
         "builtin\\users": "Users", "*s-1-5-32-545": "Users", "users": "Users",
         "nt authority\\authenticated users": "Authenticated Users", "*s-1-5-11": "Authenticated Users",
         "builtin\\guests": "Guests", "*s-1-5-32-546": "Guests",
         "nt authority\\anonymous logon": "Anonymous", "*s-1-5-7": "Anonymous",
         "nt authority\\network": "Network", "*s-1-5-2": "Network"}
WELL_KNOWN_DOMAINS = {"nt authority", "builtin", "nt service", "window manager", "font driver host",
                      "application package authority", "nt virtual machine"}
RIGHTS = {"F": "full", "M": "modify", "RX": "read+execute", "R": "read", "W": "write", "D": "delete",
          "N": "none"}
INHERIT = {"I", "OI", "CI", "IO", "NP"}

SYNCED = [("onedrive", "OneDrive"), ("dropbox", "Dropbox"), ("google drive", "Google Drive"),
          ("my drive", "Google Drive"), ("icloud drive", "iCloud"), ("iclouddrive", "iCloud"),
          ("mobile documents", "iCloud"), ("pcloud drive", "pCloud"), ("mega", "MEGA")]
EXPOSED = ["desktop", "downloads", "public"]

TEMPLATE = """# shieldwarden signposts - private word list. Stays on this machine; never in a repo.
# One extra signpost word or phrase per line (case does not matter), for example a project codename.
# A line starting with "accept:" marks a known-false path, and everything under it, as accepted:
#   accept: ~/projects/app/src/login
# Lines starting with # are comments.
"""

CREATE_NO_WINDOW = 0x08000000


# ---------- words ----------

def _phrase(text: str) -> tuple[str, ...]:
    return tuple(t for t in re.split(r"[\W_]+", text.casefold()) if t)


def tokens(name: str) -> tuple[list[str], set[str]]:
    """Primary tokens (camelCase and separators split) and the extra letter/digit sub-tokens."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    prim = [t for t in re.split(r"[\W_]+", spaced.casefold()) if t]
    subs = set()
    for t in prim:
        parts = re.findall(r"[^\W\d_]+|\d+", t)
        if len(parts) > 1:
            subs.update(parts)
    return prim, subs


def match_name(name: str, words: list[dict]) -> list[dict]:
    """Every word entry whose phrase occurs whole-word in the name, longest first."""
    prim, subs = tokens(name)
    hits = []
    for w in words:
        ph = w["phrase"]
        n = len(ph)
        if n == 1 and (ph[0] in prim or ph[0] in subs):
            hits.append(w)
        elif n > 1 and any(tuple(prim[i:i + n]) == ph for i in range(len(prim) - n + 1)):
            hits.append(w)
    return sorted(hits, key=lambda w: (-len(w["phrase"]), w["label"]))


def shipped_words() -> list[dict]:
    out = [{"phrase": _phrase(w), "label": w, "class": "strong"} for w in STRONG]
    out += [{"phrase": _phrase(w), "label": w, "class": "general"} for w in GENERAL]
    return out


def in_git_tree(path: Path) -> bool:
    p = path.resolve().parent
    for q in [p, *p.parents]:
        if (q / ".git").exists():
            return True
    return False


def read_text_any(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def resolve_private(flag: str | None) -> tuple[Path | None, str]:
    if flag:
        return Path(flag).expanduser(), "flag"
    env = os.environ.get(ENV_WORDS)
    if env:
        return Path(env).expanduser(), "env"
    if DEFAULT_WORDS_FILE.is_file():
        return DEFAULT_WORDS_FILE, "default"
    return None, "none"


def load_private(path: Path) -> tuple[list[dict], list[str]]:
    words, accepted = [], []
    n = 0
    for line in read_text_any(path).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.casefold().startswith("accept:"):
            p = s.split(":", 1)[1].strip().strip('"')
            if p:
                accepted.append(norm(os.path.expanduser(p)).casefold())
            continue
        ph = _phrase(s)
        if ph:
            n += 1
            words.append({"phrase": ph, "label": f"private list #{n}", "class": "private"})
    return words, accepted


def is_accepted(path: str, accepted: list[str]) -> bool:
    p = norm(path).casefold()
    return any(p == a or p.startswith(a.rstrip("/") + "/") for a in accepted)


# ---------- where a path sits ----------

def location(path: str) -> dict:
    p = norm(path)
    low = p.casefold()
    segs = low.split("/")
    synced = None
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.environ.get(env)
        if v:
            r = norm(v).casefold()
            if low == r or low.startswith(r + "/"):
                synced = "OneDrive"
    if not synced:
        for seg in segs:
            for key, label in SYNCED:
                if seg == key or (key == "onedrive" and seg.startswith("onedrive")):
                    synced = label
                    break
            if synced:
                break
    exposed = None
    homes = [norm(h).casefold() for h in {str(Path.home()), os.environ.get("USERPROFILE") or ""} if h]
    for h in homes:
        for e in EXPOSED:
            base = f"{h}/{e}"
            if low == base or low.startswith(base + "/"):
                exposed = e.capitalize()
    if re.match(r"^[a-z]:/users/public(/|$)", low):
        exposed = exposed or "Public"
    return {"synced": synced, "exposed": exposed}


def app_owned(path: str) -> bool:
    p = norm(path)
    segs = p.split("/")
    if segs[-1].casefold() in FUNCTIONAL:
        return True
    parents = [s.casefold() for s in segs[:-1]]
    if any(s in ("temp", "tmp") for s in parents):      # a temp folder holds the user's own files
        return False
    return any((s.startswith(".") and s not in (".", "..")) or s in APP_SEGMENTS for s in parents)


# ---------- who has access ----------

def redact_account(acct: str | None) -> str | None:
    if not acct:
        return acct
    hosts = {(os.environ.get(k) or "").casefold() for k in ("COMPUTERNAME", "USERDOMAIN", "HOSTNAME")}
    hosts.discard("")
    out = []
    for i, seg in enumerate(acct.split("\\")):
        c = seg.casefold()
        if c in USERS:
            out.append("<user>")
        elif c in hosts and c not in WELL_KNOWN_DOMAINS:
            out.append("<host>")
        else:
            out.append(seg)
    return "\\".join(out)


def parse_icacls(text: str, path: str) -> list[dict]:
    """icacls output -> rows {account, rights, inherited, deny, flags}. The first line carries the path."""
    lines = [ln.rstrip("\r") for ln in text.splitlines()]
    body = []
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith(("Successfully processed", "Failed processing")):
            continue
        body.append(ln)
    if not body:
        return []
    first = body[0]
    if first.casefold().startswith(path.casefold()):
        first = first[len(path):]
    elif len(body) > 1:
        first = first[len(body[1]) - len(body[1].lstrip()):]
    aces = [first.strip()] + [b.strip() for b in body[1:]]
    rows = []
    for ace in aces:
        i = ace.find(":(")
        if i <= 0:
            continue
        acct, flags = ace[:i], re.findall(r"\(([^)]*)\)", ace[i + 1:])
        inh = [f for f in flags if f in INHERIT]
        deny = "DENY" in flags
        rights = []
        for f in flags:
            if f in INHERIT or f == "DENY":
                continue
            rights.append(RIGHTS.get(f, f.lower()))
        rows.append({"account": acct, "rights": rights or ["special"], "inherited": "I" in inh,
                     "deny": deny, "flags": [f for f in inh if f != "I"]})
    return rows


def broad_from_rows(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        if r["deny"] or r["rights"] == ["none"]:
            continue
        label = BROAD.get(r["account"].casefold())
        if label:
            out.append(f"{label}: {'+'.join(r['rights'])}" + (" (inherited)" if r["inherited"] else ""))
    return out


def parse_net_share(text: str) -> list[str]:
    """`net share` output -> the local paths of non-administrative shares."""
    paths = []
    for ln in text.splitlines():
        m = re.match(r"^(\S+)\s+([A-Za-z]:\\\S.*?)(\s{2,}.*)?$", ln.rstrip())
        if m and not m.group(1).endswith("$"):
            paths.append(norm(m.group(2).strip()).casefold())
    return paths


def _run(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=30,
                           creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def win_owner(path: str) -> str | None:
    """The user account through the Win32 security API (ctypes, stdlib). None when it cannot be read."""
    try:
        import ctypes
        from ctypes import wintypes
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        gnsi = adv.GetNamedSecurityInfoW
        gnsi.argtypes = [wintypes.LPCWSTR, ctypes.c_int, wintypes.DWORD] + [ctypes.POINTER(ctypes.c_void_p)] * 5
        gnsi.restype = wintypes.DWORD
        owner, sd = ctypes.c_void_p(), ctypes.c_void_p()
        if gnsi(path, 1, 1, ctypes.byref(owner), None, None, None, ctypes.byref(sd)) != 0:
            return None
        try:
            look = adv.LookupAccountSidW
            look.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
                             wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(ctypes.c_int)]
            name, dom = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
            n, d, use = wintypes.DWORD(256), wintypes.DWORD(256), ctypes.c_int()
            if not look(None, owner, name, ctypes.byref(n), dom, ctypes.byref(d), ctypes.byref(use)):
                return "unresolved SID"
            return f"{dom.value}\\{name.value}" if dom.value else name.value
        finally:
            k32.LocalFree.argtypes = [ctypes.c_void_p]
            k32.LocalFree(sd)
    except (OSError, AttributeError, ValueError):
        return None


def posix_access(mode: int, owner: str | None, group: str | None, is_dir: bool) -> dict:
    broad = []
    if mode & stat.S_IROTH:
        broad.append("world-readable")
    if mode & stat.S_IWOTH:
        broad.append("world-writable")
    if mode & stat.S_IRGRP:
        broad.append(f"group-readable ({group or 'group'})")
    if mode & stat.S_IWGRP:
        broad.append(f"group-writable ({group or 'group'})")
    return {"owner": owner, "group": group, "mode": stat.filemode(mode), "acl": [], "broad": broad,
            "world": bool(mode & (stat.S_IROTH | stat.S_IWOTH))}


def posix_lookup(path: str) -> dict:
    st = os.stat(path, follow_symlinks=False)
    owner = group = None
    try:
        import grp
        import pwd
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
    except (ImportError, KeyError):
        owner, group = str(st.st_uid), str(st.st_gid)
    return posix_access(st.st_mode, owner, group, stat.S_ISDIR(st.st_mode))


class Access:
    def __init__(self, mode: str, runner=_run, owner_fn=win_owner):
        self.mode = mode
        self.runner, self.owner_fn = runner, owner_fn
        self._shares: list[str] | None = None

    def shares(self) -> list[str]:
        if self._shares is None:
            out = self.runner(["net", "share"]) if self.mode == "windows" else None
            self._shares = parse_net_share(out) if out else []
        return self._shares

    def shared(self, path: str) -> bool:
        p = norm(path).casefold()
        return any(p == s or p.startswith(s.rstrip("/") + "/") for s in self.shares())

    def lookup(self, path: str) -> dict:
        if self.mode == "none":
            return {"checked": False, "reason": "access not checked (--access none)"}
        if self.mode == "windows":
            out = self.runner(["icacls", path])
            if out is None:
                return {"checked": False, "reason": "icacls could not read it"}
            rows = parse_icacls(out, path)
            broad = broad_from_rows(rows)
            if self.shared(path):
                broad.append("shared on the network")
            return {"checked": True, "owner": redact_account(self.owner_fn(path)),
                    "acl": [{**r, "account": redact_account(r["account"])} for r in rows],
                    "broad": broad, "world": bool(broad)}
        try:
            d = posix_lookup(path)
        except OSError as e:
            return {"checked": False, "reason": type(e).__name__}
        d.update({"checked": True, "owner": redact_account(d["owner"]), "group": redact_account(d["group"])})
        return d


# ---------- suggestions ----------

def neutral_name(name: str, hit_words: list[dict], is_dir: bool, words: list[dict]) -> str:
    stem, ext = (name, "") if is_dir else os.path.splitext(name)
    new = stem
    for w in hit_words:
        if w["class"] == "private":
            continue
        for t in w["phrase"]:
            new = re.sub(rf"(?i)(?<![^\W_]){re.escape(t)}(?![^\W_])", "", new)
    new = re.sub(r"([ _.\-])[ _.\-]+", r"\1", new).strip(" _.-")
    if not new or match_name(new + ext, words) or new.casefold() == stem.casefold():
        new = ("folder-" if is_dir else "file-") + hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
    return new + ext


def cmd_path(red: str, shell: str) -> str:
    if red.startswith("~"):
        rest = red[1:]
        return ("$HOME" + rest.replace("/", "\\")) if shell == "ps" else ('$HOME' + rest)
    return red.replace("/", "\\") if shell == "ps" else red


def suggestions(hit: dict, words: list[dict], shell: str) -> list[dict]:
    red, is_dir, name = hit["path"], hit["kind"] == "folder", hit["name"]
    p = cmd_path(red, shell)
    acc, loc = hit["access"], hit["location"]
    out = []
    if acc.get("broad"):
        if shell == "ps":
            grant = "(OI)(CI)F" if is_dir else "F"
            out.append({"action": "lock down",
                        "why": "remove the broad grants; owner and SYSTEM only (SYSTEM keeps backup working)",
                        "preview": f'icacls "{p}"',
                        "command": f'icacls "{p}" /inheritance:r /grant:r "$($env:USERNAME):{grant}" '
                                   f'"*S-1-5-18:{grant}"'})
        else:
            out.append({"action": "lock down", "why": "owner-only access",
                        "preview": f'ls -ld -- "{p}"',
                        "command": f'chmod {"700" if is_dir else "600"} -- "{p}"'})
    if (loc["synced"] or loc["exposed"] or "shared on the network" in acc.get("broad", [])) and not hit["app_owned"]:
        where = loc["synced"] or loc["exposed"] or "a network share"
        if shell == "ps":
            cmd = ('New-Item -ItemType Directory -Force "$HOME\\local-files" | Out-Null; '
                   f'Move-Item -LiteralPath "{p}" -Destination "$HOME\\local-files" -Confirm')
        else:
            cmd = f'mkdir -p "$HOME/local-files" && mv -i -- "{p}" "$HOME/local-files/"'
        out.append({"action": "move", "why": f"out of {where} to a local, unsynced folder", "command": cmd})
    if not hit["app_owned"]:
        new = neutral_name(name, hit["matched"], is_dir, words)
        if shell == "ps":
            cmd = f'Rename-Item -LiteralPath "{p}" -NewName "{new}" -Confirm'
        else:
            parent = p.rsplit("/", 1)[0] if "/" in p else "."
            cmd = f'mv -i -- "{p}" "{parent}/{new}"'
        out.append({"action": "rename", "why": "a neutral name stops advertising the contents", "command": cmd})
    if any(w["class"] == "strong" for w in hit["matched"]):
        if shell == "ps":
            drive = (red[:2].upper() if re.match(r"^[a-z]:", red) else "$env:SystemDrive")
            cmd = f"manage-bde -status {drive}"
            why = ("check the drive is encrypted (administrator shell); real secrets belong in a "
                   "password manager")
        elif sys.platform == "darwin":
            cmd, why = "fdesetup status", "check FileVault; real secrets belong in a password manager"
        else:
            cmd, why = "lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS", \
                "look for a crypt layer under this mount; real secrets belong in a password manager"
        out.append({"action": "encrypt", "why": why, "command": cmd})
    if "<user>" in red or "<redacted>" in red:
        for s in out:
            s["edit_needed"] = "replace the placeholder segment with the real path on your machine"
    return out


def risk(hit: dict) -> tuple[int, str]:
    acc, loc = hit["access"], hit["location"]
    score = 0
    broad = acc.get("broad", [])
    if acc.get("world") or any(not b.startswith("group-") for b in broad):
        score += 4
    elif broad:
        score += 2
    if loc["synced"] or "shared on the network" in broad:
        score += 2
    if loc["exposed"]:
        score += 1
    if any(w["class"] in ("strong", "private") for w in hit["matched"]):
        score += 1
    return score, ("high" if score >= 4 else "medium" if score >= 2 else "low")


# ---------- the walk ----------

class Walk:
    def __init__(self, words, accepted, depth, max_entries, max_seconds):
        self.words, self.accepted = words, accepted
        self.depth, self.max_entries = depth, max_entries
        self.deadline = time.monotonic() + max_seconds
        self.entries = 0
        self.hits: list[dict] = []
        self.accepted_hits = 0
        self.not_scanned: list[dict] = []
        self.partial = None

    def skip(self, path: str, reason: str):
        self.not_scanned.append({"path": redact(path), "reason": reason})

    def check(self, path: str, name: str, kind: str):
        m = match_name(name, self.words)
        if not m:
            return
        if is_accepted(path, self.accepted):
            self.accepted_hits += 1
            return
        self.hits.append({"real": path, "path": redact(path), "name": name, "kind": kind, "matched": m})

    def walk(self, path: str, level: int):
        if self.partial:
            return
        try:
            it = os.scandir(path)
        except OSError as e:
            self.skip(path, f"unreadable ({type(e).__name__})")
            return
        with it:
            for e in it:
                if self.entries >= self.max_entries:
                    self.partial = f"entry cap ({self.max_entries}) reached"
                    self.skip(path, "rest of folder not scanned: entry cap")
                    return
                if time.monotonic() > self.deadline:
                    self.partial = "time cap reached"
                    self.skip(path, "rest of folder not scanned: time cap")
                    return
                self.entries += 1
                lk = link_kind(e)
                if lk:
                    self.check(e.path, e.name, "link")
                    self.skip(e.path, f"{lk}, not followed")
                    continue
                try:
                    is_dir = e.is_dir(follow_symlinks=False)
                except OSError:
                    is_dir = False
                if is_dir:
                    low = e.name.casefold()
                    if low in SKIP_DIRS:
                        self.skip(e.path, SKIP_DIRS[low])
                        continue
                    segs = tuple(norm(e.path).casefold().split("/"))
                    hit = next((r for suf, r in SKIP_SUFFIXES.items() if segs[-len(suf):] == suf), None)
                    if hit:
                        self.skip(e.path, hit)
                        continue
                    self.check(e.path, e.name, "folder")
                    if level + 1 >= self.depth:
                        self.skip(e.path, f"depth cap ({self.depth})")
                        continue
                    self.walk(e.path, level + 1)
                else:
                    self.check(e.path, e.name, "file")


def summarize_not_scanned(rows: list[dict], limit: int = 100) -> dict:
    by = {}
    for r in rows:
        key = r["reason"].split(" (")[0] if r["reason"].startswith("unreadable") else r["reason"]
        by[key] = by.get(key, 0) + 1
    return {"counts": by, "listed": rows[:limit], "more": max(0, len(rows) - limit)}


def table(hits: list[dict]) -> str:
    lines = ["| Risk | Path | Word | Kind | Owner | Broad grants | Synced? | Suggestion |",
             "|---|---|---|---|---|---|---|---|"]
    for h in hits:
        acc, loc = h["access"], h["location"]
        sync = loc["synced"] or (f"exposed: {loc['exposed']}" if loc["exposed"] else "no")
        broad = "; ".join(acc.get("broad", [])) or ("none" if acc.get("checked") else "not checked")
        sug = h["suggestions"][0]["action"] if h["suggestions"] else "none"
        lines.append(f"| {h['risk']} | {h['path']} | {h['matched'][0]['label']} | {h['kind']} | "
                     f"{acc.get('owner') or '-'} | {broad} | {sync} | {sug} |")
    return "\n".join(lines)


def main(argv=None, access: Access | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", dest="out", default="-")
    ap.add_argument("--depth", type=int, default=8)
    ap.add_argument("--max-entries", type=int, default=200000)
    ap.add_argument("--max-seconds", type=float, default=300)
    ap.add_argument("--max-access", type=int, default=500)
    ap.add_argument("--words")
    ap.add_argument("--access", choices=["auto", "windows", "posix", "none"], default="auto")
    ap.add_argument("--shell", choices=["ps", "sh"])
    ap.add_argument("--template", action="store_true")
    a = ap.parse_args(argv)
    if a.template:
        sys.stdout.write(TEMPLATE)
        return 0
    if not a.paths or not all(os.path.isdir(p) for p in a.paths):
        print("error: every PATH must be an existing folder", file=sys.stderr)
        return 2
    words = shipped_words()
    accepted: list[str] = []
    pfile, source = resolve_private(a.words)
    private_info = {"source": source, "file": None, "words": 0, "accepted": 0}
    if pfile is not None:
        if not pfile.is_file():
            print(f"error: private list not found: {redact(str(pfile))}", file=sys.stderr)
            return 2
        if in_git_tree(pfile):
            print("error: the private list sits inside a git work tree; keep it in ~/.warden/ "
                  "(outside every repo)", file=sys.stderr)
            return 2
        pw, accepted = load_private(pfile)
        words += pw
        private_info.update({"file": redact(str(pfile)), "words": len(pw), "accepted": len(accepted)})
    mode = a.access
    if mode == "auto":
        mode = "windows" if os.name == "nt" else "posix"
    acc = access or Access(mode)
    shell = a.shell or ("ps" if os.name == "nt" else "sh")
    w = Walk(words, accepted, a.depth, a.max_entries, a.max_seconds)
    roots = [os.path.abspath(p) for p in a.paths]
    for r in roots:
        w.check(r, os.path.basename(r.rstrip("/\\")), "folder")
        w.walk(r, 0)
    for i, h in enumerate(w.hits):
        real = h.pop("real")
        if h["kind"] == "link":
            h["access"] = {"checked": False, "reason": "a link: access is its target's"}
        elif i < a.max_access:
            h["access"] = acc.lookup(real)
        else:
            h["access"] = {"checked": False, "reason": f"access cap ({a.max_access}) reached"}
        h["location"] = location(real)
        h["app_owned"] = app_owned(real)
    for h in w.hits:
        h["score"], h["risk"] = risk(h)
        h["suggestions"] = suggestions(h, words, shell)
    w.hits.sort(key=lambda h: (-h["score"], h["path"]))
    for h in w.hits:
        h["matched"] = [{"label": m["label"], "class": m["class"]} for m in h["matched"]]
    out = header("signposts")
    out.update({"roots": [redact(r) for r in roots], "access_mode": mode, "shell": shell,
                "words": {"shipped": len(shipped_words()), "private": private_info},
                "counts": {"entries": w.entries, "hits": len(w.hits), "accepted": w.accepted_hits,
                           "high": sum(h["risk"] == "high" for h in w.hits),
                           "medium": sum(h["risk"] == "medium" for h in w.hits),
                           "low": sum(h["risk"] == "low" for h in w.hits)},
                "partial": w.partial, "hits": w.hits,
                "not_scanned": summarize_not_scanned(w.not_scanned),
                "note": "names and metadata only; no file was opened; nothing was changed"})
    write_json(out, a.out)
    if a.out and a.out != "-":
        c = out["counts"]
        print(f"signposts: {c['hits']} hits in {c['entries']} entries (high {c['high']}, medium "
              f"{c['medium']}, low {c['low']}; {c['accepted']} accepted); {len(w.not_scanned)} not scanned"
              + (f"; PARTIAL ({w.partial})" if w.partial else ""))
        if w.hits:
            print(table(w.hits[:50]))
    return 1 if (w.hits or w.partial) else 0


if __name__ == "__main__":
    sys.exit(main())
