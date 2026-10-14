# Humanize: the deep catalog

H1 to H9 live in the SKILL body with their counting units. This file states no hard rule and restates none. It carries how each rule is detected and repaired, the judgement-tier tells no hard rule catches, the lexicon procedure, a copyable check list with patterns, one worked repair, and what this doctrine gets wrong. If a line here reads like a hard rule, the body is right and this file is wrong.

**When to open it.** For humanize, for audit, and for a draft long or tell-dense enough to earn the cost. Never on a standard short draft.

**Self-applied.** This file carries no banned dash in its own prose. The worked repair's BEFORE block is a specimen fenced as `specimen` and carries banned characters on purpose; the skill's own eval lints every file outside that block.

## Contents

- The six categories
- Check list with patterns
- Applying the hard rules
- Tell catalog by category
- Where humanize yields
- Residual risks
- Worked repair
- Contested repairs

## The six categories

Findings are filed under six categories, the vocabulary of the most-used public humanizer skill (blader/humanizer, read 2026-10-01; ideas only, nothing installed). The counting units stay ours.

| Code | Category | Hard rules filed here |
|---|---|---|
| A | Staging instead of stating | H4 preamble, H8 hedge stacking, H9 missing actor |
| B | Rhythm by rule | H1 dashes, H3 length variance |
| C | Inflation and borrowed authority | H7 constructions |
| D | Formatting by rule | H2 emoji |
| E | Leftovers from the chat and the draft | H5 help-offer closer, H6 recap |
| F | Writing for the wrong reader | none; judgement only |

Audit findings run **strongest first**: P0 before P1 before P2, and inside a level the tell a reader notices first.

## Check list with patterns

Run all five, in order, before a draft goes out. Where a code tool exists, the patterns below run as one-line checks (JavaScript regex with the `u` flag; in Python write `\U0001F000` for `\u{1F000}`); where none exists, scan by eye against the same list. A failed item sends the draft back to repair.

```
[ ] 1. Codepoints (H1, H2, under the active switch)
       dashes:  [\u2012\u2013\u2014\u2015\u2212]
       emoji:   [\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]
       codes:   :[a-z0-9_+\-]+:        (a shortcode the platform renders)
[ ] 2. Claim check against the source: every claim traces with the same
       subject, object, scope and modality; all seven moves, not a word diff.
[ ] 3. Ceiling and required structure from the channel profile.
[ ] 4. First and last line:
       opener:  ^(Great question|Absolutely|Certainly|Sure|Of course|I'd be happy to)
       closer:  (Let me know if|Feel free to (reach out|ask)|Hope this helps|Happy to help)
[ ] 5. H3 count: one sentence of 8 words or fewer per five; past about forty
       words, one over fifteen and no four in a row inside a four-word band.
```

Item 2 wins any conflict: a fact never leaves to meet a ceiling or a rhythm floor. A fact that will not fit is a question for the requester.

## Applying the hard rules

Three tiers. H1 and H2 settle on a codepoint scan. H5 and H7 have an exact-match core and a judgement rim. H3, H4, H6, H8 and H9 turn on a counting unit or a register floor.

- **H1, repair order.** Full stop first, usually right. Then a colon when the second half delivers on the first; parentheses when the aside is optional; a comma only when the aside is short and the sentence stands without it. A swap without a recast leaves a splice ("The fix shipped, it cut latency in half" is a splice; "The fix shipped. It cut latency in half." is the recast).
- **H1, where the habit migrates.** Parentheses are the usual repair and so the place the rhythm reappears; that is what the per-paragraph cap is for. Promote the aside to its own sentence, or cut it.
- **H2, shortcodes.** Rendering depends on the platform. Treat any colon-wrapped token the target renders as emoji; where the platform is unknown, cut it.
- **H3, what uniformity looks like.** When nearly every sentence lands between 15 and 25 words, the band is the tell. Bullets get the check on their own terms: not every bullet the same shape and length.
- **H4, what is not preamble.** The opening move a formal letter or legal notice is expected to make. What it bites: restated requests, enthusiasm, runway, and comments about the edit itself.
- **H5 and H6, reading the close.** Ask what the last paragraph does: name a date, make an ask, promise an action, or only signal presence. "I will share updates as they come" does the last.
- **H7, the family.** An inflation frame promotes a claim without adding a fact. Look for that shape once the listed strings are gone.
- **H8, seeing the count.** Split the sentence into independent clauses first, then count inside each. When two qualifiers in one clause both carry fact ("roughly 200 accounts may be affected"), recast to move one into the verb: "We expect roughly 200 accounts to be affected" (only when the source names "we").
- **H9, the specimen.** "A decision was made to defer the migration, and clarification will be provided following the completion of the review" clears H1 to H8 and is plainly machine. Repaired, when the source names the platform team: "The platform team deferred the migration and will explain once the review finishes."
- **H9, the middle move.** When the source names no actor, recast to a form that needs none (an intransitive verb, a nominal bullet label). Reach for a stative verb only where the source reports a state. Every H9 repair then runs the read-back test in `fact-integrity.md`.

