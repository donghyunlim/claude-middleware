from crmkit.client_v1 import CRMClient


def invoice_header(backend, customer_id, month):
    """청구서 머리말. month는 "YYYY-MM"."""
    c = CRMClient(backend).get_customer(customer_id)
    if c is None:
        raise KeyError(customer_id)
    return f"[{month} 청구서] 고객번호 {c['id']} / 상호 {c['name']}"
