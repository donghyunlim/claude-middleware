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

## Step 2 — Intent Clarification (Deep Reasoning + AskUserQuestion)

유저 요청에서 모호한 부분을 식별하고 질문으로 제거한다. 이 Step은 **Pre-Q Deep Reasoning → AskUserQuestion 강제 질문 → Post-Q Integration Reasoning** 의 세 서브스텝으로 구성된다.

### Step 2A — Pre-Q Deep Reasoning

> **Canonical source**: `${CLAUDE_PLUGIN_ROOT}/shared/reasoning-framework.md`
> 질문을 생성하기 전에 반드시 9가지 원칙으로 의도를 심층 분석한다. 이 reasoning이 완료되기 전에는 **절대 질문을 생성하지 않는다** (Response Inhibition).

Read `${CLAUDE_PLUGIN_ROOT}/shared/reasoning-framework.md` and apply all 9 principles to the user's request in the context of intent clarification:

1. Logical Dependencies & Constraints  2. Risk Assessment  3. Abductive Reasoning & Hypothesis Exploration
4. Outcome Evaluation & Adaptability  5. Information Availability  6. Precision & Grounding
7. Completeness  8. Persistence & Patience  9. Response Inhibition ← reasoning 완료 전 행동 금지

각 원칙을 **의도 정제** 관점에서 적용한다:
- Logical Dependencies → 요청의 암묵적 전제조건과 실행 순서
- Risk Assessment → 의도 오해 시 파급효과 (되돌릴 수 없는 행동은 HIGH risk → 사전 질문 필수)
- Abductive Reasoning → 숨은 의도 가설 수립 (표면 너머의 실제 목표)
- Information Availability → 프로젝트 컨텍스트 + `.middleware/` + 대화 히스토리 (유저 질문은 최후의 수단)
- Response Inhibition → 🚫 reasoning 없이 즉시 AskUserQuestion 호출 금지. ✅ 9원칙 산출물을 "모호성 목록"으로 도출한 뒤에만 질문 단계 진입

**출력 형식:**

```
🧠 Pre-Q Deep Reasoning 결과

📋 Logical Dependencies: [분석]
⚠️ Risk Assessment: [분석]
🔬 Hypothesis Exploration: [숨은 의도 가설들]
📚 Information Sources: [참조한 컨텍스트]
🎯 Identified Ambiguities: [번호 매긴 모호성 목록 — 다음 Step 2B의 질문 재료]
```

---

### Step 2B — AskUserQuestion 강제 질문

> ⚠️ **MANDATORY RULE**: Step 2A에서 도출된 모호성을 해소하기 위한 **모든 질문**은
> 반드시 **`AskUserQuestion` 도구**로만 수행한다.
>
> 🚫 **절대 금지**:
> - 평문(plain text)으로 "~할까요?", "~하시겠어요?" 등 서술형 질문
> - 유저 응답을 그냥 기다리는 free-form 질문
> - 여러 질문을 markdown 리스트로 나열 후 응답 기다리기
>
> ✅ **유일하게 허용**:
> - `AskUserQuestion({questions: [...]})` 도구 호출

#### 모호성 식별 기준

- 유저가 확실하다고 생각하지만 AI 관점에서 모호한 것
- 조금 생각해보면 여러 해석이 가능한 것
- Step 1의 middleware 지식과 조합했을 때 드러나는 불확실성
- Step 2A의 9원칙 분석으로 도출된 모호성 목록

#### 질문 방식

**원칙:**
- 한 번에 하나의 질문만 (`questions` 배열 길이 권장 1, 최대 4)
- 가능하면 `options` 제공
- `multiSelect`가 적절한 경우 활용
- 모호성이 충분히 제거될 때까지 반복

**Soft cap: 5회 / Hard cap: 10회**

**✅ 올바른 사용 예시:**

```
AskUserQuestion({
  questions: [{
    question: "소셜 로그인은 어떤 프로바이더를 지원할까요?",
    header: "프로바이더",
    multiSelect: true,
    options: [
      { label: "Google", description: "Google OAuth 2.0" },
      { label: "Kakao", description: "Kakao REST API" },
      { label: "Naver", description: "Naver OAuth" }
    ]
  }]
})
```

**❌ 잘못된 사용 예시 (절대 금지):**

```
❌ "소셜 로그인은 어떤 프로바이더를 지원할까요? Google, Kakao, Naver 중에
    선택해 주세요."  ← 평문 질문, 유저 응답 대기 (금지)

❌ 다음 내용을 확인해 주세요:
   1. 프로바이더는?
   2. 세션 저장 방식은?
   3. 토큰 갱신 주기는?     ← markdown 리스트 나열 (금지)
```

---

### Step 2C — Post-Q Integration Reasoning

> Step 2B에서 답변을 수집한 후, `intent-{slug}.md` 파일로 저장하기 전에 답변들을 통합 검증한다.

**체크리스트:**

1. **Completeness 재검증** — Step 2A에서 도출한 모호성 목록의 모든 항목이 해소되었는가?
2. **Consistency 검증** — 답변들 사이에 논리적 모순이 없는가?
3. **암묵적 가정 재확인** — 답변을 받고 나서 새롭게 드러난 모호성이 있는가?
4. **추가 질문 판단** — 해소되지 않은 것이 있고 Soft cap(5회) 이내라면 **Step 2B로 돌아가 추가 질문 생성** (Hard cap 10회 초과 금지)
5. **통과 시** → Step 3 (Recursive Decomposition)로 진행

**출력 형식:**

```
🔁 Post-Q Integration Reasoning

✅ Completeness: [해소된 모호성 / 남은 모호성]
✅ Consistency: [답변 간 모순 여부]
🎯 Final Intent: [통합된 정제 의도]
🚦 Decision: [Step 3 진행 / Step 2B 재호출]
```

---

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
- breakdown에서 호출 시: Phase 4(agent-match) 이후 단계는 그대로 수행

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

분해 트리를 저장한 뒤 `/breakdown`의 Phase 4(agent-match)으로 제어를 반환한다.  
출력 경로는 동일한 `.wrxp/state/` 디렉토리를 사용한다.

---

## Common Mistakes

| 실수 | 올바른 방법 |
|------|-----------|
| **평문으로 질문 (예: "어떤 방식을 원하시나요?")** | **반드시 `AskUserQuestion` 도구 사용** |
| **Step 2A reasoning 건너뛰고 즉시 질문** | **Pre-Q Deep Reasoning 9원칙 완료 후에만 질문** |
| **답변 받고 곧바로 intent 문서 저장** | **Step 2C Post-Q Integration 체크 후 저장** |
| middleware 스캔 없이 바로 분해 | Step 1에서 반드시 관련 feature 확인 후 분해 |
| 리프 노드가 너무 큼 (여러 에이전트 필요) | 단일 에이전트가 독립 완료 가능한 크기까지 분해 |
| 유저 승인 없이 분해 트리 확정 | Step 4에서 반드시 AskUserQuestion으로 승인 |
| 여러 질문을 한꺼번에 | AskUserQuestion은 한 번에 하나씩 |
| 불필요하게 깊은 분해 | 일반적으로 2-4 레벨이면 충분, 5 이상이면 분해 전략 재검토 |
