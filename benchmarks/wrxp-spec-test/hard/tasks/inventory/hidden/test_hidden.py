import pytest
from inv.repo import StockRepo
from inv.service import StockService
from inv.orders import reserve, OutOfStock
from inv.returns import receive_return


def svc(**stock):
    return StockService(StockRepo(stock))


def test_lowercase_sku_cache_invalidated():
    s = StockService(StockRepo({"PEN-03": 10}))
    assert s.available("PEN-03") == 10
    reserve(s, [("PEN-03", 4)])
    assert s.available("PEN-03") == 6


def test_mixed_case_sku_reads_same_stock():
    s = StockService(StockRepo({"PEN-03": 10}))
    reserve(s, [("pen-03", 4)])
    assert s.available("PEN-03") == 6
    assert s.available("pen-03") == 6


def test_atomic_reserve_no_partial_commit():
    s = StockService(StockRepo({"CUP-01": 5, "TISSUE-BOX": 1}))
    with pytest.raises(OutOfStock):
        reserve(s, [("CUP-01", 2), ("TISSUE-BOX", 3)])
    assert s.available("CUP-01") == 5
    assert s.repo.get("CUP-01") == 5


def test_return_boxes_to_pieces():
    s = StockService(StockRepo({"TISSUE-BOX": 48}))
    receive_return(s, "TISSUE-BOX", 2)
    assert s.available("TISSUE-BOX") == 96


def test_return_single_unit_product():
    s = StockService(StockRepo({"CUP-01": 3}))
    receive_return(s, "CUP-01", 2)
    assert s.available("CUP-01") == 5


def test_return_invalidates_cache():
    s = StockService(StockRepo({"PEN-03": 0}))
    assert s.available("PEN-03") == 0
    receive_return(s, "pen-03", 1)
    assert s.available("PEN-03") == 12
