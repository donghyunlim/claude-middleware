# Question Policy

이 문서는 `/ha` 계열의 질문 후보 필드, 분류 상세, 질문 예산, 배치, 작성 규칙을 정한다. 질문 여부 판정(QUESTION_GATE)의 3조건, 3분류의 요약, 판정, `mid_run_decision`, 관찰 순서는 `SKILL.md` 3절에 있고, 여기에는 분류의 세부 조건만 둔다.

## Contents

- 질문 후보 계약
- 분류 상세
- 우선순위와 질문 예산
- 질문 작성과 런타임 적응
- 묻는 방식
- 답변 통합과 중단 조건
- 예시

## 질문 후보 계약

실행을 다르게 만드는 **결정**만 후보로 만든다. 포괄적인 모호성 목록을 먼저 만들지 않는다.

```yaml
QuestionCandidate:
  id: string
  decision: string
  unresolved: boolean
  evidence_checked: [string]
  answer_owner: user | evidence | agent_default | experiment
  user_only_reason: string | null
  materially_branching: boolean
  concrete_next_action_blocked: boolean
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
- `answer_owner`: 누가 답을 소유하는지 나타낸다. 개인 선호, 비공개 조직 정책, 승인, 의도는 `user`다. 저장소 상태나 API 사양은 `evidence`다. 해 보면 관찰되는 사실은 `experiment`다. 판별 기준은 `SKILL.md` 3절에 있다.
- `unresolved`: 관찰과 증거 확인을 마친 뒤에도 결정이 남아 있는지를 나타낸다.
- `materially_branching`: 답에 따라 아래에서 정의한 실행 경계가 실제로 달라질 때만 `true`다.
- `concrete_next_action_blocked`: concrete next action blocked, 즉 지금 수행할 다음 행동이 이 결정 없이는 안전하게 시작될 수 없을 때만 `true`다.
- `branches`: 서로 다른 답과 그에 따른 구체적인 `execution_delta`를 적는다.
- `assumption_cost`: 질문 비용과 비교한 가정 비용이다. 승인 자체가 필요한 경우에는 `approval_required`다.
- `safe_default`: 틀려도 손쉽게 되돌릴 수 있는 기본값이다. 고위험·승인 문제에는 두지 않는다.
- `question_class`: 증거 확인 뒤 후보를 `must_ask`, `decision_quality`, `skip`으로 분류한 결과다.

## 분류 상세

`SKILL.md`의 3조건을 통과한 후보를 다음 기준으로 나눈다. PROBE의 "버릴 수 있는 곳"은 임시 폴더, 복사본, 저장소와 데이터를 바꾸지 않는 로컬 실행이다.

1. **`must_ask`**: 사용자 소유·미해결·실질 분기 상태이며, `concrete_next_action_blocked == true`, `safe_default: null`이고 승인·보안·비밀·권한·외부 변경·파괴적·불가역 경계인 경우다. 실행이나 외부 변경 전에 묻되 discovery 예산·라운드에는 넣지 않는다. 실행 통제 경계 후보는 이 조건을 잃었다는 이유로 `decision_quality`로 우회 분류하지 않고, 증거로 해소하거나 blocker로 보고한다.
2. **`decision_quality`**: 세 기본 조건을 만족하고, 답이 산출물의 쓰임을 바꾸는 경우다. `assumption_cost`가 `lower_than_question`이어도 다음 중 하나가 바뀌면 해당한다.
   - 산출물의 독자·사용 목적
   - 공유·공개 범위
   - 결정의 상태·권한: 내부 검토안, 승인 기준, 대외 공유 초안 등의 차이
   - 참석자·소유자·수용 기준
3. **`skip`**: 사실을 증거로 확인할 수 있거나, 모든 답이 같은 실행으로 이어지거나, 차이가 사소한 표현·형식뿐인 경우다. 결과물을 바꾸는 취향·제품 판단은 `SKILL.md`의 `mid_run_decision`을 따른다.

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

## 우선순위와 질문 예산

후보는 다음 순서로 묻는다.

1. 승인·보안·비가역성 blocker
2. `decision_quality`에 해당하는 독자·용도·공유·결정 권한·참석자 관련 선택
3. 범위·계약·산출물·수용 기준을 바꾸는 다른 결정
4. 성능·비용·품질 간 최적화 방향을 바꾸는 결정

같은 실행 경로를 만드는 후보는 제거한다. 연관된 결정이라도 서로 독립적으로 답할 수 있으면 질문을 분리한다.

`must_ask` 실행 통제 질문은 discovery 예산과 라운드에 넣지 않고 별도 경로로 즉시 보낸다. 이 경로에는 아래 QuestionBudgetState 사전검사와 배치 공식을 적용하지 않으며, discovery 카운터를 갱신하지 않는다.

`decision_quality`는 질문 수 할당량이 아니며, 적격 후보가 없으면 모든 프리셋이 0문항으로 진행한다. 새 문서·회의 자료·메시지·결정 기록처럼 사람이 사용할 산출물을 만들고 그 쓰임이 불명확할 때, 프리셋별로 첫 라운드에서 다음만큼만 선제 확인한다.

- `none`: 선제 질문하지 않는다. 관찰 근거가 없으면 안전한 기본값을 `assumptions`에 기록하고 진행하며, 안전한 기본값이 없으면 실행하지 말고 blocker로 보고한다.
- `quick`: 가장 영향이 큰 후보 1개
- `standard`: 가장 중요한 후보 1~3개
- `deep`: 최대 4개

`decision_quality` 질문 라운드는 서로 관련된 실질 결정 질문을 한 번에 전달하고 답을 받은 단위다. 한 라운드에는 최대 4개만 묻는다. 호출당 한도가 양의 정수이면 `normalized_runtime_limit = runtime_limit`이고, `unknown`이거나 유효하지 않으면 `normalized_runtime_limit = 1`이다. 실제 배치 크기는 `min(4, normalized_runtime_limit, remaining_eligible, remaining_total_budget)`이다. 구조화 질문 도구가 없으면 한 라운드에 자유 응답형 질문 하나만 묻는다.

질문 예산은 다음 상태로 관리한다. 상태 정의와 갱신 규칙은 이 문서에만 두고, 프리셋 값(질문·라운드 상한, 확장 상한)은 진입 파일의 preset YAML(`/ha`는 `SKILL.md` 핵심 계약)에만 둔다.

```yaml
QuestionBudgetState:
  questions_asked_total: integer
  substantive_rounds_completed: integer
  effective_max_questions: max_questions
  effective_max_rounds: max_rounds
