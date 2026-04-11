# claude-middleware

Claude Code plugin that reads `.middleware/` project knowledge to amplify user intent and produce accurate work plans before any code work.

## Installation

```bash
claude plugin add github:donghyunlim/claude-middleware
```

## What it does

### Auto Mode (always on)

When you work in a project with a `.middleware/` directory, the plugin automatically:
1. Detects `.middleware/` on every message via a `UserPromptSubmit` hook
2. Spawns a Sonnet relay agent to read and curate project knowledge
3. Injects relevant context (features, constraints, anti-patterns, rules) into Claude's reasoning
4. You get better answers without any extra interaction

### Deep Mode (`/middleware:context`)

For complex tasks, invoke the deep analysis workflow:

```
/middleware:context "Add OAuth2 to the auth system"
```

This triggers a 5-phase workflow:
1. **Context Gathering** — Sonnet relay reads `.middleware/` and produces a briefing
2. **Selective Code Reading** — Reads relevant code files based on feature modules
3. **Counter-Questioning** — 1-20 targeted questions to clarify intent and catch oversights
4. **Plan Synthesis** — Structured work plan incorporating all gathered context
5. **Writing Plans** — Transitions to detailed implementation planning

## What is `.middleware/`?

A structured knowledge directory maintained by the [middleware server](https://github.com/donghyunlim/middleware):

- `features.yaml` — Feature definitions with anti-patterns, constraints, design decisions, domain knowledge
- `rules.yaml` — Code protection rules (locked/guarded/open paths)
- `context.yaml` — Project context (architecture, tech stack, constraints, conventions)
- `manifest.yaml` — Phase tracking and schema versions
- `history/` — Execution and extraction history

## Skills

| Skill | Invocation | Purpose |
|---|---|---|
| context | `/middleware:context` | Deep analysis: relay + selective code reading + counter-questioning (1-20) + plan synthesis + writing-plans transition |
| session-intent-inject | `/middleware:session-intent-inject` | Mine past Claude Code sessions for user-stated intents and inject them into `.middleware/features.yaml` as `[session:*]` markers |

### Session Intent Inject (v1.3.0+)

Past Claude Code session logs under `~/.claude/projects/*` contain user-stated decisions, constraints, and anti-patterns that never make it into commits. This skill bridges two subsystems that cannot talk directly:

- **MCP `session_search` tool** — reads session jsonl; only reachable from inside a Claude Code session
- **middleware FastAPI server** — runs the Phase 7 classifier pipeline; accepts a pre-dumped hits JSONL

The skill is the bridge: invoked from a Claude Code session, it can call MCP *and* `curl` the server in one shot.

**Workflow**:
1. Resolve target project (`--project` or cwd), check middleware server health
2. Call MCP `session_search` for 9 seed keywords (English + Korean imperatives: `always`, `never`, `must`, `because`, `instead`, `항상`, `절대`, `무조건`, `왜냐하면`)
3. Filter client-side: `projectPath` prefix + `/subagents/` exclusion + `role=user` + `(sessionId, line)` dedup
4. Dump survivors to `{project}/.middleware/history/session_hits_<ts>.jsonl`
5. `POST /api/projects/select` → `POST /api/sessions/extract`
6. Server pipeline clusters → classifies via Opus (verbatim check) → merges into `features.yaml` as:
   - `design_decisions[].rationale` with `dd-session-YYYYMMDD-<12hex>` id + `[session:*]` marker
   - `constraints[].reason` / `anti_patterns[].why_banned` / `domain_knowledge[].summary` with inline `[session:*]` markers

**Args**: `--project <path>`, `--dry-run`, `--seeds "a,b,c"`, `--keep-dump`, `--limit <N>`

**Requirements**: middleware server on port 8085, target project has `.middleware/`, MCP `session_search` tool available (oh-my-claudecode plugin active).

**When to use**: explicit user request to sync session intents; before large orchestration runs that depend on fresh `features.yaml`; after long meta-conversations where the user expressed preferences.

**When NOT to use**: server down; target has no `.middleware/`; current `features.yaml` already answers the question.

## Requirements

- Claude Code CLI
- A project with `.middleware/` initialized via the middleware server

## License

MIT
