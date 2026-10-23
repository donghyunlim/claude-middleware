#!/bin/sh
# (Re)launch the built app with a CDP port and wait until the workspace is past the auth screen.
# Usage: launch_app.sh   (reads app_path / cdp from $QA_HOME/config.json)
# For a single runner only. With parallel slots the orchestrator uses worxsales-qa-all-in-one's qa_rollout.sh instead.
# Only the app that listens on this config's CDP port is stopped; other WorxSales apps (other slots, a dev app) stay up.
# The session token lives only in memory: every relaunch needs SSO. If the browser still holds an SSO session,
# pressing 「다시 시도」 completes it; otherwise the user must log in in the browser window.
set -eu
QA_HOME=${QA_HOME:-$PWD}; HERE=$(cd "$(dirname "$0")" && pwd)
APP=$(python3 -c "import json;print(json.load(open('$QA_HOME/config.json'))['app_path'])")
PORT=$(python3 -c "import json;print(json.load(open('$QA_HOME/config.json')).get('cdp','http://127.0.0.1:9333').rsplit(':',1)[1])")
PID=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
if [ -n "$PID" ]; then
  kill "$PID"; i=0
  while kill -0 "$PID" 2>/dev/null && [ $i -lt 10 ]; do i=$((i+1)); sleep 1; done
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID" && sleep 2
fi
open -n "$APP" --args --remote-debugging-port="$PORT"
i=0; until curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null; do i=$((i+1)); [ $i -gt 20 ] && { echo "CDP not up"; exit 1; }; sleep 1; done
sleep 6
QA_HOME="$QA_HOME" node "$HERE/app.mjs" click '{"text":"DEV","scope":"body"}' >/dev/null 2>&1 || true
QA_HOME="$QA_HOME" node "$HERE/app.mjs" click '{"role":"button","name":"로그인","scope":"body"}' >/dev/null 2>&1 || true
for t in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 5
  TXT=$(QA_HOME="$QA_HOME" node "$HERE/app.mjs" text body 2>/dev/null || true)
  case "$TXT" in
    *"역할 전환"*) echo "ready"; exit 0 ;;
    *"다시 시도"*) QA_HOME="$QA_HOME" node "$HERE/app.mjs" click '{"role":"button","name":"다시 시도","scope":"body"}' >/dev/null 2>&1 || true ;;
  esac
done
echo "login needed: finish SSO in the browser window, then rerun"; exit 4
