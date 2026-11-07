"""Generates fixture/expenses.csv, fixture/budget_q3.csv, fixture/fx_month_end.csv (seed 3301). Run from the task dir."""
import csv, random, datetime as dt
from pathlib import Path

rnd = random.Random(3301)
FX = {"2026-05": 1366.40, "2026-06": 1372.50, "2026-07": 1385.20, "2026-08": 1391.80, "2026-09": 1378.40, "2026-10": 1402.10}
VENDORS = {
    "DEV": ["AWS코리아", "젯브레인즈", "깃허브", "데이터독", "한국IDC"],
    "PLT": ["AWS코리아", "클라우드플레어", "몽고DB"],
    "MKT": ["구글애드", "메타광고", "네이버광고", "디자인스튜디오 온", "인플루언서랩"],
    "SAL": ["KTX출장", "호텔신라", "박람회조직위", "세일즈포스"],
    "HR": ["잡코리아", "교육센터 하나", "복지몰"],
    "FIN": ["삼일회계법인", "더존", "법무법인 율"],
}
USD_VENDORS = {"AWS코리아", "젯브레인즈", "깃허브", "데이터독", "클라우드플레어", "몽고DB", "구글애드", "메타광고", "세일즈포스"}
N = {"DEV": 40, "PLT": 14, "MKT": 30, "SAL": 22, "HR": 12, "FIN": 10}
SCALE = {"DEV": 7_000_000, "PLT": 6_000_000, "MKT": 4_500_000, "SAL": 3_000_000, "HR": 1_800_000, "FIN": 1_600_000}
rows = []
start = dt.date(2026, 6, 1)
for code, n in N.items():
    for _ in range(n):
        inv = start + dt.timedelta(days=rnd.randint(0, 152))  # 2026-06-01 .. 2026-10-31
        if code == "PLT" and inv >= dt.date(2026, 8, 1):
            inv = dt.date(2026, 7, rnd.randint(1, 31))
        paid = inv + dt.timedelta(days=rnd.randint(5, 45))
        vendor = rnd.choice(VENDORS[code])
        krw = SCALE[code] * rnd.uniform(0.3, 1.7)
        if vendor in USD_VENDORS:
            rows.append([code, vendor, inv, paid, round(krw / 1380, 2), "USD", "정상"])
        else:
            rows.append([code, vendor, inv, paid, int(round(krw, -3)), "KRW", "정상"])
# hand-placed rows that separate accrual vs cash and void handling
rows += [
    ["MKT", "구글애드", dt.date(2026, 9, 26), dt.date(2026, 10, 20), 15800.00, "USD", "정상"],
    ["DEV", "한국IDC", dt.date(2026, 6, 24), dt.date(2026, 7, 15), 28_500_000, "KRW", "정상"],
    ["SAL", "박람회조직위", dt.date(2026, 8, 12), dt.date(2026, 8, 30), 12_400_000, "KRW", "취소"],
    ["SAL", "박람회조직위", dt.date(2026, 6, 20), dt.date(2026, 7, 8), 9_600_000, "KRW", "정상"],
    ["HR", "교육센터 하나", dt.date(2026, 9, 30), dt.date(2026, 10, 10), 2_100_000, "KRW", "정상"],
    ["DEV", "데이터독", dt.date(2026, 7, 3), dt.date(2026, 7, 20), 4200.00, "USD", "취소"],
]
rows.sort(key=lambda r: (r[2], r[0]))
with open(Path("fixture/expenses.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["expense_id", "dept_code", "vendor", "invoice_date", "paid_date", "amount", "currency", "status"])
    for i, r in enumerate(rows, 1):
        w.writerow([f"E{i:04d}", r[0], r[1], r[2].isoformat(), r[3].isoformat(), r[4], r[5], r[6]])
with open(Path("fixture/fx_month_end.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["month", "usd_krw"])
    for k, v in FX.items():
        w.writerow([k, f"{v:.2f}"])

# budgets: set from the accrual actuals so each department lands on a chosen variance
import importlib.util, sys
spec = importlib.util.spec_from_file_location("solve", Path(__file__).with_name("solve.py"))
solve = importlib.util.module_from_spec(spec); spec.loader.exec_module(solve)
act = solve.actuals(Path("fixture"))
TARGET = {"개발본부": 0.06, "마케팅팀": 0.15, "영업팀": -0.16, "인사팀": 0.18, "재무팀": 0.02}
with open(Path("fixture/budget_q3.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["dept", "budget_krw"])
    for d, p in TARGET.items():
        w.writerow([d, int(round(act[d] / (1 + p), -5))])
