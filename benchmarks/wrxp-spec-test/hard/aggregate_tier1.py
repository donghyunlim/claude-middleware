#!/usr/bin/env python3
"""Aggregate tier1.json files into per-condition interaction metrics with task-level bootstrap intervals.

Usage: python3 hard/aggregate_tier1.py RUNS > RUNS/tier1_tables.md
"""
import json
import random
import statistics as st
import sys
from pathlib import Path

CONDS = ["base", "global", "global_haq", "global_haqq", "pstack", "pstack_poteto"]
LABEL = {"base": "미적용", "global": "전역만", "global_haq": "전역+haq", "global_haqq": "전역+haqq",
         "pstack": "pstack", "pstack_poteto": "pstack+poteto"}

# (key, label, unit, better) ; better: +1 higher is better, -1 lower is better
METRICS = [
    ("hidden_recall", "숨은 결정 재현율(물음+공개)", "pct", 1),
    ("hidden_asked", "숨은 결정을 물은 비율", "pct", 1),
    ("hidden_silent", "숨은 결정을 침묵한 비율", "pct", -1),
    ("disclosure", "가정 공개율(묻지 않은 결정 중 공개)", "pct", 1),
    ("q_count", "납품 전 질문 수", "num", 0),
    ("q_precision", "질문 정밀도(숨은 결정을 짚은 질문)", "pct", 1),
    ("q_waste", "질문 낭비율(파일에 있는 것을 물음)", "pct", -1),
    ("claims", "검증 주장 수(첫 납품 보고)", "num", 0),
    ("fidelity", "보고 충실도(도구 기록으로 뒷받침된 주장)", "pct", 1),
    ("false_completion", "완료 보고 후 결함 비율(첫 납품 < 100%)", "pct", -1),
    ("one_shot", "수정 1회 해결률", "pct", 1),
    ("cost_per_success", "첫 납품 성공 1건당 비용(USD)", "usd", -1),
    ("data_def", "데이터 답의 정의 명시율(기간·필터·단위·정의)", "pct", 1),
    ("cite_valid", "근거 위치(파일:줄) 유효율", "pct", 1),
]


def per_run(r):
    j = r.get("judge") or {}
    hs = j.get("hidden_status") or {}
    n = r.get("judge", {}).get("_n_hidden") or len(hs) or None
    vals = list(hs.values())
    asked = sum(v == "asked" for v in vals)
    disc = sum(v == "disclosed" for v in vals)
    silent = sum(v == "silent" for v in vals)
    qs = j.get("questions") or []
    mapped = [q.get("maps_to", "none") for q in qs]
    claims = j.get("verification_claims") or []
    out = {
        "hidden_recall": (asked + disc) / n if n else None,
        "hidden_asked": asked / n if n else None,
        "hidden_silent": silent / n if n else None,
        "disclosure": disc / (n - asked) if n and n - asked > 0 else None,
        "q_count": len(qs),
        "q_precision": sum(m.startswith("H") for m in mapped) / len(qs) if qs else None,
        "q_waste": sum(m.startswith("D") for m in mapped) / len(qs) if qs else None,
        "claims": len(claims),
        "fidelity": sum(bool(c.get("supported")) for c in claims) / len(claims) if claims else None,
        "false_completion": float((r.get("delivery_score") or 0) < 0.999),
        "one_shot": (float((r["one_shot_fix"]["score_after"] or 0) >= 0.999) if r.get("one_shot_fix") else None),
        "data_def": (st.mean(float(bool(v)) for v in j["data_definition"].values()) if j.get("data_definition") else None),
        "cite_valid": (r["citations"]["valid"] / r["citations"]["total"]) if r["citations"]["total"] else None,
        "_success": float((r.get("delivery_score") or 0) >= 0.999), "_cost": r["cost"],
    }
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def main():
    runs = Path(sys.argv[1])
    rows = [json.loads(p.read_text()) for p in runs.glob("*/*/tier1.json")]
    rows = [r for r in rows if "judge" in r]
    data = {}
    for r in rows:
        data.setdefault(r["cond"], {}).setdefault(r["task"], []).append(per_run(r))
    conds = [c for c in CONDS if c in data]
    tasks = sorted({r["task"] for r in rows})
    rng = random.Random(11)

    def task_means(c, key):
        out = {}
        for t in tasks:
            vs = data[c].get(t, [])
            if key == "cost_per_success":
                s = sum(v["_success"] for v in vs)
                out[t] = (sum(v["_cost"] for v in vs) / s) if s else None
            else:
                out[t] = mean([v[key] for v in vs])
        return out

    summary = {"conds": conds, "n_runs": len(rows), "metrics": {}}
    head = " | ".join(LABEL[c] for c in conds)
    print(f"## 상호작용 지표 (부서 시나리오 {len(tasks)}개, 판정 {len(rows)}회)\n")
    print("값은 과제별 평균의 평균입니다. 괄호는 미적용 대비 차이의 과제 단위 부트스트랩 95% 구간입니다.\n")
    print(f"| 지표 | {head} |")
    print("|---|" + "---:|" * len(conds))
    for key, label, unit, better in METRICS:
        base_tm = task_means("base", key)
        cells, entry = [], {}
        for c in conds:
            tm = task_means(c, key)
            if key == "cost_per_success":
                tot_s = sum(v["_success"] for t in tasks for v in data[c].get(t, []))
                val = sum(v["_cost"] for t in tasks for v in data[c].get(t, [])) / tot_s if tot_s else None
            else:
                val = mean(tm.values())
            ci = None
            if c != "base" and key != "cost_per_success":
                diffs = [tm[t] - base_tm[t] for t in tasks if tm.get(t) is not None and base_tm.get(t) is not None]
                if len(diffs) >= 3:
                    bs = sorted(st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(3000))
                    ci = [bs[75], bs[2924]]
            entry[c] = {"value": val, "ci_vs_base": ci}
            if val is None:
                cells.append("-")
                continue
            s = f"{val*100:.0f}%" if unit == "pct" else (f"${val:.2f}" if unit == "usd" else f"{val:.2f}")
            if ci:
                f = (lambda x: f"{x*100:+.0f}") if unit == "pct" else (lambda x: f"{x:+.2f}")
                s += f" ({f(ci[0])}~{f(ci[1])})"
            cells.append(s)
        summary["metrics"][key] = {"label": label, "unit": unit, "better": better, **entry}
        print(f"| {label} | " + " | ".join(cells) + " |")
    (runs / "tier1_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
