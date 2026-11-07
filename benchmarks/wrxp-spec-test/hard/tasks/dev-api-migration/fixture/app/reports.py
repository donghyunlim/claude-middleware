from collections import Counter

from crmkit.client_v1 import CRMClient


def monthly_signups(backend):
    """가입 월(KST, "YYYY-MM")별 신규 고객 수."""
    customers = CRMClient(backend).list_customers()
    return dict(sorted(Counter(c["joined"][:7] for c in customers).items()))
