from .io_utils import read_rows


def rate_for(data_dir, currency, date):
    """date(YYYY-MM-DD) 당일 또는 그 이전 가장 최근 고시 환율(1 단위당 원)."""
    if currency == "KRW":
        return 1.0
    best = None
    for row in read_rows(data_dir, "fx_rates.csv"):
        if row["currency"] != currency or row["date"] > date:
            continue
        if best is None or row["date"] > best["date"]:
            best = row
    if best is None:
        raise LookupError(f"no rate for {currency} on {date}")
    return float(best["krw_per_unit"])
