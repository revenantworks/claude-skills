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
                          text=True, check=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL).stdout.strip()


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
                        f"cd $HOME && {G} status", f'[ "$HOME" == /tmp ] && {G} zz'])
        self.expect(0, [f"$env:HOME='C:\\tmp\\x'; {G} status"], tool="PowerShell")

    def test_non_builtin_in_a_folder_set_at_run_time_is_refused(self):
        # Owner ruling 2026-11-13: the alias table of a folder the gate cannot name is unreadable.
        git(self.work, "config", "alias.pp", "push")
        self.expect(2, [f"cd $HOME && {G} zz", f"mkdir x; d=x; cd $d && {G} pp origin main"])

    def test_redirect_on_a_push_keeps_its_reason(self):
        self.expect(2, [f"HOME=/tmp/x {G} {U} origin main"], reason=REDIRECTED)

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


class GW2(PushShapeBase):
    """FIX-GW2 (review of a60a0c8): a pushing alias set in ANOTHER repo (`alias.pp=push` there) reached a
    push because the gate read the aliases of the folder the hook started in, not the folder or git dir
    the git call really runs with. Each shape below runs `pp` in the other repo; each must be refused,
    and the same shape with a builtin must pass. The rule: resolve the alias where git really runs, and
    refuse a non-builtin subcommand where that folder or git dir cannot be known for sure."""

    PP = f"{G} pp origin main"

    def setUp(self):
        PushShapeBase.setUp(self)
        self.other = os.path.join(self.tmp, "other")
        git(self.tmp, "clone", self.remote, self.other)
        git(self.other, "config", "alias.pp", U)
        # A commit ahead of origin and guard mode, so every push the gate does see in `other` is refused
        # (no intent); the default nudge refuses only the first and would hide a second miss.
        git(self.other, "commit", "--allow-empty", "-m", "ahead")
        self.env["GATEWARDEN_MODE"] = "guard"

    def refused(self, *cmds, tool="Bash"):
        self.expect(2, list(cmds), tool=tool, reason="push gate")

    def test_01_subshell(self):
        self.refused(f"(cd ../other && {self.PP})", f"( cd ../other; {self.PP} )")

    def test_02_env_dash_c(self):
        self.refused(f"env -C ../other {self.PP}")

    def test_03_env_chdir(self):
        self.refused(f"env --chdir=../other {self.PP}", f"env --chdir ../other {self.PP}")

    def test_04_git_dir_option(self):
        self.refused(f"{G} --git-dir=../other/.git pp origin main", f"{G} --git-dir ../other/.git pp origin main",
                     f"{G} --work-tree=../other pp origin main")

    def test_05_git_dir_env(self):
        self.refused(f"GIT_DIR=../other/.git {self.PP}", f"GIT_WORK_TREE=../other {self.PP}",
                     f"GIT_COMMON_DIR=../other/.git {self.PP}")

    def test_06_redirection_after_cd(self):
        self.refused(f"cd ../other 2>/dev/null; {self.PP}", f"cd ../other >/dev/null 2>&1 && {self.PP}")

    def test_07_cd_in_a_loop(self):
        self.refused(f"for d in ../other; do cd $d; {self.PP}; done")

    def test_08_dash_c_without_a_space(self):
        self.refused(f"{G} -C../other pp origin main")

    def test_09a_cd_dash_p(self):
        self.refused(f"cd -P ../other && {self.PP}", f"cd -L ../other && {self.PP}")

    def test_09b_builtin_cd(self):
        self.refused(f"builtin cd ../other && {self.PP}", f"command cd ../other && {self.PP}")

    def test_10_git_in_inline_code(self):
        self.refused(f"python -c \"import os; os.chdir('../other'); os.system('{self.PP}')\"",
                     f"node -e \"require('child_process').execSync('{self.PP}', {{cwd: '../other'}})\"")

    def test_a_literal_cd_in_a_branch_checks_both_folders(self):
        # The cd may or may not run, so either folder's alias table applies.
        self.refused(f"if [ -d ../other ]; then cd ../other; fi; {self.PP}", f"cd ../other || true; {self.PP}")

    def test_a_subshell_scope_ends_at_its_paren(self):
        # The outer folder (work, no alias) applies after the subshell closes.
        self.expect(0, [f"(cd ../other && {G} status); {G} status"])
        self.refused(f"(cd .); cd ../other && {self.PP}")

    def test_builtins_still_pass_in_every_shape(self):
        st = f"{G} status"
        self.expect(0, [f"(cd ../other && {st})", f"env -C ../other {st}", f"env --chdir=../other {st}",
                        f"{G} --git-dir=../other/.git status", f"GIT_DIR=../other/.git {st}",
                        f"cd ../other 2>/dev/null; {st}", f"for d in ../other; do cd $d; {st}; done",
                        f"{G} -C../other status", f"cd -P ../other && {st}", f"builtin cd ../other && {st}",
                        f"python -c \"import os; os.chdir('../other'); os.system('{st}')\"",
                        f"if [ -d ../other ]; then cd ../other; fi; {st}",
                        f"{G} -C../other log --oneline -1", f"cd ../other && {G} commit --allow-empty -m x"])

    def test_aliases_in_the_folder_git_runs_in_still_resolve(self):
        # A harmless alias in the other repo passes when the gate reads that repo's table.
        git(self.other, "config", "alias.st", "status")
        self.expect(0, [f"cd -P ../other && {G} st", f"(cd ../other && {G} st)", f"env -C ../other {G} st",
                        f"{G} -C../other st", f"cd ../other 2>/dev/null; {G} st"])


