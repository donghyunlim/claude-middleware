#!/usr/bin/env python3
"""Run each task under baseline and wrxp conditions with headless Claude Code.

Usage:
  python3 run.py --out RUNS_DIR [--tasks a,b] [--conds baseline,wrxp] [--reps 3] [--parallel 6]

Each run gets a fresh copy of the task fixture. The prompt is identical across
conditions; the wrxp condition loads the plugin with --plugin-dir and prefixes
the prompt with /wrxp:ha. Hidden tests and rubrics never enter the work dir.
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
PLUGIN = HERE.parent.parent / "wrxp"

ALLOWED = ",".join(
    ["Read", "Glob", "Grep", "Write", "Edit", "Skill", "Agent", "TodoWrite", "TaskCreate", "TaskUpdate"]
    + [f"Bash({c}:*)" for c in [
        "python3", "python", "pytest", "ls", "cat", "head", "tail", "wc", "grep", "find", "rm",
        "mkdir", "mv", "cp", "du", "df", "sort", "sed", "awk", "diff", "node", "echo", "date",
        "git", "stat", "file", "tree", "uniq", "cut", "xargs", "test", "printf"]]
)

# Environment variables that would leak this repo's instructions into the run.
STRIP_ENV = ["CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_ADDITIONAL_DIRECTORIES"]


def prepare(task: str, work: Path):
    src = TASKS / task
    if work.exists():
        shutil.rmtree(work)
    if (src / "make_fixture.py").exists():
        shutil.copytree(src / "fixture", work)
        subprocess.run([sys.executable, str(src / "make_fixture.py"), str(work)], check=True)
    else:
        shutil.copytree(src / "fixture", work)


def run_one(task: str, cond: str, rep: int, out: Path, timeout: int):
    run_dir = out / task / f"{cond}-{rep}"
    work = run_dir / "work"
    if (run_dir / "result.json").exists():
        return run_dir, "cached"
    run_dir.mkdir(parents=True, exist_ok=True)
    prepare(task, work)
    prompt = (TASKS / task / "prompt.md").read_text().strip()
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED]
    if cond == "wrxp":
        cmd += ["--plugin-dir", str(PLUGIN)]
        prompt = "/wrxp:ha " + prompt
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    t0 = time.time()
    with open(run_dir / "transcript.jsonl", "w") as f:
        try:
            proc = subprocess.run(cmd, input=prompt, cwd=work, stdout=f, stderr=subprocess.PIPE,
                                  text=True, timeout=timeout, env=env)
            rc = proc.returncode
            err = proc.stderr[-2000:]
        except subprocess.TimeoutExpired:
            rc, err = -9, "timeout"
    wall = time.time() - t0
    final = None
    for line in (run_dir / "transcript.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
    meta = {"task": task, "cond": cond, "rep": rep, "rc": rc, "stderr": err, "wall_sec": wall,
            "prompt": prompt, "final": final}
    (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return run_dir, rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=",".join(sorted(p.name for p in TASKS.iterdir() if p.is_dir())))
    ap.add_argument("--conds", default="baseline,wrxp")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()
    out = Path(a.out)
    jobs = [(t, c, r) for r in range(1, a.reps + 1) for t in a.tasks.split(",") for c in a.conds.split(",")]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, t, c, r, out, a.timeout): (t, c, r) for t, c, r in jobs}
        for fu in cf.as_completed(futs):
            t, c, r = futs[fu]
            try:
                print(t, c, r, fu.result()[1], flush=True)
            except Exception as e:  # keep going on one failure
                print(t, c, r, "ERROR", e, flush=True)


if __name__ == "__main__":
    main()
