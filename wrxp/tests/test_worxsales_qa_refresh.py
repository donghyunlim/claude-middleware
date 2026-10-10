import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WRXP_ROOT = Path(__file__).resolve().parents[1]
SKILL = WRXP_ROOT / "skills/worxsales-qa-refresh"
DIFF = SKILL / "scripts/diff_sources.py"
PATTERN = r"(?P<family>[a-z_]+?)_v(?P<ver>\d+(?:\.\d+)*)\.html"


def page(pid, title, parent, sha1="s", files=(), links=(), root="기능정의서", kind="page"):
    return {"id": pid, "kind": kind, "title": title, "parent": parent, "path": ["기능정의서"], "root": root,
            "last_edited": "2026-10-10T00:00:00.000Z", "archived": False, "sha1": sha1, "files": list(files), "links": list(links)}


class DiffSourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "sources/10_quote").mkdir(parents=True)
        self.watch = {"roots": [{"name": "기능정의서", "kind": "tree", "id": "root"}], "sources_dir": str(self.tmp / "sources"),
                      "ignore": {}, "mockup": {"pattern": PATTERN, "family": "worxsales_mockup", "used_version": "1.7"}}

    def crawl(self, name, nodes, bodies):
        d = self.tmp / name
        (d / "pages").mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"roots": [], "nodes": {n["id"]: n for n in nodes}}, ensure_ascii=False))
        for pid, text in bodies.items():
            (d / "pages" / f"{pid}.md").write_text(f"# t\n\nsource: https://app.notion.com/p/{pid}\nlast_edited: x\n\n{text}\n")
        return d

    def local(self, pid, text, name="a.md"):
        (self.tmp / "sources/10_quote" / name).write_text(f"# t\n\nsource: https://app.notion.com/p/{pid}\nlast_edited: x\n\n{text}\n")

    def run_diff(self, new, prev=None):
        w = self.tmp / "watch.json"
        w.write_text(json.dumps(self.watch, ensure_ascii=False))
        args = [sys.executable, str(DIFF), str(w), str(new), "--out", str(self.tmp / "r.json")] + (["--prev", str(prev)] if prev else [])
        code = subprocess.run(args, capture_output=True, text=True).returncode
        return code, json.loads((self.tmp / "r.json").read_text())

    def test_new_child_inside_parent_is_reported_even_when_parent_is_unchanged(self):
        a, b, c = "a" * 32, "b" * 32, "c" * 32
        prev = self.crawl("p", [page(a, "10. 견적", None), page(b, "10-1", a)], {a: "x", b: "y"})
        new = self.crawl("n", [page(a, "10. 견적", None), page(b, "10-1", a), page(c, "10-14 새 화면", a)], {a: "x", b: "y", c: "z"})
        self.local(a, "x", "a.md"); self.local(b, "y", "b.md")
        code, rep = self.run_diff(new, prev)
        self.assertEqual(code, 1)
        self.assertEqual([x["id"] for x in rep["added"]], [c])
        self.assertEqual([x["id"] for x in rep["local_missing"]], [c])
        self.assertEqual(rep["edited"], [])

    def test_latest_mockup_is_chosen_by_number_not_list_order(self):
        m = "d" * 32
        files = ["worxsales_mockup_v1.8.3.html", "worxsales_mockup_v1.10.html", "worxsales_mockup_v1.9.html", "worxsales_mockup_v1.7.html"]
        new = self.crawl("n", [page(m, "최신 버전 목업", None, files=files, root="목업 DB", kind="db_row")], {m: ""})
        code, rep = self.run_diff(new)
        entry = rep["mockup"][0]
        self.assertEqual(entry["latest"], "1.10")
        self.assertTrue(entry["newer_than_used"])

    def test_clean_state_exits_zero_and_ignore_needs_an_entry(self):
        a, gone = "a" * 32, "e" * 32
        new = self.crawl("n", [page(a, "10. 견적", None)], {a: "x"})
        self.local(a, "x", "a.md"); self.local(gone, "old", "gone.md")
        code, rep = self.run_diff(new)
        self.assertEqual(code, 1)
        self.assertEqual([x["id"] for x in rep["local_orphan"]], [gone])
        self.watch["ignore"] = {gone: "사용자 결정: 보관용 사본"}
        code, rep = self.run_diff(new)
        self.assertEqual(code, 0, rep["attention"])

    def test_first_run_keeps_discoveries_as_baseline_and_second_run_flags_only_new_ones(self):
        a, d1, d2 = "a" * 32, "f" * 32, "9" * 32
        disc = lambda i, t: {"id": i, "kind": "discovered", "title": t, "parent": "x", "path": ["TF"], "root": "TF", "keyword_hit": True}
        self.local(a, "x")
        first = self.crawl("n1", [page(a, "10. 견적", None), disc(d1, "옛 목업")], {a: "x"})
        code, rep = self.run_diff(first)
        self.assertEqual(code, 0, rep["attention"])
        self.assertEqual(len(rep["baseline_discovered"]), 1)
        second = self.crawl("n2", [page(a, "10. 견적", None), disc(d1, "옛 목업"), disc(d2, "새 목업 v2")], {a: "x"})
        code, rep = self.run_diff(second, first)
        self.assertEqual([x["id"] for x in rep["discovered_new"]], [d2])

    def test_property_only_change_on_a_policy_row_is_detected(self):
        a = "a" * 32
        self.local(a, "[속성] 상태: 결정 필요\n\n본문")
        new = self.crawl("n", [page(a, "정책", None, kind="db_row")], {a: "[속성] 상태: 결정 완료\n\n본문"})
        code, rep = self.run_diff(new)
        self.assertEqual([x["id"] for x in rep["local_stale"]], [a])

    def test_copy_missing_row_properties_is_stale(self):
        a = "a" * 32
        self.local(a, "본문")
        new = self.crawl("n", [page(a, "정책", None, kind="db_row")], {a: "[속성] 상태: 결정 완료\n\n본문"})
        code, rep = self.run_diff(new)
        self.assertEqual([x["id"] for x in rep["local_stale"]], [a])

    def test_old_style_copy_without_markers_matches_crawl_with_markers(self):
        a = "a" * 32
        self.local(a, "본문")
        new = self.crawl("n", [page(a, "화면", None)], {a: "본문\n[파일] 그림.png"})
        code, rep = self.run_diff(new)
        self.assertEqual(rep["local_stale"], [])

    def test_unreadable_page_and_stale_local_copy_are_attention(self):
        a, b = "a" * 32, "b" * 32
        new = self.crawl("n", [page(a, "10. 견적", None), {"id": b, "kind": "error", "parent": a, "path": [], "root": "기능정의서", "error": "404"}], {a: "new"})
        self.local(a, "old")
        code, rep = self.run_diff(new)
        self.assertEqual([x["id"] for x in rep["errors"]], [b])
        self.assertEqual([x["id"] for x in rep["local_stale"]], [a])


