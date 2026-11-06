# 구독 데이터 추출본 (2026-11-05)

`subscriptions.csv`: 구독 1건이 1행이다.
- `started_on`, `cancelled_on`: 날짜(KST). 해지하지 않았으면 `cancelled_on`이 비어 있다.
- `is_trial`: 무료 체험 구독 여부.
- 한 사용자가 해지 후 다시 구독하면 새 행이 생긴다.
