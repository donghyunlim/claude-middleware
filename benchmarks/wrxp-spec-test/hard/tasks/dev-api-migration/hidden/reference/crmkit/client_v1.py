"""v1 클라이언트. 고객 정보를 dict로 돌려준다.

.. deprecated:: 2.0.0  `crmkit.client_v2.CustomerAPI`를 쓰세요. 다음 릴리스에서 제거됩니다.
"""
import warnings


class CRMClient:
    def __init__(self, backend):
        warnings.warn("crmkit.client_v1.CRMClient는 폐기 예정입니다. crmkit.client_v2.CustomerAPI를 쓰세요.",
                      DeprecationWarning, stacklevel=2)
        self._b = backend

    def get_customer(self, customer_id):
        """고객 dict {"id", "name", "phone", "joined"}를 돌려준다. 없으면 None."""
        return self._b.v1_get(customer_id)

    def list_customers(self):
        """전체 고객 dict 목록."""
        return self._b.v1_list()
