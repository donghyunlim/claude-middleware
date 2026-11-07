#!/usr/bin/env bash
# Fetch the pstack Claude Code port at the commit the 2026-11-07 runs used.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$here/.cache/pstack-claude"
commit=df9bc05b818e2457ac23d3343e96e4ff284dd9e9   # pstack 0.9.132
if [ ! -d "$dest/.git" ]; then
  git clone -q https://github.com/michael-denyer/pstack-claude "$dest"
fi
git -C "$dest" fetch -q origin "$commit" 2>/dev/null || true
git -C "$dest" checkout -q "$commit"
echo "pstack $(cat "$dest/VERSION") at $dest/plugins/pstack"
