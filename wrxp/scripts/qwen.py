#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Qwen3.6 로컬 LLM CLI 호출기 (OpenAI-compatible API).

설계 원칙:
- 대용량 payload 는 **file stdin** 으로 전달해 Claude context 밖에서 처리.
- Thinking 제어는 API 공식 방식 `chat_template_kwargs.enable_thinking=False` 만.
- 구조 강제는 llama.cpp 서버 레벨 (grammar / response_format).
- httpx 단일 의존성 (uv run 이 자동 격리).

사용 예:
  qwen.py --fast "2+3=?"
  cat big.md | qwen.py "요약해"
  qwen.py --raw "..."
  qwen.py --fast --json "apple 은 무엇? key=name, category"
  qwen.py --fast --enum "Fruit,Vehicle,Animal" "apple 분류?"
  qwen.py --probe                          # health check only (exit 0=up, 3=down)

환경 (모두 선택):
  QWEN_ENDPOINT  (기본 https://qwen2.gocham.kr)
  QWEN_MODEL     (기본 Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf)
  QWEN_API_KEY / QWEN_TOKEN  (없으면 인증 헤더 없이 호출)

Exit codes (fallback 라우팅용):
  0 — 성공
  2 — HTTP 4xx 또는 요청 측 오류 (prompt/schema 문제). prompt 수정 후 재시도.
  3 — 서버·네트워크·응답 형식 오류. **haiku fallback 권장**.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import BinaryIO

import httpx

DEFAULT_ENDPOINT = "https://qwen2.gocham.kr"
DEFAULT_MODEL = "Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf"

# fast-worker 최대 payload(600,000 bytes): Qwen 262K context에서 32K output 여유를 남긴다.
MAX_STDIN_BYTES = 600_000

# Qwen3.6 공식 long-output 한계 = 32,768 tokens.
# native context 는 262K 지만 생성 token 의 실용 상한은 32K 권장.
# 실제 생성은 stop 토큰 / grammar 종료로 자연 단축됨.
DEFAULT_MAX_TOKENS = 32768

# llama.cpp 공식 json.gbnf — response_format=json_object 가 약하게 해석되어
# ```json fence 또는 prose 섞이는 이슈를 회피.
JSON_GRAMMAR = r"""
root   ::= object
value  ::= object | array | string | number | ("true" | "false" | "null") ws
object ::= "{" ws ( string ":" ws value ("," ws string ":" ws value)* )? "}" ws
array  ::= "[" ws ( value ("," ws value)* )? "]" ws
string ::= "\"" (
    [^"\\\x7F\x00-\x1F] |
    "\\" (["\\bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
)* "\"" ws
number ::= ("-"? ([0-9] | [1-9] [0-9]{0,15})) ("." [0-9]+)? ([eE] [-+]? [0-9]+)? ws
ws ::= | " " | "\n" [ \t]{0,20}
"""


def _load_env(path: Path) -> None:
    """간단한 .env 파서: `KEY=VALUE`, `export KEY=VALUE`, `#` 주석, 따옴표 제거."""
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        os.environ.setdefault(
            key.strip(), value.strip().strip('"').strip("'")
        )


for candidate in (
    Path(__file__).resolve().parent / ".env",
    Path.home() / ".claude/scripts/.env",
    Path.home() / ".claude/mcp-servers/qwen-mcp/.env",
):
    _load_env(candidate)


def _endpoint_and_key() -> tuple[str, str | None]:
    endpoint = os.environ.get("QWEN_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")
    api_key = (
        os.getenv("QWEN_API_KEY")
        or os.getenv("QWEN_TOKEN")
    )
    return endpoint, api_key


def read_limited_stdin(
    stream: BinaryIO, max_bytes: int = MAX_STDIN_BYTES
) -> tuple[str, int]:
    """UTF-8 stdin을 최대 ``max_bytes + 1``만 읽어 text와 실제 읽은 byte 수를 반환한다.

    한글처럼 여러 byte로 구성된 문자가 경계에서 잘리면 불완전한 마지막 문자만
    버린다. 한 byte를 더 읽어 초과를 감지하고, 이후 byte는 읽지 않으므로
    대용량 pipe 입력으로 메모리가 커지지 않는다.
    """
    data = stream.read(max_bytes + 1)
    return data.decode("utf-8", errors="ignore"), len(data)


class ResponseContractError(RuntimeError):
    """OpenAI-compatible chat completion 응답이 기대 구조를 만족하지 않는다."""


def exit_code_for_error(exc: Exception) -> int:
    """요청 오류를 fast-worker가 이해하는 exit 계약(2/3)으로 분류한다."""
    if isinstance(exc, ResponseContractError):
        return 3
    if isinstance(exc, httpx.HTTPStatusError):
        return 3 if exc.response.status_code >= 500 else 2
    if isinstance(exc, httpx.LocalProtocolError):
        return 2
    if isinstance(exc, UnicodeDecodeError):
        return 3
    if isinstance(exc, (json.JSONDecodeError, httpx.TimeoutException, httpx.NetworkError,
                        httpx.ProtocolError, httpx.ProxyError, httpx.UnsupportedProtocol)):
        return 3
    if isinstance(exc, (ValueError, httpx.InvalidURL)):
        return 2
    if isinstance(exc, httpx.HTTPError):
        return 3
    return 2


def probe(timeout_s: float = 5.0) -> tuple[int, str]:
    """Health check. returns (exit_code, message). 0=up, 3=down.

    4xx 는 서버가 살아있다는 증거 (request 측 문제) 라서 up 판정.
    """
    endpoint, api_key = _endpoint_and_key()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        with httpx.Client(timeout=timeout_s) as c:
            r = c.get(f"{endpoint}/v1/models", headers=headers)
            r.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        return 3, f"down ({type(exc).__name__}: {exc})"
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            return 3, f"down (HTTP {exc.response.status_code})"
        return 0, f"up (HTTP {exc.response.status_code} — auth/request issue)"
    except httpx.HTTPError as exc:
        return 3, f"down ({type(exc).__name__}: {exc})"
    return 0, f"up ({endpoint})"


def _enum_to_gbnf(labels: list[str]) -> str:
    alternatives = " | ".join(
        f'"{label.strip()}"' for label in labels if label.strip()
    )
    return f"root ::= {alternatives}"


def ask(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    thinking: bool = True,
    timeout_s: float = 300.0,
    json_object: bool = False,
    json_schema: dict | None = None,
    enum_labels: list[str] | None = None,
    grammar: str | None = None,
) -> dict:
    endpoint, api_key = _endpoint_and_key()
    model = os.environ.get("QWEN_MODEL", DEFAULT_MODEL)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if not thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    # 구조 강제 — 우선순위: grammar > enum > json_schema > json_object.
    if enum_labels and grammar is None:
        # 짧거나 context-light prompt 에서 첫 라벨 편향 방지.
        hint = f"\n\n선택지 (정확히 하나): {', '.join(enum_labels)}"
        messages[-1]["content"] = messages[-1]["content"] + hint

    if grammar is not None:
        payload["grammar"] = grammar
    elif enum_labels:
        payload["grammar"] = _enum_to_gbnf(enum_labels)
    elif json_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"schema": json_schema},
        }
    elif json_object:
        payload["grammar"] = JSON_GRAMMAR

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    timeout = httpx.Timeout(
        connect=10.0, read=timeout_s, write=timeout_s, pool=10.0
    )
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{endpoint}/v1/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        return resp.json()


