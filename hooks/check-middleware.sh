#!/bin/bash
# Detect .middleware/ directory, inject context instruction, and auto-install git hooks.
# Runs on every UserPromptSubmit. Exits silently if no .middleware/ found.

MIDDLEWARE_DIR="${CLAUDE_PROJECT_DIR:-.}/.middleware"
GIT_DIR="${CLAUDE_PROJECT_DIR:-.}/.git"

if [ ! -d "$MIDDLEWARE_DIR" ]; then
  exit 0
fi

# Read phase from manifest (default 0 if unreadable)
PHASE=0
if [ -f "$MIDDLEWARE_DIR/manifest.yaml" ]; then
  PHASE=$(grep -oP 'phase:\s*\K\d+' "$MIDDLEWARE_DIR/manifest.yaml" 2>/dev/null || echo "0")
fi

# Read backend type (yaml or graphiti)
BACKEND="yaml"
if [ -f "$MIDDLEWARE_DIR/manifest.yaml" ]; then
  BACKEND=$(grep -oP 'backend:\s*\K\w+' "$MIDDLEWARE_DIR/manifest.yaml" 2>/dev/null || echo "yaml")
fi

# Read group_id for graphiti backend
GROUP_ID=""
if [ -f "$MIDDLEWARE_DIR/manifest.yaml" ]; then
  GROUP_ID=$(grep -oP 'group_id:\s*\K\w+' "$MIDDLEWARE_DIR/manifest.yaml" 2>/dev/null || echo "")
fi

# --- Auto-install git post-commit hook ---
if [ -d "$GIT_DIR" ]; then
  POST_COMMIT="$GIT_DIR/hooks/post-commit"
  HOOK_SCRIPT="${CLAUDE_PROJECT_DIR:-.}/scripts/middleware/post_commit_graphiti.py"

  if [ ! -f "$POST_COMMIT" ] && [ -f "$HOOK_SCRIPT" ]; then
    mkdir -p "$GIT_DIR/hooks"
    PYTHON_BIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "/usr/bin/python3")
    cat > "$POST_COMMIT" << EOF
#!/usr/bin/env bash
# Auto-installed by middleware plugin — sends commit data to Graphiti KG.
"$PYTHON_BIN" "$HOOK_SCRIPT" &>/dev/null &
exit 0
EOF
    chmod +x "$POST_COMMIT"
  fi
fi

# --- Inject system message based on backend type ---
if [ "$BACKEND" = "graphiti" ]; then
  cat << HOOKEOF
{
  "systemMessage": "This project has .middleware/ (phase ${PHASE}, backend: graphiti, group_id: ${GROUP_ID}). Use /middleware:mw skill to query the Graphiti knowledge graph for project context before complex tasks. The KG contains architecture principles, design decisions, constraints, and module dependencies. For quick context: search_memory_facts(query, group_ids=['${GROUP_ID}']). For conflict detection: search for IS_PROHIBITED_IN, MUST_VIA, REQUIRES_NOT_MODIFY facts."
}
HOOKEOF
else
  cat << HOOKEOF
{
  "systemMessage": "This project has a .middleware/ directory (phase ${PHASE}). Before responding, use the middleware:context skill's relay agent to gather project context. Spawn Agent(model: 'sonnet') with the relay-prompt.md from \${CLAUDE_PLUGIN_ROOT}/skills/context/relay-prompt.md combined with the user's message. Use the briefing internally to make better decisions. Do NOT show the briefing to the user. If the relay fails, silently skip."
}
HOOKEOF
fi
