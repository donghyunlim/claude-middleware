# Middleware Plugin

Claude Code plugin that reads `.middleware/` project knowledge to amplify user intent before code work.

## Auto Mode

Automatically detects `.middleware/` via `UserPromptSubmit` hook. On every message, if `.middleware/` exists, the hook injects a system instruction for Claude to gather project context using a Sonnet relay agent. Zero visible interaction for the user.

## Skills

| Skill | Invocation | Purpose |
|-------|------------|---------|
| context | `/middleware:context` | Deep analysis: relay context + selective code reading + counter-questioning (1-20) + work plan + writing-plans transition |
| session-intent-inject | `/middleware:session-intent-inject` | Bridge MCP `session_search` and `POST /api/sessions/extract` — mines past Claude Code sessions for user-stated intents and injects them into `features.yaml` as `[session:*]` markers |

## How It Works

### context skill (auto + manual)
1. **Hook** (`check-middleware.sh`) runs on every user message
2. If `.middleware/` exists, hook injects a `systemMessage` instructing Claude to use the relay agent
3. Claude spawns a **Sonnet agent** that reads `.middleware/` YAML files and curates relevant data
4. The briefing is used internally — the user sees better answers without extra interaction
5. For deep analysis, invoke `/middleware:context` explicitly for counter-questioning and plan generation

### session-intent-inject skill (manual)
1. Resolve target project path (via `--project` or cwd); check middleware FastAPI server is up on port 8085
2. Call MCP `session_search` for 9 seed keywords (English + Korean imperatives)
3. Client-side filter: `projectPath` prefix + `/subagents/` exclusion + `role=user` + dedup
4. Dump survivors to `{project}/.middleware/history/session_hits_<ts>.jsonl`
5. `POST /api/projects/select` → `POST /api/sessions/extract`; server pipeline runs classifier (Opus + verbatim check) → merger → writes `features.yaml`
6. Report counter delta + verify via `grep -c "\[session:" features.yaml`

**When Claude should invoke this skill proactively**:
- User says "sync session intents" / "session 의도 추출" / "past conversation에서 지시사항 뽑아"
- Before large `/wrxp:breakdown` runs when `features.yaml` has no recent `[session:*]` markers
- After 30+ turn meta-conversations where the user expressed durable preferences

**When Claude should NOT invoke**:
- Server down (no `{"status":"ok"}` from `/api/health`)
- Target project lacks `.middleware/`
- Current `features.yaml` already answers the user's question

**Architectural rationale**: MCP `session_search` is only reachable from inside a live Claude Code session — FastAPI cannot call MCP as a subprocess because MCP is bound to the Claude Code host process. This skill is the bridge.

## Requirements

- A project with `.middleware/` directory initialized
- `.middleware/` should contain: `manifest.yaml`, `features.yaml`, `rules.yaml`, `context.yaml`
- Features schema version: 0.3 (session-intent-inject) / 0.2+ (context)
- For session-intent-inject: oh-my-claudecode plugin active (provides `mcp__plugin_oh-my-claudecode_t__session_search`)
