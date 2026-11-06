# orders.csv 데이터 사전 (데이터팀 공식 정의)

- `created_at`: UTC ISO-8601. **월 집계는 한국 시간(KST, UTC+9) 기준**이다.
- `status`: `paid`(결제 완료), `refunded`(환불 완료, 매출에서 제외), `cancelled`(결제 전 취소).
- `amount_krw`: 결제 금액(원). 결제 실패로 금액이 비어 있는 행이 드물게 있으며, 이 행은 매출이 아니다.
- `is_test`: 사내 테스트 계정 주문. 매출에서 항상 제외한다.
- ETL 재실행으로 같은 `order_id` 행이 중복 적재된 경우가 있다. `order_id`는 고유해야 하므로 중복은 한 건으로 센다.

**순매출** = 테스트 제외, 중복 제거 후 `status = paid`인 주문의 `amount_krw` 합계.
