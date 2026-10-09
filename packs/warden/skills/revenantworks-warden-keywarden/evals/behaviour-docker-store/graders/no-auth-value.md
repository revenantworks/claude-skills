---
type: regex
pattern: '"(auth|identitytoken|registrytoken|password)"\s*:\s*"[A-Za-z0-9+/=_.-]{8,}'
flags: i
match: not_contains
weight: 2
---
No inline `auths` value appears in the reply.
