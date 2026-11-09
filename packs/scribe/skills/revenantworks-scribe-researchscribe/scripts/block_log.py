#!/usr/bin/env python3
"""Counts-only log of fetch refusals and failures for researchscribe (stdlib only).

Each line of the log is JSON: {"d": "YYYY-MM-DD", "host": "example.org",
"code": "ROBOTS_REFUSED", "n": 1}. A host is a bare hostname: a path, query,
port, user part or anything else is refused, so no page address or user data
can enter the log. The log sits outside every repo.

    python scripts/block_log.py add <host> <CODE> [--n N] [--date YYYY-MM-DD]
    python scripts/block_log.py ingest <workflow-result.json> [--date YYYY-MM-DD]
    python scripts/block_log.py report [--days 30] [--today YYYY-MM-DD]

Path: RESEARCHSCRIBE_BLOCK_LOG when set, else ~/.claude/researchscribe/block-log.jsonl.
`report` lists hosts by refusal count; a host with 3 or more refusals in the
window is marked "add a route" for the next refresh (references/source-routes.md).
"""
import datetime
import json
import os
import re
import sys

CODES = {
    "HTTP_403", "HTTP_404", "HTTP_429", "HTTP_5XX",
    "ROBOTS_REFUSED", "SITE_BLOCKED", "BOT_CHALLENGE", "LOGIN_PAYWALL",
    "JS_EMPTY", "TOO_LARGE", "REDIRECT_CROSS_HOST", "TIMEOUT", "OTHER",
}
REFUSALS = {"HTTP_403", "HTTP_429", "ROBOTS_REFUSED", "SITE_BLOCKED",
            "BOT_CHALLENGE", "LOGIN_PAYWALL"}
HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FLAG_AT = 3


def log_path():
    return os.environ.get("RESEARCHSCRIBE_BLOCK_LOG") or os.path.join(
        os.path.expanduser("~"), ".claude", "researchscribe", "block-log.jsonl")


def clean_host(host):
    h = (host or "").strip().lower().rstrip(".")
    if not HOST_RE.match(h):
        raise ValueError(f"not a bare hostname: {host!r} (no scheme, path, port or query)")
    return h


def clean_code(code):
    c = (code or "").strip().upper()
    if c not in CODES:
        raise ValueError(f"unknown outcome code {code!r}; one of {sorted(CODES)}")
    return c


def clean_date(d):
    if d is None:
        return datetime.date.today().isoformat()
    if not DATE_RE.match(d):
        raise ValueError(f"date must be YYYY-MM-DD: {d!r}")
    datetime.date.fromisoformat(d)
    return d


def append(entries, path=None):
    path = path or log_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    return len(entries)


def entry(host, code, n=1, date=None):
    n = int(n)
    if n < 1:
        raise ValueError("count must be at least 1")
    return {"d": clean_date(date), "host": clean_host(host), "code": clean_code(code), "n": n}


def from_workflow(result, date=None):
    """Entries from a research workflow result's block_stats.by_host."""
    stats = (result or {}).get("block_stats") or {}
    by_host = stats.get("by_host") or {}
    out = []
    for host in sorted(by_host):
        for code in sorted(by_host[host]):
            out.append(entry(host, code, by_host[host][code], date or result.get("date")))
    return out


def read(path=None):
    path = path or log_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                rows.append(entry(e["host"], e["code"], e.get("n", 1), e["d"]))
            except (ValueError, KeyError, TypeError):
                continue  # a malformed line is skipped, never repaired
    return rows


def summarise(rows, days=30, today=None):
    today = datetime.date.fromisoformat(today) if today else datetime.date.today()
    start = today - datetime.timedelta(days=days)
    hosts = {}
    for e in rows:
        if datetime.date.fromisoformat(e["d"]) < start:
            continue
        h = hosts.setdefault(e["host"], {"refusals": 0, "other": 0, "codes": {}})
        h["codes"][e["code"]] = h["codes"].get(e["code"], 0) + e["n"]
        if e["code"] in REFUSALS:
            h["refusals"] += e["n"]
        else:
            h["other"] += e["n"]
    return hosts


def report(rows, days=30, today=None):
    hosts = summarise(rows, days, today)
    lines = [f"block log, last {days} days: {len(hosts)} host(s)"]
    for host in sorted(hosts, key=lambda k: (-hosts[k]["refusals"], -hosts[k]["other"], k)):
        h = hosts[host]
        codes = ", ".join(f"{c} {n}" for c, n in sorted(h["codes"].items()))
        flag = "  <- add a route at refresh" if h["refusals"] >= FLAG_AT else ""
        lines.append(f"{host}: {h['refusals']} refusal(s), {h['other']} other ({codes}){flag}")
    return "\n".join(lines)


def main(argv):
    args = argv[1:]
    if not args or args[0] not in ("add", "ingest", "report"):
        print(__doc__)
        return 2

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    try:
        if args[0] == "add":
            if len(args) < 3:
                print("add needs <host> <CODE>", file=sys.stderr)
                return 2
            n = append([entry(args[1], args[2], opt("--n", 1), opt("--date"))])
            print(f"logged {n} line")
            return 0
        if args[0] == "ingest":
            if len(args) < 2:
                print("ingest needs a workflow result file", file=sys.stderr)
                return 2
            with open(args[1], encoding="utf-8") as fh:
                result = json.load(fh)
            n = append(from_workflow(result, opt("--date")))
            print(f"logged {n} line(s)")
            return 0
        print(report(read(), int(opt("--days", 30)), opt("--today")))
        return 0
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
