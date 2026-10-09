# Trigger evals — lorescribe

Provenance: written for 0.1.0 (2026-10-01); re-anchored for 0.2.0 (2026-10-01, `brief` mode and the return check: Y11-Y13, N11-N13); re-anchored again at 0.2.0 for the `manuscript` mode and branch canon (2026-10-01, version unchanged by owner decision 46: Y14-Y16, N14, N9 re-pointed to commscribe; description re-fit to 1,015 chars). Status: authored, not run; the builder's re-read against the new description is recorded under Edge notes (not blind). Read each query cold against the name and description only, and compare with the Expected column. The native suite (`evals/<case>/`) runs twenty of these rows under `claude plugin eval`. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Cold run 2026-10-01 (run J1, the LMB re-judge): blind list from `tools/blind_queries.py`, judged on the worker tier against all 30 pack descriptions at 1,015 chars: 30/30 agreed, manuscript rows included. Tiers checked: worker only; the fast and top tiers are unchecked, and the native `claude plugin eval` run is A6's. The description was then cut to 952 chars (A2 L-1: "— novel, game, tabletop, franchise —" and "keep a pronunciation key," removed); re-read by hand under Edge notes.

Re-anchored 2026-10-01 (FXL1) after the native `timeline-chart` run never called Skill: the description gained the drawn-timeline clause and the dataviz boundary (999 chars); Y17-Y18 and N15-N16 added; re-read by hand under Edge notes (not blind).

Counts: 36 queries (19 should, 17 should-not, 9 pairs)

## Should fire (19)

| # | Query | Expected | Native case |
|---|---|---|---|
| Y1 | "Check chapter 3 against my story bible — I think a drowned character turns up again." | lorescribe (check) | `trigger-check-chapter` |
| Y2 | "Build a lore bible for my game's four factions, one file each, with leaders and who is at war with whom." | lorescribe (bible) | `trigger-faction-bible` |
| Y3 | "Is it a contradiction that the captain gives an order after she died in session 4?" | lorescribe (check) | `trigger-captain-death` |
| Y4 | "Give me naming rules for the desert culture and five names with pronunciation." | lorescribe (names) | `trigger-desert-names` |
| Y5 | "Put these events on the world timeline and track who is alive after each." | lorescribe (timeline) | `trigger-world-timeline` |
| Y6 | "Check my novel's road network against the story bible — chapter 9 has a road the map says doesn't exist." | lorescribe (check) | — |
| Y7 | "Here's the in-game dialogue string table; flag anything that breaks canon before localisation." | lorescribe (check) | — |
| Y8 | "My three games share one universe in separate repos — how do I keep canon in sync and know what changed since each shipped?" | lorescribe (franchise canon) | `pin-drift` (behaviour) |
| Y9 | "Score my world bible: missing index rows, one-way links, entities with no canon level. Don't change anything." | lorescribe (audit) | — |
| Y10 | "I have a story-skills bible already; can lorescribe read it and add art tags and motifs to the factions?" | lorescribe (bible, interop) | — |
| Y11 | "Write a brief from my story bible so my local model can draft the vigil scene without breaking canon." | lorescribe (brief, story draft) | `brief-story-slice` (behaviour) |
| Y12 | "My local model wrote this scene from the brief; check it against canon before I keep any of it." | lorescribe (check, return path) | `draft-contra-flagged` (behaviour) |
| Y13 | "Draw my world timeline as a chart I can open offline." | lorescribe (brief, timeline visual) | `timeline-chart` (behaviour); `absent-runner-text` covers the entity-visual brief |
| Y14 | "Here are the twelve chapters of my finished novel. Build the story bible from them and tell me where the book contradicts itself." | lorescribe (manuscript) | `trigger-manuscript-extract`; behaviour `ms-self-contra`, `ms-no-write-before-yes`, `ms-variant-no-merge`, `ms-injected-chapter` |
| Y15 | "In my game the keep has a different ruler depending on which side the player took; check this scene for the guild path." | lorescribe (check, branches) | `branch-leak` (behaviour) |
| Y16 | "I rewrote chapters 4 and 9 — re-run the continuity extraction on just those and tell me which facts moved or disappeared." | lorescribe (manuscript re-run) | — |
| Y17 | "Turn the history of my fantasy setting into an SVG timeline I can open in a browser with no internet; rumoured events should look different." | lorescribe (timeline visual) | `trigger-timeline-svg` |
| Y18 | "Visualise my campaign world's history as a timeline chart, with who rules each kingdom after every war." | lorescribe (timeline, entity state, visual) | — |
| Y19 | "Brief the local model on the bridge ambush scene from my story bible: give it a reversal shape and the beats, all within canon." | lorescribe (brief, shape and beats) | — |

## Should not fire (17)

