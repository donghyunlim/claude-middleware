---
name: session-intent-inject
description: "Use to mine past Claude Code session logs for user-stated decisions/constraints/anti-patterns and inject them into .middleware/features.yaml as dd-session-* entries. Bridges the MCP session_search tool (only available in Claude Code sessions) and the middleware FastAPI server (which cannot call MCP directly). Invoke /middleware:session-intent-inject explicitly when the user asks to refresh session-derived intents."
schema_version: "0.2"
allowed-tools: [Read, Write, Glob, Grep, Bash, AskUserQuestion]
---

# Session Intent Inject Skill

Purpose: route user intent that lives in past conversation history — not in code or commits — into `.middleware/features.yaml` so that future middleware context injection sees it.

This skill is the bridge between two subsystems that cannot talk directly:
- **MCP `session_search` tool** — reads `~/.claude/projects/...` session jsonl; only available inside a live Claude Code session
- **middleware FastAPI server** — runs the classifier pipeline (`server/session_pipeline.py`); accepts a pre-dumped hits JSONL and produces `dd-session-*` design decisions

Claude (the caller of this skill) is the intermediary: it queries MCP, filters results, writes JSONL, and POSTs to the server.

## Preconditions (fail fast)

1. `.middleware/features.yaml` exists in the target project (Glob)
2. middleware FastAPI server is up on `localhost:8085` (`curl /api/health` returns `{"status":"ok"}`)
3. MCP tool `mcp__plugin_oh-my-claudecode_t__session_search` is available in the current session (oh-my-claudecode plugin active)

If any precondition fails, report the exact missing piece and stop. Do not proceed silently.

## Workflow

### Step 1 — Resolve target project

Parse args for `--project <path>`. Default: current working directory (`pwd`).

Validate:
- `${TARGET}/.middleware/features.yaml` must exist
- `${TARGET}` must be resolved to an absolute path (use `realpath`), and this value becomes `TARGET_CWD` for the projectPath prefix filter

### Step 2 — Health check

```bash
curl -s -m 3 http://localhost:8085/api/health
```

Expected: `{"status":"ok"}`. On failure, instruct the user to start the server (`cd <middleware> && bash serve.sh`) and stop.

### Step 3 — Select project on the server

```bash
curl -s -X POST http://localhost:8085/api/projects/select \
  -H 'Content-Type: application/json' \
  -d "{\"path\": \"${TARGET_CWD}\"}"
```

This is idempotent. Without this step, `/api/sessions/extract` returns 409.

### Step 4 — Collect hits via MCP session_search

Call `mcp__plugin_oh-my-claudecode_t__session_search` once per seed keyword. Default seed set (9 terms covering Korean and English imperative patterns):

- English: `always`, `never`, `must`, `because`, `instead`
- Korean: `항상`, `절대`, `무조건`, `왜냐하면`

Override via `--seeds "a,b,c"`. Per-call parameter: `limit: 200`.

Accumulate all raw hits into one list: `RAW_HITS`.

### Step 5 — Client-side filter

For each hit, apply in order:

1. **projectPath prefix** — `hit.projectPath.startswith(TARGET_CWD)` must be True. This excludes umbrella sessions (`cwd=donny` while target is `donny/middleware`) and sessions from sibling projects.
2. **Subagent guard** — `"/subagents/" in hit.sourcePath` → drop. Subagent transcripts contain instructions from one Claude to another; treating them as user intent would create a feedback loop.
3. **Role filter** — `hit.role == "user"` → must be True. Assistant/tool messages are noise.
4. **Dedup** — key by `(sessionId, line)` tuple.

Count survivors: `KEPT_HITS`. If `KEPT_HITS == 0`:
- If `RAW_HITS > 0`: likely the filter is too strict. Show a sample of rejected hits grouped by reason and suggest `--project` adjustment or `--seeds` expansion.
- If `RAW_HITS == 0`: no session data matches. Suggest waiting until the user has more past sessions about the target project, or confirm the target path.

### Step 6 — Dump filtered hits to JSONL

Write to `${TARGET_CWD}/.middleware/history/session_hits_<UTC-timestamp>.jsonl`. Ensure the `history/` directory exists (it does if manifest phase >= 2).

Format: one JSON object per line with keys the server expects (camelCase, matching `SessionHit` field names in `server/main.py:extract_session_intents`):
```
{"sessionId": "...", "line": 0, "projectPath": "...", "sourcePath": "...",
 "excerpt": "...", "role": "user", "timestamp": "2026-04-11T..."}
```

Store the path as `DUMP_PATH`.

### Step 7 — Dry-run short-circuit

If `--dry-run` flag is present, stop here and report:
- `RAW_HITS`, `KEPT_HITS`, `DUMP_PATH`
- Projected pipeline cost estimate: `KEPT_HITS // 3` clusters × ~$0.05 per cluster (Opus)

Do NOT call `/api/sessions/extract` in dry-run mode. The user may inspect the JSONL before proceeding.

