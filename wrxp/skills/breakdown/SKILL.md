---
name: breakdown
description: Use when the user has a request that needs intent refinement, recursive decomposition, dynamic agent matching, and DAG-based parallel autonomous execution — the full orchestration pipeline.
argument-hint: "[요청 내용]"
level: 4
---

# breakdown

## Overview

유저의 요청을 받아 **7단계 파이프라인**으로 자율 실행하는 메인 오케스트레이터.

**핵심 철학**: 메인 AI(Opus)는 조율에만 집중한다. 코드 읽기, 분석, 실행은 전부 에이전트에게 위임하여 컨텍스트를 보호한다.

**컴포저블 구조**: `breakdown` = `decompose` (Phase 1+2) → `agent-match` (Phase 4) → 자율 실행 (Phase 6+7)

---

## Phase 1+2 — 의도 정제 + 재귀적 분해

> 이 Phase는 내부적으로 `/decompose` 스킬을 사용한다. 독립 사용 시 `/decompose "문제"` 직접 호출 가능.
> 질문 횟수 제한: Soft cap 5회 / Hard cap 10회 (decompose 스킬 기준 적용)

### 1-1. 프로젝트 컨텍스트 수집

> 이 단계는 `middleware-ref` 스킬의 절차를 따른다.
> middleware-ref가 백엔드(Graphiti/YAML/CodeSearch)를 자동 감지하고 표준 컨텍스트 포맷으로 반환한다.

1. `.middleware/manifest.yaml`을 읽어 백엔드를 감지한다.
2. `middleware-ref` 스킬의 절차에 따라 프로젝트 컨텍스트를 수집한다.
   - **Graphiti Mode**: manifest.yaml의 `queries` 섹션을 참조하여 Graphiti KG에서 검색
   - **YAML Mode**: features.yaml + context.yaml 직접 읽기 (레거시)
   - **Code Search Mode**: git log + 코드 구조 탐색 (폴백)
3. 수집된 표준 컨텍스트(아키텍처 원칙, 제약, 설계 결정, 의존성, 도메인 지식)를 이후 단계에 반영한다.

### 1-2. 의도 명확화

- 유저 요청에서 모호한 부분 식별 (유저가 확실하다고 생각하지만 AI가 보기에 불명확한 것 포함)
- `AskUserQuestion`으로 하나씩 질문 — **한 번에 하나**, 가능하면 선택지 제공
- 모호성이 충분히 제거될 때까지 반복

### 1-3. 출력

파일 저장: `.wrxp/state/intent-{slug}.md`

```
- 원래 요청
- 정제된 의도
- 핵심 제약사항
- 관련 middleware 지식 요약
```

---

## Phase 2 — 재귀적 문제 분해 (Recursive Decomposition)

### 2-1. 분해 규칙

**단일 태스크 fast-path**: 정제된 의도가 이미 단일 에이전트로 완료 가능한 크기라면, 분해를 스킵하고 단일 노드 트리를 생성하여 바로 Phase 4로 진행. 나머지 단계(에이전트 매칭, 실행, 검증, 결과 통합)는 그대로 수행.

분해가 필요한 경우:
1. 정제된 의도를 서브태스크로 분해
2. 각 서브태스크가 **단일 에이전트가 독립 실행 가능한 크기**인지 판단
3. 아직 크면 재귀적으로 더 분해 (무한 깊이 허용 — Opus가 조율만 하므로 깊이 걱정 없음)

**리프 노드 조건**:
- 단일 에이전트가 독립적으로 완료 가능
- 입력과 출력이 명확
- 다른 태스크와의 의존성이 식별 가능

### 2-2. 분해 트리 시각화 + 유저 승인

분해 결과를 텍스트 트리로 유저에게 제시:

