# Trigger evals: commscribe

Counts: 31 queries (16 should, 15 should-not, 6 pairs)

Provenance: written for 0.1.0 (2026-10-01). Status: authored, not run. Read each query cold against the name and description only, and compare with the Expected column. The native suite (`evals/<case>/`) runs eleven of these rows under `claude plugin eval`, beside behaviour cases. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

Cold run 2026-10-01 (run J1): blind list from `tools/blind_queries.py`, judged on the worker tier against all 30 pack descriptions: 24/24 agreed. Tiers checked: worker only; the fast and top tiers are unchecked, and the native `claude plugin eval` run is A6's.

## Should fire (16)

| # | Query | Expected | Native case |
|---|---|---|---|
| Y1 | "Make this Slack update less robotic, it reads like a chatbot wrote it: [paste]" | commscribe (humanize) | `trigger-slack-robotic` |
| Y2 | "Turn these commit notes into release notes for v2.4 on GitHub." | commscribe (draft, release notes) | `trigger-release-notes` |
| Y3 | "Score this customer email for tone and AI tells. Don't rewrite it." | commscribe (audit) | `trigger-score-email` |
| Y4 | "Learn my writing voice from these three LinkedIn posts so future drafts sound like me." | commscribe (voice learn) | `trigger-learn-voice` |
| Y5 | "Draft the launch plan doc in Claude Docs: goals, timeline, risks, owners." | commscribe (docs) | `trigger-claude-docs` |
| Y6 | "Here's your draft and the version I actually sent. What should you change about how you write for me?" | commscribe (voice diff) | `voice-diff-no-write` (behaviour) |
| Y7 | "Same text, but as a formal email to the landlord instead of a text." | commscribe (reshape) | none |
| Y8 | "Plan the comms for next Tuesday's release: a build-log note, Discord, a social post and a follow-up a week later." | commscribe (cadence) | none |
| Y9 | "Tighten this README intro for our CLI tool; it's wordy and full of fluff." | commscribe (docs, not a skill package) | none |
| Y10 | "Write a YouTube title and description for my video on fixing a leaky tap, with chapters." | commscribe (draft) | none |
| Y11 | "Line-edit chapter 2 of my manuscript for wordiness; don't change what happens." | commscribe (humanize or reshape on docs prose) | none |
| Y12 | "Write the team status update for this week from these notes, in the support voice." | commscribe (draft, named voice) | `multi-voice-ask` (behaviour, ambiguous variant) |
| Y13 | "The delete dialog says Are you sure? with Yes and No buttons. Fix the wording." | commscribe (ui profile) | `trigger-ui-delete-dialog` |
| Y14 | "Rewrite the empty-state and error copy on this signup form." | commscribe (ui profile) | `ui-microcopy-rewrite` (behaviour) |
| Y15 | "Our buttons all say Submit and OK; give me better labels for these six actions." | commscribe (ui profile) | none |
| Y16 | "My manager replied 'I don't follow' to this explanation of the outage. Say it again so it lands." | commscribe (retell, K4 C2) | none |

## Should not fire (15)

| # | Query | Expected owner | Native case |
|---|---|---|---|
| N1 | "Build our brand palette and type scale and export it as a design system." | brandscribe | `nearmiss-brand-palette` |
| N2 | "Research which CRM we should pick for a five-person team, with sources and a verdict." | researchscribe | `nearmiss-research-crm` |
| N3 | "Humanize the SKILL.md and references in my skill package before I publish the plugin." | skillwright (prose pass on a skill package) | `nearmiss-skill-file` |
| N4 | "Write chapter 4 of my novel: the heroine reaches the river city at dusk." | none (fiction drafting) | `nearmiss-write-chapter` |
| N5 | "Send this email to the venue now." | none (no skill sends; the mail tool does) | none |
| N6 | "Update our brand voice guide so the whole company sounds warmer." | brandscribe | none |
| N7 | "Check chapter 9 against my story bible; a dead character speaks." | lorescribe | none |
| N8 | "Load a local model in LM Studio and run my queued task cards overnight." | lmstudiorunner | none |
| N9 | "Transcribe this 40-minute interview recording to SRT." | whisperrunner | none |
| N10 | "Write a system prompt for a customer support bot." | promptwright | none |
| N11 | "Trim my CLAUDE.md, it costs too many tokens." | rigwright (slim) | none |
| N12 | "Make a ten-slide deck for the quarterly review." | none (a slides artifact or deck tool) | none |
| N13 | "Score this settings page's layout, spacing and visual hierarchy before release." | brandscribe (ui) | `nearmiss-score-layout` |
| N14 | "Check dist/ for missing fonts and low-contrast text." | brandscribe (ui) | none |
| N15 | "The model keeps misreading my system prompt; rewrite the prompt so it lands." | promptwright | none |

## Edge notes

- **Sharpest pair: voice.** "Write this email in our voice" is commscribe (a named voice applied to one message). "Update our brand voice" is brandscribe (the guide itself). "Learn my voice from my edits" is commscribe (a writer's voice file, approval-gated).
- **Docs pair.** A README or memo for people is commscribe's docs mode; a skill package's own files are skillwright's. The object decides, not the word "README".
- **Fiction pair.** Line-editing a chapter's prose is commscribe; drafting new fiction is no skill; canon checks are lorescribe.
- **UI pair.** The words on a screen (labels, errors, empty states, confirms) are commscribe's `ui` profile; scoring the screen's layout, contrast or states is brandscribe `ui`, whose catalog hands copy rows here. Re-read by hand 2026-10-01 against the 997-char description (UIX): Y1-Y15 fire; N1-N14 route out; no earlier row changed verdict.
- **Retell pair (Y16 vs N15, added 2026-10-08, K4 C2, authored, not run cold).** A message a person did not understand is commscribe's retell; a prompt a model misreads is promptwright's.
- **Tuning.** Misses on the should-fire set: make the trigger list pushier. Fires on the should-not set: tighten the boundary sentence.
