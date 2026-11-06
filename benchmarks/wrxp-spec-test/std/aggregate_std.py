#!/usr/bin/env python3
"""Aggregate standard-benchmark grades into tables.md / summary.json.

Usage: python3 aggregate_std.py RUNS > RUNS/tables.md

For each benchmark and condition: the primary metric with a 95% bootstrap
interval over items, and the paired difference from `base` (same items) with
its own bootstrap interval. 2x2 main effects follow aggregate.py.
"""
import json
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aggregate import CONDS, LABEL, effects  # noqa: E402

BENCH = {
    "mmlu_pro": ("MMLU-Pro", "지식·추론", "정확도"),
    "gpqa": ("GPQA Diamond", "대학원 과학", "정확도"),
    "math500": ("MATH-500", "수학", "정확도"),
    "gsm8k": ("GSM8K", "초등 수학 서술형", "정확도"),
    "bbh": ("BIG-Bench Hard", "다단계 추론", "정확 일치"),
    "humaneval": ("HumanEval", "코드 생성", "pass@1"),
    "mbpp": ("MBPP", "코드 생성", "pass@1"),
    "ifeval": ("IFEval", "지시 이행", "프롬프트 strict 정확도"),
    "truthfulqa": ("TruthfulQA MC1", "사실성·환각", "정확도"),
    "scifact": ("SciFact (BEIR)", "검색", "Recall@5"),
}
SECONDARY = {"ifeval": ["prompt_loose", "inst_strict"], "scifact": ["recall@10", "ndcg@10", "mrr@10"]}
B = 2000


def boot(vals, rng):
    if not vals:
        return None
    means = sorted(st.mean(rng.choices(vals, k=len(vals))) for _ in range(B))
    return [means[int(0.025 * B)], means[int(0.975 * B) - 1]]


def f(v):
    return float(v) if isinstance(v, bool) else v


def main():
    runs = Path(sys.argv[1])
    rng = random.Random(7)
    data = {}  # bench -> item -> cond -> grade
    for g in runs.glob("*/*/*/grade.json"):
        cond = g.parent.name.rsplit("-", 1)[0]
        data.setdefault(g.parent.parent.parent.name, {}).setdefault(g.parent.parent.name, {})[cond] = json.loads(g.read_text())
    conds = [c for c in CONDS if any(c in v for b in data.values() for v in b.values())]
    summary = {"conds": conds, "bench": {}}
    head = " | ".join(LABEL[c] for c in conds)
    print("## 표준 벤치마크 주 지표 (괄호는 95% 부트스트랩 구간)\n")
    print(f"| 벤치마크 | 영역 | 지표 | n | {head} | 전역 효과 | /ha 효과 |")
    print("|---|---|---|---:|" + "---:|" * (len(conds) + 2))
    composite = {c: [] for c in conds}
    for bench, (name, area, metric) in BENCH.items():
        items = data.get(bench, {})
        full = [i for i, v in items.items() if all(c in v and v[c].get("score") is not None for c in conds)]
        if not full:
            continue
        res = {}
        for c in conds:
            vals = [f(items[i][c]["score"]) for i in full]
            res[c] = {"mean": st.mean(vals), "ci": boot(vals, rng)}
            composite[c].append(res[c]["mean"])
        diffs = {}
        for c in conds:
            if c == "base":
                continue
            d = [f(items[i][c]["score"]) - f(items[i]["base"]["score"]) for i in full]
            diffs[c] = {"mean": st.mean(d), "ci": boot(d, rng)}
        e = effects({c: res[c]["mean"] for c in conds})
        sec = {}
        for k in SECONDARY.get(bench, []):
            sec[k] = {c: st.mean(f(items[i][c].get(k, 0)) for i in full) for c in conds}
        proc = {c: {"cost_usd": st.mean(items[i][c]["process"]["cost_usd"] or 0 for i in full),
                    "duration_sec": st.mean(items[i][c]["process"]["duration_sec"] for i in full),
                    "output_tokens": st.mean(items[i][c]["process"]["output_tokens"] for i in full),
                    "parsed": st.mean(1.0 if items[i][c].get("parsed", True) else 0.0 for i in full)} for c in conds}
        summary["bench"][bench] = {"name": name, "area": area, "metric": metric, "n": len(full), "score": res,
                                   "diff_vs_base": diffs, "effects": e, "secondary": sec, "process": proc}
        cells = " | ".join(f"{res[c]['mean']*100:.0f}% ({res[c]['ci'][0]*100:.0f}–{res[c]['ci'][1]*100:.0f})" for c in conds)
        print(f"| {name} | {area} | {metric} | {len(full)} | {cells} | {e['global']*100:+.1f}%p | {e['ha']*100:+.1f}%p |")
    comp = {c: st.mean(v) for c, v in composite.items() if v}
    summary["composite"] = comp
    print("\n10개 벤치마크 주 지표 평균: " + " / ".join(f"{LABEL[c]} {comp[c]*100:.1f}%" for c in conds))

    print("\n## base 대비 같은 문항 차이 (95% 구간)\n")
    print("| 벤치마크 | " + " | ".join(LABEL[c] for c in conds if c != "base") + " |")
    print("|---|" + "---:|" * (len(conds) - 1))
    for bench, s in summary["bench"].items():
        cells = " | ".join(f"{s['diff_vs_base'][c]['mean']*100:+.0f}%p ({s['diff_vs_base'][c]['ci'][0]*100:+.0f}~{s['diff_vs_base'][c]['ci'][1]*100:+.0f})"
                           for c in conds if c != "base")
        print(f"| {s['name']} | {cells} |")

    print("\n## 보조 지표\n")
    print(f"| 벤치마크 | 지표 | {head} |")
    print("|---|---|" + "---:|" * len(conds))
    for bench, s in summary["bench"].items():
        for k, v in s["secondary"].items():
            print(f"| {s['name']} | {k} | " + " | ".join(f"{v[c]*100:.0f}%" if k != "ndcg@10" and k != "mrr@10" else f"{v[c]:.3f}" for c in conds) + " |")

    print("\n## 실행 비용 (문항 1개 평균)\n")
    print(f"| 벤치마크 | 지표 | {head} |")
    print("|---|---|" + "---:|" * len(conds))
    for bench, s in summary["bench"].items():
        p = s["process"]
        print(f"| {s['name']} | 비용(USD) | " + " | ".join(f"${p[c]['cost_usd']:.3f}" for c in conds) + " |")
        print(f"| {s['name']} | 시간(초) | " + " | ".join(f"{p[c]['duration_sec']:.0f}" for c in conds) + " |")
    allp = {c: [s["process"][c] for s in summary["bench"].values()] for c in conds}
    summary["process_mean"] = {c: {k: st.mean(x[k] for x in v) for k in ("cost_usd", "duration_sec", "output_tokens", "parsed")}
                               for c, v in allp.items()}
    print("\n전체 평균 비용: " + " / ".join(f"{LABEL[c]} ${summary['process_mean'][c]['cost_usd']:.3f}" for c in conds)
          + "  ·  시간: " + " / ".join(f"{LABEL[c]} {summary['process_mean'][c]['duration_sec']:.0f}초" for c in conds)
          + "  ·  ANSWER 형식 준수: " + " / ".join(f"{LABEL[c]} {summary['process_mean'][c]['parsed']*100:.0f}%" for c in conds))
    (runs / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
