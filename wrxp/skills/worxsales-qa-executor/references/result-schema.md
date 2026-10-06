# 결과 JSON 형식

행 하나당 `<run_dir>/<tc_id>.json` 하나. UTF-8, `ensure_ascii=false`. `publish_results.py`는 `headline`이 없는 파일(이전 형식)을 건너뜁니다.

```json
{
  "tc_id": "TC-07-28-007",
  "run_id": "run-2026-10-06-02",
  "started_at": "2026-10-06T22:10:00+09:00",
  "ended_at": "2026-10-06T22:16:00+09:00",
  "build": "desktop 79e0f27 (+local allowlist https://worxsales-backend.dev.jobko.io)",
  "role_context": "영업자 · 수정 가능 · JK",
  "target_data": "JK 그룹 43637, 회원 r-gi01",
  "verdict": "문제",
  "headline": "저장 안 한 메모가 탭을 닫으면 확인 없이 사라집니다",
  "checked": "비활성 레코드 탭을 닫을 때 미저장 입력을 지켜 주는지",
  "outcome": "공고 탭의 임시 입력에서는 확인 창이 뜨지만, 그룹 상세 ACNT 메모에서는 확인 없이 탭과 입력이 사라졌습니다.",
  "repro": ["① 그룹 상세 ACNT 메모에 글을 입력합니다", "② 저장하지 않고 다른 탭을 엽니다", "③ 메모가 있던 탭의 ×를 누릅니다"],
  "figures": [
    {"file": "TC-07-28-007-1.png", "zoom": "TC-07-28-007-1-zoom.png",
     "caption": "① 저장하지 않은 메모 입력", "marks": [{"n": 1, "label": "ACNT 메모 입력란(미저장)"}]},
    {"file": "TC-07-28-007-2.png", "caption": "③ ×를 누른 직후 — 확인 창 없이 탭이 닫힘",
     "marks": [{"n": 3, "label": "탭 표시줄: 메모 탭이 사라짐"}, {"n": "A", "label": "활성 탭은 그대로 유지"}]}
  ],
  "details": {
    "verdict_reason": "기대결과 후반부 ‘비활성 탭에 미저장 입력이 있으면 같은 확인 규칙 적용’(7-28-A04)을 충족하지 않음.",
    "actions": [{"step": 1, "action": "click", "target": "그룹번호 43637 링크", "observed": "그룹 상세 탭이 열림"}],
    "name_mismatches": [{"doc": "레코드 탭", "app": "작업 탭"}],
    "scenario_issue": "",
    "side_findings": ["기업 상세 탭 제목에 내부 키가 그대로 보임"]
  }
}
```

| 키 | 쓰는 법 |
|---|---|
| verdict | `OK` / `문제` / `미구현` / `실행 불가` / `보류-기록` / `알려진 차이` (판정 기준은 SKILL.md) |
| headline | 사람이 DB 목록에서 읽는 한 줄 결론. 30~50자, 결과를 말하는 완결 문장. 판정 이름을 반복하지 않음 |
| checked | 이 행이 무엇을 확인했는지. 기능 언어로, 문서 ID 없이 |
| outcome | 실제로 본 것. 화면 이름과 값으로. 1~3문장 |
| repro | 문제·알려진 차이일 때만. 번호는 그림의 번호표와 같은 번호를 씀 |
| figures | 판정 근거가 되는 장면만, 보통 1~3장. `marks`의 `n`은 그림 안 번호표와 같아야 함. 숫자는 repro 단계, `"A"`·`"B"`는 보조 표시 |
| details | 개발자용. 액션 로그, 판정 근거 조항, 이름 대응, 시나리오 문제, 행 범위 밖 관찰 |
