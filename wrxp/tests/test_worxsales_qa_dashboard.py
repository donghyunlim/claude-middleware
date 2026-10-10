import importlib.util
import sys
import unittest
from pathlib import Path

WRXP_ROOT = Path(__file__).resolve().parents[1]
DASH = WRXP_ROOT / "skills/worxsales-qa-dashboard-update"
CHAIN = WRXP_ROOT / "skills/worxsales-qa-all-in-one"


def load(name):
    sys.path.insert(0, str(DASH / "scripts"))
    spec = importlib.util.spec_from_file_location(name, DASH / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ExplicitInvocationTests(unittest.TestCase):
    def test_new_skills_require_explicit_invocation_on_both_runtimes(self):
        for skill in (DASH, CHAIN):
            frontmatter = (skill / "SKILL.md").read_text().split("---", 2)[1]
            self.assertRegex(frontmatter, r"(?m)^disable-model-invocation: true$", skill.name)
            self.assertRegex((skill / "agents/openai.yaml").read_text(), r"(?m)^policy:\n  allow_implicit_invocation: false$", skill.name)

    def test_only_the_chain_names_the_qa_skills(self):
        names = ("worxsales-qa-dashboard-update", "worxsales-qa-all-in-one")
        for path in (WRXP_ROOT / "skills").glob("*/SKILL.md"):
            for name in names:
                if path.parent.name not in (name, "worxsales-qa-all-in-one"):
                    self.assertNotIn(name, path.read_text(), str(path))
        chain = (CHAIN / "SKILL.md").read_text()
        for name in ("worxsales-qa-refresh", "worxsales-qa-executor", "worxsales-qa-dashboard-update"):
            self.assertIn(name, chain)


class BlockReasonTests(unittest.TestCase):
    def setUp(self):
        self.h = load("history")

    def test_first_matching_group_wins(self):
        r = {"outcome": "실제 발송 버튼이라 이번 실행의 쓰기 범위 밖이며, 데이터도 없습니다"}
        self.assertEqual(self.h.block_reason(r), "쓰기 범위 밖")

    def test_reads_details_reason_and_falls_back_to_other(self):
        self.assertEqual(self.h.block_reason({"details": {"verdict_reason": "LEAD_POPULATION_NOT_CONFIGURED 응답"}}), "서버 설정·응답 오류")
        self.assertEqual(self.h.block_reason({"outcome": "CORE_SOURCE_UNAVAILABLE"}), "원천 미연결")
        self.assertEqual(self.h.block_reason({"outcome": "알 수 없는 이유"}), "기타")


class SummaryBlockTests(unittest.TestCase):
    def test_summary_is_one_span_from_marker_to_divider(self):
        s = load("sync_notion")
        rnd = {"round": 2, "build": "abc1234", "end": "2026-10-10T17:00", "target": 10, "executed": 8, "coverage": 80.0,
               "impl_rate": 50.0, "unimpl_rate": 25.0, "problem": 1, "problem_new": 1, "problem_resolved": 0,
               "verdicts": {"OK": 3, "부분 OK": 1, "미구현": 2, "실행 불가": 2}, "blocked": {"데이터 없음": 2, "기타": 0},
               "role_gap": 0, "write_blocked": 0, "write_blocked_new": []}
        blocks = s.summary_blocks({"rounds": [dict(rnd, round=1, impl_rate=40.0), rnd]}, "https://claude.ai/artifact/x")
        self.assertEqual(blocks[0]["type"], "heading_2")
        self.assertTrue(blocks[0]["heading_2"]["rich_text"][0]["text"]["content"].startswith(s.MARKER))
        self.assertEqual(blocks[-1]["type"], "divider")
        self.assertEqual(sum(b["type"] == "divider" for b in blocks), 1)
        text = " ".join(b.get("bulleted_list_item", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "") for b in blocks)
        self.assertIn("+10.0p", text)
        self.assertNotIn("—", text)


class PortabilityTests(unittest.TestCase):
    def test_skill_files_carry_no_personal_paths_or_ids(self):
        for skill in (DASH, CHAIN):
            for path in skill.rglob("*"):
                if path.is_file() and path.suffix in (".md", ".py", ".sh", ".pl", ".yaml") and ".omc" not in path.parts:
                    text = path.read_text()
                    for bad in ("/Users/", "/private/tmp", "claude-501", "2230116"):
                        self.assertNotIn(bad, text, str(path))

    def test_publish_without_config_stays_local(self):
        import json, subprocess, tempfile
        d = Path(tempfile.mkdtemp())
        (d / "watch.json").write_text(json.dumps({"dashboard": {"page_id": "x"}}))
        (d / "p.html").write_text("<!doctype html><title>t</title>")
        out = subprocess.run([sys.executable, str(DASH / "scripts/publish_page.py"), str(d / "watch.json"), str(d / "p.html")],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("local only: file://", out)

    def test_rendered_page_is_a_complete_document(self):
        src = (DASH / "scripts/render_html.py").read_text()
        self.assertIn("<!doctype html>", src)
        self.assertIn('<meta charset="utf-8">', src)

    def test_queue_only_ids_limits_rows(self):
        import json, subprocess, tempfile
        d = Path(tempfile.mkdtemp())
        (d / "scenarios/07").mkdir(parents=True)
        rows = [{"tc_id": t, "policy": "결정 완료", "role": "영업자", "access": "수정 가능", "external": False, "menu": "7. 고객"} for t in ("TC-A", "TC-B")]
        (d / "scenarios/07/a.json").write_text(json.dumps(rows, ensure_ascii=False))
        (d / "ids.txt").write_text("TC-B\n")
        (d / "run").mkdir()
        subprocess.run([sys.executable, str(CHAIN / "scripts/qa_queue.py"), "build", "run", "--only-ids", "ids.txt"], cwd=d, check=True, capture_output=True)
        self.assertEqual([r["tc_id"] for r in json.loads((d / "run/queue.json").read_text())], ["TC-B"])


if __name__ == "__main__":
    unittest.main()
