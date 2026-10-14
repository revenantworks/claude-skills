## What changed

<!-- One or two sentences. -->

## Why

<!-- The problem this solves. -->

## Checks

- [ ] `python -m unittest discover -s tools -p "test_*.py"` passes
- [ ] `python tools/warden_suites.py` passes
- [ ] `python tools/build.py --check` is clean
- [ ] `python tools/pii_scan.py --staged` found no hits, and I did not use `--no-verify`
- [ ] No personal data: no name, path, email, employer, client, or key
- [ ] I updated the docs if behavior changed
- [ ] I read `CONTRIBUTING.md`
