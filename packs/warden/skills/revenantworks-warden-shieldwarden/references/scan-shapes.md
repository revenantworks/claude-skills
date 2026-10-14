# Scan shapes — the one home

Every rule `scripts/shield_scan.py` applies, what it looks for, and what keeps it quiet.
The regexes live in the script and nowhere else; this page describes them in words so no
tracked page carries a live shape. A caller that needs a new shape adds it here and in the
script in the same change, never in its own copy.

Every hit carries: `class`, `rule`, `where` (file, `history <commit>:<file>`,
`message <commit>` or `identity first seen <commit>`), `line` when known, and for a value
rule `fp` (sha256 of salt + lower-cased value, first 12 hex), `len`, and `domain` for an
email. The value itself never leaves the process, except into emit's filter-repo inputs.

## Personal data (class `pii`)

| Rule | Looks for | Quiet when |
|---|---|---|
| `user-folder` | A Windows or macOS user-folder path, either slash, single or doubled, with or without a drive letter; the account segment is the value | The segment is a placeholder (`<user>`, `user`, `owner`, `~`, `public`, `default`, and the rest of the built-in set, plus `placeholders` in config) |
| `user-folder-slug` | The same account segment inside a tool's project-folder slug (the path with its separators turned into dashes) | Same placeholder set |
| `home-folder` | A Unix home-folder path; the account segment is the value | Same placeholder set |
| `email-address` | Any mailbox-shaped address | A no-reply address, an RFC 2606 reserved domain or reserved TLD, the SSH transport form for a code host, URL userinfo after a real scheme, or a pattern in `email_allow` |
| `owner-name` | A name from the user's private names list, whole-word, any case | No list found: reported as `owner-name: NOT-RUN` with the setup command, never as clean |

## Commit identities (class `identity`, with `--identities`)

