"""Reference solution: writes campaign.json in the current dir from customers.csv."""
import csv, json, sys
from pathlib import Path
src = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
ids = [r["customer_id"] for r in csv.DictReader(open(src / "customers.csv"))
       if r["marketing_opt_in"] == "Y" and r["last_order_date"] and r["last_order_date"] <= "2026-08-03"]
json.dump({
    "target_customer_ids": ids,
    "send_at": "2026-11-17T10:00:00+09:00",
    "subjects": ["(광고) 오랜만이에요, 15% 쿠폰 드려요", "(광고) 다시 만나요! 15% 할인 쿠폰"],
    "coupon_code": "COMEBACK15",
    "holdout_pct": 20,
    "footer": "본 메일은 수신 동의하신 고객님께 발송되었습니다. 수신을 원하지 않으시면 [수신거부]를 눌러 주세요.",
}, open("campaign.json", "w"), ensure_ascii=False, indent=1)
print(len(ids))
