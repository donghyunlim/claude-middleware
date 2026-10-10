---
name: worxsales-qa-refresh
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-refresh in Claude Code or $wrxp:worxsales-qa-refresh in Codex to bring the WorxSales QA workspace up to date — re-crawl the 기능정의서 and mockup roots from the top, detect new/changed/moved pages and newer mockup versions, apply them to sources and scenarios, find code changes on develop by menu, choose rows to re-run, and verify the Notion scenario DB and 상황판. Do not activate for ordinary WorxSales development or for running scenario rows.
disable-model-invocation: true
---

# WorxSales QA Refresh

시간이 지나며 바뀌는 다섯 가지를 한 번에 따라잡습니다: **기획서(기능정의서)**, **목업(버전업)**, **develop 코드**, **Notion 시나리오 DB**, **Notion 상황판**. 결과는 갱신된 `sources/`·`scenarios/`, 다시 돌릴 행 목록, Notion 점검 결과와 짧은 보고입니다. 행 실행 자체는 이 스킬이 하지 않습니다. 사용자가 QA 실행 스킬을 따로 호출해 진행합니다.

## 원칙 (효율보다 누락 방지)

- **매번 루트부터 전부 다시 읽습니다.** 상위 페이지의 `last_edited_time`은 하위 페이지가 바뀌어도 바뀌지 않고, 새 페이지는 열·토글·동기화 블록 안이나 DB 행으로도 생깁니다. 지난번 하위 페이지 목록만 다시 확인하는 방식은 쓰지 않습니다.
- **모르는 것은 「확인 필요」입니다.** 로컬 사본이 없는 페이지, 페이지가 사라진 로컬 파일, 열 수 없는 페이지, 크롤 범위 밖으로 나가는 링크, 키워드에 맞는 새 페이지, 지도에 없는 코드 경로는 모두 보고에 올립니다. 무시하려면 `watch.json`의 `ignore`에 ID와 이유를 적습니다.
- **최신 버전은 번호로 정합니다.** 첨부 목록의 순서나 「최신」이라는 제목을 믿지 않습니다(2026-10-10 실제 사례: 목록 맨 앞이 v1.8.3, 실제 최신은 v1.9, 문서에는 「v1.7 동결」).
- **기준점은 성공한 뒤에만 옮깁니다.** `state.py commit`은 마지막 단계입니다. 중간에 실패하면 다음 실행이 같은 기준점과 다시 비교하므로 반영 누락이 남지 않습니다.
- 루트 페이지 자체가 열리지 않거나 보관(archive)되었으면 진행하지 않고 사용자에게 새 위치를 묻습니다.

## 준비

경로 표기: `<skill>`은 이 SKILL.md가 있는 폴더입니다. 작업 디렉터리는 QA 작업 폴더(`config.json`, `scenarios/`, `sources/`, `runs/`가 있는 곳)입니다. Notion 키는 `bws-run`으로 주입하고, `bws-run`이 인자를 다시 나누므로 래퍼 `refresh/run.sh <script.py> args…`를 거칩니다(없으면 [작업 폴더 파일](references/files.md)대로 만듭니다).

QA 작업 폴더의 `refresh/`에 다음 파일이 있어야 합니다. 형식은 [작업 폴더 파일](references/files.md)에 있습니다.
- `watch.json`: 크롤 루트, 목업 파일 이름 규칙과 현재 쓰는 버전, 코드 저장소, 상황판 뷰 목록, `ignore`
- `code_map.json`: 코드 경로 접두어 → 시나리오 메뉴 번호
- `lanes.json`: 실행 결과 폴더 우선순위(최신 먼저)
- `state.json`: 마지막으로 성공한 크롤, 마지막으로 테스트한 코드 커밋, 목업 버전 (`state.py`가 관리)

## 절차

진행 상황은 단계별로 한 줄씩 사용자에게 알립니다. 각 단계의 명령은 [명령 모음](references/commands.md)에 있습니다.

