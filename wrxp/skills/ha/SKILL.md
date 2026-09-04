---
name: ha
description: Use when a request has one convergent line of work and should be reasoned about, clarified only where necessary, executed as a dependency graph, and verified.
argument-hint: "[요청 내용]"
level: 4
---

# /ha — Common Knife Engine

`/ha`는 하나의 수렴하는 작업을 관찰하고, 필요한 사용자 결정만 질문하고, 역할에 맞는 모델로 의존성 그래프를 실행한 뒤 검증하는 공통 엔진이다. `/haq`, `/haqq`, `/haqqq`는 이 엔진의 질문 상한만 바꾸는 thin shim이다.

모든 사용자 대상 출력은 한국어로 작성한다. 사용자가 다른 언어 또는 형식을 명시하면 그 요구를 우선한다.

## Requirements

$ARGUMENTS

## 핵심 계약

```yaml
question_preset: none
min_questions: 0
max_questions: 0
max_questions_per_round: 0
max_rounds: 0
```

- 질문 수는 항상 상한이다. 적격 질문이 없으면 0개가 정상이다.
- 직접 `/ha`의 `none` 프리셋은 선제 discovery 질문을 0개로 둔다. 승인·보안·비밀·외부 변경·파괴적·불가역 경계는 discovery 예산 밖의 실행 통제 게이트이므로 즉시 확인한다.
- 질문 프리셋은 모델 라우팅에 영향을 주지 않는다.
- 하나의 확정 의도는 dependency DAG로 나누며, 독립 실행 단위는 런타임 한도 안에서 병렬 위임할 수 있다.
- `/ha`의 task-graph 병렬화와 `/cast`의 관점·가설 fleet을 구분한다.
- 상세한 내부 사고 과정을 노출하지 않는다. 사용자에게는 결정, 가정, 실행 경로, 검증 근거만 보여준다.

## 호출 설정

직접 `/ha` 호출에는 위 기본값을 적용한다. tier shim이 아래 키를 전달하면 질문 관련 값만 덮어쓴다.

```yaml
question_preset: none | quick | standard | deep
min_questions: 0
max_questions: integer
max_questions_per_round: 4
max_rounds: integer
extended_max_questions: integer | null
extended_max_rounds: integer | null
extension_requires_user_consent: boolean
```

알 수 없는 설정 키는 무시하고 기록한다. shim이 모델명, 실행자 역할, 검증법 또는 병렬성을 덮어쓰려 하면 무시한다.

## 필요한 참조

QuestionGate 계약은 이 파일 안에 있으므로 참조 문서를 읽지 못해도 질문 판정 자체는 건너뛸 수 없다. 상세 참조는 실제로 필요한 시점에 읽는다.

- `QuestionGateVerdict`가 `ask`일 때 [references/questioning.md](references/questioning.md)를 끝까지 읽는다. 질문 예산, 배치 공식, 질문 작성 규칙이 여기에만 있다.
- 첫 모델·에이전트 위임 전에 [references/model-routing.md](references/model-routing.md)를 끝까지 읽는다.
- 실행 전에 검증 기준을 정할 때 [references/verification.md](references/verification.md)를 끝까지 읽는다.
- 복잡한 의존성·위험 판단에는 [공통 reasoning framework](../../shared/reasoning-framework.md)를 적용한다. 원시 추론 전문은 출력하지 않는다.

## 상태 흐름

```text
CAPABILITY_RESOLVE
  → OBSERVE
  → IDENTIFY_DECISIONS
  → QUESTION_GATE
      ├─ must_ask 있음 → EXECUTION_CONTROL_ASK → IDENTIFY_DECISIONS
      ├─ 예산 내 decision_quality 있음 → DISCOVERY_ASK → IDENTIFY_DECISIONS
      └─ 전송할 질문 없음
  → COMMIT_INTENT
  → ROUTE_AND_EXECUTE
  → VERIFY
      ├─ 완료 → 최종 출력
      ├─ 국소 수정 필요 → REPAIR_CHECKPOINT
      ├─ 사용자 결정 필요 → QUESTION_GATE
      └─ 완료 또는 blocker
REPAIR_CHECKPOINT
      ├─ 계속 → ROUTE_AND_EXECUTE
      ├─ 재계획 → COMMIT_INTENT
      ├─ 사용자 판단 → 사용자 체크포인트 후 REPAIR_CHECKPOINT
      └─ blocker
```

