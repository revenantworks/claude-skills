#!/usr/bin/env python3
"""Lint a Claude Code workflow script (.js) against the documented file rules.

Standard library only. Reads one file, writes nothing, no network.

    python workflow_lint.py <workflow.js>

Exit 0 and "OK: <file>" when clean; exit 1 with one finding per line; exit 2 when the
file cannot be read. The rules mirror references/platform-facts.md (workflow format,
dated). When the platform changes the format, update that file first, then this lint.

Finding codes:
  META-FIRST      `export const meta = {...}` is not the first statement
  META-LITERAL    meta holds a variable, call, spread or template interpolation
  META-FIELD      meta lacks `name` or `description`
  PHASE-MISMATCH  a phase() title and the meta.phases titles do not match exactly
  BANNED-CALL     Date.now(), Math.random(), argless new Date(), import(), require()
  MODEL-LITERAL   a model is written into the script; pass it in through args
"""
import re
import sys

LITERAL_WORDS = {"true", "false", "null"}
BANNED = [
    (r"\bDate\s*\.\s*now\s*\(", "Date.now() throws in a workflow; pass a date in through args"),
    (r"\bMath\s*\.\s*random\s*\(", "Math.random() throws in a workflow; vary prompts by index"),
    (r"\bnew\s+Date\s*\(\s*\)", "argless new Date() throws in a workflow; pass a date in through args"),
    (r"(?<![\w$.])import\s*\(", "import() fails before the run starts; module loading is not allowed"),
    (r"(?<![\w$.])require\s*\(", "require() is not available; the script has no module loading"),
]


def mask(text):
    """Blank out comments and string contents, keeping delimiters and line breaks.

    Code inside a template literal's ${...} stays visible. Returns (masked, has_interp)
    where has_interp lists the offsets of every template interpolation start.
    """
    out = list(text)
    interps = []
    i, n = 0, len(text)
    stack = []  # brace depth markers for template interpolations

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def scan_template(i):
        # i points just after the opening backtick; returns index after the closing one
        start = i
        while i < n:
            c = text[i]
            if c == "\\":
                i += 2
                continue
            if c == "`":
                blank(start, i)
                return i + 1
            if c == "$" and i + 1 < n and text[i + 1] == "{":
                blank(start, i)
                interps.append(i)
                stack.append(0)
                return i + 2  # back to code inside the interpolation
            i += 1
        blank(start, n)
        return n

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            blank(i, j)
            i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            blank(i, j)
            i = j
        elif c in ("'", '"'):
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            blank(i + 1, min(j, n))
            i = j + 1
        elif c == "`":
            i = scan_template(i + 1)
        elif c == "{" and stack:
            stack[-1] += 1
            i += 1
        elif c == "}" and stack:
            if stack[-1] == 0:
                stack.pop()
                i = scan_template(i + 1)
            else:
                stack[-1] -= 1
                i += 1
        else:
            i += 1
    return "".join(out), interps


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def match_brace(masked, start):
    depth = 0
    for k in range(start, len(masked)):
        if masked[k] == "{":
            depth += 1
        elif masked[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return -1


def string_at(text, pos):
    m = re.match(r"\s*(['\"])(.*?)(?<!\\)\1", text[pos:])
    return m.group(2) if m else None


def lint(text):
    findings = []
    masked, interps = mask(text)

    head = re.match(r"\s*export\s+const\s+meta\s*=\s*\{", masked)
    if not head:
        findings.append("META-FIRST: the first statement must be `export const meta = {...}`")
        meta_span = None
    else:
        open_at = head.end() - 1
        close_at = match_brace(masked, open_at)
        meta_span = (open_at, close_at if close_at != -1 else len(masked))

    meta_titles = None
    if meta_span:
        a, b = meta_span
        body = masked[a:b + 1]
        reasons = []
        if "..." in body:
            reasons.append("spread")
        if "(" in body:
            reasons.append("call")
        if any(a <= p <= b for p in interps):
            reasons.append("template interpolation")
        for m in re.finditer(r"[A-Za-z_$][\w$]*", body):
            word = m.group(0)
            after = body[m.end():].lstrip()
            if after.startswith(":") or word in LITERAL_WORDS:
                continue
            reasons.append(f"identifier `{word}`")
            break
        if reasons:
            findings.append(f"META-LITERAL: meta must be a pure literal ({', '.join(reasons)}) (line {line_of(text, a)})")
        for field in ("name", "description"):
            if not re.search(rf"\b{field}\s*:", body):
                findings.append(f"META-FIELD: meta has no `{field}` (line {line_of(text, a)})")
        if re.search(r"\bphases\s*:", body):
            meta_titles = []
            for m in re.finditer(r"\btitle\s*:", body):
                title = string_at(text, a + m.end())
                if title is not None:
                    meta_titles.append(title)

    calls = []
    for m in re.finditer(r"(?<![\w$.])phase\s*\(", masked):
        title = string_at(text, m.end())
        if title is not None:
            calls.append((title, m.start()))
    if meta_titles is not None:
        for title, pos in calls:
            if title not in meta_titles:
                findings.append(f"PHASE-MISMATCH: phase('{title}') has no meta.phases entry (line {line_of(text, pos)})")
        called = {t for t, _ in calls}
        for title in meta_titles:
            if title not in called:
                findings.append(f"PHASE-MISMATCH: meta.phases lists '{title}' but no phase() call uses it")

    for pattern, why in BANNED:
        for m in re.finditer(pattern, masked):
            findings.append(f"BANNED-CALL: {why} (line {line_of(text, m.start())})")

    for m in re.finditer(r"\bmodel\s*:\s*['\"`]", masked):
        findings.append(f"MODEL-LITERAL: pass the model in through args, never as a literal (line {line_of(text, m.start())})")

    return findings


def main(argv):
    if len(argv) != 2:
        print("usage: python workflow_lint.py <workflow.js>")
        return 2
    path = argv[1]
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"cannot read {path}: {exc.strerror}")
        return 2
    findings = lint(text)
    for f in findings:
        print(f)
    if findings:
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
