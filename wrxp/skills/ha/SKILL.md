---
name: ha
description: Knife-mode reasoning-and-execution pipeline — single-agent, single-thread, no fleet. Canonical engine for /haq, /haqq, /haqqq shims. Use when the problem is one clear branch of thought.
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /ha — Knife-Mode Reasoning & Execution Engine

이 skill은 **"하나의 명확한 문제"**를 단일 사고의 갈래(single reasoning thread)로 끝까지 밀어붙이는 knife-mode engine이다. Fleet dispatching 없이 단일 agent로 Phase 1 → 2(조건부) → 3 → 5 → 6을 순차 수행한다. Phase 0(task-type cascade)과 Phase 4(design template)는 knife mode에서 생략되거나 경량화된다.

/ha 는 **/cast의 knife 대칭 canonical engine**이다. 둘 다 `shared/reasoning-framework.md`의 9원칙을 공유하지만:

- **/cast (team)**: Fleet ON — Phase 1/5/6 전 구간에서 병렬 specialized subagents dispatch. 다면 분석, 교차 검증, 여러 관점이 가치를 더하는 task.
- **/ha (knife)**: Fleet OFF — 단일 agent, 단일 사고 흐름. 문제 경로가 한 갈래로 수렴하는 task.

`/haq`, `/haqq`, `/haqqq`는 /ha를 호출하는 thin shim으로, 사용자에게 물을 수 있는 질문 수(AskUserQuestion 웹UI를 통한 brainstorming-style 선택형 질문)만 다르다.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Configuration from Caller

This skill can be invoked in two ways:

1. **Direct invocation (`/ha ...`)**: defaults to `depth_budget: 0`, meaning Phase 2 (Questioning) is **skipped** unless Phase 1 detects HIGH uncertainty. This honors the principle that 77% of requests already have a clear top-intent (Amazon Alexa research) and that simple queries waste 19-42 seconds on unnecessary reasoning (Stop Overthinking, arXiv:2503.16419).

2. **Tier shim invocation (`/haq`, `/haqq`, `/haqqq`)**: a config block is passed in via `$ARGUMENTS`. Parse the following keys at the top of the requirements:

```
depth_budget: <0-4 | 5-8 | 9-12-up-to-20>
question_rounds: <1 | 2 | 3-5>
max_budget: <4 | 8 | 20>
tier: <haq | haqq | haqqq | direct>
fleet_mode: off     # knife family는 항상 off
```

If no config block is present, treat as direct invocation with `fleet_mode: off` (knife default). The depth budget governs Phase 2's AskUserQuestion count ceiling. Phase 1's uncertainty detection still has the final say — uncertainty=LOW always skips Phase 2 regardless of caller tier.

**Knife invariants (하드 제약, tier 무관):**

- `fleet_mode: off` 고정. 어떤 tier 호출이든 Phase 1/5/6은 단일 agent로 실행된다.
- **Phase 4 (Design Template) skip**. Single deliverable이 전제이므로 9-종 task template은 생성하지 않는다. Phase 3 통합 추론이 곧 실행 명세가 된다.
- **Phase 0 cascade 축소**. Stage 1 (cheap signals) + context collection만 실행. Stage 2 (internal classification) / Stage 3 (AskUserQuestion fallback)는 생략 — knife mode는 "task type이 이미 명확"을 전제한다. 애매하면 사용자를 `/cast` 쪽으로 유도한다.
- **Phase 2 질문은 AskUserQuestion 웹UI를 통한 brainstorming-style 선택형(multi-choice) 포맷**을 기본으로 한다. prose 자유서술 질문은 지양.

---

## Phase 0 — Context & Task-Type Detection

This phase establishes the work environment, identifies the task type, gathers task-specific context, and reserves a verification plan. It is mandatory and non-skippable.

### 0-1. Task Type Table (9 types)

| Task Type | 특징 | 산출물 형태 |
|---|---|---|
| `code` | 코드 작성/수정/리팩토링/디버깅 | 파일별 구현 명세 |
| `writing` | 글 작성 (문서/이메일/보고서/에세이) | 섹션별 개요 + 본문 |
| `planning` | 계획/일정/로드맵/이벤트 준비 | 단계별 타임라인 |
| `research` | 조사/문헌 리뷰/요약 | 소스 목록 + 합성 |
| `analysis` | **데이터 분석/패턴 발견/판단/평점/이미지 분석** | 분석 보고서 + 결론 |
| `decision` | 의사결정 지원/트레이드오프 분석 | 기준 + 대안 매트릭스 |
| `creative` | 창작 (디자인/스토리/시/브레인스토밍) | 장면/스탠자/패널 분해 |
| `learning` | 학습 계획/커리큘럼/스터디 설계 | 세션별 커리큘럼 |
| `other` | 위에 해당 없음 | 자유 형식 |

**`analysis` 타입이 신규 추가된 이유** (NBER 1.5M ChatGPT 대화 분석): NBER 분류체계는 `data_analysis`와 `analyze_an_image`를 독립 leaf로 가지며, 기존 code/research/other에 흩어져 있던 "데이터 보고 판단/등급/패턴 발견" 요청을 하나의 명확한 카테고리로 통합한다. 데이터 무결성과 통계적 적절성이 핵심 검증 축이 된다.

### 0-2. Cheap-Signal-Only Detection (Knife Reduction)

Knife mode는 **Stage 1 (cheap signals)만 수행**한다. Stage 2 (Opus internal classification) 와 Stage 3 (AskUserQuestion fallback) 은 **생략**된다 — knife의 전제가 "task type이 이미 명확함"이기 때문이다. Stage 1만으로 결정이 안 나면, 이 요청은 /ha 적합성이 의심되는 것이므로 사용자에게 `/cast`로의 전환을 제안하고 중단한다.

**Stage 1 — Cheap Signals (only stage)**

CWD cues:

