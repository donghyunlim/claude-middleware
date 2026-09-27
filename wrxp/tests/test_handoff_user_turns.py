import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


WRXP_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = WRXP_ROOT / "skills/handoff/scripts/user_turns.py"

spec = importlib.util.spec_from_file_location("user_turns", SCRIPT)
user_turns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(user_turns)


def write_jsonl(records) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for record in records:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    handle.close()
    return Path(handle.name)


def claude_user(content, **extra):
    return {"type": "user", "timestamp": "t", "message": {"content": content}, **extra}


def codex_user(text):
    return {
        "type": "response_item",
        "timestamp": "t",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        },
    }


class ClaudeTurnsTests(unittest.TestCase):
    def test_keeps_only_user_authored_text(self):
        path = write_jsonl([
            claude_user("<local-command-caveat>x</local-command-caveat>", isMeta=True),
            claude_user("<command-name>/model</command-name><command-args></command-args>"),
            claude_user("<local-command-stdout>Set model</local-command-stdout>"),
            claude_user("최초 요청<system-reminder>injected</system-reminder>"),
            claude_user("<task-notification><task-id>a1</task-id></task-notification>"),
            claude_user([{"type": "tool_result", "content": "output"}]),
            {"type": "assistant", "message": {"content": "reply"}},
            claude_user([{"type": "text", "text": "두 번째"}, {"type": "image"}]),
        ])
        texts = [text for _, text, kind in user_turns.claude_turns(path) if kind == "user"]
        self.assertEqual(["최초 요청", "두 번째\n[1 image(s) attached]"], texts)

    def test_slash_command_with_arguments_is_kept(self):
        path = write_jsonl([
            claude_user(
                "<command-message>wrxp:handoff</command-message>\n"
                "<command-name>/wrxp:handoff</command-name>\n"
                "<command-args>저장은 홈에</command-args>"
            ),
        ])
        texts = [text for _, text, _ in user_turns.claude_turns(path)]
        self.assertEqual(["/wrxp:handoff 저장은 홈에"], texts)

    def test_compact_summary_becomes_marker(self):
        path = write_jsonl([
            claude_user("요청"),
            claude_user("summary of earlier turns", isCompactSummary=True),
        ])
        kinds = [kind for _, _, kind in user_turns.claude_turns(path)]
        self.assertEqual(["user", "marker"], kinds)


class OriginAndQueueTests(unittest.TestCase):
    def test_queued_prompt_kept_and_non_human_origin_dropped(self):
        def queued(prompt, mode="prompt", origin=None):
            attachment = {"type": "queued_command", "prompt": prompt,
                          "commandMode": mode, "timestamp": "q"}
            if origin:
                attachment["origin"] = {"kind": origin}
            return {"type": "attachment", "attachment": attachment}

        path = write_jsonl([
            queued("작업 중 보낸 지시", origin="human"),
            queued("완료 알림", mode="task-notification"),
            queued("슬랙에서 전달된 글", origin="peer"),
            claude_user("알림 본문", origin={"kind": "task-notification"}),
            claude_user("사용량 초기화, 계속", origin={"kind": "auto-continuation"}),
            claude_user("직접 입력", origin={"kind": "human"}),
            claude_user("<bash-input>ls</bash-input><bash-stdout>a.txt</bash-stdout>"),
        ])
        texts = [text for _, text, kind in user_turns.claude_turns(path) if kind == "user"]
        self.assertEqual(["작업 중 보낸 지시", "직접 입력", "! ls"], texts)

    def test_same_reply_to_two_questions_is_not_folded(self):
        turns = [
            ("t1", "ㅇㅇ", "user"), ("t2", "", "assistant"), ("t3", "ㅇㅇ", "user"),
        ]
        lines = list(user_turns.render(turns, max_chars=0))
        self.assertEqual(["\n## U1 t1\nㅇㅇ", "\n## U2 t3\nㅇㅇ"], lines)


