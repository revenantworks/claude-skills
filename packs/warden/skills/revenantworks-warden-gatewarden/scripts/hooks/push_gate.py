#!/usr/bin/env python3
"""push_gate.py: PreToolUse hook (matcher Bash|PowerShell) that gates `git push`.

For every `git push` in a command (compound lines, `git -C <dir>`, a full path to
git, the PowerShell tool) it:
  1. refuses force, delete, mirror, --all and --tags pushes outright, abbreviations included
     (`--forc`, `--delet`, `--mir`: git accepts any unique prefix);
  2. works out the commit range each pushed ref would send, measured against the
     remote's real branch tip (`git ls-remote`; it never fetches). A branch the remote
     lacks counts every commit the remote does not hold; when the remote cannot be
     reached it falls back to the local remote-tracking ref and says so (0356);
  2b. refuses a branch carrying commits not on the remote's main when the repository is public
     (`push_gate.public_branch`, observation 0441): visibility from a cached `gh api` answer
     (`push_gate.py visibility`); unknown visibility checks the push as before and says so;
  3. refuses unless a push intent is recorded for this repo and the range fits it
     (`max_commits`, and `head` when the intent names one);
  4. refuses unless a local-CI stamp exists for the exact commit being pushed;
  5. otherwise allows, and shows the range to Claude and to the person watching.

Wired on PostToolUse as well (same matcher), it checks after the call that the remote holds what was
pushed: a remote that did not move is reported to Claude as a failed push (`decision: block` with the
reason) and to the owner in one line, whatever git printed (observation 0399: "Everything up-to-date"
with two commits ahead). That pass only reads; it asks for no intent or stamp.

Record an intent (the range the request named) before pushing:
  python push_gate.py intend --repo <dir> --max <N> [--head <sha>] [--ttl 900]
Write a CI stamp by running the repo's own CI steps through ci_stamp.py.

Files, per worktree, under `<git dir>/gatewarden/`: push-intent.json, ci-pass.json.
GATEWARDEN_PUSH_NO_INTENT=1 turns the intent check off (range and CI still apply).

Fail mode: closed for anything that names a push. If the event cannot be read, the range cannot be
worked out, or the check runs past its time budget (hooklib.start_budget), a command containing the
word `push` is blocked with the reason; anything else passes. Pushes are found after hooklib.expand
unwraps the command (line continuations, splices, `sh -c`, `pwsh -Command`, `eval`, `iex`,
substitutions, -EncodedCommand, script files, piped scripts, a `cd` earlier on the line). The body of
a heredoc that only feeds text to git or gh (a commit message, a PR body) is prose, not a command, and
is not read for a push (observation 0355; per segment for `git commit -F -` after a `cd`, observation
0381); nor is a quoted string that a prose command (echo, grep,
rg, git commit -m, gh, Set-Content, Out-File) only prints, searches or writes to a file no shell or
interpreter runs (`.md`, `.txt`, `.json`; V-K8w FP1, V-K8w2 FP-B); nor is a heredoc that cat or tee
only writes to a file the line never runs (V-K8w2 FP-A). A program name built at run time counts in
the pipeline that names push, not in an earlier `&&` or `;` step (`$PYTHON x.py && git push`, V-K8w2
FP-D). Remote ref writes through gh are hard refusals too: `gh api` DELETE on `git/refs/…`, `gh api`
PATCH there with `force=true`, `gh repo sync --force` (V-K8w2). Refused as hard shapes (guard in every
mode, since any of them can carry a force push; warden audit K7-4-01, V-K8w): an inline alias, a
pushing alias or one nested past five levels, a run-time subcommand or program name (`git $x`,
`$G push`), Start-Process or xargs feeding git, a redirected git dir or config (GIT_DIR, --git-dir,
GIT_CONFIG_*, HOME, --exec-path), a push in inline code, a git config change to an alias, remote or
url setting on a push line, a script written and run on the same push line, a push argument filled in
at run time (`git push $F origin main`, `"$@"`, `$1`; V-K8w2 B3, B4), a glob in the command word that
may name git on a push segment (`gi[t] push`; B9), a config include (`-c include.path`, `includeIf`,
`--config-env`, a GIT_CONFIG_* include) on a line whose git subcommand is not a builtin and so may be
an alias the gate cannot read (B5; on a push it counts as a redirected config), an alias set through
the environment (GIT_CONFIG_KEY_n=alias.<name>, GIT_CONFIG_VALUE_n) that pushes or whose value cannot be
read, a config redirect (GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, GIT_CONFIG_NOSYSTEM, HOME,
XDG_CONFIG_HOME) on a line whose git subcommand is not a builtin (M14e), and a push the gate
sees but cannot parse. So is a
shell script on disk too large or locked to read, a shell script over 256 KB that names push, and a mirror or `+`/`:` push refspec set in git config (K7-4-03, K7-4-07).
A git command that moves HEAD (commit, merge, cherry-pick, am, rebase, pull, revert, reset, checkout,
switch, update-ref, stash branch) before a push on the same line is refused under `push_gate.range`:
the range is read before the line runs, so a clear on "commits 0" would send a commit no one checked
(observation 0407). Split the commit and the push into separate calls. Hard refusals still apply.
Limits: it binds the commands Claude runs, not the owner's own terminal; it does not read an
interpreter's source file (release tooling pushes by design); a stamp file written by hand defeats
step 4.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

# Global options that take the next word as their value (`--exec-path` alone prints a path).
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--attr-source"}
REFUSED_LONG = {"--force": "force", "--force-with-lease": "force", "--force-if-includes": "force",
                "--delete": "delete", "--mirror": "mirror", "--all": "all branches",
                "--tags": "all tags", "--prune": "prune"}
PUSH_VALUE_OPTS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
# Git's own commands. Any other subcommand may be an alias, so it is resolved before it passes.
BUILTINS = set("""add am annotate apply archive bisect blame branch bugreport bundle cat-file check-attr
check-ignore checkout cherry cherry-pick citool clean clone commit commit-tree config count-objects
credential describe diff diff-files diff-index diff-tree difftool fetch for-each-ref format-patch fsck gc
grep gui hash-object help init instaweb lfs log ls-files ls-remote ls-tree maintenance merge merge-base
merge-file mergetool mv name-rev notes pull range-diff read-tree rebase reflog remote repack replace
request-pull reset restore rev-list rev-parse revert rm shortlog show show-branch show-ref
sparse-checkout stash status submodule switch symbolic-ref tag update-index update-ref var
verify-commit version whatchanged worktree write-tree push""".split())
ALIAS_DEPTH = 5
ENV_REDIRECT = re.compile(r"(?i)(?<![\w])(?:GIT_(?:DIR|WORK_TREE|CONFIG_PARAMETERS|CONFIG_COUNT|CONFIG_KEY_\d+"
                          r"|CONFIG_GLOBAL|CONFIG_SYSTEM|CONFIG|EXEC_PATH)|HOME|XDG_CONFIG_HOME)\s*=")
# A loose reading of `git [options [value]] push`, counted to catch a push the parser missed. Any
# option may take the next word as its value (an unknown one too: `git --attr-source X push`); a match
# whose word follows an option known to take none is a subcommand (`git --no-pager stash push`).
DETECT = re.compile(r"(?<![\w-])git(?:\.exe)?(?:\s+-\S+(?:\s+[^\s-]\S*)?)*?\s+push(?![\w-])")
VALUELESS = {"-p", "--paginate", "-P", "--no-pager", "--bare", "--no-replace-objects", "--literal-pathspecs",
             "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs", "--no-optional-locks", "--no-advice",
             "--no-lazy-fetch", "--exec-path", "--html-path", "--man-path", "--info-path", "-v", "--version",
             "-h", "--help"}
CODE_PUSH = re.compile(r"""(?i)(?<![\w-])git(?:\.exe)?['"]?(?:[\s,]+['"]?[^\s,'"()\[\]]+['"]?){0,4}?"""
                       r"""[\s,]+['"]?push(?![\w-])""")
PUSH_HINT = re.compile(r"(?i)(?<![a-z])push(?![a-z])")
# Inline code that can start a process, load code by name or evaluate a string (B1): with a push named in
# it, the push may run. Code with none of these only computes and writes text, so a push in it is data.
# Broad on purpose: a false hit keeps the old refusal.
CODE_RUNS = re.compile(r"(?i)(?<![\w])(?:os\s*\.\s*(?:system|popen|exec\w*|spawn\w*|posix_spawn\w*|startfile|fork\w*)"
                       r"|subprocess|pty|popen\w*|__import__|importlib|runpy|ctypes|getattr|setattr|__builtins__"
                       r"|builtins|__dict__|globals|vars|locals|eval|exec\w*|compile|system|spawn\w*|fork"
                       r"|child_process|shell_exec|passthru|proc_open|qx|open3|require|import\s*\(|process\s*\."
                       r"\s*binding|deno|bun|%x|invoke|start-process|iex)(?![\w])|`[^`]*push[^`]*`"
                       r"|open\s*\([^)]*\|")
HEREDOC = re.compile(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")
REMOTE_SETTING = re.compile(r"(?i)\s*remote\..+\.(?:mirror|push)(?:=|$)")
PUSH_CONFIG_KEY = re.compile(r"(?i)^(?:alias\.|remotes?\.|url\.|include)")
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "get", "list"}
FALSE = {"false", "no", "off", "0"}
MESSAGE_PROGS = {"git", "gh"}
WRITERS = {"cat", "tee", "git", "gh"}  # a heredoc these read is text, not a script
START = {"start-process", "saps"}
FEEDERS = {"xargs", "parallel"}
LAUNCH = {"&", "!", "time", "nohup", "command", "exec", "builtin", "env", "sudo", "doas", "nice", "ionice",
          "stdbuf", "xargs", "parallel", "timeout", "if", "then", "else", "elif", "while", "until", "do",
          "{", "(", "call"}
