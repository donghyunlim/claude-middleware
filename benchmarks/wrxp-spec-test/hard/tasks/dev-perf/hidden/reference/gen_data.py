"""Generates fixture/data, fixture/expected/report.txt, hidden/datasets/* and hidden/golden/*.txt.
Goldens are produced with the ORIGINAL implementation copied to hidden/baseline/salesreport_orig.
Run from anywhere: python3 gen_data.py"""
import csv
import datetime as dt
import importlib
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent.parent
FX = TASK / "fixture"
HID = TASK / "hidden"

CATS = ["주변기기", "사무용품", "가전", "생활", "도서", "소프트웨어"]
REGIONS = ["서울", "경기", "부산", "대구", "인천", "광주", "대전", "제주"]
TIERS = ["VIP", "골드", "실버", "일반"]
WORDS = ["무선", "프리미엄", "슬림", "휴대용", "스마트", "베이직", "프로", "미니"]
ITEMS = ["마우스", "키보드", "노트", "충전기", "스탠드", "텀블러", "램프", "케이블", "파일", "스피커"]


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make(out, seed, n_lines, n_products, n_customers, rate_start, n_dup_products=5, n_dup_rates=6):
    rng = random.Random(seed)
    products = []
    for i in range(n_products):
        cur = rng.choices(["KRW", "USD", "JPY"], [6, 3, 1])[0]
        price = {"KRW": rng.randrange(20, 900) * 100, "USD": round(rng.uniform(3, 400), 2),
                 "JPY": rng.randrange(3, 300) * 100}[cur]
        products.append([f"SKU-{i:05d}", f"{rng.choice(WORDS)} {rng.choice(ITEMS)}", rng.choice(CATS), price, cur])
    dups = []
    for p in rng.sample(products, n_dup_products):  # 가격 변경 행이 뒤에 추가된 것처럼 보이는 중복 SKU
        q = list(p)
        q[3] = round(q[3] * 1.1, 2) if q[4] == "USD" else int(q[3] * 1.1)
        dups.append(q)
    customers = [[f"C{i:05d}", f"고객{i:05d}", rng.choice(REGIONS), rng.choices(TIERS, [1, 2, 3, 6])[0]]
                 for i in range(n_customers)]
    rates = []
    base = {"USD": 1380.0, "JPY": 9.2}
    d = rate_start
    end = dt.date(2026, 9, 30)
    while d <= end:
        if d.weekday() < 5:
            for c in ("USD", "JPY"):
                base[c] *= 1 + rng.uniform(-0.004, 0.004)
                rates.append([d.isoformat(), c, round(base[c], 2 if c == "USD" else 4)])
        d += dt.timedelta(days=1)
    q3 = [r for r in rates if r[0] >= "2026-07-01"]
    for r in rng.sample(q3, n_dup_rates):  # 정정 고시: 같은 날짜·통화가 두 번
        rates.append([r[0], r[1], round(r[2] * 1.01, 2 if r[1] == "USD" else 4)])
    rng.shuffle(rates)
    lines, oid = [], 0
    start = dt.date(2026, 7, 1)
    hot = [p[0] for p in dups]
    while len(lines) < n_lines:
        oid += 1
        day = (start + dt.timedelta(days=rng.randrange(92))).isoformat()
        cid = rng.choice(customers)[0]
        if rng.random() < 0.1:
            cid = " " + cid if rng.random() < 0.5 else cid + " "
        for _ in range(rng.randrange(1, 4)):
            sku = rng.choice(hot) if rng.random() < 0.15 else rng.choice(products)[0]
            lines.append([f"O{oid:06d}", day, cid, sku, rng.randrange(1, 6)])
    write(out / "order_lines.csv", ["order_id", "order_date", "customer_id", "sku", "qty"], lines)
    write(out / "products.csv", ["sku", "name", "category", "unit_price", "currency"], products + dups)
    write(out / "customers.csv", ["customer_id", "name", "region", "tier"], customers)
    write(out / "fx_rates.csv", ["date", "currency", "krw_per_unit"], rates)


SETS = {
    "mixed": dict(seed=11, n_lines=1800, n_products=300, n_customers=600, rate_start=dt.date(2026, 6, 1)),
    "many_products": dict(seed=12, n_lines=600, n_products=3000, n_customers=60, rate_start=dt.date(2026, 6, 1)),
    "many_customers": dict(seed=13, n_lines=600, n_products=40, n_customers=3000, rate_start=dt.date(2026, 6, 1)),
    "many_rates": dict(seed=14, n_lines=600, n_products=40, n_customers=60, rate_start=dt.date(2023, 1, 1)),
}

if __name__ == "__main__":
    make(FX / "data", 2026, 500, 120, 250, dt.date(2026, 6, 1))
    for name, kw in SETS.items():
        make(HID / "datasets" / name, **kw)
    bl = HID / "baseline" / "salesreport_orig"
    if not bl.exists():
        shutil.copytree(FX / "salesreport", bl, ignore=shutil.ignore_patterns("__pycache__"))
    sys.path.insert(0, str(bl.parent))
    rep = importlib.import_module("salesreport_orig.report")
    (FX / "expected").mkdir(exist_ok=True)
    (FX / "expected" / "report.txt").write_text(rep.build_report(str(FX / "data")), encoding="utf-8")
    (HID / "golden").mkdir(exist_ok=True)
    for name in SETS:
        (HID / "golden" / f"{name}.txt").write_text(rep.build_report(str(HID / "datasets" / name)), encoding="utf-8")
    print("done")
