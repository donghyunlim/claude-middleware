# wrxp — Routing Rules

이 문서는 설치·운영 참고 문서다. 플러그인 루트의 `CLAUDE.md`가 모든 세션에 자동 주입된다고 가정하지 않는다. 자동 라우팅의 신호는 `agents/fast-worker.md`의 agent metadata와 description이며, 호출자는 해당 에이전트를 명시적으로 선택한다.

## `fast-worker` subagent 로 위임해야 할 때

Claude 는 다음 중 하나라도 해당하면 `Agent(subagent_type="wrxp:fast-worker", ...)` 를 적극 검토:

- 파일 / stdout / 붙여넣은 payload 가 **~1K tokens 이상** (대략 3KB+)
- **N ≥ 5** 항목 bulk classification / labeling / transformation
- **JSON object / enum / N-item list** 처럼 **구조화된 output** 이 필요
- 로그 / stacktrace / 긴 문서 요약

`fast-worker`는 로컬 Qwen3.6(무과금, ~82 tok/s, 262K context, llama.cpp grammar로 JSON·enum·schema 서버 레벨 강제)을 호출한다. 실패 사유가 **`Qwen unavailable or invalid response`로 분류되면 자동으로 Haiku fallback**한다. 호출자는 서버 장애·응답 형식 장애를 구분하지 않아도 동일한 UX를 얻는다.

## Claude 직접 유지할 상황

- 새 파일 생성, 다중 파일 편집, 로직 판단이 필요한 파일 편집
- code review / diff review / second-opinion처럼 판단이 필요한 작업
- 정답 하나이고 정확도 critical (법률 · 의료 · 금융)
- 실시간 state (현재 시간 · git branch 같은 내장 tool 결과로 충분)
- 1-2 문장 Q&A (왕복 오버헤드 > context 절약)

## fast-worker 빠른 호출 예

```text
Agent(subagent_type="wrxp:fast-worker",
      description="long-ctx 요약",
      prompt="""
      Bash: cat README.md | ~/.claude/scripts/qwen.py --fast --json -m 800
        'Return JSON {tldr, bullets:5, risks:3}. Output ONLY the object.'
      stdout 그대로 반환.
      """)
```

## 실행 전제

- `~/.claude/scripts/qwen.py` 존재 (plugin 의 `scripts/qwen.py` 를 symlink 로 올려도 OK)
- `QWEN_API_KEY` 또는 `QWEN_TOKEN`은 plugin 또는 사용자 환경에 설정할 수 있다.
- Qwen을 사용할 수 없거나 응답 형식이 잘못돼도 Haiku fallback으로 동작한다.
