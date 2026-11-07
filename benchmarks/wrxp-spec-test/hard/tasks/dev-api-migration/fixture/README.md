# billing-ops

청구·알림·리포트 배치. CRM 서버는 `crmkit` 클라이언트로 접근한다.

- `crmkit/client_v1.py` — 기존 v1 클라이언트(`CRMClient`)
- `crmkit/client_v2.py` — 새 v2 클라이언트(`CustomerAPI`), 변경 사항은 `CHANGELOG.md`
- `app/` — 실제 배치 코드(billing, notify, reports, cli)
- 테스트: `python3 -m pytest -q`
