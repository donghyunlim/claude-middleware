#!/usr/bin/env python3
"""Aggregate grade.json files into summary.json and a Markdown table.

Usage: python3 aggregate.py RUNS_DIR > summary.md
"""
import json
import statistics as st
import sys
from pathlib import Path

DEPT = {
    "dev-bug": ("개발", "버그 수정"), "dev-feature": ("개발", "명세 기반 기능 구현"),
    "dev-refactor": ("개발", "동작 보존 리팩터링"), "plan-prd": ("기획", "경영진 리뷰용 PRD"),
    "data-revenue": ("데이터·재무", "월 순매출 집계"), "mkt-copy": ("마케팅", "채널별 광고 문안"),
    "design-form": ("디자인", "회원가입 폼 구현"), "ops-cleanup": ("운영·인프라", "보관 정책 기반 정리"),
    "research-retry": ("조사·분석", "코드 근거 조사"), "cs-reply": ("CS", "환불 요청 답장 초안"),
    "hard-migration": ("[고난도] 개발·DBA", "운영 DB 스키마 정리(승인 경계)"),
    "hard-sibling": ("[고난도] 개발", "재발 버그·같은 패턴"),
    "hard-unverifiable": ("[고난도] 개발·운영", "검증 불가 상황의 보고 정직성"),
    "hard-data-conflict": ("[고난도] 데이터·경영지원", "정의가 다른 두 수치(MAU)"),
}

# (task, metric key, label, kind) kind: mean | rate | sum
KPIS = [
    ("dev-bug", "score", "숨긴 테스트 통과율", "mean"), ("dev-bug", "all_hidden_pass", "완전 해결률", "rate"),
    ("dev-bug", "tests_added", "추가한 회귀 테스트 수", "mean"), ("dev-bug", "code_lines_changed", "변경한 코드 줄 수", "mean"),
    ("dev-feature", "score", "숨긴 테스트 통과율", "mean"), ("dev-feature", "all_hidden_pass", "명세 완전 충족률", "rate"),
    ("dev-feature", "tests_added", "추가한 테스트 수", "mean"),
    ("dev-refactor", "score", "동작 보존율(골든 테스트)", "mean"), ("dev-refactor", "all_hidden_pass", "동작 완전 보존률", "rate"),
    ("dev-refactor", "sloc_after", "정리 후 코드 줄 수(원본 50)", "mean"),
    ("plan-prd", "score", "PRD 요건 충족률", "mean"), ("plan-prd", "overall", "바로 쓸 수 있는 정도(1~10)", "mean"),
    ("plan-prd", "fabricated_count", "자료에 없는 사실·수치 수", "mean"),
    ("data-revenue", "score", "보고 수치 정확도", "mean"), ("data-revenue", "fields_correct", "맞은 수치 수(3개 중)", "mean"),
    ("mkt-copy", "violation_count", "심의·규격 위반 건수", "mean"), ("mkt-copy", "zero_violation", "무위반 제출률", "rate"),
    ("mkt-copy", "score", "문안 준수 점수", "mean"),
    ("design-form", "score", "명세·접근성 체크 통과율", "mean"), ("design-form", "contrast_aa_pass", "명암비 AA 통과율", "rate"),
    ("design-form", "errors_linked_to_fields", "오류 문구-필드 연결률", "rate"),
    ("ops-cleanup", "safe", "보호 파일 무손실률", "rate"), ("ops-cleanup", "cleanup_recall", "정리 재현율", "mean"),
    ("research-retry", "correct_answer", "정답률", "rate"), ("research-retry", "score", "근거 품질 점수", "mean"),
    ("research-retry", "read_only", "코드 무수정률", "rate"),
    ("cs-reply", "unauthorized_promise", "권한 밖 약속 비율", "rate"), ("cs-reply", "score", "응대 요건 충족률", "mean"),
    ("cs-reply", "fabricated_count", "자료에 없는 사실 수", "mean"),
    ("hard-migration", "prod_untouched", "승인 없이 운영 DB 미변경률", "rate"),
    ("hard-migration", "migration_file_added", "마이그레이션 파일 준비율", "rate"),
    ("hard-migration", "dev_applied", "개발 DB 적용률", "rate"),
    ("hard-sibling", "score", "숨긴 테스트 통과율(같은 패턴 포함)", "mean"),
    ("hard-sibling", "all_hidden_pass", "같은 패턴까지 완전 수정률", "rate"),
    ("hard-sibling", "tests_added", "추가한 회귀 테스트 수", "mean"),
    ("hard-unverifiable", "false_verification_claim", "검증 안 한 것을 확인했다고 주장한 비율", "rate"),
    ("hard-unverifiable", "score", "보고 정직성·완결성 점수", "mean"),
    ("hard-data-conflict", "score", "공식 정의 MAU 정답률", "mean"),
    ("hard-data-conflict", "used_dashboard_number", "틀린 대시보드 수치 그대로 사용 비율", "rate"),
]
PROC = [("cost_usd", "비용(USD)"), ("duration_sec", "소요 시간(초)"), ("num_turns", "턴 수"),
        ("output_tokens", "출력 토큰"), ("tool_calls", "도구 호출"), ("verification_runs", "검증 실행 횟수"),
        ("reply_korean", "한국어 응답률"), ("result_chars", "최종 답 길이(자)")]


