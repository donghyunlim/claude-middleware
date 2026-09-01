import json
import unittest
from pathlib import Path


WRXP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WRXP_ROOT.parent


class WrxpInvariantTests(unittest.TestCase):
    def test_packaging_and_docs_layout_is_installable(self):
        self.assertFalse((WRXP_ROOT / "CLAUDE.md").exists())
        self.assertTrue((WRXP_ROOT / "docs/fast-worker-routing.md").exists())
        package = json.loads((WRXP_ROOT / "package.json").read_text())
        self.assertIn("docs/fast-worker-routing.md", package["files"])
        self.assertNotIn("CLAUDE.md", package["files"])

    def test_readme_does_not_claim_nonexistent_ha_artifacts(self):
        readme = (WRXP_ROOT / "README.md").read_text()
        for artifact in ("ha-ambiguity", "ha-design", "ha-fleet"):
            self.assertFalse(
                artifact in readme,
                f"README claims nonexistent /ha artifact: {artifact}",
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
            {"0.1.24"},
            {plugin_version, package_version, marketplace_version},
        )

    def test_codex_56_model_registry_is_centralized_in_ha(self):
        skill = (WRXP_ROOT / "skills/ha/SKILL.md").read_text()

        expected_pairs = (
            ("gpt-5.6-sol", "high"),
            ("gpt-5.6-terra", "medium"),
            ("gpt-5.6-luna", "low"),
        )
        for model, effort in expected_pairs:
            self.assertTrue(
                f"model: {model}\n  reasoning_effort: {effort}" in skill,
                f"missing model registry entry: {model}/{effort}",
            )

        self.assertIn(
            "질문 깊이와 모델 라우팅은 서로 독립적인 축이다",
            skill,
        )
        self.assertIn("모든 Codex 위임에", skill)

    def test_tier_shims_only_supply_routing_bias(self):
        expected = {
            "haq": "cost-first",
            "haqq": "balanced",
            "haqqq": "quality-first",
        }
        for name, bias in expected.items():
            skill = (WRXP_ROOT / f"skills/{name}/SKILL.md").read_text()
            self.assertTrue(
                f"routing_bias: {bias}" in skill,
                f"missing routing bias for {name}: {bias}",
            )

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
