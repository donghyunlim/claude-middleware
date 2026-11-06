#!/usr/bin/env python3
"""Grade hard-suite runs: first-try (snap0) and final (last snap) scores plus cost/turn metrics.

Usage: python3 hard/grade_hard.py RUNS [--force]
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from grade import pytest_counts  # noqa: E402

TASKS = HERE / "tasks"


def judge(task, work: Path, cache: Path):
    if cache.exists():
        return json.loads(cache.read_text())
    out = work / "roadmap.md"
    if not out.exists():
        return {"items": {}, "overall": 0, "missing": True}
    fx = TASKS / task / "fixture"
    src = "\n\n".join(f"### 자료: {p.name}\n{p.read_text()}" for p in sorted(fx.iterdir()) if p.is_file())
    rubric = (TASKS / task / "hidden" / "rubric.md").read_text()
    text = out.read_text()
    prompt = f"""당신은 엄격한 블라인드 채점자다. 아래 '자료'만 사실로 인정한다. 채점 기준의 각 항목을 0 또는 1로 매기고 근거를 짧게 인용하라.
추가로 overall(1~10): 대표가 이 문서만으로 회의에서 결정할 수 있는 정도. 문서 길이: {len(text)}자.

{src}

### 채점 기준
{rubric}

### 채점할 문서
<<<
{text}
>>>

JSON 한 개만 출력하라: {{"items": {{"<항목ID>": {{"score": 0 또는 1, "why": "..."}}}}, "overall": 정수}}"""
    p = subprocess.run(["claude", "-p", "--tools", "", "--output-format", "json"], input=prompt,
                       capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
    res = json.loads(re.search(r"\{.*\}", json.loads(p.stdout)["result"], re.S).group(0))
    cache.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def score(task, work: Path, run_dir: Path, tag: str):
    if task in ("export", "coupon", "inventory"):
        p, t = pytest_counts(work, TASKS / task / "hidden")
        return {"score": p / t, "pass": p, "total": t}
    if task == "churn":
        truth = json.loads((TASKS / task / "hidden/truth.json").read_text())
        try:
            v = float(json.loads((work / "answer.json").read_text())["churn_rate_pct"])
        except Exception:
            return {"score": 0.0, "answer": None}
        return {"score": float(abs(v - truth["churn_rate_pct"]) <= 0.01), "answer": v}
    if task == "roadmap":
        j = judge(task, work, run_dir / f"judge_{tag}.json")
        items = j.get("items", {})
        return {"score": (sum(int(v["score"]) for v in items.values()) / len(items)) if items else 0.0,
                "overall": j.get("overall"), "items": {k: v["score"] for k, v in items.items()},
                "chars": len((work / "roadmap.md").read_text()) if (work / "roadmap.md").exists() else 0}
    raise KeyError(task)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for res in sorted(Path(a.runs).glob("*/*/result.json")):
        run_dir = res.parent
        task = run_dir.parent.name
        out = run_dir / "grade.json"
        if out.exists() and not a.force:
            continue
        m = json.loads(res.read_text())
        snaps = sorted(run_dir.glob("snap*"), key=lambda p: int(p.name[4:]))
        turns = m["turns"]
        # first delivery = the agent turn the user first judged as finished work (revise/accept)
        di = next((t["k"] for t in turns if t.get("user_action") in ("revise", "accept")), turns[-1]["k"])
        try:
            first = score(task, snaps[0], run_dir, "first")
            deliv = first if di == 0 else score(task, run_dir / f"snap{di}", run_dir, f"deliv{di}")
            final = deliv if len(snaps) - 1 == di else score(task, snaps[-1], run_dir, "final")
        except Exception as e:
            first = deliv = final = {"score": None, "error": repr(e)}
        g = {"first": first, "delivery": deliv, "delivery_turn": di, "final": final,
             "agent_turns": len(turns), "user_turns": m["user_turns"], "accepted": m["accepted"],
             "questions_answered": sum(1 for t in turns if t.get("user_action") == "answer"),
             "revisions_requested": sum(1 for t in turns if t.get("user_action") == "revise"),
             "user_chars": sum(len(t.get("user_message") or "") for t in turns),
             "agent_cost": sum(t["agent_cost"] for t in turns),
             "user_cost": sum(t.get("user_cost", 0) for t in turns),
             "agent_sec": sum(t["agent_sec"] for t in turns), "wall_sec": m["wall_sec"],
             "first_reply_chars": len(turns[0]["agent_message"]),
             "first_reply_korean": len(re.findall(r"[가-힣]", turns[0]["agent_message"])) >
                                   len(re.findall(r"[A-Za-z]", re.sub(r"`[^`]*`", "", turns[0]["agent_message"])))}
        out.write_text(json.dumps(g, ensure_ascii=False, indent=1))
        print(task, run_dir.name, "first", first.get("score"), "deliv", deliv.get("score"), "final", final.get("score"), "uturns", g["user_turns"], flush=True)


if __name__ == "__main__":
    main()
