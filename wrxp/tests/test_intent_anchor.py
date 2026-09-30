import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


WRXP_ROOT = Path(__file__).resolve().parents[1]
SHARED = WRXP_ROOT / "shared/scripts/user_turns.py"
WRAPPER = WRXP_ROOT / "skills/handoff/scripts/user_turns.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(records, directory=None, name=None) -> Path:
    directory = Path(directory or tempfile.mkdtemp())
    path = directory / (name or "session.jsonl")
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def claude_user(text, timestamp="t"):
    return {"type": "user", "timestamp": timestamp, "message": {"content": text}}


def claude_assistant(text="ok"):
    return {"type": "assistant", "timestamp": "t",
            "message": {"content": [{"type": "text", "text": text}]}}


class SharedExtractorTests(unittest.TestCase):
    def test_numbered_matches_render_numbering(self):
        ut = load(SHARED, "shared_user_turns")
        turns = [
            ("t1", "같은 말", "user"), ("t2", "같은 말", "user"),
            ("t3", "[compaction point]", "marker"), ("t4", "다음", "user"),
            ("t5", "", "assistant"), ("t6", "[question tool answer]\nA", "answer"),
        ]
        self.assertEqual(
            [(1, "t1", "같은 말", "turn"), (1, "t2", "", "resent"),
             (0, "t3", "[compaction point]", "marker"), (2, "t4", "다음", "turn"),
             (3, "t6", "[question tool answer]\nA", "turn")],
            list(ut.numbered(turns)),
        )

    def test_codex_goal_context_is_not_a_user_turn(self):
        ut = load(SHARED, "shared_user_turns")
        injected = {"type": "response_item", "timestamp": "t", "payload": {
            "type": "message", "role": "user", "content": [{"type": "input_text",
                "text": '<codex_internal_context source="goal">목표 계속</codex_internal_context>'}]}}
        real = {"type": "response_item", "timestamp": "t", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "실제 요청"}]}}
        path = write_jsonl([injected, real])
        self.assertEqual(["실제 요청"], [t for _, t, k in ut.codex_turns(path) if k == "user"])

    def test_handoff_wrapper_exposes_patchable_globals(self):
        wrapper = load(WRAPPER, "handoff_user_turns_wrapper")
        self.assertTrue(callable(wrapper.numbered))
        with mock.patch.object(wrapper, "CLAUDE_PROJECTS", Path("/nonexistent")):
            self.assertIsNone(wrapper.find_claude_log("x"))

    def test_handoff_wrapper_runs_as_a_script(self):
        log = write_jsonl([claude_user("첫 요청")])
        result = subprocess.run(
            [sys.executable, str(WRAPPER), "--log", str(log)],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("## U1 t\n첫 요청", result.stdout)


REVIEWER = WRXP_ROOT / "skills/intent-anchor/scripts/run_reviewer.py"


def reviewer():
    return load(REVIEWER, "run_reviewer")


class PacketTests(unittest.TestCase):
    def test_every_user_turn_is_included_verbatim(self):
        rr = reviewer()
        log = write_jsonl([
            claude_user("첫 요청: 로그인 흐름을 설명하는 문서"), claude_assistant(),
            claude_user("그게 아니라 흐름 이해가 목적"), claude_assistant(),
            claude_user("ㅇㅋ"),
        ])
        turns = rr.load_turns(log)
        self.assertEqual([1, 2, 3], [n for n, _, _ in turns])
        text, shortened = rr.render_turns(turns, log, "abcd1234")
        for fragment in ("## [원문] U1", "첫 요청: 로그인 흐름을 설명하는 문서",
                         "## [원문] U2", "## [원문] U3", "ㅇㅋ"):
            self.assertIn(fragment, text)
        self.assertEqual([], shortened)

    def test_until_turn_keeps_only_earlier_turns(self):
        rr = reviewer()
        log = write_jsonl([claude_user("a"), claude_assistant(), claude_user("b"),
                           claude_assistant(), claude_user("c")])
        self.assertEqual(["a", "b"], [t for _, _, t in rr.load_turns(log, until_turn=3)])

    def test_long_turn_keeps_head_and_tail_with_source(self):
        rr = reviewer()
        body, clipped = rr.clip("앞" * 1500 + "중" * 100 + "뒤" * 500, "log.jsonl U7")
        self.assertTrue(clipped)
        self.assertTrue(body.startswith("앞" * 1500))
        self.assertTrue(body.endswith("뒤" * 500))
        self.assertIn("100자 생략", body)
        self.assertIn("log.jsonl U7", body)

    def test_cap_folds_middle_turns_to_first_line(self):
        rr = reviewer()
        turns = [(n, "t", f"첫줄{n}\n" + "x" * 1900) for n in range(1, 11)]
        text, shortened = rr.render_turns(turns, Path("s.jsonl"), "sid", cap_bytes=8000)
        self.assertLessEqual(len(text.encode("utf-8")), 9000)
        self.assertIn("x" * 1900, text.split("## [원문] U2")[0])  # U1 full
        self.assertIn("## [원문] U10", text)
        self.assertIn("x" * 1900, text.split("## [원문] U10")[1])  # latest full
        self.assertIn("U2", shortened)
        self.assertIn("줄인 발화:", text)

    def test_cap_is_measured_in_utf8_bytes(self):
        rr = reviewer()
        turns = [(n, "t", "가" * 1000) for n in range(1, 9)]  # 3,000 bytes each
        text, shortened = rr.render_turns(turns, Path("s.jsonl"), "sid", cap_bytes=16000)
        self.assertTrue(shortened)
        self.assertLessEqual(len(text.encode("utf-8")), 17000)

    def test_redacts_values_after_secret_key_names_only(self):
        rr = reviewer()
        text = "SLACK_BOT_TOKEN=xoxb-123 api_key: abc monkey: banana PASSWORD=x"
        self.assertEqual(
            "SLACK_BOT_TOKEN=[REDACTED] api_key: [REDACTED] monkey: banana PASSWORD=x",
            rr.redact(text),
        )


HANDOFF_OLD = """# 작업 · 핸드오프

작성: 2026-09-20 10:00 KST · 세션 1111aaaa-0000-0000-0000-000000000000 · 프로젝트 폴더: /p · 이전 핸드오프: 없음

## 0. 재개 방법
- 첫 행동: x

## 1. 사용자 의도
### 1-1. 최초 의도
"로그인 이해를 AI에 맡기고 싶다" (1111aaaa:U1)

## 2. AI 기획
### 2-1. 핵심 포인트
문서 740개 생성

## 3. 현재 상태
- 완료: y
"""


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.old = self.dir / "handoffs/2026-09-20-a.md"
        self.old.parent.mkdir(parents=True)
        self.old.write_text(HANDOFF_OLD, encoding="utf-8")
        self.new = self.dir / "handoffs/2026-09-25-a.md"
        self.new.write_text(
            HANDOFF_OLD.replace("1111aaaa-0000", "2222bbbb-0000")
            .replace("이전 핸드오프: 없음", f"이전 핸드오프: {self.old}"),
            encoding="utf-8",
        )

    def test_finds_handoff_paths_in_user_turns(self):
        rr = reviewer()
        text = f"{self.new} 읽고 §0부터 이어서 진행해 줘."
        self.assertEqual([str(self.new)], rr.HANDOFF_PATH.findall(text))

    def test_chain_follows_previous_links_and_labels_sections(self):
        rr = reviewer()
        chain = rr.handoff_chain([self.new])
        self.assertEqual([self.new, self.old], [p for p, _ in chain])
        text, sessions = rr.render_handoffs(chain)
        self.assertIn(f"## [원문 인용] {self.new} §1", text)
        self.assertIn(f"## [AI 작성] {self.new} §2", text)
        self.assertIn("로그인 이해를 AI에 맡기고 싶다", text)
        self.assertNotIn("## 3. 현재 상태", text)
        self.assertEqual(
            ["1111aaaa-0000-0000-0000-000000000000",
             "2222bbbb-0000-0000-0000-000000000000"],
            sessions,
        )

    def test_missing_link_is_marked_unverified(self):
        rr = reviewer()
        chain = rr.handoff_chain([self.dir / "handoffs/none.md"])
        text, sessions = rr.render_handoffs(chain)
        self.assertIn("미확인", text)
        self.assertEqual([], sessions)

    def test_prior_session_turns_or_unverified(self):
        rr = reviewer()
        root = Path(tempfile.mkdtemp())
        (root / "proj").mkdir()
        write_jsonl([claude_user("이전 세션 첫 요청")], root / "proj",
                    "1111aaaa-0000-0000-0000-000000000000.jsonl")
        with mock.patch.object(rr.ut, "CLAUDE_PROJECTS", root), \
                mock.patch.object(rr.ut, "CODEX_SESSIONS", root / "none"):
            text = rr.render_prior_sessions(
                ["1111aaaa-0000-0000-0000-000000000000", "2222bbbb-0000-0000-0000-000000000000"],
                cap_bytes=10000,
            )
        self.assertIn("이전 세션 첫 요청", text)
        self.assertIn("2222bbbb-0000-0000-0000-000000000000: 미확인", text)

    def test_repo_state_reports_failure_outside_git(self):
        rr = reviewer()
        text = rr.repo_state(Path(tempfile.mkdtemp()))
        self.assertIn("# [기계 출력] 저장소 상태", text)
        self.assertIn("$ git status --short --branch", text)
        self.assertIn("실행 실패", text)


FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
open(os.environ["FAKE_ARGV"] + ".claude", "w").write(json.dumps(sys.argv[1:]))
sys.stdin.read()
mode = os.environ.get("FAKE_CLAUDE", "ok")
if mode == "limit":
    print("Claude usage limit reached", file=sys.stderr); sys.exit(1)
if mode == "garbage":
    print("warning: something odd"); sys.exit(0)
print(json.dumps({"type": "result", "is_error": False,
                  "result": "판정: 없음\n재구성한 의도: U1",
                  "modelUsage": {"claude-opus-5-5": {}}}))
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
open(os.environ["FAKE_ARGV"] + ".codex", "w").write(json.dumps(args))
sys.stdin.read()
if os.environ.get("FAKE_CODEX", "ok") == "limit":
    print("You've hit your usage limit", file=sys.stderr); sys.exit(1)
model = args[args.index("-m") + 1]
Path(args[args.index("-o") + 1]).write_text("판정: 드리프트 있음\n드리프트 목록: 수단이 목적을 대체", encoding="utf-8")
thread = "0000-thread-" + model
sessions = Path(os.environ["CODEX_HOME"]) / "sessions/2026/09/30"
sessions.mkdir(parents=True, exist_ok=True)
(sessions / f"rollout-x-{thread}.jsonl").write_text(json.dumps({"type": "turn_context",
    "payload": {"model": model, "effort": "high", "sandbox_policy": {"type": "read-only"}}}) + "\n")
print(json.dumps({"type": "thread.started", "thread_id": thread}))
'''


class ReviewerRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.codex_home = self.tmp / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "models_cache.json").write_text(json.dumps({"models": [
            {"slug": "gpt-5.6-sol"}, {"slug": "gpt-6-sol"}, {"slug": "gpt-6.1-sol"},
            {"slug": "gpt-6-astra"},
            {"slug": "gpt-6-luna"}, {"slug": "gpt-5.6-terra"},
        ]}))
        self.log = write_jsonl([claude_user("첫 요청"), claude_assistant(),
                                claude_user("그게 아니라 원래 의도는 이해")], self.tmp)
        self.state = self.tmp / "ai-state.md"
        self.state.write_text("- 목표: 문서 생성\n- 근거: git log", encoding="utf-8")
        self.out = self.tmp / "realign"
        # Task 4 runs before the production reviewer prompt is added in Task 5.
        self.prompt = self.tmp / "reviewer-prompt.md"
        self.prompt.write_text("# 의도 대조 요청\n", encoding="utf-8")

    def install(self, *names):
        for name in names:
            path = self.bin / name
            path.write_text(FAKE_CLAUDE if name == "claude" else FAKE_CODEX)
            path.chmod(0o755)

    def run_main(self, *extra, env=None):
        rr = reviewer()
        environ = {
            "PATH": f"{self.bin}:{os.path.dirname(sys.executable)}:/usr/bin:/bin",
            "CODEX_HOME": str(self.codex_home),
            "FAKE_ARGV": str(self.tmp / "argv"),
        }
        environ.update(env or {})
        args = ["--state", str(self.state), "--out", str(self.out), "--log", str(self.log),
                "--project", str(self.tmp), "--no-repo-state", *extra]
        with mock.patch.dict(os.environ, environ, clear=True), \
                mock.patch.object(rr, "PROMPT", self.prompt):
            code = rr.main(args)
        return rr, code

    def invocation(self, round_no=1):
        return json.loads((self.out / f"round-{round_no}/invocation.json").read_text())

    def test_codex_models_rank_astra_over_sol_newest_generation(self):
        rr = reviewer()
        self.assertEqual(["gpt-6-astra", "gpt-6.1-sol"],
                         rr.codex_models(self.codex_home / "models_cache.json"))

    def test_candidates_put_opposite_family_first(self):
        rr = reviewer()
        cache = self.codex_home / "models_cache.json"
        both = {"claude": True, "codex": True}
        self.assertEqual(
            [("codex", "gpt-6-astra"), ("codex", "gpt-6.1-sol"), ("claude", "opus")],
            rr.candidates("claude", both, cache))
        self.assertEqual(
            [("claude", "opus"), ("claude", "sonnet"), ("codex", "gpt-6-astra")],
            rr.candidates("codex", both, cache))
        self.assertEqual([("claude", "opus")],
                         rr.candidates("claude", {"claude": True, "codex": False}, cache))

    def test_detect_main_runtime_from_environment(self):
        rr = reviewer()
        self.assertEqual("claude", rr.detect_main_runtime({"CLAUDE_CODE_SESSION_ID": "a"}))
        self.assertEqual("codex", rr.detect_main_runtime({"CODEX_THREAD_ID": "b"}))
        self.assertIsNone(rr.detect_main_runtime({}))

    def test_commands_are_read_only_and_pin_high_effort(self):
        rr = reviewer()
        claude = rr.reviewer_command("claude", "opus", Path("/p"), ["/p", "/logs"], Path("/o/r.md"))
        self.assertEqual(claude[claude.index("--tools") + 1], "Read,Grep,Glob")
        self.assertEqual(claude[claude.index("--effort") + 1], "high")
        self.assertEqual(claude[claude.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(claude[-3:], ["--add-dir", "/p", "/logs"])
        codex = rr.reviewer_command("codex", "gpt-6-astra", Path("/p"), ["/p"], Path("/o/r.md"))
        self.assertEqual(codex[codex.index("--sandbox") + 1], "read-only")
        self.assertIn('model_reasoning_effort="high"', codex)
        self.assertEqual(codex[-1], "-")

    def test_claude_main_uses_codex_astra_and_records_actual_model(self):
        self.install("claude", "codex")
        _, code = self.run_main(env={"CLAUDE_CODE_SESSION_ID": "x"})
        self.assertEqual(0, code)
        record = self.invocation()
        self.assertEqual({"runtime": "codex", "actual_model": "gpt-6-astra"}, record["selected"])
        self.assertEqual("read-only", record["attempts"][0]["actual_sandbox"])
        self.assertEqual("high", record["attempts"][0]["actual_effort"])
        request = (self.out / "round-1/request.md").read_text()
        self.assertIn("그게 아니라 원래 의도는 이해", request)
        self.assertIn("# [AI 주장] 메인의 현재 상태", request)
        self.assertTrue((self.out / "round-1/response.md").read_text().startswith("판정:"))

    def test_fallback_is_recorded_when_opposite_family_hits_limit(self):
        self.install("claude", "codex")
        _, code = self.run_main("--main-runtime", "claude", env={"FAKE_CODEX": "limit"})
        self.assertEqual(0, code)
        record = self.invocation()
        self.assertEqual(["usage_limit", "usage_limit"],
                         [a.get("failure") for a in record["attempts"][:2]])
        self.assertEqual({"runtime": "claude", "actual_model": "claude-opus-5-5"},
                         record["selected"])

    def test_non_json_claude_output_falls_back(self):
        self.install("claude", "codex")
        _, code = self.run_main("--main-runtime", "codex", env={"FAKE_CLAUDE": "garbage"})
        self.assertEqual(0, code)
        record = self.invocation()
        self.assertEqual("empty_response", record["attempts"][0]["failure"])
        self.assertEqual("codex", record["selected"]["runtime"])

    def test_all_reviewers_failing_exits_4(self):
        self.install("claude")
        _, code = self.run_main("--main-runtime", "claude", env={"FAKE_CLAUDE": "limit"})
        self.assertEqual(4, code)
        self.assertIsNone(self.invocation()["selected"])
        self.assertFalse((self.out / "round-1/response.md").exists())

    def test_missing_session_log_exits_3(self):
        rr = reviewer()
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=True):
            code = rr.main(["--state", str(self.state), "--out", str(self.out),
                            "--session-id", "no-such-session", "--main-runtime", "claude"])
        self.assertEqual(3, code)

    def test_no_turns_left_exits_3(self):
        self.install("claude", "codex")
        _, code = self.run_main("--main-runtime", "claude", "--until-turn", "1")
        self.assertEqual(3, code)
        self.assertFalse((self.out / "round-1").exists())

    def test_unknown_main_runtime_exits_2(self):
        self.install("claude", "codex")
        _, code = self.run_main()
        self.assertEqual(2, code)

    def test_existing_round_dir_is_not_overwritten(self):
        self.install("claude", "codex")
        (self.out / "round-1").mkdir(parents=True)
        _, code = self.run_main("--main-runtime", "claude")
        self.assertEqual(2, code)

    def test_missing_previous_round_exits_2(self):
        self.install("claude", "codex")
        rebuttal = self.tmp / "rebuttal-2.md"
        rebuttal.write_text("U2 근거로 반박", encoding="utf-8")
        _, code = self.run_main("--main-runtime", "claude", "--round", "2",
                                "--rebuttal", str(rebuttal))
        self.assertEqual(2, code)

    def test_second_round_carries_history_and_rebuttal(self):
        self.install("claude", "codex")
        self.run_main("--main-runtime", "claude")
        rebuttal = self.tmp / "rebuttal-2.md"
        rebuttal.write_text("U2 근거로 반박", encoding="utf-8")
        _, code = self.run_main("--main-runtime", "claude", "--round", "2",
                                "--rebuttal", str(rebuttal))
        self.assertEqual(0, code)
        request = (self.out / "round-2/request.md").read_text()
        self.assertIn("# 1회차 리뷰어 응답", request)
        self.assertIn("# [AI 주장] 2회차 메인 반박", request)
        self.assertIn("U2 근거로 반박", request)
        self.assertTrue((self.out / "round-2/rebuttal.md").exists())


if __name__ == "__main__":
    unittest.main()