# FP1 (V-K8w): programs that only print or search their quoted words, and the pipes they may feed.
PROSE_PROGS = {"echo", "printf", "write-host", "write-output", "write-error", "write-warning", "write-verbose",
               "write-debug", "write-information", "grep", "egrep", "fgrep", "rg", "ag", "ack", "findstr",
               "select-string", "sls", "gh"}
SINKS = {"head", "tail", "wc", "sort", "uniq", "cat", "less", "more", "cut", "tr", "column", "nl",
         "select-object", "out-null", "out-string", "out-host", "measure-object", "format-table", "format-list"}
GIT_PROSE = {"commit", "log", "tag", "notes", "grep", "show", "stash", "merge", "revert", "shortlog",
             "rev-list", "cherry-pick", "status", "diff", "describe"}
QUOTES = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
CONFIG_CHANGES: list[str] = []


def without_message_heredocs(cmd: str) -> str:
    """Blank the body of a heredoc whose line runs only git or gh, with no pipe or redirect:
    `git commit -F - <<'EOF'` reads a message, and a message that names `git push` is not a push
    (observation 0355). Any other heredoc keeps its body, since a shell may run it. Line count kept."""
    lines, out, i = cmd.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        marks = list(HEREDOC.finditer(line))
        if len(marks) != 1:
            continue
        head = line[:marks[0].start()] + line[marks[0].end():]
        segs = hl.segments(head.replace("&&", ";").replace("||", ";"))
        if ("|" in head.replace("||", "") or ">" in head or not segs or
                any(hl.prog((hl.tokens(s) or [""])[0]) not in MESSAGE_PROGS for s in segs)) and \
                not commit_stdin_segment(line):
            continue
        end = marks[0].group(2)
        j = i
        while j < len(lines) and lines[j].strip() != end:
            j += 1
        if j == len(lines):
            continue  # no end line: leave it for the parser to judge
        out += [""] * (j - i)
        i = j
    return "\n".join(out)


COMMIT_STDIN = {"-F-", "--file=-", "--file=/dev/stdin", "-F/dev/stdin"}
GIT_HEAD_OPTS = {"-C"}  # a git option before the subcommand that takes a value (`git -C dir commit`)


def commit_stdin_segment(line: str) -> bool:
    """The heredoc on this line feeds `git commit -F -` (or `-F /dev/stdin`, `--file=-`, `--file -`) in its
    own segment, with no pipe into or out of that segment and no redirect in it (observation 0381). The
    other segments of the line (a `cd`, a `git add`) do not read the body, so they do not keep it."""
    ops = hl.split_ops(line)
    at = next((k for k, (s, _) in enumerate(ops) if HEREDOC.search(s)), None)
    if at is None or ops[at][1] == "|" or (at and ops[at - 1][1] == "|"):
        return False
    seg = HEREDOC.sub(" ", ops[at][0], count=1)
    if ">" in seg or "<" in seg or HEREDOC.search(seg):
        return False
    toks = [arg(t) for t in hl.tokens(seg)]
    if not toks or hl.prog(toks[0]) != "git":
        return False
    n = 1
    while n < len(toks) and toks[n] in GIT_HEAD_OPTS:
        n += 2
    if n >= len(toks) or toks[n] != "commit":
        return False
    rest = toks[n + 1:]
    return any(t in COMMIT_STDIN or (t in ("-F", "--file") and k + 1 < len(rest) and
                                     rest[k + 1] in ("-", "/dev/stdin"))
               for k, t in enumerate(rest))


# A file named on another segment of the line by one of these is read or staged, not run (FP-A).
NOT_RUN = {"git", "cat", "head", "tail", "wc", "ls", "dir", "less", "more", "grep", "egrep", "rg", "findstr",
           "select-string", "sls", "type", "get-content", "gc", "diff", "stat", "code", "echo", "printf", "sort"}


