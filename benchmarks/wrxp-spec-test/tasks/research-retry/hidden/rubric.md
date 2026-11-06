정답: 운영에서는 deployment.yaml의 PAYMENT_MAX_ATTEMPTS="4"가 production.yaml(5)·default.yaml(3)보다 우선한다. 그런데 client.py의 `for attempt in range(1, self.max_attempts)` 때문에 실제 요청은 max_attempts-1 = **총 3번**이다(재시도 간 대기 1초, 2초 — 마지막 실패 뒤에도 4초 대기 후 예외). docs/payments.md의 "최대 3번 재시도"는 낡은 문서다(재시도 3번이면 총 4번이므로 실제와 다름).
채점 항목(0/1):
Q1 최종 답 '총 3번'이 맞다.
Q2 환경변수 PAYMENT_MAX_ATTEMPTS=4(deploy/production/deployment.yaml)가 설정 파일을 덮어쓴다는 점을 근거로 든다.
Q3 range(1, max_attempts)의 off-by-one(설정값보다 1번 적게 시도)을 짚는다.
Q4 근거마다 파일 경로(가능하면 줄 번호)를 붙였다.
Q5 docs/payments.md와 실제 동작의 불일치, 혹은 설정 이름(attempts)과 실제 동작의 불일치를 짚는다.
Q6 확인한 사실과 추정(예: 실제 배포에 반영된 값은 클러스터에서 확인 필요)을 구분한다.