| 신호 | Task Type 후보 |
|---|---|
| `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `composer.json`, `Gemfile`, `pubspec.yaml`, `*.csproj` | code |
| `.obsidian/`, 다수의 `.md`, `docs/`, `vault/`, `notes/` | writing 또는 research |
| `*.csv`, `*.parquet`, `*.ipynb`, `*.tsv`, `*.xlsx`, `data/` | **analysis** |
| 일정 파일, ical, calendar | planning |
| `references/`, `bib*`, `papers/` | research |
| 위 어디에도 해당 없음 | 요청 텍스트로 판단 |

요청 키워드:

| 키워드 | Task Type |
|---|---|
| 구현/리팩토링/버그/코드/함수/클래스/API | code |
| 써줘/작성/글/이메일/문서/보고서/에세이 | writing |
| 계획/일정/준비/로드맵/타임라인 | planning |
| 조사/요약/리서치/문헌 | research |
| **분석해줘/패턴/등급/평점/판단해줘/이미지 분석/이 데이터** | **analysis** |
| 비교/선택/결정/어느 것/vs | decision |
| 그려줘/만들어줘/디자인/로고/아이디어/브레인스토밍 | creative |
| 배우고 싶어/공부/학습/강의/커리큘럼 | learning |

**판정 규칙**: Stage 1 confidence ≥ 0.85 → 감지된 task type 확정, 다음 sub-phase로. Confidence < 0.85 → `/cast` 사용 권장 메시지 후 knife 종료.

### 0-3. Task-Type-Specific Context Collection

| Task Type | 수집 대상 |
|---|---|
| code | 프로젝트 루트, stack, 주요 디렉토리, 의존성, linter 설정 (아래 표 참조) |
| writing | 관련 이전 글/초안, 스타일 가이드, 타겟 매체, `docs/`, `**/*.md` |
| planning | 명시 제약 (날짜/예산/인원), 기존 일정/캘린더, 이해관계자 |
| research | 기존 자료, 노트, 참고 문헌, `.obsidian/`, `notes/`, `references/`, `bib*` |
| **analysis** | **데이터 소스 (파일/DB/API), 스키마, 행/열 수, 사용 가능 도구 (pandas/SQL/spreadsheet), 분석 목적, 산출물 형태 (보고서/시각화/요약), 데이터 품질 단서** |
| decision | 대안 후보, 평가 기준, 시간/리스크 제약, 이전 논의 |
| creative | 레퍼런스, 스타일/톤 가이드, 타겟 오디언스, 권리 제약 |
| learning | 현재 수준, 목표 수준, 가용 시간, 선호 방식 |
| other | `AskUserQuestion`으로 직접 질문 |

Code stack 감지표:

| File | Stack | Linter |
|---|---|---|
| pyproject.toml | Python | mypy / ruff |
| package.json | Node/TS | tsc --noEmit / eslint |
| Cargo.toml | Rust | cargo clippy |
| go.mod | Go | go vet / staticcheck |
| pom.xml | Java Maven | - |
| build.gradle | Java Gradle | - |
| composer.json | PHP | - |
| Gemfile | Ruby | rubocop |
| pubspec.yaml | Dart/Flutter | dart analyze |
| *.csproj | C#/.NET | - |

### 0-4. Phase 6 Verification Plan Reservation (preview)

Phase 6에서 사용할 검증 방법을 Phase 0에서 미리 선택한다. 실제 검증 절차의 상세는 Phase 6에 정의되어 있고, 여기서는 어떤 verification recipe를 쓸지만 결정한다.

| Task Type | 검증 recipe (preview) |
|---|---|
| code | 감지된 linter + 테스트 러너 |
| writing | atomic claim extraction + temporal disclosure + fact-flagging |
| planning | Critical Path + cycle detection + arithmetic validation |
| research | 🔴 **CRITICAL** — DOI/citation verification + CRAAP test |
| **analysis** | **데이터 무결성 + 통계 방법 적절성 + 결론-증거 일관성** |
| decision | 🔴 **CRITICAL** — alternatives audit (≥3) + assumption surfacing + bias check |
| creative | constraint compliance + style consistency + rights check |
| learning | source anchoring + temporal disclosure + outdated-practice flag |
| other | 사용자 수용 기준 직접 확인 |

### 0-5. Phase 0 Output Format

```
🔍 Context 감지 중...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 작업 경로: [CWD]
🏷️ Task Type: [9개 중 하나] (감지 단계: Stage [1|2|3], 신뢰도 [0.0-1.0])
📁 관련 Artifact: [task-type-specific context 요약]
🎯 Task 특성: [요약]
✅ Phase 6 검증 계획 (예약): [recipe 이름]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Reasoning Framework (MANDATORY Before Every Action)

> **Canonical source**: `${CLAUDE_PLUGIN_ROOT}/shared/reasoning-framework.md`
> Before ANY action, Read the shared reasoning framework and apply all 9 principles:
> 1. Logical Dependencies and Constraints  2. Risk Assessment  3. Abductive Reasoning and Hypothesis Exploration
> 4. Outcome Evaluation and Adaptability  5. Information Availability  6. Precision and Grounding
> 7. Completeness  8. Persistence and Patience  9. Response Inhibition ← reasoning 완료 전 행동 금지

Read `${CLAUDE_PLUGIN_ROOT}/shared/reasoning-framework.md` and apply all 9 principles defined there before proceeding to any Phase.

---

## Single-Agent Policy (Knife Invariant)

/ha 는 **fleet dispatching을 사용하지 않는다**. 이것이 /cast와의 구조적 차이이며, knife 정체성의 근간이다.

Reasoning Framework(9원칙)가 "어떻게 생각할 것인가"를 정의한다면, 이 섹션은 "몇 개의 agent로 생각·실행·검증할 것인가"를 정의한다 — 답은 **하나**다.

### Why Single-Agent (본질)

하나의 명확한 문제는 하나의 추론 갈래로 풀린다. 병렬 agent를 띄우는 순간 다음 4개 비용이 발생한다:

1. **Synthesis overhead** — 여러 관점 산출물을 통합하는 Opus의 추가 작업
2. **Context bleed** — 각 agent가 서로 다른 state를 가정해 결론이 미묘하게 어긋남
3. **Noise amplification** — 문제가 단일 갈래면 "다른 관점"이 noise로 작용
4. **Latency tax** — 병렬이라도 느린 agent 하나에 전체가 묶임

Knife의 가치는 "한 화살이 정확히 꽂히는 것"이다. Fleet은 다면 탐색이 가치를 더할 때(/cast)만 의미가 있다.

### What "Single-Agent" Means in Each Phase

| Phase | /cast (team) | /ha (knife) |
|---|---|---|
| Phase 1 Pre-Q Reasoning | 복수 탐색/문서 조회 agent 병렬 | Opus 단독. Read/Grep/Glob만으로 IntentDraft + AmbiguityLedger 산출 |
| Phase 2 Questioning | EVPI 카테고리 pool에서 텍스트 질문 | **AskUserQuestion 웹UI + brainstorming-style 선택형 질문**만 (depth_budget에 따라 0~20개) |
| Phase 5 Execution | Fleet 3-20 agents 병렬 실행 | 단일 executor/worker (Haiku 또는 Opus 직접, task 성격에 따라) |
| Phase 6 Verification | 복수 critic/reviewer/verifier 병렬 | 단일 verifier. 필요하면 Opus 자가 검증으로 대체 가능 |

### When `/ha` is Wrong and `/cast` is Right

- 한 문제가 **2개 이상 명확한 하위 축**으로 쪼개진다 (예: "보안 + 성능 + DX 동시에") → /cast
- **다면 검증이 본질적으로 필요**하다 (research 결론의 CRAAP test, decision의 alternatives audit) → /cast
- 문제를 정의하는 것 자체가 **탐색 작업**이다 (unknown unknowns 많음) → /cast
- 사용자 요청이 **vague**하다 (top-intent 불분명) → /cast

반대로, 문제가 한 갈래로 풀리고 단일 artifact가 결과이면 /ha 가 오히려 낫다 (적은 synthesis overhead, 빠른 iteration).

### Escalation Path

/ha Phase 1이 HIGH uncertainty + multi-branch reasoning 필요성을 감지하면 사용자에게 `/cast`로의 escalation을 제안하고 중단한다 (Loop-Back Rule #5 Complexity Underestimate의 knife 변형). 임의로 fleet을 켜지 않는다 — knife invariant는 스킬 경계 내에서 불가침이다.

---

## Phase 1 — Pre-Q Deep Reasoning

This phase produces two typed artifacts — **IntentDraft** and **AmbiguityLedger** — BEFORE any user questioning or execution. It applies the 9 reasoning principles above to the request gathered in Phase 0. Conditional on the result, Phase 2 is either entered or skipped.

### 1-1. Purpose

Deep reasoning at this stage replaces the common anti-pattern of "ask first, think later." The aim is to enumerate every plausible interpretation, every dependency, and every information gap before deciding whether to bother the user.

Core techniques applied:

- **Self-Ask gate** (arXiv:2210.03350): explicit `Are follow-up questions needed here? Yes/No` decision at the end of this phase.
- **Least-to-Most decomposition** (SCAN 16% → 99.7%): "To solve X, we need to first resolve A, B, C, ..."
- **Plan-and-Solve PS+** (GSM8K +3%): "Extract relevant variables and their values" — name what is known and what is missing.
- **Uncertainty-of-Thoughts** (UoT, arXiv:2402.03271): simulate how plausible answers branch the plan. 20Q accuracy 48.6% → 71.2%, Medical Diagnosis +120%.

### 1-2. Sub-Steps

**1-2-1. Lightweight Artifact Exploration**

Use Grep, Glob, Read on the artifacts surfaced in Phase 0. Goal: understand existing patterns, conventions, dependencies. Do NOT execute the work yet — only observe enough to reason about ambiguity.

> **Single-agent (knife invariant)**: Per "Single-Agent Policy" (위 섹션), Phase 1 Pre-Q Reasoning은 Opus 단독으로 수행한다. Read/Grep/Glob 등 local tool만 사용해 IntentDraft + AmbiguityLedger를 산출한다. 어떤 subagent도 dispatch하지 않는다. 다면 탐색이 필요하다고 판단되면 `/cast`로 escalation 제안 후 중단 (Loop-Back Rule #5 knife 변형).

**1-2-2. IntentDraft Construction**

Draft a typed object with these fields:

```
IntentDraft:
  goal: [one sentence: what the user wants]
  primary_artifact: [the deliverable]
  inferred_constraints: [what we've inferred from CWD/keywords/context]
  explicit_constraints: [what the user explicitly said]
  task_type: [from Phase 0]
  confidence: [0.0 - 1.0]
```

**1-2-3. Ambiguity Enumeration (Least-to-Most)**

List EVERY plausible ambiguity. Do not prematurely prune. For each ambiguity, write:

- **What** is unclear
- **Why** it matters (which downstream decisions depend on it)
- **Plausible answers** (2-4 candidates)

**1-2-4. EVPI Scoring per Ambiguity**

For each ambiguity, simulate: "If I assumed each plausible answer, would the resulting plan differ materially?"

- **Hi severity**: different answers → fundamentally different plan (different files, different audience, different output form). Worth asking.
- **Med severity**: different answers → different details but same overall plan. Maybe ask if budget allows.
- **Low severity**: all plausible answers lead to the same plan. Do NOT ask. Pick the most likely default and state it.

**1-2-5. Hypothesis Generation**

For unresolved questions where no user input is available, list 2-3 hypotheses (most likely first). These will be re-tested in Phase 6.

**1-2-6. Source / Evidence Inventory**

What sources will be needed? For research/analysis/decision, list candidate sources. For code/writing, list reference files.

**1-2-7. Uncertainty Level Decision**

Aggregate the AmbiguityLedger:

| Uncertainty | Hi count | Med count | Action |
|---|---|---|---|
| **LOW** | 0 | ≤2 | **Skip Phase 2**, go directly to Phase 4 with default assumptions stated |
| **MEDIUM** | 1-3 | 3-5 | Enter Phase 2, /haq or /haqq range applies |
| **HIGH** | ≥4 | ≥6 | Enter Phase 2, /haqq or /haqqq range applies |

The caller's `depth_budget` is a CEILING, not a floor. If the caller is /haqqq but the actual uncertainty is LOW, you still skip Phase 2. This is the **Stop Overthinking** principle (arXiv:2503.16419) operationalized.

### 1-3. Self-Ask Gate

End Phase 1 with a single explicit gate:

```
Are follow-up questions needed here? [Yes / No]
Reason: [if Yes — reference highest-EVPI items; if No — state which defaults will be used]
```

If `No` → jump to Phase 4. If `Yes` → proceed to Phase 2.

### 1-4. Phase 1 Output Format

```
🧠 Pre-Q Deep Reasoning 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Logical Dependencies:
[순서/의존/제약 분석]

⚠️ Risk Assessment:
[리스크 항목]

🔬 Hypotheses:
[현재 문제에 대한 가설들]

📚 Sources / Evidence Needed:
[참고 자료 후보]

🎯 IntentDraft:
- Goal: ...
- Primary Artifact: ...
- Inferred Constraints: ...
- Explicit Constraints: ...
- Confidence: 0.XX

🎯 AmbiguityLedger:
| # | What | Why | Plausible Answers | EVPI |
|---|---|---|---|---|
| 1 | ... | ... | ... | Hi / Med / Low |

🚦 Uncertainty Level: [LOW / MEDIUM / HIGH]
   - Hi: N, Med: N, Low: N
   - Caller depth_budget: [0-4 / 5-8 / 9-12 / direct]
   - Effective decision: [SKIP Phase 2 / ENTER Phase 2 with budget X]

🚪 Self-Ask Gate: Are follow-up questions needed here? [Yes / No]
   Reason: ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Response Inhibition reminder (principle #9)**: Phase 1의 reasoning이 모두 끝난 후에만 Phase 2 또는 Phase 4로 진입한다. 중간에 미리 코드를 쓰거나 결과를 만들지 않는다.

---

## Phase 2 — Uncertainty-Driven Questioning (Conditional)

This phase asks the user clarifying questions, but only when warranted by Phase 1's uncertainty level. It enforces the user's existing **Uncertainty-Driven Questioning** principle and adds EVPI ordering, fatigue detection, and a Sandler upfront contract.

### 2-0. Skip Condition (CHECK FIRST)

**Skip Phase 2 entirely** if any of these hold:

1. `depth_budget == 0` (direct /ha invocation default)
2. `uncertainty == LOW` (Phase 1 self-ask gate said No)
3. The caller's max_budget is 0

When skipping, state explicitly which assumptions you are adopting and why, then jump directly to Phase 5 (knife mode skips Phase 4). Skipping is the **default behavior** for simple requests — 77% of top-intents in Amazon Alexa logs are correct on the first try without questioning, and Modeling Future Conversation Turns (arXiv:2410.13788) shows 61.9% correctness when LLMs choose "answer directly" over "ask first."

### 2-1. Sandler Upfront Contract Preamble

When entering Phase 2, open with an explicit contract to the user. This pattern (Sandler sales methodology) reduces drop-off and respects user agency:

```
📋 질문 단계 안내 (Upfront Contract)
- 예상 질문 수: 약 [N]개 (최대 [max_budget]개)
- 목적: [highest-EVPI 항목 1-2개 명시]
- 모든 질문에 답할 필요 없습니다. "skip" 또는 "충분해" 라고 답하면 즉시 Phase 4로 진행합니다.
- 답변 후 모호성이 해소되면 남은 질문은 자동 생략됩니다.
```

### Question Pool Construction (per task_type)

Each task type has a prioritized question **category pool**. Tiers define how many categories participate:

**Code**:
- haq: {핵심 기능, 데이터·구조}
- haqq: {핵심 기능, 데이터·구조, 에러 처리, 성능·제약, 통합·의존성}
- haqqq: {핵심 기능, 데이터·구조, 에러 처리, 성능·확장성, 통합·의존성, 보안·검증, 운영·모니터링}

**Writing**:
- haq: {독자·톤, 핵심 메시지}
- haqq: {독자·톤, 분량·형식, 핵심 메시지, 사실·자료, 구성·흐름}
- haqqq: {독자·톤, 분량·형식, 핵심 메시지, 사실·자료, 구성·흐름, 인용·출처, 편집 라운드, 게시 계획}

**Planning**:
- haq: {목표·성공 기준, 핵심 제약}
- haqq: {목표·성공 기준, 제약, 우선순위, 리스크, 이해관계자}
- haqqq: {목표·성공 기준, 제약, 우선순위, 리스크, 이해관계자, 컨틴전시, 의사소통, 측정 지표, 회고 계획}

**Research**:
- haq: {질문 구체화, 자료 출처}
- haqq: {질문 구체화, 기존 지식, 자료 출처, 분석 방법, 결론 형식}
- haqqq: {질문 구체화, 기존 지식, 자료 출처, 분석 방법, 편향 통제, 결론 형식, 재현 가능성, 후속 연구}

**Analysis**:
- haq: {분석 질문, 데이터 출처}
- haqq: {분석 질문, 데이터 출처, 분석 방법, 가정, 해석·결론 형식}
- haqqq: {분석 질문, 데이터 출처, 데이터 품질·전처리, 분석 방법, 가정, 엣지 케이스, 해석, 감도 분석, 표현·시각화, 재현성·동료 검토}

**Decision**:
- haq: {대안들, 평가 기준}
- haqq: {대안들, 평가 기준, 가중치, 시간 압박, 되돌릴 수 있는가}
- haqqq: {대안들, 평가 기준, 가중치, 시간 압박, 되돌릴 수 있는가, 감도 분석, 2차 효과, 의사소통}

**Creative**:
- haq: {주제·정서, 스타일·레퍼런스}
- haqq: {주제·정서, 시점·화자, 스타일·레퍼런스, 길이·포맷, 제약}
- haqqq: {주제·정서, 시점·화자, 스타일·레퍼런스, 길이·포맷, 제약·권리, 오디언스, 반복 계획}

**Learning**:
- haq: {목표 수준, 가용 시간}
- haqq: {현재 수준, 목표 수준, 가용 시간, 선호 학습 방식, 평가 방법}
- haqqq: {현재 수준, 목표 수준, 가용 시간, 선호 학습 방식, 평가 방법, 동기·리마인더, 실패 복구, 진척 추적}

**Other**:
- All tiers: Negotiate directly with user for 2 / 5 / 9 priority questions.

### 2-2. EVPI-Ordered Question Selection

Questions are NOT asked in arbitrary order. Use the AmbiguityLedger from Phase 1 and rank by EVPI (Expected Value of Perfect Information):

1. Highest-EVPI item first (Hi severity, biggest plan-change impact)
2. Drop any question where all plausible answers lead to the same plan (Low severity)
3. Group related Med-severity items into single multi-part questions where possible
4. EVPI ordering yields 1.5-2.7x question reduction (arXiv:2511.08798)

### 2-3. MANDATORY AskUserQuestion Tool Usage (Brainstorming-Style 선택형)

Knife 모드의 Phase 2 질문은 **AskUserQuestion 웹UI + brainstorming-style 선택형(multi-choice)** 포맷을 반드시 사용한다. Prose 자유서술 질문은 금지 — 사용자 피로도를 높이고 응답 구조화를 해친다.

**Why selection-style in knife mode**: 사용자 feedback "비주얼 컴패니언 선택형 질문 선호"와 NBER 6-10Q drop-off cliff (응답률 73.6%) 대응. 단일-갈래 문제에 prose answer를 요구하는 것은 user working memory(Cowan 4-chunk) 낭비다. 3-4지선다 + "직접 입력" 옵션이 knife의 속도와 brainstorming의 탐색성을 동시에 보존한다.

**Canonical invocation pattern**:

```
AskUserQuestion tool parameters:
- questions: [
    {
      "question": "이 분석의 1차 독자는 누구입니까?",
      "header": "독자",
      "multiSelect": false,
      "options": [
        {"label": "경영진/임원", "description": "요약 중심, 의사결정 지원"},
        {"label": "동료 분석가", "description": "방법론 중심, 재현 가능"},
        {"label": "외부 클라이언트", "description": "전문성 표현"},
        {"label": "본인 학습용", "description": "탐색적, 노트 중심"}
      ]
    }
  ]
```

**선택지 구성 원칙**:

1. **3-4개 discrete option + "직접 입력" 자유형**: Cowan 4-chunk 한계 안에서 의사결정.
2. **Option 간 semantic distance 크게**: "API only" vs "UI + API" 처럼 선택이 실제 plan을 바꾸는 branches.
3. **Description에 trade-off 명시**: 각 선택이 유도할 귀결을 한 줄로 — "요약 중심, 의사결정 지원" 식으로.
4. **Default/recommended 힌트 가능**: description에 "(권장)" 또는 "(가장 일반적)" 삽입. 강요 아님.
5. **라운드당 최대 4개 질문** (Cowan 준수).

**fallback**: 사용자가 "직접 입력"을 택하거나 옵션 외 답을 주면 knife의 판단으로 어느 bucket에 매핑할지 1회 확인 후 진행. 옵션 reconstruct를 위한 re-ask는 금지 (피로도).

### 2-4. Question Round Management

The caller's `question_rounds` controls batching:

- `question_rounds: 1` (haq) — 한 라운드에 모든 질문, 최대 4개
- `question_rounds: 2` (haqq) — 라운드당 4개씩 최대 2라운드
- `question_rounds: 3-5` (haqqq) — 라운드당 4개씩, 기본 3라운드, 필요 시 최대 5라운드

각 라운드 종료 후 AmbiguityLedger를 재평가한다. 해소된 항목이 많아 잔여 모호성이 LOW가 되면 즉시 Phase 3로 진행한다 (조기 종료).

### 2-5. Fatigue Detection (Early Termination)

다음 신호 중 2개 이상이 감지되면 즉시 Phase 3로 종료한다:

- **Answer-length decline**: 사용자 답변 길이가 라운드를 거듭할수록 40% 이상 감소
- **Monosyllabic answers**: "응", "yes", "ok" 같은 1-2 단어 답변이 구조화된 답변 뒤에 등장
- **Explicit stop cues**: "skip", "충분해", "그냥 해줘", "enough", "just do it"
- **Inattention markers**: 무의미한 반복, 첫 옵션 자동 선택, 답변 모순

User Drop-off Cliff (Survicate): 1Q 85.7% → 6-10Q 73.6% → 21-40Q 70.5%. 너무 많은 질문은 답변 품질 자체를 떨어뜨린다.

### 2-6. Stopping Criteria (Event-Driven, Not Count-Driven)

Expert discovery protocols (MI commitment language, SPIN explicit need, aporia resolution) say: stop when the user's answers express commitment / explicit need / resolved aporia, NOT when a count threshold is hit. If the AmbiguityLedger reaches all-RESOLVED or all-INFERABLE, stop immediately even if budget remains.

### 2-7. Phase 2 Output Format

```
❓ Phase 2 — Uncertainty-Driven Questioning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Upfront Contract: [N개 예상, 최대 M개, skip 가능]

🎯 라운드 1 (EVPI 순서로 [k]개)
[AskUserQuestion 호출 결과]

(필요 시) 🎯 라운드 2 ...
(필요 시) 🎯 라운드 3 ...

⏱️ Fatigue 신호: [없음 / 답변 길이 감소 / 모노실래빅 / 명시 stop]
🛑 종료 사유: [모호성 해소 / 예산 소진 / fatigue / 사용자 stop]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 3 — Post-Q Integration Reasoning

This phase reconciles user answers with the IntentDraft and AmbiguityLedger from Phase 1. It detects contradictions, resolves the ledger, and may trigger a loop-back to Phase 1 if reconciliation surfaces new ambiguity.

### 3-1. Purpose

Without integration, Phase 2 answers risk being treated as raw inputs into Phase 4 — which loses the chance to detect contradictions between answers, between an answer and an inferred constraint, or between an answer and the original IntentDraft. Reflexion (arXiv:2303.11366) showed verbal reflection lifts HumanEval 80% → 91%; Chain-of-Verification (CoVe, arXiv:2309.11495) showed independent verification questions reduce hallucinations 50-70%; Self-Refine added +20% across 7 tasks via "localize problem + give fix instruction."

### 3-2. Sub-Steps

**3-2-1. Map Answers to AmbiguityLedger**

For each item in the ledger, classify:

- **RESOLVED** — user's answer directly answers it
- **INFERABLE** — user's answer plus context allows confident inference
- **STILL_OPEN** — answer was ambiguous, user skipped, or fatigue terminated

**3-2-2. Reflexion-Style Contradiction Detection**

Look for contradictions across:

- Answer ↔ Answer (e.g. user wants "fast" and "comprehensive" both top priority)
- Answer ↔ IntentDraft (e.g. user said audience is novice but goal implies expert)
- Answer ↔ Phase 0 inferred constraints (e.g. user said no Python but project is pyproject.toml-based)

For each contradiction, write a reconciliation strategy (which side wins, or how both can be honored).

**3-2-3. CoVe-Style Verification Questions (research/decision/analysis)**

For research/decision/analysis tasks, draft 3-5 verification questions that the final output must withstand. These are NOT asked to the user — they are answered INDEPENDENTLY in Phase 6. Example for research: "Does claim X have a primary source published after 2020?" Example for decision: "Have at least 3 alternatives been considered?"

CoVe key insight: verification questions answered in isolation reduce hallucinations 50-70% vs verification done as part of the original generation.

**3-2-4. Aleatoric vs Epistemic Classification**

If a STILL_OPEN item has survived 2 rounds of questioning, treat it as **aleatoric** (genuinely uncertain in the world, not resolvable by more questions). Pick the most defensible default and state it explicitly in the IntegratedIntent.

If a STILL_OPEN item is **epistemic** (resolvable in principle but not yet resolved) and EVPI is high, this triggers **Loop-Back Rule #1**: return to Phase 1 to enumerate the new ambiguity, then re-enter Phase 2 (subject to circuit breaker).

**3-2-5. Build Integrated Intent**

Produce the final consolidated intent that Phase 4 will design from:

```
IntegratedIntent:
  goal: [refined from IntentDraft + answers]
  task_type: [from Phase 0, possibly refined]
  hard_constraints: [must-have from answers + inferred]
  soft_preferences: [nice-to-have]
  default_assumptions: [stated assumptions for STILL_OPEN aleatoric items]
  verification_questions: [3-5 CoVe questions for Phase 6]
  loopback_needed: [true|false, with reason]
```

### 3-3. Phase 3 Output Format

```
🔁 Post-Q Integration Reasoning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Ledger Resolution:
| # | Item | Status | Resolution |
|---|---|---|---|
| 1 | ... | RESOLVED | 답변: ... |
| 2 | ... | INFERABLE | 추론: ... |
| 3 | ... | STILL_OPEN (aleatoric) | 기본값: ... |

⚠️ Contradictions Detected:
[항목별 + 화해 전략]

🔬 CoVe Verification Questions (Phase 6용):
1. ...
2. ...
3. ...

🔄 Loop-back Needed: [No / Yes — to Phase 1, reason: ...]

🎯 Final Integrated Intent:
- Goal: ...
- Task Type: ...
- Hard Constraints: ...
- Soft Preferences: ...
- Default Assumptions: ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 4 — Skipped in Knife Mode

Knife의 전제는 "단일 산출물, 단일 사고 갈래"다. 9-종 task-type design template으로 실행 계획을 분리·정형화하는 /cast Phase 4는 knife mode에서 **skip**된다.

Phase 3의 Post-Q 통합 추론 결과(IntentDraft + AmbiguityLedger 해소분 + 실행 경로)가 곧 Phase 5 execution directive다. 중간 design artifact는 생성하지 않는다 — 한 사고가 한 실행으로 직결되는 것이 knife의 가치다.

**Escalation trigger**: 만약 task가 multi-file / multi-section / multi-step 산출물을 본질적으로 요구한다면 knife 적합성을 재평가하고 `/cast`로 escalate 제안 후 중단한다 (Loop-Back Rule #5 knife 변형 — Complexity Underestimate).

## Phase 5 — Execution Delegation

This phase delegates the work to a **단일 executor agent** (Haiku 또는 경량 task의 경우 Opus 직접) via the Task tool. Knife invariant에 따라 fleet dispatch 없이 한 화살로 Phase 3 directive를 실행한다.

> **Single-agent (knife invariant)**: Phase 3의 Post-Q 통합 결과가 곧 실행 지시서다. 이것을 **한 executor**에게 독립 brief로 전달한다. 여러 agent 간 synthesis overhead, context bleed, tie-breaker cost를 회피하는 것이 knife의 가치. Code task = executor 또는 Haiku worker 1개, writing = writer 1개, 분석 = scientist 1개 — task-type별 canonical choice 하나만 선택한다. 복수 관점이 필요하다고 판단되면 `/cast`로 escalation 후 중단.

### 5-1. Task Tool Invocation

```
Task tool parameters:
- subagent_type: "general-purpose"
- model: "haiku"
- prompt: (use Work Execution Directive template below)
```

### 5-2. Work Execution Directive Template

```
# Work Execution Directive

Your role is to execute the work exactly as designed. Do not add scope, do not improvise, and do not invent requirements that are not in the design document.

## Task Type
[code / writing / planning / research / analysis / decision / creative / learning / other]

## Context
- Working directory: [CWD]
- Relevant artifacts: [Phase 0 detected context]
- Task characteristics: [summary]
- Default assumptions to honor: [from Phase 3 IntegratedIntent]

## Work Content

[Paste the task-type-specific section of the Phase 4 design document here verbatim]

## Execution Order
1. [Unit 1]
2. [Unit 2]
...

## Output Expectations
- All deliverables in Korean unless the design specifies otherwise.
- Use the file types listed in the design (no surprise extensions).
- When complete, output "Work Complete" followed by a list of artifacts created/modified.

## Blocker Reporting (if you cannot proceed)
If a step is underspecified, blocked, or you find a contradiction, DO NOT ask the user. Instead, return a structured blocker report and stop:

BLOCKER: [one-sentence description of the gap]
CONTEXT: [what information is missing or contradictory]
REQUIRED: [what Opus must clarify or decide before you can proceed]

The Opus controller will classify the blocker and loop back to the appropriate phase per the Loop-Back Rules.
```

### 5-3. Task-Type Behavior Hints for Haiku

| Task Type | Haiku 동작 |
|---|---|
| code | 파일 편집/생성 (Edit, Write tool), linter/test 실행 가능 |
| writing | markdown/txt 파일 작성 |
| planning | 일정표/체크리스트 (markdown 표) 생성 |
| research | 문서 요약/합성, 인용 마커 유지 |
| analysis | 데이터 로드 + 변환 + 보고서 작성 (각 단계 결과 명시) |
| decision | 매트릭스 + 권장안 작성 |
| creative | 구조화된 창작물 작성 |
| learning | 커리큘럼 문서 작성 |
| other | 사용자가 원한 형태 |

### 5-4. Blocker Classification (Opus side)

If Haiku returns a BLOCKER, Opus classifies it and triggers the appropriate loop-back:

| Blocker type | Trigger | Loop-back |
|---|---|---|
| Design underspec (the design itself is missing detail) | Rule 3 | 5 → 4 (max 1) |
| Transient failure (network, file lock, retryable error) | Rule 4 | 5 → 5 retry (max 2) |
| Contradiction with IntegratedIntent | Rule 7 | 6 → 3 (max 1) |

### 5-5. Phase 5 Output Format

```
🚀 Phase 5 — Delegating to Haiku
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📤 Task tool 호출 (subagent_type: general-purpose, model: haiku)
[Work Execution Directive 요약]

📥 Haiku 응답:
[Work Complete / BLOCKER report]

(if BLOCKER) 🔄 Loop-back classification: [Rule N → Phase X]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 6 — Task-Type-Aware Verification

This phase verifies the Phase 5 execution output against task-type-specific quality criteria. It is the last line of defense against hallucinations, structural defects, and silently-skipped requirements. Findings are classified into 4 buckets that map to loop-back rules.

> **Single-agent (knife invariant)**: Phase 6 verification은 **단일 critic/verifier** (task-type canonical choice 하나) 또는 Opus 자가 검증으로 수행한다. Task-type별 canonical: code→code-reviewer 1개, writing→critic 1개, research→critic 1개 (단, citation verification은 Opus 직접), decision→critic 1개, analysis→scientist 1개. 복수 reviewer 병렬 dispatch는 knife invariant 위반 — 필요하면 `/cast`로 escalation. 단일 critic의 findings를 6-4 classification bucket으로 매핑.

### 6-1. Verification Recipes (per task type)

**[code]**

- 감지된 linter 실행 (mypy / tsc --noEmit / ruff / cargo clippy / go vet 등 Phase 0 detection 결과)
- 감지된 test runner 실행 (pytest / jest / cargo test / go test 등)
- 영향 받는 다른 모듈 grep 확인
- 발견된 오류 → 수정 위임

**[writing]**

- **Atomic claim extraction**: 본문의 모든 사실 주장을 1문장 단위로 추출
- **Fact-flagging**: 검증되지 않은 통계/숫자/인용/날짜에 `[STAT UNVERIFIED]` 등 마커 자동 주입 (6-3 참조)
- **Temporal disclosure**: 시점 의존 정보에 "as of [date]" 추가
- 톤 일관성, 구조, 문법 자체 점검
- (선택) LanguageTool 류 외부 도구 가능 시 사용

**[planning]**

- **Critical Path 검증**: 각 단계의 prerequisite가 실제로 선행 단계에 포함되는가
- **Cycle detection**: dependency 그래프에 사이클이 없는가
- **Arithmetic validation**: duration 합계, 예산 합계가 제약과 일치하는가
- 자원 경합 (같은 owner가 동시에 두 단계 담당하는가) 확인

**[research] 🔴 CRITICAL**

법률 분야에서 LLM hallucination rate는 39-88%에 이른다. Research task는 다른 어떤 task type보다도 강한 검증이 필요하다.

- **Mandatory DOI/citation verification**: 모든 인용에 대해 WebFetch로 1차 출처 접근 (실패 시 `[CITATION UNVERIFIED]` 마킹)
- **CRAAP test**: Currency / Relevance / Authority / Accuracy / Purpose 5축 점검
- **CoVe verification questions**: Phase 3에서 만든 검증 질문에 INDEPENDENTLY 답함 (원래 본문을 보지 않고)
- **Bias check**: 한쪽 관점만 인용했는지 확인
- 해소 불가한 인용 → `[UNVERIFIED]` 라벨로 명시 + 사용자에게 알림

**[analysis] (NEW)**

- **데이터 무결성**: row count, null %, dtype, 중복, outlier 분포 확인
- **통계 방법 적절성**: 사용된 방법이 데이터 분포/표본 크기/측정 수준에 맞는가
- **결론-증거 일관성**: 결론이 데이터에서 실제로 도출 가능한가, 과잉 일반화 없는가
- **대안 해석 탐색**: "다르게 해석할 수 있는가?" 최소 1개 대안 시나리오 검토
- **Sample size disclosure**: 표본 크기/대표성 명시
- 결과 시각화 (있는 경우) — 축, 범례, 단위 누락 확인

**[decision] 🔴 CRITICAL**

Clinical decision support에서 83% error echo rate가 보고되어 있다. Decision task도 research와 동급의 위험을 가진다.

- **Alternatives audit**: 최소 3개 대안이 매트릭스에 있는가 (없으면 즉시 fail)
- **Assumption surfacing**: 암묵 가정이 명시되어 있는가
- **Bias audit**: 가능하면 different-model judge 사용 (LLM-as-judge는 same-model self-evaluation은 신뢰 불가)
- **Sensitivity flagging**: 가중치 ±20% 변화 시 순위 뒤집힘 여부 명시
- **Reversibility statement**: 결정의 되돌림 가능성 명시

**[creative]**

- **Constraint compliance**: 사용자 명시 제약 (길이/포맷/금지어) 충족 여부
- **Style consistency**: 톤/시점/시제 일관성
- **Rights check**: 저작권 우려가 있는 직접 인용/모방 없음
- **Originality flag**: 잘 알려진 작품과 과도한 유사성 경고

**[learning]**

- **Source anchoring**: 학습 자료에 출처가 있는가 (위키피디아 vs 1차 자료)
- **Temporal disclosure**: "as of [date]" — 빠르게 변하는 분야 (frameworks, APIs, regulations)
- **Outdated-practice flag**: 더 이상 권장되지 않는 패턴이 포함되었는지
- **Pedagogical coherence**: 선행 세션이 후행 세션의 prerequisite을 충족하는가
- **Realistic time budget**: 세션 시간이 실제 학습 가능한 양인가

**[other]**

- 사용자 수용 기준 직접 확인
- 산출물 형태가 사용자가 원한 것과 일치하는가

### 6-2. Severity Rank (R9 evidence)

Hallucination 위험 severity ranking:

```
Research (CRITICAL, 39-88% fabricated citations)
> Decision (CRITICAL, 83% error echo in clinical)
> Learning
> Writing
> Analysis
> Planning
> Creative
> Code (linter/test catches most)
```

CRITICAL 등급 task type의 검증은 절대 생략하지 않는다.

### 6-3. Confidence Disclosure Auto-Injection

Final output에 다음 마커들을 자동 주입한다:

| Marker | When to inject |
|---|---|
| `[STAT UNVERIFIED]` | 검증되지 않은 통계/숫자 |
| `[QUOTE UNVERIFIED]` | 1차 출처에서 확인 불가한 직접 인용 |
| `[CITATION UNVERIFIED]` | DOI/URL 접근 실패 인용 |
| `[HIGH-STAKES ADVICE]` | 의학/법률/재무 등 결과 영향 큰 권고 |
| `[KNOWLEDGE CUTOFF: YYYY-MM]` | 모델 cutoff 이후 가능성 있는 사실 |
| `[LOW CONFIDENCE]` | Phase 1 confidence < 0.6 |
| `[ASSUMED DEFAULT]` | Phase 3 STILL_OPEN aleatoric로 default 사용된 부분 |

### 6-4. Findings Classification → Loop-Back Mapping

| Finding | Severity | Loop-back rule |
|---|---|---|
| 통과 (검증 OK) | — | 종료 |
| 사소한 수정 (typo, formatting, 부분 fact 미흡) | minor | Rule 5: 6 → 5 (재실행, 최대 3회) |
| 구조적 결함 (design 자체가 잘못됨) | structural | Rule 6: 6 → 4 (재설계, 최대 1회) |
| 요구사항 누락 (사용자가 말한 것이 빠짐) | requirements gap | Rule 7: 6 → 3 (Integrated Intent 갱신, 최대 1회) |

### 6-5. Phase 6 Output Format

```
✅ Phase 6 — Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Verification recipe: [task type별 recipe 이름]

검증 결과:
- [Item 1]: PASS / FAIL — [상세]
- [Item 2]: PASS / FAIL — [상세]
- [Item 3]: PASS / FAIL — [상세]

🔬 CoVe answers (research/decision/analysis):
1. Q: ... | Independent answer: ...
2. ...

💡 Confidence markers injected: [STAT UNVERIFIED, KNOWLEDGE CUTOFF, ...]

📊 Findings classification:
- pass / minor fix (rule 5) / structural (rule 6) / requirements gap (rule 7)

🔄 Loop-back action: [None / Rule N → Phase X]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Loop-Back Rules

The 7 phases above are not strictly linear. Loop-backs are allowed under explicit rules with hard caps. A global circuit breaker triggers user escalation if too many loop-backs accumulate.

### 8 Loop-Back Rules

| # | Trigger | From → To | Max | Notes |
|---|---|---|---|---|
| 1 | Post-Q reconciliation surfaces NEW ambiguity or contradiction Phase 2 cannot resolve | Phase 3 → Phase 1 | 2 | Re-enumerate ambiguities, may re-enter Phase 2 |
| 2 | Phase 4 design fails the verification checklist (underspec, missing evidence, placeholder leak) | Phase 4 → Phase 3 | 2 | Tighten the IntegratedIntent first |
| 3 | Phase 5 Haiku BLOCKER — design underspec | Phase 5 → Phase 4 | 1 | Rewrite the relevant design section |
| 4 | Phase 5 transient failure (retryable error) | Phase 5 → Phase 5 | 2 retry | Same Haiku call, no design change |
| 5 | Phase 6 fixable finding (minor) | Phase 6 → Phase 5 | 3 | Re-execute with corrected scope |
| 6 | Phase 6 structural issue (design itself wrong) | Phase 6 → Phase 4 | 1 | Redesign and re-execute |
| 7 | Phase 6 requirements gap (Integrated Intent missed something) | Phase 6 → Phase 3 | 1 | Re-integrate, possibly re-design and re-execute |
| 8 | **Global Circuit Breaker** | * → ABORT | 3 total | Loop-backs across all phases ≥ 3 → ABORT and escalate to user |

### Circuit Breaker Detail (Rule #8)

Loop-back count is summed across ALL rules. If the running total reaches 3, treat this as evidence that the architecture or assumption is wrong, NOT that "one more loop will fix it." Sunk-cost fallacy avoidance.

When the circuit breaker fires:

1. STOP all execution.
2. Print the loop-back history (which rule fired when, why).
3. State the suspected root cause (most common: ambiguity in Phase 0 task type detection, or contradictory user constraints).
4. Print the **User Escalation** message:
   ```
   ⛔ Circuit Breaker triggered (3 loop-backs)
   Architecture or assumption is likely wrong. Halting to ask:
   - 가장 흔한 원인: [task type 오감지 / 모순된 제약 / 데이터 부족]
   - 확인이 필요한 항목: [3개 이내]
   - 다음 행동 제안: [restart with /haqq, clarify constraint X, provide data Y]
   ```
5. Wait for user direction before any further work.

The circuit breaker is intentional and non-negotiable. Skipping it leads to MAST FM-3.1 (premature termination of debugging followed by hallucinated success claims).

---

## Anti-Patterns to Avoid

This skill explicitly avoids the following failure modes (drawn from MAST + KAIST 2025 + arXiv prompt engineering meta-studies):

- **MAST FM-2.2** — Failing to ask for clarification when needed: addressed by Phase 1 Self-Ask gate.
- **MAST FM-2.3** — Task derailment: addressed by Phase 0 task type lock + Phase 5 "do not add scope" directive.
- **MAST FM-3.1** — Premature termination: addressed by Phase 6 verification + circuit breaker.
- **MAST FM-1.2** — Disobeying role: addressed by Work Execution Directive's strict scope clause.
- **Persona-prompt anti-pattern (KAIST 2025)** — "You are a senior X" hurts factual accuracy on MMLU. This skill uses purpose framing instead.
- **Negative-instruction anti-pattern** — "Don't do X" underperforms "Do Y." This skill uses positive framing throughout.
- **Stop Overthinking (arXiv:2503.16419)** — Wasting 19-42s on simple queries. Addressed by Phase 2-0 Skip Condition + Phase 1 LOW uncertainty path.
- **Single-model routing anti-pattern** — Addressed by Phase 0 two-stage detection cascade.

---

## Role Prompting Fix (Purpose Framing, Not Persona)

When delegating to Haiku agents, **never** use persona framing like "You are a senior engineer with 20 years of experience." Instead, use **purpose framing**:

**Bad**: "You are an expert code reviewer. Review this code."
**Good**: "Your task: Identify logical flaws, performance issues, and security risks in this code. Output: list of issues + severity + fix suggestions."

**Bad**: "You are a creative writer. Write a story."
**Good**: "Write a short story (200–300 words) in the voice of [tone], about [theme], suitable for [audience]. Output: story + 1-paragraph description of creative choices."

Purpose framing:
- Reduces hallucination (Haiku focuses on the task, not the imagined role).
- Enables better agent composition (same Haiku can be a "code reviewer" in one subtask, a "test engineer" in another).
- Improves quality measurement (success is defined by task output, not role persona).

---

## Notes

- **Output language**: All user-facing output (design summaries, questions, explanations) is in **Korean**.
- **Skill invocation** from /haq, /haqq, /haqqq prepend config; /ha respects config or defaults to depth_budget=0.
- **No re-implementation**: /haq/haqq/haqqq are thin shims; they never redefine Phase 0–6 logic. They only set config + category hints.
- **Agent autonomy**: Haiku agents receive task descriptions + design template, not role personas. They are purpose-driven, not identity-driven.
- **Transparency**: Every phase outputs intermediate results, ambiguity scores, agent dispatch decisions, verification notes. User can always see why decisions were made.
- **Reasoning Framework**: 9원칙은 `shared/reasoning-framework.md`에 canonical source로 정의. ha와 decompose 모두 동일 파일을 Read하여 drift를 방지한다.

---

## Output Format (Combined View)

```
🔍 Phase 0 — Context 감지
[Phase 0 output block]

🧠 Phase 1 — Pre-Q Deep Reasoning
[Phase 1 output block, ending with Self-Ask gate]

❓ Phase 2 — Uncertainty-Driven Questioning   (skipped if uncertainty=LOW or depth_budget=0)
[Phase 2 output block — or "SKIPPED: reason"]

🔁 Phase 3 — Post-Q Integration Reasoning   (skipped if Phase 2 was skipped)
[Phase 3 output block — or "SKIPPED: defaults from Phase 1 used"]

📐 Phase 4 — Design Document (task type: [type])
[Phase 4 template filled]

🚀 Phase 5 — Delegating to Haiku
[Phase 5 output block]

✅ Phase 6 — Verification
[Phase 6 output block]

📊 Final Status:
- Task type: [type]
- Uncertainty: [LOW / MEDIUM / HIGH]
- Phase 2 entered: [Yes / No]
- Loop-backs: [count] / 3 (circuit breaker)
- Artifacts created: N
- Artifacts modified: N
- Verification result: [PASS / partial / FAIL]
- Confidence markers injected: [list]
```
