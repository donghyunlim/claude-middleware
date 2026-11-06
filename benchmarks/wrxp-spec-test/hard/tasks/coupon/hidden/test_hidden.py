import pytest
from store.coupon import apply_coupon


def cart(*items):
    return {"items": [{"sku": f"s{i}", "price": p, "qty": q, "on_sale": s} for i, (p, q, s) in enumerate(items)]}


def test_percent_basic():
    assert apply_coupon(cart((20000, 1, False)), {"type": "percent", "value": 10}) == 18000 + 3000


def test_percent_floor_10won():
    # 12,345 * 10% = 1,234.5 -> 1,230
    assert apply_coupon(cart((12345, 1, False)), {"type": "percent", "value": 10}) == 12345 - 1230 + 3000


def test_sale_items_excluded_from_discount():
    c = cart((20000, 1, False), (20000, 1, True))
    assert apply_coupon(c, {"type": "percent", "value": 10}) == 40000 - 2000


def test_max_discount_caps_percent():
    assert apply_coupon(cart((100000, 1, False)), {"type": "percent", "value": 20, "max_discount": 5000}) == 95000


def test_fixed_basic():
    assert apply_coupon(cart((40000, 1, False)), {"type": "fixed", "value": 5000}) == 35000


def test_fixed_not_above_eligible_amount():
    c = cart((3000, 1, False), (40000, 1, True))
    assert apply_coupon(c, {"type": "fixed", "value": 5000}) == 40000


def test_min_order_counts_sale_items():
    c = cart((10000, 1, False), (25000, 1, True))
    assert apply_coupon(c, {"type": "fixed", "value": 2000, "min_order": 30000}) == 33000


def test_min_order_not_met_raises():
    with pytest.raises(ValueError):
        apply_coupon(cart((10000, 1, False)), {"type": "fixed", "value": 2000, "min_order": 30000})


def test_shipping_from_pre_discount_subtotal():
    # 31,000 before discount -> free shipping even though discounted total < 30,000
    assert apply_coupon(cart((31000, 1, False)), {"type": "fixed", "value": 5000}) == 26000


def test_shipping_not_discounted():
    assert apply_coupon(cart((5000, 1, False)), {"type": "fixed", "value": 9000}) == 3000
