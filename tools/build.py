#!/usr/bin/env python3
"""claude-skills — multi-pack build: sync, validate, package.

Single source of truth: the pack tables in
packs/foundation/skills/revenantworks-foundation-skillwright/references/pack-registry.md.
Every pack under packs/ is derived from its `**<pack> members**` table there —
no second manifest to drift. The marketplace catalog is cross-checked, not derived.

Validation covers frontmatter identity/description/body limits, CHANGELOG-version
agreement, string-only `metadata` (the Agent Skills spec), and each member's
`volatile.json` (U-7): legal classes, and for calendar-class surfaces a sane cadence,
an existing file, and a dated header stamp.

The routing-seam table rides the same registry pipeline as the roster (1.2.0 item ①):
authored once under `**<pack> seams**`, generated into every member's pack.md, and
boundary-pair checked — both members in the roster, no self-pairs, no empty ownership
or signal cell, no pair declared twice with conflicting ownership, and the table present
and complete in all N manifests.

Usage:
  python3 tools/build.py            sync pack.md -> all members in all packs, validate, build dist/ zips
  python3 tools/build.py --check    CI mode: validate + report drift, write nothing, exit 1 on any problem
  python3 tools/build.py --only revenantworks-foundation-skillwright   limit zip build to one member (sync still runs)
  python3 tools/build.py --bump-pack <pack> <X.Y.Z>   one-stroke version write: marketplace entry +
                                    pack plugin.json + root CHANGELOG scaffold (prevents split-brain bumps)
  python3 tools/build.py --help     usage; reads and writes nothing (an unknown flag exits 2, also writing nothing)
  python3 tools/build.py --bump-member <member> <X.Y.Z> ("<reason>" | -m "<reason>")   one-stroke member write: frontmatter
                                    version + CHANGELOG head ([Unreleased] renamed, else scaffolded with
                                    the reason) + a dated re-anchor on every evals/*.md provenance head
  python3 tools/build.py --parity   diff EVERY shipped file in both installed copies against repo HEAD —
                                    the marketplace clone AND the plugin cache Claude Code actually loads;
                                    exit 1 on drift; skips cleanly when no local install exists (CI-safe)
  python3 tools/build.py --footprint  measured SKILL.md body plus the Load budget's every-run references per
                                    member against its registry budget, plus the pack total; warns past the
                                    budget; report only, writes nothing (manifest drift is reported, not
                                    synced — since 2026-10-01), never fails
  python3 tools/build.py --new-pack <name> --motif <suffix> --profile <standard|standalone>
                                    scaffold an empty pack: plugin.json 0.1.0, marketplace entry, README
                                    stub, registry row and block; idempotent; --check passes with zero members

Added 2026-10-01 (five-pack layout): the `**cross-pack seams**` table and `**planned:**` line render
into both packs' pack.md; the `**featured:**` line generates `featured/<skill>/` one-skill plugins
(the build writes them, --check fails on drift); --check validates native `claude plugin eval` case
folders (evals/<case>/prompt.md + graders/*.md) and warns per pack while members have none; every
write keeps the file's own line ending (observation 0220).

Pack-shared files (owner Q2, 2026-10-01): a file several members carry byte for byte lives once in
`packs/<pack>/shared/<relpath>`, and `shared/holders.json` names its holders. The build writes every
holder's copy; --check fails on a copy that is missing or differs, an unknown holder, an unlisted
source, or a member carrying a shared path it is not listed for. Members keep real copies, so each
still runs and ships alone. First user: localops' GPU seam reference and GPU pre-flight script.

Pack eval folders (unit EVG, 2026-10-01): `claude plugin eval <pack>` refuses an eval dir inside the
plugin's skills/ folder, so the build copies every native case `skills/<member>/evals/<case>/` to
`packs/<pack>/pack-evals/<short>--<case>/` (tracked, so a public install can run the suite). Since
unit K8e the runner also walks every evals/ folder by default, so plugin.json `experimental.evals`
names pack-evals/ and --check fails on a case the runner would discover twice. --check fails on
a missing or drifting copy and on a stale extra folder; --footprint ignores them. Edit the member case.

Validation also covers (added 2026-07-24): pack plugin.json == marketplace entry version
(hard fail — the split-brain class), eval provenance freshness and eval-table orphan
rows (hard fail — flipped 2026-08-07 after the 2.0.0 tag, as promised), description >=1000 chars and
and body footprint. The footprint gate was RESCOPED 2026-07-25: >500 body lines stays a hard fail (the
agentskills.io norm), while the 5k-token figure is this pack's own advisory and now gates on whether the
overage is DECLARED — a member over it must carry a budget {tokens, why}. Undeclared overage hard-fails
(flipped 2026-08-07, the promised next-tag flip); exceeding your own declared budget warns as drift. MOVED 2026-07-27: for a pack
member the budget lives in the registry's `**<pack> budgets**` table, not in frontmatter — frontmatter is
loaded on every invocation, so a `why` there cost 51-95 tokens per run to explain a build-time number.
A registry row costs zero runtime tokens, which is what makes declaring ALL members affordable rather
than only the over-advisory ones. Standalone skills outside a pack keep the frontmatter form.

Stdlib only. Run from the repo root (or anywhere; paths resolve from this file).
"""
import json
import re
import sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import shutil
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs"
DIST = ROOT / "dist"
REGISTRY = PACKS / "foundation" / "skills" / "revenantworks-foundation-skillwright" / "references" / "pack-registry.md"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
# SPDX id written when a plugin or marketplace entry names no licence (owner 2026-10-02: Apache-2.0).
DEFAULT_LICENSE = "Apache-2.0"
FEATURED = ROOT / "featured"  # one-skill plugins generated from the registry's **featured:** line
MODS = ROOT / "mods"  # mod-only plugins (function hooks); never inside a pack, a featured plugin or a zip

# Mode globals. Defaults describe an import (tests, release.py); the command line sets them
# through parse_args() + apply_args() under __main__ only (observation 0212: the old ad-hoc
# sys.argv scan ran a full build for --help or any unknown flag, and took `-m` as a reason).
CHECK = False
ONLY: str | None = None
PARITY = False
BUMP: tuple[str, str] | None = None  # (pack, version)
BUMP_MEMBER: tuple[str, str, str] | None = None  # (member, version, reason)
NEW_PACK: tuple[str, str | None, str | None] | None = None  # (name, motif, profile)
FOOTPRINT = False

USAGE = """build.py [--check] [--footprint] [--only MEMBER]
       build.py --parity
       build.py --bump-pack PACK X.Y.Z
       build.py --bump-member MEMBER X.Y.Z (REASON | -m REASON)
       build.py --new-pack NAME --motif SUFFIX --profile {standard,standalone}"""


def _parser():
    import argparse
    p = argparse.ArgumentParser(
        prog="build.py", usage=USAGE,
        description="claude-skills multi-pack build: sync references/pack.md from the registry, "
                    "validate, package dist/ zips. With no flag it is the REAL build and writes.")
    p.add_argument("--check", action="store_true",
                   help="CI mode: validate and report drift, write nothing, exit 1 on any problem")
    p.add_argument("--footprint", action="store_true",
                   help="measured SKILL.md body plus every-run references per member against its "
                        "registry budget; report only, writes nothing, never fails")
    p.add_argument("--only", metavar="MEMBER", help="limit the zip build to one member (sync still runs)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--parity", action="store_true",
                      help="diff every shipped file in the installed copies against repo HEAD")
    mode.add_argument("--bump-pack", nargs=2, metavar=("PACK", "X.Y.Z"),
                      help="marketplace entry + pack plugin.json + root CHANGELOG scaffold in one stroke")
    mode.add_argument("--bump-member", nargs="+", metavar="MEMBER X.Y.Z [REASON]",
                      help="frontmatter version + CHANGELOG head + eval provenance re-anchor in one "
                           "stroke; the reason is the third value or -m")
    mode.add_argument("--new-pack", metavar="NAME", help="scaffold an empty pack (needs --motif, --profile)")
    p.add_argument("-m", "--message", metavar="REASON", help="the --bump-member reason")
    p.add_argument("--motif", metavar="SUFFIX", help="--new-pack: the member-name suffix, e.g. scribe")
    p.add_argument("--profile", metavar="{standard,standalone}", help="--new-pack: the pack profile")
    return p


def parse_args(argv: list[str]):
    """Parse a command line. `--help` prints usage and exits 0; an unknown flag or a malformed
    mode exits 2 — both before anything is read or written. Normalises bump_member to
    (member, version, reason) and new_pack to (name, motif, profile)."""
    p = _parser()
    ns = p.parse_args(argv)
    if ns.bump_member is not None:
        vals = ns.bump_member
        if len(vals) not in (2, 3):
            p.error("--bump-member takes MEMBER X.Y.Z and a reason (as a third value or -m)")
        if len(vals) == 3 and ns.message is not None:
            p.error("--bump-member: give the reason once — a third value or -m, not both")
        reason = vals[2] if len(vals) == 3 else ns.message
        if not reason or not reason.strip():
            p.error("--bump-member needs a reason (a third value or -m REASON) — it heads the CHANGELOG entry")
        ns.bump_member = (vals[0], vals[1], reason)
    elif ns.message is not None:
        p.error("-m/--message is the --bump-member reason; it has no meaning on its own")
    if ns.new_pack is not None:
        ns.new_pack = (ns.new_pack, ns.motif, ns.profile)
    elif ns.motif is not None or ns.profile is not None:
        p.error("--motif and --profile belong to --new-pack")
    if ns.bump_pack is not None:
        ns.bump_pack = tuple(ns.bump_pack)
    return ns


def apply_args(ns) -> None:
    """Set the mode globals main() reads from a parsed command line."""
    global CHECK, ONLY, PARITY, BUMP, BUMP_MEMBER, NEW_PACK, FOOTPRINT
    CHECK, ONLY, PARITY, FOOTPRINT = ns.check, ns.only, ns.parity, ns.footprint
    BUMP, BUMP_MEMBER, NEW_PACK = ns.bump_pack, ns.bump_member, ns.new_pack


problems: list[str] = []
warnings: list[str] = []
FOOTPRINTS: dict[str, tuple[int, int | None, list[tuple[str, int]]]] = {}  # member -> (body, budget, every-run refs)
COUNTS_FORM_MISSING: list[str] = []  # members whose trigger suite lacks the fixed Counts line (unit OBA)


def fail(msg: str) -> None:
    problems.append(msg)
    print(f"  ✗ {msg}")


def warn(msg: str) -> None:
    """Non-fatal by design: deliberate drift/advisory signals (declared-budget drift,
    seam hygiene, ceiling-riding descriptions). The promised next-tag flips landed
    2026-08-07 — undeclared overage and the two eval-table checks now fail()."""
    warnings.append(msg)
    print(f"  ⚠ {msg}")


def registry_text() -> str:
    return REGISTRY.read_text(encoding="utf-8")


def registry_packs(text: str) -> dict[str, str]:
    """Pack name -> profile, from the Pack registry table."""
    packs = {}
    block = text.split("## Pack registry", 1)[1]
    for line in block.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1) != "Pack":
            packs[m.group(1)] = m.group(2)
    return packs


def registry_pack_notes(text: str, pack: str) -> str:
    """The Notes cell of one pack's row in the Pack registry table.

    Added 2026-08-07 with the second pack. `registry_packs()` captures the *Profile*
    cell only, and `pack_lines()` was handed that as its conformance source — so a pack
    whose conformance line lives (as every pack's does) in its Notes cell never matched
    locally and fell through to a whole-document search, which returns the FIRST pack's
    line. With one pack that was invisible; with two it silently stamped ossuary's
    manifest with foundation's checks and adoption date. Per-pack notes close it, and
    `pack_lines()` no longer searches the whole document.
    """
    block = text.split("## Pack registry", 1)[1]
    for line in block.splitlines():
        m = re.match(rf"\|\s*`{re.escape(pack)}`\s*\|[^|]*\|(.*)\|\s*$", line)
        if m:
            return m.group(1).strip()
    return ""


def _cut(block: str, stops) -> str:
    """The block up to the EARLIEST stop marker in document order.

    The parsers used to take the first stop *in tuple order* that occurred anywhere in the
    block. That held only while no `## ` heading followed the last pack: the 2026-10-01
    `## Cross-pack seams` section made "\\n## " match for foundation's seam table, which then
    swallowed every later pack's seam rows (25 foundation seams for 22 declared). The earliest
    stop is what "the table ends here" means; tuple order was an accident of layout.
    """
    hits = [i for i in (block.find(s) for s in stops) if i >= 0]
    return block[:min(hits)] if hits else block


def pack_members(text: str, pack: str) -> list[tuple[str, str, str]]:
    """(member, job, route) rows from the pack's canonical members table."""
    marker = f"**{pack} members**"
    if marker not in text:
        return []
    block = text.split(marker, 1)[1]
    # Order matters: these are checked in document order, first hit wins. The budgets table
    # (added 2026-07-27) sits between members and seams and its rows are ALSO `member | x | y`,
    # so it matches the roster regex below verbatim — without stopping here first, every budget
    # row was counted as a second roster entry and count integrity read 16 = 16 = 16 for an
    # eight-member pack. The seams table is naturally disjoint (no backticked first cell); this
    # one is not, so the stop is what keeps them apart.
    block = _cut(block, (f"**{pack} budgets**", f"**{pack} seams**", f"**{pack} capstone:**", "\n## ", "\n**"))
    rows = []
    for line in block.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|([^|]+)\|([^|]+)\|", line)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return rows


def pack_budgets(text: str, pack: str) -> dict[str, tuple[int, str]]:
    """{member: (tokens, why)} from the pack's body-footprint table.

    Moved here from each member's `metadata.body_budget` on 2026-07-27. The gate is
    unchanged — a body over the advisory must be DECLARED and JUSTIFIED — but frontmatter
    is loaded on every invocation, so a `why` there cost 51-95 tokens per member per run to
    explain a number no runtime reader acts on. A registry row costs zero runtime tokens,
    which is what makes declaring all N members affordable rather than only the over-limit
    ones. Standalone skills outside a pack keep the frontmatter form: they have no registry.
    """
    marker = f"**{pack} budgets**"
    if marker not in text:
        return {}
    block = text.split(marker, 1)[1]
    # Stops added 2026-10-01 (T2): a pack with an EMPTY budgets table and no seams block (a
    # freshly scaffolded pack) used to read on into the next pack's budgets — scribe's parse
    # returned warden's shieldwarden row. A bare "\n**" stop would cut foundation's table,
    # which has bold prose between its marker and its rows, so the stops are named.
    block = _cut(block, (f"**{pack} seams**", f"**{pack} capstone:**", f"**{pack} canonical repo:**", "\n## "))
    nxt = re.search(r"\n\*\*[\w-]+ (?:members|budgets)\*\*", block)
    block = block[:nxt.start()] if nxt else block
    out = {}
    for line in block.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|([^|]+)\|", line)
        if m:
            out[m.group(1).strip()] = (int(m.group(2)), m.group(3).strip())
    return out