```

`decision_quality` 배치를 보내기 전에 `questions_asked_total < effective_max_questions`와 `substantive_rounds_completed < effective_max_rounds`를 모두 확인한다. `must_ask` 실행 통제 질문에는 이 사전검사를 적용하지 않는다.

`decision_quality` 배치를 실제로 보낸 직후에는 같은 `QuestionBudgetState`에 `questions_asked_total += batch_size`와 `substantive_rounds_completed += 1`을 적용한다. `batch_size`는 실제 전송된 질문 수여야 한다. 그 뒤 `remaining_total_budget = effective_max_questions - questions_asked_total`로 다시 계산한 값으로 다음 배치를 제한한다. 따라서 새 라운드에서 예산을 초기화하거나 이전 배치 수를 다시 사용할 수 없다.

`deep` 프리셋은 명시적인 확장 동의를 받은 뒤에만 `effective_max_questions = extended_max_questions`, `effective_max_rounds = extended_max_rounds`로 바꾼다. `deep`의 기본 상한을 넘겨야 한다면 먼저 사용자의 계속 진행 의사를 확인한다. 이 제어 질문은 기본 상한에 도달한 뒤에도 새 실질 질문이 남고 `questions_asked_total < extended_max_questions`일 때 한 번만 보낼 수 있다. 확장 동의 제어 질문은 `questions_asked_total += 1`만 적용하고 `substantive_rounds_completed`는 증가시키지 않는다. 동의한 경우에만 실질 질문 라운드는 `extended_max_rounds`까지, 사용자에게 보낸 모든 질문(확장 동의 질문 포함)은 합쳐서 `extended_max_questions`까지 넓힌다. 동의하지 않으면 즉시 질문을 끝내고, 위험한 기본값으로 진행하지 않고 남은 blocker를 보고한다. 확장 상한도 목표가 아니라 절대 상한이다.

## 질문 작성과 런타임 적응

질문 하나는 결정 하나만 다룬다. 추상적인 “원하는 방향은?” 대신 선택 결과가 보이는 문장을 사용한다.

구조화 질문 도구가 있고 서로 배타적인 선택지를 만들 수 있으면 다음 형식을 사용한다.

- 2~3개의 의미상 뚜렷한 선택지
- 권장 선택지를 첫 번째에 배치하고 `(권장)` 표시
- 각 설명에 범위·비용·위험 등 실행상 귀결을 한 문장으로 명시
- 한 호출의 질문 수는 위 배치 크기 공식을 따른다

선택지를 미리 열거하면 사용자의 답을 왜곡하는 질문에는 짧은 자유 응답형을 사용한다. 구조화 질문 도구가 없으면 텍스트로 선택형 UI를 흉내 내지 말고, 가장 높은 우선순위의 질문 하나를 간결하게 묻는다.

질문 전에 짧게 다음을 알린다.

```text
실행 경로를 바꾸는 결정 N개만 확인하겠습니다. 답변으로 충분해지면 남은 질문은 생략합니다.
```

## 묻는 방식

`mid_run_decision`의 정의와 5분 기준은 `SKILL.md`에 있다. 묻는 방식은 시작 전 질문과 실행 중 질문 모두 같다.

- 질문 도구로 묻고 그 자리에서 멈춘다. 답을 받기 전에는 그 판단에 기대는 작업을 진행하지 않는다.
- 질문 도구가 없는 런타임에서는 글로 질문 하나를 쓰고 턴을 끝낸다.
- 이미 띄운 백그라운드 작업은 그대로 두고, 그 결과는 답을 받은 뒤 반영한다.
- 시안 2~3개는 실제로 물을 때만, 레이아웃·문체·구조 같은 취향 판단에 붙인다.
- 눈으로 봐야 판단하는 결정(전/후 화면, 디자인 시안, 목업)이 한 번의 질문 도구에 담기지 않을 만큼 많으면 `wrxp:visual-ask`로 결정 페이지를 띄워 묻는다. discovery 질문을 페이지로 보내면 카드 하나를 질문 하나로 세고, 끝낸 결과물의 승인과 실행 중 시안 비교는 예산에 넣지 않는다. 페이지의 답을 읽기 전에는 그 답에 기대는 작업을 진행하지 않는다.

묻지 않고 대신 정한 판단은 `SKILL.md` 최종 출력 절의 `defaults_taken` 규칙대로 보인다.

## 답변 통합과 중단 조건

각 라운드 뒤에 다음을 수행한다.

1. 답을 `resolved`, `inferable`, `still_open`으로 갱신한다.
2. 새 증거로 해결할 수 있는 항목은 조사한다.
3. `SKILL.md` 3절의 3조건을 다시 적용한다.
4. 적격 질문이 없으면 즉시 질문을 끝낸다.
5. 답변이 원래 요구와 충돌하면 충돌하는 결정 하나만 다시 확인한다.

사용자가 “그냥 진행”, “충분해”, “skip”처럼 중단 의사를 밝히면 안전한 기본값이 있는 항목만 가정한다. blocker는 가정하지 않고 보고한다.

## 예시

### 질문하지 않음

요청: “현재 React 버전을 알려줘.”

`package.json`으로 확인할 수 있으므로 `answer_owner: evidence`다. 파일을 읽고 답한다.

### 질문함

요청: “영업 대시보드를 개선해줘.”

관찰 후에도 1차 성공 기준을 사용자만 결정할 수 있고, 답에 따라 측정·UI·쿼리가 달라진다면 질문 tier에서는 `decision_quality`로 질문할 수 있다.

```yaml
decision: 1차 성공 기준
unresolved: true
evidence_checked: [사용자 요청, 저장소 대시보드 구현, 현재 지표 정의]
answer_owner: user
user_only_reason: 제품 우선순위는 저장소에서 확인할 수 없음
materially_branching: true
concrete_next_action_blocked: false
branches:
  - answer: 로딩 시간
    execution_delta: 쿼리와 렌더링 병목을 우선 최적화
  - answer: 전환율
    execution_delta: 행동 흐름과 CTA 측정을 우선 변경
  - answer: 영업 운영 효율
    execution_delta: 필터·일괄 작업·리드 우선순위를 우선 변경
risk_if_assumed: high
assumption_cost: higher_than_question
safe_default: 로딩 시간
question_class: decision_quality
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
concrete_next_action_blocked: false
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

### 실험으로 확인

요청: “이 CLI가 설정 파일이 없을 때도 실행되게 해줘.”

설정 파일이 없을 때 지금 어떤 오류가 나는지는 사용자가 아니라 실행 결과가 답한다. `answer_owner: experiment`로 두고, 임시 폴더에서 설정 파일 없이 한 번 실행해 오류를 관찰한다. 관찰로 결론이 나면 묻지 않고, 기본 동작을 무엇으로 할지처럼 사용자만 정할 수 있는 판단이 남을 때만 관찰 결과를 붙여 묻는다.

### 기본값 적용

요청에 문서의 사소한 제목 스타일이 빠졌고 저장소 관례가 명확하다면 `answer_owner: agent_default`, `risk_if_assumed: low`, `question_class: skip`으로 처리한다. 질문하지 않고 적용한 가정을 결과에 밝힌다.
