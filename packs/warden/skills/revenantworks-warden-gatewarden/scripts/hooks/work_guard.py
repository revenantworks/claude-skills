#!/usr/bin/env python3
"""work_guard.py: PreToolUse hook (matcher Bash|PowerShell) for five command shapes that each broke a
written rule twice or more. A rule broken twice gets a barrier, not a third sentence.

Rules (every one hard: guard in every mode, since each was already a standing rule in prose):

  work_guard.stash         `git stash` (any subcommand but `list` and `show`) in a repo whose
                           `git worktree list` shows more than one worktree. Units and controllers
                           share that checkout; a stash hides their work (observations 0559, 0563).
  work_guard.sed_inplace   `sed -i` / `sed --in-place` (also `-Ei`, `-i.bak`, after `xargs` or
                           `find -exec`). The permission layer denies it with no reason, and the rest
                           of a compound line is lost with it (observation 0632). Use the Edit tool.
  work_guard.no_verify     `git commit --no-verify` / `-n`, `--no-verify` on push, merge, rebase or am,
                           and `git -c core.hooksPath=...` on those: a skipped hook is a skipped check
                           (observation 0711). Passes only while an owner word is recorded with
                           `work_guard.py owner-ok` (the push-intent pattern).
  work_guard.branch_moved  `git commit`, `merge` or `cherry-pick` when the checkout's branch is not
                           the one this session saw at its last commit there, and this session ran no
                           checkout or switch there since: another session switched it under you
                           (observation 0671).
  work_guard.merge_chain   `gh pr merge` on the same line as a checks read (`gh pr checks`,
                           `gh run view|watch|list`, a `statusCheckRollup` view, a check-runs API
                           read). The merge runs whatever the read printed (observation 0691).

Only words in program position count. Heredoc bodies are blanked unless a shell reads them, and a
quoted string is one word, so `git commit -m "never git stash"` or a brief that names `sed -i` is
data (observation 0392). Limits: a command built at run time, a script file or `bash -c '...'` text is
not read; push_gate and the permission layer stay the other layers.

Owner word for no_verify, recorded before the call (it expires, 900 s by default):
  python work_guard.py owner-ok --repo <repo> --said "<the owner's words>" [--ttl 900]

Fail mode: open on an unreadable event or a crash (the permission layer and the guard hooks stay).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

HEREDOC = re.compile(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")
GIT_VALUE_OPTS = {"-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
                  "--super-prefix", "--attr-source"}
STASH_READS = {"list", "show"}
VERIFY_SUBS = {"commit", "push", "merge", "rebase", "am"}
NO_VERIFY = re.compile(r"^--no-veri(?:f|fy)?$")
COMMIT_VALUE_SHORT = set("mFCct")
COMMIT_VALUE_LONG = {"--message", "--file", "--author", "--date", "--template", "--reuse-message",
                     "--reedit-message", "--fixup", "--squash", "--trailer", "--cleanup",
                     "--pathspec-from-file"}
COMMIT_SUBS = {"commit", "merge", "cherry-pick"}
SWITCH_SUBS = {"checkout", "switch", "rebase", "bisect"}
SED_VALUE_SHORT = set("efl")
SED_SHORT_FLAGS = set("nErsuzi")
EXEC_FLAGS = {"-exec", "-execdir", "-ok", "-okdir"}
SEEN_FILE = "branch-seen.json"
SEEN_TTL = 7 * 86400
OWNER_FILE = "owner-ok.json"

STASH_WHY = ("`git stash` in a checkout with {n} worktrees: other units or sessions write here, and a "
             "stash hides their changes too (observations 0559, 0563).")
STASH_FIX = ("Park your work with a WIP commit on your own branch, or work in your own worktree: "
             "`git worktree add --detach <path>`. `git stash list` and `git stash show` pass.")
SED_WHY = "`sed -i` edits a file in place; the permission layer denies it and drops the rest of the line (observation 0632)."
SED_FIX = "Use the Edit tool for the change, or `sed ... src > new` and then the Edit or Write tool."
NOVERIFY_WHY = ("`{what}` skips the repo's git hooks, and the standing rules say never skip them "
                "(observation 0711). A WIP commit to park work never needs it.")
NOVERIFY_FIX = ("Fix what the hook refuses and commit again. If the owner asked for the skip in words, "
                "record them first: python work_guard.py owner-ok --repo <repo> --said \"<their words>\".")
MOVED_WHY = ("this checkout is on `{now}`, but at this session's last commit here it was on `{was}`, and "
             "this session ran no checkout or switch here since: another session switched it (observation 0671).")
MOVED_FIX = ("Commit from your own worktree (`git worktree add`). If you moved it yourself, run "
             "`git switch {now}` in its own call, then commit again.")
CHAIN_WHY = ("`gh pr merge` runs on the same line as the checks read, so it merges whatever the read "
             "printed, red included (observation 0691).")
CHAIN_FIX = "Read the checks in one call, row by row; merge in the next call."


class Hit(Exception):
    def __init__(self, rule: str, why: str, fix: str, rows=()):
        super().__init__(why)
        self.rule, self.why, self.fix, self.rows = rule, why, fix, list(rows)


# ---------------------------------------------------------------- reading the line

def blank_heredocs(text: str) -> tuple[str, list[str]]:
    """(the text with heredoc bodies blanked, bodies a shell reads). Any other reader's body is data."""
    lines, head, shell_bodies, i = text.split("\n"), [], [], 0
    while i < len(lines):
        line = lines[i]
        head.append(line)
        i += 1
        for m in HEREDOC.finditer(line):
            j = i
            while j < len(lines) and lines[j].strip() != m.group(2):
                j += 1
            if j == len(lines):
                break  # no end line: the rest is read as commands
            segs = hl.segments(line[:m.start()])
            reader = hl.prog((hl.tokens(segs[-1]) or [""])[0]) if segs else ""
            if reader in hl.SHELLS:
                shell_bodies.append("\n".join(lines[i:j]))
            head += [""] * (j - i + 1)
            i = j + 1
    return "\n".join(head), shell_bodies


