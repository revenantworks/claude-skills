# Trigger evals — revenantworks-warden-shieldwarden

Provenance: authored against SKILL.md at the v1.0.0 build (2026-09-28), by the build unit; re-anchored to v1.0.0, 2026-10-01 (2026-10-01: rows renamed from shieldrunner, no row changed meaning); P1 (2026-10-01): description routes permission and hook safety to gatewarden and rotation to keywarden, rows 7, 18, 23 and B1 re-judged. FX3 (2026-10-01): J1 E8 — the description now says "scan a repo, a branch or its history" (commit identities dropped: identitywarden owns identity policy); row 4 flipped to the identity member then. **Consolidation (2026-10-08, owner):** the identity and naming policy (from identitywarden) and the signposts scan (from filewarden) merged in; row 4 flips back to fire; rows 29-53 are carried from those members' suites with their origin marked, re-judged by hand against the merged description, not yet cold-judged.
Judged from **name + description only**, as a cold router would. The author wrote the
description, so this is not a cold judge; a cold re-judge of every row is owed.

Counts: 56 numbered rows (33 should, 23 should-not) and 10 boundary pairs of two, 76 in all

Balance: 33 should-fire · 23 should-not · 10 boundary pairs. Rows 2, 11 and 12 of the identity suite (a history email scan, a key scan, a `.env` rewrite) were already rows 3, 6 and 10 here, so they were not carried twice.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "did my home folder path end up in the public repo?" | User-folder path before publishing, the core claim |
| 2 | "check this branch for personal data before I push it" | Branch + personal data + before publishing |
| 3 | "is my email anywhere in this repo's history?" | Email address in history |
| 4 | "are my commit identities clean on this repo?" | Commit identities against the naming policy (`identity --range`); flipped back 2026-10-08 |
| 5 | "scan the skills for prompt-injection risks" | Audit skills for prompt injection |
| 6 | "any secrets committed in here?" | A secret, before anything is published |
| 55 | "we're making this repo public next week; is it ready, and does any code log the API key?" | `ready` go-public gate plus the `exposure` rules (K4 C5, added 2026-10-08, authored, not run cold) |
| 7 | "check the routine prompts and hooks for injected instructions" | Routine prompts and hooks, scanned for injected instructions |
| 8 | "audit the artifacts Claude published for personal info" | Artifacts Claude created |
| 9 | "check the design systems and docs you made for my name" | Design systems, docs, the user's name |
| 10 | "I leaked a path in three commits, plan the history rewrite" | After a leak, plan the rewrite |
| 11 | "dry-run the filter-repo rewrite and verify it" | Dry run and verify a rewrite |
| 12 | "shieldwarden" | Named |
| 13 | "shieldwarden after" | Named subcommand |
| 14 | "shieldwarden refresh" | Named subcommand |
| 15 | "which connectors and schedules could leak something?" | Connectors, schedules |
| 16 | "privacy check this repo before it goes public" | Personal data before publishing |
| 29 | "Which email address will my next commit in this repo use, and where is that coming from?" | `identity` (carried from identitywarden row 1) |
| 30 | "Set up a codename for the client so their real name never shows up in commits or docs." | `policy` (identitywarden row 3) |
| 31 | "I commit for two GitHub accounts on one laptop — make sure each repo uses the right identity." | `identity --root`; not keywarden, no sign-in or token (identitywarden row 4) |
| 32 | "Is the Co-authored-by line Claude adds to my commits leaking an address I don't want?" | trailer check (identitywarden row 5) |
| 33 | "Before I post this PR description, make sure it doesn't name my employer." | `check --text` (identitywarden row 6) |
| 34 | "My includeIf for the work folder doesn't seem to apply in a worktree — which config is winning?" | `identity` source (identitywarden row 7) |
| 35 | "Audit this repo for real names in branch names and commit messages, but don't change anything." | `identity` no-change score, `check --branches` (identitywarden row 8) |
| 36 | "shieldwarden policy" | Named subcommand (was "identitywarden policy", row 9) |
| 37 | "Write me a rule list of which names can appear on our public pages versus the personal repos." | `policy` by surface (identitywarden row 10) |
| 38 | "Check this PR description draft for the client's real name before I post it." | `check` on draft text (identitywarden row 21) |
| 39 | "Find any files or folders on my D: drive named secret, private or passwords, and tell me who can open them." | `signposts` (carried from filewarden row 11) |
| 40 | "What on my disk advertises sensitive data just by its name?" | `signposts` (filewarden row 12) |
| 41 | "Is anything in my Downloads called 'bank' or 'tax' that other users on this PC can read?" | `signposts` (filewarden row 13) |
| 42 | "Check the files in this folder for passwords written inside them." | `scan --dir`, a content scan (filewarden should-not row 15, now this skill's own job) |
| 43 | "shieldwarden signposts" | Named subcommand (new 2026-10-08) |
| 44 | "shieldwarden identity" | Named subcommand (new 2026-10-08) |

## Should not fire

| # | Request | Where it goes instead |
|---|---|---|
| 17 | "search my inbox for the invoice from last month" | Mail, outside the boundary; no skill here |
| 18 | "harden the hooks on this machine" | gatewarden (hook safety, named in the description) |
| 19 | "review this skill's security posture against the rubric" | skillwright (named in the description: "a skill's own posture"; restored 2026-10-08, K7-4-14) |
| 20 | "schedule a weekly scan on Sundays" | agentwright owns the schedule (named) |
| 21 | "offload this summary to the local model" | lmstudiorunner |
| 22 | "write a privacy policy for my app" | Drafting, not scanning |
| 23 | "rotate my GitHub token" | keywarden (rotation, named in the description) |
| 24 | "find the bug in this regex" | Ordinary code work |
| 25 | "clean up the Drive folder of my old photos" | The user's own Drive content, outside the boundary |
| 26 | "rebase this branch onto main" | Ordinary git work, no leak named |
| 27 | "explain what PII means under GDPR" | A question, not a scan |
| 28 | "force-push the fixed branch for me" | The skill never pushes; the user runs it |
| 45 | "Switch the gh CLI to my other account and refresh its token." | keywarden (sign-in and tokens; identitywarden row 14) |
| 46 | "Write the brand voice guide and the list of product names we use in marketing." | brandscribe (identitywarden row 13) |
| 47 | "Audit my settings.json permission rules and hooks." | gatewarden (identitywarden row 15) |
| 48 | "Write a commit message for these staged changes." | General coding (identitywarden row 16) |
| 49 | "Rename the repo and update the remote URL." | General git (identitywarden row 17) |
| 50 | "Draft a Slack post announcing the release." | commscribe (identitywarden row 18) |
| 51 | "Set up a CLAUDE.md for this repo with our naming conventions for variables." | rigwright; "naming" means code identifiers (identitywarden row 19) |
| 52 | "Which drives and folders can Claude write to on this machine?" | gatewarden `footprint` (identitywarden row 20) |
| 53 | "Is my gh token stored somewhere other people on this machine could read it?" | keywarden (credential storage; filewarden row 16) |
| 56 | "Is this third-party plugin safe to install, and does its lockfile pull from git URLs?" | trustwarden (vetting someone else's code before install; K4 C5 near-miss) |
| 54 | "What is eating all the space on my second drive?" | gatewarden `map` — a size question, not a name that advertises a secret (new 2026-10-08) |

## Boundary pairs

| Pair | Request A (fires) | Request B (does not) | The deciding signal |
|---|---|---|---|
| B1 | "is the hook config leaking my user folder?" | "make the hook config stricter" | A leak found versus a hardening change (gatewarden) |
| B2 | "does this SKILL.md tell an agent to follow fetched text?" | "does this SKILL.md pass the rubric?" | An injection finding versus the full skill audit (skillwright) |
| B3 | "scan the repo now" | "set up the scan to run every Sunday" | The scan versus its schedule (agentwright) |
| B4 | "check the doc you made for the client's name" | "check my Drive for the client's name" | Claude-made versus the user's own content |
| B5 | "plan the rewrite to strip my email from history" | "push the rewritten history" | Plan and verify versus the push the user runs |
| B6 | "is there a secret in the local model's output file?" | "run this job on the local model" | A scan of output versus the delegation (lmstudiorunner) |
| B7 | "which email will my next commit use?" | "switch gh to my other account" | Which identity a commit is authored as versus which account authenticates (keywarden) |
| B8 | "check this PR draft for the client's real name" | "write the brand voice guide" | An identity on a surface versus brand vocabulary (brandscribe) |
| B9 | "which files here are named passwords or bank, and who can open them?" | "what is eating my disk?" | A name that advertises a secret versus a size map (gatewarden) |
| B10 | "is anything named private readable by other users?" | "is my gh token stored where others can read it?" | A signpost name versus a known credential's storage (keywarden) |
