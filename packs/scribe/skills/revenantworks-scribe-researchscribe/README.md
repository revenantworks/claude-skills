# revenantworks-scribe-researchscribe

Research that ends in something usable, from any route. Native research tools (claude.ai
Research, Claude Code's bundled deep-research workflow) return cited reports; researchscribe
grades what any route finds by **kind of fact** ([documented] / [vendor-reported] / [estimate] /
[unverified]), keeps **every unchecked claim visible** (blocked pages, budget cuts, rate-limited
checks), and ends in a **verdict** with one pick and a flip condition, a versioned **playbook**,
or a **graded research report**. It states the size and cost of any fan-out and waits for a yes
before spending.

**Workflow:** Intake → route and criteria → live verification → grade → product → delivery gate

## Package contents

```
revenantworks-scribe-researchscribe/
├── SKILL.md                      # entries, the tag legend, rules for every mode
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── verification.md           # how a claim earns its tag (every run)
│   ├── verdict-mode.md           # criteria → verification → one recommendation
│   ├── verdict-measurement.md    # verdicts on measured systems
│   ├── playbook-mode.md          # template-first living docs; verify
│   ├── research-mode.md          # route picker, hand-off prompt, graded report
│   ├── hard-sources.md           # sites that block bots (dated, 30 days)
│   └── platform-facts.md         # the one dated file: roles, workflow format, limits
├── workflows/research.js         # saved workflow (Claude Code)
├── scripts/
│   ├── workflow_lint.py          # stdlib lint for the workflow file
│   └── test_workflow_lint.py
└── evals/                        # trigger-evals.md, test-cases.md, native case folders
```

## Dependencies

Web search and fetch; without them every product ships provisional and [unverified]. Optional:
the Workflow tool or a subagent tool in Claude Code; claude.ai Research on paid plans; Python 3
for the lint. Optional pointers, never required: lorescribe, commscribe, a brand's `VOICE.md`,
whisperrunner, duckrunner, lmstudiorunner. No package to install, no MCP server, no key.

## Install

Follows the [Agent Skills](https://agentskills.io/) standard: place the folder in your skills
directory, or install the scribe pack plugin. **The saved workflow runs as a plugin command only
when the pack ships it**: the pack places `workflows/research.js` in the plugin's `workflows/`
folder (or points the manifest's `workflows` field at it), and it then runs as
`/scribe:research`. Without the plugin, the skill launches the same file from its own folder.

## Entry points and commands

| Invocation | What it does |
|---|---|
| `researchscribe` | Capability line, then asks what to decide, document or check |
| `researchscribe verdict` | Pick, compare, worth-it, go/no-go → tagged table → one recommendation + flip condition |
| `researchscribe playbook` | Reference doc → template gate → answer-first fill → verification → version stamp |
| `researchscribe research` | Route (a) Research hand-off, (b) fan-out, (c) single pass → graded product |
| `researchscribe verify` | Fact and form drift catalog for an existing doc or report |
| `researchscribe sources` | A walled source: route table, capture request, owner-run API route |
| `researchscribe refresh` | Re-verify `platform-facts.md` and `hard-sources.md` |

| In-request switch | Effect |
|---|---|
| "quick" | Quick verdict: deciding cells only |
| "just write it" / "apply all" | Skips the criteria or template gate (never the yes before a fan-out) |
| "yes, small / medium / large" | Approves a fan-out at that size |
| naming a voice or brand | Prose in that voice; tags and figures unchanged |
| handing in a report | Report intake: re-graded live into a verdict, playbook or graded report |

## Checking the workflow file

```
python scripts/workflow_lint.py workflows/research.js
python -m unittest discover -s scripts -p "test_*.py"
```

## Staying current

`references/platform-facts.md` and `references/hard-sources.md` carry Last-verified stamps (30
days); `researchscribe refresh` re-reads their sources. Before each workflow launch the skill
checks the format stamp and re-reads the workflow docs when it is stale. `SOURCES.md` holds the
parity register (90 days). Every product dates its own checks.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
