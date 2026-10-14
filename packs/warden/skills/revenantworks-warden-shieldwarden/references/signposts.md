# Signposts — names that advertise sensitive data, and who can open them

A folder called `passwords` or a file called `bank statements 2025.pdf` tells anyone on the machine where to look. `signposts.py` finds those names, reads who can open each one, and proposes a fix. It reads **names and metadata only**: it never opens a file, and it never renames, moves or re-permits anything.

## Run — the steps of `shieldwarden signposts`

Moved from the SKILL.md body when the signposts scan joined shieldwarden (2026-10-08); unchanged.

1. **Private list (optional).** The shipped word list always runs. If the user wants extra words or
   accepted paths, check `~/.warden/glossary.txt` (or `WARDEN_SIGNPOST_WORDS`); if missing, offer
   the one setup command below. The user fills the file in their own editor; its words never pass
   through the chat and the report names them only as "private list #N". A list inside a git work
   tree is refused.
2. **Scan** with `python scripts/signposts.py <path> --json <out>` (`--depth 8` by default). It
   never follows a link, skips git internals and package caches, and caps depth, entries and time;
   everything skipped lands in `not_scanned`. `--template` prints an empty private list. Exit 0
   clean, 1 hits (or a partial scan), 2 input error. Output goes to the scratchpad or a folder the
   owner names.
3. **Read access** from the JSON: owner, access rows (account, rights, inherited), broad grants
   (Everyone, Users, a share; POSIX group or world bits), and whether the path is synced or exposed.
4. **Report** per "The report" below; a partial scan is reported as partial.
5. **Propose**, one command each, never run (see "Suggestions"). An app-owned name (`id_rsa`, a file
   under a dot-folder or AppData) gets no rename or move: that would break the program that reads it.

Without a shell: hand over the command, read back the JSON the user pastes, and mark every figure
not seen in it NOT-RUN.

## The word list

Matching is case-insensitive and whole-word. A name is split at separators, at camelCase and at letter/digit boundaries, so `MyPasswords2024.txt` and `2FA-backup-codes.txt` match and `syntax.txt` does not match `tax`. A phrase matches consecutive words (`PrivateKey.pem` → "private key"). The longest match is reported.

| Class | Words (shipped) |
|---|---|
| strong — a credential, key or identity document | secret, secrets, top secret, password(s), passwd, credential(s), creds, keys, private key, id rsa, wallet, seed, recovery, 2fa, mfa, backup codes, ssn, passport |
| general — a sensitive area | private, confidential, classified, sensitive, restricted, login(s), tax, bank, finance |
| private — the user's own list | anything the user adds; reported as "private list #N", never by the word |

## The user's private list (optional)

The shipped list always runs. Extra words and accepted paths live in one plain-text file on the user's machine, never in the skill package and never in a repo. Resolution order: `--words FILE` > the `WARDEN_SIGNPOST_WORDS` environment variable > `~/.warden/glossary.txt` (Windows: `%USERPROFILE%\.warden\glossary.txt`) if it exists > the shipped list alone. A list inside a git work tree is refused (exit 2).

Setup, on the user's yes, as one command; the user fills the file in their own editor, so entries never pass through the chat:

- PowerShell: `New-Item -ItemType Directory -Force "$HOME\.warden" | Out-Null; if (-not (Test-Path "$HOME\.warden\glossary.txt")) { python "<skill>\scripts\signposts.py" --template | Set-Content -Encoding utf8 "$HOME\.warden\glossary.txt" }`
- Bash: `mkdir -p ~/.warden && { [ -e ~/.warden/glossary.txt ] || python3 "<skill>/scripts/signposts.py" --template > ~/.warden/glossary.txt; }`
- Another location: `$env:WARDEN_SIGNPOST_WORDS = "<file>"` (PowerShell) or `export WARDEN_SIGNPOST_WORDS="<file>"` (Bash).

File format: one word or phrase per line; `# ...` is a comment; `accept: <path>` marks a known-false hit and everything under it as accepted (counted, not listed).

## What it skips and caps

