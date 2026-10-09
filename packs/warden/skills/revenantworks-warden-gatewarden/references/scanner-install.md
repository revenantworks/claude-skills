# Install walkthrough — optional scanners, owner-run

gatewarden installs nothing. Both tools below are optional: without them, `scan_tree.py` does the job, more slowly on a whole drive. Before installing either, the owner may vet it (trustwarden, where installed): what the installer writes, its licence, its source.

Each step: what the owner runs, how to verify it, how to roll it back.

## WizTree (Windows)

1. **Get it** from the vendor's own site (diskanalyzer.com). The portable zip writes nothing outside its folder; the installer adds a Start-menu entry and an uninstaller. Read the EULA for the use you have in mind.
   - Verify: `WizTree64.exe /?` opens the help, or the app starts.
   - Roll back: delete the portable folder, or uninstall from Settings → Apps.
2. **Test a non-elevated export** on a small folder: `WizTree64.exe "<folder>" /export="<output folder>\test.csv" /admin=0`.
   - Verify: the CSV exists and its first lines include a `File Name` header.
   - Roll back: delete the CSV.

## dust (Windows, macOS, Linux)

1. **Get it** from the project's GitHub releases (bootandy/dust) or a package manager the owner already uses (`winget`, `scoop`, `brew`, `cargo`). The Windows MSVC build needs the Visual C++ runtime.
   - Verify: `dust --version`.
   - Roll back: the same package manager's uninstall, or delete the binary.
2. **Test JSON output**: `dust -j -d 2 "<folder>" > test.json`.
   - Verify: the file parses as JSON and holds a `children` list.
   - Roll back: delete the file.

## Python

The scripts need Python 3.9 or newer and nothing else. `python --version` verifies it. On Python 3.12+ junction detection uses `Path.is_junction()`; older versions read the reparse-point attribute, with the same result.
