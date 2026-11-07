#!/usr/bin/env python3
"""Resolve-rate tables for SWE-bench Verified and Terminal-Bench 2 runs.

Usage: python3 aggregate_resolve.py RUNS NAME > RUNS/tables.md
RUNS/<instance>/<cond>-<rep>/result.json with a "grade" dict holding "resolved".
Reports resolve rate (all runs), pass@1 averaged per instance, pass^2 (both reps resolved),
cost, time, and a bootstrap 95% interval of the resolve-rate difference from base.
"""
import json
import random
import statistics as st
import sys
from math import comb
from pathlib import Path

CONDS = ["base", "global", "global_haq", "global_haqq", "pstack", "pstack_poteto"]
LABEL = {"base": "미적용", "global": "전역만", "global_haq": "전역+haq", "global_haqq": "전역+haqq",
         "pstack": "pstack", "pstack_poteto": "pstack+poteto"}


def main():
    runs, name = Path(sys.argv[1]), sys.argv[2]
    rows = []
    for p in runs.glob("*/*/result.json"):
        m = json.loads(p.read_text())
        cond, rep = p.parent.name.rsplit("-", 1)
        g = m.get("grade") or {}
        fin = m.get("final") or {}
        rows.append({"inst": p.parent.parent.name, "cond": cond, "rep": int(rep), "resolved": bool(g.get("resolved")),
                     "cost": fin.get("total_cost_usd") or 0.0, "sec": m.get("wall_sec") or 0.0,
                     "error": g.get("error")})
    conds = [c for c in CONDS if any(r["cond"] == c for r in rows)]
    insts = sorted({r["inst"] for r in rows})
    rng = random.Random(1)
    summary = {"conds": conds, "instances": insts, "by_cond": {}, "by_instance": {}}
    head = " | ".join(LABEL[c] for c in conds)
    print(f"## {name}: 조건별 해결률\n")
    print(f"| 지표 | {head} |")
    print("|---|" + "---:|" * len(conds))
    base_by = {}
    for c in conds:
        by = {}
        for r in rows:
            if r["cond"] == c:
                by.setdefault(r["inst"], []).append(r["resolved"])
        if c == "base":
            base_by = by
        k2 = [comb(sum(v), 2) / comb(len(v), 2) for v in by.values() if len(v) >= 2]
        cr = [r for r in rows if r["cond"] == c]
        d = None
        if c != "base" and base_by:
            common = [i for i in by if i in base_by]
            diffs = [st.mean(by[i]) - st.mean(base_by[i]) for i in common]
            boots = sorted(st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(2000)) if diffs else []
            d = {"mean": st.mean(diffs) if diffs else None, "ci": [boots[50], boots[1949]] if boots else None}
        summary["by_cond"][c] = {"pass@1": st.mean(st.mean(v) for v in by.values()), "pass^2": st.mean(k2) if k2 else None,
                                 "runs": len(cr), "cost": st.mean(r["cost"] for r in cr), "sec": st.mean(r["sec"] for r in cr),
                                 "diff_vs_base": d}
    s = summary["by_cond"]
    print("| pass@1 (해결률) | " + " | ".join(f"{s[c]['pass@1']*100:.0f}%" for c in conds) + " |")
    print("| pass^2 (2회 모두 해결) | " + " | ".join(f"{s[c]['pass^2']*100:.0f}%" if s[c]['pass^2'] is not None else "-" for c in conds) + " |")
    print("| 미적용 대비 차이 (95% 구간) | " + " | ".join(
        "-" if not s[c]["diff_vs_base"] else f"{s[c]['diff_vs_base']['mean']*100:+.0f}%p ({s[c]['diff_vs_base']['ci'][0]*100:+.0f}~{s[c]['diff_vs_base']['ci'][1]*100:+.0f})"
        for c in conds) + " |")
    print("| 실행당 비용 | " + " | ".join(f"${s[c]['cost']:.2f}" for c in conds) + " |")
    print("| 실행당 시간(초) | " + " | ".join(f"{s[c]['sec']:.0f}" for c in conds) + " |")
    print("| 실행 수 | " + " | ".join(str(s[c]['runs']) for c in conds) + " |")
    print(f"\n## {name}: 문항별 해결 횟수\n")
    print(f"| 문항 | {head} |")
    print("|---|" + "---:|" * len(conds))
    for i in insts:
        cells = []
        for c in conds:
            v = [r["resolved"] for r in rows if r["inst"] == i and r["cond"] == c]
            cells.append(f"{sum(v)}/{len(v)}" if v else "-")
        summary["by_instance"][i] = dict(zip(conds, cells))
        print(f"| {i} | " + " | ".join(cells) + " |")
    errs = [r for r in rows if r["error"]]
    if errs:
        print(f"\n채점 오류 {len(errs)}건: " + ", ".join(f"{r['inst']}/{r['cond']}-{r['rep']}" for r in errs[:10]))
    (runs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
