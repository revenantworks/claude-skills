# Sources — revenantworks-foundation-scoutwright

Last verified: 2026-10-01 (the guidance sources and the parity register below; upkeep reads this
stamp, 90-day cadence).

## Guidance sources

| Area | Claim used here | Source (read 2026-10-01) |
|---|---|---|
| Native eval suite | Case folders with `prompt.md` and `graders/*.md`; `case.yaml` with `context.add_dirs` grants read-only fixture directories; grader types `tool_used`, `regex` (with `match: not_contains`), `llm`; "Built-in tools that need a grant you didn't give, such as `Bash`, `Write`, `Edit`, `WebFetch`, and `WebSearch`, are removed from the session"; shell-granting suites need WSL2 on native Windows | `https://code.claude.com/docs/en/plugin-evals.md` |
| Docs indexes | `code.claude.com/docs/llms.txt` indexes the Claude Code docs; `platform.claude.com/llms.txt` lists about 748 English pages including the models overview, model deprecations, pricing (`about-claude/pricing.md`), release notes and system-prompt notes | both `llms.txt` files |
| Source map | Every URL in `references/source-map.md`, the cloud-safe verdicts, the walled sites and the access order | the R7 hard-sources research of 2026-10-01 (run record, not shipped), re-read for O5, O7 and O8 this day |
| Cross-check feed | Releasebot aggregates Anthropic release notes and offers RSS, email, CLI, MCP and API; its page shows no direct RSS URL, so the link is resolved on first use | `https://releasebot.io/updates/anthropic` |
| Second-opinion docs diff (source-map row S9) | Terms check 2026-10-01 (unit PRX), read live: `robots.txt` names `Claude-User` and `ClaudeBot` with "Allow: /" (only `/admin` disallowed) and "Content-Signal: search=yes, ai-input=yes, ai-train=yes"; no terms-of-service page is linked; the FAQ says every route "is a page you could open in a browser" and the JSON routes answer anybody; the plugin repo is MIT (one generated types file excluded). Adopted as a second-opinion source only: unofficial, single operator, no stated rate limit, so one weekly read, every item confirmed on the official page | `https://changelogs.core-directive.com/robots.txt`, `/faq`; `github.com/AnExiledDev/cc-changelog-plugin` LICENSE |
| Walled sites | Routes, capture protocol and terms watch for sites that block bots | researchscribe `references/hard-sources.md` (linked, not copied) |
| Currency doctrine | Adopt rows feed a skill currency sweep; model ids live in one dated file per skill with a refresh entry | the pack's currency and no-hard-coded-model decisions (2026-09-30) |

## Parity register (dated 2026-10-01; 90-day cadence)

Incumbents (pages read 2026-10-01 for the R7 research; this register compiled from it on the same day):

| Incumbent | What it does | Read |
|---|---|---|
| Releasebot (`releasebot.io/updates/anthropic`) | Aggregates Anthropic release notes across Claude, Claude Code and the API; RSS, email, CLI, MCP, API | page fetched |
| thecobb `claude-code-release-log` (GitHub) | A scheduled Action merges the changelog, the releases API and a weekly digest; dedups by version; classes Breaking, Security, Added, Fixed, Improved, Other | repo page fetched |
| Apify "Claude Code Changelog Watcher" | Parses releases and the changelog; tags hooks, skills, agents, slash commands, MCP, plugins, worktrees | page fetched |
| bendrucker `claude-code:changelog` | Filters release notes by installed plugins and skills | search summaries only; **unverified** |
| agents-radar | Daily digest over AI tool repos, HN and vendor pages; no Reddit | repo page fetched |
| AnExiledDev `cc-changelog-plugin` (GitHub) | `/whatsnew` and 15 tools over a third-party changelog site: version span since the running build, a mined per-build inventory of settings keys, env vars and hook events, and `docschanges`, a timed diff of Anthropic's docs with history (since 2026-09-20) | README read 2026-10-01 |

Absence check: no skill or plugin found that watches the whole platform (Code, apps, API, docs,
community) and maps each change to the user's own config. The search was semantic, not exhaustive:
**unverified absence**.

| Line | Status | Reason | Case |
|---|---|---|---|
| Official release-note coverage | met | Same feeds; Releasebot is read as a cross-check, not rebuilt | C14 |
| Dating and classification | met | thecobb's class set and first-seen dating for the undated changelog | C3 · native `changelog-new-versions` |
| Topic tags | met | Apify's tag list, extended with claude.ai and Cowork areas | C4 |
| Relevance to the user's own setup | **beaten** | Maps each change to settings keys, hooks, skills, tier tables and routines, and names the file and owning skill | C5, C9 · native `adopt-names-file` |
| Undocumented changes | **beaten** (narrowed 2026-10-01) | cc-changelog-plugin now diffs the docs on a timer; this sweep adds tracker search and lands each change against the rig (C9) | C8 · native `docs-page-diff` |
| Community sources with lawful access | **beaten** | A terms-checked route per source through researchscribe and a capture queue for walled ones | C12, C13 |
| Stale model tables in installed skills | **beaten** | No incumbent reads a skill's dated model file against the live models page | C10 · native `stale-model-table` |
| Hosted delivery (email, chat, site) | out of scope | The output is a dated file; delivery is the calling routine's | — |
| Running-version detection | out of scope | Covered by a session-side changelog skill; not the sweep's job | — |

**Named margins:** (1) rig relevance — every change lands as affects X, change file Y, owning
skill Z (C9); (2) undocumented-change detection joined to the rig map (C8); a docs diff alone is cc-changelog-plugin's; (3) lawful hard-source routing with a capture
queue (C12).

**Iterate:** take the Releasebot RSS feed as a second opinion each sweep and report what it carried
that the direct map missed (C14); adopt thecobb's dedup-by-version when a release and a changelog
entry describe the same change; adopt agents-radar's verbatim-quote-plus-summary row shape if
reports grow long; revisit bendrucker's installed-plugin filter once its page can be read. Adopted 2026-10-01 (unit PRX):
cc-changelog-plugin's `docschanges` pages are read as a second opinion beside the page-set diff
(source-map S9, `diffing.md` §3) after a live terms check (Guidance sources above).

**Retire condition:** retire scoutwright, or shrink it to the relevance layer, if Anthropic ships an
official per-setup "what changed for you" feed, or an incumbent adds config-relevance mapping plus
docs diffing.

**Verdict: PARITY + MARGIN.**

## Licence note

Nothing is copied from an incumbent. The class set (thecobb) and the tag list (Apify) are adopted as
ideas, named here; no code or text is reused.
