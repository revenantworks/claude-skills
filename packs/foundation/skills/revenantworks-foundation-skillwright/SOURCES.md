# Sources

Last verified: 2026-09-26 (the parity register, the last section of this file; upkeep reads this stamp).

This skill is assembled from public, citable material. Each section below carries its own verification date; there is no single file-wide date. The Rubric A baseline in `references/rubrics.md` carries its own Last-verified stamp and is re-researched on every build and audit — run "skillwright refresh" to regenerate it.

## Skill authoring — Anthropic primary sources (verified 2026-07-12; the five 2026-09 Rubric A additions re-read 2026-09-28)

*Applies to: `references/rubrics.md` (Rubric A), `references/build-templates.md`, `references/description-crafting.md`, `references/eval-doctrine.md`.*

| Source | Key guidance |
|---|---|
| Anthropic — Agent Skills best practices. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | ≤500-line SKILL.md body; one-level-deep references; TOCs on long reference files; third-person what+when descriptions; evaluation-driven iteration; avoid time-sensitive info and Windows paths. |
| Anthropic — Agent Skills overview. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview | Three-level progressive disclosure (metadata → body → bundled resources); frontmatter `name` + `description` required; trusted-source security guidance. |
| Anthropic — "Equipping agents for the real world with Agent Skills." https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Progressive disclosure as the core design principle; start with evaluation; split unwieldy bodies; think from the executing model's perspective. |
| Anthropic — anthropics/skills repository (incl. skill-creator). https://github.com/anthropics/skills | Template-skill starting point; pushy descriptions to counter under-triggering; interview → draft → test → iterate loop; packaging conventions (`.skill` excludes `evals/`). skill-creator was also used to validate and package this skill at construction time. |
| Claude Help Center — "How to create custom skills." https://support.claude.com/en/articles/12512198-how-to-create-custom-skills | Focused single-purpose skills compose better than one large skill; clear descriptions drive invocation; start simple before adding scripts. |

## Skill format — the Agent Skills open standard (verified 2026-07-12; the <5000-token body line read 2026-09-26)

*Applies to: package structure, frontmatter fields, naming constraints.*

**Agent Skills open standard** — https://agentskills.io/ · name ≤64 chars lowercase-hyphen; description ≤1024 chars; optional `license`, `compatibility`, and `metadata` frontmatter fields (this skill's `metadata` carries version, profile, pack, and brand).

## Incumbent scan & plugin distribution

*Applies to: the incumbent-scan sources in `references/rubrics.md`, the Plugin target section in `references/build-templates.md`, SKILL.md build steps 3–4 and Packaging. All verified live 2026-07-12.*

| Source | Role |
|---|---|
| skills.sh — https://skills.sh | Community skill directory (install counts, topics, per-agent listings, security audits); parity-verdict incumbent scan. |
| anthropics/skills — https://github.com/anthropics/skills | Official example skills; doubles as a plugin marketplace (`anthropic-agent-skills`); parity-verdict incumbent scan. |
| anthropics/claude-plugins-official — https://github.com/anthropics/claude-plugins-official | Anthropic-managed curated plugin directory; parity-verdict incumbent scan. |
| anthropics/claude-plugins-community — https://github.com/anthropics/claude-plugins-community | Public community plugin directory; submissions flow through https://clau.de/plugin-directory-submission (`claude plugin validate` first); parity-verdict incumbent scan + distribution channel. |
| anthropics/knowledge-work-plugins — https://github.com/anthropics/knowledge-work-plugins | Role-plugin reference architecture (skills + commands + connectors); pattern source for role-shaped packs. |
| Claude Code plugin docs — https://code.claude.com/docs/en/plugins | Plugin target format: `.claude-plugin/plugin.json` manifest, `skills/` with `disable-model-invocation: true` for explicit workflows (legacy `commands/` noted), optional `.mcp.json`, marketplace registration, `claude plugin validate`. |

## Pack integration & surfaces (added at 1.1.0)

*Applies to: Entry — Integrate, `references/pack-integration.md`, the Packaging upload-path fix.*

