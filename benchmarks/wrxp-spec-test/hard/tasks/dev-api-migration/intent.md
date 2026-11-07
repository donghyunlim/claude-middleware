너는 billing-ops 담당 테크 리드다. v2 마이그레이션에 대해 정해 둔 것은 아래와 같다.
- `app/`(billing, notify, reports, cli)은 v1 `CRMClient`를 더 이상 쓰지 않고 v2 `CustomerAPI`만 쓴다.
- v1 `crmkit/client_v1.py`의 `CRMClient`는 이번 릴리스에서는 지우지 않는다. 다른 팀이 아직 쓰고 있어서 한 릴리스 동안 그대로 동작해야 한다(반환 형식·동작은 지금과 같음). 대신 `CRMClient`를 만들 때 `DeprecationWarning`이 나게 해서 v2로 옮기라고 알린다.
- v1의 `name`은 v2의 `legal_name`(사업자 등록상 상호)에 대응한다. 청구서 머리말과 갱신 안내 문자 모두 `legal_name`을 쓴다. `display_name`(앱 별칭)은 쓰지 않는다.
- 마이그레이션 후에도 결과는 이전과 완전히 같아야 한다.
  - `monthly_signups`는 고객이 50명이 넘어도 전부 센다(v2 `list_customers`는 한 페이지만 준다).
  - 가입 월은 이전처럼 한국 시간(KST) 기준이다(v2 `created_at`은 UTC).
  - `renewal_messages`는 CRM에 없는 고객을 이전처럼 건너뛴다(예외를 내지 않는다). `invoice_header`는 없는 고객이면 이전처럼 KeyError를 낸다.
- 그 밖의 구현 방식은 알아서 해도 된다.
