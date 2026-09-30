# wrxp:intent-anchor 설계

작성: 2026-09-30 · 대상 버전: wrxp 0.1.39 · 상태: 사용자 검토 대기

## 1. 목적

단일 AI 모델과 긴 작업을 하다 보면 작업 방향이 사용자의 원래 의도에서 조금씩 멀어진다(드리프트). 드리프트한 모델은 스스로 이를 알아차리기 어렵다. `intent-anchor`는 드리프트가 의심되는 시점에 **사용자 발화 원문**을 기준으로, 맥락이 다른 최고 수준 모델과 토론해 작업을 사용자 의도로 되돌린다.

### 1-1. 근거 사례

세션 `01a0e0f3-51b9-7203-a976-4c1cb32bfad2`(Codex, 2026-09-27~29)에서는 "제품 전체를 이해하고 설명하는 부담을 AI에 맡긴다"는 목적이 "분석 문서를 만들고 검증해 게시한다"는 수단으로 대체되었다. 드리프트를 발견한 쪽은 사용자였다("너 말투보니까 이해못했는데?"). 그 뒤 메인이 Opus 5.5/high와 3회 토론하여 이전 결론을 철회했다. 이 사례는 다음 세 가지를 보여 준다.

- 다른 계열 모델과의 토론은 실제로 판단을 바꾼다.
- 리뷰어에게 AI가 쓴 요약이 섞이면 리뷰어도 같은 방향으로 끌려갈 수 있다.
- 토론 자체가 길어지면 새로운 부담이 된다.

### 1-2. 성공 기준

- 드리프트가 있던 세션을 사용자가 지적하기 직전까지만 입력했을 때, 리뷰어가 사용자가 나중에 지적한 핵심을 먼저 잡는다.
- 드리프트가 없던 세션은 "드리프트 없음"으로 판정한다.
- 자동 실행은 드물다(주 1회 수준). 이 기준은 테스트로 보장할 수 없으며 배포 후 기록 건수로 확인한다(§8).

## 2. 사용자 결정

| # | 결정 |
|---|---|
| D1 | 이름은 `intent-anchor`로 한다. handoff와 별도 스킬로 두고 사용자 발화 추출 스크립트를 공유한다. |
| D2 | 명시 호출과 드문 자동 실행을 모두 허용한다. 자동 실행은 문턱을 높게 잡는다. |
| D3 | 자동 신호는 **사용자의 강한 정정**과 **같은 문제의 반복 시도** 두 가지로 한정한다. 요청 없는 범위 확장과 대리 지표에 의한 완료 판정은 자동 신호로 쓰지 않는다. |
| D4 | 방향 변화의 근거가 사용자 발화에 있으면, 원래 의도와 멀어 보여도 허용한다. |
| D5 | 리뷰어에게는 사용자 발화 **전부**를 스크립트 추출 원문으로 준다. 결정 목록은 리뷰어가 직접 도출한다. |
| D6 | 이전 handoff에서 이어진 세션은 handoff §1의 원문 인용과 이전 세션 발화를 추적한다. handoff의 AI 기획(§2)은 "AI 작성"으로 표시한다. |
| D7 | 두 계정이 모두 있으면 반대 계열 최고 모델 1개, 한 계열만 있으면 그 계열 최고 모델을 새 맥락으로 쓴다. |
| D8 | 최고 모델은 실행할 때 동적으로 탐지하며, 스킬에는 계열 순위만 적는다. |
| D9 | 리뷰어 effort는 `high`로 고정한다. |
| D10 | 리뷰어에게 읽기 전용 도구를 허용한다. |
| D11 | 토론은 기본 1회, 메인이 반박할 때만 최대 3회까지 한다. 합의하지 못하면 양쪽 입장을 보고한다. |
| D12 | 드리프트가 있으면 작업을 멈추고, 보고한 뒤 질문 하나를 한다. 경로 수정은 사용자 답을 받은 뒤에만 한다. 드리프트가 없으면 요약을 보고하고 계속한다. |
| D13 | 리뷰어 호출이 실패하면 다음 순위로 내려가고, 그 사실을 보고에 밝힌다. |
| D14 | 기록은 `handoffs/realign/<날짜>-<슬러그>/`에 남긴다. |
| D15 | 실제 세션 재생으로 효과를 검증한다. |
| D16 | 이번에는 독립 스킬로만 배포하고, 다른 wrxp 스킬과 연결하지 않는다. |

