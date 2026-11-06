# shop-admin

운영팀이 쓰는 사내 주문 관리 도구입니다.

- 주문 데이터: `data/orders.json` (`shop.orders.load_orders()`로 읽음)
- 시간은 저장할 때 UTC ISO-8601이고, 화면과 보고서에는 한국 시간(KST)으로 보여 준다.
- 실행: `python3 -m shop.cli list`
- 테스트: `python3 -m pytest -q`
