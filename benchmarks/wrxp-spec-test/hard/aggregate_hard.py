#!/usr/bin/env python3
"""Aggregate hard-suite grades. Usage: python3 hard/aggregate_hard.py RUNS > RUNS/tables.md"""
import json
import statistics as st
import sys
from pathlib import Path

CONDS = ["base", "global", "global_ha", "global_haq", "global_haqq"]
LABEL = {"base": "미적용", "global": "전역만", "global_ha": "전역+ha", "global_haq": "전역+haq", "global_haqq": "전역+haqq"}
TASK = {"export": "주문 CSV 내보내기(모호한 요구)", "coupon": "쿠폰 규칙(모호한 요구)", "churn": "이탈률 정의(모호한 요구)",
        "inventory": "여러 파일에 걸친 재고 버그", "roadmap": "3개 팀 조율 로드맵 문서"}
METRICS = [
    ("delivery", "첫 납품 점수", "pct"), ("final", "최종 점수", "pct"),
    ("user_turns", "사용자 개입 횟수", "num"), ("revisions_requested", "수정 요청 횟수", "num"),
    ("questions_answered", "질문에 답한 횟수", "num"), ("user_chars", "사용자가 쓴 글자 수", "num"),
    ("total_cost", "총 비용(USD)", "usd"), ("wall_sec", "총 소요 시간(초)", "num"),
]


def val(g, key):
    if key in ("delivery", "final", "first"):
        return g[key].get("score")
    if key == "total_cost":
        return g["agent_cost"] + g["user_cost"]
    v = g.get(key)
    return float(v) if isinstance(v, bool) else v


def fmt(v, kind):
    if v is None:
        return "-"
    return f"{v*100:.0f}%" if kind == "pct" else f"${v:.2f}" if kind == "usd" else f"{v:.1f}" if v < 100 else f"{v:,.0f}"


def main():
    runs = Path(sys.argv[1])
    data = {}
    for g in runs.glob("*/*/grade.json"):
        cond, rep = g.parent.name.rsplit("-", 1)
        data.setdefault(g.parent.parent.name, {}).setdefault(cond, []).append(json.loads(g.read_text()))
    conds = [c for c in CONDS if any(c in v for v in data.values())]
    head = " | ".join(LABEL[c] for c in conds)
    summary = {"conds": conds, "overall": {}, "per_task": {}}
    print("## 전체 평균 (과제 5개 × 3회)\n")
    print(f"| 지표 | {head} |")
    print("|---|" + "---:|" * len(conds))
    for key, label, kind in METRICS:
        row = {}
        for c in conds:
            v = [val(g, key) for t in data.values() for g in t.get(c, []) if val(g, key) is not None]
            row[c] = st.mean(v) if v else None
        summary["overall"][key] = row
        print(f"| {label} | " + " | ".join(fmt(row[c], kind) for c in conds) + " |")
    for key, label, kind in [("delivery", "첫 납품 점수", "pct"), ("final", "최종 점수", "pct"),
                             ("user_turns", "사용자 개입 횟수", "num"), ("total_cost", "총 비용(USD)", "usd")]:
        print(f"\n## 과제별 {label}\n")
        print(f"| 과제 | {head} |")
        print("|---|" + "---:|" * len(conds))
        for t, name in TASK.items():
            if t not in data:
                continue
            row = {c: (st.mean([val(g, key) for g in data[t].get(c, []) if val(g, key) is not None]) if data[t].get(c) else None) for c in conds}
            summary["per_task"].setdefault(t, {})[key] = row
            print(f"| {name} | " + " | ".join(fmt(row[c], kind) for c in conds) + " |")
    (runs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
