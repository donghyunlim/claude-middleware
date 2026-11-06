"""Stock storage (stands in for the database). Quantities are in pieces."""


class StockRepo:
    def __init__(self, initial=None):
        self._stock = dict(initial or {})
        self.writes = 0

    def get(self, sku):
        return self._stock.get(sku, 0)

    def set(self, sku, qty):
        if qty < 0:
            raise ValueError(f"negative stock for {sku}")
        self._stock[sku] = qty
        self.writes += 1
