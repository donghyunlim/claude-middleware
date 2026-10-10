# 조율 규칙

조율자(이 스킬을 실행하는 메인 세션)는 큐·묶음·감사·재배정·게시만 합니다. 행 실행과 판정은 작업자가 `worxsales-qa-executor` 규칙대로 합니다. 2026-10-10까지의 실제 운영에서 얻은 규칙입니다.

## 조율 스크립트 (`<skill>/scripts/`)

작업 폴더(QA_HOME)에서 실행합니다. `<run_dir>`는 `runs/run-…/`입니다.

| 스크립트 | 용도 |
|---|---|
| `qa_queue.py build <run_dir> [--exclude-run DIR] [--only-ids FILE]` | 대상 행으로 `queue.json` 작성. `--only-ids`는 재실행으로 고른 TC ID 목록. 역할·권한 순서로 정렬 |
| `qa_queue.py next <run_dir> <n> [--group=역할/권한]` | 다음 묶음 파일 작성, 경로 출력 |
| `qa_queue.py status <run_dir>` | 완료·대기·판정별 수 |
| `qa_rollout.sh <port> <작업 폴더> <build.json>` | 쉬는 앱 슬롯을 그 빌드로 다시 띄우고 DEV 로그인. 9333 외 슬롯의 사용자 데이터는 `$QA_USERDATA_ROOT/<port>`(기본 `<작업 폴더>/.userdata`). 종료 코드 4는 사람이 로그인해야 함 |
| `publish_pending.py <run_dir> list / mark <ids>` | 게시 안 된 결과 목록, 게시 기록 |
| `merge_reverify.py <reverify_dir> <run_dir>` | 재검증 결과를 원래 결과에 합침 |

큐 도구는 묶음 파일에 들어간 행을 「이미 배정됨」으로 봅니다. 다시 맡길 행은 새 묶음 파일로 직접 만듭니다.

## 작업자 배치

- 앱 슬롯(CDP 포트 9333~)마다 작업자 한 명입니다. 작업자는 Sonnet 에이전트이고, 프롬프트에 레인 WORKER.md 경로, 묶음 파일, 포트를 줍니다.
- 영업자 행: 11~20행 묶음. 메뉴가 섞이지 않게 자릅니다.
- 역할 행(팀장·영업운영·조회만·권한 관리자): 영업자 묶음이 모두 끝난 뒤 작업자 **한 명**이 순차로 실행합니다. 역할은 한 계정에 걸리므로 병렬로 바꾸면 다른 작업자의 판정이 오염됩니다. 첫 행에서 역할 확인 신호(`role_sanity`)를 남기게 합니다.
- 작업자는 자기 묶음의 결과·그림과 자기 `_tmp/batch-<NNN>/`만 씁니다. 다른 파일은 지우거나 옮기지 않습니다.

## 묶음 감사

묶음이 끝날 때마다 확인합니다.
- 행마다 자기 그림이 있고, 시작·종료 시각이 행마다 다릅니다(한꺼번에 찍은 결과가 아님).
- 직전 판정이 「문제」였는데 바뀐 행에는 근거 문구가 있습니다.
- 역할 행의 첫 결과에 `role_sanity`가 있습니다.

어긋난 묶음은 `_rejected/`로 옮기고 다시 맡깁니다.

## 일시 장애·배포 직후 실패

- 한 화면의 조회가 계속 실패하고 다른 화면은 정상이면, 조율자가 앱 bridge나 화면 검색으로 같은 조회를 직접 다시 합니다.
- 지금 정상이면 일시 장애로 보고 해당 결과(장애 때문에 「부분 OK」가 된 행 포함)를 `_superseded/<사유>-<날짜시각>/`로 옮기고 새 묶음으로 다시 맡깁니다. 결과는 지우지 않습니다.
- 지금도 실패하면 서버 측 막힘으로 두고 보고에 적습니다(예: `LEAD_POPULATION_NOT_CONFIGURED`, `CORE_SOURCE_UNAVAILABLE`).
- 앱이 응답하지 않으면 그 슬롯만 `qa_rollout.sh`로 다시 띄웁니다. 와일드카드 종료(`pkill`, `killall`)는 쓰지 않습니다.

## 재검증

- 대상: 이번 레인에서 「문제」인 행, 직전 판정이 「문제」였는데 바뀐 행.
- 작업자는 Opus 에이전트, 규칙은 executor의 `references/reverify.md`입니다. 결과는 `<run_dir>/_reverify/`에 쓰고 `merge_reverify.py`로 합친 뒤 게시합니다.

## 게시

- 앱 슬롯이 Notion 쓰기를 기다리지 않게, 묶음 몇 개가 쌓이면 조율자가 `publish_pending.py list`로 모아 executor의 `publish_results.py --only <ids>`로 한 번에 올리고 `mark`합니다.
- 레인 사이의 덮어쓰기는 오래된 레인부터 게시해 최신 레인이 마지막에 오게 합니다.