def pack_seams(text: str, pack: str) -> list[tuple[str, str, str, str, str, str]]:
    """(left, right, left-owns, right-owns, signal, cold-listing) rows from the pack's seam table.

    The Seam cell is `left ↔ right` in short wright names and carries no backticks — that
    keeps this table disjoint from the roster and pack-registry parsers above, which both
    key on a backticked first cell.
    """
    marker = f"**{pack} seams**"
    if marker not in text:
        return []
    block = _cut(text.split(marker, 1)[1], ("\n## ", "\n**"))
    rows = []
    for line in block.splitlines():
        m = re.match(r"\|\s*([\w.-]+)\s*↔\s*([\w.-]+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
        if m:
            rows.append(tuple(g.strip() for g in m.groups()))
    return rows


def pack_seam_note(text: str, pack: str) -> str:
    """The note under the seam table (verb overloads, recorded-open seams).

    May run one line or many (a dated list of closures) — captured up to
    the next top-level `**<pack> <word>:**` annotation (capstone, canonical
    repo) or end of text, whichever comes first.
    """
    m = re.search(rf"(\*\*{pack} seam notes:\*\*.+?)(?=\n\n\*\*{pack} \w|\Z)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def registry_planned(text: str) -> dict[str, str | None]:
    """{name: pack or None} from the registry's `**planned:**` line — members named for a
    boundary before their folder exists. An item may carry its future pack: `commscribe (scribe)`.
    `none` (or an empty line) lists nothing."""
    out: dict[str, str | None] = {}
    for m in re.finditer(r"^\*\*planned:\*\*[ \t]*(.*)$", text, re.M):
        for item in m.group(1).split(","):
            im = re.fullmatch(r"\s*`?([A-Za-z][\w.-]*)`?\s*(?:\(\s*([\w-]+)\s*\))?\s*\.?\s*", item)
            if im and im.group(1).lower() != "none":
                out[im.group(1)] = im.group(2)
    return out


def cross_pack_seams(text: str) -> list[tuple[str, str, str]]:
    """(member-a, member-b, line) rows from the registry's `**cross-pack seams**` table.

    One home per pair whose two members live in different packs; the per-pack seam tables
    above hold one pack's members only. Names are short (`skillwright`) or full; the first
    cell is never backticked-and-registered as a pack because `registry_packs` filters on a
    folder or a roster existing.
    """
    marker = "**cross-pack seams**"
    if marker not in text:
        return []
    block = _cut(text.split(marker, 1)[1], ("\n## ", "\n**"))
    rows = []
    for line in block.splitlines():
        m = re.match(r"\|\s*`?([A-Za-z][\w.-]*)`?\s*\|\s*`?([A-Za-z][\w.-]*)`?\s*\|([^|]*)\|\s*$", line)
        if m and m.group(1) not in ("Member", "Seam"):
            rows.append((m.group(1), m.group(2), m.group(3).strip()))
    return rows


def _resolve_member(name: str, rosters: dict[str, list[str]]) -> list[tuple[str, str]]:
    return [(p, m) for p, ms in rosters.items() for m in ms if m == name or m.endswith(f"-{name}")]


def validate_cross_pack(rows, rosters: dict[str, list[str]], planned: dict[str, str | None]):
    """Resolve and check every cross-pack row. Returns the sound rows as
    ((pack, member, short, is_planned), (pack, member, short, is_planned), line).

    Fails a row naming a member that is neither registered in some pack's roster nor on the
    `**planned:**` line, an ambiguous short name, a self-pair, a pair whose two sides sit in
    one pack (that row belongs in the pack's own seam table), an empty line cell, and a pair
    declared twice. Warns on a planned name that is now registered (drop it from the line).
    """
    for name in planned:
        if _resolve_member(name, rosters):
            warn(f"cross-pack: {name!r} is on the **planned:** line but is now registered — drop it from the line")
    resolved, seen = [], set()
    for a, b, line in rows:
        label = f"{a} ↔ {b}"
        sides, ok = [], True
        for x in (a, b):
            hits = _resolve_member(x, rosters)
            if len(hits) == 1:
                sides.append((hits[0][0], hits[0][1], hits[0][1].rsplit("-", 1)[-1], False))
            elif hits:
                fail(f"cross-pack seam {label}: {x!r} is ambiguous across the rosters ({', '.join(m for _, m in hits)})")
                ok = False
            elif x in planned:
                sides.append((planned[x], x, x, True))
            else:
                fail(f"cross-pack seam {label}: {x!r} is neither a registered member nor named on the "
                     f"**planned:** line")
                ok = False
        if not ok:
            continue
        (pa, ma, _, _), (pb, mb, _, _) = sides
        if ma == mb:
            fail(f"cross-pack seam {label}: one member on both sides — not a boundary pair")
            continue
        if pa is not None and pa == pb:
            fail(f"cross-pack seam {label}: both members are in the {pa} pack — the row belongs in **{pa} seams**")
            continue
        if not line.strip("* "):
            fail(f"cross-pack seam {label}: empty line cell — a seam row must say where the boundary runs")
            continue
        pair = frozenset((ma, mb))
        if pair in seen:
            fail(f"cross-pack seam {label}: pair declared twice — one home per pair")
            continue
        seen.add(pair)
        resolved.append((sides[0], sides[1], line))
    return resolved


def cross_rows_for(pack: str, resolved) -> list[tuple[str, str, str]]:
    """(this-pack member, other side label, line) for every sound cross-pack row that has a
    registered member in `pack` — the same row renders into both packs' manifests."""
    out = []
    for a, b, line in resolved:
        for this, other in ((a, b), (b, a)):
            if this[0] == pack and not this[3]:
                if other[3]:
                    where = f"{other[0]}, planned" if other[0] else "planned"
                else:
                    where = other[0]
                out.append((this[2], f"{other[2]} ({where})", line))
                break
    return out


DEFAULT_CHECKS = ("2026-07-13", "C-1 drift-audit verb · C-2 neutral default")


def pack_lines(text: str, pack: str, pack_notes: str) -> tuple[str, str, tuple[str, str]]:
    """Capstone, repo, and conformance lines for one pack (graceful when absent).

    `pack_notes` is this pack's OWN Notes cell (see registry_pack_notes). The former
    whole-document fallback is gone: it made a missing per-pack line resolve to some
    other pack's, which is worse than a stated default.
    """
    cap_m = re.search(rf"\*\*{pack} capstone:\*\*(.+)", text)
    cap = cap_m.group(1).strip() if cap_m else "—"
    repo_m = re.search(rf"\*\*{pack} canonical repo:\*\*\s*(`[^`]+`)", text)
    repo = repo_m.group(1) if repo_m else "the registered canonical repo"
    conf = re.search(r"Conformance checks \(([\d-]+)\): ([^|.]+)", pack_notes)
    checks = conf.group(2).strip() if conf else DEFAULT_CHECKS[1]
    adopted = conf.group(1) if conf else DEFAULT_CHECKS[0]
    return cap, repo, (adopted, checks)


def render_pack_md(pack: str, profile: str, members, cap, repo, conf, seams=(), seam_note="", cross=(),
                   planned=None) -> str:
    adopted, checks = conf
    n_word = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
              8: "eight", 9: "nine", 10: "ten"}.get(len(members), str(len(members)))
    rows = "\n".join(f"| `{m}` | {j} | {r} |" for m, j, r in members)
    roster = [m for m, _, _ in members]

    def side(short: str) -> str:  # a planned member with no folder yet renders as planned (M2 gap)
        registered = any(m == short or m.endswith(f"-{short}") for m in roster)
        return f"{short} (planned)" if not registered and short in (planned or {}) else short
    seam_block = ""
    if seams:
        seam_rows = "\n".join(f"| {side(l)} ↔ {side(r)} | {lo} | {ro} | {sig} | {cold} |"
                              for l, r, lo, ro, sig, cold in seams)
        seam_block = (
            "\n**Routing seams** — one row per boundary pair: what each side owns, and the signal that "
            "decides. Same advisory standing as the roster; a row reading *none — table only* is a seam "
            "the cold listing cannot decide, recorded here rather than claimed.\n\n"
            "| Seam | Left owns | Right owns | Router keys on | Cold-listing signal |\n"
            "|---|---|---|---|---|\n"
            f"{seam_rows}\n"
            + (f"\n{seam_note}\n" if seam_note else "")
        )
    if cross:
        cross_rows = "\n".join(f"| {t} | {o} | {ln} |" for t, o, ln in cross)
        seam_block += (
            "\n**Cross-pack seams** — boundaries with members of other packs, authored once in the "
            "registry's cross-pack table and rendered into both packs. A *planned* member is named for "
            "the boundary it will have; it is not built yet.\n\n"
            "| Member | Other side (pack) | Line |\n"
            "|---|---|---|\n"
            f"{cross_rows}\n"
        )
    return f"""# Pack — {pack} *({profile} profile)*

> Advisory only — consulted on boundary doubt; initial routing stays at the name + description level. **Last stamped: {date.today().isoformat()}** ({n_word}-member roster + canonical repo; generated from the registry in skillwright's `pack-registry.md`).

| Member | Job | Route there when |
|---|---|---|
{rows}
{seam_block}
**Pack conformance checks** (adopted {adopted}, scored on every member audit): **{checks.replace(' · ', '** · **')}**.

**Canonical repo:** {repo} — pack source of truth for drift audits (registered in skillwright's `pack-registry.md`; subject to relocation — the registry row is authoritative).

**Capstone:** {cap}

**Absence rule:** recommend an uninstalled sibling by name — never fail the task over it. When the job leaves the pack for material no member carries (engine or API reference, a third-party set), name one default — the official docs first, then a named set — and say plainly whether that set is installed; never imply an unadopted tool is present.
"""


NUM_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}


def _count_word(word: str) -> int | None:
    return int(word) if word.isdigit() else NUM_WORDS.get(word.lower())


def validate_registry_counts(text: str, pack: str, rosters: dict[str, list[str]]) -> None:
    """Observation 0227: numbers the registry states about a pack, checked against the pack.

    - The capstone line's "a N-member pack" / "N-member roster" must equal the roster size.
    - Its "all N members" must equal the roster plus any other pack's registered members the
      line names (a capstone may drive a member across packs, as the Workbench Run does).
    - Quoted text ("the line read \\"…\\"") is history and is not checked.
    - Every budget row must name a roster member (fail: a stale row outlived its member);
      a roster member with no row warns (the gate then falls back to the 5k advisory).
    """
    roster = rosters.get(pack, [])
    cap_m = re.search(rf"\*\*{re.escape(pack)} capstone:\*\*(.+)", text)
    if cap_m:
        cap = re.sub(r"\"[^\"]*\"|“[^”]*”", "", cap_m.group(1))
        named = [m for p, ms in rosters.items() if p != pack for m in ms
                 if re.search(rf"\b{re.escape(m.rsplit('-', 1)[-1])}\b", cap)]
        for mm in re.finditer(r"(?i)\b(\w+)-member\s+(?:pack|roster)\b", cap):
            n = _count_word(mm.group(1))
            if n is not None and n != len(roster):
                fail(f"[{pack}] capstone line says '{mm.group(0)}' but the roster has {len(roster)} — "
                     f"update the line with the roster (observation 0227)")
        for mm in re.finditer(r"(?i)\ball\s+(\w+)\s+members\b", cap):
            n = _count_word(mm.group(1))
            want = len(roster) + len(named)
            if n is not None and n != want:
                fail(f"[{pack}] capstone line says '{mm.group(0)}' but the roster has {len(roster)}"
                     + (f" plus {len(named)} named across packs ({', '.join(named)})" if named else "")
                     + " — update the line with the roster (observation 0227)")
    budgets = pack_budgets(text, pack)
    for member in budgets:
        if member not in roster:
            fail(f"[{pack}] budget row for {member}, which is not in the {pack} roster — drop or move "
                 f"the row with the member (observation 0227)")
    for member in roster:
        if member not in budgets:
            warn(f"[{pack}] {member}: no budget row in **{pack} budgets** — declare one (it costs no "
                 f"runtime tokens); until then the body is held to the 5k advisory")


SEAM_SIGNALS = ("both descriptions", "one description", "none — table only")


def validate_seams(pack: str, members: list[str], seams, planned: dict[str, str | None] | None = None) -> None:
    """Boundary-pair check (1.2.0 item ①): every declared seam is structurally sound.

    Fails on a seam naming a member the pack does not have, a row pairing a member with
    itself, an empty ownership or signal cell, an unknown cold-listing value, and the same
    pair declared twice with conflicting ownership — one home per pair, as for every other
    surface the registry owns. Warns on a redundant duplicate row, a member no row mentions,
    and on `none — table only`: the recorded marker for a seam whose signal no description
    carries, which the cold listing therefore cannot route. That warn is instrumentation,
    not a defect to silence — the seam stays visible until a description claims it.
    """
    if not seams:
        if len(members) > 1:
            warn(f"[{pack}]: no routing-seam table (**{pack} seams**) for {len(members)} members — "
                 f"every boundary pair is unrecorded")
        return

    planned = planned or {}

    def resolve(short: str) -> str | None:
        hits = [m for m in members if m == short or m.endswith(f"-{short}")]
        if len(hits) == 1:
            return hits[0]
        if hits:
            fail(f"[{pack}] seam member {short!r}: ambiguous in the pack roster")
            return None
        # The M2 gap (2026-10-01): a member named for a boundary before its folder exists may
        # sit in its own pack's seam table when the registry's **planned:** line lists it; it
        # renders as planned. One planned for another pack belongs in the cross-pack table.
        if short in planned:
            if planned[short] not in (None, pack):
                fail(f"[{pack}] seam member {short!r} is planned for the {planned[short]} pack — "
                     f"the row belongs in the cross-pack seams table")
                return None
            return short
        fail(f"[{pack}] seam member {short!r} is neither in the pack roster nor named on the "
             f"**planned:** line")
        return None

    seen: dict[frozenset, tuple[dict[str, str], str]] = {}
    covered: set[str] = set()
    for left, right, lo, ro, sig, cold in seams:
        a, b = resolve(left), resolve(right)
        label = f"{left} ↔ {right}"
        if not a or not b:
            continue
        if a == b:
            fail(f"[{pack}] seam {label}: one member on both sides — not a boundary pair")
            continue
        covered |= {a, b}
        for cell, what in ((lo, "left-ownership"), (ro, "right-ownership"), (sig, "router-signal")):
            if not cell.strip("* "):
                fail(f"[{pack}] seam {label}: empty {what} cell — a seam missing it decides nothing")
        norm = cold.strip("* ").lower()
        if norm not in SEAM_SIGNALS:
            fail(f"[{pack}] seam {label}: cold-listing signal {cold!r} not one of {SEAM_SIGNALS}")
        elif norm == "none — table only":
            warn(f"[{pack}] seam {label}: cold-listing signal 'none — table only' — no description "
                 f"carries the signal, so the listing cannot route this pair; recorded open, not closed")
        pair, owns = frozenset((a, b)), {a: lo, b: ro}
        if pair in seen:
            prior_owns, prior_label = seen[pair]
            if prior_owns != owns:
                fail(f"[{pack}] seam {label}: pair already declared as {prior_label} with different "
                     f"ownership — one home per pair")
            else:
                warn(f"[{pack}] seam {label}: duplicate of {prior_label} — redundant row")
        else:
            seen[pair] = (owns, label)
    for m in members:
        if m not in covered:
            warn(f"[{pack}] {m}: named in no routing seam — every edge uncontested, or unrecorded?")


COLD_NAMES = {"both descriptions": 2, "one description": 1, "none": 0}


def validate_cold_listing(pack: str, left: str, right: str, cell: str, descs: dict[str, str]) -> None:
    """A seam's cold-listing cell, checked against the live descriptions (unit OBA).

    The cell says how many of the pair's two descriptions carry the signal; the check counts how
    many name the other member by its short name. A fix round once wrote cells with the sides
    backwards and 19 had drifted before a registry pass caught them, so the cell is re-derived on
    every `--check`. An in-pack cell is the whole value; a cross-pack row is prose, read from its
    `Cold-listing` marker, and a row with no marker or with a planned (folderless) member is skipped.
    """
    m = re.search(r"cold-listing.{0,30}?(both descriptions|one description|none)", cell, re.I) \
        if "cold-listing" in cell.lower() else \
        re.fullmatch(r"\s*\**\s*(both descriptions|one description|none)\b.*", cell, re.I | re.S)
    if not m:
        return

    def full(short: str) -> str | None:
        hits = [d for d in descs if d == short or d.endswith(f"-{short}")]
        return hits[0] if len(hits) == 1 else None

    a, b = full(left), full(right)
    if not a or not b:
        return
    a_short, b_short = a.rsplit("-", 1)[-1], b.rsplit("-", 1)[-1]
    named = (int(bool(re.search(rf"\b{re.escape(b_short)}\b", descs[a])))
             + int(bool(re.search(rf"\b{re.escape(a_short)}\b", descs[b]))))
    want = COLD_NAMES[m.group(1).lower()]
    if named != want:
        fail(f"[{pack}] seam {left} ↔ {right}: cold-listing cell says {m.group(1)!r} but {named} of 2 "
             f"descriptions name the other member — re-read both descriptions and fix the cell")


