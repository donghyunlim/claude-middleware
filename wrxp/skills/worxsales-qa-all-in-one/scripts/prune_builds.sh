#!/bin/sh
# Remove every QA build worktree except the one the slots now run, so builds do not pile up on disk.
# Usage: prune_builds.sh <desktop_repo> <keep_worktree>
# Run only after every app slot was rolled out to <keep_worktree> (a running app's files must not vanish).
# Removes worktrees that sit next to <keep_worktree> (same parent folder) and are named desktop-dev* or desktop-stg*;
# other worktrees of the repo (the user's checkout, unrelated folders) are never touched.
set -eu
REPO=$1; KEEP=$(cd "$2" && pwd -P); PARENT=$(dirname "$KEEP")
git -C "$REPO" worktree list --porcelain | sed -n 's/^worktree //p' | while read -r WT; do
  REAL=$(cd "$WT" 2>/dev/null && pwd -P || echo "$WT")
  [ "$REAL" = "$KEEP" ] && continue
  [ "$(dirname "$REAL")" = "$PARENT" ] || continue
  case "$(basename "$REAL")" in desktop-dev*|desktop-stg*) ;; *) continue;; esac
  git -C "$REPO" worktree remove --force "$WT" && echo "removed $WT"
done
git -C "$REPO" worktree prune