- Junctions and symlinks: never followed. A link whose own name matches is a hit of kind `link`; its access is its target's, so it is not read.
- Git and VCS internals (`.git`, `.hg`, `.svn`), package and build caches (`node_modules`, `.venv`, `site-packages`, `__pycache__`, `.npm`, `.gradle`, `.cache` and the like), and system folders.
- Caps: `--depth 8`, `--max-entries 200000`, `--max-seconds 300`, `--max-access 500` (hits past it get no access lookup). A cap reached makes the scan **partial**.
- Every skipped or capped folder goes in `not_scanned` (counts by reason, the first 100 listed). Report it; never call a partial scan clean.

## Who has access

| Platform | Read with | Broad when |
|---|---|---|
| Windows | `icacls <path>` per hit (no window), the user through the Win32 security API, `net share` once | a non-deny grant to Everyone, Users, Authenticated Users, Guests, Anonymous or Network, or the path sits in a non-administrative share |
| macOS, Linux | `stat` mode bits, owner and group | group-readable or -writable; world-readable or -writable (world ranks higher) |

Each access row reads account, rights (full, modify, read+execute, read, write), inherited or not. Account names are redacted like paths: the user name reads `<user>`, the machine name `<host>`. icacls prints localized account names on a non-English Windows; a name it cannot match reads as not broad, so say the check is English-name and SID based.

## Location

- **Synced:** under OneDrive (including the `OneDrive` environment roots), Dropbox, Google Drive, iCloud Drive, pCloud or MEGA.
- **Exposed:** under the home Desktop, Downloads or Public folder, or the Windows `Users\Public` folder.
- **App-owned:** a name a program reads exactly (`id_rsa`, `credentials`, `.netrc`, `wallet.dat`, ...) or a path under a dot-folder, AppData, Library or Program Files. Renaming or moving these breaks the program, so only lock-down and encrypt are proposed.

## Risk and order

Score: broad grant to everyone or the world +4 (group only +2), synced or network-shared +2, exposed folder +1, a strong or private word +1. **high** ≥ 4 · **medium** 2-3 · **low** 0-1. Hits are sorted by score, so broad access plus a signpost name comes first.

## Suggestions — proposals, each one command, never run

| Action | When | PowerShell | Bash |
|---|---|---|---|
| lock down | any broad grant | preview `icacls "<p>"`, then `icacls "<p>" /inheritance:r /grant:r "$($env:USERNAME):F" "*S-1-5-18:F"` (folders: `(OI)(CI)F`; SYSTEM kept so backup works) | preview `ls -ld -- "<p>"`, then `chmod 600` (file) or `chmod 700` (folder) |
| move | synced, exposed or shared, not app-owned | `New-Item ... "$HOME\local-files"; Move-Item -LiteralPath "<p>" -Destination "$HOME\local-files" -Confirm` | `mkdir -p "$HOME/local-files" && mv -i -- "<p>" "$HOME/local-files/"` |
| rename | not app-owned | `Rename-Item -LiteralPath "<p>" -NewName "<neutral>" -Confirm` | `mv -i -- "<p>" "<dir>/<neutral>"` |
| encrypt | a strong word | `manage-bde -status <drive>` (administrator shell; read-only) | `fdesetup status` (macOS) or `lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS` (Linux) |

The neutral name drops the signpost words (`Bank Statements` → `Statements`); when nothing neutral is left it becomes `file-<6 hex>` or `folder-<6 hex>`, keeping the extension. Real secrets belong in a password manager: say so with the encrypt row. A command whose path holds a `<user>` or `<redacted>` placeholder carries `edit_needed`; tell the user to put the real path in on their own machine.

## The report

Lead with the counts (hits, high/medium/low, accepted, entries scanned), then the table — risk, path, matched word, kind, owner, broad grants, synced?, first suggestion — then each high hit's full suggestion list, then the not-scanned summary. Paths are redacted (`~`). Nothing is written except the JSON in the output folder and any report the user asks for. Hand an ACL change on a protected path (settings, credentials, `.ssh`) over as a proposal like any other; a secret **inside** a file is `scan`'s job, never this one's.
