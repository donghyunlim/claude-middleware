---
name: ha
description: Universal reasoning-and-execution pipeline (Phase 0-6) for any task type — Deep Reasoning in Opus, Execution in Haiku
argument-hint: "[요청 내용]"
level: 4
---

ultrathink.

# /ha — Universal Reasoning & Execution Pipeline

This skill produces high-quality outputs for any task type by combining deep reasoning (Opus) with delegated execution (Haiku). It is the canonical 7-phase engine (Phase 0-6) that /haq, /haqq, /haqqq invoke as thin shims.

**Output all responses in Korean.**

## Requirements
$ARGUMENTS

---

## Configuration from Caller

This skill can be invoked in two ways:

1. **Direct invocation (`/ha ...`)**: defaults to `depth_budget: 0`, meaning Phase 2 (Questioning) is **skipped** unless Phase 1 detects HIGH uncertainty. This honors the principle that 77% of requests already have a clear top-intent (Amazon Alexa research) and that simple queries waste 19-42 seconds on unnecessary reasoning (Stop Overthinking, arXiv:2503.16419).

2. **Thin-shim invocation (`/haq`, `/haqq`, `/haqqq`)**: prepends a config block with `depth_budget: 0-4`, `5-8`, or `9-12` respectively, before the user's $ARGUMENTS.

### Recognized Config Fields

The following fields in the prepended block (or defaults) control Phase behavior:

```
depth_budget: 0 | 0-4 | 5-8 | 9-12-up-to-20
question_rounds: 1 | 2 | 3-5
max_budget: 0 | 4 | 8 | 20
tier: direct | haq | haqq | haqqq
fleet_mode: off | on
fleet_tier: mid-upper | upper | top
fleet_upper_bound: 5 | 8 | 12
fleet_max_critical: 20
budget: standard | expanded | unlimited
```

---

## 7-Phase Pipeline (Phase 0–6)

### Phase 0: Dispatch Detection

Determine task category and route to appropriate design template. All 9 categories below trigger Phase 1 Pre-Q Deep Reasoning; categories with **confidence >= 95%** may optionally skip to Phase 3 (Design) if Phase 1 gate agrees.

**9 Task Types** (auto-detected from $ARGUMENTS):

1. **code** – write, debug, refactor, optimize code; technical architecture; API design
2. **writing** – blog, article, letter, proposal, documentation, creative content
3. **planning** – project planning, strategy, timeline, roadmap, sprint planning
4. **research** – literature review, synthesis, data exploration, hypothesis formation
5. **analysis** – data analysis, business intelligence, metrics, statistical/qualitative interpretation
6. **decision** – comparison, trade-off analysis, recommendation, go/no-go, multi-criteria ranking
7. **creative** – story, art concept, music, game design, experiential ideas
8. **learning** – how-to, skill development, concept explanation, curriculum design
9. **other** – anything else; calls user for clarification if dispatch confidence < 60%

### Phase 1: Pre-Q Deep Reasoning (Opus via Skill tool)

**Goal**: Detect uncertainty (epistemic, aleatoric, pragmatic) from $ARGUMENTS alone, before asking the user.

**Input**: Raw $ARGUMENTS + detected task_type from Phase 0.

**Output**: A structured `ambiguity_ledger` dict with scores:
- `epistemic`: 0–100 (missing knowledge, factual gaps)
- `aleatoric`: 0–100 (inherent randomness, unknowable trade-offs)
- `pragmatic`: 0–100 (unclear success criteria, conflicting goals)
- `overall_uncertainty`: max(epistemic, aleatoric, pragmatic)
- `detection_rationale`: brief explanation

**Gate Logic**:
- `overall_uncertainty < 20` → LOW (Phase 2 skipped, go to Phase 3 Design directly)
- `overall_uncertainty 20–60` → MEDIUM (Phase 2 proceeds with 1–4 questions, task-dependent)
- `overall_uncertainty > 60` → HIGH (Phase 2 proceeds with full depth_budget)
- Special: If user explicitly says "I'm sure" / "definitely" / "no questions needed", override to LOW

