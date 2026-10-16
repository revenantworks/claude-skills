#!/usr/bin/env python3
"""obs_secret.py — where obsrunner finds the OBS WebSocket password, without ever printing it.

Run, not read. Stdlib only (ctypes on Windows).

  where            which source holds the password: dpapi | env | user-env | none (never the value)

Owner rule (2026-10-16): the password never sits in a plain environment variable as its home.
The home is a DPAPI file, current-user scope, in the estate's format: the hex of
CryptProtectData over the UTF-16-LE text, no entropy, at

    %LOCALAPPDATA%\\estate-secrets\\OBS_WEBSOCKET_PASSWORD.dpapi

written by `obs_configure.ps1` (the owner runs it; it prints nothing secret). The order read:

  1. the DPAPI file;
  2. the process environment variable OBS_WEBSOCKET_PASSWORD (a fallback, reported as such);
  3. the user environment in the registry (HKCU\\Environment), for a session started before the
     variable was set (reported as such).

An empty value counts as absent: a masked prompt that saved nothing must not read as
"no password". `OBSRUNNER_SECRET_SOURCES` (comma list of dpapi, env, user-env) narrows the order;
the tests use it so the rig's real secrets never reach them.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

NAME = "OBS_WEBSOCKET_PASSWORD"
SOURCES = ("dpapi", "env", "user-env")


def secret_path(name: str = NAME) -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "estate-secrets" / f"{name}.dpapi"


def _crypt(data: bytes, protect: bool) -> bytes:
    """CryptProtectData / CryptUnprotectData: current user, no entropy, no UI (flag 0x1)."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    dst = Blob()
    if not fn(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(dst)):
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(dst.pbData, ctypes.c_void_p))


def protect_text(text: str) -> str:
    """The file body for a value: hex of the protected UTF-16-LE bytes (Windows only)."""
    return _crypt(text.encode("utf-16-le"), True).hex().upper()


def read_dpapi(name: str = NAME) -> str | None:
    if os.name != "nt":
        return None
    try:
        raw = bytes.fromhex(secret_path(name).read_text(encoding="ascii").strip())
        return _crypt(raw, False).decode("utf-16-le") or None
    except Exception:  # missing file, bad hex, wrong user: absent, never a crash
        return None


def read_user_env(name: str = NAME) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, name)
        return str(val) or None
    except OSError:
        return None


def resolve(name: str = NAME) -> tuple[str | None, str]:
    """(value, source). Source is one of SOURCES or 'none'; the value is never logged."""
    order = [s.strip() for s in os.environ.get("OBSRUNNER_SECRET_SOURCES", ",".join(SOURCES)).split(",")]
    for src in order:
        if src == "dpapi":
            val = read_dpapi(name)
        elif src == "env":
            val = os.environ.get(name) or None
        elif src == "user-env":
            val = read_user_env(name)
        else:
            continue
        if val:
            return val, src
    return None, "none"


NOTES = {
    "dpapi": "password read from the DPAPI file",
    "env": "password read from a plain environment variable: run obs_configure.ps1 -Migrate to move "
           "it into the DPAPI file and delete the variable (owner rule 2026-10-16)",
    "user-env": "password read from the user environment in the registry (this session started before "
                "the variable was set): run obs_configure.ps1 -Migrate",
    "none": "no password found (DPAPI file, environment, user environment); an empty saved value counts "
            "as none. The owner runs obs_configure.ps1 (references/install-walkthrough.md)",
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["where"]:
        print(json.dumps({"error": "usage: obs_secret.py where"}))
        return 2
    _, src = resolve()
    print(json.dumps({"command": "where", "source": src, "file": str(secret_path()),
                      "note": NOTES[src]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
