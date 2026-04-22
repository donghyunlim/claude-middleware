---
name: haqq
description: Knife 중간 깊이 실행 - 5~8개 선택형 질문(불확실성 기반) 후 /ha 파이프라인 실행 (thin shim, single-agent)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haqq — Moderate Knife Tier (Thin Shim over /ha)

이 skill은 knife-mode canonical engine인 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. Phase 0~6의 모든 로직은 /ha가 관리한다. 이 파일은 depth configuration과 tier-level 질문 가이드만 제공한다.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haqq가 하는 일은 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 5-8, 라운드 2, 예산 8)
2. /haqq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다

Knife invariant(`fleet_mode: off`, Phase 4 skip, Phase 0 cheap-signal-only)는 /ha에서 관리되며 이 shim은 그대로 상속한다. 중간 깊이 질문이 필요한 단일-문제 task에 적합하다.

---

## Tier Policy (Knife, Single-Agent)

- **Knife invariant**: Single-agent 유지. Fleet dispatching 없음.
- **Question budget**: 5-8개 (최대 8), 2 rounds로 분할 (Cowan working memory 4-chunk 준수).
- **동작 원칙**: /ha의 "Single-Agent Policy" 섹션 참조.
- **복잡도 스케일링**: moderate single-problem에 5-7개 질문이 표준. simple이면 3-5개로 축소, complex knife에 7-8개 상한까지.
- **질문 전달 포맷**: AskUserQuestion 웹UI의 multi-choice 선택형 (brainstorming-style). 각 질문 3-4지선다 + 직접 입력.

---

## Config Block (passed to /ha)

```
depth_budget: 5-8
question_rounds: 2
max_budget: 8
tier: haqq
fleet_mode: off
```

이 config는 /ha Phase 2에 의해 해석된다. 라운드 1 후 ledger 재평가 — 모호성이 해소되면 라운드 2는 자동 생략. /ha Phase 1이 uncertainty를 LOW로 판정하면 depth_budget이 8이어도 Phase 2는 skip된다 (Stop Overthinking 원칙).

---

## Task-Type Question Categories (haqq tier — 5~8개)

/haqq는 task type별로 5-8개 카테고리에서 질문 후보를 선정한다. /ha Phase 2가 EVPI 순서로 이 풀에서 가장 plan-changing 질문들을 선택한다.

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

knife mode는 단일 갈래를 전제로 하지만, "그 갈래 안에서 plan을 의미 있게 바꿀 축"이 5-8개일 수 있다. /cast의 multi-branch 분석과 혼동하지 말 것 — /haqq는 여전히 **하나의** 최종 산출물을 향한다.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — /ha Phase 2-0 Skip Condition이 자동 적용된다.
- 🎯 **EVPI 기반 질문 순서** — Hi severity 위주로 묶고 Low severity는 default assumption으로 처리.
- 🖱️ **선택형 UI 고정** — Knife 모드 질문은 AskUserQuestion 웹UI의 3-4지선다 + 직접 입력 (brainstorming-style). prose 질문 지양.
- ⏱️ **Fatigue 감지 시 조기 종료** — User Drop-off Cliff 6-10Q에서 응답률 73.6%로 저하. 신호 감지 시 라운드 2 자동 생략.
- 🔁 **라운드 간 ledger 재평가** — 라운드 1 종료 후 모호성이 해소되었다면 라운드 2 진행하지 않음.

---

## When `/haqq` vs `/castqq`

- `/haqq`: 단일-문제이지만 **축이 5-8개 있는** knife (예: 중복잡도 분석의 가정·데이터·방법 등을 순차 확정).
- `/castqq`: 같은 깊이에서 **여러 전문 관점 병렬 검증**이 본질인 경우 (예: security + perf + DX fleet review).

knife는 "한 화살의 5-8개 미세 조정", team은 "여러 화살의 병렬 발사" — 산출물이 단일이면 /haqq, 다면이면 /castqq.

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
    fleet_mode: off

    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: 이 skill 자체에서 Phase 0 감지, design 작성, execution, verification 어느 것도 수행하지 않는다. /ha가 파이프라인 전체를 관리한다.

---

## Output Format

이 skill의 output은 /ha의 output이다. /haqq 자체는 짧은 헤더만 출력한다:

```
🎚️ Tier: haqq (knife, depth_budget=5-8, max=8, rounds=2)
📚 Category guidance: 5-8개 카테고리 풀
🗡️ Single-agent 모드 (fleet=off)
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
