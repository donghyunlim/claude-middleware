# 실행 환경 준비 (2026-10-06 확인)

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

시나리오 원본은 `scenarios/<메뉴>/*.json`, 원천 문서는 `sources/`, 실행 결과는 `runs/<run_id>/`에 둔다. Notion 자격 증명은 bws의 `NOTION_API_KEY`이며 `bws-run`은 인자를 다시 나누므로 래퍼 스크립트로 실행한다.

## 앱 빌드와 실행
```shell
cd <QA_HOME>
sh <skill>/scripts/build_dev_app.sh /Users/donny2/project/WorxSales/worxsales-desktop <scratch>/desktop-dev
sh <skill>/scripts/launch_app.sh     # ready / login needed
```
- 로그인은 사내 Keycloak SSO(포탈 계정)다. 앱에는 입력창이 없고 기본 브라우저가 열린다. 백엔드가 계정 이메일로 MAGMA 재직 사원을 찾는다.
- 토큰은 앱 메모리에만 있다. 앱을 다시 켜면 다시 인증해야 한다. 브라우저에 Keycloak 세션이 남아 있으면 「다시 시도」로 통과한다. `launch_app.sh`가 이 버튼을 누른다.
- `worxsales-backend.dev.worxphere.io`는 사내망 DNS에서 조회되지 않았다. 같은 dev 백엔드가 `worxsales-backend.dev.jobko.io`로 응답하므로 빌드 스크립트가 이 주소를 기본값으로 쓰고, 앱의 접속 허용 목록에 worktree 안에서만 추가한다.
- 앱을 조작할 때는 `scripts/app.mjs`만 쓴다. CDP 연결을 끊을 때 `browser.close()`를 부르면 로그인된 앱이 닫힐 수 있으므로 쓰지 않는다.

## 역할
- 모든 재직자는 영업자다. MAGMA 직책(JIKCHAK 3·6)이면 영업팀장·관리자, REP 구분 S이면 영업운영이 붙는다.
- dev·stg에서는 권한 관리자가 자기 자신에게 팀장·영업운영 역할(「조회만」/「수정 가능」, 최대 90일)을 부여할 수 있다. 부여는 공용 dev 데이터 변경이므로 사용자가 허락한 실행에서만 한다.
- 2026-10-06 dev 로그인 계정은 영업자 단일 역할이고 담당 회원이 없다(MY ACNT 비활성). 「본인 담당」 행은 담당 데이터가 생기기 전까지 「실행 불가」로 둔다.

## 화면 상태 메모
- 상단 프로필(김민지·기업영업 1팀)과 홈 대시보드는 develop의 합성 표시값이다. 실제 로그인 사용자가 아니다.
- 「합성 예시」「준비 중」 표시가 있는 영역은 실데이터가 연결되지 않은 것이므로 「미구현」으로 판정한다.