class CrawlerNodeTests(unittest.TestCase):
    def test_title_only_discover_record_never_replaces_a_crawled_page(self):
        spec = importlib.util.spec_from_file_location("crawl", SKILL / "scripts/crawl.py")
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(SKILL / "scripts"))
        spec.loader.exec_module(mod)
        c = mod.Crawler(tempfile.mkdtemp())
        c.add("p", kind="page", title="7. 고객", children=["c"])
        c.add("p", kind="discovered", title="7. 고객")
        self.assertEqual(c.nodes["p"]["kind"], "page")
        c.add("q", kind="discovered", title="새 목업")
        c.add("q", kind="page", title="새 목업", children=[])
        self.assertEqual(c.nodes["q"]["kind"], "page")


class MockupTextTests(unittest.TestCase):
    def test_single_page_mockup_keeps_korean_script_strings(self):
        spec = importlib.util.spec_from_file_location("apply_sources", SKILL / "scripts/apply_sources.py")
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(SKILL / "scripts"))
        spec.loader.exec_module(mod)
        raw = '<title>worxsales v1.9</title><script>const a={label:"견적 저장",hint:\'초안 저장\',id:"q1"};h("견적 저장")</script>'
        text = mod.html_text(raw)
        self.assertIn("worxsales v1.9", text)
        self.assertEqual(text.split("## script strings", 1)[1].strip().splitlines(), ["견적 저장", "초안 저장"])


class RefreshInvariantTests(unittest.TestCase):
    def test_requires_explicit_invocation_on_both_runtimes(self):
        frontmatter = (SKILL / "SKILL.md").read_text().split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^disable-model-invocation: true$")
        self.assertRegex((SKILL / "agents/openai.yaml").read_text(), r"(?m)^policy:\n  allow_implicit_invocation: false$")

    def test_is_not_wired_into_other_skills(self):
        for path in (WRXP_ROOT / "skills").glob("*/SKILL.md"):
            if path.parent.name != "worxsales-qa-refresh":
                self.assertNotIn("worxsales-qa-refresh", path.read_text(), str(path))

    def test_baseline_moves_only_through_state_commit(self):
        for script in (SKILL / "scripts").glob("*.py"):
            if script.name != "state.py":
                self.assertNotIn("state.json", script.read_text(), script.name)


if __name__ == "__main__":
    unittest.main()