| Rule | Looks for | Quiet when |
|---|---|---|
| `author-email`, `committer-email` | An identity email that is not a no-reply address (the machine hook's rule) | Always reported once per distinct identity |
| `author-name`, `committer-name` | An identity name matching the names list | No list (the `owner-name` NOT-RUN line covers it) |
| `author-name-unlisted`, `committer-name-unlisted` | An identity name not on `allowed_identity_names` | That config list is absent or empty |

## Secrets (class `secret`)

Provider key shapes (Anthropic, OpenAI, GitHub classic, fine-grained and OAuth, AWS access
key, Slack, Google API key), a private-key block header, and a generic `key = value` shape
for api-key, secret-key and token names. The generic shape stays quiet on documentation
forms: angle-bracket placeholders, environment-variable references, `example`,
`placeholder`, `changeme`, runs of `x`, ellipses and `REDACTED`. A caller adds its own named
shapes with `secret_patterns`. With gitleaks installed, its findings arrive as
`gitleaks:<RuleID>` in the same class; gitleaks runs with redaction, so they carry no
fingerprint.

## Injection (class `injection`)

File classes decide which rules apply. **Instruction**: `SKILL.md`, `CLAUDE.md`,
`AGENTS.md`, `README.md`, Markdown under a `references` folder, `tasks/*.md`,
`.claude/agents` and `.claude/commands`, plus `instruction_globs`. **Control**:
`.claude/settings*.json`, `.claude/hooks/*`, `.mcp.json`. **Data**: everything else.

| Rule | Looks for | Applies to |
|---|---|---|
| `directive-in-data` | Text that addresses an agent: override-the-rules phrasing, role reassignment, secret-exfiltration requests, fake assistant turns | Data files, lines with no negation or reporting word |
| `tool-call-in-data` | Tool-call or chat-template markup | Data files, same negation rule |
| `invisible-unicode` | Zero-width, bidi-override, line/paragraph separator and tag characters (a byte-order mark at the very start is fine) | All text files |
| `mixed-script-token` | One word mixing Latin with Cyrillic or Greek letters (a homoglyph) | All text files |
| `html-comment-directive` | An HTML comment whose text is an imperative | Markdown and HTML |
| `encoded-blob` | A base64 or hex run of 200+ characters | Outside asset folders, key and lock files, and data URIs |
| `pipe-to-shell` | A download piped into a shell or interpreter, or PowerShell's expression evaluator | Instruction and control files, shell scripts |
| `eval-in-prompt` | A call to the eval or exec built-in | Instruction and control Markdown or JSON |
| `fetch-and-follow` | Wording that tells the reader to act on what a fetched page says | All text files, lines with no negation word |
| `posture-gap` | An instruction file that ingests untrusted content (a fetch tool, or a read verb beside an untrusted-source noun) and never says that content is data | Instruction Markdown |

## Permission and hook posture (class `posture`)

| Rule | Looks for |
|---|---|
| `settings-ask-rule` | A non-empty `permissions.ask` in a tracked settings file (an unattended run freezes on it) |
| `settings-wide-allow` | An allow rule granting a whole tool, a wildcard shell, a download or force-push command, or any-domain web fetch |
| `settings-bypass` | `bypassPermissions` as the default mode, or every project MCP server enabled at once |
| `hook-network` | A hook command or hook script that makes a network call or installs a package |
| `hook-outside-repo` | A hook command that reaches a path outside the repo (home-folder, drive-letter or profile variables) |
| `settings-hash-drift`, `hook-hash-drift` | A control file whose sha256 differs from `hashes` in config |
| `mcp-server-unlisted` | An `.mcp.json` server not on `mcp_allowlist` |
| `unparseable-control-file` | A settings or MCP file that is not valid JSON |

## Exposure (class `exposure`, Python and JavaScript/TypeScript files)

Secrets that are not in the code but would reach a log, a trace or a dump at run time. Hits carry
a line, never a value or a fingerprint; they are skipped with `--pii-only`.

| Rule | Looks for |
|---|---|
| `secret-in-log` | A print, console, logger or trace-attribute call whose argument uses a secret-named variable (key, secret, password, token, credential), read outside plain string text and inside f-string or template interpolation. Quiet when the argument shows a redacted use (`len(`, `bool(`, `is None`, a mask, a short prefix slice) |
| `object-dump` | A whole environment, config, credentials or request-headers object printed, logged or serialized (`os.environ`, `process.env`, `vars(config)`, `config.__dict__`, `request.headers`) |
| `secret-field-repr` | In a Python file with dataclasses, attrs, pydantic models or NamedTuples: a secret-named field whose default repr or dump would print it (no `repr=False`, `SecretStr`, `SecretBytes` or exclusion) |

The fix is in code: log a fingerprint or `set`/`missing`, wrap the value in a secret type, add
`repr=False`, or dump an allowlist of fields. A hit in a deliberate test stub is accepted through
`accepted` in config, never by weakening the shape.

## Control bytes (class `control-bytes`, Markdown, YAML and text files)

`bare-cr` (a CR not followed by LF), `control-char` (C0 controls other than tab, LF and CR;
DEL; C1 controls), `invalid-utf8`. A valid multi-byte character never counts.

## Files the tree pass does not read

A file the tree pass skips is listed, never dropped silently: `not_scanned` in the JSON
(`{file, reason}`), `counts.files_skipped`, and one `skipped <path> (<reason>)` line in the
text report. Reasons: `binary or media extension (<ext>)` for the extension list in the
engine's file classes, `binary content (NUL byte)` for a NUL in the first 8 KiB, and
`over size cap`. A skipped file is not a clean file: a caller that must vouch for media
(an image's metadata, a PDF's text) reviews the listed files by another route.

## Config keys (`--config`, one JSON object)

`placeholders`, `email_allow` (full-match regexes), `allowed_identity_names`,
`secret_patterns` (name to regex), `ingest_nouns`, `mcp_allowlist`, `hashes` (path to
sha256), `accepted` (list of `{file glob, rule}`; `*` matches every rule), `skip_dirs`,
`instruction_globs`. A config file may be tracked, so it holds no personal value: real
names go in the private names list (`~/.warden/wordlist.txt`, or `WARDEN_NAMES_FILE`; see
`private-files.md`), which the script refuses when it sits inside a git work tree.

## Seam for a scheduled sweep

The user's Sunday sweep calls this engine; it keeps no scanner of its own. Mapping from
the sweep's check ids to calls, one repo at a time:

| Sweep check | Call |
|---|---|
| PII-01 (names, user-folder paths, HEAD) | `scan <repo> --pii-only --salt-env <sweep salt var> --json --gitleaks off` (the names list resolves from the private folder; `--names-file` only for another location) |
| PII-02 (history and identities) | `scan <repo> --pii-only --history --identities --salt-env <sweep salt var> --json --gitleaks off` |
| SEC-01 (secrets) | the `secret` class of the PII-01 call, plus a gitleaks pass when installed (`--gitleaks auto`) |
| SEC-03, SEC-04, SEC-05 (injection, posture gaps, settings and hooks) | `scan <repo> --config <sweep policy json> --json`; the sweep builds the JSON from its baseline (accepted findings, permission and hook hashes, MCP allowlist, routine prompt globs, domain nouns) |
| MD-01 (control bytes) | the `control-bytes` class of the same call |

The sweep reads `counts`, `hits`, `accepted` and `not_run` from the JSON. Exit 3 is a
NOT-RUN row, never a green one. Fixes stay the sweep's tier rules; this engine only raises.