def program_at(toks: list[str], k: int = 0) -> int | None:
    """Index of the program word from k on, past assignments and launchers."""
    while k < len(toks):
        t = toks[k]
        if re.match(r"^[A-Za-z_]\w*=", t) or t in hl.LAUNCHERS or hl.prog(t) in hl.LAUNCHERS:
            k += 1
            continue
        if hl.COUNT_ARG.match(t) and k > 0:
            k += 1
            continue
        return k
    return None


def flag(tok: str) -> str:
    return hl.unquote(tok)


def git_call(toks: list[str], k: int, cwd: str) -> tuple[str, list[str], str, list[str]]:
    """(subcommand, its arguments, the folder git runs in, the -c values) for `git` at toks[k]."""
    i, configs = k + 1, []
    while i < len(toks):
        t = flag(toks[i])
        if t == "-C" and i + 1 < len(toks):
            cwd = hl.resolve(flag(toks[i + 1]), cwd)
            i += 2
        elif t.startswith("-C") and len(t) > 2:
            cwd = hl.resolve(t[2:], cwd)
            i += 1
        elif t == "-c" and i + 1 < len(toks):
            configs.append(flag(toks[i + 1]))
            i += 2
        elif t in GIT_VALUE_OPTS and i + 1 < len(toks):
            i += 2
        elif t.startswith("-"):
            i += 1
        else:
            return t.lower(), [flag(x) for x in toks[i + 1:]], cwd, configs
    return "", [], cwd, configs


def calls(command: str, cwd: str, depth: int = 0):
    """Yield (program, arguments, folder, -c values) for every program-position call on the line, the
    folder following `cd`. `find -exec` and `xargs` runs count; a shell's heredoc body is read too."""
    text, shell_bodies = blank_heredocs(hl.join_lines(command))
    for seg in hl.segments(text):
        target = hl.cd_target(seg)
        if target is not None:
            cwd = hl.resolve(target, cwd)
            continue
        toks = [t.strip("()") for t in hl.tokens(seg)]
        toks = [t for t in toks if t]
        starts, k = [], program_at(toks)
        if k is not None:
            starts.append(k)
        starts += [j + 1 for j, t in enumerate(toks) if flag(t) in EXEC_FLAGS and j + 1 < len(toks)]
        for k in starts:
            p = hl.prog(toks[k])
            if p == "git":
                sub, args, where, configs = git_call(toks, k, cwd)
                yield "git", [sub] + args, where, configs
            else:
                yield p, [flag(t) for t in toks[k + 1:]], cwd, []
    if depth < 2:
        for body in shell_bodies:
            yield from calls(body, cwd, depth + 1)


