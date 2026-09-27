# Runtime setup

## 설치 상태

먼저 해당 CLI의 `plugin ... --help`로 설치된 버전의 문법을 확인한다. `codex plugin list` 또는 `claude plugin list --json`에서 `wrxp@donghyunlim`의 설치·활성 상태만 추린다. 전체 플러그인 출력이나 개인 설정·자격 증명을 수집하지 않는다. 실행 중인 런타임의 스킬 목록에서도 `wrxp:setup`과 연결할 스킬이 노출되는지 확인한다. 소스 폴더에 파일이 있다는 사실만으로 양쪽 런타임의 설치 완료를 주장하지 않는다.

사용자가 요청한 대상에 wrxp가 없으면 아래 기존 배포 경로를 사용한다. 명령이 현재 CLI에서 지원되지 않으면 오류를 설명하며 캐시나 설정 파일을 직접 조작하지 않는다.

```sh
codex plugin marketplace add donghyunlim/claude-middleware --ref main
codex plugin add wrxp@donghyunlim

claude plugin marketplace add donghyunlim/claude-middleware
claude plugin install wrxp@donghyunlim
```

marketplace가 이미 있으면 add를 반복하지 않는다. 업데이트 요청에는 Codex의 `plugin marketplace upgrade donghyunlim` 후 `plugin add wrxp@donghyunlim`, Claude의 `plugin marketplace update donghyunlim` 후 `plugin update wrxp@donghyunlim`을 사용한다. 계정 로그인·CLI 설치는 이 명령의 성공과 별개다.

## 실제 전역 파일

- Codex: `CODEX_HOME`, 없으면 `~/.codex`. 비어 있지 않은 `AGENTS.override.md`가 있으면 `AGENTS.md`보다 우선하므로 실행기는 override를 대상으로 표시한다. 다른 프로필을 뜻하는 파일이라면 대상을 먼저 협의하며 삭제하지 않는다. [공식 AGENTS.md 지침](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Claude: `CLAUDE_CONFIG_DIR`, 없으면 `~/.claude`의 `CLAUDE.md`. 사용자·프로젝트·조직 지침을 구분하고, 식별 가능한 OMC 관리 구역 밖에 wrxp 규칙을 둔다. 구역이 모호하면 SKILL.md의 원문 보존·추가 방식을 따른다. 사용자 지정 설정 경로의 실제 로드는 재시작 후 `/context` 또는 `/memory`에서 확인한다. [공식 메모리 지침](https://code.claude.com/docs/en/memory), [설정 디렉터리](https://code.claude.com/docs/en/claude-directory)

전역 지침은 모델이 따르는 문서이며 모델·권한을 기계적으로 강제하는 보안 장치가 아니다. 연결 규칙 설치, 스킬 노출, 코드 위임 모델 접근은 서로 다른 상태로 보고한다. 전체 전역 파일이 너무 크거나 프로젝트 지침과 충돌하면 그 사실을 알리고, 사용자 설정을 임의로 줄이거나 용량 제한을 올리지 않는다.
