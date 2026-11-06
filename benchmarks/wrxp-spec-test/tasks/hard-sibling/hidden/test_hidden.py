import datetime as dt
import pytest
from reports.periods import month_range, quarter_range, week_range
from reports.billing import next_billing_date
from reports.monthly import monthly_total


def test_month_dec():
    assert month_range(2026, 12) == (dt.date(2026, 12, 1), dt.date(2027, 1, 1))


@pytest.mark.parametrize("m", range(1, 12))
def test_month_other(m):
    assert month_range(2026, m) == (dt.date(2026, m, 1), dt.date(2026, m + 1, 1))


def test_monthly_total_dec():
    rows = [{"day": dt.date(2026, 12, 31), "amount": 7}, {"day": dt.date(2027, 1, 1), "amount": 1}]
    assert monthly_total(rows, 2026, 12) == 7


def test_quarter_q4():
    assert quarter_range(2026, 4) == (dt.date(2026, 10, 1), dt.date(2027, 1, 1))


@pytest.mark.parametrize("q", [1, 2, 3])
def test_quarter_other(q):
    assert quarter_range(2026, q) == (dt.date(2026, 3 * q - 2, 1), dt.date(2026, 3 * q + 1, 1))


def test_billing_december():
    assert next_billing_date(dt.date(2026, 12, 15)) == dt.date(2027, 1, 15)


def test_week():
    assert week_range(dt.date(2026, 12, 31)) == (dt.date(2026, 12, 28), dt.date(2027, 1, 4))
