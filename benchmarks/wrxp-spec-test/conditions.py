"""The 2x2 conditions: global CLAUDE.md (from wrxp:setup) on/off x /wrxp:ha on/off.

| cond      | global CLAUDE.md + settings | plugin loaded | prompt prefix |
|-----------|-----------------------------|---------------|---------------|
| base      | no                          | no            | -             |
| global    | yes                         | yes           | -             |
| ha        | no                          | yes           | /wrxp:ha      |
| global_ha | yes                         | yes           | /wrxp:ha      |
| global_haq  | yes                       | yes           | /wrxp:haq     |  (hard suite)
| global_haqq | yes                       | yes           | /wrxp:haqq    |  (hard suite)

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
    "base": {"global": False, "plugin": False, "prefix": ""},
    "global": {"global": True, "plugin": True, "prefix": ""},
    "ha": {"global": False, "plugin": True, "prefix": "/wrxp:ha"},
    "global_ha": {"global": True, "plugin": True, "prefix": "/wrxp:ha"},
    # hard suite only: question tiers on top of the global block
    "global_haq": {"global": True, "plugin": True, "prefix": "/wrxp:haq"},
    "global_haqq": {"global": True, "plugin": True, "prefix": "/wrxp:haqq"},
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


def command(cond: str, allowed: str, resume: str = None):
    c = CONDS[cond]
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", allowed]
    if resume:
        cmd += ["--resume", resume]
    if c["plugin"]:
        cmd += ["--plugin-dir", str(PLUGIN)]
    return cmd


def prompt_for(cond: str, prompt: str) -> str:
    pre = CONDS[cond]["prefix"]
    return f"{pre} {prompt}" if pre else prompt


def env_for(out: Path, cond: str):
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env["CLAUDE_CONFIG_DIR"] = str(config_dir(out, cond))
    return env
