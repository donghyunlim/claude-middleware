#!/usr/bin/env python3
"""Check whether the simulated user revealed more hidden decisions than the agent asked about.

For every run where the user answered a question before the first delivery, a judge (Sonnet) maps the
agent's questions and the user's answers to hidden-decision ids. Writes RUNS/<task>/<run>/oversharing.json
and prints per-condition totals.
Usage: python3 hard/oversharing_check.py RUNS [--parallel 8]
"""
import argparse
import collections
import concurrent.futures as cf
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"

PROMPT = """Hidden decisions of a task:
{hidden}

Below are the agent's question messages and the user's answers, in order.
{pairs}

For the agent messages: list the hidden decision ids they explicitly ask about ("asked_ids"), and separately the ids
they mention without asking, as a stated default/assumption or as an open invitation to specify ("mentioned_ids";
e.g. "I'll use 100 seats unless you say otherwise", "if your company has a definition, tell me").
For the answers, list the hidden decision ids whose correct value the user's answers state or clearly imply ("revealed_ids").
Output one JSON object only: {{"asked_ids": ["H1"], "mentioned_ids": ["H2"], "revealed_ids": ["H1", "H2", "H3"]}}"""


def check(run_dir: Path):
    out = run_dir / "oversharing.json"
    if out.exists() and "mentioned_ids" in json.loads(out.read_text()):
        return json.loads(out.read_text())
    m = json.loads((run_dir / "result.json").read_text())
    g = json.loads((run_dir / "grade.json").read_text())
    pairs = [(t["agent_message"], t["user_message"]) for t in m["turns"]
             if t.get("user_action") == "answer" and t["k"] < g["delivery_turn"]]
    if not pairs:
        return None
    ann = json.loads((TASKS / run_dir.parent.name / "annotation.json").read_text())
    hidden = "\n".join(f"- {h['id']}: {h['decision']} (correct: {h['correct']})" for h in ann["hidden"])
    text = PROMPT.format(hidden=hidden, pairs="\n\n".join(f"AGENT: {a}\nUSER: {u}" for a, u in pairs))
    p = subprocess.run(["claude", "-p", "--tools", "", "--model", "sonnet", "--output-format", "json"], input=text,
                       capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
    txt = json.loads(p.stdout)["result"]
    j = json.JSONDecoder().raw_decode(txt[txt.index("{"):])[0]
    j["n_hidden"] = len(ann["hidden"])
    out.write_text(json.dumps(j, ensure_ascii=False))
    return j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--parallel", type=int, default=8)
    a = ap.parse_args()
    dirs = sorted(p.parent for p in Path(a.runs).glob("*/*/grade.json"))
    tot = collections.defaultdict(lambda: collections.Counter())
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for d, j in zip(dirs, ex.map(check, dirs)):
            if not j:
                continue
            c = d.name.rsplit("-", 1)[0]
            asked, ment, rev = set(j["asked_ids"]), set(j.get("mentioned_ids", [])) - set(j["asked_ids"]), set(j["revealed_ids"])
            tot[c]["runs"] += 1
            tot[c]["asked"] += len(asked)
            tot[c]["revealed"] += len(rev)
            tot[c]["revealed_asked"] += len(rev & asked)
            tot[c]["revealed_mentioned"] += len(rev & ment)
            tot[c]["revealed_unprompted"] += len(rev - asked - ment)
    summary = {}
    for c, v in tot.items():
        summary[c] = dict(v)
        print(c, dict(v), f"unprompted share = {v['revealed_unprompted'] / max(v['revealed'], 1):.0%}")
    (Path(a.runs) / "oversharing_summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
