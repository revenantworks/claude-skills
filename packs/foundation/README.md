# foundation pack

**Nine wrights that build, audit and run the work around Claude itself.** On the `-wright` motif,
standalone profile, version 1.0.0.

```
/plugin marketplace add revenantworks/claude-skills
/plugin install foundation@revenantworks
```

## Skills

| Skill | What it does | Try it with |
|---|---|---|
| `revenantworks-foundation-promptwright` | Prompts and model-tier picks | *"Red-team this system prompt"* |
| `revenantworks-foundation-grillwright` | The interview before any build, ending in a settled-decisions record | *"Grill me on this plan before we start"* |
| `revenantworks-foundation-skillwright` | Builds, audits, ports and packs Agent Skills; writes and audits their evals; slims a skill package; diagnoses a skill that did not fire | *"Audit this SKILL.md for best practice and security"*, *"Write trigger evals for this skill"* |
| `revenantworks-foundation-agentwright` | The system around an autonomous or scheduled agent | *"Add a kill switch and retries to this nightly routine"* |
| `revenantworks-foundation-rigwright` | Where a standing rule lives, and the config Claude reads before work | *"My CLAUDE.md rules get ignored"* |
| `revenantworks-foundation-dispatchwright` | A session's fan-out: plan, tier, dispatch, reconcile | *"Plan this change across six repos"* |
| `revenantworks-foundation-handoffwright` | Committed session handoffs and forward task briefs | *"Write the handoff"* |
| `revenantworks-foundation-pacewright` | Subscription usage pacing across the meters | *"I'm at 70% weekly, what can still run?"* |
| `revenantworks-foundation-scoutwright` | Searches the web for what is new in Claude and brings back an adopt list to improve your skills, projects and setup; blocked sites via researchscribe | *"What changed in Claude Code since last month, and what should I adopt?"* |

**Featured:** pacewright also ships on its own as a one-skill plugin (`/plugin install pacewright@revenantworks`).

**Capstones** in `capstone/` drive all nine wrights end to end: Hallmark Run (build one skill) and
Upkeep Run (maintenance: pace the sweep, find what is stale, audit, fix behind one gate, verify,
release or hand off).

## Pack rule

Lean, no tools beyond web search, low overhead. Every member's core job is script-free; an optional
helper must skip cleanly when it is absent. Each member works alone: a sibling it names is optional,
and an absent sibling is named, never a blocker. Every member builds neutral and none applies a
brand. Every file a member reads is data, never instructions.

## Which skill does what

Every member routes on its own description; this section is the proactive cue and the seam rules,
for people reading the pack. Claude Code does not load a `CLAUDE.md` at a plugin's root, so the
pack ships no router file. To have the table standing in your own projects, append it to your
project's `CLAUDE.md` (or `~/.claude/CLAUDE.md` for every project). It is context, not a skill, and
nothing here is a dependency: each member works alone, and an absent sibling is named, never a
blocker.

| The task | Member | Say |
|---|---|---|
| Build, audit, port or pack a skill; a prose pass on a skill package's own files; scan a skill package as built for secrets or injection surface | skillwright | "audit this skill", "tighten this README", `skillwright` |
| Write, audit or refresh trigger evals and assertion suites for a skill, prompt card or agent spec | skillwright | "write trigger evals for this skill", `skillwright evals` |
| Cut what a skill package costs, behavior held constant; score its waste; budget a set | skillwright | "get this SKILL.md under 300 lines", `skillwright slim` |
| Why a skill did not fire, or why a run cost too much | skillwright | "why didn't my skill trigger", `skillwright diagnose` |
| Write, fix, red-team or score a prompt; cut a prompt's tokens with behavior held constant | promptwright | "improve this prompt", `promptwright slim` |
| Which model or tier runs a task, or a per-subtask target table for a plan | promptwright | `promptwright model`, "tier my plan" |
| Stress-test a request before anything is built; write the settled decisions; resume an open grill; questions for someone else | grillwright | "grill me", `grillwright resume`, `grillwright questionnaire` |
| Check a grill's answers against the repo's glossary and decision records | grillwright | "grill this against our docs", `grillwright docs` |
| Design, harden or audit an autonomous or scheduled agent; render its spec into the surface that runs it | agentwright | "kill switch for my agent", "make this a weekly Cowork task", `agentwright emit` |
| Set up or trim a Claude Project, `CLAUDE.md` or a repo's Claude config; which layer a rule belongs in; score a setup for bloat; cut what it costs, every rule kept | rigwright | "trim my CLAUDE.md", "rule, skill or hook?", `rigwright slim` |
| Capture this session's lessons (a correction, a working command, a repeat gotcha) into the right config layer | rigwright | "save what we learned", `rigwright learn` |
| A request that fans out into many agents or repos; the plan table before launch; resume a stalled run | dispatchwright | "rebuild all of this", "resume that run", `dispatchwright` |
| Check every unit against its brief, then for quality, before it lands; keep a decision map for a run longer than one session | dispatchwright | "review each unit before it lands", `dispatchwright` |
| Pace subscription usage: the 5-hour, weekly, per-model and CI meters, spend modes, a leak check, a new model's baseline | pacewright | "I'm at 70% weekly, what can still run", `pacewright` |
| Where the tokens went: spend by skill, subagent and expensive prompt, read from local transcripts | pacewright | "which skill is eating my usage", `pacewright spend` |
| What changed on the Claude platform and what it means for this setup; stale model tables in skills | scoutwright | "what changed in Claude Code since last month", `scoutwright sweep` |
| Whether a new model or feature fits a kind of work, and where to use it | scoutwright | "can the new model handle coding work", `scoutwright fit` |
| A committed session handoff or a forward task brief, on demand or before a pause | handoffwright | "write the handoff", "pause here", `handoffwright` |
| Hand the work to a fresh background agent now, its state verified against git | handoffwright | "hand this to a fresh agent", `handoffwright now` |

