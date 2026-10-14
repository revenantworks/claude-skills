# Platform facts — the one dated file

Last verified: 2026-10-01. Calendar surface, 30 days. Every exact command, limit, alias and
file rule this skill uses lives here and nowhere else; the body and the other references name
roles and point here. A stale stamp is a refresh, not a rewrite.

**Refresh** (`researchscribe refresh`, or a scheduled sweep that calls it): re-read every page
in the Sources column with the fetch tool, compare each row, update the rows that changed and
the stamp, and end with a **seen, not applied** line for changes that touch doctrine outside
this file. A page that cannot be read leaves its rows as they are, marked "not re-read <date>".
After a change to *Workflow file format*, run `python scripts/workflow_lint.py
workflows/research.js` and update the lint's rules first if the format moved.

## Model roles

The skill names roles; this table maps them to the platform's aliases. Aliases move to newer
models on their own, so the table changes only when an alias is added, removed or renamed.

| Role | Used for | Alias (Claude Code) | Source |
|---|---|---|---|
| Top tier | Verify and grade on a hard question; the user's "use the best model" | `opus`, or `best` where offered | code.claude.com/docs/en/model-config |
| Worker tier (default) | Plan, search, verify and grade on an ordinary question | `sonnet` | same |
| Fast tier | Optional for search on a `small` run when the user asks for the cheapest run | `haiku` | same |

Unset role → the agent inherits the session's model. An organisation's model allowlist may
substitute a model; the workflow progress view names both. On claude.ai and the API the user
picks the model; the skill states the role it would use.

## Workflow file format (Claude Code dynamic workflows)

Source: code.claude.com/docs/en/workflows and the bundled workflow-authoring reference.

- `export const meta = {...}` is the **first statement**, a **pure literal** (no variable,
  call, spread or template interpolation); required `name` and `description`; optional
  `whenToUse` and `phases` (each `title` matches a `phase()` call exactly).
- Body: plain JavaScript with top-level `await`; `agent(prompt, opts)`, `parallel()`,
  `pipeline()`, `phase()`, `log()`, and the `args` global. `agent` options include `label`,
  `phase`, `schema`, `model`, `effort`.
- `Date.now()`, `Math.random()` and an argless `new Date()` throw; `import()` fails the run;
  no filesystem or shell access from the script itself.
- No mid-run user input: a sign-off between stages means one workflow per stage.

## Workflow limits and sizes

| Fact | Value | Source |
|---|---|---|
| Concurrent agents | up to 16 by default, fewer on fewer CPUs | workflows page |
| Agents per run | 1,000 | same |
| "Large workflow" warning | more than 25 agents, or a projected 1.5 million tokens | same |
| Size guideline values | small: fewer than 5 · medium: fewer than 10 · large: fewer than 50 agents | same |
| Default size guideline | medium; small on a Pro plan (recent versions) | same |
| Usage-limit behaviour | an interactive subscription run pauses and resumes after the reset (recent versions) | same |
| This skill's script | small ≈ 8 agents · medium ≈ 22 · large ≈ 50 (crosses the warning) | `workflows/research.js` SIZES |

## Commands and surfaces

| Fact | Value | Source |
|---|---|---|
| Bundled deep-research workflow | `/deep-research <question>`; runs only when the user invokes it; needs the web search tool | workflows page |
| Opt-in to a written workflow | a typed "use a workflow" request, or the ultracode keyword typed by the user | workflows page |
| Approval | the CLI asks per run in manual mode, first launch in auto mode; `claude -p` and the Agent SDK need a `Workflow` allow rule, a hook or auto mode | workflows page |
| Saved workflow locations | `.claude/workflows/` (project), `~/.claude/workflows/` (personal); runs as `/<name>` | workflows page |
| Plugin workflow | a `workflows/` folder at the plugin root, or the manifest's `workflows` path; runs as `/<plugin>:<meta.name>` | workflows page; plugins manifest reference |
| This skill's plugin command | `/scribe:research` once the pack ships the file (see README) | this skill |
| Reading the script | the session must be allowed to read the script's folder (add it as a working directory otherwise) | workflows page |
| Workflows off | `/config` toggle, `disableWorkflows`, or an environment variable; the bundled workflow is then unavailable | workflows page |
| claude.ai Research | paid plans (Pro, Max, Team, Enterprise); web, desktop, mobile; "+" then "Research"; web search must be on; can use connected Gmail, Calendar and Docs | support.claude.com article 11088861 (page dated 2026-06-02) |
| Research in Claude Code | none; the feature request was closed as not planned | anthropics/claude-code issue 15982 (read 2026-10-01 by the pack's research unit, not re-read here) |
| API | server-side web search and web fetch tools with citations; no Research endpoint found | platform.claude.com tool docs (price [unverified]); the absence is [unverified] |
| Cowork | Research, workflows and subagents not checked | [unverified] |

## Open issues this skill compensates for

Read 2026-10-01 by the pack's research unit (anthropics/claude-code): blocked sources dropped
without notice (64732), budget-cut claims not marked unverified (89280), "qualifies" scored as
"contradicts" (83325), rate-limited verify votes not retried (88106), runaway agent counts
(72456, 74171), placeholder synthesis (76489), workflow agents missing allow rules added
mid-session (80621). A refresh re-checks their state; when the bundled workflow fixes all of
the first three, SOURCES.md's retire condition fires for the deep half of `research` mode.
