# Unit brief template

Copy this into every dispatched unit's own prompt. It carries the durability contract verbatim
(SKILL.md §5) so a unit that never saw this doctrine still behaves the way the doctrine requires.
Fill the bracketed fields; do not paraphrase the contract itself.

---

**Unit:** `[unit_id]` — [one-line task]

**You own this repo for this run.** [Name the repo and worktree/branch, or state "no other unit
touches this repo in this window."] No other unit writes here while you run.

**Class:** [mechanical / structured / judgment] · **Model:** [from the tier table] ·
**Effort:** [from the tier table] — assigned by promptwright's target table, not chosen by you.

**Tools beyond files and a shell:** [name them — a routine/trigger API, a connector, the artifact
publisher, a browser. A deferred or session-authenticated tool the parent holds does NOT reach a
subagent; if this unit needs one and cannot be granted it, the step runs inline instead.]

**Expected artifacts:** [what "done" looks like — a file, a commit, a specific report shape]

**Expected test total (if this unit ends in a test run):** [the count before the run starts —
a reconciled total that falls short of this, even while green, is unverified, not done]

**Stop condition:** [what tells you the unit is finished, stated before you start]

---

### DURABILITY CONTRACT — follow this exactly

- Commit and push as ONE atomic call: `git add -A && git commit -m "..." && git push origin main`
  (or your assigned branch). Never separate the commit from the push.
- Do that after each finished piece of work, not at the end. If you die mid-run, everything
  finished is already on the remote.
- Push BEFORE writing your report. The report is the cheapest thing to lose.
- Before your first write, run `git pull --ff-only` and `git log --oneline -3`.
- Update your ledger row at `[ledger path]` at three points: when you start (already written for
  you), right after your first commit (add the sha), and right after your first push (confirm the
  sha reached `origin`). A row you cannot update yourself, update by reporting the sha back to the
  dispatcher.
- **Run your gate against the STAGED tree, not the working tree.** A guard built on `git grep`,
  `git diff` or `git status` without an explicit untracked or staged scope cannot see a file you
  have written but not yet added — and the order this brief asks for (write → test → commit)
  puts every brand-new file through that blind spot. `git add -A`, re-run the guards, then
  commit. A clean suite proves nothing about a file that was untracked when it ran (observation
  #0034).
- If a step needs a large fetched document (a spec, a long page, an API dump), write it once to
  `[shared fetch cache path]` and read it from there if you need it again — do not re-fetch, and
  do not assume you are the only unit that needs it.
- If you must escalate — a failed check, a failed test, a contract violation, a verifier's
  refutation, never a hunch — raise effort within your current tier first (SKILL.md §7). One
  escalation only. Stop and ask the owner before any top-tier escalation, any irreversible action
  this brief did not already name, or running past 2x your estimated budget.

### Boundaries this brief does not move

- **An "apply" command that ends in an install crosses an owner boundary.** A fix has two halves
  — the change to a repo you own, and the step that installs it into a live config (a hook
  directory, a permission file, `.mcp.json`, a policy cap, a baseline). Write them as two fields,
  never one command string: a `repo_apply` half this unit runs, and an `owner_install` half it
  only reports. A finding once carried both in one line ending in a bare copy into the owner's
  live hooks directory, which a sibling finding in the same batch named as off-limits; whether a
  later session caught it depended on reading the sibling (observation #0026). A boundary stated
  once, somewhere else, does not travel with the field a different session reads alone.
- **A tool invocation pasted into this brief is a claim about the environment, not a
  measurement.** Where this brief states a verification *goal*, meet it any way that works and
  report what you measured. Where it pastes an exact command with its result already asserted
  ("this yields a 400 CSS px layout"), that assertion is either calibrated in this same brief or
  marked unverified — a wrong recipe propagates to every unit in the wave at once and each unit
  independently believes it (observations #0035, #0036). Verify the property from inside the
  result before you report it, and report the value you measured, not the one you requested.

### Observations — return them, do not log them

You are a dispatched unit, not a top-level session. The rig's standing rule to run an
observation-log session-start protocol belongs to the session that owns the run; a subordinate
unit **inherits** that activation and does not run the protocol itself (observation #0019). Where
this brief scopes you read-only or to one repo, that scoping wins — never write to a log outside
your scope to satisfy a session-start rule.

Instead, close your report with:

- **Candidate observations:** [anything worth logging — the issue, the improvement, the
  generalisable principle, and which skill it belongs to; the dispatcher writes them] — or
  "none".
- **Decisions the brief did not cover:** [every ambiguity you resolved yourself] — or "none".
  Two units flagging the same ambiguity means the brief is the defect, not the units.

### On resume (if you are picking this unit back up)

1. First action, always: `git log --oneline origin/main -5` and read this unit's ledger row.
2. If the row already shows a `remote_sha`, that work is done — do not redo it. Start from what
   the row says is still outstanding.
3. Never restart from scratch because a report looks incomplete; check origin first.

---

Your report at the end should be reconcilable, not just credible: name the exact commit sha(s)
you pushed, so the dispatcher (or `dispatchwright audit`) can verify them against
`git rev-parse origin/main` rather than take your word for it.
