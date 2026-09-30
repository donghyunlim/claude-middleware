# wrxp:intent-anchor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자 발화 원문을 기준으로 작업의 드리프트를 다른 맥락의 최고 수준 모델과 대조하는 `wrxp:intent-anchor` 스킬을 wrxp 0.1.39로 추가한다.

**Architecture:** 스킬 절차는 `SKILL.md`에 두고, 메인이 거를 수 없어야 하는 부분(사용자 발화 전부 추출, 이전 handoff 추적, 저장소 상태, 리뷰어 선택·실행·기록)은 `scripts/run_reviewer.py` 한 파일이 맡는다. 사용자 발화 추출기는 handoff에서 `shared/scripts/user_turns.py`로 옮기고, handoff 경로에는 호환 래퍼를 둔다.

**Tech Stack:** Python 3.9+ 표준 라이브러리만 사용, `unittest`(pytest로 실행), Claude Code CLI 2.1.x, Codex CLI 0.159.x.

**Spec:** `wrxp/docs/specs/2026-09-30-intent-anchor-design.md`

## Global Constraints

- Python 3.9 이상에서 동작해야 한다. 외부 패키지를 추가하지 않는다. 런타임 `X | Y` 타입 표현은 쓰지 않고 `from __future__ import annotations`를 둔다.
- 리뷰어 effort는 `high`로 고정한다.
- Claude 리뷰어 도구는 `--tools "Read,Grep,Glob"`만 허용한다. Codex 리뷰어는 `--sandbox read-only`로 실행한다. `--dangerously-*`, `bypassPermissions`, `workspace-write`, `danger-full-access`는 소스 어디에도 쓰지 않는다.
- 후보 순서: 반대 계열 최고 → 반대 계열 차순위 → 같은 계열 최고. 계열 순위는 Codex `astra > sol`, Claude `opus > sonnet`이다. 새 Codex 슬러그를 추측하지 않고 `models_cache.json`에 있는 것만 쓴다.
- 발화 잘림: 앞 1,500자와 뒤 500자. 패킷 상한: 150,000바이트(UTF-8 기준).
- 비밀값 가림: 이름이 `_TOKEN`, `_KEY`, `_SECRET`, `_PASSWORD`로 끝나는 키의 `=` 또는 `:` 뒤 값만 가린다. 값 모양으로 검색하지 않는다.
- 종료 코드: 0 성공, 2 사용 오류, 3 원문 미확인, 4 모든 리뷰어 실패.
- 회차당 제한 시간 600초, 토론은 최대 3회다.
- 버전은 `0.1.39`이며 `wrxp/.claude-plugin/plugin.json`, `wrxp/package.json`, `.claude-plugin/marketplace.json`에서 일치해야 한다.
- 다른 스킬의 `SKILL.md`와 `shared/*.md`는 `intent-anchor`를 언급하지 않는다(D16). setup의 `global-rules.md`에는 한 줄을 둔다.
- 배포 파일과 벤치마크 기록에는 대화 원문·개인 이름을 넣지 않는다. 결과는 판정·모델·소요 시간과 요지로 기록한다.
- 모든 명령은 `/Users/donny2/project/claude-middleware/wrxp`에서 실행한다. 전체 검사는 `python3 -m pytest -q tests`이며, 시작 시점 기준선은 87 passed다.
- 커밋은 `feat/wrxp-intent-anchor` 브랜치에만 하고, `.omc/` 아래 변경은 스테이징하지 않는다. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`를 붙인다.

## Review Focus

1. `--until-turn 1`처럼 남는 사용자 발화가 없는 재생: 빈 패킷으로 리뷰어를 부르지 않고 종료 코드 3으로 끝나야 한다. → Task 4 `test_no_turns_left_exits_3`
2. 2회차 이상인데 이전 회차의 `response.md`가 없음(`--out`을 잘못 지정한 경우): 이력 없는 패킷을 조용히 보내지 않고 종료 코드 2로 끝나야 한다. → Task 4 `test_missing_previous_round_exits_2`
3. Claude CLI가 JSON이 아닌 경고문을 출력하고 종료 코드 0으로 끝남: 성공으로 오인하거나 예외로 죽지 않고 실패로 기록한 뒤 폴백해야 한다. → Task 4 `test_non_json_claude_output_falls_back`
4. 같은 `round-N`을 다시 실행: 기존 기록을 덮어쓰지 않고 종료 코드 2로 끝나야 한다. → Task 4 `test_existing_round_dir_is_not_overwritten`
5. 한국어 위주의 긴 세션: 상한은 문자 수가 아니라 UTF-8 바이트로 적용되어야 한다. → Task 2 `test_cap_is_measured_in_utf8_bytes`

---

## File Structure

| 파일 | 책임 |
|---|---|
| `shared/scripts/user_turns.py` (이동) | 세션 로그에서 사용자 발화 추출. 새 함수 `numbered()`가 번호 매기기를 제공하고 `render()`는 이를 사용한다. |
| `skills/handoff/scripts/user_turns.py` (교체) | 공유 소스를 자기 네임스페이스에서 실행하는 호환 래퍼 |
| `skills/intent-anchor/scripts/run_reviewer.py` (신규) | 패킷 조립, 리뷰어 선택, 실행, 기록 |
| `skills/intent-anchor/references/reviewer-prompt.md` (신규) | 리뷰어 지시문 |
| `skills/intent-anchor/SKILL.md` (신규) | 호출 조건, 절차, 보고 형식 |
| `skills/intent-anchor/agents/openai.yaml` (신규) | Codex 표시 정보와 호출 정책 |
| `tests/test_intent_anchor.py` (신규) | run_reviewer 단위 테스트 |
| `tests/test_wrxp_invariants.py` (수정) | 호출 정책, 읽기 전용, 연결 금지, 버전 |
| `README.md`, `CHANGELOG.md`, 버전 파일 3개, `skills/setup/assets/global-rules.md` (수정) | 배포 정보 |
| `docs/benchmark/intent-anchor-0.1.39.md` (신규) | 실제 세션 재생 결과 |

---

### Task 1: 사용자 발화 추출기를 shared로 옮기기

**Files:**
- Create: `shared/scripts/user_turns.py` (기존 `skills/handoff/scripts/user_turns.py` 내용을 옮기고 `numbered()` 추가)
- Modify: `skills/handoff/scripts/user_turns.py` (호환 래퍼로 교체)
- Test: `tests/test_intent_anchor.py` (신규), `tests/test_handoff_user_turns.py` (수정하지 않음)

**Interfaces:**
- Produces: `numbered(turns) -> Iterator[tuple[int, str, str, str]]`. 각 항목은 `(number, timestamp, text, kind)`이다. `kind`는 `"turn"`(사용자 입력과 질문 답), `"marker"`(압축 지점, number 0), `"resent"`(직전과 같은 재전송, number는 앞 번호, text는 빈 문자열) 중 하나다. 기존 `claude_turns`, `codex_turns`, `is_codex_log`, `find_claude_log`, `find_codex_log`, `resolve`, `render`의 시그니처는 그대로 둔다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_intent_anchor.py`를 새로 만든다.

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py`
Expected: FAIL (`shared/scripts/user_turns.py`가 없어 `FileNotFoundError`)

- [ ] **Step 3: 추출기를 옮기고 `numbered()`를 추가**

```bash
mkdir -p shared/scripts
git mv skills/handoff/scripts/user_turns.py shared/scripts/user_turns.py
```

`shared/scripts/user_turns.py`에서 `def render(...)` 전체를 아래 두 함수로 교체한다(출력 형식은 기존과 같다).

```python
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
```

`skills/handoff/scripts/user_turns.py`를 새로 만든다.

```python
#!/usr/bin/env python3
"""Compatibility entry point for wrxp/shared/scripts/user_turns.py.

The shared source runs in this module's namespace so callers that patch module
globals (CLAUDE_PROJECTS, CODEX_SESSIONS) still reach the functions they call.
"""

