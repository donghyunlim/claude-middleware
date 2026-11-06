import pytest
from shop.paginate import paginate
from shop.api import list_products


@pytest.mark.parametrize("n,per,expected", [(0, 10, 1), (5, 10, 1), (10, 10, 1), (11, 10, 2), (20, 10, 2), (25, 10, 3), (1, 1, 1), (3, 1, 3)])
def test_total_pages(n, per, expected):
    assert paginate(list(range(n)), 1, per)[1] == expected


@pytest.mark.parametrize("n,per", [(25, 10), (20, 10), (7, 3), (9, 3), (1, 1), (100, 7)])
def test_concat_roundtrip(n, per):
    items = list(range(n))
    _, total = paginate(items, 1, per)
    out = []
    for p in range(1, total + 1):
        out += paginate(items, p, per)[0]
    assert out == items


def test_empty_page_one():
    assert paginate([], 1, 10) == ([], 1)


@pytest.mark.parametrize("page", [0, -1, 4])
def test_out_of_range(page):
    with pytest.raises(ValueError):
        paginate(list(range(25)), page, 10)


def test_per_page_invalid():
    with pytest.raises(ValueError):
        paginate([1], 1, 0)


@pytest.mark.parametrize("n,per,total", [(20, 10, 2), (25, 10, 3), (10, 10, 1), (0, 10, 1)])
def test_api_total_pages(n, per, total):
    res = list_products(list(range(n)), 1, per)
    assert res["total_pages"] == total


def test_api_last_page_and_has_next():
    res = list_products(list(range(20)), 2, 10)
    assert res["items"] == list(range(10, 20))
    assert res["has_next"] is False
    res = list_products(list(range(25)), 3, 10)
    assert res["items"] == [20, 21, 22, 23, 24]
    assert res["has_next"] is False