## 3. 구성 요소

```
wrxp/
├─ shared/scripts/user_turns.py          handoff에서 이동한 공유 추출기
├─ skills/handoff/scripts/user_turns.py  공유 추출기를 실행하는 얇은 호환 래퍼
└─ skills/intent-anchor/
   ├─ SKILL.md                         절차, 판정 기준, 보고 형식
   ├─ agents/openai.yaml               Codex 표시 정보 (allow_implicit_invocation: true)
   ├─ references/reviewer-prompt.md    리뷰어 지시문
   └─ scripts/run_reviewer.py          탐지 → 패킷 조립 → 실행 → 기록
```

`shared/`는 `package.json`의 `files`에 포함되어 있고, 설치된 Claude·Codex 플러그인 캐시에도 들어 있다(2026-09-30 확인). 호환 래퍼는 handoff SKILL.md의 기존 명령과 `test_handoff_user_turns.py`를 바꾸지 않기 위해 둔다.

### 3-1. 호출 정책

- Claude: frontmatter에 `disable-model-invocation`을 두지 않는다.
- Codex: `agents/openai.yaml`에 `allow_implicit_invocation: true`를 둔다.
- description은 명시 호출(`/wrxp:intent-anchor`, `$wrxp:intent-anchor`)과 두 자동 신호를 적고, 다음 경우에는 실행하지 않는다고 적는다: 단순 버그·오타 지적, 사용자가 방향을 직접 바꾼 경우, 한두 번의 재시도.
  - 강한 정정: 사용자가 방향 자체를 바로잡는 발화다. 예: "이해 못했네", "그게 아니라", "원래 의도는", "산으로 간다".
  - 반복 시도: 같은 목표에 수정·재시도가 계속 쌓이며, 수단이 목적을 대체했을 가능성이 있는 상황이다. 예: 같은 산출물의 v7→v21.

## 4. 실행 흐름

1. **진입.** 명시 호출이나 자동 신호로 시작한다. 자동 신호로 시작했으면 어떤 신호였는지 한 줄로 알리고, 진행하던 작업을 멈춘 상태로 둔다.
2. **AI 상태 작성.** 메인이 기록 폴더에 `ai-state.md`를 쓴다. 담을 내용은 다음과 같다.
   - 메인이 이해한 현재 목표
   - 지금 하는 일과 다음 계획
   - 최근의 방향 전환과 그 계기

   각 항목에는 근거(파일 경로, 명령, 커밋)를 붙인다. 사용자 의도는 이 파일에 쓰지 않는다.
3. **1회차 리뷰.** `run_reviewer.py --state ai-state.md --round 1`을 실행한다.
4. **메인 검토.** 판정에 동의하면 5단계로 간다. 반박할 근거가 있으면 `rebuttal-N.md`를 써서 다음 회차를 실행하며, 최대 3회까지 한다. 반박에는 U번호나 파일 근거가 있어야 한다. 근거 없는 반박("제 판단으로는")은 다음 회차의 근거로 쓰지 않는다.
5. **보고.** §6 형식에 따른다.

## 5. run_reviewer.py

### 5-1. 입력과 출력

- 입력: `--state <ai-state.md>`, `--round <N>`, `--rebuttal <파일>`(2회차부터), `--out <기록 폴더>`, 선택 사항으로 `--session-id`·`--log`(user_turns.py와 같은 의미).
- 출력: `<기록 폴더>/round-N/`에 `request.md`(리뷰어가 받은 전체 패킷), `response.md`, `invocation.json`을 쓴다. 표준 출력으로는 판정 요약과 경로를 낸다.

### 5-2. 패킷 조립 (메인이 거를 수 없는 부분)

