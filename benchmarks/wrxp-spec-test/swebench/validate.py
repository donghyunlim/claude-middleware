#!/usr/bin/env python3
"""Validate the harness on every instance of instances.jsonl.

(a) prepare, change nothing, grade      -> must be resolved=False
(b) prepare, apply reference_patch to the host repo, grade -> must be resolved=True
plus `./envrun python -c "print(1)"` must print 1.

Usage: python3 validate.py [--instances a,b] [--out DIR] [--parallel 2]
Writes DIR/validation.json.
"""
import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import swe_env as E

HERE = Path(__file__).resolve().parent


def check(inst, base: Path) -> dict:
    iid = inst["instance_id"]
    out = {"instance_id": iid}
    # (a) no-op
    rd = base / iid / "noop"
    try:
        t0 = time.time()
        work, prompt = E.prepare(inst, rd)
        out["prepare_sec"] = round(time.time() - t0, 1)
        r = subprocess.run(["./envrun", "python", "-c", "print(1)"], cwd=work, capture_output=True, text=True)
        out["envrun_ok"] = r.returncode == 0 and r.stdout.strip() == "1"
        out["envrun_out"] = (r.stdout + r.stderr).strip()[-300:]
        out["noop"] = E.grade(inst, rd)
    finally:
        E.teardown(rd)
    # (b) reference patch
    rd = base / iid / "ref"
    try:
        work, _ = E.prepare(inst, rd)
        pf = rd / "reference.patch"
        pf.write_text(inst["reference_patch"])
        ap = subprocess.run(["git", "apply", "--verbose", str(pf)], cwd=work / "repo", capture_output=True, text=True)
        out["ref_host_apply_ok"] = ap.returncode == 0
        if ap.returncode != 0:
            out["ref_host_apply_err"] = ap.stderr[-500:]
        out["ref"] = E.grade(inst, rd)
    finally:
        E.teardown(rd)
    out["valid"] = (out["envrun_ok"] and out["noop"]["resolved"] is False and out["noop"]["error"] is None
                    and out["ref"]["resolved"] is True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(HERE / "instances.jsonl"))
    ap.add_argument("--instances", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--update", action="store_true",
                    help="write P2P_ENV_EXCLUDED into the instances file: P2P tests failing both with no patch and "
                         "with the (officially resolving) reference patch, when every F2P test passes")
    a = ap.parse_args()
    insts = [json.loads(l) for l in Path(a.file).read_text().splitlines() if l.strip()]
    if a.instances:
        want = set(a.instances.split(","))
        insts = [i for i in insts if i["instance_id"] in want]
    base = Path(a.out or tempfile.mkdtemp(prefix="swe-validate-")).resolve()
    base.mkdir(parents=True, exist_ok=True)
    results = []
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(check, i, base): i["instance_id"] for i in insts}
        for fu in cf.as_completed(futs):
            try:
                r = fu.result()
            except Exception as e:
                r = {"instance_id": futs[fu], "valid": False, "exception": repr(e)}
            results.append(r)
            brief = {k: r.get(k) for k in ("instance_id", "valid", "envrun_ok", "exception")}
            for k in ("noop", "ref"):
                if k in r:
                    g = r[k]
                    brief[k] = (f"resolved={g['resolved']} f2p={g['f2p_passed']}/{g['f2p_total']} "
                                f"p2p_failed={g['p2p_failed']}/{g['p2p_total']} eval={g.get('eval_sec')}s err={g['error']}")
            print(json.dumps(brief), flush=True)
    results.sort(key=lambda r: r["instance_id"])
    if a.update:
        by = {r["instance_id"]: r for r in results}
        rows = [json.loads(l) for l in Path(a.file).read_text().splitlines() if l.strip()]
        for row in rows:
            r = by.get(row["instance_id"])
            if not r or "ref" not in r or r["ref"]["p2p_failures"] is None or r["ref"]["f2p_failures"]:
                continue
            env_fail = sorted(set(r["ref"]["p2p_failures"]) & set(r["noop"]["p2p_failures"] or []))
            if env_fail:
                row["P2P_ENV_EXCLUDED"] = sorted(set(row.get("P2P_ENV_EXCLUDED", [])) | set(env_fail))
                print(row["instance_id"], "P2P_ENV_EXCLUDED +=", env_fail)
        Path(a.file).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (base / "validation.json").write_text(json.dumps(results, indent=1))
    print(f"{sum(r['valid'] for r in results)}/{len(results)} valid; details in {base / 'validation.json'}")
    sys.exit(0 if all(r["valid"] for r in results) else 1)


if __name__ == "__main__":
    main()
