#!/usr/bin/env python3
"""Score fetch-probe results for block rate and source quality (stdlib only).

A probe file is JSON: {"probed": "YYYY-MM-DD", "rows": [{"id", "round", "set",
"family", "url", "outcome", "tier"}, ...]}. One row is one fetch-tool call.
`outcome` is OK or a refusal or failure code (see OUTCOMES); `tier` is 1-5 per
references/source-routes.md section 1.

    python scripts/source_eval.py score evals/fixtures/probe-2026-11-09.json
    python scripts/source_eval.py compare FILE --before r1:primary-html,r1:naive-api \
        --after validation:routed --gate
    python scripts/source_eval.py routes references/route-health.json

`score` prints one line per round:set. `compare` prints both sides and, with
--gate, exits 1 when the after side blocks more or reads fewer tier 1-2 sources
than the before side. `routes` exits 1 when a family's leading route in route-health.json
is not ok or built, a later first route is worse than flaky, or an avoid
route is marked ok. Nothing here fetches anything: probes are run
with the fetch tool and written to the file by hand or by the refresh entry.
"""
import json
import sys

OUTCOMES = {
    "OK",
    "HTTP_403", "HTTP_404", "HTTP_429", "HTTP_5XX",
    "ROBOTS_REFUSED", "SITE_BLOCKED", "BOT_CHALLENGE", "LOGIN_PAYWALL",
    "JS_EMPTY", "TOO_LARGE", "REDIRECT_CROSS_HOST", "TIMEOUT", "OTHER",
}
# A refusal: the site or the tool said no. Retrying or rerouting is barred.
REFUSALS = {"HTTP_403", "HTTP_429", "ROBOTS_REFUSED", "SITE_BLOCKED",
            "BOT_CHALLENGE", "LOGIN_PAYWALL"}


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data.get("rows", [])
    for r in rows:
        if r.get("outcome") not in OUTCOMES:
            raise ValueError(f"row {r.get('id')}: unknown outcome {r.get('outcome')!r}")
        if r.get("tier") not in (1, 2, 3, 4, 5):
            raise ValueError(f"row {r.get('id')}: tier must be 1-5")
    return rows


def stats(rows):
    n = len(rows)
    read = [r for r in rows if r["outcome"] == "OK"]
    refused = [r for r in rows if r["outcome"] in REFUSALS]
    top = [r for r in read if r["tier"] <= 2]
    junk = [r for r in read if r["tier"] == 5]
    pct = lambda a, b: round(100.0 * a / b, 1) if b else 0.0
    return {
        "fetches": n,
        "not_read": n - len(read),
        "refused": len(refused),
        "block_rate": pct(n - len(read), n),
        "refusal_rate": pct(len(refused), n),
        "reads_tier_1_2": pct(len(top), len(read)),
        "reads_tier_5": pct(len(junk), len(read)),
    }


def select(rows, keys):
    want = set()
    for k in keys:
        rnd, _, st = k.partition(":")
        want.add((rnd, st))
    return [r for r in rows if (r["round"], r["set"]) in want]


def line(label, s):
    return (f"{label}: {s['fetches']} fetches, {s['not_read']} not read "
            f"({s['block_rate']}%; refusals {s['refusal_rate']}%), "
            f"tier 1-2 {s['reads_tier_1_2']}% of reads, tier 5 {s['reads_tier_5']}%")


def cmd_score(path):
    rows = load(path)
    groups = []
    for r in rows:
        k = f"{r['round']}:{r['set']}"
        if k not in groups:
            groups.append(k)
    for k in groups:
        print(line(k, stats(select(rows, [k]))))
    return 0


def cmd_compare(path, before, after, gate):
    rows = load(path)
    b = stats(select(rows, before.split(",")))
    a = stats(select(rows, after.split(",")))
    if not b["fetches"] or not a["fetches"]:
        print("compare: a side selected no rows", file=sys.stderr)
        return 2
    print(line("before", b))
    print(line("after ", a))
    if gate and (a["block_rate"] > b["block_rate"] or a["reads_tier_1_2"] < b["reads_tier_1_2"]):
        print("gate: FAIL (after blocks more or reads fewer tier 1-2 sources)")
        return 1
    if gate:
        print("gate: PASS")
    return 0


def cmd_routes(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    bad = []
    for fam in data.get("families", []):
        first = fam.get("first", [])
        if not first:
            bad.append(f"{fam['family']}: no first route")
        for i, route in enumerate(first):
            allowed = ("ok", "built") if i == 0 else ("ok", "built", "flaky")
            if route.get("status") not in allowed:
                bad.append(f"{fam['family']}: first route {route.get('pattern')} has status {route.get('status')}")
        for route in fam.get("avoid", []):
            if route.get("status") == "ok":
                bad.append(f"{fam['family']}: avoid route {route.get('pattern')} is marked ok")
    for b in bad:
        print(b)
    print(f"routes: {len(bad)} finding(s)")
    return 1 if bad else 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("score", "compare", "routes"):
        print(__doc__)
        return 2
    if argv[1] == "score":
        return cmd_score(argv[2])
    if argv[1] == "routes":
        return cmd_routes(argv[2])
    args = argv[3:]
    def opt(name):
        return args[args.index(name) + 1] if name in args else None
    before, after = opt("--before"), opt("--after")
    if not before or not after:
        print("compare needs --before and --after", file=sys.stderr)
        return 2
    return cmd_compare(argv[2], before, after, "--gate" in args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
