# Middleware Plugin

Claude Code plugin that reads `.middleware/` project knowledge to amplify user intent before code work.

## Auto Mode

Automatically detects `.middleware/` via `UserPromptSubmit` hook. On every message, if `.middleware/` exists, the hook injects a system instruction for Claude to gather project context using a Sonnet relay agent. Zero visible interaction for the user.

## Skills

| Skill | Invocation | Purpose |
|-------|------------|---------|
| context | `/middleware:context` | Deep analysis: relay context + selective code reading + counter-questioning (1-20) + work plan + writing-plans transition |

## How It Works

1. **Hook** (`check-middleware.sh`) runs on every user message
2. If `.middleware/` exists, hook injects a `systemMessage` instructing Claude to use the relay agent
3. Claude spawns a **Sonnet agent** that reads `.middleware/` YAML files and curates relevant data
4. The briefing is used internally — the user sees better answers without extra interaction
5. For deep analysis, invoke `/middleware:context` explicitly for counter-questioning and plan generation

## Requirements

- A project with `.middleware/` directory initialized
- `.middleware/` should contain: `manifest.yaml`, `features.yaml`, `rules.yaml`, `context.yaml`
- Features schema version: 0.2
