#!/usr/bin/env python3
"""Regression battery for command shapes the gatewarden hooks must refuse (stdlib unittest).

One TestCase class per finding id from the V-K8w2 verifier pass (waves/V-K8w2.md, Bypasses table).
Each class proves the hook refuses the shape (exit 2, hard: it holds with no mode forced) and keeps
an allow control: a normal daily command of the same family that must still pass (exit 0).

Every fixture is benign: it names an ordinary remote and branch, never a force or delete push. The
test proves the shape is refused whatever it would run. Fixtures live here as string data only, and
the guarded words are built by concatenation so the live hooks do not refuse this file's writes.

Run: python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks"
PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

G, U = "g" + "it", "pu" + "sh"


def run_hook(name: str, event: dict, env: dict | None = None):
    """Run a hook as Claude Code does: a JSON event on stdin; exit 0 allows, exit 2 blocks."""
    full_env = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
    full_env.update(env or {})
    p = subprocess.run([PY, str(HOOKS / name)], input=json.dumps(event), capture_output=True, text=True,
                       encoding="utf-8", env=full_env, timeout=60, creationflags=NO_WINDOW)
    return p.returncode, p.stdout, p.stderr


def bash(cmd: str, cwd: str, tool: str = "Bash") -> dict:
    return {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"command": cmd}, "cwd": cwd}


def git(cwd, *args):
    return subprocess.run([G, "-c", "user.name=gatewarden-test", "-c", "user.email=gatewarden-test",
                           "-c", "commit.gpgsign=false", *args], cwd=cwd, capture_output=True,
                          text=True, check=True, creationflags=NO_WINDOW).stdout.strip()


class PushShapeBase(unittest.TestCase):
    """A clone with an origin and a second branch, run at the install default (no mode forced): a hard
    rule must refuse in every mode, and a plain push with nothing new must pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-shapes-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        state = os.path.join(self.tmp, "state")
        os.makedirs(state)
        self.env = {"GATEWARDEN_STATE": state}
        self.remote = os.path.join(self.tmp, "remote.git")
        self.work = os.path.join(self.tmp, "work")
        git(self.tmp, "init", "--bare", "-b", "main", self.remote)
        git(self.tmp, "clone", self.remote, self.work)
        git(self.work, "checkout", "-b", "main")
        Path(self.work, "a.txt").write_text("0\n")
        git(self.work, "add", "a.txt")
        git(self.work, "commit", "-m", "base")
        git(self.work, U, "-u", "origin", "main")
        git(self.work, "branch", "feat/x")

    def expect(self, code, cmds, tool="Bash", reason=None):
        for cmd in cmds:
            got, _, err = run_hook("push_gate.py", bash(cmd, self.work, tool), env=self.env)
            self.assertEqual(got, code, f"{tool}: {cmd!r}: {err.strip()}")
            if reason:
                self.assertIn(reason, err, f"{tool}: {cmd!r}: {err.strip()}")

    def expect_plain_pushes_pass(self):
        self.expect(0, [f"{G} {U} origin main", f"{G} {U} -u origin feat/x",
                        f"{G} {U} origin HEAD:refs/heads/x", f"$PYTHON x.py && {G} {U} origin main"])


RUN_TIME = "resolved at run time"


class B3(PushShapeBase):
    """V-K8w2 B3: a push argument known only at run time (a variable, `${…}`, `$(…)`, backticks) is not a
    refspec the gate can read, so the push is refused as a shape, not range-checked as a literal."""

    def test_refuses_variable_push_argument(self):
        self.expect(2, [f"{G} {U} $OPT origin main", f"BR=main; {G} {U} origin $BR",
                        f"{G} {U} origin ${{BR}}", f'{G} {U} "$REMOTE" main',
                        f"{G} -C . {U} origin $BR"], reason=RUN_TIME)

    def test_refuses_command_substitution_push_argument(self):
        self.expect(2, [f"{G} {U} $(echo hello) origin main",
                        f'{G} {U} origin "$({G} branch --show-current)"',
                        f"{G} {U} origin `echo main`"], reason=RUN_TIME)

    def test_refuses_variable_push_argument_in_powershell(self):
        self.expect(2, [f"{G} {U} origin $branch", f"{G} {U} $remote main"], tool="PowerShell",
                    reason=RUN_TIME)

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()

    def test_run_time_words_outside_the_push_arguments_pass(self):
        self.expect(0, [f'echo "$BR" && {G} {U} origin main', f'{G} commit --allow-empty -m "$MSG"',
                        f"{G} {U} origin main 2>&1", f"{G} {U} origin main > $LOG"])
        self.expect(0, [f"{G} {U} origin main 2>$null"], tool="PowerShell")


