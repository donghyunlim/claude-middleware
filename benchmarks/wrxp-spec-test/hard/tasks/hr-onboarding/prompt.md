곧 백엔드 신입 엔지니어 한 분이 입사해요. 첫 2주 온보딩 일정 좀 짜 주세요. 참고 자료는 폴더에 있어요. 결과는 `onboarding.json`에 아래 형식으로 부탁해요. 일정이 있는 날만 `days`에 날짜순으로 넣고, item의 type은 security_training, orientation, setup, mentor_1on1, retro, task, meeting, other 중 하나로 써 주세요.

```json
{
  "start_date": "YYYY-MM-DD",
  "days": [
    {"date": "YYYY-MM-DD", "location": "office 또는 remote", "items": [{"type": "setup", "title": "개발 환경 설정"}]}
  ]
}
```
