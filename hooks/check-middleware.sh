#!/bin/bash
# Detect .middleware/ directory and inject context instruction via systemMessage.
# Runs on every UserPromptSubmit. Exits silently if no .middleware/ found.

MIDDLEWARE_DIR="${CLAUDE_PROJECT_DIR:-.}/.middleware"

if [ ! -d "$MIDDLEWARE_DIR" ]; then
  exit 0
fi

# Read phase from manifest (default 0 if unreadable)
PHASE=0
if [ -f "$MIDDLEWARE_DIR/manifest.yaml" ]; then
  PHASE=$(grep -oP 'phase:\s*\K\d+' "$MIDDLEWARE_DIR/manifest.yaml" 2>/dev/null || echo "0")
fi

# Read schema version for compatibility check
SCHEMA_VER="unknown"
if [ -f "$MIDDLEWARE_DIR/manifest.yaml" ]; then
  SCHEMA_VER=$(grep -oP 'features:\s*"\K[^"]+' "$MIDDLEWARE_DIR/manifest.yaml" 2>/dev/null || echo "unknown")
fi

cat << HOOKEOF
{
  "systemMessage": "This project has a .middleware/ directory (phase ${PHASE}, schema ${SCHEMA_VER}). Before responding, use the middleware:context skill's relay agent to gather project context. Spawn Agent(model: 'sonnet') with the relay-prompt.md from \${CLAUDE_PLUGIN_ROOT}/skills/context/relay-prompt.md combined with the user's message. Use the briefing internally to make better decisions. Do NOT show the briefing to the user. If the relay fails, silently skip."
}
HOOKEOF
