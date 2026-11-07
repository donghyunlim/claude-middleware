from pathlib import Path

from salesreport.report import build_report

ROOT = Path(__file__).resolve().parent.parent


def test_matches_golden():
    assert build_report(str(ROOT / "data")) == (ROOT / "expected" / "report.txt").read_text(encoding="utf-8")
