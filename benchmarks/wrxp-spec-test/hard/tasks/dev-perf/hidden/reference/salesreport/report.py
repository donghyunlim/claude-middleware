import bisect

from . import orders
from .catalog import Product
from .formatting import pct, won
from .io_utils import read_rows


class _Index:
    """build_report 한 번 동안만 쓰는 조회 인덱스(원래 함수와 같은 규칙: 첫 행 우선)."""

    def __init__(self, data_dir):
        self.products = {}
        for row in read_rows(data_dir, "products.csv"):
            if row["sku"] not in self.products:
                self.products[row["sku"]] = Product(row["sku"], row["name"], row["category"],
                                                    float(row["unit_price"]), row["currency"])
        self.customers = {}
        for row in read_rows(data_dir, "customers.csv"):
            cid = row["customer_id"].strip()
            if cid not in self.customers:
                self.customers[cid] = {"name": row["name"], "region": row["region"], "tier": row["tier"]}
        first = {}
        for row in read_rows(data_dir, "fx_rates.csv"):
            first.setdefault((row["currency"], row["date"]), row["krw_per_unit"])
        self.rates = {}
        for (cur, date), v in sorted(first.items()):
            self.rates.setdefault(cur, ([], []))
            self.rates[cur][0].append(date)
            self.rates[cur][1].append(float(v))

    def product(self, sku):
        try:
            return self.products[sku]
        except KeyError:
            raise KeyError(sku) from None

    def customer(self, customer_id):
        cid = customer_id.strip()
        c = self.customers.get(cid)
        if c is None:
            return {"id": cid, "name": "(미등록)", "region": "미상", "tier": "일반"}
        return {"id": cid, **c}

    def rate(self, currency, date):
        if currency == "KRW":
            return 1.0
        dates, vals = self.rates.get(currency, ([], []))
        i = bisect.bisect_right(dates, date)
        if i == 0:
            raise LookupError(f"no rate for {currency} on {date}")
        return vals[i - 1]


def build_report(data_dir):
    idx = _Index(data_dir)
    lines = orders.load_lines(data_dir)
    total = 0.0
    by_region, by_category, by_product, qty_by_product = {}, {}, {}, {}
    for ln in lines:
        prod = idx.product(ln["sku"])
        amt = ln["qty"] * prod.unit_price * idx.rate(prod.currency, ln["date"])
        cust = idx.customer(ln["customer_id"])
        total += amt
        by_region[cust["region"]] = by_region.get(cust["region"], 0.0) + amt
        by_category[prod.category] = by_category.get(prod.category, 0.0) + amt
        by_product[prod.sku] = by_product.get(prod.sku, 0.0) + amt
        qty_by_product[prod.sku] = qty_by_product.get(prod.sku, 0) + ln["qty"]

    tiers = {}
    seen = {}
    for ln in lines:
        cid = ln["customer_id"].strip()
        if cid in seen:
            continue
        seen[cid] = True
        t = idx.customer(cid)["tier"]
        tiers[t] = tiers.get(t, 0) + 1

    dates = [ln["date"] for ln in lines]
    order_ids = dict.fromkeys(ln["order_id"] for ln in lines)

    out = ["판매 리포트",
           f"기간: {min(dates)} ~ {max(dates)}",
           f"주문: {len(order_ids)}건 / 주문 라인: {len(lines)}건 / 고객: {len(seen)}명",
           f"총매출(KRW): {won(total)}",
           "",
           "[지역별 매출]"]
    for region, amt in sorted(by_region.items(), key=lambda kv: -kv[1]):
        out.append(f"{region}\t{won(amt)}\t{pct(amt, total)}")
    out += ["", "[카테고리별 매출]"]
    for cat, amt in sorted(by_category.items(), key=lambda kv: -kv[1]):
        out.append(f"{cat}\t{won(amt)}\t{pct(amt, total)}")
    out += ["", "[상위 상품 TOP 10]"]
    top = sorted(by_product.items(), key=lambda kv: -kv[1])[:10]
    for i, (sku, amt) in enumerate(top, 1):
        name = idx.product(sku).name
        out.append(f"{i:>2}. {sku} {name}\t수량 {qty_by_product[sku]}\t매출 {won(amt)}")
    out += ["", "[등급별 고객 수]"]
    for t in sorted(tiers):
        out.append(f"{t}\t{tiers[t]}명")
    return "\n".join(out) + "\n"
