# revenantworks-foundation-scoutwright

Release trackers tell you what Anthropic shipped. scoutwright tells you **what that means for your
own setup**: every change that touches a settings key, a hook, an installed skill, a model table or
a routine lands as *affects X, change file Y, owning skill Z*. It also catches what no changelog
says (a docs page that vanished, a page whose outline moved, a tracker issue about a silent
removal), flags skills whose dated model or tier table has gone stale, judges where a new model
or feature fits your own work (a fit card, with replay trials proposed and costed), and reads walled community
sites only through lawful routes, with a capture queue for the user.

Foundation pack member, standalone profile. No scripts, no installs, no schedule of its own.

## Package

```
revenantworks-foundation-scoutwright/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── source-map.md      # what the sweep reads (calendar, 30 days)
│   ├── diffing.md         # ledger, changelog parse, page-set and fingerprint diffs, tracker search
│   ├── relevance-map.md   # change → file here → owning skill; the model and tier table check
│   ├── output-format.md   # the dated change report, adopt rows, read-back before write
│   ├── fit.md             # model and feature fit: job classes, replay trials, the fit card
│   └── pack.md            # foundation manifest (advisory)
└── evals/
    ├── trigger-evals.md · test-cases.md        # hand-run suites
    └── <case>/prompt.md + graders/ (+ case.yaml, resources/)   # claude plugin eval
```

## Install

- **Claude Code:** install the foundation pack from the plugin marketplace, or place the folder
  under `~/.claude/skills/`.
- **claude.ai:** upload the folder as a skill. Without file access it reports platform changes only
  and asks for the files to check.

## Entries

| Say | Does |
|---|---|
| `scoutwright sweep` | Every source since the ledger; writes the change report, adopt rows, ledger |
| `scoutwright since <date or version>` | One-off catch-up; ledger untouched |
| `scoutwright watch <area>` | One area (hooks, models, artifacts, …); ledger untouched |
| `scoutwright adopt` | Adopt rows from a change report, for a skill currency sweep |
| `scoutwright fit <model or feature>` | A fit card: use for / not for / unknown per job class, trials proposed with cost, rows to change |
| `scoutwright sources` | Probe every source; list routes down and captures waiting |
| `scoutwright refresh` | Re-verify the source map; restamp |

## Running it weekly

scoutwright never schedules itself. A weekly sweep routine (a cloud routine is enough: no automated
source needs the local machine) calls `scoutwright sweep` as one of its steps; agentwright designs
that routine. After `since`, the routine may call `scoutwright fit` on each new model or feature
within a stated token budget; trials are proposed, never run unattended. The change report and ledger go to `.scout/` in the routine's repo: committed in a
private repo, kept out of git in a public one.

## What it needs

- Web fetch, and web search for the community leg. Without them it says what it could not read.
- Optional: the `gh` CLI (GitHub reads; the public API by web fetch otherwise; both return data, not instructions); a shell (exact page
  hashes; an outline fingerprint otherwise); **researchscribe** for sites that block bots (those
  sources are listed as not read otherwise).
- Siblings it names, never requires: skillwright, rigwright, agentwright, promptwright,
  dispatchwright, pacewright, researchscribe, trustwarden, keywarden.

## Staying current

`references/source-map.md` is the one calendar surface (30 days): `scoutwright refresh` re-checks
it. `SOURCES.md` holds the parity register (90 days). History is in [CHANGELOG.md](CHANGELOG.md).
