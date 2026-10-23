import importlib.util
import sys
import unittest
from pathlib import Path

WRXP_ROOT = Path(__file__).resolve().parents[1]
DASH = WRXP_ROOT / "skills/worxsales-qa-dashboard-update"
CHAIN = WRXP_ROOT / "skills/worxsales-qa-all-in-one"
RERUN = WRXP_ROOT / "skills/worxsales-qa-rerun-not-ok"
CHAIN_NOT_OK = WRXP_ROOT / "skills/worxsales-qa-all-in-one-not-ok"
BOOT = WRXP_ROOT / "skills/worxsales-qa-bootstrap"
# which skill entry points may name which QA skills
MAY_NAME = {
    "worxsales-qa-dashboard-update": {"worxsales-qa-all-in-one", "worxsales-qa-all-in-one-not-ok"},
    "worxsales-qa-all-in-one": {"worxsales-qa-rerun-not-ok", "worxsales-qa-all-in-one-not-ok"},
    "worxsales-qa-rerun-not-ok": {"worxsales-qa-all-in-one-not-ok"},
    "worxsales-qa-all-in-one-not-ok": set(),
}


def load(name):
    sys.path.insert(0, str(DASH / "scripts"))
    spec = importlib.util.spec_from_file_location(name, DASH / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ExplicitInvocationTests(unittest.TestCase):
    def test_new_skills_require_explicit_invocation_on_both_runtimes(self):
        for skill in (DASH, CHAIN, RERUN, CHAIN_NOT_OK, BOOT):
            frontmatter = (skill / "SKILL.md").read_text().split("---", 2)[1]
            if skill == CHAIN:
                # v0.1.61 dropped disable-model-invocation so a run the user scheduled (CronCreate) can start the chain;
                # the description still limits it to explicit or scheduled invocation.
                self.assertNotIn("disable-model-invocation", frontmatter)
                self.assertIn("Use only when the user explicitly invokes", frontmatter)
                self.assertIn("scheduled", frontmatter)
            else:
                self.assertRegex(frontmatter, r"(?m)^disable-model-invocation: true$", skill.name)
            self.assertRegex((skill / "agents/openai.yaml").read_text(), r"(?m)^policy:\n  allow_implicit_invocation: false$", skill.name)

    def test_only_the_chains_name_the_qa_skills(self):
        for path in (WRXP_ROOT / "skills").glob("*/SKILL.md"):
            text = path.read_text()
            for name, allowed in MAY_NAME.items():
                if path.parent.name != name and path.parent.name not in allowed:
                    self.assertNotIn(name, text, f"{path} names {name}")
        chain = (CHAIN / "SKILL.md").read_text()
        for name in ("worxsales-qa-refresh", "worxsales-qa-executor", "worxsales-qa-dashboard-update"):
            self.assertIn(name, chain)
        chain_not_ok = (CHAIN_NOT_OK / "SKILL.md").read_text()
        for name in ("worxsales-qa-refresh", "worxsales-qa-rerun-not-ok", "worxsales-qa-dashboard-update"):
            self.assertIn(name, chain_not_ok)


class ServePageTests(unittest.TestCase):
    def test_a_hanging_client_does_not_block_other_viewers(self):
        import socket, subprocess, tempfile, time, urllib.request
        d = Path(tempfile.mkdtemp()); (d / "index.html").write_text("<p>ok</p>")
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        srv = subprocess.Popen(["/usr/bin/perl", str(DASH / "scripts/serve_page.pl"), str(d), str(port)])
        try:
            for _ in range(50):
                try: socket.create_connection(("127.0.0.1", port), timeout=1).close(); break
                except OSError: time.sleep(0.1)
            hang = socket.create_connection(("127.0.0.1", port))  # connects, never sends a request
            body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read()
            self.assertEqual(body, b"<p>ok</p>")
            hang.close()
        finally:
            srv.kill(); srv.wait()


class PruneBuildsTests(unittest.TestCase):
    def test_removes_only_sibling_qa_build_worktrees_except_the_kept_one(self):
        import subprocess, tempfile
        d = Path(tempfile.mkdtemp()); repo = d / "repo"; builds = d / "scratch"
        builds.mkdir(); repo.mkdir()
        run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)
        run("git", "init", "-q"); run("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x")
        for name in ("desktop-dev-old", "desktop-dev-new", "desktop-stg", "other-work"):
            run("git", "worktree", "add", "-q", "--detach", str(builds / name))
        run("git", "worktree", "add", "-q", "--detach", str(d / "desktop-dev-elsewhere"))
        subprocess.run(["sh", str(CHAIN / "scripts/prune_builds.sh"), str(repo), str(builds / "desktop-dev-new")], check=True, capture_output=True)
        left = sorted(p.name for p in builds.iterdir())
        self.assertEqual(left, ["desktop-dev-new", "other-work"])
        self.assertTrue((d / "desktop-dev-elsewhere").exists())

    def test_chains_prune_builds_after_rollout_and_clear_lane_tmp(self):
        for skill in (CHAIN, RERUN):
            text = (skill / "SKILL.md").read_text()
            self.assertIn("prune_builds.sh", text, skill.name)
            self.assertIn("_tmp/", text, skill.name)


