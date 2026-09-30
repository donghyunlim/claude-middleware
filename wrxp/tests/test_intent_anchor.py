import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


WRXP_ROOT = Path(__file__).resolve().parents[1]
SHARED = WRXP_ROOT / "shared/scripts/user_turns.py"
WRAPPER = WRXP_ROOT / "skills/handoff/scripts/user_turns.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(records, directory=None, name=None) -> Path:
    directory = Path(directory or tempfile.mkdtemp())
    path = directory / (name or "session.jsonl")
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def claude_user(text, timestamp="t"):
    return {"type": "user", "timestamp": timestamp, "message": {"content": text}}


def claude_assistant(text="ok"):
    return {"type": "assistant", "timestamp": "t",
            "message": {"content": [{"type": "text", "text": text}]}}


class SharedExtractorTests(unittest.TestCase):
    def test_numbered_matches_render_numbering(self):
        ut = load(SHARED, "shared_user_turns")
        turns = [
            ("t1", "같은 말", "user"), ("t2", "같은 말", "user"),
            ("t3", "[compaction point]", "marker"), ("t4", "다음", "user"),
            ("t5", "", "assistant"), ("t6", "[question tool answer]\nA", "answer"),
        ]
        self.assertEqual(
            [(1, "t1", "같은 말", "turn"), (1, "t2", "", "resent"),
             (0, "t3", "[compaction point]", "marker"), (2, "t4", "다음", "turn"),
             (3, "t6", "[question tool answer]\nA", "turn")],
            list(ut.numbered(turns)),
        )

    def test_handoff_wrapper_exposes_patchable_globals(self):
        wrapper = load(WRAPPER, "handoff_user_turns_wrapper")
        self.assertTrue(callable(wrapper.numbered))
        with mock.patch.object(wrapper, "CLAUDE_PROJECTS", Path("/nonexistent")):
            self.assertIsNone(wrapper.find_claude_log("x"))

    def test_handoff_wrapper_runs_as_a_script(self):
        log = write_jsonl([claude_user("첫 요청")])
        result = subprocess.run(
            [sys.executable, str(WRAPPER), "--log", str(log)],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("## U1 t\n첫 요청", result.stdout)


if __name__ == "__main__":
    unittest.main()
