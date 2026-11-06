"""Order reservation. Lines are (sku, pieces)."""
from .service import StockService


class OutOfStock(Exception):
    pass


def reserve(service: StockService, lines):
    """Reserve every line or none of them."""
    for sku, qty in lines:
        have = service.available(sku)
        if have < qty:
            raise OutOfStock(sku)
        service._write(sku, have - qty)
