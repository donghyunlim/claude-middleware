import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/worxsales-qa-executor/scripts/publish_results.py"


def load():
    spec = importlib.util.spec_from_file_location("publish_results", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def block(i, kind, text):
    return {"id": f"b{i}", "type": kind, kind: {"rich_text": [{"plain_text": text}]}}


class ManagedBlocksTests(unittest.TestCase):
    def run_with(self, blocks):
        mod = load()
        mod.call = lambda method, path, body=None, **kw: {"results": blocks, "has_more": False}
        return [b["id"] for b in mod.managed_blocks("page")]

    def test_keeps_human_notes_above_the_marker(self):
        ids = self.run_with([block(1, "paragraph", "기획 메모: 다음 주 재확인"),
                             block(2, "heading_2", "🤖 자동 실행 결과"),
                             block(3, "callout", "문제 · 메모가 사라짐")])
        self.assertEqual(ids, ["b2", "b3"])

    def test_replaces_unmarked_generated_bodies(self):
        self.assertEqual(self.run_with([block(1, "heading_2", "실행 기록 · pilot-01 · 문제"),
                                        block(2, "paragraph", "x")]), ["b1", "b2"])
        self.assertEqual(self.run_with([block(1, "callout", "OK · 한 행으로 나옴")]), ["b1"])

    def test_leaves_unrecognised_human_bodies_untouched(self):
        self.assertEqual(self.run_with([block(1, "paragraph", "사람이 쓴 본문")]), [])

    def test_repro_steps_are_not_double_numbered(self):
        mod = load()
        blocks = mod.body({"verdict": "문제", "headline": "h", "checked": "c", "outcome": "o",
                           "repro": ["① 입력", "② 이동"], "figures": [], "details": {}}, ".", [], True)
        kinds = [b["type"] for b in blocks[1]["callout"]["children"]]
        self.assertNotIn("numbered_list_item", kinds)

    def test_letter_marks_render_as_circled_letters(self):
        mod = load()
        self.assertEqual((mod.CIRCLED(1), mod.CIRCLED("A"), mod.CIRCLED("B")), ("①", "Ⓐ", "Ⓑ"))


if __name__ == "__main__":
    unittest.main()
