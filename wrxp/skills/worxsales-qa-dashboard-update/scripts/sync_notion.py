"""Write refresh/history.json to the Notion 상황판: two history tables and the summary block at the top.

Usage: python3 sync_notion.py <watch.json> <history.json> [--dry-run]
Env: NOTION_API_KEY.

- 「QA 회차 이력」 and 「QA 메뉴별 구현도 이력」 are inline databases on the 상황판 page, created on first
  run; their IDs are stored in watch.json dashboard.history_db_id / menu_history_db_id. Rows are
  upserted by title (R<round> · <lane> / R<round> · <menu>), so a rebuilt history overwrites in place.
- The summary block sits right after the page's first block, between a heading that starts with
  MARKER and the next divider. Only that span is replaced; everything people wrote stays.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _notion import call, children, query

MARKER = "📌 현재 요약 (자동 갱신)"
VERDICTS = ["OK", "부분 OK", "미구현", "문제", "실행 불가", "보류-기록", "알려진 차이"]


def rt(s): return [{"type": "text", "text": {"content": str(s)[:1900]}}]
def num(fmt="number"): return {"number": {"format": fmt}}


def round_schema(blocked):
    p = {"회차": {"title": {}}, "회차 번호": num(), "레인": {"rich_text": {}}, "빌드": {"rich_text": {}}, "마친 시각": {"date": {}},
         "대상": num(), "실행": num(), "실행률": num("percent"), "구현도": num("percent"), "OK율": num("percent"), "미구현율": num("percent"),
         "문제 신규": num(), "문제 해소": num(), "권한 미적용": num(), "쓰기 범위 밖": num(), "쓰기 범위 밖 신규": num()}
    for v in VERDICTS: p[v] = num()
    for b in blocked: p[f"실행 불가·{b}"] = num()
    return p


MENU_SCHEMA = {"회차·메뉴": {"title": {}}, "회차 번호": num(), "메뉴": {"select": {}}, "빌드": {"rich_text": {}}, "대상": num(), "실행": num(),
               "OK+부분 OK": num(), "미구현": num(), "문제": num(), "구현도": num("percent")}


def frac(v): return None if v is None else round(v / 100, 4)


def ensure_db(w, key, title, schema, page, dry):
    d = w["dashboard"]
    if d.get(key):
        db = call("GET", f"/databases/{d[key]}")
        missing = {k: v for k, v in schema.items() if k not in db["properties"]}
        if missing and not dry: call("PATCH", f"/databases/{d[key]}", {"properties": missing})
        return d[key]
    if dry: return None
    db = call("POST", "/databases", {"parent": {"type": "page_id", "page_id": page}, "is_inline": True,
                                      "title": rt(title), "properties": schema})
    d[key] = db["id"]
    return db["id"]


def upsert(db, title_prop, rows, dry):
    if dry and not db: return len(rows)
    have = {}
    for p in query(db):
        have["".join(t["plain_text"] for t in p["properties"][title_prop]["title"])] = p["id"]
    n = 0
    for title, props in rows:
        props = {title_prop: {"title": rt(title)}, **props}
        if dry: n += 1; continue
        if title in have: call("PATCH", f"/pages/{have[title]}", {"properties": props})
        else: call("POST", "/pages", {"parent": {"database_id": db}, "properties": props})
        n += 1
    return n


def summary_blocks(h, page_url):
    rs = h["rounds"]; c = rs[-1]; p = rs[-2] if len(rs) > 1 else c
    d = None if c["impl_rate"] is None or p["impl_rate"] is None else round(c["impl_rate"] - p["impl_rate"], 1)
    li = lambda s: {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(s)}}
    items = [
        f'대상 {c["target"]:,}행 · 실행 {c["executed"]:,}행 ({c["coverage"]}%)',
        f'구현도(OK+부분 OK) {c["impl_rate"]}% · 직전 회차 대비 {("+" if d and d > 0 else "") + str(d) + "p" if d else "변화 없음"}',
        f'미구현 {c["verdicts"]["미구현"]:,}행 ({c["unimpl_rate"]}%) · OK {c["verdicts"]["OK"]:,} · 부분 OK {c["verdicts"]["부분 OK"]:,}',
        f'문제(확정) {c["problem"]}행 · 이번 회차 신규 {c["problem_new"]} · 해소 {c["problem_resolved"]}',
        f'실행 불가 {c["verdicts"]["실행 불가"]:,}행: ' + ", ".join(f"{k} {v}" for k, v in c["blocked"].items() if v),
        f'권한 미적용 {c["role_gap"]}행 · 쓰기 범위 밖 {c["write_blocked"]}행 (이번 회차 신규 {len(c["write_blocked_new"])})',
    ]
    out = [{"type": "heading_2", "heading_2": {"rich_text": rt(MARKER)}},
           {"type": "callout", "callout": {"icon": {"emoji": "🧭"}, "color": "gray_background",
            "rich_text": rt(f'회차 {c["round"]} · desktop {c["build"]} · {c["end"].replace("T", " ")} 기준')}}]
    out += [li(s) for s in items]
    if page_url:
        out.append({"type": "paragraph", "paragraph": {"rich_text": [
            {"type": "text", "text": {"content": "회차별 구현도 점도표와 전체 표: "}},
            {"type": "text", "text": {"content": "WorxSales QA 진척판", "link": {"url": page_url}}}]}})
    out.append({"type": "divider", "divider": {}})
    return out


def replace_summary(page, blocks, dry):
    kids = children(page)
    start = next((i for i, b in enumerate(kids) if b["type"] == "heading_2" and
                  "".join(t.get("plain_text", "") for t in b["heading_2"]["rich_text"]).startswith(MARKER)), None)
    old = []
    if start is not None:
        end = next((i for i in range(start, len(kids)) if kids[i]["type"] == "divider"), start)
        old = kids[start:end + 1]
    anchor = kids[start - 1]["id"] if start else (kids[0]["id"] if kids else None)
    if dry: return len(old), len(blocks)
    for b in old: call("DELETE", f"/blocks/{b['id']}")
    body = {"children": blocks, **({"after": anchor} if anchor else {})}
    call("PATCH", f"/blocks/{page}/children", body)
    return len(old), len(blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("history"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8")); h = json.load(open(a.history, encoding="utf-8"))
    page = w["dashboard"]["page_id"]; dry = a.dry_run
    blocked = list(h["rounds"][-1]["blocked"])
    rdb = ensure_db(w, "history_db_id", "QA 회차 이력", round_schema(blocked), page, dry)
    mdb = ensure_db(w, "menu_history_db_id", "QA 메뉴별 구현도 이력", MENU_SCHEMA, page, dry)
    if not dry: json.dump(w, open(a.watch, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rrows, mrows = [], []
    for r in h["rounds"]:
        props = {"회차 번호": {"number": r["round"]}, "레인": {"rich_text": rt(r["lane"])}, "빌드": {"rich_text": rt(r["build"] or "-")},
                 "마친 시각": {"date": {"start": r["end"] + ":00+09:00"}}, "대상": {"number": r["target"]}, "실행": {"number": r["executed"]},
                 "실행률": {"number": frac(r["coverage"])}, "구현도": {"number": frac(r["impl_rate"])}, "OK율": {"number": frac(r["ok_rate"])},
                 "미구현율": {"number": frac(r["unimpl_rate"])}, "문제 신규": {"number": r["problem_new"]}, "문제 해소": {"number": r["problem_resolved"]},
                 "권한 미적용": {"number": r["role_gap"]}, "쓰기 범위 밖": {"number": r["write_blocked"]},
                 "쓰기 범위 밖 신규": {"number": len(r["write_blocked_new"])}}
        props.update({v: {"number": r["verdicts"][v]} for v in VERDICTS})
        props.update({f"실행 불가·{b}": {"number": r["blocked"].get(b, 0)} for b in blocked})
        rrows.append((f'R{r["round"]:02d} · {r["lane"]}', props))
        for m, e in r["menus"].items():
            mrows.append((f'R{r["round"]:02d} · {e["name"]}', {
                "회차 번호": {"number": r["round"]}, "메뉴": {"select": {"name": e["name"]}}, "빌드": {"rich_text": rt(r["build"] or "-")},
                "대상": {"number": e["target"]}, "실행": {"number": e["executed"]}, "OK+부분 OK": {"number": e["impl"]},
                "미구현": {"number": e["unimpl"]}, "문제": {"number": e["problem"]}, "구현도": {"number": frac(e["impl_rate"])}}))
    n1 = upsert(rdb, "회차", rrows, dry) if rdb or dry else 0
    n2 = upsert(mdb, "회차·메뉴", mrows, dry) if mdb or dry else 0
    old, new = replace_summary(page, summary_blocks(h, w["dashboard"].get("publish", {}).get("url")), dry)
    print(f"{'dry run' if dry else 'synced'}: rounds={n1} menu_rows={n2} summary blocks replaced {old} → {new}")


if __name__ == "__main__":
    main()
