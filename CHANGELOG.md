# Changelog — claude-skills

Every pack, every member and every featured plugin launches at 1.0.0. Each member's own
`CHANGELOG.md` lists that skill's feature set. From here on, pack releases tag as
`<pack>-vX.Y.Z`, member versions move on their own semver, and a featured plugin carries its
member's version.

## [warden-v1.1.5] - 2026-11-13

### Fixed

- **gatewarden**: push_gate no longer matches a same-line git config write by its path text, which a split string (`'.gi'+'t/config'`), a folder change (`cd .git && … >> config`) or a .NET call slipped past. Before a non-builtin git subcommand, a line is refused when it runs inline code that can write a file or start a process (`python -c`, `node -e`, `perl -e`, `ruby -e`, `php -r`), a .NET or COM write, a PowerShell file writer with any target, a nested shell body that writes (`bash -c`, `sh -c`, `cmd /c`, `pwsh -Command`), or any write whose target is named like a config or sits inside a `.git` folder. Any word on the line (an argument or option value) that resolves inside a `.git` folder or to a git config file counts as a write unless its program only reads, so archive, decode and editor tools (`tar -C .git`, `unzip -d .git`, `7z -o.git`, `certutil`, `ed`, `Expand-Archive`) are refused without a list. A config written in an earlier call or by a file-edit tool is read on the next call, a stated limit. Inline code that only prints, ordinary file writes and every builtin still pass.

## [warden-v1.1.4] - 2026-11-13

### Fixed

- **gatewarden**: push_gate checks a non-builtin git subcommand against every folder or git dir the line names (cd in any form, `-C`, `--git-dir`, `GIT_DIR`, `env -C`, `-WorkingDirectory`, find paths, `cwd=` in inline code), read lexically and through junctions, and refuses it when it is a pushing alias in any of them. A pushing alias set in another repo no longer passes through a subshell, a pipe, `&`, a failed cd, a nested shell, eval, `find -execdir`, Start-Process or a split program name in inline code. A folder word must be a plain literal path that exists now: a glob, quote splice, backslash escape, `~`, bare `cd` or `cd -`, a provider drive, a folder that does not exist yet, a line that writes a git config (a redirection or copy onto `.git/config`, a `git config` write or include), or a line that sets CDPATH or OLDPWD or uses New-PSDrive, subst or a link refuses a non-builtin. The builtin list is git's whole command list, so everyday commands such as `prune`, `rerere` and `verify-tag` pass.

## [hearth-v1.0.2] - 2026-11-13

### Improved

- **hearth**: The pack README now points at plugin.json for its version and names faretender as its one skill.

## [warden-v1.1.3] - 2026-11-13

### Improved

- **gatewarden**: A push that sends commits straight to main on a public repository is refused (`push_gate.public_main`); the pull request is the merge path. A branch that goes to a public repository is first read for secret shapes and run through the repo's armed pre-push hook, and a hit, or a check that did not run, refuses in every mode (`push_gate.public_leak`).
- **gatewarden**: The local-CI stamp script gives every step a deadline (`--step-timeout`, default 45 minutes) and kills a hung step with its children, and `loads` flags a plugin id that settings enable but nothing installs, or the reverse.
- **gatewarden**: The tests mark the stub pre-push hook executable so Linux CI runs it, with a new test that a non-executable hook is refused.
- **gatewarden**: push_gate refuses a non-builtin subcommand when git aliases cannot be read (it failed open on a timeout, an error, a folder the same line creates, or a folder set at run time).
- **trustwarden**: The pin check compares the top-level licence file at both SHAs and holds the pin on a changed, added or removed licence.
- **shieldwarden**: The policy and scan-shape references gain a rule for repos that take writes from outside a machine hook's reach, and a test-output leak shape.
- **warden**: The pack README points at plugin.json for its version.

## [scribe-v1.1.1] - 2026-11-13

### Improved

- **brandscribe**: Marks keep theme values out of approved art and the audit reports baked hexes as frozen art; a scripted design-system re-sync edits from a pristine copy; collision floors are measured per theme, and a version bump hunts retired hexes in every consumer.

## [localops-v1.0.3] - 2026-11-13

### Improved

- **comfyrunner**: `comfy_client.py nodes --all --save-info FILE` saves the server's whole node list in one call.
- **whisperrunner**: A configured binary or model path that no longer exists stops with the one command that re-points it; "not found" now names where it looked; `--no-context` is passed through, with advice for synthetic audio and a script-check recipe.
- **obsrunner**: `status` reads a disabled replay buffer as off and keeps the verdict OK.

## [gamedev-v1.2.1] - 2026-11-13

### Improved

- **godotsmith**: New traps and checks in the GUT, GDScript, determinism, export and CI-guard references: `-gselect` is a substring match, a one-script run with no summary is no run, and more.
- **slicesmith**: A "red for the right reason" section for new functions, seams, switches and filters, and sharper spec and plan steps.
- **uismith**: The probe reports spilled text, a cell or grid item wider than its box, in the Clipped column; the old probe passed such a page.