class GW2Candidates(PushShapeBase):
    """FIX-GW2 fix round (adversarial review of 82941fe): stepping through folder changes missed pipes,
    `&`, a failed cd, nested shells, eval, find -execdir, Start-Process -WorkingDirectory, Bash running
    PowerShell's cd words, junctions and split names in inline code. The alias check is now
    order-independent: a non-builtin subcommand that is a pushing alias in ANY folder the line names is
    refused. Each shape reaches `pp` in `other`; the everyday lines below must still pass."""

    PP = GW2.PP
    refused = GW2.refused

    def setUp(self):
        GW2.setUp(self)  # the other repo with its pushing alias, guard mode
        os.makedirs(os.path.join(self.other, "sub"))
        link = os.path.join(self.work, "L")  # work/L -> other/sub: logical L/.. = work, physical = other
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", link, os.path.join(self.other, "sub")],
                           capture_output=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        else:
            os.symlink(os.path.join(self.other, "sub"), link)

    def test_r1_cd_piped_to_cat(self):
        self.refused(f"cd ../other; cd ../work | cat; {self.PP}", f"cd ../other; cd ../work | :; {self.PP}")

    def test_r2_cd_in_the_background(self):  # opened by 82941fe
        self.refused(f"cd ../other; cd ../work & {self.PP}")

    def test_r3_cd_that_fails_on_a_redirection(self):  # opened by 82941fe
        self.refused(f"cd ../other; cd ../work < /nonexistent/x; {self.PP}",
                     f"cd ../other; cd ../work 0</nonexistent; {self.PP}")

    def test_r4_sh_c_after_cd(self):
        self.refused(f"cd ../other && sh -c '{self.PP}'")

    def test_r5_bash_c_in_a_subshell(self):
        self.refused(f"(cd ../other && bash -c '{self.PP}')")

    def test_r6_env_chdir_then_sh_c(self):
        self.refused(f"env -C ../other sh -c '{self.PP}'")

    def test_r7_env_split_string(self):
        self.refused(f"env -C ../other -S '{self.PP}'")

    def test_r8_eval_cd(self):
        self.refused(f'eval "cd ../other"; {self.PP}')

    def test_r9_find_execdir(self):
        self.refused(f"find ../other/.git -maxdepth 0 -execdir {self.PP} \\;")

    def test_r10_start_process_working_directory(self):
        self.refused(f"Start-Process {G} -ArgumentList 'pp origin main' -WorkingDirectory ../other",
                     tool="PowerShell")

    def test_r11_powershell_cd_words_in_bash(self):
        self.refused(f"cd ../other; CD ../work; {self.PP}", f"cd ../other; sl ../work; {self.PP}",
                     f"cd ../other; chdir ../work; {self.PP}", f"cd ../other; set-location ../work; {self.PP}")

    def test_r12_junction_then_dotdot(self):
        self.refused(f"cd -P L/.. && {self.PP}", f"{G} -C L/.. pp origin main")

    def test_r13_split_program_name_in_inline_code(self):
        self.refused("python -c \"import subprocess; subprocess.run(['g'+'it','pp','origin','main'], "
                     "cwd='../other')\"")

    def test_r14_sudo_chdir(self):
        self.refused(f"sudo -D ../other {self.PP}")

    EVERYDAY = [
        "node -e \"const cp=require('child_process'); console.log('use git with care')\"",
        "python -c \"import subprocess; print(subprocess.run(['git','check-ref-format','refs/heads/x']).returncode)\"",
        "python -c \"import subprocess; subprocess.run(['git','prune'])\"",
        "python -c \"import subprocess,sys; sys.exit(subprocess.call(['git','diff','--quiet']))\"",
        "python -c \"import os; os.system('git verify-tag v1.0')\"",
        "node -e \"require('fs').writeFileSync('x.txt','git hub')\"",
        "python -c \"import subprocess; subprocess.run(['git', 'interpret-trailers', '--parse'])\"",
        f"{G} --git-dir=.git rerere status",
        f"GIT_DIR=.git {G} status; {G} flow init -d",
        f"export GIT_DIR=.git; {G} log",
        f"ROOT=$(cd .. && pwd); {G} flow feature start x",
        f"{G} -C. flow init -d",
        f"env -C . {G} flow init -d",
        f"cd . 2>/dev/null; {G} flow init -d",
        f"npm test && cd . && {G} flow init -d",
        f"cd /c/does/not/exist 2>/dev/null || true; {G} status",
        f"for f in a b; do cd .; {G} log -1; done",
        f"(cd . && {G} status) && {G} log -1",
        f"cd -P . && {G} log",
        "python -c \"import subprocess; subprocess.run(['git','fast-export','--all'])\"",
    ]
    EVERYDAY_PS = [f"Set-Location . ; {G} status", f"if (Test-Path x) {{ Set-Location x }}; {G} status",
                   f"Set-Location . ; {G} flow init -d"]
    # Round 4 (controller): a folder not there now is unreadable whatever else the line runs, so these
    # two everyday lines are refused again, as on a60a0c8; they name a missing folder (`sub`, `x`).
    MISSING_FOLDER = [f"(cd sub && {G} filter-repo --analyze)"]
    MISSING_FOLDER_PS = [f"if (Test-Path x) {{ Set-Location x }}; {G} flow init -d"]

    def test_everyday_lines_pass(self):
        # The review's everyday set; `print('git log, git status, git push are commands')` is left out:
        # it names push beside a process call and was refused before FIX-GW2 too.
        self.expect(0, self.EVERYDAY)
        self.expect(0, self.EVERYDAY_PS, tool="PowerShell")


