#!/bin/sh
# Build a dev-packaged WorxSales desktop app in a detached worktree (the user's checkout is never touched).
# Usage: build_dev_app.sh <desktop_repo> <worktree_dir> [api_origin]
#   api_origin defaults to https://worxsales-backend.dev.jobko.io (reachable on the internal network;
#   dev.worxphere.io did not resolve on 2026-10-06). If the origin is not in the app's packaged allowlist,
#   it is added in the worktree only — a local test build, never committed.
# Writes desktop_worktree / app_path / api_origin into $QA_HOME/config.json (QA_HOME defaults to cwd).
set -eu
REPO=$1; WT=$2; ORIGIN=${3:-https://worxsales-backend.dev.jobko.io}; QA_HOME=${QA_HOME:-$PWD}
git -C "$REPO" fetch -q origin
if [ -d "$WT" ]; then git -C "$WT" checkout -q --detach origin/develop -- 2>/dev/null || git -C "$WT" reset -q --hard origin/develop; else git -C "$REPO" worktree add -q --detach "$WT" origin/develop; fi
cd "$WT"
git checkout -q -- electron/auth/auth-config.cjs
if ! grep -q "\"$ORIGIN\"" electron/auth/auth-config.cjs; then
  python3 - "$ORIGIN" <<'PY'
import re, sys
p = "electron/auth/auth-config.cjs"; s = open(p).read()
s2 = re.sub(r"(const PACKAGED_API_ORIGINS = new Set\(\[\n)", lambda m: m.group(1) + f'  "{sys.argv[1]}",\n', s, count=1)
if s2 == s: sys.exit("PACKAGED_API_ORIGINS not found; update build_dev_app.sh")
open(p, "w").write(s2)
PY
fi
npm ci --no-audit --no-fund >/dev/null
npm run build >/dev/null
CSC_IDENTITY_AUTO_DISCOVERY=false npx electron-builder --dir -c.extraMetadata.worxsales.apiOrigin="$ORIGIN" >/dev/null
APP=$(ls -d "$WT"/release/mac*/WorxSales.app | head -1)
COMMIT=$(git -C "$WT" rev-parse --short HEAD)
python3 - "$QA_HOME/config.json" "$WT" "$APP" "$ORIGIN" "$COMMIT" <<'PY'
import json, os, sys
p, wt, app, origin, commit = sys.argv[1:]
c = json.load(open(p)) if os.path.exists(p) else {}
c.update(desktop_worktree=wt, app_path=app, api_origin=origin, build=f"desktop {commit} (+local allowlist {origin})", cdp=c.get("cdp", "http://127.0.0.1:9333"))
json.dump(c, open(p, "w"), ensure_ascii=False, indent=2)
PY
echo "$APP"
