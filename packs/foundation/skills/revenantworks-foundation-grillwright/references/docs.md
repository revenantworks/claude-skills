# Docs — grounding the grill in the repo's own glossary and decision records

Read for `grillwright docs`, or when a grill runs in a repo that already keeps a glossary or
decision records. The spine, lenses and stop rule in `grill.md` are unchanged; this file adds one
check before each question and one after each answer.

## Contents

- Find the documents
- Before asking: answer from the docs
- After an answer: check it against the docs
- Conflicts
- Writing back
- Without docs

## Find the documents

Look once, at the start, and say what was found. Common homes:

- **Glossary** — a `CONTEXT.md`, `GLOSSARY.md`, `docs/glossary.md`, or a terms section in the
  README or CLAUDE.md.
- **Decision records** — `docs/adr/`, `docs/decisions/`, `adr/`, numbered `NNNN-*.md` files, or a
  decisions log in the project's planning folder.

Take only what the request touches: the terms the request uses and the decisions whose subject
overlaps it. Never read the whole history into context.

## Before asking: answer from the docs

Turn shape rule 1 already says facts are read, not asked. Docs mode extends it to settled
decisions:

- A question a current decision record already answers is **not asked**. Its area is marked
  Clear, and the record cites it: `Settled by ADR-0007`.
- A term the request uses with a glossary definition is used **as defined**. When the request
  seems to mean something else by it, that mismatch is the question.
- A decision record marked superseded or deprecated answers nothing; follow it to the record
  that replaced it.

## After an answer: check it against the docs

Each answer that lands is compared with the documents before it is written to the log:

| Finding | Do |
|---|---|
| Agrees with a decision | Log it with the citation |
| Uses a term differently from the glossary | Ask once: keep the glossary meaning, or change the glossary |
| Contradicts a current decision | Stop the round; name the decision; ask which wins (see Conflicts) |
| Settles something no record covers and is hard to reverse | Offer it as a new decision record at hand-off |
| Coins a term the team will reuse | Offer it as a glossary entry at hand-off |

## Conflicts

An answer that overturns a recorded decision is never logged silently. Offer three options:
keep the recorded decision (the answer changes); supersede it (a new record replaces it, and the
old one is marked superseded, never edited away); or scope it (the new choice applies only to
this request, and the record says so). The grill's stop rule cannot pass while a conflict is
open; it stays a MUST item.

## Writing back

grillwright proposes; the user approves. At hand-off, list each proposed glossary line and
decision record as a draft in the settled-decisions record under **Docs to update**. Write a
docs file only after an explicit yes, in the repo's existing format and numbering. Never create
a glossary or a decision-record folder the repo does not already have unless the user asks.

## Without docs

When the repo keeps neither, say so in one line and run the plain grill. Do not offer to start a
glossary or a decision-record practice unless the user asks.