class GW2Literal(PushShapeBase):
    """FIX-GW2 round 3 (re-review of 850eb3b): a folder word counts as a candidate only when it is a plain
    literal path that exists now. For a non-builtin subcommand the gate refuses a folder word that is
    missing (bare cd, cd -, pushd +N), holds a glob, brace, quote splice, POSIX backslash escape or `~`,
    names a drive or provider that is not a drive letter, or names a folder that does not exist yet on a
    line that may create it; and any line that changes how names resolve (CDPATH, OLDPWD, New-PSDrive,
    subst, net use, mklink, ln -s). Each shape reaches `pp` in `other` for real (review probe)."""

    PP = GW2.PP
    refused = GW2.refused

    def setUp(self):
        GW2.setUp(self)

    def test_s01_cdpath_exported(self):
        self.refused(f"export CDPATH=..; cd other && {self.PP}")

    def test_s02_cdpath_assigned(self):
        self.refused(f"CDPATH=.. ; cd other; {self.PP}")

    def test_s03_oldpwd_then_cd_dash(self):
        self.refused(f"OLDPWD=../other; cd -; {self.PP}")

    def test_s04_glob_star(self):
        self.refused(f"cd ../oth* && {self.PP}")

    def test_s05_glob_question_mark(self):
        self.refused(f"cd ../othe? && {self.PP}", f"cd ../{{other,x}} && {self.PP}")

    def test_s06_quote_splice(self):
        self.refused(f"cd ../ot''her && {self.PP}")

    def test_s07_backslash_escape(self):
        self.refused(f"cd ../ot\\her && {self.PP}")

    def test_s08_powershell_glob(self):
        self.refused(f"cd ..\\oth*; {self.PP}", tool="PowerShell")

    def test_s09_powershell_drive(self):
        self.refused(f"New-PSDrive -Name QQ -PSProvider FileSystem -Root ../other | Out-Null; Set-Location QQ:; "
                     f"{self.PP}", tool="PowerShell")

    def test_s10_folder_copied_by_python(self):
        self.refused(f"python -c \"import shutil; shutil.copytree('../other','../cpy')\" && cd ../cpy && {self.PP}")

    def test_s11_folder_copied_by_node(self):
        self.refused(f"node -e \"require('fs').cpSync('../other','../cpy2',{{recursive:true}})\" && "
                     f"{G} -C ../cpy2 pp origin main")

    def test_s12_subst_drive(self):
        self.refused(f"subst Q: ..\\other && cd /q && {self.PP}")

    def test_s13_cd_with_no_literal_folder(self):
        self.refused(f"cd; {self.PP}", f"cd ~; {self.PP}", f"cd -; {self.PP}", f"pushd +1; {self.PP}")

    def test_builtins_pass_beside_every_new_rule(self):
        st = f"{G} status"
        self.expect(0, [f"export CDPATH=..; cd other && {st}", f"cd ../oth* && {st}", f"cd -; {st}", f"cd; {st}",
                        f"cd ../ot''her && {st}", f"subst Q: ..\\other && cd /q && {st}"])

    def test_literal_existing_folders_still_resolve(self):
        git(self.other, "config", "alias.st", "status")
        self.expect(0, [f"cd ../other && {G} st", f"{G} -C ../other st", f"cd \"../other\" && {G} st"])

    def test_everyday_lines_still_pass(self):
        self.expect(0, GW2Candidates.EVERYDAY)
        self.expect(0, GW2Candidates.EVERYDAY_PS, tool="PowerShell")


