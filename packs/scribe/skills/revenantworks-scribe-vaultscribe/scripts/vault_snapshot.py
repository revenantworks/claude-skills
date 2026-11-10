"""vaultscribe living-source snapshot and drift check. Python 3 stdlib only; no network.

A living source is a document that keeps changing after it is filed (a repo's README, a team
handbook page kept in a clone). The vault never cites the live file: it cites a dated copy under
raw/snapshots/<date>/. This script makes those copies and tells when they have gone stale.

Usage
  python vault_snapshot.py --root SOURCES_ROOT [--vault VAULT] [--list FILE] [--date YYYY-MM-DD] [--dry-run]
  python vault_snapshot.py --check --root SOURCES_ROOT [--vault VAULT] [--list FILE] [--expect a,b]

The list (default VAULT/tools/snapshot-sources.txt) holds one `<group>:<path>` per line, `#` for a
comment. <group> is a folder under SOURCES_ROOT (a repo clone such as `team/handbook`); <path> is
relative to it. A line that is absolute or climbs out with `..` is refused, never copied.

Copy: writes VAULT/raw/snapshots/<date>/<group>/<path> for every listed file, byte for byte. It
never overwrites: a second run on the same date refuses, and older snapshots stay as they are.
Check (`--check`) writes nothing. It compares the newest snapshot with the originals and prints
  CHANGED: <line>           the original differs from its snapshot (line endings set aside)
  NOT-IN-SNAPSHOT: <line>   a listed source the newest snapshot lacks
  GONE: <line>              a listed source no longer exists under SOURCES_ROOT
  NEW-REPO: <group>         a group named in --expect that no list line covers
Exit codes: copy 0 done, 1 refused (the date folder exists), 2 usage error (an unsafe list line
included); check 0 fresh, 1 stale, 2 usage error, 3 NOT-RUN (no snapshot yet: nothing to compare).
Reference: references/refresh.md.
"""
import argparse
import datetime
import pathlib
import shutil
import sys

SNAPSHOT_DIR = ("raw", "snapshots")


class UsageError(Exception):
    pass


def entries(list_file):
    """Yield (line, group, relpath) for every list line; raise UsageError on an unsafe one."""
    if not list_file.is_file():
        raise UsageError(f"no source list at {list_file.as_posix()}")
    for n, line in enumerate(list_file.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        group, sep, rel = line.partition(":")
        parts = (group + "/" + rel).replace("\\", "/").split("/")
        if (not sep or not group or not rel or group.startswith(("/", "\\")) or rel.startswith(("/", "\\"))
                or ".." in parts or ":" in rel or (len(group) > 1 and group[1] == ":")):
            raise UsageError(f"list line {n} is not a safe <group>:<relative path> line: {line!r}")
        yield line, group.strip("/"), rel.strip("/")


def same(a, b):
    """Equal text once line endings are set aside (git may check either side out with CRLF)."""
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def snapshots(vault):
    base = vault.joinpath(*SNAPSHOT_DIR)
    return sorted(p for p in base.glob("????-??-??") if p.is_dir()) if base.is_dir() else []


def check(vault, root, list_file, expect):
    dates = snapshots(vault)
    if not dates:
        return ["NOT-RUN: no snapshot yet under raw/snapshots/ (run a copy first)"], 3
    newest = dates[-1]
    stale, listed = [], set()
    for line, group, rel in entries(list_file):
        listed.add(group)
        src, snap = root / group / rel, newest / group / rel
        if not src.is_file():
            stale.append(f"GONE: {line}")
        elif not snap.is_file():
            stale.append(f"NOT-IN-SNAPSHOT: {line}")
        elif not same(src, snap):
            stale.append(f"CHANGED: {line}")
    stale += [f"NEW-REPO: {g}" for g in sorted(set(expect) - listed)]
    return stale + [f"snapshot {newest.name}: {len(stale)} stale"], (1 if stale else 0)


def copy(vault, root, list_file, day, dry_run):
    out = vault.joinpath(*SNAPSHOT_DIR, day)
    rel_out = out.relative_to(vault).as_posix()
    if out.exists():
        return [f"refused: {rel_out} exists; snapshots are never overwritten"], 1
    copied, missing = [], []
    for line, group, rel in list(entries(list_file)):
        src, dst = root / group / rel, out / group / rel
        if not src.is_file():
            missing.append(line)
            continue
        copied.append(dst.relative_to(vault).as_posix())
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    lines = [f"copied: {p}" for p in copied] + [f"missing: {m}" for m in missing]
    lines.append(f"{len(copied)} copied, {len(missing)} missing{' (dry run)' if dry_run else ''}")
    return lines, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Snapshot living sources into a vault, or check them for drift.")
    ap.add_argument("--root", required=True, help="the folder that holds every <group> named in the list")
    ap.add_argument("--vault", default=".", help="the vault root (default: the current folder)")
    ap.add_argument("--list", help="the source list (default: VAULT/tools/snapshot-sources.txt)")
    ap.add_argument("--date", help="YYYY-MM-DD for the new snapshot folder (default: today)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--expect", default="", help="comma-separated groups the list must cover")
    a = ap.parse_args(argv)
    # `~` is expanded here: PowerShell passes it to a program unexpanded.
    vault, root = pathlib.Path(a.vault).expanduser(), pathlib.Path(a.root).expanduser()
    list_file = pathlib.Path(a.list).expanduser() if a.list else vault / "tools" / "snapshot-sources.txt"
    try:
        if not root.is_dir():
            raise UsageError(f"--root {root.as_posix()} is not a folder")
        if not (vault / "raw").is_dir():
            raise UsageError(f"{vault.as_posix()} has no raw/ folder; pass the vault root")
        if a.check:
            lines, code = check(vault, root, list_file, [g.strip() for g in a.expect.split(",") if g.strip()])
        else:
            day = a.date or datetime.date.today().isoformat()
            datetime.date.fromisoformat(day)
            lines, code = copy(vault, root, list_file, day, a.dry_run)
    except UsageError as e:
        print(f"usage error: {e}")
        return 2
    except ValueError:
        print(f"usage error: --date {a.date!r} is not YYYY-MM-DD")
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
