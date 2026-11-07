from crmkit.client_v2 import CustomerAPI
from crmkit.models import CustomerNotFound


def invoice_header(backend, customer_id, month):
    """청구서 머리말. month는 "YYYY-MM"."""
    try:
        c = CustomerAPI(backend).fetch(customer_id)
    except CustomerNotFound:
        raise KeyError(customer_id) from None
    return f"[{month} 청구서] 고객번호 {c.customer_id} / 상호 {c.legal_name}"
