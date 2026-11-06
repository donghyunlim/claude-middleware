from shop.api import list_products


def test_first_page():
    res = list_products(list(range(25)), page=1, per_page=10)
    assert res["items"] == list(range(10))
    assert res["has_next"] is True
