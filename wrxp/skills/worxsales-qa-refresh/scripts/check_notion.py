"""Check the Notion scenario DB against the local scenarios and the newest result of every row.

Usage: python3 check_notion.py <watch.json> [--fix-out-of-scope] [--out report.json]
Reads the lane order from watch.json "lanes" (a JSON list, newest first):
  [{"dir": "runs/run-X"}, {"dir": "runs/run-stg", "only_ids_file": "runs/run-stg/_judged_ids.txt"}, ...]
A row's newest result is the first lane that has <dir>/<tc_id>.json with a verdict.

Checks
  rows       scenario rows missing from the DB, DB rows with no local scenario, 정책 상태 / 기대결과 differences
  results    DB 최근 판정 / 최근 실행 빌드 different from the newest local result (unpublished or stale)
  scope      범위 제외 rows that still show a verdict (--fix-out-of-scope clears it and explains why)
  schema     select options missing for values the scenarios or results use
Exit 0 when clean, 1 otherwise. Dashboard views are not reachable over REST; see SKILL.md step 6.
"""
import argparse, collections, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _notion import call, query

OOS = "범위 제외"
OOS_SUMMARY = "범위 제외: 기능정의서 갱신으로 테스트 대상에서 빠짐(이전 판정 기록은 페이지 본문에 남음)"


def txt(prop):
    return "".join(t["plain_text"] for t in prop.get("rich_text", []) or prop.get("title", []))


def sel(prop):
    return (prop.get("select") or {}).get("name")


def newest(lanes):
    out = {}
    for lane in lanes:
        only = set(open(lane["only_ids_file"]).read().replace("\n", ",").split(",")) if lane.get("only_ids_file") else None
        for f in glob.glob(os.path.join(lane["dir"], "TC-*.json")):
            t = os.path.basename(f)[:-5]
            if t in out or (only is not None and t not in only): continue
            try: r = json.load(open(f, encoding="utf-8"))
            except ValueError: continue
            if r.get("verdict"): out[t] = {**r, "_lane": lane["dir"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("--fix-out-of-scope", action="store_true"); ap.add_argument("--out")
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8"))
    cfg_file, key = w["scenario_db"].split(":")
    db = json.load(open(cfg_file, encoding="utf-8"))[key]
    local = {r["tc_id"]: r for f in glob.glob("scenarios/*/*.json") for r in json.load(open(f, encoding="utf-8"))}
    res = newest(json.load(open(w["lanes"], encoding="utf-8")))
    schema = call("GET", f"/databases/{db}")["properties"]
    remote = {}
    for p in query(db, 20000):
        pr = p["properties"]
        remote[txt(pr["TC ID"])] = {"pid": p["id"], "verdict": sel(pr["최근 판정"]), "build": txt(pr["최근 실행 빌드"]),
                                    "policy": sel(pr["정책 상태"]), "expected": txt(pr["기대결과"]), "menu": sel(pr["메뉴"])}
    rep = collections.defaultdict(list)
    rep["missing_in_db"] = sorted(set(local) - set(remote))
    rep["extra_in_db"] = sorted(set(remote) - set(local))
    for t, r in local.items():
        x = remote.get(t)
        if not x: continue
        if x["policy"] != r["policy"]: rep["policy_differs"].append((t, x["policy"], r["policy"]))
        if x["expected"] != (r.get("expected") or ""): rep["expected_differs"].append(t)
        if r["policy"] == OOS:
            if x["verdict"]: rep["out_of_scope_with_verdict"].append(t)
            continue
        n = res.get(t)
        if not n:
            if x["verdict"]: rep["db_verdict_without_local_result"].append(t)
            else: rep["never_run"].append(t)
        elif n["verdict"] != x["verdict"] or n.get("build", "") != x["build"]:
            rep["result_not_published"].append((t, x["verdict"], n["verdict"], n["_lane"]))
    used = {"메뉴": {r["menu"] for r in local.values()}, "정책 상태": {r["policy"] for r in local.values()},
            "최근 판정": {n["verdict"] for n in res.values()}}
    for prop, vals in used.items():
        opts = {o["name"] for o in schema[prop]["select"]["options"]}
        for v in sorted(vals - opts): rep["select_option_missing"].append((prop, v))
    if a.fix_out_of_scope:
        for t in rep["out_of_scope_with_verdict"]:
            call("PATCH", f"/pages/{remote[t]['pid']}", {"properties": {"최근 판정": {"select": None},
                 "최근 요약": {"rich_text": [{"type": "text", "text": {"content": OOS_SUMMARY}}]}}})
        rep["fixed_out_of_scope"] = list(rep.pop("out_of_scope_with_verdict"))
    dist = collections.Counter(x["verdict"] for t, x in remote.items() if local.get(t, {}).get("policy") != OOS)
    print(f"db rows={len(remote)} scenarios={len(local)} in scope={sum(1 for r in local.values() if r['policy'] != OOS)} verdicts={dict(dist)}")
    bad = {k: len(v) for k, v in rep.items() if v and k != "fixed_out_of_scope"}
    for k, v in rep.items(): print(f"  {k}: {len(v)}", (v[:5] if v else ""))
    if a.out: json.dump(dict(rep, distribution=dict(dist)), open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
