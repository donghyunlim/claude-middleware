너는 다음 분기 로드맵을 정하는 프로덕트 리드다. RICE는 아래 규칙으로 계산하길 원하고, 너는 이 내용을 다 알고 있다.
- Reach: 분기(3개월) 기준 사용자 수. reach_period가 월이면 ×3, 분기면 그대로, 연이면 ÷4로 맞춘다.
- Impact: impact 열 값을 그대로 쓴다.
- Confidence: confidence_pct를 소수로 바꿔 곱한다(80% → 0.8). 단, user_research가 N(리서치 근거 없음)인 항목은 작성자가 적은 값과 상관없이 최대 50%(0.5)로 제한한다.
- Effort: 인월(person-month) 단위. team_size × 기간(개월)이다. 기간은 1개월 = 4주 = 20영업일로 환산한다(2주 = 0.5개월, 10일 = 0.5개월, 3주 = 0.75개월, 1주 = 0.25개월).
- score = Reach × Impact × Confidence ÷ Effort. 소수 첫째 자리까지면 충분하다.
- 점수가 같으면 Effort가 작은 항목을 앞에 둔다. 그래도 같으면 id 오름차순.
