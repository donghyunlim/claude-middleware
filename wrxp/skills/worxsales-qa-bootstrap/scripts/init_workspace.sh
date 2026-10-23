#!/bin/sh
# Create (or complete) a WorxSales QA workspace skeleton. Never overwrites an existing file.
# Usage: init_workspace.sh <qa_home> [--wrappers-only]
#   Folders: sources/ scenarios/ runs/ refresh/ docs/ scripts/
#   Templates (only when missing): config.json, refresh/{watch,code_map,lanes,write_scope}.json,
#     scenarios/GUIDE.md (from references/scenario-guide.md), scenarios/menus.json, docs/DB_만들기.md
#   Wrappers (always rewritten, they hold this plugin version's skill paths):
#     scripts/run.sh   <script.py> args...  python3 -I with cwd = workspace (any script path)
#     refresh/run.sh   <script.py> args...  worxsales-qa-refresh/scripts/<script.py>
#     refresh/run_dash.sh <script.py> args... worxsales-qa-dashboard-update/scripts/<script.py>
#   bws-run re-splits quoted arguments, so Notion scripts always go through these wrappers:
#     bws-run "$PWD/refresh/run.sh" crawl.py refresh/watch.json "$S"
#   After a plugin update, run again with --wrappers-only so the wrappers point at the new version.
set -eu
[ $# -ge 1 ] && [ "$1" != "-h" ] && [ "$1" != "--help" ] || { sed -n '2,13p' "$0"; exit 2; }
Q=$1; ONLY=${2:-}
HERE=$(cd "$(dirname "$0")/.." && pwd); SKILLS=$(dirname "$HERE"); A=$HERE/assets
mkdir -p "$Q"; Q=$(cd "$Q" && pwd)
wrap() { # wrap <file> <script dir or empty>
  if [ -n "$2" ]; then
    printf '#!/bin/sh\n# bws-run wrapper: %s <script.py> args...  (written by worxsales-qa-bootstrap init_workspace.sh)\ncd "$(dirname "$0")/.." && S=$1 && shift && exec python3 -I "%s/$S" "$@"\n' "$(basename "$1")" "$2" > "$1"
  else
    printf '#!/bin/sh\n# bws-run wrapper: bws-run re-splits quoted args, so pass everything through this script.\ncd "$(dirname "$0")/.." && exec python3 -I "$@"\n' > "$1"
  fi
  chmod +x "$1"; echo "wrapper $1"
}
mkdir -p "$Q/scripts" "$Q/refresh"
wrap "$Q/scripts/run.sh" ""
wrap "$Q/refresh/run.sh" "$SKILLS/worxsales-qa-refresh/scripts"
wrap "$Q/refresh/run_dash.sh" "$SKILLS/worxsales-qa-dashboard-update/scripts"
[ "$ONLY" = "--wrappers-only" ] && exit 0
for d in sources scenarios runs docs; do mkdir -p "$Q/$d"; done
put() { # put <src> <dst>
  if [ -e "$2" ]; then echo "kept $2"; else cp "$1" "$2"; echo "created $2"; fi
}
put "$A/config.json" "$Q/config.json"
for f in watch code_map lanes write_scope; do put "$A/$f.json" "$Q/refresh/$f.json"; done
put "$A/menus.json" "$Q/scenarios/menus.json"
put "$HERE/references/scenario-guide.md" "$Q/scenarios/GUIDE.md"
put "$A/DB_만들기.md" "$Q/docs/DB_만들기.md"
echo "next: fill config.json and refresh/watch.json (see references/workspace.md)"
