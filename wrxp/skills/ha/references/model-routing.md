# Model and Agent Routing

이 문서는 `/ha` 계열의 역할별 모델 후보와 폴백을 정한다. 역할 정의, 작업 순서·병렬 한도, 위임 여부 기준, 코드 위임 우선 규칙은 `SKILL.md` 5절에만 있다. 합의된 독립 코드 구현은 `wrxp:code-delegation`의 모델 고정(Codex `gpt-6.1-sol` `medium`/`high`, Claude Opus 5.5, 가볍고 좁은 일은 Sonnet 5.5)을 따르며 이 문서를 적용하지 않는다. 모델 이름은 선호 후보이며, 실제 런타임이 제공한 목록과 기능이 항상 우선한다.

## Contents

- 런타임 능력 확인
- 역할 매핑
- 작업 속성별 선택
- 위임 멘트
- 검증 분리
- 폴백과 공개

## 런타임 능력 확인

하위 에이전트에 모델을 지정하기 전에 가능한 범위에서 다음을 확인한다.

```yaml
RuntimeCapabilities:
  provider: codex | claude | unknown
  active_model: string | unknown
  available_models: [string]
  supported_reasoning_efforts: {model: [string]}
  can_delegate: boolean
  max_parallel_delegations: integer | unknown
  can_isolate_verifier_context: boolean
  structured_question:
    available: boolean
    max_questions_per_call: integer | unknown
  available_tools: [string]
```

`available_models`와 `supported_reasoning_efforts`는 모델과 사고 수준의 실행 가능 조합을 판정하는 한 계약이다. 특정 모델의 사고 수준 목록이 없거나 런타임이 사고 수준 인자를 받지 않으면 그 모델 호출에서 해당 인자를 생략한다.

런타임이 모델 목록을 제공하지 않으면 이름을 추측해 호출하지 않는다. 현재 활성 모델이나 런타임 기본 모델을 사용하고 그 사실을 기록한다.

## 역할 매핑

표의 Haiku 5.5와 `low`는 합의된 코드 구현이 아닌 실행 단위에만 쓴다.

| 역할 | Codex 선호 후보 | Claude 선호 후보 |
|---|---|---|
| controller | `gpt-6-astra` + `high` | Claude Opus 5.5 (`claude-opus-5-5`) |
| standard executor | `gpt-6.1-sol` + `medium` (가벼운 작업 `low`) | Claude Haiku 5.5 (`claude-haiku-5-5`), 어려운 작업은 Claude Sonnet 5.5 (`claude-sonnet-5-5`) |
| utility executor | `gpt-6-luna` + `low` | Claude Haiku 5.5 (`claude-haiku-5-5`) |
| verifier | 보통 Sol, 고위험 Astra | 보통 Sonnet 5.5, 고위험 Opus 5.5 |

Claude 실행자는 Haiku 5.5를 기본으로 한다. Haiku 5.5는 런타임이 그 모델을 정확한 이름·ID로 제공할 때만 쓰고, ID를 추측하지 않는다. `haiku` 별칭이 5.5보다 낮은 버전으로 해석되면 쓰지 않고 Sonnet 5.5를 쓰며, Haiku 4.5는 사용하지 않는다.

`gpt-6-astra`는 런타임 기본 사고 수준이 `low`이므로, controller 역할에서는 `high`를 명시적으로 전달해야 표의 의도대로 실행된다. 사고 수준을 생략하면 이 모델은 최상위 모델이면서도 가장 낮은 추론으로 응답한다.

Claude Code가 `opus`, `sonnet`, `haiku` 같은 계열 별칭만 받으면 해당 별칭을 사용하고 설치된 정확한 버전은 런타임에 맡긴다. Claude API 모델 ID를 받는 환경에서만 표의 정확한 ID를 사용한다. Codex 전용 `reasoning_effort` 필드를 Claude 위임에 강제하지 않는다. Claude 런타임이 effort를 명시적으로 지원할 때만 지원 목록의 교집합을 사용한다.

Codex 위임 API가 모델과 사고 수준을 별도 인자로 받으면 검증된 `(model, reasoning_effort)` 쌍만 전달한다. Claude Code에는 런타임이 허용한 `model` 별칭 또는 ID를 전달하고, 별도의 사고 수준 인자는 해당 런타임이 명시적으로 지원할 때만 전달한다.

## 작업 속성별 선택

### controller

다음 중 하나면 controller가 직접 수행하거나 최종 판단을 소유한다.

- 요구가 모호하거나 상충한다.
- 아키텍처 또는 여러 모듈 간 계약이 바뀐다.
- 보안, 권한, 데이터 손실 또는 비가역 변경이 포함된다.
- 하위 실행자가 같은 범주의 작업에서 두 번 실패했다.
- 결과를 종합해 최종 결정을 내려야 한다.

