# Plugin directory pack

What this repository sends to Anthropic's plugin directory, in what order, and why. Each plugin
folder is its own submission: the directory reads one folder that holds `.claude-plugin/plugin.json`,
shows that folder's README as the listing, and scans every new commit on the tracked branch.

Rules checked on 2026-11-23 against:

- [Publish to the directory](https://claude.com/docs/directory/publish) (who can submit, review)
- [Submit your plugin](https://claude.com/docs/plugins/submit) (portal steps, one submission per
  plugin folder, data handling and compliance steps, updates)
- [Plugin pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
  (what validation blocks, holds or warns on, and the security scan)
- [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy)
  (no access to Claude's memory or chat history, data minimization, three working example
  prompts, contact and support channels, prohibited uses such as generative media and
  autonomous money movement)
- [Anthropic Software Directory Terms](https://support.claude.com/en/articles/13145338-anthropic-software-directory-terms)
  (updated 2026-03-16: a vulnerability-report channel, investigated "with a reasonable standard
  of care"; no implied partnership or endorsement)

Re-read these pages before each submission; they change.

## Submission order

| # | Plugin folder | Verdict | Why |
|---|---|---|---|
| 1 | `featured/brandscribe` | **Submit first** | Distinctive name, 220 files (limit 512), no hooks, servers or network code, text files only (scripts are plain text), discloses everything it reads and writes. Strongest fit with the policy. |
| 2 | `featured/pacewright` | **Submit after one decision** | Strong niche and no code at all, but `spend` mode reads local session transcripts. The policy says software must not access Claude's chat history. The README discloses it; expect a reviewer hold or a refusal. Safer: gate or drop `spend` in the next foundation pack bump, then submit. |
| 3 | `featured/trustwarden` | Hold for the maintainer's call | Users may rely on it for install safety (liability), and it runs scanners. Ready on the file rules. |
| 4 | `featured/pixelsmith` | Hold | Writes briefs for image generators; the policy generally bars generative image tools. Needs a clear "it directs, it does not generate" line first. |
| 5 | `featured/whisperrunner` | Hold for the maintainer's call | Drives a local program (whisper.cpp) the user installs; local-tool liability. |
| 6 | `featured/faretender` | Not now | Money and claim letters sit in the policy's high-risk areas (finance, legal), which need extra review. |
| - | packs (`scribe`, `foundation`, others) | Not now | `scribe` (1,056 files) and `foundation` (650) exceed the 512-file limit, which holds them for a reviewer; generic names such as `scribe` and `foundation` risk "Name may be confused with an existing listing"; and a pack beside its featured plugin lists one skill twice. |

## Listings

The portal reads the name and short description from `plugin.json` and the description from the
README, so the listing text below is what those files already say. Change it there, never in the
portal.

### 1. brandscribe

- **Name:** `brandscribe` · display name **Revenantworks Brandscribe** · author Revenantworks
- **Version:** 1.0.1 · licence Apache-2.0 (`plugin.json` `license`; `LICENSE` in the skill folder)
- **One line:** One brand definition, everywhere Claude builds.
- **Description:** [`featured/brandscribe/README.md`](../../featured/brandscribe/README.md): keeps
  brand definitions in plain files and turns one into a Claude Design System, `DESIGN.md`,
  `VOICE.md` or a guide, with a re-sync that keeps page edits and a 31-rule UI check.
- **Example prompts (policy: at least three):** "Turn this style guide into a Claude Design
  System." · "The brand colours changed, re-sync the design system." · "Check this built page
  before it ships."
- **Screenshots and icon:** TODO for the maintainer. A square PNG icon at
  `featured/brandscribe/.claude-plugin/icon.png`; the size, path and when the portal takes it are
  not stated on the policy, submit or checklist pages read for this pack, so check the portal.
  Screenshots: a design system built from a short brand file; the
  re-sync's four lists; a `ui_check.py` report.
- **Data handling answers:** reads or stores personal data: no. Sends data to other services: only to
  the user's own claude.ai account (a Design System, on request) and to web pages the user names,
  which it fetches. Keeps data: only the files the user asks it to write, in the user's own folders. Intended for
  people under 18: no.

### 2. pacewright

- **Name:** `pacewright` · display name **Revenantworks Pacewright** · author Revenantworks
- **Version:** 1.0.1 · licence Apache-2.0
- **One line:** Spend a Claude subscription on purpose.
- **Description:** [`featured/pacewright/README.md`](../../featured/pacewright/README.md): turns
  the 5-hour, weekly and per-model meters into a spend mode and a fit check for planned work.
- **Example prompts:** "I'm at 70% weekly, what can still run before the reset?" · "Something
  ate my usage overnight." · "pacewright fit" with a list of planned work.
- **Screenshots and icon:** TODO for the maintainer. Icon as above, at
  `featured/pacewright/.claude-plugin/icon.png`. Screenshots: a `check` reading with its mode; a
  `fit` table; a `spend` table with counts only.
- **Data handling answers:** reads personal data: yes, only in `spend` mode, on request, from
  local session transcripts, keeping counts and 60-character prompt heads; those excerpts enter
  Claude's conversation, so they reach Anthropic's model service like any chat text. Sends data to
  other services: the skill sends nothing of its own, but it calls the GitHub billing API and
  `gh api rate_limit` with the user's own GitHub login, and the opt-in `share` bundle is built
  only on request and passed on only by the user. Keeps data: three small local files the user
  owns. Intended for people under 18: no.

## Policy self-check

Result for each row: pass, hold (a reviewer reads it), or warn. Checked with the file scan behind
this pack and `claude plugin validate` (both plugins: "Validation passed", one warning: no icon). Rows marked hold or needs decision stay open for pacewright until the maintainer decides.

| Rule (source) | brandscribe | pacewright |
|---|---|---|
| One folder with `.claude-plugin/plugin.json` (checklist) | pass | pass |
| Name: lowercase, distinctive, not reserved, not a brand (checklist) | pass | pass |
| `description`, `author`, `version` set (checklist) | pass | pass |
| README of 40 words or more in the folder (checklist) | pass (over 500) | pass (over 500) |
| Licence in `plugin.json` or a `LICENSE` file (checklist) | pass | pass |
| 512 files or fewer; every non-image file under 256 KiB (checklist) | pass (220 files) | pass (36 files) |
| Text files only; no `.zip`, `.pdf`, `.ico` or executables (checklist) | pass | pass |
| No symlinks, submodules, LFS, `.DS_Store` or `Thumbs.db` (checklist) | pass | pass |
| No hooks, MCP servers, package launchers or lockfiles (checklist) | pass: none | pass: none |
| No credentials in any file (checklist) | pass (PII and secret scan clean) | pass |
| Behavior disclosed in the README for the security scan (checklist) | pass | pass |
| No access to Claude's memory or chat history (policy 1) | pass | **hold**: `spend` reads local transcripts |
| Collect only what is needed (policy 1) | pass | pass: counts and prompt heads only |
| No hidden or encoded instructions; no runtime instructions from outside (policy 2) | pass | pass |
| Descriptions match what the plugin does (policy 2) | pass | **hold**: the README now lists the transcript reads, the GitHub reads with the user's login and the opt-in share bundle; confirm the portal description says the same |
| Three working example prompts (policy 3) | pass | pass |
| Contact, support and troubleshooting documented (policy 3) | pass: `SUPPORT.md` | pass: `SUPPORT.md` |
| Privacy policy if it collects data or calls a remote service (policy 3; terms) | needs decision: it fetches web pages and writes to the user's claude.ai account on request | **needs decision**: it calls GitHub with the user's login and `spend` excerpts enter the conversation; expect a privacy policy to be asked for |
| Vulnerability-report channel (terms) | pass: `SECURITY.md`, private advisory form | pass |
| Not in a prohibited use: money, generative media, ads, adult (policy 4) | pass | pass |
| No implied partnership or endorsement (terms) | pass ("Made for Claude's Design System type") | pass |
| Listing icon (portal) | **warn**: none yet; check the portal for size and format | **warn**: none yet; check the portal for size and format |

## Release standard

- **Licence:** Apache-2.0, unchanged; the root `LICENSE` is the verbatim text and every skill
  folder carries its own `LICENSE` and `NOTICE`.
- **As-is wording:** the no-warranty block sits in the root README's Licence section and in each
  submitted plugin's README.
- **Support period:** `SUPPORT.md` at the root and in each submitted plugin folder: major version
  1 gets security fixes until 2027-11-23.
- **SECURITY.md:** at the root and in each submitted plugin folder, with a versions table that
  matches `SUPPORT.md` and the private advisory form named as the directory's report channel.
- **Never-promise list:** the listing text makes no "finds all", "secure", "compliant",
  "lifetime updates" or warranty claim.
- **Versions:** the first submission needs no version bump. After listing, every change that
  should reach directory users ships with a raised version, through
  `python tools/release.py <pack>=X.Y.Z -m "..."` (the featured plugin follows its member's
  version). The directory picks up the new commit from the tracked branch.

## Submitting to the directory

Only the maintainer does these steps. Each one is an account or publish action.

1. Add a square PNG icon at `featured/brandscribe/.claude-plugin/icon.png`, and merge it to `main`. Check the portal for the accepted size and format; no page read for this pack states them.
2. Sign in to claude.ai on a paid plan and connect GitHub there, with an account that can push to `revenantworks/claude-skills`.
3. Open the developer portal at <https://claude.ai/directory/manage> and select **Submit new**, then **Plugin bundle**.
4. Enter repository `revenantworks/claude-skills`, plugin path `featured/brandscribe`, and leave the branch empty so it follows `main`.
5. Select **Validate** and confirm the report shows no **Blocking** finding.
6. On **Data handling**, give the brandscribe answers from the Listings section above.
7. On **Compliance**, set a contact address that is not a personal one and select the four acknowledgements.
8. Keep **GitHub push webhook**, leave auto-publish off, and select **Submit for review**.
9. When the version passes, select **Publish** on the plugin's page.
10. Decide pacewright: make `spend` opt-in or remove it in a foundation release before submitting; submitting as it is invites a reviewer hold or refusal.
11. For pacewright, add its icon at `featured/pacewright/.claude-plugin/icon.png`, then repeat steps 3 to 9 with plugin path `featured/pacewright` and its own data handling answers.
