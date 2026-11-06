#!/usr/bin/env python3
"""Download public benchmark data and write a fixed-seed sample to std/items/<bench>.jsonl.

Usage: python3 prepare_data.py --cache DIR [--n 20] [--seed 2026]

Sources (Hugging Face is not reachable from the benchmark environment, so every
set comes from its original GitHub/S3 release):
  mmlu_pro   TIGER-AI-Lab/MMLU-Pro eval_results (questions/options/answers are inside)
  gpqa       idavidrein/gpqa dataset.zip (Diamond split; password from the README)
  math500    openai/prm800k math_splits/test.jsonl (the MATH-500 subset)
  gsm8k      openai/grade-school-math test.jsonl
  bbh        suzgunmirac/BIG-Bench-Hard (sampled across the 27 tasks)
  humaneval  openai/human-eval HumanEval.jsonl.gz
  mbpp       google-research mbpp.jsonl (test ids 11-510)
  ifeval     google-research instruction_following_eval input_data.jsonl
  truthfulqa sylinrl/TruthfulQA mc_task.json (MC1)
  scifact    allenai/scifact release (claims_dev + corpus) for retrieval
"""
import argparse
import csv
import glob
import gzip
import io
import json
import random
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = "https://raw.githubusercontent.com"
LETTERS = "ABCDEFGHIJKLMNOP"


def fetch(url, cache: Path):
    p = cache / re.sub(r"[^A-Za-z0-9._-]", "_", url)[-150:]
    if not p.exists():
        subprocess.run(["curl", "-sSfL", "-m", "300", "-o", str(p), url], check=True)
    return p


def mc_prompt(question, options):
    lines = [question.strip(), ""] + [f"{LETTERS[i]}. {o}" for i, o in enumerate(options)]
    lines += ["", "Answer the multiple-choice question. End your reply with a final line exactly in the form `ANSWER: <letter>`."]
    return "\n".join(lines)


def mmlu_pro(cache, rng, n):
    repo = cache / "MMLU-Pro"
    if not repo.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/TIGER-AI-Lab/MMLU-Pro", str(repo)], check=True)
    z = zipfile.ZipFile(repo / "eval_results/model_outputs_claude-3-5-sonnet-20241022_5shots.json.zip")
    data = json.loads(z.read([x for x in z.namelist() if x.endswith(".json")][0]))
    seen, rows = set(), []
    for r in data:
        if r["question_id"] in seen:
            continue
        seen.add(r["question_id"])
        rows.append(r)
    rows.sort(key=lambda r: r["question_id"])
    out = []
    for r in rng.sample(rows, n):
        out.append({"id": f"mmlu_pro-{r['question_id']}", "kind": "mc", "category": r["category"],
                    "prompt": mc_prompt(r["question"], r["options"]), "gold": r["answer"]})
    return out


def gpqa(cache, rng, n):
    z = zipfile.ZipFile(fetch(f"{RAW}/idavidrein/gpqa/main/dataset.zip", cache))
    name = [x for x in z.namelist() if x.endswith("gpqa_diamond.csv")][0]
    text = z.read(name, pwd=b"deserted-untie-orchid").decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for r in rng.sample(rows, n):
        opts = [r["Correct Answer"], r["Incorrect Answer 1"], r["Incorrect Answer 2"], r["Incorrect Answer 3"]]
        opts = [o.strip() for o in opts]
        order = list(range(4))
        rng.shuffle(order)
        shuffled = [opts[i] for i in order]
        gold = LETTERS[order.index(0)]
        out.append({"id": f"gpqa-{r['Record ID']}", "kind": "mc", "category": r.get("High-level domain", ""),
                    "prompt": mc_prompt(r["Question"], shuffled), "gold": gold})
    return out


