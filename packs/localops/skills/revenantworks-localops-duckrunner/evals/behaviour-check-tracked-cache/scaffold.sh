#!/usr/bin/env bash
# Builds the fixture repo for this case: one CSV source and one committed Parquet cache.
set -euo pipefail
git init -q .
mkdir -p data
printf 'id,done\n1,true\n2,false\n' > data/a.csv
printf 'not a real parquet file\n' > data/cache.parquet
git add data/a.csv data/cache.parquet
git -c user.name=fixture -c user.email=fixture commit -q -m "fixture"
