from crmkit.client_v1 import CRMClient


def renewal_messages(backend, customer_ids):
    """갱신 안내 문자 목록. CRM에 없는 고객(탈퇴 등)은 건너뛴다."""
    client = CRMClient(backend)
    out = []
    for cid in customer_ids:
        c = client.get_customer(cid)
        if c is None:
            continue
        out.append(f"{c['name']} 담당자님, 서비스 갱신일이 다가왔습니다. 문의: 1588-0000")
    return out
