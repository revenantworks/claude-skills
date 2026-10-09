#!/usr/bin/env python3
"""hyperv_lock.py: PreToolUse hook (matcher Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit)
that blocks Hyper-V restore and remove commands Claude runs itself, outside the one
hypervrunner script allowed to run each.

Five classes, case-insensitive, anywhere in a command (a compound line, `python -c`,
`powershell -Command`) and in a script file Claude writes or edits:
  restore      Restore-VMSnapshot / Restore-VMCheckpoint
  remove       Remove-VM, Remove-VMSnapshot / Remove-VMCheckpoint, Remove-VHD
  disk-delete  deleting a .vhd, .vhdx, .avhd or .avhdx file (Remove-Item, rm, del, erase,
               os.remove, unlink, rmtree)
  wmi          Msvm_VirtualSystemSnapshotService, ApplySnapshot, DestroySnapshot, DestroySystem
  disk-write   overwriting, emptying or moving a disk file named in the verb's own arguments
               (Set-Content, Add-Content, Out-File, Clear-Content, a `>` redirect, truncate, Move-Item,
               mv, Rename-Item; shutil.move, os.replace in code), and a wildcard extension such as
               `*.vh*` given to a delete verb or piped into one (V-K8w2 B7). Deleting a whole folder
               that holds disks stays a stated limit.

Allowed (owner decision 2026-10-02):
  - hypervrunner's `scripts/teardown.py` is the only caller of remove and disk-delete
    (controlled soft delete: two locks, plan sha256, quarantine, purge). Claude may run
    its plan, execute, list, purge --due, purge-command and protect (it may also hold disk-write
    text: it quarantines disks); `purge --entry` is
    the owner's command and is blocked here. Only teardown.py may hold remove or
    disk-delete text; no hypervrunner file may hold the wmi class.
  - `scripts/cleanroom.py` runs the one restore (its own GUID-checked test VM);
    `scripts/vmctl.py` prints the restore as an owner command. Only these two may hold
    restore text.
  - A call of those scripts passes when its arguments carry no restore, remove or wmi
    text (a disk path in an argument is fine).
  - Read-only searches (grep, rg, findstr, Select-String, git grep) that only name a cmdlet,
    and everything else, including Checkpoint-VM and Get-VMSnapshot.

Pinned scripts (owner brief HV2): a Python call of teardown.py, cleanroom.py or vmctl.py
inside a hypervrunner scripts folder runs only when the file at that path matches the sha256
the owner pinned. Pins live beside this hook in `hyperv_lock.pins.json`
(`GATEWARDEN_HYPERV_PINS` moves it); the owner writes them with
`python hyperv_lock.py --pin <hypervrunner>/scripts` and re-pins after each hypervrunner
update. No pin file, an unreadable script or a changed script blocks the call. Claude may
not run `--pin` or write the pin file. A `cd` / `Set-Location` earlier on the same line
moves the folder a relative script path is read from.

Fail mode: closed for anything that names a blocked class or a pinned script; open
otherwise. Limits, stated plainly: this binds the commands Claude runs, not the owner's;
admin rights and Hyper-V Administrators membership let the owner run any of these in their
own terminal. The pin covers Python calls of the three scripts. The hooks folder and the pin file
are protected by the deny `Edit(~/.claude/hooks/**)` that `perm_audit.py harden --add-hooks` writes
(owner HV2), not by this hook. Every command is unwrapped first (hooklib.expand: splices, string
concatenation, shell wrappers, -EncodedCommand, script files and piped scripts); a name built from
variables at run time passes unless the line names a VM, disk, snapshot or checkpoint beside a
remove or restore verb.
"""
from __future__ import annotations

import datetime
import fnmatch
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

RESTORE = re.compile(r"(?i)(?<![\w-])(?:hyper-v\\)?restore-vm(?:snapshot|checkpoint)")
REMOVE = re.compile(r"(?i)(?<![\w-])(?:hyper-v\\)?(?:remove-vm(?:snapshot|checkpoint)|remove-vm(?![\w-])"
                    r"|remove-vhd(?![\w-]))")