- Claude Help Center — "Use skills in Claude" (verified 2026-07-13). https://support.claude.com/en/articles/12512180-use-skills-in-claude — custom skills upload as zips at Customize → Skills, per-account, code execution required; update = re-upload. Grounds the lazy-restamp default: installed-surface uploads are manual, one at a time.
- Claude Code docs — "Discover and install prebuilt plugins through marketplaces" (verified 2026-07-13). https://code.claude.com/docs/en/discover-plugins — `/plugin marketplace add <owner>/<repo>` + `/plugin install <name>@<marketplace>`; a repo carrying `.claude-plugin/marketplace.json` is its own marketplace. Grounds the plugin lane: one pack, one install on the Code surface.

## Pack design (added 2026-07-14; originally recorded under predecessor-era "1.2.0" numbering that never shipped — see spec D-3)

*Applies to: Entry — Pack, `references/pack-design.md`.*

- The suite-composition rules already recorded in `build-templates.md` (declared siblings, partitioned triggers as a set, one delivery) — Entry — Pack applies them at design time instead of retrofit time; no new external doctrine required.
- The 1.1.0 marketplace sources (Claude Code plugin-marketplaces docs; community submission flow in the baseline) govern the plugin/marketplace prep step; `claude plugin validate` per the same docs.

## Release doctrine (added at 1.2.0)

*Applies to: `references/release-doctrine.md`.*

No external published doctrine underwrites this one — it is derived from this pack's own shipped releases, and every step it names is traceable to a file in the canonical repo (all read 2026-07-24): `RUNBOOK.md` (the release loop, the manual-upload surfaces, the parity step), `tools/build.py` (the version, volatile, eval-provenance, count-integrity, and parity mechanisms, plus its own docstring's record of which warns are instrumentation and which are due to become failures), `.github/workflows/pack-ci.yml` (`--check` on every push to main and every pull request, never on tags; the full build plus member-zip attach on a version tag), the root `CHANGELOG.md` (the 1.0.0 / 1.1.0 / 1.1.1 release records), each member's `evals/RESULTS.md` (the before/after run ledger), and the pack-spec baton (the bump rule and the numbered deferral register). Because the sources are internal, the doctrine ages with the toolchain rather than with the ecosystem: it is durable, not calendar-volatile, and a change to the build script or the CI workflow is its restamp trigger.

## Parity verdict (added at 1.5.0)

*Applies to: Build step 4, Audit steps 2 and 4, Entry — Pack step 1, `references/rubrics.md` — Parity verdict, `references/pack-design.md`, `references/eval-authoring.md`, `references/upkeep-doctrine.md`.*

No external published doctrine underwrites the best-of-breed rule; it is the pack owner's decision of 2026-09-26, recorded through task-observer observation #0190, and it replaces the earlier niche verdict. The incumbent-scan sources it checks are the ones listed above and in `references/rubrics.md`.

This member's own register is the last section of this file, added at 1.6.0 from the 2026-09-26 audit's scan and declared in `volatile.json` (calendar, 90 days).

## Reference implementation

`revenantworks-foundation-promptwright` (current release) — the reference implementation standalone-profile build this skill patterns its outputs on: declared load budget, tool-list test for tappable selections, stamped single-update-surface volatile files, `references/` + `evals/` split, assertion-only test suite, changelog born at 1.0.0.

## Parity register

Stamped 2026-09-26 in the file header above (incumbent scan by the skill-parity audit, raw Markdown read with an exact-match search wherever the host served it; the MCP registry row re-checked live 2026-09-28). Calendar surface, 90-day cadence (`volatile.json`). The stamp moves only for what a scan actually checked. Incumbent rows re-scanned live 2026-10-01 (unit PR): skill-creator unchanged since 2026-04-23; writing-skills last changed 2026-09-19 (superpowers v6.4.1); no change to any margin.

**Incumbents checked**