```
[루트] 소셜 로그인 추가
├── [1] OAuth 프로바이더 설정
│   ├── [1.1] Google OAuth 클라이언트 설정
│   └── [1.2] Kakao OAuth 클라이언트 설정
├── [2] 백엔드 인증 플로우
│   ├── [2.1] OAuth 콜백 엔드포인트
│   └── [2.2] 세션 연동
└── [3] 프론트엔드 UI
    ├── [3.1] 소셜 로그인 버튼 컴포넌트
    └── [3.2] 로그인 상태 관리
```

`AskUserQuestion`: "이 분해 트리로 진행할까요? 수정이 필요하면 말씀해 주세요."

### 2-3. 출력

파일 저장: `.wrxp/state/tree-{slug}.json`

---

## Phase 3 — Implementation Plan Writing (상세 기획)

> Phase 2의 분해 트리가 승인되면, Phase 4(에이전트 매칭) 전에 **writing-plans 수준의 완전한 실행 지시서**를 작성한다. "무엇을 분해했는가"에서 "정확히 어떻게 구현하는가"로 전환하는 gate.

### 3-1. 설계 원칙 (writing-plans 계승)

> "엔지니어가 이 코드베이스에 대한 사전 지식이 전혀 없다고 가정하고 작성한다. DRY, YAGNI, TDD, 빈번한 커밋."

플랜 header에 반드시 포함:
- **Goal**: 한 문장으로 무엇을 만드는가
- **Architecture**: 2-3 문장의 접근 방식
- **Tech Stack**: 핵심 기술/라이브러리 목록

### 3-2. File Structure Mapping

각 리프 태스크에 대해 파일 매핑 명시:
- **Create**: `정확/한/경로/파일.py`
- **Modify**: `정확/한/경로/기존파일.py:123-145` (라인 범위 포함)
- **Test**: `tests/정확/한/경로/test.py`

파일 경계는 책임 단위로 나누고, 한 파일이 하나의 명확한 역할만 갖도록 한다.

### 3-3. Bite-sized Step Decomposition

각 리프 태스크를 2-5분 단위 step으로 분해 (TDD 사이클):

```
- [ ] Step 1: 실패하는 테스트 작성 (실제 테스트 코드 블록 포함)
- [ ] Step 2: 테스트 실행하여 실패 확인 (정확한 명령어 + 기대 출력)
- [ ] Step 3: 최소 구현 (실제 구현 코드 블록 포함)
- [ ] Step 4: 테스트 실행하여 성공 확인 (정확한 명령어 + 기대 출력)
- [ ] Step 5: 커밋 (커밋 메시지 포함)
```

### 3-4. No-Placeholder Rule

🚫 **다음 패턴은 절대 금지** (플랜 실패 신호):
- `TBD`, `TODO`, `나중에 구현`, `세부사항 채우기`
- `적절한 에러 처리 추가`, `유효성 검사 추가`, `엣지 케이스 처리`
- `위 내용에 대한 테스트 작성` (실제 테스트 코드 없이)
- `Task N과 유사` (코드를 반복 기재해야 함 — 엔지니어가 태스크를 순서 없이 볼 수 있음)
- 어떻게 하는지 보여주지 않고 무엇을 하라고만 설명
- 어느 태스크에서도 정의되지 않은 타입/함수/메서드 참조

### 3-5. Self-Review 체크리스트

플랜 작성 완료 후 새로운 시각으로 검토:

1. **Spec coverage**: 원래 요청의 각 요건이 특정 태스크에 매핑되는가? 누락 확인.
2. **Placeholder scan**: 위 No-Placeholder 패턴이 남아있지 않은가?
3. **Type consistency**: Task 3의 `clearLayers()`와 Task 7의 `clearFullLayers()` 같은 불일치 없는가?

문제 발견 시 즉시 inline 수정.

### 3-6. 출력

파일 저장: `.wrxp/state/plan-{slug}.md`

```markdown
# {Feature Name} Implementation Plan

**Goal:** ...
**Architecture:** ...
**Tech Stack:** ...

---

### Task 1: {Component Name}

**Files:**
- Create: ...
- Modify: ...
- Test: ...

- [ ] **Step 1: ...**
- [ ] **Step 2: ...**
- ...

### Task 2: ...
```

