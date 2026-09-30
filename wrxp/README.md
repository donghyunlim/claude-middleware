# wrxp — Universal Reasoning & Execution Pipeline for Claude Code

> 필요한 사용자 결정만 질문하고, 작업 속성에 맞는 모델로 실행한 뒤 근거를 검증하는 범용 reasoning-and-execution 파이프라인.

[![version](https://img.shields.io/badge/version-0.1.40-blue.svg)](./package.json)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![marketplace](https://img.shields.io/badge/marketplace-donghyunlim-orange.svg)](https://github.com/donghyunlim/claude-middleware)

## 무엇인가 (What is it?)

**wrxp**(Universal Reasoning & Execution Pipeline)는 Claude Code용 범용 reasoning-and-execution 플러그인이다. code뿐만 아니라 writing, planning, research, analysis, decision, creative, learning 등 9가지 task type에 동일한 품질 보증 파이프라인을 적용하여, 사용자의 요청을 높은 수준의 산출물로 변환한다.

wrxp의 reasoning 축은 **Knife family**다:

- **🗡️ Knife family (`ha` / `haq` / `haqq` / `haqqq`)** — **단일 수렴 목표의 task graph 실행**. 독립 단위만 런타임 한도 안에서 병렬 위임한다. `/ha`가 질문·라우팅·실행·검증의 canonical engine이며 나머지 셋은 질문 상한만 다른 thin shim이다.

Knife family는 `shared/reasoning-framework.md`의 9원칙을 따른다.

### Knife 모델 라우팅

합의된 독립 코드 구현은 아래 일반 라우팅보다 [`code-delegation`](skills/code-delegation/SKILL.md)이 우선한다. Codex·Claude 모두 `gpt-6-sol`의 `medium`을 기본으로, 복잡한 구현에는 AI가 `high`를 선택한다. `low`·사고 수준 생략·무단 모델 폴백은 허용하지 않는다. 작업자가 구현과 자체 검증을 수행하며, 충분한 최신 근거가 있으면 메인의 전체 재검증을 자동으로 추가하지 않는다. 기존 Terra 실험은 Sol의 성능 측정 결과가 아니다.

`/ha`가 유일한 registry다. Codex에서는 종합 판단=`gpt-6-astra`, 일반 구현·중간 리팩터링=`gpt-5.6-terra`, 단순 탐색·국소 변경=`gpt-5.6-luna`를 선호한다. Claude에서는 같은 역할을 Opus 5, Sonnet 5, Haiku 4.5에 대응한다. 정확한 모델과 사고 수준은 런타임 가용성을 먼저 확인하고, 지원되지 않으면 같은 역할의 가용 모델 또는 런타임 기본 모델로 폴백한다.

`/haq`·`/haqq`·`/haqqq`는 질문 상한만 전달한다. **질문 깊이와 모델 라우팅은 서로 독립적인 축이다.** 동시 위임 수는 런타임이 공개한 한도를 따르며, 미확인 또는 위임 불가 시 1로 폴백한다.

추가로 `breakdown`, `decompose`, `agent-match` orchestration 축, 단계별 협업의 `staged-development`, 맥락 기반 검색 위임의 `search-delegation`, 세션 인계의 `handoff`, 의도 대조의 `intent-anchor`, 합의된 구현 위임의 `code-delegation`, 전역 연결 관리의 `setup`, 인프라 요청 검토의 `cloudinfra-review`가 있다. 총 14개 skill.

**핵심 철학**: Knife family는 controller가 의도를 통합하고 의존성 그래프의 독립 단위를 실행한다.

wrxp의 **Uncertainty-Driven Questioning**은 질문 전에 대화·파일·문서·도구를 먼저 확인한다. 직접 `/ha`는 `none` preset(0문항·0라운드)으로 실행하며, 승인·보안·비밀·외부 변경·파괴적·불가역 경계만 discovery 예산 밖에서 즉시 확인한다. `/haq`·`/haqq`·`/haqqq`는 질문 tier에 따라 `decision_quality` 선택을 물을 수 있다.

Knife family의 수정 루프는 실제 결함이 남아 있는 동안 횟수만으로 중단하지 않는다. 검증 뒤에도 수정이 더 필요하면 5·15·25회에는 에이전트가 원래 목적·계획·수정의 필수성을 점검하고, 10·20·30회에는 진행 상황과 다음 선택을 요약해 사용자 판단을 받는다. 모든 수용 기준이 충족되면 배수에 도달했더라도 바로 완료하며, 새 권한·외부 변경·보안 경계 확대는 체크포인트를 기다리지 않고 즉시 확인한다.

## 왜 쓰는가 (Why use it?)

- **환각 감소 (Hallucination reduction)**: Chain-of-Verification 4-step 프로세스(arXiv:2309.11495) 주입으로 longform generation hallucination 50-70% 감소. Reflexion(arXiv:2303.11366) self-reflection 루프로 HumanEval pass@1 80%→91% (+11%). Research/Decision task에서는 CoVe 적용이 mandatory다.
- **질문 효율 (Question efficiency)**: 증거로 확인할 사실은 먼저 조사하고, 반드시 확인해야 하는 결정과 산출물의 쓰임을 바꾸는 사용자 선택만 질문한다. 모든 질문 수는 상한이며, 어떤 tier에서도 0문항으로 종료할 수 있다.
- **Task type 커버리지 (Task type coverage)**: NBER WP #34255 (2025년, 1.1M ChatGPT 대화 분석) 분류 체계와 Anthropic Clio 데이터를 매핑하여 9가지 task type 확정. analysis(신규)를 포함한 9 types은 사용자 workload 전 스펙트럼을 cover한다.
- **병렬 실행**: Knife family는 독립 task unit을 런타임 한도 안에서 실행한다.

## 어떻게 쓰는가 (How to use it?)

### 설치

#### Codex

```bash
codex plugin marketplace add donghyunlim/claude-middleware --ref main
codex plugin add wrxp@donghyunlim
```

업데이트는 marketplace snapshot을 갱신한 뒤 Codex를 다시 시작합니다.

```bash
codex plugin marketplace upgrade donghyunlim
codex plugin add wrxp@donghyunlim
```

#### Claude Code

```bash
claude plugin marketplace add donghyunlim/claude-middleware
claude plugin install wrxp@donghyunlim
```

업데이트는 다음 순서로 실행한 뒤 Claude Code를 다시 시작합니다.

```bash
claude plugin marketplace update donghyunlim
claude plugin update wrxp@donghyunlim
```

### 신규 사용자 전역 셋업

플러그인을 설치한 뒤 **Codex에서는 `$wrxp:setup`, Claude Code에서는 `/wrxp:setup`**을 호출하고 `Codex`, `Claude`, `양쪽` 중 대상을 지정한다. 예: `양쪽 전역 지침에 wrxp를 설정해 줘`. 플러그인이 스킬을 제공하므로 개인 skills 폴더에 스킬을 복제할 필요는 없다.

셋업은 설치·활성 상태를 확인하고 전역 `AGENTS.md`/`CLAUDE.md`에 짧은 wrxp 관리 구역을 추가한다. 개발·테스트·검색·코드 위임은 필요한 상황에 연결하고, `ha` 계열·분해 도구는 선택 용도를 안내하며, `handoff`는 명시 호출 제한을 유지한다. 전체 스킬 절차나 개인 업무 설정을 전역 파일에 복사하지 않는다.

기존 사용자 설정과 OMC 구역을 보존하고, 변경 전 백업·읽기 전용 미리보기·재실행 시 중복 방지·관리 구역만 제거하는 기능을 제공한다. 플러그인 업데이트 후 `wrxp:setup`을 다시 실행하면 연결 규칙도 갱신된다. 상세 동작은 [셋업 스킬](./skills/setup/SKILL.md), 설치되는 짧은 규칙은 [관리 구역 원본](./skills/setup/assets/global-rules.md)에 있다. 플러그인 설치만으로 셋업을 자동 실행하지 않는다.

기존 관리 표시가 깨졌거나 모호하면 원문을 고치거나 설치를 막지 않고 새 규칙만 추가한다. 갱신·제거는 안전하게 식별되는 추가분에 한정하며, 남아 있는 기존 규칙을 함께 보고한다. 잘못된 인코딩·심볼릭 링크·권한·동시 변경 등의 실제 파일 접근 오류는 이 추가 방식으로 우회하지 않는다. 공통 배포본은 다른 플러그인과의 우선순위를 지정하지 않는다.

셋업 실행기는 Python 3.9 이상이 필요하다. 코드 위임은 `gpt-6-sol` medium/high를 명시할 수 있는 실행 경로가 필요하며, Claude에서 해당 경로가 없으면 코드 위임만 준비 미완료로 안내한다. Semble·MAGMA·Qwen·BWS나 다른 플러그인은 자동 설치하지 않는다. 전역 연결 설치와 실제 모델·도구 접근 가능 여부는 별도로 확인한다.

### 맥락 기반 검색 위임

`/wrxp:search-delegation`은 여러 저장소·모듈·문서에 흩어진 대규모 지식을 넓게 탐색·압축해야 할 때만 사용한다. 그 외의 검색은 직접 수행한다. 시스템 전체의 크기나 로컬/MAGMA 여부가 아니라 이번 질문의 탐색 범위가 기준이다. 맥락·질문·범위·종료 조건을 짧게 전달하고, 변경을 좌우하는 조건과 근거 충돌은 주 모델이 직접 확인한다.

[스킬 본문](./skills/search-delegation/SKILL.md)과 [의뢰 예시](./skills/search-delegation/references/search-brief.md)에 실행 범위와 인계 계약이 있다. 실제 MCP 스키마·접근 가능성을 따르며 페이지네이션이나 근거 ID가 이미 구현됐다고 가정하지 않는다. 속도 개선율을 보장하는 규칙이 아니다.

[검색 수단 선택](./skills/search-delegation/references/search-routing.md)에 따라 로컬 의미 검색은 Semble, MAGMA 레거시는 MAGMA MCP, 알려진 파일의 작은 조회는 직접 읽기로 나눈다. 검색 수단과 위임 여부는 별도로 결정하며 Codex·Claude의 기존 작업자 연결을 재사용한다. Semble과 다른 검색 에이전트를 같은 후보에 중복 파견하지 않는다.

전역 연결은 `wrxp:setup`에서 관리한다.

### 단계별 협업 개발

```text
/wrxp:staged-development "고객 선택 화면을 함께 기획하고 구현해 줘"
```

중·대규모 개발이나 제품 방향·주요 설계가 불명확한 작업에 사용한다. 작업별 기획서 하나를 정본으로 두고 **아웃라인 합의 → 핵심 흐름 구현·검토 → 상세 개발·검증** 순서로 진행한다. 기존 기획서와 사용자 합의를 재사용하므로 이어서 작업할 때 같은 승인을 반복하지 않는다.

기획서에는 목적·범위·성공 조건, 합의된 결정과 미해결 질문, 현재 단계·진행 범위·다음 검토물, 검증 근거를 기록한다. 목적·범위·성공 조건의 중요한 변경은 사용자와 합의한 뒤 반영한다. 합의된 검토를 자동으로 위임할 수 있으며, 단순하고 영향이 작은 수정은 기획서와 단계 승인을 생략한다.

이 스킬은 `ha` 등 기존 엔진 전체를 연쇄 실행하지 않는다. 현재 단계에 필요한 작업만 선택하고, 핵심 불변조건은 초기부터 검증하며, 확정된 동작의 상세 개발에는 필요한 TDD를 적용한다. 사용자가 선택한 모델을 유지하므로 Codex의 Astra와 Claude Code에서 같은 협업 절차를 사용할 수 있다.

자동 적용 연결은 `wrxp:setup`에서 관리한다. 상세 절차는 [스킬 본문](./skills/staged-development/SKILL.md)에 유지한다.

명시적 호출은 `/wrxp:staged-development` 또는 런타임의 스킬 선택기를 사용한다. 자동 선택에는 플러그인이 설치·활성화되어 있어야 한다. [Astra 행동 검증 기록](./docs/benchmark/staged-development-0.1.29.md)은 실제 시나리오 결과와 검증 범위를 설명한다.

### 세션 핸드오프

`/wrxp:handoff`(Codex에서는 `$wrxp:handoff`)는 사용자가 필요하다고 판단한 시점에 현재 작업을 새 세션이 이어받을 문서로 기록한다. 사용자가 명시적으로 호출할 때만 실행되며 AI가 임의로 시작하지 않는다.

문서는 사용자 의도 세트(최초 의도·작업 중 결정·최종 의도)를 AI 기획과 분리해 기록하고, 현재 상태·문제점·미결 사항을 평가 없이 사실과 근거로 남긴다. 압축된 세션에서도 최초 의도를 원문으로 인용할 수 있도록 포함된 스크립트가 Claude Code·Codex 세션 로그에서 사용자 메시지를 추출한다. 저장 위치는 프로젝트 폴더의 `handoffs/`이며, 저장 후 새 서브에이전트가 문서만 읽고 재개에 필요한 질문에 답하는지 확인한다. 자세한 구조는 [handoff 스킬](./skills/handoff/SKILL.md)에 있다.

`/wrxp:intent-anchor`(Codex에서는 `$wrxp:intent-anchor`)는 작업이 사용자의 원래 의도에서 벗어났는지 사용자 발화 원문 전부를 기준으로 다른 맥락의 최고 수준 모델과 대조한다. 사용자가 작업 방향 자체를 바로잡거나 같은 목표의 재시도가 계속 쌓일 때는 드물게 자동으로 실행된다. 방향 변화의 근거가 사용자 발화에 있으면 허용하고, 벗어났으면 작업을 멈춘 뒤 질문 하나를 한다. 리뷰어는 읽기 전용으로 실행되며 기록은 프로젝트 폴더의 `handoffs/realign/`에 남는다. 자세한 절차는 [intent-anchor 스킬](./skills/intent-anchor/SKILL.md)에 있다.


### 클라우드 인프라 요청 검토

`/wrxp:cloudinfra-review`(Codex에서는 `$wrxp:cloudinfra-review`)로 요청 초안이나 Slack 스레드를 전달하면, 필요한 정보·표준 신청 경로·담당 범위·적용 및 검증 조건을 검토하고 복사해 보낼 문안을 작성합니다. 명시적으로 호출할 때만 실행되며 일반 배포 요청이나 기존 파이프라인에 자동 연결하지 않습니다.

```text
$wrxp:cloudinfra-review 이 외부 API 구성 요청을 검토하고 제출 문안으로 다듬어 줘. [초안 또는 스레드]
```

작업 요청·검토 문의·장애 조사 단계에 맞춰 필수 누락과 권고를 구분합니다. 확인되지 않은 값은 만들지 않고, 단순 표준 요청에는 불필요한 설계 항목을 요구하지 않습니다. 검토 호출만으로 Slack 게시·배포·인프라 변경을 수행하지 않습니다. [스킬 본문](./skills/cloudinfra-review/SKILL.md), [유형별 검토 기준](./skills/cloudinfra-review/references/review-rubric.md), [문안 예시](./skills/cloudinfra-review/references/request-examples.md), [행동 검증 기록](./docs/benchmark/cloudinfra-review-0.1.38.md)을 참고하세요.

Jenkins 유지·GitLab CI 최초 구성·환경별 병존/이관은 [배포 경로별 기준](./skills/cloudinfra-review/references/deployment-paths.md)으로 검토합니다. 도구 이름만으로 전환을 요구하지 않고 서비스·환경의 합의와 실제 실행·적용 상태를 구분합니다.

### 🗡️ Knife family (runtime-bounded task graph)

#### /wrxp:ha — 기본 knife (default)

```
/wrxp:ha "이 함수의 off-by-one 버그 고쳐줘"
```

`none` preset은 질문 0개·0라운드이며, 승인·보안 등 실행 통제 경계가 아니라면 바로 실행한다. 하나의 사고 갈래로 수렴하는 작업에 적합하다.

#### /wrxp:haq — 빠른 knife

```
/wrxp:haq "결제 실패 시 재시도 로직 추가"
```

`quick`, 질문 0~4개, 최대 1라운드. 한 번의 빠른 사용자 결정 확인이 필요할 때 사용한다.

#### /wrxp:haqq — 중간 knife

```
/wrxp:haqq "이 분석 쿼리의 성능 문제 진단하고 개선"
```

`standard`, 질문 0~8개, 최대 2라운드. 첫 답변 뒤 남은 결정을 다시 평가하는 표준 발견에 사용한다.

#### /wrxp:haqqq — 심층 knife

```
/wrxp:haqqq "이 migration이 prod에 안전한지 tier 최상급으로 검증"
```

`deep`, 질문 0~12개, 최대 3라운드. 한 라운드에는 최대 4개만 묻는다. 기본 상한을 넘길 때는 사용자 동의를 받아 절대 상한 20개·5라운드까지 확장한다. 비가역·고위험 단일 문제에 적합하다.

### 보조 skill

#### /wrxp:breakdown — 전체 orchestration 파이프라인

```
/wrxp:breakdown "소셜 로그인 + 결제 연동 + 알림 시스템 묶어서 추가"
```

Phase 1-7 전체 자율 실행. 의도 정제 → 재귀 분해 → Implementation Plan → Agent Matching → Strategy Selection → DAG 병렬 실행 → Result Integration. 여러 독립 feature를 함께 구현해야 할 때.

#### /wrxp:decompose — 의도 정제 + 재귀 분해

```
/wrxp:decompose "제품 검색이 느려서 사용자 이탈이 커지는 문제 해결"
```

Phase 1+2만 실행 — 분해 트리까지만 보고 실행은 나중으로 미루고 싶을 때. 출력: `.wrxp/state/intent-{slug}.md`, `tree-{slug}.json`.

#### /wrxp:agent-match — DAG 구성 + 에이전트 매칭

```
/wrxp:agent-match "태스크 목록 JSON 경로"
```

Phase 4만 실행 — 이미 분해된 task list가 있을 때, dynamic agent matching과 DAG construction만 수행. 출력: `.wrxp/state/dag-{slug}.json`.

## Tier 비교표

### 🗡️ Knife family (runtime-bounded task graph)

| Tier | 질문 수 | Rounds | Fleet | 용도 |
|---|---|---|---|---|
| /wrxp:ha (default) | 0 | 0 | runtime-bounded task graph | 승인·보안 게이트만 확인 |
| /wrxp:haq | 0-4 | 1 | runtime-bounded task graph | 빠른 확인 |
| /wrxp:haqq | 0-8 | 2 | runtime-bounded task graph | 표준 발견 |
| /wrxp:haqqq | 0-12 (동의 시 max 20) | 3 (동의 시 5) | runtime-bounded task graph | 고위험 단일 문제 심층 확인 |

## 9 Task Types

| Task Type | 용도 | 산출물 template |
|---|---|---|
| **code** | 구현, 디버깅, 리팩토링, API 설계 | 모듈 signature + I/O schema + error categories + testing approach |
| **writing** | blog, article, proposal, docs, 문학 | audience + tone + structure + quality bar |
| **planning** | 프로젝트 기획, 전략, 타임라인 | goal + milestones + resources + risk register |
| **research** | literature review, synthesis, 탐색 | question + scope + source priorities + bias control |
| **analysis** | 데이터 분석, BI, metrics, 통계 | analysis question + data quality + methodology + sensitivity |
| **decision** | 비교, trade-off, go/no-go | alternatives + criteria + weighting + reversibility |
| **creative** | story, art, music, game 설계 | core idea + audience + style + revision plan |
| **learning** | how-to, skill 개발, 커리큘럼 | current→target level + modality + assessment |
| **other** | 그 외 (자가 분류 재시도 후 fallback) | Phase 0 재-dispatch 또는 유저 확인 |

## 주요 feature

- **Pre-Q / Post-Q Deep Reasoning**: 15개 연구 논문 기반 (Self-Ask, ToT, Least-to-Most, Plan-and-Solve, Uncertainty of Thoughts, Reflexion, Self-Refine, Chain-of-Verification 등)
- **Uncertainty-Driven Questioning**: Bayesian OED 이론 + arXiv:2503.16419 "Stop Overthinking" skip gate + Cowan 4-chunk working memory 한계 준수
- **Decision-Gated Questions**: 직접 `/ha`는 실행을 막는 승인·보안 경계만 묻고, 질문 tier는 `decision_quality` 선택을 우선순위대로 질문
- **Task-Type-Aware Verification**: 9 types마다 전용 verification recipe. Research는 DOI/citation mandatory 검증, Decision은 alternatives audit + bias audit + sensitivity flagging

## 상세 리서치 리포트

wrxp의 모든 설계 결정은 publicly verifiable 연구에 근거한다. 구체적인 benchmark 수치(Self-Ask +42% Bamboogle, ToT 4%→74% Game of 24, Reflexion 80→91% HumanEval, CoVe 50-70% hallucination 감소, UoT +120% MedDG, EVPI 1.5-2.7x question reduction 등), Before/After 비교, 20개 이상의 arXiv citation, NBER 1.5M ChatGPT taxonomy 매핑, 19개 expert discovery protocol 분석은 별도 문서를 참조.

[**docs/RESEARCH_REPORT.md**](./docs/RESEARCH_REPORT.md) — Universal Reasoning-and-Execution Pipeline의 Evidence Base (10,000+ 단어, 포괄적)

## Composable usage

### 🗡️ Knife family (runtime-bounded task graph)

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/wrxp:ha "요청"` | 공통 상태 흐름 + 질문 0개/0라운드 | 승인·보안 경계가 아닌 한 즉시 실행 |
| `/wrxp:haq "요청"` | 공통 상태 흐름 + 최대 1라운드 | 빠른 확인 |
| `/wrxp:haqq "요청"` | 공통 상태 흐름 + 최대 2라운드 | 표준 발견 |
| `/wrxp:haqqq "요청"` | 공통 상태 흐름 + 최대 3라운드(동의 시 5) | 고위험 단일 문제 심층 확인 |

### Orchestration family

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/wrxp:breakdown "요청"` | Phase 1-7 orchestration | 재귀 분해 + DAG 병렬 실행 |
| `/wrxp:decompose "문제"` | breakdown Phase 1+2만 | 분해 트리까지만 |
| `/wrxp:agent-match "태스크"` | breakdown Phase 4만 | Agent matching + DAG만 |

### 선택 가이드

| 상황 | 권장 |
|---|---|
| 문제가 한 갈래로 수렴, 산출물 단일 | `/wrxp:ha` 계열 (knife) |
| 여러 feature 묶어 자율 실행 | `/wrxp:breakdown` |
| 분해 트리만 보고 싶을 때 | `/wrxp:decompose` |

knife 계열과 breakdown 계열은 직교한다. knife는 quality tier (추론 깊이)를, breakdown은 execution scope (분해 깊이)를 제어한다. 필요하면 breakdown의 각 task를 /wrxp:haqqq로 escalate할 수도 있다.

## State 파일 구조

```
.wrxp/state/
├── intent-{slug}.md           # Phase 1: 정제된 의도 (breakdown)
├── tree-{slug}.json           # Phase 2: 분해 트리 (breakdown)
├── plan-{slug}.md             # Phase 3: Implementation Plan (breakdown)
├── dag-{slug}.json            # Phase 4: Agent-matched DAG (breakdown)
├── strategy-{slug}.json       # Phase 5: 선택된 실행 전략 (breakdown)
├── execution-{slug}.json      # Phase 6: 실행 진행 상태 (breakdown)
└── breakdown-{slug}.json      # 전체 파이프라인 상태
```

`{slug}` = 요청 기반 짧은 식별자 (예: `add-social-login`, `redesign-auth`).

## License

MIT — see `LICENSE`.