from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "scripts" / "user_turns.py"
exec(compile(_SHARED.read_text(encoding="utf-8"), str(_SHARED), "exec"), globals())
```

`exec`한 소스 끝의 `if __name__ == "__main__": raise SystemExit(main())`가 래퍼를 스크립트로 실행할 때도 동작하므로 래퍼에는 별도의 main 블록을 두지 않는다. `main()`의 `__doc__`는 래퍼 docstring을 쓴다.

- [ ] **Step 4: 새 테스트와 기존 handoff 테스트가 통과하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py tests/test_handoff_user_turns.py`
Expected: PASS. `tests/test_handoff_user_turns.py`는 수정하지 않았다.

- [ ] **Step 5: 전체 검사 후 커밋**

Run: `python3 -m pytest -q tests`
Expected: 90 passed

```bash
git add shared/scripts/user_turns.py skills/handoff/scripts/user_turns.py tests/test_intent_anchor.py
git commit -m "refactor(wrxp): share the user-turn extractor with a handoff wrapper

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 패킷 조립 (사용자 발화, 잘림, 상한, 가림)

**Files:**
- Create: `skills/intent-anchor/scripts/run_reviewer.py`
- Test: `tests/test_intent_anchor.py`

**Interfaces:**
- Consumes: `ut.numbered`, `ut.claude_turns`, `ut.codex_turns`, `ut.is_codex_log` (Task 1)
- Produces:
  - `redact(text: str) -> str`
  - `clip(text: str, where: str, head: int = HEAD, tail: int = TAIL) -> tuple[str, bool]`
  - `load_turns(log: Path, until_turn: int | None = None) -> list[tuple[int, str, str]]`. 각 항목은 `(number, timestamp, text)`이며 `until_turn`은 그 번호 **미만**만 남긴다.
  - `render_turns(turns, source: Path, session: str, cap_bytes: int = CAP_BYTES) -> tuple[str, list[str]]`. 반환값은 마크다운과 줄인 발화 라벨(`"U3"` 등)이다.
  - 상수 `HEAD = 1500`, `TAIL = 500`, `CAP_BYTES = 150_000`, `KEEP_RECENT = 3`, 모듈 속성 `ut`(공유 추출기)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_intent_anchor.py`의 `if __name__` 위에 추가한다.

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py -k PacketTests`
Expected: FAIL (`run_reviewer.py`가 없음)

- [ ] **Step 3: 최소 구현 작성**

`skills/intent-anchor/scripts/run_reviewer.py`를 만든다.

```python
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
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py -k PacketTests`
Expected: PASS (6개)

- [ ] **Step 5: 커밋**

```bash
git add skills/intent-anchor/scripts/run_reviewer.py tests/test_intent_anchor.py
git commit -m "feat(wrxp): assemble intent-anchor packets from raw user turns

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 이전 handoff 추적과 저장소 상태