WMI = re.compile(r"(?i)msvm_virtualsystemsnapshotservice|\bapplysnapshot\b|\bdestroysnapshot\b|\bdestroysystem\b")
EXT = r"\.a?vhdx?\b"
DISK = re.compile(r"(?i)" + EXT)
# V-K8w2 B7: verbs that overwrite, empty or move a disk file named after them, a `>` redirect into one,
# code that moves or rewrites one, and a wildcard extension that can match one.
WRITE_PROGS = {"set-content", "sc", "add-content", "ac", "out-file", "clear-content", "clc", "clear-item", "cli",
               "move-item", "mi", "mv", "move", "rename-item", "rni", "ren", "truncate"}
VALUE_ARGS = {"-value", "-inputobject", "-encoding", "-filter", "-include", "-exclude"}
PIPE_TARGETS = {"remove-item", "ri", "rm", "del", "erase", "unlink", "shred", "clear-content", "clc", "clear-item",
                "cli", "move-item", "mi", "mv", "move", "rename-item", "rni", "ren", "truncate"}
PIPE_RUNNERS = {"xargs", "foreach-object", "%", "foreach", "parallel"}
REDIR_DISK = re.compile(r"(?i)(?<![<>&\d-])\d*>>?\|?\s*['\"]?[^\s;|&<>()'\"]*" + EXT)
WRITE_CODE = re.compile(r"(?i)shutil\.move|os\.rename|os\.replace|\.truncate\(|\[io\.file\]::(?:move|writeall\w*"
                        r"|create|replace)")
GLOB_EXT = re.compile(r"\.([A-Za-z*?\[\]]{1,8})(?![\w*?\[\]])")
DISK_EXTS = ("vhd", "vhdx", "avhd", "avhdx")


def disk_glob(text: str) -> bool:
    """A wildcard extension that can match a disk file (`*.vh*`, `*.vh*x`, `*.?vhd`)."""
    for m in GLOB_EXT.finditer(text):
        pat = m.group(1).lower()
        if re.search(r"[*?\[]", pat) and ("v" in pat or "hd" in pat) and \
                any(fnmatch.fnmatchcase(e, pat) for e in DISK_EXTS):
            return True
    return False


def disk_named(text: str) -> bool:
    return bool(DISK.search(text)) or disk_glob(text)


def disk_write(seg: str) -> bool:
    """True when the segment overwrites, empties or moves a disk file (V-K8w2 B7). The file must sit in the
    verb's own arguments: `Get-VHD x | Out-File report.txt` writes the report, not the disk."""
    if REDIR_DISK.search(seg):
        return True
    toks = hl.tokens(seg)
    for k, t in enumerate(toks):
        if hl.prog(t) not in WRITE_PROGS:
            continue
        skip = False
        for a in toks[k + 1:]:
            if skip:
                skip = False
            elif a.lower() in VALUE_ARGS:
                skip = True
            elif disk_named(hl.unquote(a)):
                return True
    return False


def pipe_reason(segs: list[str]) -> bool:
    """A pipeline that lists disk files and feeds them to a delete, move or clear verb (V-K8w2 B7):
    `Get-ChildItem *.vh*x | Remove-Item`, `ls *.<disk> | xargs rm`. Searches neither list nor feed."""
    named = False
    for seg in segs:
        if SEARCH.search(seg):
            continue
        progs = [hl.prog(t) for t in hl.tokens(seg)]
        if named and progs and (progs[0] in PIPE_TARGETS or progs[0] in PIPE_RUNNERS and
                                (DELETE.search(seg) or any(p in PIPE_TARGETS for p in progs[1:]))):
            return True
        named = named or disk_named(seg)
    return False
DELETE = re.compile(r"(?i)(?<![\w-])(?:remove-item|ri|rm|rmdir|rd|del|erase|unlink|shred)(?![\w-])"
                    r"|os\.remove|os\.unlink|shutil\.rmtree|\.unlink\(|\[io\.file\]::delete")
