---
name: haq
description: Knife 빠른 실행 - 0~4개 선택형 질문(불확실성 기반) 후 /ha 파이프라인 실행 (thin shim, single-agent)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haq — Quick Knife Tier (Thin Shim over /ha)

이 skill은 knife-mode canonical engine인 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. 자체적으로 Phase 0 감지, Pre-Q reasoning, execution delegation, verification을 수행하지 않는다 — 모두 /ha가 관리한다.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haq가 하는 일은 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 상한, 라운드 수, 예산)
2. /haq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다 (Phase 2에서 사용)

Knife invariant는 /ha에서 관리되며 이 shim은 그것을 그대로 상속한다. `fleet_mode: off`, Phase 4 skip, Phase 0 cheap-signal-only 가 모두 자동 적용된다.

---

## Tier Policy (Knife, Single-Agent)

- **Knife invariant**: Single-agent 유지. Fleet dispatching 없음 (모든 tier 공통).
- **Question budget**: 0-4개 (최대 4), 1 round 내 처리.
- **동작 원칙**: /ha의 "Single-Agent Policy" 섹션 참조.
- **복잡도 스케일링**: trivial task이면 질문 0개(Phase 2 skip)가 정상. complex single-problem에 대해 3-4개를 선별적으로.
- **질문 전달 포맷**: AskUserQuestion 웹UI의 multi-choice 선택형 (brainstorming-style). 3-4지선다 + 직접 입력 옵션.

---

## Config Block (passed to /ha)

```
depth_budget: 0-4
question_rounds: 1
max_budget: 4
tier: haq
fleet_mode: off
```

이 config는 /ha Phase 2에 의해 해석된다. /ha Phase 1이 uncertainty를 LOW로 판정하면 depth_budget이 4여도 Phase 2는 자동으로 skip된다 (Stop Overthinking 원칙).

---

## Task-Type Question Categories (haq tier — 핵심 2개)

/haq는 task type별로 가장 핵심적인 2개 카테고리에서만 질문한다. /ha Phase 2가 EVPI 순서로 이 풀에서 질문을 선택할 때 사용하는 후보 pool이다.

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

knife mode는 단일-갈래 문제가 전제이므로, 이 2개 축이 결정되면 대개 실행 경로가 하나로 수렴한다.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — /ha Phase 2-0 Skip Condition이 자동 적용된다. /haq를 호출했더라도 LOW uncertainty면 Phase 2를 건너뛴다.
- 🎯 **EVPI 기반 질문 순서** — /ha Phase 2-2가 "실행 계획을 가장 크게 바꿀 질문"을 우선한다.
- 🖱️ **선택형 UI 고정** — Knife 모드의 질문은 prose가 아니라 AskUserQuestion 웹UI의 3-4지선다 + 직접 입력으로 묻는다 (brainstorming-style).
- ⏱️ **Fatigue 감지 시 조기 종료** — /ha Phase 2-5에 의해 자동 종료.
- 🚪 **Self-Ask gate** — /ha Phase 1 끝의 "Are follow-up questions needed here? Yes/No" gate가 No면 Phase 2 진입이 일어나지 않는다.

---

## When `/haq` vs `/castq`

- `/haq`: 문제가 단일 갈래로 풀리는데 **1-2개 축만 확인하면** 바로 실행 가능할 때.
- `/castq`: 같은 깊이의 질문이 필요하지만 **여러 관점 병렬 검증**이 가치를 더할 때 (예: code + security + UX 동시 리뷰 필요).

knife는 "정확히 한 화살", team은 "여러 화살 동시 발사" — 문제 성격이 어느 쪽인지로 선택한다.

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
    fleet_mode: off

    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: 이 skill은 직접 reasoning / execution / verification을 수행하지 않는다. /ha가 모든 phase를 관리한다.

---

## Output Format

이 skill의 output은 /ha의 output이다. /haq 자체는 짧은 헤더만 출력한다:

```
🎚️ Tier: haq (knife, depth_budget=0-4, max=4, rounds=1)
📚 Category guidance: 핵심 2개 카테고리
🗡️ Single-agent 모드 (fleet=off)
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
