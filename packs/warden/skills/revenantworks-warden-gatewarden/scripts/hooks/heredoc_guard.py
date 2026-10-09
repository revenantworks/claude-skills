#!/usr/bin/env python3
"""heredoc_guard.py: PreToolUse hook (matcher Bash|PowerShell) that refuses Python code with
backslash escapes written through a shell heredoc, and Python left waiting on standard input.

A heredoc passes through the shell before Python sees it; an unquoted delimiter
collapses `\\\\` and a mixed quoting habit loses escapes, so a regex such as
`\\bword\\b` can land as something that matches nothing, silently. The Write tool
writes bytes exactly. This hook blocks a heredoc whose target is Python
(`python`, `python3`, `py`, or `cat > *.py`) when its body holds a backslash
escape outside a raw string literal, and says to use the Write tool (rule `heredoc_guard`, soft).

It also refuses Python told to read its program from standard input (rule `heredoc_guard.stdin`,
hard): a dash, `/dev/stdin`, `/dev/fd/0` or `/proc/self/fd/0` where the script name goes, for any
Python name (python, python3.12t, python2, pythonw, pypy3, py, a full Windows path), with a heredoc
or without one, also inside `sh -c`, `bash -c`, `eval`, `pwsh -Command` strings and after a line
continuation or `${IFS}`. A Python REPL started with no script, `-c` or `-m` (bare `python`,
`python -u`, `python -i`), at the start of a command, is the same hang unless a pipe, a `<` file or a
`<<<` here-string feeds it; so are `ipython`, `python -m code` and `winpty python` (V-K8w2 B10). The
same rule covers bare `node`, `node -`, `node -i`, a bare `sh`/`bash`/`zsh`, `bash -s`, `bash -i` and
`pwsh -Command -` at the start of a command, unless a pipe, a `<` file, a `<<<` here-string or a
heredoc feeds them. `--version`, `-h` and `py --list` pass. An empty or missing heredoc leaves
the call waiting on stdin until it times out; briefs forbade it in prose and it still recurred
(observation 0352), so the barrier is here. Heredoc bodies and quoted strings are not read for the
token: a commit message may name it.

Fail mode: the heredoc rule fails open (an unreadable event allows it). The stdin rule fails closed:
an event that cannot be read, a command over 256 KB, a crash or a check past its time budget is
matched as raw text, and a hit is refused (V-K8w F8, F9).
"""
from __future__ import annotations

import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

