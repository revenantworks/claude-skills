# claude-skills

**28 Agent Skills for Claude in five packs, plus optional mods. Each skill does one job, shows its
evidence, and works alone.**

![skills: 28](https://img.shields.io/badge/skills-28-blue)
![packs: 5](https://img.shields.io/badge/packs-5-blue)
![version: 1.0.0](https://img.shields.io/badge/version-1.0.0-informational)
![mods: optional](https://img.shields.io/badge/mods-optional-lightgrey)
![licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-green)
![Agent Skills: open standard](https://img.shields.io/badge/Agent%20Skills-open%20standard-lightgrey)

This repository is its own Claude Code plugin marketplace. Each pack installs as one plugin, and one
featured skill from every pack also ships on its own. Every skill follows the
[Agent Skills open standard](https://agentskills.io/), so it also runs on claude.ai, through the
Claude API, or in any compatible agent.

> [!NOTE]
> **New: mods.** [`mods/`](mods/README.md) adds two optional Claude Code plugins: `dash`, one
> dashboard that counts how the skills fire, fail and misroute, shows the meters, and suggests
> what to change (it never builds anything), and `privacy`, which masks secrets before Claude
> reads them. Installing one is the opt-in; no skill needs one.

[Quick start](#quick-start) · [Packs](#the-packs) · [Featured](#featured-skills) ·
[Mods](#mods) · [Capstones](#capstones) · [How skills route](#how-skills-route) · [Safety](#safety-posture) ·
[Testing](#testing-and-contributing) · [Licence](#licence)

## Quick start

**1. Add the marketplace once** (in Claude Code):

```
/plugin marketplace add revenantworks/claude-skills
```

**2. Then install a skill one way only.** Pick a whole pack *or* a single featured skill.

**Option A: a whole pack**

```
/plugin install warden@revenantworks
```

**— or —**

**Option B: one featured skill on its own**

```
/plugin install trustwarden@revenantworks
```

> [!IMPORTANT]
> **Load each skill once, and only where you use it.** Every enabled skill puts its description
> (about 300 tokens) in front of Claude in every conversation, and a skill loaded twice can answer
> from an older copy.
> - **Never install a featured skill and its own pack.** trustwarden is already inside the warden
>   pack; installing both loads it twice under one name.
> - **Claude Code: install the packs you work with.** Builds, scans, local programs and repo work run
>   here, where scripts have a shell and your files.
> - **claude.ai and Cowork: only the skills you use in chat** (the foundation pack is a good start).
>   warden and localops drive your own machine, so there they mostly report NOT-RUN while still
>   costing their description.
> - **Switch off what you are not using** (claude.ai: Customize → Skills). A switched-off skill costs
>   nothing.
> - **Hide synced twins in Claude Code.** A skill uploaded to claude.ai also appears in Claude Code as
>   `anthropic-skills:<name>`. Turn it off with `"skillOverrides": {"anthropic-skills:<name>": "off"}`
>   in `~/.claude/settings.json`, so only your installed copy loads.

| Packs (Option A) | Featured skills (Option B), and the pack that already holds them |
|---|---|
| `foundation` | `pacewright` (foundation) |
| `scribe` | `brandscribe` (scribe) |
| `warden` | `trustwarden` (warden) |
| `localops` | `whisperrunner` (localops) |
| `gamedev` | `pixelsmith` (gamedev) |

**3. Then just ask.** A skill loads when your request matches its description. For example:

- *"Is this skill safe to install?"* loads trustwarden.
- *"Turn this style guide into a Claude Design System."* loads brandscribe.

<details>
<summary><b>Other surfaces: claude.ai, the Claude API, a plain folder</b></summary>

- **claude.ai** (paid plans with code execution): download a skill zip from
  [Releases](../../releases), then **Customize → Skills → + → Create skill** and upload it. Per
  skill, per account; see the note above for which skills belong there and the synced twin.
- **Claude API:** upload a skill zip through the Skills API (`/v1/skills`) and reference its
  `skill_id` with the code execution tool.
- **A plain folder:** copy any skill folder from `packs/<pack>/skills/` into `~/.claude/skills/`
  (every project) or `.claude/skills/` (one project). From a clone, a junction or symlink from
  `~/.claude/skills/<skill>` to the skill folder makes an edit live in the next session.

</details>

## The packs

Five packs, one plugin each. Install the pack that matches your work and every skill in it is ready:
each one loads only when a request needs it.

| Pack | Skills | What it covers | Featured | Install |
|---|---|---|---|---|
| [**foundation**](packs/foundation/) | 9 | Building and running the work around Claude: skills and their evals, prompts, interviews, agents, config, fan-out, handoffs, pacing, platform change | pacewright | `/plugin install foundation@revenantworks` |
| [**scribe**](packs/scribe/) | 4 | Words and knowledge: research verdicts, brands and design systems, messages and docs, story canon | brandscribe | `/plugin install scribe@revenantworks` |
| [**warden**](packs/warden/) | 6 | Guarding what Claude writes or manages: leaks, identity, third-party code, disk and reach, credentials, permissions | trustwarden | `/plugin install warden@revenantworks` |
| [**localops**](packs/localops/) | 7 | Local programs, one per runner: LM Studio, ComfyUI, Docker, DuckDB, whisper.cpp, Hyper-V, OBS | whisperrunner | `/plugin install localops@revenantworks` |
| [**gamedev**](packs/gamedev/) | 4 | Game development: pixel art across zoom bands, Godot build proof, game audio by the numbers, test-first game code | pixelsmith | `/plugin install gamedev@revenantworks` |

A note on scripts: some skills ship small Python helper scripts that use only Python's built-in
standard library. Python 3 runs them with nothing to `pip install`, and each skill still works
without them.

### foundation · the wrights

Lean and standalone: no tools beyond web search, and every core job works without any script.
Capstones: Hallmark Run (build) and Upkeep Run (maintenance). Featured: **pacewright**.

| Skill | What it does | Try it with |
|---|---|---|
| [skillwright](packs/foundation/skills/revenantworks-foundation-skillwright/) | Builds, audits, ports and packs Agent Skills; writes and audits eval suites, slims a skill package and diagnoses a skill that did not fire | *"Audit this SKILL.md for best practice and security"* |
| [promptwright](packs/foundation/skills/revenantworks-foundation-promptwright/) | Builds, scores, hardens and red-teams prompts; picks the model tier for a task | *"Red-team this system prompt"* |
| [grillwright](packs/foundation/skills/revenantworks-foundation-grillwright/) | Interviews any request — code, plan, prompt, skill, agent, document — until nothing essential is left to guess, then hands a settled-decisions record to the builder | *"Grill me on this plan before we start"* |
| [agentwright](packs/foundation/skills/revenantworks-foundation-agentwright/) | Designs and audits the system around an autonomous or scheduled agent: guardrails, kill switches, cadence, failure handling | *"Add a kill switch and retries to this nightly routine"* |
| [rigwright](packs/foundation/skills/revenantworks-foundation-rigwright/) | Decides where a standing rule lives and builds the config Claude reads: CLAUDE.md, AGENTS.md, rules, Projects | *"My CLAUDE.md rules get ignored"* |
| [dispatchwright](packs/foundation/skills/revenantworks-foundation-dispatchwright/) | Turns one large request into tiered, recoverable units, dispatches them and reconciles the result | *"Plan this change across six repos and show me the plan table"* |
| [handoffwright](packs/foundation/skills/revenantworks-foundation-handoffwright/) | Writes a committed session handoff or a forward task brief, ending in a paste-ready starter prompt | *"Write the handoff"* |
| [pacewright](packs/foundation/skills/revenantworks-foundation-pacewright/) | Paces subscription usage across the meters, with spend modes and a leak check | *"Something ate my usage overnight"* |
| [scoutwright](packs/foundation/skills/revenantworks-foundation-scoutwright/) | Searches the web for what is new in Claude (docs, changelogs, release notes, community) and brings back an adopt list: how each change can improve your skills, projects and setup. Sites that block automated readers are reached through researchscribe when it is installed | *"What changed in Claude Code since last month, and what should I adopt?"* |

### scribe · words and knowledge

Helper scripts allowed when declared, built-in library first. Every skill ships with no brand,
voice or canon: nothing exists until you build one or hand one in. Capstone: Herald Run. Featured: **brandscribe**.

| Skill | What it does | Try it with |
|---|---|---|
| [researchscribe](packs/scribe/skills/revenantworks-scribe-researchscribe/) | Researches a question into a verdict with a flip condition, a playbook or a graded report; every claim tagged | *"Compare A and B and give me a go/no-go"* |
| [brandscribe](packs/scribe/skills/revenantworks-scribe-brandscribe/) | Keeps brand definitions and builds a live Claude Design System from one, plus DESIGN.md and VOICE.md; re-syncs it when the brand changes; scores pages against a neutral UI floor | *"Turn this style guide into a Claude Design System"* |
| [commscribe](packs/scribe/skills/revenantworks-scribe-commscribe/) | Writes and reshapes messages and docs for their channel and reader, and never moves a fact | *"Make this release note sound less like AI"* |
| [lorescribe](packs/scribe/skills/revenantworks-scribe-lorescribe/) | Keeps a fiction project's story bible and checks text, briefs and drafts against canon | *"Check this chapter against the story bible"* |

### warden · guarding what Claude touches

Each helper script is declared, ships with a test, and has a fallback for when no shell is
available. Hooks ship as files you install by hand. Capstone: Gatehouse Run. Featured: **trustwarden**.

| Skill | What it does | Try it with |
|---|---|---|
| [shieldwarden](packs/warden/skills/revenantworks-warden-shieldwarden/) | Keeps your identity and secrets out of anything public: scans for secrets, personal data and injected instructions, sets which names and identities may appear on each surface, flags files whose names advertise secrets, and plans gated history rewrites that never push | *"Scan this repo for secrets before I publish it"* · *"Which email will my next commit use?"* |
| [trustwarden](packs/warden/skills/revenantworks-warden-trustwarden/) | Vets third-party code before install and ends with a verdict and install terms | *"Is this MCP server safe to add?"* |
| [keywarden](packs/warden/skills/revenantworks-warden-keywarden/) | Finds where every credential lives, as fingerprints; scopes, rotates and handles leaks | *"Is my gh token too broad?"* |
| [gatewarden](packs/warden/skills/revenantworks-warden-gatewarden/) | What Claude may do and what it actually reaches: audits runtime permission rules and hooks, maps every settings level, rule and hook, security-scans an agent's tool grants, and maps disk space and every path Claude has reached, from evidence; proposes, never deletes | *"Why was this command allowed?"* · *"Where has Claude been on this machine?"* |

### localops · one program per runner

Each runner drives one local program and the helpers it declares. Installs stay with you, through a
walkthrough. Capstone: Workbench Run. Featured: **whisperrunner**.

| Skill | What it does | Try it with |
|---|---|---|
| [lmstudiorunner](packs/localops/skills/revenantworks-localops-lmstudiorunner/) | Hands work to a local LM Studio model and verifies what comes back | *"Batch these summaries to a local model overnight"* |
| [comfyrunner](packs/localops/skills/revenantworks-localops-comfyrunner/) | Runs ComfyUI image, video and audio renders behind GPU guards | *"Test this video workflow before the long render"* |
| [dockerrunner](packs/localops/skills/revenantworks-localops-dockerrunner/) | Runs Docker Desktop and WSL2 with RAM and disk checks first | *"Docker Desktop will not start"* |
| [duckrunner](packs/localops/skills/revenantworks-localops-duckrunner/) | Ask a question in plain words and get the answer from your data: it queries your CSV, JSON, Parquet and YAML files, or an existing DuckDB database file, and shows the SQL it ran. Read-only; your files are never changed | *"Which items are still open, and how many per owner?"* |
| [whisperrunner](packs/localops/skills/revenantworks-localops-whisperrunner/) | Transcribes local audio and video with whisper.cpp, with backend proof | *"Transcribe this meeting recording"* |
| [hypervrunner](packs/localops/skills/revenantworks-localops-hypervrunner/) | Builds and proves Hyper-V VMs; tests untrusted files inside a disposable Windows Sandbox with networking off, never on your real machine | *"Test this download in Windows Sandbox"* |
| [obsrunner](packs/localops/skills/revenantworks-localops-obsrunner/) | Drives OBS Studio, read-only by default, and cuts clips and chapters with FFmpeg | *"Why does my stream drop frames?"* |

### gamedev · the smiths

Helper scripts use Python's built-in library only, when declared; no third-party packages and no
network at runtime. Capstone: Forge Run. Featured: **pixelsmith**.

| Skill | What it does | Try it with |
|---|---|---|
| [pixelsmith](packs/gamedev/skills/revenantworks-gamedev-pixelsmith/) | Directs pixel art that must read at every zoom band, including a pixelated-3D band | *"This hut vanishes against the grass when zoomed out"* |
| [godotsmith](packs/gamedev/skills/revenantworks-gamedev-godotsmith/) | Godot 4.x conventions and the proof that a build is really green | *"GUT is green, but did every test file parse?"* |
| [soundsmith](packs/gamedev/skills/revenantworks-gamedev-soundsmith/) | Directs game audio and judges it by numbers: loudness, true peak, loop seams | *"What LUFS should my game's SFX hit?"* |
| [slicesmith](packs/gamedev/skills/revenantworks-gamedev-slicesmith/) | Writes game code test-first in thin slices a player can reach, with a Godot verify ladder and an honest commit per slice | *"Implement autosave, one slice at a time"* |

## Featured skills

One skill from each pack also ships as its own plugin, for when you want just that job. Each one does
something its public alternatives do not, works with no other skill installed, and carries its own
evals. Install it **or** its pack, never both.

| Skill | Pack | What sets it apart | Install |
|---|---|---|---|
| [pacewright](featured/pacewright/) | foundation | Turns usage meters into a spend plan: modes, what fits before a reset, and a check when usage jumps for no reason | `/plugin install pacewright@revenantworks` |
| [brandscribe](featured/brandscribe/) | scribe | Builds a live Claude Design System from one written brand, and re-syncs it without losing page edits | `/plugin install brandscribe@revenantworks` |
| [trustwarden](featured/trustwarden/) | warden | Vets a skill, plugin, MCP server or Action before install; lists every file no scanner read, and ends with a verdict and install terms | `/plugin install trustwarden@revenantworks` |
| [whisperrunner](featured/whisperrunner/) | localops | Local transcripts with proof the GPU did the work; a silent CPU fallback or a looping transcript fails | `/plugin install whisperrunner@revenantworks` |
| [pixelsmith](featured/pixelsmith/) | gamedev | Pixel-art rules and a look test for every zoom level of one game camera, with contrast as a number | `/plugin install pixelsmith@revenantworks` |

Each skill's page in `featured/` has the full story, more prompts to try, and what it needs.

## Mods

Mods are optional Claude Code plugins in [`mods/`](mods/README.md). A skill tells Claude how to do
a job; a mod watches the session while it runs. Mods are function-hook plugins, so they need Claude
Code 2.1.287 or later and run in Claude Code only. VS Code gets a small local extension that keeps
the dashboard in its status bar.

| Plugin | Holds | At install |
|---|---|---|
| `dash` | Skill fires (slash or automatic), failures, likely misroutes, tokens and cost by skill; the 5-hour, weekly, context and cache meters; health; background tasks; research, GPU, Godot and PR panels; a suggestion queue that proposes, never builds | On; records and PR reads opt-in |
| `privacy` | Secret and stream-key masking, the rotate tripwire, untrusted-content and received-message markers | On |

**Installing a mod is the opt-in.** Its features run from install, as with any Claude Code plugin;
`/dash off <name>` turns any off and `/dash off` stops them all. No mod blocks your work: blocking
lives in hooks and permissions. No mod sends your data anywhere, and no mod keeps a record of your
work on disk until you say yes: the dashboard asks once, and `/dash records on` answers it. Its
records hold counts, names, hashes and shapes, never prompt or command text. No mod contacts GitHub
until you say yes (`/dash network on`); the read then runs only when you act, never on a timer.

```
/plugin install dash@revenantworks
```

```
/plugin install privacy@revenantworks
```

[mods/README.md](mods/README.md) covers all 18 features, the commands, the suggestion thresholds,
the surfaces, and the files the mods write. Each skill a mod feeds carries `references/mods.md`.

## Capstones

A **capstone** is a ready-made run card that chains every skill in one pack through one real job,
start to finish, in a set order. Each skill alone does one step well; the capstone makes them
hand work to each other, and says where it stopped if a skill is missing.

**Why use one**
- **No glue work.** You give one set of inputs; each leg hands its result to the next skill.
- **A proven order.** Checks run before anything leaves your machine or reaches the public.
- **Honest endings.** A run that stops early says so in plain words, such as *MADE, NOT CLEARED*
  or *DECIDED, NOT SAID*, instead of claiming success.
- **Skippable legs.** A missing skill is named, its leg is skipped, and the run carries on where
  it safely can.

**How to run one.** Install the pack. Open the card in the pack's `capstone/` folder, fill in the
`{{inputs}}` at the top, and paste the whole card as your prompt. From a clone you can point Claude
at the file instead: *"Run packs/warden/capstone/gatehouse-run-capstone-card-v1.0.0.md for this MCP
server."*

| Capstone | Pack | What it does, in plain words |
|---|---|---|
| **Hallmark Run** | foundation | Takes one new skill from idea to release: research, prompt and build, evals, token trim, config, then ship. |
| **Upkeep Run** | foundation | Keeps a shipped pack healthy: fits the work to your usage limits, finds what Claude changed since the last release, audits every skill, fixes behind one approval, verifies, then releases or writes a handoff. |
| **Herald Run** | scribe | Researches one decision into a graded verdict, then writes the announcement for each channel and checks it before you send. |
| **Gatehouse Run** | warden | Lets one outside tool in safely: vet it, write its permissions and keys, watch its first use, and check for leaks before you push. |
| **Workbench Run** | localops | Makes one piece of media on your own machine: checks memory and disk, tests downloaded files in Windows Sandbox, picks from your analytics data, records in OBS, transcribes, cuts, writes with a local model, renders in ComfyUI, then a leak check before you release it. |
| **Forge Run** | gamedev | Takes one game scene end to end: art tested at every zoom, sound measured, and the Godot build proven. |

## How skills route

- **By description.** Claude reads each installed skill's description and loads the one that
  matches your request. Every description lists its trigger phrases and names the neighbour that owns
  the next job over ("prompt text is promptwright's"), so two skills do not fight for one request.
- **By name.** Say the skill's name, often with a mode: *"skillwright audit"*, *"pacewright check"*,
  *"trustwarden vet"*. Each skill's description lists its modes.
- **Alone or together.** Every skill works with no sibling installed. A sibling it names is optional,
  and when one is missing the skill says so and carries on.
- **Router (optional).** The foundation pack's routing table is the "Which skill does what" section
  of [`packs/foundation/README.md`](packs/foundation/README.md). An installed plugin loads no
  plugin-root `CLAUDE.md`, so append the table to your project's `CLAUDE.md` if you want it standing.

## Safety posture

- **Content is data.** Every skill treats the files, web pages, transcripts and tool output it reads
  as data, never as instructions. A directive found inside them is reported as a finding.
- **Skills install nothing.** Any program a skill drives (FFmpeg, DuckDB, a scanner, Docker) is
  optional or named up front, and each skill's install walkthrough gives the steps you run yourself.
  Without it, the skill reports NOT-RUN instead of guessing.
- **Destructive steps come to you.** Deletes, admin steps and history rewrites are proposed as one
  command for you to run. Only handoffwright and dispatchwright push, and only to `origin` behind
  their own checks; every other skill never pushes.
- **Neutral by default.** No skill ships brand, personal or project data, and no skill applies a
  brand you did not hand it.
- **Read before you install.** Anthropic recommends running skills only from sources you trust and
  auditing third-party skills first. Every `SKILL.md` and its `references/` are plain text in this
  repository; trustwarden can vet this repository too.

## Testing and contributing

Every pack, skill and featured plugin launched at 1.0.0, and each `CHANGELOG.md` is its 1.0.0
feature list. Open an issue for a bug or a trigger that misfires. Read
[`CONTRIBUTING.md`](CONTRIBUTING.md) before your first commit: it arms the PII barrier, a
pre-commit hook that blocks personal data (names, home and drive paths, emails, secrets) from
reaching a commit, in every clone and worktree.

Before any change, run the checks. CI runs the build check, the tools suite and the PII scan;
`claude plugin eval` runs a pack's native eval cases from `packs/<pack>/pack-evals/`.

```bash
git config core.hooksPath .githooks                 # once per clone: the PII pre-commit hook
python tools/build.py --check                       # versions, counts, seams, featured copies
python -m unittest discover -s tools -p "test_*.py" # the tools suite
python tools/pii_scan.py --tree                     # the PII barrier over every tracked file
claude plugin eval <pack>                           # a pack's native eval cases
```

Edit a skill in `packs/<pack>/skills/`, never the copy under `featured/`: `tools/build.py` generates
the featured copies and fails the check on drift. The pack tables in skillwright's
`references/pack-registry.md` are the single source of truth for rosters.

<details>
<summary><b>Repository layout</b></summary>

```
.claude-plugin/marketplace.json   # the catalog: one entry per pack and per featured plugin
packs/<pack>/                     # a plugin: plugin.json · skills/ · README.md (the pack rule) · NOTICE · capstone/ · pack-evals/
packs/localops/shared/            # pack-shared sources (holders.json); build.py writes each holder's copy
featured/<skill>/                 # a one-skill plugin generated from its pack member
tools/build.py                    # registry-derived sync, validation and dist zips (--check is the CI mode)
tools/release.py                  # the release loop: bump, build, check, tests, commit, tag, upload list
tools/name_leak.py                # local, before a push: fails a tracked file holding a name from ~/.warden/wordlist.txt
tools/pii_scan.py                 # the PII barrier: pre-commit hook (.githooks/) and the pii-scan CI job
RUNBOOK.md                        # release and sync procedure
CONTRIBUTING.md                   # contributor setup: arm the PII hook in every clone
```

</details>

## Licence

Apache License 2.0. The root [`LICENSE`](LICENSE) is the verbatim Apache-2.0 text and the root
[`NOTICE`](NOTICE) carries the attribution notice. Every skill folder carries its own `LICENSE` and a
`NOTICE` generated from its pack's, so a skill copied on its own keeps both. What ships in 1.0.0 is
in [`CHANGELOG.md`](CHANGELOG.md).
