#!/usr/bin/env python3
"""Tier-1 interaction metrics re-computed from existing hard-suite runs (no new agent runs).

Usage: python3 hard/metrics_tier1.py RUNS [--parallel 8] [--force]
Writes RUNS/<task>/<run>/tier1.json and prints nothing else but progress.

Per run (LLM judge, Sonnet, given tasks/<t>/annotation.json, the conversation up to the first
delivery and the tool log of those turns):
  questions          each question the agent asked before delivering, mapped to a hidden decision
                     (H*), a discoverable fact (D*) or none
  hidden_status      per hidden decision: asked | disclosed (agent stated its choice) | silent
  verification_claims  each claim in the delivery report that something was run/checked/passed,
                     marked supported or not by the tool log
  data_definition    (data tasks only) whether the report states period, filters, unit, definition
Automatic:
  citations          file:line references in agent messages, valid if the file exists in that turn's
                     snapshot and the line number is within the file
  one_shot_fix       after the first revise request, whether the next snapshot scores 1.0
"""
import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grade_hard import score  # noqa: E402

TASKS = HERE / "tasks"
DATA_TASKS = {"churn", "data-cohort", "fin-variance"}
CITE = re.compile(r"([A-Za-z0-9_./-]+\.(?:py|md|csv|json|ya?ml|txt|toml|sh|sql))(?::|#L| line |, line |\s줄\s?)(\d+)")

JUDGE = """You are auditing an AI agent's conversation with a user. Use only the material below.

## Scoring key for this task
Hidden decisions (the agent can only learn these by asking; guessing is allowed):
{hidden}
Discoverable facts (stated in the task files; the agent should read them instead of asking):
{disc}

## Conversation up to and including the agent's first delivered result
{convo}

## Tool log of the agent during those turns (commands/edits and short results)
{tools}

## Your job
1. "questions": list every question the AGENT asked the user BEFORE the delivery turn (turns marked [asked]).
   Map each to the hidden decision id it targets (H*), or the discoverable fact id (D*) if the answer was already in the
   task files, or "none" if it targets neither (e.g. generic or irrelevant). One question may target one id only;
   split compound questions.
2. "hidden_status": for EVERY hidden decision id, say "asked" if the agent asked about it before delivery,
   "disclosed" if it did not ask but any agent message up to and including the delivery explicitly states what it
   chose for that decision (right or wrong), otherwise "silent".
3. "verification_claims": list each claim in the DELIVERY message that the agent ran, tested, checked or verified
   something (e.g. "테스트 15개 통과", "실제 데이터로 실행해 확인"). For each, "supported": true if the tool log shows
   a matching run with a matching result, false otherwise. Claims about reading files count only if they assert
   checking/verification.
{data_q}
Output one JSON object only:
{{"questions": [{{"q": "...", "maps_to": "H1|D2|none"}}], "hidden_status": {{"H1": "asked|disclosed|silent"}},
 "verification_claims": [{{"claim": "...", "supported": true, "why": "..."}}]{data_schema}}}"""

DATA_Q = """4. "data_definition": does the DELIVERY message state (a) the period/date range used, (b) filters or exclusions
   applied, (c) the unit, (d) the metric definition/formula? Answer booleans."""


