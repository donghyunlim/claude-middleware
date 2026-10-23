# QA 작업 폴더 구성

QA 작업 폴더(QA_HOME)는 시나리오, 원천 사본, 실행 결과와 설정을 한곳에 둡니다. 모든 QA 스킬은 이 폴더를 작업 디렉터리로 삼습니다. 스크립트는 플러그인 안에 있으므로 작업 폴더에는 데이터와 래퍼만 둡니다.

```
<QA_HOME>/
  config.json              작업 폴더 설정 (아래 표)
  scenarios/GUIDE.md       시나리오 작성 규칙 (references/scenario-guide.md 사본)
  scenarios/menus.json     메뉴 이름 목록 (validate.py·create_db.py가 읽음)
  scenarios/<NN>/<SS>.json 화면별 시나리오, 고친 날의 _changes_/_changed_ids_/_oos_ids_<날짜> 파일
  sources/                 기능정의서·공통 문서 사본(.md), _mockups/, _snapshot_<날짜>/, _stale/
  runs/run-<날짜>-b<커밋>/  레인: WORKER.md, queue.json, batch-NNN.json, <TC>.json, 그림, _tmp/, _reverify/
  refresh/                 watch.json, code_map.json, lanes.json, state.json, write_scope.json, history.json,
                           run.sh, run_dash.sh, dashboard/, <크롤 폴더>/
  docs/DB_만들기.md         시나리오 DB를 만든 방법과 이력 (Notion에 게시)
  scripts/run.sh           bws-run 래퍼 (python3 -I "$@")
  .slots/app-<port>/       앱 슬롯마다 config.json (cdp만 다름)
  .slots/build.json        레인이 없을 때 슬롯 배포에 쓰는 빌드 값(bootstrap)
  .userdata/<port>/        앱 슬롯마다 Electron 사용자 데이터
```

## config.json

| 키 | 뜻 | 누가 씀 |
|---|---|---|
| parent_page_id | QA 페이지들(시나리오 DB, 문서, 상황판)을 둘 Notion 상위 페이지 | 사용자 지정, create_db.py |
| scenario_db_id | 「WorxSales 테스트 시나리오」 DB | create_db.py |
| db_doc_page_id, howto_page_id | `docs/` 문서를 게시한 페이지 | publish_doc.py |
| desktop_repo | worxsales-desktop 저장소(빌드는 이 저장소의 별도 worktree에서 함) | 사용자 지정 |
| desktop_worktree, app_path, build, api_origin | 지금 쓰는 빌드. `app.mjs`는 worktree의 playwright-core를 씀 | build_dev_app.sh, qa_rollout.sh |
| cdp | 이 폴더가 가리키는 앱 슬롯의 CDP 주소 | 슬롯마다 다름 |
| operator_name, operator_employee_code | QA 계정 사용자의 이름과 사번(역할 부여 때 본인 확인용) | 사용자 답, 첫 부여 작업자 |
| own_members | 서비스별 본인 담당 회원 ID `{"JK": …, "AM": …}` | bootstrap 8단계 |

비밀값은 config.json에 두지 않습니다. Notion 키는 bws의 `NOTION_API_KEY`를 `bws-run`으로 주입합니다.

## 앱 슬롯

- 슬롯 하나는 「CDP 포트 하나 + 사용자 데이터 폴더 하나 + 설정 폴더 하나」입니다. 슬롯 `9333`부터 포트를 하나씩 올려 씁니다.
- 설정 폴더는 `.slots/app-<port>/config.json`입니다. 작업 폴더의 config.json과 같고 `cdp`만 그 포트입니다. 작업자는 `QA_HOME=<설정 폴더> node <executor>/scripts/app.mjs …`로 자기 슬롯만 조작합니다.
- 사용자 데이터는 `.userdata/<port>/`입니다. 슬롯마다 따로 두어야 로그인 세션이 섞이지 않고, 다른 세션이 기본 사용자 데이터 폴더로 띄운 개발용 앱과도 부딪히지 않습니다.
- 설정 폴더가 정리 작업으로 지워졌으면 `qa_rollout.sh`가 작업 폴더의 config.json을 바탕으로 다시 만듭니다.

## 래퍼

`init_workspace.sh`가 `scripts/run.sh`, `refresh/run.sh`, `refresh/run_dash.sh`를 씁니다. `bws-run`은 따옴표로 묶은 인자를 다시 나누므로 Notion을 부르는 스크립트는 항상 래퍼를 거칩니다.

```sh
bws-run "$PWD/scripts/run.sh" <bootstrap>/scripts/sync_scenarios.py scenarios <배치 이름>
bws-run "$PWD/refresh/run.sh" crawl.py refresh/watch.json "$S"
bws-run "$PWD/refresh/run_dash.sh" history.py refresh/watch.json --out refresh/history.json
```

래퍼에는 플러그인 버전 경로가 들어갑니다. 플러그인을 업데이트하면 `init_workspace.sh <QA_HOME> --wrappers-only`로 다시 씁니다.

## refresh/ 파일

- `watch.json`, `code_map.json`, `lanes.json`, `state.json`의 형식은 [refresh 작업 폴더 파일](../../worxsales-qa-refresh/references/files.md)이 정본입니다.
- `write_scope.json`의 형식과 규칙은 [쓰기 범위](../../worxsales-qa-all-in-one/references/write-scope.md)가 정본입니다. 템플릿은 `assets/write_scope.json`입니다.
- `history.json`은 dashboard-update가 매번 처음부터 다시 만듭니다. 손으로 고치지 않습니다.

## 레인 폴더의 공용 기록 파일

| 파일 | 내용 |
|---|---|
| `_my_employee_code.txt` | 확인한 본인 사번. 다음 작업자가 다시 찾지 않게 함 |
| `_dev_data_created.txt` | 이 레인에서 만들거나 바꾼 DEV 레코드 한 줄씩(번호, 종류, 회원, 행) |
| `_grant_log.txt` | 권한 부여·회수 한 줄씩(시각, 묶음, 사번·이름, before, after, action) |
| `_published.json` | 게시한 결과 파일의 수정 시각(publish_pending.py) |
| `_selected_ids.txt`, `_selected_why.json` | 이 레인에서 돌릴 행과 고른 이유 |
| `build.json` | 레인이 쓰는 빌드(`app_path`, `desktop_worktree`, `build`) |
