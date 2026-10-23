#!/bin/sh
# Check app slots before handing out work, and log a slot back in to DEV when its session expired.
# Usage: slots.sh status <slot_dir>...     one line per slot: <port> ready|login|down|unknown [build]
#        slots.sh relogin <slot_dir>...    for each slot not ready: pick DEV, press 「다시 시도」/「로그인」, wait up to 100 s.
#                                         Slots are handled ONE AT A TIME (parallel SSO answers get crossed).
#   <slot_dir> holds the slot's config.json (cdp = that slot's port), e.g. .slots/app-9334.
#   Sessions expire after a few idle hours, so run status before every assignment and after long pauses.
#   relogin never relaunches or quits an app; a slot that is down needs qa_rollout.sh.
# Exit 0 = every slot ready, 3 = some slot still not ready.
set -u
[ $# -ge 2 ] || { sed -n '2,9p' "$0"; exit 2; }
CMD=$1; shift
A=$(cd "$(dirname "$0")/../../worxsales-qa-executor/scripts" && pwd)/app.mjs
state() { # state <dir> -> sets PORT, ST
  CDP=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('cdp',''))" "$1/config.json" 2>/dev/null)
  PORT=${CDP##*:}
  if [ -z "$CDP" ] || ! curl -s -m 2 "$CDP/json/version" >/dev/null; then ST=down; return; fi
  T=$(QA_HOME=$1 CDP=$CDP timeout 30 node "$A" text body 2>/dev/null || true)
  case "$T" in *"역할 전환"*) ST=ready;; *"다시 시도"*|*"로그인"*) ST=login;; *) ST=unknown;; esac
}
rc=0
for D in "$@"; do
  [ -f "$D/config.json" ] || { echo "$D no config.json"; rc=3; continue; }
  state "$D"
  if [ "$CMD" = relogin ] && [ "$ST" = login ]; then
    export QA_HOME=$D CDP
    timeout 60 node "$A" click '{"text":"DEV","scope":"body"}' >/dev/null 2>&1 || true
    for t in 1 2 3 4 5 6 7 8 9 10; do
      T=$(timeout 30 node "$A" text body 2>/dev/null || true)
      case "$T" in *"역할 전환"*) break;;
        *"다시 시도"*) timeout 60 node "$A" click '{"role":"button","name":"다시 시도","scope":"body"}' >/dev/null 2>&1 || true;;
        *"로그인"*) timeout 60 node "$A" click '{"role":"button","name":"로그인","scope":"body"}' >/dev/null 2>&1 || true;; esac
      sleep 10
    done
    state "$D"
  fi
  B=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('build',''))" "$D/config.json" 2>/dev/null)
  echo "$PORT $ST $B"
  [ "$ST" = ready ] || rc=3
done
exit $rc
