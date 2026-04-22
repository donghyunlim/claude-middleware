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
  QWEN_API_KEY / QWEN_TOKEN  (없으면 아래 DEFAULT_API_KEY 사용)

Exit codes (fallback 라우팅용):
  0 — 성공
  2 — HTTP 4xx 또는 요청 측 오류 (prompt/schema 문제). prompt 수정 후 재시도.
  3 — 서버 unreachable (connect fail / timeout / HTTP 5xx). **haiku fallback 권장**.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

DEFAULT_ENDPOINT = "https://qwen2.gocham.kr"
DEFAULT_MODEL = "Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf"
# 로컬 llama-server DDoS 가드용 하드코드 키. 유출 영향 미미 (endpoint 교체로 대응).
DEFAULT_API_KEY = "e3a3449a36ef845884f5aea5f068250383ea2fd5f6c6ffd7"

# stdin 대용량 가드 (Python 프로세스 OOM 회피).
MAX_STDIN_BYTES = 2_000_000  # ≈ 500K 한영 혼합 토큰

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
    Path.home() / ".claude/mcp-servers/qwen-mcp/.env",
):
    _load_env(candidate)


def _endpoint_and_key() -> tuple[str, str | None]:
    endpoint = os.environ.get("QWEN_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")
    api_key = (
        os.environ.get("QWEN_API_KEY")
        or os.environ.get("QWEN_TOKEN")
        or DEFAULT_API_KEY
    )
    return endpoint, api_key


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


def extract_content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(
            "Qwen 응답에 choices 가 비어있음: "
            + json.dumps(data, ensure_ascii=False)[:300]
        )
    msg = choices[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    reasoning = (msg.get("reasoning_content") or "").strip()
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
    prompt_stdin = "" if sys.stdin.isatty() else sys.stdin.read()

    if len(prompt_stdin) > MAX_STDIN_BYTES:
        sys.stderr.write(
            f"qwen.py: stdin {len(prompt_stdin)} bytes > {MAX_STDIN_BYTES}. "
            f"앞 {MAX_STDIN_BYTES} bytes 만 전송.\n"
        )
        prompt_stdin = prompt_stdin[:MAX_STDIN_BYTES]

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
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"qwen.py: --schema 파일 로드 실패: {exc}\n")
            sys.exit(2)

    grammar_str = None
    if args.grammar:
        try:
            with open(args.grammar) as f:
                grammar_str = f.read()
        except OSError as exc:
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
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        sys.stderr.write(
            f"qwen.py: server unreachable ({type(exc).__name__}): {exc}. "
            f"haiku fallback 권장. exit=3.\n"
        )
        sys.exit(3)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        body = exc.response.text[:200]
        if code >= 500:
            sys.stderr.write(
                f"qwen.py: HTTP {code} (server side) — fallback 권장. body: {body}\n"
            )
            sys.exit(3)
        sys.stderr.write(f"qwen.py: HTTP {code}: {body}\n")
        sys.exit(2)
    except httpx.HTTPError as exc:
        sys.stderr.write(
            f"qwen.py: transport error ({type(exc).__name__}): {exc}\n"
        )
        sys.exit(3)

    if args.raw:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    try:
        out = extract_content(data)
    except RuntimeError as exc:
        sys.stderr.write(f"qwen.py: {exc}\n")
        sys.exit(2)

    sys.stdout.write(out + ("" if out.endswith("\n") else "\n"))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
