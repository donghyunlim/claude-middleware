---
name: haq
description: 빠른 실행 - 0~4개 질문 (불확실성 기반) 후 /ha 파이프라인 실행 (thin shim)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haq — Quick Tier (Thin Shim over /ha)

This skill produces high-quality outputs by passing a quick-tier configuration to the canonical /ha pipeline. It is a **thin shim**: it does NOT re-implement Phase 0 detection, Pre-Q reasoning, design templates, delegation, or verification. All of those are managed by /ha.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haq는 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. 이 파일이 하는 일은 단 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 상한, 라운드 수, 예산)
2. /haq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다 (Phase 2에서 사용)

Phase 0~6의 모든 로직은 /ha가 관리한다. 이 파일에서는 Phase 0 감지, Pre-Q reasoning, design template, Haiku delegation, verification recipe 어느 것도 다시 정의하지 않는다.

---

## Tier Policy (Fleet Dispatching)

- **Quality tier**: 중상급 (mid-upper)
- **Per-phase 함대 상한**: 5 agents
- **3-phase 총합 상한**: 15 agents
- **Budget policy**: Standard
- **동작 원칙**: /ha의 "Fleet Dispatching — Quality Tier Policy" 섹션 참조 (Phase 1/5/6 전 구간에서 parallel specialized subagents dispatch)
- **복잡도 스케일링**: Task complexity × tier 상한으로 실제 함대 수 결정. Trivial task이면 tier=중상급이어도 1-2개만 dispatch. Critical task이면 5개 상한을 모두 사용.
- **Runtime detection**: Agent 리스트는 하드코딩되지 않는다. /ha Fleet Dispatching 정책의 dynamic detection pseudocode에 따라 매 실행마다 현재 available subagent들을 enumerate → filter → diversify → rank 순으로 선별한다.

---

## Config Block (passed to /ha)

```
depth_budget: 0-4
question_rounds: 1
max_budget: 4
tier: haq
fleet_mode: on
fleet_tier: mid-upper
fleet_upper_bound: 5
```

이 config는 /ha의 Phase 2 (Uncertainty-Driven Questioning)에 의해 해석된다. /ha의 Phase 1 Pre-Q Deep Reasoning이 uncertainty를 LOW로 판정하면, depth_budget이 4여도 Phase 2는 자동으로 skip된다 (Stop Overthinking 원칙).

---

## Task-Type Question Categories (haq tier — 핵심 2개)

/haq는 task type별로 가장 핵심적인 2개 카테고리에서만 질문한다. 이 표는 /ha의 Phase 2가 EVPI 순서로 질문을 선택할 때 사용하는 후보 풀이다.

| Task | 핵심 2 categories |
|---|---|
| code | 핵심 기능 / 데이터·구조 |
| writing | 독자·톤 / 핵심 메시지 |
| planning | 목표·성공 기준 / 핵심 제약 |
| research | 질문 구체화 / 자료 출처 |
| analysis | 분석 질문 / 데이터 출처 |
| decision | 대안들 / 평가 기준 |
| creative | 주제·정서 / 스타일·레퍼런스 |
| learning | 목표 수준 / 가용 시간 |
| other | 산출물 형태 / 성공 기준 |

**`analysis` row 추가** (NBER 1.5M ChatGPT 분석 근거): "분석 질문"은 무엇을 알아내려는지, "데이터 출처"는 어떤 데이터에서 결론을 도출할 것인지 — 이 둘이 결정되면 analysis task의 80% 이상이 명확해진다.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — /ha Phase 2-0 Skip Condition이 자동으로 적용된다. 사용자가 /haq를 호출했더라도 LOW uncertainty면 Phase 2를 건너뛴다.
- 🎯 **EVPI 기반 질문 순서** — /ha Phase 2-2가 "실행 계획을 가장 크게 바꿀 질문"을 우선한다. 같은 답이 어떤 plausible value에서도 같은 plan을 만들어내면 그 질문은 drop된다.
- ⏱️ **Fatigue 감지 시 조기 종료** — 답변 길이 40% 감소, 모노실래빅 답변, 명시적 stop 신호 ("skip", "충분해") → /ha Phase 2-5에 의해 자동 종료된다.
- 🚪 **Self-Ask gate** — Phase 1 끝의 "Are follow-up questions needed here? Yes/No" gate가 No라면, Phase 2 진입 자체가 일어나지 않는다.

---

## Skill Invocation

/haq는 /ha를 호출할 때 위의 config block을 args 앞부분에 prepend한다.

```
Skill tool parameters:
- skill: "ha"
- args: |
    depth_budget: 0-4
    question_rounds: 1
    max_budget: 4
    tier: haq
    
    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: 이 skill 자체에서 직접 Haiku를 호출하거나 design template을 만들지 않는다. /ha가 모든 phase를 관리한다. /haq는 단지 quick-tier 설정과 카테고리 힌트만 전달한다.

---

## Output Format

이 skill의 output은 사실상 /ha의 output이다 (Phase 0-6 모두 /ha가 출력한다). /haq 자체는 다음 짧은 헤더만 출력한다:

```
🎚️ Tier: haq (depth_budget=0-4, max=4, rounds=1)
📚 Category guidance: 핵심 2개 카테고리 사용
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
