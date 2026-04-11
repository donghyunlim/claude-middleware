---
name: haqq
description: 중간 깊이 실행 - 5~8개 질문 (불확실성 기반) 후 /ha 파이프라인 실행 (thin shim)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haqq — Moderate Tier (Thin Shim over /ha)

This skill produces high-quality outputs by passing a moderate-tier configuration to the canonical /ha pipeline. It is a **thin shim**: it does NOT re-implement Phase 0 detection, Pre-Q reasoning, design templates, delegation, or verification. All of those are managed by /ha.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haqq는 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. 이 파일이 하는 일은 단 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 5-8, 라운드 2, 예산 8)
2. /haqq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다 (Phase 2에서 사용)

Phase 0~6의 모든 로직은 /ha가 관리한다. 이 파일에서는 Phase 0 감지, Pre-Q reasoning, design template, Haiku delegation, verification recipe 어느 것도 다시 정의하지 않는다. 중복은 drift와 일관성 깨짐의 주요 원인이므로 의도적으로 회피한다.

---

## Tier Policy (Fleet Dispatching)

- **Quality tier**: 상급 (upper)
- **Per-phase 함대 상한**: 8 agents
- **3-phase 총합 상한**: 24 agents
- **Budget policy**: Expanded (일반 tier보다 resource 적극 투입)
- **동작 원칙**: /ha의 "Fleet Dispatching — Quality Tier Policy" 섹션 참조 (Phase 1/5/6 전 구간에서 parallel specialized subagents dispatch)
- **복잡도 스케일링**: Moderate 복잡도 task에 5-7개 agents 정도가 표준. Simple task는 3-5개로 축소, Complex/critical은 7-8개 상한까지 사용. Trivial task이면 /haq 수준 (2-3개)으로 downgrade.
- **Runtime detection**: /ha Fleet Dispatching 정책의 dynamic detection을 따른다. 하드코딩된 agent 리스트 없음. 매 실행마다 현재 Claude Code 환경의 subagent catalogue에서 task-type과 phase에 맞는 전문가를 enumerate → filter → diversify → rank.
- **중복 배제**: 8개 상한이 커 보여도 같은 역할(예: code-reviewer 2개)은 금지. 서로 다른 전문성(reviewer + test-engineer + security-reviewer + verifier ...)으로 다양화해야 tier 효과 발생.

---

## Config Block (passed to /ha)

```
depth_budget: 5-8
question_rounds: 2
max_budget: 8
tier: haqq
fleet_mode: on
fleet_tier: upper
fleet_upper_bound: 8
```

이 config는 /ha의 Phase 2가 해석한다. Cowan working memory 4-chunk 한계를 넘지 않도록 라운드당 최대 4개 질문, 최대 2 라운드로 제한된다. /ha Phase 1이 uncertainty를 LOW로 판정하면 depth_budget이 8이어도 Phase 2는 skip된다 (Stop Overthinking 원칙).

---

## Task-Type Question Categories (haqq tier — 5~8개)

/haqq는 task type별로 5-8개 카테고리에서 질문 후보를 선정한다. /ha의 Phase 2가 EVPI 순서로 이 풀에서 가장 plan-changing 질문들을 선택한다.

| Task | 카테고리 (5-8개) |
|---|---|
| code | 핵심 기능(1-2) / 데이터·구조(1-2) / 에러 처리(1) / 성능·제약(1) / 통합·의존성(1-2) |
| writing | 독자·톤(1) / 분량·형식(1) / 핵심 메시지(1-2) / 사실·자료(1) / 구성·흐름(1-2) |
| planning | 목표·성공 기준(1) / 제약(1-2) / 우선순위(1) / 리스크(1) / 이해관계자(1-2) |
| research | 질문 구체화(1-2) / 기존 지식(1) / 자료 출처(1) / 분석 방법(1) / 결론 형식(1-2) |
| analysis | 분석 질문(1-2) / 데이터 출처(1) / 분석 방법(1) / 가정(1) / 해석·결론 형식(1-2) |
| decision | 대안들(1-2) / 평가 기준(1-2) / 가중치(1) / 시간 압박(1) / 되돌릴 수 있는가(1) |
| creative | 주제·정서(1) / 시점·화자(1) / 스타일·레퍼런스(1-2) / 길이·포맷(1) / 제약(1-2) |
| learning | 현재 수준(1) / 목표 수준(1) / 가용 시간(1) / 선호 학습 방식(1) / 평가 방법(1-2) |
| other | 유저와 직접 5-8개 협의 |

**`analysis` row 추가** (NBER 1.5M ChatGPT 분석 근거): 분석 질문이 무엇인지, 어떤 데이터에서 시작하는지, 어떤 방법(통계적/기술적/시각적)을 쓰는지, 핵심 가정은 무엇인지, 결과를 어떤 형태로 해석할지 — 이 5개 축이 분석 task의 모호성 해소에 핵심이다.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — /ha Phase 2-0 Skip Condition이 자동 적용된다. /haqq를 호출했더라도 사용자 요청이 명확하면 질문 단계 자체가 건너뛰어진다.
- 🎯 **EVPI 기반 질문 순서** — /ha Phase 2-2가 plan-change impact가 큰 질문부터 묻는다. Hi severity 위주로 묶고 Low severity는 default assumption으로 처리.
- ⏱️ **Fatigue 감지 시 조기 종료** — User Drop-off Cliff 데이터: 6-10Q에서 응답률이 73.6%로 떨어진다. 신호 감지 시 라운드 2가 자동 생략될 수 있다.
- 🔁 **라운드 간 ledger 재평가** — 라운드 1 종료 후 모호성이 해소되었다면 라운드 2는 진행되지 않는다.

---

## Skill Invocation

/haqq는 /ha를 호출할 때 config block을 args 앞부분에 prepend한다.

```
Skill tool parameters:
- skill: "ha"
- args: |
    depth_budget: 5-8
    question_rounds: 2
    max_budget: 8
    tier: haqq
    
    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: 이 skill 자체에서 Phase 0 감지, design 작성, Haiku 호출, verification 어느 것도 직접 수행하지 않는다. /ha가 7-phase 파이프라인 전체를 관리한다.

---

## Output Format

이 skill의 output은 /ha의 output이다. /haqq 자체는 다음 짧은 헤더만 출력한다:

```
🎚️ Tier: haqq (depth_budget=5-8, max=8, rounds=2)
📚 Category guidance: 5-8개 카테고리 풀
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
