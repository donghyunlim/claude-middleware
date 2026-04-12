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

## Requirements

- Claude Code CLI
- A project with `.middleware/` initialized via the middleware server

## License

MIT
