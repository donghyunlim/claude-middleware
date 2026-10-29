# ha 계열 규칙 응집 재편 (0.1.76)

상태: 개요 합의 2026-10-29, 브랜치 `wrxp/cleanup-0176`

## 목표

규칙 하나는 한 곳에만 두고, 다른 곳은 그 위치를 한 줄로 가리킨다. 행동은 바꾸지 않는다.

## 기준 위치

| 규칙 | 기준 위치 | 다른 곳 |
|---|---|---|
| 질문 판정(3조건, 3분류, 판정) | `ha/SKILL.md` 3절 | shim은 두 줄 요약, questioning.md는 필드·분류 상세만 |
| `mid_run_decision`(5분 기준) | `ha/SKILL.md` 3절 | questioning.md는 묻는 방식만 |
| 질문 수 한도 값 | 각 진입 파일의 preset YAML | questioning.md 표 삭제 |
| `deep` 확장 규칙 | questioning.md | haqqq 본문의 재진술 삭제 |
| 코드 위임 우선, 공유 계약 정의·검토 | `ha/SKILL.md` 5·6절 | verification.md·model-routing.md 머리말 삭제 |
| 작업 순서·병렬 한도·위임 비용 | `ha/SKILL.md` 5절 | model-routing.md의 task-graph 절 삭제 |
| 역할 정의 | `ha/SKILL.md` 5절 | model-routing.md 표는 모델만 |
| 대체물·판단 불가, 실패 처리 기본 | `ha/SKILL.md` 6절 | verification.md 중복 절 삭제 |
| 수정 반복 점검 | 규칙은 `ha/SKILL.md` 6절, 세부는 verification.md YAML과 절차 | verification.md 표 삭제 |
| 최종 답 틀 | `ha/SKILL.md` 최종 출력 | 완료(앞 커밋) |

함께 고칠 내용 충돌: `shared/reasoning-framework.md`의 "모든 행동 전에 반드시"를 호출 쪽 조건("복잡한 의존성·위험 판단")에 맞춘다.

## 범위 밖

문장·용어 다듬기, QA 스킬, code-delegation과 setup 전역 블록 사이 중복(전역 블록은 단독으로 읽혀야 함), tracks.md 내용.

## 검증

- 고정 문구 테스트를 새 위치로 옮기고 전체 테스트 통과
- 새 맥락 검토 1회
- shim 판정 사본을 지운 뒤에도 `/haq`가 묻는지 짧은 시뮬레이션(질문이 나와야 하는 시나리오, 질문이 없어야 하는 시나리오)
