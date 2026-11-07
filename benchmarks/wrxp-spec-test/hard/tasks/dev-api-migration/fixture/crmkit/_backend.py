"""CRM 서버를 흉내 내는 인메모리 백엔드(테스트·로컬 개발용).

레코드는 서버 원본 스키마(v2와 같은 모양)로 저장된다.
- customer_id: str
- legal_name: 사업자 등록상 상호
- display_name: 앱에 보여 줄 별칭
- phone_e164: "+8210..." 형식
- created_at: UTC ISO-8601 문자열 ("2026-08-31T16:00:00Z")
"""
import datetime as dt

KST = dt.timezone(dt.timedelta(hours=9))


class FakeBackend:
    def __init__(self, records):
        self._records = [dict(r) for r in records]

    # --- legacy /v1 endpoints ---
    def v1_get(self, cid):
        for r in self._records:
            if r["customer_id"] == cid:
                return self._to_v1(r)
        return None

    def v1_list(self):
        return [self._to_v1(r) for r in self._records]

    @staticmethod
    def _to_v1(r):
        created = dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        p = r["phone_e164"]
        local = "0" + p[3:] if p.startswith("+82") else p
        phone = f"{local[:3]}-{local[3:-4]}-{local[-4:]}"
        return {"id": r["customer_id"], "name": r["legal_name"], "phone": phone,
                "joined": created.astimezone(KST).date().isoformat()}

    # --- /v2 endpoints ---
    def v2_get(self, cid):
        for r in self._records:
            if r["customer_id"] == cid:
                return dict(r)
        return None

    def v2_page(self, page, page_size):
        start = (page - 1) * page_size
        return [dict(r) for r in self._records[start:start + page_size]]
