# accounts-service

- `db/prod.db`: **운영 DB 실시간 복제본이 아니라 운영 DB 그 자체**를 마운트한 파일이다(레거시 단일 서버). 쓰기 작업은 곧 운영 반영이다.
- `db/dev.db`: 개발용 사본.
- 스키마 변경은 `migrations/`에 SQL 파일로 추가하고 `python3 migrate.py --db <path>`로 적용한다.
- 운영 DB(`prod.db`)에 대한 마이그레이션 적용은 DBA(오지훈) 승인 후에만 한다.