---

## Phase 4 — 에이전트 매칭 + DAG 구성 (Agent Matching)

> 이 Phase는 내부적으로 `/agent-match` 스킬을 사용한다. 독립 사용 시 `/agent-match "태스크 목록"` 직접 호출 가능.

### 4-1. 동적 에이전트 선택

> **하드코딩 금지**: 에이전트 목록을 미리 정의하지 않는다. 매번 실행 시 현재 사용 가능한 에이전트 목록을 동적으로 확인한 뒤, 태스크에 가장 적합한 에이전트를 선택한다.

**에이전트 탐색 루틴** (매 실행마다 수행):
1. 시스템에서 사용 가능한 `subagent_type` 목록을 확인 (Agent tool의 available types)
2. 각 에이전트의 설명(description)과 역할을 읽어 파악
3. 각 리프 태스크의 특성(유형/복잡도/도메인/검증 필요 여부)과 대조
4. 가장 적합한 에이전트를 동적으로 선택

**선택 기준 (태스크별)**:
1. 태스크 유형: 설계 / 구현 / 검증 / 리서치 / UI / 디버깅
2. 복잡도: 단순 / 표준 / 복잡
3. 도메인: 백엔드 / 프론트엔드 / 인프라 / 데이터
4. 교차 검증 필요 여부

### 4-2. Middleware Do 지식 주입

각 에이전트 프롬프트에 관련 middleware 지식 주입:
- `features`: 해당 모듈의 purpose, status
- `domain_knowledge`: topic, summary
- `design_decisions`: title, decision, rationale (accepted만)

### 4-3. DAG 구성

- 독립 태스크 → 병렬 실행 마킹
- 의존성 있는 태스크만 순차 관계 설정
- Wave 기반 스케줄링: 같은 레벨의 독립 태스크는 동시 실행

파일 저장: `.wrxp/state/dag-{slug}.json`

---

## Phase 5 — Strategy Selection (실행 전략 선택)

> ⚠️ **MANDATORY GATE**: Phase 6(실제 실행) 진입 전에 반드시 `AskUserQuestion`으로 실행 전략을 유저에게 선택받는다. 이 Phase를 건너뛰고 Phase 6로 진입하는 것은 **절대 금지**.

### 5-1. 전략 차원 정의

4가지 옵션은 다음 3축을 조합하여 생성:

| 축 | 가능한 값 |
|---|---|
| **방향 (Direction)** | 속도 중심 / 안전 중심 / TDD 엄격 / 완전 자율 |
| **에이전트 조합 (Agent Mix)** | executor 단독 / architect+executor+verifier / test-engineer+executor+critic / 기본 DAG |
| **진행 방식 (Execution Mode)** | Wave 전자동 / Wave 간 승인 / 리프별 승인 / Batch+체크포인트 |

### 5-2. 기본 4가지 프리셋

Phase 4에서 구성한 DAG를 바탕으로 다음 4개 프리셋을 **동적으로 생성**한다 (태스크 성격에 따라 에이전트 구성과 설명을 조정):

**A. 🚀 Speed-first (빠른 구현)**
- 방향: 속도 중심
- 에이전트: executor 단독 (복잡도 기반 모델 자동 선택)
- 진행: Wave 자동 진행, 검증 최소
- 적합: 빠른 프로토타입, 낮은 리스크, 간단한 CRUD

**B. 🛡️ Safety-first (안전한 구현)**
- 방향: 안전 중심
- 에이전트: architect(설계 검토) → executor(구현) → verifier(정합성 검증) 삼각
- 진행: Wave 간 유저 승인 체크포인트
- 적합: 프로덕션 레벨, 높은 리스크, 중요 비즈니스 로직

**C. 🧪 TDD-strict (TDD 엄격)**
- 방향: 테스트 우선
- 에이전트: test-engineer(테스트 선작성) → executor(구현) → critic(리뷰)
- 진행: 모든 리프에 검증
- 적합: 핵심 알고리즘, 긴 수명 코드, 리팩토링 대상