**Files:**
- Modify: `skills/intent-anchor/scripts/run_reviewer.py`
- Test: `tests/test_intent_anchor.py`

**Interfaces:**
- Consumes: `redact`, `load_turns`, `render_turns` (Task 2), `ut.find_claude_log`, `ut.find_codex_log`
- Produces:
  - `HANDOFF_PATH`: 발화 속 `.../handoffs/....md` 절대 경로를 찾는 정규식
  - `section(text: str, number: int) -> str`. `## N.` 절의 본문을 반환한다.
  - `handoff_chain(paths: list[Path], limit: int = 10) -> list[tuple[Path, str | None]]`. 먼저 받은 경로부터 `이전 핸드오프:` 링크를 따라가며, 읽을 수 없으면 text가 `None`이다.
  - `render_handoffs(chain) -> tuple[str, list[str]]`. 반환값은 마크다운과 사전 세션 ID 목록(가장 오래된 것, 가장 최근 것 순서, 중복 제거)이다.
  - `render_prior_sessions(session_ids: list[str], cap_bytes: int) -> str`
  - `repo_state(project: Path) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py -k HandoffTests`
Expected: FAIL (`AttributeError: module 'run_reviewer' has no attribute 'HANDOFF_PATH'`)

- [ ] **Step 3: 구현 추가**

`render_turns` 아래에 추가한다.

```python
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
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py -k HandoffTests`
Expected: PASS (5개)

- [ ] **Step 5: 커밋**

```bash
git add skills/intent-anchor/scripts/run_reviewer.py tests/test_intent_anchor.py
git commit -m "feat(wrxp): trace prior handoffs and repo state for intent-anchor

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 리뷰어 선택·실행·기록과 CLI

**Files:**
- Modify: `skills/intent-anchor/scripts/run_reviewer.py`
- Test: `tests/test_intent_anchor.py`

**Interfaces:**
- Consumes: Task 2·3의 모든 함수
- Produces:
  - `codex_models(cache: Path) -> list[str]`. `astra`, `sol` 순서로 계열마다 가장 높은 세대의 슬러그 1개씩을 반환한다.
  - `candidates(main_runtime: str, available: dict[str, bool], cache: Path) -> list[tuple[str, str]]`
  - `detect_main_runtime(env=None) -> str | None`
  - `reviewer_command(runtime: str, model: str, project: Path, read_dirs: list[str], response_path: Path) -> list[str]`
  - `run_claude(cmd, packet, timeout) -> tuple[dict, str]`, `run_codex(cmd, packet, timeout, response_path) -> tuple[dict, str]`
  - `codex_turn_context(thread_id: str | None) -> dict`. 반환 키는 `model`, `effort`, `sandbox`다.
  - `main(argv: list[str] | None = None) -> int`. CLI 옵션은 `--state`(필수), `--out`(필수), `--round`(기본 1), `--rebuttal`, `--session-id`, `--log`, `--until-turn`, `--no-repo-state`, `--handoff`(반복 가능), `--project`(기본 cwd), `--main-runtime {claude,codex}`, `--timeout`(기본 600), `--cap-bytes`(기본 150000).
  - 기록: `<out>/round-N/request.md`, `response.md`, `invocation.json`(2회차부터 `rebuttal.md` 포함). 표준 출력 첫 줄은 `판정:` 줄이거나 실패 안내다.

- [ ] **Step 1: 가짜 CLI와 실패하는 테스트 작성**

```python
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
        with mock.patch.dict(os.environ, environ, clear=True):
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py -k ReviewerRunTests`
Expected: FAIL (`AttributeError: ... 'codex_models'`)

- [ ] **Step 3: 구현 추가**

`repo_state` 아래에 추가한다.

```python
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
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `python3 -m pytest -q tests/test_intent_anchor.py`
Expected: PASS (Task 1~4 전체)

`test_fallback_is_recorded_when_opposite_family_hits_limit`는 Astra와 Sol(`gpt-6.1-sol`) 두 번의 실패 뒤 같은 계열인 Opus가 선택되는지를 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add skills/intent-anchor/scripts/run_reviewer.py tests/test_intent_anchor.py
git commit -m "feat(wrxp): select, run, and record read-only intent-anchor reviewers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 스킬 본문, 리뷰어 지시문, 호출 정책

**Files:**
- Create: `skills/intent-anchor/SKILL.md`
- Create: `skills/intent-anchor/references/reviewer-prompt.md`
- Create: `skills/intent-anchor/agents/openai.yaml`
- Modify: `tests/test_wrxp_invariants.py` (클래스 `WrxpInvariantTests`에 세 테스트 추가)

**Interfaces:**
- Consumes: `run_reviewer.py`의 CLI 옵션과 종료 코드 (Task 4). 리뷰어 지시문은 `PROMPT` 경로(`references/reviewer-prompt.md`)에서 읽힌다.

- [ ] **Step 1: 실패하는 불변식 테스트 작성**

`test_cloudinfra_review_has_no_automatic_pipeline_or_hook_connections` 아래에 추가한다.

