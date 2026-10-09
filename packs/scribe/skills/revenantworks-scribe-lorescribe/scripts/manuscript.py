"""lorescribe manuscript mode helper. Python 3 standard library only; no network.

Read-only on chapter files. Writes only into the ledger folder it is given (chunk: --out;
ground, collate, rehash: the folder that holds the ledger). Rows in a ledger are model output
and are treated as untrusted: a row's path may not leave the chapters root.

Subcommands
  chunk    <chapters dir | manuscript file> --out DIR [--target 3000] [--cap 4000] [--min-count 1]
  ground   <ledger.jsonl> --root CHAPTERS_DIR
  collate  <grounded.jsonl>
  rehash   <chunks.json> <grounded.jsonl>
  cast     <grounded.jsonl> [--chapters-dir chapters]
  evidence <story-skills continuity --json report>
  score    <grounded.jsonl> <truth.json>   truth: {"entities": [{"name", "aliases"}], "allowed_extras": [names]}

Exit codes: 0 clean, 1 findings (ungrounded rows, contradictions, changed chapters, errors in
evidence), 2 usage error. Reference: references/manuscript-mode.md.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SCENE_BREAK = re.compile(r"^\s*(\*\s*\*\s*\*|#|~{3,}|-{3,}|_{3,}|\*{3,})\s*$")
ATX = re.compile(r"^\s{0,3}#{1,6}\s+\S")
SETEXT = re.compile(r"^\s{0,3}(=+|-+)\s*$")
CHAPTER_LINE = re.compile(
    r"^\s*(chapter|ch\.|part|book)\s+([0-9]+|[ivxlcdm]+|[a-z]+(-[a-z]+)?)\b.*$|"
    r"^\s*(prologue|epilogue|interlude)\b.*$", re.IGNORECASE)
WORD = re.compile(r"[^\W\d_][^\W\d_'’]*")
STATE_FIELDS = {"state", "status", "location", "holder", "age"}


class UsageError(Exception):
    pass


def tokens(text):
    return (len(text) + 3) // 4


def natural_key(name):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def fold(text):
    text = unicodedata.normalize("NFKC", str(text)).lower()
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("—", "-"), ("–", "-")):
        text = text.replace(a, b)
    text = text.replace("*", "").replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", fold(name)).strip("-")


def read_lines(path):
    return Path(path).read_text(encoding="utf-8").splitlines()


def read_jsonl(path):
    p = Path(path)
    if not p.is_file():
        raise UsageError(f"not a file: {path}")
    rows = []
    for n, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if raw.strip():
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise UsageError(f"{p.name}:{n}: not JSON ({exc.msg})")
    return rows


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------- chunk ----------

def is_heading(lines, i):
    line = lines[i]
    if ATX.match(line):
        return True
    if i + 1 < len(lines) and line.strip() and SETEXT.match(lines[i + 1]) and not SCENE_BREAK.match(line):
        return lines[i + 1].strip().startswith("=")
    prev_blank = i == 0 or not lines[i - 1].strip()
    next_blank = i + 1 >= len(lines) or not lines[i + 1].strip()
    return bool(prev_blank and next_blank and CHAPTER_LINE.match(line))


def chapter_units(src):
    """Return (root, units). A folder: one unit per text file. One file: split on chapter lines."""
    src = Path(src)
    if src.is_dir():
        files = sorted((p for p in src.iterdir() if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES),
                       key=lambda p: natural_key(p.name))
        units = []
        for p in files:
            n = len(read_lines(p))
            units.append({"file": p.name, "start_line": 1, "end_line": max(n, 1)})
        return src, units
    if not src.is_file():
        raise UsageError(f"not found: {src}")
    lines = read_lines(src)
    starts = [i for i in range(len(lines)) if is_heading(lines, i)] or [0]
    if starts[0] != 0 and any(x.strip() for x in lines[:starts[0]]):
        starts.insert(0, 0)
    units = []
    for k, s in enumerate(starts):
        e = (starts[k + 1] if k + 1 < len(starts) else len(lines)) - 1
        while e > s and not lines[e].strip():
            e -= 1
        units.append({"file": src.name, "start_line": s + 1, "end_line": e + 1})
    return src.parent, units


def paragraphs(lines, start, end):
    """Yield (first_line, last_line, text, is_break) for blank-line separated blocks (1-based)."""
    i = start - 1
    while i < end:
        if not lines[i].strip():
            i += 1
            continue
        j = i
        while j + 1 < end and lines[j + 1].strip():
            j += 1
        text = "\n".join(lines[i:j + 1])
        yield i + 1, j + 1, text, bool(SCENE_BREAK.match(text))
        i = j + 1


def chunk_unit(lines, unit, target, cap):
    out, cur = [], None
    for first, last, text, brk in paragraphs(lines, unit["start_line"], unit["end_line"]):
        t = tokens(text)
        if brk:
            if cur and cur["est_tokens"] >= target // 2:
                out.append(cur)
                cur = None
            continue
        if cur and cur["est_tokens"] + t > target:
            out.append(cur)
            cur = None
        if cur is None:
            cur = {"file": unit["file"], "start_line": first, "end_line": last, "est_tokens": 0}
        cur["end_line"] = last
        cur["est_tokens"] += t
        if t > cap:
            cur["oversize"] = True
    if cur:
        out.append(cur)
    return out


def name_scan(root, units, chunks, min_count):
    counts, first, seen_lower, where = {}, {}, set(), {}
    cache = {}
    for u in units:
        lines = cache.setdefault(u["file"], read_lines(root / u["file"]))
        for n in range(u["start_line"], u["end_line"] + 1):
            line = lines[n - 1]
            heading = bool(ATX.match(line)) or bool(CHAPTER_LINE.match(line))
            for m in WORD.finditer(line):
                w = m.group(0).rstrip("'’")
                if not w[0].isupper():
                    seen_lower.add(w.lower())
                    continue
                if heading or len(w) < 2 or w.isupper():
                    continue
                counts[w] = counts.get(w, 0) + 1
                first.setdefault(w, f"{u['file']}:{n}")
                for c in chunks:
                    if c["file"] == u["file"] and c["start_line"] <= n <= c["end_line"]:
                        where.setdefault(w, [])
                        if c["id"] not in where[w]:
                            where[w].append(c["id"])
    names = [{"name": w, "count": k, "first": first[w], "chunks": where.get(w, [])}
             for w, k in counts.items() if k >= min_count and w.lower() not in seen_lower]
    return sorted(names, key=lambda x: (-x["count"], x["name"]))


def cmd_chunk(a):
    root, units = chapter_units(a.source)
    out, src = Path(a.out).resolve(), Path(a.source).resolve()
    if out == root.resolve() or out.is_relative_to(src):
        raise UsageError("refusing to write the ledger over the manuscript or inside the chapters folder; "
                         "name another --out")
    if a.target < 100 or a.cap < a.target:
        raise UsageError("--target must be >= 100 and --cap >= --target")
    out.mkdir(parents=True, exist_ok=True)
    chunks, cache = [], {}
    for u in units:
        lines = cache.setdefault(u["file"], read_lines(root / u["file"]))
        chunks.extend(chunk_unit(lines, u, a.target, a.cap))
    for k, c in enumerate(chunks, 1):
        c["id"] = f"c{k:03d}"
    files = []
    for u in units:
        if u["file"] not in files:
            files.append(u["file"])
    plan = {
        "root": str(root.resolve()), "source_kind": "folder" if Path(a.source).is_dir() else "file",
        "target": a.target, "cap": a.cap,
        "chapters": [{"file": f, "sha256": sha256(root / f), "lines": len(cache[f])} for f in files],
        "units": units, "chunks": chunks,
        "names": name_scan(root, units, chunks, a.min_count),
    }
    (out / "chunks.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"chapters": len(files), "units": len(units), "chunks": len(chunks),
                      "est_tokens": sum(c["est_tokens"] for c in chunks),
                      "oversize": sum(1 for c in chunks if c.get("oversize")),
                      "names": len(plan["names"]), "plan": "chunks.json"}))
    return 0


# ---------- ground ----------

def parse_at(at):
    m = re.match(r"^(.+):(\d+)$", str(at or ""))
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def safe_path(root, rel):
    if not rel or Path(rel).is_absolute() or re.match(r"^[a-zA-Z]:", rel):
        return None
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p


def quote_at(lines, n, quote):
    q = fold(quote).strip(" \"'")
    if not q or n < 1 or n > len(lines):
        return False
    pat = re.compile(r"(?<!\w)" + re.escape(q) + r"(?!\w)")
    window = [fold(lines[n - 1])]
    if n < len(lines):
        window.append(fold(lines[n - 1] + " " + lines[n]))
    return any(pat.search(w) for w in window)


def cmd_ground(a):
    rows = read_jsonl(a.ledger)
    root = Path(a.root).resolve()
    if not root.is_dir():
        raise UsageError(f"not a folder: {a.root}")
    good, bad, cache = [], [], {}
    for r in rows:
        rel, n = parse_at(r.get("at"))
        path = safe_path(root, rel) if rel else None
        reason = None
        if rel is None:
            reason = "no <file>:<line> in at"
        elif path is None:
            reason = "path outside the chapters root"
        elif not path.is_file():
            reason = "file not found"
        else:
            lines = cache.setdefault(path, read_lines(path))
            if not quote_at(lines, n, r.get("quote", "")):
                reason = "quote not at that line"
        if reason:
            bad.append(dict(r, ungrounded=reason))
        else:
            good.append(r)
    folder = Path(a.ledger).resolve().parent
    write_jsonl(folder / "grounded.jsonl", good)
    write_jsonl(folder / "ungrounded.jsonl", bad)
    for r in bad:
        print(f"UNGROUNDED · {r.get('at')} · \"{r.get('quote', '')}\" · {r.get('entity')}.{r.get('field')} · {r['ungrounded']}")
    print(json.dumps({"rows": len(rows), "grounded": len(good), "ungrounded": len(bad)}))
    return 1 if bad else 0


# ---------- collate ----------

def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cite(r):
    return f"{r.get('at')} · \"{r.get('quote', '')}\""


def conflicts(x, y):
    """Two rows with different values clash unless both are on different named branches."""
    bx, by = x.get("branch"), y.get("branch")
    return not (bx and by and bx != by)


def cmd_collate(a):
    rows = read_jsonl(a.ledger)
    entities, aliases, names = {}, {}, {}
    for r in rows:
        key = slug(r.get("entity", ""))
        if not key:
            continue
        names.setdefault(key, (str(r.get("entity")), r))
        field = fold(r.get("field", ""))
        if field == "alias":
            aliases.setdefault(key, set()).add(slug(r.get("value", "")))
        ent = entities.setdefault(key, {"name": str(r.get("entity")), "kind": r.get("kind"), "fields": {}})
        ent["fields"].setdefault(field, []).append(
            {k: r[k] for k in ("value", "at", "quote", "branch", "chunk") if k in r})
    findings, branch_cond = [], []
    for key, ent in sorted(entities.items()):
        for field, vals in sorted(ent["fields"].items()):
            if field in STATE_FIELDS or field == "alias":
                continue
            by_value = {}
            for v in vals:
                by_value.setdefault(fold(v.get("value", "")), []).append(v)
            keys = sorted(by_value)
            pairs_seen = set()
            for i, va in enumerate(keys):
                for vb in keys[i + 1:]:
                    hit = next(((x, y) for x in by_value[va] for y in by_value[vb] if conflicts(x, y)), None)
                    if hit:
                        x, y = hit
                        findings.append(f"SELF-CONTRA · {cite(x)} · vs {cite(y)} · entity: {key}.{field}")
                        pairs_seen.add((va, vb))
            branches = sorted({v["branch"] for v in vals if v.get("branch")})
            if len(keys) > 1 and branches and not pairs_seen:
                branch_cond.append({"entity": key, "field": field, "branches": branches,
                                    "values": [dict(v) for v in vals]})
    keys = sorted(names)
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            if kb in aliases.get(ka, set()) or ka in aliases.get(kb, set()):
                continue
            if min(len(ka), len(kb)) >= 4 and levenshtein(ka, kb) <= 2:
                ra, rb = names[ka][1], names[kb][1]
                findings.append(f"NAME-VARIANT · {ra.get('at')} · \"{names[ka][0]}\" · vs {rb.get('at')} · "
                                f"\"{names[kb][0]}\" · never merged; the user decides")
    folder = Path(a.ledger).resolve().parent
    (folder / "collated.json").write_text(json.dumps(
        {"entities": entities, "branch_conditional": branch_cond, "findings": findings},
        indent=1, ensure_ascii=False), encoding="utf-8")
    for f in findings:
        print(f)
    counts = {}
    for f in findings:
        counts[f.split(" ")[0]] = counts.get(f.split(" ")[0], 0) + 1
    print(json.dumps({"entities": len(entities), "findings": counts,
                      "branch_conditional": len(branch_cond)}))
    return 1 if findings else 0


# ---------- rehash ----------

def cmd_rehash(a):
    plan_path = Path(a.plan)
    if not plan_path.is_file():
        raise UsageError(f"not a file: {a.plan}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    root = Path(plan["root"])
    rows = read_jsonl(a.ledger)
    known = {c["file"]: c["sha256"] for c in plan["chapters"]}
    changed, missing = [], []
    for f, h in known.items():
        p = root / f
        if not p.is_file():
            missing.append(f)
        elif sha256(p) != h:
            changed.append(f)
    new = []
    if plan.get("source_kind") == "folder" and root.is_dir():
        new = sorted((p.name for p in root.iterdir() if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES
                      and p.name not in known), key=natural_key)
    out, cache, moved, stale = [], {}, 0, 0
    for r in rows:
        rel, n = parse_at(r.get("at"))
        row = dict(r)
        if rel in missing:
            row["status"] = "stale"
        elif rel not in changed:
            row["status"] = "kept"
        else:
            path = safe_path(root, rel)
            lines = cache.setdefault(rel, read_lines(path)) if path and path.is_file() else []
            if quote_at(lines, n, r.get("quote", "")):
                row["status"] = "kept"
            else:
                q = r.get("quote", "")
                hits = [k for k in range(1, len(lines) + 1) if quote_at(lines[k - 1:k], 1, q)]
                if not hits:
                    hits = [k for k in range(1, len(lines) + 1) if quote_at(lines, k, q)]
                if len(hits) == 1:
                    row["at"], row["status"] = f"{rel}:{hits[0]}", "moved"
                    moved += 1
                else:
                    row["status"] = "stale"
        if row["status"] == "stale":
            stale += 1
        out.append(row)
    write_jsonl(Path(a.ledger).resolve().parent / "rehashed.jsonl", out)
    print(json.dumps({"changed": changed, "new": new, "missing": missing, "moved": moved,
                      "stale": stale, "reread": sorted(set(changed + new))}))
    return 1 if (changed or new or missing) else 0


# ---------- cast / evidence / score ----------

def cmd_cast(a):
    rows = read_jsonl(a.ledger)
    per = {}
    for r in rows:
        if r.get("kind") != "character":
            continue
        rel, _ = parse_at(r.get("at"))
        if rel:
            per.setdefault(rel, set()).add(slug(r.get("entity", "")))
    prefix = a.chapters_dir.strip("/\\")
    for k, rel in enumerate(sorted(per, key=natural_key), 1):
        path = rel if not prefix or rel.startswith(prefix + "/") else f"{prefix}/{rel}"
        ids = ", ".join(sorted(per[rel]))
        print(f"PROPOSAL {k} · edit · {path}\nwhy: cast seen in grounded manuscript rows\n"
              f"change: frontmatter mentions: [{ids}]  (move a name to characters: only if present on the page)\n"
              f"level: soft   breaks: none\n")
    return 0


def find_items(data):
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict) and "code" in x]
    if isinstance(data, dict):
        for v in data.values():
            items = find_items(v)
            if items:
                return items
    return []


def cmd_evidence(a):
    p = Path(a.report)
    if not p.is_file():
        raise UsageError(f"not a file: {a.report}")
    try:
        items = find_items(json.loads(p.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise UsageError(f"report is not JSON ({exc.msg})")
    errors = 0
    for d in items:
        where = d.get("file", "?") + (f" ({d['chapter']})" if d.get("chapter") else "")
        line = f"STORY-SKILLS · {d.get('code')} · {where} · {d.get('message', '')} · {d.get('severity', '?')}"
        if d.get("exemption"):
            line += f" · dismissed: {d['exemption']}"
        elif d.get("severity") == "error":
            errors += 1
        print(line)
    print(json.dumps({"items": len(items), "open_errors": errors}))
    return 1 if errors else 0


def cmd_score(a):
    rows = read_jsonl(a.ledger)
    tp = Path(a.truth)
    if not tp.is_file():
        raise UsageError(f"not a file: {a.truth}")
    data = json.loads(tp.read_text(encoding="utf-8"))
    truth = data["entities"]
    # allowed_extras: real but unkeyed entities (a common-noun object, an unnamed role) that the
    # key accepts; they leave the extras count and the named-key precision denominator.
    allowed = {slug(n) for n in data.get("allowed_extras", [])}
    lookup = {}
    for t in truth:
        for n in [t["name"]] + list(t.get("aliases", [])):
            lookup[slug(n)] = t["name"]
    found = {slug(r.get("entity", "")) for r in rows if r.get("entity")}
    hit = {lookup[f] for f in found if f in lookup}
    matched = sum(1 for f in found if f in lookup)
    allowed_found = sorted(f for f in found if f not in lookup and f in allowed)
    extra = sorted(f for f in found if f not in lookup and f not in allowed)
    recall = len(hit) / len(truth) if truth else 0.0
    precision = matched / len(found) if found else 0.0
    named = matched / (matched + len(extra)) if (matched + len(extra)) else 0.0
    print(json.dumps({"truth": len(truth), "extracted": len(found), "recall": round(recall, 4),
                      "precision": round(precision, 4),
                      "named_key_precision": round(named, 4),
                      "missed": sorted(t["name"] for t in truth if t["name"] not in hit),
                      "extra": extra, "allowed_extra": allowed_found}))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="manuscript.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")
    c = sub.add_parser("chunk")
    c.add_argument("source")
    c.add_argument("--out", required=True)
    c.add_argument("--target", type=int, default=3000)
    c.add_argument("--cap", type=int, default=4000)
    c.add_argument("--min-count", type=int, default=1)
    g = sub.add_parser("ground")
    g.add_argument("ledger")
    g.add_argument("--root", required=True)
    sub.add_parser("collate").add_argument("ledger")
    r = sub.add_parser("rehash")
    r.add_argument("plan")
    r.add_argument("ledger")
    k = sub.add_parser("cast")
    k.add_argument("ledger")
    k.add_argument("--chapters-dir", default="chapters")
    sub.add_parser("evidence").add_argument("report")
    s = sub.add_parser("score")
    s.add_argument("ledger")
    s.add_argument("truth")
    return p


COMMANDS = {"chunk": cmd_chunk, "ground": cmd_ground, "collate": cmd_collate, "rehash": cmd_rehash,
            "cast": cmd_cast, "evidence": cmd_evidence, "score": cmd_score}


def main(argv=None):
    parser = build_parser()
    try:
        a = parser.parse_args(argv)
    except SystemExit:
        return 2
    if not a.cmd:
        parser.print_usage(sys.stderr)
        return 2
    try:
        return COMMANDS[a.cmd](a)
    except UsageError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
