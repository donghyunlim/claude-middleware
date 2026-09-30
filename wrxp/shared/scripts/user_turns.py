#!/usr/bin/env python3
"""Print the user's own messages from a Claude Code or Codex session log.

Compaction replaces early turns with a summary, so a handoff written late in a
session cannot trust its own memory of the first request. This reads the raw
session log and prints each genuine user message with its position and time,
including messages queued while the agent was working and answers given through
question tools (AskUserQuestion, request_user_input). Injected context (system
reminders, task notifications, tool results, slash-command and shell echoes,
AGENTS.md, skill and automation blocks) is dropped.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CODEX_SESSIONS = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"

TAG_BLOCK = re.compile(
    r"<(system-reminder|task-notification|local-command-caveat|"
    r"local-command-stdout|local-command-stderr|command-message|"
    r"bash-stdout|bash-stderr)>.*?</\1>",
    re.DOTALL,
)
COMMAND_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
BASH_INPUT = re.compile(r"<bash-input>(.*?)</bash-input>", re.DOTALL)
CODEX_INJECTED_PREFIXES = (
    "# AGENTS.md instructions",
    "<environment_context",
    "<user_instructions",
    "<permissions instructions",
    "<turn_aborted",
    "<skill>",
    "<heartbeat",
    "<in-app-browser-context",
    "<codex_delegation",
    "<recommended_plugins",
)
CODEX_USER_SOURCES = ("cli", "vscode")
DISMISSED = "doesn't want to proceed"
CODEX_UNAVAILABLE = "request_user_input is unavailable"
QUESTION_TOOLS = ("AskUserQuestion", "request_user_input")
ANSWER_HEADER = "[question tool answer]"


def clean(text: str) -> str:
    """Strip injected tags; keep a slash command only when it carries user text."""
    command = COMMAND_NAME.search(text)
    text = TAG_BLOCK.sub("", COMMAND_NAME.sub("", text))
    text = COMMAND_ARGS.sub(lambda m: m.group(1), text)
    text = BASH_INPUT.sub(lambda m: f"! {m.group(1)}", text).strip()
    if command and text:
        return f"{command.group(1).strip()} {text}"
    return text


def block_text(content) -> tuple[str, int]:
    """Join text blocks and count images in a message content value."""
    if isinstance(content, str):
        return content, 0
    blocks = content or []
    text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    return text, sum(1 for b in blocks if b.get("type") == "image")


def with_images(text: str, images: int) -> str:
    return f"{text}\n[{images} image(s) attached]".strip() if images else text


def format_answers(result: dict) -> str:
    """Render a question tool's structured result as question/answer pairs."""
    answers = result.get("answers") or {}
    notes = result.get("annotations") or {}
    lines = [ANSWER_HEADER]
    for question in result.get("questions") or []:
        asked = question.get("question", "")
        answer = str(answers.get(asked, "(no answer)"))
        lines.append(f"Q: {asked}\nA: {answer}")
        chosen = {part.strip() for part in answer.split(", ")} | {answer.strip()}
        for option in question.get("options") or []:
            if option.get("label") in chosen:
                lines.append(f"   ({option['label']}: {option.get('description', '')})")
        note = (notes.get(asked) or {}).get("notes")
        if note:
            lines.append(f"   note: {note}")
    return "\n".join(lines)


def from_human(record_or_attachment: dict) -> bool:
    """Records without an origin predate the field; anything else must be human."""
    origin = record_or_attachment.get("origin") or {}
    return origin.get("kind") in (None, "human")


def claude_turns(path: Path):
    question_calls = set()
    for line in path.open(encoding="utf-8"):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = record.get("timestamp", "")
        kind = record.get("type")
        if kind == "assistant":
            for block in record.get("message", {}).get("content") or []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") in QUESTION_TOOLS):
                    question_calls.add(block.get("id"))
            yield timestamp, "", "assistant"
            continue
        if kind == "attachment":
            queued = record.get("attachment") or {}
            if (queued.get("type") == "queued_command"
                    and queued.get("commandMode") == "prompt" and from_human(queued)):
                text, images = block_text(queued.get("prompt"))
                text = with_images(clean(text), images)
                if text:
                    yield queued.get("timestamp", timestamp), text, "user"
            continue
        if kind != "user" or record.get("isMeta") or not from_human(record):
            continue
        if record.get("isCompactSummary"):
            yield timestamp, "[compact summary omitted]", "marker"
            continue
        content = record.get("message", {}).get("content")
        if not isinstance(content, str):
            results = [b for b in content or [] if b.get("type") == "tool_result"]
            if results:
                if any(b.get("tool_use_id") in question_calls for b in results):
                    structured = record.get("toolUseResult")
                    if isinstance(structured, dict) and structured.get("questions"):
                        yield timestamp, format_answers(structured), "answer"
                    else:
                        raw = "\n".join(str(b.get("content", "")) for b in results)
                        if DISMISSED in raw:
                            raw = "[question dismissed without an answer]"
                        yield timestamp, f"{ANSWER_HEADER}\n{raw}", "answer"
                continue
        text, images = block_text(content)
        text = with_images(clean(text), images)
        if text:
            yield timestamp, text, "user"


