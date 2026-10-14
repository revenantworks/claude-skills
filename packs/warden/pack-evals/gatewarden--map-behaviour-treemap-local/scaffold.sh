#!/usr/bin/env bash
# Scaffold for behaviour-treemap-local: a small tree with uneven sizes.
set -euo pipefail
mkdir -p projects/alpha/assets projects/beta projects/gamma/build
head -c 2000000 /dev/zero > projects/alpha/assets/textures.bin
head -c 400000 /dev/zero > projects/beta/data.bin
head -c 900000 /dev/zero > projects/gamma/build/out.bin
