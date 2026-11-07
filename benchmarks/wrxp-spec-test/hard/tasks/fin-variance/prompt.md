3분기 부서별 예산 대비 실적 좀 정리해 주세요. 자료는 폴더에 다 있어요. 결과는 `variance.json`에 아래 형식으로 부탁합니다. 금액은 원 단위 정수, variance는 실적 − 예산, variance_pct는 variance ÷ 예산 × 100이고, material은 경영회의에 올릴 만큼 큰 차이인지 여부예요.

```json
{"departments": [{"dept": "부서명", "budget": 0, "actual": 0, "variance": 0, "variance_pct": 0.0, "material": false}]}
```
