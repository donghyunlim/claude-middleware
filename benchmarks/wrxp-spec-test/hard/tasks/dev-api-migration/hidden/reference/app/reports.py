import datetime as dt
from collections import Counter

from crmkit.client_v2 import CustomerAPI

KST = dt.timezone(dt.timedelta(hours=9))


def monthly_signups(backend):
    """가입 월(KST, "YYYY-MM")별 신규 고객 수."""
    customers = CustomerAPI(backend).iter_customers()
    return dict(sorted(Counter(c.created_at.astimezone(KST).strftime("%Y-%m") for c in customers).items()))
