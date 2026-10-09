# 실행 환경 준비 (2026-10-06 확인, 2026-10-09 보완)

## QA 작업 폴더
시나리오·원천·결과가 있는 폴더(QA_HOME). 사용자 환경에서는 `/Users/donny2/project/WorxSales/worxsales-ai-qa`이다. `config.json`에 다음 값이 있다.

| 키 | 의미 |
|---|---|
| scenario_db_id | Notion 「WorxSales 테스트 시나리오」 DB ID |
| desktop_worktree | 빌드에 쓴 desktop worktree. playwright-core를 여기서 불러온다 |
| app_path | 빌드한 WorxSales.app |
| api_origin | 앱이 접속하는 백엔드 |
| cdp | CDP 주소(기본 http://127.0.0.1:9333) |
| build | 결과 JSON의 build 값으로 쓰는 문자열 |

시나리오 원본은 `scenarios/<메뉴>/*.json`, 원천 문서는 `sources/`, 실행 결과는 `runs/<run_id>/`에 둔다. 실행자는 시나리오 원본으로 만든 배치 파일을 읽는다. 기능정의서·목업이 바뀌면 실행 전에 `sources/`를 다시 받고, 바뀐 화면의 시나리오를 고친 뒤 Notion DB에도 동기화한다. 내용이 바뀐 행의 이전 결과는 옛 기준이므로 새 기준으로 다시 실행한다. Notion 자격 증명은 bws의 `NOTION_API_KEY`이며 `bws-run`은 인자를 다시 나누므로 래퍼 스크립트로 실행한다.

## 앱 빌드와 실행
```shell
cd <QA_HOME>
sh <skill>/scripts/build_dev_app.sh /Users/donny2/project/WorxSales/worxsales-desktop <scratch>/desktop-dev
sh <skill>/scripts/launch_app.sh     # ready / login needed
```
- develop 최신 앱은 로그인 화면에서 연결 환경(DEV/STG/PRD)을 고른다. 고르지 않고 로그인하면 의도하지 않은 환경에 붙을 수 있으므로 매번 확인한다. 2026-10-09 기준 DEV에 회원·그룹 데이터가 더 많고 열린 화면도 많다. STG는 고객 데이터가 필요한 행을 다시 돌릴 때만 따로 쓴다.
- 로그인은 사내 Keycloak SSO(포탈 계정)다. 앱에는 입력창이 없고 기본 브라우저가 열린다. 백엔드가 계정 이메일로 MAGMA 재직 사원을 찾는다.
- 토큰은 앱 메모리에만 있다. 앱을 다시 켜면 다시 인증해야 한다. 브라우저에 Keycloak 세션이 남아 있으면 「다시 시도」로 통과한다. `launch_app.sh`가 이 버튼을 누른다.
- `worxsales-backend.dev.worxphere.io`는 사내망 DNS에서 조회되지 않았다. 같은 dev 백엔드가 `worxsales-backend.dev.jobko.io`로 응답하므로 빌드 스크립트가 이 주소를 기본값으로 쓰고, 앱의 접속 허용 목록에 worktree 안에서만 추가한다.
- 앱을 조작할 때는 `scripts/app.mjs`만 쓴다. CDP 연결을 끊을 때 `browser.close()`를 부르면 로그인된 앱이 닫힐 수 있으므로 쓰지 않는다.

## 역할
- 모든 재직자는 영업자다. MAGMA 직책(JIKCHAK 3·6)이면 영업팀장·관리자, REP 구분 S이면 영업운영이 붙는다.
- dev·stg에서는 권한 관리자가 자기 자신에게 팀장·영업운영 역할(「조회만」/「수정 가능」, 최대 90일)을 부여할 수 있다. 부여는 공용 dev 데이터 변경이므로 사용자가 허락한 실행에서만 한다.
- 2026-10-06 dev 로그인 계정은 영업자 단일 역할이고 담당 회원이 없다(MY ACNT 비활성). 「본인 담당」 행은 담당 데이터가 생기기 전까지 「실행 불가」로 둔다.
- 역할 확인·판정·부여 규칙은 [역할과 권한](roles.md)을 따른다.

## 화면 상태 메모
- 상단 프로필(김민지·기업영업 1팀)과 홈 대시보드는 develop의 합성 표시값이다. 실제 로그인 사용자가 아니다.
- 「합성 예시」「준비 중」 표시가 있는 영역은 실데이터가 연결되지 않은 것이므로 「미구현」으로 판정한다.

## 병렬 실행
- 실행자마다 앱 하나를 둔다. 앱마다 QA_HOME(그 안의 `config.json`에 자기 CDP 포트)과 사용자 데이터 폴더를 따로 쓰고, 실행자는 받은 포트 외의 앱을 건드리지 않는다. 앱 조작은 `QA_HOME=<그 앱의 폴더> node <skill>/scripts/app.mjs ...`로 한다.
- 실행자는 앱을 끄거나 다시 띄우지 않는다. 로그인 화면이 나오면 「로그인」만 누른다. 앱 교체(새 빌드 배포)는 조율자가 실행자 사이에 한다.
- 같은 계정을 여러 앱이 함께 쓰므로 다른 실행자가 만든 QA 기록이 목록에 보일 수 있다. 고치지 않고, 개수·목록 확인에 영향을 주면 details에 적는다.
- 결과 폴더는 공유한다. 자기 배치 행의 결과 파일과 PNG, 자기 임시 폴더(`runs/<run_id>/_tmp/<배치 이름>/`) 외의 파일은 지우거나 옮기거나 덮어쓰지 않는다. 와일드카드 `rm`은 쓰지 않는다. 세션 공용 scratch 폴더에 임시 파일을 두지 않는다.
- 배치 번호는 이미 있는 가장 큰 번호 다음을 쓴다. 옮겨 둔 배치 파일의 번호도 다시 쓰지 않는다.
- 이전 실행자가 남긴 작업 탭을 첫 행 전에 닫는다.
- 최신 빌드를 따라갈 때는 결과의 `build`에 그 앱이 실제로 쓰는 빌드 문자열을 넣는다. 같은 행을 새 빌드로 다시 실행하면 DB에는 최신 빌드의 결과가 보이고 이전 결과는 「이전 실행 기록」으로 내려간다.
