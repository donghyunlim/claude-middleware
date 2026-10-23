"""Create the QA 상황판 page (once) and record its id in refresh/watch.json dashboard.page_id.

Usage: python3 <skill>/scripts/create_dashboard_page.py [--parent PAGE_ID] [--title TEXT] [--dry-run]
  Run from the QA workspace. The parent defaults to config.json parent_page_id.
  The page gets one intro callout and a divider. worxsales-qa-dashboard-update's sync_notion.py later inserts the
  「📌 현재 요약 (자동 갱신)」 block and creates the two history DBs on this page. The board views over the
  scenario DB are added with the Notion MCP view tools (REST cannot create views); see references/notion.md.
  Refuses when watch.json already has dashboard.page_id.
Env: NOTION_API_KEY.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH = "refresh/watch.json"


def arg(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv):
    if "-h" in argv or "--help" in argv:
        sys.exit(__doc__)
    cfg = json.load(open("config.json", encoding="utf-8"))
    w = json.load(open(WATCH, encoding="utf-8"))
    parent = arg(argv, "--parent", cfg.get("parent_page_id"))
    title = arg(argv, "--title", "WorxSales QA 상황판")
    if not parent:
        sys.exit("no parent page: pass --parent or set config.json parent_page_id")
    if w.get("dashboard", {}).get("page_id"):
        sys.exit(f"watch.json already has dashboard.page_id={w['dashboard']['page_id']}")
    intro = ("시나리오 DB의 판정 현황입니다. 아래 요약과 회차 이력은 worxsales-qa-dashboard-update가 갱신하고, "
             "보기(뷰)는 시나리오 DB의 연결 뷰입니다.")
    body = {"parent": {"page_id": parent}, "icon": {"emoji": "📊"},
            "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
            "children": [{"type": "callout", "callout": {"rich_text": [{"type": "text", "text": {"content": intro}}], "icon": {"emoji": "ℹ️"}}},
                         {"type": "divider", "divider": {}}]}
    if "--dry-run" in argv:
        print(json.dumps(body, ensure_ascii=False)[:400])
        return 0
    sys.path.insert(0, HERE)
    from notion_api import call
    p = call("POST", "/pages", body)
    w.setdefault("dashboard", {})["page_id"] = p["id"].replace("-", "")
    json.dump(w, open(WATCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(p["id"], p["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