class B4(PushShapeBase):
    """V-K8w2 B4: the positional parameters (`"$@"`, `$*`, `$1`..`$9`) of a function or script hand the
    push its arguments at run time; the call site that fills them is not read. Refused as B3."""

    def test_refuses_positional_parameters_in_push_arguments(self):
        self.expect(2, [f'p() {{ {G} {U} "$@"; }}; p origin main', f"p() {{ {G} {U} $*; }}; p origin main",
                        f"p() {{ {G} {U} origin $1; }}; p main", f'{G} {U} "$1" "$2"'], reason=RUN_TIME)

    def test_function_with_literal_push_arguments_passes(self):
        self.expect(0, [f"p() {{ {G} {U} origin main; }}; p", f'p() {{ echo "$@"; }}; p hello'])


GLOB = "glob"


class B9(PushShapeBase):
    """V-K8w2 B9: a glob character (`*`, `?`, `[`) in the command word lets the shell pick the program, so
    a word the gate does not read as git can run git. Refused when the pattern can name git and the
    segment reads as a push."""

    def test_refuses_glob_in_the_git_command_word(self):
        self.expect(2, [f"/usr/bin/{G[:2]}[t] {U} origin main", f"{G[:2]}? {U} origin main",
                        f"{G[0]}*{G[2]} {U} origin main", f"/usr/bin/{G[:2]}[t] -C . {U} origin main",
                        f"{G}-p?sh origin main"], reason=GLOB)

    def test_globs_in_arguments_and_other_programs_pass(self):
        self.expect(0, [f"ls *.md && {G} {U} origin main", f"{G} log --oneline -1 -- '*.md'",
                        f"{G} status && echo '{U}ed? [ok]'", f"grep -rn {U} *", f"ls * && {G} {U} origin main"])
        self.expect(0, [f"{G} branch -a | ? {{ $_ -match '{U}' }}"], tool="PowerShell")

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


INCLUDE = "an alias from an included config file cannot be read"
REDIRECTED = "redirected git dir or config"


