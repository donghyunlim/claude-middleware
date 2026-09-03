---
name: haqq
description: Use when a single-path request may need a standard discovery pass across several material user-owned decisions.
argument-hint: "[요청 내용]"
level: 4
---

# /haqq — Standard Question Preset

`/haqq`는 `/ha` 공통 엔진에 표준 질문 프리셋만 전달하는 thin shim이다. 질문 정책, 모델 라우팅, 실행과 검증을 재정의하지 않는다.

모든 사용자 대상 출력은 한국어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

## Requirements

$ARGUMENTS

## Preset

```yaml
question_preset: standard
min_questions: 0
max_questions: 8
max_questions_per_round: 4
max_rounds: 2
extended_max_questions: null
extended_max_rounds: null
extension_requires_user_consent: false
execution_mode: serial
max_concurrency: 1
```

이 값은 질문 수의 상한이다. 첫 라운드 뒤 적격 질문을 다시 계산하며, 남은 질문이 없으면 즉시 실행한다.

## Common Engine Invocation

위 preset을 원본 요청 앞에 붙여 `/ha`를 호출한다.

중첩 skill 호출을 지원하지 않는 런타임에서는 다음 파일을 끝까지 읽고 같은 preset으로 직접 실행한다.

1. `../ha/SKILL.md`
2. `../ha/references/questioning.md`
3. `../ha/references/model-routing.md`
4. `../ha/references/verification.md`

shim은 task-type 질문 목록, 모델명, 실행자 역할 또는 검증 규칙을 추가하지 않는다.

## Header

```text
🎚️ Tier: haqq · standard · 질문 0~8개 · 최대 2라운드
🗡️ 실행: serial · max_concurrency=1
```
