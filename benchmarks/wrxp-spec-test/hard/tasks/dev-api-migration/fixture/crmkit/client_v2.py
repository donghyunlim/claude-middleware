"""v2 클라이언트. 자세한 변경 사항은 CHANGELOG.md 참고."""
from .models import Customer, CustomerNotFound


class CustomerAPI:
    def __init__(self, backend):
        self._b = backend

    def fetch(self, customer_id) -> Customer:
        r = self._b.v2_get(customer_id)
        if r is None:
            raise CustomerNotFound(customer_id)
        return Customer.from_record(r)

    def list_customers(self, page=1, page_size=50):
        return [Customer.from_record(r) for r in self._b.v2_page(page, page_size)]

    def iter_customers(self, page_size=50):
        page = 1
        while True:
            batch = self.list_customers(page=page, page_size=page_size)
            if not batch:
                return
            yield from batch
            page += 1
