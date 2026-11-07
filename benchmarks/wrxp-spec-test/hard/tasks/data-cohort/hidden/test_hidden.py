import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HID = Path(__file__).resolve().parent
COLS = ["cohort_week", "cohort_size", "W1", "W2", "W3", "W4"]


def load(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return [h.strip() for h in rows[0]], [[c.strip() for c in r] for r in rows[1:] if any(c.strip() for c in r)]


@pytest.fixture(scope="module")
def out():
    return load(ROOT / "retention.csv")


@pytest.fixture(scope="module")
def truth():
    return load(HID / "truth.csv")[1]


def as_map(rows):
    return {r[0]: r for r in rows}


def test_header(out):
    assert out[0] == COLS


def test_cohort_weeks_monday_kst(out, truth):
    assert sorted(r[0] for r in out[1]) == [r[0] for r in truth]


def test_sorted_oldest_first(out):
    weeks = [r[0] for r in out[1]]
    assert weeks == sorted(weeks)


def test_cohort_sizes_exclude_internal(out, truth):
    m = as_map(out[1])
    assert {w: int(float(m[w][1])) for w in m} == {r[0]: int(r[1]) for r in truth}


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_retention_payment_based(out, truth, k):
    m = as_map(out[1])
    bad = []
    for r in truth:
        got = float(m[r[0]][1 + k]) if r[0] in m else None
        if got is None or abs(got - float(r[1 + k])) > 6e-4:
            bad.append((r[0], got, r[1 + k]))
    assert not bad, bad
