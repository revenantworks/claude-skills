#!/usr/bin/env python3
"""claude-skills — apply-install-swaps: overlay private config onto neutral members.

The repo ships neutral, and no skill applies a brand (decision 36, 2026-10-01; the
brand-definition swap retired with its member). Two swap surfaces remain, both
optional — put in your swaps dir only what you want to override, and the neutral
value ships for the rest:

  LICENSE               -> every member's LICENSE
  NOTICE                -> every member's NOTICE (beside the LICENSE)
  brand-token.txt       -> every member's `metadata.brand:` value (one line)

Apache-2.0 makes the NOTICE travel with every redistribution, so every install zip
carries one: the swaps dir's NOTICE when it holds one, else the member's own NOTICE
copy (build.py writes it from `packs/<pack>/NOTICE`). The member copy alone never
triggers a zip.

Anyone who wants their own copyright or namespace token on their own install builds
it here: drop a `LICENSE`, `NOTICE` and/or `brand-token.txt` into a private directory of your
own, run this, and upload the zips it writes. The repo never carries it.

Usage:
  python3 tools/apply-install-swaps.py <swaps-dir>

Every member of every pack whose copy changes is zipped to
`dist/install/<member>-<ver>+install.zip`; every other member uploads from its plain
`dist/` zip. A `brand-definition.md` or `prompt-card.md` in a swaps dir is ignored
with a note — both swaps retired. The repo tree is never modified. Stdlib only.
"""
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Same guard build.py carries: this script prints box glyphs, and a Windows console
# defaulting to cp1252 raises UnicodeEncodeError on the success line — AFTER the zip
# is written, so the run looks failed while the artifact is fine. Worse failure mode
# than a plain crash: the operator re-runs, or ships nothing.
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs"
OUT = ROOT / "dist" / "install"

# Overrides that apply to EVERY member. Absent from the swaps dir means
# "keep the neutral value" — never "blank it".
LICENSE_FILE = "LICENSE"
NOTICE_FILE = "NOTICE"
TOKEN_FILE = "brand-token.txt"
RETIRED = {
    "prompt-card.md": "retired 2026-07-23 — branded cards are never stored",
    "brand-definition.md": "retired 2026-10-01 — no skill applies a brand (decision 36)",
}


def apply_global_overrides(work: Path, swaps_dir: Path) -> list[str]:
    """Overlay the swaps dir's LICENSE, NOTICE and namespace token onto one member copy.

    Apache-2.0 section 4(d): a redistribution carries the work's NOTICE, so the NOTICE
    travels beside the LICENSE in every install copy — the swaps dir's NOTICE when it
    holds one, else the member's own NOTICE, which build.py keeps in step with the pack
    NOTICE (unit NM) and the copied folder already carries.

    Returns what changed, so the run reports it rather than doing it silently —
    a build that quietly rewrote your copyright would be worse than one that
    refused to.
    """
    notes = []
    lic = swaps_dir / LICENSE_FILE
    if lic.is_file():
        dest = work / "LICENSE"
        # Bytes, not text: write_text turns LF into CRLF on Windows, so the shipped
        # copy would differ from the file the owner dropped in.
        if dest.is_file() and dest.read_bytes() != lic.read_bytes():
            dest.write_bytes(lic.read_bytes())
            notes.append("LICENSE")
    notice = swaps_dir / NOTICE_FILE
    dest = work / NOTICE_FILE
    if notice.is_file():
        body = notice.read_bytes()
        if not dest.is_file() or dest.read_bytes() != body:
            dest.write_bytes(body)
            notes.append("NOTICE")
    tok = swaps_dir / TOKEN_FILE
    if tok.is_file():
        value = tok.read_text(encoding="utf-8").strip().splitlines()[0].strip() if tok.read_text(encoding="utf-8").strip() else ""
        if value:
            # Bytes in, bytes out: the line's own ending (LF or CRLF) is captured and kept,
            # and write_text's LF -> CRLF translation never runs.
            skill = work / "SKILL.md"
            src = skill.read_bytes().decode("utf-8")
            out, n = re.subn(r"^([ \t]*brand:[ \t]*)\S+[ \t]*(\r?)$",
                             lambda m: m.group(1) + value + m.group(2), src, count=1, flags=re.M)
            if n and out != src:
                skill.write_bytes(out.encode("utf-8"))
                notes.append(f"token -> {value}")
    return notes


def member_version(folder: Path) -> str:
    fm = (folder / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    m = re.search(r'version:\s*"?([\d.]+)"?', fm)
    return m.group(1) if m else "0.0.0"


def members() -> list[Path]:
    """Every member folder of every pack."""
    return sorted(p for p in PACKS.glob("*/skills/*") if (p / "SKILL.md").is_file())


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    swaps_dir = Path(sys.argv[1]).expanduser().resolve()
    if not swaps_dir.is_dir():
        print(f"✗ swaps dir not found: {swaps_dir}")
        return 1

    for fname, why in RETIRED.items():
        if (swaps_dir / fname).is_file():
            print(f"  – ignoring {fname}: {why}")
    if not any((swaps_dir / f).is_file() for f in (LICENSE_FILE, NOTICE_FILE, TOKEN_FILE)):
        print("✗ nothing built — the swaps dir held no LICENSE, NOTICE or brand-token.txt.")
        return 1

    built = 0
    written: set[str] = set()
    OUT.mkdir(parents=True, exist_ok=True)
    for folder in members():
        ver = member_version(folder)
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / folder.name
            shutil.copytree(folder, work)
            notes = apply_global_overrides(work, swaps_dir)
            if not notes:
                continue
            out = OUT / f"{folder.name}-{ver}+install.zip"
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for p in sorted(work.rglob("*")):
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                        z.write(p, Path(folder.name) / p.relative_to(work))
        print(f"  ▣ dist/install/{out.name}  ({', '.join(notes)})")
        written.add(out.name)
        built += 1

    if built == 0:
        print("✗ nothing built — every member already carries the swaps dir's values.")
        return 1

    # skillwright rubric G-3, stale-output detection: a member bump leaves the
    # previous version's zip sitting in dist/install, and an operator can grab the
    # older one. Caught for real on 2026-08-07, when a zip nine versions stale
    # outlived the newer build beside it. Silence from the generator endorsed it.
    stale = sorted(p for p in OUT.glob("*+install.zip") if p.name not in written)
    for p in stale:
        p.unlink()
        print(f"  ✗ dist/install/{p.name} (superseded — removed)")

    print(f"\ninstall zips: {built} built · upload these, not the neutral dist/ zips · repo tree untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