class GW2ConfigWrites(PushShapeBase):
    """FIX-GW2 round 4 (re-review of dc7012d): a folder made on the same line (`git -C .. clone -c
    alias.pp=push`) carries a pushing alias the gate cannot read first, so any named folder that does not
    exist now refuses a non-builtin, whatever else the line runs. And a line that writes a git config
    (redirection, copy, `git config` write, an include) may add an alias before git reads it, so it
    refuses a non-builtin too."""

    PP = GW2.PP
    refused = GW2.refused

    def setUp(self):
        GW2.setUp(self)

    def test_c1_clone_with_alias_then_cd(self):
        self.refused(f"{G} -C .. clone -q -c alias.pp={U} work c3 && cd ../c3 && {self.PP}")

    def test_c2_clone_with_alias_then_dash_c(self):
        self.refused(f"{G} -C .. clone -q -c alias.pp={U} work c3; {G} -C ../c3 pp origin main")

    def test_c3_alias_appended_to_git_config(self):
        self.refused(f'echo "[alias] zz = {U}" >> .git/config; {G} zz origin main')

    def test_c4_config_copied_from_another_repo(self):
        self.refused(f"cp -r ../other/.git/config .git/config && {self.PP}")

    def test_c5_include_path_written(self):
        self.refused(f"{G} config include.path ../../other/.git/config && {self.PP}")

    def test_missing_folder_lines_are_refused_again(self):
        self.expect(2, GW2Candidates.MISSING_FOLDER)
        self.expect(2, GW2Candidates.MISSING_FOLDER_PS, tool="PowerShell")

    def test_config_reads_and_builtins_pass(self):
        self.expect(0, [f"{G} config user.name; {G} flow init -d", f"{G} config --get user.name && {G} flow init -d",
                        f"cat .git/config; {G} flow init -d", f"{G} config user.name x && {G} status",
                        f"echo x >> .git/config; {G} log -1"])


