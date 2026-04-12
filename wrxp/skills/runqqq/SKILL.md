---
name: runqqq
description: 심층 실행 - 9~12개 질문 (최대 20개, 불확실성 기반) 후 /run 파이프라인 실행 (thin shim)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haqqq — Deep Tier (Thin Shim over /ha)

This skill produces high-quality outputs by passing a deep-tier configuration to the canonical /ha pipeline. It is a **thin shim**: it does NOT re-implement Phase 0 detection, Pre-Q reasoning, design templates, delegation, or verification. All of those are managed by /ha.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haqqq는 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. 이 파일이 하는 일은 단 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 9-12, 최대 20, 라운드 3-5, 예산 20)
2. /haqqq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다 (Phase 2에서 사용)

Phase 0~6의 모든 로직은 /ha가 관리한다. 이 파일에서는 Phase 0 감지, Pre-Q reasoning, design template, Haiku delegation, verification recipe 어느 것도 다시 정의하지 않는다. 중복 정의는 drift와 일관성 위험의 가장 큰 원인이므로 의도적으로 회피한다.

---

## Tier Policy (Fleet Dispatching)

- **Quality tier**: 최상급 (top) — **무제한 버짓**
- **Per-phase 함대 상한**: 12 agents (critical task 시 최대 20)
- **3-phase 총합 상한**: 36-60 agents
- **Budget policy**: **Unlimited** — 공격적 병렬화 허용, resource 제약 없음
- **동작 원칙**: /ha의 "Fleet Dispatching — Quality Tier Policy" 섹션 참조 (Phase 1/5/6 전 구간에서 parallel specialized subagents dispatch)
- **복잡도 스케일링**: Complex/critical task에는 8-12 (또는 15-20)개 agents dispatch. Moderate task는 8-12개 표준. Trivial task라도 최소 3-5개 agents는 투입 (최상급 tier 보장).
- **Runtime detection**: 하드코딩 금지. /ha Fleet Dispatching 정책의 enumerate → filter → diversify → rank 파이프라인을 매 phase 진입 시 실행. /haqqq는 available 전문가 pool을 최대한 활용하므로 mapping 표에 없는 새 agent도 적극 편입.
- **Budget warning**: 총 parallel agent 수가 20을 초과하면 사용자에게 경고 후 진행. 무제한 예산이어도 confirmation 한 번은 거친다.
- **Tie-breaker**: /haqqq 전용 규칙 — agent 결과가 충돌하면 추가 critic agent 1개를 소환하여 adjudicate (일반 tier는 Opus 직접 결정).
- **Benchmark**: 9개 병렬 deep research agents dispatch가 이 tier의 표준 사례. 유저가 명시적으로 "최상급 수준"의 기준으로 이 숫자를 지정했다.

---

## Config Block (passed to /ha)

```
depth_budget: 9-12-up-to-20
question_rounds: 3-5
max_budget: 20
tier: haqqq
fleet_mode: on
fleet_tier: top
fleet_upper_bound: 12
fleet_max_critical: 20
budget: unlimited
```

이 config는 /ha의 Phase 2가 해석한다. 9-12개가 권장 범위이고, 매우 복잡하거나 리스크/비용/되돌림 불가 요소가 많을 때만 최대 20개까지 허용된다. Cowan working memory 4-chunk 한계 때문에 라운드당 4개씩, 기본 3 라운드 (필요 시 5 라운드)로 분할된다. /ha Phase 1이 uncertainty를 LOW로 판정하면 depth_budget이 20이어도 Phase 2는 skip된다 — 이것이 Stop Overthinking 원칙의 작동이다.

---

## Task-Type Question Categories (haqqq tier — 9~12개)

/haqqq는 task type별로 9-12개 카테고리에서 후보를 선정한다. /ha의 Phase 2가 EVPI 순서로 이 풀에서 plan-changing 항목들을 우선 선택한다.

