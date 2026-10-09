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
  3. refuses unless a push intent is recorded for this repo and the range fits it
     (`max_commits`, and `head` when the intent names one);
  4. refuses unless a local-CI stamp exists for the exact commit being pushed;
  5. otherwise allows, and shows the range to Claude and to the person watching.

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
is not read for a push (observation 0355); nor is a quoted string that a prose command (echo, grep,
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
an alias the gate cannot read (B5; on a push it counts as a redirected config), and a push the gate
sees but cannot parse. So is a
shell script on disk too large or locked to read, a shell script over 256 KB that names push, and a mirror or `+`/`:` push refspec set in git config (K7-4-03, K7-4-07).
Limits: it binds the commands Claude runs, not the owner's own terminal; it does not read an
interpreter's source file (release tooling pushes by design); a stamp file written by hand defeats
step 4.
"""
from __future__ import annotations

import argparse
import fnmatch
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
        if "|" in head.replace("||", "") or ">" in head or not segs or \
                any(hl.prog((hl.tokens(s) or [""])[0]) not in MESSAGE_PROGS for s in segs):
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


def find_pushes(command: str, cwd: str, resolve: bool = True) -> list[dict]:
    pushes = []
    flat_cmd = hl.despliced(command)
    named = bool(PUSH_HINT.search(flat_cmd))
    redirected_line = bool(ENV_REDIRECT.search(flat_cmd))
    include_line = bool(INCLUDE_ENV.search(command))
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
            expansion = alias_of(repo, sub) if resolve and sub not in BUILTINS and \
                re.fullmatch(r"[\w.-]+", sub or "-") else None
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
                    expansion = alias_of(repo, sub)
            if sub in ("send-pack", "http-push"):
                raise PushBlock("push gate: a plumbing push (send-pack, http-push) is refused; use git push.")
            if sub == "push":
                if redirected:
                    raise PushBlock("push gate: a push with a redirected git dir or config (GIT_DIR, --git-dir, "
                                    "--work-tree, GIT_CONFIG_*, HOME, --exec-path) cannot be range-checked. "
                                    "Blocked; cd into the repo.")
                run_time_args(toks[j + 1:])
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


def all_pushes(cmd: str, cwd: str) -> list[dict]:
    """Every push the command runs, after unwrapping; blocks what cannot be read."""
    cmd = without_message_heredocs(hl.join_lines(cmd))
    try:
        ex = hl.expand(cmd, cwd)
    except hl.Unparseable as exc:
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
        found += find_pushes(head, where or cwd)
        for reader, body in bodies:
            found += find_pushes(body, where or cwd, resolve=reader not in WRITERS)
    for body, path in ex.code:
        # Inline code only (python -c, node -e). A source file an interpreter runs is not read
        # for pushes: release tooling pushes by design (stated limit, references/hooks.md).
        if not path and CODE_PUSH.search(body):
            raise PushBlock("push gate: a push run from inline code cannot be range-checked. Blocked; "
                            "run it as a plain `git push` line.")
    detected = detect_count(inert_writer_bodies(cmd))
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
        out.append({"remote": remote, "dst": short_dst, "sha": sha, "count": count, "log": log, "note": note})
    return out


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
        return {"rows": view + [("status", "nothing new to push")], "items": items, "partial": []}
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
            refuse(f"no local CI pass for {r['sha'][:12]}. Run the repo's CI steps through ci_stamp.py, one "
                   "--step each (or one command after --), with no `bash -c` wrapper: on Windows it can start "
                   "WSL instead of Git Bash. Then push.",
                   f'python "{os.path.join(HERE, "ci_stamp.py")}" run --repo "{repo}" --step "<step 1>" '
                   '--step "<step 2>"', "push_gate.no_ci")
    # A stamp that left a CI check out is partial: say so loudly (observation 0354).
    return {"rows": view, "items": items, "partial": list(stamp.get("excluded") or [])}


def hook_main() -> None:
    ev, raw = hl.read_event()
    if hl.stood_down("W2"):
        sys.exit(0)
    cmd = hl.command_of(ev) if ev else ""
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
        try:
            pushes = all_pushes(cmd, ev.get("cwd") or os.getcwd())
        except PushBlock as exc:
            # Hard (K7-4-01): a push the gate cannot read may be a force or delete push in disguise.
            hl.block(str(exc), rule=exc.rule, hard=True)
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
        hl.allow(context=msg, message=msg if loud else "")
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "intend":
        sys.exit(intend_main(sys.argv[2:]))
    hook_main()
