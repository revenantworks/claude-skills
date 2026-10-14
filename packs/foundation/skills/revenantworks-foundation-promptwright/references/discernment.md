# Discernment note — "where to double-check this"

An optional section for a prompt whose output gives **factual answers to a person**: a support
bot, a research helper, a tutor, an internal Q&A assistant. It asks the model to end a factual
answer with a short pointer to where the reader can check it. The aim is a reader who verifies
what matters, not a model that sounds less sure.

## When to offer it

Offer it in Phase 5 (one line in the assembly reasoning) when all three hold:

- the output states facts a reader may act on (dates, figures, rules, product behaviour, health,
  money, law);
- a person reads the output, not a parser;
- the facts can be wrong — no closed, fully supplied context that the answer only restates.

Do not add it to structured output (JSON, a classifier label), creative work, or a prompt whose
whole answer is drawn from documents the prompt already supplies and cites. A user who declines
it is honoured; it is never forced into a build.

## What the section says

Write it in the prompt's own voice, positively framed, with the reason given. It binds four
things, each observable (the Hostile read applies):

1. **When:** only on answers that state checkable facts; never on chit-chat or opinion.
2. **Where:** name a kind of source the reader can reach — the official documentation, the
   statute, the vendor's status page, the original paper, a qualified professional — or the
   supplied document by its section. Never invent a URL, title or citation; a kind of source is
   better than a fabricated specific one.
3. **Which part:** point at the claim most worth checking (the one that is newest, most
   consequential, or least certain), not at the whole answer.
4. **Length:** one line, after the answer, never before it and never as a disclaimer paragraph.

A starting shape to adapt, not to paste:

```
<verification_note>
When your answer states a fact the reader might act on, end with one line naming where they
can confirm the claim that matters most, as a kind of source they can reach. Never invent a
link or a citation. Skip this line for opinions, small talk and answers drawn only from the
documents provided, which you cite instead.
</verification_note>
```

## How it interacts with the rest of the build

- **Missing grounding** (Phase 2 bottleneck) comes first. The note does not fix a prompt that
  will hallucinate; grounding data or retrieval does. The note helps the reader catch what is
  left.
- **Tier:** C-tier targets get the section plus one example answer that ends with the line.
- **Self-check:** the Faithful and Literal-proof checks cover it — "end with a source" is met
  literally by a made-up link, which is why rule 2 forbids one.
- **Footer:** list it under Assumed when it was added unasked.
