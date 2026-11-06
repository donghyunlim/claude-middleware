import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "orders.json"

STATUS_LABEL = {"paid": "결제완료", "cancelled": "취소", "refunded": "환불", "shipped": "배송중"}


def load_orders(path=DATA):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def order_total(order):
    return sum(i["qty"] * i["unit_price"] for i in order["items"])
