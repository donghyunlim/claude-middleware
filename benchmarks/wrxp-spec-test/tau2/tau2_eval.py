"""Score a recorded conversation with tau2-bench's own environment evaluator (DB reward)."""
import datetime as dt
import json
import uuid

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
from tau2.data_model.simulation import SimulationRun, TerminationReason
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.data_model.semantic_communication import CommunicateScoring, CommunicateScorer
from tau2.registry import registry


def load_task(domain, task_id):
    return next(t for t in registry.get_tasks_loader(domain)() if str(t.id) == str(task_id))


def build_messages(events):
    """events: list of {"role": "user"|"assistant", "content": str} or {"role": "tool_call", name, arguments, output, error}"""
    msgs, turn = [], 0
    for e in events:
        if e["role"] == "user":
            msgs.append(UserMessage(role="user", content=e["content"], turn_idx=turn)); turn += 1
        elif e["role"] == "assistant":
            msgs.append(AssistantMessage(role="assistant", content=e["content"] or "(no reply)", turn_idx=turn)); turn += 1
        elif e["role"] == "tool_call":
            cid = e.get("id") or uuid.uuid4().hex[:12]
            msgs.append(AssistantMessage(role="assistant", content=None, turn_idx=turn,
                                         tool_calls=[ToolCall(id=cid, name=e["name"], arguments=e["arguments"])]))
            turn += 1
            msgs.append(ToolMessage(id=cid, role="tool", content=e["output"], error=e.get("error", False), turn_idx=turn))
            turn += 1
    return msgs


def score(domain, task_id, events, stopped=True):
    task = load_task(domain, task_id)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    sim = SimulationRun(id=uuid.uuid4().hex, task_id=str(task_id), timestamp=now, start_time=now, end_time=now,
                        duration=0.0,
                        termination_reason=TerminationReason.USER_STOP if stopped else TerminationReason.MAX_STEPS,
                        messages=build_messages(events))
    out = {}
    for name, et in [("db", EvaluationType.ENV)]:
        r = evaluate_simulation(sim, task, et, solo_mode=False, domain=domain, strict_replay=False,
                                communicate_scoring=CommunicateScoring(scorer=CommunicateScorer.SUBSTRING))
        out[name] = r.reward
    return out
