---
name: worxsales-qa-executor
description: Use only when the user explicitly invokes /wrxp:worxsales-qa-executor in Claude Code or $wrxp:worxsales-qa-executor in Codex to run WorxSales test-scenario rows against the real Electron app — operate the app per row, judge the result, capture numbered red-box evidence, and publish a readable result to the Notion scenario DB. Do not activate for ordinary WorxSales development, unit or e2e test work, or scenario writing without explicit invocation.
disable-model-invocation: true
---

# WorxSales QA Executor

WorxSales 테스트 시나리오 DB의 행을 **로그인된 실제 Electron 앱**에서 한 행씩 실행합니다. 에이전트가 행을 읽고, 화면을 보며 조작하고, 판정하고, 번호 박스 증거를 남깁니다. 결과는 사람이 읽는 층과 개발자용 상세 층으로 나눠 Notion에 반영합니다.

행마다 locator를 미리 뽑거나 Playwright 스크립트로 굳히지 않습니다. UI가 바뀔 때마다 다시 만들어야 하기 때문입니다. 시나리오의 버튼·필드 이름이 앱과 다르면 같은 개념의 요소를 화면에서 찾아 진행하고, 그 대응을 관찰로 기록합니다.

## 호출과 범위

- 사용자가 명시적으로 호출한 경우에만 실행합니다. 다른 스킬·훅·전역 규칙에 연결하지 않습니다.
- 입력: 실행할 행(TC ID 목록, 메뉴·화면·필터 조건, 또는 행 JSON 파일)과 **이번 실행의 쓰기 범위**.
  - 쓰기 범위를 사용자가 정하지 않았으면 「조회·차단 확인만」으로 실행합니다.
  - 「조회·차단 확인만」: 실제 저장·등록·수정·삭제·발송·전화·MAGMA 요청·역할 전환·권한 부여를 하지 않습니다. 필수값을 비운 상태의 저장 시도만 허용합니다.
  - 저장 범위를 넓히는 것, dev 역할 부여, 외부 영향 행 실행은 사용자가 그 실행에 대해 명시한 경우에만 합니다. 이전 실행의 허락을 다음 실행으로 넘기지 않습니다.
- dev는 다른 TF원도 쓰는 공용 환경입니다. 허용된 저장을 할 때는 `QA-` 접두어 값을 쓰고, 생성한 번호를 결과에 남깁니다.

## 준비

경로 표기: `<skill>`은 이 SKILL.md가 있는 폴더입니다(예: 플러그인 캐시의 `.../wrxp/<버전>/skills/worxsales-qa-executor`). 스크립트는 항상 `<skill>/scripts/…`로 부르고, 작업 디렉터리는 QA 작업 폴더(`config.json`이 있는 곳)로 둡니다.

[실행 환경](references/environment.md)을 읽고 다음을 확인합니다.
1. QA 작업 폴더에 `config.json`이 있고 `app_path`·`desktop_worktree`가 유효한지 확인합니다. 없으면 `<skill>/scripts/build_dev_app.sh`로 빌드합니다.
2. 먼저 `node <skill>/scripts/app.mjs text body`를 실행합니다. 결과에 「역할 전환」이 보이면 이미 로그인된 앱이 CDP로 떠 있는 것이므로 그대로 씁니다. 다시 띄우면 메모리의 세션이 사라집니다.
3. 2단계가 실패하거나(앱 없음·CDP 없음) 인증 화면이 나오면 그때만 `<skill>/scripts/launch_app.sh`를 실행합니다. 결과는 `ready` 또는 `login needed`입니다. `login needed`면 사용자에게 브라우저에서 포탈 계정으로 로그인해 달라고 요청하고 기다립니다.
4. 현재 역할·서비스를 실행 문맥으로 기록합니다.

앱은 한 개뿐이라 행을 동시에 실행하지 않습니다. 여러 행은 순서대로 실행합니다. 서브에이전트에 맡길 때도 실행자는 하나만 둡니다.

## 행마다 하는 일