| Incumbent | Link | Checked | What it does on this job |
|---|---|---|---|
| skill-creator (Anthropic, Apache-2.0) | https://github.com/anthropics/skills/tree/main/skills/skill-creator | 2026-09-26 | Reach leader (skills.sh, 391,405 installs for "skill creator"). Intent interview, draft, with-skill and baseline runs in one turn, a grader into `grading.json`, a benchmark with mean ± stddev, an analyst pass for flaky and non-discriminating asserts, an HTML review viewer, a blind comparator, and a description loop (`run_loop`: 60/40 train and held-out, 3 runs per query, chosen on the held-out score). |
| superpowers writing-skills (MIT) | https://github.com/obra/superpowers/tree/main/skills/writing-skills | 2026-09-26 | 199,637 installs. TDD for documentation: a pressure scenario run without the skill first, the agent's excuses recorded, then the skill written and the loopholes closed. The description holds triggers only, never a workflow summary. |
| Claude Code tooling | https://code.claude.com/docs/en/plugin-evals.md · https://code.claude.com/docs/en/skills.md | 2026-09-26 | `claude plugin eval` runs each case three times with and without the plugin (WITH, W/OUT, Δ) and exits non-zero below a threshold; `tool_used: Skill` grades trigger rate; `/skill-doctor` reports listing cost and use; the listing cap is 1,536 characters of `description` plus `when_to_use`. |
| Skill scanners and linters (tools, not rivals) | getsentry `skill-scanner` (https://github.com/getsentry/skills/tree/main/skills/skill-scanner, Apache-2.0, read 2026-10-08: prompt injection, malicious scripts, excessive permissions, secret exposure, supply chain; needs `uv`) · SkillSpector · superagent-ai `skill-security` (https://github.com/superagent-ai/skills) · `ai.skilltotal/skilltotal` and `com.moltlinestudio/skillmd-lint` on https://registry.modelcontextprotocol.io | 2026-09-26; registry 2026-09-28 | Deterministic scans (regex, AST, taint, Unicode) and SKILL.md linting. Driven as stage 1 of the security pass when present; never rebuilt. |

**Parity table** (skillwright 1.6.0)

| # | Capability | Mark | How |
|---|---|---|---|
| 1 | Capture intent; interview gaps | met | Build step 1 |
| 2 | Fresh best-practices research every build | beaten (Case 48) | Build step 3, raw pages, dated; skill-creator and writing-skills carry baked guidance |
| 3 | Incumbent scan and a build call | beaten (Cases 9, 46, 47) | parity verdict before any file is written |
| 4 | SKILL.md with progressive disclosure | met | Build step 6, `build-templates.md` |
| 5 | Description written for triggering | met | `description-crafting.md`: listing cap, triggers not workflow |
| 6 | Trigger evals that run | met by driving the tool | `claude plugin eval` case folders emitted (`claim-cases.md` §9) |
| 7 | Description tuning loop | met | skill-creator's `run_loop` driven when present; a manual 60/40 loop otherwise, the pack's near-misses held out |
| 8 | Behaviour evals against a no-skill baseline | met by driving the tool | a `Without:` arm on every case (`claim-cases.md` §3) |
| 9 | Variance; flaky and non-discriminating asserts | met by driving the tool | three runs, pass fraction, discrimination check (`claim-cases.md` §5) |
| 10 | Human review surface | met by a different mechanism | one catalog, one gate; a viewer is out of scope for a skill that ships no code |
| 11 | Blind A/B of two versions | met | cold re-judge by another model family, recorded in RESULTS |
| 12 | Pressure test a discipline skill | met | `eval-doctrine.md` pressure test |
| 13 | Audit against a scored rubric | beaten (Cases 5–8) | Rubric A + profile + pack checks + catalog; `/skill-doctor` scores cost and use only |
| 14 | Security review | met; scanners driven as tools (Case 50) | S-1 to S-5 and the contract check by hand; a scanner as stage 1 |
| 15 | Package and install | beaten (Case 49) | native paths, zip, plugin target, staged-tree leak guard |
| 16 | Usage and listing cost | out of scope | reading the count is rigwright's |
| 17 | Test across model tiers | met | the self-audit states the tiers checked |

**Margins** (none of the incumbents above, nor any skill on skills.sh or server on the MCP registry, does these)

1. Parity verdict before any file is written, naming the rival and its install path on a no-go — Cases 9, 46, 47
2. Pack design with a trigger-partition gate — Case 33
3. Pack integration with count integrity (all-or-notes) — Cases 29–32
4. Port with a sanitize manifest and a scoped residue check — Cases 19–22, 28
5. Upkeep sweep of every member's volatile surfaces against a cadence — Cases 11, 12, 43
6. Security findings filed as catalog rows, scanner hits read by file role and matched string — Cases 38–40, 45, 50
7. Declared-profile scoring and pack conformance checks — Cases 8, 23
8. Contract-change sweep for retired wording across router, hooks and eval asserts — Case 51

**Iterate** (the next-version list): record a raw URL and exact-match search per baseline claim · make this register machine-readable so upkeep can age each row · a one-line intake contract (job, non-goals, success criteria, the incumbent to beat) · eval results as one page where a surface can publish one · name the blind cold re-judge as a Build step 7 step · name `/skill-doctor` as the Claude Code count source · run `claude plugin validate` before handback where the CLI exists.

**Retire condition:** skill-creator (or the platform tooling) adds pack design, porting, and a pre-build incumbent verdict. Until one incumbent has all three, margins 1–4 hold.

**Owed:** Cases 9, 36, 46, 47 and 48–51 are authored and not yet executed; their cold run on a different model family is owed (`evals/RESULTS.md`). Until it runs, the *beaten* and margin marks above rest on authored cases, not results.

## Evals entry — parity register (moved 2026-10-08 from the retired evalwright)

*Applies to: Entry — Evals, `references/eval-doctrine.md`, `suite-standards.md`, `claim-cases.md`, `eval-audit.md`, `eval-refresh.md`. Checked 2026-09-26 (90-day calendar, covered by this file's stamp); case numbers re-pointed to this skill's suite (evalwright Case N = Case N+55 here).*

### Incumbents

| # | Incumbent | Checked | What it does | Source |
|---|---|---|---|---|
| A | Claude Code `claude plugin eval` (with `init`) | 2026-09-26 | Runs case folders (`prompt.md` plus `graders/*.md`) in isolated sessions, 3 runs per case, a with/without-plugin baseline (`Δ`), grader types `regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`; `init` proposes should/shouldn't prompts and graders and trial-runs them. Needs the CLI and a plugin; every run is a paid model call | code.claude.com/docs/en/plugin-evals |
| B | Anthropic skill-creator eval loop | 2026-09-26 | `evals/evals.json`, grader and benchmark (pass rate, time, tokens, mean ± stddev), with-skill against no-skill or old-version baseline, 20-query trigger set with near-misses, an analyst pass that flags non-discriminating assertions after running | github.com/anthropics/skills (skills/skill-creator/SKILL.md) |
| C | promptfoo `promptfoo-evals` skill plus runner | 2026-09-26 (pages dated that day) | Writes `promptfooconfig.yaml`; deterministic asserts before `llm-rubric`; `skill-used` / `not-skill-used`; sibling-routing prompts; `--repeat 3`; companion red-team skills | promptfoo.dev/docs/integrations/agent-skill/ |

Re-scanned 2026-10-01 (unit PR): A, B, C unchanged on this job. Adjacent, not rivals: growthxai/output `output-eval-audit` (audits app-pipeline eval suites: error analysis, judge validation, coverage) and athola/claude-night-market `skills-eval` (skill quality with trigger isolation). Neither audits a skill suite's coverage map, pack pairs or counts.

Also read, for method only: the OpenAI eval-skills blog post (undated; four goal classes, negative
controls) and the Anthropic Agent Skills best-practices page ("build evaluations first", baseline
without the skill, at least three evaluations), both fetched 2026-09-26.

### Parity rows (2026-09-26 audit)

Key: **met** = as good · **beaten** = better · **missing** = an incumbent does it, the evals entry does
not · **OOS** = out of scope. Every beaten or margin row needs a claim case (`references/claim-cases.md`).

| Row | Capability | Verdict | Claim case |
|---|---|---|---|
| P1 | Derive cases from the target | beaten — the coverage map is a checked contract (re-derived, case count = map rows) | Case 70 |
| P2 | Trigger should/shouldn't set with near-misses | met | — |
| P3 | Pack cross-boundary pairs | beaten | Case 68 (existing) |
| P4 | Deterministic asserts, negatives first-class | met | — |
| P5 | With/without baseline arm | met since 1.2.0 (`Without:` / `Discriminates:`; emits map to the runner's baseline) | — |
| P6 | Reference output as the bar to beat | met since 1.2.0 (dated excerpt; `baseline` grader on emit) | — |
| P7 | Execution, repeats, variance, judges, cost ceilings | OOS — adopted runners (A, B) | — |
| P8 | Emit into a runner's format | met since 1.2.0 (plugin-eval case folders, `evals.json`) | — |
| P9 | Static audit of a suite (coverage, pairs, mechanics, counts, self-containment, discrimination) | beaten — no run needed | Case 71 |
| P10 | Diff-scoped refresh with retire-by-name | beaten | Case 72 |
| P11 | Count integrity and instrument discipline | beaten | Cases 73–76 |
| P12 | Suites run on claude.ai and the API with no install | beaten | Case 61 (existing) |
| P13 | Injection probe per ingesting entry | met for itself (Case 69); generation rule since 1.2.0 | — |
| P14 | Multi-model coverage | missing (small; declined 2026-09-26) | — |
| P15 | Mocks and fixtures | OOS — runtime harness; the Input line names fixtures | — |

### Standing sources

- **Pack baseline** — `references/eval-doctrine.md` merged skillwright's build-time eval
  authoring with the evals entry's core on 2026-10-08, so one file holds the doctrine.
- **Origin defect** — the count-integrity check exists because this pack shipped an 18-over-22
  intro miscount (found and fixed in the 2026-07-13 pack audits).

## Slim entry — doctrine sources and parity register (moved 2026-10-08 from the retired tokenwright)

*Applies to: Entry — Slim and `references/slim-doctrine.md`. The volatile measurement baseline (cache rates, per-model floors, tier costs) did not move: `slim-doctrine.md` points at the live docs instead of carrying a stamped copy. Case references below name the retired member's suite; the carried cases are 87–105 here.*

### Doctrine → source

| Guidance area | Claim(s) | Primary source(s) | Re-check |
|---|---|---|---|
| Governing principle | "Smallest possible set of high-signal tokens"; context engineering as curation of everything in the window | Anthropic engineering — *Effective context engineering for AI agents* (anthropic.com/engineering) | On refresh |
| Progressive disclosure & platform points | Skill metadata always-on at ~dozens of tokens; body ≤500-line norm loads on trigger; references on demand, one level deep | Anthropic Agent Skills best-practices + overview docs; Agent Skills open standard (agentskills.io); anthropics/skills | On refresh |
| Cache mechanics | Prefix hits; stable-first ordering; nothing after a variable element caches; Anthropic ~1.25× write / ~0.10× read by default, per-model read rates on the live docs page (not copied here: model versions live only in the one dated model file), ~5-min TTL, cache reads confirmed not counted against rate-limit utilization (added 2026-09-10, closes the prior "unsourced" flag) | Anthropic prompt-caching docs (canonical) — https://platform.claude.com/docs/en/build-with-claude/prompt-caching, fetched 2026-09-10 and 2026-09-22; cross-checked via 2026 provider comparisons and practitioner write-ups | On refresh — pricing drifts |
| Minimum cacheable length *(added 2026-07-24)* | A prefix below the model's floor never caches — `cache_control` is silently ignored, no error, and the prompt was not cached only when `cache_creation_input_tokens` **and** `cache_read_input_tokens` are both 0; the floor is per-model and does **not** track capability tier — read the live minimum-cacheable-prefix table for the model in use, never a copied list (per-model rows removed 2026-10-08: they named model versions outside the one dated model file) | Anthropic prompt-caching documentation, minimum-cacheable-prefix table — https://platform.claude.com/docs/en/build-with-claude/prompt-caching, fetched and verified 2026-09-28 (previously 2026-09-22 and 2026-09-10) | On refresh — per-model, moves with the model roster |
| Description cap *(added 2026-07-24; re-sourced to the primary source 2026-07-25; re-confirmed verbatim 2026-09-10 and 2026-09-22)* | Skill-listing entries truncate at 1,536 **characters** per entry; the limit is the `skillListingMaxDescChars` setting's default and is user-configurable. **Counting unit — `description` and `when_to_use` combined.** Settled by the primary source, restated on the 2026-09-10 read in the same words as 2026-07-25: *"the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing"* (frontmatter `description` row); *"Appended to `description` in the skill listing and counts toward the 1,536-character cap"* (frontmatter `when_to_use` row). Distinct from any repo house ceiling | **Anthropic — Claude Code skills documentation, https://code.claude.com/docs/en/skills** (canonical URL; the `docs.claude.com` path 301s here — confirmed again 2026-09-10). Full page fetched and quotes checked 2026-07-25 and re-fetched 2026-09-10 (fetch cached with this refresh's run record). Cross-check only, never the source of record: claudefa.st, *Claude Code's Hidden Skill Budget Setting* (2026-05). **Gap closed 2026-09-22:** both keys are on the settings reference page, `https://code.claude.com/docs/en/settings-reference` (the earlier checks read `/settings`, a different page): `skillListingMaxDescChars` — *"Default: `1536`"*; `skillListingBudgetFraction` — *"Default: `0.01`, which reserves 1% of the context window"*. House ceiling read directly from this repo's `tools/build.py` (hard fail >1024 `description` chars, warn ≥1000) | On refresh — configurable: re-verify the **counting unit**, not just the number |
| Skill-listing budget *(added 2026-07-25; flagged unconfirmed 2026-09-10; **re-confirmed 2026-09-22**)* | A second, separate mechanism from the per-entry cap, as sourced 2026-07-25. The listing always contains every skill **name**; descriptions are held to a budget that *"scales at 1% of the model's context window"*, tunable via `skillListingBudgetFraction` or the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable. On overflow Claude Code *"shortens descriptions to fit"* and *"drops descriptions starting with the skills you invoke least, so the skills you use most keep their full text."* Never conflated with the 1,536 cap: the cap is a hard per-entry truncation, the budget is context-window-relative pressure that can shorten or drop an entry well before 1,536. **2026-09-22 re-check — confirmed:** the section *"Skill descriptions are cut short"* is on the raw page (`/docs/en/skills.md`) with the quoted wording. The 2026-09-10 "not present" result came from a summarizing fetch that reported the terms absent while the raw Markdown carried them | Same page as the row above — Anthropic, https://code.claude.com/docs/en/skills, troubleshooting section *"Skill descriptions are cut short"*, sourced 2026-07-25; raw page re-read 2026-09-22 and the section found; both keys and their defaults on `https://code.claude.com/docs/en/settings-reference` | On refresh — read the raw `.md` page, never only a summary of it |
| Estimation ratios | ~4 chars/token English prose, ~0.75 tokens/word on the older tokenizer; code denser; markup overhead; non-Latin lower. **Tokenizer note *(added 2026-09-28)*:** Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer that produces approximately 30 percent more tokens for the same text, so prose runs ~3.1 chars/token there (derived, older ÷ 1.3); name the target model before estimating | Provider tokenizer documentation + practitioner measurement posts; tokenizers differ per family — treated as estimates with ±15% band by design. Tokenizer note: Anthropic token-counting docs, https://platform.claude.com/docs/en/build-with-claude/token-counting, fetched 2026-09-26 | On refresh — re-verify the tokenizer note |
| Net-cost accounting | Always-on rules bill per turn and can cost more than they save; tokens-per-task over tokens-per-request | drona23/claude-token-efficient (per-turn caveat, stated in-repo); bm629 token-optimization skill (tokens-per-task framing); Superpowers benchmark write-ups (clarify-first is net-cheaper) | Durable |
| Resident-vs-conditional (W10) | MCP/tool schemas load whole and always; documented five-figure always-on costs vs double-digit trigger-loaded skills | Practitioner measurements (LangSmith-CLI skills-vs-MCP post: ~16.1k always-on vs 91 activated); Claude Code session-floor reports | Durable pattern, numbers on refresh |
| Session floors | Agent CLIs start tens of thousands of tokens deep before the first user word | Firecrawl *12 Ways to Cut Token Consumption in Claude Code* (2026) + linked GH issue; /context, /usage introspection | On refresh |
| Trigger routing over resident docs | Routing triggers beat verbose always-loaded documentation; measured ~54% initial-context cut | johnlindquist context-optimization write-up (gist, 2025-12) | Durable pattern |
| Legibility floor | Telegraphic/symbol registers are runtime output tactics; instruction artifacts must survive a cold read | Contrast case — Caveman-style terseness skills (output lane); Anthropic instruction-style guidance (explain-the-why) | Durable |
| Formatting sensitivity | Cosmetic format changes shift tokenization and can move behavior — deformat carefully, measure after | arXiv literature on LLM format sensitivity (Sclar et al. 2023 et seq., surveyed in 2026 control-plane paper) | Durable |

### Parity register *(volatile — calendar, 90-day; re-scan due 2026-12-25)*

Replaces the build-day niche verdict (DEFENSIBLE, 2026-07-13; history in CHANGELOG.md). Every incumbent below was fetched 2026-09-26 for the skill-parity audit. Verdicts: **beaten** = the slim entry does more, **met** = parity, **out of scope** = runtime work routed elsewhere.

| Incumbent | Fetched | What it does | Capability rows it is measured on |
|---|---|---|---|
| nadimtuhin/claude-token-optimizer (CTO) — https://github.com/nadimtuhin/claude-token-optimizer | 2026-09-26 | `cto` CLI: `measure`, `audit` (19 structural checks, CI exit code), `compress` (deterministic rules, `--dry-run`), `prune`, `diff`, `watch`; counts with the Claude 2 tokenizer | exact count (met: the slim entry names `count_tokens` per model) · score-only audit (beaten) · rewrite smaller (beaten) · before/after proof (beaten) · set-level budget (beaten) |
| alexgreensh/token-optimizer (TO) — https://github.com/alexgreensh/token-optimizer | 2026-09-26 | Session layer: hooks compress tool output before it enters context, checkpoint and restore, a dollar-savings dashboard, an audit that flags `@imports` and MEMORY.md duplication | hidden always-loaded cost (met since 1.3.0: the load-graph step) · cache-aware restructuring (beaten) · cost in money (met: relative bands by design) · session compaction (out of scope — runtime; hook placement is rigwright's) |
| microsoft/LLMLingua (LL) — https://github.com/microsoft/LLMLingua | 2026-09-26 | Lossy token-classification compression of dynamic context, up to 20x | high-ratio lossy compression of RAG or history (out of scope — runtime context, not instructions) |
| doodledood prompt-token-optimizer (PTO) — https://mcpmarket.com/tools/skills/prompt-token-optimizer | 2026-09-26 | Nearest skill: an iterative lossless compression loop with a semantic-consistency check and atomic file replacement | rewrite smaller (beaten: safety-ordered ladder plus preservation contract) · equivalence check (met since 1.3.0: the blind equivalence probe) |
| claude-world/skills-optimizer (SO) — https://github.com/claude-world/skills-optimizer | 2026-10-01 | Fail-closed compression of skill and agent Markdown: per-concept preservation inventory, read-only verify, an apply gate of deterministic checks plus an independent semantic PASS, hashed backup and rollback | rewrite smaller (met) · preservation contract (met: inventory plus gate; the slim entry keeps the ladder's separate lossy gate) · equivalence check (met) |
| Anthropic `count_tokens` and `/skill-doctor` (platform) | 2026-09-26 | Free per-model token counting; the skill listing's own budget report | exact count (the slim entry drives it) · description cap and listing budget (beaten: no incumbent audits the three limits) |

**Margin (capabilities no incumbent has; re-scanned 2026-10-01), each tagged in `evals/test-cases.md`:** a lossless/lossy ladder whose lossy step has its own gate (SO has a preservation inventory and apply gate) · a score-only audit on a waste taxonomy · net-cost accounting by role · cache-floor-aware payback · the description-cap doctrine · portable, zero-runtime operation.

## Diagnose entry and runtime pointers (added 2026-10-08)

| Source | Licence | Read | What was taken |
|---|---|---|---|
| obra/superpowers `diagnosing-superpowers` — https://github.com/obra/superpowers/tree/main/skills/diagnosing-superpowers | MIT | 2026-10-08 | The evidence rule — every finding cites `path:line`, every number comes from the transcript or a command run — and the problem-statement step. Its analyst fan-out, case files and bug-report bundle were not adopted; no text was copied. Cases 106–108 |
| getsentry/skills `skill-scanner` — https://github.com/getsentry/skills/tree/main/skills/skill-scanner | Apache-2.0 | 2026-10-08 | Named as the first scanner the audit security pass runs as stage 1 when installed; driven as a tool, never required |
| JuliusBrussee/caveman — https://github.com/JuliusBrussee/caveman | see repository | 2026-10-08 | Named as an optional runtime output compressor; out of scope for a build-time slim |
| rtk-ai/rtk — https://github.com/rtk-ai/rtk | Apache-2.0 | 2026-10-08 | Named as an optional command-output compressor (a CLI proxy); out of scope for a build-time slim |

## Scanner stage (added 2026-10-08)

`references/scanner-stage.md` is written in this skill's own words; no text copied. Not re-fetched
for this change. The scanners it names as examples are the ones in the parity register above
(getsentry `skill-scanner`, SkillSpector, superagent-ai `skill-security`, the skilltotal MCP
server). The vet-first step points to trustwarden (warden pack), an optional sibling.
