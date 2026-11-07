# salesreport

분기 판매 리포트 생성기. 재무팀 정산 시스템이 결과 텍스트를 그대로 파싱해서 쓴다.

```
python3 -m salesreport.cli data out/report.txt   # 리포트 생성
python3 bench.py data 3                          # 생성 시간 측정
python3 -m pytest -q                             # expected/report.txt 와 비교
```

## 데이터 (`data/`)
- `order_lines.csv` — 주문 라인(order_id, order_date, customer_id, sku, qty). customer_id 앞뒤에 공백이 섞여 있을 수 있음
- `products.csv` — 상품(sku, name, category, unit_price, currency). 통화는 KRW/USD/JPY
- `customers.csv` — 고객(customer_id, name, region, tier)
- `fx_rates.csv` — 환율 고시(date, currency, krw_per_unit). 영업일에만 고시됨, 파일은 날짜순이 아님

운영 데이터는 주문 라인이 수만 건, 상품·고객이 수천 건, 환율 이력이 몇 년 치 규모다.
배치 서버는 한 프로세스에서 여러 데이터 폴더(매일 갱신)에 대해 `build_report`를 연달아 호출한다.
