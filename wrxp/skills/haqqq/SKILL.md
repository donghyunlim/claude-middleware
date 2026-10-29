---
name: haqqq
description: Use when a high-risk or hard-to-reverse single-path request may need deep clarification before execution.
argument-hint: "[요청 내용]"
level: 4
---

# /haqqq — Deep Question Preset

`/haqqq`는 `/ha` 공통 엔진에 심층 질문 프리셋만 전달하는 thin shim이다. 질문 정책, 모델 라우팅, 실행과 검증을 재정의하지 않는다.

사용자 대상 출력은 사용자가 쓴 언어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

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

기본 상한은 `max_questions`·`max_rounds`이며 적격 질문이 없으면 0개로 실행한다. 사용자 동의를 받아 `extended_*`까지 넓히는 규칙은 `../ha/references/questioning.md`에 있다.

## 질문 판정 (필수)

- 실행 의도를 확정하거나 파일·외부 시스템에 쓰기 전에 `../ha/SKILL.md` 3절 QUESTION_GATE 판정(3조건, `must_ask`·`decision_quality`·`skip` 분류, `ask`·`pass_zero`·`blocked`)을 반드시 마친다. 평가를 건너뛴 0문항은 `pass_zero`가 아니다.
- 이 tier를 부른 것 자체가 명확화 요청이므로, 런타임이 가정을 선호하도록 안내해도 `must_ask`와 예산 안의 `decision_quality` 질문이 우선한다. 사용자가 질문 중단을 밝힌 경우만 예외다.

## Common Engine Invocation

위 preset을 원본 요청 앞에 붙여 `/ha`를 호출한다. Skill 도구가 있는 런타임(Claude Code)에서는 파일을 직접 읽지 말고 Skill 도구로 `wrxp:ha`를 부른다. 다른 스킬 폴더의 파일 읽기는 권한 확인에 막힐 수 있다.

중첩 skill 호출을 지원하지 않는 런타임에서는 `../ha/SKILL.md`를 끝까지 읽고 같은 preset으로 직접 실행한다. 참조 파일은 `/ha`와 똑같이 그 파일이 정한 시점에만 읽는다. 질문할 때 `../ha/references/questioning.md`, 하위 에이전트 모델을 정할 때 `../ha/references/model-routing.md`, 무거운 경로에 들어갈 때 `../ha/references/tracks.md`와 `../ha/references/verification.md`를 읽는다.

shim은 task-type 질문 목록, 모델명, 실행자 역할 또는 검증 규칙을 추가하지 않는다.

## Header

```text
🎚️ Tier: haqqq · deep · 질문 0~12개/3라운드 · 동의 시 절대 상한 20개/5라운드
🗡️ 실행: runtime-bounded task graph
```