def git_out(cwd: str, *args: str) -> str | None:
    try:
        return hl.run_git(cwd, *args, timeout=10)
    except Exception:
        return None


# ---------------------------------------------------------------- the rules

def check_stash(args: list[str], cwd: str) -> None:
    rest = args[1:]
    action = rest[0].lower() if rest and not rest[0].startswith("-") else "push"
    if action in STASH_READS:
        return
    listing = git_out(cwd, "worktree", "list", "--porcelain")
    n = sum(1 for ln in (listing or "").splitlines() if ln.startswith("worktree "))
    if n > 1:
        raise Hit("work_guard.stash", STASH_WHY.format(n=n), STASH_FIX, [("stash", action), ("repo", cwd)])


def sed_in_place(args: list[str]) -> bool:
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--":
            return False
        if a == "--in-place" or a.startswith("--in-place="):
            return True
        if a.startswith("--") or not a.startswith("-") or len(a) < 2:
            continue
        for n, ch in enumerate(a[1:], 1):
            if ch == "i":
                return True
            if ch in SED_VALUE_SHORT:
                skip = n == len(a) - 1
                break
            if ch not in SED_SHORT_FLAGS:
                break
    return False


def verify_skip(sub: str, args: list[str], configs: list[str]) -> str:
    """The flag that skips the hooks, or ''."""
    for c in configs:
        if c.lower().startswith("core.hookspath"):
            return f"git -c {c.split('=', 1)[0]}=... {sub}"
    skip = False
    for a in args[1:]:
        if skip:
            skip = False
            continue
        if a == "--":
            break
        if NO_VERIFY.match(a):
            return f"git {sub} --no-verify"
        if sub != "commit":
            continue
        if a in COMMIT_VALUE_LONG:
            skip = True
        elif a.startswith("-") and not a.startswith("--") and len(a) > 1:
            for n, ch in enumerate(a[1:], 1):
                if ch == "n":
                    return f"git commit {a}"
                if ch in COMMIT_VALUE_SHORT or ch in "Su":
                    skip = ch in COMMIT_VALUE_SHORT and n == len(a) - 1
                    break
    return ""


def owner_ok(cwd: str) -> str:
    """The owner's recorded words for a hook skip in this repo while live, else ''."""
    gd = git_out(cwd, "rev-parse", "--absolute-git-dir")
    if not gd:
        return ""
    try:
        data = hl.load_json(os.path.join(gd, "gatewarden", OWNER_FILE))
        rec = data.get("no_verify") if isinstance(data, dict) else None
        if isinstance(rec, dict) and float(rec.get("expires_at", 0)) > time.time() and str(rec.get("said", "")).strip():
            return str(rec["said"]).strip()
    except (OSError, ValueError, TypeError):
        pass
    return ""


def where_is(cwd: str) -> tuple[str, str] | None:
    out = git_out(cwd, "rev-parse", "--show-toplevel", "--abbrev-ref", "HEAD")
    lines = (out or "").splitlines()
    return (os.path.normcase(os.path.normpath(lines[0])), lines[1]) if len(lines) >= 2 else None


def seen_load() -> dict:
    try:
        data = hl.load_json(os.path.join(hl.state_dir(), SEEN_FILE))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def seen_save(data: dict) -> None:
    now = time.time()
    data = {k: v for k, v in data.items() if isinstance(v, dict) and now - float(v.get("at", 0)) < SEEN_TTL}
    try:
        hl.write_json_atomic(os.path.join(hl.state_dir(), SEEN_FILE), data)
    except OSError:
        pass


CHECK_READ = re.compile(r"(?i)statusCheckRollup|check-runs|check-suites|/status\b")


