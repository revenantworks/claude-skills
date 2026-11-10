#!/usr/bin/env bash
# Write this case's invented fixture vault into the run's working folder.
# The harness runs `bash <this file>` with --scaffold.
set -eu
mkdir -p vault/raw/clips vault/raw/notes vault/wiki/topics vault/tools
cat > vault/CLAUDE.md <<'EOF'
# Vault rules
This vault is an LLM wiki. Claude maintains wiki/. The user curates raw/.
EOF
cat > vault/raw/clips/heat-pump-basics.md <<'EOF'
Heat pumps move heat instead of making it. A typical unit lasts about 15 years.
EOF
cat > vault/wiki/topics/heat-pumps.md <<'EOF'
---
sources:
  - raw/clips/heat-pump-basics.md
updated: 2026-10-01
---
# Heat pumps
Heat pumps move heat instead of making it. A typical unit lasts about 15 years.
See [[topics]].
EOF
cat > vault/wiki/topics.md <<'EOF'
# Topics
- [[heat-pumps]] how heat pumps work
EOF
cat > vault/wiki/index.md <<'EOF'
# Index
- [[topics]] hub
- [[heat-pumps]] how heat pumps work
EOF
printf '# Log\n## 2026-10-01 ingest | raw/clips/heat-pump-basics.md\n' > vault/wiki/log.md
printf '# Privacy signals\n' > vault/wiki/privacy-signals.md
cd vault
git init -q
git -c user.name=vault-test -c user.email=vault-test@users.noreply.github.com -c commit.gpgsign=false add -A
git -c user.name=vault-test -c user.email=vault-test@users.noreply.github.com -c commit.gpgsign=false commit -q -m "seed"
printf -- '---\nsources:\n  - raw/clips/heat-pump-basics.md\nupdated: 2026-11-01\n---\n# Heat pump noise\nSee [[heat-pumps]].\n' > wiki/topics/heat-pump-noise.md
printf -- '- [[heat-pump-noise]] how loud heat pumps are\n' >> wiki/index.md
printf -- '- [[heat-pump-noise]] how loud heat pumps are\n' >> wiki/topics.md