SEARCH = re.compile(r"(?i)^\s*(?:grep|egrep|rg|findstr|select-string|sls|git\s+grep|git\s+log)\b")
HV_SCRIPT = re.compile(r"(?i)revenantworks-localops-hypervrunner[\\/]+scripts[\\/]+(teardown|cleanroom|vmctl)\.py$")
# What each hypervrunner script may hold (write check) and run (command check).
MAY_HOLD = {"teardown": {"remove", "disk-delete", "disk-write"}, "cleanroom": {"restore"}, "vmctl": {"restore"}}
MAY_CALL = {"teardown", "cleanroom"}
CALL = re.compile(r"""(?ix)^\s*(?:&\s*)?(?:"[^"]*[\\/])?(?:[^\s"]*[\\/])?
    (?:python(?:3(?:\.\d+)?)?w?|py)(?:\.exe)?"?\s+(?:-\S+\s+)*
    (?:"(?P<q>[^"]+)"|'(?P<s>[^']+)'|(?P<b>\S+))(?P<rest>.*)$""")
OWNER_PURGE = re.compile(r"(?i)teardown\.py\b.*?(?<![\w-])purge(?![\w-])")
DUE = re.compile(r"(?i)(?<![\w-])--due(?![\w-])")
ENTRY = re.compile(r"(?i)(?<![\w-])--entry(?![\w-])")
DOC_EXT = re.compile(r"(?i)\.(md|markdown)$")
HINT_VERB = re.compile(r"(?i)\b(?:remove|restore|destroy|apply|delete|del|erase|unlink|rm)")
HINT_NOUN = re.compile(r"(?i)(?:vm\b|vhd|snapshot|checkpoint)")
PINNED = ("teardown", "cleanroom", "vmctl")
PIN_FILE = "hyperv_lock.pins.json"
PIN_NAME = re.compile(r"(?i)hyperv_lock\.pins\b")
PIN_CMD = re.compile(r"(?i)hyperv_lock\.py\b.*?(?<![\w-])--pin(?![\w-])")
CD = re.compile(r"""(?i)^\s*(?:cd|chdir|pushd|set-location|sl)\s+(?:-path\s+)?(?:"([^"]+)"|'([^']+)'|(\S+))\s*$""")
SCRIPT_EXT = re.compile(r"(?i)\.(ps1|psm1|psd1|bat|cmd|py|sh|vbs|js)$")

REASON = ("hyperv lock: Hyper-V restore and remove commands are not Claude's to run. Removing a VM "
          "goes through hypervrunner's teardown.py (plan, sha256, the owner's OK, soft delete); a "
          "restore is an owner command (vmctl.py owner-command --op restore); only the clean-room "
          "script may revert its own test VM. Hand the owner the teardown or owner-command line.")
PIN_OWNER_REASON = ("hyperv lock: the script pins are the owner's. Writing or changing "
                    "hyperv_lock.pins.json, or running `hyperv_lock.py --pin`, is an owner step; hand "
                    "the owner the command from gatewarden's install walkthrough.")
PURGE_REASON = ("hyperv lock: `teardown.py purge --entry` is the owner's command. Print it with "
                "`teardown.py purge-command --entry <GUID>` and hand it over; Claude may run only "
                "`purge --due` (the owner's purge_after_days).")


def pins_path() -> str:
    return os.environ.get("GATEWARDEN_HYPERV_PINS") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), PIN_FILE)


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pins() -> dict | None:
    try:
        with open(pins_path(), encoding="utf-8") as f:
            files = json.load(f).get("files")
        return files if isinstance(files, dict) else None
    except Exception:
        return None


def resolve(path: str, cwd: str) -> str:
    path = os.path.expanduser(path.strip())
    m = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    if os.name == "nt" and m:  # Git Bash style: a one-letter root folder becomes that drive
        path = m.group(1).upper() + ":" + (m.group(2) or "/")
    return os.path.normpath(os.path.join(cwd or os.getcwd(), path))


