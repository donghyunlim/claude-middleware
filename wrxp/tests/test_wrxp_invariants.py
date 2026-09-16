import json
import re
import unittest
from pathlib import Path


WRXP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WRXP_ROOT.parent


def parse_flat_yaml_block_after(text: str, heading: str) -> dict[str, object]:
    """Parse the scalar-only preset blocks without adding a YAML dependency."""
    tail = text.split(heading, 1)[1]
    match = re.search(r"```yaml\n(.*?)\n```", tail, re.DOTALL)
    if not match:
        raise AssertionError(f"missing YAML block after {heading}")

    parsed: dict[str, object] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value == "null":
            parsed[key] = None
        elif value in ("true", "false"):
            parsed[key] = value == "true"
        elif value.isdigit():
            parsed[key] = int(value)
        else:
            parsed[key] = value
    return parsed


def parse_named_flat_yaml_block_after(
    text: str,
    heading: str,
    root_key: str,
) -> dict[str, object]:
    """Parse a named YAML mapping whose values are scalar policy settings."""
    tail = text.split(heading, 1)[1]
    match = re.search(r"```yaml\n(.*?)\n```", tail, re.DOTALL)
    if not match:
        raise AssertionError(f"missing YAML block after {heading}")

    lines = match.group(1).splitlines()
    if not lines or lines[0] != f"{root_key}:":
        raise AssertionError(f"missing {root_key} root after {heading}")

    parsed: dict[str, object] = {}
    for line in lines[1:]:
        if not line.startswith("  ") or line.startswith("    "):
            continue
        key, value = line.strip().split(":", 1)
        value = value.strip()
        if value == "null":
            parsed[key] = None
        elif value in ("true", "false"):
            parsed[key] = value == "true"
        elif value.isdigit():
            parsed[key] = int(value)
        else:
            parsed[key] = value
    return parsed


