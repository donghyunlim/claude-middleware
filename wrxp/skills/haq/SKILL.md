---
name: haq
description: Use when a single-path request has a few potentially material user-owned decisions and should start quickly.
argument-hint: "[요청 내용]"
level: 4
---

# /haq — Quick Question Preset

`/haq`는 `/ha` 공통 엔진에 빠른 질문 프리셋만 전달하는 thin shim이다. 질문 정책, 모델 라우팅, 실행과 검증을 재정의하지 않는다.

모든 사용자 대상 출력은 한국어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

## Requirements

$ARGUMENTS

## Preset

```yaml
question_preset: quick
min_questions: 0
max_questions: 4
max_questions_per_round: 4
max_rounds: 1
extended_max_questions: null
extended_max_rounds: null
extension_requires_user_consent: false
```

이 값은 질문 수의 상한이다. 적격 질문이 없으면 질문 0개로 바로 실행한다.

## QuestionGate 계약 (필수)

읽기 전용 탐색은 판정 전에도 허용한다. 그러나 실행 의도를 확정하거나 파일·외부 시스템에 쓰기 전에는 반드시 아래 판정을 마친다. 이 판정을 생략한 채 실행하지 않는다.

다음 세 조건을 모두 만족하는 결정만 질문 후보다.

1. `unresolved`: 관찰과 증거 확인을 마친 뒤에도 결정이 남아 있다.
2. `answer_owner == user`: 사용자만 답할 수 있다. 승인, 비공개 조직 정책, 의도, 개인 선호가 여기에 해당한다.
3. `materially_branching`: 답에 따라 실행 경로가 실제로 달라진다.

후보는 다음 세 가지로 분류한다.

- `must_ask`: 승인·보안·비밀·권한·외부 변경·파괴적·불가역 경계이며 안전한 기본값이 없다. 질문 예산과 무관하게 즉시 묻는다.
- `decision_quality`: 답이 산출물의 독자, 사용 목적, 공유·공개 범위, 결정의 상태·권한, 참석자 또는 수용 기준을 바꾼다. 되돌릴 수 있는 기본값이 있어도 후보에서 제외하지 않는다. 새 문서, 회의 자료, 메시지 또는 결정 기록을 만들면서 그 쓰임이 요청에 명시되어 있지 않다면 기본적으로 이 분류에 해당한다.
- `skip`: 증거로 확인할 수 있거나, 모든 답이 같은 실행으로 이어지거나, 차이가 표현·형식뿐이다.

분류를 마치면 판정을 하나 남긴다.

```yaml
QuestionGateVerdict:
  verdict: ask | pass_zero | blocked
  eligible_candidates: integer
  basis: string
```

- `ask`: 적격 후보가 있다. 이 파일의 참조 목록에 있는 `questioning.md`를 끝까지 읽고, 프리셋 예산과 배치 공식에 따라 질문을 작성한다. 참조를 읽을 수 없으면 한 라운드 최대 4개 상한만 적용하되, 구조화 질문 도구를 쓸 수 없는 런타임에서는 선택지를 텍스트로 나열해 선택형을 흉내 내지 말고 우선순위가 가장 높은 질문 하나만 평문으로 묻는다. 질문 예산이 0인 `/ha` 직접 호출에서는 `must_ask`만 묻고, `decision_quality`는 안전한 기본값을 `assumptions`에 기록하거나 기본값이 없으면 `blocked`로 전환한다.
- `pass_zero`: 적격 후보가 없다. 적용한 기본값을 `assumptions`에 기록하고 실행한다.
- `blocked`: 안전한 기본값이 없는 후보가 남았는데 물을 수 없다. 실행하지 않고 남은 결정을 보고한다.

`pass_zero`는 후보를 실제로 평가한 결과가 0개일 때만 유효하다. 평가를 건너뛴 상태는 `pass_zero`가 아니다. 질문 수는 상한이며 할당량이 아니므로, 평가를 마친 0문항은 모든 프리셋에서 정상이다.

질문 tier 스킬을 호출한 것 자체가 명확화를 요청하는 명시적 사용자 지시다. 런타임 기본 설정이 질문보다 가정을 선호하도록 안내하더라도, 이 계약이 정한 `must_ask`와 예산 안의 `decision_quality` 질문은 그 기본 선호보다 우선한다. 사용자가 이 대화에서 질문 중단을 밝힌 경우에만 그 지시를 따른다.

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
🎚️ Tier: haq · quick · 질문 0~4개 · 최대 1라운드
🗡️ 실행: runtime-bounded task graph
```
