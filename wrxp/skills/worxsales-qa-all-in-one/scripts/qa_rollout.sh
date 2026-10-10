#!/bin/sh
# Relaunch one idle QA app slot on the build recorded in <build.json> and log it in to DEV.
# Usage: qa_rollout.sh <port> <qa_home> <build.json>
#   build.json: {"app_path", "desktop_worktree", "build"} for the build to roll out (written by the orchestrator
#   after worxsales-qa-executor's build_dev_app.sh). Run only when no worker is using that slot.
# Port $QA_DEFAULT_PORT (default 9333) uses the app's default user-data dir; others use $QA_USERDATA_ROOT/<port>
# (default $qa_home/.userdata), so a slot keeps its login across relaunches.
# Exit 0 = logged in, 4 = login needs a person.
set -eu
PORT=$1; HOME_DIR=$(cd "$2" && pwd); BUILD_JSON=$3
A=$(cd "$(dirname "$0")/../../worxsales-qa-executor/scripts" && pwd)/app.mjs
eval "$(python3 -I -c "import json,sys,shlex;b=json.load(open(sys.argv[1]));print(' '.join(f'{k}={shlex.quote(b[j])}' for k,j in (('APP','app_path'),('WT','desktop_worktree'),('BUILD','build'))))" "$BUILD_JSON")"
PID=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
if [ -n "$PID" ]; then
  kill "$PID"; i=0
  while kill -0 "$PID" 2>/dev/null && [ $i -lt 10 ]; do i=$((i+1)); sleep 1; done
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID" && sleep 2  # some slots ignore SIGTERM (seen twice on 2026-10-10)
fi
if [ "$PORT" = "${QA_DEFAULT_PORT:-9333}" ]; then open -n "$APP" --args --remote-debugging-port=$PORT
else UD=${QA_USERDATA_ROOT:-$HOME_DIR/.userdata}; mkdir -p "$UD"; open -n "$APP" --args --remote-debugging-port=$PORT --user-data-dir="$UD/$PORT"; fi
i=0; until curl -s -m 2 http://127.0.0.1:$PORT/json/version >/dev/null; do i=$((i+1)); [ $i -gt 30 ] && { echo "CDP not up"; exit 1; }; sleep 1; done
python3 -I - "$HOME_DIR/config.json" "$APP" "$WT" "$BUILD" <<'PY'
import json,sys
p,app,wt,b=sys.argv[1:]; c=json.load(open(p)); c.update(app_path=app,desktop_worktree=wt,build=b); json.dump(c,open(p,'w'),ensure_ascii=False,indent=2)
PY
sleep 6; export QA_HOME=$HOME_DIR
node "$A" click '{"text":"DEV","scope":"body"}' >/dev/null 2>&1 || true
node "$A" click '{"role":"button","name":"로그인","scope":"body"}' >/dev/null 2>&1 || true
for t in 1 2 3 4 5 6 7 8 9 10; do sleep 5; T=$(node "$A" text body 2>/dev/null || true)
  case "$T" in *"역할 전환"*) echo "ready $BUILD"; exit 0;; *"다시 시도"*) node "$A" click '{"role":"button","name":"다시 시도","scope":"body"}' >/dev/null 2>&1 || true;; esac; done
echo "login needed"; exit 4
