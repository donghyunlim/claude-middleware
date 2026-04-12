---
name: middleware-ref
description: "프로젝트 미들웨어 지식을 읽어 표준 컨텍스트로 반환하는 어댑터. breakdown Phase 1이 내부적으로 사용."
schema_version: "0.2"
allowed-tools: [Read, Glob, Bash, mcp__graphiti__search_memory_facts, mcp__graphiti__search_nodes]
---

# middleware-ref — 프로젝트 지식 어댑터

프로젝트의 미들웨어 지식을 읽어서 **표준 컨텍스트 포맷**으로 반환한다.
breakdown Phase 1, decompose Step 1 등이 내부적으로 이 스킬의 절차를 따른다.

## Step 1: 백엔드 감지

`.middleware/manifest.yaml`을 Read로 읽는다.

- 파일 없음 → **Code Search Mode** (Step 4)
- `backend: graphiti` → **Graphiti Mode** (Step 2)
- `backend: yaml` 또는 backend 필드 없음 → **YAML Mode** (Step 3)

## Step 2: Graphiti Mode

manifest.yaml에서 `group_id`와 `queries` 섹션을 읽는다.

```yaml
# manifest.yaml 예시
group_id: commercial_insight
queries:
  architecture: "아키텍처 원칙 설계"
  constraints: "제약사항 금지 수정불가"
  decisions: "설계 결정 근거"
  dependencies: "모듈 의존성 의존"
  domain: "도메인 지식 데이터 품질"
```

`queries`의 각 항목에 대해 **병렬로** Graphiti 쿼리를 실행한다:

```
mcp__graphiti__search_memory_facts(
  query="<queries.architecture 값>",
  group_ids=["<group_id>"],
  max_facts=10
)
```

모든 쿼리의 결과를 **표준 컨텍스트 포맷** (Step 5)으로 조합한다.

**Graphiti 연결 실패 시**: 에러를 무시하고 Code Search Mode (Step 4)로 폴백.

## Step 3: YAML Mode

`.middleware/features.yaml`이 존재하면 읽어서 다음을 추출한다:
- `design_decisions` (status: accepted만)
- `domain_knowledge`
- `constraints`

`.middleware/context.yaml`이 존재하면 추가로 읽는다:
- `architecture.principles`
- `constraints`
- `tech_stack`

결과를 **표준 컨텍스트 포맷** (Step 5)으로 조합한다.

**features.yaml 없으면**: context.yaml만 읽거나 Code Search Mode로 폴백.

## Step 4: Code Search Mode

미들웨어가 없는 프로젝트용 폴백.

1. `git log --oneline -20` 으로 최근 히스토리 파악
2. 프로젝트 루트 구조 확인 (Glob으로 주요 파일 탐색)
3. CLAUDE.md, AGENTS.md, README.md 등 존재하면 읽어서 참고
4. 결과를 **표준 컨텍스트 포맷** (Step 5)으로 조합 (빈 항목은 `[]`)

## Step 5: 표준 컨텍스트 포맷

어떤 Mode든 최종 출력은 동일한 구조:

```
## 프로젝트 컨텍스트

### 아키텍처 원칙
- [수집된 원칙 목록. 없으면 "수집된 원칙 없음"]

### 제약사항
- [수집된 제약 목록. 없으면 "수집된 제약 없음"]

### 설계 결정
- [수집된 DD 목록. 없으면 "수집된 설계 결정 없음"]

### 모듈 의존성
- [수집된 의존성. 없으면 "수집된 의존성 없음"]

### 도메인 지식
- [수집된 도메인 지식. 없으면 "수집된 도메인 지식 없음"]

[Mode: Graphiti/YAML/CodeSearch, group_id: xxx]
```

**3KB 이내**로 유지한다. 팩트가 너무 많으면 가장 관련성 높은 것만 선별.

## 호출자별 사용법

- **breakdown Phase 1**: "middleware-ref 스킬의 절차를 따라 프로젝트 컨텍스트를 수집한다"
- **decompose Step 1**: 동일
- **직접 호출**: `/wrxp:middleware-ref` (디버깅/확인용)