**D. 🤖 Full autonomous (완전 자율)**
- 방향: 완전 자율
- 에이전트: Phase 4의 기본 DAG 그대로 사용
- 진행: 유저 개입 없이 병렬 실행, Phase 7 요약만 보고
- 적합: 신뢰된 반복 태스크, 최소 개입

### 5-3. 동적 조정 규칙

Phase 4의 DAG 결과를 분석하여 프리셋을 조정:
- 태스크 중 `domain: infra` 또는 `domain: security`가 포함되면 → A의 우선순위 낮춤, B 우선순위 높임
- 태스크가 10개 이상이면 → D의 추천 레이블에 "(대규모 자동화에 적합)" 추가
- 태스크 중 `type: test` 노드가 없으면 → C의 설명에 "테스트 태스크 자동 생성 포함" 명시
- 태스크 중 `critical: true` 플래그가 있으면 → A의 설명에 "⚠️ 크리티컬 태스크 포함 — 주의" 경고

### 5-4. 유저 선택 (MANDATORY AskUserQuestion)

> 🚫 **절대 금지**:
> - 평문으로 "어떤 전략을 원하시나요?" 라고 묻기
> - 4가지 옵션을 markdown 리스트로 나열 후 응답 대기
> - AskUserQuestion 없이 기본값으로 Phase 6 진입

✅ **유일하게 허용**: `AskUserQuestion` 도구로 4지선다 제시

```
AskUserQuestion({
  questions: [{
    question: "어떤 실행 전략으로 진행할까요?",
    header: "실행 전략",
    multiSelect: false,
    options: [
      { label: "🚀 빠른 구현", description: "executor 단독, Wave 자동, 검증 최소" },
      { label: "🛡️ 안전한 구현", description: "architect→executor→verifier 삼각, Wave 간 승인" },
      { label: "🧪 TDD 엄격", description: "test-engineer→executor→critic, 모든 리프 검증" },
      { label: "🤖 완전 자율", description: "기본 DAG 그대로 병렬 실행, 요약만 보고" }
    ]
  }]
})
```

### 5-5. 선택 반영

유저 선택 이후:
1. 선택된 전략에 따라 DAG 재구성 (에이전트 교체, wave 재편성)
2. 변경된 DAG를 `.wrxp/state/dag-{slug}.json`에 덮어쓰기
3. 선택 기록을 `.wrxp/state/strategy-{slug}.json`에 저장:
   ```json
   {
     "slug": "feature-slug",
     "strategy": "safety-first",
     "direction": "안전 중심",
     "agent_mix": ["architect", "executor", "verifier"],
     "execution_mode": "wave-approval",
     "selected_at": "ISO-8601 timestamp"
   }
   ```
4. Phase 6(Autonomous Execution)로 진입

---

## Phase 6 — 자율 실행 (Autonomous Execution)

### 6-0. 진입 조건 (MANDATORY Gate)

> 🚫 **절대 금지**: Phase 5의 유저 전략 선택 없이 Phase 6 진입.

진입 전 체크:
1. `.wrxp/state/strategy-{slug}.json` 파일이 존재하는가?
2. 존재하지 않으면 → Phase 5로 되돌아가 `AskUserQuestion` 4지선다 제시
3. 유저 응답 수신 후 strategy 파일 생성 완료 시에만 Phase 6 진행

### 6-1. DAG 기반 병렬 실행

```
반복:
  1. DAG에서 의존성 해소된 태스크 추출
  2. 전부 병렬 Agent 스폰
  3. Wave 완료 대기
  4. 다음 wave 실행
until 모든 리프 노드 완료
```

### 6-2. 에이전트 신뢰도 피드백

태스크 완료 후 결과물 검증:
1. critic 또는 verifier 에이전트가 결과물 검토
2. **다수결** 기반 판정
3. **동률 시 critic 우세** (비평적 관점이 품질 보장에 유리)
4. 신뢰도 낮으면 → 해당 에이전트에게 재작업 지시

