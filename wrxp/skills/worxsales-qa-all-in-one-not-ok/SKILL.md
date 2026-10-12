---
name: worxsales-qa-all-in-one-not-ok
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-all-in-one-not-ok in Claude Code or $wrxp:worxsales-qa-all-in-one-not-ok in Codex to run the whole WorxSales QA cycle with a not-OK rerun — worxsales-qa-refresh (sources, mockups, develop code, scenario DB), then worxsales-qa-rerun-not-ok (every row whose latest verdict is not OK, across all menus), then worxsales-qa-dashboard-update. Do not activate for a single step or ordinary WorxSales work.
disable-model-invocation: true
---

# WorxSales QA All-in-One Not-OK

`worxsales-qa-all-in-one`과 같은 한 바퀴이지만, 실행 단계가 다릅니다. 코드가 바뀐 메뉴의 행만 고르지 않고 **OK가 아닌 모든 행**을 `worxsales-qa-rerun-not-ok`로 다시 돌립니다.

1. `worxsales-qa-refresh` 절차 1~6: 원천·목업·코드·시나리오 DB·상황판 뷰를 최신으로 맞춥니다. 시나리오를 고치면 메뉴마다 `scenarios/<menu>/_changed_ids_<YYYY-MM-DD>.txt`(고치거나 추가한 TC ID)와 `_oos_ids_<YYYY-MM-DD>.txt`(범위 제외로 바꾼 TC ID)를 남깁니다. 다음 단계가 이 파일로 기대결과가 바뀐 OK 행을 찾습니다. refresh의 7단계(기준점 갱신)는 6단계 뒤로 미룹니다.
2. `worxsales-qa-rerun-not-ok` 절차 1~5: 최신 빌드, OK가 아닌 행 고르기, 레인, 실행 조율, 게시와 점검.
3. `worxsales-qa-dashboard-update` 절차 1~4: 회차 이력, 진척판, Notion 상황판.
4. 마지막 회차가 `check_notion.py`와 같으면 refresh 7단계(`state.py commit`)를 실행합니다. 이번에 테스트한 커밋을 `--code`로 넘깁니다.
5. 보고와 질문 하나: `worxsales-qa-all-in-one`의 7단계와 같습니다(최신화, 실행, 상황판, 쓰기 범위 밖 현재·신규). 신규 쓰기 범위 밖 행이 있으면 그 조작을 허용할지 한 번만 묻고, 답을 `refresh/write_scope.json`에 적습니다.

각 단계의 세부 규칙은 해당 스킬의 SKILL.md가 정본입니다. 단계를 시작할 때 그 스킬의 SKILL.md를 다시 읽습니다.

## 하지 않는 일

- 단계 스킬의 규칙을 줄이거나 건너뛰지 않습니다. refresh는 루트부터 전부 읽습니다.
- 사용자 답 없이 쓰기 범위를 넓히지 않습니다.
- 행을 조율자가 직접 판정하지 않습니다.
