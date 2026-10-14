# Install walkthrough — the scanners, installed by the user

**trustwarden installs nothing.** Every step below is the user's to run, one at a time, with a
check after it and a way back. Each scanner is optional: without it, the vet reports NOT-RUN for
that reader and the verdict rests on the readers that ran. Package names and flags were read on
2026-10-01 (`scanner-matrix.md` holds the stamp); re-read a tool's own install page before
running a step, because install commands change.

Recommended set: skillspector (often already present), zizmor and pinact. Scorecard only when a
candidate's provenance is in doubt, through its Docker image. snyk agent-scan stays opt-in.

## Contents

1. skillspector
2. zizmor
3. pinact
4. OpenSSF Scorecard (Docker, on demand)
5. cisco skill-scanner (optional second opinion)
6. snyk agent-scan (opt-in only)

## 1. skillspector

- **Install:** `uv tool install git+https://github.com/NVIDIA/skillspector.git` — pin it to a tag
  or commit with `@<ref>` after the URL; the vet of a vetting tool starts with its own pin.
- **Check:** `skillspector --help` prints the `scan` command.
- **Way back:** `uv tool uninstall skillspector`.
- **Use:** `--no-llm` always; scan a checkout, never an installed link.

## 2. zizmor

- **Install:** from the tool's own install page (PyPI, cargo or Homebrew packages are listed
  there), pinned to a version, for example `uv tool install zizmor==<version>`.
- **Check:** `zizmor --version`, then `zizmor --offline --format json <a clone with workflows>`
  returns 0 or 11–14.
- **Way back:** the same package manager's uninstall (`uv tool uninstall zizmor`).

## 3. pinact

- **Install:** a release binary from the project's GitHub releases page (verify its checksum
  against the release's checksum file), or `go install`, Homebrew, aqua, winget or scoop as its
  README lists. Pin a version.
- **Check:** `pinact --version`; inside a scratch clone, `pinact run --check --no-api`.
- **Way back:** delete the binary, or the package manager's uninstall.
- **Note:** resolving tags to SHAs for a term needs the GitHub API; a token avoids rate limits and
  comes from the environment (keywarden), never typed into a command.

## 4. OpenSSF Scorecard (Docker, on demand)

- **Prerequisite:** Docker running (dockerrunner owns Docker itself).
- **Run, not install:** `docker run -e GITHUB_AUTH_TOKEN ghcr.io/ossf/scorecard:v5.5.0 --format=json --repo=<url>`
  — the token is passed from the environment by name only; never write its value on the line.
- **Check:** JSON with a score per check.
- **Way back:** `docker image rm ghcr.io/ossf/scorecard:v5.5.0` (the user runs it).

## 5. cisco skill-scanner (optional second opinion)

- **Install:** `pip install cisco-ai-skill-scanner==<version>` into a virtual environment, or
  `uv tool install cisco-ai-skill-scanner`.
- **Use:** static analyzers only. Its LLM, meta and VirusTotal analyzers need keys and send
  content off the machine; they stay off unless the user says yes for one candidate.
- **Way back:** remove the virtual environment, or `uv tool uninstall cisco-ai-skill-scanner`.

## 6. snyk agent-scan (opt-in only)

State this warning before the user decides: it needs a Snyk token, its scans go to Snyk's API,
and it **starts stdio MCP servers** to read their tool descriptions, which are data, not instructions. Never use it on the
untrusted server under vet, and never with `--dangerously-run-mcp-servers`. If the user still
wants it: `uvx snyk-agent-scan@<version>` (0.6.8 as of the matrix's Last-verified stamp) runs it without a lasting install. Way back: nothing
persists beyond the `uv` cache (`uv cache clean snyk-agent-scan`).