```python
    def test_intent_anchor_allows_rare_implicit_invocation_on_both_runtimes(self):
        skill_dir = WRXP_ROOT / "skills/intent-anchor"
        frontmatter = (skill_dir / "SKILL.md").read_text().split("---", 2)[1]
        self.assertNotIn("disable-model-invocation", frontmatter)
        for phrase in ("strongly corrects", "retried", "Not for ordinary bug reports"):
            self.assertIn(phrase, frontmatter)
        metadata = (skill_dir / "agents/openai.yaml").read_text()
        self.assertRegex(metadata, r"(?m)^policy:\n  allow_implicit_invocation: true$")

    def test_intent_anchor_reviewer_commands_are_read_only(self):
        source = (WRXP_ROOT / "skills/intent-anchor/scripts/run_reviewer.py").read_text()
        self.assertIn('"Read,Grep,Glob"', source)
        self.assertIn('"read-only"', source)
        for forbidden in ("dangerously", "bypassPermissions",
                          "workspace-write", "danger-full-access"):
            self.assertNotIn(forbidden, source)
        prompt = (WRXP_ROOT / "skills/intent-anchor/references/reviewer-prompt.md").read_text()
        self.assertIn("판정: 드리프트 있음 | 없음 | 부분", prompt)

    def test_intent_anchor_is_not_wired_into_other_skills(self):
        entrypoints = [path for path in (WRXP_ROOT / "skills").glob("*/SKILL.md")
                       if path.parent.name != "intent-anchor"]
        entrypoints += list((WRXP_ROOT / "shared").rglob("*.md"))
        for path in entrypoints:
            self.assertNotIn("intent-anchor", path.read_text(), str(path))
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest -q tests/test_wrxp_invariants.py -k intent_anchor`
Expected: FAIL (`SKILL.md` 없음)

- [ ] **Step 3: 세 파일 작성**

`skills/intent-anchor/agents/openai.yaml`:

```yaml
interface:
  display_name: "Intent Anchor"
  short_description: "사용자 발화 원문을 기준으로 작업이 원래 의도에서 벗어났는지 다른 모델과 대조합니다"
  default_prompt: "$wrxp:intent-anchor로 지금 작업이 내 원래 의도와 결정에서 벗어났는지 원문 기준으로 대조해 줘."
policy:
  allow_implicit_invocation: true
```

`skills/intent-anchor/references/reviewer-prompt.md`:

````markdown
# 의도 대조 요청

당신은 이 작업에 참여하지 않은 리뷰어입니다. 메인 AI의 작업이 사용자의 의도에서 벗어났는지(드리프트) 판정합니다. 읽기 도구로 저장소와 세션 로그를 확인할 수 있습니다. 파일 수정, 명령 실행, 외부 발송은 하지 않고 판정과 제안만 반환합니다. 비공개 사고 과정이 아니라 메인이 검토할 수 있는 판정·근거·제안만 씁니다.

## 자료의 권위

- `[원문]`: 스크립트가 세션 로그에서 추출한 사용자 발화입니다. 가장 높은 권위를 가집니다. 잘리거나 줄인 발화는 표시된 로그 경로에서 전문을 읽을 수 있습니다.
- `[원문 인용]`: 이전 핸드오프가 인용한 사용자 발화입니다. 이전 세션 발화가 함께 있으면 대조합니다.
- `[기계 출력]`: git 명령의 결과입니다.
- `[AI 주장]`, `[AI 작성]`: 메인 AI가 쓴 내용입니다. 원문이나 저장소로 확인되기 전에는 사실로 쓰지 않습니다.
- `[question tool answer]`: 선택지 질문에 대한 사용자 답입니다. 답 없이 닫힌 질문은 결정이 아닙니다.

## 판정 기준

- 방향 변화의 근거가 사용자 발화(U번호)에 있으면, 최초 요청과 멀어 보여도 **허용**합니다. 사용자는 작업 중에 생각을 바꿀 수 있습니다.
- AI가 정한 수단이 사용자의 목적을 대체했으면 **드리프트**입니다. 예: 목적은 "이해와 설명 부담을 AI에 맡긴다"인데 "페이지 N개 생성·발행 성공"으로 완료를 판정한 경우.
- 사용자가 답하지 않은 AI 제안을 승인된 것으로 취급했으면 **드리프트**입니다. "ㅇㅇ", "추천안대로" 같은 답은 직전 질문의 내용을 풀어서 승인 범위를 정합니다.
- 사용자가 기각한 대안을 다시 추진하고 있으면 **드리프트**입니다.
- 사소한 구현 선택은 드리프트로 보지 않습니다. 사용자가 되돌리고 싶어 할 만큼 방향·범위·완료 기준에 영향을 주는 것만 다룹니다.
- 사용자의 마음을 단정하지 않습니다. 원문으로 확인한 사실과 해석을 구분해 씁니다.

## 2회차 이후

메인의 반박이 붙어 있으면 그 근거를 원문과 저장소로 확인합니다. 근거가 타당하면 판정을 바꾸고, 그렇지 않으면 이유와 함께 판정을 유지합니다. 합의 자체를 위해 판정을 바꾸지 않습니다.

## 응답 형식

한국어로, 아래 형식을 그대로 씁니다. 첫 줄은 반드시 `판정:`으로 시작합니다.