class GW3ConfigWrites(PushShapeBase):
    """FIX-GW3 (warden 1.1.5): matching a git config path by its text loses to a split string
    (`'.gi'+'t/config'`), a folder change (`cd .git && … >> config`) or a .NET call. The rule is now a
    class: before a non-builtin subcommand, a line that runs inline code able to write files or start
    processes, a .NET or COM write, a PowerShell file writer (any target), a shell body that writes, or
    any write whose target is named like a config or sits inside a .git folder is refused. Inline code
    that only prints, ordinary file writes and every builtin still pass."""

    X = f"{G} x origin main"
    ALIAS = f"[alias]\\n x = {U}\\n"
    refused = GW2.refused

    def setUp(self):
        PushShapeBase.setUp(self)
        self.env["GATEWARDEN_MODE"] = "guard"

    def test_g1_python_split_path_string(self):
        self.refused(f"python -c \"p='.git/'+'config'; open(p,'a').write('{self.ALIAS}')\"; {self.X}")

    def test_g2_node_split_path_string(self):
        self.refused(f"node -e \"require('fs').appendFileSync('.gi'+'t/config','{self.ALIAS}')\"; {self.X}")

    def test_g3_cd_into_git_folder_then_write(self):
        self.refused(f'cd .git && echo "[alias] x = {U}" >> config; cd ..; {self.X}')

    def test_g4_powershell_dotnet_append(self):
        self.refused(f"[IO.File]::AppendAllText('.git/config', \"[alias]`n x = {U}`n\"); {self.X}",
                     tool="PowerShell")

    def test_class_inline_code_that_writes_or_runs(self):
        self.refused(f"perl -e \"open(F,'>>','.gi'.'t/config'); print F 'x'\"; {self.X}",
                     f"ruby -e \"File.write('a', 'b')\"; {self.X}",
                     f"php -r \"file_put_contents('a', 'b');\"; {self.X}",
                     f"python -c \"import shutil; shutil.copy('a', 'b')\"; {self.X}",
                     f"python -c \"import subprocess; subprocess.run(['true'])\"; {self.X}",
                     f"python - <<'EOF'\nopen('a', 'w').write('b')\nEOF\n{self.X}",
                     f"pwsh -EncodedCommand ZQBjAGgAbwAgAHgAIAA+ACAAeQA=; {self.X}")  # echo x > y

    def test_class_git_call_inside_the_writing_code(self):
        self.refused("python -c \"import os,subprocess; os.chdir('.git'); open('conf'+'ig','a').write('x'); "
                     f"os.chdir('..'); subprocess.run(['{G}','x','origin','main'])\"",
                     "python -c \"import subprocess; subprocess.run('echo y >> .gi''t/conf''ig', shell=True); "
                     f"subprocess.run(['{G}','x'])\"")

    def test_class_shell_bodies_and_powershell_writers(self):
        self.refused(f"bash -c 'echo y > somefile'; {self.X}", f"sh -c \"cd .git; echo y >> conf\"; {self.X}")
        self.refused(f"Set-Content -Path notes.txt -Value y; {self.X}",
                     f"[System.IO.File]::WriteAllText('a', 'b'); {self.X}",
                     f"$o = New-Object -ComObject Scripting.FileSystemObject; {self.X}",
                     f"pwsh -NoProfile -Command \"Add-Content a b\"; {self.X}", tool="PowerShell")

    def test_class_writes_to_a_config_named_or_git_folder_target(self):
        self.refused(f"echo y | tee -a ../my.gitconfig; {self.X}",
                     f"sed -i s/a/b/ .git/info/../config; {self.X}",
                     f"cp a.txt sub/config; {self.X}",
                     f"mv a.txt ../gitconfig; {self.X}",
                     f"install -m 644 a.txt .git/hooks/x; {self.X}",
                     f"dd if=a.txt of=.git/config; {self.X}",
                     f"ln -f a.txt my.config; {self.X}",
                     f"cd .git; cp ../a.txt info/exclude; cd ..; {self.X}",
                     f"t=conf; echo y >> .git/$t'ig'; {self.X}")

    def test_round2_any_program_given_a_git_folder_path(self):
        # Fix round 2 (review of dd6af23): an archive, decoder or editor writes into .git through an
        # argument or option value, not a redirection. Any word that resolves inside a .git folder or to a
        # git config file counts, unless its program only reads.
        self.refused(f"tar -xf ../c.tar -C .git; {self.X}",
                     f"unzip -oq ../c.zip -d .git; {self.X}",
                     f"certutil -f -decode ../b64 .git/config; {self.X}",
                     f"printf 'a\\n[alias]\\nx = {U}\\n.\\nw\\n' | ed .git/config; {self.X}",
                     f"7z x ../c.7z -o.git -y; {self.X}",
                     f"cd .git && tar -xf ../../c.tar; cd ..; {self.X}")
        self.refused(f"Expand-Archive ../c.zip -DestinationPath .git -Force; {self.X}", tool="PowerShell")

    def test_round2_read_only_programs_on_git_paths_pass(self):
        self.expect(0, [f"cat .git/config && {G} flow init -d", f"head -3 .git/HEAD; {G} flow init -d",
                        f"grep -c alias .git/config; {G} flow init -d", f"ls .git && {G} flow init -d",
                        f"diff .git/config ../x.cfg; {G} flow init -d",
                        f"{G} --git-dir=.git rerere status", f"GIT_DIR=.git {G} status; {G} flow init -d"])
        self.expect(0, [f"Get-Content .git/config; {G} flow init -d"], tool="PowerShell")

    def test_round3_config_parameters_in_the_environment(self):
        # Fix round 3 (review of b535a60): git reads GIT_CONFIG_PARAMETERS like `-c`, in both quoting forms.
        p1, p2 = f"\"'alias.x={U}'\"", f"\"'alias.x'='{U}'\""
        self.refused(f"GIT_CONFIG_PARAMETERS={p1} {self.X}", f"GIT_CONFIG_PARAMETERS={p2} {self.X}",
                     f"export GIT_CONFIG_PARAMETERS={p1}; {self.X}", f"env GIT_CONFIG_PARAMETERS={p2} {self.X}",
                     f"declare -x GIT_CONFIG_PARAMETERS={p1}; {self.X}", f"GIT_CONFIG=../xx {self.X}")
        self.refused(f"$env:GIT_CONFIG_PARAMETERS={p1}; {self.X}",
                     f"[Environment]::SetEnvironmentVariable('GIT_CONFIG_PARAMETERS', {p1}); {self.X}",
                     tool="PowerShell")

    def test_round3_count_key_value_trio_in_unread_forms(self):
        # The literal `NAME=value` trio is read as an alias (B5env); a form the gate cannot read refuses.
        sev = "[Environment]::SetEnvironmentVariable"
        self.refused(f"{sev}('GIT_CONFIG_COUNT', '1'); {sev}('GIT_CONFIG_KEY_0', 'alias.x'); "
                     f"{sev}('GIT_CONFIG_VALUE_0', '{U}'); {self.X}",
                     f"Set-Item env:GIT_CONFIG_COUNT 1; Set-Item env:GIT_CONFIG_KEY_0 alias.x; "
                     f"Set-Item env:GIT_CONFIG_VALUE_0 {U}; {self.X}", tool="PowerShell")

    def test_round3_builtins_beside_environment_config_pass(self):
        self.expect(0, [f"GIT_CONFIG_PARAMETERS=\"'core.pager=cat'\" {G} log -1",
                        f"GIT_CONFIG_PARAMETERS=\"'alias.x={U}'\" {G} status",
                        f"export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.pager GIT_CONFIG_VALUE_0=cat; {G} status"])
        self.expect(0, [f"[Environment]::SetEnvironmentVariable('GIT_CONFIG_COUNT', '1'); {G} log -1"],
                    tool="PowerShell")

    def test_inline_code_that_only_prints_and_ordinary_writes_pass(self):
        self.expect(0, [f"python -c \"print('.git/' + 'config')\"; {G} flow init -d",
                        f"node -e \"console.log('[alias] x')\"; {G} flow init -d",
                        f"echo y > notes.txt; {G} flow init -d",
                        f"cp a.txt b.txt && {G} flow init -d"])

    def test_builtins_pass_beside_every_new_rule(self):
        self.expect(0, [f"python -c \"open('.gi'+'t/config','a').write('x')\"; {G} log -1",
                        f"cd .git && echo y >> config; cd ..; {G} status",
                        f"bash -c 'echo y > somefile'; {G} status",
                        f"echo y | tee -a ../my.gitconfig; {G} log -1"])
        self.expect(0, [f"[IO.File]::AppendAllText('n.txt', 'y'); {G} status",
                        f"Set-Content -Path notes.txt -Value y; {G} log -1"], tool="PowerShell")

    def test_everyday_lines_still_pass(self):
        self.expect(0, GW2Candidates.EVERYDAY)
        self.expect(0, GW2Candidates.EVERYDAY_PS, tool="PowerShell")


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


