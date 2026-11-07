#!/usr/bin/env python3
"""Reconstruct 8 SWE-bench Verified instances without Hugging Face.

Sources (Hugging Face is unreachable from the benchmark host):
  * Selection: per_instance_details.json of 4 strong mini-SWE-agent v2.0.0 runs in
    github.com/SWE-bench/experiments (evaluation/verified/<run>/). We keep instances
    resolved by 2 or 3 of the 4 runs, one per repo, small Docker images.
  * eval script: logs/<id>/eval.sh of the official evaluation of run RUNS[0], from the
    public bucket s3://swe-bench-submissions/bash-only/<run>/ (metadata.yaml "assets").
    It holds the gold test patch and the test command exactly as the harness ran them.
  * FAIL_TO_PASS / PASS_TO_PASS: logs/<id>/report.json (tests_status.*.success + failure)
    of every run; all 4 must agree.
  * problem_statement: first user message of trajs/<id>/<id>.traj.json, the text inside
    "<pr_description>\nConsider the following PR description:\n ... \n</pr_description>"
    (mini-SWE-agent's template puts the dataset's problem_statement there verbatim).
    Extracted from two runs and required to match.
  * reference_patch: logs/<id>/patch.diff of the first run that resolved it (only used
    by validate.py to check the harness).
  * image: swebench/sweb.eval.x86_64.<id with "__" -> "_1776_">:latest (Docker Hub).

Usage: python3 prepare_instances.py [--out instances.jsonl]
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUCKET = "https://swe-bench-submissions.s3.amazonaws.com/bash-only"
EXP_RAW = "https://raw.githubusercontent.com/SWE-bench/experiments/main/evaluation/verified"
RUNS = [
    "20260217_mini-v2.0.0_claude-4-6-opus",
    "20260217_mini-v2.0.0_claude-4-5-opus-high",
    "20260217_mini-v2.0.0_gpt-5-2-high",
    "20260217_mini-v2.0.0_claude-4-5-sonnet-high",
]
# one per repo; each resolved by 2-3 of RUNS; images ~1.0-1.3 GB compressed
INSTANCES = [
    "psf__requests-2931",
    "pylint-dev__pylint-6386",
    "pytest-dev__pytest-7490",
    "sphinx-doc__sphinx-8595",
    "sympy__sympy-19040",
    "astropy__astropy-14182",
    "mwaskom__seaborn-3069",
    "django__django-13401",
]
PR_RE = re.compile(r"<pr_description>\nConsider the following PR description:\n(.*)\n</pr_description>", re.S)


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def image_for(iid: str) -> str:
    return f"swebench/sweb.eval.x86_64.{iid.replace('__', '_1776_')}:latest"


def repo_for(iid: str) -> str:
    owner, rest = iid.split("__", 1)
    return f"{owner}/{rest.rsplit('-', 1)[0]}"


def problem_statement(run: str, iid: str) -> str:
    traj = json.loads(get(f"{BUCKET}/{run}/trajs/{iid}/{iid}.traj.json"))
    first_user = next(m for m in traj["messages"] if m["role"] == "user")
    content = first_user["content"]
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content)
    m = PR_RE.search(content)
    if not m:
        raise RuntimeError(f"{iid}: no <pr_description> in {run} trajectory")
    return m.group(1)


def tests(run: str, iid: str):
    rep = json.loads(get(f"{BUCKET}/{run}/logs/{iid}/report.json"))
    rep = rep.get(iid, rep)  # some runs wrap the report in {instance_id: ...}
    ts = rep["tests_status"]
    f2p = sorted(ts["FAIL_TO_PASS"]["success"] + ts["FAIL_TO_PASS"]["failure"])
    p2p = sorted(ts["PASS_TO_PASS"]["success"] + ts["PASS_TO_PASS"]["failure"])
    return f2p, p2p, rep["resolved"]


def build(iid: str, details: dict) -> dict:
    resolved_by = [r for r in RUNS if details[r][iid]["resolved"]]
    f2p = p2p = None
    for r in RUNS:
        a, b, res = tests(r, iid)
        if res != details[r][iid]["resolved"]:
            raise RuntimeError(f"{iid}: report.json and per_instance_details disagree for {r}")
        if f2p is None:
            f2p, p2p = a, b
        elif (a, b) != (f2p, p2p):
            raise RuntimeError(f"{iid}: F2P/P2P lists differ between runs ({r})")
    ps = problem_statement(RUNS[0], iid)
    ps2 = problem_statement(RUNS[2], iid)
    if ps.strip() != ps2.strip():
        raise RuntimeError(f"{iid}: problem statements differ between trajectories")
    eval_sh = get(f"{BUCKET}/{RUNS[0]}/logs/{iid}/eval.sh").decode()
    ref_run = resolved_by[0]
    ref = get(f"{BUCKET}/{ref_run}/logs/{iid}/patch.diff").decode()
    return {
        "instance_id": iid,
        "repo": repo_for(iid),
        "image": image_for(iid),
        "problem_statement": ps,
        "eval_script": eval_sh,
        "FAIL_TO_PASS": f2p,
        "PASS_TO_PASS": p2p,
        "reference_patch": ref,
        "resolved_by": resolved_by,
        "sources": {
            "selection": [f"{EXP_RAW}/{r}/per_instance_details.json" for r in RUNS],
            "problem_statement": f"{BUCKET}/{RUNS[0]}/trajs/{iid}/{iid}.traj.json (<pr_description>), "
                                 f"cross-checked against {RUNS[2]}",
            "eval_script": f"{BUCKET}/{RUNS[0]}/logs/{iid}/eval.sh",
            "tests": f"{BUCKET}/<run>/logs/{iid}/report.json tests_status success+failure, identical in all of {RUNS}",
            "reference_patch": f"{BUCKET}/{ref_run}/logs/{iid}/patch.diff (resolved in that run)",
            "image": "Docker Hub " + image_for(iid),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "instances.jsonl"))
    ap.add_argument("--instances", default=",".join(INSTANCES))
    a = ap.parse_args()
    details = {r: json.loads(get(f"{EXP_RAW}/{r}/per_instance_details.json")) for r in RUNS}
    # keep validate.py --update's sandbox exclusions across regenerations
    old = {}
    if Path(a.out).exists():
        old = {r["instance_id"]: r for r in map(json.loads, Path(a.out).read_text().splitlines()) if r}
    rows = []
    for iid in a.instances.split(","):
        row = build(iid, details)
        if old.get(iid, {}).get("P2P_ENV_EXCLUDED"):
            row["P2P_ENV_EXCLUDED"] = old[iid]["P2P_ENV_EXCLUDED"]
        print(iid, "resolved_by", len(row["resolved_by"]), "/", len(RUNS),
              "F2P", len(row["FAIL_TO_PASS"]), "P2P", len(row["PASS_TO_PASS"]), file=sys.stderr)
        rows.append(row)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"wrote {len(rows)} instances to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
