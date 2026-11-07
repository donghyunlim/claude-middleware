import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RANK = {"low": 0, "medium": 1, "high": 2}
EXPECTED = {3: "high", 4: "high", 6: "medium", 7: "medium", 9: "medium", 11: "high",
            13: "medium", 14: "high", 15: "high", 18: "medium"}


@pytest.fixture(scope="module")
def issues():
    d = json.loads((ROOT / "review.json").read_text(encoding="utf-8"))
    out = {}
    for x in d["issues"]:
        c = int(re.sub(r"\D", "", str(x["clause"])))
        s = str(x["severity"]).strip().lower()
        assert s in RANK, s
        if c not in out or RANK[s] > RANK[out[c]]:
            out[c] = s
    return out


def test_flagged_clause_set(issues):
    assert set(issues) == set(EXPECTED)


def test_buyer_favorable_clauses_not_flagged(issues):
    # 지체상금(10) and supplier IP indemnity (12) protect the buyer
    assert 10 not in issues and 12 not in issues


def test_min_purchase_and_price_change_high(issues):
    assert issues.get(3) == "high" and issues.get(4) == "high"


def test_liability_cap_high(issues):
    assert issues.get(11) == "high"


def test_auto_renewal_high(issues):
    assert issues.get(15) == "high"


def test_governing_law_medium(issues):
    assert issues.get(18) == "medium"


def test_inspection_payment_warranty_medium(issues):
    assert [issues.get(c) for c in (6, 7, 9)] == ["medium"] * 3


def test_confidentiality_medium_per_guide(issues):
    assert issues.get(13) == "medium"


def test_personal_data_high_per_guide(issues):
    assert issues.get(14) == "high"


def test_all_severities(issues):
    assert issues == EXPECTED
