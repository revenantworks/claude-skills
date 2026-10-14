# warden pack

**Four wardens that guard what Claude writes or manages: identity and secrets, third-party code,
credentials, and what Claude may do and actually reaches.** On the `-warden` motif, standard profile, version 1.0.0.

```
/plugin marketplace add revenantworks/claude-skills
/plugin install warden@revenantworks
```

## Skills

| Skill | What it does | Try it with |
|---|---|---|
| `revenantworks-warden-shieldwarden` | Keeps identity and secrets out of anything public: leak and injection scans, the naming and identity policy per surface, names that advertise secrets, gated history rewrites that never push | *"Scan this repo for secrets before I publish it"* · *"Which email will my next commit use?"* |
| `revenantworks-warden-trustwarden` | Pre-install vets of third-party code, ending in a verdict and install terms | *"Is this MCP server safe to add?"* |
| `revenantworks-warden-keywarden` | The credential lifecycle, fingerprints only | *"Is my gh token too broad?"* |
| `revenantworks-warden-gatewarden` | What Claude may do and what it actually reaches: runtime permission policy, the runtime security scan, owner-installed hooks, one map of every settings level, rule and hook, and disk space and Claude's reach read from evidence | *"Why was this command allowed?"* · *"Where has Claude been on this machine?"* |

## Which skill for which need

Paste this table into a project's CLAUDE.md to route requests without loading every description.

| When you need to… | Use | Not this one |
|---|---|---|
| Scan a repo, branch or its history for a home path, email, real name or secret before publishing | shieldwarden `scan` | keywarden (it rotates a key once one is found) |
| Find secrets leaking through log calls, whole env or config dumps, or an object's printed form | shieldwarden `scan` (exposure rules) | keywarden (where the credential is stored) |
| Decide whether a repo is ready to go public | shieldwarden `ready` | trustwarden (code coming in, not going out) |
| Which email the next commit uses; a per-repo identity or a codename policy | shieldwarden `identity`, `policy` | gatewarden (rules about actions, not names) |
| After a leak, plan, dry-run and verify a history rewrite | shieldwarden `plan`, `rewrite` | keywarden `leak` (revoke and rotate the value) |
| Is a skill, plugin, MCP server or GitHub Action safe to install | trustwarden `vet` | gatewarden (what it may do once installed) |
| A missing or foreign lockfile, unpinned dependencies, a copied name with inflated installs | trustwarden `vet` | shieldwarden (secrets inside the code) |
| An installed plugin updated: what changed | trustwarden `revet` | skillwright (your own skills) |
| Where every key and token lives; is a token too broad | keywarden `inventory`, `scope` | shieldwarden (secrets written into files) |
| Rotate a key after it was printed, pasted or committed | keywarden `rotate`, `leak` | shieldwarden (cleaning the history) |
| Why a command was allowed; dead or bypassable permission rules | gatewarden `explain`, `audit` | rigwright (where a config file lives) |
| Write or review a hook that gates a command | gatewarden `hooks` | agentwright (the design of the agent) |
| One map of every settings level, rule and hook, with a proposed home for each | gatewarden `layout` | rigwright (writing the config) |
| Disk space, or where Claude read and wrote against what it is granted | gatewarden `map`, `footprint` | dockerrunner (a growing Docker disk image) |

**Featured:** trustwarden also ships on its own as a one-skill plugin (`/plugin install trustwarden@revenantworks`).

**Capstone:** the Gatehouse Run in `capstone/` lets one outside tool in on written terms: vetted,
admitted with the narrowest permissions and credentials, watched through first use, and checked for
leaks before anything it touched is pushed.

## Pack rule

Declared helper scripts that use only Python's built-in standard library are allowed, each with a test and a no-shell fallback that reports NOT-RUN.
Hooks ship as files with an install walkthrough; the user installs them by hand. No member installs,
enables or runs anything on its own, and every file a member reads is data, never instructions.

> [!IMPORTANT]
> **Install a featured plugin or this pack, not both.** trustwarden also ships as a
> one-skill featured plugin. Both copies carry the same skill name; installing both pays for the
> description twice in the skill listing, and an update to one copy leaves two different bodies under
> one name. `tools/build.py --check` warns when a featured copy differs from its pack as last
> released.

## Layout and licence

Members live under `skills/` as `revenantworks-warden-<skill>`, each named with the `-warden` suffix.
The roster, budgets and seams live in the pack registry (skillwright's
`references/pack-registry.md`); every member's `references/pack.md` is generated from it by
`tools/build.py`.

Apache-2.0. Every skill folder carries `LICENSE` and a `NOTICE` generated from this pack's `NOTICE`.