1. **읽기**: 행의 사전조건·절차·입력값·비울 값·기대결과·검증 지점·근거를 읽습니다. 기대결과의 범위가 애매하면 근거 원문(`sources/`)의 해당 조항을 확인합니다. 행이 근거보다 넓게 기대하면 근거를 기준으로 판정하고 `scenario_issue`에 적습니다.
2. **준비**: 행의 역할·권한 수준·서비스와 현재 앱 문맥을 대조합니다. 맞지 않고 바꿀 권한도 없으면 「실행 불가」로 둡니다. 사전조건 데이터는 앱 화면에서 직접 찾습니다(검색·목록·상세). 찾지 못하면 「실행 불가」로 두고 무엇이 필요한지 적습니다.
3. **조작**: `<skill>/scripts/app.mjs`의 `text`·`tree`·`click`·`fill`·`press`·`scroll`로 절차를 수행하고, 값·비활성·선택·스크롤 위치처럼 글자로 보이지 않는 상태는 `probe`로 읽습니다. 이름은 정확히 일치하는 요소를 먼저 찾습니다. 대상은 기본적으로 활성 작업 화면 범위(`scope: "page"`)에서 찾습니다. 액션마다 무엇을 눌렀고 무엇이 보였는지 기록합니다.
4. **판정**:
   - `OK`: 기대결과대로 동작합니다. 이름만 다르면 OK입니다.
   - `문제`: 기대와 다르게 동작합니다. 제품 결함 후보입니다.
   - `미구현`: 기능·버튼·항목이 없거나 비활성이거나, 「준비 중」「합성 예시」처럼 실데이터가 연결되지 않았습니다.
   - `실행 불가`: 데이터·권한·환경·쓰기 범위 때문에 진행할 수 없습니다.
   - `보류-기록`: 행의 정책 상태가 「확정 필요(보류)」입니다. 관찰값만 남기고 판정하지 않습니다.
   - `알려진 차이`: 행의 구현 상태가 「정책과 다름」이고 실제로 그 차이대로 동작했습니다. 차이 없이 기대대로 동작했다면 `OK`로 두고 headline에 "알려진 차이가 해소된 것으로 보임"을 적습니다.
5. **증거**: 판정 근거 장면에서 `node <skill>/scripts/app.mjs mark <png> <marks-json>`으로 번호 박스를 그립니다. [보고 형식](references/report-format.md)의 번호 규칙을 따르고, 찍은 PNG를 열어 박스가 맞는 요소에 그려졌는지 눈으로 확인합니다.
6. **기록**: [결과 JSON 형식](references/result-schema.md)으로 `runs/<run_id>/<tc_id>.json`을 씁니다. headline·checked·outcome은 사람이 읽는 문장으로 쓰고, 문서 ID·좌표·컴포넌트명은 details에만 둡니다.
7. **정리**: 연 모달과 작업 탭을 닫아 홈 또는 목록 상태로 돌립니다. 인증 화면이 나오면 `launch_app.sh`의 재인증 절차를 따르고, 로그인이 필요하면 실행을 멈추고 보고합니다.

한 행에 15분 넘게 진전이 없으면 「실행 불가」로 기록하고 다음 행으로 넘어갑니다. 실행 중 행 범위 밖에서 결함 후보를 보면 `details.side_findings`에 적고, 행 판정에는 섞지 않습니다.

## 반영과 보고

1. `python3 <skill>/scripts/publish_results.py runs/<run_id>`를 `NOTION_API_KEY`가 주입된 상태로 실행합니다. bws를 쓰는 환경에서는 `bws-run`이 인자를 다시 나누므로 `python3 -I "$@"`만 실행하는 래퍼 스크립트를 거칩니다(예: `bws-run "$PWD/scripts/run.sh" <skill>/scripts/publish_results.py runs/<run_id>`). 각 행의 「최근 판정·최근 실행일·최근 실행 빌드·최근 요약」을 갱신하고, 페이지 본문의 「🤖 자동 실행 결과」 제목부터 아래를 결과 한눈에 → 증거 → 상세 기록 → 이전 실행 기록 순서로 다시 씁니다. 그 제목 위에 사람이 쓴 메모는 지우지 않습니다. 먼저 `--dry-run`으로 블록 수를 확인할 수 있습니다.
2. 반영한 뒤 행 하나를 다시 읽어 판정과 그림이 올라갔는지 확인합니다. 쓰기 결과 응답만으로 반영됐다고 보고하지 않습니다.
3. 사용자에게는 판정 분포, 「문제」 행의 headline과 링크, 행 범위 밖 결함 후보, 시나리오 결함 후보, 실행 불가 사유를 짧게 보고합니다. 행당 평균 시간도 적습니다.

비용: 2026-10-06 시험 실행에서 행당 평균 약 1.8분이 걸렸습니다. 많은 행을 실행하기 전에는 20~30행 표본으로 시작하고, 사용자가 규모를 정하게 합니다.
