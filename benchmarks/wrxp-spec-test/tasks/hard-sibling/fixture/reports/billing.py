import datetime as dt


def next_billing_date(last):
    """Billing happens on the same day next month (clamped to month end)."""
    month = last.month + 1
    day = min(last.day, 28)
    return dt.date(last.year, month, day)
