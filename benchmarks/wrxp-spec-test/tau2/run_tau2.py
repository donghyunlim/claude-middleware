#!/usr/bin/env python3
"""Run tau2-bench (retail, airline) tasks through Claude Code under the benchmark conditions.

Usage: python3 tau2/run_tau2.py --out RUNS [--domains retail,airline] [--n 6] [--trials 2]
                                [--conds ...] [--parallel 6] [--max-turns 14]

- Agent: Claude Code (`claude -p`, resumed each turn) with the domain tools served over MCP
  (tau2_mcp.py) and tau2's own agent instruction + domain policy appended to the system prompt.
  The condition's prefix (/wrxp:haq, /pstack:poteto-mode, ...) goes on the first customer message.
- User: tau2's own user-simulator system prompt and scenario, generated with Sonnet through
  `claude -p --tools ""` (tau2's default user model is not reachable here).
- Score: tau2's EnvironmentEvaluator (DB-state reward) on the recorded trajectory.
Tasks: a fixed-seed sample of the domain's `test` split.
"""
import argparse
import concurrent.futures as cf
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import conditions as C  # noqa: E402
from run import ALLOWED  # noqa: E402

GREETING = "Hi! How can I help you today?"
STOP_TOKENS = ("###STOP###", "###TRANSFER###", "###OUT-OF-SCOPE###")
EXTRA_SYS = ("\n\nYou are talking with a customer through this chat. Each user message is the customer's reply. "
             "Answer the customer in plain text. Use the tau2 MCP tools (mcp__tau2__*) to look up and change records.")


def tasks_for(domain, n, seed):
    from tau2.registry import registry
    split = json.load(open(next(Path(p) for p in [
        Path(__import__("tau2").__file__).resolve().parents[2] / "data/tau2/domains" / domain / "split_tasks.json"])))
    ids = sorted(split["test"], key=str)
    rng = random.Random(f"{seed}-{domain}")
    pick = rng.sample(ids, n)
    tasks = {str(t.id): t for t in registry.get_tasks_loader(domain)()}
    return [tasks[str(i)] for i in pick]


def system_prompts(domain, task):
    from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
    from tau2.data_model.persona import PersonaConfig
    from tau2.registry import registry
    from tau2.user import guidelines as G
    from tau2.user.user_simulator import build_user_system_prompt
    env = registry.get_env_constructor(domain)()
    agent = SYSTEM_PROMPT.format(domain_policy=env.get_policy(), agent_instruction=AGENT_INSTRUCTION) + EXTRA_SYS
    pc = PersonaConfig()
    user = build_user_system_prompt(str(task.user_scenario), persona_config=pc, mode="text",
                                    guidelines=G.simulation_guidelines(pc, mode="text", use_tools=False))
    return agent, user


