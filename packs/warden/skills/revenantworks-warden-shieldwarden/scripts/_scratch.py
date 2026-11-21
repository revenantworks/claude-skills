"""Scratch-folder removal for the warden test suites (pack-shared).

The suites build throwaway git repos under the temp folder. Git writes its
object files read-only, and on Windows shutil.rmtree cannot delete a
read-only file: with ignore_errors=True the failure is silent and the whole
test folder stays behind, one per test. force_rmtree clears the read-only
bit and retries, so the folder really goes.

Gatewarden's suites (gw-*) moved to it on 2026-11-13. On 2026-11-21 the
scratch root still held thousands of shf-* and trustvet-* folders from
shieldwarden and trustwarden, so the helper became pack-shared: the source
is packs/warden/shared/scripts/_scratch.py and tools/build.py writes each
holder's copy.
"""
from __future__ import annotations

import os
import shutil
import stat
import sys


def _retry_writable(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except OSError:
        pass


def force_rmtree(path) -> None:
    """Remove path and everything under it, read-only files included. Never raises."""
    if not path or not os.path.exists(path):
        return
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_retry_writable)
        else:
            shutil.rmtree(path, onerror=_retry_writable)
    except OSError:
        pass
