---
name: worxsales-bug-report
description: Use when a WorxSales developer wants to connect Claude Code or Codex to the WorxSales CBT bug-report MCP with their personal access key (wxbrm_…), or wants to read, triage, comment on, link an MR to, or change the status of in-app bug reports and their Bugsink errors through that MCP. Not for filing a bug from the desktop app or for unrelated Slack/Notion bug lists.
---

# WorxSales 버그 제보 MCP

WorxSales 데스크톱 앱의 버그 제보(사용자 제보, 이벤트 타임라인, 스크린샷, 자동 수집 에러)를 AI가 읽고 처리하도록 MCP 서버 `worxsales-bug-report`를 연결하고 사용합니다. 새 제보는 Slack `#worxsales-bug-report`에도 올라오며, 메시지의 제보 ID로 이 MCP에서 상세를 가져옵니다.

- MCP: `https://172.16.111.17:18443/bugs/mcp` (회사망·VPN에서만 접속)
- 대시보드: `https://172.16.111.17:18443/bugs/app` — 같은 접근 키로 「접근 키로 로그인」
- 접근 키는 사람마다 하나이며 관리자가 대시보드의 키 관리 화면에서 발급·폐기합니다. MCP와 대시보드에서 한 코멘트·상태 변경은 그 키 주인 이름으로 남습니다.

## 연결

1. `claude mcp list`·`codex mcp list`로 `worxsales-bug-report`가 이미 연결돼 있는지 확인합니다. 연결돼 있고 키를 바꾸려는 것이 아니면 「사용」으로 넘어갑니다.
2. 대상(Claude Code, Codex, 양쪽)이 요청에 없으면 설치된 CLI를 보고 정하고, 둘 다 있으면 한 번 묻습니다.
3. 사용자에게 관리자에게서 받은 접근 키(`wxbrm_`로 시작)를 받습니다. 키가 없으면 관리자에게 발급을 요청하라고 안내하고 멈춥니다. 키를 응답·로그·파일에 다시 쓰지 않습니다.
4. 키를 환경변수로만 넘겨 실행합니다. `<skill>`은 이 SKILL.md가 있는 폴더입니다.

   ```sh
   WXBR_KEY='<키>' python3 "<skill>/scripts/connect.py" --target claude   # codex | both
   ```

   스크립트는 엣지 인증서를 받아 고정된 SHA-256 지문과 비교한 뒤 `~/.config/worxsales/edge-ca.pem`에 저장하고, 키로 `list_reports`를 한 번 호출해 확인한 다음 사용자 범위에 `mcp-remote`(stdio) 서버로 등록합니다. 인증서는 이 MCP 서버 프로세스에만 `NODE_EXTRA_CA_CERTS`로 주므로 셸 설정이나 시스템 신뢰 저장소를 바꾸지 않습니다. 등록 없이 확인만 하려면 `--check-only`를 붙입니다.
5. 종료 코드: 0 성공, 1 지문 불일치·키 거부(새 키 요청), 2 망·도구 문제(회사망 연결, Node.js 설치). 지문 불일치는 우회하지 말고 관리자에게 알립니다.
6. Claude Code는 재시작, Codex는 새 세션에서 도구가 보입니다. 첫 실행은 `npx`가 `mcp-remote`를 받느라 몇 초 걸립니다. `claude mcp list`에 `Missing environment variables: WXBR_AUTH` 경고가 함께 보일 수 있습니다. 키는 서버 실행 환경으로 넘어가 `mcp-remote`가 읽으므로 `✔ Connected`이면 무시해도 됩니다.

## 사용

| 도구 | 용도 |
|---|---|
| `list_reports` | 최신순 목록(상태·유형·환경 필터) |
| `get_report` | 본문, 환경, 이벤트 타임라인, 연결 에러, AI 초안·개발자용 메모, 코멘트, MR, 상태 이력, 스크린샷 |
| `list_bugsink_issues` / `get_bugsink_event` | Bugsink 이슈 목록과 이벤트 스택(마크다운) |
| `add_comment` | 조사 결과를 코멘트로 남김(쓰기 권한 키) |
| `link_merge_request` | 고친 GitLab MR 링크를 연결(쓰기 권한 키) |
| `set_status` | 상태 변경(쓰기 권한 키). 전이 표에 없는 전이는 `invalid_transition` |

- 제보를 처리할 때는 `get_report`로 이벤트 타임라인과 request id를 먼저 보고, 실패한 API·화면을 코드에서 찾은 뒤 코멘트로 근거(파일·줄, 재현 조건)를 남깁니다. 「AI 개발자용 메모」는 모델 추정이므로 코드로 확인하기 전에는 결론으로 쓰지 않습니다.
- 상태를 `fixed`로 바꾸는 것은 MR을 연결한 뒤에만 합니다. 다른 사람이 맡은 제보(`assignee`)의 상태는 바꾸지 않고 코멘트만 남깁니다.
- 잘못 남긴 코멘트는 지울 수 없으므로 새 코멘트로 정정합니다.
- 제보 본문·스크린샷에는 고객 정보가 있을 수 있습니다. 대화 밖(Slack, Notion, 이슈 트래커)으로 옮길 때는 필요한 부분만 요약하고 스크린샷은 옮기지 않습니다.
- 쓰기 도구가 `forbidden`이면 읽기 전용 키입니다. 관리자에게 쓰기 권한 키를 요청하라고 안내합니다.
