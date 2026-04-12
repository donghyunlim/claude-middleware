---
name: ctx
description: "Graphiti KG에서 프로젝트 컨텍스트를 주입하고 충돌을 감지한다. /middleware:ctx 또는 /ctx 로 호출."
schema_version: "0.2"
allowed-tools: [mcp__graphiti__search_memory_facts, mcp__graphiti__search_nodes, mcp__graphiti__get_episodes, Glob, Read]
argument-hint: "[작업 설명 또는 빈칸]"
---

# /ctx — Middleware Context Injection (Graphiti KG)

Graphiti 지식 그래프에서 프로젝트 컨텍스트를 조회하고 작업 충돌을 감지한다.

## Step 0: group_id 결정

1. `.middleware/manifest.yaml` 파일을 읽는다.
2. `group_id` 필드가 있으면 그 값을 사용한다.
3. 없으면 현재 디렉토리 이름을 snake_case로 변환하여 group_id로 사용한다.
4. 이하 모든 Graphiti 쿼리에서 `group_ids: ["<결정된 group_id>"]`를 사용한다.

## 실행 모드

### 모드 A: 부트스트랩 (`/ctx` — 인자 없음)

아래 두 쿼리를 **병렬**로 실행한다.

**쿼리 1 — 아키텍처 원칙/제약 조회:**
```
mcp__graphiti__search_memory_facts(
  query="아키텍처 원칙 제약사항 설계 결정",
  group_ids=["<group_id>"]
)
```

**쿼리 2 — 모듈 구조 조회:**
```
mcp__graphiti__search_nodes(
  query="모듈 구조 컴포넌트",
  group_ids=["<group_id>"]
)
```

결과를 다음 형식으로 출력한다 (전체 3KB 이내):

```
## 프로젝트 컨텍스트 — <group_id>

### 활성 원칙
- [facts 결과에서 추출한 아키텍처 원칙 목록]

### 제약사항
- [facts 결과에서 추출한 제약/금지 항목 목록]

### 모듈 구조
- [nodes 결과에서 추출한 주요 모듈/컴포넌트]
```

---

### 모드 B: 컨텍스트 + 충돌 감지 (`/ctx "작업 설명"` — 인자 있음)

**Step 1:** 모드 A의 부트스트랩을 먼저 수행한다.

**Step 2:** 인자에서 핵심 키워드를 추출한다.

**Step 3:** 추출한 키워드로 추가 쿼리 **두 개를 병렬** 실행한다.

**쿼리 3 — 관련 노드 조회:**
```
mcp__graphiti__search_nodes(
  query="[추출한 키워드]",
  group_ids=["<group_id>"]
)
```

**쿼리 4 — 설계 결정/제약 조회:**
```
mcp__graphiti__search_memory_facts(
  query="[추출한 키워드] 설계 결정 제약 금지",
  group_ids=["<group_id>"]
)
```

**Step 4:** 쿼리 4 결과에서 충돌 관계 타입을 검사한다.
- `IS_PROHIBITED_IN` — 금지된 패턴
- `MUST_VIA` — 반드시 경유해야 하는 경로
- `CONSTRAINS` — 제약을 부과하는 관계
- `REQUIRES_NOT_MODIFY` — 수정 금지
- `REQUIRES_NOT_DIRECTLY_MODIFY` — 직접 수정 금지
- `REQUIRES_FILTER` — 필수 필터 적용

충돌이 감지되면 `⚠️ 충돌 감지됨` 블록을 포함한다.

**Step 5:** 결과를 다음 형식으로 출력한다 (전체 3KB 이내):

```
## 프로젝트 컨텍스트 — <group_id>

### 활성 원칙
- [부트스트랩에서 추출]

### 제약사항
- [부트스트랩에서 추출]

---

## 작업 컨텍스트: "[인자로 받은 작업 설명]"

### 관련 모듈
- [쿼리 3 결과]

### 존중해야 할 설계 결정
- [쿼리 4 결과에서 추출한 설계 결정]

### 따라야 할 제약
- [쿼리 4 결과에서 추출한 제약 사항]

[충돌이 있을 경우에만:]
⚠️ 충돌 감지됨
- [충돌 내용]: [관계 타입] — [근거]
```

---

## 출력 규칙

- 모든 응답은 **한국어**로 출력한다.
- 총 출력은 **3KB 이내**로 유지한다.
- 조회 결과가 없으면 "관련 정보 없음"으로 표기한다.
- 충돌이 없으면 충돌 섹션은 생략한다.
- `expired_at`이 설정된 팩트는 무효화된 것이므로 제외한다.