def user_turn(user_sys, convo):
    lines = "\n\n".join(f"{'Agent' if r == 'assistant' else 'You (customer)'}: {c}" for r, c in convo)
    prompt = (f"{user_sys}\n\n## Conversation so far\n{lines}\n\nWrite only your next message as the customer "
              "(or the stop/transfer/out-of-scope token when the rules say so). No preamble.")
    p = subprocess.run(["claude", "-p", "--tools", "", "--model", "sonnet", "--output-format", "json"], input=prompt,
                       capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
    d = json.loads(p.stdout)
    return d["result"].strip(), d.get("total_cost_usd") or 0.0


def agent_turn(cond, out, work, msg, sid, sys_prompt, mcp_cfg, log):
    cmd = C.command(cond, ALLOWED + ",mcp__tau2", sid) + ["--mcp-config", str(mcp_cfg), "--strict-mcp-config",
                                                          "--append-system-prompt", sys_prompt]
    with open(log, "w") as f:
        try:
            p = subprocess.run(cmd, input=msg, cwd=work, stdout=f, stderr=subprocess.PIPE, text=True, timeout=900,
                               env=C.env_for(out, cond))
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = -9
    final = {}
    for line in Path(log).read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
    return rc, final


def run_one(domain, task, cond, trial, out: Path, max_turns):
    import tau2_eval
    run_dir = out / domain / str(task.id) / f"{cond}-{trial}"
    if (run_dir / "result.json").exists():
        return "cached"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    work = run_dir / "work"
    work.mkdir(parents=True)
    tool_log = run_dir / "tools.jsonl"
    mcp_cfg = run_dir / "mcp.json"
    mcp_cfg.write_text(json.dumps({"mcpServers": {"tau2": {
        "command": sys.executable, "args": [str(HERE / "tau2_mcp.py")],
        "env": {"TAU2_DOMAIN": domain, "TAU2_LOG": str(tool_log)}}}}))
    agent_sys, user_sys = system_prompts(domain, task)
    convo, events, sid, agent_cost, user_cost = [("assistant", GREETING)], [], None, 0.0, 0.0
    events.append({"role": "assistant", "content": GREETING})
    stopped, reason, t0 = False, "max_turns", time.time()
    n_seen = 0
    for k in range(max_turns):
        umsg, uc = user_turn(user_sys, convo)
        user_cost += uc
        if any(s in umsg for s in STOP_TOKENS):
            stopped, reason = True, next(s for s in STOP_TOKENS if s in umsg)
            events.append({"role": "user", "content": umsg})
            break
        convo.append(("user", umsg))
        events.append({"role": "user", "content": umsg})
        msg = C.prompt_for(cond, umsg) if k == 0 else umsg
        rc, final = agent_turn(cond, out, work, msg, sid, agent_sys, mcp_cfg, run_dir / f"agent{k}.jsonl")
        sid = final.get("session_id") or sid
        agent_cost += final.get("total_cost_usd") or 0.0
        calls = [json.loads(l) for l in tool_log.read_text().splitlines()] if tool_log.exists() else []
        for c in calls[n_seen:]:
            events.append({"role": "tool_call", **c})
        n_seen = len(calls)
        reply = final.get("result") or ""
        convo.append(("assistant", reply))
        events.append({"role": "assistant", "content": reply})
        if rc != 0 or not sid:
            reason = f"agent_rc_{rc}"
            break
    try:
        reward = tau2_eval.score(domain, task.id, events, stopped)
    except Exception as e:
        reward = {"db": 0.0, "error": repr(e)}
    meta = {"domain": domain, "task_id": str(task.id), "cond": cond, "trial": trial, "reward": reward,
            "stopped": stopped, "termination": reason, "agent_turns": sum(1 for e in events if e["role"] == "assistant") - 1,
            "tool_calls": n_seen, "agent_cost": agent_cost, "user_cost": user_cost, "wall_sec": time.time() - t0,
            "events": events}
    (run_dir / "result.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return f"db={reward.get('db')} turns={meta['agent_turns']} {reason}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--domains", default="retail,airline")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--trials", type=int, default=2)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--conds", default="base,global,global_haq,global_haqq,pstack,pstack_poteto")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--max-turns", type=int, default=14)
    ap.add_argument("--only-task", default="")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    for c in a.conds.split(","):
        C.config_dir(out, c)
    jobs = []
    for d in a.domains.split(","):
        for t in tasks_for(d, a.n, a.seed):
            if a.only_task and str(t.id) != a.only_task:
                continue
            for tr in range(1, a.trials + 1):
                for c in a.conds.split(","):
                    jobs.append((d, t, c, tr))
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_one, d, t, c, tr, out, a.max_turns): (d, t.id, c, tr) for d, t, c, tr in jobs}
        for fu in cf.as_completed(futs):
            try:
                print(*futs[fu], fu.result(), flush=True)
            except Exception as e:
                print(*futs[fu], "ERROR", repr(e), flush=True)


if __name__ == "__main__":
    main()
