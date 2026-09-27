import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "skills/setup/scripts/setup_global.py"
START = "<!-- WRXP:START -->"
END = "<!-- WRXP:END -->"


class SetupGlobalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / "plugin/skills"
        self.script = self.skills / "setup/scripts/setup_global.py"
        self.script.parent.mkdir(parents=True)
        self.asset = self.skills / "setup/assets/global-rules.md"
        self.asset.parent.mkdir(parents=True)
        self.asset.write_text("Use wrxp:ha and wrxp:cast.\n", encoding="utf-8")
        for name in ("ha", "cast"):
            folder = self.skills / name
            folder.mkdir()
            (folder / "SKILL.md").write_text("skill\n")
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"

    def run_cli(self, *args, env=None):
        if SOURCE.exists():
            shutil.copyfile(SOURCE, self.script)
        process = subprocess.run(
            [sys.executable, str(self.script), *args], cwd=self.root,
            env={**os.environ, "CODEX_HOME": str(self.codex),
                 "CLAUDE_CONFIG_DIR": str(self.claude), **(env or {})},
            text=True, capture_output=True, timeout=10,
        )
        try:
            report = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"CLI did not return JSON: {process.stdout!r} {process.stderr!r}")
        self.assertNotIn("PRIVATE USER CONTENT", process.stdout)
        return process, report

    def test_new_both_targets_and_bundled_inventory(self):
        result, report = self.run_cli("--target", "both", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([t["status"] for t in report["targets"]], ["added", "added"])
        self.assertEqual(report["bundled_skills"], ["cast", "ha"])
        self.assertIn("Use wrxp:ha", (self.codex / "AGENTS.md").read_text())
        self.assertIn(START, (self.claude / "CLAUDE.md").read_text())
        self.assertIn(START, report["managed_block"])
        self.assertEqual(report["managed_block"], (self.codex / "AGENTS.md").read_text())

    def test_default_plan_does_not_create_directories(self):
        result, report = self.run_cli("--target", "both")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["mode"], "plan")
        self.assertEqual([t["status"] for t in report["targets"]], ["added", "added"])
        self.assertFalse(self.codex.exists())
        self.assertFalse(self.claude.exists())

    def test_idempotent_apply_does_not_rewrite_or_backup(self):
        self.run_cli("--target", "codex", "--apply")
        target = self.codex / "AGENTS.md"
        before = target.stat()
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["targets"][0]["status"], "unchanged")
        self.assertEqual(target.stat().st_ino, before.st_ino)
        self.assertFalse(list(self.codex.glob("*.wrxp-backup-*")))

    def test_update_preserves_crlf_and_other_blocks_exactly(self):
        self.codex.mkdir()
        original = ("PRIVATE USER CONTENT\r\n<!-- OMC:START -->\r\nother\r\n"
                    "<!-- OMC:END -->\r\n" + START + "\r\nold\r\n" + END + "\r\ntail\r\n").encode()
        target = self.codex / "AGENTS.md"
        target.write_bytes(original)
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["targets"][0]["status"], "updated")
        self.assertEqual(target.read_bytes(), original.replace(b"old\r\n", b"Use wrxp:ha and wrxp:cast.\r\n"))

    def test_remove_only_managed_block_and_keep_user_text(self):
        self.claude.mkdir()
        target = self.claude / "CLAUDE.md"
        target.write_text("before\n" + START + "\nold\n" + END + "\nafter\n")
        result, report = self.run_cli("--target", "claude", "--remove", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["targets"][0]["status"], "removed")
        self.assertEqual(target.read_text(), "before\nafter\n")

    def test_remove_absent_does_not_create_file(self):
        result, report = self.run_cli("--target", "codex", "--remove", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["targets"][0]["status"], "absent")
        self.assertFalse(self.codex.exists())

    def test_corrupt_second_target_prevents_all_writes(self):
        self.claude.mkdir()
        target = self.claude / "CLAUDE.md"
        original = START + "\n" + START + "\n" + END
        target.write_text(original)
        result, report = self.run_cli("--target", "both", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.codex / "AGENTS.md").exists())
        self.assertTrue(target.read_text().startswith(original))
        self.assertEqual(report["targets"][1]["status"], "appended")
        self.assertTrue(report["targets"][1]["unmanaged_rules"])

    def test_invalid_utf8_is_rejected_before_both_writes(self):
        self.claude.mkdir()
        (self.claude / "CLAUDE.md").write_bytes(b"\xff")
        result, _ = self.run_cli("--target", "both", "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.codex.exists())

    def test_environment_homes_and_relative_explicit_home(self):
        result, _ = self.run_cli("--target", "both", "--apply", env={
            "CODEX_HOME": str(self.root / "env-codex"),
            "CLAUDE_CONFIG_DIR": str(self.root / "env-claude")})
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.root / "env-codex/AGENTS.md").exists())
        self.assertTrue((self.root / "env-claude/CLAUDE.md").exists())
        result, report = self.run_cli("--target", "codex", "--codex-home", "relative", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(Path(report["targets"][0]["path"]).resolve(), (self.root / "relative/AGENTS.md").resolve())

    def test_nonempty_override_is_active_codex_target(self):
        self.codex.mkdir()
        (self.codex / "AGENTS.override.md").write_text("override\n")
        (self.codex / "AGENTS.md").write_text("regular\n")
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertIn(START, (self.codex / "AGENTS.override.md").read_text())
        self.assertEqual((self.codex / "AGENTS.md").read_text(), "regular\n")
        self.assertTrue(report["targets"][0]["warnings"])

    def test_empty_override_uses_agents_md(self):
        self.codex.mkdir()
        (self.codex / "AGENTS.override.md").write_text("")
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(Path(report["targets"][0]["path"]).name, "AGENTS.md")

    def test_symlink_target_and_dangling_symlink_are_rejected(self):
        for dangling in (False, True):
            with self.subTest(dangling=dangling):
                self.codex.mkdir(exist_ok=True)
                target = self.codex / "AGENTS.md"
                destination = self.root / "elsewhere"
                if not dangling:
                    destination.write_text("safe")
                target.symlink_to(destination)
                result, _ = self.run_cli("--target", "codex", "--apply")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(destination.exists(), not dangling)
                target.unlink()
                destination.unlink(missing_ok=True)

    def test_backup_has_exact_bytes_and_owner_only_mode(self):
        self.codex.mkdir()
        target = self.codex / "AGENTS.md"
        original = b"PRIVATE USER CONTENT\n"
        target.write_bytes(original)
        target.chmod(0o640)
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        backup = Path(report["targets"][0]["backup"])
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_check_reports_drift_then_current_without_writes(self):
        result, report = self.run_cli("--target", "codex", "--check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["mode"], "check")
        self.assertFalse(self.codex.exists())
        self.run_cli("--target", "codex", "--apply")
        result, report = self.run_cli("--target", "codex", "--check")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["targets"][0]["status"], "unchanged")

    def test_missing_referenced_skill_rejects_apply(self):
        self.asset.write_text("Use wrxp:unknown.\n")
        result, _ = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.codex.exists())

    def test_nested_wrxp_block_in_other_tool_region_rejected(self):
        self.codex.mkdir()
        target = self.codex / "AGENTS.md"
        original = "<!-- OMC:START -->\n" + START + "\nx\n" + END + "\n<!-- OMC:END -->\n"
        target.write_text(original)
        result, _ = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(target.read_text().startswith(original))
        self.assertEqual(target.read_text().count("Use wrxp:ha"), 1)

    def test_ambiguous_legacy_is_append_only_idempotent_and_removable(self):
        cases = {
            "duplicate": START + "\nold\n" + END + "\n" + START + "\nold2\n" + END + "\n",
            "missing_end": START + "\nold\n",
            "reversed": END + "\nold\n" + START + "\n",
            "nested": START + "\n" + START + "\nold\n" + END + "\n" + END + "\n",
            "unclosed_other": "<!-- OMC:START -->\nprivate\n",
        }
        for label, original in cases.items():
            with self.subTest(label=label):
                home = self.root / label
                home.mkdir()
                target = home / "AGENTS.md"
                target.write_text(original)
                args = ("--target", "codex", "--codex-home", str(home))
                result, report = self.run_cli(*args, "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["targets"][0]["status"], "appended")
                self.assertTrue(target.read_text().startswith(original))
                installed = target.read_bytes()
                before = target.stat().st_mtime_ns
                backups = list(home.glob("*.wrxp-backup-*"))
                result, report = self.run_cli(*args, "--check")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["targets"][0]["status"], "unchanged")
                self.assertTrue(report["targets"][0]["unmanaged_rules"])
                result, report = self.run_cli(*args, "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(target.read_bytes(), installed)
                self.assertEqual(target.stat().st_mtime_ns, before)
                self.assertEqual(list(home.glob("*.wrxp-backup-*")), backups)
                self.asset.write_text("Updated wrxp:ha rule.\n")
                result, report = self.run_cli(*args, "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["targets"][0]["status"], "updated")
                self.assertTrue(target.read_text().startswith(original))
                self.assertIn("Updated wrxp:ha rule.", target.read_text())
                result, report = self.run_cli(*args, "--remove", "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), original)
                self.assertTrue(report["targets"][0]["unmanaged_rules"])
                self.asset.write_text("Use wrxp:ha and wrxp:cast.\n")

    def test_fenced_inline_and_indented_examples_are_never_owned(self):
        original = ("```md trailing info\n" + START + "\nexample\n" + END + "\n```\n"
                    "~~~yaml\n" + START + "\nexample\n" + END + "\n~~~\n"
                    "Inline `" + START + "` and `" + END + "`.\n"
                    "    " + START + "\n    " + END + "\n")
        self.codex.mkdir()
        target = self.codex / "AGENTS.md"
        target.write_text(original)
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(target.read_text().startswith(original))
        self.assertEqual(report["targets"][0]["status"], "added")
        result, report = self.run_cli("--target", "codex", "--remove", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), original)

    def test_unclosed_fence_and_comment_restore_exact_original_on_remove(self):
        for label, original in (("fence", "text\n~~~md\n" + START + "\nexample"),
                                ("comment", "text\n<!-- example\n" + START + "\nexample")):
            with self.subTest(label=label):
                home = self.root / label
                home.mkdir()
                target = home / "AGENTS.md"
                target.write_text(original)
                args = ("--target", "codex", "--codex-home", str(home))
                result, report = self.run_cli(*args, "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertTrue(target.read_text().startswith(original))
                self.assertIn("Use wrxp:ha", target.read_text())
                result, report = self.run_cli(*args, "--remove", "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), original)

    def test_missing_or_corrupt_ownership_record_never_grants_legacy_ownership(self):
        for label in ("missing", "corrupt"):
            with self.subTest(label=label):
                home = self.root / label
                args = ("--target", "codex", "--codex-home", str(home))
                self.run_cli(*args, "--apply")
                target = home / "AGENTS.md"
                lines = target.read_text().splitlines(keepends=True)
                if label == "missing":
                    damaged = "".join(lines[1:])
                else:
                    damaged = lines[0].replace("sha256=", "sha256=" + "0") + "".join(lines[1:])
                target.write_text(damaged)
                result, report = self.run_cli(*args, "--remove", "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), damaged)
                self.assertTrue(report["targets"][0]["unmanaged_rules"])
                result, report = self.run_cli(*args, "--apply")
                self.assertEqual(result.returncode, 0)
                self.assertTrue(target.read_text().startswith(damaged))

    def test_malformed_other_region_does_not_authorize_legacy_replacement(self):
        self.codex.mkdir()
        target = self.codex / "AGENTS.md"
        original = ("<!-- OMC:END -->\n" + START + "\nprivate legacy\n" + END +
                    "\n<!-- OMC:START -->\n")
        target.write_text(original)
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(target.read_text().startswith(original))
        self.assertEqual(report["targets"][0]["status"], "appended")
        result, report = self.run_cli("--target", "codex", "--remove", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), original)
        self.assertTrue(report["targets"][0]["unmanaged_rules"])

    def test_comment_reopened_on_same_line_is_closed_before_rules(self):
        original = "intro <!-- closed --> tail <!-- open\nexample"
        self.codex.mkdir()
        target = self.codex / "AGENTS.md"
        target.write_text(original)
        result, report = self.run_cli("--target", "codex", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(target.read_text().startswith(original))
        self.assertEqual(report["targets"][0]["status"], "added")
        self.assertIn("-->\n<!-- WRXP:OWNED", target.read_text())
        result, _ = self.run_cli("--target", "codex", "--remove", "--apply")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), original)


if __name__ == "__main__":
    unittest.main()
