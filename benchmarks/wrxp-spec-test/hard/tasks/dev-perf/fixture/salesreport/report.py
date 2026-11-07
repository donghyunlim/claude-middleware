from . import catalog, customers, fx, orders
from .formatting import pct, won


def line_amount(data_dir, line):
    p = catalog.get_product(data_dir, line["sku"])
    rate = fx.rate_for(data_dir, p.currency, line["date"])
    return line["qty"] * p.unit_price * rate


def build_report(data_dir):
    lines = orders.load_lines(data_dir)
    total = 0.0
    by_region, by_category, by_product, qty_by_product = {}, {}, {}, {}
    for ln in lines:
        amt = line_amount(data_dir, ln)
        cust = customers.get_customer(data_dir, ln["customer_id"])
        prod = catalog.get_product(data_dir, ln["sku"])
        total += amt
        by_region[cust["region"]] = by_region.get(cust["region"], 0.0) + amt
        by_category[prod.category] = by_category.get(prod.category, 0.0) + amt
        by_product[prod.sku] = by_product.get(prod.sku, 0.0) + amt
        qty_by_product[prod.sku] = qty_by_product.get(prod.sku, 0) + ln["qty"]

    tiers = {}
    seen = []
    for ln in lines:
        cid = ln["customer_id"].strip()
        if cid in seen:
            continue
        seen.append(cid)
        t = customers.get_customer(data_dir, cid)["tier"]
        tiers[t] = tiers.get(t, 0) + 1

    dates = [ln["date"] for ln in lines]
    order_ids = []
    for ln in lines:
        if ln["order_id"] not in order_ids:
            order_ids.append(ln["order_id"])

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
        name = catalog.get_product(data_dir, sku).name
        out.append(f"{i:>2}. {sku} {name}\t수량 {qty_by_product[sku]}\t매출 {won(amt)}")
    out += ["", "[등급별 고객 수]"]
    for t in sorted(tiers):
        out.append(f"{t}\t{tiers[t]}명")
    return "\n".join(out) + "\n"
