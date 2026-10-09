# Contributing

Thanks for helping. This repo ships Agent Skills to the public, so one rule comes before
everything else: **no personal data reaches a commit.** No name, no personal or machine path,
no machine or account name, no email address, no secret.

## Set up a clone (once)

```bash
git clone https://github.com/revenantworks/claude-skills.git
cd claude-skills
git config core.hooksPath .githooks      # arms the PII pre-commit hook
python -m unittest discover -s tools -p "test_*.py"
python tools/build.py --check
```

`core.hooksPath` is stored in the clone's own config, so every `git worktree add` of that clone
runs the same hook. A fresh clone does not: run the `git config` line in each new clone.

Commit with your GitHub no-reply address (Settings, Emails, "Keep my email addresses private"):

```bash
git config user.email "<id>+<login>@users.noreply.github.com"
```

The hook blocks a commit whose author or committer email is not a no-reply address.

## The PII barrier

- **Pre-commit hook** (`.githooks/pre-commit`): runs `python tools/pii_scan.py --staged` on the
  added lines of the staged diff and blocks the commit on any hit. It fails closed: with no
  Python 3.9+ it blocks too.
- **CI** (`.github/workflows/pii-scan.yml`): runs `python tools/pii_scan.py --tree --identities`
  over every tracked file and every commit identity on each push to `main`.

Rules that always run: email addresses (no-reply and example domains pass), user and home folder
paths, drive-letter paths outside the system folders, secret shapes, the commit identity and,
locally, your own machine's host and login names. A private names list adds the name rule when
it exists on your machine (`WARDEN_NAMES_FILE`, else `~/.warden/wordlist.txt`; create it with
`python packs/warden/shared/scripts/warden_private.py setup names`). It is never committed.

A hit prints `path:line  rule  fp=<fingerprint>`, never the value. Fix the line and stage again.
**Never use `--no-verify`.** A test fixture that must hold a fake path or key is accepted by rule
and by one file in `.pii-scan.json`; use example values (`example.com`, `~/path/to/file`).

## Commits and checks

Follow the commit rule in `CLAUDE.md` (`<scope>: <imperative summary>`, a body that says why).
Before you push, run the tools suite and `python tools/build.py --check`; both must pass.
`RUNBOOK.md` covers releases.
