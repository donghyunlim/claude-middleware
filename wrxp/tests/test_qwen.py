"""qwen.py의 네트워크 없는 계약 테스트."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx


SCRIPT = Path(__file__).parents[1] / "scripts" / "qwen.py"
SPEC = importlib.util.spec_from_file_location("wrxp_qwen", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
qwen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qwen)


class QwenContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.environment)

    def test_endpoint_has_no_implicit_api_key(self) -> None:
        """키가 없을 때 인증 헤더를 만들지 않는 경로를 보호한다."""
        os.environ.pop("QWEN_API_KEY", None)
        os.environ.pop("QWEN_TOKEN", None)

        _, api_key = qwen._endpoint_and_key()

        self.assertIsNone(api_key)

    def test_endpoint_prefers_api_key_over_token(self) -> None:
        """명시한 API 키가 legacy token보다 우선해야 한다."""
        os.environ["QWEN_API_KEY"] = "test-api-key"
        os.environ["QWEN_TOKEN"] = "test-token"

        _, api_key = qwen._endpoint_and_key()

        self.assertEqual("test-api-key", api_key)

    def test_documented_symlink_env_location_is_loaded(self) -> None:
        """설치 문서의 ~/.claude/scripts/.env 경로가 loader 후보에 있어야 한다."""
        source = SCRIPT.read_text()

        self.assertTrue(
            'Path.home() / ".claude/scripts/.env"' in source,
            "qwen.py must load the documented symlink-side .env",
        )

    def test_limited_stdin_reads_one_extra_byte_to_detect_overflow(self) -> None:
        """한도 초과는 요청 전에 감지하되, 읽기량은 max_bytes+1로 제한한다."""
        payload = b"a" * (qwen.MAX_STDIN_BYTES - 1) + "가".encode("utf-8")
        stream = io.BytesIO(payload)

        text, byte_count = qwen.read_limited_stdin(stream)

        self.assertEqual(qwen.MAX_STDIN_BYTES + 1, byte_count)
        self.assertEqual(qwen.MAX_STDIN_BYTES + 1, stream.tell())
        self.assertLessEqual(len(text.encode("utf-8")), qwen.MAX_STDIN_BYTES + 1)

    def test_oversize_stdin_exits_with_request_error_without_calling_api(self) -> None:
        """초과 stdin을 잘라 보내지 않고 exit 2로 거절한다."""
        stdin = io.TextIOWrapper(io.BytesIO(b"a" * (qwen.MAX_STDIN_BYTES + 1)))
        stderr = io.StringIO()

        with (
            mock.patch.object(qwen.sys, "stdin", stdin),
            mock.patch.object(qwen.sys, "stderr", stderr),
            mock.patch.object(qwen.sys, "argv", ["qwen.py", "summarize"]),
            mock.patch.object(qwen, "ask") as ask,
            self.assertRaises(SystemExit) as raised,
        ):
            qwen.main()

        self.assertEqual(2, raised.exception.code)
        self.assertIn("초과", stderr.getvalue())
        ask.assert_not_called()

    def test_invalid_utf8_constraint_files_exit_2_without_calling_api(self) -> None:
        """사용자 제공 schema/grammar 파일의 디코딩 오류는 요청 오류다."""
        for flag in ("--schema", "--grammar"):
            with self.subTest(flag=flag), tempfile.NamedTemporaryFile() as constraint:
                constraint.write(bytes([255]))
                constraint.flush()
                stderr = io.StringIO()

                with (
                    mock.patch.object(
                        qwen.sys,
                        "stdin",
                        io.TextIOWrapper(io.BytesIO(b"")),
                    ),
                    mock.patch.object(qwen.sys, "stderr", stderr),
                    mock.patch.object(
                        qwen.sys,
                        "argv",
                        ["qwen.py", "summarize", flag, constraint.name],
                    ),
                    mock.patch.object(qwen, "ask") as ask,
                    self.assertRaises(SystemExit) as raised,
                ):
                    qwen.main()

                self.assertEqual(2, raised.exception.code)
                self.assertIn("파일 로드 실패", stderr.getvalue())
                ask.assert_not_called()

    def test_invalid_response_structures_raise_contract_error_and_map_to_exit_3(self) -> None:
        """유효 JSON이라도 chat-completion 계약을 벗어나면 서버·응답 장애다."""
        invalid_responses = (
            {},
            [],
            {"choices": [None]},
            {"choices": [{"message": []}]},
            {"choices": [{"message": {"content": 1}}]},
            {"choices": [{"message": {"reasoning_content": {}}}]},
            {"choices": [{"message": {"content": " ", "reasoning_content": "\n"}}]},
        )

        for response in invalid_responses:
            with self.subTest(response=response):
                with self.assertRaises(qwen.ResponseContractError) as raised:
                    qwen.extract_content(response)
                self.assertEqual(3, qwen.exit_code_for_error(raised.exception))

    def test_main_routes_invalid_response_to_exit_3_without_network(self) -> None:
        """응답 계약 오류는 잡히지 않은 AttributeError나 exit 2가 되면 안 된다."""
        stderr = io.StringIO()

        with (
            mock.patch.object(qwen.sys, "stdin", io.TextIOWrapper(io.BytesIO(b""))),
            mock.patch.object(qwen.sys, "stderr", stderr),
            mock.patch.object(qwen.sys, "argv", ["qwen.py", "summarize"]),
            mock.patch.object(qwen, "ask", return_value={"choices": [None]}) as ask,
            self.assertRaises(SystemExit) as raised,
        ):
            qwen.main()

        self.assertEqual(3, raised.exception.code)
        self.assertIn("ResponseContractError", stderr.getvalue())
        ask.assert_called_once()

    def test_expected_request_errors_have_fallback_exit_contract(self) -> None:
        """잘못된 요청은 2, 서버·응답 장애는 3으로 귀결돼야 한다."""
        request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
        response = httpx.Response(400, request=request)

        self.assertEqual(2, qwen.exit_code_for_error(ValueError("invalid timeout")))
        self.assertEqual(3, qwen.exit_code_for_error(json.JSONDecodeError("bad", "x", 0)))
        self.assertEqual(
            3,
            qwen.exit_code_for_error(
                UnicodeDecodeError("utf-8", bytes([255]), 0, 1, "invalid byte")
            ),
        )
        self.assertEqual(3, qwen.exit_code_for_error(httpx.ReadTimeout("slow", request=request)))
        self.assertEqual(
            2,
            qwen.exit_code_for_error(
                httpx.LocalProtocolError("invalid local header", request=request)
            ),
        )
        self.assertEqual(
            3,
            qwen.exit_code_for_error(
                httpx.ProtocolError("remote protocol failure", request=request)
            ),
        )
        self.assertEqual(2, qwen.exit_code_for_error(httpx.HTTPStatusError("bad request", request=request, response=response)))


if __name__ == "__main__":
    unittest.main()