1. **원천 전체 크롤.** `crawl.py`로 `refresh/<YYYY-MM-DD-HHMM>/`에 manifest와 페이지 본문을 씁니다. 기능정의서 트리는 수백 번 API를 호출하므로 백그라운드로 돌리고 기다리는 동안 5단계(코드)를 먼저 봅니다.
2. **변경 판정.** `diff_sources.py`를 `state.json`의 manifest와 비교해 돌립니다(첫 실행이면 `--prev` 없이 로컬 사본과만 대조). 항목별 처리는 [변경 항목 처리표](references/change-types.md)를 따릅니다. `errors`(열 수 없는 페이지)는 integration 공유 누락일 수 있으니 사용자에게 알립니다.
3. **원천 반영.** `apply_sources.py`를 먼저 dry run으로 보고, 맞으면 `--apply`로 반영합니다. 옛 파일은 `sources/_snapshot_<날짜>/`에, 사라진 페이지의 파일은 `sources/_stale/`에 남습니다. `_unmapped/`에 들어간 파일은 메뉴 폴더를 정해 직접 옮깁니다. 새 목업 버전은 `sources/_mockups/`에 HTML과 텍스트로 받고, 쓰던 버전의 텍스트와 비교해 바뀐 화면을 적습니다.
4. **시나리오 갱신.** 바뀐 원천 파일만 대상으로 `scenarios/GUIDE.md`의 「기존 행 고치기」를 따릅니다: TC ID 유지, 맞지 않게 된 행은 「범위 제외」, 새 동작은 새 TC ID. 화면이 많으면 메뉴 단위로 에이전트에게 나누고, 작성에 참여하지 않은 에이전트가 표본을 원문과 대조합니다. `validate.py` 후 `sync_scenarios.py`로 DB에 반영합니다. 목업은 순위 3(참고)이며 기능정의서와 다르면 기능정의서를 따릅니다. 새 목업을 검토했으면 `watch.json`의 `mockup.used_version`과 `docs/DB_만들기.md`의 원천 표를 고칩니다.
5. **코드 변경.** `code_changes.py`를 `state.json`의 `code_commit`(없으면 `lanes.json` 첫 레인의 빌드 커밋)부터 돌립니다. 런타임 파일과 테스트 전용 파일을 나눠 보고, `unmapped` 경로는 `code_map.json`에 메뉴를 정해 넣은 뒤 다시 돌립니다. 바뀐 메뉴가 있으면 [재실행 행 고르기](references/rerun.md)대로 새 레인을 만듭니다. 실행은 사용자가 쓰기 범위를 정해 QA 실행 스킬을 따로 호출할 때 합니다. 레인을 만들면 `lanes.json` 맨 앞에 넣습니다.
6. **Notion 점검.**
   - 결과 게시: 레인 결과는 오래된 레인부터 게시해 최신 레인이 마지막에 덮어쓰게 합니다.
   - `check_notion.py`: 시나리오와 DB 행 수, 정책 상태·기대결과, 행별 최신 결과와 DB 판정·빌드, 범위 제외 행의 남은 판정, 선택지 누락을 봅니다. 범위 제외 행에 남은 판정은 `--fix-out-of-scope`로 정리합니다.
   - 상황판: REST로는 뷰를 읽을 수 없으므로 Notion MCP로 `watch.json`의 `dashboard.page_id`를 열어 뷰마다 확인합니다. [상황판 점검표](references/dashboard.md)를 따릅니다.
   - 시나리오를 바꿨으면 `docs/DB_만들기.md` 이력 표에 한 줄을 더하고 `publish_doc.py`로 게시합니다.
7. **기준점 갱신.** 2단계를 새 manifest 기준으로 다시 돌려 남은 항목이 `ignore`로 설명된 것뿐이고, `check_notion.py`의 남은 항목이 진행 중인 레인의 미게시 결과뿐일 때 `state.py commit`을 실행합니다. 그 전에는 commit하지 않습니다.
8. **보고.** 원천(추가·수정·이동·삭제, 목업 버전), 코드(커밋 범위, 메뉴별 파일 수), 시나리오(신규·수정·범위 제외 수), 재실행(레인, 행 수), Notion(불일치 수, 정리한 항목, 상황판 수정)을 나눠 적고, 확인 필요로 남긴 항목과 이유를 적습니다.

## 하지 않는 일

- 기능정의서·목업·코드 원본을 고치지 않습니다. 읽기만 합니다.
- 사용자가 정하지 않은 쓰기 범위로 행을 실행하지 않습니다. 실행 규칙은 QA 실행 스킬을 따릅니다.
- `ignore`에 이유 없이 항목을 넣지 않습니다. 사용자가 정한 제외만 넣습니다.
