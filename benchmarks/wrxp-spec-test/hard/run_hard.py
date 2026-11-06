#!/usr/bin/env python3
"""Hard suite: multi-turn runs with a simulated user who knows the hidden intent.

Usage: python3 hard/run_hard.py --out RUNS [--tasks a,b] [--conds ...] [--reps 3] [--parallel 6] [--max-user-turns 3]

Each run:
  turn 0  the agent gets the task prompt (with the condition's /wrxp prefix)
  turn k  a simulated user (Sonnet, no tools) reads the agent's last message and the
          hidden intent in tasks/<t>/intent.md, then answers a question, asks for a
          fix, or accepts. The agent continues the same session with --resume.
The work dir is snapshotted after every agent turn so first-try and final work can
both be graded. The simulated user never sees files, only the agent's messages.
"""
import argparse
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import conditions as C  # noqa: E402
from run import ALLOWED  # noqa: E402

TASKS = HERE / "tasks"
CONDS = "base,global,global_ha,global_haq,global_haqq"

SIM_PROMPT = """너는 아래 작업을 AI 에이전트에게 맡긴 사용자다. '너만 아는 의도'를 기준으로 행동한다.

규칙:
1. 에이전트가 질문하면 의도에 근거해 짧고 정확하게 답한다. 의도에 없는 것을 물으면 "그건 알아서 판단해 주세요"라고 답한다.
2. 묻지 않은 세부 사항을 먼저 알려 주지 않는다.
3. 에이전트가 완료를 보고하면, 보고에 적힌 내용만 보고 판단한다(너는 파일을 볼 수 없다). 보고에 드러난 내용이 의도와 어긋나면, 어긋난 점만 고쳐 달라고 요청한다. 보고에 드러나지 않은 것은 지적하지 않는다.
4. 질문이 없고 보고에서 어긋난 점도 보이지 않으면 수락한다.
5. 승인을 구하면(예: 진행해도 될까요, 함께 고칠까요) 의도에 맞으면 승인하고, 맞지 않으면 이유와 함께 거절한다.

## 원래 요청
{prompt}

## 너만 아는 의도
{intent}

## 지금까지의 대화
{history}

JSON 한 개만 출력하라: {{"action": "answer" | "revise" | "accept", "message": "에이전트에게 보낼 말(accept면 빈 문자열)"}}"""


def agent_turn(cond, out, work, prompt, resume, log):
    t0 = time.time()
    with open(log, "w") as f:
        try:
            p = subprocess.run(C.command(cond, ALLOWED, resume), input=prompt, cwd=work, stdout=f,
                               stderr=subprocess.PIPE, text=True, timeout=1500, env=C.env_for(out, cond))
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = -9
    final = None
    for line in Path(log).read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
    return rc, final or {}, time.time() - t0


def sim_user(prompt, intent, history):
    text = SIM_PROMPT.format(prompt=prompt, intent=intent, history=history)
    p = subprocess.run(["claude", "-p", "--tools", "", "--model", "sonnet", "--output-format", "json"], input=text,
                       capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
    d = json.loads(p.stdout)
    m = re.search(r"\{.*\}", d["result"], re.S)
    reply = json.loads(m.group(0)) if m else {"action": "accept", "message": ""}
    return reply, d.get("total_cost_usd") or 0.0


def run_one(task, cond, rep, out: Path, max_user_turns):
    run_dir = out / task / f"{cond}-{rep}"
    if (run_dir / "result.json").exists():
        return "cached"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    work = run_dir / "work"
    src = TASKS / task
    shutil.copytree(src / "fixture", work)
    prompt = (src / "prompt.md").read_text().strip()
    intent = (src / "intent.md").read_text().strip()
    turns, history, sid = [], [f"사용자: {prompt}"], None
    msg = C.prompt_for(cond, prompt)
    t_start = time.time()
    for k in range(max_user_turns + 1):
        rc, final, sec = agent_turn(cond, out, work, msg, sid, run_dir / f"agent{k}.jsonl")
        sid = final.get("session_id") or sid
        reply_text = final.get("result") or ""
        shutil.copytree(work, run_dir / f"snap{k}")
        turn = {"k": k, "rc": rc, "agent_cost": final.get("total_cost_usd") or 0.0, "agent_sec": sec,
                "num_turns": final.get("num_turns"), "agent_message": reply_text}
        history.append(f"에이전트: {reply_text}")
        if k == max_user_turns or rc != 0 or not sid:
            turns.append(turn)
            break
        reply, ucost = sim_user(prompt, intent, "\n\n".join(history))
        turn.update({"user_action": reply.get("action"), "user_message": reply.get("message", ""), "user_cost": ucost})
        turns.append(turn)
        if reply.get("action") == "accept" or not reply.get("message"):
            break
        history.append(f"사용자: {reply['message']}")
        msg = reply["message"]
    meta = {"task": task, "cond": cond, "rep": rep, "turns": turns, "wall_sec": time.time() - t_start,
            "user_turns": sum(1 for t in turns if t.get("user_action") in ("answer", "revise")),
            "accepted": any(t.get("user_action") == "accept" for t in turns)}
    (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return f"turns={len(turns)} accepted={meta['accepted']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=",".join(sorted(p.name for p in TASKS.iterdir() if p.is_dir())))
    ap.add_argument("--conds", default=CONDS)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--max-user-turns", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    for c in a.conds.split(","):
        C.config_dir(out, c)
    jobs = [(t, c, r) for r in range(1, a.reps + 1) for t in a.tasks.split(",") for c in a.conds.split(",")]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, t, c, r, out, a.max_user_turns): (t, c, r) for t, c, r in jobs}
        for fu in cf.as_completed(futs):
            t, c, r = futs[fu]
            try:
                print(t, c, r, fu.result(), flush=True)
            except Exception as e:
                print(t, c, r, "ERROR", repr(e), flush=True)


if __name__ == "__main__":
    main()