```
판정: 드리프트 있음 | 없음 | 부분
재구성한 의도: 최초 의도(U번호) + 사용자 결정 목록(D1.. 각 U번호)
항목별 대조: AI의 현재 행동/계획 → 근거 U번호 있음/없음 → 허용/드리프트
드리프트 목록: 무엇이 · 언제부터(추정) · 사용자 의도와의 차이
멈출 것 / 되돌릴 후보: (제안만)
사용자에게 물을 한 가지: 판정을 바꿀 수 있는 가장 중요한 미결 사항
```
````

`skills/intent-anchor/SKILL.md`:

````markdown
---
name: intent-anchor
description: "Use when the user explicitly invokes /wrxp:intent-anchor ($wrxp:intent-anchor in Codex). Also use, rarely, when the user strongly corrects the direction of the work itself (for example \"that's not what I meant\", \"you missed my point\", \"이해 못했네\", \"원래 의도는\", \"산으로 간다\") or when the same goal keeps being retried through repeated rewrites or versions. Compares the current work against every raw user message with a fresh-context top model, then stops and asks before changing course. Not for ordinary bug reports, typo fixes, direction changes the user made themselves, or one or two retries."
---

# Intent anchor

작업이 사용자의 원래 의도에서 벗어났는지(드리프트)를 사용자 발화 원문을 기준으로, 이 작업에 참여하지 않은 최고 수준 모델과 대조한다. 벗어났으면 작업을 멈추고 사용자에게 묻는다. 방향 변화의 근거가 사용자 발화에 있으면 원래 요청과 멀어 보여도 정상적인 진화로 본다.

## 언제 실행하는가

- 사용자가 명시적으로 호출하면 실행한다.
- 자동 실행은 드물게 한다. 다음 중 하나가 분명할 때만 실행한다.
  - 사용자가 작업 방향 자체를 바로잡는다. 단순 버그·오타·표현 지적은 해당하지 않는다.
  - 같은 목표에 수정·재시도가 계속 쌓여, 수단이 목적을 대체했을 가능성이 있다. 예를 들어 같은 산출물의 버전이 거듭 늘어나는 경우다. 한두 번의 재시도는 해당하지 않는다.
- 자동으로 실행할 때는 첫 줄에 어떤 신호였는지 밝히고, 진행 중인 작업을 멈춘 상태로 둔다.
- 이 스킬을 다른 스킬의 선행 조건이나 훅에 연결하지 않는다.

## 절차

1. **기록 폴더를 정한다.** 프로젝트 폴더의 `handoffs/realign/<YYYY-MM-DD>-<작업-슬러그>/`를 쓴다. 프로젝트 폴더가 연결된 git worktree 안이면(`git rev-parse --git-dir`와 `--git-common-dir`의 결과가 다르고 submodule이 아닌 경우) 주 체크아웃의 루트(`git rev-parse --path-format=absolute --git-common-dir`의 상위 디렉터리)를 쓴다. 같은 이름이 있으면 `-2`, `-3`을 붙인다. `.gitignore`와 커밋 여부는 바꾸지 않는다.
2. **`ai-state.md`를 쓴다.** 기록 폴더에 다음을 쓴다. 각 항목에는 근거(파일 경로, 명령, 커밋)를 붙인다.
   - 메인이 이해한 현재 목표
   - 지금 하는 일과 다음 계획
   - 최근의 방향 전환과 그 계기

   사용자 의도는 이 파일에 쓰지 않는다. 사용자 발화는 스크립트가 원문 전부를 붙이며, 메인이 요약하거나 골라서 넣지 않는다.
3. **리뷰어를 실행한다.** 스크립트는 이 스킬의 기본 디렉터리(스킬을 불러올 때 표시되는 경로) 아래에 있다. 절대 경로로 실행한다.

   ```bash
   python3 "<skill-dir>/scripts/run_reviewer.py" --state "<폴더>/ai-state.md" --out "<폴더>" --round 1
   ```

   - 현재 세션은 자동으로 찾는다. 다른 세션은 `--session-id` 또는 `--log`로 지정한다.
   - 사용자 발화에 경로가 없는 이전 핸드오프를 알고 있으면 `--handoff <경로>`로 추가한다.
   - 메인 런타임을 알 수 없다는 오류가 나오면 `--main-runtime claude|codex`를 지정한다.
   - 리뷰어는 반대 계열의 최고 모델을 우선하고(Claude 메인이면 Codex Astra, Codex 메인이면 Claude Opus), 실패하면 다음 순위로 내려간다. effort는 high, 권한은 읽기 전용이다.

   종료 코드에 따라 다음과 같이 처리한다.
   - `0`: `round-N/response.md`를 읽는다.
   - `3`(원문 미확인): 대화 기억으로 대신하지 않는다. 사용자에게 세션 로그 경로를 한 번 묻는다.
   - `4`(모든 리뷰어 실패): `round-N/request.md`를 읽고 메인이 직접 대조한다. 보고에 "자기 검토, 교차 검증 아님"을 밝힌다.
   - `2`: 출력된 사용 오류를 고친다. 기존 회차 기록은 덮어쓰지 않는다.
