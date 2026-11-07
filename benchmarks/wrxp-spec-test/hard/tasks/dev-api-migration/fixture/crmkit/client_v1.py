"""v1 클라이언트. 고객 정보를 dict로 돌려준다."""


class CRMClient:
    def __init__(self, backend):
        self._b = backend

    def get_customer(self, customer_id):
        """고객 dict {"id", "name", "phone", "joined"}를 돌려준다. 없으면 None."""
        return self._b.v1_get(customer_id)

    def list_customers(self):
        """전체 고객 dict 목록."""
        return self._b.v1_list()
