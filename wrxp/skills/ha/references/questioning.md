# Question Policy

이 문서는 `/ha` 계열의 사용자 질문 게이트를 정의한다. 질문 프리셋은 질문의 **상한**만 바꾸며, 질문 수를 채우는 할당량이 아니다. 모든 프리셋에서 질문 0개가 정상이다.

## Contents

- 관찰 우선 원칙
- 질문 후보 계약
- 적격성 게이트
- 우선순위와 프리셋
- 질문 작성과 런타임 적응
- 답변 통합과 중단 조건
- 예시

## 관찰 우선 원칙

질문 후보를 만들기 전에 다음 순서로 이미 있는 답을 찾는다.

1. 현재 사용자 요청과 이전 대화
2. 사용자가 지정한 파일, 첨부물, 링크
3. `AGENTS.md`, `CLAUDE.md`, 저장소 문서와 기존 구현
4. 사용 가능한 읽기 도구, 검색, 공식 문서와 런타임 메타데이터
5. 안전하고 되돌릴 수 있는 합리적 기본값

파일·문서·도구로 확인할 수 있는 사실은 사용자에게 묻지 않는다. 질문 카테고리 목록을 채우기 위해 질문하지 않는다.

## 질문 후보 계약

실행을 다르게 만드는 **결정**만 후보로 만든다. 포괄적인 모호성 목록을 먼저 만들지 않는다.

```yaml
QuestionCandidate:
  id: string
  decision: string
  unresolved: boolean
  evidence_checked: [string]
  answer_owner: user | evidence | agent_default
  user_only_reason: string | null
  materially_branching: boolean
  branches:
    - answer: string
      execution_delta: string
  risk_if_assumed: low | medium | high
  assumption_cost: lower_than_question | higher_than_question | approval_required
  safe_default: string | null
  question_class: must_ask | decision_quality | skip
  priority: blocker | high | normal
```

- `decision`: 이번 질문으로 확정하려는 하나의 결정이다.
- `evidence_checked`: 질문 전에 확인한 대화·파일·문서·도구다.
- `answer_owner`: 누가 답을 소유하는지 나타낸다. 개인 선호, 비공개 조직 정책, 승인, 의도는 `user`다. 저장소 상태나 API 사양은 `evidence`다.
- `unresolved`: 관찰과 증거 확인을 마친 뒤에도 결정이 남아 있는지를 나타낸다.
- `materially_branching`: 답에 따라 아래에서 정의한 실행 경계가 실제로 달라질 때만 `true`다.
- `branches`: 서로 다른 답과 그에 따른 구체적인 `execution_delta`를 적는다.
- `assumption_cost`: 질문 비용과 비교한 가정 비용이다. 승인 자체가 필요한 경우에는 `approval_required`다.
- `safe_default`: 틀려도 손쉽게 되돌릴 수 있는 기본값이다. 고위험·승인 문제에는 두지 않는다.
- `question_class`: 증거 확인 뒤 후보를 `must_ask`, `decision_quality`, `skip`으로 분류한 결과다.

## 적격성 게이트

먼저 다음 세 조건을 모두 만족하지 않는 후보는 `skip`으로 둔다.

1. `unresolved == true`: 관찰 후에도 결정이 남아 있다.
2. `answer_owner == user`: 사용자만 답할 수 있다.
3. `materially_branching == true`: 답에 따라 실행 경로가 실질적으로 달라진다.

세 조건을 통과한 후보는 다음처럼 분류한다.

1. **`must_ask`**: `assumption_cost in {higher_than_question, approval_required}`까지 만족하는 경우다. 승인·보안·비가역성·권한 문제처럼 잘못 가정하면 안 되는 결정이므로 실행이나 외부 변경 전에 묻는다. 네 필드 중 하나라도 조건을 만족하지 않으면 `must_ask`로 분류하지 않는다.
2. **`decision_quality`**: 세 기본 조건을 만족하고, 답이 산출물의 쓰임을 바꾸는 경우다. `assumption_cost`가 `lower_than_question`이어도 다음 중 하나가 바뀌면 해당한다.
   - 산출물의 독자·사용 목적
   - 공유·공개 범위
   - 결정의 상태·권한: 내부 검토안, 승인 기준, 대외 공유 초안 등의 차이
   - 참석자·소유자·수용 기준
3. **`skip`**: 사실을 증거로 확인할 수 있거나, 모든 답이 같은 실행으로 이어지거나, 차이가 사소한 표현·형식뿐인 경우다.

안전한 기본값이 있어도 `decision_quality` 후보를 버리지 않는다. 안전한 기본값은 사용자가 질문을 건너뛰거나 답변을 보류했을 때의 진행 경로일 뿐, 독자·용도·공유·결정 권한처럼 산출물의 가치와 사용 방식을 바꾸는 선택을 자동으로 숨기는 근거가 아니다. `risk_if_assumed`와 `branches`는 이 분류를 설명하는 근거이며, 필수 불리언·열거 필드를 대신하지 않는다.

`materially_branching`은 답에 따라 다음 중 하나 이상이 바뀐다는 뜻이다.

