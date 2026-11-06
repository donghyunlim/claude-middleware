"""Shopping cart pricing (KRW, integers)."""

FREE_SHIPPING_THRESHOLD = 30000
SHIPPING_FEE = 3000


def subtotal(cart):
    """cart = {"items": [{"sku", "price", "qty", "on_sale": bool}]}"""
    return sum(i["price"] * i["qty"] for i in cart["items"])


def shipping(cart):
    return 0 if subtotal(cart) >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE


def checkout_total(cart):
    return subtotal(cart) + shipping(cart)
