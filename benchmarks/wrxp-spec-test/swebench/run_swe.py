#!/usr/bin/env python3
"""Run SWE-bench Verified instances (instances.jsonl) under the conditions of ../conditions.py.

Usage:
  python3 run_swe.py --out RUNS [--conds base,global,...] [--instances a,b] [--parallel 3] [--reps 1]

Per instance x condition (x rep): swe_env.prepare -> one headless `claude -p` in run_dir/work
(repo/ + ./envrun) -> swe_env.grade -> swe_env.teardown. Writes run_dir/transcript.jsonl and
run_dir/result.json (run.py's fields plus "grade"). Runs whose result.json exists are skipped.
"""
import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import conditions as C  # noqa: E402
from run import ALLOWED  # noqa: E402
import swe_env as E  # noqa: E402

TOOLS = ALLOWED + ",Bash(./envrun:*)"


def final_event(path: Path):
    final = None
    for line in path.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
    return final


def ensure_image(image: str, min_free_gb: float) -> bool:
    """Pull image if missing; True if this call pulled it."""
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
        return False
    free = shutil.disk_usage("/").free / 1e9
    if free < min_free_gb + 2.5:  # an instance image adds up to ~2.5 GB (+2.2 GB shared base if absent)
        raise RuntimeError(f"only {free:.1f} GB free on /; not pulling {image}")
    for attempt in range(12):  # Docker Hub rate limits anonymous pulls (429); wait it out
        r = subprocess.run(["docker", "pull", "-q", image], capture_output=True, text=True)
        if r.returncode == 0:
            return True
        print(f"pull failed ({attempt + 1}/12): {r.stderr.strip()[-160:]}", flush=True)
        time.sleep(300)
    raise RuntimeError(f"could not pull {image}")


def run_one(inst: dict, run_dir: Path, cond: str, out: Path, timeout: int):
    if (run_dir / "result.json").exists():
        return "cached"
    if run_dir.exists():
        E.teardown(run_dir)
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    try:
        work, prompt = E.prepare(inst, run_dir)
        full = C.prompt_for(cond, prompt)
        t0 = time.time()
        with open(run_dir / "transcript.jsonl", "w") as f:
            try:
                proc = subprocess.run(C.command(cond, TOOLS), input=full, cwd=work, stdout=f, stderr=subprocess.PIPE,
                                      text=True, timeout=timeout, env=C.env_for(out, cond))
                rc, err = proc.returncode, proc.stderr[-2000:]
            except subprocess.TimeoutExpired:
                rc, err = -9, "timeout"
        wall = time.time() - t0
        grade = E.grade(inst, run_dir)
    finally:
        E.teardown(run_dir)
    meta = {"cond": cond, "instance_id": inst["instance_id"], "rc": rc, "stderr": err, "wall_sec": wall,
            "prompt": full, "final": final_event(run_dir / "transcript.jsonl"), "grade": grade}
    (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    # keep the run dir small: the diff is in grade/model.patch
    shutil.rmtree(run_dir / "work" / "repo", ignore_errors=True)
    return f"rc={rc} resolved={grade['resolved']} f2p={grade['f2p_passed']}/{grade['f2p_total']} p2p_failed={grade['p2p_failed']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--file", default=str(HERE / "instances.jsonl"))
    ap.add_argument("--instances", default="", help="comma-separated instance ids (default: all in --file)")
    ap.add_argument("--conds", default="base,global,global_haq,global_haqq,pstack,pstack_poteto")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--keep-images", action="store_true",
                    help="do not remove images this script pulled (default: pull on demand, remove when an "
                         "instance's runs are done, so only one instance image is on disk at a time)")
    ap.add_argument("--min-free-gb", type=float, default=8.0, help="refuse to pull when / has less free space")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    insts = [json.loads(l) for l in Path(a.file).read_text().splitlines() if l.strip()]
    if a.instances:
        want = a.instances.split(",")
        missing = set(want) - {i["instance_id"] for i in insts}
        if missing:
            sys.exit(f"unknown instances: {sorted(missing)}")
        insts = [i for i in insts if i["instance_id"] in want]
    conds = a.conds.split(",")
    for c in conds:
        C.config_dir(out, c)
    # one instance at a time (its conditions x reps in parallel) to bound disk use
    for inst in insts:
        jobs = [(out / inst["instance_id"] / f"{c}-{r}", c) for r in range(1, a.reps + 1) for c in conds]
        jobs = [(d, c) for d, c in jobs if not (d / "result.json").exists()]
        if not jobs:
            print(inst["instance_id"], "all cached", flush=True)
            continue
        try:
            pulled = ensure_image(inst["image"], a.min_free_gb)
        except RuntimeError as e:
            print(inst["instance_id"], "SKIPPED", e, flush=True)
            continue
        try:
            with cf.ThreadPoolExecutor(a.parallel) as ex:
                futs = {ex.submit(run_one, inst, d, c, out, a.timeout): d for d, c in jobs}
                for fu in cf.as_completed(futs):
                    d = futs[fu]
                    try:
                        print(d.relative_to(out), fu.result(), flush=True)
                    except Exception as e:  # keep going on one failure
                        print(d.relative_to(out), "ERROR", repr(e), flush=True)
        finally:
            if pulled and not a.keep_images:
                subprocess.run(["docker", "image", "rm", inst["image"]], capture_output=True)


if __name__ == "__main__":
    main()