def _response_message(data: object) -> dict:
    if not isinstance(data, dict):
        raise ResponseContractError("Qwen 응답 root는 object여야 함")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ResponseContractError("Qwen 응답 choices는 비어 있지 않은 list여야 함")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ResponseContractError("Qwen 응답 첫 choice는 object여야 함")
    msg = choice.get("message")
    if not isinstance(msg, dict):
        raise ResponseContractError("Qwen 응답 message는 object여야 함")
    return msg


def validate_response_contract(data: object) -> None:
    """raw 출력 경로를 포함해 chat completion 응답 구조를 검증한다."""
    msg = _response_message(data)
    content = msg.get("content", "")
    reasoning = msg.get("reasoning_content", "")
    if not isinstance(content, str) or not isinstance(reasoning, str):
        raise ResponseContractError("Qwen 응답 content와 reasoning_content는 문자열이어야 함")
    if not content.strip() and not reasoning.strip():
        raise ResponseContractError("Qwen 응답 content와 reasoning_content가 모두 비어 있음")


def extract_content(data: object) -> str:
    validate_response_contract(data)
    msg = _response_message(data)
    content = msg.get("content", "").strip()
    reasoning = msg.get("reasoning_content", "").strip()
    if not content and reasoning:
        return (
            "[reasoning-only fallback — max_tokens 가 content 전에 소진. "
            "max_tokens 확장 또는 --fast 권장]\n" + reasoning
        )
    return content


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Qwen3.6 로컬 LLM CLI (OpenAI-compatible + llama.cpp 구조강제)"
    )
    ap.add_argument("prompt", nargs="?", help="프롬프트 (없으면 stdin 을 읽음)")
    ap.add_argument("-s", "--system", help="system 프롬프트")
    ap.add_argument(
        "--fast", action="store_true",
        help="thinking OFF (chat_template_kwargs.enable_thinking=False)"
    )
    ap.add_argument("-t", "--temperature", type=float, default=0.3)
    ap.add_argument(
        "-m", "--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
        help=f"최대 생성 토큰 수 (default {DEFAULT_MAX_TOKENS}, Qwen3.6 long-output 한계)",
    )
    ap.add_argument(
        "--timeout", type=float, default=300.0, help="read timeout (초)"
    )
    ap.add_argument(
        "--raw", action="store_true",
        help="전체 JSON 응답 (reasoning_content 포함)"
    )
    ap.add_argument(
        "--probe", action="store_true",
        help="health check only. exit 0=up, 3=down. fallback 라우팅에 사용."
    )
    # 구조 강제 옵션
    ap.add_argument(
        "--json", action="store_true",
        help="JSON object 출력 강제 (llama.cpp json.gbnf)"
    )
    ap.add_argument(
        "--schema", metavar="FILE",
        help="JSON schema 파일 → response_format={type:json_schema}"
    )
    ap.add_argument(
        "--enum", metavar="CSV", dest="enum_csv",
        help="enum 라벨 CSV (예: 'A,B,C') → GBNF + prompt auto-hint"
    )
    ap.add_argument(
        "--grammar", metavar="FILE",
        help="GBNF 파일 경로 → payload.grammar"
    )
    args = ap.parse_args()

    # Health check path
    if args.probe:
        exit_code, msg = probe()
        stream = sys.stdout if exit_code == 0 else sys.stderr
        stream.write(f"qwen.py: {msg}\n")
        stream.flush()
        sys.exit(exit_code)

    prompt_cli = args.prompt
    prompt_stdin = ""
    stdin_bytes = 0
    if not sys.stdin.isatty():
        prompt_stdin, stdin_bytes = read_limited_stdin(sys.stdin.buffer)
    if stdin_bytes > MAX_STDIN_BYTES:
        sys.stderr.write(
            f"qwen.py: stdin이 최대 {MAX_STDIN_BYTES} bytes를 초과했습니다. "
            "요청을 보내지 않았습니다. exit=2.\n"
        )
        sys.exit(2)

    if prompt_cli and prompt_stdin:
        prompt = f"{prompt_cli}\n\n---\n{prompt_stdin}"
    else:
        prompt = prompt_cli or prompt_stdin

    if not prompt:
        ap.error("prompt 가 비어 있음 (arg 또는 stdin 필요)")

    json_schema_dict = None
    if args.schema:
        try:
            with open(args.schema) as f:
                json_schema_dict = json.load(f)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"qwen.py: --schema 파일 로드 실패: {exc}\n")
            sys.exit(2)

    grammar_str = None
    if args.grammar:
        try:
            with open(args.grammar) as f:
                grammar_str = f.read()
        except (OSError, UnicodeError) as exc:
            sys.stderr.write(f"qwen.py: --grammar 파일 로드 실패: {exc}\n")
            sys.exit(2)

    enum_list = None
    if args.enum_csv:
        enum_list = [x.strip() for x in args.enum_csv.split(",") if x.strip()]
        if not enum_list:
            sys.stderr.write("qwen.py: --enum 값이 비어있음\n")
            sys.exit(2)

    try:
        data = ask(
            prompt,
            system=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            thinking=not args.fast,
            timeout_s=args.timeout,
            json_object=args.json,
            json_schema=json_schema_dict,
            enum_labels=enum_list,
            grammar=grammar_str,
        )
    except (ValueError, json.JSONDecodeError, httpx.HTTPError) as exc:
        exit_code = exit_code_for_error(exc)
        if isinstance(exc, httpx.HTTPStatusError):
            body = exc.response.text[:200]
            kind = "server side" if exit_code == 3 else "request side"
            sys.stderr.write(f"qwen.py: HTTP {exc.response.status_code} ({kind}): {body}\n")
        elif exit_code == 3:
            sys.stderr.write(
                f"qwen.py: server/response error ({type(exc).__name__}): {exc}. "
                "haiku fallback 권장. exit=3.\n"
            )
        else:
            sys.stderr.write(f"qwen.py: request error ({type(exc).__name__}): {exc}. exit=2.\n")
        sys.exit(exit_code)

    if args.raw:
        try:
            validate_response_contract(data)
        except ResponseContractError as exc:
            sys.stderr.write(
                f"qwen.py: server/response error ({type(exc).__name__}): {exc}. "
                "haiku fallback 권장. exit=3.\n"
            )
            sys.exit(3)
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    try:
        out = extract_content(data)
    except ResponseContractError as exc:
        sys.stderr.write(
            f"qwen.py: server/response error ({type(exc).__name__}): {exc}. "
            "haiku fallback 권장. exit=3.\n"
        )
        sys.exit(3)

    sys.stdout.write(out + ("" if out.endswith("\n") else "\n"))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