## [foundation-v1.1.2] - 2026-11-13

### Improved

- **dispatchwright**: The unit-brief template, meters and ledger-schema references carry the lessons of recent fan-out runs.
- **agentwright**, **rigwright**, **skillwright**: New design-checklist, audit-evidence, eval-audit and MCP-tool checks.
- **pacewright**, **scoutwright**: Mode and bench references updated.

## [hearth-v1.0.1] - 2026-11-12

### Improved

- **faretender**: The fee and claim rules now cite primary sources: the FTC's own FAQ on what a price may leave out, the UK CAA and US DOT pages, and the UK text of Article 7 (GBP 220, 350, 520). The trigger description gains "fees reviewers mention".
- **faretender**: The nine native evals were run and the results recorded; the fees trigger case now names its hotels and one grader ignores case.


## [warden-v1.1.2] - 2026-11-12

### New

- **gatewarden**: `install_hooks.py`, an owner-run one-command installer for the shipped hooks. `--check` lists each hook file as same, differs or missing; the default backs up each differing live file, copies the repo version in and verifies it. It refuses a rig-newer file unless told to, and refuses a dirty or non-main checkout.

### Fixed

- **gatewarden**: A go-live hint word inside an inert quoted literal no longer fails the whole line closed.
- **gatewarden**: A `push_gate` intend or preflight chained before a push on one line is refused with a message that says to run intend as its own command.


## [warden-v1.1.1] - 2026-11-11

### Improved

- **gatewarden**: The gate lets a branch go to a public repository when it is a fast-forward of that repository's main, and says the commits become public now; a branch built on an older main is still refused, with a rebase fix.
- **gatewarden**: One repository per call; the heredoc refusal says plainly that a full heredoc is refused too; the gate says to fetch when it cannot read main's tip.
- **warden**: Every member's pack roster now lists vaultscribe; shieldwarden adds a rewrite recipe.

## [scribe-v1.1.0] - 2026-11-11

### New

- **vaultscribe**: The fifth scribe sets up, runs and keeps honest an LLM-maintained knowledge vault (raw sources, a cited wiki and a rules file, viewed in Obsidian or any Markdown folder), with ingest, query, lint, refresh and harden.

### Improved

- **researchscribe**: Fetches go by source tier, primary first, and a run stops cleanly when a source refuses automated reads.
- **brandscribe**: Every UI handback opens with what was injected and the verdict.
- **scribe**: The pack and repo docs route vault work to vaultscribe.

## [localops-v1.0.2] - 2026-11-11

### Improved

- **localops**: Every runner's pack roster now lists vaultscribe, so vault summaries route to it.

## [gamedev-v1.2.0] - 2026-11-11

### New

- **uismith 1.1.0**: A new artifact-pages reference for a theme and phone pass on published pages: purpose first, one shared theme kit instead of hand-rolled switches, tabs with a phone bottom bar, freshness stamps, downloads that work inside claude.ai, and a vetted adopt and reject list of page best practices.

### Improved

- **gamedev**: Plugin descriptions are shorter, to fit the claude.ai limit.

## [foundation-v1.1.1] - 2026-11-11

### Improved

- **skillwright**: The pack registry now lists vaultscribe in the scribe pack.
## [warden-v1.1.0] - 2026-11-04

### Improved

- **gatewarden**: Clamp the budget file's stop band in launch_throttle.
- **gatewarden**: Keep the 95 stop when a budget band is NaN.
- **gatewarden**: Document the clean-worktree push route.
- **gatewarden**: Draw the treemap page in the Neutral palette.
- **packs**: Name the /rw- command in every skill description.
- **gatewarden**: Read zero counts as passes and stamp repos with no CI.
- **gatewarden**: Fire on delete-the-biggest requests and hand over -Confirm.
- **keywarden**: Run the pre-flight even when the shape is obvious.
- **shieldwarden**: Name who can open each signpost hit in the script's words.
- **gatewarden**: Put the map must-says in the entry table.
- **warden**: Widen two more shell eval graders that failed correct runs.
- **gatewarden**: Refuse a script the gate cannot read that names push.
- **warden**: Widen the treemap eval's local-file grader.
- **gatewarden**: Flag wrong-surface skills and listing cost in loads.
- **gatewarden**: Check loads against the listing budget and live copies.
- **gatewarden**: Rewrite dead denies in harden, name the colon-star shape.

### Fixed

- **warden**: Stop three shell eval graders failing correct runs.
- **trustwarden**: Stop flagging curl piped to json.tool.

## [scribe-v1.0.1] - 2026-11-04

### Improved

- **brandscribe**: Scan for injected lines as its own ui step.
- **brandscribe**: Ordinary control labels are not injected lines.
- **packs**: Name the /rw- command in every skill description.

