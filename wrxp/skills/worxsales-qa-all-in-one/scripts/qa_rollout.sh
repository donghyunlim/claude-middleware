#!/bin/sh
# Relaunch one idle QA app slot on the build recorded in <build.json> and log it in to DEV.
# Usage: qa_rollout.sh <port> <slot_dir> <build.json>
#   build.json: {"app_path", "desktop_worktree", "build"} for the build to roll out (written by the orchestrator
#   after worxsales-qa-executor's build_dev_app.sh). Run only when no worker is using that slot.
#   <slot_dir> is the slot's settings folder (e.g. <QA_HOME>/.slots/app-<port>). If it or its config.json is missing
#   (a cleanup removed it), it is recreated from $QA_MAIN_CONFIG (default ./config.json, the workspace config).
#   config.json gets app_path / desktop_worktree / build and cdp=http://127.0.0.1:<port>.
# Every slot uses its own user-data dir $QA_USERDATA_ROOT/<port> (default ./.userdata), so slots never share a login
# and never collide with a dev app another session runs on the default profile. Set QA_DEFAULT_PORT=<port> only to
# keep an old slot on the default profile.
# Roll out slots one at a time: parallel SSO logins get crossed and stall at 「브라우저 인증 대기」.
# Exit 0 = logged in, 4 = login needs a person.
set -eu
[ $# -eq 3 ] || { sed -n '2,14p' "$0"; exit 2; }
PORT=$1; BUILD_JSON=$3
mkdir -p "$2"; HOME_DIR=$(cd "$2" && pwd)
A=$(cd "$(dirname "$0")/../../worxsales-qa-executor/scripts" && pwd)/app.mjs
eval "$(python3 -I -c "import json,sys,shlex;b=json.load(open(sys.argv[1]));print(' '.join(f'{k}={shlex.quote(b[j])}' for k,j in (('APP','app_path'),('WT','desktop_worktree'),('BUILD','build'))))" "$BUILD_JSON")"
[ -d "$APP" ] || { echo "app not built: $APP"; exit 1; }
PID=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
if [ -n "$PID" ]; then
  kill "$PID"; i=0
  while kill -0 "$PID" 2>/dev/null && [ $i -lt 10 ]; do i=$((i+1)); sleep 1; done
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID" && sleep 2  # some slots ignore SIGTERM (seen twice on 2026-10-10)
fi
if [ "$PORT" = "${QA_DEFAULT_PORT:-}" ]; then open -n "$APP" --args --remote-debugging-port=$PORT
else UD=${QA_USERDATA_ROOT:-$PWD/.userdata}; mkdir -p "$UD"; open -n "$APP" --args --remote-debugging-port=$PORT --user-data-dir="$UD/$PORT"; fi
i=0; until curl -s -m 2 http://127.0.0.1:$PORT/json/version >/dev/null; do i=$((i+1)); [ $i -gt 30 ] && { echo "CDP not up"; exit 1; }; sleep 1; done
python3 -I - "$HOME_DIR/config.json" "${QA_MAIN_CONFIG:-$PWD/config.json}" "$APP" "$WT" "$BUILD" "$PORT" <<'PY'
import json, os, sys
p, main, app, wt, b, port = sys.argv[1:]
src = p if os.path.exists(p) else main
c = json.load(open(src)) if os.path.exists(src) else {}
c.update(app_path=app, desktop_worktree=wt, build=b, cdp=f"http://127.0.0.1:{port}")
json.dump(c, open(p, "w"), ensure_ascii=False, indent=2)
PY
sleep 6; export QA_HOME=$HOME_DIR CDP=http://127.0.0.1:$PORT  # talk to this slot, not config.cdp (bug fixed 2026-10-11)
node "$A" click '{"text":"DEV","scope":"body"}' >/dev/null 2>&1 || true
node "$A" click '{"role":"button","name":"로그인","scope":"body"}' >/dev/null 2>&1 || true
for t in 1 2 3 4 5 6 7 8 9 10; do sleep 5; T=$(node "$A" text body 2>/dev/null || true)
  case "$T" in *"역할 전환"*) echo "ready $BUILD"; exit 0;; *"다시 시도"*) node "$A" click '{"role":"button","name":"다시 시도","scope":"body"}' >/dev/null 2>&1 || true;; esac; done
echo "login needed"; exit 4