- 수정 파일 또는 외부 시스템
- API·데이터 계약
- 산출물의 종류, 산출물의 독자·사용 목적 또는 공유·공개 범위
- 구현 범위와 수용 기준
- 결정의 상태·권한, 참석자·소유자·수용 기준
- 보안 또는 되돌림 전략

다음은 질문하지 않는다.

- 모든 답이 같은 실행 계획으로 이어지는 경우
- 로컬 파일이나 공식 문서로 확인할 수 있는 경우
- 낮은 위험의 세부 선호이며 안전한 기본값이 있고, `decision_quality`의 쓰임 변화도 없는 경우
- 단순히 task-type 질문 표에 포함된 항목인 경우

고위험 사용자 결정에는 안전한 기본값을 만들지 않는다. 질문 상한에 도달했는데 blocker가 남으면 실행하지 말고 남은 결정을 보고한다.

## 우선순위와 프리셋

후보는 다음 순서로 묻는다.

1. 승인·보안·비가역성 blocker
2. `decision_quality`에 해당하는 독자·용도·공유·결정 권한·참석자 관련 선택
3. 범위·계약·산출물·수용 기준을 바꾸는 다른 결정
4. 성능·비용·품질 간 최적화 방향을 바꾸는 결정

같은 실행 경로를 만드는 후보는 제거한다. 연관된 결정이라도 서로 독립적으로 답할 수 있으면 질문을 분리한다.

`must_ask` 후보가 있으면 먼저 배치에 넣고 남은 슬롯만 `decision_quality` 후보로 채운다. `decision_quality`는 질문 수 할당량이 아니다. 적격 후보가 전혀 없으면 모든 프리셋이 0문항으로 진행한다. 다만 새 문서·회의 자료·메시지·결정 기록처럼 사람이 사용할 산출물을 만들고 그 쓰임이 불명확하면, 프리셋별로 다음만큼 선제 확인한다.

- `auto`·`quick`: 가장 영향이 큰 `decision_quality` 후보 1개만 첫 라운드에 묻는다.
- `standard` 프리셋은 1~3개의 가장 중요한 `decision_quality` 후보를 첫 라운드에 묻는다. `must_ask`가 슬롯을 차지하면 남은 슬롯에서 가장 영향이 큰 후보만 추가한다.
- `deep`: blocker와 고위험 후보를 먼저 두고, 남은 슬롯에서 최대 4개의 `decision_quality` 후보를 묻는다.

질문 라운드는 서로 관련된 실질 결정 질문을 한 번에 전달하고 답을 받은 단위다. 한 라운드에는 최대 4개만 묻는다. 호출당 한도가 양의 정수이면 `normalized_runtime_limit = runtime_limit`이고, `unknown`이거나 유효하지 않으면 `normalized_runtime_limit = 1`이다. 실제 배치 크기는 `min(4, normalized_runtime_limit, remaining_eligible, remaining_total_budget)`이다. 구조화 질문 도구가 없으면 한 라운드에 자유 응답형 질문 하나만 묻는다.

실질 질문 배치를 실제로 보낸 직후에는 같은 `QuestionBudgetState`에 `questions_asked_total += batch_size`와 `substantive_rounds_completed += 1`을 적용한다. `batch_size`는 실제 전송된 질문 수여야 한다. 그 뒤 `remaining_total_budget = effective_max_questions - questions_asked_total`로 다시 계산한 값으로 다음 배치를 제한한다. 따라서 새 라운드에서 예산을 초기화하거나 이전 배치 수를 다시 사용할 수 없다.

| preset | 기본 질문 상한 | 라운드당 상한 | 기본 라운드 상한 | 용도 |
|---|---:|---:|---:|---|
| `auto` | 4 | 4 | 2 | `/ha` 직접 호출의 균형형 기본값 |
| `quick` | 4 | 4 | 1 | 한 번의 빠른 확인 |
| `standard` | 8 | 4 | 2 | 답변 후 재평가가 필요한 표준 발견 |
| `deep` | 12 | 4 | 3 | 고위험 단일 문제의 단계적 확인 |

`deep`의 12개 또는 3라운드를 넘겨야 한다면 먼저 사용자의 계속 진행 의사를 확인한다. 이 제어 질문은 기본 상한에 도달한 뒤에도 새 실질 질문이 남고 `questions_asked_total < extended_max_questions`일 때 한 번만 보낼 수 있다. 확장 동의 제어 질문은 `questions_asked_total += 1`만 적용하고 `substantive_rounds_completed`는 증가시키지 않는다. 동의한 경우에만 최대 5개의 실질 질문 라운드와 사용자에게 보낸 모든 질문을 합쳐 총 20개까지 확장한다. 동의하지 않으면 즉시 질문을 끝낸다. 따라서 동의 뒤에는 `20 - questions_asked_total`개보다 많이 물을 수 없다. 20개도 목표가 아니라 절대 상한이다.

## 질문 작성과 런타임 적응

질문 하나는 결정 하나만 다룬다. 추상적인 “원하는 방향은?” 대신 선택 결과가 보이는 문장을 사용한다.

구조화 질문 도구가 있고 서로 배타적인 선택지를 만들 수 있으면 다음 형식을 사용한다.

