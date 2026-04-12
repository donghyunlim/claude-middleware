---
name: init
description: "새 프로젝트에 .middleware/ 초기화 + Graphiti KG 시드. 원커맨드 셋업."
schema_version: "0.2"
allowed-tools: [Read, Write, Glob, Grep, Bash, mcp__graphiti__add_memory, mcp__graphiti__search_nodes, mcp__graphiti__get_status, AskUserQuestion]
argument-hint: "[group_id (선택)]"
---

# /middleware:init — 프로젝트 미들웨어 초기화

새 프로젝트에 `.middleware/`를 생성하고 Graphiti KG에 초기 지식을 시드한다.

## 전제 조건 확인

1. Graphiti MCP 서버 연결 확인: `mcp__graphiti__get_status()` 호출
   - 실패 시: "Graphiti MCP 서버가 연결되지 않았습니다. MCP 설정을 확인하세요." 출력 후 종료
2. `.middleware/` 이미 존재하는지 Glob으로 확인
   - 존재 시: `AskUserQuestion`으로 "이미 .middleware/가 있습니다. 덮어쓸까요?" 질문
   - "아니오" 선택 시 종료

## Step 1: group_id 결정

- 인자로 group_id가 주어지면 그대로 사용
- 없으면 현재 디렉토리 이름을 snake_case로 변환 (예: `my-project` → `my_project`)

## Step 2: 프로젝트 스캔

**병렬로** 다음 정보를 수집한다:

**2-1. Git 히스토리:**
```bash
git log --oneline -20
```

**2-2. 프로젝트 구조:**
```bash
ls -la  # 루트 파일 목록
```
주요 설정 파일 확인: package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod 등

**2-3. 주요 디렉토리:**
```
Glob("**/")  # 1단계 디렉토리 구조
```

**2-4. 기존 컨텍스트 파일:**
- CLAUDE.md, AGENTS.md, .cursorrules 등이 있으면 읽어서 참고

## Step 3: .middleware/ 생성

수집한 정보를 바탕으로 3개 파일을 생성한다.

**manifest.yaml:**
```yaml
version: '0.2'
phase: 4
created: '<오늘 날짜>'
updated: '<오늘 날짜>'
backend: graphiti
group_id: '<결정된 group_id>'
schemas:
  rules: '0.1'
  context: '0.1'
```

**context.yaml:**
Step 2에서 수집한 정보를 바탕으로 작성:
```yaml
version: '0.1'
project:
  name: <프로젝트 이름>
  description: <git log + 구조에서 추론한 1-2문장 설명>
architecture:
  style: <감지된 아키텍처 스타일>
  overview: <디렉토리 구조 기반 개요>
  principles: []  # 초기에는 비워둠 — KG에서 점진적으로 채워짐
tech_stack:
  <감지된 기술 스택>
constraints: []  # 초기에는 비워둠
```

**rules.yaml:**
```yaml
version: "0.1"
rules: []  # 초기에는 비워둠 — 유저가 필요시 추가
```

## Step 4: Graphiti KG 시드

생성된 context.yaml의 내용을 Graphiti에 에피소드로 적재한다.

**에피소드 1: 프로젝트 개요**
```
mcp__graphiti__add_memory(
  name="프로젝트 개요: <프로젝트 이름>",
  episode_body="<context.yaml의 project.description + architecture.overview를 자연어로>",
  group_id="<group_id>",
  source="text",
  source_description="middleware init scan"
)
```

**에피소드 2: 기술 스택 + 구조** (Step 2에서 수집한 정보)
```
mcp__graphiti__add_memory(
  name="기술 스택과 프로젝트 구조",
  episode_body="<tech stack + 주요 디렉토리 구조 + 설정 파일 정보를 자연어로>",
  group_id="<group_id>",
  source="text",
  source_description="middleware init scan"
)
```

**에피소드 3: 최근 개발 활동** (git log 기반)
```
mcp__graphiti__add_memory(
  name="최근 개발 활동",
  episode_body="<git log -20의 커밋 메시지를 요약한 자연어 텍스트>",
  group_id="<group_id>",
  source="text",
  source_description="git history scan"
)
```

CLAUDE.md나 AGENTS.md가 존재하면 **에피소드 4**로 추가:
```
mcp__graphiti__add_memory(
  name="기존 프로젝트 지침",
  episode_body="<CLAUDE.md/AGENTS.md 핵심 내용 요약>",
  group_id="<group_id>",
  source="text",
  source_description="existing project instructions"
)
```

## Step 5: 결과 보고

```
✅ middleware 초기화 완료

📁 .middleware/
  ├── manifest.yaml  (backend: graphiti, group_id: <group_id>)
  ├── context.yaml   (프로젝트 개요 + 아키텍처)
  └── rules.yaml     (빈 상태 — 필요시 추가)

🧠 Graphiti KG (<group_id>)
  - 에피소드 N개 시드 완료 (백그라운드 처리 중, 3-5분 후 검색 가능)

🔗 다음 단계:
  - /middleware:ctx 로 컨텍스트 조회
  - git commit 시 자동으로 KG 갱신 (post-commit hook 자동 설치됨)
  - 설계 결정이나 제약이 생기면 /middleware:ctx 로 확인 후 작업
```

## 주의사항

- Graphiti 에피소드는 비동기 처리 (3-5분 소요). 즉시 검색 안 될 수 있음.
- context.yaml은 인간이 읽는 참고용. 실제 AI 컨텍스트는 Graphiti KG에서 조회.
- group_id에 하이픈(-) 사용 금지. underscore(_) 사용.
- 모든 출력은 한국어.
