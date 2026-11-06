"""Builds the ops-cleanup fixture into a target dir (files are generated, not stored)."""
import datetime as dt, os, sys
root = sys.argv[1]
today = dt.date(2026, 11, 6)
for sub in ["logs", "backups", "legal_hold"]:
    os.makedirs(os.path.join(root, sub), exist_ok=True)
def mk(path, d, size):
    p = os.path.join(root, path)
    with open(p, "wb") as f:
        f.write(b"x" * size)
    ts = dt.datetime(d.year, d.month, d.day, 3, 0).timestamp()
    os.utime(p, (ts, ts))
for i in range(0, 60, 3):
    d = today - dt.timedelta(days=i)
    mk(f"logs/app-{d}.log", d, 200_000)
for i in range(0, 400, 7):
    d = today - dt.timedelta(days=i)
    mk(f"backups/db-{d}.sql.gz", d, 500_000)
for m in range(1, 13):
    d = dt.date(2026 if m <= 11 else 2025, m, 1)
    if d <= today:
        mk(f"backups/db-{d}.sql.gz", d, 500_000)
mk("backups/db-2025-12-01.sql.gz", dt.date(2025, 12, 1), 500_000)
mk("backups/db-2025-10-01.sql.gz", dt.date(2025, 10, 1), 500_000)
for name in ["case-2024-0912-emails.mbox", "case-2024-0912-db-2024-09-01.sql.gz", "app-2024-08-30.log"]:
    mk(f"legal_hold/{name}", dt.date(2024, 9, 1), 300_000)