def validate_script_declarations(pack: str, notes: str, folder: Path) -> None:
    """A pack rule that requires each script to be declared in named places, checked (unit OBA).

    Read from the pack row's Notes: when they say scripts are allowed when declared, every shipped
    script (`scripts/*.py`, tests and `_`-prefixed helpers excepted) must be named in the README and,
    where the rule names it, in the SKILL.md `## Load budget` section. The `compatibility:` field
    has a 500-character cap, so it may summarise ("runs the stdlib scripts"), but must mention them.
    """
    if not re.search(r"scripts?\b[^.|]*\bdeclared|declared[^.|]*\bscripts?\b", notes, re.I):
        return
    sdir = folder / "scripts"
    scripts = sorted(p.name for p in sdir.glob("*.py")
                     if not p.name.startswith(("test_", "_"))) if sdir.is_dir() else []
    if not scripts:
        return
    skill = (folder / "SKILL.md").read_text(encoding="utf-8")
    parts = skill.split("---", 2)
    fm, body = (parts[1], parts[2]) if len(parts) == 3 else ("", skill)
    readme_p = folder / "README.md"
    places: list[tuple[str, str]] = []
    if "readme" in notes.lower():
        places.append(("README.md", readme_p.read_text(encoding="utf-8") if readme_p.is_file() else ""))
    if "load budget" in notes.lower():
        lb = re.search(r"^## Load budget\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
        places.append(("the SKILL.md Load budget", lb.group(1) if lb else ""))
    for where, text in places:
        missing = [s for s in scripts if s not in text]
        if missing:
            fail(f"[{pack}] {folder.name}: {', '.join(missing)} not named in {where} — the pack rule "
                 f"declares every script there")
    if "compatibility" in notes.lower():
        comp = re.search(r"^compatibility:\s*(.*)$", fm, re.M)
        named = comp and ("script" in comp.group(1).lower() or any(s in comp.group(1) for s in scripts))
        if not named:
            fail(f"[{pack}] {folder.name}: ships {len(scripts)} script(s) but its compatibility field "
                 f"never mentions scripts — the pack rule declares them there")


def validate_seam_manifest(folder: Path, n_seams: int) -> None:
    """Item ①'s single-home half: the seam table is authored once in the registry and
    generated into every member, so every member's pack.md must carry all of it."""
    if not n_seams:
        return
    target = folder / "references" / "pack.md"
    if not target.is_file():
        fail(f"{folder.name}: no references/pack.md to carry the routing-seam table")
        return
    text = target.read_text(encoding="utf-8")
    if "**Routing seams**" not in text:
        fail(f"{folder.name}: references/pack.md carries no routing-seam table (regenerate from the registry)")
        return
    rows = sum(1 for ln in text.splitlines()
               if re.match(r"\|\s*[\w.-]+(?: \(planned\))?\s*↔\s*[\w.-]+(?: \(planned\))?\s*\|", ln))
    if rows != n_seams:
        fail(f"{folder.name}: references/pack.md carries {rows} seam row(s), registry declares {n_seams}")


def _slug(heading: str) -> str:
    """GitHub-style heading slug: lowercase, markup and punctuation dropped (hyphens and
    underscores kept), spaces to hyphens."""
    text = re.sub(r"[`*_~]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", heading.strip().lower())
    return re.sub(r"\s", "-", re.sub(r"[^\w\- ]", "", text))


def _anchor_line(lines: list[str], frag: str) -> int | None:
    """Index of the line that `#frag` resolves to — a heading whose slug matches, a heading
    carrying an explicit `{#frag}`, or an `<a id|name="frag">` tag — else None."""
    frag = frag.strip().lower()
    for i, ln in enumerate(lines):
        h = re.match(r"\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", ln)
        if h:
            explicit = re.search(r"\{#([\w-]+)\}\s*$", h.group(1))
            if (explicit and explicit.group(1).lower() == frag) or _slug(h.group(1)) == frag:
                return i
        if re.search(rf"<a\s+(?:id|name)=[\"']{re.escape(frag)}[\"']", ln, re.I):
            return i
    return None


VOLATILE_FILE = "volatile.json"  # beside SKILL.md; owner decision M3, 2026-10-08
_VOLATILE_KEYS = ("file", "class", "cadence_days")


def validate_volatile(folder: Path) -> None:
    """U-7: validate the member's `volatile.json` (a JSON list beside SKILL.md).

    Moved out of frontmatter `metadata.volatile` by owner decision M3 (2026-10-08): the
    Agent Skills spec types `metadata` as a string-to-string map, and the nested list broke it.
    Rules: the file must exist (uniform layer — `[]` for none); it holds a list of objects
    with `file` + `class` (calendar | event-driven) and no other key but `cadence_days`;
    the referenced file must exist. Calendar entries additionally need an integer
    cadence_days (7-365) and a dated header stamp (Last verified: YYYY-MM-DD) in the
    file's first lines; event-driven entries must not carry cadence_days.
    """
    vf = folder / VOLATILE_FILE
    if not vf.is_file():
        fail(f"{folder.name}: {VOLATILE_FILE} missing (uniform layer requires it beside SKILL.md — [] for none)")
        return
    try:
        entries = json.loads(vf.read_text(encoding="utf-8"))
    except ValueError as e:
        fail(f"{folder.name}: {VOLATILE_FILE} is not valid JSON ({e})")
        return
    if not isinstance(entries, list):
        fail(f"{folder.name}: {VOLATILE_FILE} must be a JSON list of {{file, class, cadence_days?}} ([] for none)")
        return
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not isinstance(e.get("file"), str):
            fail(f"{folder.name}: {VOLATILE_FILE} entry {i} must be an object with a string \"file\"")
            continue
        extra = sorted(set(e) - set(_VOLATILE_KEYS))
        if extra:
            fail(f"{folder.name}: volatile {e['file']}: unknown key(s) {', '.join(extra)} "
                 f"(allowed: {', '.join(_VOLATILE_KEYS)})")
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("file"), str):
            continue
        ref, cls = e["file"], e.get("class")
        if cls not in ("calendar", "event-driven"):
            fail(f"{folder.name}: volatile {ref}: class {cls!r} not calendar|event-driven")
            continue
        # Observation 0221: a pointer may name a section, `file.md#anchor` (the audit template's
        # parity-register row writes one). Strip the anchor for the file check, then confirm a
        # heading (or an explicit {#id} / <a id|name>) with that slug exists.
        path, _, frag = ref.partition("#")
        target = folder / path
        if not target.is_file():
            fail(f"{folder.name}: volatile {ref}: declared file does not exist")
            continue
        section_at = None
        if frag:
            section_at = _anchor_line(target.read_text(encoding="utf-8").splitlines(), frag)
            if section_at is None:
                fail(f"{folder.name}: volatile {ref}: {path} has no heading or anchor for #{frag}")
                continue
        if cls == "event-driven":
            if "cadence_days" in e:
                fail(f"{folder.name}: volatile {ref}: event-driven must not carry cadence_days")
            continue
        # calendar
        cad = e.get("cadence_days")
        if not (type(cad) is int and 7 <= cad <= 365):  # a JSON integer: not "90", not true, not 90.0
            fail(f"{folder.name}: volatile {ref}: calendar cadence_days {cad!r} not a sane integer (7-365)")
        # Stamp may sit at the file head (model-snapshot, measurement, platform-notes)
        # or at the head of the file's volatile *section* (rubrics.md ~line 18) —
        # 40 lines covers both; the strict "Last …:" form avoids prose dates.
        # With an anchor, the section's own head (40 lines from its heading) also counts.
        flines = target.read_text(encoding="utf-8").splitlines()
        head = "\n".join(flines[:40] + (flines[section_at:section_at + 40] if section_at is not None else []))
        # One grammar only: "Last verified:" — matches the Cowork upkeep task's grep exactly.
        # (Narrowed 2026-07-24 from verified|restamped|stamped; all four calendar
        # files already used the strict form, so this was a zero-content-change tightening.)
        stamp = re.search(r"Last verified:\s*(\d{4}-\d{2}-\d{2})", head)
        if not stamp:
            fail(f"{folder.name}: volatile {ref}: calendar file has no dated header stamp")
        else:
            try:
                d = date.fromisoformat(stamp.group(1))
                if d > date.today():
                    fail(f"{folder.name}: volatile {ref}: stamp {stamp.group(1)} is in the future")
            except ValueError:
                fail(f"{folder.name}: volatile {ref}: stamp {stamp.group(1)!r} is not a valid date")


_YAML_NON_STRING = re.compile(  # plain scalars a YAML loader types as int/float/bool/null/date
    r"^(?:[-+]?(?:0|[1-9][0-9_]*|0x[0-9a-fA-F_]+|0o?[0-7_]+)"
    r"|[-+]?(?:\.[0-9]+|[0-9][0-9_]*(?:\.[0-9_]*)?)(?:[eE][-+]?[0-9]+)?"
    r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)"
    r"|(?i:true|false|yes|no|on|off|y|n|null)|~"
    r"|\d{4}-\d{1,2}-\d{1,2}(?:[Tt ].*)?)$")


def validate_metadata_strings(folder: Path, fm: str) -> None:
    """Owner decision M3 (2026-10-08): `metadata` holds string values only.

    The Agent Skills spec (agentskills.io/specification) defines `metadata` as "A map from
    string keys to string values". A nested list or map (the old `metadata.volatile` block,
    a frontmatter `body_budget`) or a plain scalar a YAML loader types as a number, boolean,
    null or date fails, so the shape cannot come back. Stdlib parse; no yaml needed.
    """
    lines = fm.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^metadata:", ln)), None)
    if start is None:
        return
    inline = lines[start][len("metadata:"):].split(" #")[0].strip()
    if inline and inline != "{}":
        fail(f"{folder.name}: metadata must be a block map of string values (found inline {inline!r})")
        return
    hints = {"volatile": " — the volatile list lives in volatile.json beside SKILL.md",
             "body_budget": " — a member's body budget lives in the registry's budgets table"}
    key_indent, key, block_scalar, flagged = None, None, False, set()

    def bad(k: str, what: str) -> None:
        if k not in flagged:
            flagged.add(k)
            fail(f"{folder.name}: metadata.{k} is {what} — the Agent Skills spec allows string values "
                 f"only under metadata (quote a scalar){hints.get(k, '')}")

    for ln in lines[start + 1:]:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        indent = len(ln) - len(ln.lstrip(" "))
        if indent == 0:
            break  # the next top-level key
        if key_indent is None:
            key_indent = indent
        if indent > key_indent:
            if key is not None and not block_scalar:
                bad(key, "a nested list or map")
            continue
        if ln.lstrip().startswith("-"):
            bad(key or "(top)", "a list")
            continue
        m = re.match(r"^\s+([^\s:#][^:]*?):(?:\s+(.*?))?\s*$", ln)
        if indent < key_indent or not m:
            bad(ln.strip()[:30], "not a `key: value` line")
            key, block_scalar = None, False
            continue
        key, raw = m.group(1).strip(), (m.group(2) or "")
        block_scalar = raw[:1] in ("|", ">")
        value = raw if raw[:1] in ('"', "'") else raw.split(" #")[0].strip()
        if block_scalar or value[:1] in ('"', "'"):
            continue
        if not value:
            bad(key, "empty (null) or a nested list or map")
        elif value[:1] in ("[", "{"):
            bad(key, "a flow list or map")
        elif value[:1] in ("&", "*", "!"):
            bad(key, "an anchor, alias or tag")
        elif _YAML_NON_STRING.match(value):
            bad(key, f"a non-string scalar ({value})")


FOOTPRINT_ADVISORY = 5000  # house advisory, not a spec limit; see validate_skill


_EVERY_RUN = re.compile(r"\bevery\s+(?:run|mode|entry)\b", re.I)
_EVERY_RUN_NEGATED = re.compile(r"\b(?:not|never)\b(?:\W+\w+){0,3}?\W+every\s+(?:run|mode|entry)\b", re.I)
_FILE_TICK = re.compile(r"`([^`\s]+\.(?:md|py|json|ya?ml|txt|csv))`")


def _load_budget_units(section: str) -> tuple[list[str], list[list[str]]]:
    """Split a Load budget section into prose units and table rows.

    Units: each bullet (with its continuation lines) is one unit; a prose paragraph is joined
    across its wrapped lines and cut into sentences and `;` clauses, so a file named in the next
    sentence never rides on this one's "every run". Table rows are returned as cell lists, the
    header and the `|---|` separator dropped."""
    units: list[str] = []
    rows: list[list[str]] = []
    for para in re.split(r"\n\s*\n", section):
        lines = para.strip().splitlines()
        if not lines:
            continue
        if lines[0].lstrip().startswith("|"):
            body = [ln for ln in lines if ln.lstrip().startswith("|")]
            for ln in body[1:]:  # body[0] is the header row
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
            continue
        bullets: list[str] = []
        for ln in lines:
            if re.match(r"\s*[-*]\s+", ln) or not bullets:
                bullets.append(ln)
            else:
                bullets[-1] += " " + ln.strip()
        for chunk in bullets:
            if re.match(r"\s*[-*]\s+", chunk):
                units.append(chunk)
            else:
                units.extend(s for s in re.split(r"(?<=[.;!?])\s+", chunk) if s.strip())
    return units, rows


