"""Reference solution: accrual basis (invoice_date in Q3), void rows excluded, PLT -> 개발본부,
USD at month-end rate of the invoice month, material = |pct| >= 10 and |variance| >= 5,000,000.
Usage: python3 solve.py FIXTURE_DIR  (writes variance.json in the current dir)"""
import csv, json, sys
from pathlib import Path

DEPT = {"DEV": "개발본부", "PLT": "개발본부", "MKT": "마케팅팀", "SAL": "영업팀", "HR": "인사팀", "FIN": "재무팀"}


def actuals(src: Path):
    fx = {r["month"]: float(r["usd_krw"]) for r in csv.DictReader(open(src / "fx_month_end.csv"))}
    tot = {}
    for r in csv.DictReader(open(src / "expenses.csv")):
        if r["status"] == "취소" or not ("2026-07-01" <= r["invoice_date"] <= "2026-09-30"):
            continue
        amt = float(r["amount"]) * (fx[r["invoice_date"][:7]] if r["currency"] == "USD" else 1)
        d = DEPT[r["dept_code"]]
        tot[d] = tot.get(d, 0) + amt
    return tot


if __name__ == "__main__":
    src = Path(sys.argv[1])
    act = actuals(src)
    out = []
    for r in csv.DictReader(open(src / "budget_q3.csv")):
        b, a = int(r["budget_krw"]), round(act[r["dept"]])
        v = a - b
        pct = round(v / b * 100, 2)
        out.append({"dept": r["dept"], "budget": b, "actual": a, "variance": v, "variance_pct": pct,
                    "material": abs(pct) >= 10 and abs(v) >= 5_000_000})
    json.dump({"departments": out}, open("variance.json", "w"), ensure_ascii=False, indent=1)
    for o in out:
        print(o)
