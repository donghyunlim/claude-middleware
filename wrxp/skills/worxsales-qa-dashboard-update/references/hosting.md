# 진척판 호스팅

진척판은 HTML 파일 하나라 어디서든 열 수 있습니다. 여러 사람이 같은 주소로 보려면 이 맥이나 ssh로 닿는 맥 한 대에서 띄웁니다. 서버실처럼 방화벽이 막는 곳보다, 보는 사람과 같은 Wi-Fi에 있는 맥이 낫습니다.

## 서버 준비 (한 번)

```sh
sh <skill>/scripts/serve_setup.sh <ssh_host|local> <dir> <port>
# 예: sh <skill>/scripts/serve_setup.sh local qa-dashboard 8090     # 이 맥
# 내리기: sh <skill>/scripts/serve_setup.sh --remove <ssh_host|local> <dir>
```

- `local`은 이 맥, 그 밖의 값은 ssh 키로 접속되는 맥입니다. sudo가 필요 없습니다. `<dir>`는 그 사용자 홈 기준입니다.
- 서버는 `serve_page.pl`(macOS 기본 Perl만 사용)이며, 어떤 경로로 요청해도 `<remote_dir>/index.html`만 읽기 전용으로 돌려줍니다. 디렉터리 목록이나 다른 파일은 보이지 않습니다.
  - macOS의 `/usr/bin/python3`는 개발 도구가 없으면 설치 창만 띄우는 껍데기라 쓰지 않습니다(2026-10-10 서버실 맥북에서 확인).
- 사용자 LaunchAgent(`com.wrxp.qa-dashboard`)로 등록되어, 그 사용자가 로그인해 있는 동안 계속 돌고 꺼지면 다시 뜹니다. 로그는 `~/Library/Logs/com.wrxp.qa-dashboard.log`입니다.
- 준비 뒤 `watch.json`에 적습니다.

```json
"dashboard": {"publish": {"ssh_host": "local", "remote_dir": "qa-dashboard",
                           "url": "http://<LocalHostName>.local:8090/", "verify_url": "http://127.0.0.1:8090/"}}
```

- `url`은 사람이 여는 주소이고 상황판 요약의 링크가 됩니다. `<LocalHostName>`은 `scutil --get LocalHostName` 값입니다. `.local` 이름은 Wi-Fi가 바뀌어 IP가 달라져도 같은 네트워크 안에서 그대로 열립니다.
- `verify_url`은 게시 확인용 주소입니다. 게시하는 맥에서 닿아야 하며, 없으면 `url`을 씁니다.

## 확인

- `curl -s -o /dev/null -w "%{http_code}" <url>`이 200이면 됩니다.
- 열리지 않으면 그 맥에서 `launchctl print gui/$(id -u)/com.wrxp.qa-dashboard`와 로그를 봅니다. 맥이 재부팅되어 사용자가 로그인하지 않았으면 서버도 꺼져 있습니다.
- 같은 네트워크 밖에서는 열리지 않습니다. 노트북이 잠자기 상태이거나 꺼져 있어도 열리지 않습니다. 밖에서 봐야 하면 사용자에게 공개 방법(터널 등)을 따로 묻습니다.
