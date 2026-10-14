# Run ledger (2026-10-01 to 2026-10-05)

| Row | Class | Model | Tokens | Check | Result |
|---|---|---|---|---|---|
| R-11 | mechanical | model-beta-2 | 42000 | `python tools/build.py --check` exit 0 | landed |
| R-12 | mechanical | model-beta-2 | 38000 | docs link check passes | landed |
| R-13 | mechanical | model-beta-2 | 51000 | `python -m unittest` 233 tests green | landed |
| R-14 | build | model-beta-2 | 160000 | feature tests green | landed |
| R-15 | long-report | model-alpha-2 | 90000 | report has every section, output 40k tokens | landed |