## [localops-v1.0.1] - 2026-11-04

### New

- **obsrunner**: Add a playtest mode for recorded play sessions.

### Improved

- **whisperrunner**: Default run to the configured VAD model.
- **packs**: Name the /rw- command in every skill description.

## [foundation-v1.1.0] - 2026-11-04

### New

- **vigil**: Add the board, suggestion cards and spend-mode switches.

### Improved

- **pacewright**: Make the budget writer refuse a no-cap turbo file.
- **dispatchwright**: Gate turbo launches on the rig, cap writers at six.
- **pacewright**: Replace turbo's no-cap rule with the rig-aware turbo.
- **dispatchwright**: Write the rig-gate, stuck and brief-file rules.
- **dispatchwright**: Fit the rig gate in its budget and count what runs.
- **dispatchwright**: Keep the ledger guard inside its hook timeout.
- **pacewright**: Clear a kept ceiling when the writer enters turbo.
- **dispatchwright**: Isolate the hook controls and drop the no-cap line.
- **pacewright**: State the rig-aware turbo in the profile, eval and gate.
- **dispatchwright**: Slim the body to its row and fix the stuck rule.
- **dispatchwright**: Bind any unit id shape to its own ledger row.
- **dispatchwright**: Count the leaf engines in the rig gate.
- **dispatchwright**: Bind launches by ledger row id and refuse dup ids.
- **dispatchwright**: Say one land is one suite slot in the brief template.
- **dispatchwright**: Count stuck checks per row and add four brief rules.
- Gamedev, dispatchwright: fold in a game's test-speed lessons.
- Gamedev, dispatchwright: apply the fresh review of the test-speed fold.
- **packs**: Name the /rw- command in every skill description.

## [gamedev-v1.1.0] - 2026-11-04

### New

- **slicesmith**: Add stacked pin round; run touched scripts, full suite once.
- **godotsmith**: Add shared user:// trap and pushed-head stamp rule.
- **godotsmith**: Add godot_check.py for import, lint and GUT in order.
- **gamedev**: Add the opt-in gdscript-lsp plugin with a format hook.
- **godotsmith**: Add the play-log convention and the polygon lesson.
- **gamedev**: Add the godot-mcp plugin, a security-first Godot MCP server.
- **slicesmith**: Add deviation classes, debug file, stub check.
- **godotsmith**: Add --parse-all to parse every .gd file in a repo.

### Improved

- **godotsmith**: Pin-round controls, -gconfig=, summary parser, perf window.
- **pixelsmith**: Flatten onto grey ground and count opaque pixels.
- **gamedev**: Name the gdscript-lsp plugin in the pack README.
- **gdscript-lsp**: Install by --plugin-dir until the registry lists it.
- **uismith**: Carry the probe's pixel figure in a break row.
- **godotsmith**: Route a one-file run that ran the whole suite.
- **pixelsmith**: Keep remedies out of the contrast table.
- **slicesmith**: Refuse test-later plainly; name the skill in C3.
- **uismith**: Give a cause-proof overflow fix; split the judge.
- **slicesmith**: Take a playtest evidence row as a fix's reproduction.
- **godotsmith**: Prove OS-touching changes on every CI platform first.
- Gamedev, dispatchwright: fold in a game's test-speed lessons.
- **packs**: Name the /rw- command in every skill description.
- **uismith**: Fail the probe on page errors, empty sections, hidden overflow.
- **godotsmith**: Harden --parse-all after a fresh review.
- **uismith**: A report names a bare request, counts sections read with folds open, and states the crushed-box limit.

### Fixed

- **godot-mcp**: Harden the server after a security review.
- **uismith**: Stop the probe calling good pages empty.

## [Unreleased]

- **New pack: hearth** (`-tender` motif, standard profile), for personal and household life
  skills. First member **faretender** 1.0.0: one all-in trip total with every tax and fee added,
  money items from reviews, a price watch on a refundable booking, trip events on the calendar
  and delay claims. It never books, cancels or pays. faretender is also featured as a one-skill
  plugin. The repo now holds 30 skills in six packs.
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
  background tasks; at most five suggestion cards that propose, never build; and `/rw-<skill>` short
  commands for every skill, generated from the registry, with the long names hidden from the `/`
  list), and `shroud` (secret
  and stream-key masking with restore, the rotate tripwire, untrusted-content and
  received-message markers), kept apart so safety never depends on the dashboard. A local VS Code
  extension (`mods/vscode`) keeps the dashboard in the status bar. Mods never block: blocking
  lives in hooks and permissions. Once a mod plugin is installed, its features are on by default.
  Local records are opt-in and asked about once (`/rw-vigil records on|off`): no mod keeps a record
  of your work on disk until you say yes, the dashboard's records hold counts, names, hashes and
  shapes and never prompt or command text, and records never leave the machine. `/rw-vigil off`
  stops every feature.
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
