#!/usr/bin/env python3
"""Compatibility entry point for wrxp/shared/scripts/user_turns.py.

The shared source runs in this module's namespace so callers that patch module
globals (CLAUDE_PROJECTS, CODEX_SESSIONS) still reach the functions they call.
"""

from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "scripts" / "user_turns.py"
exec(compile(_SHARED.read_text(encoding="utf-8"), str(_SHARED), "exec"), globals())