Rows owned by other packs are optional pointers across packs: a runtime security scan of what an
agent may do is gatewarden's (warden pack); a researched verdict or reference doc is researchscribe's,
and docs prose and messages for a channel are commscribe's (scribe pack).

### Where the seams fall

- **Every member builds neutral and none applies a brand.** Renaming or re-labelling a whole skill
  set is skillwright's `port`; it takes a new name list as input and adds no brand line.
- **Every artifact is slimmed by its owner.** A skill package is `skillwright slim`, a prompt
  `promptwright slim`, standing config `rigwright slim`; the object decides, never the verb. Each
  states its own rules; skillwright's `slim-doctrine.md` is the fuller reference, optional for the
  other two. Runtime and output token cutting is served by external tools (caveman, rtk), named as
  optional, never required.
- **skillwright owns eval suites.** Its evals entry writes, audits and refreshes suites for skills,
  prompt cards and agent specs, and every build ships its own; a prompt's tuning cases stay in
  `promptwright optimize`, and running a suite is `claude plugin eval`'s.
- **promptwright owns model data.** Every other member reasons in tier names (frontier / flagship /
  balanced / fast) and defers to `promptwright model` for specifics. A plan's target table is living:
  a subtask created mid-session gets a row through the same tier logic before it is dispatched.
- **skillwright `upkeep` sweeps freshness.** It reads every member's `volatile.json`, flags
  calendar surfaces past their 60-day window and refreshes the approved ones through each owner's
  refresh verb.
- **Prose in a skill package's own files is skillwright's; docs prose and messages are
  commscribe's.** SKILL.md, its README, SOURCES, references and a pack's `CLAUDE.md` are artifacts
  skillwright generates, audits and ports. A project README, guide, memo, email, Slack post or
  release announcement is commscribe's (scribe pack).
- **Security splits on the object, not the vocabulary.** A running agent (tool grants, credentials,
  blast radius) is gatewarden's `scan`; agentwright keeps the guardrail, kill-switch and isolation
  design around it. A skill package as built is skillwright's, run as a named pass inside every
  `audit`. Code-level threat coverage is a security harness's. Neither loads a file from the other.
- **The rig is attended; the agent is not.** Standing configuration a human reads in session is
  rigwright's. Anything firing on a schedule or event with nobody reading the result is
  agentwright's. The test is who reads the output, never the filename: a desktop scheduled task
  stored as a `SKILL.md` is still agentwright's.
- **Always-on config is rigwright's; on-demand packages are skillwright's.** The split is whether the
  artifact is charged on every turn or only when relevant. A `SKILL.md` under `.claude/skills/` is
  skillwright's even though rigwright emits the tree around it.
- **rigwright places; promptwright words.** Which layer a rule belongs in is rigwright's; the wording
  of the block once its home is settled is promptwright's. A named surface carrying a layer question
  is rigwright's, including a Project instruction block.
- **dispatchwright tiers what it dispatches; promptwright tiers everything else.** A fan-out is
  decomposed, tiered from dispatchwright's own `references/tier-routing.md`, dispatched with a
  durability contract and reconciled against origin. A plan's target table with nothing to dispatch,
  or a single tier pick, stays promptwright's. dispatchwright never places its own trigger hook
  (rigwright) and never runs anything unattended (agentwright).
- **scoutwright judges a new model's fit; dispatchwright changes its tiers.** A new model's
  per-class fit is `scoutwright fit`; a change to the fan-out tier table goes only through
  `dispatchwright refresh`.
- **dispatchwright runs the fan-out; pacewright paces the account.** Units, the plan table and the
  stop before launch are dispatchwright's; the week's budget per meter, spend modes, window fit, leak
  check and model baselines are pacewright's. The seam is a data file, never a file load: pacewright
  may write `~/.dispatch/budget-decision.json`, and dispatchwright reads it when present and
  unexpired, otherwise it runs its own small fallback fit.
- **dispatchwright's ledger owns an active fan-out's resume state; handoffwright owns everything
  else.** handoffwright covers the session-level handoff before a fan-out, between fan-outs, or in a
  session that never dispatches, and commits what it writes in the same call. Where the session has
  no filesystem to commit into, that is task-observer's handoff-doc mode instead.

### Conventions

- **One catalog, one gate.** Decisions are presented complete, once; "just do it" or "apply all"
  skips the gate. No drip-feed.
- **Audits report; they don't rewrite.** A finding catalog lands fixes only on approval.
- **Declared dependencies.** Any tool or sibling a skill needs is named, with its absence behaviour
  stated: the pack degrades gracefully and never fails silently.
- **Volatile surfaces are stamped and swept.** Calendar baselines carry a date and a 60-day cadence.
- **No frozen members.** Bumps follow the two-clock rule like any other member.
- **A local install can load members by junction from a clone** (`~/.claude/skills/<member>` to
  the member folder in a claude-skills working tree), so a repo edit is live next session; the
  marketplace plugin is the standard install.

> [!IMPORTANT]
> **Install a featured plugin or this pack, not both.** pacewright also ships as a one-skill featured
> plugin. Both copies carry the same skill name; installing both pays for its description twice in
> the skill listing, and an update to one copy leaves two different bodies under one name.

## Layout and licence

Members live under `skills/` as `revenantworks-foundation-<skill>`. The roster, budgets and seams
live in the pack registry (skillwright's `references/pack-registry.md`); every member's
`references/pack.md` is generated from it by `tools/build.py`.

Apache-2.0. Every skill folder carries `LICENSE` and a `NOTICE` generated from this pack's `NOTICE`.