# ---------------------------------------------------------------- M14d (2026-10-09)
# The V-K8w2 rows K8w3b fixed in place (B6, B10, gh remote refs, FP-A..FP-D): their case strings are
# copied from test_hooks.py (K8w3bPushTests, K8w3bDirectRuleTests; the originals stay) so every
# verifier row has a class here. B7's cases stay in test_hooks.py only (K8w3bDirectRuleTests): the
# live hyperv_lock refuses writing them into a new file, by design. Push fixtures inside heredocs are
# plain pushes, never a force: the shape is refused whatever the body holds. The guarded words are
# built by concatenation.

def flat(text: str) -> str:
    """The refusal text on one line: hl.note wraps the reason at 100 columns."""
    return " ".join(text.split())


class DirectShapeBase(unittest.TestCase):
    """A plain folder at the install default (no mode forced) for the hooks that read the line alone."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-shapes-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        state = os.path.join(self.tmp, "state")
        os.makedirs(state)
        self.env = {"GATEWARDEN_STATE": state}

    def expect(self, hook, code, cmds, tool="Bash", reason=None):
        for cmd in cmds:
            got, _, err = run_hook(hook, bash(cmd, self.tmp, tool), env=self.env)
            self.assertEqual(got, code, f"{hook} {tool}: {cmd!r}: {err.strip()}")
            if reason:
                self.assertIn(reason, flat(err), f"{hook} {tool}: {cmd!r}: {err.strip()}")


GO_LIVE = "go-live and stream-key requests are the owner's button"
OBS64, OBS_CMD, OBS_CLI = "obs" + "64", "obs" + "-cmd", "obs" + "-cli"
START_STREAM, START_VCAM = "--start" + "streaming", "--start" + "virtualcam"


class B6(DirectShapeBase):
    """V-K8w2 B6: OBS started from the command line with a go-live flag, or the obs-cmd / obs-cli verbs that
    start or toggle a stream or the virtual camera, are the same go-live request as the WebSocket call."""

    def test_refuses_obs_command_line_go_live(self):
        self.expect("golive_block.py", 2, [f"{OBS64}.exe {START_STREAM}", f"{OBS64} {START_VCAM} --minimize-to-tray",
                                           f"{OBS_CMD} stream" + "ing start", f"{OBS_CMD} virtual-camera toggle",
                                           f"{OBS_CLI} stream start", f"{OBS_CLI} virtualcam start"], reason=GO_LIVE)

    def test_other_obs_command_lines_pass(self):
        self.expect("golive_block.py", 0, [f"{OBS64}.exe --minimize-to-tray", f"{OBS_CMD} recording start",
                                           f"{OBS_CMD} stream" + "ing status", f"{OBS_CLI} scene current"])


NO_INPUT = "standard input"
PYN = "py" + "thon"


class B10(DirectShapeBase):
    """V-K8w2 B10: a shell or REPL started with nothing on standard input (`node -`, bare `node` / `sh`,
    `bash -s`, `pwsh -Command -`, ipython, `python -m code`, a winpty launcher) waits until the call times
    out. Refused by heredoc_guard's stdin rule; a fed, scripted or inline call still passes."""

    def test_refuses_shells_and_repls_with_no_input(self):
        self.expect("heredoc_guard.py", 2, ["node", "node -", "node -i", "sh", "bash -s", "bash -i",
                                            "pwsh -Command -", "ipython", f"{PYN} -m code", f"winpty {PYN}"],
                    reason=NO_INPUT)
        self.expect("heredoc_guard.py", 2, ["node"], tool="PowerShell", reason=NO_INPUT)

    def test_fed_or_scripted_calls_pass(self):
        self.expect("heredoc_guard.py", 0, ["node x.js", "node -e 1", "node --test", "node --version", "echo 1 | node",
                                            "node < x.js", "bash x.sh", "bash -c 'echo hi'", "bash -s < x.sh",
                                            "cat x.sh | bash -s", "bash <<'EOF'\necho hi\nEOF", "ipython x.py",
                                            f"winpty {PYN} x.py", "which sh", "bash --version",
                                            "pwsh -Command Get-Date", "pwsh -File x.ps1", f"{PYN} -m json.tool x.json"])


