---
name: haqq
description: Use when a single-path request may need a standard discovery pass across several material user-owned decisions.
argument-hint: "[요청 내용]"
level: 4
---

# /haqq — Standard Question Preset

`/haqq`는 `/ha` 공통 엔진에 표준 질문 프리셋만 전달하는 thin shim이다. 질문 정책, 모델 라우팅, 실행과 검증을 재정의하지 않는다.

사용자 대상 출력은 사용자가 쓴 언어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

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
```

이 값은 질문 수의 상한이다. 첫 라운드 뒤 적격 질문을 다시 계산하며, 남은 질문이 없으면 즉시 실행한다.

## 질문 판정 (필수)

- 실행 의도를 확정하거나 파일·외부 시스템에 쓰기 전에 `../ha/SKILL.md` 3절 QUESTION_GATE 판정(3조건, `must_ask`·`decision_quality`·`skip` 분류, `ask`·`pass_zero`·`blocked`)을 반드시 마친다. 평가를 건너뛴 0문항은 `pass_zero`가 아니다.
- 이 tier를 부른 것 자체가 명확화 요청이므로, 런타임이 가정을 선호하도록 안내해도 `must_ask`와 예산 안의 `decision_quality` 질문이 우선한다. 사용자가 질문 중단을 밝힌 경우만 예외다.

## Common Engine Invocation

위 preset을 원본 요청 앞에 붙여 `/ha`를 호출한다.

중첩 skill 호출을 지원하지 않는 런타임에서는 `../ha/SKILL.md`를 끝까지 읽고 같은 preset으로 직접 실행한다. 참조 파일은 `/ha`와 똑같이 그 파일이 정한 시점에만 읽는다. 질문할 때 `../ha/references/questioning.md`, 하위 에이전트 모델을 정할 때 `../ha/references/model-routing.md`, 무거운 경로에 들어갈 때 `../ha/references/tracks.md`와 `../ha/references/verification.md`를 읽는다.

shim은 task-type 질문 목록, 모델명, 실행자 역할 또는 검증 규칙을 추가하지 않는다.

## Header

```text
🎚️ Tier: haqq · standard · 질문 0~8개 · 최대 2라운드
🗡️ 실행: runtime-bounded task graph
```