4. **판정을 검토한다.** 판정에 동의하면 5단계로 간다. U번호나 파일 근거로 반박할 수 있을 때만 `<폴더>/rebuttal-N.md`를 쓰고 `--round N --rebuttal <파일>`로 다음 회차를 실행한다. 토론은 최대 3회다. 판정이 불리하다는 이유만으로 반박하지 않으며, 근거 없는 반박("제 판단으로는")은 쓰지 않는다.
5. **보고한다.**
   - **드리프트 있음·부분:** 작업을 멈추고 다음을 짧게 보고한 뒤 질문 하나를 한다. 선택지 도구가 있으면 사용한다. 경로 수정과 되돌리기(코드 롤백, 외부 변경 취소)는 사용자 답을 받은 뒤에만 한다.
     - 원래 의도: 원문을 인용한 두세 줄(U번호)
     - 벗어난 지점: 한두 개 항목과 근거
     - 멈춘 작업 / 되돌릴 후보
     - 질문 하나
   - **드리프트 없음:** 재확인한 최종 의도와 현재 작업의 연결을 몇 줄로 보고하고, 멈춘 작업을 이어 간다.
   - **3회 안에 합의하지 못함:** 양쪽 입장과 근거를 나란히 보여 주고 질문 하나를 한다.

   모든 보고에는 리뷰어의 실제 모델(`invocation.json`의 `selected`), 폴백 이력, 회차, 기록 폴더 경로를 적는다.

## 원칙

- 사용자 발화 원문이 기준이다. AI가 쓴 요약·기획·핸드오프 §2는 원문으로 확인되기 전에는 사실로 쓰지 않는다.
- 리뷰어의 결론은 권고다. 사용자의 결정을 대신하지 않는다.
- 모델을 몰래 바꾸지 않는다. 폴백했으면 보고에 밝힌다.
- 비밀값은 기록하지 않는다. 스크립트는 비밀 키 이름 뒤의 값을 가리지만, `ai-state.md`와 반박에도 값을 쓰지 않는다.
````

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `python3 -m pytest -q tests/test_wrxp_invariants.py -k intent_anchor && python3 -m pytest -q tests`
Expected: PASS. 전체 테스트가 통과한다. `test_setup_global.py`는 스킬 목록을 동적으로 읽으므로 영향이 없어야 한다. 실패하면 그 출력을 기록하고 원인을 고친다.

- [ ] **Step 5: 커밋**

```bash
git add skills/intent-anchor tests/test_wrxp_invariants.py
git commit -m "feat(wrxp): add the intent-anchor skill and reviewer prompt

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 배포 정보 (버전, CHANGELOG, README, setup 규칙)

**Files:**
- Modify: `.claude-plugin/plugin.json`, `package.json`, `../.claude-plugin/marketplace.json` (`"version": "0.1.38"` → `"0.1.39"`, wrxp 항목만)
- Modify: `tests/test_wrxp_invariants.py` (`test_release_versions_match`의 `{"0.1.38"}` → `{"0.1.39"}`)
- Modify: `CHANGELOG.md`, `README.md`, `skills/setup/assets/global-rules.md`

- [ ] **Step 1: 버전 테스트를 먼저 바꾸고 실패 확인**

`tests/test_wrxp_invariants.py`에서 `{"0.1.38"},`를 `{"0.1.39"},`로 바꾼다.

Run: `python3 -m pytest -q tests/test_wrxp_invariants.py -k release_versions`
Expected: FAIL (`{'0.1.39'} != {'0.1.38'}`)

- [ ] **Step 2: 버전 파일 3개 갱신**

`wrxp/.claude-plugin/plugin.json`, `wrxp/package.json`, 저장소 루트의 `.claude-plugin/marketplace.json`(wrxp 항목)에서 `"version": "0.1.38"`을 `"version": "0.1.39"`로 바꾼다. marketplace의 middleware 항목(`1.7.0`)은 건드리지 않는다.

- [ ] **Step 3: CHANGELOG, README, setup 규칙 갱신**

`CHANGELOG.md`에서 `## [0.1.38] - 2026-09-28` 위에 추가한다.

```markdown
## [0.1.39] - 2026-09-30

- `intent-anchor` 스킬을 추가했습니다. 작업이 사용자의 원래 의도에서 벗어났는지, 세션 로그에서 추출한 사용자 발화 전부와 이전 핸드오프의 원문 인용을 기준으로 이 작업에 참여하지 않은 최고 수준 모델과 대조합니다.
- 두 계정이 모두 있으면 반대 계열(Claude 메인이면 Codex Astra, Codex 메인이면 Claude Opus), 한 계열만 있으면 그 계열 최고 모델을 새 맥락으로 씁니다. effort는 high, 권한은 읽기 전용이며 실제 모델·폴백 이력을 기록합니다.
- 명시 호출과 드문 자동 실행(방향 자체를 바로잡는 정정, 같은 목표의 반복 재시도)을 지원합니다. 드리프트가 확인되면 작업을 멈추고 질문 하나를 하며, 경로 수정은 사용자 답을 받은 뒤에만 합니다.
- `handoff`의 사용자 발화 추출기를 `shared/scripts/user_turns.py`로 옮겨 두 스킬이 공유합니다. 기존 `handoff` 경로와 동작은 유지됩니다.
```

`README.md` 28행에서 `세션 인계의 \`handoff\`,` 뒤에 ` 의도 대조의 \`intent-anchor\`,`를 넣고 `총 18개 skill.`을 `총 19개 skill.`로 바꾼다.

`README.md`의 handoff 절(`자세한 구조는 [handoff 스킬](./skills/handoff/SKILL.md)에 있다.`로 끝나는 문단) 바로 뒤에 추가한다.

