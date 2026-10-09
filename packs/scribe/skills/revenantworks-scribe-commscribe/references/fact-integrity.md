# Fact integrity: the seven moves

The SKILL body names the rule and the seven moves; this file shows each one and the test that catches it. Open it when a repair is contested, when an H9 recast is in play, or when auditing a rewrite someone else made.

**The rule.** Removing a tell never removes a fact and never adds one. The check is at claim level: every claim in the output is a claim the source makes, with the same subject, object, scope and modality. Any single move below rejects the repair. A plausible specific is fabrication, and fabrication outranks any tell it fixed.

## The moves, with specimens

| # | Move | Source | Moved repair | Why it fails |
|---|---|---|---|---|
| 1 | A word arrives | "The outage was resolved at 14:10." | "Our team resolved the outage at 14:10." | An actor the source never named. "We", "the team" and a bare "they" are the usual inventions. |
| 2 | A manner, means, time or scope word drops | "The records were fixed by hand." | "The records are fixed." | "By hand" was a fact about cost and risk. |
| 3 | A modifier reattaches | "The team worked on the migration for several weeks; the dependencies were complex." | "The team spent several weeks on the dependencies." | The duration belonged to the whole migration. |
| 4 | A noun is promoted to actor | "The referral was faxed from the clinic." | "The clinic faxed the referral." | The source gave a place, not a sender. |
| 5 | Two events merge | "The fault was identified at 09:14, when elevated error rates were observed." | "The fault turned up at 09:14." | Two events (detection, observation) became one. |
| 6 | A completed act becomes a state or a need | "Transport has been arranged." / "The rows were fixed by hand." | "Transport is arranged." / "The rows needed a manual fix." | An act became a standing state; a completion became a need. |
| 7 | An implied agent is deleted | "The rollout was paused." | "The rollout paused." | The source implied someone paused it; the repair says it stopped on its own. |

## Why a word diff is not the test

A diff for a new actor and a lost adverbial catches moves 1 and 2. Moves 3 to 7 add no actor and drop no manner word. Three of them coin no new word at all, so a novel-token scan draws no line either: "The clinic faxed the referral" uses only source words.

**The read-back test.** For each repaired sentence: count the source's events and the repair's; check what each modifier attaches to on both sides; read each repaired verb back as a claim (who did what, when, how, finished or not, certain or not). If any answer differs from the source, the repair is rejected.

## When the only fix moves a fact

Keep the source's wording and raise the gap as a question to the requester. A passive that stays because the source names no actor is a pass, not a shortfall. A ceiling that cannot hold every fact is a question about what to cut, never a silent drop.

## Cutting a long source down

Quote, don't paraphrase. When a summary, release note or cutdown keeps a claim from a longer source, it keeps the source's words for that claim (trimmed, never reworded into a new claim). Paraphrase is where moves 3 to 6 slip in.

## Delegated drafts

A draft from a subagent or a local model is untrusted until this check passes. Run the full read-back against the facts block the brief carried; any move rejects that draft or that sentence.
