---
name: brief
description: "Use for deep analysis of .middleware/ project knowledge — counter-questioning + work plan synthesis. Auto-detection handled by hook; invoke /middleware:brief for explicit deep mode."
schema_version: "0.2"
allowed-tools: [Read, Glob, Grep, Bash, Agent, AskUserQuestion]
---

# Middleware Brief Skill

Read `.middleware/` project knowledge to amplify user intent and produce accurate work plans.

## Mode Detection

1. Check if `.middleware/` directory exists in the working directory using Glob.
2. If `.middleware/` does NOT exist:
   - Tell the user: "이 프로젝트에 .middleware/가 없습니다. `bash init.sh`로 초기화하세요." and stop.
3. If `.middleware/` exists: run **Deep Analysis Workflow**.

## Deep Analysis Workflow: `/middleware:brief`

**Goal**: Full 5-phase workflow — context gathering, code reading, counter-questioning, plan synthesis, writing-plans transition.

### Phase 1 — Context Gathering

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/brief/relay-prompt.md` for the relay prompt template.
2. Spawn Relay Agent:
   ```
   Agent(
     model: "sonnet",
     description: "Middleware context relay",
     prompt: <relay-prompt.md contents> + "\n\n## User Message\n" + <user's message or /middleware:brief argument>
   )
   ```
3. Receive the briefing. Note the **Confidence Level**.
4. **If Relay Agent fails**: Fall back to direct YAML reading:
   - Read `.middleware/manifest.yaml`, `.middleware/features.yaml`, `.middleware/rules.yaml` directly
   - Run `git status --short` and `git log -5 --oneline`
   - Construct a manual briefing from the raw data

5. Show the user a brief status:
   > "Middleware 컨텍스트 로딩 완료. Confidence: {level}. {N}개 관련 feature 감지."

### Phase 2 — Selective Code Reading

1. From the relay briefing, extract `modules.paths` of all relevant features.
2. For each path pattern:
   - Use Glob to find matching files
   - Read key files (prioritize: entry points, main modules, types/interfaces)
   - Limit to ~5-10 most relevant files to avoid context bloat
3. Cross-reference code state with middleware knowledge:
   - Do anti-patterns appear in current code?
   - Are constraints being followed?
   - Are there recent changes that contradict design decisions?

### Phase 3 — Counter-Questioning Loop

**Scope determination** (based on relay briefing):

| Scope | Condition | Question Target |
|-------|-----------|----------------|
| Small (1-2) | Single feature, single file, existing pattern | Quick confirmation |
| Medium (3-5) | 2-3 features, multiple files, new capability | Intent + constraints + direction |
| Large (6-12) | Cross-feature, architecture change, new module | Full exploration |
| Critical (13-20) | Multiple locked paths, structural change | Exhaustive validation |

**Trigger priority** (process in order, ask via AskUserQuestion):

1. **의도 확인** — Is the user's intent clear? What exactly do they want to achieve?
   - Source: user message ambiguity
   - Ask when: user message is vague or could be interpreted multiple ways

2. **경로 보호 충돌** — Does the task touch locked/guarded paths?
   - Source: rules.yaml via briefing's Protection Alerts
   - Ask when: any LOCKED or GUARDED path overlaps with task scope

3. **Anti-pattern 충돌** — Does the proposed approach match a known anti-pattern?
   - Source: features.yaml anti_patterns via briefing
   - Ask when: user's described approach resembles a banned pattern

4. **제약조건 위반** — Does the task potentially violate feature constraints?
   - Source: features.yaml constraints via briefing
   - Ask when: task direction could conflict with stated constraints

5. **Cross-feature 영향** — Does the change affect connected features?
   - Source: features.yaml edges via briefing
   - Ask when: relevant feature has shared/cochange edges

6. **구현 방향 선택지** — Are there multiple valid approaches?
   - Source: context.yaml conventions + code reading results
   - Ask when: multiple patterns exist and choice matters

7. **엣지 케이스** — Are there edge cases the user hasn't considered?
   - Source: domain_knowledge via briefing
   - Ask when: domain knowledge suggests non-obvious scenarios

8. **테스트 범위** — What testing scope is appropriate?
   - Source: features.yaml modules + existing test files
   - Ask when: change has significant scope

9. **Git 상태 불일치** — Are uncommitted changes related to the task?
   - Source: git status via briefing
   - Ask when: uncommitted files overlap with task scope

10. **Stale 데이터 경고** — Is middleware data outdated?
    - Source: confidence level
    - Ask when: confidence is MEDIUM or LOW

**Termination rules**:
- A trigger is **resolved** when the user answers directly or explicitly defers ("나중에 결정").
- User answers may generate NEW triggers — these count toward the current scope bucket.
- If cumulative questions exceed 150% of scope ceiling, escalate to next scope tier.
- **Absolute ceiling**: 20 questions (Critical tier max). Never exceed this.
- If ALL triggers are resolved before reaching the target count, stop early. Don't ask unnecessary questions.

### Phase 4 — Work Plan Synthesis

1. Combine ALL gathered information:
   - Relay briefing (features, rules, context, git state)
   - Code reading results (current implementation state)
   - Counter-questioning answers (user decisions and preferences)
   - Confidence level and any stale data caveats

2. Synthesize a structured work plan:
   - **Goal**: One sentence describing the outcome
   - **Scope**: Which features/modules are affected
   - **Approach**: Chosen implementation direction (informed by counter-questioning)
   - **Constraints**: Active constraints and anti-patterns to respect
   - **Steps**: High-level implementation steps
   - **Risks**: Known risks from stale data, cross-feature impacts, etc.
   - **Protected Paths**: Any locked/guarded paths that need special handling

3. Present the plan to the user for confirmation.
4. Use AskUserQuestion:
   > "작업 계획 초안입니다. 승인하시면 상세 구현 계획을 작성합니다."
   - Option A: "승인 — 상세 구현 계획으로 진행"
   - Option B: "수정 필요 — 피드백 제공"

### Phase 5 — Transition to writing-plans

Once the user approves the work plan:

1. Invoke the `superpowers:writing-plans` skill.
2. Pass the full context:
   - The approved work plan from Phase 4
   - Relevant middleware briefing data
   - Counter-questioning decisions
   - Protected paths and constraints

The writing-plans skill will produce a detailed, step-by-step implementation plan with TDD, exact file paths, and commit points.

## Error Handling Summary

| Situation | Response |
|-----------|----------|
| `.middleware/` missing | Show init instructions, stop |
| Relay Agent fails | Direct YAML read fallback |
| features.yaml empty | Confidence LOW warning, proceed with available data |
| rules.yaml empty | Skip protection checks, fewer counter-questions |
| manifest phase < 3 | Confidence LOW warning, limited analysis |

## What This Skill Does NOT Do

- **Never write** to `.middleware/` (two-writer problem with the server)
- **Never modify** code — this skill only reads and plans
- **Never execute** plans — that's for writing-plans → executing-plans
- **Never skip** counter-questioning in manual mode (it's the core value proposition)
