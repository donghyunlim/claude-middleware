# wrxp — Universal Reasoning & Execution Pipeline for Claude Code

> Opus는 조율(reason + synthesize), specialized subagents가 실행. 9가지 task type에 대해 불확실성 기반 질문과 Fleet Dispatching으로 publication-grade 산출물을 만드는 7-phase 파이프라인.

[![version](https://img.shields.io/badge/version-0.1.5-blue.svg)](./package.json)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![marketplace](https://img.shields.io/badge/marketplace-donghyunlim-orange.svg)](https://github.com/donghyunlim/claude-middleware)

## 무엇인가 (What is it?)

**wrxp**(Universal Reasoning & Execution Pipeline)는 Claude Code용 범용 reasoning-and-execution 플러그인이다. code뿐만 아니라 writing, planning, research, analysis, decision, creative, learning 등 9가지 task type에 동일한 품질 보증 파이프라인을 적용하여, 사용자의 요청을 높은 수준의 산출물로 변환한다.

wrxp는 7개 skill로 구성된다. `breakdown`, `decompose`, `agent-match`는 기존 orchestration 축이고, `ha`, `haq`, `haqq`, `haqqq`는 2026년 04월에 추가된 Universal Reasoning & Execution 축이다. 후자의 4개 skill은 모두 동일한 canonical engine인 `/wrxp:ha`(Phase 0-6)를 호출하는 thin shim 구조를 취하며, 이는 drift와 중복 구현 위험을 구조적으로 제거한다.

**핵심 철학**: Opus는 조율에만 집중한다. Phase 0(dispatch 감지), Phase 1(Pre-Q Deep Reasoning), Phase 3(Post-Q 통합 추론), Phase 5/6(검증 synthesis)은 Opus가 직접 수행하지만, 실제 실행(code writing, document drafting, data processing)과 phase-specific 검증(code review, fact-check, sensitivity analysis)은 Fleet Dispatching으로 최대 20개의 specialized Haiku subagents에 분산 위임된다. 이렇게 하면 orchestrator의 context window는 보호되고, 전문가 인력은 필요할 때 병렬로 호출된다.

wrxp의 **Uncertainty-Driven Questioning**은 Bayesian Optimal Experimental Design 이론에 기반한다. Phase 1이 $ARGUMENTS만으로 epistemic / aleatoric / pragmatic 3축 ambiguity ledger를 산출하고, Phase 2는 해당 ledger에 따라 EVPI(Expected Value of Perfect Information) 기반으로 질문을 선별한다. Phase 1이 LOW uncertainty로 판정하면 depth_budget이 20이어도 Phase 2는 skip되며, 이는 arXiv:2503.16419 "Stop Overthinking" 연구의 정상 동작이다.

wrxp의 **Fleet Dispatching**은 tier별로 dispatching 상한선을 정하여 공격적 병렬화를 허용하면서도 resource 폭주를 방지한다. /ha는 단일 agent, /haq는 phase당 5 agent, /haqq는 8 agent, /haqqq는 12(critical 시 20) agent를 Phase 1/5/6 각 phase에 dispatch한다. 총 cluster size는 15-60 agents, /haqqq는 unlimited budget이다.

## 왜 쓰는가 (Why use it?)

- **환각 감소 (Hallucination reduction)**: Chain-of-Verification 4-step 프로세스(arXiv:2309.11495) 주입으로 longform generation hallucination 50-70% 감소. Reflexion(arXiv:2303.11366) self-reflection 루프로 HumanEval pass@1 80%→91% (+11%). Research/Decision task에서는 CoVe 적용이 mandatory다.
- **질문 효율 (Question efficiency)**: EVPI-ordered questioning으로 불필요한 질문 1.5-2.7배 감소 (arXiv:2511.08798). Amazon Alexa 데이터상 사용자 top-intent가 이미 77% 정확하므로, default는 "묻지 않음"이며, Phase 1이 HIGH로 판정할 때만 Phase 2가 활성화된다.
- **Task type 커버리지 (Task type coverage)**: NBER WP #34255 (2025년, 1.1M ChatGPT 대화 분석) 분류 체계와 Anthropic Clio 데이터를 매핑하여 9가지 task type 확정. analysis(신규)를 포함한 9 types은 사용자 workload 전 스펙트럼을 cover한다.
- **병렬 전문가 투입 (Fleet Dispatching)**: tier별로 3-60개의 specialized subagent가 Phase 1(uncertainty 감지), Phase 5(execution), Phase 6(검증)에 동시 dispatch된다. 하드코딩된 agent 목록이 아니라 runtime enumerate → filter → diversify → rank 파이프라인을 거친 동적 매칭이다.
- **Loop-Back Safety**: 8가지 loop-back 규칙(Ambiguity Spiral, Verification Fail, Scope Creep, Data Unavailable, Complexity Underestimate, Reviewer Deadlock, Token Exhaustion, User Timeout)과 Global Circuit Breaker가 무한 루프와 scope drift를 자동 차단한다.
- **Expert Discovery 패턴 내재화**: 19개의 전문가 discovery 프로토콜(SPIKES, MI, SPIN, Sandler, Five Whys, JTBD, MECE, Calgary-Cambridge 등)에서 추출한 10개 Universal Principle이 파이프라인 설계 전반에 내재되어 있다. Sandler Upfront Contract는 Phase 2 preamble로, Five Whys는 Phase 1-2 depth probe로, MI Reflective Summarization은 Phase 3 통합으로 이어진다.
- **Role Prompting Fix**: KAIST 2025 연구에 따라 persona 기반 prompting("You are a senior X")이 MMLU 등 factual task에서 성능을 떨어뜨린다. wrxp는 모든 agent prompt에서 persona를 제거하고 purpose-focused framing만 사용한다.
- **Confidence Disclosure 자동 주입**: Phase 6 최종 산출물에 tier, 질문 수, agent 수, 잔여 불확실성이 자동으로 disclosure 섹션으로 삽입되어, 사용자는 산출물의 근거와 한계를 언제든 감사(audit)할 수 있다.

## 어떻게 쓰는가 (How to use it?)

### 설치

```bash
claude plugin add donghyunlim/wrxp
```

### 핵심 skill 네 가지

#### /wrxp:ha — 기본 파이프라인 (default)

```
/wrxp:ha "OAuth2 소셜 로그인을 기존 인증 시스템에 추가"
```

depth_budget=0, 질문 없음. Phase 1이 HIGH uncertainty로 판정하지 않는 한 Phase 2는 skip되고 Phase 3 Design으로 직행한다. 명확한 task 또는 short/trivial task에 적합. 단일 agent dispatch (최소 fleet).

#### /wrxp:haq — 빠른 실행 (중상급)

```
/wrxp:haq "로그인 API 추가"
```

depth_budget=0-4, question_rounds=1. Phase 1 uncertainty에 따라 0-4개 질문(한 라운드 안에 소화 가능한 Cowan 4-chunk 한계). Phase 1/5/6에서 phase당 최대 5 agents dispatch, 총 15 agents, standard budget. Code나 simple-moderate task에 적합.

#### /wrxp:haqq — 중간 깊이 (상급)

```
/wrxp:haqq "인증 시스템 재설계 — JWT에서 session 기반으로 이관"
```

depth_budget=5-8, question_rounds=2. 5-8개 질문을 2 rounds로 분할 (Cowan 한계 준수). Phase 1/5/6에서 phase당 최대 8 agents dispatch, 총 24 agents, expanded budget. Moderate-complex task, security 또는 business-logic이 stake인 경우.

#### /wrxp:haqqq — 심층 실행 (최상급, unlimited)

```
/wrxp:haqqq "레거시 모놀리스를 마이크로서비스로 점진 전환"
```

depth_budget=9-12 (critical 시 최대 20), question_rounds=3-5. 9-20개 질문을 3-5 rounds로 분할. Phase 1/5/6에서 phase당 최대 12 agents (critical task에는 최대 20), 총 36-60 agents, **unlimited budget**. Tie-breaker critic agent도 동원한다. Critical decision, 되돌릴 수 없는 변경, 전략 수립에 적합.

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

## 7단계 파이프라인 (Phase 0-6 at a glance)

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

| Tier | 질문 수 | Fleet 상한/phase | 총 Fleet | Budget | 용도 |
|---|---|---|---|---|---|
| /wrxp:ha (default) | 0 (conditional) | 1-5 | 3-15 | Standard | 명확한 task, short/trivial |
| /wrxp:haq | 0-4 | 5 | 15 | Standard | 빠른 실행, code simple-moderate |
| /wrxp:haqq | 5-8 | 8 | 24 | Expanded | 중간 복잡도, security/biz-logic |
| /wrxp:haqqq | 9-12 (max 20) | 12 (max 20) | 36-60 | **Unlimited** | Critical task, 되돌림 불가 |

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
- **EVPI-Ordered Questions**: arXiv:2511.08798 기반 1.5-2.7x 질문 감소. 질문 카테고리 pool에서 plan-changing impact가 큰 순서대로 선별
- **Dynamic Fleet Dispatching**: Runtime에 available subagent 목록을 enumerate → filter(task_type, phase) → diversify(중복 제거) → rank(fit score) → dispatch(top N)
- **Task-Type-Aware Verification**: 9 types마다 전용 verification recipe. Research는 DOI/citation mandatory 검증, Decision은 alternatives audit + bias audit + sensitivity flagging
- **Loop-Back Rules + Circuit Breaker**: 8 rules (LB1-LB8) + global abort threshold. Ambiguity Spiral / Verification Fail / Scope Creep / Data Unavailable / Complexity Underestimate / Reviewer Deadlock / Token Exhaustion / User Timeout
- **Role Prompting Fix**: persona framing 제거, purpose framing만 사용 (KAIST 2025 연구 반영)
- **Confidence Disclosure Auto-Injection**: Phase 6 산출물 말미에 tier, 질문 수, agent 수, 잔여 불확실성을 자동 삽입

## 상세 리서치 리포트

wrxp의 모든 설계 결정은 publicly verifiable 연구에 근거한다. 구체적인 benchmark 수치(Self-Ask +42% Bamboogle, ToT 4%→74% Game of 24, Reflexion 80→91% HumanEval, CoVe 50-70% hallucination 감소, UoT +120% MedDG, EVPI 1.5-2.7x question reduction 등), Before/After 비교, 20개 이상의 arXiv citation, NBER 1.5M ChatGPT taxonomy 매핑, 19개 expert discovery protocol 분석은 별도 문서를 참조.

[**docs/RESEARCH_REPORT.md**](./docs/RESEARCH_REPORT.md) — Universal Reasoning-and-Execution Pipeline의 Evidence Base (10,000+ 단어, 포괄적)

## Composable usage

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/wrxp:ha "요청"` | Phase 0-6 전체 | Universal reasoning 기본 (depth=0, 단일 agent) |
| `/wrxp:haq "요청"` | Phase 0-6 전체 | 0-4 질문, 5-agent fleet |
| `/wrxp:haqq "요청"` | Phase 0-6 전체 | 5-8 질문, 8-agent fleet, expanded |
| `/wrxp:haqqq "요청"` | Phase 0-6 전체 | 9-20 질문, 12-20 agent fleet, unlimited |
| `/wrxp:breakdown "요청"` | Phase 1-7 orchestration | 재귀 분해 + DAG 병렬 실행 |
| `/wrxp:decompose "문제"` | breakdown Phase 1+2만 | 분해 트리까지만 |
| `/wrxp:agent-match "태스크"` | breakdown Phase 4만 | Agent matching + DAG만 |

ha 계열과 breakdown 계열은 직교한다. ha 계열은 quality tier (추론 깊이)를, breakdown 계열은 execution scope (분해 깊이)를 제어한다. 필요하면 `/wrxp:breakdown`의 각 phase 안에서 individual task를 `/wrxp:haqqq`로 escalate할 수도 있다.

## State 파일 구조

```
.wrxp/state/
├── intent-{slug}.md           # Phase 1: 정제된 의도 (breakdown)
├── tree-{slug}.json           # Phase 2: 분해 트리 (breakdown)
├── plan-{slug}.md             # Phase 3: Implementation Plan (breakdown)
├── dag-{slug}.json            # Phase 4: Agent-matched DAG (breakdown)
├── strategy-{slug}.json       # Phase 5: 선택된 실행 전략 (breakdown)
├── execution-{slug}.json      # Phase 6: 실행 진행 상태 (breakdown)
├── breakdown-{slug}.json      # 전체 파이프라인 상태
├── ha-ambiguity-{slug}.json   # /ha Phase 1: ambiguity ledger
├── ha-design-{slug}.md        # /ha Phase 3: design template
└── ha-fleet-{slug}.json       # /ha Phase 4-6: fleet dispatch 기록
```

`{slug}` = 요청 기반 짧은 식별자 (예: `add-social-login`, `redesign-auth`).

## License

MIT — see `LICENSE`.
