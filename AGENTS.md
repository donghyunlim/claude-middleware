# Middleware Plugin

Claude Code plugin that reads `.middleware/` project knowledge to amplify user intent before code work.

## Auto Mode

Automatically detects `.middleware/` via `UserPromptSubmit` hook. On every message:

1. **Hook** (`check-middleware.sh`) checks for `.middleware/` and reads `manifest.yaml`
2. Based on `backend` field, injects appropriate system message:
   - `yaml`: instructs Claude to use Sonnet relay agent for YAML reading
   - `graphiti`: instructs Claude to use `/middleware:ctx` for KG queries
3. Auto-installs git post-commit hook if `scripts/middleware/post_commit_graphiti.py` exists

## Skills

| Skill | Invocation | Backend | Purpose |
|-------|------------|---------|---------|
| brief | `/middleware:brief` | YAML | Deep analysis: relay + counter-questioning + plan synthesis |
| ctx | `/middleware:ctx` | Graphiti | KG context injection + conflict detection |

## How It Works

### YAML Backend (v1)
1. Hook injects systemMessage for Sonnet relay agent
2. Relay reads `.middleware/` YAML files and curates relevant data
3. Briefing used internally for better answers

### Graphiti KG Backend (v2)
1. Hook injects systemMessage for Graphiti queries
2. `/middleware:ctx` queries knowledge graph for principles, constraints, design decisions
3. Conflict detection checks intent against existing design decisions
4. Post-commit hook auto-ingests commit data to keep KG current

### Knowledge Cycle (Graphiti)
```
/middleware:ctx (read) -> Claude codes -> git commit -> post-commit hook (write) -> KG enriched -> next /ctx (read)
```

## Requirements

- A project with `.middleware/` directory initialized
- `.middleware/manifest.yaml` with `backend` and `group_id` fields
- For YAML: `features.yaml`, `rules.yaml`, `context.yaml`
- For Graphiti: Graphiti MCP server connected, `group_id` configured
