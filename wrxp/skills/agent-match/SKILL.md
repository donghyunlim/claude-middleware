---
name: agent-match
description: 태스크에 최적 에이전트를 동적 매칭하고 의존성 DAG를 구성하여 실행 계획 출력
argument-hint: "[태스크 목록 또는 tree JSON 경로]"
level: 4
---

# agent-match

## Overview

분해된 태스크 목록(또는 트리)을 받아, 각 태스크에 최적의 에이전트를 동적으로 매칭하고, 의존성 DAG를 구성하여 실행 계획을 출력하는 스킬.

breakdown의 Phase 4를 독립 스킬로 분리한 것. 독립 사용과 breakdown 내부 호출 모두 지원.

---

## Step 1 — Input Parsing

입력 형식을 감지하여 리프 노드(실행 가능 태스크)만 추출한다.

| 입력 형식 | 처리 방법 |
|----------|---------|
| `.wrxp/state/tree-{slug}.json` 경로 | JSON 파일 읽기 → 리프 노드 추출 |
| 직접 텍스트 태스크 목록 | 번호/bullet 파싱 → 태스크 목록화 |
| 자유 형식 텍스트 | AI가 구조 추론 → 태스크 목록화 |

**리프 노드 추출 규칙:**
- `children`이 없거나 빈 배열인 노드만 추출
- 각 리프에는 `id`, `label`, `parent_path` 포함

---

## Step 2 — Task Analysis

각 리프 태스크에 대해 4가지 차원을 분석한다.

| 차원 | 가능한 값 | 설명 |
|-----|---------|------|
| **유형** | `design` / `implement` / `review` / `research` / `test` / `debug` / `ui` | 태스크의 성격 |
| **복잡도** | `simple` / `standard` / `complex` | 난이도 |
| **도메인** | `backend` / `frontend` / `infra` / `data` / `docs` | 영역 |
| **검증 필요** | `true` / `false` | 교차 검증이 필요한지 |

분석 결과를 각 태스크 메타데이터에 기록한다.

---

## Step 3 — Dynamic Agent Selection

> **하드코딩 금지**: 에이전트 목록을 미리 테이블로 고정하지 않는다. 매 실행마다 현재 사용 가능한 에이전트를 동적으로 탐색하여 최적 조합을 결정한다.

**에이전트 탐색 루틴** (매 실행마다 수행):
1. Agent tool의 available `subagent_type` 목록을 확인
2. 각 에이전트의 description과 역할을 읽어 파악
3. Step 2에서 분석한 태스크 특성(유형/복잡도/도메인)과 대조
4. 가장 적합한 에이전트를 선택 — 복잡도에 따라 모델 티어도 동적 결정

**선택 원칙:**
- 태스크 유형에 맞는 전문 에이전트를 우선 선택 (설계→architect 계열, 구현→executor 계열 등)
- 복잡도가 높으면 상위 모델(Opus), 단순하면 하위 모델(Haiku) 활용
- 교차 검증이 필요하면 비평/검증 에이전트를 추가 배정

**검증 필요 시 추가 에이전트:**
- 비평 관점의 에이전트 (critic 계열)
- 정합성 확인 에이전트 (verifier 계열)

**신뢰도 판정 규칙:**
- 다수결 기반
- 동률 시 critic이 우세

---

## Step 4 — Middleware Knowledge Injection

관련 middleware 지식을 각 에이전트의 프롬프트에 주입할 내용을 준비한다.

**주입할 지식 유형:**

| 유형 | 소스 | 주입 내용 |
|-----|------|---------|
| `features` | `.middleware/features.yaml` | 해당 모듈의 `purpose`, `status` |
| `domain_knowledge` | `.middleware/features.yaml` | `topic`, `summary` — 해당 태스크 관련만 |
| `design_decisions` | `.middleware/features.yaml` | `title`, `decision`, `rationale` — `accepted` 상태만 |

**주입 방식:**
- 에이전트 프롬프트의 컨텍스트 섹션에 삽입
- 태스크별로 관련 지식만 선택적으로 포함
- 관련 없는 모듈의 지식은 주입하지 않음

**middleware_context 참조 형식:**
```
{feature-slug}:domain_knowledge:{topic-name}
{feature-slug}:design_decisions:{decision-title}
{feature-slug}:features:{module-name}
```

---

## Step 5 — DAG Construction

태스크 간 의존성을 분석하여 DAG를 구성한다.

**의존성 판단 규칙:**

| 조건 | 관계 |
|-----|------|
| 같은 파일을 수정하는 태스크 | 순차 (depends_on) |
| 타입 정의 → 해당 타입 사용 코드 | 순차 |
| 서로 다른 모듈의 독립 작업 | 병렬 (같은 wave) |
| review/test → 구현 완료 후 | 구현 태스크에 depends_on |

**DAG JSON 스키마:**
```json
{
  "slug": "feature-slug",
  "waves": [
    {
      "wave": 1,
      "tasks": [
        {
          "id": "1.1",
          "label": "태스크 설명",
          "agent": "architect",
          "agent_model": "opus",
          "middleware_context": [
            "feature-slug:domain_knowledge:topic-1"
          ],
          "depends_on": []
        }
      ]
    },
    {
      "wave": 2,
      "tasks": [
        {
          "id": "2.1",
          "label": "태스크 설명",
          "agent": "executor",
          "agent_model": "sonnet",
          "middleware_context": [],
          "depends_on": ["1.1"]
        }
      ]
    }
  ]
}
```

**Wave 기반 스케줄링:**
- 같은 wave의 태스크는 모두 병렬 실행
- wave N 전체 완료 → wave N+1 시작

---

## Step 6 — Execution Plan Output

**저장:**
- DAG JSON: `.wrxp/state/dag-{slug}.json`

**유저에게 표시할 실행 계획 요약 형식:**

```
== Execution Plan ==
Wave 1 (병렬 N개):
  [1.1] 태스크 레이블 → agent (Model)
  [1.2] 태스크 레이블 → agent (Model)

Wave 2 (병렬 N개, Wave 1 의존):
  [2.1] 태스크 레이블 → agent (Model) + verifier
  [2.2] 태스크 레이블 → agent (Model)

Wave 3 (순차, Wave 2 의존):
  [3.1] 태스크 레이블 → agent (Model) + critic
```

**추가 에이전트가 있는 경우** `+ verifier`, `+ critic` 등으로 표기.

---

## 독립 사용 vs breakdown 호출

### 독립 사용
```
/agent-match "태스크 목록"
```
- 매칭 결과와 DAG를 출력하고 종료
- 유저가 검토 후 수동 실행하거나 breakdown으로 이어서 사용

### breakdown에서 내부 호출
- breakdown이 Phase 4에서 이 스킬의 로직을 사용
- decompose 출력물 (`tree-{slug}.json`)을 입력으로 받음
- DAG 저장 후 breakdown이 Phase 6(실행)로 진행

---

## Common Mistakes

| 실수 | 해결책 |
|-----|-------|
| 중간 노드(부모)를 태스크로 포함 | 리프 노드만 추출 (Step 1) |
| 모든 태스크에 동일 모델 적용 | 복잡도 기반 모델 분기 (Step 3) |
| middleware 지식 전체 주입 | 해당 태스크와 관련된 것만 선택적 주입 (Step 4) |
| 독립 태스크를 순차로 구성 | 모듈 경계 기준 병렬 wave 편성 (Step 5) |
| slug 불일치 | tree JSON 파일명에서 slug 추출하여 dag 파일명에 동일 사용 |
