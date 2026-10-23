# 앱 빌드·슬롯·로그인과 인계

`<skills>`는 이 스킬 폴더의 상위 폴더(플러그인의 `skills/`)입니다. 앱 조작 규칙의 정본은 `worxsales-qa-executor`의 [실행 환경](../../worxsales-qa-executor/references/environment.md)입니다.

## 1. 빌드

```sh
QA_HOME=$PWD sh <skills>/worxsales-qa-executor/scripts/build_dev_app.sh <desktop_repo> <빌드 폴더>/desktop-dev-<커밋 5자리>
```

- 사용자의 desktop 체크아웃은 건드리지 않고 별도 worktree에서 develop을 빌드합니다. 빌드 폴더 이름은 `desktop-dev*`로 시작해야 나중에 `prune_builds.sh`가 옛 빌드를 지웁니다.
- 끝나면 `config.json`의 `desktop_worktree`·`app_path`·`build`가 채워지고, 스크립트는 마지막 줄에 앱 경로를 출력합니다. 그 세 값을 슬롯 배포용 `build.json`으로 옮깁니다. bootstrap 단계에는 레인이 없으므로 `.slots/build.json`에 둡니다(레인을 만든 뒤에는 QA 한 바퀴 스킬이 같은 내용을 레인 폴더에 씁니다).
  ```sh
  mkdir -p .slots && python3 -c "import json;c=json.load(open('config.json'));json.dump({k:c[k] for k in ('app_path','desktop_worktree','build')},open('.slots/build.json','w'),ensure_ascii=False,indent=1)"
  ```
- `app_path`의 `WorxSales.app`이 실제로 있는지 확인한 뒤 다음 단계로 갑니다.
- 빌드 하나가 수 GB입니다. 디스크 여유를 먼저 봅니다.

## 2. 슬롯 띄우기와 로그인

```sh
sh <skills>/worxsales-qa-all-in-one/scripts/qa_rollout.sh 9333 .slots/app-9333 .slots/build.json
sh <skills>/worxsales-qa-all-in-one/scripts/slots.sh status .slots/app-*
```

- 슬롯은 **하나씩** 띄웁니다. 동시에 띄우면 브라우저 인증이 엇갈려 「브라우저 인증 대기」에 멈춥니다.
- 로그인은 사내 SSO입니다. 앱에는 입력창이 없고 기본 브라우저가 열립니다. 브라우저에 SSO 세션이 있으면 「다시 시도」로 통과하고, 없으면 사용자가 브라우저에서 한 번 로그인합니다(종료 코드 4).
- 로그인 화면의 연결 환경은 항상 **DEV**를 고릅니다. PRD를 고르지 않습니다.
- 첫 회차는 슬롯 1~2개로 시작하고, 표본 20~30행으로 시간과 판정 일관성을 본 뒤 늘립니다.

## 3. 첫 확인

- `check_env.sh`로 도구, 키 이름, 슬롯, 브라우저 CDP, MC 상태를 봅니다.
- 앱 화면에서 본인 이름, 역할(「역할 전환」 목록), 담당 회원이 있는지 확인하고 `config.json`의 `operator_name`에 적습니다. 사번은 권한 관리 부여 창의 [확인] 조회로 본인 이름이 나오는 값만 씁니다.
- 본인 담당 회원(서비스별 담당이 본인인 회원)을 JK·AM 하나씩 찾아 `config.json`의 `own_members`(예: `{"JK": "<회원 ID>", "AM": "<회원 ID>"}`)에 적습니다. QA 한 바퀴 스킬이 첫 레인 WORKER.md의 `{OWN_MEMBERS}`를 이 값으로 채웁니다. 담당이 서비스마다 다를 수 있으므로 저장 전에 화면의 담당자를 확인합니다.

## 4. 인계

준비가 끝나면 사용자에게 다음을 보고하고, 실행은 사용자가 QA 한 바퀴 스킬(`/wrxp:worxsales-qa-all-in-one`)을 호출할 때 시작합니다.
- 만든 것: 작업 폴더, 원천 사본 수, 시나리오 행 수(메뉴별), DB·상황판 주소
- 쓰기 범위 초안(`refresh/write_scope.json`)과 사용자에게 받은 답
- 외부 조건별 상태와 풀리는 행 수([외부 조건](external-deps.md))
- 첫 실행 권장: 표본 20~30행, 슬롯 수
