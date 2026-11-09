#!/usr/bin/env python3
"""claude-skills — release: the whole close-of-pass loop in one command.

    python tools/release.py foundation=2.5.0 [-m "message"] [--no-push]
                            [--swaps DIR] [--export-dir DIR]
    python tools/release.py --dry-run foundation=2.5.0   # print the plan, write nothing

Steps, in order (each stops the run on failure, nothing after it runs):
  1. bump-pack       build.py --bump-pack <pack> <ver> for each pack named — marketplace
                     entry + plugin.json + root CHANGELOG scaffold in one stroke; idempotent.
                     A bare scaffold is replaced by a draft from the pack's commits since the
                     previous tag (release_notes.py: internal scopes dropped, New / Improved /
                     Fixed / Breaking), headed by a "(fill in)" review line
  2. changelog gate  the root CHANGELOG entry for each new tag must be written — a
                     "(fill in)" line under the new heading stops the run here, and so does
                     a Breaking item with no "Migrate:" line; a file path, function name,
                     commit hash or item over four sentences is printed as a warning
  3. build           python tools/build.py — regenerates every references/pack.md, builds dist/
  4. check           python tools/build.py --check must be clean
  5. tests           python -m unittest discover -s tools -p "test_*.py", then
                     python tools/warden_suites.py (every warden member's script suite)
  6. commit          git add -A; pii_scan.py --staged (the public CHANGELOG included, armed
                     hook or not); git commit -m <message>
  7. tag + push      git tag -a <pack>-v<ver> per pack (annotated); on main only, git push
                     origin main, then each tag by its full ref, one push per tag
                     (GitHub fires no event past three tags in one push); success only after
                     git ls-remote reads main and every tag back from origin at this commit
                     (--no-push leaves the tags local; CI attaches the member zips on tag)
  8. upload list     members whose zip changed since the previous tag, and the exact claude.ai
                     upload list (an install variant, dist/install/*+install.zip, is listed
                     instead of the plain zip when apply-install-swaps.py built one from
                     a --swaps dir); every upload is optional
  9. export          with --export-dir, copy every member zip (+ install zips) there with a
                     README.txt carrying the upload list

No skill applies a brand (decision 36, 2026-10-01): the brand-copy step and the
--refresh-brand flag were removed with the retired brand member.

A local install that loads members by junction from a clone needs nothing from a release;
a plugin install updates with `claude plugin update` (RUNBOOK.md).
Stdlib only. Run from anywhere; paths resolve from this file.
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402  — ROOT, PACKS, DIST, MARKETPLACE
import release_notes  # noqa: E402

ROOT = build.ROOT
PY = sys.executable
# member -> reason its claude.ai upload is REQUIRED rather than optional; empty since the
# brand member retired (2026-10-01). Kept so a future required upload is one line.
REQUIRED_ON_CLAUDE_AI: dict[str, str] = {}


def sh(*args: str, cwd: Path = ROOT, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(list(args), cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not quiet and r.stdout.strip():
        print(r.stdout.rstrip())
    if check and r.returncode != 0:
        print(r.stderr.rstrip() or r.stdout.rstrip())
        raise SystemExit(f"✗ {' '.join(args)} failed (exit {r.returncode})")
    return r


def step(n: int, title: str) -> None:
    print(f"\n[{n}] {title}")


# Step 7 (observation 0618). A lightweight tag never rides `--follow-tags`, so the 2026-11-04 releases
# reached origin with no tags and CI built no zips; the push gate also refuses `push origin HEAD` and
# `--tags` on a public repo. So: annotated tags, main pushed by name, each tag by its full ref, and
# success only once origin is read back holding main and every tag at this commit.
def make_tags(tags: list[str], cwd: Path = ROOT) -> None:
    head = sh("git", "rev-parse", "HEAD", cwd=cwd, quiet=True).stdout.strip()
    for t in tags:
        if sh("git", "rev-parse", "-q", "--verify", f"refs/tags/{t}", cwd=cwd, check=False, quiet=True).returncode:
            sh("git", "tag", "-a", t, "-m", t, cwd=cwd, quiet=True)
            print(f"  ✓ tagged {t} (annotated)")
            continue
        kind = sh("git", "cat-file", "-t", f"refs/tags/{t}", cwd=cwd, quiet=True).stdout.strip()
        at = sh("git", "rev-parse", f"refs/tags/{t}^{{commit}}", cwd=cwd, quiet=True).stdout.strip()
        if kind != "tag":
            raise SystemExit(f"✗ tag {t} exists but is lightweight; recreate it annotated: "
                             f"git tag -d {t} && git tag -a {t} -m {t} {at[:12]}")
        if at != head:
            raise SystemExit(f"✗ tag {t} exists at {at[:12]}, not at HEAD {head[:12]}")
        print(f"  = tag {t} exists (annotated, at HEAD)")


def remote_tags(tags: list[str], cwd: Path = ROOT) -> dict[str, str]:
    """tag -> the commit origin's tag points at (the peeled ^{} line of an annotated tag), read
    from the remote itself with `git ls-remote`, never from local refs."""
    # No ref patterns: a pattern matches the ref's tail, so `refs/tags/x` would drop the `x^{}` line.
    out = sh("git", "ls-remote", "--tags", "origin", cwd=cwd, quiet=True).stdout
    seen: dict[str, str] = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        name = ref[len("refs/tags/"):-3] if ref.endswith("^{}") else ""
        if name in tags:
            seen[name] = sha
    return seen


def push_release(tags: list[str], cwd: Path = ROOT) -> None:
    head = sh("git", "rev-parse", "HEAD", cwd=cwd, quiet=True).stdout.strip()
    branch = sh("git", "symbolic-ref", "-q", "--short", "HEAD", cwd=cwd, check=False, quiet=True).stdout.strip()
    if branch != "main":
        raise SystemExit(f"✗ a release pushes main by name; HEAD is on {branch or 'a detached commit'}. "
                         "Land the release commit on main first, or rerun with --no-push")
    sh("git", "push", "-q", "origin", "main", cwd=cwd, quiet=True)
    # One push per tag: GitHub creates no push event, so no tag CI and no release zips, for any tag
    # when more than three tags arrive in one push (the 2026-11-09 recovery of four tags hit it).
    for t in tags:
        sh("git", "push", "-q", "origin", f"refs/tags/{t}", cwd=cwd, quiet=True)
    main_line = sh("git", "ls-remote", "origin", "refs/heads/main", cwd=cwd, quiet=True).stdout.split()
    if not main_line or main_line[0] != head:
        raise SystemExit(f"✗ origin main is {main_line[0][:12] if main_line else 'missing'}, not {head[:12]}")
    seen = remote_tags(tags, cwd)
    bad = [t for t in tags if seen.get(t) != head]
    if bad:
        raise SystemExit(f"✗ origin does not hold {', '.join(bad)} at {head[:12]} (read back with ls-remote); "
                         "main is already pushed: rerun the same release command to push the tags again")


def pack_version(pack: str) -> str:
    return json.loads((build.PACKS / pack / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def member_versions_at(ref: str | None) -> dict[str, str]:
    """{member: version} at a git ref (None = working tree)."""
    out = {}
    for pack_dir in sorted(build.PACKS.iterdir()):
        for folder in sorted((pack_dir / "skills").iterdir()) if (pack_dir / "skills").is_dir() else []:
            rel = folder.relative_to(ROOT).as_posix() + "/SKILL.md"
            if ref is None:
                text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).is_file() else ""
            else:
                text = sh("git", "show", f"{ref}:{rel}", check=False, quiet=True).stdout
            m = re.search(r'version:\s*"?([\d.]+)"?', text.split("---")[1]) if text.count("---") >= 2 else None
            if m:
                out[folder.name] = m.group(1)
    return out


def previous_tag(pack: str, exclude: str) -> str | None:
    tags = sh("git", "tag", "-l", f"{pack}-v*", "--sort=-v:refname", check=False, quiet=True).stdout.split()
    tags = [t for t in tags if t != exclude]
    return tags[0] if tags else None


# ---------------------------------------------------------------- the loop

def main() -> int:
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:  # observation 0212: help is read-only, never a run
        print(__doc__)
        return 0
    dry = "--dry-run" in argv
    push = "--no-push" not in argv
    msg = None
    swaps: list[str] = []
    export_dir: Path | None = None
    bumps: dict[str, str] = {}
    it = iter(argv)
    for a in it:
        if a in ("-m", "--message"):
            msg = next(it)
        elif a == "--swaps":
            swaps.append(next(it))
        elif a == "--export-dir":
            export_dir = Path(next(it))
        elif a in ("--dry-run", "--no-push"):
            continue
        elif a.startswith("-"):
            raise SystemExit(f"✗ unknown flag {a!r} — see release.py --help")
        elif "=" in a:
            pack, ver = a.split("=", 1)
            if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
                raise SystemExit(f"✗ {a}: version must be X.Y.Z")
            bumps[pack] = ver
        else:
            raise SystemExit(f"✗ unrecognized argument {a!r}")
    if not bumps:
        raise SystemExit("✗ name at least one pack=X.Y.Z")
    if len(swaps) > 1:
        raise SystemExit("✗ one --swaps dir only (peer definitions retired with the brand member)")

    prev_tags = {p: previous_tag(p, f"{p}-v{v}") for p, v in bumps.items()}
    since = {p: prev_tags[p] or release_notes.default_since() for p in bumps}
    if dry:
        print("dry run — plan:")
        for p, v in bumps.items():
            print(f"  {p}: {pack_version(p)} → {v}  (previous tag {prev_tags[p]})  tag {p}-v{v}")
        print(f"  push: {push} · swaps: {swaps or '—'} · export: {export_dir or '—'}")
        for p in bumps:
            print(f"\n  draft for {p} (commits since {since[p] or 'the start'}):")
            body = release_notes.draft(p, since[p])
            print("\n".join("    " + ln for ln in (body or "(no user-facing commits)").split("\n")))
        return 0

    step(1, "bump-pack")
    for p, v in bumps.items():
        if pack_version(p) == v:
            print(f"  = {p} already at {v}")
        else:
            sh(PY, str(ROOT / "tools" / "build.py"), "--bump-pack", p, v)
        body = release_notes.draft(p, since[p])
        if build._rewrite(ROOT / "CHANGELOG.md",
                          lambda text, tag=f"{p}-v{v}", body=body: release_notes.fill_scaffold(text, tag, body)):
            print(f"  ✓ {p}: CHANGELOG draft written from commits since {since[p] or 'the start'} — review it")

    step(2, "changelog gate")
    clog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for p, v in bumps.items():
        head = f"## [{p}-v{v}]"
        section = release_notes.section(clog, f"{p}-v{v}")
        if section is None:
            raise SystemExit(f"✗ CHANGELOG.md has no heading {head}")
        if release_notes.FILL in section:
            raise SystemExit(f"✗ CHANGELOG.md: write the entry under {head} (it still says '{release_notes.FILL}'), "
                             f"then re-run — bump-pack is idempotent")
        errors, warnings = release_notes.lint(section)
        for w in warnings:
            print(f"  ! {head}: {w}")
        if errors:
            raise SystemExit(f"✗ CHANGELOG.md {head}: " + "; ".join(errors))
    print("  ✓ every new heading has an entry")

    step(3, "build")
    sh(PY, str(ROOT / "tools" / "build.py"))
    if swaps:
        sh(PY, str(ROOT / "tools" / "apply-install-swaps.py"), *swaps)

    step(4, "check")
    sh(PY, str(ROOT / "tools" / "build.py"), "--check")

    step(5, "tests")
    sh(PY, "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py")
    sh(PY, str(ROOT / "tools" / "warden_suites.py"))

    step(6, "commit")
    tags = [f"{p}-v{v}" for p, v in bumps.items()]
    message = msg or f"release: {' + '.join(tags)}"
    sh("git", "add", "-A", quiet=True)
    sh(PY, str(ROOT / "tools" / "pii_scan.py"), "--staged")  # the CHANGELOG is public; armed hook or not
    if sh("git", "diff", "--cached", "--quiet", check=False, quiet=True).returncode == 0:
        print("  = nothing to commit (already committed)")
    else:
        sh("git", "commit", "-q", "-m", message, quiet=True)
        print(f"  ✓ committed: {message}")

    step(7, "tag + push")
    make_tags(tags)
    if push:
        push_release(tags)
        print("  ✓ pushed main + tags, read back from origin — CI attaches the member zips to each Release")
    else:
        print("  --no-push: tags stay local")

    step(8, "zips changed + claude.ai upload list")
    now = member_versions_at(None)
    changed: dict[str, tuple[str, str]] = {}
    for p in bumps:
        prev = prev_tags[p]
        before = member_versions_at(prev) if prev else {}
        for member, ver in now.items():
            if member.startswith(f"revenantworks-{p}-") and before.get(member) != ver:
                changed[member] = (before.get(member, "—"), ver)
    if not changed:
        print("  no member zip changed since the previous tags")
    for member, (b, a) in sorted(changed.items()):
        zip_path = build.DIST / f"{member}-{a}.zip"
        inst = sorted((build.DIST / "install").glob(f"{member}-{a}+install.zip")) if (build.DIST / "install").is_dir() else []
        req = REQUIRED_ON_CLAUDE_AI.get(member)
        flag = "REQUIRED" if req else "optional"
        print(f"  {flag:<8} {member}  {b} → {a}   {inst[0] if inst else zip_path}" + (f"   ({req})" if req else ""))
    print("  claude.ai: Settings → Capabilities → Skills → delete the old copy → Create skill → upload the zip")

    if export_dir:
        step(9, f"export → {export_dir}")
        export_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for z in sorted(build.DIST.glob("*.zip")) + (sorted((build.DIST / "install").glob("*.zip")) if (build.DIST / "install").is_dir() else []):
            shutil.copy2(z, export_dir / z.name); copied.append(z.name)
        lines = [f"claude-skills member zips — built {date.today().isoformat()} · tags: {', '.join(tags)}", "",
                 "Re-upload on claude.ai (Settings → Capabilities → Skills → delete old → Create skill → upload):", ""]
        for member, (b, a) in sorted(changed.items()):
            req = REQUIRED_ON_CLAUDE_AI.get(member)
            inst = [c for c in copied if c.startswith(f"{member}-{a}+install")]
            lines.append(f"  [{'REQUIRED' if req else 'optional'}] {inst[0] if inst else f'{member}-{a}.zip'}"
                         + (f"  — {req}" if req else ""))
        lines += ["", "Every SKILL.md inside these zips carries only the six frontmatter keys claude.ai accepts",
                  "(name, description, license, compatibility, metadata, allowed-tools).", "",
                  "All zips in this folder:"] + [f"  {c}" for c in copied]
        build._write_text(export_dir / "README.txt", "\n".join(lines) + "\n")  # bytes (observation 0220)
        print(f"  ✓ {len(copied)} zip(s) + README.txt")

    print("\nrelease: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
