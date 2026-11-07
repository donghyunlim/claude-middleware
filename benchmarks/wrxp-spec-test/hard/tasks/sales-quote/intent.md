너는 한빛물류 건을 맡은 영업 담당자다. 박 팀장과 통화해서 확인한 내용과 견적 방침은 아래와 같다.
- 좌석 수는 120석, 약정 기간은 3년(36개월)이다.
- 플랜은 Business(BIZ-SEAT)이고 SSO 애드온(ADDON-SSO)을 120석 모두에 붙인다. Enterprise는 최소 200석이라 해당 없다.
- 온보딩 교육(SVC-ONBOARD) 1회를 넣는다. 그 외 항목은 넣지 않는다.
- line_items: 구독 항목은 qty=좌석 수, months=36, unit_price=좌석당 월 단가, amount=qty×unit_price×months. 일회성 항목은 months=null, amount=qty×unit_price.
- 할인은 할인 정책 문서대로: 좌석 할인과 약정 할인을 합산하되 최대 20%로 제한한다. 할인은 구독 항목에만 적용하고 일회성 서비스(온보딩)에는 적용하지 않는다. discount_rate_pct는 실제 적용한 비율(20)이다.
- 공급가액(supply_amount)은 subtotal에서 할인을 뺀 뒤 천 원 미만을 절사한 금액이다. discount_amount는 subtotal − supply_amount다(절사분 포함).
- 부가세(VAT)는 공급가액의 10%로 따로 표시하고 원 미만은 절사한다. total = supply_amount + vat.
- 견적 유효기간은 팀장 승인을 받아 30일로 한다: valid_until = 2026-12-09.
- customer는 "한빛물류"라고 쓰면 된다.
