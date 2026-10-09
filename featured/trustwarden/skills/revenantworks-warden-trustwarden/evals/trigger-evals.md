# Trigger evals — revenantworks-warden-trustwarden

Counts: 26 queries (13 should, 13 should-not, 5 pairs)

Provenance: authored against SKILL.md v0.1.0 (2026-10-01), by the unit that wrote the
description. Judged from **name + description only**, as a cold router would. Not a cold judge —
the reader wrote the clauses — so a cold re-judge is owed. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Balance: 13 should-fire · 13 should-not (10 near-misses, 3 off-topic) — 26 in all.

FX3 (2026-10-01): J1 E10 added "check the licence before we fold this repo into ours" to the description (fixes misroute M10, row 10, which J1 sent to skillwright's integrate). Re-judged by hand against the new description: row 10 fires here; the skillwright boundary rows still go to skillwright (building or auditing your own skills). J1 cold re-judge: 24 rows, 1 misroute (M10), now fixed.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "is this skill from github safe to install?" | Named trigger |
| 2 | "vet this MCP server before I add it to my config" | Named trigger |
| 3 | "check this GitHub Action before I use it in CI" | Named trigger |
| 4 | "should I trust this plugin from a marketplace I just found?" | Named trigger |
| 5 | "what does this tool's installer write to my machine?" | Named trigger |
| 6 | "a plugin update came in, what changed since I pinned it?" | revet |
| 7 | "what terms should I install this under?" | terms |
| 8 | "someone shared a skills repo in a thread, worth adding?" | Pre-install question, pushy |
| 9 | "the scanner said clean, so I can install it, right?" | Coverage margin |
| 10 | "can we fold this repo's planning system into our skills?" | Licence before fold-in |
| 11 | "trustwarden vet the claude-mem plugin" | Named keyword |
| 12 | "is this MCP server for a forum OK to use? it goes through a paid proxy API" | Data-route terms |
| 25 | "this 'superpowers' skill pack claims 600k installs but the account is new, and its lockfile pulls from git URLs; safe to add?" | Copied name, inflated installs, lockfile (K4 C4) |

## Should not fire

| # | Request | Routes to | Kind |
|---|---|---|---|
| 13 | "audit my permission allow list, I think it's too wide" | gatewarden | near-miss (runtime permissions) |
| 14 | "add a deny rule so Claude can't run rm -rf" | gatewarden | near-miss (writes the rule) |
| 15 | "what can my installed MCP server actually do right now?" | gatewarden | near-miss (installed tool at runtime) |
| 16 | "scan my repo for leaked API keys" | shieldwarden | near-miss (secrets) |
| 17 | "review the skill I just wrote for best practices" | skillwright | near-miss (own skill) |
| 18 | "security-audit our own skill pack before release" | skillwright | near-miss (own skills) |
| 19 | "open this downloaded zip in a sandbox" | hypervrunner | near-miss (runs the sandbox) |
| 20 | "rotate my GitHub token" | keywarden | near-miss (credentials) |
| 21 | "install the commit-commands plugin" | plain install | near-miss (trustwarden may be suggested, not fired) |
| 22 | "set up a weekly routine that scouts new Claude tools" | agentwright | off-topic (schedule) |
| 23 | "why is my docker disk so big" | dockerrunner | off-topic |
| 24 | "write a prompt for summarising PDFs" | promptwright | off-topic |
| 26 | "is the name of the skill I'm about to publish too close to a popular one?" | skillwright | near-miss (own skill's name collision, K4 C4) |

## Boundary notes

- **Sharpest pair: 2 vs 15.** Both name an MCP server. Before install ("before I add it") is
  trustwarden; what an installed server may do is gatewarden. The description's first sentence says
  "before it is installed" for this reason.
- **21 is the watched miss.** A plain install request should not fire a vet uninvited; trustwarden may
  be suggested in one line. If it fires, tighten "before it is installed" rather than widening.
- **16 vs 1.** A secret inside a candidate is found during a vet and handed to shieldwarden; a repo
  scan for keys is shieldwarden from the start.
- **17/18 vs 1.** Our own skills are skillwright's audit; someone else's, before install, are here.
- **25 vs 26** (added 2026-10-08, K4 C4, authored, not run cold). A look-alike someone else
  published, before install, is trustwarden's; whether our own skill's name collides is
  skillwright's parity check.
- **Tuning rule:** misses on 1–12 → make the trigger list pushier; fires on 13–21 → tighten the
  routing sentence for that sibling.
