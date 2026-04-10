---
name: decompose
description: 의도 정제 + 재귀적 문제 분해. 모호한 요청을 명확한 태스크 트리로 변환
argument-hint: "[분해할 문제나 요청]"
level: 4
---

# Decompose Skill

유저의 요청에서 의도를 정제하고, 문제를 재귀적으로 분해하여 실행 가능한 태스크 트리를 출력한다.

**독립 사용**: `/decompose "문제"` → 분해 트리 출력 후 종료  
**breakdown 내부 호출**: `/breakdown`의 Phase 1+2로 사용

---

## Step 1 — 프로젝트 컨텍스트 수집

### Case A: `.middleware/` 존재 시 (Middleware Mode)

explore 에이전트로 `.middleware/features.yaml`을 빠르게 스캔한다.

1. `.middleware/features.yaml` 전체 구조 확인
2. 유저 요청과 관련된 feature/module만 선택적으로 읽기
   - 관련성이 불분명하면 전체 스캔으로 확대 (과감하게)
3. 관련 feature에서 Do 중심 지식 추출:
   - `domain_knowledge`: topic, summary
   - `design_decisions`: title, decision, rationale (status: accepted 만)
   - `features`: purpose, status
4. 추출한 지식을 이후 단계에서 의도 정제와 분해에 반영
5. 추가 확인이 필요하면 언제든 middleware를 적극적으로 재확인

### Case B: `.middleware/` 부재 시 (Code Search Mode)

middleware가 없는 프로젝트에서는 코드 서치 모드로 전환한다.

1. `git log --oneline -30` 으로 최근 커밋 히스토리를 살펴 프로젝트가 어떤 것인지 대략 파악
2. 프로젝트 루트의 구조 확인 (디렉토리 목록, package.json, requirements.txt 등)
3. explore 에이전트로 유저 요청과 관련된 코드 영역을 직접 탐색
   - Glob/Grep으로 관련 파일 찾기
   - 주요 엔트리포인트와 모듈 구조 파악
4. 수집한 코드 컨텍스트를 middleware 지식 대신 활용
5. 비용이 더 들지만 정확한 이해를 위해 적극적으로 코드를 읽는다

---

## Step 2 — Intent Clarification

유저 요청에서 모호한 부분을 식별하고 질문으로 제거한다.

### 모호성 식별 기준

- 유저가 확실하다고 생각하지만 AI 관점에서 모호한 것
- 조금 생각해보면 여러 해석이 가능한 것
- Step 1의 middleware 지식과 조합했을 때 드러나는 불확실성

### 질문 방식

AskUserQuestion 도구를 사용한다:
- 한 번에 하나의 질문만
- 가능하면 선택지(options) 제공
- multiSelect가 적절한 경우 활용
- 모호성이 충분히 제거될 때까지 반복

**Soft cap: 5회 / Hard cap: 10회**

### 출력

정제된 의도를 `.wrxp/state/intent-{slug}.md`에 저장:

```markdown
# Intent: {slug}

## 정제된 의도
{명확해진 유저의 의도}

## 유저 답변 요약
- Q: {질문}
  A: {답변}

## 관련 Middleware 컨텍스트
{Step 1에서 추출한 관련 지식}
```

slug는 요청의 핵심 키워드를 kebab-case로 변환하여 생성한다.  
예: "소셜 로그인 추가" → `social-login`

---

## Step 3 — Recursive Decomposition

정제된 의도를 서브태스크 트리로 재귀적으로 분해한다.

### 단일 태스크 판단 (fast-path)

정제된 의도가 이미 단일 에이전트로 완료 가능한 크기라면, **분해를 스킵**한다.
- 단일 노드 트리(`root` = 리프)를 생성하고 Step 4(시각화/승인)도 스킵
- 바로 Step 5(출력)로 진행
- breakdown에서 호출 시: Phase 3(agent-match) 이후 단계는 그대로 수행

### 분해 규칙

분해가 필요한 경우:

1. 의도를 최상위 서브태스크들로 분해
2. 각 서브태스크에 대해 리프 노드 기준 판단:
   - 단일 에이전트가 독립적으로 완료 가능한가?
   - 입력과 출력이 명확한가?
   - 다른 태스크와의 의존성이 식별 가능한가?