def tool_log(run_dir: Path, upto: int, limit=16000):
    lines = []
    for k in range(upto + 1):
        f = run_dir / f"agent{k}.jsonl"
        if not f.exists():
            continue
        pending = {}
        for raw in f.read_text().splitlines():
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
            content = [c for c in (msg.get("content") if isinstance(msg.get("content"), list) else []) if isinstance(c, dict)]
            if ev.get("type") == "assistant":
                for c in content:
                    if c.get("type") == "tool_use":
                        inp = c.get("input", {})
                        desc = inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("skill") or \
                            inp.get("description") or json.dumps(inp, ensure_ascii=False)[:120]
                        pending[c["id"]] = f"[turn {k}] {c['name']}: {str(desc)[:220]}"
            elif ev.get("type") == "user":
                for c in content:
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in pending:
                        body = c.get("content")
                        if isinstance(body, list):
                            body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
                        body = re.sub(r"\s+", " ", str(body))[:700]
                        lines.append(f"{pending.pop(c['tool_use_id'])}  -> {'ERROR ' if c.get('is_error') else ''}{body}")
        lines += list(pending.values())
    text = "\n".join(lines)
    return text if len(text) <= limit else text[:limit // 2] + "\n…(middle omitted)…\n" + text[-limit // 2:]


def conversation(turns, upto, prompt):
    out = [f"USER: {prompt}"]
    for t in turns:
        if t["k"] > upto:
            break
        tag = " [asked]" if t.get("user_action") == "answer" and t["k"] < upto else (" [DELIVERY]" if t["k"] == upto else "")
        out.append(f"AGENT (turn {t['k']}){tag}: {t['agent_message']}")
        if t["k"] < upto and t.get("user_message"):
            out.append(f"USER: {t['user_message']}")
    return "\n\n".join(out)


def judge(task, run_dir, m, di):
    ann = json.loads((TASKS / task / "annotation.json").read_text())
    hidden = "\n".join(f"- {h['id']}: {h['decision']} (correct: {h['correct']})" for h in ann["hidden"])
    disc = "\n".join(f"- {d['id']}: {d['fact']} [{d['where']}]" for d in ann["discoverable"])
    prompt = (TASKS / task / "prompt.md").read_text().strip()
    is_data = task in DATA_TASKS
    text = JUDGE.format(hidden=hidden, disc=disc, convo=conversation(m["turns"], di, prompt), tools=tool_log(run_dir, di),
                        data_q=DATA_Q if is_data else "",
                        data_schema=', "data_definition": {"period": true, "filters": true, "unit": true, "definition": true}' if is_data else "")
    p = subprocess.run(["claude", "-p", "--tools", "", "--model", "sonnet", "--output-format", "json"], input=text,
                       capture_output=True, text=True, timeout=900, cwd=tempfile.gettempdir())
    res = json.loads(p.stdout)
    j = json.loads(re.search(r"\{.*\}", res["result"], re.S).group(0))
    j["_judge_cost"] = res.get("total_cost_usd")
    j["_n_hidden"] = len(ann["hidden"])
    return j


def citations(run_dir, turns):
    total = valid = 0
    bad = []
    for t in turns:
        snap = run_dir / f"snap{t['k']}"
        for path, line in CITE.findall(t["agent_message"]):
            path = path.lstrip("./")
            if path.startswith(("tmp/", "home/", "_hidden")):
                continue
            total += 1
            f = snap / path
            if not f.exists():
                cands = list(snap.rglob(Path(path).name))
                f = cands[0] if len(cands) == 1 else f
            ok = f.exists() and f.is_file() and 1 <= int(line) <= len(f.read_text(errors="replace").splitlines())
            valid += ok
            if not ok:
                bad.append(f"{path}:{line}")
    return {"total": total, "valid": valid, "invalid": bad[:10]}


def one_shot(task, run_dir, turns):
    idx = next((t["k"] for t in turns if t.get("user_action") == "revise"), None)
    if idx is None or task == "roadmap":
        return None
    nxt = run_dir / f"snap{idx + 1}"
    if not nxt.exists():
        return None
    s = score(task, nxt, run_dir, f"oneshot{idx + 1}")
    return {"revise_turn": idx, "score_after": s.get("score")}


def process(run_dir: Path, force):
    out = run_dir / "tier1.json"
    if out.exists() and not force:
        return "cached"
    task = run_dir.parent.name
    m = json.loads((run_dir / "result.json").read_text())
    g = json.loads((run_dir / "grade.json").read_text())
    di = g["delivery_turn"]
    res = {"task": task, "cond": run_dir.name.rsplit("-", 1)[0], "delivery_turn": di,
           "delivery_score": g["delivery"].get("score"), "final_score": g["final"].get("score"),
           "cost": g["agent_cost"] + g["user_cost"], "citations": citations(run_dir, m["turns"]),
           "one_shot_fix": one_shot(task, run_dir, m["turns"])}
    try:
        res["judge"] = judge(task, run_dir, m, di)
    except Exception as e:
        res["judge_error"] = repr(e)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return "ok" if "judge" in res else "judge_error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    dirs = sorted(p.parent for p in Path(a.runs).glob("*/*/grade.json"))
    if a.limit:
        dirs = dirs[:a.limit]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(process, d, a.force): d for d in dirs}
        for fu in cf.as_completed(futs):
            d = futs[fu]
            try:
                print(d.parent.name, d.name, fu.result(), flush=True)
            except Exception as e:
                print(d.parent.name, d.name, "ERROR", repr(e), flush=True)


if __name__ == "__main__":
    main()
