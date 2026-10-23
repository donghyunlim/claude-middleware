"""Create the scenario DB (once) under a Notion page and record ids in the workspace config.json.

Usage: python3 <skill>/scripts/create_db.py <parent_page_id> [--menus FILE] [--title TEXT] [--dry-run]
  Run from the QA workspace. Creates an inline DB with the scenario columns and the latest-run columns that
  worxsales-qa-executor's publish_results.py writes (최근 판정 · 최근 실행일 · 최근 실행 빌드 · 최근 증거 · 최근 요약).
  Menu options come from --menus, else scenarios/menus.json, else the bundled assets/menus.json.
  Refuses to run when config.json already has scenario_db_id (one DB per workspace; delete the key on purpose to redo).
  config.json keeps every other key; only parent_page_id and scenario_db_id are set.
  --dry-run prints the property names and exits without calling Notion.
Env: NOTION_API_KEY.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VERDICTS = ["OK", "부분 OK", "문제", "미구현", "보류-기록", "알려진 차이", "실행 불가"]


def sel(*names):
    return {"select": {"options": [{"name": n} for n in names]}}


def props(menus):
    return {
        "시나리오명": {"title": {}},
        "TC ID": {"rich_text": {}},
        "메뉴": sel(*menus),
        "화면": {"rich_text": {}},
        "화면 정의": {"url": {}},
        "역할": sel("영업자", "영업팀장·관리자", "영업운영", "권한 관리자"),
        "권한 수준": sel("수정 가능", "조회만"),
        "서비스": {"multi_select": {"options": [{"name": "JK"}, {"name": "AM"}]}},
        "대상 관계": sel("본인 담당", "다른 담당", "범위 밖", "해당 없음"),
        "유형": sel("정상", "필수값 누락", "형식·경계값", "권한 거부", "조회만 차단", "상태·예외", "이동·복귀"),
        "사전조건": {"rich_text": {}},
        "절차": {"rich_text": {}},
        "입력값": {"rich_text": {}},
        "비울 값": {"rich_text": {}},
        "필수정보": {"rich_text": {}},
        "기대결과": {"rich_text": {}},
        "검증 지점": {"rich_text": {}},
        "근거": {"rich_text": {}},
        "정책 상태": sel("확정", "확정 필요(보류)", "범위 제외"),
        "구현 상태": sel("미확인", "구현됨", "미구현", "정책과 다름"),
        "우선순위": sel("P0", "P1", "P2"),
        "실행 방식": sel("합성 데이터", "실서버 필요", "수동"),
        "외부 영향": {"checkbox": {}},
        "생성 배치": {"rich_text": {}},
        "최근 판정": sel(*VERDICTS),
        "최근 실행일": {"date": {}},
        "최근 실행 빌드": {"rich_text": {}},
        "최근 증거": {"url": {}},
        "최근 요약": {"rich_text": {}},
    }


def main(argv):
    pos = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("-") and argv[i - 1] not in ("--menus", "--title")]
    if len(pos) != 1 or "-h" in argv or "--help" in argv:
        sys.exit(__doc__)
    parent = pos[0]
    mf = argv[argv.index("--menus") + 1] if "--menus" in argv else (
        "scenarios/menus.json" if os.path.exists("scenarios/menus.json") else os.path.join(HERE, "..", "assets", "menus.json"))
    title = argv[argv.index("--title") + 1] if "--title" in argv else "WorxSales 테스트 시나리오"
    p = props(json.load(open(mf, encoding="utf-8")))
    if "--dry-run" in argv:
        print(title, "|", len(p), "properties:", ", ".join(p))
        return 0
    cfg = json.load(open("config.json", encoding="utf-8")) if os.path.exists("config.json") else {}
    if cfg.get("scenario_db_id"):
        sys.exit(f"config.json already has scenario_db_id={cfg['scenario_db_id']}; not creating a second DB")
    sys.path.insert(0, HERE)
    from notion_api import call
    db = call("POST", "/databases", {
        "parent": {"type": "page_id", "page_id": parent},
        "title": [{"type": "text", "text": {"content": title}}],
        "description": [{"type": "text", "text": {"content": "기능정의서·역할 권한 문서 기준 사용자 시나리오. 행 = 시나리오 × 역할 × 대상 관계. 만든 방법은 「테스트 시나리오 DB 만들기」 페이지를 참고합니다."}}],
        "is_inline": True,
        "properties": p,
    })
    cfg.update(parent_page_id=parent, scenario_db_id=db["id"])
    json.dump(cfg, open("config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(db["id"], db["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
