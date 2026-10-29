# Verification Policy

이 문서는 `/ha` 계열이 무거운 경로에서 따르는 검증 세부를 정한다. 코드 위임 우선 규칙은 `SKILL.md` 5절에, 가벼운 경로의 검증·대체물·판단 불가·공유 계약 검토·기본 실패 처리·수정 횟수 세는 법은 `SKILL.md` 6절에만 있다.

## Contents

- 검증 기준
- 실제 화면 확인
- 수정 루프 체크포인트
- 검증 불가
- 결과 기록

## 검증 기준

검증 기준은 실행 전에 수용 기준과 위험에서 정하고, 변경 위험과 영향 범위에 비례해 검증 강도를 높인다. 검증하지 못한 항목은 `limitations`에 적는다.

트랙별 핵심 확인은 [tracks.md](tracks.md)를 따른다.

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

`repair_attempts_total`(세는 법은 `SKILL.md` 6절)은 같은 작업 안에서는 원인·파일·접근법이 바뀌어도 누적값을 재설정하지 않는다. 사용자가 새 목적을 승인해 별도 실행 계약을 시작할 때만 새 상태를 만든다.

모든 수정은 아직 충족되지 않은 수용 기준이나 재현된 실패에 직접 연결하고, 다음 검증에서 확인할 진전 근거를 먼저 정한다. 연결할 수 없는 선택적 개선과 인접 하드닝은 수정 횟수와 관계없이 현재 작업에서 제외한다.

| 검증 결과 | 수정 횟수 | 다음 행동 |
|---|---|---|
| 수용 기준 충족 | 모든 횟수 | `complete` |
| 결함 잔존 | 10의 배수 | `user_checkpoint` |
| 결함 잔존 | 10의 배수가 아닌 5의 배수 | `agent_checkpoint` |
| 결함 잔존 | 그 외 | `continue` |

- `user_checkpoint`: 원래 목적과 확정 계획, 완료된 내용과 검증 근거, 현재 실패, 지금까지의 수정에서 얻은 새 증거, 다음 수정과 필수성, 범위·권한·보안 변화, 권장 판단을 요약하고 사용자가 계속·재계획·범위 축소·부분 종료를 판단할 때까지 기다린다. 계속하기로 해도 누적값은 재설정하지 않는다.
- `agent_checkpoint`: 가능하면 원래 요청·확정 계획·현재 증거만 받은 독립 verifier가 판단한다. 다음 수정이 남은 수용 기준에 필수이고 기존 범위 안이며 새 증거나 측정 가능한 진전이 있으면 계속한다. 선택적 개선이나 인접 하드닝이면 현재 작업에서 제외한다. 계획 변경이나 사용자 소유 결정이 필요하면 사용자에게 넘긴다.
- `continue`: 검증 근거에 따라 다음 국소 수정을 진행한다.

사용자 체크포인트 질문과 실행 중 새 승인·보안 경계를 확인하는 질문은 실행 통제이므로 초기 발견 단계의 `QuestionBudgetState`에 포함하지 않는다. 이 분리는 질문 횟수만 분리할 뿐 승인을 추정하거나 대신하지 않는다. 새 권한, 비밀 접근, 외부 변경, 파괴적 작업 또는 보안 경계 확대는 체크포인트까지 미루지 않고 발견 즉시 사용자 승인을 기다린다.

수정 횟수에 상한은 없지만 동일한 입력·가설·행동을 새 증거 없이 반복하지 않는다. 같은 전제로 거듭 실패하면 다음 시도 전에 그 전제를 한 문장으로 적고 먼저 확인한다. 진전이 없으면 원인을 다시 조사하거나 접근법을 바꾸고, 새 접근도 근거를 만들 수 없으면 검증 불가 blocker로 보고한다.

## 검증 불가

검증할 수 없으면 추측으로 통과 처리하지 않고 부분 완료 또는 blocker로 종료한다. 실제 수정은 위 체크포인트 정책을 따르며 같은 원인이라는 이유만으로 중단하지 않는다.

## 결과 기록

`/ha`의 최종 답 틀(`result`)은 `SKILL.md`의 최종 출력 절에 있다. 무거운 경로에서는 그에 더해 검증 결과를 다음 형태로 남긴다.

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
