import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["B-03", "B-01", "B-02", "B-11", "B-05", "B-04", "B-12", "B-06", "B-10", "B-07", "B-09", "B-08"]
SCORE = {"B-03": 10000, "B-01": 9600, "B-02": 9000, "B-11": 8000, "B-05": 7200, "B-04": 7200,
         "B-12": 6400, "B-06": 5000, "B-10": 4000, "B-07": 2000, "B-09": 1250, "B-08": 112.5}


@pytest.fixture(scope="module")
def ranked():
    d = json.loads((ROOT / "ranked.json").read_text(encoding="utf-8"))
    return [str(x["id"]).strip() for x in d], {str(x["id"]).strip(): float(x["score"]) for x in d}


def close(a, b):
    return abs(a - b) <= 0.01 * b


def test_all_items_once(ranked):
    ids, _ = ranked
    assert sorted(ids) == sorted(ORDER) and len(ids) == len(ORDER)


def test_top1(ranked):
    assert ranked[0][0] == "B-03"


def test_top5_order(ranked):
    assert ranked[0][:5] == ORDER[:5]


def test_tie_break_lower_effort_first(ranked):
    # B-05 and B-04 both score 7200; B-05 has 1 person-month, B-04 has 1.5
    ids = ranked[0]
    assert ids.index("B-05") + 1 == ids.index("B-04")


def test_reach_normalized_to_quarter(ranked):
    # B-03 reach is yearly (40000/yr -> 10000/quarter); B-11 is monthly (2500/mo -> 7500/quarter)
    s = ranked[1]
    assert close(s["B-03"], 10000) and close(s["B-11"], 8000)


def test_confidence_capped_without_research(ranked):
    # B-02 PM wrote 90% but has no user research -> 50%
    assert close(ranked[1]["B-02"], 9000)


def test_effort_in_person_months(ranked):
    # B-04: 3 people x 2 weeks = 1.5 person-months
    assert close(ranked[1]["B-04"], 7200)


def test_top5_scores(ranked):
    s = ranked[1]
    assert all(close(s[i], SCORE[i]) for i in ORDER[:5])


def test_all_scores(ranked):
    s = ranked[1]
    assert all(close(s[i], v) for i, v in SCORE.items())


def test_sorted_descending(ranked):
    ids, s = ranked
    assert all(s[a] >= s[b] for a, b in zip(ids, ids[1:]))
