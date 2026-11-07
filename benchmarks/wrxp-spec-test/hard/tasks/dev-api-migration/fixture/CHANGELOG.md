# crmkit CHANGELOG

## 2.0.0 (2026-10-20)

새 클라이언트 `crmkit.client_v2.CustomerAPI`를 추가했습니다. v1 `CRMClient`는 서버의 /v1 엔드포인트가 내려가는 대로 제거될 예정입니다.

### 변경 사항 (v1 → v2)
- 고객 정보가 dict 대신 `crmkit.models.Customer` 데이터클래스로 반환됩니다.
- 필드 이름 변경:
  - `id` → `customer_id`
  - `phone` (`010-1234-5678`) → `phone_e164` (`+821012345678`)
  - `joined` (가입일, `YYYY-MM-DD`) → `created_at` (`datetime`)
  - `name` → `legal_name` / `display_name` 두 필드로 분리되었습니다. `legal_name`은 사업자 등록상 상호, `display_name`은 고객이 앱에서 설정한 별칭입니다.
- `fetch(customer_id)`는 고객이 없으면 `None` 대신 `CustomerNotFound`를 발생시킵니다.
- **`list_customers()`는 이제 한 페이지(기본 50건)만 반환합니다.** 전체 고객이 필요하면 `iter_customers()`를 쓰세요.
- **`created_at`은 UTC 기준 시각입니다.** v1의 `joined`는 서버가 KST로 변환한 날짜였습니다. 한국 날짜가 필요하면 직접 KST(UTC+9)로 변환해야 합니다.

## 1.4.2 (2026-05-02)
- `CRMClient.list_customers()` 응답 속도 개선.
