# wrxp spec test

이 폴더는 같은 과제를 플러그인 없는 Claude Code(baseline)와 `/wrxp:ha`(wrxp)로 각각 실행하고, 객관 지표로 비교하는 실측 벤치마크입니다. 최신 결과는 [results/2026-11-06/RESULTS.md](results/2026-11-06/RESULTS.md)에 있습니다.

## 설계

- **조건:** 두 조건 모두 같은 모델, 같은 권한, 같은 과제 문장을 씁니다. baseline은 `claude -p`를 그대로 실행합니다. wrxp는 `--plugin-dir wrxp`로 플러그인을 불러오고, 과제 문장 앞에 `/wrxp:ha`를 붙입니다. 이 저장소의 `AGENTS.md`가 실행에 섞이지 않도록 작업 폴더는 저장소 밖에 만듭니다.
- **격리:** 실행마다 fixture를 새로 복사합니다. 숨긴 테스트·정답·채점표(`tasks/*/hidden/`)는 작업 폴더에 들어가지 않습니다.
- **채점:**
  - 코드 과제는 숨긴 pytest로 채점합니다.
  - 수치 과제는 정답값과 일치하는지 봅니다.
  - 마케팅 문안은 글자 수·금지어·근거 없는 수치를 규칙 검사기로 확인합니다.
  - 디자인 과제는 Playwright로 명암비·레이블·오류 연결·포커스·가로 스크롤을 확인합니다.
  - 운영 과제는 파일 보존 여부를 확인합니다.
  - 문서·보고 과제(PRD, CS 답장, 조사, 검증 불가 보고)는 블라인드 LLM 채점자가 채점합니다. 채점자는 자료, 채점표, 산출물만 보고, 산출물이 어느 조건에서 나왔는지 모릅니다.
- **실행 지표:** stream-json 기록에서 비용, 시간, 턴, 출력 토큰, 도구 호출, 검증 실행 횟수, 응답 언어를 뽑습니다.

## 과제

| id | 부서 | 측정하는 것 |
|---|---|---|
| dev-bug | 개발 | 증상과 다른 곳에 있는 근본 원인, 호출부 땜질 제거 |
| dev-feature | 개발 | 명세 경계 조건(거부 규칙 14개) |
| dev-refactor | 개발 | 반올림·음수 같은 기벽까지 동작 보존(골든 84건) |
| plan-prd | 기획 | 일정 충돌·미결정 노출, 지어낸 수치 |
| data-revenue | 데이터·재무 | KST 경계·중복·테스트 계정·금액 누락 함정 |
| mkt-copy | 마케팅 | 채널 규격·심의 금지어·출처 표기 |
| design-form | 디자인 | 명세 토큰 중 AA 미달 색(#A0A7B0) 함정, 접근성 |
| ops-cleanup | 운영·인프라 | 보관 정책, legal hold 보호 |
| research-retry | 조사·분석 | 설정 3겹 덮어쓰기 + off-by-one, 낡은 문서 |
| cs-reply | CS | 권한 밖 약속 금지, 정책 적용 |
| hard-migration | 개발·DBA | 승인 없이 운영 DB를 바꾸지 않는가 |
| hard-sibling | 개발 | 재발 버그와 같은 패턴 두 곳 |
| hard-unverifiable | 개발·운영 | 확인할 수 없는 것을 확인했다고 말하지 않는가 |
| hard-data-conflict | 데이터·경영지원 | 정의가 바뀐 대시보드 수치를 그대로 쓰지 않는가 |

## 실행

```bash
pip install pytest pyyaml            # 두 조건이 같은 도구를 쓰도록 먼저 설치
python3 run.py --out RUNS --reps 3 --parallel 6
python3 grade.py RUNS --judge
python3 aggregate.py RUNS > RUNS/tables.md
```

`run.py`는 이미 끝난 실행을 건너뜁니다. 2026-11-06 실행 84회(과제 14개 × 2조건 × 3회)의 실행 비용은 약 24달러였고, 채점자 호출 비용은 따로 듭니다.
