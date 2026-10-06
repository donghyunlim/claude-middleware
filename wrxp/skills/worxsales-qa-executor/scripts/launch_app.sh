#!/bin/sh
# (Re)launch the built app with a CDP port and wait until the workspace is past the auth screen.
# Usage: launch_app.sh   (reads app_path / cdp from $QA_HOME/config.json)
# The session token lives only in memory: every relaunch needs SSO. If the browser still holds a Keycloak
# session, pressing 「다시 시도」 completes it; otherwise the user must log in in the browser window.
set -eu
QA_HOME=${QA_HOME:-$PWD}; HERE=$(cd "$(dirname "$0")" && pwd)
APP=$(python3 -c "import json;print(json.load(open('$QA_HOME/config.json'))['app_path'])")
PORT=$(python3 -c "import json;print(json.load(open('$QA_HOME/config.json')).get('cdp','http://127.0.0.1:9333').rsplit(':',1)[1])")
osascript -e 'quit app "WorxSales"' 2>/dev/null || true; sleep 2
open -n "$APP" --args --remote-debugging-port="$PORT"
i=0; until curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null; do i=$((i+1)); [ $i -gt 20 ] && { echo "CDP not up"; exit 1; }; sleep 1; done
for t in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 5
  TXT=$(QA_HOME="$QA_HOME" node "$HERE/app.mjs" text body 2>/dev/null || true)
  case "$TXT" in
    *"역할 전환"*) echo "ready"; exit 0 ;;
    *"다시 시도"*) QA_HOME="$QA_HOME" node "$HERE/app.mjs" click '{"role":"button","name":"다시 시도","scope":"body"}' >/dev/null 2>&1 || true ;;
  esac
done
echo "login needed: finish SSO in the browser window, then rerun"; exit 4