| # | Query | Expected owner | Native case |
|---|---|---|---|
| N1 | "Research the real history of Roman roads for my novel, with sources." | researchscribe | `nearmiss-roman-roads` |
| N2 | "Write chapter 4: the heroine reaches the river city at dusk." | no skill (drafting) | `nearmiss-write-chapter` |
| N3 | "Define our brand vocabulary — words we use, words we never use." | brand skill, not lorescribe | `nearmiss-brand-vocab` |
| N4 | "Pixel palette for the ice faction, eight colours that read at small sizes." | pixelsmith | `nearmiss-ice-palette` |
| N5 | "What does the lorewright skill do?" | researchscribe (old name) | `nearmiss-lorewright-name` |
| N6 | "Write the music brief for the river traders' theme — instruments, tempo, loudness target." | soundsmith | — |
| N7 | "Is this Godot test run green enough to close the milestone?" | godotsmith | — |
| N8 | "Which worldbuilding app should I buy, World Anvil or Campfire? Compare them with sources." | researchscribe (verdict) | — |
| N9 | "Line-edit this scene for pacing and cut 300 words." | commscribe (line edit, owner Q30) | — |
| N10 | "Turn my campaign notes into an EPUB." | no skill (manuscript build) | — |
| N11 | "Load whichever LM Studio model fits best and run my queued task cards overnight; they are story drafts." | lmstudiorunner | `nearmiss-run-local-model` |
| N12 | "Render this ComfyUI workflow at 1024 square; my last video render crashed the machine." | comfyrunner | — |
| N13 | "Write a pixel-art generator brief for the river guard sprite with a spec block and palette." | pixelsmith | — |
| N14 | "Line-edit chapter 7 of my novel for rhythm and cut 200 words; keep every fact." | commscribe | `nearmiss-line-edit-chapter` |
| N15 | "Draw our monthly sign-ups for the last year as a line chart I can open offline, one HTML file with inline SVG." | dataviz built-in (real data) | `nearmiss-sales-chart` |
| N16 | "Make a timeline chart of our product milestones for the team page." | dataviz built-in or no skill (real-world schedule) | — |
| N17 | "Tighten the pacing of this scene I wrote; keep what happens, cut the slack between beats." | commscribe (line edit, facts frozen) | — |

## Edge notes

- Sharpest pair: Y6 vs N1. Both name a novel and roads. Real-world facts → researchscribe; the story's own canon → lorescribe.
- Second pair: Y10 vs N4/N6. Recording visual tags and motifs as canon data is lorescribe; directing the art or audio from them is pixelsmith or soundsmith.
- N5: the word "lore" alone never routes here; lorewright meant research.
- Third pair: Y11 vs N11. A brief built from canon is lorescribe; loading a model and running the card is lmstudiorunner, even when the card is a story draft. Y13 and the entity-visual brief vs N12/N13: canon in, brief out is lorescribe; rendering is comfyrunner; a pixel spec block is pixelsmith.
- Fourth pair: Y14/Y16 vs N9/N14. Chapters in and canon or contradictions out is lorescribe; the words of a chapter changed, facts frozen, is commscribe. The description's "line edits commscribe's" carries it.
- Re-read 2026-10-01 against the 1,015-char description by the builder (not blind; `tools/blind_queries.py` plus a separate judge is the cold run, left for A6): Y1-Y16 fire on the named clauses (Y14 "extract one from a manuscript ... contradicts itself"; Y15 "timeline with entity state and story branches" plus "check a ... scene"; Y16 manuscript and contradiction clauses); Y11-Y13 still fire on "brief a local model or image tool from canon" after the parenthetical was cut; N1-N14 route out on their boundary clauses. No row changed verdict.
- Re-read 2026-10-01 against the 952-char description (A2 L-1, by hand, not blind): Y2 (game factions) fires on "story, lore or world bible (characters, places, factions ...)"; Y4 (naming rules with pronunciation) fires on "set naming rules, generate or test names"; Y6-Y8 and Y15 keep "fiction project", "in-game strings" and "share one canon across repos"; N1-N14 unchanged. No row changed verdict. The pronunciation key stays in the body (`names`, `audit`).
- Fifth pair: Y17/Y18 vs N15/N16. A chart of the story's own timeline is lorescribe; a chart of real data or a real schedule is the dataviz built-in's. The miss it answers: Y13's phrasing ("draw ... as a chart I can open offline") names no bible, canon or fiction word, and the 952-char description covered the drawn chart only through "brief a local model or image tool", so the run answered unaided. The 999-char description names the chart in the timeline clause ("or draw it as an offline HTML/SVG chart") and routes "charts of real data" to dataviz.
- Re-read 2026-10-01 against the 999-char description (FXL1, by hand, not blind): Y13, Y17, Y18 fire on the timeline clause's drawn chart; Y5 and Y15 keep "timeline with entity state and branches"; Y1-Y4, Y6-Y12, Y14 and Y16 keep their clauses ("orphans" and "direction" were cut; N4 and N13 still route out on "pixel art is pixelsmith's"; audit and Y9 keep `audit` in the mode list and "world bible"); N15 and N16 route out on "charts of real data are dataviz's"; N1-N14 unchanged. No row changed verdict.
- Sixth pair (added 2026-10-08, K4 C3, authored, not run cold): Y19 vs N17. Scene shape and beats inside a canon-checked brief are lorescribe's; tightening the prose of a written scene is commscribe's line edit.
- Pairs are counted one row per pair, from the notes above: Y6-N1, Y10-N4, Y11-N11, Y13-N12, Y14-N9, Y16-N14, Y17-N15, Y18-N16, Y19-N17 (9).
- Tuning rule: misses on the yes-set → make triggers pushier; fires on the no-set → tighten the boundary clauses.
