import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# accrual basis, invoice-month month-end FX, void excluded, PLT merged into 개발본부
BUDGET = {"개발본부": 188000000, "마케팅팀": 73300000, "영업팀": 42300000, "인사팀": 13500000, "재무팀": 7800000}
ACTUAL = {"개발본부": 199258225, "마케팅팀": 84339417, "영업팀": 35511079, "인사팀": 15948000, "재무팀": 7997000}
MATERIAL = {"개발본부": False, "마케팅팀": True, "영업팀": True, "인사팀": False, "재무팀": False}
TOL = 1000  # won


@pytest.fixture(scope="module")
def deps():
    d = json.loads((ROOT / "variance.json").read_text(encoding="utf-8"))
    return {x["dept"].strip(): x for x in d["departments"]}


def test_five_departments_platform_merged(deps):
    assert set(deps) == set(BUDGET)


def test_budget_values(deps):
    assert all(int(deps[k]["budget"]) == v for k, v in BUDGET.items())


def test_dev_actual_includes_platform(deps):
    assert abs(deps["개발본부"]["actual"] - ACTUAL["개발본부"]) <= TOL


def test_marketing_actual_accrual_with_usd(deps):
    # includes a USD invoice dated 2026-09-26 that was paid in October
    assert abs(deps["마케팅팀"]["actual"] - ACTUAL["마케팅팀"]) <= TOL


def test_sales_actual_void_excluded(deps):
    assert abs(deps["영업팀"]["actual"] - ACTUAL["영업팀"]) <= TOL


def test_hr_and_finance_actuals_accrual(deps):
    assert abs(deps["인사팀"]["actual"] - ACTUAL["인사팀"]) <= TOL
    assert abs(deps["재무팀"]["actual"] - ACTUAL["재무팀"]) <= TOL


def test_variance_and_pct_consistent(deps):
    for x in deps.values():
        assert abs(x["variance"] - (x["actual"] - x["budget"])) <= 1
        assert abs(float(x["variance_pct"]) - x["variance"] / x["budget"] * 100) <= 0.01


def test_material_flags(deps):
    assert {k: bool(deps[k]["material"]) for k in MATERIAL} == MATERIAL


def test_material_needs_amount_threshold(deps):
    # 인사팀: +18% but only ~2.4M won over budget -> not material
    assert deps["인사팀"]["material"] is False


def test_material_needs_pct_threshold(deps):
    # 개발본부: ~11M won over budget but only ~6% -> not material
    assert deps["개발본부"]["material"] is False
