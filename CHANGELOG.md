# Changelog — claude-skills

Every pack, every member and every featured plugin launches at 1.0.0. Each member's own
`CHANGELOG.md` lists that skill's feature set. From here on, pack releases tag as
`<pack>-vX.Y.Z`, member versions move on their own semver, and a featured plugin carries its
member's version.

## [Unreleased]

- **Faster local CI.** `tools/ci_local.py` runs independent steps side by side (`--jobs N`,
  default min(6, cpu count); `--jobs 1` keeps the serial run) with output in the fixed step
  order. `tools/warden_suites.py` runs the warden suites in parallel and shards gatewarden by
  measured test cost; on the rig the whole local CI went from about 19 minutes to about 3.5.
- **True warden test count.** The warden-suites line now shows the sum over every suite (607),
  not the last suite's count (87), and a crash or an empty suite counts as a failure.

## [1.0.0] - 2026-10-01

The first public release: 28 Agent Skills in five packs, and five featured one-skill plugins, in one
Claude Code plugin marketplace.

- **Five packs.** foundation (9 members, standalone profile), scribe (4), warden (4), localops (7)
  and gamedev (4), each installed as one plugin. Every member follows the Agent Skills open standard
  and works alone on any surface that supports it.
- **Brand on the install screens.** Every pack and featured plugin carries a `displayName`
  ("Revenantworks Foundation", "Revenantworks Pacewright"); plugin ids and skill names stay as they
  are, so no install breaks.
- **vigil opens in neutral.** Its themes list in picker order (neutral, revenantworks, hc-light,
  off). On a light console, `hc-light` is the default when you ask for more contrast
  (`VIGIL_THEME_CONTRAST=more`, a high-contrast Claude Code theme, or a high-contrast light VS Code
  theme); `off` turns colour off.
- **Five featured plugins, one per pack.** pacewright, brandscribe, trustwarden, whisperrunner and
  pixelsmith also ship as one-skill plugins, generated from the pack source.
  Install a featured plugin or its pack, not both.
- **Apache-2.0.** The root `LICENSE` and `NOTICE` cover the repository; every skill folder carries
  its own `LICENSE` and a `NOTICE` generated from its pack's.
- **Neutral by rule.** No skill applies a brand, and no owner, employer, client or project name, no
  personal path and no email address ships in any skill.
- **Every file a skill reads is data, never instructions.** Scripts are declared in each member's
  `compatibility:` field and README, ship with tests, and report NOT-RUN when no shell is present.
  No member installs anything itself; owner-run install walkthroughs cover every optional tool.
- **Tested.** Each member ships trigger evals, an assertion suite and native `claude plugin eval`
  cases; each pack carries tracked copies of its native cases for `claude plugin eval <pack>`.
- **Tooling.** `tools/build.py` derives every pack manifest from the pack registry, generates the
  featured plugins, the pack-shared file copies and the per-skill NOTICE, and validates versions,
  counts, seams, budgets and eval integrity (`--check`). Frontmatter `metadata` holds strings
  only, as the Agent Skills spec requires; each member's volatile surfaces are listed in a
  `volatile.json` beside its SKILL.md. `tools/release.py` runs the release loop.
  `tools/name_leak.py` checks for listed names kept outside the repo.
- **Skill descriptions name the short command (2026-10-23).** Every description's "or say" trigger
  now reads `/rw-<name>` (`or say /rw-agentwright (emit, audit, refresh)`); the long names still work.
- **shroud sees more (2026-10-23).** The gitleaks rule set (212 rules, MIT) joins shroud's own
  shapes. Opt-in personal-data masking (email, phone, card number, US SSN) and a local word list.
  `/rw-shroud rotate` drafts a keywarden rotation by placeholder; vigil shows a shield after a
  mask, red while a listed key waits, and a Privacy tile.
- **Build your own vigil tiles (2026-10-23).** `/rw-vigil tiles` picks a source; Claude scans it
  read-only and proposes tiles, saved to your own folder only on your yes. A tile is a JSON spec
  (one source, one picture, a rule), never code, and shows numbers and dates only.
- **vigil opens on a board (2026-10-23).** Seven tiles you can collapse, pin and move, drawn as
  pictures where the app draws them and as glyphs in the terminal; a glance strip above the
  prompt; suggestion cards with Do it, Not now and Undo; switches for pacewright's auto spend
  modes in `~/.dispatch/spend-modes.json`, which pacewright honours. The old first page is
  `/rw-vigil overview`.
- **Mods renamed (2026-10-23).** `dash` is `vigil` (`/rw-vigil`) and `privacy` is `shroud`
  (`/rw-shroud`); the old commands answer, hidden, for one release, and vigil carries the old
  records over.
