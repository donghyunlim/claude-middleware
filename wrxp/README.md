# wrxp

Intent refinement + recursive decomposition + dynamic agent matching + DAG-based autonomous execution for Claude Code.

## What is this?

wrxp is a Claude Code plugin that breaks down complex requests into manageable tasks, dynamically matches them to the best available agents, and executes them in parallel using DAG-based scheduling.

**Core philosophy**: The main AI (Opus) orchestrates only. Code reading, analysis, and execution are fully delegated to specialist agents, preserving the orchestrator's context window.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **breakdown** | `/wrxp:breakdown "request"` | Full pipeline: intent refinement → decomposition → agent matching → autonomous execution |
| **decompose** | `/wrxp:decompose "problem"` | Intent clarification + recursive task tree decomposition |
| **agent-match** | `/wrxp:agent-match "task list"` | Dynamic agent selection + dependency DAG construction |

Each skill can be used independently or composed together.

## Installation

```bash
claude plugin add donghyunlim/wrxp
```

## How It Works

```
User request
  → Phase 1: Project context scan + AskUserQuestion (ambiguity removal)
  → Phase 2: Recursive decomposition + tree visualization + user approval
  → Phase 3: Dynamic agent matching + middleware knowledge injection + DAG
  → Phase 4: Parallel execution (wave-based) + reliability feedback
  → Phase 5: Result integration + summary
```

### Key Features

- **Recursive decomposition**: Unlimited depth, trust Opus as coordinator
- **Dynamic agent discovery**: No hardcoded agent list — discovers available agents at runtime
- **Middleware integration**: Injects project domain knowledge (features, design decisions) into agent prompts. Falls back to git log + code search when `.middleware/` is absent
- **DAG-based parallelism**: Independent tasks run simultaneously, dependencies are sequenced
- **Reliability feedback**: Multi-agent cross-validation with majority vote (critic wins ties)
- **Single-task fast-path**: Skips decomposition for atomic tasks, all other phases preserved
- **User escalation**: Critical design issues surface to user immediately; failures escalate rather than auto-retry

## Composable Design

```
/breakdown = /decompose → /agent-match → autonomous execution
```

- `/decompose` outputs a task tree (`.wrxp/state/tree-{slug}.json`)
- `/agent-match` consumes the tree and outputs a DAG (`.wrxp/state/dag-{slug}.json`)
- `/breakdown` orchestrates both and executes the DAG

## State Files

```
.wrxp/state/
├── intent-{slug}.md          # Refined intent document
├── tree-{slug}.json          # Decomposition tree
├── dag-{slug}.json           # Agent-matched DAG with waves
├── execution-{slug}.json     # Execution progress
└── breakdown-{slug}.json     # Pipeline state
```

## License

MIT
