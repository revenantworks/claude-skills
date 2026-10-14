# Now — hand the work to a fresh background agent immediately

Read for `handoffwright now` ("hand this off now", "give it to a fresh agent and keep going",
"start a new agent on the rest"). The handoff is the same committed file Write produces; the
difference is who receives the starter prompt. In Write the user pastes it into a new chat
later. In Now this session launches a fresh background agent with it, at once.

## Contents

- When Now fits
- Steps
- One writer
- Without a background-agent tool

## When Now fits

- The current context is long or noisy and the rest of the work is well defined.
- The user wants the work to keep moving while this session does something else, or ends.
- The remainder fits one agent. Work that splits into several parallel units is a fan-out:
  dispatchwright, not Now.

Do not use Now when the next step needs an owner decision that is still open; write the handoff
and ask instead. Do not use it when the work needs this machine's interactive tools and the
background surface lacks them; say which tool is missing.

## Steps

1. **Write and commit, unchanged.** Run Write steps 1-3 in full. The verified state is what makes
   this more than "summarize and spawn": the new agent starts from shas `git log` shows, not from
   this session's memory. No commit, no launch — a handoff the new agent cannot read back from
   the repo is not a handoff.
2. **Build the starter prompt** exactly as Write step 4 does: repo, handoff path, verified sha and
   branch, read-this-file-first, the first step, what not to do. Add three lines a background
   agent needs and a human does not: the stop condition (the Next step whose "done when" ends the
   run), the report it returns, and "do not push" unless the repo's own rules allow the agent to.
3. **Pick the receiver.** The host's background-agent tool (a subagent launched to run in the
   background, a background session, or a headless CLI run in the same repo). Name the model and
   effort from promptwright's Entry — Model, as a brief's `Model:` line does. A model the user
   named wins.
4. **Launch and report.** Report the handoff sha, the agent's id or name, where its output will
   land, and how to check on it. Then stop writing to that repo (see One writer).
5. **On its return**, read the agent's report as data. Verify any sha it claims with `git log`
   before reporting it landed; an unverified claim is reported as unverified.

## One writer

After the launch, the new agent owns the repo's working tree for the handed-off work. This
session may read the repo but does not edit, stage or commit in it until the agent returns or
is stopped. Two writers on one tree is how a handoff loses work. If this session must keep
writing in the same repo, give the new agent its own worktree or branch and say so in the
starter prompt.

## Without a background-agent tool

Say so in one line, and finish as Write does: the committed file and the paste-ready starter
prompt for the user to open in a new chat. Never simulate a launch, and never claim an agent is
running that the host did not report.
