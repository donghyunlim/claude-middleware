---
name: worxsales-qa-bootstrap
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-bootstrap in Claude Code or $wrxp:worxsales-qa-bootstrap in Codex to set up a WorxSales AI-QA workspace from nothing — create the folder, wrappers and config templates, download the 기능정의서·공통 문서 sources, write scenario rows by menu with the scenario guide, create and sync the Notion scenario DB, create the 상황판 page and views, agree the write scope, build the app and log in the slots, and list the external conditions the user must provide. Do not activate when a QA workspace already exists and only needs refreshing or running, or for ordinary WorxSales work.
disable-model-invocation: true
---

# WorxSales QA Bootstrap

아무 산출물이 없는 상태에서 QA 작업 폴더를 만들고, 다른 QA 스킬이 바로 돌 수 있는 상태까지 준비합니다. 같은 원천을 읽으면 행의 표현은 달라도 메뉴·화면·역할 축과 기대결과의 본질은 같게 나오도록, 규칙과 스크립트를 이 스킬에 담았습니다. 행 실행은 하지 않습니다.

## 원칙

- **문서에 있는 것만 씁니다.** 시나리오는 [시나리오 작성 규칙](references/scenario-guide.md)의 근거 우선순위를 따르고, 문서에 없는 동작을 지어내지 않습니다.
- **작성과 검토를 나눕니다.** 시나리오를 쓴 에이전트가 아닌 에이전트가 표본을 원문과 대조합니다.
- **기존 것을 덮지 않습니다.** 스크립트는 이미 있는 파일·DB·페이지를 다시 만들지 않습니다. 작업 폴더가 이미 있으면 빠진 것만 채우고, 최신화는 QA 최신화(refresh) 스킬에 넘깁니다.
- **값은 작업 폴더에 둡니다.** Notion ID, 본인 메일·전화번호, 사번, 회원 ID 같은 값은 스킬이 아니라 `config.json`, `refresh/*.json`에 둡니다. 비밀값은 bws에만 둡니다.
- 사용자의 결정이 필요한 것(상위 페이지 위치, 쓰기 범위, 외부 조건)은 선택지 도구로 한 번에 묻고 답을 그대로 기록합니다.

## 준비물

`<skill>`은 이 SKILL.md가 있는 폴더입니다. 사용자에게 받을 것은 다음과 같습니다.
- QA 작업 폴더 위치, worxsales-desktop 저장소 경로
- Notion: 기능정의서 최상위 페이지, 목업 DB, 상위 작업 공간, QA 페이지를 둘 상위 페이지(integration 공유 포함)
- 공통 문서 4종의 페이지 ID: 역할·권한 정리, 화면·모달 인벤토리(CBT 제공 범위), 정책 확인 필요 목록(또는 정책 결정 DB), 용어사전. 사용자가 모르면 기능정의서 최상위 아래에서 제목으로 찾아 후보를 보여 주고 확인을 받습니다.
- bws의 `NOTION_API_KEY`(키 이름만 확인합니다)
- 이 세션의 Notion MCP 연결(상황판 뷰 생성에 씁니다). 스크립트로는 확인할 수 없으므로, Notion MCP 도구로 상위 페이지를 한 번 읽어 연결을 확인합니다. 연결이 없으면 사용자에게 연결을 요청하고, 그동안 뷰 없이 나머지를 진행합니다.

## 절차

진행 상황은 단계마다 한 줄로 알립니다.

1. **작업 폴더.** `sh <skill>/scripts/init_workspace.sh <QA_HOME>`으로 폴더, 래퍼, 템플릿을 만들고 `config.json`과 `refresh/watch.json`의 자리표시자를 채웁니다. 형식은 [작업 폴더 구성](references/workspace.md)에 있고, refresh 스킬 스크립트의 명령은 그 문서의 「래퍼」 절을 따릅니다. `sh <skill>/scripts/check_env.sh <QA_HOME>`으로 도구와 키 이름을 확인합니다.
2. **원천 받기.** `fetch_spec.py`로 공통 문서 4종을 시나리오 규칙이 찾는 폴더 이름으로 받습니다.
   ```sh
   R="bws-run $PWD/scripts/run.sh <skill>/scripts/fetch_spec.py"
   $R <역할·권한 정리 ID> sources/common
   $R <화면 인벤토리 ID> sources/common_inventory
   $R <정책 확인 목록 ID> sources/common_policy
   $R <용어사전 ID> sources/common_glossary
   $R <메뉴 페이지 ID> sources/<NN_메뉴이름>      # 기능정의서 최상위의 메뉴 페이지마다
   ```
   메뉴 페이지 제목으로 `scenarios/menus.json`을 맞춥니다. 이어서 refresh 스킬을 첫 실행(이전 크롤 없음)으로 돌려 빠진 원천(정책 결정 DB 행, 최상위 안내 페이지 등 `local_missing`)을 채우고 기준점을 만듭니다. 명령은 refresh 스킬 `references/commands.md`의 1~3·7단계와 같습니다: `crawl.py` → `diff_sources.py`(`--prev` 없이) → `apply_sources.py` dry run 확인 → `apply_sources.py … --apply` → `_unmapped/`에 들어간 파일을 메뉴 폴더로 옮김 → `state.py commit --manifest <크롤 폴더>`.
