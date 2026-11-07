#!/usr/bin/env python3
"""Validate each task: (a) no work -> not resolved; (b) reference solution via ./envrun -> resolved.

Usage: python3 validate.py --out DIR [--tasks a,b] [--parallel 4]
Writes DIR/validation.json.
"""
import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import time
from pathlib import Path

import tb_env as E

HERE = Path(__file__).resolve().parent


def check(task, out: Path):
    res = {}
    for mode in ("a_nowork", "b_solution"):
        rd = out / task["id"] / mode
        if rd.exists():
            shutil.rmtree(rd)
        rd.mkdir(parents=True)
        try:
            work, _ = E.prepare(task, rd)
            sol_sec = None
            if mode == "b_solution":
                t0 = time.time()
                subprocess.run(["./envcp", str(HERE / task["solution_dir"]), ":/solution"], cwd=work, check=True)
                with open(rd / "solution.log", "w") as f:
                    p = subprocess.run(["./envrun", task["solution_cmd"]], cwd=work, stdout=f, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, timeout=min(task["agent_timeout_sec"], 1800))
                sol_sec = round(time.time() - t0, 1)
                subprocess.run(["./envrun", "rm -rf /solution"], cwd=work)
            g = E.grade(task, rd)
            g["solution_rc"] = p.returncode if mode == "b_solution" else None
            g["solution_sec"] = sol_sec
            res[mode] = g
        except Exception as e:
            res[mode] = {"error": repr(e)}
        finally:
            E.teardown(rd)
    res["ok"] = (res["a_nowork"].get("resolved") is False) and (res["b_solution"].get("resolved") is True)
    return task["id"], res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=None)
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    tasks = E.load_tasks()
    ids = a.tasks.split(",") if a.tasks else list(tasks)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for tid, r in ex.map(lambda t: check(tasks[t], out), ids):
            results[tid] = r
            print(tid, "OK" if r["ok"] else "FAIL", json.dumps({k: v for k, v in r.items() if k != "ok"}), flush=True)
    (out / "validation.json").write_text(json.dumps(results, indent=1))
    print(f"{sum(r['ok'] for r in results.values())}/{len(results)} tasks validated")


if __name__ == "__main__":
    main()