def math500(cache, rng, n):
    rows = [json.loads(l) for l in fetch("https://media.githubusercontent.com/media/openai/prm800k/main/prm800k/math_splits/test.jsonl", cache).read_text().splitlines()]
    out = []
    for r in rng.sample(rows, n):
        out.append({"id": "math500-" + re.sub(r"[^A-Za-z0-9._-]", "_", r["unique_id"]), "kind": "math", "category": r["subject"],
                    "prompt": r["problem"] + "\n\nSolve the problem. End your reply with a final line exactly in the form `ANSWER: <final answer>` (LaTeX allowed, no extra words).",
                    "gold": r["answer"]})
    return out


def gsm8k(cache, rng, n):
    rows = [json.loads(l) for l in fetch(f"{RAW}/openai/grade-school-math/master/grade_school_math/data/test.jsonl", cache).read_text().splitlines()]
    out = []
    for i, r in sorted(rng.sample(list(enumerate(rows)), n)):
        out.append({"id": f"gsm8k-{i}", "kind": "number", "category": "",
                    "prompt": r["question"] + "\n\nEnd your reply with a final line exactly in the form `ANSWER: <number>`.",
                    "gold": r["answer"].split("####")[-1].strip().replace(",", "")})
    return out


BBH_TASKS = ["boolean_expressions", "causal_judgement", "date_understanding", "disambiguation_qa", "dyck_languages",
             "formal_fallacies", "geometric_shapes", "hyperbaton", "logical_deduction_five_objects",
             "logical_deduction_seven_objects", "logical_deduction_three_objects", "movie_recommendation",
             "multistep_arithmetic_two", "navigate", "object_counting", "penguins_in_a_table",
             "reasoning_about_colored_objects", "ruin_names", "salient_translation_error_detection", "snarks",
             "sports_understanding", "temporal_sequences", "tracking_shuffled_objects_five_objects",
             "tracking_shuffled_objects_seven_objects", "tracking_shuffled_objects_three_objects", "web_of_lies",
             "word_sorting"]


def bbh(cache, rng, n):
    pool = []
    for t in BBH_TASKS:
        ex = json.loads(fetch(f"{RAW}/suzgunmirac/BIG-Bench-Hard/main/bbh/{t}.json", cache).read_text())["examples"]
        pool += [(t, i, e) for i, e in enumerate(ex)]
    tasks = rng.sample(BBH_TASKS, min(n, len(BBH_TASKS)))
    out = []
    for t in tasks[:n]:
        cand = [p for p in pool if p[0] == t]
        _, i, e = rng.choice(cand)
        out.append({"id": f"bbh-{t}-{i}", "kind": "exact", "category": t,
                    "prompt": e["input"] + "\n\nEnd your reply with a final line exactly in the form `ANSWER: <answer>`, where <answer> uses the same format as the options or the expected output (for example `(B)`, `True`, `valid`, or the sorted words).",
                    "gold": e["target"]})
    return out


def humaneval(cache, rng, n):
    rows = [json.loads(l) for l in gzip.decompress(fetch(f"{RAW}/openai/human-eval/master/data/HumanEval.jsonl.gz", cache).read_bytes()).decode().splitlines()]
    out = []
    for r in sorted(rng.sample(rows, n), key=lambda r: int(r["task_id"].split("/")[1])):
        out.append({"id": "humaneval-" + r["task_id"].split("/")[1], "kind": "code", "category": "",
                    "files": {"solution.py": r["prompt"]},
                    "prompt": f"Complete the function `{r['entry_point']}` in `solution.py` so that it satisfies its docstring. Keep the signature. Use only the standard library.",
                    "gold": {"test": r["test"], "entry_point": r["entry_point"]}})
    return out