3. **목업.** 목업 DB에서 버전 번호가 가장 높은 파일을 `sources/_mockups/`에 받고 `watch.json`의 `mockup.used_version`에 적습니다. 목업은 참고 자료입니다.
4. **시나리오 작성.** 메뉴를 묶음으로 나눠 에이전트에게 맡깁니다. 각 에이전트에게 `scenarios/GUIDE.md`, 공통 문서, 담당 화면 원문의 경로만 줍니다. 쓴 뒤 다른 에이전트가 메뉴마다 표본을 원문과 대조하고, 결과를 `docs/DB_만들기.md` 이력 표에 적습니다. `python3 <skill>/scripts/validate.py scenarios`가 오류 0이어야 다음 단계로 갑니다.
5. **Notion.** [Notion 준비](references/notion.md)대로 시나리오 DB를 만들고(`create_db.py`), `sync_scenarios.py scenarios <배치 이름>`으로 올린 뒤(`--dry-run`으로 먼저 행 수 확인), 행 몇 개를 다시 읽어 글자와 칸을 확인합니다. `docs/DB_만들기.md`를 게시하고, 상황판 페이지(`create_dashboard_page.py`)와 뷰를 만듭니다.
6. **쓰기 범위.** `refresh/write_scope.json` 템플릿은 「조회·차단 확인만」입니다. 템플릿의 `_examples`를 보여 주며 넓힐 조작, 본인 메일·전화번호(`self`), DEV·STG 과감한 시험 허용 여부를 묻고, 사용자가 답한 항목만 `allowed`로 옮기고 답을 `decisions`에 원문 그대로 적습니다. 답이 없으면 기본값 그대로 둡니다. 규칙의 정본은 QA 한 바퀴 스킬의 `references/write-scope.md`이며 [작업 폴더 구성](references/workspace.md#refresh-파일)에서 연결됩니다.
7. **코드 지도.** refresh 스킬의 `code_changes.py`를 develop 최근 커밋 범위로 한 번 돌려 `UNMAPPED` 경로를 `refresh/code_map.json`에 메뉴 번호로 채웁니다. 제품 화면이 아닌 폴더는 `[]`입니다.
8. **앱과 슬롯.** [앱 준비](references/app-setup.md)대로 develop을 빌드하고, 빌드 결과로 `.slots/build.json`을 쓴 뒤 슬롯을 하나씩 띄워 DEV로 로그인합니다. 레인은 아직 만들지 않습니다(첫 레인은 QA 한 바퀴 스킬이 만듭니다). 본인 이름·역할·담당 회원을 화면에서 확인해 `config.json`에 적습니다.
9. **외부 조건.** [외부 조건](references/external-deps.md)의 항목마다 지금 상태를 확인하고, 막히는 행 수를 셉니다(시나리오의 `external`, `run_mode`, 화면 메뉴로 어림). 사용자가 해 줄 일을 풀리는 행 수가 많은 순서로 적습니다.
10. **보고와 인계.** 만든 것, 쓰기 범위, 외부 조건, 첫 실행 권장을 보고합니다. 실행은 사용자가 QA 한 바퀴 스킬을 호출할 때 시작합니다([인계](references/app-setup.md#4-인계)).

## 하지 않는 일

- 기능정의서·목업·코드 원본을 고치지 않습니다.
- 행을 실행하거나 판정하지 않습니다. 앱에서는 로그인과 본인 정보 확인만 합니다.
- 사용자 답 없이 쓰기 범위를 기본값보다 넓히지 않습니다.
- MC 비밀번호 입력, 처음 보는 OAuth 동의, MAGMA DB 쓰기를 대신하지 않습니다.
