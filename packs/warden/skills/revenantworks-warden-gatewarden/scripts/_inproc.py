"""Run a gatewarden hook script inside the test process (observation 0725).

A Python spawn per case made the hook suites the slowest part of local CI on Windows. This runs the hook
file as `__main__` with runpy after dropping every module loaded from hooks/, so each case starts from
fresh module state (hooklib's event, clock and read-file lists, push_gate's caches), exactly as a new
process would. stdin, stdout, stderr, argv and the environment are swapped for the call and restored.

Limits, kept as subprocess tests: anything that tests the time budget (its backstop is os._exit, which
would end the test run), and at least one smoke case per hook, so the real entry point is still proven.
The budget defaults to an hour here unless the case sets GATEWARDEN_BUDGET.
"""
from __future__ import annotations

import io
import json
import os
import runpy
import sys
import traceback
from pathlib import Path

HOOKS = Path(__file__).resolve().parent / "hooks"


def _drop_hook_modules() -> None:
    root = os.path.normcase(str(HOOKS))
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None) or ""
        if path and os.path.normcase(os.path.abspath(path)).startswith(root):
            del sys.modules[name]


def run_hook(name: str, data: str, env: dict, argv: tuple = ()) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) of hooks/<name> fed `data` on stdin under exactly `env`."""
    saved_env = dict(os.environ)
    saved = (sys.stdin, sys.stdout, sys.stderr, list(sys.argv), list(sys.path))
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        os.environ.clear()
        os.environ.update({k: v for k, v in env.items() if v is not None})
        os.environ.setdefault("GATEWARDEN_BUDGET", "3600")
        _drop_hook_modules()
        sys.path.insert(0, str(HOOKS))
        sys.stdin, sys.stdout, sys.stderr = io.StringIO(data), out, err
        sys.argv = [str(HOOKS / name), *argv]
        try:
            runpy.run_path(str(HOOKS / name), run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        except Exception:
            err.write(traceback.format_exc())
            code = 1
    finally:
        sys.stdin, sys.stdout, sys.stderr, sys.argv, sys.path[:] = saved
        os.environ.clear()
        os.environ.update(saved_env)
        _drop_hook_modules()
    return code, out.getvalue(), err.getvalue()


def run_event(name: str, event: dict, env: dict) -> tuple[int, str, str]:
    return run_hook(name, json.dumps(event), env)
