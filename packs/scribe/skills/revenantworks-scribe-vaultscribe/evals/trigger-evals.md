# Trigger Evals — revenantworks-scribe-vaultscribe

- Provenance: revenantworks-scribe-vaultscribe · v1.0.0 · derived 2026-11-09. Authored, not run; rows 1, 4, 7, 9, 15, 16, 17 and 18 also run as native cases (`evals/<case>/`).
- Counts: 24 queries (14 should, 10 should-not, 5 pairs), judged cold against name + description only.

## Should fire (14)

| # | Query | Should trigger? | Why |
|---|---|---|---|
| 1 | "I want a second brain in Obsidian that Claude keeps up to date from articles I save. Set it up." | ✅ yes | setup; native `trigger-start-vault` |
| 2 | "Start an LLM wiki in this folder like Karpathy described: raw sources, a compiled wiki, a rules file." | ✅ yes | setup, named pattern |
| 3 | "Ingest raw/clips/heat-pumps.md into my knowledge base." | ✅ yes | ingest one source |
| 4 | "Ingest everything new in raw/ that hasn't been filed yet." | ✅ yes | ingest new; native `trigger-ingest-new` |
| 5 | "What does my vault say about heat pump sizing? Link the pages." | ✅ yes | query |
| 6 | "Save that answer as a page in the wiki." | ✅ yes | query, filing an answer |
| 7 | "Lint my Obsidian vault: broken links, orphans, pages with no sources." | ✅ yes | lint; native `trigger-lint-vault` |
| 8 | "Check my notes vault for email addresses, home folder paths or API keys before I push it." | ✅ yes | lint, privacy and secrets |
| 9 | "Our repo READMEs changed since I filed them in the wiki. Which pages are stale? Update just those." | ✅ yes | refresh; native `trigger-refresh-sources` |
| 10 | "Snapshot the team handbook docs into the vault again and tell me what drifted." | ✅ yes | refresh, snapshot |
| 11 | "I clip web pages into my second brain. Lock it down so a clipped page can't make Claude run commands or fetch URLs." | ✅ yes | harden |
| 12 | "vaultscribe harden" | ✅ yes | named entry |
| 13 | "My personal knowledge base keeps catching personal stuff from sources. When should I move it to a private folder?" | ✅ yes | lint, escalation path |
| 14 | "Set up the vault so I can sync it with git from two Windows PCs without merge conflicts in the index and log." | ✅ yes | setup, git-safe |

## Should not fire (10)

| # | Query | Should trigger? | Why |
|---|---|---|---|
| 15 | "Start a story bible for my fantasy novel's three kingdoms, one file per character." | ❌ no | lorescribe; pair with 2; native `nearmiss-story-bible` |
| 16 | "Research the best heat pump brands with sources and give me a graded report." | ❌ no | researchscribe; pair with 5; native `nearmiss-research-report` |
| 17 | "Make an Obsidian Canvas board and a Bases view of my reading list." | ❌ no | obsidian-skills (formats); pair with 1; native `nearmiss-obsidian-canvas` |
| 18 | "My API key was committed to the vault last month. Rewrite the git history to remove it." | ❌ no | shieldwarden (history rewrite); pair with 8; native `nearmiss-history-rewrite` |
| 19 | "Audit every permission rule in my user and project settings for dead rules." | ❌ no | gatewarden; pair with 11 |
| 20 | "Rewrite this wiki page as a friendly email to my team." | ❌ no | commscribe |
| 21 | "Summarise these forty PDFs with my local model in LM Studio overnight." | ❌ no | lmstudiorunner |
| 22 | "Write a Python script that counts words in every Markdown file." | ❌ no | no skill (general coding) |
| 23 | "Which Obsidian theme is easiest on the eyes?" | ❌ no | no skill (app preference) |
| 24 | "Turn my meeting recording into a transcript." | ❌ no | whisperrunner |

**Edge notes.** The sharpest pair is 8 against 18: both are about a secret in the vault, but 8 asks for a check of the current files and 18 for a history rewrite. Next is 1 against 17: Obsidian named in both, but 17 asks for Obsidian's own file formats. Misses on the yes-set mean the triggers need pushier wording; fires on the no-set mean the boundary sentence needs tightening.