## Tell catalog by category

### A. Staging instead of stating

- **Preamble** (H4), **hedge stacking** (H8), **missing actor** (H9).
- **Over-signposting.** "First... Second... Finally..." over three short points. Cut the ordinals unless sequence carries meaning.
- **Both-sides framing.** A balanced survey when the writer has a position. If the request or thread shows the position, lead with it, then the strongest objection once.
- **Terminal qualifier.** "...though this may vary depending on context." If the tail names a condition, scope, exception or date, it is content; otherwise delete from the comma.

### B. Rhythm by rule

- **Dashes** (H1) and **uniform length** (H3).
- **Opener uniformity.** Every sentence subject-first, or on "The" or "This". Vary the entry; name the noun instead of a bare "This helps".
- **Paragraph uniformity.** Three-sentence blocks forever. One single-sentence paragraph fixes it.
- **Rule of three.** Delete the third term. If no fact is lost, it was a tell.
- **Machined parallelism.** Every limb the same shape. Scannable parallel items (release-note bullets, options, steps) are structure and stay; parallelism inside running prose is a tell.
- **Zero fragments.** Over roughly 200 words with none reads machined. At most one, where it lands a point. Formal email, legal notices and release notes take complete sentences.

### C. Inflation and borrowed authority

- **Banned constructions** (H7).
- **Shallow -ing riders.** "..., highlighting the team's commitment." Delete from the comma; if no fact is lost, it was a tell.
- **Borrowed authority.** "Studies show", "experts agree" with nothing named. Name the source if the thread gives it; otherwise cut the frame or ask. Never supply a study.
- **Inflated verbs and wordy pairs.** ensure, serves to, plays a key role in, enables; "in order to" is to, "due to the fact that" is because, "at this point in time" is now.
- **Lexicon.** A smell test, not a filter. One question decides each instance: does a plainer word lose anything? *High smell* (presume tell): delve, leverage (verb), seamless, holistic, multifaceted, intricate, pivotal, realm, landscape (metaphor), tapestry, testament, underscore, foster, garner, elevate, unlock, harness, navigate (metaphor), embark, journey (metaphor), treasure trove, game-changer, cutting-edge, best-in-class, synergy, resonate. *Context-dependent* (presume fine): robust, comprehensive, nuanced, crucial, vital, align, streamline. A term of art in the reader's field is not a smell word ("threat landscape" in security). Flag density: one smell word repeated inside 200 words, or three distinct ones in a paragraph. Replace the abstraction with the concrete thing only when the source has it.

### D. Formatting by rule

- **Emoji** (H2).
- **Bold mid-sentence.** Cut it, or move the phrase to the front. Bold is for lead lines and labels a profile requires.
- **Headers on short content.** Under roughly 150 words, no headers; the lead line is the header. Title-case labels ("Key Takeaways", "Next Steps", "TL;DR") go too, unless the profile asks for them.
- **Nested one-line bullets** and **listification** (an argument chopped into bullets). Bullets carry parallel items; prose carries reasoning.
- **Curly quotes in plain-text channels** where the thread uses straight ones. Never touch quoted material.
- **Hard wraps** in a paste-ready block. Output for paste is unwrapped plain text.

### E. Leftovers from the chat and the draft

- **Help-offer closer** (H5) and **recap paragraph** (H6).
- **Chatbot residue.** "As an AI", "Here is a revised version:", "Certainly! Below is", knowledge-cutoff caveats, a "consult a professional" nobody asked for. Test: would the named sender write this line to this reader?
- **Stale version references.** A product named with a version or "as of my last update" frame the source never gave. Keep a version only when the source states it.
- **Email boilerplate.** "I hope this email finds you well", "I wanted to reach out", "circling back", "just following up". Open at the point; the greeting stays.