**Example** (code):
```
ambiguity_ledger:
  epistemic: 15  (user gave clear requirements, maybe missing edge cases)
  aleatoric: 5   (deterministic task)
  pragmatic: 35  (success criteria partially vague: "optimize" but no metrics given)
  overall_uncertainty: 35  → MEDIUM
  detection_rationale: |
    User request is mostly clear (function signature, I/O examples given).
    Primary uncertainty is around performance targets and acceptance criteria.
    Phase 2 will ask 2–3 clarifying questions on metrics and constraints.
```

---

### Phase 2: Uncertainty-Driven Questioning (Opus via Skill tool)

**Prerequisite**: Phase 1 gate is MEDIUM or HIGH (otherwise skip to Phase 3).

**Goal**: Reduce ambiguity ledger entries via targeted follow-up questions.

**Key Principles**:
- **EVPI ordering**: Ask questions that change the execution plan most → lowest impact last.
- **Stop Overthinking (arXiv:2503.16419)**: If user's answers drop uncertainty to LOW, stop asking. Don't ask all 0-4 / 5-8 / 9-12 if 2–3 suffice.
- **Fatigue detection (arXiv:2511.08798)**: User response length drop-off > 40%, monosyllabic replies, explicit "skip" → auto-stop Phase 2.
- **Cowan memory limits**: Max 4 questions per round. Break into multiple rounds if needed.

**Mechanics**:

#### Phase 2-0: Skip Condition Check
```
if overall_uncertainty < 20:
  return SKIP, go to Phase 3
elif overall_uncertainty 20–60:
  q_budget = min(2, depth_budget // 2)  # e.g., 0-4 budget → ask up to 2
elif overall_uncertainty > 60:
  q_budget = min(depth_budget, 4 * question_rounds)  # e.g., 0-4 → 4; 5-8 → 8; 9-12 → 12
```

#### Phase 2-1: Question Pool Construction (per task_type)

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

**Analysis** (all tiers):
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

#### Phase 2-2: EVPI Ranking & Question Selection

For each question category in the tier's pool:
1. **Estimate EVPI** (Expected Value of Perfect Information):
   - If we get a "yes" or "no" answer to this question, how much would it change the execution plan?
   - Rank categories by EVPI (descending: plan-changing first).
