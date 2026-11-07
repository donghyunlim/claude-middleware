#!/usr/bin/env python3
"""MCP stdio server exposing a tau2-bench domain's agent tools to Claude Code.

Env vars: TAU2_DOMAIN (retail|airline|...), TAU2_LOG (jsonl path).
Every call is appended to TAU2_LOG. Claude Code starts a new server process on
each resumed turn, so on start the server replays the log against a fresh
environment to restore the database state.
"""
import asyncio
import json
import os
import uuid

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from tau2.data_model.message import ToolCall
from tau2.registry import registry

DOMAIN = os.environ["TAU2_DOMAIN"]
LOG = os.environ["TAU2_LOG"]

env = registry.get_env_constructor(DOMAIN)()
TOOLS = {t.name: t for t in env.get_tools()}

if os.path.exists(LOG):
    for line in open(LOG):
        e = json.loads(line)
        env.get_response(ToolCall(id=e["id"], name=e["name"], arguments=e["arguments"]))

server = Server("tau2")


@server.list_tools()
async def list_tools():
    out = []
    for t in TOOLS.values():
        fn = t.openai_schema["function"]
        out.append(types.Tool(name=fn["name"], description=fn.get("description", ""), inputSchema=fn["parameters"]))
    return out


@server.call_tool()
async def call_tool(name, arguments):
    cid = uuid.uuid4().hex[:12]
    msg = env.get_response(ToolCall(id=cid, name=name, arguments=arguments or {}))
    with open(LOG, "a") as f:
        f.write(json.dumps({"id": cid, "name": name, "arguments": arguments or {}, "output": msg.content,
                            "error": msg.error}, ensure_ascii=False) + "\n")
    return [types.TextContent(type="text", text=msg.content or "")]


async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