def every_run_refs(folder: Path) -> list[tuple[str, int]]:
    """[(path, tokens)] for the files EVERY entry of a member reads on every run (observation
    0223; owner answer to P1b's open question, 2026-10-01).

    The rubric counts a file every entry point reads as body, but --footprint measured SKILL.md
    alone (pixelsmith: body ≈2400 of a 3500 budget, real load ≈4800 with `band-rules.md`). The
    member's `## Load budget` section is read in whatever form it states the rule:

        - `references/band-rules.md` — every run: the per-band rules      (bullet)
        Every run touches `eval-doctrine.md`. Open `claim-cases.md` on…    (prose sentence)
        `references/verification.md` on every run, plus the entry's files (clause)
        Every mode reads `references/dangerous-shapes.md` before…         (every mode / entry)
        | Entry | Reads |  — a file named in every row (outside a parenthesis) (entry table)

    A sentence, `;` clause or bullet that says "every run", "every mode" or "every entry"
    (and does not negate it) counts the backticked files in that unit only. A file read by
    only some entries is conditional and does not count: the budget row bounds the load every
    run pays, not the heaviest optional read. The declaration is body text the member already
    carries, so it costs no extra runtime tokens. A bare file name means `references/`. Tokens
    are chars/4, the body's own estimate. A named file that does not exist warns.
    """
    sk = folder / "SKILL.md"
    if not sk.is_file():
        return []
    m = re.search(r"^## Load budget[^\n]*\n(.*?)(?=^## |\Z)", _read(sk), re.M | re.S)
    units, rows = _load_budget_units(m.group(1) if m else "")
    named: list[str] = []
    for u in units:
        if _EVERY_RUN.search(u) and not _EVERY_RUN_NEGATED.search(u):
            named += _FILE_TICK.findall(u)
    if len(rows) >= 2:
        per_row = [set(_FILE_TICK.findall(re.sub(r"\([^)]*\)", "", " | ".join(r[1:])))) for r in rows]
        common = set.intersection(*per_row)
        named += [f for f in _FILE_TICK.findall(" ".join(" ".join(r[1:]) for r in rows)) if f in common]
    out: list[tuple[str, int]] = []
    seen: set[str] = set()
    for raw in named:
        rel = raw.strip()
        rel = rel if "/" in rel else f"references/{rel}"
        if rel in seen:
            continue
        seen.add(rel)
        p = folder / rel
        if p.is_file():
            out.append((rel, len(_read(p)) // 4))
        else:
            warn(f"{folder.name}: Load budget lists `{rel}` as read every run, but the file does not exist")
    return out


def validate_skill(folder: Path, budget: tuple[int, str] | None = None) -> str | None:
    """Return the member's version, recording problems as we go."""
    sk = folder / "SKILL.md"
    if not sk.exists():
        fail(f"{folder.name}: no SKILL.md")
        return None
    text = sk.read_text(encoding="utf-8")
    parts = text.split("---")
    if len(parts) < 3:
        fail(f"{folder.name}: no frontmatter block")
        return None
    fm = parts[1]
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    ver = re.search(r'version:\s*"?([\d.]+)"?', fm)
    if not name or name.group(1) != folder.name:
        fail(f"{folder.name}: frontmatter name != folder name")
    if name and len(name.group(1)) > 64:
        fail(f"{folder.name}: name > 64 chars")
    # The only two frontmatter limits confirmed against a real upload error, so the only
    # two the gate asserts. `compatibility` past 500 chars was rejected by the live
    # claude.ai upload form on 2026-08-14 (ossuary-v2.2.2 — bonecaller 533, linecaller
    # 667). `description` is deliberately NOT bounded here beyond the house ceiling
    # below: the pack twice trimmed it on an assumed 500 that two real uploads never
    # reproduced (ossuary-v2.2.3), and a guessed number in the gate institutionalizes
    # that mistake. Fail rather than upload-fail; the tightest live margin is 463/500.
    compat = re.search(r"^compatibility:\s*(.+)$", fm, re.M)
    if compat and len(compat.group(1)) > 500:
        fail(f"{folder.name}: compatibility {len(compat.group(1))} chars > 500 — the live upload "
             f"form rejects this field past 500 (confirmed 2026-08-14)")
    if not desc:
        fail(f"{folder.name}: no description")
    elif len(desc.group(1)) > 1024:  # characters, not bytes — multibyte punctuation overreads byte counters
        fail(f"{folder.name}: description {len(desc.group(1))} chars > 1024 (house ceiling, not the platform cap)")
    elif len(desc.group(1)) >= 1000:
        warn(f"{folder.name}: description {len(desc.group(1))}/1024 chars — ceiling-riding, zero edit headroom "
             f"(8 maxed descriptions ≈ the entire default 2k-token listing budget; slim at the 1.2.0 pass)")
    # Platform truth is a different unit from the house ceiling above: Claude Code truncates the
    # CONCATENATION of description + when_to_use at 1,536 chars per listing entry (configurable via
    # skillListingMaxDescChars). Checking description alone is blind to the unit that actually
    # truncates — a member could pass the 1024 house rule and still be cut by the platform once a
    # when_to_use is added. No member declares when_to_use today, so this is a latent guard.
    if desc:
        wtu = re.search(r"^when_to_use:\s*(.+)$", fm, re.M)
        combined = len(desc.group(1)) + (len(wtu.group(1)) if wtu else 0)
        if combined > 1536:
            fail(f"{folder.name}: description+when_to_use {combined} chars > 1536 — the platform truncates "
                 f"the combined listing entry (skillListingMaxDescChars)")
        elif combined > 1382:  # 90% of the platform cap
            warn(f"{folder.name}: description+when_to_use {combined}/1536 chars — near the platform "
                 f"truncation cap for the combined listing entry")
    yaml_err = frontmatter_yaml_error(fm)
    if yaml_err:
        fail(f"{folder.name}: frontmatter fails YAML parse — {yaml_err} (quote the value)")
    body_lines = parts[2].count("\n")
    if body_lines > 500:
        fail(f"{folder.name}: SKILL.md body {body_lines} lines > 500")
    # Footprint. The ≤500-line rule above is the ecosystem norm (agentskills.io, via rubrics.md)
    # and stays a hard fail. The token figure below is this pack's OWN advisory, not a spec limit:
    # tokens are the truer cost (a dense 265-line body can outweigh a sparse 500-line one), but the
    # 5k number was arbitrary and fired on members the spec passes.
    #
    # Rescoped 2026-07-25: the gate is no longer "how big" but "is the size DECLARED and JUSTIFIED".
    # A member over the advisory must carry a row in the registry's `**<pack> budgets**` table:
    # the ceiling it is allowed (its own drift check) and why it earns the room. (The frontmatter
    # `metadata.body_budget` block that once served a standalone skill was a nested map, which
    # the Agent Skills spec forbids under metadata; validate_metadata_strings fails it since M3.)
    # Undeclared overage is the defect (hard fail since 2026-08-07 — item ③'s promise
    # landed). Declared overage is a recorded decision. Exceeding your OWN declared budget is drift
    # and warns regardless. This applies the pack's existing declared-dependencies doctrine to cost.
    body_tokens = len("---".join(parts[2:])) // 4  # chars/4 prose estimate, ±15%
    refs = every_run_refs(folder)
    FOOTPRINTS[folder.name] = (body_tokens, budget[0] if budget else None, refs)
    extra = sum(t for _, t in refs)  # files every entry reads on every run count as body (0223)
    # The registry row is the one home for a body budget (see pack_budgets).
    if budget:
        if extra and body_tokens + extra > budget[0]:
            warn(f"{folder.name}: body ≈{body_tokens} + every-run references ≈{extra} "
                 f"({', '.join(r for r, _ in refs)}) = ≈{body_tokens + extra} tokens, over its registry "
                 f"budget of {budget[0]} — a file every entry point reads counts as body (observation 0223)")
        elif body_tokens > budget[0]:
            warn(f"{folder.name}: SKILL.md body ≈{body_tokens} tokens over its registry budget "
                 f"of {budget[0]} — drift; slim it or raise the row deliberately")
    elif body_tokens > FOOTPRINT_ADVISORY:
        fail(f"{folder.name}: SKILL.md body ≈{body_tokens} tokens > {FOOTPRINT_ADVISORY//1000}k "
             f"advisory with no budget row in the registry — declare it there "
             f"and why it earns the room, or slim it (undeclared overage: hard fail since 2026-08-07)")
    validate_metadata_strings(folder, fm)
    if re.search(r"^\s+body_budget(?:_why)?:", fm, re.M):
        fail(f"{folder.name}: metadata.body_budget in frontmatter — a pack member's body budget lives "
             f"in the registry's budgets table only (the frontmatter pair is for a standalone skill)")
    validate_volatile(folder)
    validate_evals(folder, re.search(r'version:\s*"?([\d.]+)"?', fm).group(1) if re.search(r'version:\s*"?([\d.]+)"?', fm) else "0.0.0")
    validate_id_namespaces(folder)
    fm_ver = ver.group(1) if ver else "0.0.0"
    changelog = folder / "CHANGELOG.md"
    if changelog.exists():
        head = re.search(r"^##\s*\[([\d.]+)\]", changelog.read_text(encoding="utf-8"), re.M)
        if head and head.group(1) != fm_ver:
            fail(f"{folder.name}: CHANGELOG head [{head.group(1)}] != frontmatter version {fm_ver}")
        elif not head:
            fail(f"{folder.name}: CHANGELOG.md has no version heading")
    else:
        fail(f"{folder.name}: no CHANGELOG.md")
    return fm_ver


PROV_WORDS = re.compile(r"(?i)provenance|derived|target|re-?anchored")
PROV_WINDOW = 16  # a provenance paragraph must START in the first 16 lines


def _continues_paragraph(line: str) -> bool:
    """True when `line` carries on the paragraph above it: not blank, not a heading, table row,
    rule or new list item (a `> ` blockquote prefix is looked through)."""
    body = re.sub(r"^\s*>\s?", "", line).strip()
    return bool(body) and not re.match(r"(#|\||---|[-*+]\s|\d+[.)]\s)", body)


def _provenance_paragraphs(lines: list[str]) -> list[tuple[int, int]]:
    """(first, last) line index of each provenance paragraph in an eval file's head.

    The head ends at the first `## ` heading; a paragraph counts when one of its lines in the
    first PROV_WINDOW lines carries a provenance word, and it runs from that line to the end of
    its paragraph. Observation 0233: bump_member used to write after the LAST matching line in
    the first 16 — mid-sentence in a wrapped paragraph, or into a table row past the head.
    validate_evals reads the same lines, so the writer and the checker share one window."""
    stop = min(next((i for i, ln in enumerate(lines) if ln.startswith("## ")), len(lines)), PROV_WINDOW)
    out, i = [], 0
    while i < stop:
        if PROV_WORDS.search(lines[i]):
            j = i
            while j + 1 < len(lines) and not lines[j + 1].startswith("## ") and _continues_paragraph(lines[j + 1]):
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


CASE_ID = re.compile(r"^(?:#{2,4}\s+|\*\*)Case\s+(\d+)\b")
ROW_ID = re.compile(r"^\|\s*(\d+)\s*\|")
# The head of an eval file — everything above its first `## ` heading, table or case — is where
# provenance and count lines live, and re-anchor notes accrete there. History belongs in
# RESULTS.md. 60 was set from the tree on 2026-10-01 (observation 0225): the longest head
# then was 59 lines (lmstudiorunner's SUITE.md); the next longest ran 22.
EVAL_HEAD_MAX = 60
COUNTS_FIXED = re.compile(r"\s*(?:[-*]\s*)?Counts:\s*(\d+)\s+queries\s*\(\s*(\d+)\s+should,\s*(\d+)\s+should-not,"
                          r"\s*(\d+)\s+pairs?(?:,\s*(\d+)\s+injection\s+probes?)?\s*\)", re.I)


def validate_eval_counts(label: str, name: str, lines: list[str]) -> None:
    """Observation 0225: an eval file's stated totals, checked against what it holds.

    Cases are `## Case N` / `### Case N` headings or `**Case N` lines (distinct N); queries are
    numbered table rows `| N |`. Checked when stated: a `Counts: N cases|queries` line in the
    head, the title's `— N [assertion] cases|queries`, the title's `(A should / B shouldn't
    [/ C injection probes])` split, and a `## Section (N)` heading against the rows under it.
    A layout with nothing recognisable to count is skipped, never guessed at. Also fails a
    head longer than EVAL_HEAD_MAX lines.
    """
    cases = {m.group(1) for ln in lines if (m := CASE_ID.match(ln))}
    rows = [ln for ln in lines if ROW_ID.match(ln)]
    where = f"{label}: evals/{name}"
    head_end = next((i for i, ln in enumerate(lines)
                     if ln.startswith("## ") or ln.lstrip().startswith("|") or CASE_ID.match(ln)), len(lines))
    if head_end > EVAL_HEAD_MAX:
        fail(f"{where}: head runs {head_end} lines (max {EVAL_HEAD_MAX}) — move re-anchor history to "
             f"evals/RESULTS.md and keep one current provenance line (observation 0225)")

    def held(kind: str) -> tuple[int, str]:
        return (len(cases), "cases") if kind.lower().startswith("case") else (len(rows), "numbered rows")

    for ln in lines[:head_end]:
        m = re.match(r"\s*(?:[-*]\s*)?Counts:\s*(\d+)\s+(cases|queries)\b", ln, re.I)
        if m:
            n, what = held(m.group(2))
            if n and int(m.group(1)) != n:
                fail(f"{where}: count line states {m.group(1)} {m.group(2)} but the file holds {n} {what}")
    # The fixed form (unit OBA): suites stated counts in five prose forms and some left boundary
    # pairs out, so a trigger suite carries `Counts: N queries (S should, T should-not, P pairs)`.
    fixed = [m for ln in lines[:head_end] if (m := COUNTS_FIXED.match(ln))]
    # An optional `, Q injection probes` slot (unit FXL2): probe rows are numbered rows that are
    # neither should nor should-not, so they count toward N and never toward the pairs.
    for m in fixed:
        n, s, t, p = (int(x) for x in m.groups()[:4])
        q = int(m.group(5) or 0)
        if s + t + q != n:
            split = f"{s} + {t} + {q}" if m.group(5) else f"{s} + {t}"
            fail(f"{where}: fixed count line splits {split} = {s + t + q} but states {n} queries")
        if p > min(s, t):
            fail(f"{where}: fixed count line states {p} pairs but a pair needs one should and one "
                 f"should-not row (at most {min(s, t)})")
    if name == "trigger-evals.md" and not fixed and label not in COUNTS_FORM_MISSING:
        COUNTS_FORM_MISSING.append(label)
    title = lines[0] if lines and lines[0].startswith("# ") else ""
    tm = re.search(r"[—–-]\s*(\d+)\s+(?:assertion\s+)?(cases|queries)\b", title, re.I)
    if tm:
        n, what = held(tm.group(2))
        if n and int(tm.group(1)) != n:
            fail(f"{where}: title states {tm.group(1)} {tm.group(2)} but the file holds {n} {what}")
        sm = re.search(r"\((\d+)\s+should\s*/\s*(\d+)\s+shouldn['’]?t(?:\s*/\s*(\d+)\s+injection\s+probes?)?\)",
                       title, re.I)
        if sm:
            parts = [int(x) for x in sm.groups() if x]
            if sum(parts) != int(tm.group(1)):
                fail(f"{where}: title split {' + '.join(map(str, parts))} = {sum(parts)} but the title "
                     f"states {tm.group(1)}")
    for i, ln in enumerate(lines):
        hm = re.match(r"##\s+(.*?)\s*\((\d+)\)\s*$", ln)
        if not hm:
            continue
        end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
        n = sum(1 for ln2 in lines[i + 1:end] if ROW_ID.match(ln2))
        if n and n != int(hm.group(2)):
            fail(f"{where}: section '{hm.group(1)}' states {hm.group(2)} but holds {n} numbered row(s)")


def frontmatter_yaml_error(fm: str) -> str | None:
    """None when the whole frontmatter parses as YAML, else a one-line reason (unit K8e). Every
    field is parsed, not only the description: a plain value holding ": " (handoffwright and
    pixelsmith `compatibility:` until K8e) breaks a strict YAML loader. PyYAML when installed;
    else a stdlib scan that fails a plain (unquoted, non-block) scalar holding ": " or ending ":"."""
    try:
        import yaml
    except ModuleNotFoundError:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(fm)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            return f"{getattr(e, 'problem', None) or type(e).__name__}{where}"
        return None if isinstance(data, dict) else "frontmatter is not a mapping"
    for n, line in enumerate(fm.splitlines(), 1):
        m = re.match(r"^\s*(?:- )?[\w.-]+:[ \t]+(.*)$", line)
        if not m:
            continue
        val = m.group(1).split(" #", 1)[0].rstrip()
        if not val or val[0] in "'\"|>[{&*!":
            continue
        if ": " in val or val.endswith(":"):
            return f"plain value holds ': ' at line {n}"
    return None


def validate_evals(folder: Path, fm_ver: str) -> None:
    """Eval-suite integrity (added 2026-07-24; WARN this release, fail at the next tag).

    1. Provenance freshness: an evals/*.md head naming an older member version with no
       dated reconfirmation line is the exact defect class an evals audit (skillwright) flags in others.
    2. Orphan rows: a numbered table row appearing after prose that follows the table
       silently escapes count checks (a rows-21/22 orphan class seen 2026-07-24).
    """
    evdir = folder / "evals"
    if not evdir.is_dir():
        return
    for f in sorted(evdir.glob("*.md")):
        # RESULTS.md is an execution ledger — frozen records re-confirmed on their own
        # cadence, so old version stamps there are history, not provenance drift.
        if f.name == "RESULTS.md":
            continue
        # Head window: 6 lines was tuned for the original short headers; re-anchor
        # notes accrete downward, so read enough of the head to see the newest one.
        # The window and the paragraph rule are shared with bump_member (observation 0233).
        all_lines = f.read_text(encoding="utf-8").splitlines()
        prov_text = "\n".join(all_lines[i] for s, e in _provenance_paragraphs(all_lines) for i in range(s, e + 1))
        prov_versions = re.findall(r"\bv(\d+\.\d+\.\d+)\b", prov_text)
        # 2026-08-08 tightening: a dated re-anchor line used to satisfy freshness even
        # when it re-anchored to an OLD version — linecaller's test-cases.md sat at
        # "re-anchored to v1.1.0" through the 1.2.0 release and the gate read clean.
        # Rule: the CURRENT member version must be named somewhere on the provenance
        # lines. Membership, not last-token: provenance lines legitimately end with
        # other artifacts' versions (a suite may name its fixture's v1.0.0 last),
        # and predecessor-era designations can read HIGHER than current after the
        # 2026-07-31 re-baseline, so ordering comparisons are meaningless. Known
        # accepted gap: a reused designation could satisfy membership from a
        # predecessor-era mention — a heuristic gate, strictly tighter than before.
        # The pre-0233 window (any provenance-word line in the first 16, headings included) is
        # still read as a fallback: the old bump_member wrote notes there — onto a case's
        # Assert line past the head — so a note in it is MISPLACED (warn), not missing (fail).
        legacy = re.findall(r"\bv(\d+\.\d+\.\d+)\b", "\n".join(
            ln for ln in all_lines[:PROV_WINDOW] if PROV_WORDS.search(ln)))
        if fm_ver in prov_versions:
            pass
        elif fm_ver in legacy:
            warn(f"{folder.name}: evals/{f.name}: the v{fm_ver} re-anchor sits past the provenance head "
                 f"(after the first ## heading or outside the provenance paragraph) — move it into the "
                 f"provenance paragraph (observation 0233)")
        elif prov_versions or legacy:
            names = sorted(set(prov_versions) | set(legacy))
            fail(f"{folder.name}: evals/{f.name} provenance names {names} "
                 f"but never the current member version {fm_ver} — re-anchor in the same commit")
        validate_eval_counts(folder.name, f.name, all_lines)
        # Orphan = a numbered row whose nearest preceding non-empty line is not table-shaped
        # (a row under its own "|#|Query|" header in a later section is structured, not orphaned).
        lines = f.read_text(encoding="utf-8").splitlines()
        prev = ""
        for ln in lines:
            if re.match(r"\|\s*\d+\s*\|", ln) and prev and not prev.lstrip().startswith("|"):
                fail(f"{folder.name}: evals/{f.name}: numbered row {ln.strip()[:60]!r} follows prose, "
                     f"not a table — orphaned from count checks; move it into a table")
                break
            if ln.strip():
                prev = ln


# Id namespaces (observation 0305): S<n> names a source in SOURCES.md, C<n> a case in an eval
# file, so a bare "C9" never points at either. An id sits where a row or heading starts.
ID_AT_LINE_START = re.compile(r"^\s*(?:\||[-*#]+\s*|)\**\s*([SC])(\d+)\b")


def validate_id_namespaces(folder: Path) -> None:
    """WARN on an S<n> id in an eval file and on a C<n> id in SOURCES.md. Warn, not fail: members
    that predate the convention carry violations the owner decides on (observation 0305)."""
    targets = []
    evdir = folder / "evals"
    if evdir.is_dir():
        targets += [(f, "S", "eval case ids use C<n>") for f in sorted(evdir.glob("*.md"))
                    if f.name != "RESULTS.md"]
    if (folder / "SOURCES.md").is_file():
        targets.append((folder / "SOURCES.md", "C", "source ids use S<n>"))
    for f, bad, rule in targets:
        for n, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = ID_AT_LINE_START.match(ln)
            if m and m.group(1) == bad:
                warn(f"{folder.name}: {f.relative_to(folder)}:{n}: id {bad}{m.group(2)} is in the wrong "
                     f"namespace ({rule}); first of possibly more in this file (observation 0305)")
                break


GRADER_TYPES = ("regex", "tool_used", "tool_order", "file_exists", "llm", "baseline")
# Folders under evals/ that are never native cases: run output, and the hand-run suites'
# fixture trees (any member may ship evals/fixtures/).
NATIVE_EVAL_AUX = {"results", "fixtures"}


def _md_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    """({key: value}, body) for a `---` frontmatter block at the file head. ({}, text) when the
    file has none; (None, text) when the block is opened and never closed. Flat keys only — the
    layout check needs `type` and `weight`, not a YAML parser (stdlib only)."""
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    fm = {}
    for ln in text[4:end].split("\n"):
        m = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", ln)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip("\"'")
    return fm, text[end + 4:].split("\n", 1)[1] if "\n" in text[end + 4:] else ""


def validate_native_evals(evdir: Path, label: str) -> int:
    """Native `claude plugin eval` layout check; returns the number of native cases found.

    A suite is a set of case folders under `evals/`: each holds `prompt.md` (frontmatter =
    run limits and tools) and `graders/*.md` whose frontmatter `type:` is one of
    GRADER_TYPES (optional numeric `weight`, optional `arm`); `case.yaml` is optional and
    `evals/results/` is run output. A malformed case fails — a suite the runner cannot load
    audits nothing. A missing suite is the caller's advisory warning (tightened later), and
    the hand-run `evals/*.md` files stay valid beside it.
    """
    if not evdir.is_dir():
        return 0
    cases = 0
    for d in sorted(p for p in evdir.iterdir() if p.is_dir()):
        if d.name in NATIVE_EVAL_AUX or d.name.startswith((".", "_")):
            continue
        where = f"{label}: evals/{d.name}/"
        if not any((d / n).exists() for n in ("prompt.md", "graders", "case.yaml")):
            warn(f"{where} is neither a native eval case (no prompt.md, graders/ or case.yaml) nor a "
                 f"known auxiliary folder ({', '.join(sorted(NATIVE_EVAL_AUX))})")
            continue
        cases += 1
        prompt = d / "prompt.md"
        if not prompt.is_file():
            fail(f"{where}: native eval case has no prompt.md")
        else:
            fm, body = _md_frontmatter(prompt.read_text(encoding="utf-8"))
            if fm is None:
                fail(f"{where}prompt.md: frontmatter opened with --- and never closed")
            elif not body.strip():
                fail(f"{where}prompt.md: no prompt text after the frontmatter")
        graders = sorted((d / "graders").glob("*.md")) if (d / "graders").is_dir() else []
        if not graders:
            fail(f"{where}: native eval case has no graders/*.md — a case that grades nothing cannot fail")
        for g in graders:
            fm, _ = _md_frontmatter(g.read_text(encoding="utf-8"))
            gl = f"{where}graders/{g.name}"
            if fm is None:
                fail(f"{gl}: frontmatter opened with --- and never closed")
                continue
            if fm.get("type") not in GRADER_TYPES:
                fail(f"{gl}: grader type {fm.get('type')!r} is not one of {', '.join(GRADER_TYPES)}")
            if "weight" in fm and not re.fullmatch(r"\d+(\.\d+)?", fm["weight"]):
                fail(f"{gl}: weight {fm['weight']!r} is not a number")
    return cases


def bump_needed(packs: dict[str, str], versions: dict[str, tuple[Path, str]]) -> list[str]:
    """Shipped content changed since the pack's current version was tagged, but no version moved.

    Added 2026-08-17 for the post-commit hook (.claude/hooks/bump-check.py). For each pack whose
    tag `<pack>-v<plugin.json version>` exists locally, diff HEAD (plus the working tree) against
    that tag under packs/<pack>/. Any difference means the pack has moved past what its version
    names — the pack version is what installs and zips key on, so the change is invisible until
    it moves. Emits `pack bump needed: <pack>` and, per member whose folder differs while its
    frontmatter version equals the tagged one, `member bump needed: <member>`. Advisory (warn),
    never a failure: a pass legitimately carries unbumped commits until it closes. When the
    current version's tag is missing but an older `<pack>-v*` tag exists, emits `release tag missing:`
    (X-13, 2026-09-28). Silent when git is absent or the pack has no tags at all (fresh clone before
    `git fetch --tags`, CI on a detached ref).
    """
    import subprocess
    lines: list[str] = []
    for pack in packs:
        pj = PACKS / pack / ".claude-plugin" / "plugin.json"
        if not pj.is_file():
            continue
        ver = json.loads(pj.read_text(encoding="utf-8")).get("version")
        tag = f"{pack}-v{ver}"
        try:
            has_tag = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                                     capture_output=True, text=True).returncode == 0
            if not has_tag:
                older = subprocess.run(["git", "-C", str(ROOT), "tag", "--list", f"{pack}-v*"],
                                       capture_output=True, text=True).stdout.split()
                if older:
                    lines.append(f"release tag missing: {tag} — plugin.json says {ver} but no such tag exists "
                                 f"(older {pack} tags exist, e.g. {sorted(older)[-1]})")
                continue
            changed = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", tag, "--", f"packs/{pack}"],
                                     capture_output=True, text=True).stdout.split()
        except (OSError, FileNotFoundError):
            return lines
        if not changed:
            continue
        lines.append(f"pack bump needed: {pack} — {len(changed)} shipped file(s) differ from {tag} "
                     f"while plugin.json still says {ver}")
        for member, (skills_dir, mver) in versions.items():
            rel = f"packs/{pack}/skills/{member}/"
            if not any(c.startswith(rel) for c in changed):
                continue
            try:
                old = subprocess.run(["git", "-C", str(ROOT), "show", f"{tag}:{rel}SKILL.md"],
                                     capture_output=True, text=True, encoding="utf-8").stdout
            except OSError:
                continue
            m = re.search(r'version:\s*"?([\d.]+)"?', old.split("---")[1] if old.count("---") >= 2 else "")
            if m and m.group(1) == mver:
                lines.append(f"member bump needed: {member} — shipped files differ from {tag} at the same "
                             f"member version {mver}")
    for ln in lines:
        warn(ln)
    return lines


