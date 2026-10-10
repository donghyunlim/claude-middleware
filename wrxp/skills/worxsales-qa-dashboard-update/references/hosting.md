# 진척판 호스팅

진척판은 HTML 파일 하나라 어디서든 열 수 있습니다. 여러 사람이 같은 주소로 보려면 항상 켜진 맥 한 대에 올립니다.

## 서버 준비 (한 번)

```sh
sh <skill>/scripts/serve_setup.sh <ssh_host> <remote_dir> <port>
# 예: sh <skill>/scripts/serve_setup.sh my-server-mac qa-dashboard 8090
```

- ssh 키로 접속되는 맥이면 됩니다. sudo가 필요 없습니다.
- 서버는 `serve_page.pl`(macOS 기본 Perl만 사용)이며, 어떤 경로로 요청해도 `<remote_dir>/index.html`만 읽기 전용으로 돌려줍니다. 디렉터리 목록이나 다른 파일은 보이지 않습니다.
  - macOS의 `/usr/bin/python3`는 개발 도구가 없으면 설치 창만 띄우는 껍데기라 쓰지 않습니다(2026-10-10 서버실 맥북에서 확인).
- 사용자 LaunchAgent(`com.wrxp.qa-dashboard`)로 등록되어, 그 사용자가 로그인해 있는 동안 계속 돌고 꺼지면 다시 뜹니다. 로그는 `~/Library/Logs/com.wrxp.qa-dashboard.log`입니다.
- 준비 뒤 `watch.json`에 적습니다.

```json
"dashboard": {"publish": {"ssh_host": "my-server-mac", "remote_dir": "qa-dashboard", "url": "http://<그 맥의 사내 IP>:8090/"}}
```

## 확인

- `curl -s -o /dev/null -w "%{http_code}" <url>`이 200이면 됩니다.
- 열리지 않으면 그 맥에서 `launchctl print gui/$(id -u)/com.wrxp.qa-dashboard`와 로그를 봅니다. 맥이 재부팅되어 사용자가 로그인하지 않았으면 서버도 꺼져 있습니다.
- 사내망 밖에서는 열리지 않습니다. 밖에서 봐야 하면 사용자에게 공개 방법(터널 등)을 따로 묻습니다.