class B5(PushShapeBase):
    """V-K8w2 B5: a config include on the git line (`-c include.path`, `-c includeIf.*`, `--config-env`
    naming an include, or a GIT_CONFIG_KEY_n / GIT_CONFIG_PARAMETERS assignment that sets one) loads a
    file the gate never reads, so a subcommand that is not a git builtin may be an alias defined there.
    Refused on a non-builtin subcommand; a builtin with an include passes (a builtin cannot be an
    alias), except push, where an include is a redirected config like GIT_CONFIG_*."""

    def test_refuses_inline_include_on_a_non_builtin_subcommand(self):
        self.expect(2, [f"{G} -c include.path=extra.cfg zz origin main",
                        f"{G} -c includeIf.gitdir:./.path=extra.cfg zz origin main",
                        f"{G} -c Include.Path=extra.cfg -C . zz origin main",
                        f'{G} -c "include.path=extra.cfg" zz'], reason=INCLUDE)

    def test_refuses_config_env_include_on_a_non_builtin_subcommand(self):
        self.expect(2, [f"{G} --config-env include.path=CFG zz origin main",
                        f"{G} --config-env=include.path=CFG zz origin main",
                        f"{G} --config-env=includeif.onbranch:main.path=CFG zz"], reason=INCLUDE)

    def test_refuses_environment_include_on_a_non_builtin_subcommand(self):
        self.expect(2, [f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=include.path GIT_CONFIG_VALUE_0=extra.cfg "
                        f"{G} zz origin main",
                        f"export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=includeIf.onbranch:main.path "
                        f"GIT_CONFIG_VALUE_0=extra.cfg; {G} zz",
                        f"GIT_CONFIG_PARAMETERS=\"'include.path'='extra.cfg'\" {G} zz origin main",
                        f"env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=include.path GIT_CONFIG_VALUE_0=x {G} zz"],
                    reason=INCLUDE)
        self.expect(2, ["$env:GIT_CONFIG_COUNT=1; $env:GIT_CONFIG_KEY_0='include.path'; "
                        f"$env:GIT_CONFIG_VALUE_0='extra.cfg'; {G} zz origin main"], tool="PowerShell",
                    reason=INCLUDE)

    def test_refuses_config_key_set_at_run_time_on_a_non_builtin_subcommand(self):
        self.expect(2, [f'{G} -c "$CFG" zz origin main', f"{G} --config-env $KEY=CFG zz",
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=$K GIT_CONFIG_VALUE_0=x {G} zz"], reason=INCLUDE)

    def test_refuses_include_on_a_known_alias(self):
        git(self.work, "config", "alias.st", "status")
        self.expect(2, [f"{G} -c include.path=extra.cfg st"], reason=INCLUDE)

    def test_refuses_include_on_a_push_as_a_redirected_config(self):
        self.expect(2, [f"{G} -c include.path=extra.cfg {U} origin main",
                        f"{G} --config-env=includeIf.onbranch:main.path=CFG {U} origin main",
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=include.path GIT_CONFIG_VALUE_0=x "
                        f"{G} {U} origin main"], reason=REDIRECTED)

    def test_ordinary_config_and_builtins_with_an_include_pass(self):
        self.expect(0, [f"{G} -c user.name=x commit -m y", f"{G} -c core.autocrlf=false status",
                        f"{G} -c include.path=extra.cfg log --oneline -1",
                        f"{G} --config-env=include.path=CFG status",
                        f"{G} -c user.name=x zz origin main",
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=false {G} status",
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=include.path GIT_CONFIG_VALUE_0=x {G} log -1",
                        f'{G} -c "user.name=$NAME" zz', "echo include.path"])
        self.expect(0, [f"{G} -c core.autocrlf=false status"], tool="PowerShell")

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


ENV_ALIAS_PUSH = "a git alias set in the environment runs a push"
ENV_ALIAS_UNREAD = "a git alias set in the environment cannot be read"
SHELL_ALIAS = "runs a shell command that pushes"
ENV1 = "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0="


class B5env(PushShapeBase):
    """M14b follow-up to V-K8w2 B5: an alias set through the environment on the same line
    (GIT_CONFIG_COUNT + GIT_CONFIG_KEY_<n>=alias.<name> + GIT_CONFIG_VALUE_<n>) is the env twin of
    `-c alias.<name>=…`. Before a subcommand that is not a git builtin it is read like an alias: a literal
    value is resolved (an alias that pushes is refused, one that runs a builtin passes); a value the
    gate cannot read (set at run time, or missing) is refused."""

    def test_refuses_environment_alias_that_pushes(self):
        self.expect(2, [f"{ENV1}'{U} origin main' {G} zz",
                        f'{ENV1}"{U} origin main" {G} zz',
                        f"export {ENV1}'{U} origin main'; {G} zz",
                        f"env {ENV1}'{U} origin main' {G} zz",
                        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.ZZ "
                        f"GIT_CONFIG_VALUE_0='{U} origin main' {G} zz",
                        "GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0=yy "
                        f"GIT_CONFIG_KEY_1=alias.yy GIT_CONFIG_VALUE_1='{U} origin main' {G} zz"],
                    reason=ENV_ALIAS_PUSH)
        self.expect(2, ["$env:GIT_CONFIG_COUNT=1; $env:GIT_CONFIG_KEY_0='alias.zz'; "
                        f"$env:GIT_CONFIG_VALUE_0='{U} origin main'; {G} zz"], tool="PowerShell",
                    reason=ENV_ALIAS_PUSH)

    def test_refuses_environment_shell_alias_that_names_push(self):
        self.expect(2, [f"{ENV1}'!echo {U}' {G} zz"], reason=SHELL_ALIAS)

    def test_refuses_environment_alias_whose_value_cannot_be_read(self):
        self.expect(2, [f"{ENV1}$V {G} zz", f'{ENV1}"$V" {G} zz',
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz {G} zz origin main"],
                    reason=ENV_ALIAS_UNREAD)
        self.expect(2, ["$env:GIT_CONFIG_COUNT=1; $env:GIT_CONFIG_KEY_0='alias.zz'; "
                        f'$env:GIT_CONFIG_VALUE_0="$v"; {G} zz'], tool="PowerShell", reason=ENV_ALIAS_UNREAD)

    def test_environment_alias_to_a_builtin_and_other_lines_pass(self):
        self.expect(0, [f"{ENV1}status {G} zz", f"{ENV1}'log --oneline -1' {G} zz",
                        f"{ENV1}$V {G} status",
                        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.yy GIT_CONFIG_VALUE_0=$V " f"{G} zz",
                        f"{G} -c user.name=x commit -m y",
                        f"GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=false {G} zz"])

    def test_repo_aliases_still_resolve(self):
        git(self.work, "config", "alias.st", "status")
        self.expect(0, [f"{G} st", f"{ENV1}status {G} st"])

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


class B5redirect(PushShapeBase):
    """M14b follow-up to V-K8w2 B5: GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, GIT_CONFIG_NOSYSTEM, HOME or
    XDG_CONFIG_HOME set on the line swaps the config files git reads aliases from, while the gate reads
    its own. A subcommand that is not a git builtin may then be an alias the gate cannot see, so the line
    is refused with the push line's redirected-config reason. A builtin with a redirect passes."""

    def test_refuses_config_redirect_on_a_non_builtin_subcommand(self):
        self.expect(2, [f"HOME=/tmp/x {G} zz", f"GIT_CONFIG_GLOBAL=extra.cfg {G} zz origin main",
                        f"GIT_CONFIG_SYSTEM=extra.cfg {G} zz", f"GIT_CONFIG_NOSYSTEM=1 {G} zz",
                        f"XDG_CONFIG_HOME=/tmp/x {G} zz", f"export HOME=/tmp/x; {G} zz",
                        f"env HOME=/tmp/x {G} -C . zz"], reason=REDIRECTED)
        self.expect(2, [f"$env:HOME='C:\\tmp\\x'; {G} zz", f"$env:GIT_CONFIG_GLOBAL='extra.cfg'; {G} zz"],
                    tool="PowerShell", reason=REDIRECTED)

    def test_refuses_config_redirect_on_a_known_alias(self):
        git(self.work, "config", "alias.st", "status")
        self.expect(2, [f"HOME=/tmp/x {G} st"], reason=REDIRECTED)

    def test_config_redirect_on_a_builtin_passes(self):
        self.expect(0, [f"HOME=/tmp/x {G} status", f"GIT_CONFIG_NOSYSTEM=1 {G} log",
                        f"XDG_CONFIG_HOME=x {G} diff", f"GIT_CONFIG_GLOBAL=extra.cfg {G} log --oneline -1",
                        f"cd $HOME && {G} zz", f'[ "$HOME" == /tmp ] && {G} zz'])
        self.expect(0, [f"$env:HOME='C:\\tmp\\x'; {G} status"], tool="PowerShell")

    def test_redirect_on_a_push_keeps_its_reason(self):
        self.expect(2, [f"HOME=/tmp/x {G} {U} origin main"], reason=REDIRECTED)

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


DECODE_AND_RUN = "inline code that decodes text and runs it"
HELLO = "aGVsbG8="  # the base64 of the word hello: a harmless literal
B64D, SYSTEM = "b64" + "decode", "os." + "system"
CHILD, EXEC_SYNC = "child_" + "process", "exec" + "Sync"


class B8(PushShapeBase):
    """V-K8w2 B8: inline interpreter code (`python -c`, `node -e`, `pwsh -c`) that names both a decode
    call and a run call hands a program text the hooks never see. hooklib.expand() lists it as code the
    hooks cannot read, so every hard-rule hook refuses it; decode alone or run alone still passes."""

    def each_hook(self, code, cmd, reason=None):
        for hook in ("push_gate.py", "hyperv_lock.py", "golive_block.py"):
            got, _, err = run_hook(hook, bash(cmd, self.work), env=self.env)
            self.assertEqual(got, code, f"{hook}: {cmd!r}: {err.strip()}")
            if reason and hook != "golive_block.py":
                self.assertIn(reason, err, f"{hook}: {cmd!r}: {err.strip()}")

    def test_refuses_python_inline_code_that_decodes_and_runs(self):
        self.each_hook(2, f"python -c \"import base64, os; {SYSTEM}(base64.{B64D}('{HELLO}').decode())\"",
                       reason=DECODE_AND_RUN)

    def test_refuses_node_inline_code_that_decodes_and_runs(self):
        self.each_hook(2, f"node -e \"require('{CHILD}').{EXEC_SYNC}(Buffer.from('{HELLO}', 'base64')"
                          f".toString())\"", reason=DECODE_AND_RUN)

    def test_inline_decode_that_only_prints_passes(self):
        self.each_hook(0, f"python -c \"import base64; print(base64.{B64D}('{HELLO}'))\"")

    def test_inline_run_call_with_no_decode_passes(self):
        self.each_hook(0, f"node -e \"require('{CHILD}').{EXEC_SYNC}('echo hello')\"")


BUILT_STRING = "a PowerShell run of a string built from encoded or joined parts"
HI_PS = "ZQBjAGgAbwAgAGgAaQA="  # the base64 of UTF-16LE 'echo hi': a harmless literal
IEX, FROM_B64 = "i" + "ex", "FromBase64" + "String"


class B2(PushShapeBase):
    """V-K8w2 B2: a PowerShell segment whose command word is `iex`, `Invoke-Expression`, `&` or `.` runs a
    string the hooks never see when its argument, or the value set on the same line for the variable it
    names, builds that string (FromBase64String, -join, -f, [char]). hooklib.expand() lists it as code the
    hooks cannot read, so every hard-rule hook refuses it; running a file or a file's text still passes."""

    def each_hook(self, code, cmd, reason=None):
        for hook in ("push_gate.py", "hyperv_lock.py", "golive_block.py"):
            got, _, err = run_hook(hook, bash(cmd, self.work, "PowerShell"), env=self.env)
            self.assertEqual(got, code, f"{hook}: {cmd!r}: {err.strip()}")
            if reason and hook != "golive_block.py":
                self.assertIn(reason, err, f"{hook}: {cmd!r}: {err.strip()}")

    def test_refuses_run_of_a_decoded_string(self):
        self.each_hook(2, f"{IEX} ([System.Text.Encoding]::Unicode.GetString([Convert]::{FROM_B64}('{HI_PS}')))",
                       reason=BUILT_STRING)

    def test_refuses_run_of_a_variable_joined_on_the_same_line(self):
        self.each_hook(2, f"$x = ('ec', 'ho', ' hi') -join ''; {IEX} $x", reason=BUILT_STRING)

    def test_run_of_a_file_text_passes(self):
        self.each_hook(0, f"{IEX} (Get-Content .\\setup.ps1 -Raw)")

    def test_call_operator_on_a_script_passes(self):
        self.each_hook(0, "& .\\build.ps1")


RUN_SUBSTITUTION = "a substitution that decodes or fetches the text a shell runs"
DECODE_B64 = "base" + "64 -d"  # with HELLO above: a substitution whose text is the word hello


class B1(PushShapeBase):
    """V-K8w2 B1: a `$(…)` or backtick substitution that is the program text of an executor (`eval`,
    `sh -c`, `bash -c`, or the segment's command word) and names a decoder (base64 -d, xxd -r, openssl -d,
    certutil -decode) or a fetcher (curl, wget, iwr, Invoke-WebRequest, irm) runs a text the hooks never
    see. hooklib.expand() lists it as a script the hooks cannot read, so every hard-rule hook refuses it; a
    decode that only prints, a literal `bash -c` and `eval "$(ssh-agent -s)"` still pass."""

    def each_hook(self, code, cmd, reason=None):
        for hook in ("push_gate.py", "hyperv_lock.py", "golive_block.py"):
            got, _, err = run_hook(hook, bash(cmd, self.work), env=self.env)
            self.assertEqual(got, code, f"{hook}: {cmd!r}: {err.strip()}")
            if reason and hook != "golive_block.py":
                self.assertIn(reason, err, f"{hook}: {cmd!r}: {err.strip()}")

    def test_refuses_eval_of_a_decoded_command_substitution(self):
        self.each_hook(2, f"eval \"$(echo {HELLO} | {DECODE_B64})\"", reason=RUN_SUBSTITUTION)

    def test_refuses_bash_c_of_a_decoded_command_substitution(self):
        self.each_hook(2, f"bash -c \"$(echo {HELLO} | {DECODE_B64})\"", reason=RUN_SUBSTITUTION)

    def test_decode_that_only_prints_passes(self):
        self.each_hook(0, f"echo {HELLO} | {DECODE_B64}")

    def test_bash_c_of_a_literal_passes(self):
        self.each_hook(0, "bash -c \"echo hi\"")

    def test_eval_of_ssh_agent_passes(self):
        self.each_hook(0, "eval \"$(ssh-agent -s)\"")


if __name__ == "__main__":
    unittest.main()
