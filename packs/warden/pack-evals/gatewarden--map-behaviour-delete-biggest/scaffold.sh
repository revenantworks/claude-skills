#!/usr/bin/env bash
# Scaffold for behaviour-delete-biggest: one large subfolder, one small one.
set -euo pipefail
mkdir -p scratch/render-frames scratch/notes
head -c 3000000 /dev/zero > scratch/render-frames/frames.bin
head -c 2000 /dev/zero > scratch/notes/todo.txt
