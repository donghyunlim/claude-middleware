## wrxp

Reply in the language the user writes in unless they ask otherwise. Use available wrxp skills only when their scope matches the task. Keep detailed procedures in the plugin, not in this file. Preserve user/project instructions and existing approvals; simplify small edits and do not stack full pipelines for the same phase.

- Development: use `wrxp:staged-development` for large or hard-to-reverse development, or work whose product direction is unresolved. If unavailable, reuse one canonical plan and proceed through outline agreement → core implementation/review → detail/tests; consult the user when scope or important decisions change.
- Tests: run existing project commands for already-needed checks and retain command, exit status, and raw evidence. Do not repeat or expand checks without relevant changes, failures, or concrete risks.
- Search: search directly by default. Use `wrxp:search-delegation` only for broad discovery/compression across substantial scattered knowledge. Otherwise, if delegation is needed and the skill is unavailable, pass context, question, scope, and stopping conditions; require source locations and check decisive conditions/conflicts. System size, MCP availability, or several queries alone do not justify delegation.
- Coding: use `wrxp:code-delegation` for approved independent implementation. Otherwise hand off the existing plan, ownership, and acceptance criteria; the worker implements and self-tests without recursive delegation. Pin the worker per runtime: in Codex, `gpt-6.1-sol` with `medium` by default or AI-selected `high` for complex work; in Claude, `Agent.model` `opus` (Claude Opus 5.5) by default or `sonnet` for light, narrow work, without offloading to Codex. Exclude lower tiers (`low`, `haiku`), an omitted model or effort, and silent model fallback. Keep tiny edits direct. Accept adequate current-code evidence without automatic whole-task re-review, except that a shared-contract change gets one fresh-context review (`sonnet` in Claude, `gpt-6.1-sol` `high` in Codex); investigate concrete risks and honor requested reviews.
- Session transfer: use `wrxp:handoff` only when explicitly invoked by the user. Do not start it during routine summaries or completion.
- Intent drift: use `wrxp:intent-anchor` when explicitly invoked, or rarely when the user strongly corrects the direction of the work; it compares the work against the user's raw messages with a fresh-context top model, then stops and asks before changing course.
- Orchestration: `wrxp:ha`, `wrxp:haq`, `wrxp:haqq`, `wrxp:haqqq` handle a convergent task. Choose only when requested or relevant; question depth does not select the model. Keep the current development stage and permission boundaries.
- Setup: use `wrxp:setup` only for requested setup/update/removal of these connections, not on every task. Never treat setup or delegation as permission to install unrelated tools, access credentials, commit, push, or deploy.

### 한국어 출력 원칙

- 한국어로 답하거나 한국어 결과물을 작성할 때에는 의미가 분명하고 자연스러운 현대 한국어를 사용합니다. 이 원칙은 외국어로 작성해야 하는 내용을 한국어로 번역하거나 대체하라는 뜻이 아닙니다.
- 문맥을 이해하는 데 필요한 주체, 대상, 조건과 영향 범위를 생략하지 않습니다. 예를 들어, "그러면 경고가 붙습니다"라고만 쓰지 않고 어떤 대상에 경고가 추가되는지 밝힙니다.
- 의미 관계를 분명히 하는 조사와 어미를 사용합니다. 다만 자명한 내용을 반복하거나 보조 표현을 늘려 문장을 불필요하게 장황하게 만들지 않습니다.
- 일반 문장은 서술어와 종결어미를 갖춘 완결된 형태로 마무리합니다. 제목, 표, 목록, 레이블과 짧은 상태 표시는 예외로 합니다.
- 널리 통용되는 정확한 어휘를 우선하며, 불필요한 비유·과장·희귀어를 피합니다. 예를 들어, "코드로 박습니다"보다 "코드에 명시합니다"라고 표현합니다.
- 통용되는 한국어 번역어나 음차가 있는 기술 용어는 이를 우선하고, 그렇지 않은 고유명사와 기술 용어는 원어를 유지합니다.
- 사용자가 지정한 언어, 높임말, 문체, 형식과 프로젝트 관례를 우선합니다. 사용자가 의도적으로 생략, 비문 또는 전보식 표현을 요구한 경우에는 그 요구를 따르고, 그렇지 않은 경우에는 그러한 표현을 모방하지 않습니다.
- 코드, 식별자, 명령어, 경로, API 필드, 주석, 로그, 오류 메시지, 커밋 메시지와 인용문에는 원문 또는 프로젝트 관례를 적용합니다.
- 소설, 대본, 번역 등 별도의 문체 지침이 있는 결과물에는 해당 지침을 우선합니다.
- 서브에이전트의 결과를 사용자에게 전달할 때에도 한국어 부분은 이 원칙에 맞게 정리합니다.
- 최종 출력 전에 대상이 모호한 표현, 필요한 문장 성분·조사·어미의 누락, 명사 나열형 불완전 문장이 없는지 점검합니다.
- 완성된 한국어 보고서, 공지, 명세처럼 사용자에게 전달할 산출물은 마지막에 `wrxp:korean-polish`로 교정합니다. 채팅 답변과 초안에는 쓰지 않습니다.