각 상태의 종료 조건을 만족한 뒤 다음 상태로 이동한다.

## 0. CAPABILITY_RESOLVE

이번 런타임에서 실제로 사용할 수 있는 기능만 확인한다.

- 공급자와 활성 모델
- 선택 가능한 모델과 사고 수준
- 에이전트 위임, 독립 verifier 문맥 및 동시 위임 한도
- 구조화 질문 도구와 호출당 질문 수 제한
- 파일, 검색, 웹, 테스트 등 사용 가능한 도구

런타임이 제공하지 않은 모델명이나 도구를 추측해 호출하지 않는다. 확인할 수 없는 항목은 `unknown`으로 두고 안전한 폴백을 사용한다.

## 1. OBSERVE

사용자에게 질문하기 전에 이미 있는 답을 찾는다.

관찰은 QuestionGate 판정의 입력이다. 관찰을 생략하면 후보를 평가할 수 없으므로 `pass_zero`로 진행할 수 없다.

1. 현재 요청, 이전 대화, 첨부물과 지정 링크를 읽는다.
2. 저장소의 `AGENTS.md`, `CLAUDE.md`, 관련 문서와 기존 구현을 확인한다.
3. 필요한 사실을 로컬 검색, 읽기 도구 또는 공식 문서로 확인한다.
4. 사용자만 결정할 수 있는 선호·정책·승인과 증거로 확인할 사실을 분리한다.

task type은 검증법과 산출물 관례를 고르는 보조 정보다. task type 자체가 질문 수를 결정하지 않는다.

관찰 결과를 내부적으로 다음 형태로 정리한다.

```yaml
Observation:
  goal: string
  deliverable: string
  explicit_constraints: [string]
  repository_constraints: [string]
  evidence: [string]
  acceptance_criteria: [string]
  unresolved_decisions: [string]
```

목표 또는 산출물이 한 갈래로 수렴하지 않고 독립적인 관점·가설 탐색이 핵심이면 실행 전에 `/cast` 계열이 더 적합한지 판단한다. 하나의 확정 의도를 이루는 독립 실행 단위가 여러 개인 것은 `/ha`의 task graph로 처리한다.

## 2. IDENTIFY_DECISIONS

“모호할 수 있는 것”을 전부 나열하지 않는다. 답에 따라 실행이 달라질 수 있는 결정만 식별한다.

각 결정에서 다음을 확인한다.

- 어떤 증거를 이미 확인했는가
- 답을 사용자, 증거 또는 안전한 기본값 중 누가 소유하는가
- 가능한 답마다 파일·계약·범위·산출물·수용 기준·위험 처리가 어떻게 달라지는가
- 잘못 가정했을 때의 위험과 되돌림 비용은 무엇인가

이 결과로 `QuestionCandidate`를 만들고 `references/questioning.md`의 적격성 게이트를 적용한다.

## 3. QUESTION_GATE

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

## 4. COMMIT_INTENT

질문 답변과 관찰 근거를 통합해 실행 계약을 확정한다.

```yaml
CommittedIntent:
  goal: string
  deliverable: string
  hard_constraints: [string]
  acceptance_criteria: [string]
  user_decisions: [string]
  assumptions: [string]
  blockers: [string]
  execution_units: [string]
  verification_criteria: [string]
```

- 사용자 답과 명시 요구가 추론된 기본값보다 우선한다.
- 정책·안전 규칙과 저장소 지침은 그대로 지킨다.
- 낮은 위험의 기본값은 `assumptions`에 남긴다.
- 고위험 blocker가 하나라도 있으면 실행하지 않고 필요한 결정만 보고한다.
- 실행 전 `references/verification.md`에 따라 검증 기준을 예약한다.

## 5. ROUTE_AND_EXECUTE