def codex_turns(path: Path):
    question_calls = set()
    for line in path.open(encoding="utf-8"):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = record.get("payload") or {}
        timestamp = record.get("timestamp", "")
        if record.get("type") == "compacted":
            yield timestamp, "[compaction point]", "marker"
            continue
        if record.get("type") != "response_item":
            continue
        kind = payload.get("type")
        if kind == "function_call" and payload.get("name") in QUESTION_TOOLS:
            question_calls.add(payload.get("call_id"))
            continue
        if kind == "function_call_output":
            output = str(payload.get("output", ""))
            if payload.get("call_id") in question_calls and not output.startswith(CODEX_UNAVAILABLE):
                yield timestamp, f"{ANSWER_HEADER}\n{output}", "answer"
            continue
        if kind != "message":
            continue
        if payload.get("role") == "assistant":
            yield timestamp, "", "assistant"
            continue
        if payload.get("role") != "user":
            continue
        parts = [
            c.get("text", "").strip() for c in payload.get("content", [])
            if c.get("type") in ("input_text", "text")
        ]
        text = clean("\n".join(
            part for part in parts
            if part and not part.startswith(CODEX_INJECTED_PREFIXES)
        ))
        if text:
            yield timestamp, text, "user"


def is_codex_log(path: Path) -> bool:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                return "payload" in json.loads(line)
            except json.JSONDecodeError:
                continue
    return False


def find_claude_log(session_id: str) -> Path | None:
    matches = sorted(CLAUDE_PROJECTS.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def find_codex_log(session_id: str) -> Path | None:
    matches = sorted(CODEX_SESSIONS.glob(f"**/rollout-*{session_id}.jsonl"))
    return matches[-1] if matches else None


def latest_codex_log_for(cwd: str) -> Path | None:
    """Newest interactive (cli or vscode) Codex rollout started in cwd."""
    logs = sorted(CODEX_SESSIONS.glob("**/rollout-*.jsonl"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    for log in logs[:200]:
        with log.open(encoding="utf-8") as handle:
            try:
                meta = json.loads(handle.readline()).get("payload") or {}
            except json.JSONDecodeError:
                continue
        if meta.get("cwd") == cwd and meta.get("source") in CODEX_USER_SOURCES:
            return log
    return None


def resolve(args) -> Path:
    if args.log:
        return Path(args.log).expanduser()
    if args.session_id:
        found = find_claude_log(args.session_id) or find_codex_log(args.session_id)
        if found:
            return found
        sys.exit(f"no session log found for {args.session_id}")
    # A Codex run started from Claude Code (or the reverse) inherits both ids;
    # the session doing the work is the one whose log was written last.
    candidates = [
        log for log in (
            find_claude_log(os.environ.get("CLAUDE_CODE_SESSION_ID", "") or "-"),
            find_codex_log(os.environ.get("CODEX_THREAD_ID", "") or "-"),
        ) if log
    ]
    if candidates:
        return max(candidates, key=lambda log: log.stat().st_mtime)
    found = latest_codex_log_for(os.getcwd())
    if found:
        print(f"# warning: no session id; using the newest Codex session in {os.getcwd()}",
              file=sys.stderr)
        return found
    sys.exit("pass --log PATH or --session-id ID (no session id in the environment)")


def numbered(turns):
    """Yield (number, timestamp, text, kind); kind is turn, marker, or resent.

    Only back-to-back resends with no reply between them fold into the previous
    number, so two identical answers to two questions stay separate turns.
    """
    number, previous = 0, None
    for timestamp, text, kind in turns:
        if kind == "assistant":
            previous = None
            continue
        if kind == "marker":
            previous = None
            yield 0, timestamp, text, "marker"
            continue
        if text == previous:
            yield number, timestamp, "", "resent"
            continue
        previous = text
        number += 1
        yield number, timestamp, text, "turn"


def render(turns, max_chars: int):
    """Number messages; fold only back-to-back resends with no reply between them."""
    for number, timestamp, text, kind in numbered(turns):
        if kind == "marker":
            yield f"\n--- {text} {timestamp}"
            continue
        if kind == "resent":
            yield f"(U{number} resent {timestamp})"
            continue
        if max_chars and len(text) > max_chars:
            text = f"{text[:max_chars]}\n[... {len(text) - max_chars} more chars]"
        yield f"\n## U{number} {timestamp}\n{text}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", help="session log path (.jsonl)")
    parser.add_argument("--session-id", help="Claude Code or Codex session id")
    parser.add_argument(
        "--max-chars", type=int, default=1500,
        help="truncate each message beyond this many characters (0 = no limit)",
    )
    args = parser.parse_args()

    path = resolve(args)
    turns = codex_turns if is_codex_log(path) else claude_turns
    print(f"# source: {path}")
    printed = 0
    for line in render(turns(path), args.max_chars):
        printed += line.startswith("\n## U")
        print(line)
    if not printed:
        print("# warning: no user messages found; the log format may have changed",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
