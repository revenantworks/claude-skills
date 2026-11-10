#!/usr/bin/env bash
# Write this case's invented fixture vault into the run's working folder.
# The harness runs `bash <this file>` with --scaffold.
set -eu
mkdir -p sources/team/alpha sources/team/beta vault/raw/notes vault/wiki/repos vault/tools
mkdir -p vault/raw/snapshots/2026-10-01/team/alpha vault/raw/snapshots/2026-10-01/team/beta
printf '# Alpha\nAlpha builds the release bundles.\n' > vault/raw/snapshots/2026-10-01/team/alpha/README.md
printf '# Alpha\nAlpha builds the release bundles and signs them.\nIt now also publishes the docs site.\n' > sources/team/alpha/README.md
printf '# Beta\nBeta runs the nightly tests.\n' > vault/raw/snapshots/2026-10-01/team/beta/README.md
cp vault/raw/snapshots/2026-10-01/team/beta/README.md sources/team/beta/README.md
printf '# Living sources\nteam/alpha:README.md\nteam/beta:README.md\n' > vault/tools/snapshot-sources.txt
cat > vault/wiki/repos/alpha-tool.md <<'EOF'
---
sources:
  - raw/snapshots/2026-10-01/team/alpha/README.md
updated: 2026-10-01
---
# Alpha tool
Alpha builds the release bundles. See [[beta-tool]] and [[repos]].
EOF
cat > vault/wiki/repos/beta-tool.md <<'EOF'
---
sources:
  - raw/snapshots/2026-10-01/team/beta/README.md
updated: 2026-10-01
---
# Beta tool
Beta runs the nightly tests. See [[alpha-tool]].
EOF
printf '# Repos\n- [[alpha-tool]]\n- [[beta-tool]]\n' > vault/wiki/repos.md
printf '# Index\n- [[repos]]\n- [[alpha-tool]]\n- [[beta-tool]]\n' > vault/wiki/index.md
printf '# Log\n' > vault/wiki/log.md
printf '# Privacy signals\n' > vault/wiki/privacy-signals.md
