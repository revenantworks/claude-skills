# Test Cases — example-notes

5 cases. Provenance: derived from example-notes v0.1.0, 2026-09-30.

## Case 1 — happy path
**Input:** a transcript with two actions, both owned and dated.
**Assert:** two numbered lines, each with an owner and a date.

## Case 2 — no owner
**Input:** a transcript with one action and no owner.
**Assert:** the line reads `owner: unassigned`.

## Case 3 — no date
**Input:** a transcript with one owned action and no date.
**Assert:** the line reads `no date`; no date is invented.

## Case 4 — agenda request
**Input:** "write the agenda for Monday's meeting"
**Assert:** the reply is helpful.
