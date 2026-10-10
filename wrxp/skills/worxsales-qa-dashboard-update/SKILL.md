---
name: worxsales-qa-dashboard-update
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-dashboard-update in Claude Code or $wrxp:worxsales-qa-dashboard-update in Codex to rebuild the WorxSales QA round history from every result lane since the first pilot, and update the Notion 상황판 (summary block, round-history and menu-history tables) and the 구현도 dot-plot page. Do not activate for running scenario rows, refreshing sources, or ordinary WorxSales work.
disable-model-invocation: true
---

# WorxSales QA Dashboard Update

QA 실행 결과 폴더(레인)를 **최초 회차부터 전부 다시 모아** 회차 이력과 누적 통계를 만들고, 세 곳에 보입니다.

- Notion 상황판 맨 위의 「📌 현재 요약 (자동 갱신)」 블록
- 상황판 안의 인라인 DB 두 개: 「QA 회차 이력」(회차마다 한 행), 「QA 메뉴별 구현도 이력」(회차·메뉴마다 한 행)
- 「WorxSales QA 진척판」 HTML 페이지: 회차별 구현도 점도표, 메뉴별 구현도 점 이동, 모든 지표의 표

지표 정의와 계산 방식은 [지표 정의](references/metrics.md)에 있습니다. 행 실행, 원천·시나리오 갱신, 상황판 뷰 필터 점검은 이 스킬이 하지 않습니다.

## 원칙

- **매번 처음부터 다시 계산합니다.** 이전 history.json에 덧붙이지 않습니다. 레인 결과가 재검증·재배정으로 바뀌어도 모든 회차가 일관됩니다.
- **마지막 회차는 `check_notion.py`와 같아야 합니다.** 대상 행 수, 판정별 수, 구현도가 다르면 게시하지 않고 원인(레인 우선순위, 미게시 결과, 범위 제외 정리)을 찾습니다.
- **사람이 쓴 내용은 건드리지 않습니다.** 요약 블록은 표지 헤딩부터 다음 구분선까지만 바꾸고, DB 행은 제목(`R<회차> · <레인>`)으로 덮어씁니다.
- 아티팩트는 비공개로 게시됩니다. 다른 사람이 보려면 사용자가 공유해야 한다고 보고에 적습니다.

## 준비

`<skill>`은 이 SKILL.md가 있는 폴더입니다. 작업 디렉터리는 QA 작업 폴더입니다. Notion 키는 `bws-run`으로 주입하고, 인자가 다시 나뉘지 않게 래퍼를 씁니다.

```sh
# refresh/run_dash.sh  (없으면 만들고 chmod +x)
#!/bin/sh
cd "$(dirname "$0")/.." && S=$1 && shift && exec python3 -I <skill>/scripts/$S "$@"
```

`refresh/watch.json`에 다음이 있어야 합니다(refresh 스킬과 같은 파일).
- `lanes`(레인 우선순위 파일 경로), `scenario_db`(`config.json:키`), `dashboard.page_id`
- `history.extra_lanes`: lanes.json에 없는 초기 회차 레인(파일럿 등). lanes.json 뒤의 우선순위로 붙습니다.
- 첫 실행 뒤 스크립트가 채우는 값: `dashboard.history_db_id`, `dashboard.menu_history_db_id`. 첫 게시 뒤 사람이 채우는 값: `dashboard.artifact_url`.

## 절차

1. **이력 계산.** `bws-run refresh/run_dash.sh history.py refresh/watch.json --out refresh/history.json`. 회차마다 한 줄이 출력됩니다. 마지막 줄을 `check_notion.py` 결과와 대조합니다.
2. **진척판 HTML.** `python3 <skill>/scripts/render_html.py refresh/history.json refresh/dashboard/qa-progress.html --notion-url https://www.notion.so/<dashboard.page_id>`. 상황판으로 돌아가는 링크가 페이지에 붙습니다.
3. **진척판 게시.** Artifact 도구로 `refresh/dashboard/qa-progress.html`을 게시합니다.
   - `watch.json`에 `dashboard.artifact_url`이 있으면 그 값을 `url`로 넘겨 같은 주소를 유지합니다. 처음 게시하는 경우에만 `icon`(`chart`)을 넘기고, 결과 주소를 `artifact_url`에 적습니다.
   - 제목은 「WorxSales QA 진척판」으로 유지합니다.
4. **Notion 반영.** `bws-run refresh/run_dash.sh sync_notion.py refresh/watch.json refresh/history.json --dry-run`으로 바꿀 행 수와 요약 블록 교체 수를 보고, 맞으면 `--dry-run` 없이 다시 실행합니다. 두 번 실행해도 행과 블록이 쌓이지 않아야 합니다(교체 수가 「N → N」).
5. **보고.** 마지막 회차의 지표 6묶음(진척, 구현도, 품질, 막힘, 역할, 쓰기 범위 밖), 직전 회차 대비 변화, 구현도가 가장 많이 오르거나 내린 메뉴, 진척판 주소, Notion에 바꾼 행 수를 적습니다. 쓰기 범위 밖 신규 행이 있으면 TC ID를 적습니다.

## 하지 않는 일

- 시나리오 DB의 행이나 판정을 고치지 않습니다. 결과 게시는 QA 실행 스킬과 refresh 스킬의 몫입니다.
- 상황판의 기존 뷰를 바꾸지 않습니다.
- 레인 결과 파일을 고치거나 옮기지 않습니다.
