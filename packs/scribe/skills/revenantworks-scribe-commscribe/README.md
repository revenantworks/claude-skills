# revenantworks-scribe-commscribe

Writes and cleans up messages and docs for their channel and reader: email, texts, Slack or Teams, release notes, social, Discord, YouTube, status updates, READMEs, memos, long docs in Claude Docs, and UI microcopy (buttons, errors, empty and loading states, confirms). The default is a plain human voice with no AI tells, and no fact moves while the text is reshaped. It never sends anything.

Part of the **scribe** pack (standard profile). It ships no scripts and needs no tools beyond the surface's own file tools; with none, everything comes back in chat.

## What it does that others do not

| Margin | What it means | Eval case |
|---|---|---|
| Facts never move | Every repair is checked claim by claim against seven named fact moves (an invented actor, a dropped manner word, a reattached modifier, a promoted noun, merged events, an act turned into a state, a deleted agent). Any hit rejects the repair | `evals/test-cases.md` T4, T5 · native `humanize-facts-frozen` |
| Channel contracts with precedence | Each channel has a ceiling and required structure; frozen facts outrank the ceiling, the ceiling outranks style rules. Claude Docs is a channel: outline first, one update per section, through the connector only | T1, T12 · native `docs-no-connector` |
| Voices that learn, opt-in | Several named voices side by side, picked per request and never assumed; a voice learns from 3 to 5 samples or from the diff between a draft and the writer's final edit; nothing is saved without a yes | T9, T10 · native `voice-diff-no-write`, `multi-voice-ask` |

Also: dash removal is a recast, never a comma splice; a score-only audit with a ship-or-revise gate; a first-run question so the writer knows the dash and emoji defaults and can switch them.

## Modes

`draft` · `reshape` · `humanize` · `audit` · `formats` · `cadence` · `voice` (`learn`, `diff`) · `docs`. A bare `commscribe` answers in three sentences and asks what to write.

## Voices and defaults

Voice files live where the writer keeps them (a `voices/` folder by default, one file per voice, plus `defaults.md`). The skill ships none. On the first run it asks once whether to keep the no-dash, no-emoji defaults and offers to save the answer. A brand's own voice guide (for example one exported by brandscribe) is read, never edited.

## Optional helpers

- **lmstudiorunner** (localops pack) runs offline drafts or bulk rewrites from a commscribe brief; every item that comes back is fact-checked.
- **whisperrunner** (localops pack) turns a voice note into a transcript that becomes the frozen source.

Neither is required. Without them, Claude drafts and asks for a paste.

## Boundaries

- A skill package's own files (SKILL.md, its README, references): skillwright.
- Defining a brand, its palette or its voice guide: brandscribe.
- A researched write-up with graded sources: researchscribe.
- Canon checks on fiction: lorescribe. Line-editing a chapter's prose is commscribe's.
- Sending: the surface's own mail or chat tool.

## Package

```
revenantworks-scribe-commscribe/
  SKILL.md
  README.md  CHANGELOG.md  SOURCES.md  LICENSE
  references/
    channel-profiles.md  humanize.md  fact-integrity.md
    voice-file.md  handoffs.md  pack.md
  evals/
    trigger-evals.md  test-cases.md
    <case>/prompt.md  <case>/graders/*.md   (claude plugin eval suite)
```

## Install

Install the scribe pack from the claude-skills plugin marketplace in Claude Code, or upload the folder as a skill on claude.ai. No other setup.

## Staying current

`references/channel-profiles.md` is restamped when a platform's conventions move. `SOURCES.md` is a 90-day calendar surface: re-run the incumbent scan when it ages out.