2. **Ask top-EVPI questions** up to q_budget per round.
3. **Drop dominated questions** (same answer in all plausible scenarios → no new info → don't ask).

#### Phase 2-3: Ask + Listen

For each selected question:
- Phrase in Korean, task-type friendly.
- Wait for user reply.
- Record answer + response_time.

#### Phase 2-4: Update Ambiguity Ledger

After each question:
- Re-score epistemic, aleatoric, pragmatic in light of answer.
- If overall_uncertainty drops to < 20, set Phase 2 gate = STOP (next round skipped).

#### Phase 2-5: Fatigue Detection & Auto-Stop

After each question, check:
- **Response time**: > 60s without reply → warn "still here? take your time" once, then timeout to Phase 3.
- **Response length**: Drop > 40% vs. previous response → possible fatigue signal.
- **Monosyllabic replies**: "yes", "no", "ok" only, multiple rounds → fatigue.
- **Explicit stop signals**: user says "skip", "enough", "just do it" → break Phase 2.

If any detected, exit Phase 2 after current question, proceed to Phase 3.

#### Phase 2-6: Multi-Round Logic

If `question_rounds > 1` and ambiguity not yet resolved:
- **Between rounds**: Re-evaluate ambiguity_ledger.
  - If uncertainty < 20, stop (don't do Round 2).
  - Otherwise, re-rank EVPI pool for remaining uncertainties.
- **Cowan working memory rule**: Never ask > 4 questions in a single prompt; split into 2+ rounds for 5+ questions.

**Example (haqq, 5-8 question budget)**:
```
Round 1:
  - Q1 (EVPI=highest): "What data sources will you use?"
  - Q2 (EVPI=high): "What is the primary success metric?"
  - Q3 (EVPI=medium): "Any sensitive/proprietary data concerns?"
  - Q4 (EVPI=medium-low): "Timeline for analysis?"
  
  User answers; ambiguity drops from MEDIUM (45) to LOW-MEDIUM (30).
  
Round 2:
  - Check: Still < 20? No, stay at 30.
  - Re-rank EVPI for remaining 4 categories.
  - Q5, Q6: ask top 2, user answers.
  - Ambiguity now 18 → STOP (don't do more rounds).
```

---

### Phase 3: Design Template Assembly (Opus via Skill tool)

**Prerequisite**: Phase 2 complete (or skipped).

**Input**: $ARGUMENTS + ambiguity_ledger + Phase 2 answers (if any).

**Goal**: Assemble a task-specific design template that Phase 4 will convert to executable sub-task delegation.

**Output**: A structured **Design Document** with:
- Task summary (1-2 sentences)
- Success criteria (measurable, from ambiguity_ledger + Phase 2 answers)
- Subtasks (logical decomposition)
- Constraints (time, resources, format)
- Dependencies (if parallel execution intended)
- Assumptions (default for aleatoric items; explicit for epistemic)
- Quality bar (Haiku tier, reasoning depth)

**Per Task Type**:

**Code**:
- Module/function signature.
- Input/output schema.
- Constraints (performance, memory, language idioms).
- Error handling categories (from Phase 2 or defaults).
- Testing approach (unit, integration, edge cases).
- Delegation: code-writer (Haiku), code-reviewer (Haiku), test-engineer (Haiku).

**Writing**:
- Audience (from Phase 2 or inferred).
- Tone (from Phase 2 or inferred).
- Structure (sections, flow, length).
- Quality bar (draft, polished, publication-ready).
- Delegation: writer (Haiku), editor (Haiku).

**Planning**:
- Goal statement + success criteria.
- Key milestones + timeline.
- Resource allocation.
- Risk register (from Phase 2 or standard risks).
- Stakeholder communication plan (if applicable).
- Delegation: planner (Haiku), risk-analyst (Haiku), reviewer (Haiku).

**Research**:
- Research question(s) (refined from Phase 2).
- Scope (what's in, what's out).
- Source priorities (academic, industry, user data, etc.).
- Synthesis plan (how to combine sources).
- Bias control (peer review, source diversity, caveats).
- Delegation: researcher (Haiku), source-validator (Haiku), synthesizer (Haiku).

**Analysis**:
- Analysis question (from Phase 2).
- Data source(s) + quality notes.
- Methodology (statistical, visual, qualitative).
- Assumptions + sensitivity plan.
- Output format (charts, tables, narrative, all).
- Delegation: analyst (Haiku), data-engineer (Haiku), visualization-designer (Haiku).

**Decision**:
- Alternatives (from Phase 2 or generated).
- Evaluation criteria (from Phase 2).
- Weighting (if multi-criteria).
- Reversibility & downside risk.
- Communication plan (how to explain decision).
- Delegation: comparator (Haiku), recommender (Haiku), communicator (Haiku).

**Creative**:
- Core idea / theme (from Phase 2).
- Target audience + emotional tone.
- Style / references (from Phase 2).
- Constraints (length, format, rights).
- Revision plan (iteration, feedback).
- Delegation: creator (Haiku), critic (Haiku), refiner (Haiku).

**Learning**:
- Skill / concept (from Phase 2).
- Current level → target level.
- Available time + preferred modality.
- Assessment method.
- Support needs (feedback, accountability).
- Delegation: instructor (Haiku), assessor (Haiku), mentor (Haiku).

---

### Phase 4: Fleet Dispatching – Agent Matching & Parallel Execution

**Goal**: Map design template sub-tasks to available specialist Haiku agents (subagents), dispatch in parallel, collect results.

#### Approach: Dynamic Detection (not hardcoded)

Instead of a static mapping table, **Phase 4 uses runtime detection**:

1. **Enumerate** available subagents in current Claude Code environment (via `/omc:team` or similar introspection).
2. **Filter** by task_type + phase (e.g., code reviewers for code tasks, only if Phase 1/5/6).
3. **Diversify** (avoid duplicate roles; prefer complementary expertise).
4. **Rank** by predicted fit (task complexity, agent specialization, user feedback).
5. **Dispatch** top N (N = tier_upper_bound, scaled by task complexity).

#### Quality Tier Policy

**Tier** → **Per-phase agent upper bound** → **3-phase total** → **Budget** → **Runtime scaling**

| Tier | Per-phase | 3-phase total | Budget | Complexity scaling | Notes |
|---|---|---|---|---|---|
| direct (depth=0) | 1 | 1 | standard | Trivial: 1; Simple: 1 | Minimal; direct Opus output or single Haiku. |
| haq (depth=0-4) | 5 | 15 | standard | Trivial: 1–2; Simple: 2–3; Moderate: 3–5 | Fast iteration. 5 parallel Haiku writers/reviewers. |
| haqq (depth=5-8) | 8 | 24 | expanded | Trivial: 3–5; Simple: 4–5; Moderate: 5–7; Complex: 7–8 | Mid-tier resource. 8 agents per phase. |
| haqqq (depth=9-12+) | 12 (or 20 critical) | 36–60 | unlimited | Trivial: 5–6; Simple: 6–8; Moderate: 8–10; Complex/Critical: 10–12 (or up to 20) | Top tier. Aggressive parallelization. |

**Budget warning**: If total parallel agents > 20, warn user before Phase 5. (haqqq can override if user confirms "unlimited budget".)

#### Task Complexity Auto-Detection

Per task_type, estimate complexity from:
- $ARGUMENTS length (< 100 words → trivial; 100–300 → simple; 300–1000 → moderate; > 1000 → complex)
- Ambiguity_ledger overall_uncertainty (< 20 → trivial; 20–60 → simple/moderate; > 60 → complex)
- Number of sub-tasks from design template (1 → trivial; 2–3 → simple; 4–6 → moderate; 7+ → complex)

#### Phase 1 / Phase 5 / Phase 6 Scope

Agents are **only** dispatched in Phase 1, Phase 5, and Phase 6:
- **Phase 1**: Specialization detection agents (e.g., "code-complexity-analyzer", "writing-target-detector") may assist Opus in detecting uncertainty.
- **Phase 5**: Execution verification agents (e.g., "code-reviewer", "writing-quality-checker", "test-engineer") run in parallel on Haiku outputs.
- **Phase 6**: Refinement agents (e.g., "style-guide-checker", "accessibility-reviewer") polish outputs.

Phases 2, 3, 4 are **Opus solo** (no agent dispatch).

#### Agent Invocation Pattern

```python
# Pseudocode
agents_needed = get_design_template_subtasks()
tier_upper_bound = fleet_upper_bound  # e.g., 5 for haq, 8 for haqq
complexity = estimate_task_complexity(arguments, ambiguity_ledger, design)

available_agents = enumerate_subagents()  # e.g., [code-writer, code-reviewer, test-engineer, ...]
filtered = [a for a in available_agents if a.phase in [1, 5, 6] and a.task_type == current_task_type]
diversified = rank_and_diversify(filtered, avoid_duplicates=True)
ranked = rank_by_fit(diversified, complexity, design, tier_upper_bound)

num_to_dispatch = min(tier_upper_bound, complexity_scaled(tier, complexity))
dispatch_list = ranked[:num_to_dispatch]

for agent in dispatch_list (parallel):
    result[agent.name] = invoke_haiku_agent(agent, design_subtask, tier_config)
```

#### Fleet Dispatching Output

Collect parallel Haiku agent results into a dict:
```
{
  "code_writer": "<Haiku output>",
  "code_reviewer": "<Haiku output>",
  "test_engineer": "<Haiku output>",
  ...
}
```

Pass to Phase 5 for verification & synthesis.

---

### Phase 5: Execution Verification & Synthesis (Opus via Skill tool)

**Input**: Design template + parallel Haiku agent results from Phase 4.

**Goal**: Verify quality, reconcile conflicts, synthesize final output.

**Key Verification Recipes** (per task_type):

**Code**:
- Does output compile / have syntax errors?
- Does it match design template (signature, I/O, constraints)?
- Test coverage (unit, integration)?
- Performance + memory within constraints?
- Reviewer feedback: logic flaws, style, security?

**Writing**:
- Audience tone match (from design)?
- Structure coherence?
- Fact-check + source accuracy (if applicable)?
- Copy-editing (grammar, readability)?

**Planning**:
- Milestone logic (dependencies honored)?
- Resource/timeline feasibility?
- Risk register completeness?
- Stakeholder alignment?

**Research**:
- Source diversity + bias control?
- Synthesis coherence?
- Citation accuracy?
- Conclusion support (data-backed)?

**Analysis**:
- Methodology sound?
- Assumptions explicit + reasonable?
- Sensitivity analysis present?
- Visualization clarity?
- Reproducibility (can others repeat steps)?

**Decision**:
- All alternatives fairly evaluated?
- Criteria weighting transparent?
- Downside risks acknowledged?
- Communication clear + persuasive?

**Creative**:
- Core idea compelling?
- Tone/style consistent?
- Constraints honored?
- Originality / freshness?

**Learning**:
- Content level-appropriate?
- Modality match (video, text, etc.)?
- Progression logical?
- Assessment valid?

**Conflict Resolution**:
- If code reviewer and code writer disagree on approach, Opus decides based on ambiguity_ledger + design.
- If multiple writers produce conflicting facts, flag for Phase 6 research.
- haqqq tier: Summon a tie-breaker critic agent (additional Haiku) to arbitrate; others use Opus judgment.

---

### Phase 6: Final Refinement & Polish (Opus + Optional Specialist Agents)

**Input**: Opus-verified output from Phase 5 + design template.

**Goal**: Apply final styling, accessibility, brand guidelines, etc.

**Standard Refinements**:

**Code**:
- Lint / format (PEP 8, Prettier, etc.).
- Comments + docstrings.
- README / usage examples.

**Writing**:
- Brand voice consistency.
- Accessibility (alt text, screen reader compatibility).
- SEO (if applicable).

**Planning**:
- Formatting + template consistency.
- Gantt / dependency visualization.
- Stakeholder sign-off prep.

**Research**:
- Bibliography formatting (APA, Chicago, etc.).
- Supplementary materials organization.
- Peer review readiness.

**Analysis**:
- Chart accessibility (color-blind safe, alt text).
- Data table formatting.
- Legend + axis clarity.

**Decision**:
- Executive summary (1-page).
- Presentation slide outline (if requested).
- FAQ or risk mitigation plan.

**Creative**:
- Peer critique integration.
- Revision notes for next iteration.

**Learning**:
- Curriculum roadmap.
- Progress checklist.

---

### Phase 7: Return Final Output

Deliver polished, verified output to user in requested format (text, code, JSON, etc.).

Include a short meta-summary:
- Which tier was invoked (direct, haq, haqq, haqqq)?
- How many Phase 2 questions asked + ambiguity before/after?
- How many parallel agents dispatched (Phase 1/5/6)?
- Quality bar achieved (draft, polished, publication-ready).

---

## 8 Loop-Back Rules + Global Circuit Breaker

If any phase detects a failure mode, apply loop-back:

| Rule | Trigger | Action |
|---|---|---|
| **LB1: Ambiguity Spiral** | Phase 2 questions increase ambiguity instead of reducing it. | Return to Phase 3 Design with explicit assumption statements (stop asking). |
| **LB2: Verification Fail** | Phase 5 detects critical errors in Haiku output (compile fail, logic flaw). | Dispatch a corrector agent; if 2x retries fail, escalate to Opus rewrite. |
| **LB3: Scope Creep** | Design template subtasks exceed 50% of initial estimate. | User consent required before Phase 4 dispatch (offer scope reduction). |
| **LB4: Data Unavailable** | Research/analysis can't access required data source. | List alternatives; ask user (Phase 2 gate); proceed with proxy or note limitation. |
| **LB5: Complexity Underestimate** | Haiku output quality below bar; complexity > tier capability. | Raise tier (if user accepts) or revert to Opus direct rewrite. |
| **LB6: Reviewer Deadlock** | Phase 5 verification agents in persistent disagreement. | Haiku debate round (2 agents argue, Opus decides); if unresolved, mark as "POV-dependent" in output. |
| **LB7: Token Exhaustion** | Approaching context limit during Phase 4/5. | Abort parallel dispatch; consolidate to essential subtasks only. |
| **LB8: User Timeout** | No response > 60s in Phase 2 questioning. | Auto-advance to Phase 3 with best-effort assumptions. |

**Global Circuit Breaker**: If > 2 loop-backs trigger in a single invocation, pause and report to user: "This request is hitting complexity limits. Would you like to break it into smaller tasks or escalate to a human specialist?"

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

## Example Walkthrough: Code Task

**User Input**:
```
/ha Write a Python function that takes a CSV file path and returns a Pandas DataFrame
with outliers removed. Use IQR method.
```

**Phase 0**: Dispatch = "code" ✓

**Phase 1 (Opus)**: Pre-Q Deep Reasoning
```
ambiguity_ledger:
  epistemic: 25 (user wants IQR, but didn't specify columns or how to define outliers)
  aleatoric: 5 (deterministic)
  pragmatic: 20 (no success criteria; "removed" is vague)
  overall_uncertainty: 25 → MEDIUM
  gate: Proceed to Phase 2.
```

**Phase 2 (Opus)**: Questioning (depth_budget=0, skips Phase 2 by default)
→ Phase 1 says MEDIUM, so check gate: `depth_budget=0` and uncertainty=25.
→ Direct invocation, no phase 2 questions. Go to Phase 3.

*(If user had called `/haq`, depth_budget=0-4, so we'd ask ~2 questions here.)*

**Phase 3 (Opus)**: Design Template
```
Design:
  - Function name: remove_outliers_iqr
  - Inputs: csv_path (str), columns (list, optional: auto-detect all numeric)
  - Outputs: DataFrame (rows with outliers removed)
  - IQR threshold: default Q1 - 1.5*IQR, Q3 + 1.5*IQR (parameterized)
  - Success criteria:
    - Runs without errors on typical CSVs (< 1M rows).
    - Handles missing values gracefully (skip or impute, configurable).
    - Documentation + docstring clear.
  - Subtasks:
    1. Read CSV safely (encoding, NA handling).
    2. Detect numeric columns.
    3. Compute IQR per column.
    4. Filter rows outside bounds.
    5. Return cleaned DataFrame.
  - Quality bar: Haiku (simple task), single pass + review.
```

**Phase 4 (Opus)**: Fleet Dispatch
```
complexity = estimate_task_complexity(...) = "simple" (single function, 5 lines)
tier_upper_bound = 1 (direct invocation, depth=0)
num_to_dispatch = 1

Dispatch:
  - code_writer (Haiku): Write the function per design.
```

**Haiku (code_writer)**:
```python
import pandas as pd

def remove_outliers_iqr(csv_path, columns=None):
    """
    Remove rows with outliers (IQR method) from a CSV file.
    
    Args:
        csv_path: Path to CSV file.
        columns: List of numeric columns to check. If None, auto-detect.
    
    Returns:
        DataFrame with outlier rows removed.
    """
    df = pd.read_csv(csv_path)
    if columns is None:
        columns = df.select_dtypes(include=['number']).columns.tolist()
    
    for col in columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df = df[(df[col] >= lower) & (df[col] <= upper)]
    
    return df
```

**Phase 5 (Opus)**: Verification
```
Checks:
  ✓ Code runs without syntax errors.
  ✓ Matches design (inputs, outputs, IQR logic).
  ✓ Handles edge cases (empty DataFrame, no numeric cols → empty list, no filtering).
  ✗ Missing: docstring example.
  ✓ Simple, readable (no performance concerns for typical data).

Refinement needed: Add usage example to docstring.
```

**Phase 6 (Opus)**: Polish
```
Refined code:
```python
import pandas as pd

def remove_outliers_iqr(csv_path, columns=None):
    """
    Remove rows with outliers (IQR method) from a CSV file.
    
    Args:
        csv_path (str): Path to CSV file.
        columns (list, optional): Numeric columns to check. If None, auto-detect.
    
    Returns:
        pd.DataFrame: DataFrame with outlier rows removed.
    
    Example:
        df = remove_outliers_iqr("data.csv", columns=["age", "income"])
        print(f"Removed {len(original) - len(df)} rows.")
    """
    df = pd.read_csv(csv_path)
    if columns is None:
        columns = df.select_dtypes(include=['number']).columns.tolist()
    
    for col in columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df = df[(df[col] >= lower) & (df[col] <= upper)]
    
    return df
```

**Phase 7**: Return
```
🎚️ Tier: direct (depth=0, auto-skip Phase 2)
📊 Ambiguity: MEDIUM (25) → addressed via design defaults
🚀 Agents: 1 (code-writer)
✅ Quality: polished

[code above]
```

---

## Notes

- **Output language**: All user-facing output (design summaries, questions, explanations) is in **Korean**.
- **Skill invocation** from /haq, /haqq, /haqqq prepend config; /ha respects config or defaults to depth_budget=0.
- **No re-implementation**: /haq/haqq/haqqq are thin shims; they never redefine Phase 0–6 logic. They only set config + category hints.
- **Agent autonomy**: Haiku agents receive task descriptions + design template, not role personas. They are purpose-driven, not identity-driven.
- **Transparency**: Every phase outputs intermediate results, ambiguity scores, agent dispatch decisions, verification notes. User can always see why decisions were made.
