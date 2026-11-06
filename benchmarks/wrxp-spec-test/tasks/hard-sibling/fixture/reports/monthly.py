from .periods import month_range


def monthly_total(rows, year, month):
    start, end = month_range(year, month)
    return sum(r["amount"] for r in rows if start <= r["day"] < end)
