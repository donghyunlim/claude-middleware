# 명령 모음

QA 작업 폴더에서 실행합니다. `R=refresh/run.sh`, 크롤 폴더 이름은 `S=refresh/$(date +%Y-%m-%d-%H%M)`로 둡니다.

```sh
# 1. 전체 크롤 (백그라운드 권장, 기능정의서 기준 수십 분)
bws-run "$PWD/$R" crawl.py refresh/watch.json "$S"

# 2. 변경 판정 (첫 실행이면 --prev 생략)
P=$(python3 <skill>/scripts/state.py show | python3 -c "import json,sys;print(json.load(sys.stdin).get('manifest',''))")
python3 <skill>/scripts/diff_sources.py refresh/watch.json "$S" ${P:+--prev "$P"} --out "$S/report.json"

# 3. 원천 반영 (dry run → --apply)
bws-run "$PWD/$R" apply_sources.py refresh/watch.json "$S" "$S/report.json"
bws-run "$PWD/$R" apply_sources.py refresh/watch.json "$S" "$S/report.json" --apply

# 4. 시나리오 (작업 폴더 스크립트)
python3 scripts/validate.py scenarios
bws-run "$PWD/scripts/run.sh" scripts/sync_scenarios.py scenarios <배치 이름>

# 5. 코드
python3 <skill>/scripts/code_changes.py refresh/watch.json <마지막 테스트 커밋> --out "$S/code.json"

# 6. Notion
bws-run "$PWD/$R" check_notion.py refresh/watch.json --out "$S/notion.json"
bws-run "$PWD/$R" check_notion.py refresh/watch.json --fix-out-of-scope

# 7. 기준점 (모든 점검 통과 뒤)
python3 <skill>/scripts/state.py commit --manifest "$S" --code <이번에 테스트한 커밋> --mockup <검토한 목업 버전>
```

`diff_sources.py`, `code_changes.py`, `check_notion.py`는 확인할 항목이 있으면 종료 코드 1을 냅니다. 오류가 아니라 「볼 것이 있음」입니다.
