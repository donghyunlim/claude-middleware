---
name: haqqq
description: Knife 심층 실행 - 9~12개 질문 (최대 20, 불확실성 기반) 후 /ha 파이프라인 실행 (thin shim, single-agent deep probe)
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /haqqq — Deep Knife Tier (Thin Shim over /ha)

이 skill은 knife-mode canonical engine인 /ha 위에 얹힌 **thin shim** (얇은 래퍼)이다. Phase 0~6의 모든 로직은 /ha가 관리한다. 이 파일은 depth configuration과 tier-level 질문 가이드만 제공한다.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Role of This File

/haqqq가 하는 일은 두 가지다:

1. /ha에 전달할 **depth configuration**을 명시한다 (질문 수 9-12, 최대 20, 라운드 3-5, 예산 20)
2. /haqqq tier에 적합한 **task-type별 질문 카테고리 가이드**를 제공한다

Knife invariant(`fleet_mode: off`, Phase 4 skip, Phase 0 cheap-signal-only)는 /ha에서 관리되며 이 shim은 그대로 상속한다. /haqqq는 **한 문제를 깊게 파고드는** knife의 극한 형태다.

---

## Tier Identity (vs /castqqq — IMPORTANT)

/haqqq와 /castqqq는 **같은 깊이, 다른 축**이다. 오해하지 말 것:

| 축 | /castqqq (team, depth) | /haqqq (knife, depth) |
|---|---|---|
| 비유 | **다면 탐사선 12-20대 병렬** | **한 탐침을 20m 깊이로** |
| Fleet | ON (Phase 1/5/6 병렬 12-20 agents) | **OFF** (single-agent) |
| 질문 풀 | 광범위 라이프사이클 전체 (9-12 카테고리) | 단일 문제의 9-12개 미세 축 |
| 산출물 | 다면 분석 보고 | **하나의** 깊게 검증된 결정/설계/산출물 |
| 용도 | 광폭 탐색·다면 검증·cross-validation | 한 문제의 끝까지 · 가정·감도·엣지까지 소진 |
| Tie-breaker | critic agent 소환 | 자가 감도 분석 (agent 추가 불가) |

**/haqqq를 고르는 전형**: "단일 의사결정인데, 이 결정이 되돌림 불가능하고 stakes가 매우 높다" — 10-20개 축에서 **한 문제**를 탈탈 털어본다. 여러 대안 비교는 /castqqq 영역이다.

---

## Tier Policy (Knife, Single-Agent, Deep)

- **Knife invariant**: Single-agent 유지. Fleet dispatching 없음 — tier가 최상급이어도 불변.
- **Question budget**: 9-12개 (critical 시 최대 20), 3-5 rounds로 분할.
- **동작 원칙**: /ha의 "Single-Agent Policy" 섹션 참조.
- **Budget warning**: 총 질문 수가 12를 초과하려 하면 사용자에게 경고 후 진행. 최대 20은 truly critical · irreversible task 에 한해.
- **Aleatoric 처리**: 같은 모호성이 2 라운드 이상 살아남으면 /ha Phase 3가 aleatoric로 분류하고 default를 명시. 무한히 묻지 않는다.
- **질문 전달 포맷**: AskUserQuestion 웹UI의 multi-choice 선택형 (brainstorming-style). 각 질문 3-4지선다 + 직접 입력.

---

## Config Block (passed to /ha)

```
depth_budget: 9-12-up-to-20
question_rounds: 3-5
max_budget: 20
tier: haqqq
fleet_mode: off
budget: deep-single-thread
```

이 config는 /ha Phase 2에 의해 해석된다. Cowan 4-chunk 한계로 라운드당 4개씩 분할, 기본 3 라운드 (필요 시 5). /ha Phase 1이 uncertainty를 LOW로 판정하면 depth_budget이 20이어도 Phase 2는 skip된다.

---

## Task-Type Question Categories (haqqq tier — 9~12개)

/haqqq는 task type별로 9-12개 카테고리에서 후보를 선정한다. /cast와 달리 여기서는 **한 문제의 단일 산출물**에 대해 9-12개 축을 끝까지 확정한다.

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

**단일 문제 · 깊은 탐구**가 원칙. `decision` task에서 "대안들(2)"은 **선택해야 할 한 결정**의 후보 옵션을 의미하지, 병렬로 실행할 다중 플랜이 아니다. 다중 플랜 병렬은 /castqqq.

---

## Uncertainty-Driven Principle Reminder

- 📭 **불확실성이 이미 0이면 질문 0개도 정상** — 최상급 tier여도 LOW면 skip.
- 🎯 **EVPI 기반 질문 순서** — 9-12개 풀에서 plan-change impact가 큰 축부터 문다.
- 🖱️ **선택형 UI 고정** — AskUserQuestion 웹UI의 3-4지선다 + 직접 입력 (brainstorming-style). 20개라도 매 질문 선택형 유지.
- ⏱️ **Fatigue 감지 시 조기 종료** — User Drop-off Cliff: 21-40Q 구간에서 70.5%까지 저하. 신호 감지 시 라운드 자동 단축.
- 🔁 **라운드 간 ledger 재평가** — 각 라운드 종료 후 AmbiguityLedger 재평가. LOW 도달 시 다음 라운드 자동 생략.
- 🚦 **Aleatoric 항목 처리** — 2 라운드 생존 시 default 명시, 무한 질문 방지.
- 🚪 **Escalation self-check** — 10+ 질문이 정말 "한 문제 깊이"인지, 혹시 multi-branch는 아닌지 매 라운드 점검. multi-branch로 판정되면 사용자에게 /castqqq 전환 제안.

---

## When `/haqqq` is the Right Choice

- **Irreversible single decision** with high stakes (returning not an option).
- **Single deliverable** that must be bulletproof across 10+ dimensions (audit-ready analysis, production-critical module, high-stakes proposal).
- **Deep probe** — 한 가설이나 한 설계를 가정·데이터·edge case까지 모두 벗겨본다.

반대로 여러 대안 중 고르는 결정, 다면 lifecycle 검증, parallel expert review가 본질이면 /castqqq.

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
    fleet_mode: off

    [원본 $ARGUMENTS 내용을 그대로 이어서]
```

> **중요**: Fleet 없이 깊이로 승부한다. /ha가 Phase 0-6 (Phase 4 skip 포함) 전체 + Loop-Back Rules + Circuit Breaker를 관리한다.

---

## Output Format

이 skill의 output은 /ha의 output이다. /haqqq 자체는 짧은 헤더만 출력한다:

```
🎚️ Tier: haqqq (knife-deep, depth_budget=9-12-up-to-20, max=20, rounds=3-5)
📚 Category guidance: 9-12개 카테고리 풀 (단일-문제 깊은 축)
🗡️ Single-agent 모드 (fleet=off, 깊이로 승부)
🚀 /ha 호출 중...

[/ha의 Phase 0-6 출력이 이어짐]
```
