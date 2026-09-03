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

- 모든 호출에서 CAPABILITY_RESOLVE 직후, OBSERVE 전에 [references/questioning.md](references/questioning.md)를 끝까지 읽는다. 이 순서를 질문 후보가 아직 없다는 이유로 건너뛰지 않는다.
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

이 상태에 들어오기 전에 `references/questioning.md`를 읽었어야 한다. 읽지 않았다면 관찰을 시작하지 말고 먼저 읽는다.

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

`references/questioning.md`에 따라 각 후보를 `must_ask`, `decision_quality`, `skip`으로 분류한다.

- `must_ask`: 사용자 소유·미해결 상태이고 concrete next action blocked이며 `safe_default: null`인 승인·보안·비밀·권한·외부 변경·파괴적·불가역 경계다. 실행 전에 반드시 묻고 discovery 예산에는 넣지 않는다.
- `decision_quality`: 같은 세 기본 조건을 만족하고 산출물의 독자·용도·공유 범위·결정 권한·참석자·수용 기준을 바꾼다. 안전한 기본값이 있어도 새 문서·회의 자료·메시지·결정 기록의 쓰임을 바꾸면 tier 예산 안에서 선제적으로 묻는다.
- `skip`: 증거로 확인할 수 있거나 모든 답이 같은 실행으로 이어지거나 표현만 달라지는 항목이다.

질문 수는 할당량이 아니다. `none` 프리셋은 선제 discovery 질문을 0개로 두고, 실행 통제 게이트 외 후보는 관찰 근거 또는 기록한 안전한 기본값으로 진행한다. 안전한 기본값이 없으면 실행하지 말고 blocker로 보고한다. `quick`·`standard`·`deep` 프리셋은 질문 티어 계약에 따라 `decision_quality` 후보를 물을 수 있다. 후보가 없으면 0문항으로 바로 진행한다.

`must_ask` 실행 통제 질문은 별도 전송 경로로 즉시 보낸다. 이 경로에는 QuestionBudgetState 사전검사 또는 discovery 배치 공식을 적용하지 않으며, discovery 카운터를 갱신하지 않는다. `remaining_total_budget`과 배치 크기 공식은 `decision_quality` 배치에만 적용한다.

`decision_quality` 배치는 구조화 질문 도구의 런타임 스키마와 한도를 따르되, 한 라운드에 최대 4개만 묻는다. 호출당 한도가 양의 정수이면 `normalized_runtime_limit = runtime_limit`이고, `unknown`이거나 유효하지 않으면 `normalized_runtime_limit = 1`이다. 실제 배치 크기는 `min(4, normalized_runtime_limit, remaining_eligible, remaining_total_budget)`이다. 의미상 배타적인 선택지를 만들 수 없거나 구조화 도구가 없으면 가장 중요한 질문 하나를 짧은 자유 응답형으로 묻는다.

다음 상태를 유지한다.

```yaml
QuestionBudgetState:
  questions_asked_total: integer
  substantive_rounds_completed: integer
  effective_max_questions: max_questions
  effective_max_rounds: max_rounds
```

`decision_quality` 배치를 보내기 전에 `questions_asked_total < effective_max_questions`와 `substantive_rounds_completed < effective_max_rounds`를 모두 확인한다. 배치를 실제로 보낸 직후 같은 상태 객체에 `questions_asked_total += batch_size`와 `substantive_rounds_completed += 1`을 적용한다. `batch_size`는 제안한 수가 아니라 실제로 보낸 질문 수다. 이어서 `remaining_total_budget = effective_max_questions - questions_asked_total`로 다시 계산한다. 각 답변 뒤에 결정을 다시 계산한다. 적격 질문이 사라지면 예산이 남아도 즉시 종료한다. 기본 상한에 도달하면 질문을 멈춘다.

`deep` 프리셋은 명시적인 확장 동의를 받은 뒤에만 `effective_max_questions = extended_max_questions`, `effective_max_rounds = extended_max_rounds`로 바꾼다. 확장 동의 제어 질문은 `questions_asked_total += 1`만 적용하고 `substantive_rounds_completed`는 증가시키지 않는다. 이 제어 질문은 기본 상한에 도달한 뒤에도 새 실질 질문이 남고 `questions_asked_total < extended_max_questions`일 때 한 번만 허용한다. 사용자가 동의하지 않으면 즉시 질문을 끝낸다. 질문 총수가 20개를 넘거나 실질 질문 라운드가 5개를 넘도록 확장하지 않는다. 질문 상한에 도달했는데 승인·보안·비가역 blocker가 남으면 임의로 진행하지 않는다.

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
