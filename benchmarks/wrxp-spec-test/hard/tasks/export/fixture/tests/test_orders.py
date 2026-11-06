from shop.orders import order_total


def test_total():
    assert order_total({"items": [{"qty": 2, "unit_price": 1000}]}) == 2000
