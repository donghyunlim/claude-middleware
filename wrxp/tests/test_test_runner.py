import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "skills/test-runner/scripts/run_tests.py"


class TestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_command(self, command, options=()):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--cwd", str(self.root),
             "--output-dir", str(self.root), *options, "--", *command],
            capture_output=True, text=True, timeout=10,
        )
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result, json.loads(result.stdout)

    def test_command_arguments_and_both_streams_are_preserved(self):
        literal = "$(touch should-not-exist); *"
        result, record = self.run_command([
            sys.executable, "-c", "import sys; print(sys.argv[1]); print('err', file=sys.stderr)", literal,
        ])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(record["execution_status"], "completed")
        self.assertEqual(Path(record["stdout"]["path"]).read_text(), literal + "\n")
        self.assertEqual(Path(record["stderr"]["path"]).read_text(), "err\n")
        self.assertFalse((self.root / "should-not-exist").exists())
        self.assertEqual(json.loads(Path(record["record_path"]).read_text()), record)

    def test_nonzero_test_exit_is_not_a_runner_start_failure(self):
        result, record = self.run_command([sys.executable, "-c", "print('FAILED'); raise SystemExit(3)"])
        self.assertEqual(result.returncode, 3)
        self.assertEqual(record["command_exit_code"], 3)
        self.assertEqual(record["execution_status"], "completed")

    def test_missing_command_is_not_started(self):
        result, record = self.run_command([str(self.root / "not-an-executable")])
        self.assertEqual(result.returncode, 127)
        self.assertEqual(record["execution_status"], "not_started")
        self.assertIsNone(record["command_exit_code"])

    def test_timeout_retains_partial_output_and_is_not_success(self):
        result, record = self.run_command(
            [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(5)"],
            ("--timeout", "0.3"),
        )
        self.assertEqual(result.returncode, 124)
        self.assertEqual(record["execution_status"], "timed_out")
        self.assertIn("started", Path(record["stdout"]["path"]).read_text())

    def test_large_logs_keep_full_evidence_with_bounded_preview(self):
        result, record = self.run_command([sys.executable, "-c", "print('a'*50000)"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(Path(record["stdout"]["path"]).stat().st_size, 50001)
        self.assertTrue(record["stdout"]["preview_truncated"])
        self.assertLessEqual(len(record["stdout"]["preview"]), 8192)

    def test_source_context_is_opt_in_and_detects_changes(self):
        source = self.root / "module.py"
        source.write_text("original\n")
        result, record = self.run_command(
            [sys.executable, "-c", "from pathlib import Path; Path('module.py').write_text('changed')"],
            ("--source", "module.py"),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("1: original", record["sources"][0]["text"])
        self.assertTrue(record["sources"][0]["changed_during_run"])
        self.assertNotEqual(record["sources"][0]["sha256_before"], record["sources"][0]["sha256_after"])

    def test_output_runs_do_not_overwrite_previous_evidence(self):
        command = [sys.executable, "-c", "print('ok')"]
        _, first = self.run_command(command)
        _, second = self.run_command(command)
        self.assertNotEqual(first["record_path"], second["record_path"])
        self.assertTrue(Path(first["record_path"]).is_file())

    def test_source_preview_is_bounded_but_hash_covers_whole_file(self):
        import hashlib
        raw = b"x" * 30000
        (self.root / "large.py").write_bytes(raw)
        _, record = self.run_command([sys.executable, "-c", "pass"], ("--source", "large.py"))
        source = record["sources"][0]
        self.assertTrue(source["preview_truncated"])
        self.assertEqual(source["sha256_before"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(source["changed_during_run"])
        self.assertLess(len(source["text"]), 24100)

    def test_numbered_source_preview_respects_total_byte_budget(self):
        (self.root / "lines.py").write_bytes(b"\n" * 24000)
        (self.root / "other.py").write_text("print('other')\n")
        _, record = self.run_command([sys.executable, "-c", "pass"],
                                    ("--source", "lines.py", "--source", "other.py"))
        self.assertLessEqual(sum(len(s["text"].encode()) for s in record["sources"]), 24000)
        self.assertTrue(record["sources"][0]["preview_truncated"])

    def test_late_descendant_output_cannot_change_recorded_log(self):
        import hashlib
        import time
        child = "import time; time.sleep(0.2); print('late')"
        parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); print('early',flush=True)"
        _, record = self.run_command([sys.executable, "-c", parent])
        time.sleep(0.4)
        raw = Path(record["stdout"]["path"]).read_bytes()
        self.assertEqual(record["stdout"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record["stdout"]["bytes"], len(raw))


if __name__ == "__main__":
    unittest.main()