스크립트가 다음을 차례로 붙인다. 메인은 `ai-state.md`와 반박만 제공한다.

1. `references/reviewer-prompt.md`
2. **사용자 발화 원문 [원문]:** `shared/scripts/user_turns.py`로 현재 세션의 U1~Un 전부를 추출한다.
3. **이전 handoff [원문 인용 / AI 작성]:** 사용자 발화에 handoff 경로가 있거나 같은 작업의 handoff가 있으면, §1(원문 인용)과 출처 세션의 발화를 추출한다. §2는 "AI 작성"으로 표시한다. 체인은 최초 세션과 최근 세션을 우선하고, 끊기면 "미확인"으로 표시한다.
4. **저장소 상태 [기계 출력]:** `git status --short --branch`, `git log --oneline -15`, `git diff --stat`.
5. **AI 상태 [AI 주장]:** `ai-state.md`.
6. 이전 회차의 응답과 반박(2회차부터).

**크기 제한**
- 발화마다 앞 1,500자와 뒤 500자만 남기고, 잘렸다는 표시와 전문 위치(로그 경로, U번호)를 붙인다.
- 전체가 약 150KB를 넘으면 최초 세션의 첫 발화와 최근 발화를 그대로 두고, 중간 발화는 첫 줄만 남긴다. 줄인 발화 목록은 패킷에 적는다. 리뷰어는 읽기 도구로 로그 전문을 볼 수 있다.

**비밀값 가림**
키 이름 패턴(`*_TOKEN`, `*_KEY`, `*_SECRET`, `*_PASSWORD` 뒤의 `=` 또는 `:`)이 나오면 그 뒤의 값을 가린다. 값 모양으로는 검색하지 않는다.

**원문 추출 실패**
세션 로그를 찾지 못하면 종료 코드 3으로 끝내고 "원문 미확인"을 출력한다. 이때 메인은 대화 기억으로 대신하지 않고, 사용자에게 로그 경로를 한 번 묻는다.

### 5-3. 리뷰어 선택

1. **메인 런타임 확인.** `CLAUDE_CODE_SESSION_ID`는 Claude, `CODEX_THREAD_ID`는 Codex로 본다. 둘 다 있으면 user_turns.py와 같은 규칙(로그가 최근인 쪽)을 따른다.
2. **후보 목록.** 반대 계열이 먼저 오고 같은 계열이 다음에 온다.
   - Codex 계열: `~/.codex/models_cache.json`에 있는 모델 가운데 `astra > sol` 순위에서 가장 높은 최신 세대를 고르고, 그다음 순위를 차순위로 둔다. 새 슬러그를 추측하지 않는다.
   - Claude 계열: 별칭 `opus > sonnet` 순서로 쓴다. 실제 모델 ID는 결과 JSON에서 기록한다.
3. **가용성 확인.** CLI가 존재하는지 확인한다. 인증·한도 문제는 실행 실패로 판정한다.
4. **폴백.** 반대 계열 최고 → 반대 계열 차순위 → 같은 계열 최고(새 맥락) 순으로 시도한다. 모두 실패하면 종료 코드 4로 끝내고, 메인이 원문 대조를 직접 하되 보고에 "자기 검토, 교차 검증 아님"을 명시한다.

### 5-4. 실행 명령

```
claude --print --model <opus|sonnet> --effort high --output-format json \
  --tools Read,Grep,Glob --permission-mode dontAsk \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --no-session-persistence --add-dir <프로젝트>          # 패킷은 표준 입력

codex exec -C <프로젝트> -m <slug> -c 'model_reasoning_effort="high"' \
  --sandbox read-only --json -o <response.md> -          # 패킷은 표준 입력
```

- Claude 리뷰어에게는 Bash를 주지 않는다. 셸 명령의 읽기 전용 여부를 보장할 수 없기 때문이다. git 정보는 §5-2의 4번으로 대신한다.
- 승인 우회 옵션(`--dangerously-*`, `bypassPermissions`)은 쓰지 않는다.
- 회차당 제한 시간은 10분이다. 제한 시간 초과, 0이 아닌 종료 코드, 빈 응답은 모두 실패로 보고 폴백한다.

