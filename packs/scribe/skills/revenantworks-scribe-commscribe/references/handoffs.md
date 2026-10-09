# Optional local hand-offs

Two local-model skills can take part of the work. Both are pointers: commscribe never calls a local app itself, never installs anything, and works fully without either. Each hand-off is a brief out and a check on what comes back.

## lmstudiorunner: offline drafts and bulk rewrites

Use when the requester wants drafting kept on the machine, or a batch (many release-note items, a set of FAQ answers) rewritten in one run. commscribe writes the brief; lmstudiorunner picks the model, runs it and applies its own fitness check. Pick a model that fits the job's role in lmstudiorunner's terms; delegated drafting under explicit style rules wants the balanced tier or its local equivalent.

Brief, as one block:

```
TASK: <draft | reshape | humanize> one <channel> item per input below.
FACTS (frozen; use only these; never add a name, number, date or actor):
- <fact 1>
- <fact 2>
CHANNEL: <profile name>, <ceiling>, <required structure>
RULES: no characters U+2012 to U+2015 or U+2212 (unless dashes allowed);
       no emoji; first sentence carries information; no closing help offer;
       name the actor only when FACTS names one.
VOICE (optional): <voice name>, pairs:
  BEFORE ... / AFTER ...
OUTPUT: plain text, one item per input, no commentary.
INPUTS:
<item 1>
<item 2>
```

On return: run the full Check from the SKILL body on every item, with the claim check against the FACTS block. An item with a moved fact is rejected and redrafted by Claude, never patched silently. Report the count kept and rejected in one line.

Without lmstudiorunner: Claude drafts, and the brief is offered as text if the requester wants to run it elsewhere.

## whisperrunner: voice note to draft

Use when the source is a recording (a voice memo with the points for an email). whisperrunner transcribes; the transcript is the source, and its facts are frozen like any handed-in text. Filler words and false starts are not facts; names, numbers, dates and commitments are. A word the transcript marks as uncertain goes back as a question, never a guess.

Without whisperrunner: ask the requester to paste the points or a transcript.
