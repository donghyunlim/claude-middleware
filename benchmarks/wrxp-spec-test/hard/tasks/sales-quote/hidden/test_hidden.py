import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def q():
    return json.loads((ROOT / "quote.json").read_text(encoding="utf-8-sig"))


def items(q):
    return {li["sku"].strip(): li for li in q["line_items"]}


def num(x):
    return round(float(x))


def test_exact_line_items(q):
    assert sorted(items(q)) == ["ADDON-SSO", "BIZ-SEAT", "SVC-ONBOARD"]


def test_seat_line_120_seats_36_months(q):
    li = items(q)["BIZ-SEAT"]
    assert (num(li["qty"]), num(li["months"]), num(li["unit_price"]), num(li["amount"])) == (120, 36, 13900, 60_048_000)


def test_sso_addon_line(q):
    li = items(q)["ADDON-SSO"]
    assert (num(li["qty"]), num(li["months"]), num(li["unit_price"]), num(li["amount"])) == (120, 36, 2500, 10_800_000)


def test_onboarding_one_time(q):
    li = items(q)["SVC-ONBOARD"]
    assert li.get("months") is None
    assert (num(li["qty"]), num(li["unit_price"]), num(li["amount"])) == (1, 1_800_000, 1_800_000)


def test_subtotal(q):
    assert num(q["subtotal"]) == 72_648_000


def test_discount_rate_capped(q):
    assert float(q["discount_rate_pct"]) == 20


def test_supply_amount_discount_on_subscriptions_only_and_truncated(q):
    assert num(q["supply_amount"]) == 58_478_000
    assert num(q["discount_amount"]) == 14_170_000


def test_vat_separate_and_total(q):
    assert num(q["vat"]) == 5_847_800
    assert num(q["total"]) == 64_325_800


def test_valid_until_30_days(q):
    assert q["valid_until"] == "2026-12-09"
