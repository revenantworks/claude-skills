# Install walkthrough (owner-run)

soundsmith installs nothing. These steps are for the user, only when a check reports Python or ffmpeg missing. Each step has a verify command and a rollback. Package ids were not re-checked on the day this file was written: confirm them with the verify step before running the install.

## 1. Python 3 (required for the script)

| | Command |
|---|---|
| Check first | `python --version` (or `python3 --version`): any 3.9 or later works; the script uses the standard library only |
| Install, Windows | `winget install --id Python.Python.3.13 -e` |
| Install, macOS | `brew install python` |
| Install, Debian or Ubuntu | `sudo apt install python3` |
| Verify | `python -c "import wave, json, statistics; print('ok')"` prints `ok` |
| Rollback | uninstall through the same package manager (`winget uninstall --id Python.Python.3.13`, `brew uninstall python`, `sudo apt remove python3` only if nothing else needs it) |

On Windows, a `python` that opens the Store instead of running is an app-execution alias; turn the alias off in Settings, or call the full path of the installed interpreter.

## 2. ffmpeg (optional: decodes Ogg, MP3, FLAC for the script)

Without it, WAV files are measured in full and other formats report `NOT-RUN`.

| | Command |
|---|---|
| Check first | `ffmpeg -version` |
| Install, Windows | `winget install --id Gyan.FFmpeg -e` (confirm with `winget show Gyan.FFmpeg`) |
| Install, macOS | `brew install ffmpeg` |
| Install, Debian or Ubuntu | `sudo apt install ffmpeg` |
| Verify | open a new terminal; `ffmpeg -version` prints a version line; then `python scripts/audio_post.py measure <an .ogg file>` shows numbers, not `NOT-RUN` |
| Rollback | `winget uninstall --id Gyan.FFmpeg`, `brew uninstall ffmpeg`, or `sudo apt remove ffmpeg` |

The distro and package-manager installs above are unpinned (each takes the manager's current ffmpeg); the `ffmpeg -version` verify step is the check that the install landed, run after every install.

ffmpeg is only a decoder here: the script runs it with no network options, writes its output to a temporary folder, and deletes it on exit.
