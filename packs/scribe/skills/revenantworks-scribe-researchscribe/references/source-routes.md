# Source routes — tiers, the fetch ladder and the stop rule

Last verified: 2026-11-09 (140 fetch-tool probes, `evals/fixtures/probe-2026-11-09.json`;
endpoint status in `route-health.json`). Calendar surface, 30 days: `researchscribe refresh`
re-probes one URL per route and updates `route-health.json` and this stamp.

Loaded by `verdict`, `playbook`, `verify`, `research`, `sources` and `refresh`, beside
`verification.md`. Sites that block automated
reading entirely (Reddit, YouTube transcripts, X) stay `hard-sources.md`'s.

## Contents

- 1. Source tiers
- 2. The fetch ladder
- 3. Route table per family
- 4. The stop rule
- 5. The block log (counts only)
- 6. What the probe showed, and refresh

## 1. Source tiers

Rank a source by what it is, before reading it. The tier decides what a source may settle;
the evidence tag (SKILL.md) still decides how a claim reads.

| Tier | What it is | May settle |
|---|---|---|
| **1** | The record itself: the publisher's or maintainer's API, registry, release, standard text, primary dataset, the paper or filing | any deciding claim |
| **2** | The authority's own human page: official docs, an advisory, a regulator's page, a recall database, a DOI registry record | any deciding claim |
| **3** | Independent and curated: an independent test lab, a third-party index (endoflife.date, ADS), a downstream distro's advisory, an encyclopedia | an independent measurement (`verification.md` §5); background; never a version or date when tier 1 is readable |
| **4** | Secondary: press, vendor blogs about other products, forums, Q&A, personal analysis | an opinion question, where the community is the subject; otherwise a lead only |
| **5** | Do not read: SEO farms, a hijacked domain serving "best X" pages, spam issue trackers, `*.pages.dev` review mills, a copy of another site's paper or docs on a different host, a package mirror for a "latest" question, versioned docs older than the question | nothing; when search returns only tier 5, search again with the primary's name or domain |

Tier 5 signs: the domain has nothing to do with the subject; the page copies a paper, RFC or doc
whose home is elsewhere; the URL carries an old version (`/doc/1.14/`) for a "current" question;
a redirect leads to an unrelated host. A tier 5 result is noted once in the attempts as
"skipped: tier 5", never read and never cited.

## 2. The fetch ladder

For each deciding claim, take the first rung that applies and stop when the claim is read:

1. **A built route in the session**: an authorised CLI or connector for that source (`gh` for
   GitHub; a connected MCP server). Status `built` in `route-health.json`.
2. **The family's first route** in §3 whose status is `ok`: usually a machine-readable record
   (API JSON, `.txt`, registry page) the fetch tool can read.
3. **The primary human page** of the same publisher.
4. **The same publisher's other format**: `.txt`, `.pdf` or HTML twin, `/llms.txt` or a `.md`
   page, a Discourse `.json`, a redirect inside the same registrable domain (www.ncbi →
   pmc.ncbi). Use this rung when a page comes back empty, too large or JavaScript-only.
5. **Another tier 1 or 2 publisher of the same fact** (NVD ⇄ OSV, arXiv ⇄ Crossref, PubMed ⇄
   PMC).
6. **A lower tier**, tagged as what it is, or a capture request (`hard-sources.md` §3); else the
   claim ships [unverified] with every attempt listed.

Never a rung: an archive, a cache, a mirror, a reader or proxy service, a changed user agent, a
shell fetch of a URL the fetch tool refused, or a URL found inside a source.

## 3. Route table per family

Measured 2026-11-09 with the fetch tool. **First** routes in order; **avoid** routes failed on
every probe and are not tried with the fetch tool. Exact patterns and probe ids:
`route-health.json`.

