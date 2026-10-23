#!/bin/sh
# Read-only check of what a QA workspace needs on this Mac. Changes nothing, prints one line per item.
# Usage: check_env.sh <qa_home> [browser_cdp_port]
#   tools      node (>= 22 for the global WebSocket used by cdp_tab.mjs), python3, git, curl, timeout (coreutils), bws-run
#   secrets    bws key NAMES only (NOTION_API_KEY); values are never printed
#   repo       config.json desktop_repo / desktop_worktree / app_path
#   slots      every slot folder <qa_home>/.slots/app-<port> or config.json cdp: ready / login / down
#   browser    the user's browser CDP port (default 9222): open or closed
#   MatrixCloud ws://localhost:1040: open = MC app running and logged in; refused = not running;
#              an HTTP 503 on the upgrade = MC running but not logged in or not ready
#   Notion MCP  cannot be checked by a script; a reminder line is printed
# Exit 0 always; read the lines.
[ $# -ge 1 ] && [ "$1" != "-h" ] && [ "$1" != "--help" ] || { sed -n '2,12p' "$0"; exit 2; }
Q=$(cd "$1" && pwd); BP=${2:-9222}
EXE=$(cd "$(dirname "$0")/../../worxsales-qa-executor/scripts" && pwd)
say() { printf '%-12s %s\n' "$1" "$2"; }
for t in node python3 git curl timeout bws-run; do command -v $t >/dev/null 2>&1 && say tool "$t ok" || say tool "$t MISSING"; done
command -v node >/dev/null 2>&1 && say tool "node $(node -v)"
if command -v bws-catalog >/dev/null 2>&1; then
  bws-catalog 2>/dev/null | grep -q '\bNOTION_API_KEY\b' && say secret "NOTION_API_KEY registered" || say secret "NOTION_API_KEY not in bws catalog"
else say secret "bws-catalog missing (cannot check key names)"; fi
if [ -f "$Q/config.json" ]; then
  for k in desktop_repo desktop_worktree app_path scenario_db_id; do
    v=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$Q/config.json" $k)
    case $k in scenario_db_id) [ -n "$v" ] && say config "$k set" || say config "$k empty";;
      *) [ -n "$v" ] && [ -e "$v" ] && say config "$k ok" || say config "$k missing or not found";; esac
  done
else say config "config.json missing (run init_workspace.sh)"; fi
slot() { # slot <dir>
  P=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('cdp','http://127.0.0.1:9333'))" "$1/config.json")
  if ! curl -s -m 2 "$P/json/version" >/dev/null; then say slot "$P down"; return; fi
  T=$(QA_HOME=$1 CDP=$P timeout 30 node "$EXE/app.mjs" text body 2>/dev/null || true)
  case "$T" in *"역할 전환"*) say slot "$P ready";; *"로그인"*|*"다시 시도"*) say slot "$P login needed";; *) say slot "$P unknown screen";; esac
}
[ -f "$Q/config.json" ] && slot "$Q"
for d in "$Q"/.slots/app-*; do [ -f "$d/config.json" ] && slot "$d"; done
curl -s -m 2 "http://127.0.0.1:$BP/json/version" >/dev/null && say browser "CDP $BP open" || say browser "CDP $BP closed"
# websocket upgrade handshake only; curl gives up after 3 s and the code tells the state
C=$(curl -s -o /dev/null -m 3 -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: cWEtY2hlY2stZW52LXByb2Jl' http://localhost:1040/ 2>/dev/null || true)
case "$C" in 101) say matrix "MC open (running and accepting)";; 503) say matrix "MC 503: running but not logged in or not ready";;
  000|"") say matrix "MC not running (connection refused)";; *) say matrix "MC HTTP $C";; esac
say notion-mcp "not checkable here: read the parent page once with the session's Notion MCP tool (needed for 상황판 views)"
exit 0