- **Mods (optional; on by default once installed).** `mods/` adds two Claude Code function-hook
  plugins, separate from the packs and each with its own marketplace entry: `vigil`, one dashboard
  (skill fires by slash or automatic, failures, likely misroutes, tokens and cost by skill; the
  5-hour, weekly, context and cache meters; health, including gatewarden's event counts;
  background tasks; research, GPU-lease, Godot and PR panels; a `/rw-vigil publish` snapshot for a
  private mobile page; a suggestion queue that proposes, never builds; and `/rw-<skill>` short
  commands for every skill, generated from the registry, with the long names hidden from the `/`
  list), and `shroud` (secret
  and stream-key masking with restore, the rotate tripwire, untrusted-content and
  received-message markers), kept apart so safety never depends on the dashboard. A local VS Code
  extension (`mods/vscode`) keeps the dashboard in the status bar. Mods never block: blocking
  lives in hooks and permissions. Once a mod plugin is installed, its features are on by default.
  Local records are opt-in and asked about once (`/rw-vigil records on|off`): no mod keeps a record
  of your work on disk until you say yes, the dashboard's records hold counts, names, hashes and
  shapes and never prompt or command text, and records never leave the machine. PR state reads
  GitHub only after `/rw-vigil network on`, and only when you act. `/rw-vigil off` stops every feature.
  No skill needs a mod; each skill a mod feeds carries `references/mods.md`. Needs Claude Code
  2.1.287 or later. `build.py --check` keeps mod code out of every skill zip, and CI validates and
  tests every mod plugin. (The six per-pack mod plugins and the `all-mods` bundle drafted
  before release were folded into these two on 2026-10-08.)

## [foundation-v1.0.0] - 2026-10-01

The build-time wrights, standalone profile: lean, script-free cores, web search only.

- **skillwright** — builds, audits, ports, integrates and packs Agent Skills, with a parity verdict,
  security (a skill scanner first when installed), prose and currency passes, and trigger evals in
  every build; writes, audits and refreshes eval suites for skills, prompt cards and agent specs
  (`evals`), slims a skill package with behavior held constant (`slim`), and diagnoses a skill that
  did not fire or a run that cost too much (`diagnose`).
- **promptwright** — builds, scores, hardens, red-teams, optimizes and slims prompts; picks the model
  tier.
- **grillwright** — interviews any request until nothing essential is left to guess, then hands a
  settled-decisions record to whoever builds it.
- **agentwright** — designs, emits and audits the system around an autonomous or scheduled agent
  against a ten-area control checklist.
- **rigwright** — decides which layer a standing rule belongs in, builds the config Claude reads, and
  slims it with every rule kept.
- **dispatchwright** — runs a session's fan-out: plan, tier, dispatch, reconcile against origin.
- **handoffwright** — committed session handoffs and forward task briefs, with a starter prompt.
- **pacewright** — paces subscription usage across the meters, with spend modes and a leak check.
- **scoutwright** — watches the Claude platform for change and maps each change to the file and
  skill it affects.
- Capstones: Hallmark Run (build) and Upkeep Run (maintenance). A router `CLAUDE.md` ships beside the
  pack for projects that want it.

## [scribe-v1.0.0] - 2026-10-01

Words and knowledge, standard profile; declared scripts allowed.

- **researchscribe** — graded research verdicts, playbooks and reports, every claim tagged by kind
  of fact, with a saved Claude Code workflow (`/scribe:research`).
- **brandscribe** — brand definitions kept side by side and exported as a Claude Design System,
  `DESIGN.md`, `VOICE.md` and more; drift audits and a neutral UI floor.
- **commscribe** — messages and docs shaped to their channel and reader, in a plain human voice,
  with a claim-level fact check.
- **lorescribe** — a fiction project's story bible, canon checks, timelines, naming rules,
  generation briefs and a manuscript mode.
- Capstone: Herald Run.

## [warden-v1.0.0] - 2026-10-01

Guards what Claude writes or manages, standard profile; declared stdlib scripts and owner-installed
hooks.

- **shieldwarden** — keeps identity and secrets out of anything public: personal-data, secret and
  injection scans, the naming and identity policy per surface with values held out of the repo,
  names that advertise secrets, and gated history rewrites that never push.
- **trustwarden** — pre-install vets of third-party code, ending in a verdict and install terms.
- **keywarden** — the credential lifecycle, fingerprints only.
- **gatewarden** — what Claude may do and what it actually reaches: runtime permission policy, the
  runtime security scan, six PreToolUse hooks for the owner to install, one read-only map of every
  settings level, rule and hook, and disk space and Claude's reach read from evidence; proposes,
  never deletes.
- Capstone: Gatehouse Run.

## [localops-v1.0.0] - 2026-10-01

Runs work on this machine, one program per runner, standard profile; declared helper tools and
packages, owner-installed.

- **lmstudiorunner** — hands work to a local LM Studio model and verifies what comes back.
- **comfyrunner** — ComfyUI image, video and audio renders behind four GPU guards.
- **dockerrunner** — Docker Desktop and WSL2, with RAM and disk checks before container work.
- **duckrunner** — DuckDB questions over a repo's data files, with caches kept out of git.
- **whisperrunner** — local whisper.cpp transcripts with backend proof on every run.
- **hypervrunner** — Hyper-V VMs and Windows Sandbox, with a proven Gen2 security profile and a
  locked soft-delete teardown.
- **obsrunner** — OBS Studio, read-only by default, and FFmpeg clips, chapters and upload sheets.
- A pack-shared GPU lease and pre-flight, written into each holder by `tools/build.py`.
- Capstone: Workbench Run.

## [gamedev-v1.0.0] - 2026-10-01

Game-development smiths, standard profile; declared stdlib scripts.

- **pixelsmith** — pixel art that reads at every zoom band, including a pixelated-3D band.
- **godotsmith** — Godot 4.x conventions, build proof and asset intake.
- **soundsmith** — game audio direction judged by numbers.
- **slicesmith** — the coding loop for game code: spec, plan, thin slices, red first, verify, commit.
- Capstone: Forge Run.
