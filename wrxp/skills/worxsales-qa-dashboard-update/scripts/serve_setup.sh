#!/bin/sh
# One-time: serve <dir>/index.html over HTTP on this Mac or a Mac reachable by ssh, as a per-user LaunchAgent (no sudo).
# Usage: serve_setup.sh <ssh_host|local> <dir relative to that user's home> <port>
#        serve_setup.sh --remove <ssh_host|local> <dir>   # stop the agent and delete its plist, log and served files
# The server is serve_page.pl (core Perl only). The agent runs while that user is logged in and restarts if it exits.
set -eu
LABEL=com.wrxp.qa-dashboard
on() { h=$1; shift; if [ "$h" = local ]; then (cd "$HOME" && sh -c "$*"); else ssh -o BatchMode=yes "$h" "$*"; fi; }
if [ "$1" = --remove ]; then
  HOST=$2; DIR=$3
  on "$HOST" "launchctl bootout gui/\$(id -u)/$LABEL 2>/dev/null; rm -f ~/Library/LaunchAgents/$LABEL.plist ~/Library/Logs/$LABEL.log '$DIR/index.html' '$DIR/.index.html.tmp' '$DIR/.serve_page.pl'; rmdir '$DIR' 2>/dev/null; echo removed"
  exit 0
fi
HOST=$1; DIR=$2; PORT=$3
on "$HOST" "mkdir -p '$DIR' && cat > '$DIR/.serve_page.pl'" < "$(dirname "$0")/serve_page.pl"
if [ "$HOST" = local ]; then RUN="sh -s"; else RUN="ssh -o BatchMode=yes $HOST sh -s"; fi
$RUN "$DIR" "$PORT" "$LABEL" <<'SH'
set -eu
cd "$HOME"; DIR=$HOME/$1; PORT=$2; LABEL=$3; PLIST=$HOME/Library/LaunchAgents/$LABEL.plist
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
[ -f "$DIR/index.html" ] || echo '<!doctype html><meta charset="utf-8"><title>WorxSales QA 진척판</title><p>아직 게시 전입니다.</p>' > "$DIR/index.html"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>Label</key><string>$LABEL</string>
 <key>ProgramArguments</key><array><string>/usr/bin/perl</string><string>$DIR/.serve_page.pl</string><string>$DIR</string><string>$PORT</string></array>
 <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
 <key>StandardErrorPath</key><string>$HOME/Library/Logs/$LABEL.log</string>
</dict></plist>
PL
launchctl bootout gui/$(id -u)/$LABEL 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST"
i=0; until curl -s -o /dev/null http://127.0.0.1:$PORT/; do i=$((i+1)); [ $i -gt 10 ] && { echo "not serving; see ~/Library/Logs/$LABEL.log"; exit 1; }; sleep 1; done
echo "serving $DIR/index.html on :$PORT"
SH
