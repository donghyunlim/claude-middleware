from store.cart import checkout_total


def test_shipping():
    assert checkout_total({"items": [{"sku": "a", "price": 10000, "qty": 1, "on_sale": False}]}) == 13000
