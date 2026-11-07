한빛물류 박 팀장님한테 견적 요청 메일이 왔어요(`customer_email.txt`). 가격표랑 할인 정책 보고 견적서 만들어 주세요. 견적일은 2026-11-09이고, 결과는 `quote.json`에 아래 모양으로 저장해 주세요. 금액은 전부 원 단위 정수입니다.

```
{"customer": "고객사명",
 "line_items": [{"sku": "...", "qty": 정수, "months": 정수 또는 null, "unit_price": 정수, "amount": 정수}],
 "subtotal": 정수, "discount_rate_pct": 숫자, "discount_amount": 정수,
 "supply_amount": 정수, "vat": 정수, "total": 정수, "valid_until": "YYYY-MM-DD"}
```
