# Rotation runbooks

Read by `rotate` and `leak`. Every runbook has the same spine: **inventory → issue new → swap
every consumer → verify → revoke old → re-inventory.** The user issues and revokes; keywarden
lists, edits consumers on a yes, verifies through the wrapper and checks the old fingerprint is
gone. In a leak, revoking the old value is urgent: do it as soon as the new one works, or
before, if the value is public.

## GitHub personal access token

1. Inventory: `cred_inventory.py --stores files,env,gcm,gh` plus the user's list of routines,
   cloud environments and MCP servers that use it.
2. New: the user creates a fine-grained token at github.com → Settings → Developer settings →
   Personal access tokens, using `scope-recipes.md`.
3. Swap: gh → the user runs `gh auth login` (or `gh auth refresh`) in their terminal; GCM → the
   next push prompts; files → replace the literal with a reference (diff, yes per file); cloud
   environment → the user pastes it in the editor, one line.
4. Verify: `python scripts/preflight.py run -- gh api /user --jq .login` per consumer.
5. Revoke: the user deletes the old token on the same page. One command alternative for an
   OAuth app grant: none; it is a page.
6. Re-inventory: the old fingerprint must appear in no row.

## gh OAuth token (from `gh auth login`)

New and revoke in one step: the user runs `gh auth refresh -h github.com` (or
`gh auth logout` then `gh auth login`). Revoke stray grants at github.com → Settings →
Applications → Authorized OAuth Apps.

## API key (any vendor)

1. Inventory as above; note every `seen_at`.
2. New: the user creates a key in the vendor console with the smallest scope and an expiry.
3. Swap: `.env` → reference via `op run` or `bws run`, or a keyring; settings `env` block →
   remove it and inject per command; cloud environment → an API credential (Pro and Max) so the
   session never sees it.
4. Verify through `preflight.py run`.
5. Revoke the old key in the vendor console.
6. Re-inventory.

## SSH key

New: the user runs `ssh-keygen -t ed25519 -f <path>` (passphrase in their terminal) and adds
the public key to the account. Swap: `~/.ssh/config` `IdentityFile` per host. Verify:
`ssh -T git@github.com` (prints the account name, not a key). Revoke: delete the old public key
from the account, then the old private file. A private key never enters the transcript; only
the `.pub` file may be read.

## Routine or cloud environment credential

The credential's design (what the routine needs, where it is held) is agentwright's. keywarden
runs the swap: the user deletes and re-adds an API credential (they cannot be edited or viewed
after saving), or replaces the variable on one line. Next fire verifies; read its log for a
masked failure.

## Windows Credential Manager entry

Swap and revoke by target name: the user runs `cmdkey /delete:<target>` after the new value
is stored by the tool that owns it (GCM re-prompts on the next push). keywarden never adds a
value with `/pass:` on a command line: that prints into history.

## After every rotation

Record: what was rotated (class and fingerprint), how many consumers, the date, and anything
still NOT-RUN. Never the value, never the account name.