def mbpp(cache, rng, n):
    rows = [json.loads(l) for l in fetch(f"{RAW}/google-research/google-research/master/mbpp/mbpp.jsonl", cache).read_text().splitlines()]
    rows = [r for r in rows if 11 <= r["task_id"] <= 510]
    out = []
    for r in sorted(rng.sample(rows, n), key=lambda r: r["task_id"]):
        out.append({"id": f"mbpp-{r['task_id']}", "kind": "code", "category": "",
                    "files": {},
                    "prompt": f"{r['text']}\n\nWrite the function in `solution.py`. Your code should pass this test:\n\n{r['test_list'][0]}",
                    "gold": {"tests": r["test_list"] + r.get("challenge_test_list", []), "setup": r.get("test_setup_code", "")}})
    return out


def ifeval(cache, rng, n):
    rows = [json.loads(l) for l in fetch(f"{RAW}/google-research/google-research/master/instruction_following_eval/data/input_data.jsonl", cache).read_text().splitlines()]
    out = []
    for r in sorted(rng.sample(rows, n), key=lambda r: r["key"]):
        out.append({"id": f"ifeval-{r['key']}", "kind": "ifeval", "category": ",".join(r["instruction_id_list"]),
                    "prompt": r["prompt"], "gold": {"instruction_id_list": r["instruction_id_list"], "kwargs": r["kwargs"]}})
    return out


def truthfulqa(cache, rng, n):
    rows = json.loads(fetch(f"{RAW}/sylinrl/TruthfulQA/main/data/mc_task.json", cache).read_text())
    out = []
    for i, r in sorted(rng.sample(list(enumerate(rows)), n)):
        items = list(r["mc1_targets"].items())
        rng.shuffle(items)
        opts = [k for k, _ in items]
        gold = LETTERS[[v for _, v in items].index(1)] if len(opts) <= 10 else None
        if gold is None:
            continue
        out.append({"id": f"truthfulqa-{i}", "kind": "mc", "category": "", "prompt": mc_prompt(r["question"], opts), "gold": gold})
    return out


def scifact(cache, rng, n):
    tgz = fetch("https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz", cache)
    t = tarfile.open(tgz)
    def member(name):
        return t.extractfile([m for m in t.getmembers() if m.name.endswith(name)][0]).read().decode()
    corpus = [json.loads(l) for l in member("corpus.jsonl").splitlines()]
    claims = [json.loads(l) for l in member("claims_dev.jsonl").splitlines()]
    claims = [c for c in claims if c.get("evidence")]
    corpus_dir = HERE / "items" / "scifact_corpus"
    if not corpus_dir.exists():
        corpus_dir.mkdir(parents=True)
        for d in corpus:
            (corpus_dir / f"{d['doc_id']}.txt").write_text(d["title"] + "\n\n" + " ".join(d["abstract"]))
    out = []
    for c in sorted(rng.sample(claims, n), key=lambda c: c["id"]):
        out.append({"id": f"scifact-{c['id']}", "kind": "retrieval", "category": "", "corpus": "scifact_corpus",
                    "prompt": ("The folder `corpus/` holds about 5,000 scientific abstracts, one per file named `<doc_id>.txt`.\n\n"
                               f"Claim: {c['claim']}\n\nFind the abstracts that provide evidence to support or refute this claim. "
                               "Rank the 10 most relevant documents. End your reply with a final line exactly in the form "
                               "`ANSWER: <doc_id>, <doc_id>, ...` (most relevant first, up to 10 ids)."),
                    "gold": sorted(int(k) for k in c["evidence"].keys())})
    return out


BENCHES = {"mmlu_pro": mmlu_pro, "gpqa": gpqa, "math500": math500, "gsm8k": gsm8k, "bbh": bbh,
           "humaneval": humaneval, "mbpp": mbpp, "ifeval": ifeval, "truthfulqa": truthfulqa, "scifact": scifact}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    (HERE / "items").mkdir(exist_ok=True)
    for name, fn in BENCHES.items():
        if a.only and name not in a.only.split(","):
            continue
        rng = random.Random(f"{a.seed}-{name}")
        items = fn(cache, rng, a.n)
        with open(HERE / "items" / f"{name}.jsonl", "w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(name, len(items))


if __name__ == "__main__":
    main()