### F. Writing for the wrong reader

- **Register drift.** A legal tone in a family text, slang in a formal complaint. The channel profile sets register; humanize never drags a message down a register to sound human.
- **Explaining what the reader knows,** or skipping what they do not (an acronym a customer has never seen). Write for the named reader.
- **Writer-side framing.** The message describes the writer's process ("after reviewing the logs carefully") when the reader needs the outcome.

### What replaces a tell

Subtraction alone leaves dead prose. Name the actor, use the specific verb, insert the number where an adjective was working, take a position and stop. On actorless source text, contractions are often unreachable (they live on subject-verb pairs the freeze forbids inventing); none is then a pass.

## Where humanize yields

- **Required structure is not a tell.** A Slack bold lead, Keep-a-Changelog buckets, YouTube chapters: contracts, not decoration.
- **A named voice.** Its lexicon list beats the smell list. A voice sign-off with a dash gets recast unless the voice's dash switch is off.
- **The profile owns register; humanize owns humanity.** Formal plus humanized is plain, complete, tell-free sentences. It is not casual.

## Residual risks

- **The dash and emoji defaults are policy, not laws of writing.** Em dashes are normal in good human prose; the real tell is uniform overuse. The bright line is cheap to enforce, which is why it is the default and why a voice file can switch it off. On Discord, social and YouTube, emoji are native convention; the per-message ask exists for that.
- **H9 is the rule most likely to break the freeze.** In the predecessor skill's first assertion run, the only two failures were H9 repairs: one invented an actor, one shed a manner fact.
- **A repair can keep every word and still move a claim.** See the near miss in the worked repair.
- **A large shrink is a signal, not a success.** If the AFTER is under half the BEFORE, look at what did the shrinking.
- **One voice across a set.** Uniform rules make uniform output; the cadence mode's variation rule is the counter.
- **Over-application reads dead.** Every sentence clipped, fragments as decoration, contractions forced into a legal notice. If the repair makes the sentence worse, the tell was not the problem.
- **A hedge is sometimes the truth.** Where something is unknown, the honest repair says so once.
- **Humanize never fakes humanity.** No invented typos, manufactured casualness, borrowed slang or anecdotes.

## Worked repair

A handed-in Slack update, humanize mode, defaults on. The BEFORE block is the specimen.

BEFORE:

```specimen
Great question! I'd be happy to give an update on where things stand.

It's worth noting that the database migration — which the team has been
working diligently on for several weeks — is now complete as of Tuesday.
:tada: They did a **truly comprehensive** job navigating a complex and
multifaceted landscape of dependencies. Moreover, we've seen robust
improvements in p95 query latency, which fell from 840ms to 210ms.

It's not just faster, it's more reliable — there were no failed writes
during the cutover window.

**Next Steps**
- We will continue to monitor
  - Monitoring runs through Friday

At the end of the day, this is a game-changer for the platform. Let me know
if you have any questions!
```

AFTER:

```
**The database migration is complete** as of Tuesday. The team worked diligently on it for several weeks, and the dependencies were complex.

p95 query latency fell from 840ms to 210ms, and no writes failed during the cutover window.

We're monitoring through Friday.
```

Report line: removed the opener, three em dashes, an emoji shortcode, mid-sentence bold, a header over two lines, a nested one-line bullet, the help offer, six smell words, four inflation frames, and a closing line with no claim; kept the Slack bold lead and the writer's read of the team and the dependencies, in plainer words.

The claim check runs before the report and is not printed: Tuesday, several weeks, the dependencies, 840 to 210, the failed writes and Friday all trace with their source subjects. **The near miss:** "the team spent several weeks on the dependencies" uses only source nouns and still reattaches a duration the source put on the whole migration (move 3). A noun-membership check passes it; the claim check rejects it.

## Contested repairs

**An incident update posted to Slack.** The passive floor covers the postmortem and the status-page notice. A channel post about the same incident is a different artifact: it names the actors the source supplies and recasts the rest.

**A flagged word that stays.** "Robust under 3x load, per the soak test." The plainer words lose the sense of surviving stress, and the benchmark makes it precise. Keep it and say so in the report line.

**A repair that is refused.** Four release-note items in the same shape. Machined parallelism says break one; the profile says these are scannable items. The profile wins, and nothing is reported.