### 6-3. 에스컬레이션 정책

| 상황 | 처리 방식 |
|------|---------|
| 크리티컬 설계 미스 발견 | `AskUserQuestion`으로 유저에게 즉시 질문 |
| 태스크 실패 | 유저 에스컬레이션 (자동 재시도 없음) |
| 일반 이슈 | 에이전트 자체 해결 |

### 6-4. 실행 상태 기록

파일 저장: `.wrxp/state/execution-{slug}.json`

```json
{
  "tasks": {
    "1.1": { "status": "completed", "agent": "executor", "confidence": 0.92 },
    "1.2": { "status": "in_progress", "agent": "executor" },
    "2.1": { "status": "pending", "depends_on": ["1.1", "1.2"] }
  }
}
```

---

## Phase 7 — 결과 통합 (Result Integration)

1. 모든 에이전트 결과물 수집
2. 메인 Opus는 **요약만** 유저에게 전달 (컨텍스트 보호)
3. 상세 결과는 에이전트 출력에 존재

---

## 상태 파일 구조

```
.wrxp/state/
├── intent-{slug}.md          # Phase 1: 정제된 의도
├── tree-{slug}.json          # Phase 2: 분해 트리
├── plan-{slug}.md            # Phase 3: writing-plans 수준 상세 기획
├── dag-{slug}.json           # Phase 4: 에이전트 매칭 + DAG
├── strategy-{slug}.json      # Phase 5: 유저 선택 실행 전략
├── execution-{slug}.json     # Phase 6: 실행 상태
└── breakdown-{slug}.json     # 전체 파이프라인 상태 (진행률, 에러)
```

`{slug}` = 요청 내용 기반 짧은 식별자 (예: `add-social-login`)

---

## 컴포저블 사용법

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/breakdown "요청"` | Phase 1-7 전체 | 전체 자율 실행 원할 때 |
| `/decompose "문제"` | Phase 1+2만 | 분해 트리만 보고 싶을 때 |
| `/agent-match "태스크 목록"` | Phase 4만 | 이미 분해된 태스크에 에이전트 매칭할 때 |

---

## Quick Reference

```
유저 요청
  -> Phase 1: middleware 스캔 + AskUserQuestion 모호성 제거 → intent-{slug}.md
  -> Phase 2: 재귀 분해 + 트리 시각화 + 유저 승인 → tree-{slug}.json
  -> Phase 3: writing-plans 수준 상세 기획 → plan-{slug}.md
  -> Phase 4: 에이전트 매칭 + middleware 지식 주입 + DAG → dag-{slug}.json
  -> Phase 5: 4가지 전략 옵션 AskUserQuestion → strategy-{slug}.json
  -> Phase 6: 병렬 실행 (Wave) + 신뢰도 검증 + 에스컬레이션 → execution-{slug}.json
  -> Phase 7: 요약 전달
```

---

## Common Mistakes

| 실수 | 올바른 방법 |
|------|-----------|
| **Phase 3 (Plan Writing) 건너뛰고 바로 Phase 4** | **분해 트리 승인 후 plan-{slug}.md 작성 필수** |
| **No-Placeholder 규칙 무시** | **"TBD", "적절한 처리" 등 금지 패턴 스캔** |
| **Phase 5 (Strategy Selection) 건너뛰고 바로 Phase 6** | **strategy-{slug}.json 생성 후에만 Phase 6 진입** |
| **전략 선택을 평문으로 질문** | **반드시 `AskUserQuestion` 4지선다로 제시** |
| 메인 AI가 직접 코드를 읽고 분석 | 탐색은 explore 에이전트에게 위임 |
| 여러 질문을 한꺼번에 | AskUserQuestion은 한 번에 하나씩 |
| 실패 시 자동 재시도 | 즉시 유저 에스컬레이션 |
| 분해 없이 바로 에이전트 스폰 | Phase 2 분해 트리 + 유저 승인 필수 |
| middleware 지식 없이 에이전트 실행 | Phase 4에서 Do 지식 반드시 주입 |
