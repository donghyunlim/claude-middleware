---
name: worxsales-qa-all-in-one
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-all-in-one in Claude Code or $wrxp:worxsales-qa-all-in-one in Codex to run the whole WorxSales QA cycle in one go — worxsales-qa-refresh (sources, mockups, develop code, scenario DB), then re-running the changed and not-yet-OK rows with worxsales-qa-executor workers in the real app, then worxsales-qa-dashboard-update for the 상황판 history. Do not activate for a single step, ordinary WorxSales development, or scenario writing.
disable-model-invocation: true
---

# WorxSales QA All-in-One

QA 한 바퀴를 순서대로 돕니다.

1. `worxsales-qa-refresh`: 기획서·목업·develop 코드·시나리오 DB·상황판 뷰를 최신으로 맞추고 다시 돌릴 행을 고릅니다.
2. `worxsales-qa-executor`: 고른 행을 작업자 에이전트가 실제 앱에서 한 행씩 실행하고 Notion에 게시합니다. 이 스킬은 **조율만** 합니다.
3. `worxsales-qa-dashboard-update`: 최초 회차부터 회차 이력을 다시 모아 상황판 요약·이력 표와 진척판을 갱신합니다.

각 단계의 세부 규칙은 해당 스킬의 SKILL.md가 정본입니다. 이 스킬은 순서, 단계 사이에 넘기는 값, 조율 규칙, 끝에 묻는 질문만 정합니다. 단계를 시작할 때 그 스킬의 SKILL.md를 다시 읽습니다.

## 쓰기 범위

- 실행 단계의 쓰기 범위는 `refresh/write_scope.json`을 따릅니다. 파일이 없으면 [쓰기 범위](references/write-scope.md)의 기본값(2026-10-10에 사용자가 허락한 범위)으로 만들고 보고에 적습니다.
- 기본값을 넘는 조작(실제 발송, 전화, 세그먼트 「적용하기」, 다른 사람 데이터 수정, 다른 사람에게 권한 부여)은 이 스킬이 스스로 허락하지 않습니다. 해당 행은 「실행 불가」(이번 실행의 쓰기 범위 밖)로 남습니다.
- 기획 범위가 늘어 새로 쓰기 범위 밖이 된 행이 생기면, 끝에서 그 조작을 허용할지 **한 번** 묻습니다(절차 7).

## 절차

진행 상황은 단계마다 한 줄씩 알립니다. `<skill>`은 이 SKILL.md가 있는 폴더입니다. 조율 스크립트는 모두 `<skill>/scripts/`에 있어 작업 폴더에 따로 둘 필요가 없습니다.

1. **최신화.** `worxsales-qa-refresh`의 절차 1~6을 그대로 따릅니다. 원천 루트가 열리지 않거나 보관되었으면 여기서 멈추고 묻습니다. 이 스킬 안에서는 refresh의 7단계(기준점 갱신)를 실행 단계 뒤로 미룹니다.
2. **재실행 행 고르기.** refresh의 [재실행 행 고르기] 기준으로 대상 행을 고릅니다: 런타임 파일이 바뀐 메뉴의 OK가 아닌 행, 기대결과가 바뀌었거나 새로 생긴 행, 아직 실행하지 않은 행. 대상이 없으면 3~5단계를 건너뛰고 6단계로 갑니다.
3. **레인과 앱 준비.** 새 커밋이 있으면 executor의 `build_dev_app.sh`로 빌드하고, 쉬는 슬롯마다 `<skill>/scripts/qa_rollout.sh <port> <작업 폴더> <build.json>`으로 새 빌드를 띄웁니다. `build.json`은 빌드의 `app_path`·`desktop_worktree`·`build`를 담아 조율자가 레인 폴더에 씁니다. `runs/run-<날짜>-b<커밋 4~5자리>/`를 만들고, [작업자 지시 틀](references/worker-template.md)을 복사해 자리표시자(`{RUN_ID}` 등)를 채우고 「Write scope」 절을 `write_scope.json`대로 씁니다. 직전 레인의 WORKER.md에 그 뒤 더해진 규칙이 있으면 함께 옮깁니다. `lanes.json` 맨 앞에 넣습니다.
4. **실행 조율.** [조율 규칙](references/orchestration.md)을 따릅니다. 요지는 다음과 같습니다.
   - 작업자는 Sonnet 에이전트입니다. 조율자는 행을 직접 실행하지 않습니다.
   - 영업자 행은 11~20행 묶음으로 앱 슬롯마다 한 작업자에게 맡깁니다. 역할 행은 영업자 묶음이 모두 끝난 뒤 작업자 한 명이 순차로 실행합니다.
   - 묶음이 끝날 때마다 감사하고, 일시 장애·배포 직후 실패는 조율자가 직접 다시 확인한 뒤 재배정합니다.
   - 「문제」와 「문제」에서 바뀐 판정은 Opus 재검증 후 합칩니다.
5. **게시.** 레인 결과를 오래된 레인부터 게시하고, `check_notion.py`로 최신 결과와 DB가 맞는지 확인합니다.
6. **상황판과 기준점.** `worxsales-qa-dashboard-update` 절차 1~4를 실행합니다. 마지막 회차가 `check_notion.py`와 같으면 refresh의 7단계(`state.py commit`)를 실행합니다. 이번에 테스트한 커밋을 `--code`로 넘깁니다.
7. **보고와 질문 하나.** 다음을 나눠 적습니다.
   - 최신화: 원천·목업·코드·시나리오 변경 수, 확인 필요 항목
   - 실행: 레인, 행 수, 판정 분포, 직전 판정에서 바뀐 행 수, 재검증 결과
   - 상황판: 구현도와 직전 회차 대비 변화, 진척판 주소(`dashboard.publish.url`, 없으면 로컬 파일 경로)
   - 쓰기 범위 밖: **현재** 행 수와 **이번 회차 신규** 행 수(history.json 마지막 회차의 `write_blocked`, `write_blocked_new`). 신규 행은 TC ID와 막힌 조작을 적습니다.

   신규 쓰기 범위 밖 행이 있으면 선택지 도구로 한 번만 묻습니다: 그 조작을 다음 실행부터 허용할지, 지금처럼 「실행 불가」로 둘지. 허용하면 `write_scope.json`에 조작·날짜·사용자 답을 적고, 해당 행만 다음 실행에서 돌린다고 알립니다. 금지 목록의 조작(실제 고객 발송, 전화)은 사용자가 대상과 방법을 명시하지 않으면 허용으로 기록하지 않습니다.

## 하지 않는 일

- 단계 스킬의 규칙을 줄이거나 건너뛰지 않습니다. 시간이 걸려도 refresh는 루트부터 전부 읽습니다.
- 사용자 답 없이 쓰기 범위를 넓히지 않습니다.
- 행을 조율자가 직접 판정하지 않습니다. 감사·재확인은 판정을 바꾸지 않고 재배정만 합니다.
