import csv, io, json, datetime as dt
from pathlib import Path
import pytest
from shop.export import export_orders

ORDERS = [
    {"id": "A1", "created_at": "2026-10-31T15:30:00Z", "status": "paid", "customer": {"name": "김민준", "email": "a@x.com"},
     "items": [{"sku": "P1", "name": "컵", "qty": 2, "unit_price": 3500}, {"sku": "P2", "name": "펜", "qty": 1, "unit_price": 1200}]},
    {"id": "A2", "created_at": "2026-10-01T00:05:00Z", "status": "cancelled", "customer": {"name": "이서연", "email": "b@x.com"},
     "items": [{"sku": "P1", "name": "컵", "qty": 1, "unit_price": 3500}]},
    {"id": "A3", "created_at": "2026-10-02T23:59:00Z", "status": "refunded", "customer": {"name": "박도윤", "email": "c@x.com"},
     "items": [{"sku": "P3", "name": "노트", "qty": 3, "unit_price": 12000}]},
    {"id": "A4", "created_at": "2026-10-15T03:00:00Z", "status": "shipped", "customer": {"name": "최하은", "email": "d@x.com"},
     "items": [{"sku": "P4", "name": "백", "qty": 1, "unit_price": 15500}]},
]


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    p = tmp_path_factory.mktemp("o") / "orders.csv"
    export_orders(json.loads(json.dumps(ORDERS)), str(p))
    raw = Path(p).read_bytes()
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    return raw, rows


def test_bom(out):
    assert out[0].startswith(b"\xef\xbb\xbf")


def test_header(out):
    assert [h.strip() for h in out[1][0]] == ["주문번호", "주문일시", "고객명", "상품수", "결제금액", "상태"]


def test_one_row_per_order_and_cancelled_excluded(out):
    ids = [r[0] for r in out[1][1:] if r]
    assert sorted(ids) == ["A1", "A3", "A4"]


def test_sorted_oldest_first(out):
    assert [r[0] for r in out[1][1:] if r] == ["A3", "A4", "A1"]


def test_kst_format(out):
    m = {r[0]: r[1] for r in out[1][1:] if r}
    assert m["A1"] == "2026-11-01 00:30" and m["A3"] == "2026-10-03 08:59"


def test_amount_plain_integer(out):
    m = {r[0]: r[4] for r in out[1][1:] if r}
    assert m["A1"] == "8200" and m["A3"] == "36000"


def test_qty_sum(out):
    m = {r[0]: r[3] for r in out[1][1:] if r}
    assert m["A1"] == "3" and m["A3"] == "3"


def test_status_korean_refund_included(out):
    m = {r[0]: r[5] for r in out[1][1:] if r}
    assert m["A3"] == "환불" and m["A1"] == "결제완료" and m["A4"] == "배송중"


def test_no_email(out):
    assert "@x.com" not in out[0].decode("utf-8-sig")
