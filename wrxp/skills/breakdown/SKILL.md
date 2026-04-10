---
name: breakdown
description: Use when the user has a request that needs intent refinement, recursive decomposition, dynamic agent matching, and DAG-based parallel autonomous execution — the full orchestration pipeline.
argument-hint: "[요청 내용]"
level: 4
---

# breakdown

## Overview

유저의 요청을 받아 **5단계 파이프라인**으로 자율 실행하는 메인 오케스트레이터.

**핵심 철학**: 메인 AI(Opus)는 조율에만 집중한다. 코드 읽기, 분석, 실행은 전부 에이전트에게 위임하여 컨텍스트를 보호한다.

**컴포저블 구조**: `breakdown` = `decompose` (Phase 1+2) → `agent-match` (Phase 3) → 자율 실행 (Phase 4+5)

---

## Phase 1+2 — 의도 정제 + 재귀적 분해

> 이 Phase는 내부적으로 `/decompose` 스킬을 사용한다. 독립 사용 시 `/decompose "문제"` 직접 호출 가능.
> 질문 횟수 제한: Soft cap 5회 / Hard cap 10회 (decompose 스킬 기준 적용)

### 1-1. 프로젝트 컨텍스트 수집

**`.middleware/` 존재 시** (Middleware Mode):
1. `.middleware/features.yaml` 스캔 — 요청과 관련된 feature/module만 선택적으로 읽기
2. 관련 feature의 `domain_knowledge`, `design_decisions` 추출 (Do 중심)
   - **주입 대상**: features purpose/status, domain_knowledge topic+summary, design_decisions title+decision+rationale (accepted만)
3. 필요하면 언제든 전체 스캔으로 확대 (과감하게)

**`.middleware/` 부재 시** (Code Search Mode):
1. `git log --oneline -30`으로 프로젝트 히스토리 파악
2. 프로젝트 루트 구조 확인 (디렉토리, 설정 파일)
3. explore 에이전트로 관련 코드를 직접 탐색 (비용 증가 허용)

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

**단일 태스크 fast-path**: 정제된 의도가 이미 단일 에이전트로 완료 가능한 크기라면, 분해를 스킵하고 단일 노드 트리를 생성하여 바로 Phase 3로 진행. 나머지 단계(에이전트 매칭, 실행, 검증, 결과 통합)는 그대로 수행.

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

## Phase 3 — 에이전트 매칭 + DAG 구성 (Agent Matching)

> 이 Phase는 내부적으로 `/agent-match` 스킬을 사용한다. 독립 사용 시 `/agent-match "태스크 목록"` 직접 호출 가능.

### 3-1. 동적 에이전트 선택

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

### 3-2. Middleware Do 지식 주입

각 에이전트 프롬프트에 관련 middleware 지식 주입:
- `features`: 해당 모듈의 purpose, status
- `domain_knowledge`: topic, summary
- `design_decisions`: title, decision, rationale (accepted만)

### 3-3. DAG 구성

- 독립 태스크 → 병렬 실행 마킹
- 의존성 있는 태스크만 순차 관계 설정
- Wave 기반 스케줄링: 같은 레벨의 독립 태스크는 동시 실행

파일 저장: `.wrxp/state/dag-{slug}.json`

---

## Phase 4 — 자율 실행 (Autonomous Execution)

### 4-1. DAG 기반 병렬 실행

```
반복:
  1. DAG에서 의존성 해소된 태스크 추출
  2. 전부 병렬 Agent 스폰
  3. Wave 완료 대기
  4. 다음 wave 실행
until 모든 리프 노드 완료
```

### 4-2. 에이전트 신뢰도 피드백

태스크 완료 후 결과물 검증:
1. critic 또는 verifier 에이전트가 결과물 검토
2. **다수결** 기반 판정
3. **동률 시 critic 우세** (비평적 관점이 품질 보장에 유리)
4. 신뢰도 낮으면 → 해당 에이전트에게 재작업 지시

### 4-3. 에스컬레이션 정책

| 상황 | 처리 방식 |
|------|---------|
| 크리티컬 설계 미스 발견 | `AskUserQuestion`으로 유저에게 즉시 질문 |
| 태스크 실패 | 유저 에스컬레이션 (자동 재시도 없음) |
| 일반 이슈 | 에이전트 자체 해결 |

### 4-4. 실행 상태 기록

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

## Phase 5 — 결과 통합 (Result Integration)

1. 모든 에이전트 결과물 수집
2. 메인 Opus는 **요약만** 유저에게 전달 (컨텍스트 보호)
3. 상세 결과는 에이전트 출력에 존재

---

## 상태 파일 구조

```
.wrxp/state/
├── intent-{slug}.md          # Phase 1: 정제된 의도
├── tree-{slug}.json          # Phase 2: 분해 트리
├── dag-{slug}.json           # Phase 3: 에이전트 매칭 + DAG
├── execution-{slug}.json     # Phase 4: 실행 상태
└── breakdown-{slug}.json     # 전체 파이프라인 상태 (진행률, 에러)
```

`{slug}` = 요청 내용 기반 짧은 식별자 (예: `add-social-login`)

---

## 컴포저블 사용법

| 호출 | 실행 범위 | 사용 시점 |
|------|---------|---------|
| `/breakdown "요청"` | Phase 1-5 전체 | 전체 자율 실행 원할 때 |
| `/decompose "문제"` | Phase 1+2만 | 분해 트리만 보고 싶을 때 |
| `/agent-match "태스크 목록"` | Phase 3만 | 이미 분해된 태스크에 에이전트 매칭할 때 |

---

## Quick Reference

```
유저 요청
  -> Phase 1: middleware 스캔 + AskUserQuestion 모호성 제거 → intent-{slug}.md
  -> Phase 2: 재귀 분해 + 트리 시각화 + 유저 승인 → tree-{slug}.json
  -> Phase 3: 에이전트 매칭 + middleware 지식 주입 + DAG → dag-{slug}.json
  -> Phase 4: 병렬 실행 (Wave) + 신뢰도 검증 + 에스컬레이션 → execution-{slug}.json
  -> Phase 5: 요약 전달
```

---

## Common Mistakes

| 실수 | 올바른 방법 |
|------|-----------|
| 메인 AI가 직접 코드를 읽고 분석 | 탐색은 explore 에이전트에게 위임 |
| 여러 질문을 한꺼번에 | AskUserQuestion은 한 번에 하나씩 |
| 실패 시 자동 재시도 | 즉시 유저 에스컬레이션 |
| 분해 없이 바로 에이전트 스폰 | Phase 2 분해 트리 + 유저 승인 필수 |
| middleware 지식 없이 에이전트 실행 | Phase 3에서 Do 지식 반드시 주입 |
