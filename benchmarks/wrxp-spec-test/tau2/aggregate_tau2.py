#!/usr/bin/env python3
"""tau2-bench aggregation: pass^k (Yao et al., tau-bench) per condition and domain.

pass^k for one task with c successes out of n trials = C(c,k)/C(n,k); averaged over tasks.
Usage: python3 tau2/aggregate_tau2.py RUNS > RUNS/tables.md
"""
import json
import statistics as st
import sys
from math import comb
from pathlib import Path

CONDS = ["base", "global", "global_haq", "global_haqq", "pstack", "pstack_poteto"]
LABEL = {"base": "미적용", "global": "전역만", "global_haq": "전역+haq", "global_haqq": "전역+haqq",
         "pstack": "pstack", "pstack_poteto": "pstack+poteto"}


def main():
    runs = Path(sys.argv[1])
    rows = [json.loads(p.read_text()) for p in runs.glob("*/*/*/result.json")]
    conds = [c for c in CONDS if any(r["cond"] == c for r in rows)]
    domains = sorted({r["domain"] for r in rows})
    summary = {"conds": conds, "by_domain": {}, "overall": {}}
    head = " | ".join(LABEL[c] for c in conds)
    print("## τ²-bench DB 보상 (pass^k)\n")
    print(f"| 도메인 | 지표 | {head} |")
    print("|---|---|" + "---:|" * len(conds))
    for dom in domains + ["전체"]:
        sel = [r for r in rows if dom == "전체" or r["domain"] == dom]
        out = {}
        for c in conds:
            by_task = {}
            for r in sel:
                if r["cond"] == c:
                    by_task.setdefault((r["domain"], r["task_id"]), []).append(r["reward"].get("db", 0.0) >= 1.0)
            n = min((len(v) for v in by_task.values()), default=0)
            out[c] = {f"pass^{k}": st.mean(comb(sum(v), k) / comb(len(v), k) for v in by_task.values())
                      for k in range(1, n + 1)} if by_task else {}
            cr = [r for r in sel if r["cond"] == c]
            out[c]["cost"] = st.mean(r["agent_cost"] + r["user_cost"] for r in cr) if cr else None
            out[c]["turns"] = st.mean(r["agent_turns"] for r in cr) if cr else None
            out[c]["tasks"] = len(by_task)
        summary["by_domain" if dom != "전체" else "overall"][dom] = out
        for key in ["pass^1", "pass^2"]:
            print(f"| {dom} | {key} | " + " | ".join(f"{out[c].get(key, 0)*100:.0f}%" if key in out[c] else "-" for c in conds) + " |")
        print(f"| {dom} | 실행당 비용 | " + " | ".join(f"${out[c]['cost']:.2f}" if out[c]["cost"] else "-" for c in conds) + " |")
        print(f"| {dom} | 에이전트 턴 | " + " | ".join(f"{out[c]['turns']:.1f}" if out[c]["turns"] else "-" for c in conds) + " |")
    (runs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
