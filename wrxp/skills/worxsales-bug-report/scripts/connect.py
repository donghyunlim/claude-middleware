#!/usr/bin/env python3
"""Register the WorxSales bug-report MCP server in Claude Code and/or Codex.

The personal access key comes from the WXBR_KEY environment variable and is never printed.
The edge certificate is self-signed, so this script fetches it, checks its SHA-256 fingerprint
against the pinned value, saves it, and gives only this MCP server a NODE_EXTRA_CA_CERTS that
trusts it (through mcp-remote over stdio). No global shell or trust-store change is made.

Usage: WXBR_KEY=wxbrm_... python3 connect.py --target claude|codex|both [--check-only]
Exit codes: 0 ok, 1 verification failed, 2 usage or environment error.
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOST, PORT = "172.16.111.17", 18443
MCP_URL = f"https://{HOST}:{PORT}/bugs/mcp"
DASHBOARD_URL = f"https://{HOST}:{PORT}/bugs/app"
# SHA-256 of the DER certificate served by the edge (CN=stt-mcp-serverroom, valid until 2036-09-28).
PINNED_SHA256 = "98A60CC5B07A77C66E99778F9389729E821D72C40B29BA85AC95994DAD489A2B"
SERVER_NAME = "worxsales-bug-report"
MCP_REMOTE = "mcp-remote@0.14.3"
CA_PATH = Path.home() / ".config" / "worxsales" / "edge-ca.pem"


def fail(code, message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def fetch_certificate():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # verified below by the pinned fingerprint instead
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=HOST) as tls:
                der = tls.getpeercert(binary_form=True)
    except OSError as exc:
        fail(2, f"cannot reach {HOST}:{PORT} ({exc}); connect to the company network or VPN first")
    digest = hashlib.sha256(der).hexdigest().upper()
    if digest != PINNED_SHA256:
        fail(1, f"edge certificate fingerprint {digest} does not match the pinned value; stop and tell the admin")
    return ssl.DER_cert_to_PEM_cert(der)


def save_certificate(pem):
    CA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CA_PATH.exists() or CA_PATH.read_text() != pem:
        CA_PATH.write_text(pem)
    print(f"certificate: {CA_PATH}")


def check_key(key):
    ctx = ssl.create_default_context(cafile=str(CA_PATH))
    ctx.check_hostname = False  # the certificate is pinned; its SAN lists the IP but Python matches it inconsistently
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "list_reports", "arguments": {"limit": 1}}}).encode()
    req = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            payload = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        fail(1, f"the server rejected the key (HTTP {exc.code}); ask the admin for a new key")
    except OSError as exc:
        fail(2, f"MCP request failed ({exc})")
    try:
        answer = json.loads(payload)
    except ValueError:
        fail(1, "unexpected MCP response; ask the admin to check the server")
    if "error" in answer or answer.get("result", {}).get("isError"):
        fail(1, "the key was accepted but list_reports failed; ask the admin to check the key")
    print("key: ok (list_reports answered)")


def launch_args():
    return ["npx", "-y", MCP_REMOTE, MCP_URL, "--header", "Authorization:${WXBR_AUTH}", "--transport", "http-only"]


def run(cmd, secret_env):
    # The key is passed as an argument to the CLI that stores it in its own config; never echo the command.
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    out = (result.stdout + result.stderr).replace(secret_env, "***")
    return result.returncode, out.strip()


def register_claude(key):
    if not shutil.which("claude"):
        fail(2, "claude CLI not found")
    auth = f"Bearer {key}"
    run(["claude", "mcp", "remove", "-s", "user", SERVER_NAME], key)
    code, out = run(["claude", "mcp", "add", "-s", "user", SERVER_NAME,
                     "-e", f"NODE_EXTRA_CA_CERTS={CA_PATH}", "-e", f"WXBR_AUTH={auth}", "--", *launch_args()], key)
    if code != 0:
        fail(1, f"claude mcp add failed: {out}")
    print("claude: registered (user scope); restart Claude Code to load it")


def register_codex(key):
    if not shutil.which("codex"):
        fail(2, "codex CLI not found")
    auth = f"Bearer {key}"
    run(["codex", "mcp", "remove", SERVER_NAME], key)
    code, out = run(["codex", "mcp", "add", SERVER_NAME,
                     "--env", f"NODE_EXTRA_CA_CERTS={CA_PATH}", "--env", f"WXBR_AUTH={auth}", "--", *launch_args()], key)
    if code != 0:
        fail(1, f"codex mcp add failed: {out}")
    print("codex: registered; start a new Codex session to load it")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=["claude", "codex", "both"], required=True)
    parser.add_argument("--check-only", action="store_true", help="verify certificate and key without registering")
    args = parser.parse_args()
    key = os.environ.get("WXBR_KEY", "").strip()
    if not key.startswith("wxbrm_"):
        fail(2, "set WXBR_KEY to the personal access key (it starts with wxbrm_)")
    save_certificate(fetch_certificate())
    check_key(key)
    if args.check_only:
        return
    if not shutil.which("npx"):
        fail(2, "npx (Node.js) not found; install Node.js first")
    if args.target in ("claude", "both"):
        register_claude(key)
    if args.target in ("codex", "both"):
        register_codex(key)
    print(f"dashboard: {DASHBOARD_URL} (log in with the same key under 「접근 키로 로그인」)")


if __name__ == "__main__":
    main()