def inert_writer_bodies(text: str) -> str:
    """Blank the body of a heredoc that cat or tee only writes to a file this line never runs (V-K8w2
    FP-A): `cat <<'EOF' > README.md` holding "run git push when done" is notes, not a push. The body
    stays when the head pipes on, writes nowhere, or the written file's name shows on another segment
    whose program may run it (`bash t.sh`, `./t`, `F=t; sh $F`). A script written and run on one line is
    still refused through ex.pending, which is read from the full text. Line count kept."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        marks = list(HEREDOC.finditer(line))
        if len(marks) != 1:
            continue
        j = i
        while j < len(lines) and lines[j].strip() != marks[0].group(2):
            j += 1
        if j == len(lines):
            continue
        ops = hl.split_ops(line)
        at = next((k for k, (s, _) in enumerate(ops) if HEREDOC.search(s)), None)
        if at is None or ops[at][1] == "|" or (at and ops[at - 1][1] == "|"):
            continue
        seg = ops[at][0]
        toks = hl.tokens(seg)
        progs = [hl.prog(t) for t in toks]
        if not progs or progs[0] not in ("cat", "tee"):
            continue
        names = {os.path.basename(p.replace("\\", "/")).lower() for p, _ in hl._writes(seg, toks, progs, True, True)}
        names.discard("")
        if not names:
            continue
        others = [s for k, (s, _) in enumerate(ops) if k != at] + [s for s, _ in hl.split_ops("\n".join(lines[j + 1:]))]
        others += [s for s, _ in hl.split_ops("\n".join(out[:-1]))]
        if any(re.search(r"(?i)(?<![\w.-])" + re.escape(n) + r"(?![\w.-])", s) and not _not_run(s)
               for n in names for s in others):
            continue
        out += [""] * (j - i)
        i = j
    return "\n".join(out)


def _not_run(seg: str) -> bool:
    toks = hl.tokens(seg)
    k = command_index(toks)
    return k is not None and hl.prog(toks[k]) in NOT_RUN and k == 0


def split_heredocs(text: str) -> tuple[str, list[tuple[str, str]]]:
    """(the text with heredoc bodies blanked, [(program that reads the body, body)]). A body a writer
    (cat, tee, git, gh) reads is parsed for a literal push, never alias-resolved (V-K8w F5)."""
    lines, head, bodies, i = text.split("\n"), [], [], 0
    while i < len(lines):
        line = lines[i]
        head.append(line)
        i += 1
        for m in HEREDOC.finditer(line):
            j = i
            while j < len(lines) and lines[j].strip() != m.group(2):
                j += 1
            if j == len(lines):
                break  # no end line: the rest stays in the head and is parsed as commands
            segs = hl.segments(line[:m.start()])
            reader = hl.prog((hl.tokens(segs[-1]) or [""])[0]) if segs else ""
            bodies.append((reader, "\n".join(lines[i:j])))
            head += [""] * (j - i + 1)
            i = j + 1
    return "\n".join(head), bodies


class PushBlock(Exception):
    rule = "push_gate.shape"


class RefBlock(PushBlock):
    rule = "push_gate.irreversible"


class HeadMoveBlock(PushBlock):
    """A command that moves HEAD runs before a push on the same line (observation 0407). The range is
    read before the line runs, so it misses what the line adds. A soft rule: it follows the range mode."""
    rule = "push_gate.range"
    hard = False


# Git commands that can move HEAD or the branch a push sends (observation 0407). `checkout` and `reset`
# with a `--` path list only touch files, so they do not count; of `stash`, only `stash branch` does.
HEAD_MOVERS = {"commit", "merge", "cherry-pick", "am", "rebase", "pull", "revert", "reset", "checkout", "switch",
               "update-ref", "stash"}
PATH_FORM = {"checkout", "reset"}


def moves_head(sub: str, rest: list[str]) -> bool:
    if sub not in HEAD_MOVERS:
        return False
    if sub in PATH_FORM and "--" in rest:
        return False
    if sub == "stash":
        return rest[:1] == ["branch"]
    return True


GH_API_VALUE_OPTS = {"-X", "--method", "-H", "--header", "-f", "--raw-field", "-F", "--field", "--input", "-q",
                     "--jq", "-t", "--template", "--cache", "-p", "--preview", "--hostname"}


def gh_ref_check(toks: list[str]) -> None:
    """Remote ref writes through gh that skip git push (V-K8w2 scope row), refused as hard rules: `gh api`
    DELETE on a `git/refs/…` endpoint, `gh api` PATCH on one with a `force=true` field, and
    `gh repo sync --force` (it hard-resets the remote branch). Literal words only."""
    k = command_index(toks)
    if k is None or hl.prog(toks[k]) != "gh":
        return
    words = [arg(t) for t in toks[k + 1:]]
    if words[:2] == ["repo", "sync"] and any(w == "--force" or w.lower().startswith("--force=") and
                                             w.split("=", 1)[1].lower() not in FALSE for w in words[2:]):
        raise RefBlock("push gate: `gh repo sync --force` resets a remote branch and drops its commits. "
                       "Refused; if the owner wants it, the owner runs it.")
    if words[:1] != ["api"]:
        return
    method, endpoint, fields, n = "", "", [], 1
    while n < len(words):
        w = words[n]
        name, eq, val = w.partition("=")
        if w.startswith("-X") and len(w) > 2 and not w.startswith("--"):
            method = w[2:]
        elif name in GH_API_VALUE_OPTS:
            if not eq:
                val = words[n + 1] if n + 1 < len(words) else ""
                n += 1
            if name in ("-X", "--method"):
                method = val
            elif name in ("-f", "--raw-field", "-F", "--field"):
                fields.append(val)
        elif not w.startswith("-") and not endpoint:
            endpoint = w
        n += 1
    method = method.upper()
    if "git/refs" not in endpoint.lower():
        return
    forced = any(f.split("=", 1)[0].strip().lower() == "force" and f.partition("=")[2].strip().lower()
                 not in FALSE for f in fields)
    if method == "DELETE" or (method == "PATCH" and forced):
        raise RefBlock(f"push gate: `gh api {method} {endpoint}` {'deletes' if method == 'DELETE' else 'force-moves'} "
                       "a remote ref without git push. Refused; if the owner wants it, the owner runs it.")


def arg(tok: str) -> str:
    return hl.despliced(hl.unquote(tok))


_ALIASES: dict[str, dict[str, str]] = {}


def aliases(repo: str) -> dict[str, str]:
    """Every alias the repo sees, read once per run (V-K8w F5: one git call per word ran past the
    hook timeout on a long heredoc, and a timeout lets the call through)."""
    key = os.path.normcase(os.path.abspath(repo or "."))
    if key not in _ALIASES:
        table: dict[str, str] = {}
        try:
            p = subprocess.run(["git", "config", "--get-regexp", r"^alias\."], cwd=repo or None,
                               capture_output=True, text=True, timeout=hl.budget_timeout(15),
                               creationflags=hl.NO_WINDOW)
            for line in p.stdout.splitlines() if p.returncode == 0 else []:
                name, _, value = line.partition(" ")
                table[name[len("alias."):].lower()] = value
        except (OSError, subprocess.SubprocessError):
            pass
        _ALIASES[key] = table
    return _ALIASES[key]


def alias_of(repo: str, sub: str) -> str | None:
    return aliases(repo).get(sub.lower())


def command_index(toks: list[str]) -> int | None:
    """The index of the word a simple command runs, past assignments, launchers and their options."""
    k = 0
    while k < len(toks):
        t = toks[k]
        if not t.strip("({!") or re.match(r"^[A-Za-z_]\w*=", t) or re.match(r"^\$[\w:{}]+\s*=", t) \
                or t.lower() in LAUNCH or hl.prog(t) in LAUNCH or t.startswith("-") \
                or re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", t):
            k += 1
            continue
        if re.fullmatch(r"\$[\w:]+", t) and k + 1 < len(toks) and toks[k + 1].startswith("="):
            k += 2  # PowerShell `$r = git rev-parse HEAD`: the value is the command
            continue
        return k
    return None


def shape_checks(toks: list[str], carries_push: bool = True) -> None:
    """Hard shapes on a text that names push (V-K8w F3, F4). A program built at run time counts only in
    the pipeline that itself names push (V-K8w2 FP-D): `$PYTHON x.py && git push` runs the push plainly."""
    k = command_index(toks)
    if carries_push and k is not None and hl.word(toks[k]) == "\x00":
        raise PushBlock(f"push gate: a program name built at run time (`{toks[k][:40]}`) on a line that "
                        "names push cannot be checked. Blocked; write the program name out.")
    progs = [hl.prog(t) for t in toks]
    for i, p in enumerate(progs):
        later = progs[i + 1:]
        if p in START and any(q in ("git", "git-push") for q in later):
            raise PushBlock("push gate: Start-Process hands git its arguments as data the gate cannot read "
                            "on a line that names push. Blocked; run the push as a plain `git push` line.")
        if p in FEEDERS and any(q in ("git", "git-push") for q in later):
            raise PushBlock(f"push gate: {p} adds git's arguments at run time on a line that names push. "
                            "Blocked; run the push as a plain `git push` line.")


def _plain_git(seg: str) -> bool:
    """A segment whose program is git, written out, with no variable or substitution anywhere in it."""
    toks = hl.tokens(seg)
    k = command_index(toks)
    return k is not None and hl.prog(toks[k]) == "git" and not re.search(r"\$|`", seg)


# A push argument the shell fills in at run time (V-K8w2 B3, B4): `$x`, `${x}`, `$(…)` (flattened to
# `$__SUB` before this runs, backticks too), `"$@"`, `$*`, `$1`..`$9`, and cmd's `%x%`. Read raw, before
# hooklib.despliced drops `$@` and `$*` as empty splices.
RUN_TIME_ARG = re.compile(r"\$[A-Za-z_{(@*#?!0-9]|%[A-Za-z_]\w*%")
# A git program a glob in the command word may name (V-K8w2 B9: `/usr/bin/gi[t] push`).
GIT_NAMES = ("git", "git.exe", "git-push", "git-push.exe")
# A config include loads a file the gate never reads (V-K8w2 B5), so an alias defined there cannot be
# resolved: `-c include.path=…`, `-c includeIf.<cond>.path=…`, `--config-env include.path=ENV`, and
# a GIT_CONFIG_KEY_n or GIT_CONFIG_PARAMETERS assignment that sets one. A key filled in at run time
# (`-c "$CFG"`, `GIT_CONFIG_KEY_0=$K`) may be an include, so it counts as one.
INCLUDE_KEY = re.compile(r"(?i)^\s*include(?:if)?\.")
INCLUDE_ENV = re.compile(r"""(?i)(?<![\w])GIT_CONFIG_(?:KEY_\d+\s*=\s*['"]?\s*(?:include(?:if)?\.|\$|%[A-Za-z_])"""
                         r"""|PARAMETERS\s*=[^\n]*?(?:include(?:if)?\.|\$))""")
# An alias set through the environment (M14e): GIT_CONFIG_KEY_<n>=alias.<name> with GIT_CONFIG_VALUE_<n>,
# the env twin of `-c alias.<name>=…`. Read line-wide, like INCLUDE_ENV.
ENV_CONFIG_PAIR = re.compile(r"""(?i)(?<![\w])GIT_CONFIG_(KEY|VALUE)_(\d+)\s*=\s*"""
                             r"""('[^']*'|"(?:\\.|[^"\\])*"|[^\s;&|)]*)""")
# A config redirect that swaps the files git reads aliases from (M14e): the gate reads its own.
CONFIG_HOME_ENV = re.compile(r"(?i)(?<![\w-])(?:GIT_CONFIG_(?:GLOBAL|SYSTEM|NOSYSTEM)|XDG_CONFIG_HOME|HOME)"
                             r"\s*=(?!=)")


def env_aliases(text: str) -> tuple[dict[str, str], set[str]]:
    """({alias name: literal value}, {alias names whose value cannot be read}) for the aliases the line
    sets through GIT_CONFIG_KEY_<n>/GIT_CONFIG_VALUE_<n>. A value set at run time (`$V`, `"$V"`, a
    substitution) or missing cannot be read; a single-quoted value is literal."""
    keys: dict[str, str] = {}
    vals: dict[str, str] = {}
    for m in ENV_CONFIG_PAIR.finditer(text):
        (keys if m.group(1).upper() == "KEY" else vals)[m.group(2)] = m.group(3)
    table: dict[str, str] = {}
    unread: set[str] = set()
    for n, raw in keys.items():
        key = hl.unquote(raw).strip()
        if not key.lower().startswith("alias."):
            continue
        name, val = key[len("alias."):].lower(), vals.get(n)
        if val is None or not val.startswith("'") and (RUN_TIME_ARG.search(val) or "`" in val):
            unread.add(name)
        else:
            table[name] = hl.unquote(val)
    return table, unread


def run_time_args(raw: list[str]) -> None:
    """Refuse a push whose arguments are filled in at run time: the gate would range-check the literal
    text (`$F` as a remote, `"$@"` as nothing) while the shell pushes what the value holds."""
    for t in strip_redirections(raw):
        if RUN_TIME_ARG.search(t):
            raise PushBlock(f"push gate: push arguments resolved at run time (`{t[:40]}`) cannot be checked. "
                            "Blocked; write the remote and the branch out.")


def glob_git(toks: list[str], seg: str) -> None:
    """Refuse a glob (`*`, `?`, `[`) in the command word when the pattern may name git and the segment
    reads as a push: the shell, not the word, picks the program (`gi[t] push`, `g*t push`, `git-p?sh`).
    A glob in an argument (`grep push *`, `ls *.md`) is not the program and passes."""
    k = command_index(toks)
    if k is None:
        return
    tok = toks[k]
    name = re.split(r"[\\/]", hl.unquote(tok))[-1].lower()
    if not re.search(r"[*?\[]", name):
        return
    if any(fnmatch.fnmatchcase(g, name) for g in GIT_NAMES[2:]) or \
            (PUSH_HINT.search(seg) and any(fnmatch.fnmatchcase(g, name) for g in GIT_NAMES[:2])):
        raise PushBlock(f"push gate: a glob in the command word (`{tok[:40]}`) lets the shell pick the "
                        "program on a line that names push. Blocked; write `git` out.")


def config_write(rest: list[str]) -> bool:
    if any(a.lower() in CONFIG_READS for a in rest):
        return False
    return any(PUSH_CONFIG_KEY.match(a) for a in rest if not a.startswith("-"))


def find_pushes(command: str, cwd: str, resolve: bool = True, head_moves: bool = True) -> list[dict]:
    pushes = []
    flat_cmd = hl.despliced(command)
    named = bool(PUSH_HINT.search(flat_cmd))
    redirected_line = bool(ENV_REDIRECT.search(flat_cmd))
    include_line = bool(INCLUDE_ENV.search(command))
    home_line = bool(CONFIG_HOME_ENV.search(command))
    env_table, env_unread = env_aliases(command)
    ops = hl.split_ops(command)
    # Which pipeline each segment sits in, and which pipelines name push themselves (FP-D).
    line_of, n = [], 0
    for idx, (_, sep) in enumerate(ops):
        line_of.append(n)
        n += sep != "|"
    naming = [idx for idx, (s, _) in enumerate(ops) if PUSH_HINT.search(hl.despliced(s))]
    pushing = {line_of[idx] for idx in naming}
    # The exemption holds only when every segment naming push is a plain `git …` command: a push word in
    # an assignment (`Y=push; $X $Y`) or any other place keeps the line-wide rule.
    plain = all(_plain_git(ops[idx][0]) for idx in naming)
    moved: list[str] = []  # segments before this point that move HEAD (observation 0407)
    for idx, (seg, _) in enumerate(ops):
        hl.check_budget()
        target = hl.cd_target(seg)
        if target:
            cwd = hl.resolve(target, cwd)
            continue
        # A substitution in a word makes that word run-time text (git $(echo push), git `echo push`).
        flat = re.sub(r"`[^`]*`|\$\([^()]*\)", "$__SUB", seg)
        toks = hl.tokens(hl.IFS.sub(" ", flat))
        if named and resolve:
            shape_checks(toks, line_of[idx] in pushing or not plain)
        glob_git(toks, seg)
        for i, tok in enumerate(toks):
            p = hl.prog(tok)
            if p == "git-push":
                run_time_args(toks[i + 1:])
                if moved and head_moves:
                    raise HeadMoveBlock(f"push gate: `{moved[0]}` runs before the push on the same line. "
                                        "Blocked; split the commit and the push into separate calls.")
                pushes.append({"repo": cwd, "args": [arg(t) for t in toks[i + 1:]], "segment": seg.strip()[:160]})
                continue
            if p != "git":
                continue
            repo, j, redirected, include = cwd, i + 1, redirected_line, include_line
            while j < len(toks) and hl.despliced(toks[j]).startswith("-"):
                o = hl.despliced(toks[j])
                opt = o.split("=", 1)[0]
                val = o.split("=", 1)[1] if "=" in o else (arg(toks[j + 1]) if j + 1 < len(toks) else "")
                if opt in ("-c", "--config-env"):
                    raw = toks[j].split("=", 1)[1] if "=" in toks[j] else (toks[j + 1] if j + 1 < len(toks) else "")
                    if INCLUDE_KEY.match(val) or RUN_TIME_ARG.search(raw.split("=", 1)[0]):
                        include = redirected = True  # B5: an included file may set anything, push too
                if opt in ("-c", "--config-env") and val.lower().lstrip().startswith("alias."):
                    raise PushBlock("push gate: an inline git alias (`-c alias.…`) can hide a push. Blocked; "
                                    "run the git command it stands for as a plain line.")
                if opt in ("-c", "--config-env") and REMOTE_SETTING.match(val):
                    raise PushBlock("push gate: an inline remote setting (`-c remote.<name>.mirror` or "
                                    "`.push`) can turn a plain push into a mirror or force push. Blocked; "
                                    "run the push as a plain `git push` line.")
                if opt in ("--git-dir", "--work-tree") or (opt == "--exec-path" and "=" in o):
                    redirected = True
                if opt == "-C" and j + 1 < len(toks):
                    repo = hl.resolve(toks[j + 1], repo)
                    j += 2
                elif opt in GIT_OPTS_WITH_VALUE and "=" not in o and j + 1 < len(toks):
                    j += 2
                else:
                    j += 1
            if j >= len(toks):
                continue
            w = hl.word(toks[j])
            if w == "\x00":
                raise PushBlock("push gate: a git subcommand built at run time cannot be checked. Blocked; "
                                "write the subcommand out.")
            parts = [x for x in re.split(r"[,\s]+", w) if x]
            sub = parts[0] if parts else ""
            if resolve and include and sub and sub not in BUILTINS:
                raise PushBlock(f"push gate: an alias from an included config file cannot be read. `{sub}` is "
                                "not a git builtin, so it may be an alias, and this line loads a config "
                                "include (`-c include.path`, `includeIf`, `--config-env`, GIT_CONFIG_*) or a "
                                "config key set at run time. Blocked; run the command the alias stands for, "
                                "or drop the include.")
            if resolve and home_line and sub and sub not in BUILTINS:
                raise PushBlock(f"push gate: a redirected git dir or config (GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, "
                                f"GIT_CONFIG_NOSYSTEM, HOME, XDG_CONFIG_HOME) swaps the config git reads "
                                f"aliases from. `{sub[:40]}` is not a git builtin, so it may be an alias the "
                                "gate cannot read. Blocked; run the command the alias stands for, or drop "
                                "the redirect.")

            def lookup(name: str, repo: str = repo) -> str | None:
                """An alias the line sets in the environment first (M14e), then the repo's own."""
                if name.lower() in env_unread:
                    raise PushBlock(f"push gate: a git alias set in the environment cannot be read: "
                                    f"`GIT_CONFIG_KEY_<n>=alias.{name[:40]}` has a value set at run time or "
                                    "none. Blocked; run the command the alias stands for.")
                return env_table[name.lower()] if name.lower() in env_table else alias_of(repo, name)

            from_env = False
            expansion = None
            if resolve and sub not in BUILTINS and re.fullmatch(r"[\w.-]+", sub or "-"):
                from_env = sub.lower() in env_table
                expansion = lookup(sub)
            if moves_head(sub, [arg(t) for t in toks[j + 1:j + 2]] + (["--"] if "--" in toks[j + 1:] else [])):
                moved.append(seg.strip()[:80])
            if sub not in ("push", "config", "remote", "send-pack", "http-push") and expansion is None:
                continue  # its arguments are never read: no O(n) copy per word on a long line (V-K8w F5)
            rest = [arg(x) for x in parts[1:]] + [arg(t) for t in toks[j + 1:]]
            if sub == "config" and config_write(rest) or sub == "remote" and \
                    any(a.lower().startswith("--mirror") for a in rest):
                CONFIG_CHANGES.append(seg.strip()[:80])
            if expansion is not None:
                name, depth = sub, 0
                while expansion is not None:
                    depth += 1
                    if depth > ALIAS_DEPTH:  # V-K8w F10: never pass an alias the gate did not resolve
                        raise PushBlock(f"push gate: the git alias `{name}` names another alias more than "
                                        f"{ALIAS_DEPTH} levels deep. Blocked; run the command it stands for.")
                    if expansion.lstrip().startswith("!"):
                        if PUSH_HINT.search(hl.despliced(expansion)):
                            raise PushBlock(f"push gate: the git alias `{name}` runs a shell command that "
                                            "pushes. Blocked; run the push as a plain `git push` line.")
                        break
                    words = expansion.split()
                    while words and words[0].startswith("-"):  # an alias may lead with global options
                        if words.pop(0).split("=", 1)[0] in GIT_OPTS_WITH_VALUE and PUSH_HINT.search(expansion):
                            raise PushBlock(f"push gate: the git alias `{name}` sets git options and names "
                                            "push. Blocked; run the push as a plain `git push` line.")
                    if not words:
                        break
                    sub, rest = arg(words[0]), [arg(x) for x in words[1:]] + rest
                    if sub in BUILTINS:
                        break
                    from_env = from_env or sub.lower() in env_table
                    expansion = lookup(sub)
            if sub in ("send-pack", "http-push"):
                raise PushBlock("push gate: a plumbing push (send-pack, http-push) is refused; use git push.")
            if sub == "push" and from_env:
                raise PushBlock(f"push gate: a git alias set in the environment runs a push (`{name[:40]}`, "
                                "GIT_CONFIG_KEY_<n>=alias.…). Blocked; run the push as a plain `git push` line.")
            if sub == "push":
                if redirected:
                    raise PushBlock("push gate: a push with a redirected git dir or config (GIT_DIR, --git-dir, "
                                    "--work-tree, GIT_CONFIG_*, HOME, --exec-path) cannot be range-checked. "
                                    "Blocked; cd into the repo.")
                run_time_args(toks[j + 1:])
                if moved and head_moves:
                    raise HeadMoveBlock(
                        f"push gate: `{moved[0]}` runs before the push on the same line. The gate reads the "
                        "range before the line runs, so it cannot see what that command adds or moves "
                        "(observation 0407). Blocked; split the commit and the push into separate calls, "
                        "then record the intent and the CI stamp for the new head.")
                pushes.append({"repo": repo, "args": rest, "segment": seg.strip()[:160]})
    return pushes


def blank_quotes(seg: str) -> str:
    """Quoted spans holding whitespace become empty quotes: prose a command prints, not words it runs."""
    return QUOTES.sub(lambda m: m.group(0)[0] * 2 if re.search(r"\s", m.group(0)) else m.group(0), seg)


# A file a shell or an interpreter may run (V-K8w2 FP-B): prose written anywhere else stays prose.
RUNNABLE = re.compile(r"(?i)\.(?:sh|bash|zsh|ksh|fish|ps1|psm1|psd1|bat|cmd|py|pyw|js|mjs|cjs|ts|pl|rb|php|vbs)$")
PS_WRITERS = {"set-content", "sc", "add-content", "ac", "out-file"}


def write_redirect(seg: str) -> bool:
    """True when the segment writes its output to a file a shell or interpreter may run (`> x.sh`,
    `Set-Content run.ps1`). Output to null, a stream or a data or notes file (`>> todo.txt`,
    `> plan.json`, `Out-File notes.md`) is not (V-K8w2 FP-B): a script written and run on the same line
    is still refused through ex.pending."""
    s = QUOTES.sub("", seg)
    for m in re.finditer(r">+\|?", s):
        target = s[m.end():].lstrip()
        if not (target.startswith("&") or re.match(r"(?i)(?:/dev/null|\$null|nul)(?![\w/])", target)):
            word = re.match(r"[^\s;|&<>()]*", target).group(0)
            if not word or RUNNABLE.search(hl.unquote(word)):
                return True
    toks = hl.tokens(seg)
    progs = [hl.prog(t) for t in toks]
    for k, p in enumerate(progs):
        if p in PS_WRITERS:
            paths = [hl.unquote(p2) for p2, _ in hl._writes(" ".join(toks[k:]), toks[k:], progs[k:], True, True)]
            if not paths or any(RUNNABLE.search(x) for x in paths):
                return True
    return False


def prose_program(toks: list[str]) -> bool:
    k = command_index(toks)
    if k is None:
        return False
    p = hl.prog(toks[k])
    if p == "gh":
        return not (k + 1 < len(toks) and hl.word(toks[k + 1]) == "alias")
    if p in PROSE_PROGS or p in SINKS or p in PS_WRITERS:
        return True
    head = toks[k]
    if len(head) > 2 and head[0] == head[-1] and head[0] in "'\"" and re.search(r"\s", head):
        return True  # a PowerShell string literal it prints (`"…" | Out-File x`); no program has spaces
    if p != "git":
        return False
    j = k + 1
    while j < len(toks) and toks[j].startswith("-"):
        j += 2 if toks[j] in GIT_OPTS_WITH_VALUE else 1
    return j < len(toks) and hl.word(toks[j]) in GIT_PROSE


def detect_count(cmd: str) -> int:
    """How many `git … push` the text holds, read loosely. A pipeline of prose commands (echo, grep,
    rg, git commit -m, gh; head, sort and the like after a pipe) with no output written to a file
    has its quoted phrases blanked first (V-K8w FP1): `git commit -m "explain git push"` prints."""
    groups, cur = [], []
    for seg, sep in hl.split_ops(cmd):
        cur.append(seg)
        if sep != "|":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    n = 0
    for group in groups:
        prose = all(prose_program(hl.tokens(s)) and not write_redirect(s) for s in group)
        for s in group:
            for m in DETECT.finditer(hl.despliced(blank_quotes(s) if prose else s).lower()):
                words, prev, sub = m.group(0).split()[1:-1], "", False
                for w in words:
                    if not w.startswith("-") and (prev in VALUELESS or "=" in prev):
                        sub = True  # the word after a valueless option is the subcommand
                    prev = w if w.startswith("-") else ""
                n += not sub
    return n


def names_push(text: str) -> bool:
    return bool(PUSH_HINT.search(hl.despliced(text or ""))) or any(PUSH_HINT.search(t) for t in hl.FILES_READ)


def all_pushes(cmd: str, cwd: str, head_moves: bool = True) -> list[dict]:
    """Every push the command runs, after unwrapping; blocks what cannot be read."""
    cmd = without_message_heredocs(hl.join_lines(cmd))
    try:
        ex = hl.expand(cmd, cwd)
    except hl.Unparseable as exc:
        if exc.script:  # B2 (observation 0419): name the script and the depth; the verdict stays
            raise PushBlock(f"push gate: the script `{os.path.basename(exc.script)}` runs commands nested more "
                            f"than {hl.MAX_DEPTH} levels deep (level {exc.depth} reached), so it cannot be "
                            "checked for a push. Blocked; run the script's steps one by one.")
        if exc.hard or PUSH_HINT.search(hl.despliced(cmd)):
            raise PushBlock(f"push gate: {exc} cannot be checked for a push. Blocked; run the "
                            "command in plain text.")
        return []
    if ex.unread:  # a shell script on disk the gate could not read may hold a force push (K7-4-03)
        raise PushBlock(f"push gate: {ex.unread[0]} cannot be checked for a push. Blocked; run the "
                        "steps it holds as plain lines, or split the script.")
    if any(PUSH_HINT.search(hl.despliced(t)) for t in ex.big):
        raise PushBlock(f"push gate: a shell script over {hl.BIG // 1000} KB that names push is not parsed "
                        "word by word. Blocked; run the push as a plain `git push` line.")
    named = bool(PUSH_HINT.search(hl.despliced(cmd)))
    if ex.pending and named:
        raise PushBlock(f"push gate: a script this line writes and runs ({os.path.basename(ex.pending[0])}) "
                        "cannot be read before it runs, on a line that names push. Blocked; write the "
                        "script in one call and run it in the next.")
    found = []
    for text, where in ex.shells:
        head, bodies = split_heredocs(inert_writer_bodies(text))
        for run in [head] + [body for reader, body in bodies if reader not in WRITERS]:
            for seg in hl.segments(run):
                gh_ref_check(hl.tokens(seg))
        found += find_pushes(head, where or cwd, head_moves=head_moves)
        for reader, body in bodies:
            found += find_pushes(body, where or cwd, resolve=reader not in WRITERS, head_moves=head_moves)
    for body, path in ex.code:
        # Inline code only (python -c, node -e, a quoted heredoc an interpreter reads). A source file an
        # interpreter runs is not read for pushes: release tooling pushes by design (stated limit,
        # references/hooks.md). Push words in code that can start no process are data (B1, 0382): a
        # string the code writes to a file never runs. Any process call, dynamic import or eval keeps
        # the refusal.
        if not path and CODE_PUSH.search(body) and CODE_RUNS.search(body):
            raise PushBlock("push gate: a push run from inline code cannot be range-checked. Blocked; "
                            "run it as a plain `git push` line.")
    detected = detect_count(inert_writer_bodies(hl.data_view(cmd)))
    if detected > len(found):
        raise PushBlock("push gate: this line holds a push the gate cannot parse. Blocked; run the push "
                        "as a plain `git push` line. If the words `git push` are only text, put them in a "
                        "quoted message (`git commit -m`, `echo`, `grep`) or a heredoc, or write a file.")
    if CONFIG_CHANGES and named:  # `git config alias.gp 'push -f' && git gp`: the alias is not set yet
        raise PushBlock(f"push gate: a git config change that can turn a push into a force, mirror or "
                        f"delete push (`{CONFIG_CHANGES[0]}`) shares a line that names push. Blocked; change "
                        "the setting in its own call (the gate reads it before the next push).")
    if ex.opaque and named:
        raise PushBlock(f"push gate: {ex.opaque[0]} on a line that names push. Blocked; run the push as "
                        "a plain `git push` line.")
    unique, seen = [], set()
    for p in found:
        key = (os.path.normcase(os.path.normpath(p["repo"])), tuple(p["args"]))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


# A shell redirection on the push line (`2>&1`, `> log.txt`, `2> err`) is not a push argument.
REDIR = re.compile(r"^(?:\d*|&)(?:>>?|<)(?:&\d+|&-)?$")
REDIR_WITH_TARGET = re.compile(r"^(?:\d*|&)(?:>>?|<)(?:&\d+|&-|\S+)$")


def strip_redirections(args: list[str]) -> list[str]:
    """Drop shell redirections and their file targets from a push's argument list."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if REDIR.match(a) and not a.endswith(("&1", "&2", "&-")):
            skip = True  # a bare `>` or `2>`: the next token is its file
            continue
        if REDIR_WITH_TARGET.match(a):
            continue
        out.append(a)
    return out


def push_positionals(args: list[str]) -> list[str]:
    """The remote and refspecs: option values (`-o x`, `--repo x`) skipped; `--repo` names the remote
    when no positional does."""
    args = strip_redirections(args)
    pos, repo, k = [], None, 0
    while k < len(args):
        a = args[k]
        if a == "--":
            pos += args[k + 1:]
            break
        if a.startswith("-") and len(a) > 1:
            name = a.split("=", 1)[0]
            if name == "--repo":
                repo = a.split("=", 1)[1] if "=" in a else (args[k + 1] if k + 1 < len(args) else None)
            k += 2 if name in PUSH_VALUE_OPTS and "=" not in a else 1
            continue
        pos.append(a)
        k += 1
    return pos if pos or not repo else [repo]


def refused_flag(args: list[str]) -> str | None:
    args = strip_redirections(args)
    for a in args:
        if a.startswith("--"):
            name = a.split("=", 1)[0].lower()
            for flag, why in REFUSED_LONG.items():
                # git takes any unique prefix of a long option (V-K8w F2): `--delet`, `--mir`, `--forc`.
                if name == flag or (len(name) >= 3 and flag.startswith(name)):
                    return f"{why} (`{a}`)"
        elif a.startswith("-") and len(a) > 1:
            if "f" in a[1:]:
                return f"force (`{a}`)"
            if "d" in a[1:]:
                return f"delete (`{a}`)"
        elif a.startswith("+"):
            return f"force (`{a}`)"
        elif a.startswith(":"):
            return f"delete (`{a}`)"
    return None


def config_refusal(repo: str, args: list[str]) -> str | None:
    """A plain push that the repo's git config turns into a mirror, force or delete push (K7-4-07):
    `remote.<name>.mirror` true, or a `remote.<name>.push` refspec starting `+` (force) or `:`
    (delete). A refspec on the command line replaces the configured ones, so those are read only
    when the line names none. With no remote named, every remote is checked: the one git picks
    (pushRemote, pushDefault, the upstream, origin) is among them. A `remotes.<group>` name stands for
    each remote it lists (V-K8w F11)."""
    pos = push_positionals(args)
    p = subprocess.run(["git", "config", "--get-regexp", r"^remote\..*\.(mirror|push)$|^remotes\."],
                       cwd=repo or None, capture_output=True, text=True, timeout=hl.budget_timeout(15),
                       creationflags=hl.NO_WINDOW)
    if p.returncode == 1:
        return None  # no such setting anywhere
    if p.returncode != 0:
        raise RuntimeError("git config could not be read")
    lines = p.stdout.splitlines()
    groups = {k[len("remotes."):].lower(): v.split() for k, _, v in (ln.partition(" ") for ln in lines)
              if k.lower().startswith("remotes.")}
    names = set(groups.get(pos[0].lower(), [pos[0]])) if pos else None
    for line in lines:
        key, _, value = line.partition(" ")
        if key.lower().startswith("remotes."):
            continue
        name, _, var = key[len("remote."):].rpartition(".")
        if names is not None and name not in names:
            continue
        if var == "mirror" and value.strip().lower() not in FALSE:
            return f"mirror (`remote.{name}.mirror` in git config)"
        if var == "push" and len(pos) < 2 and value.strip().startswith(("+", ":")):
            return (f"{'force' if value.strip().startswith('+') else 'delete'} "
                    f"(`remote.{name}.push = {value.strip()}` in git config)")
    return None


def ranges(repo: str, args: list[str]) -> list[dict]:
    pos = push_positionals(args)
    remote = pos[0] if pos else None
    specs = pos[1:]
    if remote is None:
        try:
            up = hl.run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            remote = up.split("/", 1)[0]
        except RuntimeError:
            remote = "origin"
    if not specs:
        branch = hl.run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        try:
            up = hl.run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            dst = up.split("/", 1)[1]
        except (RuntimeError, IndexError):
            dst = branch
        specs = [f"{branch}:{dst}"]
    out = []
    for spec in specs:
        src, _, dst = spec.partition(":")
        dst = dst or src
        sha = hl.run_git(repo, "rev-parse", f"{src}^{{commit}}")
        short_dst = re.sub(r"^refs/(heads|tags)/", "", dst)
        span, note = remote_span(repo, remote, short_dst, dst, sha)
        count = int(hl.run_git(repo, "rev-list", "--count", *span) or 0)
        log = hl.run_git(repo, "log", "--oneline", "-n", "30", *span)
        out.append({"remote": remote, "dst": short_dst, "sha": sha, "count": count, "log": log, "note": note,
                    "tag": is_tag_push(repo, src, dst)})
    return out


def is_tag_push(repo: str, src: str, dst: str) -> bool:
    """The destination is a tag: `refs/tags/…` named out, or a short name that is a local tag and no branch."""
    if dst.startswith("refs/tags/"):
        return True
    if dst.startswith("refs/") or src.startswith("refs/heads/"):
        return False
    for ref, tag in ((f"refs/heads/{src}", False), (f"refs/tags/{src}", True)):
        try:
            hl.run_git(repo, "rev-parse", "--verify", "--quiet", ref)
            return tag
        except RuntimeError:
            continue
    return False


def remote_span(repo: str, remote: str, short_dst: str, dst: str, sha: str) -> tuple[list[str], str]:
    """The rev-list span this push sends, measured against the remote's real tip (observation 0356).

    A local remote-tracking ref goes stale when the remote is deleted, renamed or recreated: it
    then shows 0 new commits while the push sends the whole branch. So the remote is asked first.
    """
    full = dst if dst.startswith("refs/") else f"refs/heads/{short_dst}"
    os.environ["GIT_TERMINAL_PROMPT"] = "0"  # never wait on a credential prompt inside a hook
    try:
        listed = hl.run_git(repo, "ls-remote", remote, full, timeout=10)
    except Exception:  # offline, no such remote, a timeout
        listed = None
    if listed is not None:
        tip = listed.split()[0] if listed.strip() else ""
        if not tip:
            # The remote lacks the branch: every commit it does not already hold is sent.
            return [sha, "--not", f"--remotes={remote}"] if _remote_has_refs(repo, remote) else [sha], \
                "the remote has no such branch"
        try:
            hl.run_git(repo, "cat-file", "-e", f"{tip}^{{commit}}")
            return [f"{tip}..{sha}"], ""
        except RuntimeError:
            return [sha, "--not", f"--remotes={remote}"], "the remote tip is not in this clone"
    tracking = f"refs/remotes/{remote}/{short_dst}"
    try:
        hl.run_git(repo, "rev-parse", "--verify", "--quiet", tracking)
        return [f"{tracking}..{sha}"], "remote not reached; measured against the local tracking ref"
    except RuntimeError:
        return [sha, "--not", f"--remotes={remote}"], "remote not reached; measured against the local tracking refs"


def _remote_has_refs(repo: str, remote: str) -> bool:
    """True when the remote lists any branch: an empty (recreated) remote holds nothing, so a
    stale local tracking ref must not be subtracted."""
    try:
        return bool(hl.run_git(repo, "ls-remote", "--heads", remote, timeout=10).strip())
    except Exception:
        return True


def gw_dir(repo: str) -> str:
    return os.path.join(hl.run_git(repo, "rev-parse", "--absolute-git-dir"), "gatewarden")


# ---------------------------------------------------------------- public branch (observation 0441)
# A branch pushed to a public repository publishes every commit it carries. On 2026-10-15 a branch cut
# from a stale local main put 101 commits of rewritten history on a public repo. Owner decision
# 2026-10-17: refuse a branch push to a public repo when the branch carries commits not on the remote's
# main. Pushing main itself, a tag, and any push to a private repo are unchanged. Visibility comes from
# a cache in the state folder (VISIBILITY_TTL), refreshed by one read-only `gh api` call; when it cannot
# be known the push is checked as before and the cleared note says "visibility unknown".
PUBLIC_RULE = "push_gate.public_branch"
VISIBILITY_TTL = 86400.0
VISIBILITY_FILE = "repo-visibility.json"
GITHUB_URL = re.compile(r"(?i)^(?:https?://(?:[^@/\s]+@)?github\.com(?::\d+)?/|ssh://(?:[^@/\s]+@)?github\.com"
                        r"(?::\d+)?/|[\w.-]+@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
_MAIN: dict[tuple[str, str], tuple[str, str, str]] = {}


def github_slug(url: str) -> str | None:
    """`owner/repo` (lower case) for a github.com remote URL; None for any other host or a path."""
    m = GITHUB_URL.match((url or "").strip())
    return f"{m.group(1)}/{m.group(2)}".lower() if m else None


def remote_url(repo: str, remote: str) -> str:
    """The URL a push to `remote` goes to, as configured (pushurl first; `insteadOf` not applied)."""
    for key in (f"remote.{remote}.pushurl", f"remote.{remote}.url"):
        try:
            return hl.run_git(repo, "config", "--get", key)
        except RuntimeError:
            continue
    return remote if re.search(r"[/:]", remote) else ""


def gh_program() -> list[str]:
    raw = os.environ.get("GATEWARDEN_GH") or "gh"
    if raw.startswith("["):
        try:
            prog = json.loads(raw)
            if isinstance(prog, list) and prog and all(isinstance(x, str) for x in prog):
                return prog
        except ValueError:
            pass
        return []
    return [raw]


def visibility(slug: str, refresh: bool = False) -> tuple[str, str]:
    """("public" | "private" | "unknown", where it came from). A cached answer younger than the TTL is
    used with no network call; otherwise one read-only `gh api repos/<slug> --jq .private` call refreshes
    it. A failed call (gh missing, signed out, offline, no access) answers unknown and caches nothing."""
    path = os.path.join(hl.state_dir(), VISIBILITY_FILE)
    key = f"github.com/{slug}"
    try:
        cache = hl.load_json(path)
        cache = cache if isinstance(cache, dict) else {}
    except (OSError, ValueError):
        cache = {}
    entry = cache.get(key) if isinstance(cache.get(key), dict) else {}
    now = time.time()
    try:
        age = now - float(entry.get("checked_at", 0))
    except (TypeError, ValueError):
        age = -1.0
    if not refresh and isinstance(entry.get("private"), bool) and 0 <= age + 60 and age < VISIBILITY_TTL:
        return ("private" if entry["private"] else "public"), f"cache, {int(age // 3600)} h old"
    prog = gh_program()
    if not prog:
        return "unknown", "GATEWARDEN_GH unreadable"
    env = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1", NO_COLOR="1")
    try:
        p = subprocess.run([*prog, "api", f"repos/{slug}", "--jq", ".private"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=hl.budget_timeout(8), env=env,
                           stdin=subprocess.DEVNULL, creationflags=hl.NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return "unknown", "gh could not run"
    said = (p.stdout or "").strip().lower()
    if p.returncode != 0 or said not in ("true", "false"):
        return "unknown", "gh could not read the repo"
    cache[key] = {"private": said == "true", "checked_at": now}
    try:
        hl.write_json_atomic(path, cache)
    except OSError:
        pass  # the answer stands; the next push asks again
    return ("private" if said == "true" else "public"), "gh api"


def remote_main(repo: str, remote: str) -> tuple[str, str, str]:
    """(the remote's default branch, its tip or "", a note), from `git ls-remote --symref <remote> HEAD`;
    the local tracking refs when the remote cannot be reached. Read once per run."""
    key = (os.path.normcase(os.path.abspath(repo or ".")), remote)
    if key in _MAIN:
        return _MAIN[key]
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    name, tip, note = "main", "", ""
    try:
        listed = hl.run_git(repo, "ls-remote", "--symref", remote, "HEAD", timeout=10)
        for line in listed.splitlines():
            m = re.match(r"^ref:\s*refs/heads/(\S+)\s+HEAD$", line.strip())
            if m:
                name = m.group(1)
            elif re.match(r"^[0-9a-f]{40,64}\s+HEAD$", line.strip()):
                tip = line.split()[0]
        if not tip:
            note = f"the remote has no {name} branch"
    except Exception:
        try:
            name = hl.run_git(repo, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD").split("/", 1)[-1]
        except RuntimeError:
            pass
        try:
            tip = hl.run_git(repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{name}")
            note = "remote not reached; measured against the local tracking ref"
        except RuntimeError:
            note = "remote not reached and no local tracking ref"
    _MAIN[key] = (name, tip, note)
    return _MAIN[key]


def off_main(repo: str, remote: str, sha: str) -> tuple[str, int, str]:
    """(main's name, how many commits `sha` carries that the remote's main does not hold, a note)."""
    name, tip, note = remote_main(repo, remote)
    if tip:
        try:
            hl.run_git(repo, "cat-file", "-e", f"{tip}^{{commit}}")
            return name, int(hl.run_git(repo, "rev-list", "--count", sha, f"^{tip}") or 0), note
        except RuntimeError:
            note = f"the remote's {name} tip is not in this clone (moved or rewritten); fetch first"
    return name, int(hl.run_git(repo, "rev-list", "--count", sha) or 0), note


def public_branch(push: dict, rows: list[dict]) -> list[tuple[str, str]]:
    """The public-branch rule for one push: refuses in guard, else returns rows for the cleared note
    (the nudge, or "visibility unknown"). Watch logs only."""
    out: list[tuple[str, str]] = []
    repo = push["repo"]
    for r in rows:
        if not r["count"] or r.get("tag") or r["dst"] == "main":
            continue
        main, n, note = off_main(repo, r["remote"], r["sha"])
        if r["dst"] == main or n == 0:
            continue
        noun = "commit" if n == 1 else "commits"
        branch, where = r["dst"], f"{r['remote']}/{main}"
        slug = github_slug(remote_url(repo, r["remote"]))
        state, source = visibility(slug) if slug else ("unknown", "not a GitHub remote")
        if state == "private":
            continue
        if state == "unknown":
            out.append(("public", f"visibility unknown ({source}); `{branch}` has {n} {noun} not on {where}, "
                                  "pushed as before"))
            continue
        why = (f"`{branch}` carries {n} {noun} not on {where}, and {slug} is a public repository: the push "
               "would publish them (observation 0441).")
        mode = hl.mode_for(PUBLIC_RULE)
        if mode == "guard":
            hl.block(hl.note("push gate", "refused", why=why,
                             rows=[("read", push.get("segment", "?")), ("branch", f"{branch} → {r['remote']}"),
                                   ("off main", f"{n} {noun}" + (f" ({note})" if note else "")),
                                   ("visibility", f"public ({source})")],
                             fix=f"land the commits on {main} first and push {main}, or push {branch} to a "
                                 "private remote"),
                     rule=PUBLIC_RULE)
        nudged = mode == "nudge" and not hl._nudged_before(PUBLIC_RULE)
        hl.log_event(PUBLIC_RULE, mode, "nudged" if nudged else "logged", why, False)
        if nudged:
            out.append(("public", f"nudge: {branch} carries {n} {noun} not on {where}; {slug} is public. "
                                  f"Land them on {main} first"))
    return out


def visibility_main(argv: list[str]) -> int:
    """`push_gate.py visibility --repo <dir> [--remote origin] [--refresh]`: print what the public-branch
    rule reads for that remote. Read-only on GitHub; --refresh makes the one `gh api` call now."""
    ap = argparse.ArgumentParser(prog="push_gate.py visibility")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    slug = github_slug(remote_url(a.repo, a.remote))
    if not slug:
        print(f"{a.remote}: visibility unknown (not a GitHub remote); the public-branch rule does not apply")
        return 0
    state, source = visibility(slug, refresh=a.refresh)
    print(f"{slug}: {state} ({source})")
    return 0


def refuse_hard(pushes: list[dict]) -> None:
    """Every hard refusal for every push, before any slow range work (a timeout must not reach them)."""
    for check in (lambda p: refused_flag(p["args"]), lambda p: config_refusal(p["repo"], p["args"])):
        for push in pushes:
            why = check(push)
            if why:
                # Name what was read (observation 0327): a refusal the agent cannot
                # explain can only be retried or routed around.
                hl.block(hl.note("push gate", "refused", why=f"a {why} push is refused.",
                                 rows=[("read", push.get("segment", "?")),
                                       ("rule", "pushes go to origin, one named range, never forced or deleting")],
                                 fix="none for Claude; if the owner wants this push, the owner runs it"),
                         rule="push_gate.irreversible", hard=True)


HERE = os.path.dirname(os.path.abspath(__file__))


def range_view(rows: list[dict]) -> tuple[list[tuple[str, str]], list[str]]:
    """Note rows (target, commits) and item lines (`<sha>  <subject>`) for the pushes' ranges."""
    out, items = [], []
    for r in rows:
        out += [("target", f"{r['remote']}/{r['dst']}"),
                ("commits", f"{r['count']}" + (f" ({r['note']})" if r.get("note") else ""))]
        items += [re.sub(r"^(\S+) ", r"\1  ", ln) for ln in r["log"].split("\n") if ln.strip()]
    return out, items


def check_push(push: dict) -> dict:
    """Return the push's note rows, commit lines and skipped CI checks; block otherwise (soft rules)."""
    repo = push["repo"]
    rows = ranges(repo, push["args"])
    total = sum(r["count"] for r in rows)
    view, items = range_view(rows)
    if total == 0:
        return {"rows": view + [("status", "nothing new to push")], "items": items, "partial": [],
                "ranges": rows, "checked": False}
    view += public_branch(push, rows)  # observation 0441: before the intent, so the fix comes first
    d = gw_dir(repo)
    head = rows[-1]["sha"][:12]
    intend = f'python "{os.path.join(HERE, "push_gate.py")}" intend --repo "{repo}"'

    def refuse(why: str, fix: str, rule: str) -> None:
        hl.block(hl.note("push gate", "refused", why=why, rows=view, items=items, fix=fix), rule=rule)

    if os.environ.get("GATEWARDEN_PUSH_NO_INTENT") != "1":
        intent_path = os.path.join(d, "push-intent.json")
        try:
            intent = hl.load_json(intent_path)
        except (OSError, ValueError):
            intent = None
        if not intent or float(intent.get("expires_at", 0)) < time.time():
            refuse(f"no live push intent for this repo ({'expired' if intent else 'absent'}). Record the "
                   "range the request named first.", f"{intend} --max {total} --head {head}", "push_gate.no_intent")
        if total > int(intent.get("max_commits", 0)):
            refuse(f"this push sends {total} commits; the request named at most {intent.get('max_commits')}.",
                   f"push only the named range, or if the request covers all {total}: {intend} --max {total}",
                   "push_gate.range")
        want = intent.get("head")
        if want and all(not r["sha"].startswith(want.lower()) for r in rows):
            refuse(f"the intent names head {want[:12]}, but this push sends "
                   f"{', '.join(r['sha'][:12] for r in rows)}.",
                   f"push the named head, or if the request named this one: {intend} --max {total} --head {head}",
                   "push_gate.head")
    try:
        stamp = hl.load_json(os.path.join(d, "ci-pass.json"))
    except (OSError, ValueError):
        stamp = {}
    for r in rows:
        if stamp.get("head") != r["sha"]:
            stamp_cmd = f'python "{os.path.join(HERE, "ci_stamp.py")}" run --repo "{repo}"'
            if not has_ci(repo):  # observation 0455: a repo with no CI gets the gate's baseline, not improvised steps
                refuse(f"no local CI pass for {r['sha'][:12]}. This repo has no CI (no tracked workflow or "
                       "ci-local script): stamp it with ci_stamp.py --no-ci, the gate's own baseline. Then push.",
                       f"{stamp_cmd} --no-ci", "push_gate.no_ci")
            refuse(f"no local CI pass for {r['sha'][:12]}. Run the repo's CI steps through ci_stamp.py, one "
                   "--step each (or one command after --), with no `bash -c` wrapper: on Windows it can start "
                   "WSL instead of Git Bash. Then push.",
                   f'{stamp_cmd} --step "<step 1>" --step "<step 2>"', "push_gate.no_ci")
    # A stamp that left a CI check out is partial: say so loudly (observation 0354). So is one that
    # covered fewer of its workflow's run: steps than the workflow has (B6, observation 0367).
    short = []
    try:
        total, covered = int(stamp.get("workflow_steps") or 0), int(stamp.get("steps_covered") or 0)
    except (TypeError, ValueError):
        total = covered = 0
    if total and covered < total:
        short.append(f"local CI covered {covered} of {total} run: steps in {stamp.get('workflow', 'the workflow')}")
    return {"rows": view, "items": items, "partial": list(stamp.get("excluded") or []) + short,
            "ranges": rows, "checked": True, "no_ci": bool(stamp.get("no_ci"))}


HAS_CI = re.compile(r"(?i)^\.github/workflows/[^/]+\.ya?ml$|(?:^|/)ci[-_]local(?:\.[a-z0-9]+)?$")


def has_ci(repo: str) -> bool:
    """True when the repo tracks a CI workflow or a ci-local script (ci_stamp.py's HAS_CI; observation
    0455). True when git cannot say, so the refusal keeps asking for the repo's own steps."""
    try:
        out = hl.run_git(repo, "ls-files")
    except Exception:  # noqa: BLE001 - a git failure must not turn into a --no-ci suggestion
        return True
    return not out or any(HAS_CI.search(f) for f in out.splitlines())


def owner_line(views: list[dict]) -> str:
    """The owner's copy of a cleared push: ONE line. The host prefixes every line of a hook's
    message with its own label, so the multi-line note reads as noise there; Claude still gets
    the full note as context. It says where the push goes, what it carries, and what was proved."""
    parts = []
    for v in views:
        for r in v["ranges"]:
            dest = f"{r['remote']}/{r['dst']}"
            if not r["count"]:
                parts.append(f"nothing new → {dest}")
                continue
            log = [ln for ln in r["log"].split("\n") if ln.strip()]
            noun = "commit" if r["count"] == 1 else "commits"
            if r["count"] == 1 and log:
                sha, _, subject = log[0].partition(" ")
                what = f"{sha[:7]} {hl.clip(subject, 56)}"
            else:
                what = f"{log[-1].split(' ')[0][:7]}..{log[0].split(' ')[0][:7]}" if log else r["sha"][:7]
            parts.append(f"{r['count']} {noun} → {dest} · {what}")
    proofs = []
    if any(v["checked"] for v in views):
        if os.environ.get("GATEWARDEN_PUSH_NO_INTENT") != "1":
            proofs.append("intent ✓")
        partial = [s for v in views for s in v["partial"]]
        no_ci = all(v.get("no_ci") for v in views if v["checked"])
        proofs.append(f"local CI PARTIAL ({len(partial)} left to GitHub CI)" if partial
                      else "no-CI baseline ✓" if no_ci else "local CI ✓")
    return " · ".join([f"{hl.GLYPHS['cleared']} push gate", *parts, *proofs])


def line_moves_head(cmd: str) -> bool:
    """True when any segment of the line runs a git command that can move HEAD (0407's list)."""
    for seg in hl.segments(cmd):
        toks = hl.tokens(seg)
        k = command_index(toks)
        if k is None or hl.prog(toks[k]) != "git":
            continue
        j = k + 1
        while j < len(toks) and toks[j].startswith("-"):
            j += 2 if toks[j] in GIT_OPTS_WITH_VALUE else 1
        if j < len(toks) and moves_head(hl.word(toks[j]), [arg(t) for t in toks[j + 1:j + 2]]
                                        + (["--"] if "--" in toks[j + 1:] else [])):
            return True
    return False


def verify_main(ev: dict, cmd: str) -> None:
    """PostToolUse (observation 0399): after a shell call that pushed, ask the remote whether it now holds
    what was pushed. git once printed "Everything up-to-date" with two commits still ahead; a push the
    remote did not take is reported as a failure, never as done. Read-only: it never blocks or refuses,
    and it asks for no intent or stamp. Silent when the line moves HEAD after the push (the local head
    is then not what was pushed) or when nothing was pushed."""
    if ev.get("tool_name") not in hl.SHELL_TOOLS or not PUSH_HINT.search(hl.despliced(cmd)):
        hl.allow()
    try:
        pushes = all_pushes(cmd, ev.get("cwd") or os.getcwd(), head_moves=False)
    except PushBlock:
        hl.allow()  # the pre-push gate refused or could not read it: nothing to compare
    if not pushes or line_moves_head(cmd):
        hl.allow()
    behind, unreached = [], []
    for push in pushes:
        for r in ranges(push["repo"], push["args"]):
            if r["note"].startswith("remote not reached"):
                unreached.append(f"{r['remote']}/{r['dst']}")
            elif r["count"]:
                behind.append(r)
    if behind:
        r = behind[0]
        noun = "commit" if r["count"] == 1 else "commits"
        reason = (f"push gate: the remote did not move. {r['remote']}/{r['dst']} still lacks {r['count']} "
                  f"{noun} up to {r['sha'][:12]} after this push, whatever git printed (observation 0399). "
                  f"The push is not done. Run `git push -v {r['remote']} {r['dst']}` once, then compare "
                  f"`git ls-remote {r['remote']} {r['dst']}` with the local head, and report the push as "
                  "failed until they match.")
        line = (f"{hl.GLYPHS['refused']} push gate · remote did not move · {r['remote']}/{r['dst']} lacks "
                f"{r['count']} {noun} · {r['sha'][:7]}")
        sys.stdout.write(json.dumps({"decision": "block", "reason": reason, "systemMessage": line}) + "\n")
        sys.exit(0)
    if unreached:
        hl.allow(context=f"push gate: could not reach {', '.join(unreached)} to confirm the push landed. "
                         "Check `git ls-remote` against the local head before reporting it done.")
    hl.allow()


def hook_main() -> None:
    ev, raw = hl.read_event()
    if hl.stood_down("W2"):
        sys.exit(0)
    cmd = hl.command_of(ev) if ev else ""
    if ev and ev.get("hook_event_name") == "PostToolUse":
        try:
            verify_main(ev, cmd)
        except SystemExit:
            raise
        except Exception:
            hl.allow()  # a check after the fact never fails the call it follows

    hl.start_budget("push_gate.shape", "push gate: this push could not be checked in time.",
                    lambda: names_push(cmd or raw))
    try:
        if ev is None:
            raise ValueError("unreadable hook input")
        if ev.get("tool_name") not in hl.SHELL_TOOLS:
            hl.allow()
        if len(cmd) > hl.BIG:  # V-K8w F8: never parse a huge command word by word
            if names_push(cmd):
                hl.block(f"push gate: a command over {hl.BIG // 1000} KB that names push is not parsed word "
                         "by word. Blocked; run the push as a plain `git push` line.",
                         rule="push_gate.shape", hard=True)
            hl.allow()
        head_move = None
        try:
            pushes = all_pushes(cmd, ev.get("cwd") or os.getcwd())
        except HeadMoveBlock as exc:
            # A HEAD move before the push (0407) is a range question, so it follows the range mode. The
            # line is read again without that rule first, so every hard refusal and shape still applies.
            head_move = exc
            try:
                pushes = all_pushes(cmd, ev.get("cwd") or os.getcwd(), head_moves=False)
            except PushBlock as inner:
                hl.block(str(inner), rule=inner.rule, hard=True)
        except PushBlock as exc:
            # Hard (K7-4-01): a push the gate cannot read may be a force or delete push in disguise.
            hl.block(str(exc), rule=exc.rule, hard=True)
        for p in pushes:  # B3 (observation 0435): the folder is made by this same command
            if not os.path.isdir(p["repo"]):
                hl.block(hl.note("push gate", "refused",
                                 why="the push target is created in this same command, so it cannot be "
                                     "checked before the command runs.",
                                 rows=[("read", p.get("segment", "?")), ("folder", p["repo"])],
                                 fix="create and commit first, then push in its own call"),
                         rule="push_gate.unreadable", hard=True)
        if head_move is not None:
            refuse_hard(pushes)
            if hl.mode_for(head_move.rule) != "watch":
                hl.block(str(head_move), rule=head_move.rule)
            hl.log_event(head_move.rule, "watch", "logged", str(head_move), False)
        if not pushes:
            hl.allow()
        refuse_hard(pushes)
        views = [check_push(p) for p in pushes]
        rows = [r for v in views for r in v["rows"]]
        partial = [s for v in views for s in v["partial"]]
        if partial:
            rows.append(("partial", "local CI was PARTIAL, not the CI verdict; not run locally: "
                         + "; ".join(partial) + ". CI on the push decides those."))
        msg = hl.note("push gate", "cleared", rows=rows, items=[i for v in views for i in v["items"]])
        loud = hl.mode_for("push_gate.no_intent") == "guard" or bool(partial)
        line = owner_line(views)
        if partial:  # the owner still needs the names of the checks local CI skipped
            line += " — not run locally: " + "; ".join(partial)
        hl.allow(context=msg, message=line if loud else "")
    except SystemExit:
        raise
    except Exception as exc:  # fail closed for a push
        if re.search(r"\bpush\b", raw or ""):
            # git's stderr can echo a remote URL or a ref name: mask secret shapes (K7-4-12).
            hl.block(f"push gate: could not check this push ({type(exc).__name__}: {hl.scrub(str(exc))}). "
                     "Blocked.", rule="push_gate.unreadable", hard=True)
        hl.allow()


def intend_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="push_gate.py intend")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--max", type=int, required=True, dest="max_commits")
    ap.add_argument("--head")
    ap.add_argument("--ttl", type=int, default=900)
    ap.add_argument("--quiet", action="store_true", help="the one-line verdict only (it is one line already)")
    a = ap.parse_args(argv)
    d = gw_dir(a.repo)
    os.makedirs(d, exist_ok=True)
    head = a.head
    if head:
        try:  # store the full sha, so a short one on the command line still matches
            head = hl.run_git(a.repo, "rev-parse", f"{head}^{{commit}}")
        except RuntimeError:
            print(f"push intent: {head} is not a commit in this repo", file=sys.stderr)
            return 2
    data = {"max_commits": a.max_commits, "head": head, "written_at": time.time(),
            "expires_at": time.time() + a.ttl}
    hl.write_json_atomic(os.path.join(d, "push-intent.json"), data)
    print(f"push intent recorded: at most {a.max_commits} commit(s)"
          + (f", head {head[:12]}" if head else "") + f", for {a.ttl} s")
    return 0


def preflight_main(argv: list[str]) -> int:
    """S3: the local CI stamp, the push intent and a one-line verdict in one call. It never pushes; the
    push stays its own visible call.

      python push_gate.py preflight --repo <r> --max <n> [--head <sha>] [--ttl 900] [--excluded "N: R"]
          [--workflow <file> [--covers N|all]] [--step "<cmd>" ...] [--quiet] [-- <ci command>]

    The CI run has ci_stamp.py's rules (clean tree, HEAD unmoved, a skipped check is no stamp unless
    --excluded) and its full log stays in <git dir>/gatewarden/ci-last.log. The intent names the stamped
    head unless --head names another."""
    ap = argparse.ArgumentParser(prog="push_gate.py preflight")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--max", type=int, required=True, dest="max_commits")
    ap.add_argument("--head")
    ap.add_argument("--ttl", type=int, default=900)
    ap.add_argument("--excluded", action="append", default=[])
    ap.add_argument("--step", action="append", default=[])
    ap.add_argument("--workflow")
    ap.add_argument("--covers")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--quiet", action="store_true", help="accepted for symmetry; the output is one line")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    stamp_args = [sys.executable, os.path.join(HERE, "ci_stamp.py"), "run", "--repo", a.repo, "--quiet",
                  "--runs", str(a.runs)]
    for item in a.excluded:
        stamp_args += ["--excluded", item]
    for step in a.step:
        stamp_args += ["--step", step]
    if a.workflow:
        stamp_args += ["--workflow", a.workflow] + (["--covers", a.covers] if a.covers else [])
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if cmd:
        stamp_args += ["--", *cmd]
    p = subprocess.run(stamp_args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=hl.NO_WINDOW)
    said = " ".join(((p.stdout or "") + " " + (p.stderr or "")).split())
    if p.returncode != 0:
        print(f"preflight: no stamp, no intent ({hl.clip(said, 200)})", file=sys.stderr)
        return p.returncode
    try:
        stamp = hl.load_json(os.path.join(gw_dir(a.repo), "ci-pass.json"))
    except (OSError, ValueError):
        print("preflight: the stamp could not be read back; no intent recorded", file=sys.stderr)
        return 2
    head = a.head or stamp.get("head")
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        rc = intend_main(["--repo", a.repo, "--max", str(a.max_commits), "--head", head, "--ttl", str(a.ttl)])
    if rc != 0:
        print(f"preflight: CI stamped, but the intent was not recorded (head {head})", file=sys.stderr)
        return rc
    rows = ranges(a.repo, [])
    total = sum(r["count"] for r in rows)
    span = ", ".join(f"{r['remote']}/{r['dst']}..{r['sha'][:12]}" for r in rows)
    partial = list(stamp.get("excluded") or [])
    if int(stamp.get("workflow_steps") or 0) > int(stamp.get("steps_covered") or 0):
        partial.append(f"{stamp.get('steps_covered')} of {stamp.get('workflow_steps')} workflow steps")
    print(f"preflight: {os.path.basename(os.path.abspath(a.repo))} · {span} · {total} "
          f"commit{'s' if total != 1 else ''} · stamp {str(stamp.get('head'))[:12]} · "
          + (f"PARTIAL ({'; '.join(partial)})" if partial else "full")
          + (f" · over the intent of {a.max_commits}" if total > a.max_commits else ""))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "intend":
        sys.exit(intend_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "preflight":
        sys.exit(preflight_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "visibility":
        sys.exit(visibility_main(sys.argv[2:]))
    hook_main()