class QuestionAnswerTests(unittest.TestCase):
    def test_claude_question_tool_answer_is_kept_with_chosen_option(self):
        path = write_jsonl([
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "q1", "name": "AskUserQuestion"},
                {"type": "tool_use", "id": "b1", "name": "Bash"},
            ]}},
            claude_user([{"type": "tool_result", "tool_use_id": "b1", "content": "ls"}]),
            claude_user(
                [{"type": "tool_result", "tool_use_id": "q1", "content": "The user answered"}],
                toolUseResult={
                    "questions": [{"question": "저장 위치?", "options": [
                        {"label": "홈", "description": "~/handoffs"},
                        {"label": "저장소", "description": "<repo>/handoffs"},
                    ]}],
                    "answers": {"저장 위치?": "저장소"},
                    "annotations": {"저장 위치?": {"notes": "omc 제외"}},
                },
            ),
        ])
        turns = [t for t in user_turns.claude_turns(path) if t[2] != "assistant"]
        self.assertEqual(1, len(turns))
        _, text, kind = turns[0]
        self.assertEqual("answer", kind)
        self.assertIn("Q: 저장 위치?\nA: 저장소", text)
        self.assertIn("(저장소: <repo>/handoffs)", text)
        self.assertNotIn("~/handoffs", text)
        self.assertIn("note: omc 제외", text)

    def test_codex_question_output_kept_unless_unavailable(self):
        def call(call_id):
            return {"type": "response_item", "timestamp": "t", "payload": {
                "type": "function_call", "name": "request_user_input", "call_id": call_id}}

        def output(call_id, text):
            return {"type": "response_item", "timestamp": "t", "payload": {
                "type": "function_call_output", "call_id": call_id, "output": text}}

        path = write_jsonl([
            call("c1"), output("c1", "request_user_input is unavailable in Default mode"),
            call("c2"), output("c2", "A안으로 진행"),
        ])
        texts = [text for _, text, _ in user_turns.codex_turns(path)]
        self.assertEqual(["[question tool answer]\nA안으로 진행"], texts)

    def test_dismissed_question_and_exact_option_match(self):
        path = write_jsonl([
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "q1", "name": "AskUserQuestion"},
                {"type": "tool_use", "id": "q2", "name": "AskUserQuestion"},
            ]}},
            claude_user([{"type": "tool_result", "tool_use_id": "q1",
                          "content": "The user doesn't want to proceed with this tool use."}]),
            claude_user(
                [{"type": "tool_result", "tool_use_id": "q2", "content": "answered"}],
                toolUseResult={
                    "questions": [{"question": "q?", "options": [
                        {"label": "A", "description": "첫째"},
                        {"label": "A안 확장", "description": "둘째"},
                    ]}],
                    "answers": {"q?": "A안 확장"},
                },
            ),
        ])
        texts = [text for _, text, kind in user_turns.claude_turns(path) if kind == "answer"]
        self.assertIn("[question dismissed without an answer]", texts[0])
        self.assertIn("(A안 확장: 둘째)", texts[1])
        self.assertNotIn("첫째", texts[1])


class CodexTurnsTests(unittest.TestCase):
    def test_drops_injected_context_and_marks_compaction(self):
        path = write_jsonl([
            codex_user("# AGENTS.md instructions\n<INSTRUCTIONS>...</INSTRUCTIONS>"),
            codex_user("<environment_context>cwd</environment_context>"),
            codex_user("<heartbeat>automation tick</heartbeat>"),
            codex_user("사용자 요청"),
            codex_user("<skill>\n<name>wrxp:haqqq</name>\n</skill>"),
            {"type": "compacted", "timestamp": "t", "payload": {"message": ""}},
            codex_user("이어서"),
        ])
        turns = list(user_turns.codex_turns(path))
        self.assertEqual(
            ["사용자 요청", "[compaction point]", "이어서"],
            [text for _, text, _ in turns],
        )
        self.assertEqual(["user", "marker", "user"], [kind for _, _, kind in turns])


class CodexMultipartTests(unittest.TestCase):
    def test_injected_parts_dropped_from_a_mixed_message(self):
        record = codex_user("<recommended_plugins>x</recommended_plugins>")
        record["payload"]["content"] += [
            {"type": "input_text", "text": "# AGENTS.md instructions\n..."},
            {"type": "input_text", "text": "<environment_context>cwd</environment_context>"},
            {"type": "input_text", "text": "실제 요청"},
        ]
        path = write_jsonl([record])
        texts = [text for _, text, kind in user_turns.codex_turns(path) if kind == "user"]
        self.assertEqual(["실제 요청"], texts)


class FormatDetectionTests(unittest.TestCase):
    def test_codex_detected_from_content_not_path(self):
        codex = write_jsonl([{"type": "session_meta", "payload": {"cwd": "/x"}}])
        claude = write_jsonl([{"type": "user", "message": {"content": "hi"}}])
        self.assertTrue(user_turns.is_codex_log(codex))
        self.assertFalse(user_turns.is_codex_log(claude))


class RenderTests(unittest.TestCase):
    def test_folds_resends_and_truncates(self):
        turns = [
            ("t1", "같은 메시지", "user"),
            ("t2", "같은 메시지", "user"),
            ("t3", "[compaction point]", "marker"),
            ("t4", "같은 메시지", "user"),
            ("t5", "가" * 12, "user"),
        ]
        lines = list(user_turns.render(turns, max_chars=10))
        self.assertEqual("\n## U1 t1\n같은 메시지", lines[0])
        self.assertEqual("(U1 resent t2)", lines[1])
        self.assertEqual("\n## U2 t4\n같은 메시지", lines[3])
        self.assertIn("[... 2 more chars]", lines[4])


if __name__ == "__main__":
    unittest.main()
