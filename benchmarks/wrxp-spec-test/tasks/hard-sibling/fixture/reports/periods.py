import datetime as dt


def month_range(year, month):
    """[start, end) dates of a calendar month."""
    start = dt.date(year, month, 1)
    end = dt.date(year, month + 1, 1)
    return start, end


def quarter_range(year, quarter):
    """[start, end) dates of a calendar quarter (1..4)."""
    start = dt.date(year, 3 * (quarter - 1) + 1, 1)
    end = dt.date(year, 3 * quarter + 1, 1)
    return start, end


def week_range(day):
    """[monday, next monday) around ``day``."""
    monday = day - dt.timedelta(days=day.weekday())
    return monday, monday + dt.timedelta(days=7)
