# Unit review and the decision map

Read this when a writer unit returns (the review, §7) and when a run will outlast one session
(the decision map, `plan` and `resume`). Both are procedure, not new rules: the reviewer rules in
`tier-routing.md` and the scope check in §8 still apply unchanged.

## Contents

- Per-unit review — the worktree, then two stages in a fixed order
- Decision map — what is decided, what is open, what blocks what

## Per-unit review

Every writer unit works in its own worktree on a short-lived branch (§6), so its diff is the
whole of its work and nothing else. When it returns, the controller runs one review in two
stages. The order is fixed: quality is never judged on work that did not do what it was asked.

**Stage 1 — spec conformance.** Did the unit do what its brief says, and only that?

1. Every deliverable the brief names is present, by path or sha — not by the unit's report.
2. `git diff --name-status <base>..<sha>` lists only paths inside the row's `files_allowed`.
   One path outside it fails the stage.
3. The brief's stop conditions held: no push the brief did not name, no deleted test, no edited
   assert the brief did not name, the call cap respected.
4. The test total matches the brief's expected total (§8); a short total fails the stage.

A stage 1 failure sends the row back as one fix round with the failed item quoted. Stage 2
does not run on it, and the row stays `unverified`.

**Stage 2 — quality.** Is the work good, now that it is the right work? A fresh-context
reviewer (required; another model family preferred, `tier-routing.md`) reads the diff only:
correctness, a test that proves the change, readability, no dead or duplicated code, nothing
that weakens a check. It maps every hunk to a finding id and re-derives any headline figure
with its own probe. It reports; it never fixes. A finding becomes a fix round, never a
reviewer edit.

**Sizing the review.** A mechanical row (a docs sync, a status table) may take stage 1 alone,
run by the controller from the diff command above; the row says so. A build or judgment row
always gets both stages. The review's own spend is recorded on the row like any unit's.

Only a row that passed both stages (or stage 1 where the row says stage 1 alone) goes on to
landing and Reconcile.

## Decision map

Work that will outlast one session keeps a decision map beside the ledger
(`<run folder>/decisions.md`). The ledger says what each unit did; the map says why the run is
shaped the way it is and what still has to be settled. One page; three parts:

| Part | One line per | Columns |
|---|---|---|
| Decided | decision | id · the decision · who settled it · date · the words or the sha it rests on |
| Open | question | id · the question · who settles it · the rows it blocks · options, recommended first |
| Blocks | ledger row | row · the open decision ids it waits on |

Rules:

- **A decision moves from Open to Decided only on the settler's own words, quoted, or a landed
  sha.** A unit's report never settles one.
- **A row that waits on an open decision is not launched.** Every other launchable row launches
  before the question is asked (§6, Asking the user).
- **A changed decision is struck through and replaced, never deleted**, so a later session can
  see what moved and when.
- **`resume` reads the map after the ledger** and before anything is re-dispatched; a decision
  settled while the run was stopped is recorded first.
- **A decision that changes scope or a milestone is the replan gate** (`dispatch`): the map
  records it, the replan page explains it.
- The map follows the run records' rule for public repos (§5): kept off git there, or in a
  private companion repo.
