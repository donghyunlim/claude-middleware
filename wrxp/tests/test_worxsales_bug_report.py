import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

WRXP_ROOT = Path(__file__).resolve().parents[1]
SKILL = WRXP_ROOT / "skills/worxsales-bug-report"
CONNECT = SKILL / "scripts/connect.py"


def load_connect():
    spec = importlib.util.spec_from_file_location("wxbr_connect", CONNECT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorxsalesBugReportTests(unittest.TestCase):
    def run_connect(self, key):
        env = {k: v for k, v in os.environ.items() if k != "WXBR_KEY"}
        if key is not None:
            env["WXBR_KEY"] = key
        return subprocess.run([sys.executable, str(CONNECT), "--target", "claude", "--check-only"],
                              capture_output=True, text=True, env=env, timeout=30)

    def test_missing_or_malformed_key_stops_before_any_network_call(self):
        for key in (None, "", "not-a-key"):
            result = self.run_connect(key)
            self.assertEqual(result.returncode, 2)
            self.assertIn("WXBR_KEY", result.stderr)

    def test_server_is_launched_through_pinned_mcp_remote_with_env_header(self):
        connect = load_connect()
        args = connect.launch_args()
        self.assertRegex(connect.MCP_REMOTE, r"^mcp-remote@\d+\.\d+\.\d+$")
        self.assertIn("Authorization:${WXBR_AUTH}", args)
        self.assertNotIn("wxbrm_", " ".join(args))
        self.assertRegex(connect.PINNED_SHA256, r"^[0-9A-F]{64}$")

    def test_skill_documents_the_entry_point_and_never_embeds_a_key(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("scripts/connect.py", text)
        self.assertNotRegex(text, r"wxbrm_[A-Za-z0-9_-]{8,}")
        self.assertTrue((SKILL / "agents/openai.yaml").exists())


if __name__ == "__main__":
    unittest.main()
