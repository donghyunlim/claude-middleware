#!/bin/sh
# One-time: serve <remote_dir>/index.html over HTTP on a Mac reachable by ssh, as a per-user LaunchAgent (no sudo).
# Usage: serve_setup.sh <ssh_host> <remote_dir relative to remote home> <port>
# The server is serve_page.pl (core Perl only). The agent runs while that user is logged in and restarts if it exits.
set -eu
HOST=$1; DIR=$2; PORT=$3; LABEL=com.wrxp.qa-dashboard
ssh -o BatchMode=yes "$HOST" "mkdir -p '$DIR'"
ssh -o BatchMode=yes "$HOST" "cat > '$DIR/.serve_page.pl'" < "$(dirname "$0")/serve_page.pl"
ssh -o BatchMode=yes "$HOST" sh -s "$DIR" "$PORT" "$LABEL" <<'SH'
set -eu
DIR=$HOME/$1; PORT=$2; LABEL=$3; PLIST=$HOME/Library/LaunchAgents/$LABEL.plist
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
