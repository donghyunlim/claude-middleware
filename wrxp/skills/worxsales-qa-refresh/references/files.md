# 작업 폴더 파일

모두 QA 작업 폴더의 `refresh/` 아래에 둡니다.

## run.sh

`bws-run`은 따옴표로 묶은 인자를 다시 나누므로 스크립트 실행을 래퍼로 감쌉니다.

```sh
#!/bin/sh
# refresh/run.sh <script.py> args...
cd "$(dirname "$0")/.." && S=$1 && shift && exec python3 -I <skill>/scripts/$S "$@"
```

## watch.json

```json
{
 "roots": [
  {"name": "기능정의서", "kind": "tree", "id": "<기능정의서 최상위 페이지>"},
  {"name": "목업 DB", "kind": "tree", "is_database": true, "id": "<목업 파일이 행으로 쌓이는 DB>"},
  {"name": "[TF] 작업 공간", "kind": "discover", "id": "<상위 작업 공간 페이지>", "depth": 2,
   "keywords": ["목업", "mockup", "기능정의서", "정의서", "역할", "권한", "인벤토리", "정책", "설계서"]}
 ],
 "sources_dir": "sources",
 "ignore": {"<page_id>": "<사용자가 정한 제외 이유>"},
 "mockup": {"pattern": "(?P<family>[a-z_]+?)_v(?P<ver>\\d+(?:\\.\\d+)*)\\.html", "family": "worxsales_mockup", "used_version": "1.7"},
 "code": {"repo": "<desktop 저장소>", "branch": "origin/develop", "map": "refresh/code_map.json"},
 "scenario_db": "config.json:scenario_db_id",
 "lanes": "refresh/lanes.json",
 "dashboard": {"page_id": "<상황판 페이지>", "exclude_out_of_scope_views": ["..."], "plain_views": ["..."]}
}
```

- 첫 번째 루트가 로컬 `sources/`와 대조하는 기능정의서 트리입니다.
- `tree` 루트는 본문·하위 페이지·DB 행·첨부를 모두 읽습니다. `discover` 루트는 제목만 `depth` 단계까지 읽어 키워드에 맞는 새 페이지를 찾습니다. 상위 작업 공간은 크고 원천이 아닌 페이지가 많으므로 `discover`로 둡니다.
- 루트는 하위 페이지가 아니라 **모아 두는 상위 페이지·DB**로 잡습니다. 새 버전이 형제 페이지나 새 행으로 생겨도 잡히게 하기 위해서입니다.

## code_map.json

경로 접두어 → 메뉴 번호 목록입니다. 가장 긴 접두어가 이깁니다. 제품 화면이 아닌 폴더(예제, UI 가이드, 문서)는 `[]`로 둡니다. 새 폴더는 `code_changes.py`가 `UNMAPPED`로 알려 주므로 그때 넣습니다.

## lanes.json

실행 결과 폴더 목록이며, 최신 레인이 먼저 옵니다. 일부 행만 판정에 쓰는 레인은 `only_ids_file`로 행을 한정합니다.

```json
[{"dir": "runs/run-2026-10-09-b566f"}, {"dir": "runs/run-2026-10-09-stg", "only_ids_file": "runs/run-2026-10-09-stg/_judged_ids.txt"}, {"dir": "runs/run-2026-10-09-full"}]
```

## state.json

`state.py`만 씁니다. `manifest`(마지막 성공 크롤 폴더), `code_commit`, `mockup_version`, `last_success`, `history`를 담습니다.
