# Verification Policy

코드 위임에는 `wrxp:code-delegation`이 우선한다. 현재 코드에 대응하는 작업자의 자체 검증 근거가 충분하면 아래 작성자/verifier 분리를 자동으로 추가하지 않는다. 사용자 요청 리뷰, 근거 누락 또는 구체적인 보안·통합 위험에는 필요한 범위의 추가 검토를 수행한다. 예외로, 공유 계약(정의는 `/ha` 본문)을 바꾸면 새 맥락 sonnet 검토를 1회 붙인다.

이 문서는 `/ha` 계열의 위험 비례 검증과 종료 조건을 정의한다.

## Contents

- 공통 검증 계약
- 대체물과 판단 불가
- 공유 계약 검토
- 실제 화면 확인
- 수정 루프 체크포인트
- 실패 처리
- 결과 기록

## 공통 검증 계약

1. 검증 기준은 실행 전에 수용 기준과 위험에서 정한다.
2. 가능한 경우 작성자와 verifier의 문맥을 분리한다.
3. 주장보다 관찰 가능한 증거를 우선한다: 테스트 결과, 정적 검사, 실제 파일, 공식 출처, 계산 재현.
4. 검증하지 못한 항목은 통과로 간주하지 않고 한계를 밝힌다.
5. 변경 위험과 영향 범위에 비례해 검증 강도를 높인다.

트랙별 핵심 확인은 [tracks.md](tracks.md)를 따른다.

## 대체물과 판단 불가

대체물(다른 환경, 목업, 자기 보고, 요약본)로 확인한 것은 통과가 아니다. 실제 대상으로 확인하지 못했으면 결과를 `inconclusive`(판단 불가)로 두고, 무엇을 확인하지 못했는지 `limitations`에 적는다.

## 공유 계약 검토

공유 계약을 바꾸면 새 맥락 sonnet 검토를 1회 붙인다. 검토 브리프에는 "변경이 안전한 근거 사실 하나를 찾아 실행으로 확인하고, 검색이 닿지 않는 사용처(설정, 다른 언어, 전송 형식)를 본다"를 넣는다. 이 검토가 영향 범위 점검을 대신한다.

## 실제 화면 확인

화면 확인은 프로젝트 실행 스킬, 내장 `run`, 브라우저·시뮬레이터 도구 순서로 시도한다. 모두 안 되면 이유를 적고 `inconclusive`로 보고한다.

고위험·비가역 변경은 dry-run, 백업·롤백 가능성, 권한 경계, 실제 대상 재확인을 추가한다. 사용자의 별도 승인 없이는 파괴적 실행을 검증 명목으로 수행하지 않는다.

## 수정 루프 체크포인트

검증에서 실제 결함이 남아 다음 수정이 필요하면 수정 횟수 자체로 중단하지 않는다. 대신 수정이 원래 목적을 향해 진행되는지 주기적으로 재확인한다.

```yaml
RepairLoopPolicy:
  hard_repair_limit: null
  agent_checkpoint_interval: 5
  user_checkpoint_interval: 10
  user_checkpoint_precedence: true
  checkpoint_requires_remaining_work: true
  checkpoint_questions_count_toward_discovery_budget: false
  approval_questions_count_toward_discovery_budget: false
  security_waits_for_checkpoint: false
  repair_requires_unmet_acceptance_criterion: true
  progress_evidence_required: true
  counter_resets_on_checkpoint: false
```

| 검증 결과 | 수정 횟수 | 다음 행동 |
|---|---|---|
| 수용 기준 충족 | 모든 횟수 | `complete` |
| 결함 잔존 | 10의 배수 | `user_checkpoint` |
| 결함 잔존 | 10의 배수가 아닌 5의 배수 | `agent_checkpoint` |
| 결함 잔존 | 그 외 | `continue` |

`repair_attempts_total`은 확인된 결함을 해결하기 위해 산출물·설정·계획을 실질적으로 바꾸고 검증한 횟수다. 변경 없이 같은 검사를 다시 실행하거나, 조사만 수행하거나, 일시적 도구 실패를 재시도한 것은 포함하지 않는다. 같은 작업 안에서는 원인·파일·접근법이 바뀌어도 누적값을 재설정하지 않는다. 사용자가 새 목적을 승인해 별도 실행 계약을 시작할 때만 새 상태를 만든다.