```markdown

`/wrxp:intent-anchor`(Codex에서는 `$wrxp:intent-anchor`)는 작업이 사용자의 원래 의도에서 벗어났는지 사용자 발화 원문 전부를 기준으로 다른 맥락의 최고 수준 모델과 대조한다. 사용자가 작업 방향 자체를 바로잡거나 같은 목표의 재시도가 계속 쌓일 때는 드물게 자동으로 실행된다. 방향 변화의 근거가 사용자 발화에 있으면 허용하고, 벗어났으면 작업을 멈춘 뒤 질문 하나를 한다. 리뷰어는 읽기 전용으로 실행되며 기록은 프로젝트 폴더의 `handoffs/realign/`에 남는다. 자세한 절차는 [intent-anchor 스킬](./skills/intent-anchor/SKILL.md)에 있다.
```

`skills/setup/assets/global-rules.md`에서 `- Session transfer:` 줄 바로 뒤에 추가한다.

```markdown
- Intent drift: use `wrxp:intent-anchor` when explicitly invoked, or rarely when the user strongly corrects the direction of the work or the same goal keeps being retried; it compares the work against the user's raw messages with a fresh-context top model, then stops and asks before changing course.
```

- [ ] **Step 4: 전체 검사**

Run: `python3 -m pytest -q tests`
Expected: 전체 통과. `test_setup_global.py`가 규칙 줄 수나 내용을 고정하고 있어 실패하면, 그 테스트의 기대값을 이 한 줄에 맞게 갱신하고 이유를 커밋 메시지에 적는다.

Run: `python3 skills/setup/scripts/setup_global.py --target both`
Expected: 읽기 전용 미리보기에 `intent-anchor` 줄이 포함된다. `--apply`는 실행하지 않는다(전역 파일 반영은 사용자가 따로 요청할 때만 한다).

- [ ] **Step 5: 커밋**

```bash
git add .claude-plugin/plugin.json package.json ../.claude-plugin/marketplace.json CHANGELOG.md README.md skills/setup/assets/global-rules.md tests/test_wrxp_invariants.py
git commit -m "feat(wrxp): release v0.1.39 with intent-anchor

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 실제 세션 재생으로 효과 검증

실제 모델을 호출한다. 각 실행에 수 분이 걸리며, 결과는 모델 응답에 따라 달라진다. 재생 폴더는 세션 scratchpad에 두고, 저장소에는 요지만 기록한다.

**Files:**
- Create: `docs/benchmark/intent-anchor-0.1.39.md`

- [ ] **Step 1: 드리프트 세션의 재생 지점 찾기**

```bash
DRIFT=~/.codex/sessions/2026/09/27/rollout-2026-09-27T12-40-37-01a0e0f3-51b9-7203-a976-4c1cb32bfad2.jsonl
python3 shared/scripts/user_turns.py --log "$DRIFT" --max-chars 300 \
  | awk '/^## U/{u=$2} /말투보니까/{print u; exit}'
```

Expected: `U<번호>` 한 줄. 이 번호를 `DRIFT_U`로 둔다(예: `U57`이면 57).

- [ ] **Step 2: 재생 시점의 AI 상태 만들기**

재생 지점 직전의 마지막 AI 응답을 `ai-state.md`로 쓴다. 두 로그 형식을 모두 처리하는 아래 스크립트를 `$SCRATCH/last_assistant.py`로 저장한다(`$SCRATCH`는 세션 scratchpad 경로).

```python
import json, sys
from pathlib import Path

log, marker = Path(sys.argv[1]), sys.argv[2]
last = ""
for line in log.open(encoding="utf-8"):
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    p = r.get("payload") or {}
    if r.get("type") == "response_item" and p.get("type") == "message":
        texts = [c.get("text", "") for c in p.get("content", []) if isinstance(c, dict)]
        if p.get("role") == "assistant" and any(texts):
            last = "\n".join(texts)
        elif p.get("role") == "user" and any(marker in t for t in texts):
            break
    elif r.get("type") == "assistant":
        blocks = r.get("message", {}).get("content") or []
        texts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
        if any(texts):
            last = "\n".join(texts)
    elif r.get("type") == "user":
        content = r.get("message", {}).get("content")
        if isinstance(content, str) and marker in content:
            break
print("# 메인의 현재 상태 (재생: 원 세션에서 사용자 반응 직전의 마지막 AI 응답)\n")
print(last)
```

```bash
mkdir -p "$SCRATCH/replay-drift"
python3 "$SCRATCH/last_assistant.py" "$DRIFT" "말투보니까" > "$SCRATCH/replay-drift/ai-state.md"
head -20 "$SCRATCH/replay-drift/ai-state.md"
```

Expected: 사용자 반응 직전의 AI 보고 앞부분이 출력된다. 비어 있으면 marker 탐색이 실패한 것이므로 Step 1 출력으로 해당 발화의 정확한 문구를 확인해 marker를 바꾼다.

- [ ] **Step 3: 드리프트 세션 재생 실행 (원래 메인이 Codex였으므로 리뷰어는 Claude Opus)**

```bash
python3 skills/intent-anchor/scripts/run_reviewer.py \
  --log "$DRIFT" --until-turn "$DRIFT_U" --no-repo-state --main-runtime codex \
  --project /Users/donny2/worxsales-architect/.worktrees/corpus-core-v02 \
  --state "$SCRATCH/replay-drift/ai-state.md" --out "$SCRATCH/replay-drift" --round 1
