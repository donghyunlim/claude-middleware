"""Generates fixture/data/*.csv (seed 20260807) and hidden/truth.csv + reference/retention.csv.
Run: python3 gen_data.py  (from anywhere)"""
import csv
import datetime as dt
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent.parent
KST = dt.timezone(dt.timedelta(hours=9))
UTC = dt.timezone.utc
rng = random.Random(20260807)
START = dt.datetime(2026, 8, 3, tzinfo=KST)        # Monday
END_SIGNUP = START + dt.timedelta(weeks=8)
END_EVENTS = dt.datetime(2026, 11, 2, tzinfo=KST)


def ts(d):
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def rand_time_in_day(day, early=False):
    if early:  # Monday 00:00-08:59 KST == Sunday UTC
        return day + dt.timedelta(seconds=rng.randrange(0, 9 * 3600))
    return day + dt.timedelta(seconds=rng.randrange(0, 86400))


users, events = [], []
N = 1300
for i in range(N):
    internal = rng.random() < 0.06
    uid = (f"test_{i:04d}" if rng.random() < 0.5 else f"u{100000 + i}") if internal else f"u{100000 + i}"
    if internal and uid.startswith("u"):
        email = f"qa{i}@ourapp.kr"
    else:
        email = f"user{i}@" + rng.choice(["gmail.com", "naver.com", "kakao.com", "daum.net"])
    channel = rng.choice(["organic", "ads", "referral"])
    week = rng.randrange(8)
    wk_start = START + dt.timedelta(weeks=week)
    r = rng.random()
    if r < 0.22:
        signup = rand_time_in_day(wk_start, early=True)               # Mon early KST
    elif r < 0.32:
        signup = rand_time_in_day(wk_start + dt.timedelta(days=6))     # Sunday KST
    else:
        signup = rand_time_in_day(wk_start + dt.timedelta(days=rng.randrange(7)))
    users.append({"user_id": uid, "email": email, "signup_channel": channel})
    events.append((signup, uid, "signup", ""))
    login_p = 0.9 if internal else rng.uniform(0.3, 0.85)
    pay_p = 0.95 if internal else rng.uniform(0.05, 0.45)
    t = signup
    k = 0
    while True:
        k += 1
        wk = wk_start + dt.timedelta(weeks=k)
        if wk >= END_EVENTS:
            break
        decay = 0.88 ** k
        for _ in range(rng.randrange(1, 4)):
            if rng.random() < login_p * decay + 0.05:
                d = wk + dt.timedelta(days=rng.randrange(7))
                events.append((rand_time_in_day(d, early=rng.random() < 0.2), uid, "login", ""))
        if rng.random() < pay_p * decay:
            d = wk + dt.timedelta(days=rng.choice([0, 0, 1, 2, 3, 4, 5, 6]))
            events.append((rand_time_in_day(d, early=rng.random() < 0.35), uid, "payment",
                           rng.choice([9900, 14900, 29000])))
        if rng.random() < 0.12:
            d = wk + dt.timedelta(days=rng.randrange(7))
            events.append((rand_time_in_day(d, early=rng.random() < 0.3), uid, "payment_failed",
                           rng.choice([9900, 14900, 29000])))

events.sort(key=lambda e: (e[0], e[1]))
fx = TASK / "fixture" / "data"
fx.mkdir(parents=True, exist_ok=True)
with open(fx / "users.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["user_id", "email", "signup_channel"])
    w.writeheader()
    w.writerows(users)
with open(fx / "events.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["event_id", "user_id", "event_type", "event_ts", "amount"])
    for n, (t, uid, et, amt) in enumerate(events, 1):
        w.writerow([f"e{n:06d}", uid, et, ts(t), amt])

# ground truth
internal = {u["user_id"] for u in users if u["user_id"].startswith("test_") or u["email"].endswith("@ourapp.kr")}
cohort, pays = {}, defaultdict(set)
for t, uid, et, _ in events:
    if uid in internal:
        continue
    k = t.astimezone(KST)
    monday = (k - dt.timedelta(days=k.weekday())).date()
    if et == "signup":
        cohort[uid] = monday
    elif et == "payment":
        pays[uid].add(monday)
rows = []
for cw in sorted(set(cohort.values())):
    mem = [u for u, c in cohort.items() if c == cw]
    r = [cw.isoformat(), len(mem)]
    for k in range(1, 5):
        target = cw + dt.timedelta(weeks=k)
        r.append(f"{sum(1 for u in mem if target in pays[u]) / len(mem):.4f}")
    rows.append(r)
for p in (TASK / "hidden" / "truth.csv", HERE / "retention.csv"):
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cohort_week", "cohort_size", "W1", "W2", "W3", "W4"])
        w.writerows(rows)
print(len(users), len(events), len(internal))
for r in rows:
    print(r)
