요즘 안 들어오는 휴면 고객들 다시 불러오는 이메일 캠페인 하나 잡아 주세요. 고객 데이터랑 쿠폰 목록은 폴더에 있어요. 계획은 `campaign.json`에 아래 형식으로 저장해 주세요.

```json
{
  "target_customer_ids": ["C0001", "..."],
  "send_at": "ISO-8601 발송 시각",
  "subjects": ["제목", "..."],
  "coupon_code": "쿠폰 코드",
  "holdout_pct": 0,
  "footer": "본문 하단 문구"
}
```
