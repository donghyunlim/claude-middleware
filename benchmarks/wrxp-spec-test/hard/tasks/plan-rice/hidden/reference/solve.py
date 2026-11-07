"""Reference RICE ranking. Usage: python3 solve.py FIXTURE_DIR (writes ranked.json in cwd)."""
import csv, json, re, sys
from pathlib import Path
from fractions import Fraction as F

PER = {"월": F(3), "분기": F(1), "연": F(1, 4)}
UNIT = {"개월": F(1), "주": F(1, 4), "일": F(1, 20)}


def months(s):
    m = re.fullmatch(r"([\d.]+)(개월|주|일)", s.strip())
    return F(m.group(1)) * UNIT[m.group(2)]


rows = []
for r in csv.DictReader(open(Path(sys.argv[1]) / "backlog.csv")):
    reach = F(r["reach"]) * PER[r["reach_period"]]
    conf = F(r["confidence_pct"]) / 100
    if r["user_research"] == "N":
        conf = min(conf, F(1, 2))
    eff = int(r["team_size"]) * months(r["duration"])
    rows.append((reach * F(r["impact"]) * conf / eff, eff, r["id"]))
rows.sort(key=lambda t: (-t[0], t[1], t[2]))
json.dump([{"id": i, "score": round(float(s), 1)} for s, _, i in rows], open("ranked.json", "w"), indent=1)
for s, e, i in rows:
    print(i, float(s), float(e))
