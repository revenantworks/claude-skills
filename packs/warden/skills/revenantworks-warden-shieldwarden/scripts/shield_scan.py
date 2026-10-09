#!/usr/bin/env python3
"""shieldwarden's scan engine: personal data, secrets and agent-attack shapes.

One engine. Every shape shieldwarden checks lives in this file, and nowhere else:
user-folder paths, emails, owner-supplied names, commit identities, secret shapes,
prompt-injection shapes, permission and hook posture, and control bytes. Callers
(the skill's own procedure, a scheduled sweep) pass their local policy in through
--config and --names-file; they never copy a regex. The names list defaults to the
warden private folder (WARDEN_NAMES_FILE, else ~/.warden/wordlist.txt; see
warden_private.py); with none, the user-name rule is reported NOT-RUN.

Modes
  scan    report hits in a git work tree (tracked files) or any folder (--dir),
          plus, on request, the full history (--history) and every commit
          identity (--identities). Optional gitleaks pass; it skips cleanly.
  emit    write git filter-repo inputs (replace-text, replace-message, mailmap)
          into a folder OUTSIDE every git work tree. Prints paths and counts only.
  verify  the post-rewrite gate: history + identities + tree, personal-data and
          secret classes only, plus `git bundle verify` of the backup when given.

Rules of the engine
  * Read-only on the target. It never commits, never rewrites, never pushes.
  * Scanned content is data. Nothing read from a file, a diff or a commit is
    executed, evaluated, or followed; subprocesses take argument lists, never a
    shell string.
  * Never echo a found value. A hit carries its rule, where it is, a salted
    fingerprint (sha256 of salt + lower-cased value, first 12 hex), the value's
    length and, for an email, its domain. Salt: the env var named by --salt-env
    (default SHIELD_SALT); without it, a random per-run salt, flagged in output.
  * Every file the tree pass does not read is listed in not_scanned with its
    path and reason (binary or media extension, NUL byte, over the size cap),
    so a skipped file is never read as a clean one.
  * Exit codes: 0 clean, 1 hits, 3 NOT-RUN (target or git unusable, a refused
    input), 4 crashed.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import secrets as _rand
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warden_private  # noqa: E402  (pack-shared: the private-file convention, references/private-files.md)

VERSION = "1.1.0"
CLEAN, HITS, NOT_RUN, CRASH = 0, 1, 3, 4
MAX_FILE = 2_000_000

# ---------------------------------------------------------------- personal data
_SEP = r"[\\/]"
PATH_SHAPES = [
    # A Windows or macOS user folder, either slash, doubled slashes as in JSON.
    ("user-folder", re.compile(rf"(?i)(?:[A-Z]:)?{_SEP}{{1,2}}Users{_SEP}{{1,2}}([A-Za-z0-9_.-]+)")),
    # The slug form a path takes inside a tool's project-folder name.
    ("user-folder-slug", re.compile(r"(?i)Users-([A-Za-z0-9_.]+)")),
    # A Unix home folder.
    ("home-folder", re.compile(r"(?<![\w.-])/(?:home)/([A-Za-z0-9_.-]+)")),
]
PLACEHOLDERS = {
    "%userprofile%", "$env:userprofile", "~", "<user>", "<you>", "<name>",
    "<username>", "user", "username", "youruser", "someuser", "someacct",
    "public", "default", "defaultuser", "all users", "alluser", "x",
    "owner", "someone", "me", "...", "runner",
}
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,24}\b")
EMAIL_ALLOWED = [re.compile(p) for p in (
    r"(?i)^[A-Za-z0-9._%+-]+@users\.noreply\.github\.com$",
    r"(?i)^(?:noreply|no-reply|donotreply|do-not-reply)@[A-Za-z0-9.-]+$",
    r"(?i)^[A-Za-z0-9._%+-]+@(?:no-?reply)\.[A-Za-z0-9.-]+$",
    r"(?i)^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)*example\.(?:com|net|org)$",
    r"(?i)^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?:invalid|test|localhost|example)$",
    r"(?i)^git@(?:github|gitlab|bitbucket|ssh\.dev\.azure)\.[A-Za-z.]+$",
)]
URL_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:\Z")
# A commit identity is clean only on a no-reply address (the machine hook's rule).
IDENTITY_ALLOWED = re.compile(r"(?i)(@users\.noreply\.github\.com|^noreply@anthropic\.com|^noreply@github\.com)$")

# ---------------------------------------------------------------------- secrets
SECRET_SHAPES = {
    "anthropic-key": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "openai-key": r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b",
    "github-pat-classic": r"\bghp_[A-Za-z0-9]{36,}\b",
    "github-pat-fine": r"\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "github-oauth": r"\bgh[ousr]_[A-Za-z0-9]{36,}\b",
    "aws-access-key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "slack-token": r"\bxox[abpors]-[A-Za-z0-9\-]{10,}\b",
    "private-key-block": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----",
    "google-api-key": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "generic-api-key": r"(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-/+]{16,}['\"]?",
}
GENERIC_DOC = re.compile(r"(?i)(<[^>]+>|\$\{?[A-Z_]+\}?|your[_-]?key|example|placeholder|xxx+|\.\.\.|REDACTED|changeme)")

# ------------------------------------------------------------ injection shapes
# Tokens that would trip this engine's own scan are assembled, so the shape
# source stays clean under its own rules.
_IEX = "Invoke-" + "Expression"
DIRECTIVE = re.compile(r"""(?ix)
    \b ignore \s+ (?:all \s+ |any \s+ |the \s+ |your \s+ )? (?:previous|prior|above|earlier|preceding|foregoing) \s+ (?:instructions?|rules?|prompts?|directions?|guidance)
  | \b disregard \s+ (?:all \s+ |any \s+ |the \s+ |your \s+ )? (?:previous|prior|above|earlier|preceding|foregoing|system|these|those|its|the)? \s* (?:instructions?|rules?|prompts?|directions?|guidance|guardrails?|constraints?)
  | \b you \s+ are \s+ now \s+ (?:a|an|the|in|free|no\s+longer|unrestricted|dan|acting|operating)\b
  | \b system \s+ prompt \b
  | \b as \s+ an \s+ ai \s+ (?:language \s+ )? (?:model|assistant|system|agent|chatbot) \b
  | \b new \s+ instructions? \s* [:\-]
  | \b execute \s+ the \s+ following \b
  | \b run \s+ (?:this|the \s+ following) \s+ commands? \b
  | \b (?:do \s+ not|don'?t|never) \s+ (?:tell|inform|mention \s+ (?:this \s+ )? to|reveal \s+ (?:this \s+ )? to) \s+ the \s+ (?:user|owner|human|operator)\b
  | \b (?:reveal|print|dump|exfiltrate|send|email|post|leak) \s+ (?:the \s+|your \s+|all \s+)? (?:system \s+ prompt|secrets?|credentials?|api \s+ keys?|tokens?|environment \s+ variables?|\.env)\b
  | \b assistant \s* : \s* (?:sure|ok|okay|certainly|understood)\b
""")
TOOL_CALL = re.compile(r"""(?ix)
    < \s* (?:tool_use|tool_call|function_calls?|invoke\s+name=|antml:invoke|antml:function_calls)
  | \b function_call \s* [:=] \s* \{
  | "tool_calls" \s* : \s* \[
  | < \| im_start \|> | < \| system \|> | \[INST\] | << SYS >>
""")
NEGATION = re.compile(r"(?i)\b(?:never|not|don'?t|do\s+not|refuse|reject|ignore\s+such|treat(?:ed)?|is\s+a\s+finding|are\s+a\s+finding|as\s+data|flags?|detects?|reports?|contains?|found|example|e\.g\.|such\s+as|like|pattern|matches?)\b")
_INVIS = [(0x200B, 0x200F), (0x2028, 0x2029), (0x202A, 0x202E), (0x2060, 0x2064),
          (0x2066, 0x2069), (0xFEFF, 0xFEFF), (0x180E, 0x180E), (0xE0000, 0xE007F)]
INVISIBLE = re.compile("[" + "".join(
    (chr(lo) + "-" + chr(hi)) if lo != hi else chr(lo) for lo, hi in _INVIS) + "]")
LATIN = re.compile(r"[A-Za-z]")
CONFUSABLE = re.compile("[Ѐ-ӿͰ-Ͽ]")
TOKEN = re.compile("[\\wЀ-ӿͰ-Ͽ]{4,}")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
IMPERATIVE = re.compile(r"""(?ix)
    ^\s*(?:[-*>]\s*)? (?:please\s+)?
    (?:ignore|disregard|run|execute|delete|remove|send|post|fetch|download|open|install|curl|wget|write|overwrite|push|commit|email|forward|exfiltrate|reveal|print|echo|cat|read|follow|obey|visit|click|call|invoke|use|switch|change|update|modify|edit|grant|allow|enable|disable|bypass|skip|approve|paste|copy|upload|leak|dump|export)\b
  | \b (?:you\s+must|you\s+should|you\s+need\s+to|you\s+have\s+to|do\s+not\s+tell|don'?t\s+tell|do\s+not\s+mention|the\s+assistant\s+(?:must|should|will))\b
""")
COMMENT_BENIGN = re.compile(r"(?i)^\s*(?:markdownlint|prettier|eslint|editorconfig|TODO|FIXME|NOTE|HACK|XXX|generated|auto-generated|do not edit|toc|end|begin|-+|=+|#)")
BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
HEX_RUN = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{200,}(?![0-9a-fA-F])")
DATA_URI = re.compile(r"data:[a-z]+/[a-z0-9.+\-]+;base64,")
PIPE_SHELL = re.compile(
    r"(?i)\b(?:curl|wget|Invoke-WebRequest|iwr|irm|Invoke-RestMethod)\b[^\n|]*\|\s*(?:sudo\s+)?"
    r"(?:sh|bash|zsh|pwsh|powershell|iex|" + _IEX + r"|python3?|perl|node)\b"
    r"|\b" + _IEX + r"\b|(?<![\w.])iex\s*\(")
EVAL_CALL = re.compile(r"(?<![\w.])(?:eval|exec)\s*\(")
FETCH_FOLLOW = re.compile(r"""(?ix)
    \b (?:open|visit|fetch|load|read|go\s+to) \s+ (?:the\s+|this\s+|that\s+|each\s+|every\s+|any\s+)? (?:url|link|page|site|website|address|endpoint) \b [^.\n]{0,60}? \b (?:and\s+)? (?:do|follow|obey|apply|execute|run|perform|carry\s+out) \s+ (?:what(?:ever)?\s+it\s+says|the\s+instructions|its\s+instructions|any\s+instructions|the\s+steps|what\s+it\s+tells|as\s+it\s+says|as\s+instructed)
  | \b do \s+ what(?:ever)? \s+ (?:it|the\s+page|the\s+site|the\s+file|the\s+response|the\s+content|the\s+email|the\s+message) \s+ (?:says|tells\s+you|asks|instructs|wants)
  | \b (?:instructions?|directions?) \s+ (?:on|in|from) \s+ the \s+ (?:fetched|returned|downloaded|retrieved|remote) \s+ (?:page|content|file|document|response) \s+ (?:are|is|must\s+be|should\s+be) \s+ (?:followed|obeyed|executed|applied|authoritative)
""")
INGEST_TOOL = re.compile(r"(?i)\bWebFetch\b|\bWebSearch\b|\bget_file_contents\b|\brequests\.(?:get|post|request)\b|\bimport\s+requests\b|\burllib\b|\bcurl\b|\bwget\b|\bInvoke-WebRequest\b|\bhttpx\b|raw\.githubusercontent\.com|\bscrap(?:e|es|ed|ing)\b|\bcrawl(?:s|ed|ing)?\b")
INGEST_VERB = re.compile(r"(?i)\b(?:fetch(?:es|ed|ing)?|pulls?|pulled|download(?:s|ed|ing)?|read(?:s|ing)?|quer(?:y|ies|ied)|load(?:s|ed)?|retriev(?:e|es|ed)|ingest(?:s|ed)?|receiv(?:e|es|ed)|import(?:s|ed)?|parse[sd]?|consum(?:e|es|ed)|search(?:es|ed)?|open(?:s|ed)?)\b")
INGEST_NOUNS = [r"web\s*pages?", r"websites?", r"urls?", r"links?", r"apis?", r"api\s+endpoints?",
                r"(?:api|http|web)\s+responses?", r"feeds?", r"rss", r"github\s+(?:contents?|api|issues?|comments?)",
                r"search\s+results?", r"e-?mails?", r"inbox", r"(?:incoming|inbound)\s+messages?",
                r"pasted\s+\w+", r"attachments?", r"uploads?", r"user-supplied", r"third-party",
                r"external\s+(?:sources?|data|content|sites?)", r"untrusted\s+\w+", r"news"]
INGEST_NEG = re.compile(r"(?i)\b(?:removed|retired|never|no\s+longer|not|without|forbidden|denied|deny|banned|disallowed|does\s+not|do\s+not|don'?t|cannot|can'?t|instead\s+of|git\s+fetch)\b")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n\s*\n|\n\s*(?=[-*\d]+[.)]?\s)|\n#+\s")
POSTURE = re.compile(r"""(?ix)
    (?:is|are|as|be|remains?|stays?|treat(?:ed|s)?(?:\s+as)?|considered) \s+ (?:only\s+|always\s+|just\s+|raw\s+|inert\s+|the\s+)? (?:data|input|content|evidence|material|object\s+under\s+work) \b [^.\n]{0,80}? \b (?:not|never|no) \s+ (?:as\s+)? (?:an?\s+|the\s+)? (?:instructions?|directions?|commands?|directives?|orders?|prompts?|authority|calls?)
  | \b content \s+ is \s+ data \b
  | \b data, \s+ (?:not|never) \s+ (?:an?\s+)? (?:instructions?|directions?|commands?|directives?)
  | \b (?:never|not) \s+ (?:as\s+)? (?:an?\s+)? instructions? \b
  | \b never \s+ (?:follow(?:ed|s)?|obey(?:ed|s)?|execut(?:e|ed|es)|act(?:ed|s)?\s+on) \b [^.\n]{0,60} \b (?:instructions?|directives?|directions?|commands?) \b
""")

# ------------------------------------------------------ permission and hook posture
HOOK_NET = re.compile(r"(?i)\b(?:curl|wget|Invoke-WebRequest|iwr|irm|Invoke-RestMethod|requests\.(?:get|post|put|delete|request)|urllib\.request|urlopen|http\.client|httpx|aiohttp|socket\.(?:socket|create_connection)|netcat|ssh|scp|rsync|pip3?\s+install|npm\s+install|npx|Start-BitsTransfer|WebClient|HttpClient)\b")
HOOK_OUTSIDE = re.compile(r"""(?x)
    (?<![\w$}{:./\\-]) (?:/(?:home|root|usr|etc|opt|tmp|var|Users)/[^\s"']*)
  | (?<![\w$}{:./\\-]) ~/[^\s"']*
  | \b[A-Za-z]:[\\/][^\s"']*
  | \$HOME\b | \$\{HOME\} | \$USERPROFILE\b | %USERPROFILE% | %APPDATA% | \$env:USERPROFILE | \$env:APPDATA
""")
WIDE_ALLOW = re.compile(r"""(?ix)
    ^ (?:Bash|PowerShell|WebFetch|Agent|Task|mcp__[\w-]+) $
  | ^ (?:Bash|PowerShell) \( \s* (?:\*|\*:\*|:\*) \s* \) $
  | ^ (?:Bash|PowerShell) \( \s* (?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod|iex|eval|sh|bash|pwsh|powershell|nc|ssh|scp|rsync|sudo|rm\s+-rf|git\s+push\s+--force|git\s+push\s+-f)\b [^)]* \) $
  | ^ WebFetch \( \s* (?:\*|domain:\*|domain:\s*\*) \s* \) $
""")

# ------------------------------------- secrets leaking through logs and object dumps
# Code shapes, not values (K4 C5): a secret-named variable handed to a log or print call, a whole
# environment or config object dumped, a secret field a default repr or model dump would print.
# Hits carry a line, never a value or a fingerprint.
CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
SECRET_NAME = re.compile(r"(?i)(?<![A-Za-z0-9])(?:api[_-]?key|apikey|client[_-]?secret|secret[_-]?key|secret|"
                         r"password|passwd|access[_-]?token|auth[_-]?token|refresh[_-]?token|bearer[_-]?token|"
                         r"private[_-]?key|credentials?|token)(?![A-Za-z0-9_])")
LOG_CALL = re.compile(r"(?<![\w.])(?:print|pprint|console\.(?:log|info|debug|warn|error|dir)|"
                      r"(?:log|logger|logging|_log|_logger|LOG|LOGGER)\.(?:debug|info|warning|warn|error|"
                      r"exception|critical|log)|span\.set_attribute|set_tag)\s*\((.*)")
REDACTED_USE = re.compile(r"(?i)redact|mask|\*\*\*|\blen\s*\(|\bbool\s*\(|\bis\s+(?:not\s+)?None\b|"
                          r"\bfingerprint|\bhash|\[\s*:\s*\d\s*\]|\bset\b|\bmissing\b|\bexpired?\b")
OBJECT_DUMP = re.compile(r"""(?x)
    (?<![\w.]) (?:print|pprint|console\.(?:log|info|debug|dir)|json\.dumps|JSON\.stringify|
                (?:log|logger|logging)\.(?:debug|info|warning|error))
    \s*\( \s* (?:dict\s*\(\s*)?
    (?: os\.environ | process\.env | vars\s*\(\s*\w*(?:config|settings|cfg|env|creds?|credentials|options|args)\w*\s*\)
      | \w*(?:config|settings|cfg|creds?|credentials)\w*\.__dict__
      | (?:request|req|response|resp)\.headers )
    \s*\)?\s*[,)]
""")
SECRET_FIELD = re.compile(r"^\s+(\w+)\s*:\s*([^=#]+?)\s*(?:=\s*(.*))?$")
MODEL_MARK = re.compile(r"@dataclass|@(?:attr\.)?(?:s|define|frozen)\b|\bBaseModel\b|\bBaseSettings\b|\bNamedTuple\b")
SAFE_FIELD = re.compile(r"Secret(?:Str|Bytes)|repr\s*=\s*False|exclude\s*=\s*True|Field\([^)]*repr\s*=\s*False")

# ------------------------------------------------------------------ file classes
SKIP_DIRS = {"node_modules", ".venv", "venv", "bin", "obj", ".godot", "dist", "build",
             ".git", "__pycache__", "vendor", ".import"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2", ".ttf", ".otf",
           ".zip", ".gz", ".7z", ".pdf", ".pyc", ".exe", ".dll", ".so", ".dylib", ".duckdb",
           ".parquet", ".bundle", ".wav", ".mp3", ".ogg", ".mp4", ".psd", ".safetensors"}
ASSET_DIRS = {"assets", "asset", "static", "public", "images", "img", "fonts", "media"}
BLOB_SKIP_EXT = {".ipynb", ".svg", ".pem", ".crt", ".cer", ".pub", ".lock", ".min.js"}
CONTROL_TEXT_EXT = {".md", ".yaml", ".yml", ".txt"}
# C0 controls minus tab, LF and CR; DEL; the C1 controls. A bare CR is its own rule.
CONTROL_CHAR = re.compile("[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f-\\x9f]")
INSTRUCTION_NAMES = {"SKILL.md", "CLAUDE.md", "AGENTS.md", "README.md"}
PII_CLASSES = {"pii", "identity", "secret"}


class Refused(Exception):
    """An input the engine will not take (exit 3)."""


# ---------------------------------------------------------------------- helpers
def git(repo: Path, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=timeout)


def git_text(repo: Path, *args: str) -> str:
    return git(repo, *args).stdout.decode("utf-8", errors="replace")


def work_tree_of(path: Path) -> Path | None:
    if not shutil.which("git"):
        return None
    probe = path if path.is_dir() else path.parent
    while not probe.exists():
        probe = probe.parent
    r = git(probe, "rev-parse", "--show-toplevel")
    if r.returncode != 0:
        return None
    return Path(r.stdout.decode("utf-8", errors="replace").strip()).resolve()


class Engine:
    def __init__(self, cfg: dict, names: list[tuple[str, str]], salt_env: str):
        salt = os.environ.get(salt_env, "")
        self.salt_kind = "env" if salt else "random-per-run (fingerprints not comparable across runs)"
        self.salt = salt or _rand.token_hex(16)
        self.placeholders = PLACEHOLDERS | {p.lower() for p in cfg.get("placeholders", [])}
        self.email_allow = EMAIL_ALLOWED + [re.compile(p) for p in cfg.get("email_allow", [])]
        self.allowed_ident_names = {n.lower() for n in cfg.get("allowed_identity_names", [])}
        self.secret_shapes = {k: re.compile(v) for k, v in {**SECRET_SHAPES, **cfg.get("secret_patterns", {})}.items()}
        self.ingest_noun = re.compile(r"(?i)\b(?:" + "|".join(INGEST_NOUNS + cfg.get("ingest_nouns", [])) + r")\b")
        self.mcp_allow = set(cfg.get("mcp_allowlist", []))
        self.hashes = cfg.get("hashes", {})
        self.accepted = cfg.get("accepted", [])
        self.skip_dirs = SKIP_DIRS | set(cfg.get("skip_dirs", []))
        self.instruction_globs = cfg.get("instruction_globs", [])
        self.names = [(n, r, re.compile(r"(?i)(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])"))
                      for n, r in names]
        self.hits: list[dict] = []
        self.accepted_hits: list[dict] = []
        self.not_scanned: list[dict] = []
        self.not_run: list[str] = []
        self.raw: dict[str, set] = {"segment": set(), "slug": set(), "home": set(), "email": set(),
                                    "secret": set(), "name": set()}
        self.idents: set[tuple[str, str]] = set()
        self.files_scanned = 0

    # -- reporting
    def fp(self, value: str) -> str:
        return hashlib.sha256((self.salt + value.lower()).encode("utf-8")).hexdigest()[:12]

    def add(self, cls: str, rule: str, where: str, line: int | None = None, value: str | None = None,
            domain: str | None = None, file: str | None = None, entry: int | None = None) -> None:
        hit = {"class": cls, "rule": rule, "where": where}
        if entry is not None:
            hit["entry"] = entry  # a names-file line number; its value and length never leave the list
        if line is not None:
            hit["line"] = line
        if value is not None:
            hit["fp"] = self.fp(value)
            hit["len"] = len(value)
        if domain:
            hit["domain"] = domain
        target = file or where
        for a in self.accepted:
            if a.get("rule") in (rule, "*") and fnmatch.fnmatch(target, a.get("file", "")):
                self.accepted_hits.append(hit)
                return
        self.hits.append(hit)

    # -- shape passes over one line of text
    def pii_line(self, text: str, cls: str, where: str, line: int | None, file: str | None = None) -> None:
        for rule, rx in PATH_SHAPES:
            for m in rx.finditer(text):
                seg = m.group(1).rstrip(".")
                if seg.lower() in self.placeholders or not seg:
                    continue
                self.raw[{"user-folder": "segment", "user-folder-slug": "slug", "home-folder": "home"}[rule]].add(seg)
                self.add(cls, rule, where, line, seg, file=file)
        for m in EMAIL.finditer(text):
            val = m.group(0)
            if any(a.match(val) for a in self.email_allow):
                continue
            before = text[:m.start()]
            if before.endswith("//") and URL_SCHEME.search(before[:-2]):
                continue  # URL userinfo, not a mailbox
            self.raw["email"].add(val)
            self.add(cls, "email-address", where, line, val, domain=val.partition("@")[2].lower(), file=file)
        for entry, (name, _repl, rx) in enumerate(self.names, 1):
            if rx.search(text):
                self.raw["name"].add(name)
                self.add(cls, "owner-name", where, line, file=file, entry=entry)
        for rule, rx in self.secret_shapes.items():
            for m in rx.finditer(text):
                val = m.group(0)
                if rule == "generic-api-key" and GENERIC_DOC.search(val):
                    continue
                self.raw["secret"].add(val)
                self.add("secret" if cls == "pii" else cls, rule, where, line, val, file=file)

    # -- file classes
    def file_class(self, rel: str) -> str:
        p = rel.replace("\\", "/")
        base = p.rsplit("/", 1)[-1]
        if (fnmatch.fnmatch(p, ".claude/settings*.json") or fnmatch.fnmatch(p, "*/.claude/settings*.json")
                or "/.claude/hooks/" in "/" + p or p.endswith(".mcp.json") or p == ".mcp.json"):
            return "control"
        if (base in INSTRUCTION_NAMES or "/references/" in "/" + p and p.endswith(".md")
                or fnmatch.fnmatch(p, "tasks/*.md") or fnmatch.fnmatch(p, "*/tasks/*.md")
                or "/.claude/agents/" in "/" + p or "/.claude/commands/" in "/" + p
                or any(fnmatch.fnmatch(p, g) for g in self.instruction_globs)):
            return "instruction"
        return "data"

    # -- one file
    def scan_file(self, rel: str, data: bytes, want_inj: bool) -> None:
        self.files_scanned += 1
        ext = os.path.splitext(rel)[1].lower()
        try:
            text = data.decode("utf-8")
            bad_utf8 = False
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
            bad_utf8 = True
        fclass = self.file_class(rel)
        # Split on LF only: splitlines() also breaks on form feed, U+2028 and other
        # characters this scan exists to find.
        lines = [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]
        for i, ln in enumerate(lines, 1):
            self.pii_line(ln, "pii", rel, i, file=rel)
        if not want_inj:
            return
        if ext in CONTROL_TEXT_EXT:
            if bad_utf8:
                self.add("control-bytes", "invalid-utf8", rel)
            for i, raw_ln in enumerate(data.split(b"\n"), 1):
                if re.search(rb"\r(?!$)", raw_ln):
                    self.add("control-bytes", "bare-cr", rel, i)
            for i, ln in enumerate(lines, 1):
                if CONTROL_CHAR.search(ln):
                    self.add("control-bytes", "control-char", rel, i)
        self.inject_text(rel, text, lines, fclass, ext)
        if ext in CODE_EXT:
            self.exposure_text(rel, text, lines, ext)
        if fclass == "control":
            self.control_file(rel, data, text)

    def inject_text(self, rel: str, text: str, lines: list[str], fclass: str, ext: str) -> None:
        parts = set(rel.replace("\\", "/").lower().split("/")[:-1])
        for i, ln in enumerate(lines, 1):
            body = ln[1:] if i == 1 and ln.startswith(chr(0xFEFF)) else ln
            if INVISIBLE.search(body):
                self.add("injection", "invisible-unicode", rel, i)
            for tok in TOKEN.findall(ln):
                if LATIN.search(tok) and CONFUSABLE.search(tok):
                    self.add("injection", "mixed-script-token", rel, i)
                    break
            negated = bool(NEGATION.search(ln))
            if fclass == "data" and not negated:
                if DIRECTIVE.search(ln):
                    self.add("injection", "directive-in-data", rel, i)
                if TOOL_CALL.search(ln):
                    self.add("injection", "tool-call-in-data", rel, i)
            if FETCH_FOLLOW.search(ln) and not negated:
                self.add("injection", "fetch-and-follow", rel, i)
            if fclass in ("instruction", "control") or ext in (".sh", ".ps1", ".bat", ".cmd"):
                if PIPE_SHELL.search(ln) and not negated:
                    self.add("injection", "pipe-to-shell", rel, i)
                if fclass != "data" and ext in (".md", ".json") and EVAL_CALL.search(ln) and not negated:
                    self.add("injection", "eval-in-prompt", rel, i)
            if not (parts & ASSET_DIRS) and not any(rel.lower().endswith(e) for e in BLOB_SKIP_EXT) \
                    and not DATA_URI.search(ln) and (BASE64_RUN.search(ln) or HEX_RUN.search(ln)):
                self.add("injection", "encoded-blob", rel, i)
        if ext in (".md", ".html", ".htm"):
            for m in HTML_COMMENT.finditer(text):
                inner = m.group(1).strip()
                if inner and not COMMENT_BENIGN.match(inner) and IMPERATIVE.search(inner):
                    self.add("injection", "html-comment-directive", rel, text.count("\n", 0, m.start()) + 1)
        if fclass == "instruction" and ext == ".md" and not POSTURE.search(text):
            if any(self.ingests(s) for s in SENTENCE_SPLIT.split(text)):
                self.add("injection", "posture-gap", rel)

    def exposure_text(self, rel: str, text: str, lines: list[str], ext: str) -> None:
        """Secrets reaching logs, traces or dumps through code (class `exposure`, K4 C5)."""
        models = ext == ".py" and bool(MODEL_MARK.search(text))
        for i, ln in enumerate(lines, 1):
            code = ln.split("#", 1)[0] if ext == ".py" else ln.split("//", 1)[0]
            if not code.strip():
                continue
            m = LOG_CALL.search(code)
            if m and SECRET_NAME.search(_code_refs(m.group(1))) and not REDACTED_USE.search(m.group(1)):
                self.add("exposure", "secret-in-log", rel, i)
            if OBJECT_DUMP.search(code):
                self.add("exposure", "object-dump", rel, i)
            if models and ln[:1] in (" ", "\t") and not code.rstrip().endswith((",", "(", ")")):
                f = SECRET_FIELD.match(code.rstrip())
                if f and SECRET_NAME.search(f.group(1)) and "(" not in f.group(2) \
                        and not SAFE_FIELD.search(code):
                    self.add("exposure", "secret-field-repr", rel, i)

    def ingests(self, sentence: str) -> bool:
        if INGEST_NEG.search(sentence):
            return False
        return bool(INGEST_TOOL.search(sentence) or (INGEST_VERB.search(sentence) and self.ingest_noun.search(sentence)))

    def control_file(self, rel: str, data: bytes, text: str) -> None:
        p = rel.replace("\\", "/")
        want = self.hashes.get(p)
        if want and hashlib.sha256(data).hexdigest() != want:
            self.add("posture", "hook-hash-drift" if "/hooks/" in "/" + p else "settings-hash-drift", rel)
        if "/.claude/hooks/" in "/" + p:
            for i, ln in enumerate(text.splitlines(), 1):
                if HOOK_NET.search(ln):
                    self.add("posture", "hook-network", rel, i)
            return
        try:
            doc = json.loads(text)
        except ValueError:
            self.add("posture", "unparseable-control-file", rel)
            return
        if not isinstance(doc, dict):
            return
        if p.endswith(".mcp.json"):
            for srv in (doc.get("mcpServers") or {}):
                if srv not in self.mcp_allow:
                    self.add("posture", "mcp-server-unlisted", rel)
            return
        perms = doc.get("permissions") or {}
        if perms.get("ask"):
            self.add("posture", "settings-ask-rule", rel)
        for rule in perms.get("allow") or []:
            if isinstance(rule, str) and WIDE_ALLOW.search(rule.strip()):
                self.add("posture", "settings-wide-allow", rel)
        if perms.get("defaultMode") == "bypassPermissions" or doc.get("enableAllProjectMcpServers") is True:
            self.add("posture", "settings-bypass", rel)
        for cmd in _hook_commands(doc.get("hooks")):
            if HOOK_NET.search(cmd):
                self.add("posture", "hook-network", rel)
            if HOOK_OUTSIDE.search(cmd.replace("$CLAUDE_PROJECT_DIR", "").replace("${CLAUDE_PROJECT_DIR}", "")):
                self.add("posture", "hook-outside-repo", rel)


_INTERP = re.compile(r"\{([^{}]*)\}")
_QUOTED = re.compile(r"""(['"`])(?:\\.|(?!\1).)*\1""")


def _code_refs(arg: str) -> str:
    """The names a call argument really uses: code outside string literals, plus whatever sits in
    an f-string or template interpolation. A word inside plain quoted text is not a variable."""
    return _QUOTED.sub(" ", arg) + " " + " ".join(_INTERP.findall(arg))


def _hook_commands(node) -> list[str]:
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                out.append(v)
            else:
                out.extend(_hook_commands(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_hook_commands(v))
    return out


# --------------------------------------------------------------------- passes
def list_files(eng: Engine, target: Path, is_repo: bool, untracked: bool) -> list[str]:
    if is_repo:
        out = git_text(target, "ls-files", "-z").split("\0")
        if untracked:
            out += git_text(target, "ls-files", "-z", "-o", "--exclude-standard").split("\0")
        return [f for f in out if f and not (set(f.split("/")[:-1]) & eng.skip_dirs)]
    files = []
    for root, dirs, names in os.walk(target):
        dirs[:] = [d for d in dirs if d not in eng.skip_dirs]
        for n in names:
            files.append(os.path.relpath(os.path.join(root, n), target).replace("\\", "/"))
    return files


def tree_pass(eng: Engine, target: Path, is_repo: bool, untracked: bool, want_inj: bool) -> None:
    for rel in list_files(eng, target, is_repo, untracked):
        path = target / rel
        ext = os.path.splitext(rel)[1].lower()
        if ext in BIN_EXT:
            eng.not_scanned.append({"file": rel, "reason": f"binary or media extension ({ext})"})
            continue
        try:
            if path.stat().st_size > MAX_FILE:
                eng.not_scanned.append({"file": rel, "reason": "over size cap"})
                continue
            data = path.read_bytes()
        except OSError:
            continue  # deleted in the work tree, or a broken link
        if b"\0" in data[:8192]:
            eng.not_scanned.append({"file": rel, "reason": "binary content (NUL byte)"})
            continue
        eng.scan_file(rel, data, want_inj)


def history_pass(eng: Engine, repo: Path) -> None:
    """Added lines of every commit on every ref, plus commit messages."""
    proc = subprocess.Popen(["git", "-C", str(repo), "log", "--all", "-p", "--unified=0", "--no-color",
                             "--no-ext-diff", "--no-renames", "--format=@@COMMIT %h"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    commit, fname = "?", "?"
    assert proc.stdout is not None
    for raw in proc.stdout:
        ln = raw.decode("utf-8", errors="replace").rstrip("\n")
        if ln.startswith("@@COMMIT "):
            commit = ln[9:].strip()
        elif ln.startswith("+++ "):
            fname = ln[6:] if ln.startswith("+++ b/") else ln[4:]
        elif ln.startswith("+") and not ln.startswith("+++"):
            eng.pii_line(ln[1:], "pii", f"history {commit}:{fname}", None, file=fname)
    proc.wait()
    msgs = git_text(repo, "log", "--all", "--format=%h%x00%B%x1e")
    for rec in msgs.split("\x1e"):
        if "\0" not in rec:
            continue
        h, body = rec.strip("\n").split("\0", 1)
        for ln in body.splitlines():
            eng.pii_line(ln, "pii", f"message {h}", None, file=f"message {h}")


def identity_pass(eng: Engine, repo: Path) -> None:
    out = git_text(repo, "log", "--all", "--format=%h%x00%an%x00%ae%x00%cn%x00%ce")
    seen = set()
    for row in out.splitlines():
        parts = row.split("\0")
        if len(parts) != 5:
            continue
        h, an, ae, cn, ce = parts
        for role, name, email in (("author", an, ae), ("committer", cn, ce)):
            if (role, name, email) in seen:
                continue
            seen.add((role, name, email))
            flagged = False
            if email and not IDENTITY_ALLOWED.search(email):
                eng.add("identity", f"{role}-email", f"identity first seen {h}", None, email,
                        domain=email.partition("@")[2].lower() or "none")
                flagged = True
            if any(rx.search(name) for _n, _r, rx in eng.names):
                eng.add("identity", f"{role}-name", f"identity first seen {h}", None, name)
                flagged = True
            elif eng.allowed_ident_names and name.lower() not in eng.allowed_ident_names:
                eng.add("identity", f"{role}-name-unlisted", f"identity first seen {h}", None, name)
                flagged = True
            if flagged:
                eng.idents.add((name, email))


def gitleaks_pass(eng: Engine, target: Path, is_repo: bool, binary: str) -> None:
    exe = shutil.which(binary)
    if not exe:
        eng.not_run.append("gitleaks: NOT-RUN (not installed; optional)")
        return
    with tempfile.TemporaryDirectory() as td:
        report = Path(td) / "gl.json"
        attempts = ([[exe, "git", "--no-banner", "--redact", "--exit-code", "0", "--report-format", "json",
                      "--report-path", str(report), str(target)],
                     [exe, "detect", "--no-banner", "--redact", "--exit-code", "0", "--report-format", "json",
                      "--report-path", str(report), "--source", str(target)]] if is_repo else
                    [[exe, "dir", "--no-banner", "--redact", "--exit-code", "0", "--report-format", "json",
                      "--report-path", str(report), str(target)],
                     [exe, "detect", "--no-git", "--no-banner", "--redact", "--exit-code", "0", "--report-format",
                      "json", "--report-path", str(report), "--source", str(target)]])
        code = None
        for cmd in attempts:
            try:
                code = subprocess.run(cmd, capture_output=True, timeout=1800).returncode
            except (OSError, subprocess.TimeoutExpired):
                code = -1
            if code == 0 and report.is_file():
                break
        if code != 0 or not report.is_file():
            eng.not_run.append(f"gitleaks: NOT-RUN (exit {code})")
            return
        try:
            findings = json.loads(report.read_text(encoding="utf-8") or "[]")
        except ValueError:
            eng.not_run.append("gitleaks: NOT-RUN (unreadable report)")
            return
    for f in findings or []:
        where = f.get("File", "?")
        if f.get("Commit"):
            where = f"history {str(f['Commit'])[:7]}:{where}"
        eng.add("secret", "gitleaks:" + str(f.get("RuleID", "unknown")), where, f.get("StartLine"),
                file=f.get("File", "?"))


# -------------------------------------------------------------------- inputs
def load_json(path: str | None) -> dict:
    if not path:
        return {}
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refused(f"config unreadable ({type(e).__name__})")
    if not isinstance(doc, dict):
        raise Refused("config must be a JSON object")
    return doc


def load_names(flag: str | None, target: Path) -> tuple[list[tuple[str, str]], str | None]:
    """The names list, resolved by warden_private: --names-file > WARDEN_NAMES_FILE > ~/.warden/wordlist.txt.

    Returns (names, not_run_note). No list anywhere is a NOT-RUN line for the user-name rule,
    never a silent pass; a named file that is missing or sits inside a git work tree is refused.
    """
    res = warden_private.resolve("names", flag)
    if res.path is None:
        return [], f"owner-name: NOT-RUN ({res.problem})"
    if res.problem:
        raise Refused(res.problem)
    p = res.path.resolve()
    if work_tree_of(p.parent) is not None or _inside(p, target):
        raise Refused("names list sits inside a git work tree or the target; keep it outside every repo")
    out = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise Refused("names list unreadable")
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        for prefix in ("sub:", "word:"):  # name-leak match modes; this engine always matches whole words
            if ln.lower().startswith(prefix):
                ln = ln[len(prefix):].strip()
                break
        name, _, repl = ln.partition("==>")
        if len(name.strip()) >= 3:
            out.append((name.strip(), repl.strip() or "the user"))
    return out, None


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------- modes
def run_scan(args, eng: Engine, target: Path, is_repo: bool) -> None:
    tree_pass(eng, target, is_repo, args.untracked, want_inj=not args.pii_only)
    if is_repo and args.history:
        history_pass(eng, target)
    if is_repo and args.identities:
        identity_pass(eng, target)
    if args.gitleaks != "off":
        gitleaks_pass(eng, target, is_repo, args.gitleaks_bin)


def run_emit(args, eng: Engine, target: Path) -> list[str]:
    out = Path(args.out).resolve()
    if _inside(out, target) or work_tree_of(out) is not None:
        raise Refused("--out sits inside a git work tree; filter-repo inputs hold raw values and live outside every repo")
    tree_pass(eng, target, True, False, want_inj=False)
    history_pass(eng, target)
    identity_pass(eng, target)
    rules = []
    for seg in sorted(eng.raw["segment"]):
        rules.append(r"regex:(?i)(Users[\\/]{1,2})" + re.escape(seg) + r"(?![A-Za-z0-9_.-])==>\1<user>")
    for seg in sorted(eng.raw["slug"]):
        rules.append(r"regex:(?i)(Users-)" + re.escape(seg) + r"(?![A-Za-z0-9_.])==>\1user")
    for seg in sorted(eng.raw["home"]):
        rules.append(r"regex:(/(?:home)/)" + re.escape(seg) + r"(?![A-Za-z0-9_.-])==>\1user")
    for name, repl, _rx in eng.names:
        if name in eng.raw["name"]:
            rules.append(r"regex:(?i)(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])==>" + repl)
    for val in sorted(eng.raw["email"]):
        rules.append("literal:" + val + "==>***REMOVED***")
    for val in sorted(eng.raw["secret"]):
        rules.append("literal:" + val + "==>***REMOVED***")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fname in ("replace-text.txt", "replace-message.txt"):
        (out / fname).write_bytes(("\n".join(rules) + "\n").encode("utf-8"))
        written.append(str(out / fname))
    counts = {k: len(v) for k, v in eng.raw.items()}
    if args.mailmap_to:
        m = re.fullmatch(r"\s*(.+?)\s*<([^>]+)>\s*", args.mailmap_to)
        if not m or not IDENTITY_ALLOWED.search(m.group(2)):
            raise Refused("--mailmap-to must be 'Name <no-reply address>'")
        lines = [f"{m.group(1)} <{m.group(2)}> {n} <{e}>" for n, e in sorted(eng.idents)]
        (out / "mailmap.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        written.append(str(out / "mailmap.txt"))
        counts["identities"] = len(lines)
    else:
        eng.not_run.append("mailmap: NOT-EMITTED (pass --mailmap-to 'Name <no-reply address>')")
    eng.emit_counts = counts  # type: ignore[attr-defined]
    return written


def run_verify(args, eng: Engine, target: Path) -> None:
    tree_pass(eng, target, True, False, want_inj=False)
    history_pass(eng, target)
    identity_pass(eng, target)
    if args.bundle:
        r = subprocess.run(["git", "-C", str(target), "bundle", "verify", str(Path(args.bundle).resolve())],
                           capture_output=True, timeout=900)
        if r.returncode != 0:
            eng.add("backup", "bundle-verify-failed", "backup bundle")


# ----------------------------------------------------------------------- main
def report(eng: Engine, mode: str, label: str, as_json: bool, written: list[str] | None = None) -> None:
    counts: dict = {"hits": len(eng.hits), "accepted": len(eng.accepted_hits), "files_scanned": eng.files_scanned,
                    "files_skipped": len(eng.not_scanned), "by_rule": {}, "by_class": {}}
    for h in eng.hits:
        counts["by_rule"][h["rule"]] = counts["by_rule"].get(h["rule"], 0) + 1
        counts["by_class"][h["class"]] = counts["by_class"].get(h["class"], 0) + 1
    doc = {"tool": "shield_scan", "version": VERSION, "mode": mode, "target": label, "salt": eng.salt_kind,
           "hits": eng.hits, "accepted": eng.accepted_hits, "counts": counts, "not_run": eng.not_run,
           "not_scanned": eng.not_scanned}
    if written is not None:
        doc["written"] = written
        doc["emitted"] = getattr(eng, "emit_counts", {})
    if as_json:
        print(json.dumps(doc, indent=1))
        return
    print(f"shield_scan {VERSION} {mode} {label}: {counts['hits']} hit(s), {counts['accepted']} accepted, "
          f"{eng.files_scanned} file(s), {len(eng.not_scanned)} skipped; salt {eng.salt_kind}")
    for h in eng.hits:
        extra = "".join(f" {k}={h[k]}" for k in ("line", "entry", "fp", "len", "domain") if k in h)
        print(f"  [{h['class']}] {h['rule']} @ {h['where']}{extra}")
    for n in eng.not_run:
        print(f"  {n}")
    for d in eng.not_scanned:
        print(f"  skipped {d['file']} ({d['reason']})")
    for w in written or []:
        print(f"  wrote {w}")
    if written is not None:
        print(f"  emitted counts: {json.dumps(getattr(eng, 'emit_counts', {}))}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("scan", "emit", "verify"):
        s = sub.add_parser(name)
        s.add_argument("target", help="repo work tree (or, with --dir, any folder)")
        s.add_argument("--config", help="JSON policy: placeholders, email_allow, allowed_identity_names, "
                                        "secret_patterns, ingest_nouns, mcp_allowlist, hashes, accepted, "
                                        "skip_dirs, instruction_globs")
        s.add_argument("--names-file", help="owner names, one per line (name==>replacement); default "
                                            "$WARDEN_NAMES_FILE, else ~/.warden/wordlist.txt; outside every repo")
        s.add_argument("--salt-env", default="SHIELD_SALT")
        s.add_argument("--json", action="store_true")
        if name == "scan":
            s.add_argument("--dir", action="store_true", help="target is a plain folder, not a git work tree")
            s.add_argument("--history", action="store_true")
            s.add_argument("--identities", action="store_true")
            s.add_argument("--untracked", action="store_true")
            s.add_argument("--pii-only", action="store_true", help="personal data and secrets only")
            s.add_argument("--gitleaks", choices=("auto", "off"), default="auto")
            s.add_argument("--gitleaks-bin", default="gitleaks")
        if name == "emit":
            s.add_argument("--out", required=True, help="folder outside every git work tree")
            s.add_argument("--mailmap-to", help="'Name <no-reply address>' every flagged identity maps to")
        if name == "verify":
            s.add_argument("--bundle", help="backup bundle to check with git bundle verify")
    args = ap.parse_args(argv)
    target = Path(args.target).resolve()
    label = target.name or "target"
    if not target.is_dir():
        print(f"shield_scan: NOT-RUN - target folder not found ({label})")
        return NOT_RUN
    is_repo = not getattr(args, "dir", False)
    if is_repo:
        if not shutil.which("git"):
            print("shield_scan: NOT-RUN - git not on PATH")
            return NOT_RUN
        top = work_tree_of(target)
        if top is None:
            print(f"shield_scan: NOT-RUN - {label} is not a git work tree (use scan --dir for a plain folder)")
            return NOT_RUN
    try:
        names, names_note = load_names(args.names_file, target)
        eng = Engine(load_json(args.config), names, args.salt_env)
        if names_note:
            eng.not_run.append(names_note)
        written = None
        if args.mode == "scan":
            run_scan(args, eng, target, is_repo)
        elif args.mode == "emit":
            written = run_emit(args, eng, target)
        else:
            run_verify(args, eng, target)
    except Refused as e:
        print(f"shield_scan: NOT-RUN - refused: {e}")
        return NOT_RUN
    report(eng, args.mode, label, args.json, written)
    if args.mode == "emit":
        return CLEAN
    if args.mode == "verify":
        return HITS if any(h["class"] in PII_CLASSES | {"backup"} for h in eng.hits) else CLEAN
    return HITS if eng.hits else CLEAN


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(CRASH)
    except Exception as e:  # never print a traceback: it can carry a scanned value
        print(f"shield_scan: CRASHED ({type(e).__name__})")
        sys.exit(CRASH)
