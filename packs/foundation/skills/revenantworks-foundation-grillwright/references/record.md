# Record — the settled-decisions record and its log

Read by `record`, `resume`, `questionnaire` and every hand-off. The record is the only
deliverable grillwright writes, and every build skill can read it without knowing grillwright.

## Where it lives

- With file tools in a repo: `GRILL-<slug>.md` at the project root, the slug a short kebab-case
  name of the work. A later grill of the same work updates its own file; it never adds a sibling.
- Inside an existing spec, plan or issue the user names: a `## Clarifications` section appended
  there instead of a new file.
- No file tools: the record in chat, in one fenced block, said so.

Write the file as answers land (Turn shape rule 4). Never commit it unasked.

## Shape

```markdown
# Grill — <title>

Lens: <target> · Weight: <Spike|Bounded|Architectural> · Rounds: <n> · Aspects: <n>
Outcome: <Clear | Open MUST: <areas> | Not worth building: <reason>>

## Settled
| # | Area | Decision | Source |
|---|---|---|---|
| 1 | JOB | Autosave every 5 minutes and on scene change | Said |
| 2 | CONTRACT | Old saves load unchanged | Said |
| 3 | DETAIL | No on-screen notice | Assumed (➡ accepted) |

## Done means
- <the check, test or reviewer that proves it, one line each>

## Out of scope
- <what this work will not do>

## Open
- [?] <question> — <why it matters>

## Log
### Session <YYYY-MM-DD>
- Q1 Trigger → A: timer plus scene change
- Q2 Slot → B ➡: rotating slot
```

## Rules

- **Source** is `Said` (the user stated it), `Read` (taken from a named file) or `Assumed`
  (a recommendation accepted without an explicit yes, or a MAY closed on assumption).
- **Done means** is never empty for a Clear outcome. If PROOF was never answered, Outcome is not
  Clear.
- **Log** is append-only. A changed decision gets a new log line; the Settled row is edited and
  the old value is not deleted from the log.
- **Hand-off line** closes the reply, not the file:
  `Next: <owner> — <command or first step>, reading GRILL-<slug>.md.`

## Resume

Read the record. Report its Outcome line and the count of `[?]` items. Ask only those, in the
spine order, then re-run the stop rule. A record whose Outcome is Clear and has no `[?]` reports
that and stops.

## Questionnaire

For someone else to answer later. Ask the user only two things: who it goes to, and what they
need back. Then write:

```markdown
# Questions for <role> — <title>

Needed by: <date or event> · Return to: <who>

1. <question>?
   Why this matters: <one line>
   Options considered: <A / B / C, or "open">
   Answer:
```

Most important first; MUST areas before SHOULD. No question the reader cannot answer from their
own role.