def registry_featured(text: str) -> list[str]:
    """Names on the registry's `**featured:** a, b` line (short or full member names; `none` = [])."""
    m = re.search(r"^\*\*featured:\*\*[ \t]*(.*)$", text, re.M)
    if not m:
        return []
    items = [x.strip(" `.") for x in m.group(1).split(",")]
    return [x for x in items if x and x.lower() != "none"]


def _featured_plugin(src: Path, pack_pj: dict, short: str) -> dict:
    """The featured plugin.json: named for the skill, versioned by the MEMBER (the plugin holds
    one member, so its version is the cache key that moves when that member ships), and
    carrying the pack's author, repository and license — nothing hardcoded here."""
    fm = _frontmatter(src / "SKILL.md")
    ver = re.search(r'version:\s*"?([\d.]+)"?', fm)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    plugin = {"name": short, "version": ver.group(1) if ver else "0.0.0",
              "description": desc.group(1).strip().strip("\"'") if desc else ""}
    for key in ("author", "repository", "license"):
        if key in pack_pj:
            plugin[key] = pack_pj[key]
    return plugin


def featured_release_skew(root: Path, pack: str, member: str, short: str, copy: Path) -> list[str]:
    """Warn when a featured copy's content differs from the member as its pack last released it.

    Added for the J1 featured verdict (2026-10-01): a user who installs the pack AND the
    featured plugin sees two entries under one skill name. The featured plugin is versioned by
    the member, the pack by the pack, so the two can carry different bodies and nothing in the
    listing says which is newer. Verify mode already fails on drift between the featured copy
    and the pack source in this tree; this compares the copy with the pack's newest
    `<pack>-v*` release tag, which is what a pack user actually has. Advisory (warn): a pass
    legitimately runs ahead of the release until it closes. Silent with no git or no tag.
    Returns the differing paths (relative to the member folder).
    """
    import subprocess

    def git(*args: str, text: bool = True):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=text)

    try:
        tags = git("tag", "--list", f"{pack}-v*").stdout.split()
    except OSError:
        return []

    def key(tag: str):
        return tuple(int(x) if x.isdigit() else 0 for x in tag.rsplit("-v", 1)[-1].split("."))

    if not tags or not copy.is_dir():
        return []
    tag = max(tags, key=key)
    prefix = f"packs/{pack}/skills/{member}/"
    listed = git("ls-tree", "-r", "--name-only", tag, "--", prefix)
    if listed.returncode != 0:
        return []
    released = {p[len(prefix):] for p in listed.stdout.splitlines() if p.startswith(prefix)}
    have = {p.as_posix() for p in _shipped(copy)}
    if not released:
        return []  # the member is newer than the pack's last release: bump_needed says so
    diff = sorted(released ^ have)
    for rel in sorted(released & have):
        old = git("show", f"{tag}:{prefix}{rel}", text=False).stdout
        if old.replace(b"\r\n", b"\n") != (copy / rel).read_bytes().replace(b"\r\n", b"\n"):
            diff.append(rel)
    if diff:
        warn(f"featured/{short}: its copy of {member} differs from the {pack} pack as last released "
             f"({tag}) in {len(diff)} file(s) ({', '.join(diff[:5])}{', …' if len(diff) > 5 else ''}) — "
             f"a user with both installed gets two bodies under one skill name; release {pack} or "
             f"tell users to install one, not both")
    return diff