def checks_read(prog: str, args: list[str]) -> bool:
    if prog != "gh" or len(args) < 2:
        return False
    a, b = args[0].lower(), args[1].lower()
    if (a, b) == ("pr", "checks") or (a == "run" and b in ("view", "watch", "list")):
        return True
    if (a, b) == ("pr", "view") or a == "api":
        return any(CHECK_READ.search(x) for x in args)
    return False


def check(ev: dict) -> Hit | None:
    """The first rule the event's command breaks, or None. Pure apart from git reads and the
    branch-seen state, so the tests call it in-process (observation 0725: fewer process spawns)."""
    if ev.get("tool_name") not in hl.SHELL_TOOLS:
        return None
    if hl._EVENT is not ev:  # in-process callers: hooklib reads the tool (PowerShell or not) from here
        hl._EVENT.clear()
        hl._EVENT.update(ev)
    cmd = hl.command_of(ev)
    if not cmd or len(cmd) > hl.BIG:
        return None
    cwd = str(ev.get("cwd") or os.getcwd())
    session = str(ev.get("session_id") or "")
    seen, dirty, switched, read_checks = seen_load(), False, set(), False
    try:
        for prog, args, where, configs in calls(cmd, cwd):
            if checks_read(prog, args):
                read_checks = True
            if prog == "gh" and args[:2] == ["pr", "merge"] and read_checks:
                raise Hit("work_guard.merge_chain", CHAIN_WHY, CHAIN_FIX)
            if prog == "gh" and args[:2] == ["pr", "checkout"]:
                switched.add(where)
            if prog == "sed" and sed_in_place(args):
                raise Hit("work_guard.sed_inplace", SED_WHY, SED_FIX)
            if prog != "git" or not args:
                continue
            sub = args[0]
            if sub == "stash":
                check_stash(args, where)
            if sub in VERIFY_SUBS:
                what = verify_skip(sub, args, configs)
                if what and not owner_ok(where):
                    raise Hit("work_guard.no_verify", NOVERIFY_WHY.format(what=what), NOVERIFY_FIX)
            if sub in SWITCH_SUBS or sub == "worktree":
                switched.add(where)
            if sub in COMMIT_SUBS and session:
                if where in switched:
                    continue  # this line moves the branch itself; the next commit relearns it
                loc = where_is(where)
                if loc is None:
                    continue
                key = session + "|" + loc[0]
                was = (seen.get(key) or {}).get("branch")
                if was and was != loc[1]:
                    raise Hit("work_guard.branch_moved", MOVED_WHY.format(now=loc[1], was=was),
                              MOVED_FIX.format(now=loc[1]), [("repo", loc[0])])
                seen[key] = {"branch": loc[1], "at": time.time()}
                dirty = True
        if session and switched:
            for w in switched:
                loc = where_is(w)
                if loc and seen.pop(session + "|" + loc[0], None) is not None:
                    dirty = True
    except Hit as hit:
        return hit
    finally:
        if dirty:
            seen_save(seen)
    return None


# ---------------------------------------------------------------- entry points

def hook_main() -> None:
    ev, _raw = hl.read_event()
    if ev is None:
        hl.allow()
    hit = check(ev)
    if hit:
        hl.block(hl.note("work guard", "refused", why=hit.why, rows=hit.rows, fix=hit.fix), rule=hit.rule, hard=True)
    hl.allow()


def owner_ok_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="work_guard.py owner-ok")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--said", required=True, help="the owner's own words asking for the hook skip")
    ap.add_argument("--ttl", type=int, default=900)
    a = ap.parse_args(argv)
    if not a.said.strip():
        print("owner-ok: --said is empty; record the owner's own words", file=sys.stderr)
        return 2
    gd = git_out(a.repo, "rev-parse", "--absolute-git-dir")
    if not gd:
        print(f"owner-ok: {a.repo} is not a git repo", file=sys.stderr)
        return 2
    d = os.path.join(gd, "gatewarden")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, OWNER_FILE)
    try:
        data = hl.load_json(path)
        data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    data["no_verify"] = {"said": a.said.strip(), "written_at": time.time(), "expires_at": time.time() + a.ttl}
    hl.write_json_atomic(path, data)
    print(f"owner word recorded for a hook skip in this repo, for {a.ttl} s")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "owner-ok":
        sys.exit(owner_ok_main(sys.argv[2:]))
    try:
        hook_main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
