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
2. Injects relevant project context into Claude's reasoning
3. Auto-installs git post-commit hook (if `scripts/middleware/post_commit_graphiti.py` exists)
4. You get better answers without any extra interaction

### Two Backends

| Backend | Storage | Context Injection | Auto-update |
|---------|---------|-------------------|-------------|
| **YAML** (v1) | `.middleware/features.yaml` | Sonnet relay agent reads YAML | Manual or LLM extraction |
| **Graphiti KG** (v2) | Graphiti knowledge graph | `/middleware:ctx` queries KG | Post-commit hook auto-ingestion |

The backend is determined by `manifest.yaml`:
```yaml
# v1 (YAML)
backend: yaml

# v2 (Graphiti KG)
backend: graphiti
group_id: commercial_insight
```

## Skills

| Skill | Invocation | Backend | Purpose |
|---|---|---|---|
| brief | `/middleware:brief` | YAML | Deep analysis: relay + counter-questioning + plan synthesis |
| **ctx** | `/middleware:ctx` | **Graphiti** | **KG context injection + conflict detection** |

### `/middleware:ctx` (Graphiti KG backend)

```bash
# Bootstrap: load project architecture principles + constraints
/middleware:ctx

# Context + conflict detection for a specific task
/middleware:ctx "Add new API endpoint for CSV download"
```

**What it does:**
1. Queries Graphiti KG for architecture principles, constraints, design decisions
2. Searches for related modules and dependencies
3. Detects conflicts between your intent and existing design decisions
4. Injects ~3KB of targeted context (vs 580KB full YAML)

**Conflict detection** — automatically warns when your request conflicts with:
- `IS_PROHIBITED_IN` — forbidden patterns
- `MUST_VIA` — mandatory routing (e.g., all LLM calls must go through ClaudeClient)
- `REQUIRES_NOT_MODIFY` — locked files/paths
- `REQUIRES_FILTER` — mandatory data filters

### `/middleware:brief` (YAML backend)

For projects still using the YAML backend:
```bash
/middleware:brief "Add OAuth2 to the auth system"
```

5-phase workflow: Context Gathering -> Selective Code Reading -> Counter-Questioning -> Plan Synthesis -> Writing Plans

## Knowledge Cycle

```
/middleware:ctx              git commit
  (read from KG)              (write to KG)
       |                           |
       v                           v
  Claude Code  ----coding---->  post-commit hook
  gets context                  sends to Graphiti
       ^                           |
       |                           v
       +---- next session <--- KG enriched
```

The post-commit hook is **auto-installed** by the plugin when:
- `.middleware/manifest.yaml` has `backend: graphiti`
- `scripts/middleware/post_commit_graphiti.py` exists in the project

### Two-tier ingestion (post-commit)

| Tier | Content | LLM required | Failure rate |
|------|---------|--------------|--------------|
| **Tier 1** | git metadata, changed files, import diffs | No | 0% |
| **Tier 2** | diff summary, intent extraction | Yes (optional) | ~25% (graceful) |

Tier 1 always succeeds. Tier 2 failure doesn't block Tier 1 data.

## What is `.middleware/`?

A structured knowledge directory for your project:

```
.middleware/
├── manifest.yaml    # Phase, backend type, group_id
├── context.yaml     # Architecture, constraints, conventions (human-readable)
├── rules.yaml       # Code protection rules (locked/guarded/open)
├── hooks/           # pre-commit protection hook
├── plans/           # Work plan tracking
└── skills/          # Project-local skill overrides
```

**v1 (YAML)** also includes `features.yaml` (auto-extracted from commits) and `history/`.

**v2 (Graphiti KG)** replaces `features.yaml` and `history/` with the Graphiti knowledge graph, keeping `context.yaml` and `rules.yaml` as human-readable references.

## Requirements

- Claude Code CLI
- A project with `.middleware/` initialized
- For Graphiti backend: Graphiti MCP server connected

## License

MIT
