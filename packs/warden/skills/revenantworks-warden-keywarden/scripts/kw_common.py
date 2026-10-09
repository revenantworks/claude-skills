"""Shared helpers for keywarden's scripts (stdlib only).

The rule every helper serves: a credential value is held in memory only as
long as it takes to fingerprint or mask it, and it is never printed, logged,
written or placed in an exception message.

Fingerprint: sha256(salt + value.lower()), first 12 hex. This is the same
method shieldwarden's shield_scan.py uses, so a keywarden row and a
shieldwarden hit for the same value carry the same fingerprint when both runs
read the same salt variable (default SHIELD_SALT).
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets as _rand
import sys
import traceback

VERSION = "0.1.0"

# Exit codes, shared with shieldwarden: 0 clean, 1 findings, 3 NOT-RUN, 4 crash.
CLEAN, FINDINGS, NOT_RUN, CRASH = 0, 1, 3, 4

# Prefix classes: a class NAME is reported, never the prefix plus more.
PREFIX_CLASSES = [
    ("github_pat_", "github-fine-grained-pat"),
    ("ghp_", "github-classic-pat"),
    ("gho_", "github-oauth-token"),
    ("ghu_", "github-app-user-token"),
    ("ghs_", "github-app-server-token"),
    ("ghr_", "github-refresh-token"),
    ("sk-ant-", "anthropic-api-key"),
    ("sk-", "sk-style-api-key"),
    ("AKIA", "aws-access-key-id"),
    ("ASIA", "aws-temporary-key-id"),
    ("xoxb-", "slack-bot-token"),
    ("xoxp-", "slack-user-token"),
    ("glpat-", "gitlab-pat"),
    ("AIza", "google-api-key"),
    ("npm_", "npm-token"),
    ("hf_", "huggingface-token"),
    ("-----BEGIN", "private-key-block"),
]

# Token shapes masked in any output, whether or not the value was known.
SHAPE_RE = re.compile(
    r"(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_\-]{16,}"
    r"|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[abposr]-[A-Za-z0-9\-]{10,}|glpat-[A-Za-z0-9_\-]{16,}"
    r"|AIza[A-Za-z0-9_\-]{30,}|npm_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,})"
)
# Header values that carry a credential, masked whatever their shape.
HEADER_RE = re.compile(
    r"((?:proxy-)?authorization|x-api-key|api-key|x-auth-token|private-token|cookie)"
    r"(\s*[:=]\s*['\"]?)((?:bearer|token|basic)\s+)?([^\s'\",}]+)",
    re.IGNORECASE,
)
URL_USERINFO_RE = re.compile(r"(\w+://)([^/\s:@]+)(?::([^/\s@]+))?@")

SECRET_WORDS = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|PASS$|PWD$|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|CREDENTIAL|AUTH"
    r"|_PAT$|^PAT_|COOKIE|SESSION_?KEY|CLIENT_?SECRET|SIGNING|WEBHOOK_?URL|DSN$|CONN(ECTION)?_?STR)",
    re.IGNORECASE,
)
NOT_SECRET = re.compile(r"(TOKENIZERS?_|_TOKENS$|MAX_TOKENS|TOKEN_LIMIT|AUTHOR($|_|S$|_NAME))", re.IGNORECASE)

REFERENCE_RE = re.compile(
    r"^(op://|bws?://|vault:|azkv:|aws-sm:|secret://|\$\{[^}]+\}$|\$[A-Za-z_][A-Za-z0-9_]*$"
    r"|%[A-Za-z_][A-Za-z0-9_]*%$|<[^>]*>$|\{\{[^}]*\}\}$)",
    re.IGNORECASE,
)
VAULT_REF_RE = re.compile(r"^(op|bws?|secret)://|^(vault|azkv|aws-sm):", re.IGNORECASE)
PLACEHOLDERS = {"", "changeme", "change-me", "xxx", "xxxx", "your-key-here", "your_token_here",
                "todo", "tbd", "none", "null", "redacted", "***", "placeholder", "example"}


def get_salt(salt_env: str) -> tuple[str, str]:
    """Return (salt, kind). Kind says whether fingerprints compare across runs."""
    salt = os.environ.get(salt_env, "")
    if salt:
        return salt, "env"
    return _rand.token_hex(16), "random-per-run (fingerprints not comparable across runs)"


def fingerprint(value: str, salt: str) -> str:
    return hashlib.sha256((salt + value.lower()).encode("utf-8")).hexdigest()[:12]


def prefix_class(value: str) -> str:
    for prefix, name in PREFIX_CLASSES:
        if value.startswith(prefix):
            return name
    return "unknown"


def is_reference(value: str) -> bool:
    v = value.strip().strip("'\"")
    if v.lower() in PLACEHOLDERS or set(v) <= {"*", "x", "X", "."}:
        return True
    return bool(REFERENCE_RE.match(v))


def secret_named(key: str) -> bool:
    if NOT_SECRET.search(key):
        return False
    return bool(SECRET_WORDS.search(key))


def looks_secret(key: str, value: str) -> bool:
    v = value.strip()
    return secret_named(key) or prefix_class(v) != "unknown" or bool(VAULT_REF_RE.match(v))


def strip_scheme(value: str) -> str:
    v = value.strip()
    m = re.match(r"^(bearer|token|basic)\s+(.+)$", v, re.IGNORECASE)
    return m.group(2) if m else v


def describe(value: str, salt: str) -> dict:
    """The only view of a value any script may emit."""
    v = strip_scheme(value)
    if is_reference(v):
        return {"kind": "reference", "prefix_class": "n/a", "length": len(v), "fingerprint": None}
    return {"kind": "plaintext", "prefix_class": prefix_class(v), "length": len(v),
            "fingerprint": fingerprint(v, salt)}


def strip_userinfo(url: str) -> str:
    return URL_USERINFO_RE.sub(lambda m: m.group(1), url)


def mask_text(text: str, known: list[str], salt: str) -> tuple[str, int]:
    """Replace every known value, its base64 forms, token shapes, header values
    and URL credentials with <masked:...>. Returns (text, count)."""
    count = 0

    def tag(v: str) -> str:
        return f"<masked:{prefix_class(v)}:{fingerprint(v, salt)}>"

    variants: list[tuple[str, str]] = []
    for v in sorted({k for k in known if k and len(k) >= 6}, key=len, reverse=True):
        variants.append((v, tag(v)))
        for raw in (v, "x-access-token:" + v, ":" + v):
            b = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            variants.append((b.rstrip("="), tag(v)))
    for needle, rep in variants:
        if needle in text:
            count += text.count(needle)
            text = text.replace(needle, rep)

    def shape_sub(m: re.Match) -> str:
        nonlocal count
        count += 1
        return tag(m.group(0))

    text = SHAPE_RE.sub(shape_sub, text)

    def header_sub(m: re.Match) -> str:
        nonlocal count
        if m.group(4).startswith("<masked"):
            return m.group(0)
        count += 1
        return m.group(1) + m.group(2) + (m.group(3) or "") + tag(m.group(4))

    text = HEADER_RE.sub(header_sub, text)

    def url_sub(m: re.Match) -> str:
        nonlocal count
        if m.group(3) and not m.group(3).startswith("<masked"):
            count += 1
            return m.group(1) + "<user>:" + tag(m.group(3)) + "@"
        return m.group(1) + "<user>@"

    text = URL_USERINFO_RE.sub(url_sub, text)
    return text, count


def crash_report(exc: BaseException) -> None:
    """Report a crash by exception type and code location only.

    The message is never printed: a message can carry the value being
    processed (a repr, a format string, a request object)."""
    frames = traceback.extract_tb(exc.__traceback__)
    where = "; ".join(f"{os.path.basename(f.filename)}:{f.lineno} in {f.name}" for f in frames[-4:])
    sys.stderr.write(f"CRASH {type(exc).__name__} at {where} (message withheld: it may hold a value)\n")


def run_guarded(main, argv=None) -> int:
    try:
        return main(argv)
    except SystemExit as e:
        if isinstance(e.code, int):
            return e.code
        return NOT_RUN
    except BaseException as e:  # noqa: BLE001 - the whole point is to catch everything
        crash_report(e)
        return CRASH
