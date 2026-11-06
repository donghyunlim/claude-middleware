from inv.repo import StockRepo
from inv.service import StockService
from inv.orders import reserve


def test_reserve_simple():
    s = StockService(StockRepo({"CUP-01": 5}))
    reserve(s, [("CUP-01", 2)])
    assert s.available("CUP-01") == 3
