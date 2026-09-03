# wrxp — Universal Reasoning & Execution Pipeline for Claude Code

> 필요한 사용자 결정만 질문하고, 작업 속성에 맞는 모델로 실행한 뒤 근거를 검증하는 범용 reasoning-and-execution 파이프라인.

[![version](https://img.shields.io/badge/version-0.1.25-blue.svg)](./package.json)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![marketplace](https://img.shields.io/badge/marketplace-donghyunlim-orange.svg)](https://github.com/donghyunlim/claude-middleware)

## 무엇인가 (What is it?)

**wrxp**(Universal Reasoning & Execution Pipeline)는 Claude Code용 범용 reasoning-and-execution 플러그인이다. code뿐만 아니라 writing, planning, research, analysis, decision, creative, learning 등 9가지 task type에 동일한 품질 보증 파이프라인을 적용하여, 사용자의 요청을 높은 수준의 산출물로 변환한다.

wrxp의 reasoning 축은 **2개 대칭 family**로 구성된다:

- **🗡️ Knife family (`ha` / `haq` / `haqq` / `haqqq`)** — **단일 사고 갈래, 직렬 실행**. 동시 dispatching OFF. 문제가 한 갈래로 수렴할 때 사용한다. `/ha`가 질문·라우팅·실행·검증의 canonical engine이며 나머지 셋은 질문 상한만 다른 thin shim이다.
- **🛡️ Team family (`cast` / `castq` / `castqq` / `castqqq`)** — **Fleet ON, 병렬 specialized subagents**. Phase 1/5/6에서 3-20개 agent 병렬 dispatch. 다면 분석·교차 검증·여러 관점이 가치를 더할 때. /cast 가 canonical engine, 나머지 셋은 thin shim.

두 family는 `shared/reasoning-framework.md`의 9원칙을 공유한다. 선택 기준: **사고의 흐름이 하나의 갈래면 /ha, 여러 갈래의 병렬 탐색이 본질이면 /cast**.

### Knife 모델 라우팅

`/ha`가 유일한 registry다. Codex에서는 종합 판단=`gpt-5.6-sol`, 일반 구현·중간 리팩터링=`gpt-5.6-terra`, 단순 탐색·국소 변경=`gpt-5.6-luna`를 선호한다. Claude에서는 같은 역할을 Opus 5, Sonnet 5, Haiku 4.5에 대응한다. 정확한 모델과 사고 수준은 런타임 가용성을 먼저 확인하고, 지원되지 않으면 같은 역할의 가용 모델 또는 런타임 기본 모델로 폴백한다.

`/haq`·`/haqq`·`/haqqq`는 질문 상한만 전달한다. **질문 깊이와 모델 라우팅은 서로 독립적인 축이다.** `max_concurrency: 1`은 동시 실행을 금지하지만 worker와 verifier를 한 명씩 순차 호출하는 것은 허용한다.

추가로 `breakdown`, `decompose`, `agent-match` orchestration 축이 있다 (재귀 분해 + DAG 병렬). 총 11개 skill.

**핵심 철학**: Knife family는 controller가 의도를 통합하고 작업 속성에 맞는 단일 executor와 verifier를 순차 사용한다. Team family는 독립적인 전문 관점의 병렬 탐색이 필요한 경우에만 Fleet Dispatching을 사용한다.

wrxp의 **Uncertainty-Driven Questioning**은 질문 전에 대화·파일·문서·도구를 먼저 확인한다. 그 뒤에도 남은 사용자 소유 결정을 `must_ask`와 `decision_quality`로 나눈다. 전자는 승인·보안·비가역성처럼 잘못 가정하면 안 되는 결정이고, 후자는 자료의 독자·용도·공유 범위·결정 권한처럼 산출물의 쓰임을 바꾸는 선택이다. 질문 예산은 항상 상한이므로 두 종류의 후보가 모두 없으면 모든 tier에서 질문 0개가 정상이다.

Knife family의 수정 루프는 실제 결함이 남아 있는 동안 횟수만으로 중단하지 않는다. 검증 뒤에도 수정이 더 필요하면 5·15·25회에는 에이전트가 원래 목적·계획·수정의 필수성을 점검하고, 10·20·30회에는 진행 상황과 다음 선택을 요약해 사용자 판단을 받는다. 모든 수용 기준이 충족되면 배수에 도달했더라도 바로 완료하며, 새 권한·외부 변경·보안 경계 확대는 체크포인트를 기다리지 않고 즉시 확인한다.

wrxp의 **Fleet Dispatching**은 team family(`/cast` 계열)에 적용된다 — tier별로 dispatching 상한선을 정하여 공격적 병렬화를 허용하면서도 resource 폭주를 방지한다. /cast는 1-5, /castq는 phase당 5, /castqq는 8, /castqqq는 12(critical 시 20) agent를 Phase 1/5/6 각 phase에 dispatch한다. 총 cluster size는 15-60 agents, /castqqq는 unlimited budget이다. 반면 knife family(`/ha` 계열)는 tier와 무관하게 `max_concurrency: 1`이며, 하나의 수렴하는 작업을 순차 실행한다.

## 왜 쓰는가 (Why use it?)

- **환각 감소 (Hallucination reduction)**: Chain-of-Verification 4-step 프로세스(arXiv:2309.11495) 주입으로 longform generation hallucination 50-70% 감소. Reflexion(arXiv:2303.11366) self-reflection 루프로 HumanEval pass@1 80%→91% (+11%). Research/Decision task에서는 CoVe 적용이 mandatory다.
- **질문 효율 (Question efficiency)**: 증거로 확인할 사실은 먼저 조사하고, 반드시 확인해야 하는 결정과 산출물의 쓰임을 바꾸는 사용자 선택만 질문한다. 모든 질문 수는 상한이며, 어떤 tier에서도 0문항으로 종료할 수 있다.
- **Task type 커버리지 (Task type coverage)**: NBER WP #34255 (2025년, 1.1M ChatGPT 대화 분석) 분류 체계와 Anthropic Clio 데이터를 매핑하여 9가지 task type 확정. analysis(신규)를 포함한 9 types은 사용자 workload 전 스펙트럼을 cover한다.
- **병렬 전문가 투입 (Fleet Dispatching)**: Team family에서만 tier별 specialized subagent를 Phase 1(uncertainty 감지), Phase 5(execution), Phase 6(검증)에 동시 dispatch한다. Knife family는 `max_concurrency: 1`을 유지한다.
- **Loop-Back Safety**: 8가지 loop-back 규칙(Ambiguity Spiral, Verification Fail, Scope Creep, Data Unavailable, Complexity Underestimate, Reviewer Deadlock, Token Exhaustion, User Timeout)과 Global Circuit Breaker가 무한 루프와 scope drift를 자동 차단한다.
- **Expert Discovery 패턴 내재화**: 19개의 전문가 discovery 프로토콜(SPIKES, MI, SPIN, Sandler, Five Whys, JTBD, MECE, Calgary-Cambridge 등)에서 추출한 10개 Universal Principle이 파이프라인 설계 전반에 내재되어 있다. Sandler Upfront Contract는 Phase 2 preamble로, Five Whys는 Phase 1-2 depth probe로, MI Reflective Summarization은 Phase 3 통합으로 이어진다.
- **Role Prompting Fix**: KAIST 2025 연구에 따라 persona 기반 prompting("You are a senior X")이 MMLU 등 factual task에서 성능을 떨어뜨린다. wrxp는 모든 agent prompt에서 persona를 제거하고 purpose-focused framing만 사용한다.
- **Confidence Disclosure 자동 주입**: Phase 6 최종 산출물에 tier, 질문 수, agent 수, 잔여 불확실성이 자동으로 disclosure 섹션으로 삽입되어, 사용자는 산출물의 근거와 한계를 언제든 감사(audit)할 수 있다.

## 어떻게 쓰는가 (How to use it?)

### 설치

```bash
claude plugin add donghyunlim/wrxp
```

### 🗡️ Knife family (single-thread, serial execution)

#### /wrxp:ha — 기본 knife (default)

```
/wrxp:ha "이 함수의 off-by-one 버그 고쳐줘"
```

자동 질문 상한은 4개이며, 적격 질문이 없으면 바로 실행한다. 하나의 사고 갈래로 수렴하는 작업에 적합하다.

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

### 🛡️ Team family (fleet-on, parallel)

#### /wrxp:cast — 기본 team (default)

```
/wrxp:cast "OAuth2 소셜 로그인 설계와 구현"
```

다면 분석 기본. Fleet ON, Phase 1/5/6에서 1-5 agents 병렬. 여러 전문가 관점이 가치를 더할 때.

#### /wrxp:castq · /castqq · /castqqq

Knife family와 같은 질문 깊이 ladder이지만 **fleet=ON**. Team은 병렬 expert review + cross-validation이 가치를 더하는 경우에 사용 (security + perf + UX 동시 리뷰, multi-branch decision, 광범위 lifecycle 검증 등). 자세한 세부는 각 skill SKILL.md 참조.

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

## Team family 7단계 파이프라인 (Phase 0-6 at a glance)

아래 그림은 병렬 Fleet을 사용하는 `/cast` 계열의 흐름이다. Knife family인 `/ha` 계열은 위에서 설명한 공통 상태 흐름과 `max_concurrency: 1` 직렬 계약을 사용한다.

```
Phase 0: Context & Task-Type Detection
   ↓ (9가지 task type 자동 분류)
Phase 1: Pre-Q Deep Reasoning (Opus)
   ↓ (ambiguity ledger + Fleet detection agents)
Phase 2: Uncertainty-Driven Questioning (조건부)
   ↓ (EVPI ordering, Cowan 4-chunk, fatigue 자동 stop)
Phase 3: Post-Q Integration Reasoning (Opus)
   ↓ (Reflexion + CoVe)
Phase 4: Task-Type-Aware Design Document
   ↓ (9 template 중 하나)
Phase 5: Execution Delegation (Fleet)
   ↓ (parallel Haiku agents + Blocker Report)
Phase 6: Task-Type-Aware Verification (Fleet)
   ↓ (per-type verification recipe + Confidence Disclosure)
Final Output
```

## Tier 비교표

### 🗡️ Knife family (동시 실행 없음, `max_concurrency: 1`)

| Tier | 질문 수 | Rounds | Fleet | 용도 |
|---|---|---|---|---|
| /wrxp:ha (default) | 0-4 | 2 | 순차 | 균형형 자동 질문 |
| /wrxp:haq | 0-4 | 1 | 순차 | 빠른 확인 |
| /wrxp:haqq | 0-8 | 2 | 순차 | 표준 발견 |
| /wrxp:haqqq | 0-12 (동의 시 max 20) | 3 (동의 시 5) | 순차 | 고위험 단일 문제 심층 확인 |

### 🛡️ Team family (fleet=on, parallel)

| Tier | 질문 수 | Fleet 상한/phase | 총 Fleet | Budget | 용도 |
|---|---|---|---|---|---|
| /wrxp:cast (default) | 0 (conditional) | 1-5 | 3-15 | Standard | 다면 분석 기본 |
| /wrxp:castq | 0-4 | 5 | 15 | Standard | 빠른 multi-perspective |
| /wrxp:castqq | 5-8 | 8 | 24 | Expanded | 중간 복잡도 multi-facet |
| /wrxp:castqqq | 9-12 (max 20) | 12 (max 20) | 36-60 | **Unlimited** | Critical, multi-branch |

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
- **Decision-Gated Questions**: 증거로 확인할 수 있는 사실은 먼저 조사하고, `must_ask` 결정과 독자·용도·공유·권한을 바꾸는 `decision_quality` 선택을 우선순위대로 질문
- **Dynamic Fleet Dispatching**: Runtime에 available subagent 목록을 enumerate → filter(task_type, phase) → diversify(중복 제거) → rank(fit score) → dispatch(top N)
- **Task-Type-Aware Verification**: 9 types마다 전용 verification recipe. Research는 DOI/citation mandatory 검증, Decision은 alternatives audit + bias audit + sensitivity flagging
- **Loop-Back Rules + Circuit Breaker**: 8 rules (LB1-LB8) + global abort threshold. Ambiguity Spiral / Verification Fail / Scope Creep / Data Unavailable / Complexity Underestimate / Reviewer Deadlock / Token Exhaustion / User Timeout
- **Role Prompting Fix**: persona framing 제거, purpose framing만 사용 (KAIST 2025 연구 반영)
- **Confidence Disclosure Auto-Injection**: Phase 6 산출물 말미에 tier, 질문 수, agent 수, 잔여 불확실성을 자동 삽입

## 상세 리서치 리포트

wrxp의 모든 설계 결정은 publicly verifiable 연구에 근거한다. 구체적인 benchmark 수치(Self-Ask +42% Bamboogle, ToT 4%→74% Game of 24, Reflexion 80→91% HumanEval, CoVe 50-70% hallucination 감소, UoT +120% MedDG, EVPI 1.5-2.7x question reduction 등), Before/After 비교, 20개 이상의 arXiv citation, NBER 1.5M ChatGPT taxonomy 매핑, 19개 expert discovery protocol 분석은 별도 문서를 참조.

[**docs/RESEARCH_REPORT.md**](./docs/RESEARCH_REPORT.md) — Universal Reasoning-and-Execution Pipeline의 Evidence Base (10,000+ 단어, 포괄적)

## Composable usage

### 🗡️ Knife family (single-thread, serial execution)

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/wrxp:ha "요청"` | 공통 상태 흐름 + 질문 0~4개 | 균형형 기본 실행 |
| `/wrxp:haq "요청"` | 공통 상태 흐름 + 최대 1라운드 | 빠른 확인 |
| `/wrxp:haqq "요청"` | 공통 상태 흐름 + 최대 2라운드 | 표준 발견 |
| `/wrxp:haqqq "요청"` | 공통 상태 흐름 + 최대 3라운드(동의 시 5) | 고위험 단일 문제 심층 확인 |

### 🛡️ Team family (fleet-dispatching, parallel)

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/wrxp:cast "요청"` | Phase 0-6 full | 다면 분석 기본 (depth=0, 1-5 agents) |
| `/wrxp:castq "요청"` | Phase 0-6 full | 0-4 질문, 최대 5-agent fleet |
| `/wrxp:castqq "요청"` | Phase 0-6 full | 5-8 질문, 최대 8-agent fleet, expanded |
| `/wrxp:castqqq "요청"` | Phase 0-6 full | 9-20 질문, 12-20 agent fleet, unlimited |

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
| 다면 검증·병렬 관점 필요 | `/wrxp:cast` 계열 (team) |
| 여러 feature 묶어 자율 실행 | `/wrxp:breakdown` |
| 분해 트리만 보고 싶을 때 | `/wrxp:decompose` |

knife/team 계열과 breakdown 계열은 직교한다. knife/team은 quality tier (추론 깊이)를, breakdown은 execution scope (분해 깊이)를 제어한다. 필요하면 breakdown의 각 task를 /wrxp:haqqq 또는 /wrxp:castqqq로 escalate할 수도 있다.

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
