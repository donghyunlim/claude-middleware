#!/usr/bin/env python3
"""Run tasks under the 2x2 conditions in conditions.py with headless Claude Code.

Usage:
  python3 run.py --suite dept --out RUNS [--tasks a,b] [--conds base,global,ha,global_ha] [--reps 3] [--parallel 8]
  python3 run.py --suite std  --out RUNS [--benches mmlu_pro,gpqa] [--conds ...] [--parallel 8]

dept: the department tasks in tasks/ (fresh fixture copy per run, hidden files never copied).
std:  the public benchmark items in std/items/*.jsonl (built by std/prepare_data.py).
The prompt text is identical across conditions except for the /wrxp:ha prefix.
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

import conditions as C

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
ITEMS = Path(os.environ.get("WRXP_ITEMS", HERE / "std" / "items"))

ALLOWED = ",".join(
    ["Read", "Glob", "Grep", "Write", "Edit", "Skill", "Agent", "TodoWrite", "TaskCreate", "TaskUpdate"]
    + [f"Bash({c}:*)" for c in [
        "python3", "python", "pytest", "ls", "cat", "head", "tail", "wc", "grep", "find", "rm",
        "mkdir", "mv", "cp", "du", "df", "sort", "sed", "awk", "diff", "node", "echo", "date",
        "git", "stat", "file", "tree", "uniq", "cut", "xargs", "test", "printf"]]
)


def prepare_dept(task: str, work: Path):
    src = TASKS / task
    shutil.copytree(src / "fixture", work)
    if (src / "make_fixture.py").exists():
        subprocess.run([sys.executable, str(src / "make_fixture.py"), str(work)], check=True)


def prepare_std(item: dict, work: Path):
    work.mkdir(parents=True)
    for name, text in (item.get("files") or {}).items():
        (work / name).write_text(text)
    if item.get("corpus"):
        dst = work / "corpus"
        dst.mkdir()
        for p in (ITEMS / item["corpus"]).iterdir():
            os.link(p, dst / p.name)


def run_one(run_dir: Path, prompt: str, prepare, cond: str, out: Path, timeout: int):
    if (run_dir / "result.json").exists():
        return "cached"
    work = run_dir / "work"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    prepare(work)
    full = C.prompt_for(cond, prompt)
    t0 = time.time()
    with open(run_dir / "transcript.jsonl", "w") as f:
        try:
            proc = subprocess.run(C.command(cond, ALLOWED), input=full, cwd=work, stdout=f, stderr=subprocess.PIPE,
                                  text=True, timeout=timeout, env=C.env_for(out, cond))
            rc, err = proc.returncode, proc.stderr[-2000:]
        except subprocess.TimeoutExpired:
            rc, err = -9, "timeout"
    final = None
    for line in (run_dir / "transcript.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
    if (work / "corpus").exists():
        shutil.rmtree(work / "corpus")  # hard links; keep the run dir small
    meta = {"cond": cond, "rc": rc, "stderr": err, "wall_sec": time.time() - t0, "prompt": full, "final": final}
    (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return rc


def jobs_dept(a, out):
    for r in range(1, a.reps + 1):
        for t in a.tasks.split(","):
            prompt = (TASKS / t / "prompt.md").read_text().strip()
            for c in a.conds.split(","):
                yield out / t / f"{c}-{r}", prompt, (lambda w, t=t: prepare_dept(t, w)), c


def jobs_std(a, out):
    for b in a.benches.split(","):
        for line in (ITEMS / f"{b}.jsonl").read_text().splitlines():
            it = json.loads(line)
            for c in a.conds.split(","):
                yield out / b / it["id"] / f"{c}-1", it["prompt"], (lambda w, it=it: prepare_std(it, w)), c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["dept", "std"], default="dept")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=",".join(sorted(p.name for p in TASKS.iterdir() if p.is_dir())))
    ap.add_argument("--benches", default=",".join(sorted(p.stem for p in ITEMS.glob("*.jsonl"))) if ITEMS.exists() else "")
    ap.add_argument("--conds", default=",".join(C.CONDS))
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    for c in a.conds.split(","):
        C.config_dir(out, c)
    jobs = list((jobs_dept if a.suite == "dept" else jobs_std)(a, out))
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, d, p, prep, c, out, a.timeout): d for d, p, prep, c in jobs}
        for fu in cf.as_completed(futs):
            d = futs[fu]
            try:
                print(d.relative_to(out), fu.result(), flush=True)
            except Exception as e:  # keep going on one failure
                print(d.relative_to(out), "ERROR", repr(e), flush=True)


if __name__ == "__main__":
    main()