| Task | 카테고리 (9-12개) |
|---|---|
| code | 핵심 기능(2-3) / 데이터·구조(2) / 에러 처리(1-2) / 성능·확장성(1-2) / 통합·의존성(1-2) / 보안·검증(1) / 운영·모니터링(1) |
| writing | 독자·톤(1-2) / 분량·형식(1) / 핵심 메시지(2) / 사실·자료(1-2) / 구성·흐름(1-2) / 인용·출처(1) / 편집 라운드(1) / 게시 계획(1) |
| planning | 목표·성공 기준(2) / 제약(2) / 우선순위(1) / 리스크(1-2) / 이해관계자(1-2) / 컨틴전시(1) / 의사소통(1) / 측정 지표(1) / 회고 계획(1) |
| research | 질문 구체화(2) / 기존 지식(1-2) / 자료 출처(1-2) / 분석 방법(1-2) / 편향 통제(1) / 결론 형식(1) / 재현 가능성(1) / 후속 연구(1) |
| analysis | 분석 질문(2) / 데이터 출처(1-2) / 데이터 품질·전처리(1) / 분석 방법(1-2) / 가정(1) / 엣지 케이스(1) / 해석(1) / 감도 분석(1) / 표현·시각화(1) / 재현성·동료 검토(1) |
| decision | 대안들(2) / 평가 기준(1-2) / 가중치(1) / 시간 압박(1) / 되돌릴 수 있는가(1) / 감도 분석(1) / 2차 효과(1) / 의사소통(1-2) |
| creative | 주제·정서(1-2) / 시점·화자(1) / 스타일·레퍼런스(2) / 길이·포맷(1) / 제약·권리(1-2) / 오디언스(1-2) / 반복 계획(1) |
| learning | 현재 수준(1-2) / 목표 수준(1) / 가용 시간(1) / 선호 학습 방식(1) / 평가 방법(1) / 동기·리마인더(1) / 실패 복구(1) / 진척 추적(1-2) |
| other | 유저와 직접 9-12개 협의 |

**`analysis` row 추가** (NBER 1.5M ChatGPT 분석 + R9 hallucination 위험 고려): 심층 tier에서는 분석 질문, 데이터 출처, 데이터 품질, 방법, 가정, 엣지 케이스, 해석, 감도 분석, 시각화, 재현성/동료 검토까지 — analysis task의 전체 라이프사이클을 다룬다. 특히 sensitivity와 reproducibility는 high-stakes 분석에서 결과 신뢰도를 좌우한다.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — /ha Phase 2-0 Skip Condition이 자동 적용된다. /haqqq를 호출했더라도 LOW uncertainty면 Phase 2 자체가 건너뛰어진다. 이것은 Stop Overthinking (arXiv:2503.16419) 원칙의 정상 동작이다.
- 🎯 **EVPI 기반 질문 순서** — /ha Phase 2-2가 plan-change impact 큰 질문을 우선한다. 1.5-2.7배 질문 수 절감 효과 (arXiv:2511.08798). 9-12개 풀에서 실제 묻는 질문은 그보다 적을 수 있다.
- ⏱️ **Fatigue 감지 시 조기 종료** — User Drop-off Cliff: 21-40Q 구간에서 70.5%까지 떨어진다. 깊은 질문이 항상 좋은 게 아니다. /ha Phase 2-5의 fatigue 신호가 라운드를 자동 단축한다.
- 🔁 **라운드 간 ledger 재평가** — 각 라운드 종료 후 AmbiguityLedger를 재평가하여, 잔여 모호성이 LOW로 떨어지면 다음 라운드가 자동 생략된다.
- 🚦 **Aleatoric 항목 처리** — 같은 모호성이 2 라운드 이상 살아남으면 /ha Phase 3-2-4가 aleatoric로 분류하고 default를 명시한다. 무한히 묻지 않는다.

---

## Skill Invocation

/haqqq는 /ha를 호출할 때 config block을 args 앞부분에 prepend한다.

```
Skill tool parameters:
- skill: "ha"
- args: |
    depth_budget: 9-12-up-to-20
    question_rounds: 3-5
    max_budget: 20
    tier: haqqq
    
    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: 이 skill 자체에서 Phase 0 감지, design 작성, Haiku 호출, verification 어느 것도 직접 수행하지 않는다. /ha가 7-phase 파이프라인 (Phase 0-6) + 8 Loop-Back Rules + Circuit Breaker 전체를 관리한다.

---

## Output Format

이 skill의 output은 /ha의 output이다. /haqqq 자체는 다음 짧은 헤더만 출력한다:

```
🎚️ Tier: haqqq (depth_budget=9-12-up-to-20, max=20, rounds=3-5)
📚 Category guidance: 9-12개 카테고리 풀 (분석 라이프사이클 전체)
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
