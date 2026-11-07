#!/usr/bin/env python3
"""Run Terminal-Bench 2 tasks (tasks.jsonl) under the conditions in ../conditions.py with headless Claude Code.

Usage:
  python3 run_tb2.py --out RUNS [--tasks a,b] [--conds base,global,...] [--parallel 3] [--reps 1]

Per task x condition: start the task container (tb_env.prepare), run `claude -p` once in run_dir/work
(the agent reaches the container only via ./envrun and ./envcp), save transcript.jsonl + result.json
like ../run.py, then grade inside the same container (grade.json) and remove it.
Runs whose result.json exists are skipped.
"""
import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import conditions as C  # noqa: E402
import tb_env as E  # noqa: E402
from run import ALLOWED  # noqa: E402

TB_ALLOWED = ALLOWED + ",Bash(./envrun:*),Bash(./envcp:*)"
MAX_TIMEOUT = 1800


def run_one(task: dict, run_dir: Path, cond: str, out: Path):
    if (run_dir / "result.json").exists():
        return "cached"
    if run_dir.exists():
        E.teardown(run_dir)
        import shutil
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    timeout = int(min(task["agent_timeout_sec"], MAX_TIMEOUT))
    try:
        work, prompt = E.prepare(task, run_dir)
        full = C.prompt_for(cond, prompt)
        t0 = time.time()
        with open(run_dir / "transcript.jsonl", "w") as f:
            try:
                proc = subprocess.run(C.command(cond, TB_ALLOWED), input=full, cwd=work, stdout=f,
                                      stderr=subprocess.PIPE, text=True, timeout=timeout, env=C.env_for(out, cond))
                rc, err = proc.returncode, proc.stderr[-2000:]
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
        try:
            g = E.grade(task, run_dir)
        except Exception as e:
            g = {"resolved": False, "passed": 0, "total": 0, "error": repr(e)}
        meta = {"task": task["id"], "cond": cond, "rc": rc, "stderr": err, "wall_sec": wall,
                "agent_timeout_sec": timeout, "prompt": full, "final": final, "grade": g}
        (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        return f"rc={rc} resolved={g.get('resolved')} {g.get('passed')}/{g.get('total')}"
    finally:
        E.teardown(run_dir)


def main():
    tasks = E.load_tasks()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=",".join(tasks))
    ap.add_argument("--conds", default="base,global,global_haq,global_haqq,pstack,pstack_poteto")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--reps", type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    conds = a.conds.split(",")
    for c in conds:
        C.config_dir(out, c)
    ids = a.tasks.split(",")
    for t in ids:  # pull images up front, serially
        E.ensure_image(tasks[t])
    jobs = [(tasks[t], out / t / f"{c}-{r}", c) for r in range(1, a.reps + 1) for t in ids for c in conds]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, t, d, c, out): d for t, d, c in jobs}
        for fu in cf.as_completed(futs):
            d = futs[fu]
            try:
                print(d.relative_to(out), fu.result(), flush=True)
            except Exception as e:  # keep going on one failure
                print(d.relative_to(out), "ERROR", repr(e), flush=True)


if __name__ == "__main__":
    main()