### 5-5. invocation.json

```json
{
  "round": 1,
  "attempts": [
    {"runtime": "codex", "requested_model": "gpt-6-astra", "effort": "high",
     "exit_code": 1, "failure": "usage_limit", "seconds": 4.2},
    {"runtime": "claude", "requested_model": "opus", "actual_models": ["claude-opus-5-5"],
     "effort": "high", "exit_code": 0, "seconds": 161.0}
  ],
  "selected": {"runtime": "claude", "actual_model": "claude-opus-5-5"},
  "packet": {"bytes": 88213, "user_turns": 142, "truncated_turns": ["U12", "U40"],
             "prior_handoffs": ["handoffs/2026-09-27-x.md"]},
  "command": ["claude", "--print", "..."]
}
```

## 6. 판정과 보고

### 6-1. 리뷰어 지시문의 판정 기준

- 방향 변화의 근거가 사용자 발화(U번호)에 있으면 **허용**한다.
- AI가 정한 수단이 사용자의 목적을 대체했으면 **드리프트**로 본다. 예: 목적을 "이해를 AI에 맡긴다"로 두고도 "740페이지 발행 성공"으로 완료를 판정한 경우.
- 사용자가 답하지 않은 AI 제안을 승인된 것으로 취급했으면 **드리프트**로 본다.
- 사용자의 마음을 단정하지 않고, 원문으로 확인한 사실과 해석을 구분한다.
- `[AI 주장]`과 `[AI 작성]` 자료는 원문이나 저장소로 확인되기 전까지 사실로 쓰지 않는다.
- 제안만 하고, 파일 수정·명령 실행·외부 발송은 하지 않는다.

### 6-2. 리뷰어 응답 형식

```
판정: 드리프트 있음 | 없음 | 부분
재구성한 의도: 최초 의도(U번호) + 사용자 결정 목록(D1.. 각 U번호)
항목별 대조: AI의 현재 행동/계획 → 근거 U번호 있음/없음 → 허용/드리프트
드리프트 목록: 무엇이 · 언제부터(추정) · 사용자 의도와의 차이
멈출 것 / 되돌릴 후보: (제안만)
사용자에게 물을 한 가지: 판정을 바꿀 수 있는 가장 중요한 미결 사항
```

### 6-3. 사용자 보고

- **드리프트 있음·부분:** 작업을 멈추고 다음을 보고한다.
  - 원래 의도: 원문을 인용한 두세 줄
  - 벗어난 지점: 한두 개 항목과 근거
  - 멈춘 작업 / 되돌릴 후보
  - 질문 하나(선택지 도구가 있으면 사용한다)
  - 리뷰어 모델·회차·기록 경로

  되돌리기(코드 롤백, 외부 변경 취소)는 사용자 답을 받은 뒤에만 한다.
- **드리프트 없음:** 재확인한 최종 의도와 현재 작업의 연결을 몇 줄로 보고하고, 멈춘 작업을 이어 간다.
- **합의 실패(3회):** 양쪽 입장과 근거를 나란히 보여 주고 질문 하나를 한다.

## 7. 기록 위치

프로젝트 폴더의 `handoffs/realign/<YYYY-MM-DD>-<슬러그>/`에 둔다. 연결된 git worktree 안이면 handoff와 같은 규칙으로 주 체크아웃의 루트를 쓴다. 같은 이름이 있으면 `-2`, `-3`을 붙인다. `.gitignore`와 커밋 여부는 바꾸지 않는다.

## 8. 검증

### 8-1. 단위 테스트 (`tests/test_intent_anchor.py`)

