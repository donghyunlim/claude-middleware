import datetime as dt
from reports.monthly import monthly_total


def test_october():
    rows = [{"day": dt.date(2026, 10, 3), "amount": 10}, {"day": dt.date(2026, 11, 1), "amount": 5}]
    assert monthly_total(rows, 2026, 10) == 10
