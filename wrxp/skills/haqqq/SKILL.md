---
name: haqqq
description: Use when a high-risk or hard-to-reverse single-path request may need deep clarification before execution.
argument-hint: "[요청 내용]"
level: 4
---

# /haqqq — Deep Question Preset

`/haqqq`는 `/ha` 공통 엔진에 심층 질문 프리셋만 전달하는 thin shim이다. 질문 정책, 모델 라우팅, 실행과 검증을 재정의하지 않는다.

모든 사용자 대상 출력은 한국어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

## Requirements

$ARGUMENTS

## Preset

```yaml
question_preset: deep
min_questions: 0
max_questions: 12
max_questions_per_round: 4
max_rounds: 3
extended_max_questions: 20
extended_max_rounds: 5
extension_requires_user_consent: true
```

12개와 3라운드는 기본 상한이며 라운드당 최대 4개만 묻는다. 적격 질문이 없으면 0개로 실행한다. 기본 상한 이후에도 사용자만 결정할 수 있는 고위험 항목이 남으면 계속 질문할지 먼저 확인한다. 사용자가 동의한 경우에만 실질적인 질문을 최대 5라운드까지 진행하고, 사용자에게 제시한 모든 질문을 합쳐 최대 20개까지 확장한다. 확장 동의 질문도 총 질문 수에 포함한다. 동의가 없거나 절대 상한에 도달하면 위험한 기본값으로 진행하지 않고 blocker를 보고한다.

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
🎚️ Tier: haqqq · deep · 질문 0~12개/3라운드 · 동의 시 절대 상한 20개/5라운드
🗡️ 실행: runtime-bounded task graph
```
