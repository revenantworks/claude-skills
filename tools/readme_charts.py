#!/usr/bin/env python3
"""Draw the README's "skills per pack" chart from the repository's own files, so it never drifts.

Reads each pack's plugin.json (name, version) and counts its member folders under skills/ the
same way tools/build.py does, then writes one SVG per colour scheme under docs/assets/. The
README shows them with <picture> and prefers-color-scheme.

    python tools/readme_charts.py           # write the SVGs
    python tools/readme_charts.py --check   # exit 1 when a committed SVG differs from the data

tools/build.py --check runs the same check. Standard library only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path("docs") / "assets"
STEM = "skills-per-pack"

# Reference palette from the dataviz skill (validated: lightness band, chroma, contrast >= 3:1
# for the bar; text inks clear 4.5:1). One series, so one hue and no legend: the title names it.
THEMES = {
    "light": {"surface": "#fcfcfb", "border": "#e1e0d9", "ink": "#0b0b0b", "ink2": "#52514e", "bar": "#2a78d6"},
    "dark": {"surface": "#1a1a19", "border": "#2c2c2a", "ink": "#f0efec", "ink2": "#c3c2b7", "bar": "#3987e5"},
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

WIDTH = 720
PAD = 24
BAR_X = 208
VALUE_ROOM = 40
ROW_H = 36
BAR_H = 20
TOP = 88


def member_dirs(skills_dir: Path) -> list[str]:
    """Member folders under one pack's skills/ (hidden and _-prefixed skipped), as build.py counts."""
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))


def collect(root: Path) -> list[dict]:
    """One row per pack: name, version and skill count, most skills first, then by name."""
    rows = []
    packs = root / "packs"
    for pdir in sorted(p for p in packs.iterdir() if p.is_dir()) if packs.is_dir() else []:
        manifest = pdir / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            continue
        pj = json.loads(manifest.read_text(encoding="utf-8"))
        rows.append({"name": pj.get("name", pdir.name), "version": pj.get("version", "?"),
                     "skills": len(member_dirs(pdir / "skills"))})
    rows.sort(key=lambda r: (-r["skills"], r["name"]))
    return rows


def render(rows: list[dict], theme: str) -> str:
    """The chart as SVG text: deterministic, so the committed file can be compared byte for byte."""
    t = THEMES[theme]
    total = sum(r["skills"] for r in rows)
    peak = max((r["skills"] for r in rows), default=1) or 1
    span = WIDTH - PAD - VALUE_ROOM - BAR_X
    height = TOP + ROW_H * len(rows) + 36
    title = "Skills per pack"
    sub = f"{total} skills in {len(rows)} packs. Each pack installs as one plugin."
    desc = "; ".join(f"{r['name']} {r['version']}: {r['skills']} skill{'s' if r['skills'] != 1 else ''}" for r in rows)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="100%" '
        f'role="img" aria-labelledby="t d" font-family="{escape(FONT, {chr(34): "&quot;"})}">',
        f'  <title id="t">{escape(title)}: {escape(sub)}</title>',
        f'  <desc id="d">{escape(desc)}.</desc>',
        f'  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="8" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'  <text x="{PAD}" y="40" font-size="17" font-weight="600" fill="{t["ink"]}">{escape(title)}</text>',
        f'  <text x="{PAD}" y="62" font-size="13" fill="{t["ink2"]}">{escape(sub)}</text>',
        f'  <line x1="{BAR_X}" y1="{TOP - 6}" x2="{BAR_X}" y2="{TOP + ROW_H * len(rows) - 10}" '
        f'stroke="{t["border"]}" stroke-width="1"/>',
    ]
    for i, r in enumerate(rows):
        y = TOP + i * ROW_H
        mid = y + BAR_H / 2
        w = round(span * r["skills"] / peak, 1)
        out.append(f'  <text x="{PAD}" y="{mid:g}" dy="0.35em" font-size="14" font-weight="600" '
                   f'fill="{t["ink"]}">{escape(r["name"])}</text>')
        out.append(f'  <text x="{PAD + 100}" y="{mid:g}" dy="0.35em" font-size="12" '
                   f'fill="{t["ink2"]}">v{escape(r["version"])}</text>')
        if w > 0:
            # Square at the baseline, 4px rounded at the data end.
            rr = min(4, w)
            out.append(f'  <path d="M{BAR_X} {y} h{w - rr:g} a{rr} {rr} 0 0 1 {rr} {rr} v{BAR_H - 2 * rr} '
                       f'a{rr} {rr} 0 0 1 -{rr} {rr} h-{w - rr:g} z" fill="{t["bar"]}"/>')
        out.append(f'  <text x="{BAR_X + w + 8:g}" y="{mid:g}" dy="0.35em" font-size="14" font-weight="600" '
                   f'fill="{t["ink"]}">{r["skills"]}</text>')
    out.append(f'  <text x="{PAD}" y="{height - 16}" font-size="11" fill="{t["ink2"]}">'
               f'Drawn by tools/readme_charts.py from packs/*/.claude-plugin/plugin.json and packs/*/skills/</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def sync(root: Path | None = None, write: bool = True) -> list[str]:
    """Write (or, with write=False, only compare) both SVGs. Returns the paths that differed."""
    root = root or ROOT
    rows = collect(root)
    drift = []
    for theme in THEMES:
        rel = ASSETS / f"{STEM}-{theme}.svg"
        path = root / rel
        want = render(rows, theme).encode("utf-8")
        have = path.read_bytes() if path.is_file() else None
        if have != want:
            drift.append(rel.as_posix())
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(want)
    return drift


def _lum(hex_: str) -> float:
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two #rrggbb colours."""
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    drift = sync(ROOT, write=not check)
    for rel in drift:
        print(f"{'drifts' if check else 'wrote'}: {rel}")
    if check:
        print("readme charts:", "DRIFT - run python tools/readme_charts.py" if drift else "clean")
        return 1 if drift else 0
    print(f"readme charts: {len(drift)} file(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
