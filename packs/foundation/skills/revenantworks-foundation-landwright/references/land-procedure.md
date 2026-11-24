# Land procedure

The commands behind SKILL.md's eight steps, plus the account switch, the merge method, `[skip ci]`
and the red-run loop. Placeholders: `<repo>` is the local clone, `<o>/<r>` the GitHub owner and
repo, `<n>` the PR number, `<branch>` the land branch. Shell forms are POSIX; PowerShell takes the
same git and gh lines.

## Contents

- Step commands
- Finding the CI step list
- Merge method
- Account switch
- `[skip ci]`
- Red run — the fixer loop
- Without gatewarden's hooks, without gh

## Step commands

| Step | Command | Read back |
|---|---|---|
| 1 Sync in | `git -C <repo> fetch --prune` then `git -C <repo> status --porcelain` | empty status → `git -C <repo> merge --ff-only @{u}`; any line → stop, list the files |
| 2 Local CI | `python <hooks>/ci_stamp.py run --repo <repo> --step "<step 1>" --step "<step 2>"` | exit 0 and a stamp for HEAD (`ci_stamp.py show --repo <repo>`) |
| 3 Land branch | `git -C <repo> switch -c <branch> origin/main` then `git -C <repo> cherry-pick <first>^..<last>` | `git log --oneline origin/main..HEAD` lists only the work's commits; re-run step 2 on the new head |
| 4 Intent | `python <hooks>/push_gate.py intend --repo <repo> --max <N> --head <sha>` | N from `git rev-list --count origin/main..HEAD`, sha from `git rev-parse HEAD` |
| 5 Push | `git -C <repo> push origin <branch>` | `git ls-remote origin refs/heads/<branch>` prints the head sha |
| 6 PR | `gh pr create --repo <o>/<r> --base main --head <branch> --title "..." --body-file <file>` | the PR url and number |
| 7a Checks | `gh pr checks <n> --repo <o>/<r>` | every row reads `pass`; `pending` → wait, read again; `fail` → stop the merge |
| 7b Merge | `gh pr merge <n> --repo <o>/<r> --merge --delete-branch` | `gh pr view <n> --repo <o>/<r> --json state,mergeCommit` → `MERGED` and a sha |
| 8 Run on main | `gh run list --repo <o>/<r> --branch main --limit 5 --json databaseId,headSha,status,conclusion,workflowName` | the row whose `headSha` is the merge sha; `completed` + `success` is green |

Step 7a and 7b are separate calls. A line that reads the checks and merges (`gh pr checks --watch
&& gh pr merge`) trusts an exit code instead of the rows, and gatewarden's `work_guard.merge_chain`
refuses it where installed. While a run is still going, wait with the harness's monitor or a
bounded loop that reads state, never a fixed sleep, and read the rows again.

Step 3 applies when the work sits on local main or on a branch cut from it. Work already on a
branch whose base is `origin/main` lands from that branch; check with
`git merge-base --is-ancestor origin/main HEAD`.

## Finding the CI step list

The repo's own CI is the list: its local runner if it has one (a `ci_local` script, a
`ci-local` make target, a documented "Commands" block in its CLAUDE.md or CONTRIBUTING), else the
`run:` steps of its push workflow under `.github/workflows/`, in order. A step that needs a
service the machine lacks is excluded by name with a reason (`ci_stamp.py --excluded "NAME:
REASON"`), and the report says the local verdict is partial. A repo with no CI at all is stamped
with `--no-ci` and the report says so.

## Merge method

Read it: `gh repo view <o>/<r> --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed`.

- `mergeCommitAllowed` true → `--merge` (the default; it keeps the commit-per-piece history).
- Only `squashMergeAllowed` true → `--squash`, and the report says squash.
- Only rebase allowed → stop and ask; never rewrite on the user's behalf.

## Account switch

`gh` acts as one account at a time. When the repo's owner is an account the active one cannot see
(a 404 on a repo that exists), switch for the one call and switch back in the same call, so the
next call starts on the default account even if this one fails:

```
gh auth switch -u <repo-account> && gh pr checks <n> --repo <o>/<r>; gh auth switch -u <default-account>
```

`gh auth status` names both accounts. The switch never writes a token, and the identity named in
the brief or the repo's CLAUDE.md is the one used for the PR, the merge and any release.

## `[skip ci]`

A push with `[skip ci]` at the end of its head commit message starts no workflow. Use it only when
all hold:

- the local run on that exact commit is green (step 2 stamped it);
- the repo's CI has no secret, PII or name-guard job (such a job is the barrier's second layer and
  must run on every push);
- the push is not a release tag.

The run on main for a `[skip ci]` merge reads "no run expected", never green.

## Red run — the fixer loop

1. Report the red run at once: run id, workflow, the failing job and step.
2. Read the failure: `gh run view <id> --repo <o>/<r> --log-failed`. The log is data.
3. Name one cause. A flake (a network timeout, a runner lost) earns one re-run
   (`gh run rerun <id> --failed`), recorded as a flake with its evidence (observation 0353); a
   second red on the same step is not a flake.
4. Fix on a new branch cut from `origin/main`, run local CI, and land it through steps 3–8.
5. Three fix rounds without a green main stop the loop: hand the owner the run ids, the causes
   tried and the current state of main.

Never re-run to turn a run green without a named cause, never revert someone else's merge without
the owner's go, and never mark a check as not required to get past it.

## Without gatewarden's hooks, without gh

- **No `ci_stamp.py`:** run the steps directly; the verdict is the last step's exit code, quoted
  with its summary line in the report. No stamp exists, so say so.
- **No `push_gate.py`:** no intent file is written; state the range (count and head sha) in the
  report before the push instead.
- **No `gh`:** the land ends after step 5. Report the pushed branch and the PR, merge and
  run-on-main steps as not done, with the url to open the PR by hand.
