# Description Crafting — Routing Is Set Here

The description decides whether a built skill ever runs. Load this file when writing or fixing one.

## Rules

- **≤1024 characters, third person, what + when.** State what the skill does, then the conditions that should fire it — in the words a user would actually type, not the author's jargon. All when-to-use information lives here; the body is never consulted for routing. **No unquoted colon-space inside the text** — YAML parses `: ` as a nested mapping and the frontmatter fails validation; use an em-dash or quote the whole scalar.
- **Lean pushy.** Skills under-trigger. After the plain triggers, widen deliberately: "…even if they don't explicitly say <keyword>." Push toward the task, never past it.
- **Name the invocation keywords.** If the skill answers to a word ("promptwright", "skillwright") or subcommands ("<name> refresh"), quote them — quoted keywords route hardest.
- **Cover every entry point.** A skill with build/audit/configure modes lists trigger phrases for each; an entry point absent from the description effectively doesn't exist.
- **Verb parity: enumerate what the body implements, then check each verb has a token here** (added 2026-09-11, observation #0021). Where the body documents a set of reply verbs, write ops, or subcommands, list them and confirm every one has a literal or near-literal token in the trigger list — not a generic catch-all standing in for it. One skill's body documented four write-op replies and its description named three; the fourth survived two version bumps because the eval suite sat authored-but-never-run, so no cold judge ever read the description against the body. The check is a diff between two lists already open on the same pass, and a catch-all phrase ("any status question") reads as covering read-only asks, never a write op.
- **Key use case first; the listing cap is 1,536** *(added 2026-09-28, code.claude.com/docs/en/skills)*. Claude Code truncates a skill's listing at 1,536 characters of `description` plus `when_to_use` combined (`when_to_use` is Claude Code-only). Put the main use case in the first sentence so truncation never cuts it, and stay under the 1,024 description ceiling in `rubrics.md` for every other surface.
- **Triggers, not the workflow** *(added 2026-09-28, from superpowers writing-skills)*. The description states when to fire and never summarises the steps: a model given a workflow summary may follow it instead of reading the body.
- **Close with the boundary sentence.** One line that routes the nearest neighbor away: "For <adjacent job>, <other skill> is the right tool." Boundaries beat breadth — a description that grabs a neighbor's traffic fails the set.

## The discoverability test

Write ten realistic requests before finalizing: seven that should trigger, three near-misses that shouldn't. Reading only name + description, route all ten. Any miss is a description defect, not a body defect. For suites, run the test across the whole sibling set — requests must land on the right member.

**The tuning loop** *(added 2026-09-28)*. When skill-creator is installed, drive its description loop (`run_loop`: a 60/40 train and held-out split, each query run three times, the winner chosen on the held-out score) as a tool, and add the pack's trigger-partition near-misses to its held-out set. Otherwise run it by hand: split the trigger table 60/40, tune on the 60% for at most three rounds, and keep the version that scores best on the held-out 40%, with the near-misses in the held-out rows. Choosing on the rows you tuned against rewards overfitting.

**Re-anchoring a suite is not running it** (observation #0021). Updating an eval file's version line proves the file was opened; only an actual cold judge, reading the description text alone, catches a verb the body grew after the description was last tuned. A suite marked "authored, not run" has never tested anything — carry that state as a finding, not a footnote.

**Measure every description in the set, not only the one that failed.** The ceiling in `rubrics.md` is a hard gate; treat ~900 characters as a soft warning band and record the measured length per member at delivery. A 2026-09-09 delivery pass measured all ten members of one pack and found two sitting in that band — visible only because the whole set was measured, not just the member under edit (observation #0011).

## Anti-patterns

Vague capability statements ("helps with documents"); author-side vocabulary the user won't type; when-to-use guidance buried in the body; breadth that annexes an adjacent skill's triggers; brand language occupying trigger budget (brand belongs in the name and README, never in the description).
