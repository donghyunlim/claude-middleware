# Notion 준비

한국어 본문은 Notion MCP의 JSON 파라미터로 쓰면 글자가 깨진 사례가 있습니다. 그래서 DB 행과 문서는 REST 스크립트로 쓰고, Notion MCP는 REST로 할 수 없는 뷰 작업과 확인용 읽기에만 씁니다. 쓴 뒤에는 한 번 다시 읽어 글자를 확인합니다.

## 0. 공유

Notion integration(`NOTION_API_KEY`의 봇)이 다음 페이지를 읽을 수 있어야 합니다. 열 수 없는 페이지는 크롤에서 `errors`로 나오므로, 사용자에게 공유를 요청합니다.
- 읽기: 기능정의서 최상위 페이지, 목업 DB, 상위 작업 공간
- 쓰기: QA 페이지들을 둘 상위 페이지(`config.json`의 `parent_page_id`)

## 1. 시나리오 DB

```sh
python3 <skill>/scripts/create_db.py --help
bws-run "$PWD/scripts/run.sh" <skill>/scripts/create_db.py <parent_page_id>
```

- 시나리오 칸과 최근 실행 칸(최근 판정·최근 실행일·최근 실행 빌드·최근 증거·최근 요약)을 함께 만듭니다. 「최근 판정」 선택지에는 「부분 OK」가 들어 있습니다.
- `config.json`에 이미 `scenario_db_id`가 있으면 만들지 않습니다. DB는 작업 폴더당 하나입니다.

## 2. 문서 페이지

`docs/DB_만들기.md`(시나리오 DB를 만든 방법과 이력)를 게시합니다. 이후 시나리오를 바꿀 때마다 이력 표에 한 줄을 더하고 다시 게시합니다.

```sh
bws-run "$PWD/scripts/run.sh" <skill>/scripts/publish_doc.py docs/DB_만들기.md db_doc_page_id
```

## 3. 상황판

```sh
bws-run "$PWD/scripts/run.sh" <skill>/scripts/create_dashboard_page.py
```

페이지를 만든 뒤 Notion MCP의 뷰 생성 도구로 시나리오 DB의 연결 뷰를 상황판 페이지에 더합니다. 아래는 지금까지 써 온 구성입니다. 이름은 `watch.json`의 `dashboard.exclude_out_of_scope_views`·`plain_views`와 같아야 refresh의 상황판 점검이 맞습니다.

| 뷰 | 형태 | 필터 | 묶음·정렬 |
|---|---|---|---|
| ⏳ 미실행 | 표 | 최근 판정 비어 있음 AND 정책 상태 ≠ 범위 제외 | 메뉴로 묶음 |
| 판정 분포 | 차트(막대) | 정책 상태 ≠ 범위 제외 | 최근 판정별 개수 |
| 메뉴별 진행도 | 차트(가로 막대) | 정책 상태 ≠ 범위 제외 | 메뉴별, 최근 판정으로 색 구분 |
| 우선순위별 판정 | 차트 | 정책 상태 ≠ 범위 제외 | 우선순위별, 최근 판정으로 색 구분 |
| 판정 보드 | 보드 | 정책 상태 ≠ 범위 제외 | 최근 판정 |
| ❌ 문제 큐 | 표 | 최근 판정 = 문제 | 최근 실행일 내림차순 |
| ⚠️ 실행 불가(메뉴별) | 표 | 최근 판정 = 실행 불가 | 메뉴로 묶음 |
| 🕒 최근 실행 순 | 표 | 최근 실행일 비어 있지 않음 | 최근 실행일 내림차순 |

- 판정 선택지(OK, 부분 OK, 문제, 미구현, 보류-기록, 알려진 차이, 실행 불가)가 그룹·차트에서 숨김으로 빠지지 않았는지 확인합니다.
- 요약 블록과 회차 이력 DB 두 개는 dashboard-update의 `sync_notion.py`가 첫 실행에서 만듭니다. 미리 만들지 않습니다.
- 뷰를 만든 뒤 Notion MCP로 상황판을 열어 뷰 이름과 필터를 한 번 확인합니다. 점검 기준은 [상황판 점검표](../../worxsales-qa-refresh/references/dashboard.md)입니다.
