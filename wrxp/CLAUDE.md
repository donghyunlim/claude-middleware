# wrxp — Routing Rules (auto-loaded)

Claude Code 가 본 plugin 설치 세션에서 이 파일을 자동으로 read (OMC 동일 메커니즘 — plugin 경로의 CLAUDE.md 는 session start 시 system prompt 에 injection).

## `fast-worker` subagent 로 위임해야 할 때

Claude 는 다음 중 하나라도 해당하면 `Agent(subagent_type="wrxp:fast-worker", ...)` 를 적극 검토:

- 파일 / stdout / 붙여넣은 payload 가 **~3KB 이상**
- 같은 파일을 이 세션에서 **2회 이상 Read** 할 예정 (반복 참조)
- **N ≥ 5** 항목 bulk classification / labeling / transformation
- **JSON object / enum / N-item list** 처럼 **구조화된 output** 이 필요
- 로그 / stacktrace / 긴 문서 요약 / diff 리뷰 / second-opinion

`fast-worker` 는 로컬 Qwen3.6 (무과금, ~82 tok/s, 262K context, llama.cpp grammar 로 JSON·enum·schema 서버 레벨 강제) 을 호출. **Qwen 서버가 unreachable 이면 자동으로 haiku fallback**. 호출자는 서버 상태를 몰라도 동일 UX.

## Claude 직접 유지할 상황

- Write / Edit / MultiEdit / NotebookEdit 파일 편집 (fast-worker 는 Bash + Read 만)
- 정답 하나이고 정확도 critical (법률 · 의료 · 금융)
- 실시간 state (현재 시간 · git branch 같은 내장 tool 결과로 충분)
- 1-2 문장 Q&A (왕복 오버헤드 > context 절약)

## fast-worker 빠른 호출 예

```
Agent(subagent_type="wrxp:fast-worker",
      description="long-ctx 요약",
      prompt=\"\"\"
      Bash: cat README.md | ~/.claude/scripts/qwen.py --fast --json -m 800
        'Return JSON {tldr, bullets:5, risks:3}. Output ONLY the object.'
      stdout 그대로 반환.
      \"\"\")
```

사용자가 fast-worker 의 내부 (qwen.py 옵션 · fallback) 를 몰라도 Claude 가 자동 라우팅.

## 실행 전제

- `~/.claude/scripts/qwen.py` 존재 (plugin 의 `scripts/qwen.py` 를 symlink 로 올려도 OK)
  - `ln -sf ~/.claude/plugins/cache/donghyunlim/wrxp/*/scripts/qwen.py ~/.claude/scripts/qwen.py`
- `~/.claude/scripts/.env` 에 `QWEN_API_KEY=...` (없으면 qwen.py 내장 DEFAULT_API_KEY 사용)
- Qwen 서버 접근 가능 (`QWEN_ENDPOINT` 환경 변수로 override 가능). 접근 불가해도 haiku fallback 으로 동작.
