#!/usr/bin/env bash
# Stage this case's fixture folders into the run's working folder.
# The harness runs `bash <this file>` with --scaffold; $0 is its path in the case folder.
set -eu
src="$(dirname "$0")"
cp -R "$src/page" ./page
