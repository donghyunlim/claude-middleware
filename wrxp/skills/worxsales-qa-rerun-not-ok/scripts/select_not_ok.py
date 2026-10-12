"""Pick every scenario row that is not OK yet, across all menus.

Usage: python3 select_not_ok.py <watch.json> --out <ids.txt> [--menus 7,11] [--exclude-lane runs/run-...]

A row is picked when it is in scope (정책 상태 is not 범위 제외) and
  - it has no result in any lane, or
  - its latest result is not `OK` (부분 OK, 미구현, 문제, 실행 불가, 보류-기록, 알려진 차이), or
  - its latest result is `OK` but the row's expected result changed on or after the day of that result.
    Changes are read from scenarios/<menu>/_changed_ids_<YYYY-MM-DD>.txt (one TC ID per line).
The latest result follows the lane priority in watch.json `lanes` (newest first; history.extra_lanes last),
the same order the dashboard and check_notion use. --exclude-lane ignores a lane (e.g. the one being filled).
"""
import argparse, collections, glob, json, os, re


def lane_rows(lane):
    only = set(open(lane["only_ids_file"]).read().replace("\n", ",").split(",")) if lane.get("only_ids_file") else None
    out = {}
    for f in glob.glob(os.path.join(lane["dir"], "TC-*.json")):
        t = os.path.basename(f)[:-5]
        if only is not None and t not in only: continue
        try: r = json.load(open(f, encoding="utf-8"))
        except ValueError: continue
        if r.get("verdict"): out[t] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("--out", required=True)
    ap.add_argument("--menus", default=""); ap.add_argument("--exclude-lane", action="append", default=[])
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8"))
    lanes = json.load(open(w["lanes"], encoding="utf-8")) + w.get("history", {}).get("extra_lanes", [])
    skip = {os.path.normpath(d) for d in a.exclude_lane}
    latest = {}
    for ln in lanes:
        if os.path.normpath(ln["dir"]) in skip: continue
        for t, r in lane_rows(ln).items(): latest.setdefault(t, r)
    changed = {}
    for f in glob.glob("scenarios/*/_changed_ids_*.txt"):
        m = re.search(r"_changed_ids_(\d{4}-\d{2}-\d{2})\.txt$", f)
        if not m: continue
        for t in (l.strip() for l in open(f, encoding="utf-8")):
            if t: changed[t] = max(changed.get(t, ""), m.group(1))
    menus = {m.strip() for m in a.menus.split(",") if m.strip()}
    picked, why = [], collections.Counter()
    for f in sorted(glob.glob("scenarios/*/*.json")):
        for s in json.load(open(f, encoding="utf-8")):
            t = s["tc_id"]
            if s.get("policy") == "범위 제외": continue
            if menus and s["menu"].split(".")[0] not in menus: continue
            r = latest.get(t)
            if r is None: picked.append(t); why["미실행"] += 1; continue
            v = r["verdict"]
            if v != "OK": picked.append(t); why[v] += 1; continue
            day = (r.get("ended_at") or r.get("started_at") or "")[:10]
            if t in changed and changed[t] >= day: picked.append(t); why["OK·기대결과 변경"] += 1
    open(a.out, "w", encoding="utf-8").write("\n".join(picked) + "\n")
    print(f"picked={len(picked)} -> {a.out}", dict(why))


if __name__ == "__main__":
    main()
