"""Upsert scenarios/**/*.json into the 시나리오 DB, keyed by TC ID.

Usage: python3 <skill>/scripts/sync_scenarios.py <scenario_dir> <batch_label> [--dry-run] [--skip=N]
Run from the QA workspace (reads config.json scenario_db_id). Env: NOTION_API_KEY (not needed for --dry-run).
An existing row keeps its 생성 배치; the dashboard counts a row from that batch date on.
(--skip=N resumes an interrupted run: the first N rows in file order are left as they are.)
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from notion_api import call

DB = None


def rt(s):
    s = s or ""
    return [{"type": "text", "text": {"content": s[i:i + 1900]}} for i in range(0, len(s), 1900)][:100]


def props(r, batch):
    return {
        "시나리오명": {"title": rt(r["title"])},
        "TC ID": {"rich_text": rt(r["tc_id"])},
        "메뉴": {"select": {"name": r["menu"]}},
        "화면": {"rich_text": rt(r["screen"])},
        "화면 정의": {"url": r["screen_url"] or None},
        "역할": {"select": {"name": r["role"]}},
        "권한 수준": {"select": {"name": r["access"]}},
        "서비스": {"multi_select": [{"name": s} for s in r["services"]]},
        "대상 관계": {"select": {"name": r["target"]}},
        "유형": {"select": {"name": r["type"]}},
        "사전조건": {"rich_text": rt(r["precondition"])},
        "절차": {"rich_text": rt(r["steps"])},
        "입력값": {"rich_text": rt(r["inputs"])},
        "비울 값": {"rich_text": rt(r["omit"])},
        "필수정보": {"rich_text": rt(r["required"])},
        "기대결과": {"rich_text": rt(r["expected"])},
        "검증 지점": {"rich_text": rt(r["checkpoints"])},
        "근거": {"rich_text": rt(r["evidence"])},
        "정책 상태": {"select": {"name": r["policy"]}},
        "구현 상태": {"select": {"name": r["impl"]}},
        "우선순위": {"select": {"name": r["priority"]}},
        "실행 방식": {"select": {"name": r["run_mode"]}},
        "외부 영향": {"checkbox": r["external"]},
        "생성 배치": {"rich_text": rt(batch)},
    }


def existing():
    out, cursor = {}, None
    while True:
        body = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
        r = call("POST", f"/databases/{DB}/query", body)
        for p in r["results"]:
            tid = "".join(t["plain_text"] for t in p["properties"]["TC ID"]["rich_text"])
            out[tid] = p["id"]
        if not r.get("has_more"):
            return out
        cursor = r["next_cursor"]


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(pos) != 2 or "-h" in sys.argv or "--help" in sys.argv:
        sys.exit(__doc__)
    (src, batch), dry = pos, "--dry-run" in sys.argv
    rows = [r for f in sorted(glob.glob(os.path.join(src, "**", "*.json"), recursive=True))
            if not os.path.basename(f).startswith("_") and os.path.basename(f) != "menus.json"
            for r in json.load(open(f, encoding="utf-8"))]
    skip = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--skip=")), 0)
    rows = rows[skip:]
    if dry:
        print(f"rows={len(rows)} (dry run: Notion not called)")
        sys.exit(0)
    DB = json.load(open("config.json", encoding="utf-8"))["scenario_db_id"]
    have = existing()
    created = updated = 0
    for r in rows:
        p = props(r, batch)
        if r["tc_id"] in have:
            p.pop("생성 배치")  # keep the batch that first created the row
            call("PATCH", f"/pages/{have[r['tc_id']]}", {"properties": p}); updated += 1
        else:
            call("POST", "/pages", {"parent": {"database_id": DB}, "properties": p}); created += 1
        if (created + updated) % 25 == 0:
            print("progress", created + updated, flush=True)
    print(f"rows={len(rows)} created={created} updated={updated} existing_before={len(have)}")
