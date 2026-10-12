---
name: worxsales-qa-rerun-not-ok
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-rerun-not-ok in Claude Code or $wrxp:worxsales-qa-rerun-not-ok in Codex to re-run, across all menus, every WorxSales scenario row whose latest verdict is not OK (plus OK rows whose expected result changed after that OK) with worxsales-qa-executor workers on the latest develop build, then publish to Notion. Do not activate for refreshing sources, single rows, or ordinary WorxSales work.
disable-model-invocation: true
---

# WorxSales QA Rerun Not-OK

최신 판정이 **OK가 아닌 모든 행**을 메뉴를 가리지 않고 다시 실행합니다. 코드가 바뀐 메뉴만 고르는 방식과 달리, 「지금 OK가 아닌 것이 여전히 OK가 아닌가」를 전체로 다시 봅니다.

- 대상: 범위 제외가 아닌 행 가운데
  - 결과가 없는 행(미실행)
  - 최신 판정이 OK가 아닌 행: 부분 OK, 미구현, 문제, 실행 불가, 보류-기록, 알려진 차이
  - 최신 판정이 OK이지만 그 결과 이후 기대결과가 바뀐 행(`scenarios/<menu>/_changed_ids_<YYYY-MM-DD>.txt`에 그날 이후 날짜로 오른 행)
- OK 행은 그 밖에는 다시 보지 않습니다. 부분 OK는 확인 못 한 항목이 남은 행이므로 다시 봅니다.

행 실행·판정·증거 규칙은 `worxsales-qa-executor`가 정본입니다. 이 스킬은 고르는 기준과 조율만 정합니다. 조율 규칙(작업자 배치, 묶음 감사, 일시 장애 재배정, 재검증, 게시)과 그 스크립트는 `worxsales-qa-all-in-one`의 `references/orchestration.md`와 `scripts/`를 그대로 씁니다. 쓰기 범위는 같은 스킬의 `references/write-scope.md`와 작업 폴더의 `refresh/write_scope.json`을 따릅니다.

## 절차

`<skill>`은 이 SKILL.md가 있는 폴더, `<skills>`는 그 상위 폴더입니다. 작업 폴더(QA_HOME)에서 실행합니다.

1. **빌드 확인.** develop HEAD가 앱 슬롯의 빌드와 다르면 executor의 `build_dev_app.sh`로 빌드하고, 빌드가 끝났는지(앱 파일이 있는지) 확인한 뒤에만 `<skills>/worxsales-qa-all-in-one/scripts/qa_rollout.sh`로 슬롯을 하나씩 바꿉니다. 모든 슬롯을 바꾼 뒤 같은 폴더의 `prune_builds.sh <desktop repo> <새 빌드 worktree>`로 이전 빌드 worktree를 지웁니다.
2. **행 고르기.** `python3 <skill>/scripts/select_not_ok.py refresh/watch.json --out <lane>/_selected_ids.txt`. 사용자가 메뉴를 지정했으면 `--menus 7,11`을 붙입니다. 출력의 사유별 수를 사용자에게 한 줄로 알립니다.
   - 같은 원인으로 다시 돌려도 결과가 바뀌지 않는 막힘(예: DEV 서버 설정 누락으로 매번 같은 503)은 실행 전에 한 번 직접 확인하고, 그대로면 그 사유의 행을 빼고 뺀 수와 이유를 보고에 적습니다.
3. **레인.** `runs/run-<날짜>-b<커밋 4~5자리>/`를 만들고 큐를 짓습니다: `python3 <skills>/worxsales-qa-all-in-one/scripts/qa_queue.py build <lane> --only-ids <lane>/_selected_ids.txt`. WORKER.md는 all-in-one의 작업자 지시 틀과 직전 레인의 추가 규칙으로 만들고, `lanes.json` 맨 앞에 레인을 넣습니다.
4. **실행 조율.** all-in-one의 조율 규칙대로 합니다. 영업자 행은 슬롯마다 11~20행 묶음, 역할 행은 영업자 묶음과 재검증이 끝난 뒤(이미 있는 부여는 슬롯마다 병렬, 부여 변경이 필요한 묶음은 한 명이 순차로). 묶음마다 감사하고, 「문제」와 「문제」에서 바뀐 판정은 Opus로 재검증해 합칩니다.
5. **게시와 점검.** 작업자가 모두 끝나면 레인의 `_tmp/`를 지웁니다(증거 그림은 레인 폴더 바로 아래라 남습니다). `publish_pending.py`로 모아 게시하고 refresh의 `check_notion.py`로 DB와 대조합니다.
6. **보고.** 고른 행 수(사유별), 실행 행 수, 판정 분포, OK로 바뀐 행 수와 OK에서 내려간 행 수, 재검증 결과, 뺀 행과 이유, 새로 쓰기 범위 밖이 된 행.

## 하지 않는 일

- 원천·시나리오 갱신과 상황판 갱신은 하지 않습니다(그것까지 한 번에 하려면 not-ok 한 바퀴 스킬을 씁니다).
- OK 행을 표본으로라도 다시 돌리지 않습니다. 회귀 확인이 필요하면 사용자가 메뉴·TC를 정해 executor로 따로 돌립니다.
- 쓰기 범위를 넓히지 않습니다.