| Family | First routes | Avoid (why) |
|---|---|---|
| arXiv paper | `arxiv.org/abs/<id>` · `arxiv.org/pdf/<id>` · `arxiv.org/html/<id>` | `export.arxiv.org/api` (robots) · Semantic Scholar and OpenAlex APIs (client error) |
| DOI metadata | `api.crossref.org/works/<doi>` | — |
| Biomedical | `pmc.ncbi.nlm.nih.gov/articles/<PMCID>/` (open access); metadata by DOI via Crossref | `pubmed.ncbi.nlm.nih.gov` (captcha) · E-utilities (robots) · Europe PMC REST (429) |
| Python package | `pypi.org/project/<name>/` · licence from the repo's raw `LICENSE` | PyPI JSON and simple index (robots) · `api.deps.dev` (robots) |
| GitHub | `gh api repos/<o>/<r>/releases/latest` · unauthenticated `api.github.com` (60 an hour, shared: flaky) · `github.com/<o>/<r>/releases` | — |
| Vulnerability | `api.osv.dev/v1/vulns/<id>` · `services.nvd.nist.gov/rest/json/cves/2.0?cveId=<id>` | `nvd.nist.gov/vuln/detail` (JS-only) · cisa.gov KEV feed and page (client error) |
| IETF standard | `rfc-editor.org/rfc/rfc<N>.txt` · `datatracker.ietf.org/api/v1/doc/document/rfc<N>/` | FTP and translation copies (tier 5) |
| US government data | `bls.gov/news.release/<x>.nr0.htm` · Federal Register API · World Bank API | `api.bls.gov` (robots) |
| Release lifecycle | `endoflife.date/api/<product>.json` (tier 3: confirm a deciding date on the maker's release) | very large docs pages (navigation only) |
| Steam | `store.steampowered.com/api/appdetails?appids=<id>` · the store page · `appreviews/<id>?json=1` (flaky) | `api.steampowered.com` (robots): live player counts have no fetch route |
| Encyclopedia | `en.wikipedia.org/wiki/<Title>` (tier 3, background only) | REST summary and `api.php` (client error) |
| Community | Discourse `/t/<id>.json`, `/latest.json` · HN `hn.algolia.com/api/v1/search` | Stack Exchange API (site blocked) · Reddit (`hard-sources.md`) |
| Product | saferproducts.gov recall API (tier 2) · independent lab pages such as rtings.com (tier 3, flaky) | — |
| Docs site | `/llms.txt` where the site publishes one | — |

A family not listed runs the ladder from rung 3. A refusal there is logged (§5); a host that
refuses three runs in 30 days earns a row here at the next refresh.

**Owner-run routes.** Some documented APIs refuse the fetch tool under robots.txt (arXiv's API,
PyPI JSON, BLS, E-utilities, the Steam Web API). The skill never reaches them another way. Where
the owner wants one, the route is a client the owner installs and authorises after a vet
(trustwarden when installed), like `gh`; once connected it is rung 1, with the provider's own
rate rule (arXiv: one request every three seconds; NCBI: three a second without a key; SEC: a
declared user agent).

## 4. The stop rule

| Outcome | What it means | Next step |
|---|---|---|
| Robots refusal, site block, bot challenge or captcha, login or paywall, 403 | a refusal | stop on that URL; never retry it, never reach it another way; next rung |
| 429 | a rate limit | at most one retry, after other work; a second 429 is a refusal |
| JavaScript-only, too large, empty | not a refusal | ladder rung 4 (same publisher's other format) |
| 404 or moved | not a refusal | one search for the same publisher's current page; else next rung |
| Cross-host redirect | not followed | recorded; read the product from its own host |

**Host breaker:** two refusals from one host in a run end fetching from that host for the run;
the claims it held go down the ladder. Every refusal is an attempt in the product (URL, outcome,
date) and a count in the block log.

## 5. The block log (counts only)

`scripts/block_log.py` keeps a local tally so refresh can see which hosts keep refusing. One
line per run per host and outcome: date, host, outcome code, count. Never a path, query, page
text, title or anything about the user.

```
python scripts/block_log.py add <host> <OUTCOME> [--n N]
python scripts/block_log.py ingest <workflow result .json>
python scripts/block_log.py report [--days 30]
```

The log lives at `RESEARCHSCRIBE_BLOCK_LOG` when set, else
`~/.claude/researchscribe/block-log.jsonl`, outside every repo. Where file tools are absent the
product's attempts list is the record. A scheduled run adds its counts and lists them in its
report; `refresh` reads `report` before re-probing.

## 6. What the probe showed, and refresh

Ten questions across ten families, read with the fetch tool on 2026-11-09, then five new
questions to check the table out of sample (`scripts/source_eval.py score`):

- Search-then-read was rarely refused (5% to 15% not read), but only 21% to 32% of what it
  read was tier 1 or 2, and 16% to 27% was tier 5.
- Going straight to primary pages and well-known APIs failed on 15 of 40 fetches (37.5%), 9 of
  them refusals: robots rules on documented APIs, captchas, JavaScript shells.
- The routed table on new questions: 1 of 20 fetches not read (5%), no refusals, 79% of reads
  tier 1 or 2, none tier 5.

**Refresh** (`researchscribe refresh`): read `block_log.py report` first; fetch one URL per
first and avoid route with the fetch tool; add the rows to a new probe file and run
`source_eval.py routes`. A first route that fails on two refreshes moves to avoid; a flagged
host earns a row; an avoid route that reads cleanly twice may move back. Update
`route-health.json` and the stamp at the top together.