- 리뷰어 선택: 런타임, 설치된 CLI, `models_cache` 조합별로 선택 결과와 폴백 순서를 확인한다. CLI는 가짜 실행 파일로 대체한다.
- 패킷: 사용자 발화 전부가 포함되는지(메인 입력으로 제외할 수 없는지), 잘림 표시·크기 상한·비밀값 가림, 출처 표시(`[원문]`, `[AI 주장]`, `[AI 작성]`, `[기계 출력]`)를 확인한다.
- handoff 연쇄: §1 인용과 출처 세션을 추적하는지, 체인이 끊기면 "미확인"으로 표시하는지 확인한다.
- 원문 추출 실패 시 종료 코드 3, 전체 폴백 실패 시 종료 코드 4가 나오는지 확인한다.
- `invocation.json`의 필드를 확인한다.
- 기존 `test_handoff_user_turns.py`가 수정 없이 통과하는지 확인한다(호환 래퍼 검증).

### 8-2. 불변식 테스트 (`test_wrxp_invariants.py`)

- 호출 정책(§3-1)과 description의 두 자동 신호
- 리뷰어 명령에 쓰기 권한이 없음(Claude `--tools Read,Grep,Glob`, Codex `--sandbox read-only`, 우회 옵션 없음)
- 다른 스킬 본문이 `intent-anchor`를 호출하지 않음(D16)
- 버전 0.1.39가 plugin.json·package.json·marketplace.json에서 일치(기존 `test_release_versions_match` 갱신)

### 8-3. 효과 검증 (실제 모델 호출, 수동)

1. **드리프트가 있던 세션:** `01a0e0f3`을 "너 말투보니까 이해못했는데?" 직전 발화까지만 잘라 입력한다. "드리프트 있음"이 나오고, 수단(문서 생성·발행)이 목적(이해와 설명 부담을 AI에 맡기는 것)을 대체했다는 핵심을 잡으면 통과다.
2. **드리프트가 없던 세션:** 이 설계를 만든 Claude 세션(`35f34c11-8d41-40ae-a7cd-d957f6d4d835`)을 설계 승인 시점까지 입력한다. "드리프트 없음"이 나오면 통과다.
3. 두 결과와 모델·소요 시간을 `docs/benchmark/intent-anchor-0.1.39.md`에 기록한다. 실패하면 리뷰어 지시문을 수정한 뒤 다시 실행하고, 그 이력도 기록한다.

D15를 실행하기 위해 AI가 추가한 항목이다(사용자 검토 필요). 재생을 위해 `run_reviewer.py`에 `--until-turn <U번호>` 옵션(해당 발화 이전까지만 추출)을 둔다. 이 경우 저장소 상태는 현재 시점의 것이므로, 효과 검증에서는 `--no-repo-state`로 제외하고 그 세션의 마지막 AI 응답 일부를 `ai-state.md`로 쓴다.

### 8-4. 한계

- 자동 실행 빈도는 테스트로 보장할 수 없다. 배포 후 `handoffs/realign/` 건수를 보고 description을 조정한다.
- 자동 실행은 결국 메인 모델이 신호를 인식해야 일어난다. 드리프트가 심할수록 인식하지 못할 수 있으며, 이 경우 명시 호출이 안전망이다.
- 같은 계열 리뷰어는 사각지대가 겹친다. 효과는 주로 새 맥락에서 나온다.

## 9. 함께 바꾸는 파일

- `README.md`: 스킬 목록과 호출 방법
- `CHANGELOG.md`: 0.1.39 항목
- `.claude-plugin/plugin.json`, `package.json`, marketplace 버전
- `.claude-plugin/marketplace.json`(저장소 루트)
- `skills/setup/assets/global-rules.md`: handoff 줄 다음에 기존 관례대로 한 줄을 추가한다. 예: `- Intent drift: use \`wrxp:intent-anchor\` when explicitly invoked, or rarely when the user strongly corrects the direction or the same goal keeps being retried; compare against the user's raw turns with a fresh-context top model, then stop and ask before changing course.` (설계 중 AI가 추가한 항목, 사용자 검토 필요)

## 10. 범위 밖

- 다른 wrxp 스킬(`ha` 복구 체크포인트, `staged-development` 단계 전환)과의 연결(D16)
- 훅 기반 자동 감지
- 여러 리뷰어의 병렬 판정
- 드리프트를 자동으로 되돌리는 기능
