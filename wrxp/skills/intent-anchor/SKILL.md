---
name: intent-anchor
description: "Use when the user explicitly invokes /wrxp:intent-anchor ($wrxp:intent-anchor in Codex). Also use, rarely, when the user strongly corrects the direction of the work itself (for example \"that's not what I meant\", \"you missed my point\", \"이해 못했네\", \"원래 의도는\", \"산으로 간다\") or when the same goal keeps being retried through repeated rewrites or versions. Compares the current work against every raw user message with a fresh-context top model, then stops and asks before changing course. Not for ordinary bug reports, typo fixes, direction changes the user made themselves, or one or two retries."
---

# Intent anchor

작업이 사용자의 원래 의도에서 벗어났는지(드리프트)를 사용자 발화 원문을 기준으로, 이 작업에 참여하지 않은 최고 수준 모델과 대조한다. 벗어났으면 작업을 멈추고 사용자에게 묻는다. 방향 변화의 근거가 사용자 발화에 있으면 원래 요청과 멀어 보여도 정상적인 진화로 본다.

## 언제 실행하는가

- 사용자가 명시적으로 호출하면 실행한다.
- 자동 실행은 드물게 한다. 다음 중 하나가 분명할 때만 실행한다.
  - 사용자가 작업 방향 자체를 바로잡는다. 단순 버그·오타·표현 지적은 해당하지 않는다.
  - 같은 목표에 수정·재시도가 계속 쌓여, 수단이 목적을 대체했을 가능성이 있다. 예를 들어 같은 산출물의 버전이 거듭 늘어나는 경우다. 한두 번의 재시도는 해당하지 않는다.
- 자동으로 실행할 때는 첫 줄에 어떤 신호였는지 밝히고, 진행 중인 작업을 멈춘 상태로 둔다.
- 이 스킬을 다른 스킬의 선행 조건이나 훅에 연결하지 않는다.

## 절차

1. **기록 폴더를 정한다.** 프로젝트 폴더의 `handoffs/realign/<YYYY-MM-DD>-<작업-슬러그>/`를 쓴다. 프로젝트 폴더가 연결된 git worktree 안이면(`git rev-parse --git-dir`와 `--git-common-dir`의 결과가 다르고 submodule이 아닌 경우) 주 체크아웃의 루트(`git rev-parse --path-format=absolute --git-common-dir`의 상위 디렉터리)를 쓴다. 같은 이름이 있으면 `-2`, `-3`을 붙인다. `.gitignore`와 커밋 여부는 바꾸지 않는다.
2. **`ai-state.md`를 쓴다.** 기록 폴더에 다음을 쓴다. 각 항목에는 근거(파일 경로, 명령, 커밋)를 붙인다.
   - 메인이 이해한 현재 목표
   - 지금 하는 일과 다음 계획
   - 최근의 방향 전환과 그 계기

   사용자 의도는 이 파일에 쓰지 않는다. 사용자 발화는 스크립트가 원문 전부를 붙이며, 메인이 요약하거나 골라서 넣지 않는다.
3. **리뷰어를 실행한다.** 스크립트는 이 스킬의 기본 디렉터리(스킬을 불러올 때 표시되는 경로) 아래에 있다. 절대 경로로 실행한다.

   ```bash
   python3 "<skill-dir>/scripts/run_reviewer.py" --state "<폴더>/ai-state.md" --out "<폴더>" --round 1
   ```

   - 현재 세션은 자동으로 찾는다. 다른 세션은 `--session-id` 또는 `--log`로 지정한다.
   - 사용자 발화에 경로가 없는 이전 핸드오프를 알고 있으면 `--handoff <경로>`로 추가한다.
   - 메인 런타임을 알 수 없다는 오류가 나오면 `--main-runtime claude|codex`를 지정한다.
   - 리뷰어는 반대 계열의 최고 모델을 우선하고(Claude 메인이면 Codex Astra, Codex 메인이면 Claude Opus), 실패하면 다음 순위로 내려간다. effort는 high, 권한은 읽기 전용이다.

   종료 코드에 따라 다음과 같이 처리한다.
   - `0`: `round-N/response.md`를 읽는다.
   - `3`(원문 미확인): 대화 기억으로 대신하지 않는다. 사용자에게 세션 로그 경로를 한 번 묻는다.
   - `4`(모든 리뷰어 실패): `round-N/request.md`를 읽고 메인이 직접 대조한다. 보고에 "자기 검토, 교차 검증 아님"을 밝힌다.
   - `2`: 출력된 사용 오류를 고친다. 기존 회차 기록은 덮어쓰지 않는다.
4. **판정을 검토한다.** 판정에 동의하면 5단계로 간다. U번호나 파일 근거로 반박할 수 있을 때만 `<폴더>/rebuttal-N.md`를 쓰고 `--round N --rebuttal <파일>`로 다음 회차를 실행한다. 토론은 최대 3회다. 판정이 불리하다는 이유만으로 반박하지 않으며, 근거 없는 반박("제 판단으로는")은 쓰지 않는다.
5. **보고한다.**
   - **드리프트 있음·부분:** 작업을 멈추고 다음을 짧게 보고한 뒤 질문 하나를 한다. 선택지 도구가 있으면 사용한다. 경로 수정과 되돌리기(코드 롤백, 외부 변경 취소)는 사용자 답을 받은 뒤에만 한다.
     - 원래 의도: 원문을 인용한 두세 줄(U번호)
     - 벗어난 지점: 한두 개 항목과 근거
     - 멈춘 작업 / 되돌릴 후보
     - 질문 하나
   - **드리프트 없음:** 재확인한 최종 의도와 현재 작업의 연결을 몇 줄로 보고하고, 멈춘 작업을 이어 간다.
   - **3회 안에 합의하지 못함:** 양쪽 입장과 근거를 나란히 보여 주고 질문 하나를 한다.

   모든 보고에는 리뷰어의 실제 모델(`invocation.json`의 `selected`), 폴백 이력, 회차, 기록 폴더 경로를 적는다.

## 원칙

- 사용자 발화 원문이 기준이다. AI가 쓴 요약·기획·핸드오프 §2는 원문으로 확인되기 전에는 사실로 쓰지 않는다.
- 리뷰어의 결론은 권고다. 사용자의 결정을 대신하지 않는다.
- 모델을 몰래 바꾸지 않는다. 폴백했으면 보고에 밝힌다.
- 비밀값은 기록하지 않는다. 스크립트는 비밀 키 이름 뒤의 값을 가리지만, `ai-state.md`와 반박에도 값을 쓰지 않는다.
