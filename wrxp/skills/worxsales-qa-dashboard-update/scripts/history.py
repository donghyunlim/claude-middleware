"""Rebuild the QA round history from every result lane, from the first pilot to now.

Usage: python3 history.py <watch.json> [--out refresh/history.json]
Env: NOTION_API_KEY (reads each scenario row's 생성 배치 to know when the row entered scope).

A round is one result lane. Rounds are ordered by the time their last row finished. The state after
round k is what the DB would have shown then: for every row, the newest result among lanes finished by
then, with the lane priority of lanes.json (newest first; extra history lanes last). The final round
therefore matches check_notion.py.

Denominator: a row counts from the date in its 생성 배치 label (e.g. full-2026-10-08) and is left out
when its current 정책 상태 is 범위 제외. Exclusion dates are not recorded per row, so earlier rounds
also leave out rows that were excluded later (stated in metrics.md).
"""
import argparse, collections, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _notion import query

OOS = "범위 제외"
IMPL = ("OK", "부분 OK")
VERDICTS = ["OK", "부분 OK", "미구현", "문제", "실행 불가", "보류-기록", "알려진 차이"]
# order matters: the first matching group wins
BLOCK_REASONS = [
    ("쓰기 범위 밖", ("쓰기 범위", "실제 발송", "실발송", "적용하기", "전화 걸기", "고객 대상")),
    ("도구 한계", ("주소창", "주소 입력", "주소 직접", "네이티브", "픽스처", "자동화", "시연 모드", "더블클릭", "다른 브라우저",
                "두 번째 사용자", "실패를 만들", "실패시킬", "실패 유도", "장애 주입", "공유 실행 세션", "지연시킬")),
    ("원천 미연결", ("원천 미연결", "CORE_SOURCE_UNAVAILABLE", "원천 범위", "provider 미연결", "미연결 안내")),
    ("서버 설정·응답 오류", ("NOT_CONFIGURED", "응답 형식", "조회하지 못했습니다", "조회 실패", "HTTP", "INVALID", "찾을 수 없습니다")),
    ("데이터 없음", ("사전조건", "데이터", "없어", "없습니다", "찾지 못", "0건")),
]


def block_reason(r):
    text = " ".join(str(x) for x in (r.get("outcome"), r.get("headline"), (r.get("details") or {}).get("verdict_reason"), r.get("verdict_reason")) if x)
    return next((name for name, keys in BLOCK_REASONS if any(k in text for k in keys)), "기타")


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


def build_of(rows):
    c = collections.Counter(re.search(r"desktop ([0-9a-f]{7})", r.get("build") or "").group(1)
                            for r in rows.values() if re.search(r"desktop ([0-9a-f]{7})", r.get("build") or ""))
    return c.most_common(1)[0][0] if c else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("--out", default="refresh/history.json")
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8"))
    lanes = json.load(open(w["lanes"], encoding="utf-8")) + w.get("history", {}).get("extra_lanes", [])
    cfg_file, key = w["scenario_db"].split(":")
    db = json.load(open(cfg_file, encoding="utf-8"))[key]
    born = {}
    for p in query(db, 20000):
        pr = p["properties"]
        tid = "".join(t["plain_text"] for t in pr["TC ID"]["rich_text"])
        m = re.search(r"\d{4}-\d{2}-\d{2}", "".join(t["plain_text"] for t in pr["생성 배치"]["rich_text"]))
        born[tid] = m.group(0) if m else "0000-00-00"
    scen = {r["tc_id"]: r for f in glob.glob("scenarios/*/*.json") for r in json.load(open(f, encoding="utf-8"))}

    loaded = []
    for prio, lane in enumerate(lanes):
        rows = lane_rows(lane)
        if not rows: continue
        ends = sorted(r.get("ended_at") or r.get("started_at") or "" for r in rows.values())
        loaded.append({"prio": prio, "lane": lane, "rows": rows, "start": ends[0][:16], "end": ends[-1][:16], "build": build_of(rows)})
    loaded.sort(key=lambda x: x["end"])

    rounds, prev_problem, prev_blocked = [], set(), set()
    for k, rd in enumerate(loaded):
        done = sorted(loaded[:k + 1], key=lambda x: x["prio"])  # lanes.json priority among finished lanes
        state = {}
        for ln in done:
            for t, r in ln["rows"].items(): state.setdefault(t, r)
        day = rd["end"][:10]
        scope = [t for t, s in scen.items() if s["policy"] != OOS and born.get(t, "9999") <= day]
        cnt = collections.Counter(state[t]["verdict"] for t in scope if t in state)
        executed = sum(cnt.values())
        problem = {t for t in scope if t in state and state[t]["verdict"] == "문제"}
        blocked = collections.Counter(block_reason(state[t]) for t in scope if t in state and state[t]["verdict"] == "실행 불가")
        write_blocked = {t for t in scope if t in state and state[t]["verdict"] == "실행 불가" and block_reason(state[t]) == "쓰기 범위 밖"}
        role_gap = sum(1 for t in scope if t in state and "권한 미적용" in (state[t].get("outcome") or "")[:12])
        menus = {}
        for t in scope:
            m = scen[t]["menu"].split(".")[0]
            e = menus.setdefault(m, {"name": scen[t]["menu"], "target": 0, "executed": 0, "impl": 0, "unimpl": 0, "problem": 0})
            e["target"] += 1
            if t in state:
                v = state[t]["verdict"]; e["executed"] += 1
                e["impl"] += v in IMPL; e["unimpl"] += v == "미구현"; e["problem"] += v == "문제"
        for e in menus.values():
            e["impl_rate"] = round(100 * e["impl"] / e["executed"], 1) if e["executed"] else None
        pct = lambda n: round(100 * n / executed, 1) if executed else None
        rounds.append({
            "round": k + 1, "lane": os.path.basename(rd["lane"]["dir"].rstrip("/")), "build": rd["build"],
            "start": rd["start"], "end": rd["end"], "lane_rows": len(rd["rows"]),
            "target": len(scope), "executed": executed, "coverage": round(100 * executed / len(scope), 1) if scope else None,
            "verdicts": {v: cnt.get(v, 0) for v in VERDICTS},
            "impl_rate": pct(cnt["OK"] + cnt["부분 OK"]), "ok_rate": pct(cnt["OK"]), "unimpl_rate": pct(cnt["미구현"]),
            "problem": len(problem), "problem_new": len(problem - prev_problem), "problem_resolved": len(prev_problem - problem),
            "blocked": {name: blocked.get(name, 0) for name, _ in BLOCK_REASONS + [("기타", ())]},
            "write_blocked": len(write_blocked), "write_blocked_new": sorted(write_blocked - prev_blocked),
            "role_gap": role_gap, "menus": dict(sorted(menus.items(), key=lambda kv: int(kv[0]))),
        })
        prev_problem, prev_blocked = problem, write_blocked
    out = {"generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"), "rounds": rounds}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in rounds:
        print(f"{r['round']:2d} {r['lane']:<34} {r['build'] or '-':7} {r['end']}  대상 {r['target']:4d} 실행 {r['executed']:4d}  구현도 {r['impl_rate']}%  미구현 {r['unimpl_rate']}%  문제 {r['problem']} (+{r['problem_new']}/-{r['problem_resolved']})  쓰기범위밖 {r['write_blocked']}")


if __name__ == "__main__":
    main()