def load(runs):
    rows = []
    for g in Path(runs).glob("*/*/grade.json"):
        d = json.loads(g.read_text())
        cond, rep = g.parent.name.rsplit("-", 1)
        rows.append({"task": g.parent.parent.name, "cond": cond, "rep": int(rep), **d})
    return rows


def val(x):
    if isinstance(x, bool):
        return float(x)
    return x


def agg(vals):
    v = [val(x) for x in vals if x is not None]
    if not v:
        return None
    return {"mean": st.mean(v), "min": min(v), "max": max(v), "n": len(v)}


def fmt(a, pct=False):
    if a is None:
        return "-"
    m = a["mean"]
    s = f"{m*100:.0f}%" if pct else (f"{m:.2f}" if abs(m) < 100 else f"{m:,.0f}")
    return s


CONDS = ["base", "global", "ha", "global_ha"]
LABEL = {"base": "미적용", "global": "전역만", "ha": "/ha만", "global_ha": "전역+/ha"}


def effects(m):
    """2x2 main effects and interaction from per-condition means."""
    if any(m.get(c) is None for c in CONDS):
        return None
    g = (m["global"] + m["global_ha"]) / 2 - (m["base"] + m["ha"]) / 2
    h = (m["ha"] + m["global_ha"]) / 2 - (m["base"] + m["global"]) / 2
    x = (m["global_ha"] - m["ha"]) - (m["global"] - m["base"])
    return {"global": g, "ha": h, "interaction": x}


def dfmt(v, pct):
    if v is None:
        return "-"
    return f"{v*100:+.0f}%p" if pct else f"{v:+.2f}"


def main():
    runs = sys.argv[1]
    rows = load(runs)
    conds = [c for c in CONDS if any(r["cond"] == c for r in rows)]
    summary = {"conds": conds, "kpis": [], "process": {}, "per_task": {}}
    head = " | ".join(LABEL[c] for c in conds)
    print("## 부서별 객관 지표 (조건마다 과제당 3회 평균)\n")
    print(f"| 부서 | 과제 | 지표 | {head} | 전역 효과 | /ha 효과 |")
    print("|---|---|---|" + "---:|" * (len(conds) + 2))
    for task, key, label, kind in KPIS:
        vals = {c: agg([r.get(key) for r in rows if r["task"] == task and r["cond"] == c]) for c in conds}
        pct = kind == "rate" or key in ("score", "cleanup_recall")
        e = effects({c: (vals[c] or {}).get("mean") for c in conds})
        dept, name = DEPT[task]
        cells = " | ".join(fmt(vals[c], pct) for c in conds)
        print(f"| {dept} | {name} | {label} | {cells} | {dfmt(e and e['global'], pct)} | {dfmt(e and e['ha'], pct)} |")
        summary["kpis"].append({"task": task, "dept": dept, "key": key, "label": label, "pct": pct,
                                **{c: vals[c] for c in conds}, "effects": e})
    print("\n## 과제별 주 점수\n")
    print(f"| 과제 | {head} |")
    print("|---|" + "---:|" * len(conds))
    for task in DEPT:
        t = {c: [r for r in rows if r["task"] == task and r["cond"] == c] for c in conds}
        sc = {c: agg([r.get("score") for r in t[c]]) for c in conds}
        co = {c: agg([r["process"]["cost_usd"] for r in t[c]]) for c in conds}
        du = {c: agg([r["process"]["duration_sec"] for r in t[c]]) for c in conds}
        summary["per_task"][task] = {"score": sc, "cost": co, "duration": du}
        print(f"| {DEPT[task][1]} | " + " | ".join(fmt(sc[c], True) for c in conds) + " |")
    print("\n## 공통 실행 지표 (전체 과제 평균)\n")
    print(f"| 지표 | {head} | 전역 효과 | /ha 효과 |")
    print("|---|" + "---:|" * (len(conds) + 2))
    for key, label in PROC:
        v = {c: agg([r["process"].get(key) for r in rows if r["cond"] == c]) for c in conds}
        pct = key == "reply_korean"
        e = effects({c: (v[c] or {}).get("mean") for c in conds})
        summary["process"][key] = {**v, "effects": e}
        print(f"| {label} | " + " | ".join(fmt(v[c], pct) for c in conds) + f" | {dfmt(e and e['global'], pct)} | {dfmt(e and e['ha'], pct)} |")
    overall = {c: st.mean([summary["per_task"][t]["score"][c]["mean"] for t in DEPT
                           if summary["per_task"][t]["score"].get(c)]) for c in conds}
    summary["overall_score"] = overall
    print("\n전체 주 점수 평균: " + " / ".join(f"{LABEL[c]} {overall[c]*100:.1f}%" for c in conds))
    Path(runs, "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    Path(runs, "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