def sync_featured(names: list[str], rosters: dict[str, list[str]], root: Path | None = None,
                  write: bool = False) -> int:
    """Generate (write=True) or verify (write=False) every `featured/<skill>/` one-skill plugin.

    Each holds `.claude-plugin/plugin.json`, `skills/<member>/` copied file for file from the
    pack source, and a landing-page `README.md` written once as a stub and then owned by hand;
    the marketplace carries one entry per plugin (`./featured/<skill>`). Verify mode fails on
    any drift — a file missing, differing or extra in the copy, a stale plugin.json, a missing
    README, a marketplace entry missing or out of step — and on a featured folder or entry the
    registry line does not name. Generate mode repairs drift but never deletes a folder.
    Returns the number of featured plugins.
    """
    root = root or ROOT
    feat_root = root / "featured"
    mkt_path = root / ".claude-plugin" / "marketplace.json"
    cat = json.loads(_read(mkt_path))
    entries = {p.get("name"): p for p in cat.get("plugins", [])}
    wanted: dict[str, tuple[str, str, Path]] = {}
    for name in names:
        hits = _resolve_member(name, rosters)
        if len(hits) != 1:
            fail(f"featured: {name!r} {'is not a registered member' if not hits else 'is ambiguous'}")
            continue
        pack, member = hits[0]
        short = member.rsplit("-", 1)[-1]
        src = root / "packs" / pack / "skills" / member
        if short in rosters:
            fail(f"featured: plugin name {short!r} collides with the pack of the same name")
        elif not src.is_dir():
            fail(f"featured: {member} has no folder in packs/{pack}/skills/ to copy from")
        else:
            wanted[short] = (pack, member, src)
    mkt_dirty = False
    for short, (pack, member, src) in wanted.items():
        dest = feat_root / short
        skill_dest = dest / "skills" / member
        pack_pj = json.loads(_read(root / "packs" / pack / ".claude-plugin" / "plugin.json"))
        plugin = _featured_plugin(src, pack_pj, short)
        drift: list[str] = []
        pj_path = dest / ".claude-plugin" / "plugin.json"
        if not pj_path.is_file() or json.loads(_read(pj_path)) != plugin:
            drift.append(".claude-plugin/plugin.json")
            if write:
                _write_text(pj_path, json.dumps(plugin, indent=2, ensure_ascii=False) + "\n")
        src_files = set(_shipped(src))
        dst_files = set(_shipped(dest / "skills")) if (dest / "skills").is_dir() else set()
        for rel in sorted(src_files):
            out = skill_dest / rel
            data = (src / rel).read_bytes()
            if not out.is_file() or out.read_bytes().replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
                drift.append(f"skills/{member}/{rel.as_posix()}")
                if write:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(data)
        for rel in sorted(dst_files - {Path(member) / r for r in src_files}):
            drift.append(f"skills/{rel.as_posix()} (not in the pack source)")
            if write:
                (dest / "skills" / rel).unlink()
        # Apache-2.0 4(d): the NOTICE travels inside the skill folder (unit NM), so the copy
        # above carries it as an ordinary member file; the plugin root needs no second copy.
        readme = dest / "README.md"
        if not readme.is_file():
            drift.append("README.md")
            if write:
                _write_text(readme, f"# {short}\n\n"
                                    f"A one-skill plugin: `{member}` from the {pack} pack, generated by "
                                    f"`tools/build.py` from the pack source.\n\n"
                                    f"Install: `/plugin install {short}@{cat.get('name', '<marketplace>')}`\n\n"
                                    f"Landing page stub: replace this paragraph with what the skill does, what "
                                    f"is unique about it, and how it fits its pack. Everything under `skills/` is "
                                    f"generated; edit the pack source, never this copy.\n")
        pack_entry = entries.get(pack, {})
        want_entry = {"name": short, "source": f"./featured/{short}", "description": plugin["description"],
                      "version": plugin["version"], "license": plugin.get("license", DEFAULT_LICENSE),
                      "category": pack_entry.get("category", "productivity"),
                      "keywords": ["agent-skills", "skills", "featured"]}
        if "repository" in plugin:
            want_entry["repository"] = plugin["repository"]
        have = entries.get(short)
        if not have or any(have.get(k) != want_entry[k] for k in ("source", "version", "description")):
            drift.append("marketplace entry")
            if write:
                if have:
                    have.update({k: want_entry[k] for k in ("source", "version", "description")})
                else:
                    cat.setdefault("plugins", []).append(want_entry)
                    entries[short] = want_entry
                mkt_dirty = True
        if drift and write:
            print(f"  ✎ featured/{short}: {len(drift)} item(s) regenerated")
        elif drift:
            fail(f"featured/{short}: drifts from the pack source ({', '.join(drift[:5])}"
                 f"{f', … {len(drift) - 5} more' if len(drift) > 5 else ''}) — run tools/build.py")
        if not write:
            featured_release_skew(root, pack, member, short, skill_dest)
    if mkt_dirty:
        _write_text(mkt_path, json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    if feat_root.is_dir():
        for d in sorted(p for p in feat_root.iterdir() if p.is_dir() and p.name not in wanted):
            fail(f"featured/{d.name}/ is not on the registry's **featured:** line — delete it or add it to the line")
    for name, entry in entries.items():
        if str(entry.get("source", "")).startswith("./featured/") and name not in wanted:
            fail(f"marketplace.json: featured plugin {name!r} is not on the registry's **featured:** line")
    return len(wanted)


def check_mods(root: Path | None = None) -> int:
    """Mod-only plugins under `mods/` (owner 2026-10-06): each is listed in the marketplace at
    its own version, carries the empty `"hooks": {}` key older Claude Code needs to keep loading,
    and holds no skills. Hook-module code never ships inside a skill: no .ts, .tsx or .jsx file
    and no hooks.json naming `modules` under a pack member or a featured plugin, so it cannot
    reach a claude.ai zip (a skill's own shell hooks, gatewarden's, are not modules and stay).
    A bundle (`all-mods`) holds no code and lists every other mod plugin under `dependencies`,
    so one install pulls in all of them. Returns the number of mod plugins."""
    root = root or ROOT
    mods_root = root / "mods"
    mkt_path = root / ".claude-plugin" / "marketplace.json"
    entries = {}
    if mkt_path.is_file():
        entries = {p["name"]: p for p in json.loads(mkt_path.read_text(encoding="utf-8")).get("plugins", [])}
    found = sorted(p for p in mods_root.iterdir() if (p / ".claude-plugin" / "plugin.json").is_file()) if mods_root.is_dir() else []
    for d in found:
        pj = json.loads((d / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        name = pj.get("name", d.name)
        if name != d.name:
            fail(f"mods/{d.name}: plugin.json name {name!r} differs from its folder")
        entry = entries.get(name)
        if not entry:
            fail(f"marketplace.json: no entry for mod plugin {name!r} (source ./mods/{d.name})")
        else:
            if entry.get("source") != f"./mods/{d.name}":
                fail(f"marketplace.json: {name!r} source {entry.get('source')!r} != './mods/{d.name}'")
            if entry.get("version") != pj.get("version"):
                fail(f"mods/{d.name}: plugin.json version {pj.get('version')!r} != marketplace entry {entry.get('version')!r}")
        hj = d / "hooks" / "hooks.json"
        deps = pj.get("dependencies")
        if deps is not None and not hj.is_file():
            # A bundle: no code, every other mod plugin as a dependency at its own version.
            others = sorted(x.name for x in found if x != d and (x / "hooks" / "hooks.json").is_file())
            if sorted(deps) != others:
                fail(f"mods/{d.name}: a bundle must depend on every mod plugin {others}, has {sorted(deps)}")
            continue
        if not hj.is_file():
            fail(f"mods/{d.name}: missing hooks/hooks.json")
        else:
            h = json.loads(hj.read_text(encoding="utf-8"))
            if h.get("hooks") != {} or not h.get("modules"):
                fail(f"mods/{d.name}: hooks.json must be {{\"hooks\": {{}}, \"modules\": [...]}} so older Claude Code still loads")
            for mod in h.get("modules") or []:
                mf = hj.parent / mod
                if not mf.is_file():
                    fail(f"mods/{d.name}: hooks.json names {mod}, which does not exist")
                else:
                    m = re.search(r"^const VERSION = '([^']+)'", mf.read_text(encoding="utf-8"), re.M)
                    if m and m.group(1) != pj.get("version"):
                        fail(f"mods/{d.name}: {mod} VERSION {m.group(1)!r} != plugin.json version {pj.get('version')!r}")
        if (d / "skills").exists():
            fail(f"mods/{d.name}: a mod plugin holds no skills (they ship in packs/)")
    for name, entry in entries.items():
        src = str(entry.get("source", ""))
        if src.startswith("./mods/") and not (root / src[2:] / ".claude-plugin" / "plugin.json").is_file():
            fail(f"marketplace.json: mod plugin {name!r} source {src} not found")
    for base in [root / "packs", root / "featured"]:
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            rel = f.relative_to(root)
            parts = rel.parts
            in_skill = ("skills" in parts) or parts[0] == "featured"
            if not in_skill:
                continue
            if f.is_file() and f.suffix in {".ts", ".tsx", ".jsx", ".mts"}:
                fail(f"{rel}: a hooks-module file inside a skill would ship in its zip; mods live in mods/")
            elif f.is_file() and f.name == "hooks.json" and '"modules"' in f.read_text(encoding="utf-8", errors="replace"):
                fail(f"{rel}: a hooks module wired inside a skill would ship in its zip; mods live in mods/")
    return len(found)


SHARED_MANIFEST = "holders.json"


def sync_shared(pack: str, roster: list[str], root: Path | None = None, write: bool = False,
                report_only: bool = False) -> int:
    """Generate (write=True) or verify every pack-shared file copy (owner Q2, 2026-10-01).

    The source lives once in `packs/<pack>/shared/<relpath>`; `shared/holders.json` is
    `{"files": {"<relpath>": ["<member>", ...]}}` with short or full member names. Each holder
    carries a byte copy at `<member>/<relpath>`, so a member still runs and ships alone. Verify
    mode fails on a copy missing or differing (line endings aside), a holder not in the roster, a
    listed file with no source, a source file the manifest does not list, and a member that
    carries a shared path without being listed (a hand copy the generator would never update).
    report_only (--footprint) warns instead and writes nothing. A pack with no `shared/` folder
    is a no-op. Returns the number of holder copies the manifest declares.
    """
    root = root or ROOT
    shared = root / "packs" / pack / "shared"
    if not shared.is_dir():
        return 0
    label = f"[{pack}] shared"
    manifest = shared / SHARED_MANIFEST
    try:
        files = json.loads(_read(manifest))["files"]
        if not isinstance(files, dict) or not all(isinstance(v, list) for v in files.values()):
            raise ValueError("files must map a path to a list of members")
    except FileNotFoundError:
        fail(f"{label}: packs/{pack}/shared/ has no {SHARED_MANIFEST} naming which member carries which file")
        return 0
    except (ValueError, KeyError, TypeError) as e:
        fail(f"{label}: packs/{pack}/shared/{SHARED_MANIFEST} is malformed ({e})")
        return 0
    sources = {p.relative_to(shared).as_posix() for p in shared.rglob("*")
               if p.is_file() and p.name != SHARED_MANIFEST and "__pycache__" not in p.parts
               and p.suffix != ".pyc"}
    for rel in sorted(sources - set(files)):
        fail(f"{label}: source {rel} is not listed in {SHARED_MANIFEST} — list its holders or remove it")
    by_short = {m.rsplit("-", 1)[-1]: m for m in roster}
    skills = root / "packs" / pack / "skills"
    n = 0
    for rel, holders in sorted(files.items()):
        src = shared / rel
        if rel not in sources:
            fail(f"{label}: {rel} is listed in {SHARED_MANIFEST} but has no source in packs/{pack}/shared/")
            continue
        data = src.read_bytes()
        listed: set[str] = set()
        for name in holders:
            full = name if name in roster else by_short.get(name)
            if not full:
                fail(f"{label}: holder {name!r} of {rel} is not a member of the {pack} roster")
                continue
            listed.add(full)
            n += 1
            out = skills / full / rel
            if out.is_file() and out.read_bytes().replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n"):
                continue
            what = f"{full}/{rel} {'is missing' if not out.is_file() else 'drifts from'} its shared source " \
                   f"packs/{pack}/shared/{rel}"
            if write:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                print(f"  ✎ shared → {full}/{rel}")
            elif report_only:
                warn(f"{what} — run tools/build.py to regenerate it (--footprint writes nothing)")
            else:
                fail(f"{what} — run tools/build.py (edit the shared source, never a copy)")
        for full in roster:
            if full not in listed and (skills / full / rel).is_file():
                fail(f"{label}: {full}/{rel} is a shared path but {full} is not listed in {SHARED_MANIFEST} "
                     f"— add it as a holder or delete the hand copy")
    return n


NOTICE_FILE = "NOTICE"


def sync_member_notice(pack: str, roster: list[str], root: Path | None = None, write: bool = False,
                       report_only: bool = False) -> int:
    """Generate (write=True) or verify every member's NOTICE copy (unit NM, 2026-10-02).

    Apache-2.0 section 4(d): a redistribution carries the work's NOTICE, and a lone skill folder
    copied out of a pack is one. The pack NOTICE (`packs/<pack>/NOTICE`) stays the single source;
    every roster member carries a byte copy at `<member>/NOTICE`, beside its LICENSE. Verify mode
    fails on a copy missing or differing (line endings aside); report_only (--footprint) warns
    and writes nothing. A pack with no NOTICE is a no-op. Returns the number of member copies.
    """
    root = root or ROOT
    src = root / "packs" / pack / NOTICE_FILE
    if not src.is_file():
        return 0
    data = src.read_bytes()
    skills = root / "packs" / pack / "skills"
    n = 0
    for full in roster:
        if not (skills / full).is_dir():
            continue  # a missing member folder fails in the roster check
        n += 1
        out = skills / full / NOTICE_FILE
        if out.is_file() and out.read_bytes().replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n"):
            continue
        what = f"{full}/{NOTICE_FILE} {'is missing' if not out.is_file() else 'drifts from'} its pack source " \
               f"packs/{pack}/{NOTICE_FILE}"
        if write:
            out.write_bytes(data)
            print(f"  ✎ notice → {full}/{NOTICE_FILE}")
        elif report_only:
            warn(f"{what} — run tools/build.py to regenerate it (--footprint writes nothing)")
        else:
            fail(f"{what} — run tools/build.py (edit the pack NOTICE, never a copy)")
    return n


PACK_EVAL_SEP = "--"
# The generated pack suite's folder, named in each pack's plugin.json `experimental.evals` (unit K8e,
# owner M7). Never "evals": under the default name `claude plugin eval` opens every folder with an
# `evals` path segment, so it found each case twice (the copy and skills/<member>/evals/<case>/) and
# double-counted scores. A non-default manifest value walks only this folder.
PACK_EVAL_DIR = "pack-evals"
RUNNER_DEFAULT_EVAL_DIR = "evals"


def runner_case_dirs(pdir: Path) -> list[Path]:
    """The case folders `claude plugin eval <pdir>` discovers (claude 2.1.295 rule, unit K8e):
    the eval dir is plugin.json `experimental.evals`, else `evals`. Under the default name every
    folder below the plugin with an `evals` path segment is opened; under any other name only the
    folders below that path. A case is a folder holding prompt.md or case.yaml (not walked into);
    hidden folders and results/ are skipped."""
    try:
        man = json.loads((pdir / ".claude-plugin" / "plugin.json").read_bytes())
    except (OSError, ValueError):
        man = {}
    exp = man.get("experimental") if isinstance(man, dict) else None
    name = exp.get("evals") if isinstance(exp, dict) and isinstance(exp.get("evals"), str) else None
    segs = [s for s in (name or RUNNER_DEFAULT_EVAL_DIR).replace("\\", "/").split("/") if s not in ("", ".")]
    default = segs == [RUNNER_DEFAULT_EVAL_DIR]
    found: list[Path] = []

    def walk(d: Path) -> None:
        rel = list(d.relative_to(pdir).parts)
        opens = RUNNER_DEFAULT_EVAL_DIR in rel if default else rel[:len(segs)] == segs
        if opens and any((d / n).is_file() for n in ("prompt.md", "case.yaml")):
            found.append(d)
            return
        for c in sorted(p for p in d.iterdir() if p.is_dir()):
            if c.name.startswith(".") or c.name in ("results", "node_modules"):
                continue
            crel = rel + [c.name]
            if default or crel[:len(segs)] == segs or segs[:len(crel)] == crel:
                walk(c)

    walk(pdir)
    return found


def check_pack_eval_manifest(pdir: Path, label: str, write: bool = False) -> None:
    """plugin.json must name PACK_EVAL_DIR as `experimental.evals` (write mode sets it), and the
    runner must discover each case once, only from PACK_EVAL_DIR/ (unit K8e)."""
    pj = pdir / ".claude-plugin" / "plugin.json"
    if not pj.is_file():
        return
    data = json.loads(pj.read_bytes())
    exp = data.get("experimental")
    if not (isinstance(exp, dict) and exp.get("evals") == PACK_EVAL_DIR):
        if write:
            data["experimental"] = {**(exp if isinstance(exp, dict) else {}), "evals": PACK_EVAL_DIR}
            _write_text(pj, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            print(f"  ✎ {label}: plugin.json experimental.evals = {PACK_EVAL_DIR}")
        else:
            fail(f"{label}: plugin.json experimental.evals must be \"{PACK_EVAL_DIR}\" — without it "
                 f"`claude plugin eval` walks every evals/ folder and runs each case twice; run tools/build.py")
            return
    seen: dict[str, str] = {}
    for d in runner_case_dirs(pdir):
        rel = d.relative_to(pdir).as_posix()
        if not rel.startswith(PACK_EVAL_DIR + "/"):
            fail(f"{label}: `claude plugin eval` discovers {rel}/ outside {PACK_EVAL_DIR}/ — "
                 f"it would run beside the generated copies")
        elif d.name in seen:
            fail(f"{label}: `claude plugin eval` discovers case {d.name} twice ({seen[d.name]}, {rel})")
        seen[d.name] = rel


def _native_cases(evdir: Path) -> list[Path]:
    """The native case folders under one member's evals/ — the rule validate_native_evals uses."""
    if not evdir.is_dir():
        return []
    return [d for d in sorted(evdir.iterdir())
            if d.is_dir() and d.name not in NATIVE_EVAL_AUX and not d.name.startswith((".", "_"))
            and any((d / n).exists() for n in ("prompt.md", "graders", "case.yaml"))]


def _case_files(d: Path) -> dict[str, bytes]:
    """{relpath: bytes, CRLF folded} for every file a case folder ships."""
    return {p.relative_to(d).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
            for p in sorted(d.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def sync_pack_evals(pack: str, roster: list[str], root: Path | None = None, write: bool = False) -> int:
    """Generate (write=True) or verify the pack-level eval folder (unit EVG, 2026-10-01).

    Every native case `packs/<pack>/skills/<member>/evals/<case>/` (prompt.md, graders/, resources/ —
    the whole folder) is copied to `packs/<pack>/pack-evals/<short>--<case>/` (PACK_EVAL_DIR, named in
    plugin.json `experimental.evals` so the runner walks only the copies — unit K8e). The member case is the source of truth.
    Hand-run files (trigger-evals.md, RESULTS.md, SUITE.md ...) and auxiliary folders are not cases.
    Verify mode fails on a copy missing or differing (line endings aside, extra or missing files
    included) and on any other folder in the pack's PACK_EVAL_DIR/ (results/, fixtures/ and hidden or
    _-prefixed folders aside). Write mode rewrites each drifting copy whole and removes stale
    generated (`--`) folders; a hand folder there still fails and is kept. Returns the case count.
    """
    root = root or ROOT
    pdir = root / "packs" / pack
    out_dir = pdir / PACK_EVAL_DIR
    label = f"[{pack}] evals"
    expected: dict[str, Path] = {}
    for full in roster:
        short = full.rsplit("-", 1)[-1]
        for d in _native_cases(pdir / "skills" / full / "evals"):
            expected[f"{short}{PACK_EVAL_SEP}{d.name}"] = d
    for name, src in expected.items():
        out = out_dir / name
        if out.is_dir() and _case_files(out) == _case_files(src):
            continue
        rel_src = src.relative_to(pdir).as_posix()
        what = f"{label}: {name}/ {'is missing' if not out.is_dir() else 'drifts from'} its source {rel_src}/"
        if write:
            if out.exists():
                shutil.rmtree(out)
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            print(f"  ✎ evals → packs/{pack}/{PACK_EVAL_DIR}/{name}/")
        else:
            fail(f"{what} — run tools/build.py (edit the member case, never the copy)")
    if out_dir.is_dir():
        for d in sorted(p for p in out_dir.iterdir() if p.is_dir()):
            if d.name in expected or d.name in NATIVE_EVAL_AUX or d.name.startswith((".", "_")):
                continue
            if PACK_EVAL_SEP not in d.name:
                fail(f"{label}: {d.name}/ is not generated — packs/{pack}/{PACK_EVAL_DIR}/ holds only build.py copies "
                     f"of member cases; move it to a member's evals/ folder")
            elif write:
                shutil.rmtree(d)
                print(f"  ✗ evals → packs/{pack}/{PACK_EVAL_DIR}/{d.name}/ (stale)")
            else:
                fail(f"{label}: {d.name}/ is stale (no member case behind it) — run tools/build.py")
    check_pack_eval_manifest(pdir, label, write)
    return len(expected)


def check_marketplace(packs: dict[str, str]) -> None:
    """Cross-check the catalog: every pack has an entry; every entry's source exists;
    the pack's own plugin.json version matches the catalog (added 2026-07-24 —
    hard fail: a plugin.json/marketplace split-brain shipped for a month, CI-invisible)."""
    if not MARKETPLACE.exists():
        fail("missing .claude-plugin/marketplace.json")
        return
    cat = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entries = {p["name"]: p for p in cat.get("plugins", [])}
    for pack in packs:
        if pack not in entries:
            fail(f"marketplace.json: no plugin entry for pack '{pack}'")
        else:
            src = ROOT / entries[pack].get("source", "").lstrip("./")
            if not src.is_dir():
                fail(f"marketplace.json: '{pack}' source {entries[pack].get('source')} not found")
            else:
                pj = src / ".claude-plugin" / "plugin.json"
                cat_ver = entries[pack].get("version")
                if not pj.is_file():
                    fail(f"'{pack}': missing {pj.relative_to(ROOT)}")
                else:
                    pj_ver = json.loads(pj.read_text(encoding="utf-8")).get("version")
                    if pj_ver != cat_ver:
                        fail(f"'{pack}': plugin.json version {pj_ver!r} != marketplace entry {cat_ver!r} "
                             f"(use --bump-pack to write both in one stroke)")
    for name, entry in entries.items():
        if str(entry.get("source", "")).startswith(("./featured/", "./mods/")):
            continue  # a featured one-skill plugin (sync_featured) or a mod-only plugin (check_mods)
        if name not in packs:
            fail(f"marketplace.json: plugin '{name}' has no pack table in the registry")


def bump_pack(pack: str, ver: str, root: Path | None = None, today: str | None = None) -> int:
    """One-stroke version write: marketplace entry + pack plugin.json + root CHANGELOG scaffold."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        print(f"✗ {ver!r} is not X.Y.Z"); return 1
    root = root or ROOT
    mkt = root / ".claude-plugin" / "marketplace.json"
    cat = json.loads(mkt.read_text(encoding="utf-8"))
    entry = next((p for p in cat.get("plugins", []) if p["name"] == pack), None)
    if entry is None:
        print(f"✗ no marketplace entry for pack {pack!r}"); return 1
    old = entry.get("version")
    entry["version"] = ver
    # Observation 0220: every write below goes through the bytes-mode helpers, so each file
    # keeps its own line ending — write_text turned all three CRLF on Windows.
    _write_text(mkt, json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    pj_path = root / entry.get("source", "").lstrip("./") / ".claude-plugin" / "plugin.json"
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    pj["version"] = ver
    _write_text(pj_path, json.dumps(pj, indent=2, ensure_ascii=False) + "\n")
    clog = root / "CHANGELOG.md"
    if clog.exists():
        heading = f"## [{pack}-v{ver}] - {today or date.today().isoformat()}"

        def scaffold(text: str) -> str:
            if heading in text:
                return text
            lines = text.split("\n")
            for i, ln in enumerate(lines):
                if ln.startswith("## "):
                    lines[i:i] = [heading, "", "- (fill in)", ""]
                    return "\n".join(lines)
            return text.rstrip("\n") + "\n\n" + heading + "\n\n- (fill in)\n"
        _rewrite(clog, scaffold)
    print(f"✓ {pack}: {old} → {ver} (marketplace.json + plugin.json + CHANGELOG scaffold)")
    return 0


def new_pack(name: str, motif: str | None, profile: str | None, root: Path | None = None,
             today: str | None = None) -> int:
    """Scaffold an empty pack: `packs/<name>/.claude-plugin/plugin.json` (0.1.0), its marketplace
    entry, a README stub, the Pack registry row and the per-pack registry block (empty members
    and budgets tables, capstone, canonical repo). Each part is created only when absent, so a
    re-run is a no-op; `--check` passes on the result with zero members."""
    root = root or ROOT
    today = today or date.today().isoformat()
    if not re.fullmatch(r"[a-z][a-z0-9]*", name or ""):
        print(f"✗ pack name {name!r}: lowercase letters and digits, singular (e.g. scribe)"); return 1
    motif = (motif or "").strip()
    motif = motif if motif.startswith("-") else f"-{motif}"
    if not re.fullmatch(r"-[a-z]+", motif):
        print("✗ --motif <suffix> is required: the member-name suffix, e.g. --motif scribe"); return 1
    if profile not in ("standard", "standalone"):
        print("✗ --profile must be standard or standalone"); return 1
    registry = root / REGISTRY.relative_to(ROOT)
    mkt_path = root / ".claude-plugin" / "marketplace.json"
    pack_dir = root / "packs" / name
    cat = json.loads(mkt_path.read_text(encoding="utf-8"))
    plugins = cat.setdefault("plugins", [])
    clash = next((p for p in plugins if p.get("name") == name and p.get("source") != f"./packs/{name}"), None)
    if clash:
        print(f"✗ marketplace already has a plugin named {name!r} with source {clash.get('source')!r}"); return 1
    template = next((p for p in plugins if str(p.get("source", "")).startswith("./packs/")), {})
    repo_url = template.get("repository")
    licence = template.get("license", DEFAULT_LICENSE)
    desc = f"Skills on the {motif} motif ({profile} profile). Scaffolded {today}; no members yet."
    reg_text = _read(registry)
    brand_m = re.search(r"Brand token \*\(label\)\* \|\s*`([^`]+)`", reg_text)
    brand = brand_m.group(1) if brand_m else "<brand>"
    repo_m = re.search(r"\*\*[\w-]+ canonical repo:\*\*\s*(`[^`]+`)", reg_text)
    repo = repo_m.group(1) if repo_m else (f"`{re.sub(r'^https?://', '', repo_url)}`" if repo_url
                                           else "the registered canonical repo")
    created: list[str] = []

    pj = pack_dir / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        data = {"name": name, "version": "0.1.0", "description": desc}
        data["experimental"] = {"evals": PACK_EVAL_DIR}  # one discovery route (unit K8e)
        if cat.get("owner", {}).get("name"):
            data["author"] = {"name": cat["owner"]["name"]}
        if repo_url:
            data["repository"] = repo_url
        data["license"] = licence
        _write_text(pj, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        created.append(pj.relative_to(root).as_posix())
    if not any(p.get("name") == name for p in plugins):
        entry = {"name": name, "source": f"./packs/{name}", "description": desc, "version": "0.1.0",
                 "license": licence, "category": template.get("category", "productivity"),
                 "keywords": ["agent-skills", "skills", "pack"]}
        if repo_url:
            entry["repository"] = repo_url
        plugins.append(entry)
        _write_text(mkt_path, json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
        created.append("marketplace entry")
    readme = pack_dir / "README.md"
    if not readme.exists():
        _write_text(readme, f"# {name} pack\n\n"
                            f"Skills on the `{motif}` motif, {profile} profile. Scaffolded {today} by "
                            f"`tools/build.py --new-pack`; no members yet.\n\n"
                            f"Members live under `skills/` as `{brand}-{name}-<skill>`, each named with the "
                            f"`{motif}` suffix. The roster, budgets and seams live in the pack registry "
                            f"(skillwright's `references/pack-registry.md`); every member's "
                            f"`references/pack.md` is generated from it by `tools/build.py`.\n")
        created.append(readme.relative_to(root).as_posix())

    def register(text: str) -> str:
        head, sep, tail = text.partition("## Pack registry")
        if not sep:
            raise SystemExit(f"✗ {registry.name}: no '## Pack registry' section")
        if not re.search(rf"^\|\s*`{name}`\s*\|", tail, re.M):
            lines = tail.split("\n")
            start = next(i for i, ln in enumerate(lines) if ln.startswith("|"))
            end = next((i for i in range(start, len(lines)) if not lines[i].startswith("|")), len(lines))
            lines.insert(end, f"| `{name}` | {profile} | Skills on the `{motif}` motif (registered {today} by "
                              f"`build.py --new-pack`, no members yet). Conformance checks ({today}): C-1 "
                              f"drift-audit verb · C-2 neutral default. Integrate policy: restamp: lazy ({today}) |")
            tail = "\n".join(lines)
            created.append("registry row")
        text = head + sep + tail
        if f"**{name} members**" not in text:
            block = (f"**{name} members** *(canonical roster — pack manifests are generated from this table)*\n\n"
                     "| Member | Job | Route there when |\n|---|---|---|\n\n"
                     f"**{name} budgets** *(body-footprint table — one row per member; `build.py` validates each "
                     "member's measured SKILL.md body against its row)*\n\n"
                     "| Member | Budget (tokens) | Why |\n|---|---|---|\n\n"
                     f"**{name} capstone:** none — scaffolded {today} with no members; revisit when the roster "
                     "reaches three.\n\n"
                     f"**{name} canonical repo:** {repo} — source of truth for member drift audits "
                     f"(registered {today}).\n\n")
            at = text.find("\n## Cross-pack seams")
            text = (text[:at + 1] + block + text[at + 1:]) if at >= 0 else text.rstrip("\n") + "\n\n" + block
            created.append("registry block")
        return text
    _rewrite(registry, register)
    print(f"✓ {name} ({motif}, {profile}): {', '.join(created) or 'already scaffolded'}")
    return 0


def _read(p: Path) -> str:
    """File text with CRLF folded to LF (bytes in, so no platform translation)."""
    return p.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _write_text(p: Path, text: str) -> bool:
    """Write text as bytes, keeping the file's own line ending — LF for a new file, which is
    what `.gitattributes` declares. `Path.write_text` translates "\\n" to CRLF on Windows, so
    every generated file came back CRLF on the rig (observation 0220). True when bytes changed."""
    old = p.read_bytes() if p.is_file() else None
    eol = "\r\n" if old is not None and b"\r\n" in old else "\n"
    new = text.replace("\r\n", "\n").replace("\n", eol).encode("utf-8")
    if new == old:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(new)
    return True


def _rewrite(p: Path, edit) -> bool:
    """Apply edit(text) -> text to one file, keeping that file's own line ending (bytes in,
    bytes out — write_text would turn LF into CRLF on Windows). True when the file changed."""
    raw = p.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    new = edit(raw.replace("\r\n", "\n"))
    if new == raw.replace("\r\n", "\n"):
        return False
    p.write_bytes(new.replace("\n", eol).encode("utf-8"))
    return True


def bump_member(folder: Path, ver: str, reason: str, today: str | None = None) -> int:
    """One-stroke member version write (observation #0129) — every file a member bump's gate
    forces to move: the SKILL.md frontmatter version; the CHANGELOG head (a staged
    `## [Unreleased]` or `## Unreleased` heading becomes `## [ver] — date`, otherwise a heading plus `reason`
    is scaffolded); and a dated re-anchor on each evals/*.md provenance head (RESULTS.md is
    an execution ledger and is left alone). Idempotent. Run --check afterwards."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        print(f"✗ {ver!r} is not X.Y.Z"); return 1
    today = today or date.today().isoformat()
    changed: list[str] = []

    def version(text: str) -> str:
        new, n = re.subn(r'(\n\s*version:\s*)"?[\d.]+"?', rf'\g<1>"{ver}"', text, count=1)
        if n != 1:
            raise SystemExit(f"✗ {folder.name}: no frontmatter version line in SKILL.md")
        return new
    if _rewrite(folder / "SKILL.md", version):
        changed.append("SKILL.md")

    def changelog(text: str) -> str:
        if re.search(rf"^##\s*\[{re.escape(ver)}\]", text, re.M):
            return text
        staged = r"^##\s*\[?Unreleased\]?"  # both Keep a Changelog forms: [Unreleased] and Unreleased
        if re.search(staged, text, re.M | re.I):
            return re.sub(staged + r".*$", f"## [{ver}] — {today}", text, count=1, flags=re.M | re.I)
        m = re.search(r"^## ", text, re.M)
        block = f"## [{ver}] — {today}\n\n- {reason}\n\n"
        return text[:m.start()] + block + text[m.start():] if m else text.rstrip("\n") + "\n\n" + block
    if _rewrite(folder / "CHANGELOG.md", changelog):
        changed.append("CHANGELOG.md")

    # Observation 0211: "current" means the exact token this function writes — "re-anchored to
    # v<ver>" — on a provenance line. Bare membership of "v<ver>" was satisfied by history: a
    # predecessor-era designation equal to the new version made the bump skip the file, and
    # --check (which tests membership) then read clean on a stale suite.
    token = re.compile(rf"(?i)re-?anchored to v{re.escape(ver)}(?![\d.]*\d)")
    for f in sorted((folder / "evals").glob("*.md")) if (folder / "evals").is_dir() else []:
        if f.name == "RESULTS.md":
            continue

        def anchor(text: str) -> str:
            lines = text.split("\n")
            paras = _provenance_paragraphs(lines)  # observation 0233: found by the head, not a line number
            block = [i for s, e in paras for i in range(s, e + 1)]
            if not block or any(token.search(lines[i]) for i in block):
                return text
            # Observation 0239: the provenance line names ONE current anchor, so an existing
            # "re-anchored to vX.Y.Z[, date]" phrase is rewritten in place (history lives in
            # RESULTS.md and the CHANGELOG). Only a line with no such phrase gets a clause
            # appended — and then both sentences are closed, never left as a run-on.
            phrase = re.compile(r"(?i)(re-?anchored to )v\d+\.\d+\.\d+(?:,\s*\d{4}-\d{2}-\d{2})?")
            for i in reversed(block):
                found = list(phrase.finditer(lines[i]))
                if found:
                    m = found[-1]
                    lines[i] = lines[i][:m.start()] + f"{m.group(1)}v{ver}, {today}" + lines[i][m.end():]
                    return "\n".join(lines)
            # Append at the END of the paragraph that names provenance (else the last one), so a
            # wrapped paragraph is never split mid-sentence.
            labelled = [p for p in paras if any(re.search(r"(?i)provenance", lines[i]) for i in range(p[0], p[1] + 1))]
            at = (labelled or paras)[-1][1]
            line = lines[at].rstrip()
            if not re.search(r"[.!?:][*_)\]]*$", line):
                line += "."
            why = reason.strip()
            if why and not why.endswith((".", "!", "?")):
                why += "."
            lines[at] = f"{line} **Re-anchored to v{ver}, {today}:** {why}".rstrip()
            return "\n".join(lines)
        if _rewrite(f, anchor):
            changed.append(f"evals/{f.name}")
    print(f"✓ {folder.name} → {ver}: {', '.join(changed) or 'already at this version'}")
    return 0


def _frontmatter(p: Path) -> str:
    return p.read_text(encoding="utf-8").split("---")[1]


def _norm(p: Path) -> str:
    """File text with line endings normalised — a CRLF working tree vs an LF clone is
    not drift, and reporting it as such trains the reader to ignore the detector."""
    return p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


# Runtime/VCS artefacts that exist on one side by design — never drift.
# `.in_use` is the plugin manager's live-session marker directory, not shipped content.
PARITY_SKIP = {".in_use", ".DS_Store", ".git", "__pycache__"}

def _shipped(root: Path):
    """Every file that ships from a pack root, relative to it."""
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix == ".pyc" or PARITY_SKIP.intersection(p.parts) or p.name in PARITY_SKIP:
            continue
        yield p.relative_to(root)


def _compare_tree(repo_root: Path, inst_root: Path, label: str) -> int:
    """Diff every shipped file, not just SKILL.md frontmatter. Returns the drift count.

    Frontmatter-only was the original scope and it under-reported twice: it reported clean
    while `ledger.md` and `spec.md` in the loaded copy lagged a post-tag commit, because a
    reference doc, README, ledger or spec is not frontmatter and was never compared.
    """
    drift = []
    for rel in _shipped(repo_root):
        inst = inst_root / rel
        src = repo_root / rel
        if not inst.is_file():
            drift.append(f"missing: {rel.as_posix()}")
        elif _norm(src) != _norm(inst):
            drift.append(f"differs: {rel.as_posix()}")
    for rel in _shipped(inst_root):
        if (repo_root / rel).is_file():
            continue
        drift.append(f"extra:   {rel.as_posix()}")
    if drift:
        for d in drift[:20]:
            print(f"  ✗ {d}")
        if len(drift) > 20:
            print(f"  … and {len(drift) - 20} more")
    else:
        print(f"  ✓ {label}: every shipped file matches repo HEAD")
    return len(drift)


def parity(packs: dict[str, str]) -> int:
    """Diff every shipped file in both installed copies vs repo HEAD (owner-machine detector).

    TWO surfaces drift independently, and checking only the first is how a session kept
    loading a superseded member while this command reported clean (2026-08-01, promptwright
    1.1.0):

      clone — ~/.claude/plugins/marketplaces/<mkt>, a git clone that moves only on
              /plugin marketplace update. It served pre-1.1.0 descriptions for a month.
      cache — ~/.claude/plugins/cache/<mkt>/<pack>/<version>/, the copy Claude Code actually
              LOADS, written only on /plugin install|update. A refreshed clone does not move
              it: the clone is where an update reads FROM, the cache is what it writes TO,
              so clone-clean and cache-stale is a real and silent state.

    Note the cache flattens the pack root — `skills/<member>/`, not `packs/<pack>/skills/`.
    Each surface skips cleanly when absent (CI-safe).

    Scope is EVERY shipped file, not just SKILL.md frontmatter. The narrow version reported
    clean twice while the loaded copy was stale, because the files that lagged — `ledger.md`,
    `spec.md` — are not frontmatter and were never compared. Line endings are normalised: a
    CRLF working tree against an LF clone is not drift.
    """
    home = Path.home() / ".claude" / "plugins"
    mkt = home / "marketplaces" / "revenantworks"
    drifted = 0
    checked = 0

    if not mkt.is_dir():
        print("clone: no local marketplace clone — skipped (nothing installed here)")
    else:
        checked += 1
        print("clone — ~/.claude/plugins/marketplaces/revenantworks")
        for pack in packs:
            drifted += _compare_tree(PACKS / pack, mkt / "packs" / pack, f"clone:{pack}")

    installed = home / "installed_plugins.json"
    if not installed.is_file():
        print("cache: no installed_plugins.json — skipped (no plugin installed here)")
    else:
        entries = json.loads(installed.read_text(encoding="utf-8")).get("plugins", {})
        for pack in packs:
            recs = entries.get(f"{pack}@revenantworks") or []
            if not recs:
                print(f"cache: {pack} not installed — skipped")
                continue
            checked += 1
            for rec in recs:
                root = Path(rec.get("installPath", ""))
                print(f"cache — {root} ({rec.get('scope', '?')} scope, v{rec.get('version', '?')})")
                if not root.is_dir():
                    print(f"  ✗ {pack}: installPath does not exist"); drifted += 1
                    continue
                drifted += _compare_tree(PACKS / pack, root, "loaded copy")

    # junction — ~/.claude/skills/<member>, the rig's load path since 2026-08-17:
    # members junction straight into this working tree and the plugin clone and
    # cache above are absent by design there, so without this surface the command
    # reported "nothing installed here — skipped" on the one machine that loads
    # every member (sweep finding 2026-08-23: the gate had gone vacuous). A
    # junction that resolves into this tree cannot drift; what CAN go stale is a
    # member present as a real copy, or a link that resolves somewhere else —
    # those get the full tree compare. Skips cleanly where ~/.claude/skills is
    # absent or holds no member (CI, other clones).
    skills_root = Path.home() / ".claude" / "skills"
    if skills_root.is_dir():
        for pack in packs:
            pack_skills = PACKS / pack / "skills"
            if not pack_skills.is_dir():
                continue
            members = [d for d in sorted(pack_skills.iterdir()) if d.is_dir()]
            present = [m for m in members if (skills_root / m.name).exists()]
            if not present:
                continue
            checked += 1
            print(f"junction — ~/.claude/skills ({pack}: {len(present)}/{len(members)} members present)")
            linked = 0
            for m in members:
                inst = skills_root / m.name
                if not inst.exists():
                    print(f"  ✗ {m.name}: not installed"); drifted += 1
                    continue
                try:
                    resolved = inst.resolve()
                except OSError:
                    print(f"  ✗ {m.name}: junction does not resolve"); drifted += 1
                    continue
                if resolved == m.resolve():
                    linked += 1
                    continue
                drifted += _compare_tree(m, inst, f"copy:{m.name}")
            if linked:
                print(f"  ✓ {linked}/{len(members)} members junction into this tree")

    if not checked:
        print("parity: nothing installed here — skipped")
        return 0
    print("parity:", f"DRIFT ({drifted}) — for plugin surfaces refresh the clone "
          f"(/plugin marketplace update revenantworks) THEN the loaded copy "
          f"(claude plugin update <pack>@revenantworks); for a junction surface, re-link "
          f"the member or fold the stale copy back into this tree"
          if drifted else "clean")
    return 1 if drifted else 0


def _descriptions(rosters: dict[str, list[str]]) -> dict[str, str]:
    """{member: frontmatter description} for every rostered member whose SKILL.md exists."""
    out: dict[str, str] = {}
    for pack, roster in rosters.items():
        for member in roster:
            f = PACKS / pack / "skills" / member / "SKILL.md"
            if f.is_file():
                m = re.search(r"^description:\s*(.*)$", _frontmatter(f), re.M)
                out[member] = m.group(1) if m else ""
    return out


def _member_dirs(skills_dir: Path) -> list[str]:
    """Names of the member folders under one pack's skills/ (hidden and _-prefixed skipped)."""
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))


def main() -> int:
    # One set of accumulators per run (unit FXL2): tests call main() repeatedly and call the
    # validators directly, so clear before any early return. problems/warnings are left alone:
    # callers slice them around a call (test_build_split.capture).
    COUNTS_FORM_MISSING.clear()
    FOOTPRINTS.clear()
    text = registry_text()
    packs = registry_packs(text)
    packs = {p: prof for p, prof in packs.items() if (PACKS / p).is_dir() or pack_members(text, p)}
    if NEW_PACK:
        return new_pack(*NEW_PACK)
    if BUMP:
        return bump_pack(*BUMP)
    if BUMP_MEMBER:
        member, ver, reason = BUMP_MEMBER
        found = sorted(PACKS.glob(f"*/skills/{member}"))
        if len(found) != 1:
            print(f"✗ {member!r}: {len(found)} matching member folders under packs/*/skills/"); return 1
        return bump_member(found[0], ver, reason)
    if PARITY:
        return parity(packs)
    check_marketplace(packs)
    mods = check_mods()
    print(f"mods: {mods} mod-only plugin(s) checked")

    total_members = total_folders = total_manifests = 0
    versions: dict[str, tuple[Path, str]] = {}
    synced = drift = 0
    rosters = {p: [m for m, _, _ in pack_members(text, p)] for p in packs}
    planned = registry_planned(text)
    cross = validate_cross_pack(cross_pack_seams(text), rosters, planned)
    print(f"registry[cross-pack]: {len(cross)} seams · {len(planned)} planned")
    descs = _descriptions(rosters)
    for left, right, cell in cross_pack_seams(text):
        validate_cold_listing("cross-pack", left, right, cell, descs)

    for pack, profile_notes in packs.items():
        profile = profile_notes.split(" ")[0] if profile_notes else "standalone"
        members = pack_members(text, pack)
        seams = pack_seams(text, pack)
        budgets = pack_budgets(text, pack)
        cap, repo, conf = pack_lines(text, pack, registry_pack_notes(text, pack))
        print(f"registry[{pack}]: {len(members)} members · {len(seams)} seams")
        validate_seams(pack, [m for m, _, _ in members], seams, planned)
        for left, right, _, _, _, cold in seams:
            validate_cold_listing(pack, left, right, cold, descs)
        validate_registry_counts(text, pack, rosters)
        pack_md = render_pack_md(pack, profile, members, cap, repo, conf, seams, pack_seam_note(text, pack),
                                 cross_rows_for(pack, cross), planned)
        skills_dir = PACKS / pack / "skills"
        folders = [skills_dir / m for m, _, _ in members]
        missing = [f.name for f in folders if not f.is_dir()]
        no_native: list[str] = []
        for nm in missing:
            fail(f"[{pack}] member in registry but not in packs/{pack}/skills/: {nm}")
        # The reverse direction (controller item, 2026-10-01): a folder the roster does not list
        # used to be skipped silently, and "folders" was derived from the roster, so count
        # integrity read 17 = 17 with an unregistered folder present. Folders are now counted
        # on disk and an unlisted one fails.
        on_disk = _member_dirs(skills_dir)
        roster_names = {m for m, _, _ in members}
        for nm in on_disk:
            if nm not in roster_names:
                fail(f"[{pack}] member folder packs/{pack}/skills/{nm}/ is not in the registry — add its row "
                     f"to **{pack} members** (and **{pack} budgets**), or remove the folder")
        total_members += len(members)
        total_folders += len(on_disk)
        # Pack-shared copies before the per-member checks, so a body or footprint read sees the
        # regenerated file (owner Q2: build.py writes the shared GPU check copies).
        n_shared = sync_shared(pack, [m for m, _, _ in members], ROOT, write=not CHECK and not FOOTPRINT,
                               report_only=FOOTPRINT)
        if n_shared:
            print(f"registry[{pack}]: {n_shared} shared cop{'y' if n_shared == 1 else 'ies'} from packs/{pack}/shared/")
        n_notice = sync_member_notice(pack, [m for m, _, _ in members], ROOT, write=not CHECK and not FOOTPRINT,
                                      report_only=FOOTPRINT)
        if n_notice:
            print(f"registry[{pack}]: {n_notice} member NOTICE cop{'y' if n_notice == 1 else 'ies'} "
                  f"from packs/{pack}/NOTICE")
        for folder in folders:
            if not folder.is_dir():
                continue
            target = folder / "references" / "pack.md"
            current = target.read_text(encoding="utf-8") if target.exists() else ""
            strip = lambda s: re.sub(r"Last stamped: [\d-]+", "Last stamped: X", s)
            if strip(current) != strip(pack_md):
                drift += 1
                if CHECK:
                    fail(f"{folder.name}: references/pack.md drifts from the registry")
                elif FOOTPRINT:  # report only: --footprint used to sync manifests as a side effect
                    warn(f"{folder.name}: references/pack.md drifts from the registry — run tools/build.py "
                         f"to sync it (--footprint writes nothing)")
                else:
                    _write_text(target, pack_md)  # bytes, own line ending (observation 0220)
                    synced += 1
                    print(f"  ✎ synced {folder.name}/references/pack.md")
            validate_seam_manifest(folder, len(seams))
            validate_script_declarations(pack, registry_pack_notes(text, pack), folder)
            total_manifests += 1
            versions[folder.name] = (skills_dir, validate_skill(folder, budgets.get(folder.name)))
            if not validate_native_evals(folder / "evals", folder.name):
                no_native.append(folder.name.rsplit("-", 1)[-1])
        if not FOOTPRINT:  # the generated pack suite (unit EVG); --footprint ignores it
            n_cases = sync_pack_evals(pack, [m for m, _, _ in members], ROOT, write=not CHECK)
            if n_cases:
                print(f"registry[{pack}]: {n_cases} eval case(s) in packs/{pack}/{PACK_EVAL_DIR}/")
        validate_native_evals(PACKS / pack / PACK_EVAL_DIR, f"[{pack}] plugin")  # the generated pack suite
        if no_native:
            # Advisory until the native suites land (A6 tightens it): the hand-run evals/*.md
            # suites stay valid, but `claude plugin eval` has nothing to run for these members.
            warn(f"[{pack}] {len(no_native)}/{len(members)} member(s) carry no native `claude plugin eval` "
                 f"suite (evals/<case>/prompt.md + graders/*.md): {', '.join(no_native)}")

    for pdir in sorted(p for p in PACKS.iterdir() if p.is_dir()) if PACKS.is_dir() else []:
        if pdir.name in packs:
            continue
        for nm in _member_dirs(pdir / "skills"):
            if REGISTRY.is_relative_to(pdir / "skills" / nm):
                continue  # the registry's own home (a test tree registers no pack around it)
            total_folders += 1
            fail(f"member folder packs/{pdir.name}/skills/{nm}/ sits in a pack the registry does not list "
                 f"({pdir.name}) — register the pack (build.py --new-pack) or move the folder")

    if COUNTS_FORM_MISSING and not FOOTPRINT:
        warn(f"{len(COUNTS_FORM_MISSING)} trigger suite(s) lack the fixed count line `Counts: N queries "
             f"(S should, T should-not, P pairs[, Q injection probes])`: {', '.join(m.rsplit('-', 1)[-1] for m in COUNTS_FORM_MISSING)}")

    if not FOOTPRINT:
        # After the pack.md sync, so a featured copy carries the freshly generated manifest.
        n_featured = sync_featured(registry_featured(text), rosters, ROOT, write=not CHECK)
        print(f"featured: {n_featured} one-skill plugin(s)")

    if FOOTPRINT:
        print()
        print("footprint — SKILL.md body + every-run references (files every entry reads, any form)")
        print("            vs registry budget (chars/4, ±15%)")
        print()
        print(f"  {'member':<14} {'body':>6} {'+every':>7} {'=load':>7}  {'budget':>7}  headroom")
        tot = 0
        for member in sorted(FOOTPRINTS):
            body, budget, refs = FOOTPRINTS[member]
            extra = sum(t for _, t in refs)
            load = body + extra
            tot += load
            short = member.split("-")[-1]
            cols = f"  {short:<14} {body:>6} {('+' + str(extra)) if extra else '':>7} {load:>7}"
            if budget is None:
                print(f"{cols}  {'—':>7}  (no budget row)")
                continue
            head = budget - load
            flag = "  ← OVER" if head < 0 else ("  ← thin" if head < 200 else "")
            print(f"{cols}  /{budget:>6}  {head:>+6}{flag}")
            # The over-budget warning is validate_skill's, so --check and --footprint agree.
        print()
        print(f"  {'TOTAL':<14} {tot:>6} tokens across {len(FOOTPRINTS)} members — the whole-pack"
              f" figure, not a per-session cost: members load one at a time.")

    if not CHECK and not FOOTPRINT and not problems:
        DIST.mkdir(exist_ok=True)
        for member, (skills_dir, ver) in versions.items():
            if ONLY and member != ONLY:
                continue
            folder = skills_dir / member
            out = DIST / f"{member}-{ver}.zip"
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for p in sorted(folder.rglob("*")):
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                        z.write(p, p.relative_to(skills_dir))
            print(f"  ▣ dist/{out.name}")
            # Prune this member's superseded builds. Without it dist/ accumulates one zip
            # per version ever built, and release-doctrine treats these as the upload
            # source of truth — so a stale neighbour is a mis-upload waiting to happen.
            for old in DIST.glob(f"{member}-*.zip"):
                if old != out:
                    old.unlink()
                    print(f"  ✗ dist/{old.name} (superseded)")

    if CHECK:
        bump_needed(packs, {m: (d, v) for m, (d, v) in versions.items() if v})

    print(f"\ncount integrity: registry {total_members} = folders {total_folders} = manifests {total_manifests}")
    if warnings:
        print(f"warnings: {len(warnings)} (deliberate drift/advisory signals — non-fatal by design)")
    if CHECK:
        print("check:", "DRIFT/PROBLEMS — see above" if (problems or drift) else "clean")
        return 1 if (problems or drift) else 0
    print("build:", "PROBLEMS — see above" if problems else f"ok ({synced} manifest(s) synced)")
    return 1 if problems else 0


if __name__ == "__main__":
    apply_args(parse_args(sys.argv[1:]))
    sys.exit(main())
