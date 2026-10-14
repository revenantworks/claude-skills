# Private files — the user's lists stay on the user's machine

A skill package carries nothing user-specific: no paths, no names, no terms, no hashes. A
user's private lists live in one per-user folder **outside every repo**, the same on Windows,
macOS and Linux. Nothing in it is uploaded, committed or pasted into a chat.

| File | Default path | Variable | Read by |
|---|---|---|---|
| Names list | `~/.warden/wordlist.txt` (Windows: `%USERPROFILE%\.warden\wordlist.txt`) | `WARDEN_NAMES_FILE` | shieldwarden (`owner-name`, identity names, rewrite inputs); a repo's own name-leak check |
| Identity values | `~/.warden/aliases.txt` | `WARDEN_IDENTITY_VALUES_FILE` | shieldwarden (`check`, `lint`, `identity`) |
| Signpost words | `~/.warden/glossary.txt` | `WARDEN_SIGNPOST_WORDS` | shieldwarden (`signposts`; set up with `signposts.py --template`, `references/signposts.md`) |

keywarden writes no inventory file: its fingerprints go to stdout and the report only, so it
needs no private file.

## Resolution order (every script)

1. The explicit flag (`--names-file`, `--values`, a repo tool's `--list`).
2. The variable for that file.
3. The default path, when it exists.
4. None: the check reports **NOT-RUN** with the setup command. It never passes silently.

A file named by the flag or the variable that is missing is refused, not skipped. A file inside
a git work tree is refused, whichever way it was named. Output names a hit by rule, place and a
masked form or fingerprint, never by the entry.

## Setup (first need)

1. Run `python scripts/warden_private.py where`. It prints each file's source and entry count,
   never an entry. A file that resolves needs nothing more.
2. Missing: recommend the default path and hand the user one command, which creates the folder
   and a template holding comment lines only (it never overwrites):
   - names list: `python scripts/warden_private.py setup names`
   - identity values: `python scripts/warden_private.py setup identity-values`
3. The user opens the file in their own editor and adds the entries. Entries never pass through
   the chat; do not offer to type them in.
4. Another location instead: `python scripts/warden_private.py setup names --path <file>`
   creates the template there and prints the one command that sets the variable (PowerShell on
   Windows, `~/.profile` elsewhere). The location must be outside every repo.

## File formats

- **Names list** — one entry per line; `#` lines and blanks are ignored. `Name` matches the
  whole word and a rewrite replaces it with "the user"; `Name==>replacement` sets the
  replacement; `sub:term` asks a name-leak check for a substring match (shieldwarden reads the
  term and matches whole words).
- **Identity values** — `class:label = value` per line; every key must be listed in the
  policy's `values_keys` (`references/policy-format.md` in shieldwarden).

## An old file inside a repo

An identity values file left in a repo folder (the earlier gitignored layout) is **not used**.
`identity_check.py lint` reports `values-file-in-repo` with one command that moves it:
`python scripts/warden_private.py adopt identity-values <old file>`. It refuses when the default
already exists. Afterwards delete the `.gitignore` line and the policy's `values_file` field.
