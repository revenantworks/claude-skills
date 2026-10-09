---
type: regex
pattern: 'prefill|<thinking>'
flags: i
match: not_contains
target: last_message
---
No Claude-only prefill or thinking-tag phrasing in the delivered prompt.