### Step 8 — Trigger extraction pipeline

```bash
curl -s -X POST http://localhost:8085/api/sessions/extract \
  -H 'Content-Type: application/json' \
  -d "{\"hits_jsonl_path\": \"${DUMP_PATH}\"}"
```

Parse the JSON response. Expected fields:
- `total_hits`, `filtered`, `clusters`, `classified`
- `merged_inserted`, `merged_deduped`, `merged_skipped`
- `verbatim_violations`, `cost_usd`, `duration_ms`

### Step 9 — Verify and report

Count `[session:` markers in features.yaml before and after (use `grep -c "\[session:"`). The marker appears in all four categories:
- `design_decisions[*].rationale` → also tagged with `dd-session-*` ID prefix
- `constraints[*].reason` → inline marker only
- `anti_patterns[*].why_banned` → inline marker only
- `domain_knowledge[*].summary` → inline marker only

Do NOT count only `dd-session-*` — that would miss constraint/anti-pattern/domain-knowledge insertions, which the classifier may choose depending on the hit's category.

Report table:

```
| metric              | value |
|---------------------|-------|
| raw hits (MCP)      | N     |
| kept after filter   | N     |
| clusters            | N     |
| classified          | N     |
| merged_inserted     | N     |
| merged_deduped      | N     |
| merged_skipped      | N     |
| verbatim_violations | N     |
| cost_usd            | $N    |
| duration_ms         | N     |
| [session: before    | N     |
| [session: after     | N     |
| [session: delta     | +N    |
```

Warnings (surface these explicitly, do not bury):
- `verbatim_violations > 0` → ⚠️ LLM broke the verbatim substring rule. Pipeline dropped the offending clusters but the cause should be investigated (server log: `journalctl -u middleware-server` or `/tmp/middleware-server.log`).
- `classified > 0 && merged_inserted == 0 && merged_deduped == 0` → all classifications went to `merged_skipped`. Either the target feature slug was wrong (classifier picked a slug that doesn't exist in `features.yaml`) or merger-side defense-in-depth rejected quotes.
- `total_hits > 0 && classified == 0` → classifier returned `skip` for everything. Likely the cluster prompt is biased against the current data; consider adjusting the classifier prompt (`server/session_classifier.py:CLASSIFIER_SYSTEM_PROMPT`).

### Step 10 — Cleanup

Unless `--keep-dump` is set, delete `DUMP_PATH` after successful report. The JSONL was a one-shot input; keeping it invites stale reuse.

## Args reference

| Flag | Default | Meaning |
|---|---|---|
| `--project <path>` | cwd | Target project directory (must contain `.middleware/`) |
| `--dry-run` | off | Stop after Step 7 (dump only, no pipeline call) |
| `--seeds "a,b,c,..."` | default 9 | Override seed keyword list |
| `--keep-dump` | off | Preserve JSONL dump after success (debugging) |
| `--limit <N>` | 200 | `session_search` limit per seed call |

## Why this skill exists (architectural note)

Phase 7 of middleware delivered the classifier pipeline (`server/session_{search,filter,cluster,classifier,merger,pipeline}.py`) plus `POST /api/sessions/extract`, but the endpoint only accepts a **pre-dumped** JSONL file. The MCP `session_search` tool that would populate that JSONL is only reachable from inside a Claude Code session — FastAPI cannot call it as a subprocess because MCP is bound to the hosting Claude process, not the shell.

This skill fills that gap: a Claude Code session, invoking this skill, has access to both MCP (to collect hits) and Bash/curl (to POST to the server), so it can complete the round trip in one shot.

Originally the plan was to fold this into `wrxp:breakdown`'s Phase 1 context collection (the "7g" deferred task). Splitting it into a standalone skill avoids coupling the bridge to any one orchestration framework — breakdown can still invoke it later.

## Error handling reference

| Situation | Response |
|---|---|
| `.middleware/` missing | Tell user to `bash init.sh` in the target dir, stop |
| Server returns connection refused | Tell user to `bash serve.sh`, stop |
| Server returns 409 | Step 3 was skipped or the server lost state — call `/api/projects/select` and retry once |
| MCP tool not loaded | Likely oh-my-claudecode plugin inactive — stop, ask user to verify |
| 0 kept hits, non-zero raw hits | Show filter breakdown (how many dropped by prefix / subagent / role / dedup) |
| `verbatim_violations > 0` | Log a warning with exact count and suggest inspecting the server log |
| curl exit code ≠ 0 | Capture stderr, show to user, stop |

## What this skill does NOT do

- **Does not parse or classify hits** — the server pipeline owns that (Phase 7 `session_classifier.py`)
- **Does not write to `features.yaml` directly** — the server owns `_features_lock` and atomic writes
- **Does not install or configure the server** — assumes server is already running
- **Does not support projects whose session jsonl lacks cwd-matching `projectPath`** — if a user ran Claude Code from an umbrella directory, sessions may be invisible to this skill's prefix filter. Document this as a known limitation rather than working around it.
