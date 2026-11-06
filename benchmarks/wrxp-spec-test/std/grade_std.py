#!/usr/bin/env python3
"""Grade standard-benchmark runs: RUNS/<bench>/<item_id>/<cond>-1/ -> grade.json.

Usage: python3 grade_std.py RUNS [--force] [--items DIR]

Metrics per bench:
  mmlu_pro, gpqa, truthfulqa (MC1)  accuracy (letter match)
  gsm8k                             accuracy (numeric match)
  math500                           accuracy (normalized match, LLM equivalence check only on mismatch)
  bbh                               exact match (normalized)
  humaneval, mbpp                   pass@1 (hidden tests on solution.py)
  ifeval                            prompt-level strict / loose, instruction-level strict
  scifact                           Recall@5, Recall@10, nDCG@10, MRR@10
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from grade import process_metrics  # noqa: E402


def final_text(run_dir):
    m = json.loads((run_dir / "result.json").read_text())
    return ((m.get("final") or {}).get("result") or "")


def extract(text):
    hits = re.findall(r"ANSWER\s*[:：]\s*(.+)", text)
    if not hits:
        return None
    a = hits[-1].strip()
    a = re.sub(r"^[`*_\s]+|[`*_\s]+$", "", a)
    return a.strip()


def letter(a):
    if a is None:
        return None
    m = re.match(r"^\(?([A-P])\)?(?:[.)\s]|$)", a.strip())
    return m.group(1) if m else None


def num(a):
    if a is None:
        return None
    s = a.replace(",", "").replace("$", "")
    m = re.findall(r"-?\d+(?:\.\d+)?", s)
    return float(m[0]) if m else None


def norm_math(s):
    if s is None:
        return None
    s = s.strip().strip("$").strip()
    s = re.sub(r"\\boxed\{(.*)\}$", r"\1", s)
    for a, b in [("\\left", ""), ("\\right", ""), ("\\!", ""), ("\\,", ""), ("\\;", ""), ("dfrac", "frac"),
                 ("tfrac", "frac"), ("^\\circ", ""), ("^{\\circ}", ""), ("\\%", ""), ("%", ""), (" ", ""),
                 ("\\text{", "{"), ("\\mbox{", "{"), ("\\dots", "..."), ("\\cdot", "*")]:
        s = s.replace(a, b)
    s = re.sub(r"\{\s*\}", "", s)
    s = s.rstrip(".")
    return s


def llm_equiv(gold, ans, cache: Path):
    if cache.exists():
        return json.loads(cache.read_text())["equivalent"]
    prompt = (f"Are these two final answers to a math problem mathematically equivalent? Gold: {gold}\nCandidate: {ans}\n"
              "Reply with exactly one word: YES or NO.")
    p = subprocess.run(["claude", "-p", "--tools", "", "--model", "sonnet", "--output-format", "json"], input=prompt,
                       capture_output=True, text=True, timeout=300, cwd=tempfile.gettempdir())
    verdict = "YES" in json.loads(p.stdout)["result"].upper()
    cache.write_text(json.dumps({"equivalent": verdict}))
    return verdict


def norm_exact(s):
    if s is None:
        return None
    s = s.strip().strip(".").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def run_code(code: str, timeout=60):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.py"
        p.write_text(code)
        try:
            r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=timeout, cwd=d)
            return r.returncode == 0, r.stderr[-400:]
        except subprocess.TimeoutExpired:
            return False, "timeout"


def g_code(item, run_dir):
    sol = run_dir / "work" / "solution.py"
    if not sol.exists():
        return {"score": 0.0, "pass": False, "error": "no solution.py"}
    src = sol.read_text()
    g = item["gold"]
    if "entry_point" in g:
        ok, err = run_code(src + "\n\n" + g["test"] + f"\n\ncheck({g['entry_point']})\n")
    else:
        ok, err = run_code(src + "\n\n" + (g.get("setup") or "") + "\n" + "\n".join(g["tests"]) + "\n")
    return {"score": float(ok), "pass": ok, "error": None if ok else err}


def g_ifeval(item, run_dir):
    from ifeval_lib import evaluation_lib as ev
    resp = final_text(run_dir)
    key = int(item["id"].split("-")[1])
    inp = ev.InputExample(key=key, instruction_id_list=item["gold"]["instruction_id_list"], prompt=item["prompt"],
                          kwargs=item["gold"]["kwargs"])
    strict = ev.test_instruction_following_strict(inp, {item["prompt"]: resp})
    loose = ev.test_instruction_following_loose(inp, {item["prompt"]: resp})
    return {"score": float(strict.follow_all_instructions), "prompt_strict": strict.follow_all_instructions,
            "prompt_loose": loose.follow_all_instructions,
            "inst_strict": sum(strict.follow_instruction_list) / len(strict.follow_instruction_list),
            "inst_followed": strict.follow_instruction_list}


def g_retrieval(item, ans):
    gold = set(item["gold"])
    ids = [int(x) for x in re.findall(r"\d+", ans or "")][:10]
    seen, ranked = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ranked.append(i)
    r5 = len(gold & set(ranked[:5])) / len(gold)
    r10 = len(gold & set(ranked[:10])) / len(gold)
    dcg = sum(1 / math.log2(k + 2) for k, d in enumerate(ranked[:10]) if d in gold)
    idcg = sum(1 / math.log2(k + 2) for k in range(min(len(gold), 10)))
    mrr = next((1 / (k + 1) for k, d in enumerate(ranked[:10]) if d in gold), 0.0)
    return {"score": r5, "recall@5": r5, "recall@10": r10, "ndcg@10": dcg / idcg, "mrr@10": mrr, "ranked": ranked}


def grade_item(bench, item, run_dir):
    text = final_text(run_dir)
    ans = extract(text)
    if item["kind"] == "code":
        return g_code(item, run_dir)
    if item["kind"] == "ifeval":
        return g_ifeval(item, run_dir)
    if item["kind"] == "retrieval":
        return {"answer": ans, **g_retrieval(item, ans)}
    out = {"answer": ans, "parsed": ans is not None}
    if item["kind"] == "mc":
        ok = letter(ans) == item["gold"]
    elif item["kind"] == "number":
        n = num(ans)
        ok = n is not None and abs(n - float(item["gold"])) < 1e-6
    elif item["kind"] == "exact":
        a, g = norm_exact(ans), norm_exact(item["gold"])
        ok = a == g or (g.startswith("(") and a in (g.strip("()"), g))
    elif item["kind"] == "math":
        a, g = norm_math(ans), norm_math(item["gold"])
        ok = a is not None and a == g
        if not ok and ans:
            ok = llm_equiv(item["gold"], ans, run_dir / "equiv.json")
            out["llm_equiv_used"] = True
    out.update({"score": float(ok), "correct": ok})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--items", default=os.environ.get("WRXP_ITEMS", str(HERE / "items")))
    a = ap.parse_args()
    items = {}
    for f in Path(a.items).glob("*.jsonl"):
        for line in f.read_text().splitlines():
            it = json.loads(line)
            items[(f.stem, it["id"])] = it
    for res in sorted(Path(a.runs).glob("*/*/*/result.json")):
        run_dir = res.parent
        bench, item_id = run_dir.parent.parent.name, run_dir.parent.name
        out = run_dir / "grade.json"
        if out.exists() and not a.force:
            continue
        try:
            g = grade_item(bench, items[(bench, item_id)], run_dir)
        except Exception as e:
            g = {"score": None, "grader_error": repr(e)}
        g["process"] = process_metrics(run_dir)
        out.write_text(json.dumps(g, ensure_ascii=False, indent=1))
        print(bench, item_id, run_dir.name, g.get("score"), flush=True)


if __name__ == "__main__":
    main()
