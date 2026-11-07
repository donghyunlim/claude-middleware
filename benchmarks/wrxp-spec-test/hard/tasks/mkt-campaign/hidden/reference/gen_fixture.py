"""Generates fixture/customers.csv (seed 20261101). Run from the task dir."""
import csv, random, datetime as dt
from pathlib import Path

rnd = random.Random(20261101)
BASE = dt.date(2026, 11, 1)
SUR = "김이박최정강조윤장임한오서신권황안송류홍"
GIV = ["민준", "서연", "도윤", "하은", "지호", "수아", "예준", "지유", "주원", "서윤", "현우", "채원", "건우", "다은", "우진", "소율", "시우", "윤서", "준서", "지민"]
rows = []
for i in range(1, 201):
    name = rnd.choice(SUR) + rnd.choice(GIV)
    signup = BASE - dt.timedelta(days=rnd.randint(120, 1100))
    r = rnd.random()
    if r < 0.15:
        last, orders = "", 0
    else:
        # buckets of days-before-2026-11-01; nothing between 80 and 100 days
        b = rnd.random()
        if b < 0.30:
            ago = rnd.randint(1, 59)
        elif b < 0.45:
            ago = rnd.randint(60, 79)
        elif b < 0.75:
            ago = rnd.randint(100, 179)
        else:
            ago = rnd.randint(180, 420)
        d = BASE - dt.timedelta(days=ago)
        if d < signup:
            signup = d - dt.timedelta(days=rnd.randint(10, 200))
        last, orders = d.isoformat(), rnd.randint(1, 14)
    opt = "Y" if rnd.random() < 0.7 else "N"
    rows.append([f"C{i:04d}", name, f"user{i:04d}@example.com", signup.isoformat(), last, orders, opt])
with open(Path("fixture/customers.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["customer_id", "name", "email", "signup_date", "last_order_date", "total_orders", "marketing_opt_in"])
    w.writerows(rows)
