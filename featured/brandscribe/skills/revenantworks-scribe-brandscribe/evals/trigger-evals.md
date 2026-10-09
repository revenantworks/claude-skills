# Trigger evals — brandscribe

Provenance: written for 0.1.0 (2026-10-01). Status: authored, not run. Read each query cold against the name and description only, and compare with the Expected column. The native suite (`evals/<case>/`) runs fourteen of these rows under `claude plugin eval`, beside behaviour cases. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Cold run 2026-10-01 (run J1): blind list from `tools/blind_queries.py`, judged on the worker tier against all 30 pack descriptions: Y1-Y12 and N1-N12, 24/24 agreed. Tiers checked: worker only; the fast and top tiers are unchecked, and the native `claude plugin eval` run is A6's. Y13-Y14 came from J1 misroutes M4 and M5 (rigwright and skillwright suites) and arrived with the description clause "to apply a brand to a README, a page or generated output"; re-read by hand against the new description, not blind.

2026-10-08 (warden 6 → 4): N10's expected answer drops the retired identitywarden; shieldwarden owns it now.

Counts: 36 queries (19 should, 17 should-not, 8 pairs)

## Should fire (19)

| # | Query | Expected | Native case |
|---|---|---|---|
| Y1 | "Turn our style guide into a Claude design system — tokens for light and dark, the type scale, a brand book page." | brandscribe (export design-system) | `trigger-guide-to-ds` |
| Y2 | "We changed the accent in our brand definition; re-sync the design system but keep the notes people added on the page." | brandscribe (sync) | `trigger-resync` |
| Y3 | "Audit this repo's docs and site for the old product name and colours that aren't in our palette. Report only." | brandscribe (audit) | `trigger-old-name-audit` |
| Y4 | "Give me a DESIGN.md for this project from our brand definition." | brandscribe (export design-md) | `trigger-design-md` |
| Y5 | "Does this landing page pass our brand? Pass or fail and the blockers." | brandscribe (gate) | `trigger-gate-page` |
| Y6 | "Define a brand for my new studio: name rules, palette, type, voice. Ask me only what you need." | brandscribe (build) | — |
| Y7 | "Pull the colours and fonts from our website and make them into brand tokens." | brandscribe (build, ingest a URL) | — |
| Y8 | "We run two brands from one repo. Set up both so each request picks the right one." | brandscribe (setup, multi-brand) | — |
| Y9 | "Update our brand voice: we want it warmer, and add before/after examples." | brandscribe (build, voice) | — |
| Y10 | "Export our lexicon as Vale rules so CI flags the words we never use." | brandscribe (export vale) | — |
| Y11 | "Connect the design system someone made on the page to our brand definition and tell me what differs." | brandscribe (sync, connect) | `connect-four-lists` (behaviour) |
| Y12 | "brandscribe audit the docs folder" | brandscribe (audit, named) | — |
| Y13 | "Apply our brand palette to the project README." | brandscribe (apply: gate, then the changed file at the gate) | `no-definition-apply` (behaviour, no brand stored) |
| Y14 | "Apply my company's branding to the skills we generate." | brandscribe (apply to generated output) | — |
| Y15 | "Critique this dashboard before we ship it: hierarchy, spacing, empty and error states." | brandscribe (ui) | `trigger-ui-critique` |
| Y16 | "Check dist/index.html for UI problems." | brandscribe (ui, checker first) | `ui-check-dist` (behaviour) |
| Y17 | "Does this landing page look generic?" | brandscribe (ui, specificity area) | `trigger-ui-generic` |
| Y18 | "Score the settings page's hierarchy and spacing." | brandscribe (ui) | — |
| Y19 | "brandscribe ui on the built site" | brandscribe (ui, named) | `ui-taste-p3` (behaviour) |

## Should not fire (17)

| # | Query | Expected owner | Native case |
|---|---|---|---|
| N1 | "Write a Slack message announcing the beta opens Monday." | commscribe or any writer | `nearmiss-slack-launch` |
| N2 | "Sync my React component library into Claude Design." | the design-sync command | `nearmiss-react-design-sync` |
| N3 | "Draw me a logo for a coffee cart as an SVG." | no skill (drawing) | `nearmiss-draw-logo` |
| N4 | "Start a story bible for my game's five noble houses, their sigils and colours." | lorescribe | `nearmiss-story-bible` |
| N5 | "Make this email sound like us — here's our VOICE.md." | commscribe (one message, voice handed in) | — |
| N6 | "Plan a three-month marketing campaign for the launch." | no skill (campaigns out of scope) | — |
| N7 | "Pixel palette for the ice faction, eight colours that read at small sizes." | pixelsmith | — |
| N8 | "Rename our whole skill pack and update every skill's files." | skillwright (port) | — |
| N9 | "Generate a mood board image of a misty harbour on my GPU." | comfyrunner | — |
| N10 | "Is this repo leaking my real name or an API key?" | shieldwarden | — |
| N11 | "Build a slide deck about our quarterly results." | the Slides artifact type (uses the default design system itself) | — |
| N12 | "Write CLAUDE.md rules so Claude follows our coding style." | rigwright | — |
| N13 | "Build me a landing page for a neighbourhood bakery." | none (the model builds; artifact-design for an artifact) | `nearmiss-build-landing` |
| N14 | "Make a bar chart of weekly signups." | the built-in dataviz guidance | `nearmiss-bar-chart` |
| N15 | "Fix the re-render bug in this React component." | /code-review or a debugging pass | — |
| N16 | "Rewrite the empty-state and error copy on this signup form." | commscribe (ui profile) | — |
| N17 | "The hut sprite vanishes against the grass when zoomed out; fix its palette." | pixelsmith | — |

## Edge notes

- Sharpest pair: **Y9 vs N5** on the word "voice". Changing the stored brand voice is brandscribe; writing one message in a voice is commscribe even when the voice file is handed in.
- Second pair: **Y1 vs N2**. A design system from a guide or definition is brandscribe; one from React code is design-sync.
- **N4**: house colours in fiction are canon, not a brand palette.
- Third pair: **Y13/Y14 vs N8 and N12**. Putting a brand's names, colours and strings onto a README or generated output is brandscribe; renaming a skill pack's files is skillwright's port; standing CLAUDE.md rules are rigwright. Re-read 2026-10-01 against the 959-char description (E3): Y1-Y14 fire; N1-N12 route out on their boundary clauses; no earlier row changed verdict.
- **N11**: decks pick up the default design system with no skill involved; brandscribe only builds the system.
- Fourth pair: **Y15-Y19 vs N13, N14, N16, N17**. Reviewing a built page is brandscribe `ui`; building one is the model's, a chart is dataviz's, the words on it are commscribe's, sprite readability is pixelsmith's. Re-read by hand 2026-10-01 against the 995-char description (UIX): Y1-Y19 fire; N1-N17 route out. N6 (campaigns) lost its explicit clause in the rewrite and still routes out: nothing in the description names campaigns or strategy. Y3 lost "off-voice copy" and still fires on "old names" and off-palette colours.
- Pairs are counted one row per pair, from the notes above: Y9-N5, Y1-N2, Y13-N8, Y14-N12, Y15-N13, Y16-N14, Y17-N16, Y18-N17 (8). The N4 and N11 notes name one side only and count none.
- Tuning rule: misses on the yes-set → make the description's trigger list pushier; fires on the no-set → tighten the boundary sentence.