```

Expected: 종료 코드 0, 첫 줄 `판정: 드리프트 있음` 또는 `판정: 부분`.
통과 조건: `round-1/response.md`의 드리프트 목록이 "수단(문서 생성·검증·발행)이 목적(제품 이해와 설명 부담을 AI에 맡기는 것)을 대체했다"는 요지를 담는다. `invocation.json`의 `selected.actual_model`이 Opus 계열이다.

- [ ] **Step 4: 드리프트가 없는 세션 재생 (원래 메인이 Claude였으므로 리뷰어는 Codex Astra)**

```bash
CLEAN=~/.claude/projects/-Users-donny2/35f34c11-8d41-40ae-a7cd-d957f6d4d835.jsonl
python3 shared/scripts/user_turns.py --log "$CLEAN" --max-chars 200 \
  | awk '/^## U/{u=$2} /승인, 계획서 작성/{print u; exit}'
```

출력된 번호에 1을 더한 값을 `CLEAN_U`로 둔다(승인 답까지 포함). 이후 실행한다.

```bash
mkdir -p "$SCRATCH/replay-clean"
python3 "$SCRATCH/last_assistant.py" "$CLEAN" "승인, 계획서 작성" > "$SCRATCH/replay-clean/ai-state.md"
python3 skills/intent-anchor/scripts/run_reviewer.py \
  --log "$CLEAN" --until-turn "$CLEAN_U" --no-repo-state --main-runtime claude \
  --project /Users/donny2/project/claude-middleware \
  --state "$SCRATCH/replay-clean/ai-state.md" --out "$SCRATCH/replay-clean" --round 1
```

Expected: 종료 코드 0, 첫 줄 `판정: 없음`. `selected.actual_model`이 `gpt-6-astra`다.
참고: `CLAUDE_CODE_SESSION_ID` 로그의 `last_assistant.py` 탐색은 질문 도구 답(`tool_result`)을 marker로 찾지 못할 수 있다. 이 경우 marker를 그 직전 사용자 발화의 문구(예: 스펙 검토 질문에 앞선 "ㅇㅋ")로 바꾸고, 바꾼 사실을 기록한다.

- [ ] **Step 5: 결과 기록**

`docs/benchmark/intent-anchor-0.1.39.md`를 만든다. 대화 원문은 넣지 않고 아래 구조에 **실제 실행 값**을 채운다.

```markdown
# intent-anchor 0.1.39 재생 검증

실행: 2026-09-30 · 실행 스크립트: skills/intent-anchor/scripts/run_reviewer.py

| 사례 | 메인(원 세션) | 리뷰어 실제 모델 | 시도 | 판정 | 핵심을 잡았는가 | 소요(초) | 패킷(바이트, 발화 수, 줄인 발화 수) |
|---|---|---|---|---|---|---|---|
| 드리프트 있던 세션 (사용자 지적 직전까지) | codex | (invocation.json selected.actual_model) | (attempts 요약) | (response.md 첫 줄) | 예/아니오 + 한 줄 요지 | (attempts[-1].seconds) | (packet.bytes, user_turns, len(truncated_turns)) |
| 드리프트 없던 세션 (설계 승인까지) | claude | … | … | … | 오탐 여부 | … | … |

## 관찰

- 리뷰어가 짚은 드리프트의 요지와 사용자가 실제로 지적한 요지의 비교(각 2~3문장, 원문 인용 없이).
- 실패·재실행이 있었다면 원인, 바꾼 지시문, 재실행 결과.

## 한계

- 재생은 저장소 상태를 제외했다(`--no-repo-state`). 실제 사용 시에는 git 상태가 함께 전달된다.
- 두 사례만으로 오탐·미탐 비율을 말할 수 없다. 자동 실행 빈도는 배포 후 `handoffs/realign/` 건수로 확인한다.
```

- [ ] **Step 6: 실패 시 처리**

어느 사례든 통과 조건을 만족하지 않으면 `references/reviewer-prompt.md`의 판정 기준을 고치고, 새 폴더(`replay-drift-2` 등)로 다시 실행한다. 기존 회차 기록은 덮어쓰지 않는다. 고친 내용과 재실행 결과를 Step 5 문서의 "관찰"에 남긴다. 두 번 고쳐도 통과하지 않으면 멈추고 사용자에게 결과를 보고한다.

- [ ] **Step 7: 커밋**

```bash
git add docs/benchmark/intent-anchor-0.1.39.md skills/intent-anchor/references/reviewer-prompt.md
git commit -m "docs(wrxp): record intent-anchor replay verification

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 완료 조건

- `python3 -m pytest -q tests` 전체 통과(기준선 87개 + 신규)
- Task 7의 두 재생이 통과 조건을 만족하고, 결과가 `docs/benchmark/intent-anchor-0.1.39.md`에 기록됨
- 변경 파일에 `TODO`, `TBD`, `test.skip`, `.only`가 없음(`rg -n "TODO|TBD|\.skip\(|\.only\(" skills/intent-anchor shared tests/test_intent_anchor.py`)
- 전역 지침 파일은 수정하지 않음(setup `--apply` 미실행)