class FlatPushBase(PushShapeBase):
    def expect(self, code, cmds, tool="Bash", reason=None):
        for cmd in cmds:
            got, _, err = run_hook("push_gate.py", bash(cmd, self.work, tool), env=self.env)
            self.assertEqual(got, code, f"{tool}: {cmd!r}: {err.strip()}")
            if reason:
                self.assertIn(reason, flat(err), f"{tool}: {cmd!r}: {err.strip()}")


GH_API, GH_SYNC = "`gh api ", "`gh repo sync --force` resets a remote branch"


class GhRefs(FlatPushBase):
    """V-K8w2 scope row: `gh api` DELETE on a git ref, a PATCH with force=true, and `gh repo sync --force`
    move or drop a remote ref without git push. Refused as push_gate.irreversible; reads and a PATCH with
    force=false pass."""

    def test_refuses_gh_api_remote_ref_delete_or_force(self):
        self.expect(2, ["gh api -X DELETE repos/o/r/git/refs/heads/main",
                        "gh api --method=DELETE /repos/o/r/git/refs/tags/v1",
                        "gh api -X PATCH repos/o/r/git/refs/heads/main -f sha=abc -F force=true"], reason=GH_API)

    def test_refuses_gh_repo_sync_force(self):
        self.expect(2, ["gh repo sync --force", "gh repo sync o/r --force"], reason=GH_SYNC)

    def test_gh_remote_ref_reads_pass(self):
        self.expect(0, ["gh api repos/o/r/git/refs/heads/main", "gh repo sync",
                        "gh api -X PATCH repos/o/r/git/refs/heads/main -f sha=abc -F force=false"])


WRITE_AND_RUN = "a script this line writes and runs"
CANNOT_PARSE = "this line holds a push the gate cannot parse"


class FP_A(FlatPushBase):
    """V-K8w2 FP-A: a cat/tee heredoc written to a notes file whose body names a push is prose, not a push
    (push_gate.inert_writer_bodies). A heredoc written to a file the same line then runs is still read."""

    def test_notes_heredoc_naming_a_push_passes(self):
        self.expect(0, [f"cat <<'EOF' > README.md\nRun {G} {U} origin main when done.\nEOF",
                        f"cat >> RESUME.md <<EOF\nthen {G} {U} origin main\nEOF",
                        f"tee notes.md <<'EOF'\n{G} {U} is refused here when forced\nEOF",
                        f"cat > notes.md <<'EOF'\n{G} {U} origin main\nEOF\n{G} add notes.md"])

    def test_refuses_heredoc_written_and_run_on_the_same_line(self):
        self.expect(2, [f"cat > t.sh <<'EOF'\n{G} {U} origin main\nEOF\nbash t.sh",
                        f"cat > notes.md <<'EOF'\n{G} {U} origin main\nEOF\nsh notes.md"], reason=WRITE_AND_RUN)