class SelectNotOkTests(unittest.TestCase):
    def test_picks_not_ok_unrun_and_ok_rows_changed_after_the_ok(self):
        import json, subprocess, tempfile
        d = Path(tempfile.mkdtemp())
        (d / "scenarios/07").mkdir(parents=True); (d / "runs/lane").mkdir(parents=True); (d / "refresh").mkdir()
        rows = [{"tc_id": t, "menu": "7. 고객", "policy": p} for t, p in
                (("TC-OK", "확정"), ("TC-OKCHG", "확정"), ("TC-PART", "확정"), ("TC-NEW", "확정"), ("TC-OOS", "범위 제외"), ("TC-OKOLD", "확정"))]
        (d / "scenarios/07/a.json").write_text(json.dumps(rows, ensure_ascii=False))
        res = {"TC-OK": "OK", "TC-OKCHG": "OK", "TC-PART": "부분 OK", "TC-OOS": "미구현", "TC-OKOLD": "OK"}
        for t, v in res.items():
            day = "2026-10-13" if t == "TC-OKOLD" else "2026-10-11"
            (d / f"runs/lane/{t}.json").write_text(json.dumps({"verdict": v, "ended_at": f"{day}T10:00:00+0900"}, ensure_ascii=False))
        (d / "scenarios/07/_changed_ids_2026-10-12.txt").write_text("TC-OKCHG\nTC-OKOLD\n")
        (d / "refresh/lanes.json").write_text(json.dumps([{"dir": "runs/lane"}]))
        (d / "refresh/watch.json").write_text(json.dumps({"lanes": "refresh/lanes.json"}))
        subprocess.run([sys.executable, str(RERUN / "scripts/select_not_ok.py"), "refresh/watch.json", "--out", "ids.txt"],
                       cwd=d, check=True, capture_output=True)
        self.assertEqual((d / "ids.txt").read_text().split(), ["TC-OKCHG", "TC-PART", "TC-NEW"])


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
        for skill in (DASH, CHAIN, RERUN, CHAIN_NOT_OK, BOOT):
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

    def test_local_publish_writes_home_dir_and_checks_verify_url(self):
        import http.server, json, os, tempfile, threading
        home = Path(tempfile.mkdtemp()); d = Path(tempfile.mkdtemp())
        served = home / "dash"
        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(served), **k)
        srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        verify = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
        (d / "watch.json").write_text(json.dumps({"dashboard": {"publish": {"ssh_host": "local", "remote_dir": "dash",
                                                  "url": "http://example.local:8090/", "verify_url": verify}}}))
        (d / "p.html").write_text("<!doctype html><title>t</title>")
        import subprocess
        out = subprocess.run([sys.executable, str(DASH / "scripts/publish_page.py"), str(d / "watch.json"), str(d / "p.html")],
                             capture_output=True, text=True, env={**os.environ, "HOME": str(home)})
        srv.shutdown()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("published: http://example.local:8090/", out.stdout)
        self.assertEqual((served / "index.html").read_text(), "<!doctype html><title>t</title>")

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
