---
type: regex
pattern: '<script\b|<link\b|@import|\bsrc\s*=|\bhref\s*=\s*["'']?https?://'
flags: i
match: not_contains
weight: 2
---
Nothing in the file loads from outside: no script, stylesheet link, import, src attribute or remote href.