class FP_B(FlatPushBase):
    """V-K8w2 FP-B: prose naming a push redirected into a data file (.txt .md .json …) or written by
    Set-Content / Add-Content / Out-File passes; the same text into a runnable file is still refused."""

    def test_prose_into_a_data_file_passes(self):
        self.expect(0, [f'echo "{G} {U} later" >> todo.txt', f"printf '%s\\n' 'then {G} {U} origin main' > notes.md",
                        f'echo "{G} {U} after review" > plan.json'])
        self.expect(0, [f'Set-Content notes.md "remember to {G} {U}"',
                        f'Add-Content -Path todo.txt -Value "{G} {U} later"',
                        f'"{G} {U} later" | Out-File todo.txt'], tool="PowerShell")

    def test_refuses_push_text_into_a_script_file(self):
        self.expect(2, [f'echo "{G} {U} origin main" > x.sh'], reason=CANNOT_PARSE)
        self.expect(2, [f'Set-Content run.ps1 "{G} {U} origin main"'], tool="PowerShell", reason=CANNOT_PARSE)


class FP_C(FlatPushBase):
    """V-K8w2 FP-C: `git push origin $BR` (a loop variable, `"$(git branch --show-current)"`) names a branch
    known only at run time. M14a decided it stays refused by design, with the B3 run-time reason, not
    resolved or nudged; write the branch out. The literal push passes."""

    def test_refuses_branch_known_only_at_run_time(self):
        self.expect(2, [f"{G} {U} origin $BR", f"for b in main; do {G} {U} origin $b; done",
                        f'{G} {U} origin "$({G} branch --show-current)"'], reason=RUN_TIME)

    def test_literal_branch_push_passes(self):
        self.expect(0, [f"{G} {U} origin main", f"{G} {U} -u origin feat/x"])


BUILT_PROGRAM = "a program name built at run time"


class FP_D(FlatPushBase):
    """V-K8w2 FP-D: a variable program (`$PYTHON`) in an earlier `&&` / `;` segment does not make a plain
    `git push` unreadable. A variable in the push segment itself is still refused, and so is a run-time
    push argument behind the same earlier segment (the disguised-input control K8w3b left open): the
    exemption holds only when the push segment is a plain `git …` with no `$` or backtick, so the
    line-wide rule refuses it first."""

    def test_variable_program_in_an_earlier_segment_passes(self):
        self.expect(0, [f"$PYTHON x.py && {G} {U} origin main", f"$py tools/release.py; {G} {U} origin main"])

    def test_refuses_variable_program_in_the_push_segment(self):
        self.expect(2, [f"$PYTHON x.py && $G {U} origin main", f"G={G}; $G {U} origin main"], reason=BUILT_PROGRAM)

    def test_refuses_run_time_argument_after_an_earlier_variable_program(self):
        self.expect(2, [f"$PYTHON x.py && {G} {U} $OPT origin main"], reason=BUILT_PROGRAM)


class UnreadScript(unittest.TestCase):
    """The gate stopped reading a script at an unclosed substitution and reported no pushes, so a later
    force push passed unread. The wrapper line names only the file, so the script's own code decides
    (observation 0597). The substitution fixture is built by concatenation for the same reason as G, U."""

    OPEN = "$" + "("

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-unread-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        state = os.path.join(self.tmp, "state")
        os.makedirs(state)
        self.env = {"GATEWARDEN_STATE": state}

    def verdict(self, body, tool, name="t.ps1"):
        path = Path(self.tmp, name)
        path.write_text(body, encoding="utf-8")
        return run_hook("push_gate.py", bash(str(path), self.tmp, tool), env=self.env)

    def test_refuses_a_push_after_an_unclosed_substitution(self):
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                got, _, err = self.verdict(f'Write-Host "a {self.OPEN} b"\n{G} {U} origin main\n', tool)
                self.assertEqual(got, 2, err)
                self.assertIn("t.ps1", err)

    def test_an_unclosed_substitution_naming_no_push_passes(self):
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                got, _, err = self.verdict(f'Write-Host "a {self.OPEN} b"\nGet-Date\n', tool)
                self.assertEqual(got, 0, err)

    def test_a_comment_naming_push_does_not_count(self):
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                got, _, err = self.verdict(f'# the daily task sends the {U}\nWrite-Host "a {self.OPEN} b"\n', tool)
                self.assertEqual(got, 0, err)

    def test_a_refusal_names_the_segment_that_names_push(self):
        got, _, err = self.verdict(f'param([switch]$Force)\nreturn "{U}: not sent"\n', "PowerShell")
        self.assertEqual(got, 2, err)
        self.assertIn("not sent", err)


if __name__ == "__main__":
    unittest.main()
