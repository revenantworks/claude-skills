# Least privilege — reached against granted

The footprint compares two sets of path roots. **Reached**: every path a tool call touched in the window, from transcripts. **Granted**: every root a standing setting opens (evidence-sources.md, "Settings that grant reach"). The comparison is evidence for a decision; changing a rule is gatewarden's job.

## Grouping

`footprint.py --depth N` groups reached paths by their first N segments (default 3: a drive and two folders, or `~` and two folders). Raise it to see inside a busy root; lower it for a one-screen summary. A path is **granted** when it sits under any granted root, compared case-insensitively on Windows.

## The four readings

| Reading | Meaning | What to propose |
|---|---|---|
| Reached and granted | Normal work | Nothing |
| **Reached, not granted** | Claude touched it with no standing grant: a one-off approval, a shell command, or a path outside every project | Ask whether it was expected. Repeated, expected reach → a narrow grant (gatewarden writes it). Unexpected reach, especially writes → a deny rule (gatewarden) and a shieldwarden scan of what was written |
| **Granted, never reached** | An added directory or allow rule no session in the window used | A least-privilege candidate: propose removing it (gatewarden). Say how long the window was; a 7-day window proves less than 30 |
| Shell reach | Paths lifted from Bash or PowerShell commands | Weaker evidence: a path in a command may be an argument that was never opened. Report separately; never call it a write |

Score the footprint in one line: roots reached, the share reached under a grant, the count of reached-not-granted roots with writes, and the count of unused grants.

## Rules of judgement

- **Writes outrank reads.** A write outside every grant is the top finding. A read outside every grant is the second.
- **The working folder and the scratchpad are always granted.** Their reach is never a finding.
- **Claude's own folders are normal reach.** Reads under `~/.claude` (memory, skills, settings) are expected; writes there to settings, hooks or skills are worth naming.
- **Protected roots stay.** A grant to a folder the owner keeps for a standing job (a notes vault, a shared drive) is reported unused, never proposed for removal without the owner's word on why it exists.

## What the evidence cannot show

- **Refusals.** A denied call is not a reached path. Transcripts show what Claude did, not what it tried.
- **Reach before the retention cutoff.** Older transcripts are deleted (default 30 days).
- **Reach through another program.** A script Claude ran may read anything; the transcript holds only the command line.
- **Other machines and cloud sessions.** A cloud session's transcript lives in its own environment.

State these limits in every footprint report. A clean footprint means "no evidence of reach", not "no reach".

## Iterate

An audit-log hook installed in advance (a PostToolUse logger) adds refusals and exact timings. gatewarden reads such a log as a second evidence source when the owner points at it; it never installs one.