def pin_reason(target: str, cwd: str) -> str | None:
    """None when `target` is not a pinned hypervrunner script or matches its pin."""
    full = resolve(target, cwd)
    script = own_script(target) or own_script(full.replace("\\", "/"))
    if script not in PINNED:
        return None
    name = script + ".py"
    fix = "The owner pins it: python <hooks dir>/hyperv_lock.py --pin <hypervrunner>/scripts"
    pins = load_pins()
    if not pins or not pins.get(name):
        return f"hyperv lock: hypervrunner's {name} is not pinned, so Claude may not run it. {fix}"
    try:
        found = sha256_of(full)
    except OSError:
        return f"hyperv lock: cannot read {name} at that path to check its pin. {fix}"
    if found != str(pins[name]).lower():
        return (f"hyperv lock: {name} at that path does not match its pinned sha256 (pinned "
                f"{str(pins[name])[:12]}, found {found[:12]}). Only the pinned hypervrunner script may "
                f"run. If the owner updated hypervrunner, the owner re-pins. {fix}")
    return None


def pin(scripts_dir: str) -> int:
    """Owner step: write one sha256 per pinned script into the pin file."""
    files = {}
    for s in PINNED:
        p = os.path.join(scripts_dir, s + ".py")
        if not os.path.isfile(p):
            sys.stderr.write(f"hyperv_lock --pin: {p} not found; nothing written\n")
            return 1
        files[s + ".py"] = sha256_of(p)
    data = {"pinned": datetime.date.today().isoformat(), "source": os.path.abspath(scripts_dir),
            "files": files}
    with open(pins_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    for k, v in files.items():
        print(f"{k}  {v}")
    print(f"wrote {pins_path()}")
    return 0


def classes(text: str) -> set[str]:
    found = set()
    if RESTORE.search(text):
        found.add("restore")
    if REMOVE.search(text):
        found.add("remove")
    if WMI.search(text):
        found.add("wmi")
    if disk_named(text) and DELETE.search(text):
        found.add("disk-delete")
    if DISK.search(text) and WRITE_CODE.search(text):
        found.add("disk-write")
    return found


def dangerous(text: str) -> bool:
    return bool(classes(text))


def own_script(path: str) -> str | None:
    m = HV_SCRIPT.search(path.strip())
    return m.group(1).lower() if m else None


def all_classes(text: str) -> set[str]:
    """Classes in the text as written and with quote, escape and concat splices removed."""
    return classes(text) | classes(hl.despliced(text))


def segment_reason(seg: str, cwd: str = "") -> str | None:
    flat = hl.despliced(seg)
    if OWNER_PURGE.search(flat) and (ENTRY.search(flat) or not DUE.search(flat)):
        return PURGE_REASON
    if (PIN_CMD.search(flat) or PIN_NAME.search(flat)) and not SEARCH.search(seg):
        return PIN_OWNER_REASON
    m = CALL.match(seg)
    target = (m.group("q") or m.group("s") or m.group("b") or "") if m else ""
    if m:
        r = pin_reason(target, cwd)
        if r:
            return r
    found = all_classes(seg)
    if disk_write(seg) or disk_write(hl.despliced(seg)):
        found.add("disk-write")
    if not found or SEARCH.search(seg):
        return None
    if m:
        script = own_script(target)
        if script in MAY_CALL and not (all_classes(m.group("rest")) - {"disk-delete", "disk-write"}):
            return None
    return REASON


def view_reason(cmd: str, cwd: str = "") -> str | None:
    pipe: list[str] = []
    for seg, sep in hl.split_ops(cmd):
        c = CD.match(seg)
        if c:
            cwd = resolve(c.group(1) or c.group(2) or c.group(3), cwd)
            pipe = []
            continue
        r = segment_reason(seg, cwd)
        if r:
            return r
        pipe.append(seg)
        if sep != "|":
            if len(pipe) > 1 and pipe_reason(pipe):
                return REASON + " (a pipeline feeds disk files to a delete, move or clear verb)"
            pipe = []
    return None


def hinted(cmd: str) -> bool:
    flat = hl.despliced(cmd)
    return bool(HINT_VERB.search(flat) and HINT_NOUN.search(flat)) or dangerous(flat)


def command_reason(cmd: str, cwd: str = "") -> str | None:
    """Check every shell text and code body the command runs (hooklib.expand)."""
    if len(cmd) > hl.BIG:  # V-K8w F8: a regex scan, never a word-by-word parse
        if all_classes(cmd):
            return REASON + " (a command over 256 KB, read as raw text)"
        return None
    try:
        ex = hl.expand(cmd, cwd)
    except hl.Unparseable as exc:
        if exc.hard or hinted(cmd):
            return REASON + f" ({exc}: the lock cannot read it, so it is blocked)"
        return None
    unread = ex.unread + ex.unread_code
    if unread:  # a script on disk the lock could not read: fail closed (K7-4-03, V-K8w FP2)
        return REASON + f" ({unread[0]}: the lock cannot read it, so it is blocked)"
    for text in ex.big:  # a script over 256 KB: its text is matched, not parsed
        if all_classes(text):
            return REASON + " (a script over 256 KB holds the same command)"
    for text, where in ex.shells:
        r = view_reason(text, where or cwd)
        if r:
            return r
    for body, path in ex.code:
        bad = all_classes(body) - MAY_HOLD.get(own_script(path.replace("\\", "/")) or "", set())
        if bad:
            return REASON + f" The code it runs holds the same command ({', '.join(sorted(bad))})."
    if ex.opaque and hinted(cmd):
        return REASON + f" ({ex.opaque[0]} on a line that names a VM or disk: blocked to be safe)"
    return None


def write_reason(path: str, body: str) -> str | None:
    if PIN_NAME.search(os.path.basename(path.replace("\\", "/"))):
        return PIN_OWNER_REASON
    if not path or DOC_EXT.search(path):
        return None
    script = own_script(path.replace("\\", "/"))
    if not SCRIPT_EXT.search(path) and "revenantworks-localops-hypervrunner" in path.replace("\\", "/"):
        return None  # hypervrunner's own data and docs; its scripts are held to MAY_HOLD below
    bad = all_classes(body) - MAY_HOLD.get(script or "", set())
    if not bad:
        return None
    return REASON + f" Writing it into a file Claude can run is the same command ({', '.join(sorted(bad))})."


def main() -> None:
    ev, raw = hl.read_event()
    if hl.stood_down("L2"):
        sys.exit(0)
    cmd = hl.command_of(ev) if ev else ""
    hl.start_budget("hyperv_lock", REASON, lambda: dangerous(cmd or raw) or hinted(cmd or raw)
                    or any(dangerous(t) for t in hl.FILES_READ))
    try:
        if ev is None:
            raise ValueError("unreadable hook input")
        tool = ev.get("tool_name")
        ti = ev.get("tool_input") or {}
        if tool in hl.SHELL_TOOLS:
            r = command_reason(hl.command_of(ev), str(ev.get("cwd") or ""))
            if r:
                hl.block(r, rule="hyperv_lock", hard=True)
        elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            path = str(ti.get("file_path") or ti.get("notebook_path") or "")
            body = " ".join(str(ti.get(k) or "") for k in ("content", "new_string", "new_source"))
            for e in ti.get("edits") or []:
                body += " " + str((e or {}).get("new_string") or "")
            r = write_reason(path, body)
            if r:
                hl.block(r, rule="hyperv_lock", hard=True)
        hl.allow()
    except SystemExit:
        raise
    except Exception:
        if dangerous(raw or ""):
            hl.block(REASON + " (hook input could not be read; blocked to be safe)", rule="hyperv_lock", hard=True)
        hl.allow()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--pin":
        sys.exit(pin(sys.argv[2]))
    main()