HEREDOC = re.compile(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1")
PY_TARGET = re.compile(r"(?i)(?:^|[\s;&|(])(?:[\w./\\-]*[/\\])?(?:python3?|py)(?:\.exe)?(?:\s|$)|>\s*\S+\.py\b")
RAW_STR = re.compile(r"[rR][bB]?(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')"
                     r"|[bB][rR](\"[^\"\n]*\"|'[^'\n]*')")
ESCAPE = re.compile(r"\\[abfnrtv0xuUNdDsSwWbB\\'\"]")


def offending(cmd: str) -> bool:
    for m in HEREDOC.finditer(cmd):
        head = cmd[:m.start()].splitlines()[-1] if cmd[:m.start()].splitlines() else ""
        line_end = cmd.find("\n", m.end())
        head += cmd[m.end():line_end if line_end != -1 else len(cmd)]
        if not PY_TARGET.search(head):
            continue
        rest = cmd[line_end + 1:] if line_end != -1 else ""
        end = re.search(rf"(?m)^\s*{re.escape(m.group(2))}\s*$", rest)
        body = rest[:end.start()] if end else rest
        if ESCAPE.search(RAW_STR.sub("", body)):
            return True
    return False


# Every Python a shell can start by name: python, python3, python3.12, python3.13t (free-threaded),
# python2, pythonw, pypy, pypy3.10, the py launcher; .exe or not (V-K8w F7).
PY_NAME = re.compile(r"(?i)^(?:i?python(?:\d+(?:\.\d+)*t?)?w?|pypy(?:\d+(?:\.\d+)*)?|py)(?:\.exe)?$")
REPL_MODULES = {"code", "asyncio", "IPython"}  # `python -m code` with nothing after it is a REPL (V-K8w2 B10)
# V-K8w2 B10: other programs that sit waiting on stdin when nothing feeds them.
NODE_NAME = re.compile(r"(?i)^node(?:js)?(?:\.exe)?$")
SH_NAME = re.compile(r"(?i)^(?:sh|bash|zsh|dash|ksh|ash)(?:\.exe)?$")
PWSH_NAME = re.compile(r"(?i)^(?:pwsh|powershell)(?:\.exe)?$")
NODE_DONE = {"-e", "--eval", "-p", "--print", "-v", "--version", "-h", "--help", "--test", "--run", "-c", "--check",
             "--v8-options"}
NODE_VALUE = {"-r", "--require", "--import", "--loader", "--experimental-loader", "--env-file", "--conditions", "-C",
              "--title", "--input-type", "--inspect-port"}
SH_VALUE = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
PWSH_VALUE = {"-executionpolicy", "-ep", "-ex", "-workingdirectory", "-wd", "-outputformat", "-of", "-o",
              "-inputformat", "-if", "-in", "-windowstyle", "-w", "-win", "-configurationname", "-config",
              "-settingsfile", "-settings", "-custompipename"}
OTHER_TAIL = " (nothing feeds its input)"
STDIN_ARGS = {"-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"}
OPT_WITH_VALUE = {"-W", "-X", "-Q"}
INFO_FLAGS = {"-V", "-VV", "--version", "-h", "-?", "--help", "--help-env", "--help-xoptions", "--help-all",
              "-0", "-0p", "--list", "--list-paths"}
OPERATORS = set("();<>|&\n")
LAUNCH = {"time", "nohup", "exec", "env", "sudo", "doas", "nice", "&", "call", "timeout", "!", "winpty"}
RUNNERS = {"uv", "poetry", "pipenv", "pdm", "hatch", "rye", "conda"}  # `<runner> run python`
WRAPPERS = hl.SHELLS | {"eval", "iex", "invoke-expression", "su", "sudo", "doas", "ssh", "watch", "script",
                        "flock", "runuser", "xargs", "nohup", "timeout", "start-process", "saps", "env"}
ANSI_C = re.compile(r"\$(['\"])((?:\\.|(?!\1).)*)\1")
# The stdin shape as raw text, for an event the parser does not read (bad JSON, over 256 KB, a crash).
RAW_STDIN = re.compile(r"(?i)(?:^|[\s;&|(`\"'=])(?:[^\s;&|()]*[\\/])?(?:python[\d.]*t?w?|pypy[\d.]*|py)(?:\.exe)?"
                       r"['\"]?(?:\s+-[^\s;&|]*)*?\s+['\"$]*(?:-|/dev/stdin|/dev/fd/0|/proc/self/fd/0)['\"]*"
                       r"(?=$|[\s;&|)'\"`])")


def raw_reads_stdin(text: str) -> bool:
    return bool(RAW_STDIN.search(hl.IFS.sub(" ", hl.join_lines(text or "", ps=True))))


def _without_heredoc_bodies(cmd: str) -> str:
    """The command with every heredoc body (and its end line) removed; head lines stay."""
    out, pending = [], []
    for line in cmd.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending = [m.group(2) for m in HEREDOC.finditer(line)]
    return "\n".join(out)


def _shell_tokens(text: str) -> list[str]:
    """Words outside quotes, with shell operators as their own tokens. A quoted string is one
    word (its quotes removed), so `echo "python -"` never reads as a python call."""
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:  # an unbalanced quote: drop quoted spans, split the rest
        rough = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", " _q_ ", text)
        return re.sub(r"([();<>|&\n])", r" \1 ", rough).split()


def _command_start(toks: list[str], i: int) -> bool:
    """True when toks[i] is the program a simple command runs (past assignments and launchers)."""
    k = i - 1
    while k >= 0 and not set(toks[k]) <= OPERATORS:
        k -= 1
    k += 1
    while k < i:
        t = toks[k]
        if re.match(r"^[A-Za-z_]\w*=", t) or t.lower() in LAUNCH or t.startswith("-") or re.fullmatch(r"\d+[smhd]?", t):
            k += 1
        elif t.lower() in RUNNERS and k + 1 < i and toks[k + 1].lower() == "run":
            k += 2
        else:
            return False
    return True


def _fed(toks: list[str], i: int, j: int) -> bool:
    """True when something feeds the call's stdin: a pipe before it, a `<` file or `<<<` after it."""
    k = i - 1
    while k >= 0 and not set(toks[k]) <= OPERATORS:
        k -= 1
    if k >= 0 and toks[k] in ("|", "|&"):
        return True
    while j < len(toks) and toks[j] not in (";", "|", "||", "&&", "&", "\n", "(", ")"):
        if toks[j] in ("<", "<<<"):
            return True
        j += 1
    return False


def _check_tokens(toks: list[str]) -> str:
    for i, tok in enumerate(toks):
        name = re.split(r"[\\/]", tok)[-1]
        runtime = tok.startswith("$") and "py" in tok.lower()  # $PY -, ${PYTHON} -
        if not (PY_NAME.match(name) or runtime):
            continue
        j, script, info, interactive = i + 1, False, False, False
        while j < len(toks) and not set(toks[j]) <= OPERATORS:
            a = toks[j]
            if a in STDIN_ARGS:
                return f"{name} {a}"
            if a == "--":
                if j + 1 < len(toks) and toks[j + 1] in STDIN_ARGS:
                    return f"{name} -- {toks[j + 1]}"
                script = j + 1 < len(toks) and not set(toks[j + 1]) <= OPERATORS
                break
            if a == "-m" and j + 1 < len(toks) and toks[j + 1] in REPL_MODULES and \
                    (j + 2 >= len(toks) or set(toks[j + 2]) <= OPERATORS):
                interactive = True
                break
            if a in ("-c", "-m") or not a.startswith("-"):
                script = True
                break
            if a in INFO_FLAGS:
                info = True
            if not a.startswith("--") and a[1:2] not in ("W", "X", "Q") and "i" in a[1:]:
                interactive = True
            j += 2 if a in OPT_WITH_VALUE else 1
        if runtime or not _command_start(toks, i):
            continue
        if ((not script and not info) or interactive) and not _fed(toks, i, j):
            return f"{name} (an interactive Python with no script)"
    return ""


def _waits(toks: list[str], i: int, j: int, name: str) -> bool:
    """Scan one call's arguments toks[i+1:j]; True when node, a POSIX shell or PowerShell would sit
    reading stdin: no script and no inline code, a `-` script, `bash -s`, `-i`, `pwsh -Command -`."""
    args = toks[i + 1:j]
    if NODE_NAME.match(name):
        k, interactive = 0, False
        while k < len(args):
            a = args[k]
            if a == "-":
                return True
            if a in NODE_DONE or a.split("=", 1)[0] in NODE_DONE:
                return False
            if a in ("-i", "--interactive"):
                interactive = True
            elif a in NODE_VALUE:
                k += 1
            elif not a.startswith("-"):
                return interactive
            k += 1
        return True
    if SH_NAME.match(name):
        k, stdin = 0, False
        while k < len(args):
            a = args[k]
            if a in ("--version", "--help"):
                return False
            if a in SH_VALUE:
                k += 2
                continue
            if a in ("-", "--"):
                return stdin or k + 1 >= len(args)
            if a.startswith("-") and not a.startswith("--"):
                if "c" in a[1:]:
                    return False
                stdin = stdin or "s" in a[1:]  # `-i` with no script is caught at the end anyway
            elif not a.startswith("-"):
                return stdin
            k += 1
        return True
    if PWSH_NAME.match(name):
        k = 0
        while k < len(args):
            a = args[k]
            low = a.lower()
            n = low.lstrip("-/")
            if hl.is_encoded_flag(a) or low in ("-v", "-version", "-h", "-help", "-?", "/?"):
                return False
            if a[:1] in "-/" and n and ("command".startswith(n) or "file".startswith(n)):
                return k + 1 < len(args) and args[k + 1] == "-"
            if low in PWSH_VALUE:
                k += 2
                continue
            if not a.startswith(("-", "/")):
                return False
            k += 1
        return True
    return False


def _check_others(toks: list[str]) -> str:
    """V-K8w2 B10: node, sh/bash/zsh, pwsh at the start of a command, left reading stdin with nothing
    feeding it. A pipe, a `<` file, a `<<<` here-string or a heredoc feeds it."""
    for i, tok in enumerate(toks):
        name = re.split(r"[\\/]", tok)[-1]
        if not (NODE_NAME.match(name) or SH_NAME.match(name) or PWSH_NAME.match(name)):
            continue
        if not _command_start(toks, i):
            continue
        j = i + 1
        while j < len(toks) and not set(toks[j]) <= OPERATORS:
            j += 1
        if not _waits(toks, i, j, name) or _fed(toks, i, j):
            continue
        if any(t == "<<" for t in toks[j:next((m for m in range(j, len(toks)) if toks[m] in
                                                  (";", "|", "||", "&&", "&", "\n")), len(toks))]):
            continue  # a heredoc feeds it
        return " ".join([name] + toks[i + 1:j]) + OTHER_TAIL
    return ""


def _views(text: str) -> list[str]:
    """The text as the shell reads it: continuations joined, ${IFS} as a space, $'-' as '-', comments and
    heredoc bodies gone; plus the same with backslashes as slashes (C:\\Python313\\python.exe)."""
    t = hl.IFS.sub(" ", hl.join_lines(text))
    t = ANSI_C.sub(lambda m: "'" + m.group(2) + "'", t)
    t = _without_heredoc_bodies(hl.strip_comments(t))
    return [t, t.replace("\\", "/")] if "\\" in t else [t]


def _inner_texts(text: str, depth: int = 0) -> list[str]:
    """The text, and every string a shell wrapper on it runs (sh -c, bash -c, eval, pwsh -Command,
    an -EncodedCommand), recursively (V-K8w F6). A wrapper unwraps only its own command's strings."""
    out = [text]
    if depth >= hl.MAX_DEPTH:
        return out
    try:
        subs = hl.substitutions(text)
    except hl.Unparseable:
        subs = []
    for s in subs:
        out += _inner_texts(s, depth + 1)
    for seg in hl.segments(_without_heredoc_bodies(hl.strip_comments(hl.join_lines(text)))):
        toks = hl.tokens(seg)
        progs = [hl.prog(t) for t in toks]
        if not any(p in WRAPPERS for p in progs):
            continue
        for k, t in enumerate(toks):
            if len(t) > 2 and t[0] == t[-1] and t[0] in "'\"":
                out += _inner_texts(t[1:-1], depth + 1)
            elif hl.is_encoded_flag(t) and k + 1 < len(toks) and any(p in hl.PS for p in progs):
                try:
                    out += _inner_texts(hl.decode_ps(toks[k + 1]), depth + 1)
                except hl.Unparseable:
                    pass
    return out


def python_reads_stdin(cmd: str) -> str:
    """The offending call (`python -`), or "" when no Python call waits on stdin."""
    for text in _inner_texts(cmd):
        hl.check_budget()
        for view in _views(text):
            toks = _shell_tokens(view)
            slip = _check_tokens(toks) or _check_others(toks)
            if slip:
                return slip
    return ""


STDIN_REASON = ("heredoc guard: `{slip}` makes Python read its program from standard input; an empty "
                "or missing heredoc, or no input at all, leaves the call waiting until it times out. Write "
                "the script with the Write tool and run `python <file>`, or use `python -c`.")
OTHER_REASON = ("heredoc guard: `{slip}` starts a shell or REPL that reads standard input, and nothing feeds "
                "it; the call waits until it times out. Run a script file, pass the code inline (`-c`, `-e`, "
                "`-Command \"...\"`), or pipe the input in.")


def main() -> None:
    ev, raw = hl.read_event()
    if hl.stood_down("W1"):
        sys.exit(0)
    cmd = hl.command_of(ev) if ev else ""
    hl.start_budget("heredoc_guard.stdin", STDIN_REASON.format(slip="python -"),
                    lambda: raw_reads_stdin(cmd or raw))
    try:
        if ev is None:  # V-K8w F9: an unreadable event is matched as raw text for the hard rule
            if raw_reads_stdin(raw):
                hl.block(STDIN_REASON.format(slip="python -") + " (hook input could not be read)",
                         rule="heredoc_guard.stdin", hard=True)
            hl.allow()
        # The stdin rule covers both shell tools: `python -` hangs from PowerShell too (K7-4-11).
        if ev.get("tool_name") not in hl.SHELL_TOOLS:
            hl.allow()
        if len(cmd) > hl.BIG:  # V-K8w F8: a regex scan, never a word-by-word parse
            if raw_reads_stdin(cmd):
                hl.block(STDIN_REASON.format(slip="python -") + " (a command over 256 KB, read as raw text)",
                         rule="heredoc_guard.stdin", hard=True)
            hl.allow()
        slip = python_reads_stdin(cmd)
        if slip:
            reason = OTHER_REASON if slip.endswith(OTHER_TAIL) else STDIN_REASON
            hl.block(reason.format(slip=slip), rule="heredoc_guard.stdin", hard=True)
        if ev.get("tool_name") == "Bash" and offending(cmd):
            hl.block("heredoc guard: this heredoc feeds Python code that holds a backslash escape. The shell "
                     "can change it before Python reads it. Write the file with the Write tool, then run it.", rule="heredoc_guard")
        hl.allow()
    except SystemExit:
        raise
    except Exception:
        if raw_reads_stdin(cmd or raw):
            hl.block(STDIN_REASON.format(slip="python -") + " (the hook could not finish; blocked to be safe)",
                     rule="heredoc_guard.stdin", hard=True)
        hl.allow()


if __name__ == "__main__":
    main()