모든 수정은 아직 충족되지 않은 수용 기준이나 재현된 실패에 직접 연결하고, 다음 검증에서 확인할 진전 근거를 먼저 정한다. 연결할 수 없는 선택적 개선과 인접 하드닝은 수정 횟수와 관계없이 현재 작업에서 제외한다.

검증 직후 모든 수용 기준이 충족되면 횟수가 5 또는 10의 배수여도 완료한다. 해결할 결함이 남았으면 다음 순서로 판정한다.

1. `repair_attempts_total % 10 == 0`: 사용자 체크포인트가 우선한다. 원래 목적과 확정 계획, 완료된 내용과 검증 근거, 현재 실패, 지금까지의 수정에서 얻은 새 증거, 다음 수정과 필수성, 범위·권한·보안 변화, 권장 판단을 요약하고 사용자가 계속·재계획·범위 축소·부분 종료를 판단할 때까지 기다린다. 계속하기로 해도 누적값은 재설정하지 않는다.
2. 그 외 `repair_attempts_total % 5 == 0`: 에이전트 체크포인트를 실행한다. 가능하면 원래 요청·확정 계획·현재 증거만 받은 독립 verifier가 판단한다. 다음 수정이 남은 수용 기준에 필수이고 기존 범위 안이며 새 증거나 측정 가능한 진전이 있으면 계속한다. 선택적 개선이나 인접 하드닝이면 현재 작업에서 제외한다. 계획 변경이나 사용자 소유 결정이 필요하면 사용자에게 넘긴다.
3. 그 외: 검증 근거에 따라 다음 국소 수정을 진행한다.

사용자 체크포인트 질문과 실행 중 새 승인·보안 경계를 확인하는 질문은 실행 통제이므로 초기 발견 단계의 `QuestionBudgetState`에 포함하지 않는다. 이 분리는 질문 횟수만 분리할 뿐 승인을 추정하거나 대신하지 않는다. 새 권한, 비밀 접근, 외부 변경, 파괴적 작업 또는 보안 경계 확대는 체크포인트까지 미루지 않고 발견 즉시 사용자 승인을 기다린다.

수정 횟수에 상한은 없지만 동일한 입력·가설·행동을 새 증거 없이 반복하지 않는다. 같은 전제로 거듭 실패하면 다음 시도 전에 그 전제를 한 문장으로 적고 먼저 확인한다. 진전이 없으면 원인을 다시 조사하거나 접근법을 바꾸고, 새 접근도 근거를 만들 수 없으면 검증 불가 blocker로 보고한다.

## 실패 처리

- **국소 결함**: 범위를 유지한 채 수정하고 관련 검증을 다시 실행한다.
- **의도·구조 결함**: 실행을 중단하고 확정 의도 단계로 돌아간다.
- **사용자 결정 누락**: 질문 게이트로 돌아가되 적격성 조건을 다시 적용한다.
- **일시적 실패**: 동일 조건 재시도는 최대 두 번이다. 이후 원인과 대안을 보고한다.
- **검증 불가**: 추측으로 통과 처리하지 않고 부분 완료 또는 blocker로 종료한다.

일시적 실패 재시도는 산출물을 바꾸는 수정 루프와 별개다. 실제 수정은 위 체크포인트 정책을 따르며 같은 원인이라는 이유만으로 중단하지 않는다.

## 결과 기록

`/ha`의 최종 출력은 다음 틀을 따른다. `defaults_taken`에는 `assumptions`를 포함해 묻지 않고 대신 정한 판단을 적고, 확인 절차는 `questioning.md`의 기본값 하한을 따른다. 실제 위임이나 폴백이 없으면 `model_routes`를 생략할 수 있다.

```yaml
result:
  outcome: string
  artifacts: [string]
  defaults_taken: [string]
  user_decisions: [string]
  verification_evidence: [string]
  remaining_risks: [string]
  model_routes: [model_route]
```

검증 결과는 다음 형태로 남긴다.

```yaml
verification:
  criteria: [string]
  evidence: [string]
  result: pass | partial | fail | blocked | inconclusive
  limitations: [string]
  retries: integer
  repair_attempts_total: integer
  checkpoint: none | agent | user
```

사용자에게는 상세 내부 추론이 아니라 결과, 증거, 남은 위험만 전달한다.