### standard executor

경계와 수용 기준이 정해진 일반 구현·중간 규모 리팩터링·버그 수정·테스트는 standard executor에 맡긴다. 여러 파일을 수정한다는 이유만으로 controller나 병렬 체계로 올리지 않는다.

Claude에서는 애매하면 Haiku 5.5로 시작하고, 다음 작업만 Sonnet 5.5로 올린다.

- 여러 단계를 스스로 판단하며 길게 진행하는 작업(예: 앱을 직접 조작하는 QA)
- 화면·이미지를 보고 판단하는 작업
- 원인이 불분명한 디버깅
- 설계 판단이 필요한 여러 파일 수정
- Haiku 5.5가 한 번 실패한 작업

### utility executor

결과가 결정론적이고 범위가 좁을 때 사용한다.

- 문자열·파일·심볼 검색과 목록화
- 정렬, 포맷, 스키마 추출
- 명확한 1~3줄 또는 이에 준하는 국소 코드 변경
- 이미 정해진 명령의 실행과 결과 수집

utility가 범위·설계·보안 판단을 새로 내려야 하면 standard 또는 controller로 승격한다.

## 위임 멘트

정체성 역할극 대신 목적과 경계를 전달한다.

### controller

```text
목적: 요청과 관찰 근거를 종합해 실행 의도를 확정한다.
책임: 충돌·위험·의존성을 판단하고, 사용자 결정이 필요한 blocker와 실행 가능한 기본값을 구분한다.
산출물: 확정 목표, 제약, 수용 기준, 실행 순서, 검증 기준.
```

### standard executor

```text
목적: 확정된 실행 단위를 구현하거나 조사한다.
범위: 전달된 파일·모듈과 수용 기준 안에서 작업하고, 새 제품 결정을 만들지 않는다.
산출물: 변경 내용, 실행한 검사, 남은 blocker.
```

### utility executor

```text
목적: 지정된 결정론적 탐색·변환·국소 변경을 수행한다.
범위: 결과를 해석해 범위를 넓히지 말고, 발견한 사실과 정확한 위치를 반환한다.
산출물: 요청된 결과와 재현 가능한 근거.
```

### verifier

```text
목적: 산출물을 원 요구·수용 기준·위험에 대조해 독립적으로 검증한다.
범위: 작성자의 결론을 전제로 삼지 않고 실제 파일·테스트·출처를 확인한다.
산출물: PASS/FAIL, 증거, 수정이 필요한 정확한 항목.
```

## 검증 분리

- utility 결과의 의미 해석이나 코드 품질 검증은 standard가 맡는다.
- standard가 작성한 표준 변경은 가능하면 새 verifier 문맥의 standard가 검증한다.
- 보안·비가역·아키텍처 변경은 controller가 최종 검증한다.
- 독립 verifier 문맥을 만들 수 없으면 현재 모델이 별도 검증 패스를 수행하고 `검증 독립성 저하`를 기록한다.

## fallback과 공개

1. 선호 후보가 `available_models`에 있는지 확인한다.
2. 후보 모델이 사고 수준 인자를 지원하면 해당 모델의 `supported_reasoning_efforts[model]` 안에서 목표 수준과 가장 가까운 값을 고른다. 목표 역할이 `low`, `medium`, `high`라면 같은 값을 우선하고, 정확한 값이 없을 때에만 런타임이 제공한 순서 또는 설명에 근거해 가장 가까운 값을 고른다.
3. 후보 모델의 사고 수준 목록을 확인할 수 없거나 인자를 지원하지 않으면 사고 수준을 생략한다. 확인되지 않은 `(model, effort)` 쌍을 만들지 않는다.
4. 선호 모델이 없으면 런타임 설명에 근거해 같은 공급자의 동급 역할 모델에 2~3단계를 다시 적용한다.
5. 동급 후보를 확인할 수 없으면 현재 활성 모델 또는 기본 모델을 사용하고, 확인된 경우에만 지원 사고 수준을 붙인다.
6. 위임 기능이 없으면 현재 모델이 직접 수행한다.
7. 호출이 사고 수준 오류로 거절되면 같은 모델에서 런타임이 확인한 지원 수준 또는 사고 수준 생략으로 한 번 재시도한다. 모델 자체가 거절되면 같은 이름을 반복하지 않고 현재 활성 모델 또는 기본 모델로 한 번 재시도한다.
8. 공급자 전환은 런타임이 실제로 지원하고 사용자·정책 범위 안일 때만 한다.

최종 결과에는 실제 위임이 있었거나 폴백이 발생한 경우 다음을 남긴다.

```yaml
model_route:
  role: controller | standard_executor | utility_executor | verifier
  preferred: string
  actual: string | runtime_default
  effort: string | omitted
  fallback_reason: string | null
```
