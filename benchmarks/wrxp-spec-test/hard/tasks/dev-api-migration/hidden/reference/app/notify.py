from crmkit.client_v2 import CustomerAPI
from crmkit.models import CustomerNotFound


def renewal_messages(backend, customer_ids):
    """갱신 안내 문자 목록. CRM에 없는 고객(탈퇴 등)은 건너뛴다."""
    api = CustomerAPI(backend)
    out = []
    for cid in customer_ids:
        try:
            c = api.fetch(cid)
        except CustomerNotFound:
            continue
        out.append(f"{c.legal_name} 담당자님, 서비스 갱신일이 다가왔습니다. 문의: 1588-0000")
    return out