- 2~3개의 의미상 뚜렷한 선택지
- 권장 선택지를 첫 번째에 배치하고 `(권장)` 표시
- 각 설명에 범위·비용·위험 등 실행상 귀결을 한 문장으로 명시
- 한 호출의 질문 수는 `min(4, normalized_runtime_limit, remaining_eligible, remaining_total_budget)`

선택지를 미리 열거하면 사용자의 답을 왜곡하는 질문에는 짧은 자유 응답형을 사용한다. 구조화 질문 도구가 없으면 텍스트로 선택형 UI를 흉내 내지 말고, 가장 높은 우선순위의 질문 하나를 간결하게 묻는다.

질문 전에 짧게 다음을 알린다.

```text
실행 경로를 바꾸는 결정 N개만 확인하겠습니다. 답변으로 충분해지면 남은 질문은 생략합니다.
```

## 답변 통합과 중단 조건

각 라운드 뒤에 다음을 수행한다.

1. 답을 `resolved`, `inferable`, `still_open`으로 갱신한다.
2. 새 증거로 해결할 수 있는 항목은 조사한다.
3. 적격성 게이트를 다시 적용한다.
4. 적격 질문이 없으면 즉시 질문을 끝낸다.
5. 답변이 원래 요구와 충돌하면 충돌하는 결정 하나만 다시 확인한다.

사용자가 “그냥 진행”, “충분해”, “skip”처럼 중단 의사를 밝히면 안전한 기본값이 있는 항목만 가정한다. blocker는 가정하지 않고 보고한다.

## 예시

### 질문하지 않음

요청: “현재 React 버전을 알려줘.”

`package.json`으로 확인할 수 있으므로 `answer_owner: evidence`다. 파일을 읽고 답한다.

### 질문함

요청: “영업 대시보드를 개선해줘.”

관찰 후에도 1차 성공 기준을 사용자만 결정할 수 있고, 답에 따라 측정·UI·쿼리가 달라진다면 질문한다.

```yaml
decision: 1차 성공 기준
unresolved: true
evidence_checked: [사용자 요청, 저장소 대시보드 구현, 현재 지표 정의]
answer_owner: user
user_only_reason: 제품 우선순위는 저장소에서 확인할 수 없음
materially_branching: true
branches:
  - answer: 로딩 시간
    execution_delta: 쿼리와 렌더링 병목을 우선 최적화
  - answer: 전환율
    execution_delta: 행동 흐름과 CTA 측정을 우선 변경
  - answer: 영업 운영 효율
    execution_delta: 필터·일괄 작업·리드 우선순위를 우선 변경
risk_if_assumed: high
assumption_cost: higher_than_question
safe_default: null
question_class: must_ask
priority: high
```

### 회의 자료의 선택을 먼저 묻는 경우

요청: “회의록과 협업 도구를 찾아 다음 주 파트너 미팅 자료를 개인 비공개 페이지에 준비해줘.”

비공개 저장 위치는 이미 명확하지만, 자료가 내부 진행용인지 파트너에게 공유할 초안인지, P0/P1 항목을 내부 제안으로 둘지 승인 기준으로 만들지는 증거만으로 정할 수 없다. 안전한 내부용 기본값이 있더라도 이 선택은 산출물의 쓰임과 회의 중 행동을 바꾸므로 `decision_quality`다.

```yaml
decision: 자료의 독자와 의사결정 상태
unresolved: true
evidence_checked: [회의록, 캘린더 초대, 기존 협업 문서]
answer_owner: user
user_only_reason: 자료의 공유·승인 목적은 조직 문서만으로 확정할 수 없음
materially_branching: true
branches:
  - answer: 내부 진행용 워킹 문서
    execution_delta: 쟁점·질문·미확정 항목을 중심으로 작성
  - answer: 파트너 공유 가능 초안
    execution_delta: 표현·근거·공개 범위를 정제하고 내부 메모를 분리
  - answer: 승인 또는 Go/No-go 판단 자료
    execution_delta: 결정 기준·책임자·결정표를 중심으로 작성
risk_if_assumed: medium
assumption_cost: lower_than_question
safe_default: 내부 진행용 워킹 문서
question_class: decision_quality
priority: high
```

`standard` 프리셋의 첫 라운드에서는 다음처럼 선택의 결과를 보여 주는 질문을 최대 3개까지 제시한다.

1. “이번 자료는 내부 진행용, 파트너 공유 가능 초안, 승인·Go/No-go 판단 자료 중 어디에 맞출까요?”
2. “P0/P1 항목은 내부 검토 제안으로 둘까요, 아니면 회의에서 확정할 승인 기준으로 만들까요?”
3. “회의록과 초대 명단이 다르면 미확정 참석자로 표시할까요, 아니면 작성 전에 참석자 확인을 진행할까요?”

### 기본값 적용

요청에 문서의 사소한 제목 스타일이 빠졌고 저장소 관례가 명확하다면 `answer_owner: agent_default`, `risk_if_assumed: low`, `question_class: skip`으로 처리한다. 질문하지 않고 적용한 가정을 결과에 밝힌다.