class WrxpInvariantTests(unittest.TestCase):
    def test_packaging_and_docs_layout_is_installable(self):
        self.assertFalse((WRXP_ROOT / "CLAUDE.md").exists())
        self.assertTrue((WRXP_ROOT / "docs/fast-worker-routing.md").exists())
        package = json.loads((WRXP_ROOT / "package.json").read_text())
        self.assertIn("docs/fast-worker-routing.md", package["files"])
        self.assertIn("CHANGELOG.md", package["files"])
        self.assertTrue((WRXP_ROOT / "CHANGELOG.md").exists())
        self.assertNotIn("CLAUDE.md", package["files"])

    def test_readme_does_not_claim_nonexistent_ha_artifacts(self):
        readme = (WRXP_ROOT / "README.md").read_text()
        for artifact in ("ha-ambiguity", "ha-design", "ha-fleet"):
            self.assertFalse(
                artifact in readme,
                f"README claims nonexistent /ha artifact: {artifact}",
            )

    def test_current_knife_docs_describe_runtime_bounded_task_graph_parallelism(self):
        readme = (WRXP_ROOT / "README.md").read_text()
        ha = (WRXP_ROOT / "docs/benchmark/ha.md").read_text()
        haq = (WRXP_ROOT / "docs/benchmark/haq.md").read_text()
        haqq = (WRXP_ROOT / "docs/benchmark/haqq.md").read_text()
        haqqq = (WRXP_ROOT / "docs/benchmark/haqqq.md").read_text()
        research = (WRXP_ROOT / "docs/RESEARCH_REPORT.md").read_text()

        self.assertIn("`/haqq` | 균형 잡힌 실행 (0~8개 질문)", ha)
        self.assertIn("0~12개, 동의 시 최대 20개 질문", ha)
        self.assertNotIn("균형 잡힌 실행 (5-8개 질문)", ha)
        self.assertNotIn("심층 실행 (9-20개 질문)", ha)
        self.assertIn("0문항", haq)
        self.assertIn("런타임이 공개한 동시 위임 한도", haq)
        self.assertIn("최대 8개", haqq)
        self.assertIn("한 라운드에 최대 4개", haqq)
        self.assertNotIn("5~8개 핵심 질문", haqq)
        self.assertNotIn("2개씩 묶어서", haqq)
        self.assertIn("0~12개", haqqq)
        self.assertIn("명시적 동의", haqqq)
        self.assertIn("런타임이 공개한 동시 위임 한도", haqqq)
        self.assertIn("task graph", haqqq)
        self.assertNotIn("최대 3회까지 반복", ha)
        self.assertIn("5·15·25", ha)
        self.assertIn("10·20·30", ha)
        for current_row in (
            "| /wrxp:haq | 0-4 | 1 | runtime-bounded task graph |",
            "| /wrxp:haqq | 0-8 | 2 | runtime-bounded task graph |",
            "| /wrxp:haqqq | 0-12 (동의 시 max 20) | 3 (동의 시 5) | runtime-bounded task graph |",
        ):
            self.assertIn(current_row, readme)
        self.assertIn("질문 깊이와 모델 라우팅은 서로 독립적인 축", readme)
        self.assertIn("## Team family 7단계 파이프라인", readme)
        self.assertIn(
            "Knife family인 `/ha` 계열은 위에서 설명한 runtime-bounded dependency task graph 계약",
            readme,
        )
        self.assertIn("어떤 tier에서도 0문항으로 종료", readme)
        self.assertIn("관점·가설 fleet", readme)
        self.assertNotIn("Phase 1이 HIGH로 판정할 때만", readme)
        self.assertLess(
            research.index("현재 계약 정정 (0.1.26)"),
            research.index("## Executive Summary"),
        )

    def test_fast_worker_docs_cover_all_fallback_causes(self):
        docs = (WRXP_ROOT / "docs/fast-worker-routing.md").read_text()
        self.assertTrue(
            "Qwen unavailable or invalid response" in docs,
            "fast-worker docs must describe every exit-3 fallback cause",
        )
        self.assertFalse(
            "unreachable" in docs,
            "fast-worker docs must not label every fallback as unreachable",
        )

    def test_packaging_and_git_exclude_python_caches(self):
        for ignore_file in (".npmignore", ".gitignore"):
            patterns = (WRXP_ROOT / ignore_file).read_text().splitlines()
            for pattern in ("__pycache__/", "*.pyc", "*.pyo"):
                self.assertIn(pattern, patterns)
        package = json.loads((WRXP_ROOT / "package.json").read_text())
        self.assertIn("scripts/qwen.py", package["files"])
        self.assertNotIn("scripts", package["files"])

    def test_release_versions_match(self):
        plugin_version = json.loads(
            (WRXP_ROOT / ".claude-plugin/plugin.json").read_text()
        )["version"]
        package_version = json.loads(
            (WRXP_ROOT / "package.json").read_text()
        )["version"]
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin/marketplace.json").read_text()
        )
        marketplace_version = next(
            plugin["version"]
            for plugin in marketplace["plugins"]
            if plugin["name"] == "wrxp"
        )

        self.assertEqual(
            {"0.1.31"},
            {plugin_version, package_version, marketplace_version},
        )

    def test_model_registry_covers_codex_and_claude_runtime_candidates(self):
        routing = (
            WRXP_ROOT / "skills/ha/references/model-routing.md"
        ).read_text()

        expected_rows = (
            "| controller | `gpt-6-astra` + `high` | Claude Opus 5 (`claude-opus-5`) |",
            "| standard executor | `gpt-5.6-terra` + `medium` | Claude Sonnet 5 (`claude-sonnet-5`) |",
            "| utility executor | `gpt-5.6-luna` + `low` | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) |",
        )
        for row in expected_rows:
            self.assertIn(row, routing)

        for capability in (
            "active_model",
            "available_models",
            "supported_reasoning_efforts",
            "can_delegate",
            "max_parallel_delegations",
            "can_isolate_verifier_context",
        ):
            self.assertIn(capability, routing)
        self.assertIn("확인되지 않은 `(model, effort)` 쌍을 만들지 않는다", routing)
        self.assertIn("같은 모델에서", routing)
        self.assertIn("`opus`, `sonnet`, `haiku`", routing)
        self.assertIn("Claude API 모델 ID", routing)
        self.assertIn("runtime_parallel_limit", routing)
        self.assertIn("독립 실행 단위만 같은 wave", routing)
        self.assertIn("동시 활성 subagent 수", routing)

        benchmark = (
            WRXP_ROOT / "docs/benchmark/model-routing-0.1.26.md"
        ).read_text()
        self.assertIn("모델 분류나 동률 판단 성향을 바꾸지 않는다", benchmark)
        self.assertNotIn("동률 판단의 비용 성향만", benchmark)
        self.assertIn("실제 subagent 호출", routing)
        self.assertIn("최소 충분 위임", routing)

    def test_question_policy_requires_user_ownership_and_execution_delta(self):
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()
        candidate_match = re.search(
            r"```yaml\nQuestionCandidate:\n(.*?)\n```",
            questioning,
            re.DOTALL,
        )
        self.assertIsNotNone(candidate_match)
        candidate_fields = set(
            re.findall(r"^  ([a-z_]+):", candidate_match.group(1), re.MULTILINE)
        )
        for field in (
            "unresolved",
            "evidence_checked",
            "answer_owner",
            "materially_branching",
            "concrete_next_action_blocked",
            "execution_delta",
            "risk_if_assumed",
            "assumption_cost",
            "safe_default",
        ):
            if field == "execution_delta":
                self.assertIn(field, candidate_match.group(1))
            else:
                self.assertIn(field, candidate_fields)
        for gate in (
            "`unresolved == true`",
            "`answer_owner == user`",
            "`materially_branching == true`",
            "`concrete_next_action_blocked == true`",
            "`safe_default: null`",
        ):
            self.assertIn(gate, questioning)
        self.assertIn("실행 통제 경계 후보는 이 조건을 잃었다는 이유로", questioning)

    def test_question_policy_promotes_user_owned_artifact_choices(self):
        """Meeting-brief choices must not disappear behind a reversible default."""
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        self.assertIn(
            "question_class: must_ask | decision_quality | skip", questioning
        )
        for choice_surface in (
            "산출물의 독자·사용 목적",
            "공유·공개 범위",
            "결정의 상태·권한",
            "참석자·소유자·수용 기준",
        ):
            self.assertIn(choice_surface, questioning)
        self.assertIn(
            "안전한 기본값이 있어도 `decision_quality` 후보를 버리지 않는다",
            questioning,
        )
        self.assertIn(
            "`standard` 프리셋은 1~3개의 가장 중요한 "
            "`decision_quality` 후보를 첫 라운드에 묻는다",
            questioning,
        )

    def test_direct_ha_has_a_zero_question_none_preset(self):
        """Direct /ha has no discovery budget; gates are a separate control path."""
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        self.assertEqual(
            {
                "question_preset": "none",
                "min_questions": 0,
                "max_questions": 0,
                "max_questions_per_round": 0,
                "max_rounds": 0,
            },
            parse_flat_yaml_block_after(engine, "## 핵심 계약"),
        )
        self.assertIn("none | quick | standard | deep", engine)
        self.assertIn("| `none` | 0 | 0 | 0 |", questioning)
        self.assertIn("승인·보안·비밀·외부 변경·파괴적·불가역", engine)
        self.assertIn("`concrete_next_action_blocked == true`", questioning)
        self.assertIn("safe_default: null", questioning)
        self.assertIn("안전한 기본값이 없으면 실행하지 말고 blocker", questioning)
        self.assertNotIn("`must_ask`가 슬롯을 차지하면", questioning)
        self.assertNotIn("`deep`: blocker와 고위험 후보를 먼저", questioning)

    def test_execution_control_questions_bypass_discovery_budget_state(self):
        """Approval gates must never consume or be capped by discovery batches."""
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        for contract in ("별도 전송 경로", "QuestionBudgetState 사전검사",
                         "갱신하지 않는다", "`decision_quality` 배치에만"):
            self.assertIn(contract, questioning)
        self.assertIn("must_ask 있음 → EXECUTION_CONTROL_ASK", engine)
        self.assertIn("예산 내 decision_quality 있음 → DISCOVERY_ASK", engine)
        self.assertIn(
            "승인·보안·비밀·외부 변경·파괴적·불가역 경계는 discovery 예산 밖",
            engine,
        )
        for name in ("ha", "haq", "haqq", "haqqq"):
            entry = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertIn("질문 예산과 무관하게 즉시 묻는다", entry)

    def test_runtime_caps_and_dependency_waves_have_a_structured_contract(self):
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()

        for contract in (
            "max_parallel_delegations: positive_integer | unknown",
            "runtime_parallel_limit:",
            "when_can_delegate_false: 1",
            "when_max_unknown: 1",
            "when_max_positive: max_parallel_delegations",
            "same_file_write",
            "shared_state",
            "external_side_effect",
            "producer_consumer",
            "writer_verifier",
        ):
            self.assertIn(contract, engine)

    def test_tier_shims_only_supply_question_presets(self):
        expected = {
            "haq": {
                "question_preset": "quick",
                "min_questions": 0,
                "max_questions": 4,
                "max_questions_per_round": 4,
                "max_rounds": 1,
                "extended_max_questions": None,
                "extended_max_rounds": None,
                "extension_requires_user_consent": False,
            },
            "haqq": {
                "question_preset": "standard",
                "min_questions": 0,
                "max_questions": 8,
                "max_questions_per_round": 4,
                "max_rounds": 2,
                "extended_max_questions": None,
                "extended_max_rounds": None,
                "extension_requires_user_consent": False,
            },
            "haqqq": {
                "question_preset": "deep",
                "min_questions": 0,
                "max_questions": 12,
                "max_questions_per_round": 4,
                "max_rounds": 3,
                "extended_max_questions": 20,
                "extended_max_rounds": 5,
                "extension_requires_user_consent": True,
            },
        }
        for name, expected_preset in expected.items():
            skill = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertEqual(
                expected_preset,
                parse_flat_yaml_block_after(skill, "## Preset"),
            )
            self.assertNotIn("routing_bias:", skill)
            for model in (
                "gpt-6-astra",
                "gpt-5.6-sol",
                "gpt-5.6-terra",
                "gpt-5.6-luna",
                "claude-opus",
                "claude-sonnet",
                "claude-haiku",
            ):
                self.assertNotIn(model, skill)

    def test_question_round_and_extension_budgets_are_enforced(self):
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        self.assertIn(
            "`min(4, normalized_runtime_limit, remaining_eligible, remaining_total_budget)`",
            questioning,
        )
        self.assertIn("`normalized_runtime_limit = 1`", questioning)
        self.assertNotIn(
            "normalized_runtime_limit",
            engine,
            "budget arithmetic must live only in questioning.md",
        )
        budget_match = re.search(
            r"```yaml\nQuestionBudgetState:\n(.*?)\n```",
            questioning,
            re.DOTALL,
        )
        self.assertIsNotNone(budget_match)
        budget_fields = set(
            re.findall(r"^  ([a-z_]+):", budget_match.group(1), re.MULTILINE)
        )
        self.assertEqual(
            {
                "questions_asked_total",
                "substantive_rounds_completed",
                "effective_max_questions",
                "effective_max_rounds",
            },
            budget_fields,
        )
        self.assertIn(
            "`questions_asked_total < effective_max_questions`",
            questioning,
        )
        self.assertIn(
            "`substantive_rounds_completed < effective_max_rounds`",
            questioning,
        )
        self.assertIn(
            "`effective_max_questions = extended_max_questions`",
            questioning,
        )
        self.assertIn(
            "`effective_max_rounds = extended_max_rounds`",
            questioning,
        )
        self.assertIn(
            "확장 동의 제어 질문은 `questions_asked_total += 1`만 적용",
            questioning,
        )
        self.assertIn("최대 5개의 실질 질문 라운드", questioning)
        self.assertIn("20 - questions_asked_total", questioning)

    def test_question_budget_state_records_each_dispatched_batch(self):
        """A sent question batch must consume its question and round budget."""
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        self.assertIn("`questions_asked_total += batch_size`", questioning)
        self.assertIn("`substantive_rounds_completed += 1`", questioning)
        self.assertIn(
            "`remaining_total_budget = effective_max_questions - "
            "questions_asked_total`",
            questioning,
        )
        self.assertIn(
            "`questions_asked_total += 1`만 적용하고 "
            "`substantive_rounds_completed`는 증가시키지 않는다",
            questioning,
        )
        self.assertNotIn(
            "questions_asked_total",
            engine,
            "counter update rules must live only in questioning.md",
        )

    def test_question_gate_is_inline_so_it_survives_a_skipped_reference_read(self):
        """The 0.1.26 failure: the gate lived 45KB away behind an unenforced read."""
        skill = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()

        self.assertIn(
            "QuestionGate 계약은 이 파일 안에 있으므로 참조 문서를 읽지 못해도 "
            "질문 판정 자체는 건너뛸 수 없다",
            skill,
        )
        self.assertIn(
            "`QuestionGateVerdict`가 `ask`일 때 "
            "[references/questioning.md](references/questioning.md)",
            skill,
        )
        self.assertNotIn("모든 호출에서 CAPABILITY_RESOLVE 직후", skill)
        self.assertNotIn("읽지 않았다면 관찰을 시작하지 말고 먼저 읽는다", skill)

        gate_heading = skill.index("## 3. QUESTION_GATE")
        commit_heading = skill.index("## 4. COMMIT_INTENT")
        self.assertLess(gate_heading, commit_heading)

    def test_question_gate_contract_is_byte_identical_across_entry_files(self):
        """Every entry file carries the same gate; shims never fork the policy."""
        blocks = {}
        for name in ("ha", "haq", "haqq", "haqqq"):
            text = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            start = text.index("읽기 전용 탐색은 판정 전에도 허용한다")
            tail = "사용자가 이 대화에서 질문 중단을 밝힌 경우에만 그 지시를 따른다."
            end = text.index(tail) + len(tail)
            blocks[name] = text[start:end]

        self.assertEqual(
            1,
            len(set(blocks.values())),
            f"QuestionGate blocks diverged across {sorted(blocks)}",
        )

        gate = blocks["ha"]
        verdict_match = re.search(
            r"```yaml\nQuestionGateVerdict:\n(.*?)\n```", gate, re.DOTALL
        )
        self.assertIsNotNone(verdict_match)
        self.assertEqual(
            {"verdict", "eligible_candidates", "basis"},
            set(re.findall(r"^  ([a-z_]+):", verdict_match.group(1), re.MULTILINE)),
        )
        for clause in (
            "verdict: ask | pass_zero | blocked",
            "`unresolved`",
            "`answer_owner == user`",
            "`materially_branching`",
            "질문 예산과 무관하게 즉시 묻는다",
            "평가를 건너뛴 상태는 `pass_zero`가 아니다",
        ):
            self.assertIn(clause, gate)

    def test_gate_outranks_a_runtime_default_that_discourages_questions(self):
        """Codex Default mode prefers assumptions over questions; the tier call overrides it."""
        for name in ("ha", "haq", "haqq", "haqqq"):
            entry = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertIn(
                "질문 tier 스킬을 호출한 것 자체가 명확화를 요청하는 "
                "명시적 사용자 지시다",
                entry,
            )
            self.assertIn(
                "런타임 기본 설정이 질문보다 가정을 선호하도록 안내하더라도, "
                "이 계약이 정한 `must_ask`와 예산 안의 `decision_quality` 질문은 "
                "그 기본 선호보다 우선한다",
                entry,
            )
            self.assertIn(
                "사용자가 이 대화에서 질문 중단을 밝힌 경우에만 그 지시를 따른다",
                entry,
            )

    def test_free_form_fallback_matches_runtimes_without_a_choice_widget(self):
        """Codex forbids faking a multiple-choice question as assistant text."""
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        self.assertIn(
            "구조화 질문 도구가 없으면 텍스트로 선택형 UI를 흉내 내지 말고, "
            "가장 높은 우선순위의 질문 하나를 간결하게 묻는다",
            questioning,
        )

        # Observed in the 0.1.27 behavior run: with questioning.md unreadable the
        # model asked four text questions with (a)/(b)/(c) options, which Codex
        # forbids. The fallback has to survive a failed reference read.
        for name in ("ha", "haq", "haqq", "haqqq"):
            entry = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertIn(
                "참조를 읽을 수 없으면 한 라운드 최대 4개 상한만 적용하되, "
                "구조화 질문 도구를 쓸 수 없는 런타임에서는 선택지를 텍스트로 "
                "나열해 선택형을 흉내 내지 말고 우선순위가 가장 높은 질문 하나만 "
                "평문으로 묻는다",
                entry,
            )

    def test_gate_covers_the_scenarios_that_regressed_in_0_1_26(self):
        """Each observed scenario must map to a discriminating rule in the contract."""
        gate = (WRXP_ROOT / "skills/haqq/SKILL.md").read_text()
        questioning = (
            WRXP_ROOT / "skills/ha/references/questioning.md"
        ).read_text()

        scenarios = (
            # The reported RED case: a meeting brief whose use was never stated.
            (
                "회의 자료 준비",
                gate,
                "새 문서, 회의 자료, 메시지 또는 결정 기록을 만들면서 "
                "그 쓰임이 요청에 명시되어 있지 않다면 기본적으로 이 분류에 해당한다",
            ),
            # A lookup answerable from the repository: never ask.
            ("단순 조회", gate, "증거로 확인할 수 있거나"),
            # A cosmetic preference with a safe default and no change of use.
            (
                "사소한 형식 선택",
                questioning,
                "낮은 위험의 세부 선호이며 안전한 기본값이 있고, "
                "`decision_quality`의 쓰임 변화도 없는 경우",
            ),
            # A destructive or irreversible boundary: ask regardless of budget.
            (
                "고위험 외부 변경",
                gate,
                "승인·보안·비밀·권한·외부 변경·파괴적·불가역 경계이며 "
                "안전한 기본값이 없다",
            ),
        )
        for label, document, rule in scenarios:
            self.assertIn(rule, document, f"gate does not cover: {label}")

    def test_reasoning_framework_does_not_suppress_user_owned_decisions(self):
        """The always-loaded framework must not bias the model against asking."""
        framework = (WRXP_ROOT / "shared/reasoning-framework.md").read_text()

        self.assertIn(
            "**This preference does NOT extend to user-owned decisions**",
            framework,
        )
        self.assertIn(
            "first resort for user-owned decisions",
            framework,
        )
        self.assertNotIn(
            "- **Prefer calling tools with available information over asking "
            "the user**, unless",
            framework,
        )
        self.assertNotIn(
            "Information only available by asking the user (last resort)",
            framework,
        )

    def test_entry_files_stay_small_enough_to_be_read_every_call(self):
        """Progressive disclosure only works if the entry files are cheap."""
        caps = {"ha": 16_000, "haq": 6_000, "haqq": 6_000, "haqqq": 6_000}
        for name, cap in caps.items():
            size = (WRXP_ROOT / f"skills/{name}/SKILL.md").stat().st_size
            self.assertLessEqual(
                size, cap, f"{name}/SKILL.md grew to {size} bytes (cap {cap})"
            )

    def test_repair_loop_routes_fifth_and_tenth_checkpoints_without_a_hard_cap(self):
        """Valid repairs continue, with agent and user checkpoints at distinct multiples."""
        verification = (
            WRXP_ROOT / "skills/ha/references/verification.md"
        ).read_text()
        policy = parse_named_flat_yaml_block_after(
            verification,
            "## 수정 루프 체크포인트",
            "RepairLoopPolicy",
        )

        self.assertEqual(
            {
                "hard_repair_limit": None,
                "agent_checkpoint_interval": 5,
                "user_checkpoint_interval": 10,
                "user_checkpoint_precedence": True,
                "checkpoint_requires_remaining_work": True,
                "checkpoint_questions_count_toward_discovery_budget": False,
                "approval_questions_count_toward_discovery_budget": False,
                "security_waits_for_checkpoint": False,
                "repair_requires_unmet_acceptance_criterion": True,
                "progress_evidence_required": True,
                "counter_resets_on_checkpoint": False,
            },
            policy,
        )

        section = verification.split("## 수정 루프 체크포인트", 1)[1]
        table_start = section.index("| 검증 결과 | 수정 횟수 | 다음 행동 |")
        table_end = section.index("\n\n", table_start)
        table_lines = section[table_start:table_end].splitlines()[2:]
        routes = [
            tuple(cell.strip().strip("`") for cell in line.strip("|").split("|"))
            for line in table_lines
        ]
        self.assertEqual(
            [
                ("수용 기준 충족", "모든 횟수", "complete"),
                ("결함 잔존", "10의 배수", "user_checkpoint"),
                (
                    "결함 잔존",
                    "10의 배수가 아닌 5의 배수",
                    "agent_checkpoint",
                ),
                ("결함 잔존", "그 외", "continue"),
            ],
            routes,
        )

    def test_all_knife_presets_inherit_one_repair_checkpoint_policy(self):
        verification = (
            WRXP_ROOT / "skills/ha/references/verification.md"
        ).read_text()
        engine = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()

        self.assertEqual(1, verification.count("RepairLoopPolicy:"))
        self.assertIn("references/verification.md", engine)
        for name in ("haq", "haqq", "haqqq"):
            shim = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertIn("../ha/references/verification.md", shim)
            self.assertNotIn("RepairLoopPolicy:", shim)

    def test_ha_is_concise_common_engine_with_progressive_disclosure(self):
        skill_path = WRXP_ROOT / "skills/ha/SKILL.md"
        skill = skill_path.read_text()
        self.assertLessEqual(len(skill.splitlines()), 500)
        self.assertIn("references/questioning.md", skill)
        self.assertIn("references/model-routing.md", skill)
        self.assertIn("references/verification.md", skill)
        self.assertIn("runtime_parallel_limit", skill)
        self.assertIn("질문 프리셋은 모델 라우팅에 영향을 주지 않는다", skill)

        core = parse_flat_yaml_block_after(skill, "## 핵심 계약")
        self.assertEqual(
            {
                "question_preset": "none",
                "min_questions": 0,
                "max_questions": 0,
                "max_questions_per_round": 0,
                "max_rounds": 0,
            },
            core,
        )

    def test_readme_lists_supported_claude_and_codex_install_paths(self):
        readme = (WRXP_ROOT / "README.md").read_text()

        for command in (
            "codex plugin marketplace add donghyunlim/claude-middleware --ref main",
            "codex plugin add wrxp@donghyunlim",
            "codex plugin marketplace upgrade donghyunlim",
            "claude plugin marketplace add donghyunlim/claude-middleware",
            "claude plugin install wrxp@donghyunlim",
            "claude plugin marketplace update donghyunlim",
            "claude plugin update wrxp@donghyunlim",
        ):
            self.assertIn(command, readme)
        self.assertNotIn(
            "claude plugin marketplace add github:donghyunlim/claude-middleware",
            readme,
        )

    def test_haqqq_documents_task_units_and_verification_not_a_opinion_fleet(self):
        benchmark = (WRXP_ROOT / "docs/benchmark/haqqq.md").read_text()

        self.assertIn("task-unit 라우팅", benchmark)
        self.assertIn("독립 verifier", benchmark)
        self.assertIn("관점·가설 fleet은 `/cast`", benchmark)
        for stale_claim in (
            "여러 AI의 답변이 서로 다를 때",
            "다수결",
            "여러 독립 AI의 교차 검증",
            "여러 AI가 독립 분석 후 종합",
        ):
            self.assertNotIn(stale_claim, benchmark)

    def test_knife_frontmatter_preserves_claude_plugin_extensions(self):
        for name in ("ha", "haq", "haqq", "haqqq"):
            text = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            frontmatter = text.split("---", 2)[1]
            self.assertRegex(frontmatter, r'(?m)^argument-hint: "\[요청 내용\]"$')
            self.assertRegex(frontmatter, r"(?m)^level: 4$")

    def test_knife_flow_never_depends_on_skipped_phase_4(self):
        skill = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()
        forbidden = (
            "Phase 4로 jump",
            "Phase 5 → Phase 4",
            "Phase 6 → Phase 4",
            "task-type-specific section of the Phase 4 design document",
            "Phase 5 → Phase 4 → Phase 5",
            "Stage [1|2|3]",
            "Phase 0 two-stage detection cascade",
            "unless the design specifies otherwise",
            "file types listed in the design",
            "design summaries",
        )
        for phrase in forbidden:
            self.assertFalse(
                phrase in skill,
                f"knife flow still depends on skipped Phase 4: {phrase}",
            )

    def test_fast_worker_frontmatter_description_is_quoted(self):
        frontmatter = (
            WRXP_ROOT / "agents/fast-worker.md"
        ).read_text().split("---", 2)[1]
        description_line = next(
            line for line in frontmatter.splitlines()
            if line.startswith("description:")
        )
        self.assertTrue(
            description_line.startswith(('description: "', "description: '")),
            "fast-worker description must be quoted YAML",
        )
        self.assertTrue(
            "unavailable or returns an invalid response" in description_line,
            "fast-worker metadata must describe every fallback cause",
        )

    def test_qwen_has_no_hardcoded_default_api_key(self):
        script = (WRXP_ROOT / "scripts/qwen.py").read_text()
        has_hardcoded_default = (
            "DEFAULT_API_KEY = \"" in script
            or "DEFAULT_API_KEY = '" in script
        )
        self.assertFalse(
            has_hardcoded_default,
            "qwen.py contains a hardcoded default API key",
        )
        self.assertTrue(
            'os.getenv("QWEN_API_KEY")' in script,
            "qwen.py must read QWEN_API_KEY from the environment",
        )


if __name__ == "__main__":
    unittest.main()
