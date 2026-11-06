"""The 2x2 conditions: global CLAUDE.md (from wrxp:setup) on/off x /wrxp:ha on/off.

| cond      | global CLAUDE.md + settings | plugin loaded | prompt prefix |
|-----------|-----------------------------|---------------|---------------|
| base      | no                          | no            | -             |
| global    | yes                         | yes           | -             |
| ha        | no                          | yes           | /wrxp:ha      |
| global_ha | yes                         | yes           | /wrxp:ha      |

Every condition runs with its own CLAUDE_CONFIG_DIR so that only the setup
output differs. "global" loads the plugin because the setup rules route to
wrxp skills and setup presumes the plugin is installed.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.parent / "wrxp"
SETUP = PLUGIN / "skills/setup/scripts/setup_global.py"

CONDS = {
    "base": {"global": False, "plugin": False, "ha": False},
    "global": {"global": True, "plugin": True, "ha": False},
    "ha": {"global": False, "plugin": True, "ha": True},
    "global_ha": {"global": True, "plugin": True, "ha": True},
}
STRIP_ENV = ["CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_ADDITIONAL_DIRECTORIES"]


def config_dir(out: Path, cond: str) -> Path:
    d = out / "_cfg" / cond
    if not d.exists():
        d.mkdir(parents=True)
        if CONDS[cond]["global"]:
            r = subprocess.run([sys.executable, str(SETUP), "--target", "claude", "--claude-home", str(d), "--apply"],
                               capture_output=True, text=True, check=True)
            rep = json.loads(r.stdout)
            if rep.get("error"):
                raise RuntimeError(rep["error"])
    return d


def command(cond: str, allowed: str):
    c = CONDS[cond]
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", allowed]
    if c["plugin"]:
        cmd += ["--plugin-dir", str(PLUGIN)]
    return cmd


def prompt_for(cond: str, prompt: str) -> str:
    return ("/wrxp:ha " + prompt) if CONDS[cond]["ha"] else prompt


def env_for(out: Path, cond: str):
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env["CLAUDE_CONFIG_DIR"] = str(config_dir(out, cond))
    return env
