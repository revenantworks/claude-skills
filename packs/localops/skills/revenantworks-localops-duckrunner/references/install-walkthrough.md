# Install walkthrough (owner-run)

duckrunner installs nothing. These are the user's steps, one at a time, each with the command
that proves it worked and the way back. Read this file when the engine, the yaml extension or
PyYAML is missing, or when the user asks how to set duckrunner up. The version to install is
the pin in `readers.md`; the commands below show it as `<pin>` (for example `1.5`).

No step needs an administrator account. Run them in an ordinary terminal.

## 1. Python

Check: `python --version` shows 3.9 or newer. On Linux or macOS the command may be `python3`.
Nothing to install or roll back if it does; otherwise install Python from python.org first.

## 2. The DuckDB engine (required for `ask` and `cache`)

Install, user scope, inside the pin:

    python -m pip install --user "duckdb==<pin>.*"

Verify: `python -c "import duckdb; print(duckdb.__version__)"` prints a version that starts
with `<pin>.`.

Roll back: `python -m pip uninstall duckdb`.

The DuckDB command-line program is not needed by this skill. If the user wants it for their own
use: `winget install DuckDB.cli` (whether the winget package installs per user or per machine
was not verified on 2026-09-28), verified with `duckdb --version`, rolled back with
`winget uninstall DuckDB.cli`.

## 3. The yaml community extension (the first YAML path)

This runs third-party code inside DuckDB. Review it first: the extension's page in the
community-extensions repository names its source repository and version (`readers.md` has the
current one). Where the warden pack's trustwarden is installed, run its review before this step.

Install and load once:

    python -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL yaml FROM community'); c.execute('LOAD yaml'); print(c.execute(\"SELECT extension_name, extension_version, installed, loaded FROM duckdb_extensions() WHERE extension_name = 'yaml'\").fetchall())"

Verify: the printed row shows `installed` and `loaded` as `True`.

Roll back: delete the extension file. It sits in the user's home folder, at
`.duckdb/extensions/<duckdb version>/<platform>/yaml.duckdb_extension`. That delete is the
owner's one command; duckrunner never runs it.

## 4. PyYAML (the fallback YAML path, and YAML manifests)

    python -m pip install --user pyyaml

Verify: `python -c "import yaml; print(yaml.__version__)"`.

Roll back: `python -m pip uninstall pyyaml`.

## 5. Prove the whole set

Run the skill's own tests from the skill folder:

    python -m unittest discover -s scripts -p "test_*.py"

Verify: `OK`, and with steps 2 and 4 done, no test is reported as skipped. A skipped test names
the missing piece.

Then score a real repo without changing it:

    python scripts/duck_run.py check --repo <repo> --pin <pin>

Verify: the `engine` rule shows the DuckDB version, `yaml_extension: true` after step 3, and
`pyyaml: true` after step 4.

## 6. Before upgrading DuckDB past the pin

Do not upgrade until the yaml extension has a build for the new version (`readers.md`,
"Versions and the pin"). Upgrading early leaves only the PyYAML fallback, and every YAML answer
then says so. When the build exists: upgrade with step 2's command at the new pin, re-run step 3
to fetch the matching extension, re-run step 5, then move the pin in `readers.md`.