3. 기준을 충족하지 못하면 → 재귀적으로 더 분해
4. 무한 깊이 허용 — Opus가 조율만 하므로 깊이 걱정 불필요

### 노드 메타데이터

각 노드에 포함:
- `id`: 계층 번호 (`1`, `1.1`, `1.1.2` 등)
- `label`: 서브태스크 한 줄 제목
- `description`: 무엇을 해야 하는지 간결한 설명
- `is_leaf`: 더 이상 분해되지 않는 실행 단위 여부
- `children`: 자식 노드 id 목록

---

## Step 4 — Tree Visualization

분해 결과를 텍스트 트리로 유저에게 시각화한다.

```
[루트] {원래 요청}
├── [1] {서브태스크 1}
│   ├── [1.1] {리프 태스크}
│   └── [1.2] {리프 태스크}
├── [2] {서브태스크 2}
│   └── [2.1] {리프 태스크}
└── [3] {서브태스크 3}
```

각 노드에 간단한 설명을 한 줄로 첨부한다.

### 유저 승인

AskUserQuestion으로 트리 승인을 요청한다:

**질문**: "이 분해 트리로 진행할까요?"  
**옵션**: `승인`, `수정 필요`

- `승인` → Step 5로 진행
- `수정 필요` → 어떤 부분을 어떻게 바꾸길 원하는지 피드백 수집 후 트리 조정, 다시 Step 4로

---

## Step 5 — Output

승인된 분해 트리를 `.wrxp/state/tree-{slug}.json`에 저장한다.

### JSON 구조

```json
{
  "slug": "social-login",
  "root": "소셜 로그인 추가",
  "intent": "Google과 Kakao OAuth를 백엔드 세션과 연동하여 프론트엔드 UI까지 완성",
  "nodes": [
    {
      "id": "1",
      "parent": null,
      "label": "OAuth 프로바이더 설정",
      "description": "Google, Kakao OAuth 클라이언트 자격증명 설정",
      "is_leaf": false,
      "children": ["1.1", "1.2"]
    },
    {
      "id": "1.1",
      "parent": "1",
      "label": "Google OAuth 클라이언트 설정",
      "description": "Google Cloud Console에서 OAuth 2.0 클라이언트 ID 생성 및 환경변수 설정",
      "is_leaf": true,
      "children": []
    },
    {
      "id": "1.2",
      "parent": "1",
      "label": "Kakao OAuth 클라이언트 설정",
      "description": "Kakao Developers에서 앱 등록 및 REST API 키 환경변수 설정",
      "is_leaf": true,
      "children": []
    }
  ]
}
```

### 독립 사용 시 종료

`/decompose "문제"` 단독 호출이면 여기서 종료하고 다음을 안내한다:

```
분해 트리가 저장되었습니다: .wrxp/state/tree-{slug}.json

이어서 진행하려면:
  /agent-match  — 각 태스크에 최적 에이전트 매칭
  /breakdown    — 전체 파이프라인 (분해 → 매칭 → 실행)
```

### breakdown에서 호출 시

분해 트리를 저장한 뒤 `/breakdown`의 Phase 3(agent-match)으로 제어를 반환한다.  
출력 경로는 동일한 `.wrxp/state/` 디렉토리를 사용한다.

---

## Common Mistakes

| 실수 | 올바른 방법 |
|------|-----------|
| middleware 스캔 없이 바로 분해 | Step 1에서 반드시 관련 feature 확인 후 분해 |
| 리프 노드가 너무 큼 (여러 에이전트 필요) | 단일 에이전트가 독립 완료 가능한 크기까지 분해 |
| 유저 승인 없이 분해 트리 확정 | Step 4에서 반드시 AskUserQuestion으로 승인 |
| 여러 질문을 한꺼번에 | AskUserQuestion은 한 번에 하나씩 |
| 불필요하게 깊은 분해 | 일반적으로 2-4 레벨이면 충분, 5 이상이면 분해 전략 재검토 |
