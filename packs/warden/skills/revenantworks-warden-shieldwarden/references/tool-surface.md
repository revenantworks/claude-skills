# Tool surface

Last verified: 2026-09-28

The external tools this skill calls and the flags that can move between releases. Checked by
`refresh` every 90 days. Every tool here is optional except git and Python 3, and each has a
fallback that reports NOT-RUN rather than reading as clean.

| Tool | Used for | Flags relied on | Absent or too old |
|---|---|---|---|
| git | tree listing, history, identities, bundle, clone | `ls-files -z`, `log --all -p --unified=0 --no-renames`, `log --format` with `%x00`, `branch -r --contains`, `bundle create --all`, `bundle verify`, `clone --no-local` | The script exits 3 (NOT-RUN) and the report says so |
| Python 3.9+ | `scripts/shield_scan.py` | stdlib only | Every script row is NOT-RUN; the cloud review still runs |
| git filter-repo | the rewrite | `--replace-text`, `--replace-message`, `--mailmap`, `--refs <range>`, `--invert-paths --path`; `--sensitive-data-removal` in newer releases | No rewrite; `plan` still runs; the user installs it or the run stops at gate 2 |
| gitleaks | a second secret pass | v8.19 and later: `gitleaks git` and `gitleaks dir`; older: `gitleaks detect --source` and `--no-git`; both with `--redact --report-format json --report-path --exit-code 0` | `gitleaks: NOT-RUN` in `not_run`; exit code unchanged |
| gh | read-only checks (repo visibility, default branch, secret-scanning status) | `gh repo view --json` | Say so; ask the user, or use the GitHub MCP read tools |

## Notes to re-check on refresh

- Does the installed filter-repo list `--sensitive-data-removal` in `git filter-repo --help`?
  The GitHub removal guide recommends it where available.
- Has gitleaks renamed or retired the `detect` and `protect` commands? The script tries the
  new command first and falls back to the old one.
- Has the GitHub removal guide changed what the user must ask support to purge?
- Has any scanner in the parity register (SOURCES.md) added a personal-data mode that would
  shrink this skill's margin?
