#!/usr/bin/env python3
"""Ask a fresh-context top model whether the work still follows the user's words.

The packet is assembled here rather than by the main agent: every user message
from the session log, prior handoff quotes, and machine repo state are attached
verbatim, and the main agent contributes only its labelled claims (ai-state.md
and rebuttals). The reviewer runs read-only and its real model is recorded.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
PROMPT = SKILL_DIR / "references" / "reviewer-prompt.md"
_SHARED = SKILL_DIR.parents[1] / "shared" / "scripts" / "user_turns.py"
_spec = importlib.util.spec_from_file_location("wrxp_shared_user_turns", _SHARED)
ut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ut)

HEAD, TAIL, CAP_BYTES, KEEP_RECENT = 1500, 500, 150_000, 3
EXIT_USAGE, EXIT_NO_SOURCE, EXIT_NO_REVIEWER = 2, 3, 4
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z0-9]+(?:_[A-Z0-9]+)*_(?:TOKEN|KEY|SECRET|PASSWORD))"
    r"(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
)


def redact(text: str) -> str:
    """Hide values assigned to secret-looking key names; never match value shapes."""
    return SECRET_ASSIGNMENT.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)


def clip(text: str, where: str, head: int = HEAD, tail: int = TAIL) -> tuple[str, bool]:
    if len(text) <= head + tail:
        return text, False
    cut = len(text) - head - tail
    return f"{text[:head]}\n[... {cut}자 생략. 전문: {where}]\n{text[-tail:]}", True


def load_turns(log: Path, until_turn: int | None = None) -> list[tuple[int, str, str]]:
    turns = ut.codex_turns if ut.is_codex_log(log) else ut.claude_turns
    kept = []
    for number, timestamp, text, kind in ut.numbered(turns(log)):
        if kind != "turn":
            continue
        if until_turn is not None and number >= until_turn:
            break
        kept.append((number, timestamp, text))
    return kept


def _block(number: int, timestamp: str, body: str) -> str:
    return f"\n## [원문] U{number} {timestamp}\n{body}"


def render_turns(turns, source: Path, session: str,
                 cap_bytes: int = CAP_BYTES) -> tuple[str, list[str]]:
    """Every turn in order; past the cap, middle turns fold to their first line.

    The first turn and the most recent KEEP_RECENT turns always stay intact.
    """
    blocks, shortened = [], []
    for number, timestamp, text in turns:
        body, clipped = clip(redact(text), f"{source} U{number}")
        if clipped:
            shortened.append(f"U{number}")
        blocks.append([number, timestamp, body, text])
    sizes = [len(_block(n, ts, b).encode("utf-8")) for n, ts, b, _ in blocks]
    total = sum(sizes)
    for i in range(1, max(1, len(blocks) - KEEP_RECENT)):
        if total <= cap_bytes:
            break
        number, timestamp, _, raw = blocks[i]
        lines = redact(raw).strip().splitlines()
        first = lines[0][:200] if lines else ""
        blocks[i][2] = f"{first}\n[... 첫 줄만 남김. 전문: {source} U{number}]"
        new_size = len(_block(number, timestamp, blocks[i][2]).encode("utf-8"))
        total += new_size - sizes[i]
        sizes[i] = new_size
        if f"U{number}" not in shortened:
            shortened.append(f"U{number}")
    header = f"# [원문] 사용자 발화 · 세션 {session} · 로그 {source}\n"
    if shortened:
        header += f"줄인 발화: {', '.join(shortened)}\n"
    return header + "".join(_block(n, ts, b) for n, ts, b, _ in blocks), shortened


HANDOFF_PATH = re.compile(r"(/[^\s`'\"<>()]*handoffs/[^\s`'\"<>()]+\.md)")
SESSION_IN_HEADER = re.compile(r"세션\s+([0-9a-f][0-9a-f-]{7,})")
PREVIOUS_IN_HEADER = re.compile(r"이전 핸드오프:\s*([^\s·]+)")


def section(text: str, number: int) -> str:
    match = re.search(rf"(?ms)^## {number}\.[^\n]*\n(.*?)(?=^## \d+\.|\Z)", text)
    return match.group(1).strip() if match else ""


def handoff_chain(paths: list[Path], limit: int = 10) -> list[tuple[Path, str | None]]:
    """Newest first: each handoff, then the one its header names as previous."""
    chain, seen, queue = [], set(), list(paths)
    while queue and len(chain) < limit:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            chain.append((path, None))
            continue
        text = path.read_text(encoding="utf-8")
        chain.append((path, text))
        previous = PREVIOUS_IN_HEADER.search(text)
        if previous and previous.group(1) not in ("없음", "미확인"):
            queue.append(Path(previous.group(1)).expanduser())
    return chain


def render_handoffs(chain) -> tuple[str, list[str]]:
    parts, sessions = [], []
    for path, text in chain:
        if text is None:
            parts.append(f"\n## 이전 핸드오프 {path}: 미확인 (파일을 읽을 수 없음)")
            continue
        found = SESSION_IN_HEADER.search(text)
        if found:
            sessions.append(found.group(1))
        parts.append(f"\n## [원문 인용] {path} §1\n{redact(section(text, 1))}")
        parts.append(f"\n## [AI 작성] {path} §2\n{redact(section(text, 2))}")
    if not parts:
        return "", []
    ends = []
    for sid in (sessions[-1:] + sessions[:1]):
        if sid not in ends:
            ends.append(sid)
    return "# 이전 핸드오프\n" + "".join(parts), ends


def render_prior_sessions(session_ids: list[str], cap_bytes: int) -> str:
    parts = []
    for sid in session_ids:
        log = ut.find_claude_log(sid) or ut.find_codex_log(sid)
        if not log:
            parts.append(f"\n# 이전 세션 {sid}: 미확인 (로그 없음)")
            continue
        text, _ = render_turns(load_turns(log), log, sid, cap_bytes)
        parts.append("\n" + text)
    return "".join(parts)


def repo_state(project: Path) -> str:
    out = ["# [기계 출력] 저장소 상태"]
    for cmd in (["git", "status", "--short", "--branch"],
                ["git", "log", "--oneline", "-15"],
                ["git", "diff", "--stat"]):
        try:
            result = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
            ok = result.returncode == 0
            body = result.stdout.strip() if ok else f"(실행 실패: {result.stderr.strip()[:200]})"
        except OSError as exc:
            body = f"(실행 실패: {exc})"
        out.append(f"\n$ {' '.join(cmd)}\n{body}")
    return "\n".join(out)


FAMILY_RANK = {"codex": ("astra", "sol"), "claude": ("opus", "sonnet")}
CODEX_SLUG = re.compile(r"^gpt-(\d+(?:\.\d+)?)-(astra|sol)$")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def codex_models(cache: Path) -> list[str]:
    """Newest generation of each ranked tier, best tier first; never guess slugs."""
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    models = data.get("models", []) if isinstance(data, dict) else data
    best = {}
    for model in models:
        match = CODEX_SLUG.match(str(model.get("slug", "")))
        if not match:
            continue
        version, tier = float(match.group(1)), match.group(2)
        if tier not in best or version > best[tier][0]:
            best[tier] = (version, match.group(0))
    return [best[tier][1] for tier in FAMILY_RANK["codex"] if tier in best]


def candidates(main_runtime: str, available: dict[str, bool],
               cache: Path) -> list[tuple[str, str]]:
    family = {
        "codex": codex_models(cache) if available.get("codex") else [],
        "claude": list(FAMILY_RANK["claude"]) if available.get("claude") else [],
    }
    other = "claude" if main_runtime == "codex" else "codex"
    return ([(other, model) for model in family[other]]
            + [(main_runtime, model) for model in family[main_runtime][:1]])


def detect_main_runtime(env=None) -> str | None:
    env = os.environ if env is None else env
    claude_id, codex_id = env.get("CLAUDE_CODE_SESSION_ID"), env.get("CODEX_THREAD_ID")
    if claude_id and codex_id:
        logs = {"claude": ut.find_claude_log(claude_id), "codex": ut.find_codex_log(codex_id)}
        logs = {name: log for name, log in logs.items() if log}
        return max(logs, key=lambda name: logs[name].stat().st_mtime) if logs else None
    if claude_id:
        return "claude"
    return "codex" if codex_id else None


def reviewer_command(runtime: str, model: str, project: Path,
                     read_dirs: list[str], response_path: Path) -> list[str]:
    if runtime == "claude":
        return ["claude", "--print", "--model", model, "--effort", "high",
                "--output-format", "json", "--tools", "Read,Grep,Glob",
                "--permission-mode", "dontAsk", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence",
                "--add-dir", *read_dirs]
    return ["codex", "exec", "-C", str(project), "-m", model,
            "-c", 'model_reasoning_effort="high"', "--sandbox", "read-only",
            "--skip-git-repo-check", "--json", "-o", str(response_path), "-"]


def classify(returncode, output: str, text: str) -> str:
    if "limit" in output.lower():
        return "usage_limit"
    if returncode != 0:
        return "exit_code"
    return "empty_response" if not text else "error"


def run_claude(cmd, packet: str, timeout: int) -> tuple[dict, str]:
    proc = subprocess.run(cmd, input=packet, capture_output=True, text=True, timeout=timeout)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {}
    text = str(payload.get("result") or "").strip() if isinstance(payload, dict) else ""
    usage = payload.get("modelUsage") if isinstance(payload, dict) else None
    record = {"exit_code": proc.returncode, "actual_models": list((usage or {}).keys())}
    if proc.returncode != 0 or payload.get("is_error") or not text:
        record["failure"] = classify(proc.returncode, proc.stderr + proc.stdout, text)
    return record, text


def codex_turn_context(thread_id: str | None) -> dict:
    if not thread_id:
        return {}
    logs = sorted((codex_home() / "sessions").glob(f"**/rollout-*{thread_id}.jsonl"))
    if not logs:
        return {}
    for line in logs[-1].open(encoding="utf-8"):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "turn_context":
            payload = record.get("payload") or {}
            return {"model": payload.get("model"), "effort": payload.get("effort"),
                    "sandbox": (payload.get("sandbox_policy") or {}).get("type")}
    return {}


def run_codex(cmd, packet: str, timeout: int, response_path: Path) -> tuple[dict, str]:
    proc = subprocess.run(cmd, input=packet, capture_output=True, text=True, timeout=timeout)
    thread = None
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            thread = event.get("thread_id")
    text = (response_path.read_text(encoding="utf-8").strip()
            if response_path.is_file() else "")
    context = codex_turn_context(thread)
    record = {"exit_code": proc.returncode, "thread_id": thread,
              "actual_models": [context["model"]] if context.get("model") else [],
              "actual_effort": context.get("effort"), "actual_sandbox": context.get("sandbox")}
    if proc.returncode != 0 or not text:
        record["failure"] = classify(proc.returncode, proc.stderr + proc.stdout, text)
    return record, text


def history_block(out: Path, round_no: int, rebuttal: str) -> str:
    """Earlier responses and rebuttals in order; raises FileNotFoundError on a gap."""
    parts = []
    for k in range(1, round_no):
        response = out / f"round-{k}" / "response.md"
        parts.append(f"# {k}회차 리뷰어 응답\n{response.read_text(encoding='utf-8')}")
        if k + 1 < round_no:
            earlier = out / f"round-{k + 1}" / "rebuttal.md"
            parts.append(f"# [AI 주장] {k + 1}회차 메인 반박\n"
                         f"{redact(earlier.read_text(encoding='utf-8'))}")
    if round_no > 1:
        parts.append(f"# [AI 주장] {round_no}회차 메인 반박\n{redact(rebuttal)}")
    return "\n\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state", required=True, help="main agent's ai-state.md")
    parser.add_argument("--out", required=True, help="handoffs/realign/<date>-<slug> folder")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--rebuttal", help="main agent's rebuttal for rounds 2-3")
    parser.add_argument("--session-id")
    parser.add_argument("--log")
    parser.add_argument("--until-turn", type=int, help="keep only turns before this U number")
    parser.add_argument("--no-repo-state", action="store_true")
    parser.add_argument("--handoff", action="append", default=[])
    parser.add_argument("--project", default=os.getcwd())
    parser.add_argument("--main-runtime", choices=("claude", "codex"))
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--cap-bytes", type=int, default=CAP_BYTES)
    args = parser.parse_args(argv)

    out = Path(args.out).expanduser()
    round_dir = out / f"round-{args.round}"
    if not 1 <= args.round <= 3:
        print("회차는 1~3만 허용한다.")
        return EXIT_USAGE
    if round_dir.exists():
        print(f"이미 있는 기록을 덮어쓰지 않는다: {round_dir}")
        return EXIT_USAGE
    if args.round > 1 and not args.rebuttal:
        print("2회차부터는 --rebuttal이 필요하다.")
        return EXIT_USAGE
    main_runtime = args.main_runtime or detect_main_runtime()
    if not main_runtime:
        print("메인 런타임을 알 수 없다. --main-runtime claude|codex를 지정한다.")
        return EXIT_USAGE
    try:
        log = ut.resolve(argparse.Namespace(log=args.log, session_id=args.session_id))
    except SystemExit as exc:
        print(f"원문 미확인: {exc}")
        return EXIT_NO_SOURCE
    if not log.is_file():
        print(f"원문 미확인: 로그 파일 없음 {log}")
        return EXIT_NO_SOURCE
    turns = load_turns(log, args.until_turn)
    if not turns:
        print(f"원문 미확인: 사용자 발화가 없다 {log}")
        return EXIT_NO_SOURCE
    rebuttal = Path(args.rebuttal).read_text(encoding="utf-8") if args.rebuttal else ""
    try:
        history = history_block(out, args.round, rebuttal)
    except FileNotFoundError as exc:
        print(f"이전 회차 기록이 없다: {exc.filename}")
        return EXIT_USAGE

    project = Path(args.project).expanduser().resolve()
    session = log.stem[-36:]
    turns_md, shortened = render_turns(turns, log, session, args.cap_bytes)
    mentioned = [Path(p).expanduser() for p in args.handoff]
    mentioned += [Path(m) for _, _, text in turns for m in HANDOFF_PATH.findall(text)]
    chain = handoff_chain(list(dict.fromkeys(mentioned)))
    handoff_md, prior_sessions = render_handoffs(chain)
    sections = [
        PROMPT.read_text(encoding="utf-8"),
        turns_md,
        handoff_md,
        render_prior_sessions(prior_sessions, args.cap_bytes // 4) if prior_sessions else "",
        "" if args.no_repo_state else repo_state(project),
        f"# [AI 주장] 메인의 현재 상태\n{redact(Path(args.state).read_text(encoding='utf-8'))}",
        history,
    ]
    packet = "\n\n---\n\n".join(part for part in sections if part)

    round_dir.mkdir(parents=True)
    (round_dir / "request.md").write_text(packet, encoding="utf-8")
    if args.rebuttal:
        (round_dir / "rebuttal.md").write_text(rebuttal, encoding="utf-8")
    response_path = round_dir / "response.md"
    available = {name: shutil.which(name) is not None for name in ("claude", "codex")}
    read_dirs = sorted({str(project), str(log.parent)})
    attempts, selected, text = [], None, ""
    for runtime, model in candidates(main_runtime, available, codex_home() / "models_cache.json"):
        cmd = reviewer_command(runtime, model, project, read_dirs, response_path)
        started = time.monotonic()
        try:
            if runtime == "claude":
                record, text = run_claude(cmd, packet, args.timeout)
            else:
                record, text = run_codex(cmd, packet, args.timeout, response_path)
        except subprocess.TimeoutExpired:
            record, text = {"exit_code": None, "actual_models": [], "failure": "timeout"}, ""
        except OSError as exc:
            record, text = {"exit_code": None, "actual_models": [],
                            "failure": f"os_error: {exc}"}, ""
        record.update(runtime=runtime, requested_model=model, effort="high",
                      seconds=round(time.monotonic() - started, 1), command=cmd)
        attempts.append(record)
        if "failure" not in record:
            selected = {"runtime": runtime,
                        "actual_model": (record["actual_models"] or [model])[0]}
            break

    invocation = {
        "round": args.round, "main_runtime": main_runtime,
        "attempts": attempts, "selected": selected,
        "packet": {"bytes": len(packet.encode("utf-8")), "user_turns": len(turns),
                   "truncated_turns": shortened, "source_log": str(log),
                   "prior_handoffs": [str(path) for path, _ in chain]},
    }
    (round_dir / "invocation.json").write_text(
        json.dumps(invocation, ensure_ascii=False, indent=2), encoding="utf-8")
    if not selected:
        if response_path.exists():
            response_path.unlink()
        print("리뷰어 호출 실패: 모든 후보가 실패했다. "
              f"{round_dir / 'request.md'}로 메인이 직접 대조하고 "
              "보고에 '자기 검토, 교차 검증 아님'을 밝힌다. "
              f"기록: {round_dir / 'invocation.json'}")
        return EXIT_NO_REVIEWER
    response_path.write_text(text + "\n", encoding="utf-8")
    verdict = next((line for line in text.splitlines() if line.startswith("판정:")),
                   "판정: (형식 없음, 응답을 직접 읽는다)")
    tried = " → ".join(f"{a['requested_model']}({a.get('failure', 'ok')})" for a in attempts)
    print(verdict)
    print(f"리뷰어: {selected['actual_model']} · 시도: {tried}")
    print(f"응답: {response_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
