# 데이터 사전 (product analytics export)

## data/users.csv
| 컬럼 | 설명 |
|---|---|
| user_id | 사용자 ID |
| email | 가입 이메일 |
| signup_channel | 유입 채널(organic / ads / referral) |

## data/events.csv
| 컬럼 | 설명 |
|---|---|
| event_id | 이벤트 ID |
| user_id | 사용자 ID (users.csv와 조인) |
| event_type | `signup`(가입), `login`(로그인), `payment`(결제 성공), `payment_failed`(결제 시도 실패 — 매출 아님) |
| event_ts | 이벤트 시각, **UTC** ISO-8601 (`Z`) |
| amount | 결제 금액(원). payment / payment_failed에만 값이 있음 |

## 주의 사항
- **내부 테스트 계정**: `user_id`가 `test_`로 시작하거나 `email`이 `@ourapp.kr` 도메인인 계정은 QA·사내 계정입니다. 모든 지표 집계에서 제외합니다.
- 가입 시각은 `event_type = signup` 이벤트의 시각입니다. 사용자당 signup은 1건입니다.
