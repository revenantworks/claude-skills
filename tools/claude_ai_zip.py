#!/usr/bin/env python3
"""claude-skills — build one pack as a claude.ai plugin zip (observation #0690).

claude.ai takes a plugin as one zip holding exactly one plugin.json. A pack with sub-plugins
(gamedev: godot-mcp, gdscript-lsp) carries one manifest per sub-plugin, so `git archive` of the
pack is refused, and stripping the nested manifests by hand dropped the sub-plugins' MCP and LSP
servers: the desktop app lost the Godot MCP after the upload. This is that recipe as a build step.

  - every tracked file under packs/<pack>/, minus each plugins/<sub>/.claude-plugin/ folder;
  - a root .mcp.json and .lsp.json merged from the pack root's own (if any) and each sub-plugin's,
    with `${CLAUDE_PLUGIN_ROOT}/` re-pointed to `${CLAUDE_PLUGIN_ROOT}/plugins/<sub>/`;
  - a refusal on a server name two sources share, and unless exactly one plugin.json remains.

    python tools/claude_ai_zip.py <pack> [--out dist] [--compare <previous.zip>]

--compare lists the previous upload's top-level entries the new zip lacks and exits 1 when any
is missing: diff the whole layout before replacing an upload, not only the manifest.
Stdlib only. Prints paths and counts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = "${CLAUDE_PLUGIN_ROOT}/"


def repoint(value, sub: str):
    """Every string under value with the plugin-root token moved into plugins/<sub>/."""
    if isinstance(value, str):
        return value.replace(TOKEN, f"{TOKEN}plugins/{sub}/")
    if isinstance(value, list):
        return [repoint(v, sub) for v in value]
    if isinstance(value, dict):
        return {k: repoint(v, sub) for k, v in value.items()}
    return value


def tracked(root: Path, pack: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", f"packs/{pack}/"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    prefix = f"packs/{pack}/"
    return sorted(p[len(prefix):] for p in out.split("\0") if p.startswith(prefix))


def merged(root: Path, pack: str, files: list[str], name: str, key: str | None) -> dict:
    """The root config `name` (.mcp.json under key mcpServers, .lsp.json at top level)."""
    servers: dict = {}
    sources = [(f, None) for f in files if f == name]
    sources += [(f, f.split("/")[1]) for f in files
                if f.startswith("plugins/") and f.count("/") == 2 and f.endswith("/" + name)]
    for rel, sub in sources:
        data = json.loads((root / "packs" / pack / rel).read_text(encoding="utf-8"))
        block = data.get(key, {}) if key else data
        for server, cfg in block.items():
            if server in servers:
                raise SystemExit(f"✗ {name}: server {server!r} is defined twice ({rel})")
            servers[server] = repoint(cfg, sub) if sub else cfg
    return servers


def build(pack: str, out: Path, root: Path = ROOT) -> Path:
    pdir = root / "packs" / pack
    manifest = pdir / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        raise SystemExit(f"✗ packs/{pack}: no .claude-plugin/plugin.json")
    version = json.loads(manifest.read_text(encoding="utf-8")).get("version", "0.0.0")
    files = tracked(root, pack)
    keep = [f for f in files if not (f.startswith("plugins/") and "/.claude-plugin/" in f)
            and f not in (".mcp.json", ".lsp.json")]
    mcp = merged(root, pack, files, ".mcp.json", "mcpServers")
    lsp = merged(root, pack, files, ".lsp.json", None)
    manifests = [f for f in keep if f.endswith("plugin.json") and "/.claude-plugin/" in "/" + f]
    if manifests != [".claude-plugin/plugin.json"]:
        raise SystemExit(f"✗ the zip must hold exactly one plugin.json, found {manifests}")
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{pack}-claude-ai-v{version}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in keep:
            z.write(pdir / f, f)
        if mcp:
            z.writestr(".mcp.json", json.dumps({"mcpServers": mcp}, indent=2) + "\n")
        if lsp:
            z.writestr(".lsp.json", json.dumps(lsp, indent=2) + "\n")
    print(f"✓ {dest.relative_to(root) if dest.is_relative_to(root) else dest}: {len(keep)} files, "
          f"{len(mcp)} MCP server(s), {len(lsp)} LSP server(s), one plugin.json")
    return dest


def top_level(zip_path: Path) -> set[str]:
    with zipfile.ZipFile(zip_path) as z:
        return {n.split("/", 1)[0] for n in z.namelist() if n}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # the ✓ and ✗ marks on a Windows console
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--compare", metavar="PREVIOUS_ZIP")
    a = ap.parse_args(argv)
    dest = build(a.pack, Path(a.out))
    if a.compare:
        missing = sorted(top_level(Path(a.compare)) - top_level(dest))
        if missing:
            print(f"✗ the previous upload has top-level entries this zip lacks: {missing}")
            return 1
        print("✓ every top-level entry of the previous upload is present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