`references/model-routing.md`의 역할 기준으로 각 실행 단위를 고른다.

- **controller**: 종합 판단, 아키텍처, 보안, 비가역 결정, 교차 계약과 blocker 분류
- **standard executor**: 일반 코드 작업, 중간 규모 리팩터링, 디버깅, 테스트, 표준 조사·문서
- **utility executor**: 단순 탐색, 목록화, 포맷, 명확한 국소 코드 변경과 기계 검사

```yaml
RuntimeParallelism:
  max_parallel_delegations: positive_integer | unknown
  runtime_parallel_limit:
    when_can_delegate_false: 1
    when_max_unknown: 1
    when_max_positive: max_parallel_delegations
  dependency_edges: [same_file_write, shared_state, external_side_effect, producer_consumer, writer_verifier]
```

controller는 확정 의도를 실행 단위와 의존선으로 나눈다. 런타임이 공개한 동시 위임 한도 안에서 의존성이 없는 단위만 같은 wave로 위임하며, 한도를 확인할 수 없거나 위임할 수 없으면 `runtime_parallel_limit = 1`로 둔다. 같은 파일 쓰기, 공유 상태, 외부 부작용, 생산자→소비자, writer→verifier는 의존선으로 두어 직렬 wave로 실행한다. 한 wave의 결과를 통합하고 실패·blocker를 처리한 뒤에만 의존 후속 wave를 시작한다. 사소한 단일 작업은 controller가 직접 수행할 수 있다.

위임에는 역할극 대신 다음을 포함한다.

- 목적과 정확한 범위
- 관련 파일·증거·사용자 결정
- 지켜야 할 제약과 실행 순서
- 기대 산출물과 검증 기준
- blocker 발생 시 필요한 보고 형식

실행자는 새 제품 결정을 임의로 만들지 않는다. 새 사용자 전용 결정이 발견되면 controller에 blocker로 돌려보낸다.

## 6. VERIFY

`references/verification.md`의 공통 계약과 task-type별 최소 검증을 적용한다.

- 가능한 경우 작성과 검증의 문맥을 분리한다.
- 테스트, 정적 검사, 실제 파일, 공식 출처와 재현 가능한 계산을 증거로 사용한다.
- 국소 결함은 수정하고 관련 검증을 다시 수행한다.
- 의도·구조 결함은 COMMIT_INTENT로 돌아간다.
- 사용자 결정이 새로 필요하면 QUESTION_GATE로 돌아간다.
- 실제 수정 뒤에는 `RepairLoopPolicy`에 따라 누적 횟수를 기록한다. 수정 횟수 자체에는 상한을 두지 않는다.
- 해결할 결함이 남은 10의 배수 수정에서는 현재 상태를 요약해 사용자 판단을 기다린다. 그 외 5의 배수 수정에서는 에이전트가 원래 목적·계획·현재 수정의 필수성을 판단한다.
- 새 권한·외부 변경·파괴적 작업·보안 경계 확대는 횟수와 관계없이 즉시 승인 경계를 적용하며, 이 실행 통제 질문은 초기 질문 예산과 분리한다.
- 동일한 입력·가설·행동을 새 증거 없이 반복하지 않는다.

검증되지 않은 결과를 완료로 표시하지 않는다.

## 최종 출력

사용자에게 필요한 내용만 간결하게 전달한다.

```yaml
result:
  outcome: string
  artifacts: [string]
  assumptions: [string]
  user_decisions: [string]
  verification_evidence: [string]
  remaining_risks: [string]
  model_routes: [model_route]
```

실제 위임이나 폴백이 없으면 `model_routes`를 생략할 수 있다. 내부 후보 목록과 상세 추론은 출력하지 않는다.

## 중첩 호출이 없는 런타임

`/haq`, `/haqq`, `/haqqq`가 `/ha`를 도구로 호출할 수 없으면 shim은 이 파일과 위 세 reference를 읽고 preset 설정을 적용해 같은 상태 흐름을 직접 수행한다. 이 경우에도 shim은 별도 질문 정책이나 모델 registry를 만들지 않는다.
